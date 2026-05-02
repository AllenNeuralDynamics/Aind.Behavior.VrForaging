import os
from pathlib import Path
from typing import Any, TypeVar, Union

import aind_behavior_curriculum
import pydantic

# This curriculum only has 2 stages and a single transition from stage 1 to stage 2
# The first stage has a single policy that update suggestions while stage 1 is active
from aind_behavior_curriculum import (
    Metrics,
    StageTransition,
    Trainer,
    TrainerState,
    create_curriculum,
)
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .. import __semver__
from ..cli import CurriculumCliArgs, CurriculumSuggestion, model_from_json_file
from .metrics import VrForagingTemplateMetrics
from .stages import s_stage_a, s_stage_b

CURRICULUM_NAME = "TemplateCurriculum"
PKG_LOCATION = ".".join(__name__.split(".")[:-1])

TModel = TypeVar("TModel", bound=pydantic.BaseModel)


# ============================================================
# Stage transitions
# ============================================================


def st_s_stage_a_s_stage_b(metrics: VrForagingTemplateMetrics) -> bool:
    return metrics.metric1 > 1


# ============================================================
# Curriculum definition
# ============================================================

curriculum_class: type = create_curriculum(
    CURRICULUM_NAME, __semver__, (AindVrForagingTaskLogic,), pkg_location=PKG_LOCATION
)
CURRICULUM = curriculum_class()


CURRICULUM.add_stage_transition(s_stage_a, s_stage_b, StageTransition(st_s_stage_a_s_stage_b))

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
    if args.data_directory == Path("demo"):
        from . import __test_placeholder

        trainer_state, metrics = __test_placeholder.make()

    else:
        trainer_state = trainer_state_from_file(args.input_trainer_state)
        metrics = metrics_from_dataset_path(args.data_directory, trainer_state)
        return CurriculumSuggestion(
            trainer_state=trainer_state, metrics=metrics, dsl_version=aind_behavior_curriculum.__version__
        )
    trainer_state = TRAINER.evaluate(trainer_state, metrics)
    return CurriculumSuggestion(trainer_state=trainer_state, metrics=metrics, version=__semver__)
