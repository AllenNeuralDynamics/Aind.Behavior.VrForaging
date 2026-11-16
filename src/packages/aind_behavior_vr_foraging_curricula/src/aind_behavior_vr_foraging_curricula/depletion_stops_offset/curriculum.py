from typing import Any, TypeVar

import aind_behavior_curriculum
import pydantic
from aind_behavior_curriculum import (
    StageTransition,
    Trainer,
    TrainerState,
    create_curriculum,
)
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .. import __semver__
from ..cli import CurriculumCliArgs, CurriculumSuggestion
from ..depletion.curriculum import (
    add_shaping_tracks,
    metrics_from_dataset_path,
    st_s_stage_all_odors_rewarded_s_stage_graduation,
    trainer_state_from_file,
)
from .stages import make_s_stage_all_odors_rewarded, make_s_stage_graduation

CURRICULUM_NAME = "DepletionStopsOffset"
PKG_LOCATION = ".".join(__name__.split(".")[:-1])

TModel = TypeVar("TModel", bound=pydantic.BaseModel)


# ============================================================
# Curriculum definition
# ============================================================

curriculum_class: type[aind_behavior_curriculum.Curriculum[AindVrForagingTaskLogic]] = create_curriculum(
    CURRICULUM_NAME, __semver__, (AindVrForagingTaskLogic,), pkg_location=PKG_LOCATION
)
CURRICULUM = curriculum_class()


add_shaping_tracks(CURRICULUM, make_s_stage_all_odors_rewarded())

CURRICULUM.add_stage_transition(
    make_s_stage_all_odors_rewarded(),
    make_s_stage_graduation(),
    StageTransition(st_s_stage_all_odors_rewarded_s_stage_graduation),
)

# ==============================================================================
# Create a Trainer that uses the curriculum to bootstrap suggestions
# ==============================================================================

TRAINER = Trainer(CURRICULUM)


def run_curriculum(args: CurriculumCliArgs) -> CurriculumSuggestion[TrainerState[Any], Any]:
    metrics: aind_behavior_curriculum.Metrics
    trainer_state = trainer_state_from_file(args.input_trainer_state, TRAINER)
    metrics = metrics_from_dataset_path(args.data_directory, trainer_state)
    trainer_state = TRAINER.evaluate(trainer_state, metrics)
    return CurriculumSuggestion(trainer_state=trainer_state, metrics=metrics, version=__semver__)
