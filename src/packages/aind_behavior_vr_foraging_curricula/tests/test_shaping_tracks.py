"""Parallel per-odor shaping tracks shared by every curriculum that reuses the depletion shaping."""

import importlib
from typing import cast

import pytest
from aind_behavior_curriculum import Trainer
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula.depletion.metrics import DepletionCurriculumMetrics
from aind_behavior_vr_foraging_curricula.depletion.stages import (
    S_ONE_ODOR_NO_DEPLETION,
    S_ONE_ODOR_W_DEPLETION_DAY_0,
    SHAPING_ODOR_INDICES,
    shaping_stage_name,
)

CURRICULA_WITH_SHAPING = [
    "depletion",
    "depletion_stops_offset",
    "depletion_stops_rate",
    "deterministic_reversals",
    "deterministic_reversals_reward_capped",
    "replenishment_depletion_offset",
]

SHAPING_BASE_NAMES = (S_ONE_ODOR_NO_DEPLETION, S_ONE_ODOR_W_DEPLETION_DAY_0)


def _trainer(curriculum: str) -> Trainer:
    return importlib.import_module(f"aind_behavior_vr_foraging_curricula.{curriculum}").TRAINER


def _odor_of(stage_name: str) -> int | None:
    """Track (odor index) a stage belongs to, or None if it is not a shaping stage."""
    for odor_index in SHAPING_ODOR_INDICES:
        if stage_name in {shaping_stage_name(base, odor_index) for base in SHAPING_BASE_NAMES}:
            return odor_index
    return None


def _passing_metrics() -> DepletionCurriculumMetrics:
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


def test_shaping_stage_name():
    assert shaping_stage_name(S_ONE_ODOR_NO_DEPLETION, 0) == "one_odor_no_depletion"
    assert shaping_stage_name(S_ONE_ODOR_NO_DEPLETION, 2) == "one_odor_no_depletion [odor_2]"
    with pytest.raises(ValueError):
        shaping_stage_name(S_ONE_ODOR_NO_DEPLETION, 3)


@pytest.mark.parametrize("curriculum", CURRICULA_WITH_SHAPING)
class TestShapingTracks:
    def test_one_track_per_odor(self, curriculum: str):
        names = {s.name for s in _trainer(curriculum).curriculum.see_stages()}
        for odor_index in SHAPING_ODOR_INDICES:
            for base in SHAPING_BASE_NAMES:
                assert shaping_stage_name(base, odor_index) in names

    def test_odor_zero_keeps_legacy_names(self, curriculum: str):
        names = {s.name for s in _trainer(curriculum).curriculum.see_stages()}
        assert {"one_odor_no_depletion", "one_odor_w_depletion_day_0"} <= names

    def test_default_enrollment_is_odor_zero(self, curriculum: str):
        state = _trainer(curriculum).create_enrollment()
        assert state.stage is not None
        assert state.stage.name == "one_odor_no_depletion"

    def test_stage_uses_only_its_track_odor(self, curriculum: str):
        for stage in _trainer(curriculum).curriculum.see_stages():
            odor_index = _odor_of(stage.name)
            if odor_index is None:
                continue
            task = cast(AindVrForagingTaskLogic, stage.task)
            assert task.stage_name == stage.name
            for block in task.task_parameters.environment.blocks:
                for patch in block.environment.patches:
                    expected = [1 if i == odor_index else 0 for i in range(3)]
                    assert patch.odor_specification == expected

    def test_no_transition_crosses_tracks(self, curriculum: str):
        cur = _trainer(curriculum).curriculum
        for stage in cur.see_stages():
            src = _odor_of(stage.name)
            if src is None:
                continue
            for _, dest in cur.see_stage_transitions(stage):
                dst = _odor_of(dest.name)
                assert dst is None or dst == src, f"{stage.name} -> {dest.name} crosses tracks"

    def test_tracks_converge_on_one_stage(self, curriculum: str):
        cur = _trainer(curriculum).curriculum
        exits = {
            dest.name
            for stage in cur.see_stages()
            if _odor_of(stage.name) is not None
            for _, dest in cur.see_stage_transitions(stage)
            if _odor_of(dest.name) is None
        }
        assert len(exits) == 1

    @pytest.mark.parametrize("odor_index", SHAPING_ODOR_INDICES)
    def test_progression_stays_on_track(self, curriculum: str, odor_index: int):
        trainer = _trainer(curriculum)
        start = next(
            s
            for s in trainer.curriculum.see_stages()
            if s.name == shaping_stage_name(S_ONE_ODOR_NO_DEPLETION, odor_index)
        )
        state = trainer.create_trainer_state(stage=start, active_policies=start.start_policies)
        state = trainer.evaluate(state, _passing_metrics())
        assert state.stage is not None
        assert state.stage.name == shaping_stage_name(S_ONE_ODOR_W_DEPLETION_DAY_0, odor_index)
        state = trainer.evaluate(state, _passing_metrics())
        assert state.stage is not None
        assert _odor_of(state.stage.name) is None
