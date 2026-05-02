from typing import Callable

import aind_behavior_services.task.distributions as distributions
from aind_behavior_curriculum import MetricsProvider, Policy, Stage
from aind_behavior_vr_foraging import task_logic as vr_task_logic
from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)

from .metrics import VrForagingTemplateMetrics, metrics_from_dataset


def NumericalUpdaterParametersHelper(initial_value, on_success, on_failure, minimum, maximum):
    return vr_task_logic.NumericalUpdaterParameters(
        initial_value=initial_value,
        on_success=on_success,
        on_failure=on_failure,
        minimum=minimum,
        maximum=maximum,
    )


updaters = {
    vr_task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: vr_task_logic.NumericalUpdater(
        operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
        parameters=NumericalUpdaterParametersHelper(0, 0.005, 0, 0, 0.2),
    ),
    vr_task_logic.UpdaterTarget.STOP_DURATION_OFFSET: vr_task_logic.NumericalUpdater(
        operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
        parameters=NumericalUpdaterParametersHelper(0, 0.005, 0, 0, 0.5),
    ),
    vr_task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: vr_task_logic.NumericalUpdater(
        operation=vr_task_logic.NumericalUpdaterOperation.GAIN,
        parameters=NumericalUpdaterParametersHelper(40, 0, -0.25, 10, 40),
    ),
}

operation_control = vr_task_logic.OperationControl(
    movable_spout_control=vr_task_logic.MovableSpoutControl(
        enabled=True,
        time_to_collect_after_reward=1,
        retracting_distance=2000,
    ),
    audio_control=vr_task_logic.AudioControl(frequency=1000, duration=0.2),
    odor_control=vr_task_logic.OdorControl(
        valve_max_open_time=100000, target_odor_flow=100, target_total_flow=1000, use_channel_3_as_carrier=True
    ),
    position_control=vr_task_logic.PositionControl(
        gain=vr_task_logic.Vector3(x=1, y=1, z=1),
        initial_position=vr_task_logic.Vector3(x=0, y=2.56, z=0),
        frequency_filter_cutoff=5,
        velocity_threshold=40,
    ),
)


def OperantLogicHelper(stop_duration: float = 0.2, is_operant: bool = False):
    return vr_task_logic.OperantLogic(
        is_operant=is_operant,
        stop_duration=stop_duration,
        time_to_collect_reward=1000000,
        grace_distance_threshold=10,
    )


def ExponentialDistributionHelper(rate=1, minimum=0, maximum=1000):
    return distributions.ExponentialDistribution(
        distribution_parameters=distributions.ExponentialDistributionParameters(rate=rate),
        truncation_parameters=distributions.TruncationParameters(min=minimum, max=maximum, is_truncated=True),
        scaling_parameters=distributions.ScalingParameters(scale=1.0, offset=0.0),
    )


def RewardVirtualSiteGeneratorHelper(contrast: float = 0.5, friction: float = 0):
    return vr_task_logic.VirtualSiteGenerator(
        render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
        label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
        length_distribution=ExponentialDistributionHelper(1, 0, 10),
        treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
    )


def InterSiteVirtualSiteGeneratorHelper(contrast: float = 0.5, friction: float = 0):
    return vr_task_logic.VirtualSiteGenerator(
        render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
        label=vr_task_logic.VirtualSiteLabels.INTERSITE,
        length_distribution=ExponentialDistributionHelper(1, 0, 10),
        treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
    )


def InterPatchVirtualSiteGeneratorHelper(contrast: float = 1, friction: float = 0):
    return vr_task_logic.VirtualSiteGenerator(
        render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
        label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
        length_distribution=ExponentialDistributionHelper(1, 0, 10),
        treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
    )


def PostPatchVirtualSiteGeneratorHelper(contrast: float = 1, friction: float = 0.5):
    return vr_task_logic.VirtualSiteGenerator(
        render_specification=vr_task_logic.RenderSpecification(contrast=contrast),
        label=vr_task_logic.VirtualSiteLabels.POSTPATCH,
        length_distribution=ExponentialDistributionHelper(1, 0, 10),
        treadmill_specification=vr_task_logic.TreadmillSpecification(friction=vr_task_logic.scalar_value(friction)),
    )


reward_function = vr_task_logic.PatchRewardFunction(
    available=vr_task_logic.ClampedRateFunction(minimum=0, maximum=5, rate=vr_task_logic.scalar_value(-1)),
    rule=vr_task_logic.RewardFunctionRule.ON_REWARD,
)

reset_function = vr_task_logic.OnThisPatchEntryRewardFunction(
    available=vr_task_logic.SetValueFunction(value=vr_task_logic.scalar_value(0.1))
)

replenish_function = vr_task_logic.OutsideRewardFunction(
    available=vr_task_logic.ClampedRateFunction(minimum=0, maximum=5, rate=vr_task_logic.scalar_value(1)),
    rule=vr_task_logic.RewardFunctionRule.ON_TIME,
)

patch1 = vr_task_logic.Patch(
    label="reset",
    state_index=0,
    odor_specification=vr_task_logic._OdorSpecification(index=1, concentration=1),
    reward_specification=vr_task_logic.RewardSpecification(
        amount=vr_task_logic.scalar_value(1),
        probability=vr_task_logic.scalar_value(1),
        available=vr_task_logic.scalar_value(5),
        reward_function=[reward_function, reset_function],
        operant_logic=OperantLogicHelper(),
        delay=ExponentialDistributionHelper(1, 0, 10),
    ),
    patch_virtual_sites_generator=vr_task_logic.PatchVirtualSitesGenerator(
        inter_patch=InterPatchVirtualSiteGeneratorHelper(),
        inter_site=InterSiteVirtualSiteGeneratorHelper(),
        reward_site=RewardVirtualSiteGeneratorHelper(),
        post_patch=PostPatchVirtualSiteGeneratorHelper(),
    ),
)

patch2 = vr_task_logic.Patch(
    label="slow-replenish",
    state_index=1,
    odor_specification=vr_task_logic._OdorSpecification(index=0, concentration=1),
    reward_specification=vr_task_logic.RewardSpecification(
        reward_function=[reward_function, replenish_function],
        operant_logic=OperantLogicHelper(),
        delay=ExponentialDistributionHelper(1, 0, 10),
    ),
    patch_virtual_sites_generator=vr_task_logic.PatchVirtualSitesGenerator(
        inter_patch=InterPatchVirtualSiteGeneratorHelper(),
        inter_site=InterSiteVirtualSiteGeneratorHelper(),
        reward_site=RewardVirtualSiteGeneratorHelper(),
    ),
)

environment_statistics = vr_task_logic.EnvironmentStatistics(
    first_state_occupancy=[1, 0], transition_matrix=[[1, 0], [0, 1]], patches=[patch1, patch2]
)


# ============================================================
# Policies to update task parameters based on metrics
# ============================================================

# Useful type hints for generic policies
PolicyType = Callable[
    [VrForagingTemplateMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting


def p_identity_policy(metrics: VrForagingTemplateMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """An identity policy that does nothing"""
    return task


def p_set_mode_from_metric1(
    metrics: VrForagingTemplateMetrics, task: AindVrForagingTaskLogic
) -> AindVrForagingTaskLogic:
    if metrics.metric1 < 0:
        task.task_parameters.rng_seed = 10
    elif 0 <= metrics.metric1 < 0.5:
        task.task_parameters.rng_seed = 20
    else:
        task.task_parameters.rng_seed = 30
    return task


# ============================================================
# Stage definition
# ============================================================

s_stage_a = Stage(
    name="stage_a",
    task=AindVrForagingTaskLogic(
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=1,
            updaters=updaters,
            environment=vr_task_logic.BlockStructure(
                blocks=[vr_task_logic.Block(environment_statistics=environment_statistics, end_conditions=[])],
                sampling_mode="Random",
            ),
            operation_control=operation_control,
        ),
    ),
    start_policies=[Policy(x) for x in [p_set_mode_from_metric1]],
    metrics_provider=MetricsProvider(metrics_from_dataset),
)

s_stage_b = Stage(
    name="stage_b",
    task=AindVrForagingTaskLogic(
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=2,
            updaters=updaters,
            environment=vr_task_logic.BlockStructure(
                blocks=[vr_task_logic.Block(environment_statistics=environment_statistics, end_conditions=[])],
                sampling_mode="Random",
            ),
            operation_control=operation_control,
        )
    ),
    metrics_provider=MetricsProvider(metrics_from_dataset),
)
