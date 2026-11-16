from typing import Any, TypeVar

import aind_behavior_curriculum
import pydantic
from aind_behavior_curriculum import (
    Stage,
    StageTransition,
    Trainer,
    TrainerState,
    create_curriculum,
)
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .. import __semver__
from ..cli import CurriculumCliArgs, CurriculumSuggestion
from ..utils import metrics_from_dataset_path, trainer_state_from_file
from .metrics import DepletionCurriculumMetrics
from .stages import (
    SHAPING_ODOR_INDICES,
    make_s_stage_all_odors_rewarded,
    make_s_stage_graduation,
    make_s_stage_one_odor_no_depletion,
    make_s_stage_one_odor_w_depletion_day_0,
)

CURRICULUM_NAME = "Depletion"
PKG_LOCATION = ".".join(__name__.split(".")[:-1])

TModel = TypeVar("TModel", bound=pydantic.BaseModel)


# ============================================================
# Stage transitions
# ============================================================


def st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0(metrics: DepletionCurriculumMetrics) -> bool:
    if metrics.last_reward_site_length is None:
        return False
    return (
        (metrics.n_reward_sites_traveled > 200)
        and (metrics.n_choices > 150)
        and (metrics.last_reward_site_length >= 50)
    )


def st_s_stage_one_odor_w_depletion_day_0_s_stage_all_odors_rewarded(
    metrics: DepletionCurriculumMetrics,
) -> bool:
    return metrics.n_patches_visited > 20


def st_s_stage_all_odors_rewarded_s_stage_graduation(metrics: DepletionCurriculumMetrics) -> bool:
    patches = metrics.n_patches_visited_per_patch
    return patches.get(0, 0) > 10 and patches.get(1, 0) > 10


# ============================================================
# Parallel shaping tracks
# ============================================================


def add_shaping_tracks(
    curriculum: aind_behavior_curriculum.Curriculum,
    next_stage: Stage,
    odor_indices: tuple[int, ...] = SHAPING_ODOR_INDICES,
) -> None:
    """Add one shaping track per odor, all converging into ``next_stage``.

    Each track is ``one_odor_no_depletion -> one_odor_w_depletion_day_0`` using a single
    odor (see ``stages.shaping_stage_name`` for the naming). Tracks never cross: a subject
    stays on the odor it was enrolled with until it leaves shaping. Enroll a subject on a
    track by naming its first stage explicitly; the default enrollment (the first stage
    added to the graph) is the odor-0 track, so this must be called before any other
    stage is added to ``curriculum``.
    """
    for odor_index in odor_indices:
        no_depletion = make_s_stage_one_odor_no_depletion(odor_index)
        w_depletion = make_s_stage_one_odor_w_depletion_day_0(odor_index)
        curriculum.add_stage_transition(
            no_depletion,
            w_depletion,
            StageTransition(st_s_stage_one_odor_no_depletion_s_stage_one_odor_w_depletion_day_0),
        )
        curriculum.add_stage_transition(
            w_depletion,
            next_stage,
            StageTransition(st_s_stage_one_odor_w_depletion_day_0_s_stage_all_odors_rewarded),
        )


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
