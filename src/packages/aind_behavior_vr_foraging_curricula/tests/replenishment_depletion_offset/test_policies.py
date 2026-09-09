import numpy as np
import pytest
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.depletion.metrics import DepletionCurriculumMetrics
from aind_behavior_vr_foraging_curricula.replenishment_depletion_offset.policies import p_update_replenishment_rate
from aind_behavior_vr_foraging_curricula.replenishment_depletion_offset.stages import make_s_mcm_final_stage

DT = 0.1


def _make_metrics(total_water_consumed: float) -> DepletionCurriculumMetrics:
    return DepletionCurriculumMetrics(
        total_water_consumed=total_water_consumed,
        n_reward_sites_traveled=300,
        n_choices=151,
        n_patches_visited=50,
        n_patches_visited_per_patch={0: 25, 1: 25},
        last_stop_duration_offset_updater=0.5,
        last_reward_site_length=50,
        last_delay_duration=0.08,
    )


def _extract_rate(task: AindVrForagingTaskLogic, patch_index: int = 0) -> float:
    patch = task.task_parameters.environment.blocks[0].environment.patches[patch_index]
    reward_function = [
        f for f in patch.reward_specification.reward_function if hasattr(f.probability, "transition_matrix")
    ][0]
    return -np.log(np.array(reward_function.probability.transition_matrix)[0, 0]) / DT


@pytest.fixture
def base_task() -> AindVrForagingTaskLogic:
    # Starting replenishment rate for every patch is 0.1 (see rep_rates in stages.py)
    return make_s_mcm_final_stage().task.model_copy(deep=True)


class TestUpdateReplenishmentRateProgression:
    def test_drinking_at_or_above_max_applies_full_drop(self, base_task: AindVrForagingTaskLogic):
        updated = p_update_replenishment_rate(_make_metrics(1.0), base_task)
        assert _extract_rate(updated) == pytest.approx(0.09, abs=1e-6)

    def test_drinking_at_or_below_min_applies_no_drop(self, base_task: AindVrForagingTaskLogic):
        updated = p_update_replenishment_rate(_make_metrics(0.7), base_task)
        assert _extract_rate(updated) == pytest.approx(0.1, abs=1e-6)

    def test_drinking_below_min_is_clamped_same_as_min(self, base_task: AindVrForagingTaskLogic):
        updated = p_update_replenishment_rate(_make_metrics(0.0), base_task)
        assert _extract_rate(updated) == pytest.approx(0.1, abs=1e-6)

    def test_drinking_halfway_applies_half_drop(self, base_task: AindVrForagingTaskLogic):
        updated = p_update_replenishment_rate(_make_metrics(0.85), base_task)
        assert _extract_rate(updated) == pytest.approx(0.095, abs=1e-6)

    def test_two_session_progression_holds_after_reaching_floor_minus_one_step(
        self, base_task: AindVrForagingTaskLogic
    ):
        # Session 1: drinks the max -> full drop (0.1 -> 0.09)
        after_first = p_update_replenishment_rate(_make_metrics(1.0), base_task)
        assert _extract_rate(after_first) == pytest.approx(0.09, abs=1e-6)

        # Session 2: drinks the min -> no further drop (stays at 0.09)
        after_second = p_update_replenishment_rate(_make_metrics(0.7), after_first)
        assert _extract_rate(after_second) == pytest.approx(0.09, abs=1e-6)

    def test_rate_never_drops_below_floor(self, base_task: AindVrForagingTaskLogic):
        task = base_task
        # Repeatedly apply the max drop; after two sessions it should be clamped at the 0.08 floor.
        for _ in range(5):
            task = p_update_replenishment_rate(_make_metrics(1.0), task)
        assert _extract_rate(task) == pytest.approx(0.08, abs=1e-6)
