from typing import Callable

import numpy as np
from aind_behavior_vr_foraging import task_logic as vr_task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from ..depletion.metrics import DepletionCurriculumMetrics
from .utils import compute_cmc_transition_probability

# ============================================================
# Policies to update task parameters based on metrics
# ============================================================

# Useful type hints for generic policies
PolicyType = Callable[
    [DepletionCurriculumMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def p_update_replenishment_rate(
    metrics: DepletionCurriculumMetrics, task: AindVrForagingTaskLogic
) -> AindVrForagingTaskLogic:
    """Update replenishment rate based on water consumed in the session."""

    MAX_RATE_DROP_PER_SESSION = 0.01  # (0.10 - 0.05) / 5 sessions
    TARGET_MAX_WATER = 1000
    TARGET_MIN_WATER = 700
    water_consumed = clamp(metrics.total_water_consumed, TARGET_MIN_WATER, TARGET_MAX_WATER)
    # Linearly interpolate replenishment rate based on water consumed
    gain_from_water = 1.0 - (
        (TARGET_MAX_WATER - water_consumed) / (TARGET_MAX_WATER - TARGET_MIN_WATER) * MAX_RATE_DROP_PER_SESSION
    )

    assert len(task.task_parameters.environment.blocks) == 1, "Only single block environments are supported."
    patches = task.task_parameters.environment.blocks[0].environment_statistics.patches
    for patch in patches:
        reward_function_candidates = [
            f
            for f in patch.reward_specification.reward_function
            if (
                isinstance(f, vr_task_logic.OutsideRewardFunction)
                and isinstance(f.probability, vr_task_logic.CtcmFunction)
            )
        ]
        if len(reward_function_candidates) != 1:
            raise ValueError(
                f"Expected exactly one CtcmFunction in OutsideRewardFunction for patch {patch.label}, found {reward_function_candidates}"
            )
        # We assume a dt = 0.1, and an approximately poisson replenishment process
        dt = 0.1
        estimated_rate = -np.log(np.array(reward_function_candidates[0].probability.transition_matrix)[0, 0]) / dt
        updated_rate = clamp(estimated_rate - gain_from_water, 0.05, 0.10)
        reward_function_candidates[0].probability.transition_matrix = compute_cmc_transition_probability(
            len(reward_function_candidates[0].probability.transition_matrix), updated_rate, dt
        ).tolist()
    return task
