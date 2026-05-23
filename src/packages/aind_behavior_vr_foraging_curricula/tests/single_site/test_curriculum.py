from typing import Any, cast

import pytest
from aind_behavior_curriculum import Curriculum, Trainer, TrainerState
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.single_site import CURRICULUM, TRAINER
from aind_behavior_vr_foraging_curricula.single_site.curriculum import (
    st_s_graduated_narrow_delay_to_s_graduated_stage,
    st_s_learn_to_choose_to_s_three_contrast,
    st_s_learn_to_stop_low_p_to_s_learn_to_choose,
    st_s_learn_to_stop_to_s_learn_to_choose,
    st_s_learn_to_stop_to_s_learn_to_stop_low_p,
    st_s_three_contrast_to_s_graduated_narrow_delay,
)
from aind_behavior_vr_foraging_curricula.single_site.metrics import (
    SingleSiteMetrics,
)
from aind_behavior_vr_foraging_curricula.single_site.policies import (
    p_learn_to_stop,
    p_seed_reward_delay,
    p_seed_stop_duration,
)
from aind_behavior_vr_foraging_curricula.single_site.stages import (
    make_s_learn_to_choose,
    make_s_three_contrast,
)


@pytest.fixture
def trainer() -> Trainer[Any]:
    return TRAINER


@pytest.fixture
def curriculum() -> Curriculum[AindVrForagingTaskLogic]:
    return CURRICULUM


@pytest.fixture
def init_state() -> TrainerState[Any]:
    return TRAINER.create_enrollment()


def _make_metrics(**overrides: Any) -> SingleSiteMetrics:
    defaults: dict[str, Any] = dict(
        total_water_consumed=0.0,
        n_patches_visited=0,
        n_patches_seen=0,
        last_stop_threshold_updater=None,
        last_stop_duration_offset_updater=None,
        last_reward_delay_offset_updater=None,
    )
    defaults.update(overrides)
    return SingleSiteMetrics(**defaults)


# ============================================================
# Stage-transition predicates
# ============================================================


class TestLearnToStopToLearnToChoose:
    def test_pass_when_all_thresholds_met(self):
        metrics = _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
            last_stop_threshold_updater=8,
            last_stop_duration_offset_updater=1.0,
        )
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is True

    def test_fail_when_offset_below_max(self):
        metrics = _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
            last_stop_threshold_updater=8,
            last_stop_duration_offset_updater=0.9,
        )
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False

    def test_fail_when_threshold_too_high(self):
        metrics = _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
            last_stop_threshold_updater=9,
            last_stop_duration_offset_updater=1.0,
        )
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False

    def test_fail_when_insufficient_visits(self):
        metrics = _make_metrics(
            n_patches_visited=100,
            n_patches_seen=300,
            last_stop_threshold_updater=8,
            last_stop_duration_offset_updater=1.0,
        )
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False

    def test_fail_when_metrics_none(self):
        metrics = _make_metrics(n_patches_visited=150, n_patches_seen=300)
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False


class TestLearnToStopToLearnToStopLowP:
    def test_always_true(self):
        # Unconditional fallback: any metrics shape should fire.
        assert st_s_learn_to_stop_to_s_learn_to_stop_low_p(_make_metrics()) is True
        assert (
            st_s_learn_to_stop_to_s_learn_to_stop_low_p(
                _make_metrics(
                    n_patches_visited=999,
                    n_patches_seen=999,
                    last_stop_threshold_updater=8,
                    last_stop_duration_offset_updater=1.0,
                )
            )
            is True
        )


class TestLearnToStopLowPToLearnToChoose:
    def _ok(self) -> SingleSiteMetrics:
        return _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
            last_stop_threshold_updater=8,
            last_stop_duration_offset_updater=1.0,
        )

    def test_pass(self):
        assert st_s_learn_to_stop_low_p_to_s_learn_to_choose(self._ok()) is True

    def test_fail_when_offset_below_max(self):
        metrics = self._ok().model_copy(update=dict(last_stop_duration_offset_updater=0.9))
        assert st_s_learn_to_stop_low_p_to_s_learn_to_choose(metrics) is False


class TestLearnToChooseToThreeContrast:
    def _ok(self) -> SingleSiteMetrics:
        return _make_metrics(
            n_patches_visited=100,
            n_patches_seen=200,
            last_reward_delay_offset_updater=0.3,
        )

    def test_pass(self):
        assert st_s_learn_to_choose_to_s_three_contrast(self._ok()) is True

    def test_fail_when_visit_ratio_too_high(self):
        # 190/200 = 0.95 > 0.7 → mouse not discriminating
        metrics = self._ok().model_copy(update=dict(n_patches_visited=190))
        assert st_s_learn_to_choose_to_s_three_contrast(metrics) is False

    def test_fail_when_delay_not_saturated(self):
        metrics = self._ok().model_copy(update=dict(last_reward_delay_offset_updater=0.1))
        assert st_s_learn_to_choose_to_s_three_contrast(metrics) is False

    def test_fail_when_delay_metric_missing(self):
        metrics = self._ok().model_copy(update=dict(last_reward_delay_offset_updater=None))
        assert st_s_learn_to_choose_to_s_three_contrast(metrics) is False


class TestThreeContrastToGraduatedNarrowDelay:
    def _ok(self) -> SingleSiteMetrics:
        return _make_metrics(
            n_patches_visited=120,
            n_patches_seen=250,
            last_reward_delay_offset_updater=1.4,
            last_stop_duration_offset_updater=-0.45,
        )

    def test_pass(self):
        assert st_s_three_contrast_to_s_graduated_narrow_delay(self._ok()) is True

    def test_fail_when_visit_ratio_too_low(self):
        # 60/250 = 0.24 < 0.3 → mouse overly skipping
        metrics = self._ok().model_copy(update=dict(n_patches_visited=60))
        assert st_s_three_contrast_to_s_graduated_narrow_delay(metrics) is False

    def test_fail_when_visit_ratio_too_high(self):
        metrics = self._ok().model_copy(update=dict(n_patches_visited=240))
        assert st_s_three_contrast_to_s_graduated_narrow_delay(metrics) is False

    def test_fail_when_delay_not_saturated(self):
        metrics = self._ok().model_copy(update=dict(last_reward_delay_offset_updater=1.0))
        assert st_s_three_contrast_to_s_graduated_narrow_delay(metrics) is False

    def test_fail_when_stop_not_saturated(self):
        # stop offset still close to 0 → coupled ramp hasn't kicked in
        metrics = self._ok().model_copy(update=dict(last_stop_duration_offset_updater=-0.2))
        assert st_s_three_contrast_to_s_graduated_narrow_delay(metrics) is False

    def test_fail_when_stop_metric_missing(self):
        metrics = self._ok().model_copy(update=dict(last_stop_duration_offset_updater=None))
        assert st_s_three_contrast_to_s_graduated_narrow_delay(metrics) is False


class TestGraduatedNarrowDelayToGraduatedStage:
    def _ok(self) -> SingleSiteMetrics:
        return _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
        )

    def test_pass(self):
        assert st_s_graduated_narrow_delay_to_s_graduated_stage(self._ok()) is True

    def test_fail_when_insufficient_seen(self):
        metrics = self._ok().model_copy(update=dict(n_patches_seen=200))
        assert st_s_graduated_narrow_delay_to_s_graduated_stage(metrics) is False

    def test_fail_when_visit_ratio_too_low(self):
        metrics = self._ok().model_copy(update=dict(n_patches_visited=60))
        assert st_s_graduated_narrow_delay_to_s_graduated_stage(metrics) is False


# ============================================================
# Policies
# ============================================================


class TestPLearnToStop:
    def test_seeds_updater_initial_values_from_metrics(self, init_state: TrainerState):
        metrics = _make_metrics(
            n_patches_visited=200,
            n_patches_seen=300,
            last_stop_threshold_updater=10.0,
            last_stop_duration_offset_updater=0.5,
        )
        assert init_state.stage is not None
        task = cast(AindVrForagingTaskLogic, init_state.stage.task).model_copy(deep=True)

        updated = p_learn_to_stop(metrics, task)
        vel = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters
        dur = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters

        assert vel.initial_value == metrics.last_stop_threshold_updater * 1.2
        assert dur.initial_value == metrics.last_stop_duration_offset_updater * 0.8


class TestPSeedRewardDelay:
    def _learn_to_choose_task(self) -> AindVrForagingTaskLogic:
        # Stage 2's task — has REWARD_DELAY_OFFSET updater with max=0.3
        return cast(AindVrForagingTaskLogic, make_s_learn_to_choose().task).model_copy(deep=True)

    def _three_contrast_task(self) -> AindVrForagingTaskLogic:
        # Stage 3's task — has REWARD_DELAY_OFFSET updater with max=1.5
        return cast(AindVrForagingTaskLogic, make_s_three_contrast().task).model_copy(deep=True)

    def test_seeds_from_prior_offset_with_easing(self):
        metrics = _make_metrics(last_reward_delay_offset_updater=0.3)
        task = self._three_contrast_task()  # max=1.5, so 0.3*0.8=0.24 fits
        updated = p_seed_reward_delay(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters
        assert params.initial_value == pytest.approx(0.3 * 0.8)

    def test_clamps_to_max(self):
        # Prior session 1.5 (saturated S3) -> 1.2 after easing -> clamped to S2's max (0.3)
        metrics = _make_metrics(last_reward_delay_offset_updater=1.5)
        task = self._learn_to_choose_task()  # max=0.3
        updated = p_seed_reward_delay(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters
        assert params.initial_value == 0.3

    def test_no_op_when_metric_is_none(self):
        metrics = _make_metrics(last_reward_delay_offset_updater=None)
        task = self._learn_to_choose_task()
        original = task.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters.initial_value
        updated = p_seed_reward_delay(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters
        assert params.initial_value == original  # untouched default


class TestPSeedStopDuration:
    def _three_contrast_task(self) -> AindVrForagingTaskLogic:
        # Stage 3's task — has STOP_DURATION_OFFSET updater with min=-0.5, max=0
        return cast(AindVrForagingTaskLogic, make_s_three_contrast().task).model_copy(deep=True)

    def test_seeds_from_prior_offset_with_easing(self):
        # Prior end at -0.4 -> ease toward 0 by ×0.8 -> -0.32 (inside [-0.5, 0])
        metrics = _make_metrics(last_stop_duration_offset_updater=-0.4)
        task = self._three_contrast_task()
        updated = p_seed_stop_duration(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters
        assert params.initial_value == pytest.approx(-0.4 * 0.8)

    def test_clamps_to_min(self):
        # An extreme negative value should clamp to -0.5
        metrics = _make_metrics(last_stop_duration_offset_updater=-2.0)
        task = self._three_contrast_task()
        updated = p_seed_stop_duration(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters
        assert params.initial_value == -0.5

    def test_no_op_when_metric_is_none(self):
        metrics = _make_metrics(last_stop_duration_offset_updater=None)
        task = self._three_contrast_task()
        original = task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.initial_value
        updated = p_seed_stop_duration(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters
        assert params.initial_value == original


# ============================================================
# Full progression
# ============================================================


class TestProgression:
    def test_advance_each_stage(self, trainer: Trainer, init_state: TrainerState):
        """Walk through the full curriculum, providing metrics that fire each
        transition in turn. Confirms the graph is wired in the expected order."""
        stages = trainer.curriculum.see_stages()
        # Insertion order: S1, S2, S1.5 (added between S1's two transitions and S2's own).
        expected_stage_names = {
            "learn_to_stop",
            "learn_to_stop_low_p",
            "learn_to_choose",
            "three_contrast",
            "graduated_narrow_delay",
            "graduated_stage",
        }
        assert {s.name for s in stages} == expected_stage_names

        state = init_state
        assert state.stage is not None and state.stage.name == "learn_to_stop"

        # 1 -> 2
        metrics = _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
            last_stop_threshold_updater=8,
            last_stop_duration_offset_updater=1.0,
        )
        state = trainer.evaluate(state, metrics)
        assert state.stage is not None and state.stage.name == "learn_to_choose"

        # 2 -> 3
        metrics = _make_metrics(
            n_patches_visited=100,
            n_patches_seen=200,
            last_reward_delay_offset_updater=0.3,
        )
        state = trainer.evaluate(state, metrics)
        assert state.stage is not None and state.stage.name == "three_contrast"

        # 3 -> 4
        metrics = _make_metrics(
            n_patches_visited=120,
            n_patches_seen=250,
            last_reward_delay_offset_updater=1.4,
            last_stop_duration_offset_updater=-0.45,
        )
        state = trainer.evaluate(state, metrics)
        assert state.stage is not None and state.stage.name == "graduated_narrow_delay"

        # 4 -> 5
        metrics = _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
        )
        state = trainer.evaluate(state, metrics)
        assert state.stage is not None and state.stage.name == "graduated_stage"

    def test_no_advance_on_insufficient_metrics(self, trainer: Trainer, init_state: TrainerState):
        # Sticky animal: S1 saturation gates miss -> the unconditional fallback fires
        # and lands them in learn_to_stop_low_p, not stuck in S1.
        metrics = _make_metrics(
            n_patches_visited=0,
            n_patches_seen=0,
            last_stop_threshold_updater=60,
            last_stop_duration_offset_updater=0.0,
        )
        state = trainer.evaluate(init_state, metrics)
        assert state.stage is not None and state.stage.name == "learn_to_stop_low_p"

    def test_sticky_path_via_low_p(self, trainer: Trainer, init_state: TrainerState):
        # Path 2: animal misses S1 gates -> falls to S1.5 -> graduates from S1.5.
        sticky = _make_metrics(
            n_patches_visited=10,
            n_patches_seen=50,
            last_stop_threshold_updater=40,
            last_stop_duration_offset_updater=0.3,
        )
        state = trainer.evaluate(init_state, sticky)
        assert state.stage is not None and state.stage.name == "learn_to_stop_low_p"

        # Next session in S1.5 saturates the gates -> graduate to S2.
        saturated = _make_metrics(
            n_patches_visited=150,
            n_patches_seen=300,
            last_stop_threshold_updater=8,
            last_stop_duration_offset_updater=1.0,
        )
        state = trainer.evaluate(state, saturated)
        assert state.stage is not None and state.stage.name == "learn_to_choose"
