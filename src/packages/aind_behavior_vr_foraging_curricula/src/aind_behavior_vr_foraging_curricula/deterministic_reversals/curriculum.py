from ._curriculum_builder import build_deterministic_reversal_curriculum
from .stages import make_s_stage_all_odors_rewarded, make_s_stage_graduation

CURRICULUM_NAME = "DeterministicReversals"
PKG_LOCATION = ".".join(__name__.split(".")[:-1])

CURRICULUM, TRAINER, run_curriculum = build_deterministic_reversal_curriculum(
    CURRICULUM_NAME,
    PKG_LOCATION,
    make_s_stage_all_odors_rewarded,
    make_s_stage_graduation,
)
