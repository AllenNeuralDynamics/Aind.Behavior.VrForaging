from typing import Any, Callable, Type

import aind_behavior_curriculum
from aind_behavior_curriculum import Stage, StageTransition, Trainer, TrainerState, create_curriculum
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .. import __semver__
from ..cli import CurriculumCliArgs, CurriculumSuggestion
from ..depletion.curriculum import (
    metrics_from_dataset_path,
    st_s_stage_all_odors_rewarded_s_stage_graduation,
    st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0,
    st_s_stage_one_odor_w_depletion_day_0_s_stage_all_odors_rewarded,
    st_s_stage_one_odor_w_depletion_day_0_s_stage_one_odor_w_depletion_day_1,
    st_s_stage_one_odor_w_depletion_day_1_s_stage_all_odors_rewarded,
    st_s_stage_one_odor_w_depletion_day_1_s_stage_one_odor_w_depletion_day_0,
    trainer_state_from_file,
)
from ..depletion.stages import (
    make_s_stage_one_odor_no_depletion,
    make_s_stage_one_odor_w_depletion_day_0,
    make_s_stage_one_odor_w_depletion_day_1,
)


def build_deterministic_reversal_curriculum(
    curriculum_name: str,
    pkg_location: str,
    make_all_odors_rewarded: Callable[[], Stage],
    make_graduation: Callable[[], Stage],
) -> tuple[
    aind_behavior_curriculum.Curriculum,
    Trainer,
    Callable[[CurriculumCliArgs], CurriculumSuggestion[TrainerState[Any], Any]],
]:
    curriculum_class: Type[aind_behavior_curriculum.Curriculum[AindVrForagingTaskLogic]] = create_curriculum(
        curriculum_name, __semver__, (AindVrForagingTaskLogic,), pkg_location=pkg_location
    )
    curriculum = curriculum_class()

    curriculum.add_stage_transition(
        make_s_stage_one_odor_no_depletion(),
        make_s_stage_one_odor_w_depletion_day_0(),
        StageTransition(st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0),
    )
    curriculum.add_stage_transition(
        make_s_stage_one_odor_w_depletion_day_0(),
        make_s_stage_one_odor_w_depletion_day_1(),
        StageTransition(st_s_stage_one_odor_w_depletion_day_0_s_stage_one_odor_w_depletion_day_1),
    )
    curriculum.add_stage_transition(
        make_s_stage_one_odor_w_depletion_day_1(),
        make_s_stage_one_odor_w_depletion_day_0(),
        StageTransition(st_s_stage_one_odor_w_depletion_day_1_s_stage_one_odor_w_depletion_day_0),
    )
    curriculum.add_stage_transition(
        make_s_stage_one_odor_w_depletion_day_1(),
        make_all_odors_rewarded(),
        StageTransition(st_s_stage_one_odor_w_depletion_day_1_s_stage_all_odors_rewarded),
    )
    curriculum.add_stage_transition(
        make_s_stage_one_odor_w_depletion_day_0(),
        make_all_odors_rewarded(),
        StageTransition(st_s_stage_one_odor_w_depletion_day_0_s_stage_all_odors_rewarded),
    )
    curriculum.add_stage_transition(
        make_all_odors_rewarded(),
        make_graduation(),
        StageTransition(st_s_stage_all_odors_rewarded_s_stage_graduation),
    )

    trainer = Trainer(curriculum)

    def run_curriculum(args: CurriculumCliArgs) -> CurriculumSuggestion[TrainerState[Any], Any]:
        metrics: aind_behavior_curriculum.Metrics
        trainer_state = trainer_state_from_file(args.input_trainer_state, trainer)
        metrics = metrics_from_dataset_path(args.data_directory, trainer_state)
        trainer_state = trainer.evaluate(trainer_state, metrics)
        return CurriculumSuggestion(trainer_state=trainer_state, metrics=metrics, version=__semver__)

    return curriculum, trainer, run_curriculum
