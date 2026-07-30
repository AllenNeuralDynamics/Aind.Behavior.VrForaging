"""Deterministic S/D/N reversal task-logic generator (tyro CLI).

Builds an ``AindVrForagingTaskLogic`` for the batch-8 deterministic-reversal paradigm and
writes a standalone ``TrainerState`` JSON for deployment via the launcher (not the
curriculum system).

Each block has three patch types:

- ``single``   – one guaranteed reward on the first stop, then depleted.
- ``delayed``  – depleting/accumulating reward across stops (``reward`` mode picks the
  schedule; see :class:`ReversalConfig`).
- ``no_reward``– never rewarded.

The odor↔contingency assignment is chosen by a **set** permutation over the three
olfactometer **channel indices** (0/1/2); a *reversal* swaps the set between blocks. The
physical odorant on each channel lives in the **rig config** (``rig_input.json`` /
instrument metadata), NOT here — this file only says "the odor on channel k".

Examples:

Reproduce the current graduation config (set1, capped, no reversal):
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
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, cast

import numpy as np
import tyro
from aind_behavior_curriculum import Stage, TrainerState
from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)
from aind_behavior_vr_foraging_curricula.depletion import helpers

SetName = Literal["set1", "set2", "set3", "set4", "set5", "set6"]
RewardMode = Literal["full", "capped", "reduced"]
Group = Literal["no_reversal", "single_reversal", "multiple_reversal", "alternating"]
PatchType = Literal["single", "delayed", "no_reward"]
SwapKind = Literal["DS", "DN", "SN"]
CountBy = Literal["stops", "patches"]
_DEFAULT_COUNT_BY: CountBy = "stops"

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
    """Delayed-patch payout: full/capped ≈ 3 drops (capped also hard-caps total volume at
    amount×3 and guarantees the first stop); reduced ≈ 2 drops."""
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

    stop_duration: float = 1.0
    delay_mean: float = 0.5
    reward_amount: float = 5.0
    velocity_threshold: float = 8.0

    weight_null: float = 1.0
    """Relative frequency of the no-reward patch. Under a DS-only reversal the null odor
    never changes channel, so it carries no information about the reversal — down-weight it
    to spend more of a finite session on the two contingencies that do swap. Setting it to
    0 keeps the patch defined (so state indices stay stable for analysis) but never visited."""
    weight_delayed: float = 1.0
    """Relative frequency of the delayed patch."""
    weight_single: float = 1.0
    """Relative frequency of the single patch."""

    rewardsite_length: float = 50
    minimum_interpatch_length: float = 150
    maximum_interpatch_length: float = 400
    minimum_intersite_length: float = 20
    maximum_intersite_length: float = 80

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


def make_reward_function(
    option: Optional[PatchType],
    first_stop: float = 0.5,
    cap_delayed_rewards: RewardMode = "capped",
    amount_drop: float = 5.0,
) -> list:
    """Build the reward-function list for a patch type (see module docstring)."""
    if option == "delayed":
        if cap_delayed_rewards == "capped":
            lut_values = [0.5, 1, 1, 1, 0]
            probability = task_logic.LookupTableFunction(
                lut_keys=list(np.arange(len(lut_values)) + 1), lut_values=lut_values
            )
            reward_function_prob = task_logic.PatchRewardFunction(
                probability=probability,
                rule=task_logic.RewardFunctionRule.ON_CHOICE_ACCUMULATED,
            )
            reward_available = amount_drop * 3
            available = task_logic.ClampedRateFunction(
                rate=task_logic.scalar_value(-amount_drop),
                minimum=0,
                maximum=reward_available,
            )
            reward_function_avail = task_logic.PatchRewardFunction(
                available=available,
                rule=task_logic.RewardFunctionRule.ON_REWARD,
            )
            reset_function = task_logic.OnThisPatchEntryRewardFunction(
                probability=task_logic.SetValueFunction(
                    value=task_logic.scalar_value(1)
                ),
                available=task_logic.SetValueFunction(
                    value=task_logic.scalar_value(reward_available)
                ),
            )
            return [reward_function_prob, reward_function_avail, reset_function]
        # "reduced" pays one fewer drop; "full" matches capped's LUT without the cap.
        lut_values = (
            [0.5, 1, 1, 0] if cap_delayed_rewards == "reduced" else [0.5, 1, 1, 1, 0]
        )
        probability = task_logic.LookupTableFunction(
            lut_keys=list(np.arange(len(lut_values)) + 1), lut_values=lut_values
        )
        reward_function_prob = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        )
        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(
                value=task_logic.scalar_value(first_stop)
            ),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(100)),
        )
        return [reward_function_prob, reset_function]

    if option == "single":
        probability = task_logic.LookupTableFunction(lut_keys=[1, 2], lut_values=[1, 0])
        reward_function = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        )
        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(1)),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(100)),
        )
        return [reward_function, reset_function]

    if option == "no_reward":
        reward_function = task_logic.PatchRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(0)),
            rule=task_logic.RewardFunctionRule.ON_CHOICE,
        )
        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(0)),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(0)),
        )
        return [reward_function, reset_function]

    raise ValueError(
        f"Option '{option}' not recognized. Valid: 'single', 'delayed', 'no_reward'."
    )


def make_odor_index(index: int, n_odors: int = 3) -> list[float]:
    """One-hot odor specification over ``n_odors`` channels."""
    odor = [0.0] * n_odors
    odor[index] = 1.0
    return odor


def make_patch(
    cfg: ReversalConfig,
    label: str,
    state_index: int,
    odor_index: list[float],
    patch_type: PatchType,
    reward_amount: float,
    first_p: float,
    reward_available: float,
    cap_delayed_rewards: RewardMode = "capped",
) -> task_logic.Patch:
    """Assemble one ``Patch`` (odor + reward spec + geometry) from ``cfg``."""
    return task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=odor_index,
        reward_specification=task_logic.RewardSpecification(
            operant_logic=helpers.make_operant_logic(stop_duration=cfg.stop_duration),
            delay=helpers.make_normal_distribution(
                mean=cfg.delay_mean, standard_deviation=0.15, minimum=0.0, maximum=1.0
            ),
            amount=task_logic.scalar_value(reward_amount),
            probability=task_logic.scalar_value(first_p),
            available=task_logic.scalar_value(reward_available),
            reward_function=make_reward_function(
                option=patch_type,
                first_stop=first_p,
                cap_delayed_rewards=cap_delayed_rewards,
                amount_drop=reward_amount,
            ),
        ),
        patch_virtual_sites_generator=helpers.make_patch_virtual_sites_generator(
            rewardsite=cfg.rewardsite_length,
            interpatch_min=cfg.minimum_interpatch_length,
            interpatch_max=cfg.maximum_interpatch_length,
            intersite_min=cfg.minimum_intersite_length,
            intersite_max=cfg.maximum_intersite_length,
        ),
    )


def patch_options(cfg: ReversalConfig, select: SetName) -> task_logic.MarkovEnvironment:
    """Build the 3-patch (null/delayed/single) MarkovEnvironment for one set."""
    mapping = ODOR_LABEL[select]
    # Labels are explicit about the odor CHANNEL each contingency sits on, e.g.
    # "patch_delayed_ch1". The three labels of a block fully determine the set, and a
    # reversal is visible directly as a contingency's channel changing between blocks.
    patches_list = [
        make_patch(
            cfg,
            label=f"patch_null_ch{mapping['noreward']}",
            state_index=0,
            odor_index=make_odor_index(mapping["noreward"]),
            patch_type="no_reward",
            reward_amount=0,
            first_p=0,
            reward_available=0,
        ),
        make_patch(
            cfg,
            label=f"patch_delayed_ch{mapping['delayed']}",
            state_index=1,
            odor_index=make_odor_index(mapping["delayed"]),
            patch_type="delayed",
            reward_amount=cfg.reward_amount,
            first_p=0.5,
            reward_available=50,
            cap_delayed_rewards=cfg.reward,
        ),
        make_patch(
            cfg,
            label=f"patch_single_ch{mapping['single']}",
            state_index=2,
            odor_index=make_odor_index(mapping["single"]),
            patch_type="single",
            reward_amount=cfg.reward_amount,
            first_p=1,
            reward_available=50,
        ),
    ]
    # Weights are keyed to contingency (state_index), not odor channel, so the mix stays
    # attached to null/delayed/single as the channels swap across a reversal.
    occupancy, transition_matrix = occupancy_matrix(cfg.patch_weights())
    return task_logic.MarkovEnvironment(
        first_state_occupancy=occupancy,
        transition_matrix=transition_matrix,
        patches=patches_list,
    )


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

    return AindVrForagingTaskLogic(
        stage_name=stage_name,
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=None,
            environment=task_logic.BlockStructure(
                blocks=blocks, sampling_mode="Sequential"
            ),
            operation_control=helpers.make_default_operation_control(
                velocity_threshold=cfg.velocity_threshold
            ),
        ),
    )


def _describe(cfg: ReversalConfig) -> None:
    """Print the block sequence and each set's contingency→channel map (odorant is rig-defined)."""
    occupancy, _ = occupancy_matrix(cfg.patch_weights())
    print(
        f"  patch mix: null={occupancy[0]:.0%}, delayed={occupancy[1]:.0%}, "
        f"single={occupancy[2]:.0%}"
    )
    for i, (select, end_value) in enumerate(build_sequence(cfg)):
        m = ODOR_LABEL[select]
        end = (
            "to session end" if isinstance(end_value, list) else f"{end_value} patches"
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
