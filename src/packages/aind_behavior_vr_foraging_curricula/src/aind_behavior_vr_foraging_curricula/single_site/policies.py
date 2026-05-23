from typing import Callable

from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .metrics import SingleSiteMetrics


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


# ============================================================
# Policies to update task parameters based on metrics
# ============================================================

# Useful type hints for generic policies
PolicyType = Callable[
    [SingleSiteMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting


def p_learn_to_stop(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    assert metrics.last_stop_threshold_updater is not None
    task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.initial_value = _clamp(
        metrics.last_stop_threshold_updater * 1.2,  # make it easier than last stop
        minimum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.minimum,
        maximum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.maximum,
    )
    assert metrics.last_stop_duration_offset_updater is not None

    task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.initial_value = _clamp(
        metrics.last_stop_duration_offset_updater * 0.8,  # make it easier than last stop
        minimum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.minimum,
        maximum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.maximum,
    )

    return task


def p_seed_reward_delay(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    if metrics.last_reward_delay_offset_updater is None:
        return task
    updater = task.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET]
    updater.parameters.initial_value = _clamp(
        metrics.last_reward_delay_offset_updater * 0.8,  # ease in from where last session ended
        minimum=updater.parameters.minimum,
        maximum=updater.parameters.maximum,
    )
    return task


def p_seed_stop_duration(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    if metrics.last_stop_duration_offset_updater is None:
        return task
    updater = task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET]
    # In S3 the offset is negative (stop shrinks as reward delay grows). Scaling by
    # 0.8 nudges it back toward 0 so each session re-ramps a shorter distance.
    updater.parameters.initial_value = _clamp(
        metrics.last_stop_duration_offset_updater * 0.8,
        minimum=updater.parameters.minimum,
        maximum=updater.parameters.maximum,
    )
    return task
