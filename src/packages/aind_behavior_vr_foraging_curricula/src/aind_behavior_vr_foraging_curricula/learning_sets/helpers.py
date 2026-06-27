import random
from collections import deque
from dataclasses import dataclass
from typing import Optional

from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic


@dataclass
class CorridorGeometry:
    inter_patch_min_length: float
    inter_patch_mean_length: float
    inter_patch_max_length: float
    reward_site_length: float


#: Number of distinct odors available to the learning-set generator.
ODOR_COUNT: int = 7

#: Reward volume (µL) range and starting default. Sessions begin at ``DEFAULT``; the
#: graduated-stage water policy steers it within ``[MIN, MAX]``.
REWARD_AMOUNT_UL_MAX: float = 8.0
REWARD_AMOUNT_UL_MIN: float = 4.0
REWARD_AMOUNT_UL_DEFAULT: float = 6.0

#: Stop-duration shaping. The operant ``stop_duration`` is held at ``STOP_DURATION_BASE``
#: and a ``STOP_DURATION_OFFSET`` updater ramps on top of it, so the effective stop
#: grows ``STOP_DURATION_BASE -> STOP_DURATION_BASE + STOP_DURATION_OFFSET_MAX`` (= 3.0 s).
#: The base is deliberately tiny so that on the first few days (before the offset has
#: accumulated / seeded) a brief dip below the velocity threshold counts as a stop and
#: the subject can earn reward by chance.
STOP_DURATION_BASE: float = 0.1
STOP_DURATION_OFFSET_MAX: float = 2.9
STOP_DURATION_GRADUATED: float = 3.0  # fixed stop in the graduated stage (no updater)

#: Corridor geometry. Single reward site per patch; inter-site spacing is fixed. The
#: inter-patch spacing and reward-site length are *shaped* across sessions by
#: ``p_ease_geometry`` -- from the compressed (easy, day-1) values toward full spacing,
#: scaled by how many sites the subject traveled in the prior session. Full spacing is
#: reached at ``GEOMETRY_EASE_SITES`` traveled sites (``n_patches_seen``).
INTERSITE_LENGTH: float = 15.0
GEOMETRY_EASE_SITES: float = 150.0
GEOMETRY_COMPRESSED: CorridorGeometry = CorridorGeometry(
    inter_patch_min_length=30.0,
    inter_patch_mean_length=40.0,
    inter_patch_max_length=70.0,
    reward_site_length=25.0,
)
GEOMETRY_FULL: CorridorGeometry = CorridorGeometry(
    inter_patch_min_length=30.0,
    inter_patch_mean_length=60.0,
    inter_patch_max_length=190.0,
    reward_site_length=40.0,
)

#: Stop-velocity-threshold shaping (cm/s). One GAIN updater drives the threshold from
#: lenient (``VELOCITY_THRESHOLD_START``, so almost any deceleration registers as a stop)
#: down to the final ``VELOCITY_THRESHOLD_FLOOR`` across sessions.
#: ``STOP_VELOCITY_LEARNING_FACTOR`` eases each session's start a little above where the
#: prior session floored.
VELOCITY_THRESHOLD_START: float = 60.0
VELOCITY_THRESHOLD_FLOOR: float = 8.0
STOP_VELOCITY_LEARNING_FACTOR: float = 1.2

#: Reward delay (s) between a qualifying stop and reward delivery. Kept fixed/simple.
REWARD_DELAY_S: float = 0.5

#: Daily sequence size: ``N_PAIRS`` (neg, pos) pairs, each repeated ``N_SITES_EACH``
#: times for both variants -> ``N_PAIRS * N_SITES_EACH * 2`` reward sites per session.
N_PAIRS: int = 1000
N_SITES_EACH: int = 5

#: Proportion-based discrimination ramp. Negative sites per pair are introduced
#: progressively across sessions: session 1 → 0 neg (all positive), then 1, 3, 5.
#: Once the ramp is exhausted the ratio stays at 5+5.
N_NEG_RAMP: tuple[int, ...] = (1, 3, 5)

#: Cross-session seeding: start the stop-duration offset a little below where the
#: prior session ended, so the subject is not dropped at the longest stop on day N+1.
STOP_DURATION_LEARNING_FACTOR: float = 0.85

#: Graduated-stage water budget. If the prior session's water exceeds ``WATER_CAP_ML`` the
#: reward amount is trimmed by ``REWARD_AMOUNT_STEP_UL``; if it falls below ``WATER_FLOOR_ML``
#: the amount is raised by the same step (both clamped to the allowed range).
WATER_CAP_ML: float = 1.0
WATER_FLOOR_ML: float = 0.7
REWARD_AMOUNT_STEP_UL: float = 0.5


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def lerp(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def odor_concentration_from_index(odor_index: int, concentration: float = 1.0) -> list[float]:
    """One-hot odor mixture vector for ``odor_index`` at ``concentration``."""
    arr = [0.0 for _ in range(ODOR_COUNT)]
    arr[odor_index] = concentration
    return arr


def get_odor_sequence(total_trials: int, n: int = 1) -> list[tuple[int, int]]:
    """Generate ``total_trials`` (negative, positive) odor-index pairs.

    Same rules as ``examples/task_learning_sets.py``: no odor that appeared in the
    last ``n`` pairs may reappear, so consecutive pairs share no odor.
    """
    odors = list(range(ODOR_COUNT))
    if len(odors) < 2 * n + 2:
        raise ValueError("Not enough odors to satisfy the constraints with the given n.")

    pairs: list[tuple[int, int]] = []
    history: deque[tuple[int, int]] = deque(maxlen=n)
    for _ in range(total_trials):
        forbidden: set[int] = set()
        for pair in history:
            forbidden.update(pair)
        available = [o for o in odors if o not in forbidden]
        pos = random.choice(available)
        available.remove(pos)
        neg = random.choice(available)
        pairs.append((neg, pos))
        history.append((neg, pos))
    return pairs


def make_sequence(n_pos_each: int = N_SITES_EACH, n_neg_each: int = N_SITES_EACH, n_pairs: int = N_PAIRS) -> list[int]:
    """Build the ``patch_indices`` ordering for one session's block.

    For each (neg, pos) pair, emit ``n_neg_each`` negative-variant sites
    (``state_index == neg``) and ``n_pos_each`` positive-variant sites
    (``state_index == pos + ODOR_COUNT``), shuffled together.
    """
    trial_sequence: list[int] = []
    for neg, pos in get_odor_sequence(total_trials=n_pairs, n=1):
        block = [neg] * n_neg_each + [pos + ODOR_COUNT] * n_pos_each
        random.shuffle(block)
        trial_sequence.extend(block)
    return trial_sequence


def make_operation_control(velocity_threshold: float = VELOCITY_THRESHOLD_FLOOR) -> task_logic.OperationControl:
    return task_logic.OperationControl(
        position_control=task_logic.PositionControl(
            frequency_filter_cutoff=5,
            velocity_threshold=velocity_threshold,
        ),
    )


def make_patch(
    is_rewarded: bool,
    odor_index: int,
    p_reward: float,
    reward_amount: float = REWARD_AMOUNT_UL_DEFAULT,
    stop_duration: float = STOP_DURATION_BASE,
    geometry: Optional[CorridorGeometry] = None,
    inter_site_length: float = INTERSITE_LENGTH,
) -> task_logic.Patch:
    """A single odor-marked reward site (one reward site per patch).

    ``is_rewarded`` selects the positive (``state_index = odor_index + ODOR_COUNT``)
    or negative (``state_index = odor_index``) variant; ``p_reward`` sets its reward
    probability (the curriculum shapes the negative variant's probability). The
    inter-patch / reward-site lengths are the shaped geometry (see ``p_ease_geometry``).
    """
    if geometry is None:
        geometry = GEOMETRY_FULL
    return task_logic.Patch(
        label=f"{odor_index}_{'Rewarded' if is_rewarded else 'NonRewarded'}",
        state_index=odor_index + ODOR_COUNT * int(is_rewarded),
        odor_specification=odor_concentration_from_index(odor_index, 1.0),
        patch_terminators=[
            task_logic.PatchTerminatorOnRewardSite(count=task_logic.scalar_value(1)),
        ],
        reward_specification=task_logic.RewardSpecification(
            amount=task_logic.scalar_value(reward_amount),
            probability=task_logic.scalar_value(p_reward),
            delay=task_logic.scalar_value(REWARD_DELAY_S),
            operant_logic=task_logic.OperantLogic(
                is_operant=False,
                stop_duration=stop_duration,
            ),
        ),
        patch_virtual_sites_generator=task_logic.PatchVirtualSitesGenerator(
            inter_patch=task_logic.VirtualSiteGenerator(
                render_specification=task_logic.RenderSpecification(contrast=1),
                label=task_logic.VirtualSiteLabels.INTERPATCH,
                length_distribution=distributions.ExponentialDistribution(
                    distribution_parameters=distributions.ExponentialDistributionParameters(
                        rate=1 / geometry.inter_patch_mean_length
                    ),
                    scaling_parameters=distributions.ScalingParameters(offset=geometry.inter_patch_min_length),
                    truncation_parameters=distributions.TruncationParameters(
                        min=geometry.inter_patch_min_length,
                        max=geometry.inter_patch_max_length,
                    ),
                ),
            ),
            inter_site=task_logic.VirtualSiteGenerator(
                render_specification=task_logic.RenderSpecification(contrast=0.5),
                label=task_logic.VirtualSiteLabels.INTERSITE,
                length_distribution=task_logic.scalar_value(inter_site_length),
            ),
            reward_site=task_logic.VirtualSiteGenerator(
                render_specification=task_logic.RenderSpecification(contrast=0.5),
                label=task_logic.VirtualSiteLabels.REWARDSITE,
                length_distribution=task_logic.scalar_value(geometry.reward_site_length),
            ),
        ),
    )


def make_block(
    negative_probability: float,
    positive_probability: float = 1.0,
    reward_amount: float = REWARD_AMOUNT_UL_DEFAULT,
    stop_duration: float = STOP_DURATION_BASE,
    geometry: Optional[CorridorGeometry] = None,
    n_pairs: int = N_PAIRS,
    n_neg_each: int = 0,
) -> task_logic.Block:
    """One session's block: ``ODOR_COUNT`` negative + ``ODOR_COUNT`` positive odor patches
    played in a freshly generated ``Ordered`` sequence.

    ``n_neg_each`` controls how many negative-variant sites appear per pair (0 on day 1,
    ramping via ``N_NEG_RAMP``); positive sites fill the remainder up to
    ``N_SITES_EACH * 2`` total per pair. ``negative_probability`` sets the reward
    probability for negative patches (fixed at 0 in the proportion-based design).
    ``geometry`` defaults to the compressed day-1 values; ``p_ease_geometry`` eases them
    toward full across sessions.
    """
    geometry = geometry if geometry is not None else GEOMETRY_COMPRESSED
    n_pos_each = N_SITES_EACH * 2 - n_neg_each
    patches = [
        make_patch(
            is_rewarded=False,
            odor_index=i,
            p_reward=negative_probability,
            reward_amount=reward_amount,
            stop_duration=stop_duration,
            geometry=geometry,
        )
        for i in range(ODOR_COUNT)
    ] + [
        make_patch(
            is_rewarded=True,
            odor_index=i,
            p_reward=positive_probability,
            reward_amount=reward_amount,
            stop_duration=stop_duration,
            geometry=geometry,
        )
        for i in range(ODOR_COUNT)
    ]
    return task_logic.Block(
        environment=task_logic.SequenceEnvironment(
            patches=patches,
            sampling_mode="Ordered",
            patch_indices=make_sequence(n_pos_each=n_pos_each, n_neg_each=n_neg_each, n_pairs=n_pairs),
        ),
    )


def make_stop_duration_updater(initial_value: float = 0.0) -> task_logic.NumericalUpdater:
    """Within-session ramp of the stop-duration offset (0 -> ``STOP_DURATION_OFFSET_MAX``)."""
    return task_logic.NumericalUpdater(
        operation=task_logic.NumericalUpdaterOperation.OFFSET,
        parameters=task_logic.NumericalUpdaterParameters(
            initial_value=initial_value,
            on_success=0.01,
            minimum=0.0,
            maximum=STOP_DURATION_OFFSET_MAX,
        ),
    )


def make_stop_velocity_updater(
    initial_value: float = VELOCITY_THRESHOLD_START,
    minimum: float = VELOCITY_THRESHOLD_FLOOR,
    maximum: float = VELOCITY_THRESHOLD_START,
) -> task_logic.NumericalUpdater:
    """Within-session shaping of the stop-velocity threshold: GAIN multiplies it by 0.93
    on each rewarded stop, drawing it from ``initial_value`` down toward ``minimum`` so
    the velocity slack closes as the subject practices real stops."""
    return task_logic.NumericalUpdater(
        operation=task_logic.NumericalUpdaterOperation.GAIN,
        parameters=task_logic.NumericalUpdaterParameters(
            initial_value=initial_value,
            on_success=0.93,
            minimum=minimum,
            maximum=maximum,
        ),
    )
