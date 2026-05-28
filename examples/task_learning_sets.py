import os
import random

import aind_behavior_services.task.distributions as distributions
import aind_behavior_vr_foraging.task_logic as vr_task_logic
from aind_behavior_curriculum import Stage, TrainerState
from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)

MINIMUM_INTERPATCH_LENGTH = 50
MEAN_INTERPATCH_LENGTH = 120
MAXIMUM_INTERPATCH_LENGTH = 450
INTERSITE_LENGTH = 50
REWARDSITE_LENGTH = 50
REWARD_AMOUNT = 7
VELOCITY_THRESHOLD = 8  # cm/s

ODOR_COUNT = 7


def odor_concentration_from_index(
    odor_index: int, concentration: float = 1.0
) -> vr_task_logic.OdorMixture:
    """Helper function to create an odor concentration vector from an index and concentration value."""
    arr = [0.0 for x in range(ODOR_COUNT)]
    arr[odor_index] = concentration
    return arr


def make_patch(
    is_rewarded: bool,
    odor_index: int,
):

    return vr_task_logic.Patch(
        label=f"{odor_index}_Rewarded" if is_rewarded else f"{odor_index}_NonRewarded",
        state_index=odor_index + ODOR_COUNT * int(is_rewarded),
        odor_specification=odor_concentration_from_index(odor_index, 1.0),
        patch_terminators=[
            vr_task_logic.PatchTerminatorOnRewardSite(
                count=vr_task_logic.scalar_value(1)
            ),
        ],
        reward_specification=vr_task_logic.RewardSpecification(
            amount=vr_task_logic.scalar_value(REWARD_AMOUNT),
            probability=vr_task_logic.scalar_value(1.0 if is_rewarded else 0.0),
            delay=vr_task_logic.scalar_value(0.5),
            operant_logic=vr_task_logic.OperantLogic(
                is_operant=False,
                stop_duration=2.0,
                time_to_collect_reward=100000,
                grace_distance_threshold=10,
            ),
        ),
        patch_virtual_sites_generator=vr_task_logic.PatchVirtualSitesGenerator(
            inter_patch=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=1),
                label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
                length_distribution=distributions.ExponentialDistribution(
                    distribution_parameters=distributions.ExponentialDistributionParameters(
                        rate=1 / MEAN_INTERPATCH_LENGTH
                    ),
                    scaling_parameters=distributions.ScalingParameters(
                        offset=MINIMUM_INTERPATCH_LENGTH
                    ),
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


def get_odor_sequence(total_trials: int, n: int) -> list[tuple[int, int]]:
    import random
    from collections import deque

    ODORS = list(range(ODOR_COUNT))

    if len(ODORS) < 2 * n + 2:
        raise ValueError(
            "Not enough odors to satisfy the constraints with the given n."
        )

    patches = []
    history = deque(maxlen=n)

    for _ in range(total_trials):
        forbidden = set()
        for pair in history:
            forbidden.update(pair)

        available = [o for o in ODORS if o not in forbidden]

        pos = random.choice(available)
        available.remove(pos)
        neg = random.choice(available)

        patches.append((neg, pos))
        history.append((neg, pos))

    return patches




def make_block(
    n_sites_each: int = 5,
    n_pairs: int = 500,
) -> vr_task_logic.Block:

    odor_sequence = get_odor_sequence(total_trials=n_pairs, n=1)
    trial_sequence: list[int] = []
    for pair in odor_sequence:
        this_block = [pair[0], pair[1] + ODOR_COUNT] * n_sites_each
        random.shuffle(this_block)
        trial_sequence.extend(this_block)

    return vr_task_logic.Block(
        environment=vr_task_logic.SequenceEnvironment(
            patches=[
                make_patch(is_rewarded=False, odor_index=i) for i in range(ODOR_COUNT)
            ]
            + [make_patch(is_rewarded=True, odor_index=i) for i in range(ODOR_COUNT)],
            sampling_mode="Ordered",
            patch_indices=trial_sequence,
        ),
        end_conditions=[
            vr_task_logic.BlockEndConditionPatchCount(
                value=vr_task_logic.scalar_value(n_sites_each * 2)
            )
        ],
    )


operation_control = vr_task_logic.OperationControl(
    position_control=vr_task_logic.PositionControl(
        frequency_filter_cutoff=5,
        velocity_threshold=VELOCITY_THRESHOLD,
    ),
)

task_logic = AindVrForagingTaskLogic(
    task_parameters=AindVrForagingTaskParameters(
        rng_seed=None,
        environment=vr_task_logic.BlockStructure(
            blocks=[make_block(n_sites_each=5, n_pairs=100)],
        ),
        operation_control=operation_control,
    ),
    stage_name="LearningSets",
)


def main(path_seed: str = "./local/LearningSets_{schema}.json"):
    example_task_logic = task_logic
    example_trainer_state = TrainerState(
        stage=Stage(name="example_stage", task=example_task_logic),
        curriculum=None,
        is_on_curriculum=False,
    )
    os.makedirs(os.path.dirname(path_seed), exist_ok=True)
    models = [example_task_logic, example_trainer_state]

    for model in models:
        with open(
            path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8"
        ) as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
