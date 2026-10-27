import os

import numpy as np
import pytest
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.replenishment_depletion_offset.metrics import (
    ReplenishmentCurriculumMetrics,
    ReplenishmentSessionMetrics,
    past_sessions_from_file,
)
from aind_behavior_vr_foraging_curricula.replenishment_depletion_offset.policies import (
    p_update_replenishment_rate,
    p_update_reward_amount,
)
from aind_behavior_vr_foraging_curricula.replenishment_depletion_offset.stages import make_s_mcm_final_stage
from aind_behavior_vr_foraging_curricula.replenishment_depletion_offset.utils import compute_cmc_transition_probability

DT = 0.1


STAGE = "mcm_final_stage"


def _make_metrics(
    total_water_consumed: float, rate: float = 0.1, past: list[ReplenishmentSessionMetrics] | None = None
) -> ReplenishmentCurriculumMetrics:
    return ReplenishmentCurriculumMetrics(
        stage_name=STAGE,
        replenishment_rate=rate,
        past_sessions=past or [],
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


def _set_rate(task: AindVrForagingTaskLogic, rate: float) -> None:
    for patch in task.task_parameters.environment.blocks[0].environment.patches:
        f = [f for f in patch.reward_specification.reward_function if hasattr(f.probability, "transition_matrix")][0]
        f.probability.transition_matrix = compute_cmc_transition_probability(
            len(f.probability.transition_matrix), rate, DT
        ).tolist()


def _past(water: float, rate: float, stage: str = STAGE) -> ReplenishmentSessionMetrics:
    m = ReplenishmentSessionMetrics(**_make_metrics(water, rate).model_dump())
    m.stage_name = stage
    return m


@pytest.fixture
def base_task() -> AindVrForagingTaskLogic:
    # Start from the graduated rate of 0.1; the initial rate is covered in TestInitialRateReduction
    task = make_s_mcm_final_stage().task.model_copy(deep=True)
    _set_rate(task, 0.1)
    return task


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


class TestInitialRateReduction:
    @staticmethod
    def _initial_task() -> AindVrForagingTaskLogic:
        return make_s_mcm_final_stage().task.model_copy(deep=True)

    def test_starts_at_initial_rate(self):
        assert _extract_rate(self._initial_task()) == pytest.approx(100.0, rel=1e-6)

    def test_holds_without_history(self):
        updated = p_update_replenishment_rate(_make_metrics(1.0, rate=100.0), self._initial_task())
        assert _extract_rate(updated) == pytest.approx(100.0, rel=1e-6)

    def test_holds_if_a_recent_session_missed_target(self):
        metrics = _make_metrics(1.0, rate=100.0, past=[_past(0.9, 100.0)])
        updated = p_update_replenishment_rate(metrics, self._initial_task())
        assert _extract_rate(updated) == pytest.approx(100.0, rel=1e-6)

    def test_ignores_sessions_from_other_stages(self):
        metrics = _make_metrics(1.0, rate=100.0, past=[_past(1.0, 100.0, stage="other_stage")])
        updated = p_update_replenishment_rate(metrics, self._initial_task())
        assert _extract_rate(updated) == pytest.approx(100.0, rel=1e-6)

    def test_drops_to_graduation_rate_after_enough_sessions(self):
        metrics = _make_metrics(1.0, rate=100.0, past=[_past(1.0, 100.0)])
        updated = p_update_replenishment_rate(metrics, self._initial_task())
        assert _extract_rate(updated) == pytest.approx(0.1, abs=1e-6)


class TestUpdateRewardAmount:
    @staticmethod
    def _amount(task: AindVrForagingTaskLogic) -> float:
        patch = task.task_parameters.environment.blocks[0].environment.patches[0]
        return patch.reward_specification.amount.distribution_parameters.value

    def test_holds_before_reaching_min_rate(self, base_task: AindVrForagingTaskLogic):
        metrics = _make_metrics(1.0, rate=0.09, past=[_past(1.0, 0.09)])
        assert self._amount(p_update_reward_amount(metrics, base_task)) == 5.0

    def test_holds_if_only_one_session_at_min_rate(self, base_task: AindVrForagingTaskLogic):
        metrics = _make_metrics(1.0, rate=0.08, past=[_past(1.0, 0.09)])
        assert self._amount(p_update_reward_amount(metrics, base_task)) == 5.0

    def test_drops_after_enough_sessions_at_min_rate(self, base_task: AindVrForagingTaskLogic):
        metrics = _make_metrics(1.0, rate=0.08, past=[_past(1.0, 0.08)])
        assert self._amount(p_update_reward_amount(metrics, base_task)) == 4.0


class TestPastSessionsFromFile:
    def test_missing_file_is_empty(self, tmp_path):
        assert past_sessions_from_file(tmp_path / "past_metrics.jsonl") == []

    def test_drops_lines_that_cannot_be_deserialized(self, tmp_path):
        path = tmp_path / "past_metrics.jsonl"
        good = _past(1.0, 0.1).model_dump_json()
        lines = [good, "not json", '{"stage_name": "x"}', "", good]
        path.write_text(os.linesep.join(lines), encoding="utf-8")
        assert len(past_sessions_from_file(path)) == 2


class TestSessionId:
    @staticmethod
    def _with_id(session_id: str | None) -> ReplenishmentSessionMetrics:
        m = _past(1.0, 0.1)
        m.session_id = session_id
        return m

    def test_session_id_is_optional_and_defaults_to_none(self):
        assert _past(1.0, 0.1).session_id is None

    def test_session_id_roundtrips_through_file(self, tmp_path):
        path = tmp_path / "past_metrics.jsonl"
        path.write_text(self._with_id("subj_1").model_dump_json(), encoding="utf-8")
        assert [s.session_id for s in past_sessions_from_file(path)] == ["subj_1"]

    def test_lines_without_session_id_still_load(self, tmp_path):
        path = tmp_path / "past_metrics.jsonl"
        record = _past(1.0, 0.1).model_dump()
        del record["session_id"]
        path.write_text(ReplenishmentSessionMetrics.model_construct(**record).model_dump_json(exclude={"session_id"}))
        assert len(past_sessions_from_file(path)) == 1

    def test_serialized_current_metrics_can_be_appended_to_history(self, tmp_path):
        path = tmp_path / "past_metrics.jsonl"
        current = _make_metrics(1.0, past=[_past(1.0, 0.1)])
        current.session_id = "subj_2"
        path.write_text(current.model_dump_json(), encoding="utf-8")
        loaded = past_sessions_from_file(path)
        assert [s.session_id for s in loaded] == ["subj_2"]
        assert not hasattr(loaded[0], "past_sessions")
