from typing import Any, cast

import pytest
from aind_behavior_curriculum import Curriculum, Trainer, TrainerState
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.single_site import CURRICULUM, TRAINER
from aind_behavior_vr_foraging_curricula.single_site.curriculum import (
    st_s_learn_to_choose_to_s_probability_grid_short_delay,
    st_s_learn_to_stop_to_s_learn_to_choose,
    st_s_probability_grid_short_delay_to_s_probability_grid_long_delay,
)
from aind_behavior_vr_foraging_curricula.single_site.metrics import SingleSiteMetrics
from aind_behavior_vr_foraging_curricula.single_site.policies import (
    GATED_REWARD_PROBABILITY,
    WATER_GATE_ML,
    p_learn_to_run,
    p_learn_to_stop,
    p_reward_water_gate,
    p_seed_reward_delay,
)
from aind_behavior_vr_foraging_curricula.single_site.stages import (
    make_s_learn_to_choose,
    make_s_learn_to_stop,
    make_s_probability_grid_short_delay,
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
    def _make_passing_metrics(self) -> SingleSiteMetrics:
        return _make_metrics(n_patches_visited=150, n_patches_seen=300, last_stop_threshold_updater=8)

    def test_pass_when_velocity_floored_and_enough_stops(self):
        assert st_s_learn_to_stop_to_s_learn_to_choose(self._make_passing_metrics()) is True

    def test_fail_when_threshold_too_high(self):
        metrics = self._make_passing_metrics().model_copy(update=dict(last_stop_threshold_updater=9))
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False

    def test_fail_when_insufficient_visits(self):
        metrics = self._make_passing_metrics().model_copy(update=dict(n_patches_visited=100))
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False

    def test_fail_when_insufficient_seen(self):
        metrics = self._make_passing_metrics().model_copy(update=dict(n_patches_seen=200))
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False

    def test_fail_when_threshold_metric_none(self):
        metrics = _make_metrics(n_patches_visited=150, n_patches_seen=300)
        assert st_s_learn_to_stop_to_s_learn_to_choose(metrics) is False


class TestLearnToChooseToProbabilityGridShort:
    def _make_passing_metrics(self) -> SingleSiteMetrics:
        return _make_metrics(n_patches_visited=100, n_patches_seen=200, last_reward_delay_offset_updater=0.3)

    def test_pass(self):
        assert st_s_learn_to_choose_to_s_probability_grid_short_delay(self._make_passing_metrics()) is True

    def test_fail_when_visit_ratio_too_high(self):
        # 190/200 = 0.95 > 0.7 -> not discriminating
        metrics = self._make_passing_metrics().model_copy(update=dict(n_patches_visited=190))
        assert st_s_learn_to_choose_to_s_probability_grid_short_delay(metrics) is False

    def test_fail_when_delay_not_saturated(self):
        metrics = self._make_passing_metrics().model_copy(update=dict(last_reward_delay_offset_updater=0.1))
        assert st_s_learn_to_choose_to_s_probability_grid_short_delay(metrics) is False

    def test_fail_when_delay_metric_missing(self):
        metrics = self._make_passing_metrics().model_copy(update=dict(last_reward_delay_offset_updater=None))
        assert st_s_learn_to_choose_to_s_probability_grid_short_delay(metrics) is False


class TestProbabilityGridShortToLong:
    def _make_passing_metrics(self) -> SingleSiteMetrics:
        return _make_metrics(n_patches_visited=150, n_patches_seen=300, last_reward_delay_offset_updater=1.4)

    def test_pass(self):
        assert st_s_probability_grid_short_delay_to_s_probability_grid_long_delay(self._make_passing_metrics()) is True

    def test_fail_when_insufficient_seen(self):
        metrics = self._make_passing_metrics().model_copy(update=dict(n_patches_seen=200))
        assert st_s_probability_grid_short_delay_to_s_probability_grid_long_delay(metrics) is False

    def test_fail_when_visit_ratio_too_low(self):
        # 60/300 = 0.2 < 0.3 -> overly skipping
        metrics = self._make_passing_metrics().model_copy(update=dict(n_patches_visited=60))
        assert st_s_probability_grid_short_delay_to_s_probability_grid_long_delay(metrics) is False

    def test_fail_when_delay_not_grown(self):
        metrics = self._make_passing_metrics().model_copy(update=dict(last_reward_delay_offset_updater=1.0))
        assert st_s_probability_grid_short_delay_to_s_probability_grid_long_delay(metrics) is False


# ============================================================
# Policies
# ============================================================


class TestPLearnToStop:
    def test_seeds_velocity_initial_value(self, init_state: TrainerState):
        metrics = _make_metrics(n_patches_visited=200, n_patches_seen=300, last_stop_threshold_updater=10.0)
        assert init_state.stage is not None
        task = cast(AindVrForagingTaskLogic, init_state.stage.task).model_copy(deep=True)
        updated = p_learn_to_stop(metrics, task)
        vel = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters
        assert vel.initial_value == pytest.approx(10.0 * 1.2)

    def test_clamps_to_max(self, init_state: TrainerState):
        metrics = _make_metrics(last_stop_threshold_updater=60.0)
        assert init_state.stage is not None
        task = cast(AindVrForagingTaskLogic, init_state.stage.task).model_copy(deep=True)
        updated = p_learn_to_stop(metrics, task)
        vel = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters
        assert vel.initial_value == 60.0  # 60*1.2 clamped to max 60

    def test_no_op_when_metric_none(self, init_state: TrainerState):
        assert init_state.stage is not None
        task = cast(AindVrForagingTaskLogic, init_state.stage.task).model_copy(deep=True)
        original = task.task_parameters.updaters[
            task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD
        ].parameters.initial_value
        updated = p_learn_to_stop(_make_metrics(), task)
        vel = updated.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters
        assert vel.initial_value == original


class TestPRewardWaterGate:
    def _patches_probability(self, task: AindVrForagingTaskLogic) -> float:
        patch = task.task_parameters.environment.blocks[0].environment_statistics.patches[0]
        return patch.reward_specification.probability.distribution_parameters.value

    def test_drops_when_water_at_or_above_gate(self):
        task = cast(AindVrForagingTaskLogic, make_s_learn_to_stop().task).model_copy(deep=True)
        updated = p_reward_water_gate(_make_metrics(total_water_consumed=WATER_GATE_ML), task)
        assert self._patches_probability(updated) == pytest.approx(GATED_REWARD_PROBABILITY)

    def test_keeps_full_when_struggling(self):
        task = cast(AindVrForagingTaskLogic, make_s_learn_to_stop().task).model_copy(deep=True)
        updated = p_reward_water_gate(_make_metrics(total_water_consumed=WATER_GATE_ML - 0.1), task)
        assert self._patches_probability(updated) == pytest.approx(1.0)


class TestPLearnToRun:
    def _reward_site_len(self, task: AindVrForagingTaskLogic) -> float:
        gen = task.task_parameters.environment.blocks[0].environment_statistics.patches[0].patch_virtual_sites_generator
        return gen.reward_site.length_distribution.distribution_parameters.value

    def test_stays_compressed_on_first_session(self):
        task = cast(AindVrForagingTaskLogic, make_s_learn_to_stop().task).model_copy(deep=True)
        compressed = self._reward_site_len(task)
        updated = p_learn_to_run(_make_metrics(n_patches_seen=0), task)
        assert self._reward_site_len(updated) == pytest.approx(compressed)

    def test_eases_to_full_after_enough_locomotion(self):
        task = cast(AindVrForagingTaskLogic, make_s_learn_to_stop().task).model_copy(deep=True)
        updated = p_learn_to_run(_make_metrics(n_patches_seen=1000), task)
        # full reward-site length is 40 (LEARN_TO_STOP_GEOMETRY_FULL)
        assert self._reward_site_len(updated) == pytest.approx(40.0)


class TestPSeedRewardDelay:
    def _grid_short_task(self) -> AindVrForagingTaskLogic:
        # probability_grid_short has REWARD_DELAY_OFFSET updater with max=1.5
        return cast(AindVrForagingTaskLogic, make_s_probability_grid_short_delay().task).model_copy(deep=True)

    def _learn_to_choose_task(self) -> AindVrForagingTaskLogic:
        # learn_to_choose has REWARD_DELAY_OFFSET updater with max=0.3
        return cast(AindVrForagingTaskLogic, make_s_learn_to_choose().task).model_copy(deep=True)

    def test_seeds_from_prior_offset_with_easing(self):
        metrics = _make_metrics(last_reward_delay_offset_updater=1.0)
        task = self._grid_short_task()  # max=1.5, so 1.0*0.8=0.8 fits
        updated = p_seed_reward_delay(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters
        assert params.initial_value == pytest.approx(1.0 * 0.8)

    def test_clamps_to_max(self):
        metrics = _make_metrics(last_reward_delay_offset_updater=1.5)
        task = self._learn_to_choose_task()  # max=0.3
        updated = p_seed_reward_delay(metrics, task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters
        assert params.initial_value == 0.3

    def test_no_op_when_metric_none(self):
        task = self._learn_to_choose_task()
        original = task.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters.initial_value
        updated = p_seed_reward_delay(_make_metrics(last_reward_delay_offset_updater=None), task)
        params = updated.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET].parameters
        assert params.initial_value == original


# ============================================================
# Full progression
# ============================================================


class TestProgression:
    def test_stage_set(self, trainer: Trainer):
        assert {s.name for s in trainer.curriculum.see_stages()} == {
            "learn_to_stop",
            "learn_to_choose",
            "probability_grid_short_delay",
            "probability_grid_long_delay",
        }

    def test_advance_each_stage(self, trainer: Trainer, init_state: TrainerState):
        state = init_state
        assert state.stage is not None and state.stage.name == "learn_to_stop"

        # learn_to_stop -> learn_to_choose
        state = trainer.evaluate(
            state, _make_metrics(n_patches_visited=150, n_patches_seen=300, last_stop_threshold_updater=8)
        )
        assert state.stage is not None and state.stage.name == "learn_to_choose"

        # learn_to_choose -> probability_grid_short_delay
        state = trainer.evaluate(
            state, _make_metrics(n_patches_visited=100, n_patches_seen=200, last_reward_delay_offset_updater=0.3)
        )
        assert state.stage is not None and state.stage.name == "probability_grid_short_delay"

        # probability_grid_short_delay -> probability_grid_long_delay
        state = trainer.evaluate(
            state, _make_metrics(n_patches_visited=150, n_patches_seen=300, last_reward_delay_offset_updater=1.4)
        )
        assert state.stage is not None and state.stage.name == "probability_grid_long_delay"

    def test_no_advance_on_insufficient_metrics(self, trainer: Trainer, init_state: TrainerState):
        # Struggling animal stays on learn_to_stop (no low_p fallback anymore).
        metrics = _make_metrics(n_patches_visited=0, n_patches_seen=0, last_stop_threshold_updater=60)
        state = trainer.evaluate(init_state, metrics)
        assert state.stage is not None and state.stage.name == "learn_to_stop"
