from typing import Any, cast

import pytest
from aind_behavior_curriculum import Curriculum, Trainer, TrainerState
from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.learning_sets import CURRICULUM, TRAINER
from aind_behavior_vr_foraging_curricula.learning_sets.curriculum import st_shaping_to_graduated
from aind_behavior_vr_foraging_curricula.learning_sets.helpers import (
    GEOMETRY_COMPRESSED,
    GEOMETRY_FULL,
    N_NEG_RAMP,
    N_SITES_EACH,
    ODOR_COUNT,
    REWARD_AMOUNT_UL_DEFAULT,
    REWARD_AMOUNT_UL_MAX,
    REWARD_AMOUNT_UL_MIN,
    STOP_DURATION_LEARNING_FACTOR,
    STOP_VELOCITY_LEARNING_FACTOR,
    VELOCITY_THRESHOLD_FLOOR,
    VELOCITY_THRESHOLD_START,
)
from aind_behavior_vr_foraging_curricula.learning_sets.metrics import LearningSetsMetrics
from aind_behavior_vr_foraging_curricula.learning_sets.policies import (
    p_ease_geometry,
    p_introduce_negative_sites,
    p_seed_stop_duration,
    p_seed_stop_velocity,
    p_water_cap,
)
from aind_behavior_vr_foraging_curricula.learning_sets.stages import make_s_graduated, make_s_shaping


@pytest.fixture
def trainer() -> Trainer[Any]:
    return TRAINER


@pytest.fixture
def curriculum() -> Curriculum[AindVrForagingTaskLogic]:
    return CURRICULUM


@pytest.fixture
def init_state() -> TrainerState[Any]:
    return TRAINER.create_enrollment()


def _make_metrics(**overrides: Any) -> LearningSetsMetrics:
    defaults: dict[str, Any] = dict(
        total_water_consumed=0.0,
        n_patches_visited=0,
        n_patches_seen=0,
        last_stop_duration_offset_updater=None,
        last_stop_velocity_threshold_updater=None,
        last_n_neg_sites_per_pair=None,
        last_reward_amount=None,
    )
    defaults.update(overrides)
    return LearningSetsMetrics(**defaults)


def _task(stage_factory) -> AindVrForagingTaskLogic:
    return cast(AindVrForagingTaskLogic, stage_factory().task).model_copy(deep=True)


def _unique(values: list[float]) -> float:
    assert len(set(values)) == 1, f"expected a single distinct value, got {set(values)}"
    return values[0]


def _negative_probability(task: AindVrForagingTaskLogic) -> float:
    return _unique(
        [
            p.reward_specification.probability.distribution_parameters.value
            for p in task.task_parameters.environment.blocks[0].environment.patches
            if p.state_index < ODOR_COUNT
        ]
    )


def _positive_probability(task: AindVrForagingTaskLogic) -> float:
    return _unique(
        [
            p.reward_specification.probability.distribution_parameters.value
            for p in task.task_parameters.environment.blocks[0].environment.patches
            if p.state_index >= ODOR_COUNT
        ]
    )


def _reward_amount(task: AindVrForagingTaskLogic) -> float:
    return _unique(
        [
            p.reward_specification.amount.distribution_parameters.value
            for p in task.task_parameters.environment.blocks[0].environment.patches
        ]
    )


def _reward_site_length(task: AindVrForagingTaskLogic) -> float:
    return _unique(
        [
            p.patch_virtual_sites_generator.reward_site.length_distribution.distribution_parameters.value
            for p in task.task_parameters.environment.blocks[0].environment.patches
        ]
    )


def _inter_patch_max(task: AindVrForagingTaskLogic) -> float:
    return _unique(
        [
            p.patch_virtual_sites_generator.inter_patch.length_distribution.truncation_parameters.max
            for p in task.task_parameters.environment.blocks[0].environment.patches
        ]
    )


def _n_neg_per_pair(task: AindVrForagingTaskLogic) -> int:
    from aind_behavior_vr_foraging_curricula.learning_sets.helpers import N_PAIRS

    patch_indices = task.task_parameters.environment.blocks[0].environment.patch_indices
    n_neg = sum(1 for idx in patch_indices if idx < ODOR_COUNT)
    return n_neg // N_PAIRS


# ============================================================
# Stage-transition predicate
# ============================================================


class TestShapingToGraduated:
    def _passing(self) -> LearningSetsMetrics:
        return _make_metrics(
            last_n_neg_sites_per_pair=N_SITES_EACH,
            last_stop_velocity_threshold_updater=VELOCITY_THRESHOLD_FLOOR,
            n_patches_seen=300,
            n_patches_visited=150,
        )

    def test_pass(self):
        assert st_shaping_to_graduated(self._passing()) is True

    def test_fail_when_neg_ratio_not_full(self):
        assert st_shaping_to_graduated(self._passing().model_copy(update=dict(last_n_neg_sites_per_pair=3))) is False

    def test_fail_when_velocity_not_at_final_floor(self):
        assert (
            st_shaping_to_graduated(self._passing().model_copy(update=dict(last_stop_velocity_threshold_updater=30.0)))
            is False
        )

    def test_fail_when_not_discriminating(self):
        # 290/300 ~ 0.97 > 0.7 -> harvesting everything
        assert st_shaping_to_graduated(self._passing().model_copy(update=dict(n_patches_visited=290))) is False

    def test_fail_when_metric_none(self):
        assert st_shaping_to_graduated(self._passing().model_copy(update=dict(last_n_neg_sites_per_pair=None))) is False


# ============================================================
# Policies
# ============================================================


class TestPIntroduceNegativeSites:
    def test_first_session_no_negatives(self):
        task = _task(make_s_shaping)
        p_introduce_negative_sites(_make_metrics(), task)
        assert _n_neg_per_pair(task) == 0

    def test_ramp_step_0_to_1(self):
        task = _task(make_s_shaping)
        p_introduce_negative_sites(_make_metrics(last_n_neg_sites_per_pair=0), task)
        assert _n_neg_per_pair(task) == N_NEG_RAMP[0]

    def test_ramp_step_1_to_3(self):
        task = _task(make_s_shaping)
        p_introduce_negative_sites(_make_metrics(last_n_neg_sites_per_pair=1), task)
        assert _n_neg_per_pair(task) == N_NEG_RAMP[1]

    def test_ramp_step_3_to_5(self):
        task = _task(make_s_shaping)
        p_introduce_negative_sites(_make_metrics(last_n_neg_sites_per_pair=3), task)
        assert _n_neg_per_pair(task) == N_NEG_RAMP[2]

    def test_ramp_saturates_at_5(self):
        task = _task(make_s_shaping)
        p_introduce_negative_sites(_make_metrics(last_n_neg_sites_per_pair=5), task)
        assert _n_neg_per_pair(task) == N_SITES_EACH

    def test_indices_within_valid_range(self):
        task = _task(make_s_shaping)
        p_introduce_negative_sites(_make_metrics(last_n_neg_sites_per_pair=3), task)
        indices = task.task_parameters.environment.blocks[0].environment.patch_indices
        assert all(0 <= idx < 2 * ODOR_COUNT for idx in indices)


class TestPSeedStopDuration:
    def test_seeds_eased_lower(self):
        task = _task(make_s_shaping)
        p_seed_stop_duration(_make_metrics(last_stop_duration_offset_updater=2.0), task)
        iv = task.task_parameters.updaters["StopDurationOffset"].parameters.initial_value
        assert iv == pytest.approx(2.0 * STOP_DURATION_LEARNING_FACTOR)

    def test_clamps_to_max(self):
        task = _task(make_s_shaping)
        p_seed_stop_duration(_make_metrics(last_stop_duration_offset_updater=1000.0), task)
        params = task.task_parameters.updaters["StopDurationOffset"].parameters
        assert params.initial_value == params.maximum

    def test_no_op_when_metric_none(self):
        task = _task(make_s_shaping)
        original = task.task_parameters.updaters["StopDurationOffset"].parameters.initial_value
        p_seed_stop_duration(_make_metrics(), task)
        assert task.task_parameters.updaters["StopDurationOffset"].parameters.initial_value == original


class TestPSeedStopVelocity:
    def test_shaping_stage_runs_full_velocity_ramp(self):
        task = _task(make_s_shaping)
        params = task.task_parameters.updaters["StopVelocityThreshold"].parameters
        assert params.initial_value == pytest.approx(VELOCITY_THRESHOLD_START)
        assert params.minimum == pytest.approx(VELOCITY_THRESHOLD_FLOOR)
        assert params.maximum == pytest.approx(VELOCITY_THRESHOLD_START)
        assert task.task_parameters.operation_control.position_control.velocity_threshold == pytest.approx(
            VELOCITY_THRESHOLD_START
        )

    def test_seeds_eased_above_floor(self):
        task = _task(make_s_shaping)
        p_seed_stop_velocity(_make_metrics(last_stop_velocity_threshold_updater=25.0), task)
        iv = task.task_parameters.updaters["StopVelocityThreshold"].parameters.initial_value
        assert iv == pytest.approx(25.0 * STOP_VELOCITY_LEARNING_FACTOR)

    def test_clamps_to_max(self):
        task = _task(make_s_shaping)
        p_seed_stop_velocity(_make_metrics(last_stop_velocity_threshold_updater=1000.0), task)
        params = task.task_parameters.updaters["StopVelocityThreshold"].parameters
        assert params.initial_value == params.maximum

    def test_no_op_when_metric_none(self):
        task = _task(make_s_shaping)
        original = task.task_parameters.updaters["StopVelocityThreshold"].parameters.initial_value
        p_seed_stop_velocity(_make_metrics(), task)
        assert task.task_parameters.updaters["StopVelocityThreshold"].parameters.initial_value == original

    def test_no_velocity_updater_in_graduated_stage(self):
        task = _task(make_s_graduated)
        assert "StopVelocityThreshold" not in task.task_parameters.updaters
        assert task.task_parameters.operation_control.position_control.velocity_threshold == pytest.approx(
            VELOCITY_THRESHOLD_FLOOR
        )


class TestPLearnToRun:
    def test_first_session_stays_compressed(self):
        task = _task(make_s_shaping)
        p_ease_geometry(_make_metrics(n_patches_seen=0), task)
        assert _reward_site_length(task) == pytest.approx(GEOMETRY_COMPRESSED.reward_site_length)
        assert _inter_patch_max(task) == pytest.approx(GEOMETRY_COMPRESSED.inter_patch_max_length)

    def test_eases_to_full_after_enough_travel(self):
        task = _task(make_s_shaping)
        p_ease_geometry(_make_metrics(n_patches_seen=10_000), task)
        assert _reward_site_length(task) == pytest.approx(GEOMETRY_FULL.reward_site_length)
        assert _inter_patch_max(task) == pytest.approx(GEOMETRY_FULL.inter_patch_max_length)

    def test_partial_easing_is_between(self):
        task = _task(make_s_shaping)
        from aind_behavior_vr_foraging_curricula.learning_sets.helpers import GEOMETRY_EASE_SITES

        p_ease_geometry(_make_metrics(n_patches_seen=int(GEOMETRY_EASE_SITES // 2)), task)
        midpoint = 0.5 * (GEOMETRY_COMPRESSED.reward_site_length + GEOMETRY_FULL.reward_site_length)
        assert _reward_site_length(task) == pytest.approx(midpoint)

    def test_inter_patch_distribution_stays_exponential(self):
        task = _task(make_s_shaping)
        p_ease_geometry(_make_metrics(n_patches_seen=10_000), task)
        for patch in task.task_parameters.environment.blocks[0].environment.patches:
            dist = patch.patch_virtual_sites_generator.inter_patch.length_distribution
            assert isinstance(dist, distributions.ExponentialDistribution)


class TestPWaterCap:
    def test_trims_when_over_budget(self):
        task = _task(make_s_graduated)
        p_water_cap(_make_metrics(total_water_consumed=1.2, last_reward_amount=8.0), task)
        assert _reward_amount(task) == pytest.approx(7.5)

    def test_raises_when_under_floor(self):
        task = _task(make_s_graduated)
        p_water_cap(_make_metrics(total_water_consumed=0.5, last_reward_amount=5.0), task)
        assert _reward_amount(task) == pytest.approx(5.5)

    def test_holds_within_window(self):
        task = _task(make_s_graduated)
        p_water_cap(_make_metrics(total_water_consumed=0.7, last_reward_amount=6.0), task)
        assert _reward_amount(task) == pytest.approx(6.0)

    def test_never_below_min(self):
        task = _task(make_s_graduated)
        p_water_cap(_make_metrics(total_water_consumed=0.9, last_reward_amount=REWARD_AMOUNT_UL_MIN), task)
        assert _reward_amount(task) == pytest.approx(REWARD_AMOUNT_UL_MIN)

    def test_never_above_max(self):
        task = _task(make_s_graduated)
        p_water_cap(_make_metrics(total_water_consumed=0.5, last_reward_amount=REWARD_AMOUNT_UL_MAX), task)
        assert _reward_amount(task) == pytest.approx(REWARD_AMOUNT_UL_MAX)

    def test_defaults_to_default_when_metric_none(self):
        task = _task(make_s_graduated)
        p_water_cap(_make_metrics(total_water_consumed=0.7), task)
        assert _reward_amount(task) == pytest.approx(REWARD_AMOUNT_UL_DEFAULT)


# ============================================================
# Full progression
# ============================================================


class TestProgression:
    def test_stage_set(self, trainer: Trainer):
        assert {s.name for s in trainer.curriculum.see_stages()} == {"shaping", "graduated"}

    def test_advance_to_graduated(self, trainer: Trainer, init_state: TrainerState):
        state = init_state
        assert state.stage is not None and state.stage.name == "shaping"

        state = trainer.evaluate(
            state,
            _make_metrics(
                last_n_neg_sites_per_pair=N_SITES_EACH,
                last_stop_velocity_threshold_updater=VELOCITY_THRESHOLD_FLOOR,
                n_patches_seen=300,
                n_patches_visited=150,
            ),
        )
        assert state.stage is not None and state.stage.name == "graduated"

    def test_stays_on_shaping_until_full_ratio(self, trainer: Trainer, init_state: TrainerState):
        state = trainer.evaluate(
            init_state,
            _make_metrics(
                last_n_neg_sites_per_pair=3,
                last_stop_velocity_threshold_updater=VELOCITY_THRESHOLD_FLOOR,
                n_patches_seen=300,
                n_patches_visited=200,
            ),
        )
        assert state.stage is not None and state.stage.name == "shaping"

    def test_no_advance_on_insufficient_metrics(self, trainer: Trainer, init_state: TrainerState):
        state = trainer.evaluate(init_state, _make_metrics())
        assert state.stage is not None and state.stage.name == "shaping"
