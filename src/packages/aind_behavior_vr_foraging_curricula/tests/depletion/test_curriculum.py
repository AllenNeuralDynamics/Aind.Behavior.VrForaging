from typing import Any, cast

import pytest
from aind_behavior_curriculum import TrainerState
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.depletion import CURRICULUM, TRAINER
from aind_behavior_vr_foraging_curricula.depletion.curriculum import (
    st_s_stage_all_odors_rewarded_s_stage_graduation,
    st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0,
    st_s_stage_one_odor_w_depletion_day_0_s_stage_one_odor_w_depletion_day_1,
    st_s_stage_one_odor_w_depletion_day_1_s_stage_all_odors_rewarded,
    st_s_stage_one_odor_w_depletion_day_1_s_stage_one_odor_w_depletion_day_0,
)
from aind_behavior_vr_foraging_curricula.depletion.metrics import DepletionCurriculumMetrics
from aind_behavior_vr_foraging_curricula.depletion.policies import p_learn_to_run, p_learn_to_stop, p_stochastic_reward


@pytest.fixture
def init_state() -> TrainerState[Any]:
    return TRAINER.create_enrollment()


@pytest.fixture
def second_state() -> TrainerState[Any]:
    current_state = CURRICULUM.see_stages()[1]
    state = TRAINER.create_trainer_state(stage=current_state, active_policies=current_state.start_policies)
    return state


@pytest.fixture
def fail_metrics() -> DepletionCurriculumMetrics:
    return DepletionCurriculumMetrics(
        total_water_consumed=0,
        n_choices=0,
        n_reward_sites_traveled=5,
        n_patches_visited=0,
        n_patches_visited_per_patch={0: 0, 1: 0},
        last_stop_duration_offset_updater=0.3,
        last_reward_site_length=30,
        last_delay_duration=0.05,
    )


@pytest.fixture
def ok_metrics() -> DepletionCurriculumMetrics:
    return DepletionCurriculumMetrics(
        total_water_consumed=0.750,
        n_choices=151,
        n_reward_sites_traveled=300,
        n_patches_visited=50,
        n_patches_visited_per_patch={0: 25, 1: 25},
        last_stop_duration_offset_updater=0.5,
        last_reward_site_length=50,
        last_delay_duration=0.08,
    )


@pytest.mark.usefixtures("init_state", "ok_metrics", "fail_metrics")
class TestCurriculumProgression:
    def test_p_learn_to_stop(self, init_state: TrainerState):
        metrics = DepletionCurriculumMetrics(
            total_water_consumed=0.750,
            n_choices=151,
            n_reward_sites_traveled=300,
            n_patches_visited=50,
            n_patches_visited_per_patch={0: 25, 1: 25},
            last_stop_duration_offset_updater=0.5,
            last_reward_site_length=50,
            last_delay_duration=0.08,
        )

        assert init_state.stage is not None
        init_state.stage.set_start_policies(start_policies=[p_learn_to_run, p_learn_to_stop, p_stochastic_reward])

        init_settings = cast(AindVrForagingTaskLogic, init_state.stage.task)

        updated = p_learn_to_stop(metrics, init_settings.model_copy(deep=True))
        assert updated is not None
        assert updated.task_parameters.updaters is not None

    def test_p_learn_to_run(self, init_state: TrainerState):
        metrics = DepletionCurriculumMetrics(
            total_water_consumed=0.750,
            n_choices=151,
            n_reward_sites_traveled=300,
            n_patches_visited=50,
            n_patches_visited_per_patch={0: 25, 1: 25},
            last_stop_duration_offset_updater=0.5,
            last_reward_site_length=50,
            last_delay_duration=0.08,
        )

        assert init_state.stage is not None
        init_settings = cast(AindVrForagingTaskLogic, init_state.stage.task)

        updated = p_learn_to_run(metrics, init_settings.model_copy(deep=True))
        assert updated is not None
        assert updated.task_parameters.updaters is not None

    def test_st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0(
        self, fail_metrics: DepletionCurriculumMetrics, ok_metrics: DepletionCurriculumMetrics
    ):
        assert st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0(fail_metrics) is False
        assert st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0(ok_metrics) is True

    def test_st_s_stage_one_odor_w_depletion_day_0_s_stage_one_odor_w_depletion_day_1(
        self, fail_metrics: DepletionCurriculumMetrics, ok_metrics: DepletionCurriculumMetrics
    ):
        assert st_s_stage_one_odor_w_depletion_day_0_s_stage_one_odor_w_depletion_day_1(ok_metrics) is True
        assert st_s_stage_one_odor_w_depletion_day_0_s_stage_one_odor_w_depletion_day_1(fail_metrics) is False

    def test_st_s_stage_one_odor_w_depletion_day_1_s_stage_one_odor_w_depletion_day_0(
        self, fail_metrics: DepletionCurriculumMetrics, ok_metrics: DepletionCurriculumMetrics
    ):
        assert st_s_stage_one_odor_w_depletion_day_1_s_stage_one_odor_w_depletion_day_0(fail_metrics) is True
        assert st_s_stage_one_odor_w_depletion_day_1_s_stage_one_odor_w_depletion_day_0(ok_metrics) is False

    def test_st_s_stage_one_odor_w_depletion_day_1_s_stage_all_odors_rewarded(
        self, fail_metrics: DepletionCurriculumMetrics, ok_metrics: DepletionCurriculumMetrics
    ):
        assert st_s_stage_one_odor_w_depletion_day_1_s_stage_all_odors_rewarded(ok_metrics) is True
        assert st_s_stage_one_odor_w_depletion_day_1_s_stage_all_odors_rewarded(fail_metrics) is False

    def test_progression_pass(self, init_state: TrainerState, ok_metrics: DepletionCurriculumMetrics):
        proposal = TRAINER.evaluate(init_state, ok_metrics)
        assert proposal.is_on_curriculum is True
        assert proposal.curriculum == TRAINER.curriculum
        assert proposal.stage is not None
        assert proposal.stage.name == TRAINER.curriculum.see_stages()[1].name
        assert proposal.stage.task == TRAINER.curriculum.see_stages()[1].task

    def test_progression_fail(self, init_state: TrainerState, fail_metrics: DepletionCurriculumMetrics):
        proposal = TRAINER.evaluate(init_state, fail_metrics)
        assert proposal.is_on_curriculum is True
        assert proposal.curriculum == TRAINER.curriculum
        assert proposal.stage is not None
        assert init_state.stage is not None
        assert proposal.stage == init_state.stage

    # ---------- Edge cases ----------
    def test_missing_metric_fields(self):
        metrics = DepletionCurriculumMetrics(
            total_water_consumed=0,
            n_reward_sites_traveled=201,
            n_choices=151,
            n_patches_visited=0,
            n_patches_visited_per_patch={0: 0, 1: 0},
            last_stop_duration_offset_updater=0.5,
            last_reward_site_length=None,
            last_delay_duration=0.08,
        )
        assert st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0(metrics) is False

    def test_n_patches_visited_edge_cases(self):
        metrics = DepletionCurriculumMetrics(
            total_water_consumed=0.750,
            n_reward_sites_traveled=300,
            n_choices=200,
            n_patches_visited=30,
            n_patches_visited_per_patch={},  # missing keys
            last_stop_duration_offset_updater=0.5,
            last_reward_site_length=50,
            last_delay_duration=0.08,
        )
        assert not st_s_stage_all_odors_rewarded_s_stage_graduation(metrics)
        metrics.n_patches_visited_per_patch = {0: 25, 1: 0}
        assert not st_s_stage_all_odors_rewarded_s_stage_graduation(metrics)

    # ---------- Circular / policy transitions ----------
    def test_circular_stage_transitions(self):
        current_state = CURRICULUM.see_stages()[2]
        state = TRAINER.create_trainer_state(stage=current_state, active_policies=current_state.start_policies)
        metrics = DepletionCurriculumMetrics(
            total_water_consumed=0.750,
            n_reward_sites_traveled=300,
            n_choices=200,
            n_patches_visited=25,
            n_patches_visited_per_patch={0: 15, 1: 15},
            last_stop_duration_offset_updater=0.5,
            last_reward_site_length=50,
            last_delay_duration=0.08,
        )

        # Forward transition
        progress_state = TRAINER.evaluate(state, metrics)
        assert progress_state.stage is not None
        assert progress_state.stage.name != current_state.name

        # Reverse transition
        metrics.n_patches_visited = 15
        regress_state = TRAINER.evaluate(progress_state, metrics)
        assert regress_state.stage is not None
        assert regress_state.stage.name != current_state.name or regress_state.stage.name != progress_state.stage.name

    def test_trainer_evaluate_updates(self, init_state: TrainerState):
        metrics = DepletionCurriculumMetrics(
            total_water_consumed=0.750,
            n_reward_sites_traveled=300,
            n_choices=200,
            n_patches_visited=25,
            n_patches_visited_per_patch={0: 15, 1: 15},
            last_stop_duration_offset_updater=0.5,
            last_reward_site_length=50,
            last_delay_duration=0.08,
        )
        new_state = TRAINER.evaluate(init_state, metrics)
        assert isinstance(new_state, TrainerState)
        assert new_state.is_on_curriculum
        assert new_state.curriculum == TRAINER.curriculum
        assert new_state.active_policies is not None
        assert new_state.active_policies == []

    def test_stage_does_not_advance_wrong_metrics(self, init_state: TrainerState):
        metrics = DepletionCurriculumMetrics(
            total_water_consumed=0.75,
            n_reward_sites_traveled=500,
            n_choices=200,
            n_patches_visited=10,
            n_patches_visited_per_patch={0: 10},
            last_stop_duration_offset_updater=0.4,
            last_reward_site_length=40,
            last_delay_duration=0.08,
        )
        new_state = TRAINER.evaluate(init_state, metrics)
        assert new_state.stage is not None
        assert init_state.stage is not None
        assert new_state.stage.name == init_state.stage.name
