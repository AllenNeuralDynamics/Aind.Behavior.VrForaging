"""Deterministic S/D/N reversal task-logic generator (tyro CLI).

Builds an ``AindVrForagingTaskLogic`` for the batch-8 deterministic-reversal paradigm and
writes a standalone ``TrainerState`` JSON for deployment via the launcher (not the
curriculum system).

**The task comes from the curriculum, not from this file.** Each block is a vendored stage --
``reversal_baseline`` (``--baseline reversal``, the default and what this cohort runs) or
``graduation`` (``--baseline graduation``), from ``deterministic_reversals`` (``--reward full``)
or ``deterministic_reversals_reward_capped`` (``--reward capped``) -- deep-copied and repointed
at a different odor permutation. Corridor geometry, stop duration, reward delay, reward curves
and operation control are all inherited, so a curriculum edit propagates here automatically and
the two cannot drift apart. See :func:`baseline_block`.

This matters because they did drift. An earlier version redeclared the whole task alongside the
curriculum, and the copies diverged: corridor 150-400 vs 100-250 cm, stop duration 1.0 vs 0.5 s,
an exponential reward delay replaced by a normal one. Those three values were *deliberate* --
they are the task the reversal cohort is meant to run -- but they lived only in a hand-copied
generator, under stage names that did not distinguish them from the curriculum's own. So they
could not be reviewed, versioned, or told apart in analysis, and "fixing the drift" by inheriting
graduation silently changed the task for three mice. They now live in the curriculum as
``reversal_baseline``, and the baseline is stamped into every stage name.

``tests/test_task_reversal.py`` pins ``no_reversal --step set1`` to be exactly the vendored stage
for BOTH baselines, since set1 *is* their shared permutation.

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
barely having sampled):
    uv run python examples/task_reversal.py --group single_reversal --count-by patches --block-length 40

Jitter the block length so the reversal is not on a schedule the animal can learn. The
number given stays the MEAN, so the session budget is unchanged; --block-jitter is the mean
of the exponential spread around it:
    uv run python examples/task_reversal.py --group alternating --swap DS --step set1 --n-reversals 5 --block-length 85 --block-jitter 12

Infer the current set from a mouse's last uploaded session, then just pick the reversal:
    uv run python examples/task_reversal.py --from-mouse 867424 --group single_reversal --transition set6 --reward capped --block-length 20

Infer from the freshest session still staged on the NAS (not yet uploaded to S3):
    uv run python examples/task_reversal.py --from-session /path/to/nas/867424_2026-07-13_20-27-51 --group single_reversal --transition set6 --reward capped

Deviate from the curriculum on purpose (tagged _sd1 _ipmin150 _ipmax400 in the stage name):
    uv run python examples/task_reversal.py --group no_reversal --step set1 --stop-duration 1.0 --minimum-interpatch-length 150 --maximum-interpatch-length 400
"""

from __future__ import annotations

import bisect
import json
import math
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, Optional, cast

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
Baseline = Literal["reversal", "graduation"]
Group = Literal["no_reversal", "single_reversal", "multiple_reversal", "alternating"]
PatchType = Literal["single", "delayed", "no_reward"]
SwapKind = Literal["DS", "DN", "SN"]
CountBy = Literal["stops", "patches"]
_DEFAULT_COUNT_BY: CountBy = "stops"

#: The vendored stage each (baseline, reward) pair inherits from. Everything physical --
#: geometry, timings, reward curves, operation control -- comes from here, so a curriculum edit
#: propagates and cannot silently diverge. See :func:`baseline_block`.
#:
#: ``reversal`` is the task this cohort actually runs: graduation adjusted for a longer corridor,
#: a doubled stop requirement and a predictable normal delay. Those three differences are
#: deliberate, and they live in the curriculum rather than in flags precisely so they cannot be
#: half-applied. ``graduation`` selects the plain on-curriculum stage.
_BASELINE_STAGE = {
    ("reversal", "capped"): _stages_capped.make_s_stage_reversal_baseline,
    ("reversal", "full"): _stages_full.make_s_stage_reversal_baseline,
    ("graduation", "capped"): _stages_capped.make_s_stage_graduation,
    ("graduation", "full"): _stages_full.make_s_stage_graduation,
}
_BASELINE_CURRICULUM = {
    "capped": "DeterministicReversalsRewardCapped",
    "full": "DeterministicReversals",
}
#: Stage-name tag per baseline. Always emitted: the bare name has already meant two different
#: tasks (batch-8 geometry before 2026-08-11, curriculum geometry on it), and merging two tasks
#: under one name is the failure this generator exists to prevent.
_BASELINE_TAG = {"reversal": "blrev", "graduation": "blgrad"}
#: Stage each baseline resolves to, for the provenance line.
_BASELINE_STAGE_NAME = {"reversal": "reversal_baseline", "graduation": "graduation"}
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

# Contingency of each patch ``state_index``, as both the task logic and the rig's
# ``ActivePatch`` stream encode it.
_CONTINGENCY: dict[int, str] = {0: "noreward", 1: "delayed", 2: "single"}

# Visit rate below which an executed block holds too little behaviour to have taught the
# animal its mapping: the mouse quit inside it rather than ran it.
_ENGAGED_VISIT_RATE = 0.3

# Fixed loop order for the multiple-reversal group (single-swap reversals, S-D-N).
_MULTI_REVERSAL_LOOP: list[SetName] = ["set1", "set6", "set2", "set5", "set3", "set4"]

# Default steady-state block length; deviations are tagged into the stage name.
_DEFAULT_BLOCK_LENGTH = 40

# Width of a jittered block's window, in units of the jitter mean. At 3 the exponential keeps
# 95% of its mass inside the window, so the shape is still recognisably exponential, while the
# block keeps a hard ceiling a session budget can be planned against.
_JITTER_SPAN = 3.0
# Mean of a unit exponential truncated to [0, _JITTER_SPAN], in units of its own mean.
# Truncation pulls the mean below 1; the floor is lowered by exactly this much so that turning
# jitter on does not lengthen the block.
_JITTER_MEAN = 1.0 - _JITTER_SPAN * math.exp(-_JITTER_SPAN) / (
    1.0 - math.exp(-_JITTER_SPAN)
)


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

    baseline: Baseline = "reversal"
    """Which vendored stage to inherit the task from. ``reversal`` = ``reversal_baseline``, the
    task this cohort runs (150-400 cm inter-patch, 1.0 s stop, Normal(0.5, 0.15) reward delay);
    ``graduation`` = the plain on-curriculum stage (100-250, 0.5 s, Exponential). Both are
    defined in the curriculum, so neither can drift from what is deployed. Always tagged into
    the stage name."""
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
    ``block_length``. The first block is the pre-reversal baseline -- the A of an ABA -- and
    it opens on the mapping the animal ended the previous session on, so it starts
    part-settled and wants to be SHORTER than a block that follows a reversal: about its own
    settling time plus one analysis window. Ignored when the first block is also the last
    (no_reversal), since that one is unbounded.

    Note this sizes DECLARED block 1, not "the opener": a closed cycle comes back round to it,
    and every later visit is a reversal needing a full-length block. Give the cycle enough
    blocks that the short one lands once per session, or leave this unset and size every block
    alike."""
    block_jitter: float = 0.0
    """Mean of an exponential spread applied to every bounded block's length, in ``count_by``
    units. 0 gives every block exactly its declared length.

    A fixed block length is itself learnable: the reversal always lands on the same stop, so an
    animal that has learned the schedule can switch before the odors change rather than because
    they did. An exponential has a flat hazard -- how much of a block has already elapsed says
    nothing about how much is left -- so there is no schedule to learn.

    ``block_length`` and ``first_block_length`` keep meaning the MEAN realized length rather
    than becoming floors, so turning jitter on rejitters the schedule without spending more of
    a session. These lengths are budget-tuned per animal; silently lengthening them is the one
    thing this flag must not do. See :func:`block_length_distribution`."""
    count_by: CountBy = _DEFAULT_COUNT_BY
    """Currency the block advances in: "stops" (``ChoiceFeedback``) or "patches"
    (``ActivePatch``, i.e. every patch encountered, stopped at or not). "patches" is the
    original behaviour -- predictable structure and N guaranteed odor presentations; "stops"
    is robust to an animal that skips its way to the reversal. See ``make_end_condition``
    for the trade-off. The choice is tagged into the stage name (``_pb``/``_sb``)."""
    wrap: Optional[bool] = None
    """Bound the FINAL block too, so the rig cycles the block list instead of parking in an
    unbounded last block. Defaults to closing the cycle for any design that cycles.

    The task engine repeats the block list once it is exhausted. Leaving the last block
    unbounded suppresses that: the session ends inside one giant terminal block that runs
    well past the engagement cliff and is not analyzable. A closed cycle keeps every block
    the same size, so blocks past the cliff degrade gracefully instead of swallowing most of
    the session, and the analysis target can simply be a prefix of the cycle -- an ABA is the
    first three blocks of a repeating A,B.

    ``None`` resolves per group: closed for ``alternating`` and ``multiple_reversal``, open
    for ``single_reversal``, whose whole point is a one-way transition into a state the mouse
    then holds, within the session and across the sessions that follow. Asking for ``--wrap``
    there is refused rather than ignored."""
    patch_cap: Optional[int] = None
    """Optional upper bound in PATCHES on every non-terminal block, merged with the stop
    condition so that whichever fires first ends the block.

    Leave it unset. It exists for a design that deliberately wants a patch ceiling, not as a
    remedy for an animal that stops working: it can only bind once the visit rate has
    collapsed, so it hands a reversal to a mouse that is not sampling — the exact failure
    ``count_by="stops"`` was adopted to prevent. See :func:`make_end_condition`. Only
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

    def resolved_wrap(self) -> bool:
        """Whether the block list closes into a cycle, resolving the ``None`` default.

        Closed by default wherever the design cycles. ``single_reversal`` never does: it is a
        one-way transition into a state the animal then holds, through the rest of the
        session and into the ones after it, which is how it learns to reverse at all. Asking
        for a cycle there is refused rather than quietly ignored.
        """
        cycles = self.group in ("alternating", "multiple_reversal")
        if self.wrap is None:
            return cycles
        if self.wrap and self.group == "single_reversal":
            raise ValueError(
                "--wrap does not apply to --group single_reversal: it reverses into a state "
                "the animal holds across sessions, rather than cycling. Use --group "
                "alternating for a closed cycle."
            )
        return self.wrap

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


def baseline_block(
    reward: RewardMode, baseline: Baseline = "reversal"
) -> task_logic.Block:
    """The vendored block for ``(baseline, reward)`` -- the single source of task truth.

    Everything physical lives here: corridor geometry, stop duration, reward delay, reward
    curves, patch terminators. This generator only ever permutes odors, slices blocks, and
    applies the explicit overrides in :data:`OVERRIDES` on top. Nothing about the task is
    redeclared locally, so a curriculum edit propagates and the two cannot drift apart.

    Both baselines are set1 (null=ch0, delayed=ch1, single=ch2), so a ``no_reversal`` set1
    state is byte-identical to the vendored stage apart from the ``_ch<n>`` label suffix.
    ``tests/test_task_reversal.py`` pins exactly that, for every baseline.
    """
    stage = _BASELINE_STAGE[(baseline, reward)]()
    blocks = stage.task.task_parameters.environment.blocks
    if len(blocks) != 1:
        raise ValueError(
            f"Vendored {stage.name!r} for reward={reward!r} has {len(blocks)} blocks, expected 1. "
            "The curriculum changed shape; this generator needs updating."
        )
    labels = {p.label for p in blocks[0].environment.patches}
    if labels != set(BASELINE_PATCHES):
        raise ValueError(
            f"Vendored {stage.name!r} for reward={reward!r} has patches {sorted(labels)}, expected "
            f"{sorted(BASELINE_PATCHES)}. The curriculum changed shape; update BASELINE_PATCHES."
        )
    return blocks[0]


def baseline_operation_control(reward: RewardMode, baseline: Baseline = "reversal"):
    """The vendored stage's operation control (velocity threshold and friends)."""
    return _BASELINE_STAGE[(baseline, reward)]().task.task_parameters.operation_control


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


def _delay_parameters(patch: task_logic.Patch):
    """The delay distribution's parameter block, whatever its family."""
    return patch.reward_specification.delay.distribution_parameters


def _read_delay_mean(patch: task_logic.Patch) -> float:
    """Mean delay in seconds, read out of either an exponential rate or a normal mean."""
    params = _delay_parameters(patch)
    rate = getattr(params, "rate", None)
    return 1.0 / rate if rate is not None else params.mean


def _write_delay_mean(patch: task_logic.Patch, value: float) -> None:
    """Set the mean delay without touching the distribution family."""
    params = _delay_parameters(patch)
    if getattr(params, "rate", None) is not None:
        params.rate = 1.0 / value
    else:
        params.mean = value


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
    # Retunes the MEAN of whichever delay family the baseline supplies -- Exponential(rate=1/mean)
    # for graduation, Normal(mean, std) for reversal_baseline. It does NOT switch family: which
    # family the delay has decides whether the animal can time its wait, and swapping one for the
    # other silently is exactly what put the batch-8 cohort on a task the curriculum did not
    # describe. Pick the family by choosing a baseline; pick the mean with this flag.
    "delay_mean": Override(
        tag="dm",
        read=_read_delay_mean,
        write=_write_delay_mean,
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
    block = baseline_block(cfg.reward, cfg.baseline)
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
    block = baseline_block(cfg.reward, cfg.baseline).model_copy(deep=True)
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


def block_length_distribution(mean: float, jitter: float):
    """A block's length: fixed at ``mean``, or exponentially spread around it.

    ``jitter`` is the exponential's own mean, not the width of the window. The floor sits
    *below* ``mean`` by exactly the amount truncation shifts an exponential's mean, so the
    realized mean is ``mean`` whether jitter is on or off — see
    :attr:`ReversalConfig.block_jitter` for why that has to hold.

    Truncation to ``[floor, floor + _JITTER_SPAN * jitter]`` uses the schema default mode,
    ``exclude``: an out-of-range draw is resampled rather than clamped, so no block sits
    exactly on the ceiling and the hazard stays flat right up to it.
    """
    if jitter < 0:
        raise ValueError(f"--block-jitter must be >= 0, got {jitter:g}.")
    if jitter == 0:
        return _scalar(mean)
    floor = round(mean - jitter * _JITTER_MEAN)
    if floor < 1:
        raise ValueError(
            f"--block-jitter {jitter:g} is too wide for a block of {mean:g}: it puts the floor "
            f"at {floor}. Keep the jitter under {mean / _JITTER_MEAN:.0f}."
        )
    return distributions.ExponentialDistribution(
        distribution_parameters=distributions.ExponentialDistributionParameters(
            rate=1 / jitter
        ),
        scaling_parameters=distributions.ScalingParameters(offset=floor),
        truncation_parameters=distributions.TruncationParameters(
            min=floor, max=floor + round(_JITTER_SPAN * jitter)
        ),
    )


def make_end_condition(
    value,
    count_by: CountBy = "stops",
    patch_cap: Optional[int] = None,
    jitter: float = 0.0,
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

    Under ``"stops"`` a block does not advance while the animal is skipping. That is the
    point, not a defect: a reversal delivered to a mouse that is not sampling is one it cannot
    learn, and the block it lands in was never taught either.

    ``patch_cap`` overrides that -- the rig merges end conditions, so whichever fires FIRST
    ends the block, making it an upper bound in patches rather than an additional requirement.
    Prefer to leave it unset. It binds precisely when the visit rate has collapsed, so every
    reversal it triggers goes to an animal that cannot use it, which is the failure counting
    stops exists to avoid; and it buys nothing analysis cannot get after the fact by finding
    the engagement cliff. A long dead block at the end of a session costs neither water nor
    welfare, and it is excluded cleanly. Meaningless under ``"patches"`` (the primary condition
    is already a patch count) and ignored there.

    ``jitter`` spreads the length exponentially about ``value`` instead of fixing it; see
    :func:`block_length_distribution`. It applies to the primary condition only — the cap is a
    ceiling on a disengaged animal, not a target, so it stays fixed.
    """
    if isinstance(value, list):
        return value
    length = block_length_distribution(value, jitter)
    if count_by == "patches":
        return [task_logic.BlockEndConditionPatchCount(value=length)]
    conditions: list = [task_logic.BlockEndConditionChoice(value=length)]
    if patch_cap is not None:
        conditions.append(
            task_logic.BlockEndConditionPatchCount(value=_scalar(patch_cap))
        )
    return conditions


def build_sequence(cfg: ReversalConfig) -> list[tuple[SetName, object]]:
    """Return ``[(set, end_condition_value), ...]`` for the chosen group.

    The final block gets ``[]`` (runs to session end) unless ``--wrap``, which bounds it
    like the rest so the rig cycles back to block 0. Earlier blocks end after
    ``block_length`` (in ``count_by`` units), except the first, which honours
    ``first_block_length`` when set. Uses a list (not a dict) so the multiple-reversal
    loop can't be clobbered by duplicate keys.
    """
    wrap = cfg.resolved_wrap()
    seq: list[tuple[SetName, object]]
    if cfg.group == "no_reversal":
        seq = [(cfg.step, cfg.block_length if wrap else [])]
    elif cfg.group == "single_reversal":
        seq = [(cfg.step, cfg.block_length), (cfg.transition, [])]
    elif cfg.group == "multiple_reversal":
        seq = [(s, cfg.block_length) for s in _MULTI_REVERSAL_LOOP]
        if not wrap:
            seq[-1] = (seq[-1][0], [])
    elif cfg.group == "alternating":
        if cfg.n_reversals < 1:
            raise ValueError("--n-reversals must be >= 1 for group=alternating.")
        partner = partner_set(cfg.step, cfg.swap)
        pair: list[SetName] = [cfg.step, partner]
        # A closed alternation needs an even declaration, else the seam puts the same set on
        # both sides -- a scheduled reversal that silently is not one. Round up rather than
        # refuse: how many reversals the animal actually sees is set by how long it works,
        # not by the length of the list the rig cycles.
        n_blocks = cfg.n_reversals + 1
        if wrap and n_blocks % 2:
            n_blocks += 1
        seq = [(pair[i % 2], cfg.block_length) for i in range(n_blocks)]
        if not wrap:
            seq[-1] = (seq[-1][0], [])
    else:
        raise ValueError(f"Group '{cfg.group}' not recognized.")

    # The first block absorbs warm-up and carry-over from the previous session, so it is
    # sized independently. No-op when the first block is also the last (it is unbounded).
    if cfg.first_block_length is not None and not isinstance(seq[0][1], list):
        seq[0] = (seq[0][0], cfg.first_block_length)

    # Backstop: a closed list repeats block 0 straight after block N, so that seam is a
    # reversal like any other and has to obey the alternation. `alternating` rounds up to
    # reach this; a hand-built loop can still trip it.
    if wrap and len(seq) > 1 and seq[0][0] == seq[-1][0]:
        raise ValueError(
            f"a closed cycle needs the map to alternate across the seam; got {len(seq)} "
            f"blocks both starting and ending on {seq[0][0]}."
        )
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
                end_value,
                count_by=cfg.count_by,
                patch_cap=cfg.patch_cap,
                jitter=cfg.block_jitter,
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

    # Which vendored stage the task came from. Always present, unlike the override tags: the
    # bare name has already denoted two different tasks, and a name that silently covers both
    # is exactly what lets analysis pool sessions that should never be pooled.
    stage_name += f"_{_BASELINE_TAG[cfg.baseline]}"

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
    # Two sessions with the same mean block length are not the same task if one of them is
    # predictable, so jitter is tagged whenever any block is actually bounded by it. Read off
    # the sequence rather than the flag: on an unbounded single block there is nothing to
    # jitter, and a tag there would claim a difference the rig never saw.
    if cfg.block_jitter and any(not isinstance(end, list) for _, end in sequence):
        stage_name += f"_jit{cfg.block_jitter:g}"
    # The cap changes what the rig does, so it has to be in the name too -- otherwise a
    # capped and an uncapped stop-gated session write to the same file.
    if cfg.patch_cap is not None and cfg.count_by == "stops" and len(sequence) > 1:
        stage_name += f"_cap{cfg.patch_cap}"
    # Read off the built sequence, not the flag: a design that cannot cycle would otherwise
    # be labelled wrapped while its last block still runs to session end, and the label is
    # what analysis groups sessions by.
    if len(sequence) > 1 and not any(isinstance(end, list) for _, end in sequence):
        stage_name += "_wrap"
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

    operation_control = baseline_operation_control(cfg.reward, cfg.baseline)
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
    print(
        f"  inherits: {_BASELINE_CURRICULUM[cfg.reward]} v{__semver__} "
        f"({_BASELINE_STAGE_NAME[cfg.baseline]})"
    )
    overrides = applied_overrides(cfg)
    if overrides:
        block = baseline_block(cfg.reward, cfg.baseline)
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
        if isinstance(end_value, list):
            end = "to session end"
        elif cfg.block_jitter:
            # Read the bounds back off the built distribution so the printed range cannot
            # drift from the one the rig is handed.
            bounds = block_length_distribution(
                end_value, cfg.block_jitter
            ).truncation_parameters
            end = f"{bounds.min:g}-{bounds.max:g} {cfg.count_by}, mean {end_value:g}"
        else:
            end = f"{end_value} {cfg.count_by}"
        print(
            f"  block {i + 1}: {select} ({end}) — "
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


def _resolve_stream(session: str, stream: str) -> str:
    """Resolve a session reference to one of its software-event streams.

    Mirrors :func:`_resolve_tasklogic`; raises for a reference that names the task logic
    directly, since a bare JSON carries no record of what was executed.
    """
    if session.endswith(".json"):
        raise FileNotFoundError(f"{session!r} is a task logic, not a session tree")
    if session.startswith("s3://"):
        return session.rstrip("/") + f"/behavior/SoftwareEvents/{stream}.json"
    root = Path(session)
    for sub in ("behavior", "Behavior"):
        candidate = root / sub / "SoftwareEvents" / f"{stream}.json"
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"No {stream} stream under {session!r}")


def _read_stream(session: str, stream: str) -> list[dict[str, Any]]:
    """Parse one software-event stream (JSON lines); empty if the session did not emit it."""
    try:
        text = _read_source_text(_resolve_stream(session, stream))
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _frame_time(event: dict[str, Any]) -> float:
    """Behaviour-clock timestamp of a software event."""
    return float(event["frame_timestamp"])


def _channel_map(patches: list[dict[str, Any]]) -> dict[str, int]:
    """Map ``contingency -> odour channel`` from one-hot patch definitions.

    Keyed on ``state_index``, which is pinned to contingency and never moves; the channel is
    exactly what a reversal swaps. Labels encode the same thing but are free text.
    """
    out: dict[str, int] = {}
    for patch in patches:
        spec = patch.get("odor_specification")
        if isinstance(spec, list) and spec:
            out[_CONTINGENCY[int(patch["state_index"])]] = spec.index(max(spec))
    return out


def _executed_channel_map(session: str) -> dict[str, int] | None:
    """Channel map of the last block the mouse actually engaged with, from the rig's log.

    Blocks it entered but abandoned are skipped: a block run at a collapsed visit rate
    taught the animal nothing, so it cannot be the state to stay continuous with.

    Returns ``None`` when the session logged no patches, leaving the caller to fall back.
    """
    patches = sorted(_read_stream(session, "ActivePatch"), key=_frame_time)
    if not patches:
        return None
    onsets = sorted(_frame_time(e) for e in _read_stream(session, "Block"))
    stops = sorted(_frame_time(e) for e in _read_stream(session, "ChoiceFeedback"))
    edges = [_frame_time(e) for e in patches] + [float("inf")]

    blocks: dict[int, list[tuple[dict[str, Any], bool]]] = {}
    for i, event in enumerate(patches):
        lo, hi = edges[i], edges[i + 1]
        index = max(bisect.bisect_right(onsets, lo) - 1, 0)
        visited = bisect.bisect_left(stops, hi) > bisect.bisect_left(stops, lo)
        blocks.setdefault(index, []).append((event["data"], visited))

    for index in sorted(blocks, reverse=True):
        entries = blocks[index]
        rewarded = [
            visited for data, visited in entries if int(data["state_index"]) in (1, 2)
        ]
        if rewarded and sum(rewarded) / len(rewarded) >= _ENGAGED_VISIT_RATE:
            return _channel_map([data for data, _ in entries])
    return None


def _declared_channel_map(session: str) -> dict[str, int]:
    """Channel map of a session's final *declared* block, from its ``tasklogic_input.json``."""
    task_logic_json = json.loads(_read_source_text(_resolve_tasklogic(session)))
    return _channel_map(
        task_logic_json["task_parameters"]["environment"]["blocks"][-1]["environment"][
            "patches"
        ]
    )


def infer_baseline_set(session: str) -> tuple[str, str]:
    """Infer the set a mouse *ended* a session in, so the next one can open continuously.

    Reads the last block the animal actually engaged with, from the rig's ``ActivePatch``
    log. The declared block list cannot answer this once blocks are bounded at both ends
    (``--wrap``): the rig then cycles that list and the session stops wherever the animal
    quits, mid-list, so the final declared block is usually not the one it ran. Trusting the
    declaration reports a set the mouse never reached and opens the next session on an
    uncued reversal — the exact failure this inference exists to prevent.

    Falls back to the final declared block when nothing was logged (a bare
    ``tasklogic_input.json``, or a session that emitted no patches).

    Returns
    -------
    tuple of (str, str)
        The set name and how it was read, for the caller to report.
    """
    channel = _executed_channel_map(session)
    source = "last engaged block"
    if channel is None:
        channel, source = (
            _declared_channel_map(session),
            "declared last block (nothing logged)",
        )
    triple = (channel.get("single"), channel.get("delayed"), channel.get("noreward"))
    set_name = _SET_BY_MAPPING.get(triple)  # type: ignore[arg-type]
    if set_name is None:
        raise ValueError(
            f"{source.capitalize()} mapping single={triple[0]}, delayed={triple[1]}, "
            f"null={triple[2]} matches no known set — pass --step explicitly."
        )
    return set_name, source


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
        inferred, read_from = infer_baseline_set(source)
        print(
            f"inferred current baseline set: {inferred} from the {read_from}  (--step was {cfg.step})"
        )
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
