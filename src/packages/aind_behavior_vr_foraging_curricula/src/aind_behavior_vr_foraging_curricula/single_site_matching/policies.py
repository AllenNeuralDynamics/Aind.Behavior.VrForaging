from typing import Callable

from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from . import helpers
from .metrics import SingleSiteMatchingMetrics

# ============================================================
# Policies to update task parameters based on metrics
# ============================================================

# Useful type hints for generic policies
PolicyType = Callable[
    [SingleSiteMatchingMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting


def p_learn_to_stop(metrics: SingleSiteMatchingMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    assert metrics.last_stop_threshold_updater is not None
    task.task_parameters.updaters[
        task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD
    ].parameters.initial_value = helpers.clamp(
        metrics.last_stop_threshold_updater * 1.2,  # make it easier than last stop
        minimum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.minimum,
        maximum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.maximum,
    )
    assert metrics.last_stop_duration_offset_updater is not None

    task.task_parameters.updaters[
        task_logic.UpdaterTarget.STOP_DURATION_OFFSET
    ].parameters.initial_value = helpers.clamp(
        metrics.last_stop_duration_offset_updater * 0.8,  # make it easier than last stop
        minimum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.minimum,
        maximum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.maximum,
    )

    return task
