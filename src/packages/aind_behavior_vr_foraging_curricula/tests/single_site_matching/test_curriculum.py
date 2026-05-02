from typing import Any, cast

import pytest
from aind_behavior_curriculum import Curriculum, Trainer, TrainerState
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.single_site_matching import CURRICULUM, TRAINER
from aind_behavior_vr_foraging_curricula.single_site_matching.curriculum import (
    st_s_learn_to_stop_to_s_graduated_stage,
)
from aind_behavior_vr_foraging_curricula.single_site_matching.metrics import SingleSiteMatchingMetrics
from aind_behavior_vr_foraging_curricula.single_site_matching.policies import p_learn_to_stop


@pytest.fixture
def trainer() -> Trainer[Any]:
    return TRAINER


@pytest.fixture
def curriculum() -> Curriculum[AindVrForagingTaskLogic]:
    return CURRICULUM


@pytest.fixture
def init_state() -> TrainerState[Any]:
    return TRAINER.create_enrollment()


@pytest.fixture
def fail_metrics() -> SingleSiteMatchingMetrics:
    return SingleSiteMatchingMetrics(
        total_water_consumed=0.0,
        n_patches_visited=0,
        n_patches_seen=0,
        last_stop_threshold_updater=0.5,
        last_stop_duration_offset_updater=0.5,
    )


@pytest.fixture
def ok_metrics() -> SingleSiteMatchingMetrics:
    return SingleSiteMatchingMetrics(
        total_water_consumed=1.0,
        n_patches_visited=150,
        n_patches_seen=300,
        last_stop_threshold_updater=8,
        last_stop_duration_offset_updater=0.6,
    )


class TestCurriculumProgression:
    def test_p_learn_to_stop(self, init_state: TrainerState):
        metrics = SingleSiteMatchingMetrics(
            total_water_consumed=1.0,
            n_patches_visited=200,
            n_patches_seen=300,
            last_stop_threshold_updater=10.0,
            last_stop_duration_offset_updater=0.5,
        )

        assert init_state.stage is not None
        init_settings = cast(AindVrForagingTaskLogic, init_state.stage.task)

        updated = p_learn_to_stop(metrics, init_settings.model_copy(deep=True))
        assert updated is not None
        assert updated.task_parameters.updaters is not None
        assert (
            updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.initial_value
            == metrics.last_stop_threshold_updater * 1.2
        )
        assert (
            updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.initial_value
            == metrics.last_stop_duration_offset_updater * 0.8
        )

    def test_st_s_learn_to_stop_to_s_graduated_stage(self, ok_metrics: SingleSiteMatchingMetrics):
        assert st_s_learn_to_stop_to_s_graduated_stage(ok_metrics) is True

    def test_st_s_learn_to_stop_to_s_graduated_stage_fail(self, fail_metrics: SingleSiteMatchingMetrics):
        assert st_s_learn_to_stop_to_s_graduated_stage(fail_metrics) is False

    def test_progression_pass(self, trainer: Trainer, init_state: TrainerState, ok_metrics: SingleSiteMatchingMetrics):
        proposal = trainer.evaluate(init_state, ok_metrics)
        assert proposal.is_on_curriculum is True
        assert proposal.curriculum == trainer.curriculum
        assert proposal.stage is not None
        assert proposal.stage.name == trainer.curriculum.see_stages()[1].name
        assert proposal.stage.task == trainer.curriculum.see_stages()[1].task

    def test_progression_fail(
        self, trainer: Trainer, init_state: TrainerState, fail_metrics: SingleSiteMatchingMetrics
    ):
        proposal = trainer.evaluate(init_state, fail_metrics)
        assert proposal.is_on_curriculum is True
        assert proposal.curriculum == trainer.curriculum
        assert proposal.stage is not None
        assert proposal.stage.name == trainer.curriculum.see_stages()[0].name
        # Cannot evaluate the task as it is subject to change by policies
