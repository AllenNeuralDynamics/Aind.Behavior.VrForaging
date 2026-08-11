"""Deterministic S/D/N reversal task-logic generator (tyro CLI).

Builds an ``AindVrForagingTaskLogic`` for the batch-8 deterministic-reversal paradigm and
writes a standalone ``TrainerState`` JSON for deployment via the launcher (not the
curriculum system).

**The task comes from the curriculum, not from this file.** Each block is the vendored
``graduation`` stage of ``deterministic_reversals`` (``--reward full``) or
``deterministic_reversals_reward_capped`` (``--reward capped``), deep-copied and repointed at
a different odor permutation. Corridor geometry, stop duration, reward delay, reward curves
and operation control are all inherited, so a curriculum edit propagates here automatically
and the two cannot drift apart. See :func:`baseline_block`.

This matters because they did drift: an earlier version redeclared the whole task alongside
the curriculum, and the copies diverged (corridor 150-400 vs 100-250 cm, stop duration 1.0 vs
0.5 s, an exponential reward delay silently replaced by a normal one). Mice ran a measurably
different task from the one the curriculum described, under stage names that looked like plain
baselines. ``tests/test_task_reversal.py`` now pins ``no_reversal --step set1`` to be exactly
the curriculum's ``graduation``, since set1 *is* graduation's permutation.

Each block has three patch types (defined by the curriculum):

- ``single``   – one guaranteed reward on the first stop, then depleted.
- ``delayed``  – depleting/accumulating reward across stops (``--reward`` picks capped or
  uncapped; both are ~3 drops).
- ``no_reward``– never rewarded.

The odor↔contingency assignment is chosen by a **set** permutation over the three
olfactometer **channel indices** (0/1/2); a *reversal* swaps the set between blocks. The
physical odorant on each channel lives in the **rig config** (``rig_input.json`` /
instrument metadata), NOT here — this file only says "the odor on channel k".

Every physical knob defaults to ``None`` = inherit. Passing one is an explicit deviation from
the curriculum, and it is stamped into the stage name (``_sd1.5``, ``_ipmin150``, …) so a
modified task can never share a name — or a ``trainer_state`` — with the baseline. Overrides
retune values the curriculum already exposes; changing a distribution family, the patch count,
or a reward curve's shape is a curriculum edit, not a flag.

Examples:

Reproduce the graduation config exactly (set1, capped, no reversal, no overrides):
    uv run python examples/task_reversal.py --group no_reversal --step set1 --reward capped

One S↔D reversal (set1 -> set6) after 20 stops (default unit), capped rewards:
    uv run python examples/task_reversal.py --group single_reversal --step set1 --transition set6 --reward capped --block-length 20

Repeated S↔D reversals only, every 30 stops (blocks alternate set1 <-> set6; no-reward
odor stays pinned to one channel for the whole session), with a longer first block to
absorb warm-up and carry-over from the previous session:
    uv run python examples/task_reversal.py --group alternating --swap DS --step set1 --n-reversals 5 --block-length 30 --first-block-length 80

Count blocks in PATCHES encountered instead of stops (the original behaviour -- predictable
structure and N guaranteed odor presentations, but a skipping animal reaches the reversal
barely having sampled). Add --patch-cap under the default stop-counting to bound how long a
disengaged animal can stall in one block:
    uv run python examples/task_reversal.py --group single_reversal --count-by patches --block-length 40
    uv run python examples/task_reversal.py --group single_reversal --count-by stops --block-length 40 --patch-cap 80

Infer the current set from a mouse's last uploaded session, then just pick the reversal:
    uv run python examples/task_reversal.py --from-mouse 867424 --group single_reversal --transition set6 --reward capped --block-length 20

Infer from the freshest session still staged on the NAS (not yet uploaded to S3):
    uv run python examples/task_reversal.py --from-session /path/to/nas/867424_2026-07-13_20-27-51 --group single_reversal --transition set6 --reward capped

Deviate from the curriculum on purpose (tagged _sd1 _ipmin150 _ipmax400 in the stage name):
    uv run python examples/task_reversal.py --group no_reversal --step set1 --stop-duration 1.0 --minimum-interpatch-length 150 --maximum-interpatch-length 400
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Optional, cast

import tyro
from aind_behavior_curriculum import Stage, TrainerState
from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)
from aind_behavior_vr_foraging_curricula import __semver__
from aind_behavior_vr_foraging_curricula.deterministic_reversals import (
    _stages_shared,
    stages as _stages_full,
)
from aind_behavior_vr_foraging_curricula.deterministic_reversals_reward_capped import (
    stages as _stages_capped,
)

SetName = Literal["set1", "set2", "set3", "set4", "set5", "set6"]
RewardMode = Literal["full", "capped"]
Group = Literal["no_reversal", "single_reversal", "multiple_reversal", "alternating"]
PatchType = Literal["single", "delayed", "no_reward"]
SwapKind = Literal["DS", "DN", "SN"]
CountBy = Literal["stops", "patches"]
_DEFAULT_COUNT_BY: CountBy = "stops"

#: The curriculum whose ``graduation`` stage each reward mode inherits from. Everything
#: physical -- geometry, timings, reward curves, operation control -- comes from here, so a
#: curriculum edit propagates and cannot silently diverge. See ``baseline_stage``.
_BASELINE_STAGE = {
    "capped": _stages_capped.make_s_stage_graduation,
    "full": _stages_full.make_s_stage_graduation,
}
_BASELINE_CURRICULUM = {
    "capped": "DeterministicReversalsRewardCapped",
    "full": "DeterministicReversals",
}
#: The only structural assumption made about the vendored stage: three patches with these
#: labels, carrying these contingencies. Checked on every build, so a curriculum reshape
#: fails loudly here instead of silently emitting a stale task.
BASELINE_PATCHES: dict[str, str] = {
    "patch_null": "noreward",
    "patch_delayed": "delayed",
    "patch_single": "single",
}

# Which olfactometer channel index (0/1/2) carries each contingency, per set.
ODOR_LABEL: dict[str, dict[str, int]] = {
    "set1": {"single": 2, "delayed": 1, "noreward": 0},
    "set2": {"single": 1, "delayed": 0, "noreward": 2},
    "set3": {"single": 0, "delayed": 2, "noreward": 1},
    "set4": {"single": 2, "delayed": 0, "noreward": 1},
    "set5": {"single": 0, "delayed": 1, "noreward": 2},
    "set6": {"single": 1, "delayed": 2, "noreward": 0},
}

# Reverse lookup: (single_ch, delayed_ch, noreward_ch) -> set name, for inferring the
# current set from an existing session's channel mapping.
_SET_BY_MAPPING: dict[tuple[int, int, int], str] = {
    (m["single"], m["delayed"], m["noreward"]): name for name, m in ODOR_LABEL.items()
}

# Fixed loop order for the multiple-reversal group (single-swap reversals, S-D-N).
_MULTI_REVERSAL_LOOP: list[SetName] = ["set1", "set6", "set2", "set5", "set3", "set4"]

# Default steady-state block length; deviations are tagged into the stage name.
_DEFAULT_BLOCK_LENGTH = 40


@dataclass
class ReversalConfig:
    """Parameters for a deterministic-reversal session."""

    group: Group = "single_reversal"
    """Reversal structure: no_reversal (1 block), single_reversal (step→transition, one
    flip), multiple_reversal (fixed S-D-N loop over all six sets), alternating (repeated
    reversals of a single restricted type — see ``swap``)."""
    step: SetName = "set1"
    """The set used for the first block (and the only block when no_reversal)."""
    transition: SetName = "set6"
    """The set after the reversal (single_reversal only)."""
    swap: SwapKind = "DS"
    """Which contingency pair reverses, for group=alternating. Each single-swap relation is
    an involution, so the sequence alternates between ``step`` and its unique partner."""
    n_reversals: int = 5
    """Number of reversals for group=alternating (blocks = n_reversals + 1)."""

    from_mouse: Optional[str] = None
    """Infer --step from this mouse's most recent *uploaded* session on S3. Not-yet-uploaded
    sessions won't appear (upload can lag ~12 h) — use --from-session for those."""
    from_session: Optional[str] = None
    """Infer --step from a specific session: an s3:// URI or a local/NAS path (a session root
    or a tasklogic_input.json directly). Takes precedence over --from-mouse."""
    bucket: str = "aind-open-data"
    """S3 bucket searched by --from-mouse."""

    reward: RewardMode = "capped"
    """Which vendored curriculum to inherit the task from. ``capped`` =
    DeterministicReversalsRewardCapped (hard-caps delayed volume at amount×3 and guarantees
    the first stop); ``full`` = DeterministicReversals (same ~3-drop curve, no volume cap)."""
    block_length: int = _DEFAULT_BLOCK_LENGTH
    """Length of every non-terminal block, in units of ``count_by`` (stops or patches); the
    final block runs to session end.

    The two units are NOT interchangeable, but they happen to land close together here: this
    is a depleting-patch task, so one patch hosts many stops -- measured on 867424
    (2026-07-28): 253 patches, only 41% visited at all, ~3.0 stops per visited patch, 310
    stops total. So 40 stops ~ 33 patches for that mouse, and a number tuned in one unit
    roughly carries over to the other. Re-check the ratio per cohort before relying on it,
    since it moves with both skip rate and exploitation depth."""
    first_block_length: Optional[int] = None
    """Length of the FIRST block only, in units of ``count_by``; defaults to
    ``block_length``. The first block carries warm-up and whatever the animal brings over
    from the previous session, so it usually wants to be longer than the steady-state
    blocks. Ignored when the first block is also the last (no_reversal), since that one is
    unbounded."""
    count_by: CountBy = _DEFAULT_COUNT_BY
    """Currency the block advances in: "stops" (``ChoiceFeedback``) or "patches"
    (``ActivePatch``, i.e. every patch encountered, stopped at or not). "patches" is the
    original behaviour -- predictable structure and N guaranteed odor presentations; "stops"
    is robust to an animal that skips its way to the reversal. See ``make_end_condition``
    for the trade-off. The choice is tagged into the stage name (``_pb``/``_sb``)."""
    patch_cap: Optional[int] = None
    """Optional upper bound in PATCHES on every non-terminal block. End conditions are merged
    (first to fire wins), so this bounds how long a disengaged animal can sit in one block
    without ever reaching ``block_length``. ``None`` means pure stop-gating. Only
    meaningful when ``count_by="stops"``; ignored otherwise."""

    # --- Physical overrides -------------------------------------------------------------
    # Every field below defaults to None, meaning "inherit from the vendored graduation
    # stage". Passing one deviates from the curriculum, and any deviation is stamped into the
    # stage name (see OVERRIDES) so a modified task can never share a filename -- or a
    # trainer_state -- with the baseline. Overrides retune values the curriculum already
    # exposes; they never change structure. Changing a distribution FAMILY, the patch count,
    # or a reward curve's shape is a curriculum edit, not a flag.
    stop_duration: Optional[float] = None
    """Seconds the animal must hold still to register a choice. None inherits (0.5)."""
    delay_mean: Optional[float] = None
    """Mean of the curriculum's exponential reward delay, in seconds. None inherits (0.5).
    Retunes the rate; it does not switch distribution family."""
    reward_amount: Optional[float] = None
    """Per-drop reward volume (uL) for the two rewarded patches. None inherits (5.0). The
    delayed patch's payout curve is re-derived from the curriculum's own ``deterministic_curves``
    so the volume cap stays consistent with the drop size."""
    velocity_threshold: Optional[float] = None
    """Stop-velocity threshold (cm/s). None inherits (8.0)."""
    rewardsite_length: Optional[float] = None
    """Reward-site length (cm). None inherits (50)."""
    minimum_interpatch_length: Optional[float] = None
    """Inter-patch floor (cm). None inherits (100)."""
    maximum_interpatch_length: Optional[float] = None
    """Inter-patch ceiling (cm). None inherits (250)."""
    minimum_intersite_length: Optional[float] = None
    """Inter-site floor (cm). None inherits (20)."""
    maximum_intersite_length: Optional[float] = None
    """Inter-site ceiling (cm). None inherits (80)."""

    weight_null: float = 1.0
    """Relative frequency of the no-reward patch. Under a DS-only reversal the null odor
    never changes channel, so it carries no information about the reversal — down-weight it
    to spend more of a finite session on the two contingencies that do swap. Setting it to
    0 keeps the patch defined (so state indices stay stable for analysis) but never visited."""
    weight_delayed: float = 1.0
    """Relative frequency of the delayed patch."""
    weight_single: float = 1.0
    """Relative frequency of the single patch."""

    output: str = "./local/task_logic_schemas/{stage_name}.json"
    """Output path template for the TrainerState JSON ({stage_name} is substituted)."""

    def patch_weights(self) -> list[float]:
        """Relative patch frequencies in ``state_index`` order: null, delayed, single."""
        return [self.weight_null, self.weight_delayed, self.weight_single]


def occupancy_matrix(weights: list[float]) -> tuple[list[float], list[list[float]]]:
    """Return ``(first_state_occupancy, transition_matrix)`` realizing ``weights``.

    Every row of the matrix is the same normalized weight vector, so patch identity is
    drawn i.i.d. and each patch's long-run frequency is exactly its normalized weight
    (equal weights reproduce the original uniform matrix). Keeping the rows identical also
    means the mix is unaffected by which patch the animal just visited.
    """
    total = sum(weights)
    if total <= 0 or any(w < 0 for w in weights):
        raise ValueError(
            f"Patch weights must be non-negative with a positive sum; got {weights}."
        )
    row = [w / total for w in weights]
    return row, [list(row) for _ in weights]


def make_odor_index(index: int, n_odors: int = 3) -> list[float]:
    """One-hot odor specification over ``n_odors`` channels."""
    odor = [0.0] * n_odors
    odor[index] = 1.0
    return odor


def baseline_block(reward: RewardMode) -> task_logic.Block:
    """The vendored ``graduation`` block for ``reward`` -- the single source of task truth.

    Everything physical lives here: corridor geometry, stop duration, reward delay, reward
    curves, patch terminators. This generator only ever permutes odors, slices blocks, and
    applies the explicit overrides in :data:`OVERRIDES` on top. Nothing about the task is
    redeclared locally, so a curriculum edit propagates and the two cannot drift apart.

    ``graduation`` is itself set1 (null=ch0, delayed=ch1, single=ch2), so a ``no_reversal``
    set1 state is byte-identical to the curriculum's own stage apart from the ``_ch<n>``
    label suffix. ``tests/test_task_reversal.py`` pins exactly that.
    """
    stage = _BASELINE_STAGE[reward]()
    blocks = stage.task.task_parameters.environment.blocks
    if len(blocks) != 1:
        raise ValueError(
            f"Vendored graduation for reward={reward!r} has {len(blocks)} blocks, expected 1. "
            "The curriculum changed shape; this generator needs updating."
        )
    labels = {p.label for p in blocks[0].environment.patches}
    if labels != set(BASELINE_PATCHES):
        raise ValueError(
            f"Vendored graduation for reward={reward!r} has patches {sorted(labels)}, expected "
            f"{sorted(BASELINE_PATCHES)}. The curriculum changed shape; update BASELINE_PATCHES."
        )
    return blocks[0]


def baseline_operation_control(reward: RewardMode):
    """The vendored stage's operation control (velocity threshold and friends)."""
    return _BASELINE_STAGE[reward]().task.task_parameters.operation_control


# ---------------------------------------------------------------------------
# Explicit overrides
# ---------------------------------------------------------------------------
# Each entry pairs a reader (the inherited value) with a writer, so "did this actually change
# anything?" is mechanical rather than assumed. An override enters the stage name only when
# its value DIFFERS from the inherited one -- passing --stop-duration 0.5 on a curriculum that
# already uses 0.5 is a no-op and collapses to the baseline name, keeping name == task.


@dataclass(frozen=True)
class Override:
    """One explicitly overridable scalar on the vendored baseline."""

    tag: str
    """Short stage-name tag, e.g. ``sd`` -> ``_sd1.5``. Must be unique across OVERRIDES."""
    read: Callable[[task_logic.Patch], Optional[float]]
    """Inherited value for a patch, or None where the field does not apply to it."""
    write: Callable[[task_logic.Patch, float], None]
    """Apply the new value to a patch."""


def _sites(patch: task_logic.Patch):
    return patch.patch_virtual_sites_generator


def _set_reward_amount(patch: task_logic.Patch, value: float) -> None:
    """Retune the drop size, re-deriving the payout curve from the curriculum's own builder.

    The delayed patch's cap is a function of the drop size (``ClampedRateFunction`` rate
    ``-amount`` and maximum ``amount x 3``), so setting ``amount`` alone would leave the cap
    describing the old volume. Rebuilding via ``deterministic_curves`` keeps them consistent
    by construction rather than by a local copy of the arithmetic.
    """
    old = patch.reward_specification.amount.distribution_parameters.value
    if not old:
        return  # the null patch pays nothing; a drop size is meaningless there
    contingency = BASELINE_PATCHES[_base_label(patch)]
    capped = (
        patch.reward_specification.available.distribution_parameters.value == old * 3
    )
    patch.reward_specification.amount = task_logic.scalar_value(value)
    patch.reward_specification.reward_function = _stages_shared.deterministic_curves(
        amount_drop=value,
        option=cast(Literal["single", "delayed"], contingency),
        cap_delayed_rewards=capped,
    )
    if capped:
        patch.reward_specification.available = task_logic.scalar_value(value * 3)


OVERRIDES: dict[str, Override] = {
    "stop_duration": Override(
        tag="sd",
        read=lambda p: (
            p.reward_specification.operant_logic.stop_duration.distribution_parameters.value
        ),
        write=lambda p, v: setattr(
            p.reward_specification.operant_logic,
            "stop_duration",
            task_logic.scalar_value(v),
        ),
    ),
    # The curriculum's delay is Exponential(rate=1/mean); an override retunes the rate. It does
    # NOT switch family -- swapping Exponential for Normal is exactly the silent structural
    # change that put the batch-8 cohort on a different task than the curriculum described.
    "delay_mean": Override(
        tag="dm",
        read=lambda p: 1.0 / p.reward_specification.delay.distribution_parameters.rate,
        write=lambda p, v: setattr(
            p.reward_specification.delay.distribution_parameters, "rate", 1.0 / v
        ),
    ),
    "reward_amount": Override(
        tag="rw",
        read=lambda p: (
            p.reward_specification.amount.distribution_parameters.value or None
        ),
        write=_set_reward_amount,
    ),
    "rewardsite_length": Override(
        tag="rs",
        read=lambda p: (
            _sites(p).reward_site.length_distribution.distribution_parameters.value
        ),
        write=lambda p, v: setattr(
            _sites(p).reward_site.length_distribution.distribution_parameters,
            "value",
            v,
        ),
    ),
    "minimum_interpatch_length": Override(
        tag="ipmin",
        read=lambda p: (
            _sites(p).inter_patch.length_distribution.truncation_parameters.min
        ),
        write=lambda p, v: setattr(
            _sites(p).inter_patch.length_distribution.truncation_parameters, "min", v
        ),
    ),
    "maximum_interpatch_length": Override(
        tag="ipmax",
        read=lambda p: (
            _sites(p).inter_patch.length_distribution.truncation_parameters.max
        ),
        write=lambda p, v: setattr(
            _sites(p).inter_patch.length_distribution.truncation_parameters, "max", v
        ),
    ),
    "minimum_intersite_length": Override(
        tag="ismin",
        read=lambda p: (
            _sites(p).inter_site.length_distribution.truncation_parameters.min
        ),
        write=lambda p, v: setattr(
            _sites(p).inter_site.length_distribution.truncation_parameters, "min", v
        ),
    ),
    "maximum_intersite_length": Override(
        tag="ismax",
        read=lambda p: (
            _sites(p).inter_site.length_distribution.truncation_parameters.max
        ),
        write=lambda p, v: setattr(
            _sites(p).inter_site.length_distribution.truncation_parameters, "max", v
        ),
    ),
}
#: ``velocity_threshold`` lives on operation_control, not per-patch, so it is applied
#: separately but tagged by the same rule.
_VELOCITY_TAG = "vt"


def _base_label(patch: task_logic.Patch) -> str:
    """The patch's curriculum label, with any ``_ch<n>`` suffix stripped."""
    return patch.label.rsplit("_ch", 1)[0]


def applied_overrides(cfg: ReversalConfig) -> dict[str, float]:
    """Overrides whose value actually DIFFERS from what the curriculum provides.

    Comparing against the inherited value (rather than merely checking whether a flag was
    passed) is what keeps the stage name faithful to the task: a redundant override collapses
    to the baseline name, and a real deviation can never share a name with the baseline.
    """
    block = baseline_block(cfg.reward)
    out: dict[str, float] = {}
    for field, ov in OVERRIDES.items():
        value = getattr(cfg, field)
        if value is None:
            continue
        inherited = {ov.read(p) for p in block.environment.patches} - {None}
        if inherited != {value}:
            out[field] = value
    if cfg.velocity_threshold is not None:
        if (
            cfg.velocity_threshold
            != baseline_operation_control(
                cfg.reward
            ).position_control.velocity_threshold
        ):
            out["velocity_threshold"] = cfg.velocity_threshold
    return out


def patch_options(cfg: ReversalConfig, select: SetName) -> task_logic.MarkovEnvironment:
    """The vendored 3-patch environment, repointed at ``select``'s odor channels.

    A reversal changes exactly two things per patch -- ``odor_specification`` and ``label`` --
    plus the occupancy weights. Everything else is inherited from the baseline block.
    """
    block = baseline_block(cfg.reward).model_copy(deep=True)
    mapping = ODOR_LABEL[select]
    overrides = applied_overrides(cfg)
    for patch in block.environment.patches:
        # Labels stay explicit about the odor CHANNEL each contingency sits on, e.g.
        # "patch_delayed_ch1", so a reversal is visible directly as a contingency's channel
        # changing between blocks, and the three labels fully determine the set.
        channel = mapping[BASELINE_PATCHES[patch.label]]
        patch.odor_specification = make_odor_index(channel)
        patch.label = f"{patch.label}_ch{channel}"
        for field, value in overrides.items():
            if field in OVERRIDES:
                OVERRIDES[field].write(patch, value)
    # Weights are keyed to contingency (state_index), not odor channel, so the mix stays
    # attached to null/delayed/single as the channels swap across a reversal.
    occupancy, transition_matrix = occupancy_matrix(cfg.patch_weights())
    block.environment.first_state_occupancy = occupancy
    block.environment.transition_matrix = transition_matrix
    return block.environment


def _scalar(value) -> distributions.Scalar:
    return distributions.Scalar(
        distribution_parameters=distributions.ScalarDistributionParameter(value=value)
    )


def make_end_condition(
    value, count_by: CountBy = "stops", patch_cap: Optional[int] = None
) -> list:
    """Block end condition; ``[]`` means "run to session end".

    ``count_by`` picks the currency the block advances in:

    - ``"patches"`` -- ``BlockEndConditionPatchCount`` counts ``ActivePatch``, i.e. every
      patch ENCOUNTERED whether or not the animal stopped. Advances on a fixed schedule, so
      session structure is predictable, and it guarantees N distinct odor presentations. But
      a skipping animal reaches the reversal barely having sampled: ~59% of patches are run
      past (867424), so a 40-patch block delivers only ~16 visited patches.
    - ``"stops"`` -- ``BlockEndConditionChoice`` counts ``ChoiceFeedback``, i.e. stops. Robust
      to skipping, since patches run past do not advance the block.

    Two caveats on ``"stops"``, both from patches being multi-stop in this depleting task:

    - Stops are NOT distinct odor experiences. ~3 stops land in one patch, so N stops buys
      roughly N/3 odor-contingency samples, and that ratio moves with exploitation depth.
      ``"patches"`` is the more direct guarantee of *distinct* sampling.
    - Perseveration can accelerate the reversal: an animal still exploiting the pre-reversal
      mapping racks up stops quickly, ending the block sooner. Watch for this after a flip.

    Under ``"stops"`` a fully disengaged animal never advances at all. ``patch_cap`` guards
    that: the rig merges end conditions, so whichever fires FIRST ends the block -- it is an
    upper bound in patches, not an additional requirement. It is meaningless under
    ``"patches"`` (the primary condition is already a patch count) and ignored there.
    """
    if isinstance(value, list):
        return value
    if count_by == "patches":
        return [task_logic.BlockEndConditionPatchCount(value=_scalar(value))]
    conditions: list = [task_logic.BlockEndConditionChoice(value=_scalar(value))]
    if patch_cap is not None:
        conditions.append(
            task_logic.BlockEndConditionPatchCount(value=_scalar(patch_cap))
        )
    return conditions


def build_sequence(cfg: ReversalConfig) -> list[tuple[SetName, object]]:
    """Return ``[(set, end_condition_value), ...]`` for the chosen group.

    The final block always gets ``[]`` (runs to session end); earlier blocks end after
    ``block_length`` (in ``count_by`` units), except the first, which honours
    ``first_block_length`` when set. Uses a list (not a dict) so the multiple-reversal
    loop can't be clobbered by duplicate keys.
    """
    seq: list[tuple[SetName, object]]
    if cfg.group == "no_reversal":
        seq = [(cfg.step, [])]
    elif cfg.group == "single_reversal":
        seq = [(cfg.step, cfg.block_length), (cfg.transition, [])]
    elif cfg.group == "multiple_reversal":
        seq = [(s, cfg.block_length) for s in _MULTI_REVERSAL_LOOP]
        seq[-1] = (seq[-1][0], [])
    elif cfg.group == "alternating":
        if cfg.n_reversals < 1:
            raise ValueError("--n-reversals must be >= 1 for group=alternating.")
        partner = partner_set(cfg.step, cfg.swap)
        pair: list[SetName] = [cfg.step, partner]
        seq = [(pair[i % 2], cfg.block_length) for i in range(cfg.n_reversals + 1)]
        seq[-1] = (seq[-1][0], [])
    else:
        raise ValueError(f"Group '{cfg.group}' not recognized.")

    # The first block absorbs warm-up and carry-over from the previous session, so it is
    # sized independently. No-op when the first block is also the last (it is unbounded).
    if cfg.first_block_length is not None and not isinstance(seq[0][1], list):
        seq[0] = (seq[0][0], cfg.first_block_length)
    return seq


_CONTINGENCIES = ("single", "delayed", "noreward")
_CODE = {"single": "S", "delayed": "D", "noreward": "N"}
_ORDER = {"delayed": 0, "single": 1, "noreward": 2}  # D-first, matches the plan


def held_constant(step: SetName, transition: SetName) -> Optional[str]:
    """The single contingency whose channel is unchanged across the reversal, if any."""
    a, b = ODOR_LABEL[step], ODOR_LABEL[transition]
    held = [c for c in _CONTINGENCIES if a[c] == b[c]]
    return held[0] if len(held) == 1 else None


def reversal_type(step: SetName, transition: SetName) -> str:
    """Short code for which two contingencies swap channels between two sets.

    ``"DS"``/``"DN"``/``"SN"`` for a clean single-swap reversal (one contingency held
    constant), ``"none"`` if the sets are identical, else ``"mixed"`` (a 3-cycle).
    """
    a, b = ODOR_LABEL[step], ODOR_LABEL[transition]
    held = [c for c in _CONTINGENCIES if a[c] == b[c]]
    if len(held) == 3:
        return "none"
    if len(held) == 1:
        swapped = sorted(
            (c for c in _CONTINGENCIES if c not in held), key=lambda c: _ORDER[c]
        )
        return "".join(_CODE[c] for c in swapped)
    return "mixed"


def partner_set(step: SetName, swap: SwapKind) -> SetName:
    """The unique set reached from ``step`` by a single ``swap``-type reversal.

    Each single-swap relation is an involution (swapping two contingencies twice restores
    the original), so it partitions the six sets into three disjoint pairs. A sequence
    restricted to one swap type therefore alternates between ``step`` and this partner and
    can never leave that pair — e.g. DS keeps no-reward pinned to one channel throughout.
    """
    matches = [s for s in ODOR_LABEL if reversal_type(step, cast(SetName, s)) == swap]
    if len(matches) != 1:  # pragma: no cover - impossible for the six-permutation set
        raise ValueError(
            f"Expected exactly one {swap} partner for {step}, got {matches}."
        )
    return cast(SetName, matches[0])


def make_task_logic(cfg: ReversalConfig) -> AindVrForagingTaskLogic:
    """Assemble the full ``AindVrForagingTaskLogic`` for ``cfg``."""
    sequence = build_sequence(cfg)
    blocks = [
        task_logic.Block(
            environment=patch_options(cfg, select),
            end_conditions=make_end_condition(
                end_value, count_by=cfg.count_by, patch_cap=cfg.patch_cap
            ),
        )
        for select, end_value in sequence
    ]
    if cfg.group == "no_reversal":
        stage_name = f"deterministic_{cfg.step}_{cfg.reward}"
    elif cfg.group == "single_reversal":
        # e.g. deterministic_set1_DS_reversal_set6_capped — set kept for bookkeeping,
        # the DS/DN/SN code names the reversal by which contingencies swap.
        rt = reversal_type(cfg.step, cfg.transition)
        stage_name = (
            f"deterministic_{cfg.step}_{rt}_reversal_{cfg.transition}_{cfg.reward}"
        )
    elif cfg.group == "alternating":
        # e.g. deterministic_set1_DS_x5_capped — step and swap fully determine the pair.
        stage_name = (
            f"deterministic_{cfg.step}_{cfg.swap}_x{cfg.n_reversals}_{cfg.reward}"
        )
    else:  # multiple_reversal
        stage_name = f"deterministic_{cfg.step}_multi_reversal_{cfg.reward}"

    # Block lengths enter the name only when they deviate from the defaults, so existing
    # stage names are unchanged; without this a sweep over block length would write every
    # variant to the same file. The tag also carries the UNIT (_sb stops / _pb patches) --
    # a non-default count_by is always tagged, so a 40-stop and a 40-patch session cannot
    # collide on one filename.
    first_end = sequence[0][1]
    unit_tag = "sb" if cfg.count_by == "stops" else "pb"
    if len(sequence) > 1 and (
        cfg.block_length != _DEFAULT_BLOCK_LENGTH or cfg.count_by != _DEFAULT_COUNT_BY
    ):
        stage_name += f"_{unit_tag}{cfg.block_length}"
    if not isinstance(first_end, list) and first_end != cfg.block_length:
        stage_name += f"_fb{first_end}"
    # The cap changes what the rig does, so it has to be in the name too -- otherwise a
    # capped and an uncapped stop-gated session write to the same file.
    if cfg.patch_cap is not None and cfg.count_by == "stops" and len(sequence) > 1:
        stage_name += f"_cap{cfg.patch_cap}"
    weights = cfg.patch_weights()
    if len(set(weights)) > 1:
        stage_name += f"_wN{weights[0]:g}-D{weights[1]:g}-S{weights[2]:g}"
    # Any deviation from the vendored curriculum is stamped here, so a modified task can never
    # share a stage name -- or a trainer_state -- with the baseline it was derived from. Sorted
    # for a deterministic name regardless of flag order.
    overrides = applied_overrides(cfg)
    for field, value in sorted(overrides.items()):
        tag = _VELOCITY_TAG if field == "velocity_threshold" else OVERRIDES[field].tag
        stage_name += f"_{tag}{value:g}"

    operation_control = baseline_operation_control(cfg.reward)
    if "velocity_threshold" in overrides:
        operation_control.position_control.velocity_threshold = overrides[
            "velocity_threshold"
        ]

    return AindVrForagingTaskLogic(
        stage_name=stage_name,
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=None,
            environment=task_logic.BlockStructure(
                blocks=blocks, sampling_mode="Sequential"
            ),
            operation_control=operation_control,
        ),
    )


def _describe(cfg: ReversalConfig) -> None:
    """Print provenance, any overrides, and the block sequence with each set's channel map."""
    # These states are off-curriculum (curriculum=None), so nothing in the trainer state
    # records what the task was derived from. Print it: once the generator tracks the
    # curriculum, a curriculum bump silently changes the output unless it is visible here.
    print(f"  inherits: {_BASELINE_CURRICULUM[cfg.reward]} v{__semver__} (graduation)")
    overrides = applied_overrides(cfg)
    if overrides:
        block = baseline_block(cfg.reward)
        for field, value in sorted(overrides.items()):
            if field == "velocity_threshold":
                was = baseline_operation_control(
                    cfg.reward
                ).position_control.velocity_threshold
            else:
                was = next(
                    v
                    for v in (
                        OVERRIDES[field].read(p) for p in block.environment.patches
                    )
                    if v is not None
                )
            print(
                f"  OVERRIDE {field}: {was:g} -> {value:g}  (curriculum value not used)"
            )
    else:
        print("  overrides: none (task matches the curriculum exactly)")
    occupancy, _ = occupancy_matrix(cfg.patch_weights())
    print(
        f"  patch mix: null={occupancy[0]:.0%}, delayed={occupancy[1]:.0%}, "
        f"single={occupancy[2]:.0%}"
    )
    for i, (select, end_value) in enumerate(build_sequence(cfg)):
        m = ODOR_LABEL[select]
        end = (
            "to session end"
            if isinstance(end_value, list)
            else f"{end_value} {cfg.count_by}"
        )
        print(
            f"  block {i}: {select} ({end}) — "
            f"single=ch{m['single']}, delayed=ch{m['delayed']}, null=ch{m['noreward']}"
        )
    if cfg.group == "single_reversal":
        rt = reversal_type(cfg.step, cfg.transition)
        held = held_constant(cfg.step, cfg.transition)
        held_str = (
            f"held constant: {held} on ch{ODOR_LABEL[cfg.step][held]}"
            if held
            else "no single odor held constant (3-cycle)"
        )
        print(f"  reversal: {rt}  ({held_str})")
    if cfg.group == "alternating":
        partner = partner_set(cfg.step, cfg.swap)
        held = held_constant(cfg.step, partner)
        assert held is not None  # a single-swap partner always holds one contingency
        print(
            f"  reversal: {cfg.swap} × {cfg.n_reversals}, alternating "
            f"{cfg.step} <-> {partner}  "
            f"(held constant: {held} on ch{ODOR_LABEL[cfg.step][held]})"
        )


def _read_source_text(source: str) -> str:
    """Read a file's text from an ``s3://`` URI (via ``s5cmd``, unsigned) or a local/NAS path."""
    if source.startswith("s3://"):
        result = subprocess.run(
            ["s5cmd", "--no-sign-request", "cat", source],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    return Path(source).read_text(encoding="utf-8")


def _resolve_tasklogic(session: str) -> str:
    """Resolve a session reference to its ``tasklogic_input.json``.

    ``session`` may already be the JSON, or a session root (``behavior/Logs/…`` is
    appended). Works for both ``s3://`` URIs and local/NAS paths.
    """
    if session.endswith(".json"):
        return session
    if session.startswith("s3://"):
        return session.rstrip("/") + "/behavior/Logs/tasklogic_input.json"
    root = Path(session)
    for sub in (
        "behavior/Logs/tasklogic_input.json",
        "Behavior/Logs/tasklogic_input.json",
        "tasklogic_input.json",
    ):
        if (root / sub).exists():
            return str(root / sub)
    raise FileNotFoundError(f"Could not find tasklogic_input.json under {session!r}")


def _latest_session_uri(subject_id: str, bucket: str) -> str:
    """Most recent *uploaded* session for a mouse on S3 (folder names sort chronologically)."""
    result = subprocess.run(
        ["s5cmd", "--no-sign-request", "ls", f"s3://{bucket}/{subject_id}_"],
        capture_output=True,
        text=True,
        check=True,
    )
    folders = re.findall(rf"({re.escape(subject_id)}_\S+?)/", result.stdout)
    if not folders:
        raise ValueError(f"No sessions found for {subject_id} in s3://{bucket}/")
    return f"s3://{bucket}/{sorted(set(folders))[-1]}"


def infer_baseline_set(session: str) -> str:
    """Infer the current baseline set from a session's LAST block channel mapping.

    Reads the session's ``tasklogic_input.json`` (S3 or local), reads the final block's
    per-contingency odor channel, and reverse-maps it to a set name. The last block is
    "where the mouse currently is" (the transition set of a reversal, or the sole block).
    """
    task_logic_json = json.loads(_read_source_text(_resolve_tasklogic(session)))
    patches = task_logic_json["task_parameters"]["environment"]["blocks"][-1][
        "environment"
    ]["patches"]
    channel: dict[str, int] = {}
    for patch in patches:
        label = patch.get("label", "")
        odor = patch.get("odor_specification")
        ch = odor.index(1.0) if isinstance(odor, list) and 1.0 in odor else None
        if ch is None:
            continue
        for prefix, key in (
            ("patch_single", "single"),
            ("patch_delayed", "delayed"),
            ("patch_null", "noreward"),
        ):
            if label.startswith(prefix):
                channel[key] = ch
    triple = (channel.get("single"), channel.get("delayed"), channel.get("noreward"))
    set_name = _SET_BY_MAPPING.get(triple)  # type: ignore[arg-type]
    if set_name is None:
        raise ValueError(
            f"Last-block mapping single={triple[0]}, delayed={triple[1]}, null={triple[2]} "
            "matches no known set — pass --step explicitly."
        )
    return set_name


def main(cfg: ReversalConfig) -> None:
    """Generate the task logic + trainer state for ``cfg`` and write the JSON."""
    # Resolve the current baseline set from an existing session, if requested.
    if cfg.from_session or cfg.from_mouse:
        if cfg.from_session:
            source = cfg.from_session
        else:
            assert cfg.from_mouse is not None  # guaranteed by the enclosing condition
            source = _latest_session_uri(cfg.from_mouse, cfg.bucket)
            print(f"latest uploaded session for {cfg.from_mouse}: {source}")
        inferred = infer_baseline_set(source)
        print(f"inferred current baseline set: {inferred}  (--step was {cfg.step})")
        cfg.step = inferred  # type: ignore[assignment]

    task_logic_instance = make_task_logic(cfg)
    trainer_state = TrainerState(
        stage=Stage(name=task_logic_instance.stage_name, task=task_logic_instance),
        curriculum=None,
        is_on_curriculum=False,
    )
    print(f"stage_name: {task_logic_instance.stage_name}")
    _describe(cfg)

    out_path = cfg.output.format(stage_name=task_logic_instance.stage_name)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(trainer_state.model_dump_json(indent=3))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main(tyro.cli(ReversalConfig, description=__doc__))
