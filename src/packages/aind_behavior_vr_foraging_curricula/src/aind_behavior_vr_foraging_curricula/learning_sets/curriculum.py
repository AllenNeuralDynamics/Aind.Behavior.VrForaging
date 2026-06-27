from typing import Any, Type, TypeVar

import aind_behavior_curriculum
import pydantic
from aind_behavior_curriculum import StageTransition, Trainer, TrainerState, create_curriculum
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .. import __semver__
from ..cli import CurriculumCliArgs, CurriculumSuggestion
from ..utils import metrics_from_dataset_path, trainer_state_from_file
from .helpers import N_SITES_EACH, VELOCITY_THRESHOLD_FLOOR
from .metrics import LearningSetsMetrics
from .stages import make_s_graduated, make_s_shaping

CURRICULUM_NAME = "LearningSets"
PKG_LOCATION = ".".join(__name__.split(".")[:-1])

TModel = TypeVar("TModel", bound=pydantic.BaseModel)


# ============================================================
# Stage transitions
# ============================================================


def st_shaping_to_graduated(metrics: LearningSetsMetrics) -> bool:
    """Graduate the shaping stage once the negative-site proportion has reached the full
    5+5 ratio, the stop-velocity threshold has been shaped down to its final floor, and
    the subject is discriminating (skipping a meaningful fraction of patches)."""
    if (
        metrics.last_n_neg_sites_per_pair is None
        or metrics.last_stop_velocity_threshold_updater is None
        or metrics.n_patches_seen == 0
    ):
        return False
    visit_ratio = metrics.n_patches_visited / metrics.n_patches_seen
    return (
        (metrics.last_n_neg_sites_per_pair >= N_SITES_EACH)
        and (metrics.last_stop_velocity_threshold_updater <= VELOCITY_THRESHOLD_FLOOR)
        and (metrics.n_patches_seen >= 200)
        and (visit_ratio <= 0.7)
    )


# ============================================================
# Curriculum definition
# ============================================================

curriculum_class: Type[aind_behavior_curriculum.Curriculum[AindVrForagingTaskLogic]] = create_curriculum(
    CURRICULUM_NAME, __semver__, (AindVrForagingTaskLogic,), pkg_location=PKG_LOCATION
)
CURRICULUM = curriculum_class()

CURRICULUM.add_stage_transition(
    make_s_shaping(),
    make_s_graduated(),
    StageTransition(st_shaping_to_graduated),
)

# ==============================================================================
# Trainer
# ==============================================================================

TRAINER = Trainer(CURRICULUM)


def run_curriculum(args: CurriculumCliArgs) -> CurriculumSuggestion[TrainerState[Any], Any]:
    metrics: aind_behavior_curriculum.Metrics
    trainer_state = trainer_state_from_file(args.input_trainer_state, TRAINER)
    metrics = metrics_from_dataset_path(args.data_directory, trainer_state)
    trainer_state = TRAINER.evaluate(trainer_state, metrics)
    return CurriculumSuggestion(trainer_state=trainer_state, metrics=metrics, version=__semver__)
