import os
from typing import Any, Type, TypeVar, Union

import aind_behavior_curriculum
import pydantic
from aind_behavior_curriculum import (
    Metrics,
    StageTransition,
    Trainer,
    TrainerState,
    create_curriculum,
)
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .. import __semver__
from ..cli import CurriculumCliArgs, CurriculumSuggestion
from ..utils import model_from_json_file
from .metrics import SingleSiteMatchingMetrics
from .stages import (
    make_s_graduated_stage,
    make_s_learn_to_stop,
)

CURRICULUM_NAME = "SingleSiteMatching"
PKG_LOCATION = ".".join(__name__.split(".")[:-1])

TModel = TypeVar("TModel", bound=pydantic.BaseModel)


# ============================================================
# Stage transitions
# ============================================================


def st_s_learn_to_stop_to_s_graduated_stage(metrics: SingleSiteMatchingMetrics) -> bool:
    if metrics.last_stop_threshold_updater is None:
        return False
    if metrics.last_stop_duration_offset_updater is None:
        return False

    if (
        (metrics.last_stop_threshold_updater <= 8)
        and (metrics.last_stop_duration_offset_updater >= 0.6)
        and (metrics.n_patches_seen >= 300)
        and (metrics.n_patches_visited >= 150)
    ):
        return True
    return False


# ============================================================
# Curriculum definition
# ============================================================

curriculum_class: Type[aind_behavior_curriculum.Curriculum[AindVrForagingTaskLogic]] = create_curriculum(
    CURRICULUM_NAME, __semver__, (AindVrForagingTaskLogic,), pkg_location=PKG_LOCATION
)
CURRICULUM = curriculum_class()

CURRICULUM.add_stage_transition(
    make_s_learn_to_stop(),
    make_s_graduated_stage(),
    StageTransition(st_s_learn_to_stop_to_s_graduated_stage),
)

# ==============================================================================
# Create a Trainer that uses the curriculum to bootstrap suggestions
# ==============================================================================

TRAINER = Trainer(CURRICULUM)


def trainer_state_from_file(path: Union[str, os.PathLike], trainer: Trainer = TRAINER) -> TrainerState:
    return model_from_json_file(path, trainer.trainer_state_model)


def metrics_from_dataset_path(dataset_path: Union[str, os.PathLike], trainer_state: TrainerState) -> Metrics:
    stage = trainer_state.stage
    if stage is None:
        raise ValueError("Trainer state does not have a stage")
    if stage.metrics_provider is None:
        raise ValueError("Stage does not have a metrics provider")
    metrics_provider = stage.metrics_provider
    return metrics_provider.callable(dataset_path)


def run_curriculum(args: CurriculumCliArgs) -> CurriculumSuggestion[TrainerState[Any], Any]:
    metrics: aind_behavior_curriculum.Metrics
    trainer_state = trainer_state_from_file(args.input_trainer_state)
    metrics = metrics_from_dataset_path(args.data_directory, trainer_state)
    trainer_state = TRAINER.evaluate(trainer_state, metrics)
    return CurriculumSuggestion(trainer_state=trainer_state, metrics=metrics, version=__semver__)
