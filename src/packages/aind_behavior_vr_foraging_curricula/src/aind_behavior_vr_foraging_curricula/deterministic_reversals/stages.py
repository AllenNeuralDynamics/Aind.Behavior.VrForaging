from typing import Literal

import numpy as np
from aind_behavior_curriculum import MetricsProvider, Stage
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from ..depletion import helpers
from ..depletion.metrics import metrics_from_dataset


# ============================================================
# Stage definition
# ============================================================
def deterministic_curves(
    amount_drop=5.0,
    option: str = "single",
):
    if option == "delayed":
        lut_values = [0.5, 1, 1, 1, 0]
        probability = task_logic.LookupTableFunction(
            lut_keys=list(np.arange(len(lut_values)) + 1), lut_values=lut_values
        )
        reward_function_prob = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        )
        reward_available = 100
        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(1)),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(reward_available)),
        )
        return [reward_function_prob, reset_function]

    elif option == "single":
        lut_values = [1, 0]
        probability = task_logic.LookupTableFunction(lut_keys=[1, 2], lut_values=lut_values)

        reward_function = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        )
        reward_available = 100

        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(1)),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(reward_available)),
        )
        return [reward_function, reset_function]

    elif option == "null":
        probability = task_logic.SetValueFunction(value=task_logic.scalar_value(0))

        reward_function = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE,
        )

        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(0)),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(0)),
        )
        return [reward_function, reset_function]


def make_patch(
    label: str,
    state_index: int,
    odor_index: int,
    patch_type: Literal["single", "delayed", "null"],
    reward_amount: float = 5.0,
    first_p: float = 0.5,
    reward_available: float = 9999,
    stop_duration: float = 0.5,
    delay_mean: float = 0.5,
):

    agent = task_logic.RewardSpecification(
        operant_logic=helpers.make_operant_logic(stop_duration=stop_duration, is_operant=False),
        delay=helpers.make_exponential_distribution(rate=1 / delay_mean, minimum=0.0, maximum=1.0),
        amount=task_logic.scalar_value(value=reward_amount),
        probability=task_logic.scalar_value(first_p),
        available=task_logic.scalar_value(reward_available),
        reward_function=deterministic_curves(amount_drop=reward_amount, option=patch_type),
    )

    return task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=odor_index,
        reward_specification=agent,
        patch_virtual_sites_generator=helpers.make_patch_virtual_sites_generator(
            rewardsite=50,
            interpatch_min=100,
            interpatch_max=250,
            intersite_min=20,
            intersite_max=80,
        ),
    )


def make_s_stage_all_odors_rewarded() -> Stage:
    return Stage(
        name="all_odors_rewarded",
        task=AindVrForagingTaskLogic(
            stage_name="all_odors_rewarded",
            task_parameters=AindVrForagingTaskParameters(
                operation_control=helpers.make_default_operation_control(velocity_threshold=8),
                environment=task_logic.BlockStructure(
                    blocks=[
                        task_logic.Block(
                            environment=task_logic.MarkovEnvironment(
                                first_state_occupancy=[0.5, 0.5],
                                transition_matrix=[[0.5, 0.5], [0.5, 0.5]],
                                patches=[
                                    make_patch(
                                        label="patch_single",
                                        state_index=0,
                                        odor_index=[0, 0, 1],
                                        patch_type="single",
                                        reward_amount=5.0,
                                        first_p=1,
                                        reward_available=100,
                                    ),
                                    make_patch(
                                        label="patch_delayed",
                                        state_index=1,
                                        odor_index=[0, 1, 0],
                                        patch_type="delayed",
                                        reward_amount=5.0,
                                        first_p=0.5,
                                        reward_available=100,
                                    ),
                                ],
                            ),
                            end_conditions=[],
                        )
                    ],
                ),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_stage_graduation() -> Stage:
    return Stage(
        name="graduation",
        task=AindVrForagingTaskLogic(
            stage_name="graduation",
            task_parameters=AindVrForagingTaskParameters(
                operation_control=helpers.make_default_operation_control(velocity_threshold=8),
                environment=task_logic.BlockStructure(
                    blocks=[
                        task_logic.Block(
                            environment=task_logic.MarkovEnvironment(
                                first_state_occupancy=[1 / 3, 1 / 3, 1 / 3],
                                transition_matrix=[[1 / 3, 1 / 3, 1 / 3], [1 / 3, 1 / 3, 1 / 3], [1 / 3, 1 / 3, 1 / 3]],
                                patches=[
                                    make_patch(
                                        label="patch_null",
                                        state_index=0,
                                        odor_index=[1, 0, 0],
                                        patch_type="null",
                                        reward_amount=0.0,
                                        first_p=0,
                                        reward_available=0,
                                    ),
                                    make_patch(
                                        label="patch_delayed",
                                        state_index=1,
                                        odor_index=[0, 1, 0],
                                        patch_type="delayed",
                                        reward_amount=5.0,
                                        first_p=0.5,
                                        reward_available=100,
                                    ),
                                    make_patch(
                                        label="patch_single",
                                        state_index=2,
                                        odor_index=[0, 0, 1],
                                        patch_type="single",
                                        reward_amount=5.0,
                                        first_p=1,
                                        reward_available=100,
                                    ),
                                ],
                            ),
                            end_conditions=[],
                        )
                    ],
                ),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )
