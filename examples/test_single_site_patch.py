import os
from typing import Optional

import aind_behavior_services.task.distributions as distributions
from aind_behavior_curriculum import Stage, TrainerState

import aind_behavior_vr_foraging.task as vr_task_logic
from aind_behavior_vr_foraging.task import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)

MINIMUM_INTERPATCH_LENGTH = 50
MEAN_INTERPATCH_LENGTH = 150
MAXIMUM_INTERPATCH_LENGTH = 500
INTERSITE_LENGTH = 50
REWARDSITE_LENGTH = 50
REWARD_AMOUNT = 3
VELOCITY_THRESHOLD = 15  # cm/s

P_REWARD_BLOCK: list[tuple[float, Optional[float], Optional[float]]] = [
    (1.0, 1.0, None),
    (0.8, 0.8, None),
    (0.8, 0.2, None),
]

P_BAIT_BLOCK = [
    (1.0, 1.0, None),
    (0.4, 0.4, None),
    (0.4, 0.1, None),
]


def make_patch(
    label: str,
    state_index: int,
    odor_index: int,
    p_reward: float,
    p_replenish: float,
):
    baiting_function = vr_task_logic.PersistentRewardFunction(
        rule=vr_task_logic.RewardFunctionRule.ON_PATCH_ENTRY,
        probability=vr_task_logic.SetValueFunction(
            value=distributions.BinomialDistribution(
                distribution_parameters=distributions.BinomialDistributionParameters(n=1, p=p_replenish),
                scaling_parameters=distributions.ScalingParameters(offset=p_reward),
                truncation_parameters=distributions.TruncationParameters(min=p_reward, max=1),
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
        odor_specification=vr_task_logic.OdorSpecification(index=odor_index, concentration=1),
        patch_terminators=[
            vr_task_logic.PatchTerminatorOnChoice(count=vr_task_logic.scalar_value(1)),
            vr_task_logic.PatchTerminatorOnRejection(count=vr_task_logic.scalar_value(1)),
        ],
        reward_specification=vr_task_logic.RewardSpecification(
            amount=vr_task_logic.scalar_value(REWARD_AMOUNT),
            probability=vr_task_logic.scalar_value(p_reward),
            available=vr_task_logic.scalar_value(999999),
            delay=vr_task_logic.scalar_value(0.5),
            operant_logic=vr_task_logic.OperantLogic(
                is_operant=False,
                stop_duration=0.5,
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
                        rate=1 / MEAN_INTERPATCH_LENGTH
                    ),
                    scaling_parameters=distributions.ScalingParameters(offset=MINIMUM_INTERPATCH_LENGTH),
                    truncation_parameters=distributions.TruncationParameters(
                        min=MINIMUM_INTERPATCH_LENGTH,
                        max=MAXIMUM_INTERPATCH_LENGTH,
                    ),
                ),
            ),
            inter_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.INTERSITE,
                length_distribution=vr_task_logic.scalar_value(INTERSITE_LENGTH),
            ),
            reward_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
                length_distribution=vr_task_logic.scalar_value(REWARDSITE_LENGTH),
            ),
        ),
    )


def make_block(
    p_rew: tuple[float, Optional[float], Optional[float]],
    p_replenish: tuple[float, Optional[float], Optional[float]],
    n_min_trials: int = 100,
) -> vr_task_logic.Block:
    patches = [make_patch(label="OdorA", state_index=0, odor_index=0, p_reward=p_rew[0], p_replenish=p_replenish[0])]
    if p_rew[1] is not None:
        assert p_replenish[1] is not None
        patches.append(
            make_patch(label="OdorB", state_index=1, odor_index=1, p_reward=p_rew[1], p_replenish=p_replenish[1])
        )
    if p_rew[2] is not None:
        assert p_replenish[2] is not None
        patches.append(
            make_patch(label="OdorC", state_index=2, odor_index=2, p_reward=p_rew[2], p_replenish=p_replenish[2])
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
                    scaling_parameters=distributions.ScalingParameters(offset=n_min_trials),
                    truncation_parameters=distributions.TruncationParameters(min=n_min_trials, max=n_min_trials + 50),
                )
            )
        ],
    )


operation_control = vr_task_logic.OperationControl(
    movable_spout_control=vr_task_logic.MovableSpoutControl(enabled=False),
    audio_control=vr_task_logic.AudioControl(duration=0.2, frequency=9999),
    odor_control=vr_task_logic.OdorControl(),
    position_control=vr_task_logic.PositionControl(
        frequency_filter_cutoff=5,
        velocity_threshold=VELOCITY_THRESHOLD,
    ),
)


task_logic = AindVrForagingTaskLogic(
    task_parameters=AindVrForagingTaskParameters(
        rng_seed=None,
        environment=vr_task_logic.BlockStructure(
            blocks=[
                make_block(p_rew=P_REWARD_BLOCK[i], p_replenish=P_BAIT_BLOCK[i], n_min_trials=100)
                for i in range(len(P_REWARD_BLOCK))
            ],
            sampling_mode="Sequential",
        ),
        operation_control=operation_control,
    ),
    stage_name="single_site_patch",
)


def main(path_seed: str = "./local/SingleSitePatch_{schema}.json"):
    example_task_logic = task_logic
    example_trainer_state = TrainerState(
        stage=Stage(name="example_stage", task=example_task_logic), curriculum=None, is_on_curriculum=False
    )
    os.makedirs(os.path.dirname(path_seed), exist_ok=True)
    models = [example_task_logic, example_trainer_state]

    for model in models:
        with open(path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
