from typing import Callable

from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from . import helpers
from .metrics import DepletionCurriculumMetrics

# ============================================================
# Policies to update task parameters based on metrics
# ============================================================

# Useful type hints for generic policies
PolicyType = Callable[
    [DepletionCurriculumMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting


def p_stochastic_reward(metrics: DepletionCurriculumMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    if metrics.total_water_consumed > 0.750:
        assert len(task.task_parameters.environment.blocks) > 0, "Expected at least one block in the task parameters"
        default_block = task.task_parameters.environment.blocks[0]
        assert len(default_block.environment_statistics.patches) > 0, "Expected at least one patch in the default block"

        default_block.environment_statistics.patches[0].reward_specification.probability = task_logic.scalar_value(0.9)

        reward_functions_defined = default_block.environment_statistics.patches[0].reward_specification.reward_function

        for reward_function in reward_functions_defined:
            if isinstance(reward_function, task_logic.PatchRewardFunction):
                reward_function.probability = task_logic.SetValueFunction(value=task_logic.scalar_value(0.9))

    return task


def p_learn_to_run(metrics: DepletionCurriculumMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    if metrics.n_reward_sites_traveled > 200:
        assert len(task.task_parameters.environment.blocks) > 0, "Expected at least one block in the task parameters"
        default_block = task.task_parameters.environment.blocks[0]
        assert len(default_block.environment_statistics.patches) > 0, "Expected at least one patch in the default block"
        patch_gen = default_block.environment_statistics.patches[0].patch_virtual_sites_generator

        gain = min(metrics.n_reward_sites_traveled / 200.0, 3.0)  # 1.0 for 200, 2.0 for 400, 3.0 for 600+

        assert isinstance(patch_gen.inter_site.length_distribution, distributions.ExponentialDistribution)
        assert patch_gen.inter_site.length_distribution.truncation_parameters is not None
        patch_gen.inter_site.length_distribution.truncation_parameters.min = helpers.clamp(
            patch_gen.inter_site.length_distribution.truncation_parameters.min * (1.5**gain),
            minimum=10,
            maximum=20,
        )
        patch_gen.inter_site.length_distribution.truncation_parameters.max = helpers.clamp(
            patch_gen.inter_site.length_distribution.truncation_parameters.max * (1.5**gain),
            minimum=30,
            maximum=100,
        )

        assert isinstance(patch_gen.inter_patch.length_distribution, distributions.ExponentialDistribution)
        assert patch_gen.inter_patch.length_distribution.truncation_parameters is not None
        patch_gen.inter_patch.length_distribution.truncation_parameters.min = helpers.clamp(
            patch_gen.inter_patch.length_distribution.truncation_parameters.min * (2**gain),
            minimum=25,
            maximum=200,
        )
        patch_gen.inter_patch.length_distribution.truncation_parameters.max = helpers.clamp(
            patch_gen.inter_patch.length_distribution.truncation_parameters.max * (2**gain),
            minimum=75,
            maximum=600,
        )

        assert isinstance(patch_gen.reward_site.length_distribution, distributions.Scalar)
        patch_gen.reward_site.length_distribution.distribution_parameters.value = helpers.clamp(
            patch_gen.reward_site.length_distribution.distribution_parameters.value + (10 * gain),
            minimum=20,
            maximum=50,
        )

    return task


def p_learn_to_stop(metrics: DepletionCurriculumMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    if metrics.n_choices > 100:
        updaters = task.task_parameters.updaters
        updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.initial_value = (
            updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.initial_value - 16.6
        )
        if updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.initial_value < 15.2:
            updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.initial_value = 15

        updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.initial_value = (
            updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.initial_value + 0.1
        )
        if metrics.last_delay_duration is not None:
            updaters[
                task_logic.UpdaterTarget.REWARD_DELAY_OFFSET
            ].parameters.initial_value = metrics.last_delay_duration

    return task
