from aind_behavior_curriculum import MetricsProvider, Policy, Stage
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from . import helpers
from .metrics import metrics_from_dataset
from .policies import p_learn_to_run, p_learn_to_stop, p_stochastic_reward

# ============================================================
# Stage definition
# ============================================================


def make_s_stage_one_odor_no_depletion() -> Stage:
    _updaters = {
        task_logic.UpdaterTarget.STOP_DURATION_OFFSET: task_logic.NumericalUpdater(
            operation=task_logic.NumericalUpdaterOperation.OFFSET,
            parameters=task_logic.NumericalUpdaterParameters(initial_value=0, on_success=0.003, minimum=0, maximum=0.5),
        ),
        task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: task_logic.NumericalUpdater(
            operation=task_logic.NumericalUpdaterOperation.OFFSET,
            parameters=task_logic.NumericalUpdaterParameters(
                initial_value=0,
                on_success=0.0005,
                minimum=0,
                maximum=0.5,
            ),
        ),
        task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: task_logic.NumericalUpdater(
            operation=task_logic.NumericalUpdaterOperation.GAIN,
            parameters=task_logic.NumericalUpdaterParameters(
                initial_value=60,
                on_success=0.96,
                minimum=10,
                maximum=60,
            ),
        ),
    }
    return Stage(
        name="one_odor_no_depletion",
        task=AindVrForagingTaskLogic(
            stage_name="one_odor_no_depletion",
            task_parameters=AindVrForagingTaskParameters(
                updaters=_updaters,
                operation_control=helpers.make_default_operation_control(velocity_threshold=60),
                environment=task_logic.BlockStructure(
                    blocks=[
                        task_logic.Block(
                            environment_statistics=task_logic.EnvironmentStatistics(
                                patches=[
                                    task_logic.Patch(
                                        label="PatchZA",
                                        state_index=0,
                                        odor_specification=task_logic._OdorSpecification(index=0, concentration=1),
                                        reward_specification=task_logic.RewardSpecification(
                                            operant_logic=helpers.make_operant_logic(
                                                stop_duration=0.0, is_operant=False
                                            ),
                                            amount=task_logic.scalar_value(5),
                                            probability=task_logic.scalar_value(1),
                                            available=task_logic.scalar_value(9999),
                                            reward_function=[
                                                task_logic.PatchRewardFunction(
                                                    amount=task_logic.SetValueFunction(
                                                        value=task_logic.scalar_value(5)
                                                    ),
                                                    probability=task_logic.SetValueFunction(
                                                        value=task_logic.scalar_value(1)
                                                    ),
                                                    available=task_logic.SetValueFunction(
                                                        value=task_logic.scalar_value(value=9999)
                                                    ),
                                                    rule=task_logic.RewardFunctionRule.ON_CHOICE,
                                                )
                                            ],
                                        ),
                                        patch_virtual_sites_generator=helpers.make_patch_virtual_sites_generator(
                                            rewardsite=20,
                                            interpatch_min=25,
                                            interpatch_max=75,
                                            intersite_min=10,
                                            intersite_max=30,
                                        ),
                                    )
                                ]
                            ),
                            end_conditions=[],
                        )
                    ],
                ),
            ),
        ),
        start_policies=[Policy(x) for x in [p_learn_to_run, p_learn_to_stop, p_stochastic_reward]],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def _make_s_stage_one_odor_w_depletion_parameters() -> AindVrForagingTaskParameters:
    return AindVrForagingTaskParameters(
        updaters={
            task_logic.UpdaterTarget.STOP_DURATION_OFFSET: task_logic.NumericalUpdater(
                operation=task_logic.NumericalUpdaterOperation.OFFSET,
                parameters=task_logic.NumericalUpdaterParameters(
                    initial_value=0.4, on_success=0.005, minimum=0, maximum=0.5
                ),
            ),
            task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: task_logic.NumericalUpdater(
                operation=task_logic.NumericalUpdaterOperation.OFFSET,
                parameters=task_logic.NumericalUpdaterParameters(
                    initial_value=0.25,
                    on_success=0.003,
                    minimum=0,
                    maximum=0.5,
                ),
            ),
            task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: task_logic.NumericalUpdater(
                operation=task_logic.NumericalUpdaterOperation.GAIN,
                parameters=task_logic.NumericalUpdaterParameters(
                    initial_value=25,
                    on_success=0.96,
                    minimum=8,
                    maximum=60,
                ),
            ),
        },
        operation_control=helpers.make_default_operation_control(velocity_threshold=8),
        environment=task_logic.BlockStructure(
            blocks=[
                task_logic.Block(
                    environment_statistics=task_logic.EnvironmentStatistics(
                        patches=[
                            task_logic.Patch(
                                label="PatchZB",
                                state_index=0,
                                odor_specification=task_logic._OdorSpecification(index=0, concentration=1),
                                reward_specification=helpers.exponential_probability_reward_count(
                                    available_water=50, amount_drop=5, maximum_p=0.9, c=0.9752, stop_duration=0.0
                                ),
                                patch_virtual_sites_generator=helpers.make_patch_virtual_sites_generator(),
                            )
                        ]
                    ),
                    end_conditions=[],
                )
            ],
        ),
    )


def make_s_stage_one_odor_w_depletion_day_0() -> Stage:
    return Stage(
        name="one_odor_w_depletion_day_0",
        task=AindVrForagingTaskLogic(
            stage_name="one_odor_w_depletion_day_0",
            task_parameters=_make_s_stage_one_odor_w_depletion_parameters(),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_stage_one_odor_w_depletion_day_1() -> Stage:
    return Stage(
        name="one_odor_w_depletion_day_1",
        task=AindVrForagingTaskLogic(
            stage_name="one_odor_w_depletion_day_1",
            task_parameters=_make_s_stage_one_odor_w_depletion_parameters(),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
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
                            environment_statistics=task_logic.EnvironmentStatistics(
                                first_state_occupancy=[0.5, 0.5],
                                transition_matrix=[[0.5, 0.5], [0.5, 0.5]],
                                patches=[
                                    helpers.make_graduated_patch(
                                        label="odor_90", state_index=1, odor_index=1, max_reward_probability=0.9
                                    ),
                                    helpers.make_graduated_patch(
                                        label="odor_60", state_index=0, odor_index=2, max_reward_probability=0.6
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
                            environment_statistics=task_logic.EnvironmentStatistics(
                                first_state_occupancy=[0.45, 0.45, 0.1],
                                transition_matrix=[[0.45, 0.45, 0.1], [0.45, 0.45, 0.1], [0.45, 0.45, 0.1]],
                                patches=[
                                    helpers.make_graduated_patch(
                                        label="odor_0", state_index=2, odor_index=0, max_reward_probability=0.0
                                    ),
                                    helpers.make_graduated_patch(
                                        label="odor_90", state_index=1, odor_index=1, max_reward_probability=0.9
                                    ),
                                    helpers.make_graduated_patch(
                                        label="odor_60", state_index=0, odor_index=2, max_reward_probability=0.6
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
