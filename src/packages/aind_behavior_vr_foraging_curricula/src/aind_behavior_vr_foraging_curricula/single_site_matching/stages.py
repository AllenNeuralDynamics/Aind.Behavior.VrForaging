from typing import Any, Optional

import aind_behavior_services.task.distributions as distributions
import aind_behavior_vr_foraging.task_logic as vr_task_logic
from aind_behavior_curriculum import MetricsProvider, Policy, Stage
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from .metrics import metrics_from_dataset
from .policies import p_learn_to_stop


def make_patch(
    label: str,
    state_index: int,
    odor_index: int,
    p_reward: float,
    p_replenish: float,
    stop_duration: float = 0.5,
    reward_amount: float = 5.0,
    inter_site_length: float = 15,
    reward_site_length: float = 40,
    inter_patch_min_length: float = 50,
    inter_patch_mean_length: float = 150,
    inter_patch_max_length: float = 500,
):
    baiting_function = vr_task_logic.PersistentRewardFunction(
        rule=vr_task_logic.RewardFunctionRule.ON_PATCH_ENTRY,
        probability=vr_task_logic.SetValueFunction(
            value=distributions.BinomialDistribution(
                distribution_parameters=distributions.BinomialDistributionParameters(n=1, p=p_replenish),
                scaling_parameters=distributions.ScalingParameters(offset=p_reward),
                truncation_parameters=distributions.TruncationParameters(min=p_reward, max=1, truncation_mode="clamp"),
            ),
        ),
    )

    depletion_function = vr_task_logic.PatchRewardFunction(
        probability=vr_task_logic.SetValueFunction(
            value=vr_task_logic.scalar_value(p_reward),
        ),
        rule=vr_task_logic.RewardFunctionRule.ON_REWARD,
    )

    return vr_task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=[1 if i == odor_index else 0 for i in range(3)],
        patch_terminators=[
            vr_task_logic.PatchTerminatorOnChoice(count=vr_task_logic.scalar_value(1)),
            vr_task_logic.PatchTerminatorOnRejection(count=vr_task_logic.scalar_value(1)),
        ],
        reward_specification=vr_task_logic.RewardSpecification(
            amount=vr_task_logic.scalar_value(reward_amount),
            probability=vr_task_logic.scalar_value(p_reward),
            available=vr_task_logic.scalar_value(999999),
            delay=vr_task_logic.scalar_value(0.5),
            operant_logic=vr_task_logic.OperantLogic(
                is_operant=False,
                stop_duration=stop_duration,
                time_to_collect_reward=100000,
                grace_distance_threshold=10,
            ),
            reward_function=[baiting_function, depletion_function],
        ),
        patch_virtual_sites_generator=vr_task_logic.PatchVirtualSitesGenerator(
            inter_patch=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=1),
                label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
                length_distribution=distributions.ExponentialDistribution(
                    distribution_parameters=distributions.ExponentialDistributionParameters(
                        rate=1.0 / inter_patch_mean_length
                    ),
                    scaling_parameters=distributions.ScalingParameters(offset=inter_patch_min_length),
                    truncation_parameters=distributions.TruncationParameters(
                        min=inter_patch_min_length,
                        max=inter_patch_max_length,
                    ),
                ),
            ),
            inter_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.INTERSITE,
                length_distribution=vr_task_logic.scalar_value(inter_site_length),
            ),
            reward_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
                length_distribution=vr_task_logic.scalar_value(reward_site_length),
            ),
        ),
    )


def make_block(
    p_rew: tuple[float, Optional[float], Optional[float]],
    p_replenish: tuple[float, Optional[float], Optional[float]],
    n_min_patches: int = 100,
    make_patch_kwargs: Optional[dict[str, Any]] = None,
) -> vr_task_logic.Block:
    make_patch_kwargs = make_patch_kwargs or {}
    patches = [
        make_patch(
            label="OdorA",
            state_index=0,
            odor_index=0,
            p_reward=p_rew[0],
            p_replenish=p_replenish[0],
            **make_patch_kwargs,
        )
    ]
    if p_rew[1] is not None:
        assert p_replenish[1] is not None
        patches.append(
            make_patch(
                label="OdorB",
                state_index=1,
                odor_index=1,
                p_reward=p_rew[1],
                p_replenish=p_replenish[1],
                **make_patch_kwargs,
            )
        )
    if p_rew[2] is not None:
        assert p_replenish[2] is not None
        patches.append(
            make_patch(
                label="OdorC",
                state_index=2,
                odor_index=2,
                p_reward=p_rew[2],
                p_replenish=p_replenish[2],
                **make_patch_kwargs,
            )
        )

    per_p = 1.0 / len(patches)
    return vr_task_logic.Block(
        environment_statistics=vr_task_logic.EnvironmentStatistics(
            first_state_occupancy=[per_p] * len(patches),
            transition_matrix=[[per_p] * len(patches) for _ in range(len(patches))],
            patches=patches,
        ),
        end_conditions=[
            vr_task_logic.BlockEndConditionPatchCount(
                value=distributions.ExponentialDistribution(
                    distribution_parameters=distributions.ExponentialDistributionParameters(rate=1 / 25),
                    scaling_parameters=distributions.ScalingParameters(offset=n_min_patches),
                    truncation_parameters=distributions.TruncationParameters(min=n_min_patches, max=n_min_patches + 50),
                )
            )
        ],
    )


def make_operation_control(velocity_threshold: float) -> vr_task_logic.OperationControl:
    return vr_task_logic.OperationControl(
        movable_spout_control=vr_task_logic.MovableSpoutControl(enabled=False),
        audio_control=vr_task_logic.AudioControl(duration=0.2, frequency=9999),
        odor_control=vr_task_logic.OdorControl(),
        position_control=vr_task_logic.PositionControl(
            frequency_filter_cutoff=5,
            velocity_threshold=velocity_threshold,
        ),
    )


# ============================================================
# Stage definition
# ============================================================


def make_s_learn_to_stop() -> Stage:
    return Stage(
        name="learn_to_stop",
        task=AindVrForagingTaskLogic(
            stage_name="learn_to_stop",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    vr_task_logic.UpdaterTarget.STOP_DURATION_OFFSET: vr_task_logic.NumericalUpdater(
                        operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=vr_task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=0.003, minimum=0, maximum=0.6
                        ),
                    ),
                    vr_task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: vr_task_logic.NumericalUpdater(
                        operation=vr_task_logic.NumericalUpdaterOperation.GAIN,
                        parameters=vr_task_logic.NumericalUpdaterParameters(
                            initial_value=60,
                            on_success=0.995,
                            minimum=8,
                            maximum=60,
                        ),
                    ),
                },
                environment=vr_task_logic.BlockStructure(
                    blocks=[
                        make_block(
                            p_rew=(1, 1, None),
                            p_replenish=(1, 1, None),
                            n_min_patches=100000,
                            make_patch_kwargs={
                                "inter_patch_min_length": 50,
                                "inter_patch_mean_length": 120,
                                "inter_patch_max_length": 150,
                                "inter_site_length": 15,
                                "reward_site_length": 40,
                            },
                        ),
                    ],
                    sampling_mode="Sequential",
                ),
                operation_control=make_operation_control(velocity_threshold=60),
            ),
        ),
        start_policies=[Policy(x) for x in [p_learn_to_stop]],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_graduated_stage() -> Stage:
    _graduated_make_patch_kwargs = {
        "inter_patch_min_length": 30,
        "inter_patch_mean_length": 60,
        "inter_patch_max_length": 190,
        "inter_site_length": 15,
        "reward_site_length": 50,
        "reward_amount": 7,
        "stop_duration": 1.5,
    }

    return Stage(
        name="graduated_stage",
        task=AindVrForagingTaskLogic(
            stage_name="graduated_stage",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=vr_task_logic.BlockStructure(
                    blocks=[
                        make_block(
                            p_rew=(0.9, 0.10, None),
                            p_replenish=(0.45, 0.05, None),
                            n_min_patches=40,
                            make_patch_kwargs=_graduated_make_patch_kwargs,
                        ),
                        make_block(
                            p_rew=(0.10, 0.9, None),
                            p_replenish=(0.05, 0.45, None),
                            n_min_patches=40,
                            make_patch_kwargs=_graduated_make_patch_kwargs,
                        ),
                    ],
                    sampling_mode="Random",
                ),
                operation_control=make_operation_control(velocity_threshold=8),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )
