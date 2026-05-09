from typing import Any, cast

import aind_behavior_services.task.distributions as distributions
import pytest
from aind_behavior_curriculum import Curriculum, Trainer, TrainerState
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.single_site_matching import CURRICULUM, TRAINER
from aind_behavior_vr_foraging_curricula.single_site_matching.curriculum import (
    st_s_learn_to_stop_to_s_graduated_stage,
)
from aind_behavior_vr_foraging_curricula.single_site_matching.metrics import SingleSiteMatchingMetrics
from aind_behavior_vr_foraging_curricula.single_site_matching.policies import (
    _ENV_GROW_GAINS,
    _ENV_GROW_MIN_PATCHES_VISITED,
    _ENV_GROW_TARGETS,
    _P_REW_DROP_FULL_STEP,
    _P_REW_DROP_TARGET,
    _P_REW_DROP_WATER_MAX_ML,
    _P_REW_DROP_WATER_MIN_ML,
    p_drop_reward_probability,
    p_grow_environment,
    p_learn_to_stop,
)
from aind_behavior_vr_foraging_curricula.single_site_matching.stages import make_s_learn_to_stop


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


# ---------------------------------------------------------------------------
# Helpers shared by the two new policy test classes
# ---------------------------------------------------------------------------


def _fresh_task() -> AindVrForagingTaskLogic:
    """Return a deep copy of the learn_to_stop stage task (avoids state leakage)."""
    return make_s_learn_to_stop().task.model_copy(deep=True)


def _make_metrics(
    *,
    total_water_consumed: float = 1.0,
    n_patches_visited: int = 150,
    n_patches_seen: int = 300,
    last_stop_threshold_updater: float = 10.0,
    last_stop_duration_offset_updater: float = 0.5,
) -> SingleSiteMatchingMetrics:
    return SingleSiteMatchingMetrics(
        total_water_consumed=total_water_consumed,
        n_patches_visited=n_patches_visited,
        n_patches_seen=n_patches_seen,
        last_stop_threshold_updater=last_stop_threshold_updater,
        last_stop_duration_offset_updater=last_stop_duration_offset_updater,
    )


def _inter_patch_dist(task: AindVrForagingTaskLogic) -> distributions.ExponentialDistribution:
    dist = (
        task.task_parameters.environment.blocks[0]
        .environment_statistics.patches[0]
        .patch_virtual_sites_generator.inter_patch.length_distribution
    )
    assert isinstance(dist, distributions.ExponentialDistribution)
    return dist


def _reward_site_dist(task: AindVrForagingTaskLogic) -> distributions.Scalar:
    dist = (
        task.task_parameters.environment.blocks[0]
        .environment_statistics.patches[0]
        .patch_virtual_sites_generator.reward_site.length_distribution
    )
    assert isinstance(dist, distributions.Scalar)
    return dist


def _reward_spec_p(task: AindVrForagingTaskLogic, patch_idx: int = 0) -> float:
    spec = (
        task.task_parameters.environment.blocks[0]
        .environment_statistics.patches[patch_idx]
        .reward_specification.probability
    )
    assert isinstance(spec, distributions.Scalar)
    return spec.distribution_parameters.value


# ---------------------------------------------------------------------------
# p_grow_environment tests
# ---------------------------------------------------------------------------


class TestPGrowEnvironment:
    def test_no_update_below_threshold(self):
        """Geometry must not change when n_patches_visited is below the minimum."""
        task = _fresh_task()
        ip = _inter_patch_dist(task)
        assert ip.truncation_parameters is not None
        original_min = ip.truncation_parameters.min
        original_max = ip.truncation_parameters.max
        original_mean = 1.0 / ip.distribution_parameters.rate
        original_rsl = _reward_site_dist(task).distribution_parameters.value

        metrics = _make_metrics(n_patches_visited=_ENV_GROW_MIN_PATCHES_VISITED - 1)
        result = p_grow_environment(metrics, task)

        ip_after = _inter_patch_dist(result)
        assert ip_after.truncation_parameters is not None
        assert ip_after.truncation_parameters.min == original_min
        assert ip_after.truncation_parameters.max == original_max
        assert abs(1.0 / ip_after.distribution_parameters.rate - original_mean) < 1e-9
        assert _reward_site_dist(result).distribution_parameters.value == original_rsl

    def test_single_session_increases_geometry(self):
        """After one qualifying session each dimension increases by its gain factor."""
        task = _fresh_task()
        ip = _inter_patch_dist(task)
        assert ip.truncation_parameters is not None
        assert ip.scaling_parameters is not None
        start_min = ip.truncation_parameters.min
        start_max = ip.truncation_parameters.max
        start_mean = 1.0 / ip.distribution_parameters.rate
        start_rsl = _reward_site_dist(task).distribution_parameters.value

        metrics = _make_metrics(n_patches_visited=_ENV_GROW_MIN_PATCHES_VISITED)
        result = p_grow_environment(metrics, task)

        ip_after = _inter_patch_dist(result)
        assert ip_after.truncation_parameters is not None

        expected_min = min(
            start_min * _ENV_GROW_GAINS["inter_patch_min_length"], _ENV_GROW_TARGETS["inter_patch_min_length"]
        )
        expected_max = min(
            start_max * _ENV_GROW_GAINS["inter_patch_max_length"], _ENV_GROW_TARGETS["inter_patch_max_length"]
        )
        expected_mean = min(
            start_mean * _ENV_GROW_GAINS["inter_patch_mean_length"], _ENV_GROW_TARGETS["inter_patch_mean_length"]
        )
        expected_rsl = min(start_rsl * _ENV_GROW_GAINS["reward_site_length"], _ENV_GROW_TARGETS["reward_site_length"])

        assert abs(ip_after.truncation_parameters.min - expected_min) < 1e-6
        assert abs(ip_after.truncation_parameters.max - expected_max) < 1e-6
        assert abs(1.0 / ip_after.distribution_parameters.rate - expected_mean) < 1e-6
        assert abs(_reward_site_dist(result).distribution_parameters.value - expected_rsl) < 1e-6

    def test_scaling_parameters_offset_matches_min(self):
        """The ExponentialDistribution offset must equal the updated min so the
        distribution always starts at the new minimum."""
        task = _fresh_task()
        metrics = _make_metrics(n_patches_visited=_ENV_GROW_MIN_PATCHES_VISITED)
        result = p_grow_environment(metrics, task)

        ip_after = _inter_patch_dist(result)
        assert ip_after.truncation_parameters is not None
        assert ip_after.scaling_parameters is not None
        assert ip_after.scaling_parameters.offset == ip_after.truncation_parameters.min

    def test_clamps_at_target_after_many_sessions(self):
        """Repeated updates must not push geometry above the graduated-stage targets."""
        task = _fresh_task()
        metrics = _make_metrics(n_patches_visited=_ENV_GROW_MIN_PATCHES_VISITED)

        for _ in range(20):  # far more sessions than needed
            task = p_grow_environment(metrics, task)

        ip = _inter_patch_dist(task)
        assert ip.truncation_parameters is not None
        assert abs(ip.truncation_parameters.min - _ENV_GROW_TARGETS["inter_patch_min_length"]) < 1e-6
        assert abs(ip.truncation_parameters.max - _ENV_GROW_TARGETS["inter_patch_max_length"]) < 1e-6
        assert abs(1.0 / ip.distribution_parameters.rate - _ENV_GROW_TARGETS["inter_patch_mean_length"]) < 1e-6
        assert (
            abs(_reward_site_dist(task).distribution_parameters.value - _ENV_GROW_TARGETS["reward_site_length"]) < 1e-6
        )

    def test_reaches_target_within_n_days(self):
        """Starting from the initial stage values, the target must be reached within
        a small number of qualifying sessions (defined by the gain exponent)."""
        task = _fresh_task()
        metrics = _make_metrics(n_patches_visited=_ENV_GROW_MIN_PATCHES_VISITED)

        # The gains are designed for ~4 sessions; allow a small buffer
        max_sessions = 6
        for _ in range(max_sessions):
            task = p_grow_environment(metrics, task)

        ip = _inter_patch_dist(task)
        assert ip.truncation_parameters is not None
        assert ip.truncation_parameters.min >= _ENV_GROW_TARGETS["inter_patch_min_length"] - 1e-6
        assert ip.truncation_parameters.max >= _ENV_GROW_TARGETS["inter_patch_max_length"] - 1e-6
        assert 1.0 / ip.distribution_parameters.rate >= _ENV_GROW_TARGETS["inter_patch_mean_length"] - 1e-6
        assert _reward_site_dist(task).distribution_parameters.value >= _ENV_GROW_TARGETS["reward_site_length"] - 1e-6

    def test_all_patches_updated(self):
        """All patches in all blocks must receive the geometry update."""
        task = _fresh_task()
        metrics = _make_metrics(n_patches_visited=_ENV_GROW_MIN_PATCHES_VISITED)
        result = p_grow_environment(metrics, task)

        for block in result.task_parameters.environment.blocks:
            for patch in block.environment_statistics.patches:
                ip = patch.patch_virtual_sites_generator.inter_patch.length_distribution
                assert isinstance(ip, distributions.ExponentialDistribution)
                assert ip.truncation_parameters is not None
                # min must have moved away from the original start value of 25
                assert ip.truncation_parameters.min > 25.0


# ---------------------------------------------------------------------------
# p_drop_reward_probability tests
# ---------------------------------------------------------------------------


class TestPDropRewardProbability:
    def test_no_update_below_water_minimum(self):
        """p_reward must not change when water is below the minimum threshold."""
        task = _fresh_task()
        original_p = _reward_spec_p(task)

        metrics = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MIN_ML - 0.01)
        result = p_drop_reward_probability(metrics, task)

        assert _reward_spec_p(result) == original_p

    def test_no_update_at_exact_water_minimum(self):
        """At exactly 700 µL the water fraction is 0 so step = 0 → no change."""
        task = _fresh_task()
        original_p = _reward_spec_p(task)

        metrics = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MIN_ML)
        result = p_drop_reward_probability(metrics, task)

        assert abs(_reward_spec_p(result) - original_p) < 1e-9

    def test_half_step_at_midpoint_water(self):
        """At 850 µL the fraction is 0.5, so step = 0.5 * full_step."""
        task = _fresh_task()
        original_p = _reward_spec_p(task)
        mid_water = (_P_REW_DROP_WATER_MIN_ML + _P_REW_DROP_WATER_MAX_ML) / 2  # 0.85

        metrics = _make_metrics(total_water_consumed=mid_water)
        result = p_drop_reward_probability(metrics, task)

        expected_p = original_p - 0.5 * _P_REW_DROP_FULL_STEP
        assert abs(_reward_spec_p(result) - expected_p) < 1e-9

    def test_full_step_at_water_maximum(self):
        """At exactly 1000 µL the full step is applied."""
        task = _fresh_task()
        original_p = _reward_spec_p(task)

        metrics = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MAX_ML)
        result = p_drop_reward_probability(metrics, task)

        expected_p = original_p - _P_REW_DROP_FULL_STEP
        assert abs(_reward_spec_p(result) - expected_p) < 1e-9

    def test_clamped_above_water_maximum(self):
        """Water above 1000 µL must produce the same step as exactly 1000 µL."""
        task_a = _fresh_task()
        task_b = _fresh_task()

        at_max = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MAX_ML)
        above_max = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MAX_ML + 0.5)

        p_drop_reward_probability(at_max, task_a)
        p_drop_reward_probability(above_max, task_b)

        assert abs(_reward_spec_p(task_a) - _reward_spec_p(task_b)) < 1e-9

    def test_clamps_at_target_after_many_sessions(self):
        """p_reward must not drop below the target after many qualifying sessions."""
        task = _fresh_task()
        metrics = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MAX_ML)

        for _ in range(20):  # far more than the designed 4 days
            task = p_drop_reward_probability(metrics, task)

        assert abs(_reward_spec_p(task) - _P_REW_DROP_TARGET) < 1e-9

    def test_reaches_target_within_n_days(self):
        """Starting from p=1, full-step sessions should reach the target in N days."""
        task = _fresh_task()
        metrics = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MAX_ML)

        # Designed for 4 days; allow a small buffer
        n_days = round(1.0 / _P_REW_DROP_FULL_STEP)  # == _P_REW_DROP_N_DAYS
        for _ in range(n_days):
            task = p_drop_reward_probability(metrics, task)

        assert abs(_reward_spec_p(task) - _P_REW_DROP_TARGET) < 1e-9

    def test_all_reward_function_fields_updated_consistently(self):
        """PatchRewardFunction and PersistentRewardFunction must mirror the new p
        for every patch (each patch may start at a different p_reward)."""
        task = _fresh_task()
        metrics = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MAX_ML)
        result = p_drop_reward_probability(metrics, task)

        for block in result.task_parameters.environment.blocks:
            for patch in block.environment_statistics.patches:
                # Ground-truth new_p comes from the patch's own reward spec
                spec = patch.reward_specification.probability
                assert isinstance(spec, distributions.Scalar)
                patch_new_p = spec.distribution_parameters.value

                for rf in patch.reward_specification.reward_function:
                    if isinstance(rf, task_logic.PatchRewardFunction):
                        assert isinstance(rf.probability, task_logic.SetValueFunction)
                        assert isinstance(rf.probability.value, distributions.Scalar)
                        assert abs(rf.probability.value.distribution_parameters.value - patch_new_p) < 1e-9

                    elif isinstance(rf, task_logic.PersistentRewardFunction):
                        assert isinstance(rf.probability, task_logic.SetValueFunction)
                        assert isinstance(rf.probability.value, distributions.BinomialDistribution)
                        binom = rf.probability.value
                        assert binom.scaling_parameters is not None
                        assert binom.truncation_parameters is not None
                        assert abs(binom.scaling_parameters.offset - patch_new_p) < 1e-9
                        assert abs(binom.truncation_parameters.min - patch_new_p) < 1e-9

    def test_all_patches_updated(self):
        """Every patch in every block must have p_reward clamped to
        max(initial_p - full_step, target)."""
        task = _fresh_task()

        # Record initial probabilities per patch before the update
        initial_probs = [
            cast(distributions.Scalar, patch.reward_specification.probability).distribution_parameters.value
            for block in task.task_parameters.environment.blocks
            for patch in block.environment_statistics.patches
        ]

        metrics = _make_metrics(total_water_consumed=_P_REW_DROP_WATER_MAX_ML)
        result = p_drop_reward_probability(metrics, task)

        idx = 0
        for block in result.task_parameters.environment.blocks:
            for patch in block.environment_statistics.patches:
                spec = patch.reward_specification.probability
                assert isinstance(spec, distributions.Scalar)
                expected = max(initial_probs[idx] - _P_REW_DROP_FULL_STEP, _P_REW_DROP_TARGET)
                assert abs(spec.distribution_parameters.value - expected) < 1e-9
                idx += 1

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
