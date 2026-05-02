# DO NOT RE-IMPLEMENT THIS FILE. THIS EXISTS FOR TESTING PURPOSES ONLY
from aind_behavior_curriculum import Policy, TrainerState

from .curriculum import (
    TRAINER,
    s_stage_a,
)
from .metrics import VrForagingTemplateMetrics
from .stages import p_set_mode_from_metric1

trainer_state = TRAINER.create_trainer_state(
    stage=s_stage_a,
    is_on_curriculum=True,
    active_policies=tuple([Policy(x) for x in [p_set_mode_from_metric1]]),
)

metrics = VrForagingTemplateMetrics(metric1=50, metric2_history=[1.0, 2.0, 3.0])


def make() -> tuple[TrainerState, VrForagingTemplateMetrics]:
    return trainer_state, metrics
