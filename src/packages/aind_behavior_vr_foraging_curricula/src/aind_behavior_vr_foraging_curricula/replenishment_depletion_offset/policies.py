from collections.abc import Callable

from aind_behavior_vr_foraging import task_logic as vr_task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .metrics import ReplenishmentCurriculumMetrics
from .utils import compute_cmc_transition_probability, estimate_replenishment_rate, get_replenishment_function

# ============================================================
# Policies to update task parameters based on metrics
# ============================================================

# Useful type hints for generic policies
PolicyType = Callable[
    [ReplenishmentCurriculumMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting

DT = 0.1
MAX_RATE_DROP_PER_SESSION = 0.01  # (0.10 - 0.08) / 2 sessions
TARGET_MAX_WATER = 1.0  # mL
TARGET_MIN_WATER = 0.7  # mL
MAX_RATE = 0.10
MIN_RATE = 0.08
RATE_TOLERANCE = 1e-6

# History-gated steps (first rate drop, reward drop):
# - Need `TARGET_WATER` in the last `N_SESSIONS_AT_TARGET` sessions of the current stage, today included.
# - The gradual rate drop only looks at today's session.
TARGET_WATER = 0.8  # mL
N_SESSIONS_AT_TARGET = 3
REDUCED_REWARD_AMOUNT = 4.0  # microliters


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _met_target_for_recent_sessions(
    today_metrics: ReplenishmentCurriculumMetrics,
    today_task: AindVrForagingTaskLogic,
    *,
    at_min_rate: bool = False,
) -> bool:
    """True if the last `N_SESSIONS_AT_TARGET` sessions of the current stage:
    - consumed at least `TARGET_WATER`
    - ran at `MIN_RATE` (only if `at_min_rate`)
    """
    past = [s for s in today_metrics.past_sessions if s.stage_name == today_task.stage_name]
    recent = [*past, today_metrics][-N_SESSIONS_AT_TARGET:]
    return len(recent) == N_SESSIONS_AT_TARGET and all(
        m.total_water_consumed >= TARGET_WATER
        and (not at_min_rate or m.replenishment_rate <= MIN_RATE + RATE_TOLERANCE)
        for m in recent
    )


def _set_replenishment_rate(today_task: AindVrForagingTaskLogic, rate: float) -> None:
    for patch in today_task.task_parameters.environment.blocks[0].environment.patches:
        ctcm = get_replenishment_function(patch).probability
        ctcm.transition_matrix = compute_cmc_transition_probability(len(ctcm.transition_matrix), rate, DT).tolist()


def p_update_replenishment_rate(
    today_metrics: ReplenishmentCurriculumMetrics, today_task: AindVrForagingTaskLogic
) -> AindVrForagingTaskLogic:
    """Reduces the replenishment rate:
    - Initial rate -> `MAX_RATE`: once the water target is met for `N_SESSIONS_AT_TARGET` sessions.
    - `MAX_RATE` -> `MIN_RATE`: gradually, each step scaled by today's water.
    """

    assert len(today_task.task_parameters.environment.blocks) == 1, "Only single block environments are supported."
    patches = today_task.task_parameters.environment.blocks[0].environment.patches

    current_rate = estimate_replenishment_rate(get_replenishment_function(patches[0]).probability.transition_matrix)
    # If we go above the maximum (only first time hopefully).
    if current_rate > MAX_RATE + RATE_TOLERANCE:
        if _met_target_for_recent_sessions(today_metrics, today_task):
            _set_replenishment_rate(today_task, MAX_RATE)
        return today_task

    # Otherwise we compute the updated rate
    water_consumed = clamp(today_metrics.total_water_consumed, TARGET_MIN_WATER, TARGET_MAX_WATER)
    gain_from_water = (
        (water_consumed - TARGET_MIN_WATER) / (TARGET_MAX_WATER - TARGET_MIN_WATER) * MAX_RATE_DROP_PER_SESSION
    )
    for patch in patches:
        ctcm = get_replenishment_function(patch).probability
        estimated_rate = estimate_replenishment_rate(ctcm.transition_matrix, DT)
        updated_rate = clamp(estimated_rate - gain_from_water, MIN_RATE, MAX_RATE)
        ctcm.transition_matrix = compute_cmc_transition_probability(
            len(ctcm.transition_matrix), updated_rate, DT
        ).tolist()
    return today_task


def p_update_reward_amount(
    today_metrics: ReplenishmentCurriculumMetrics, today_task: AindVrForagingTaskLogic
) -> AindVrForagingTaskLogic:
    """Reduces the reward amount once the last `N_SESSIONS_AT_TARGET` sessions
    all ran at `MIN_RATE` and met the water target.
    """

    if _met_target_for_recent_sessions(today_metrics, today_task, at_min_rate=True):
        for patch in today_task.task_parameters.environment.blocks[0].environment.patches:
            patch.reward_specification.amount = vr_task_logic.scalar_value(REDUCED_REWARD_AMOUNT)
    return today_task
