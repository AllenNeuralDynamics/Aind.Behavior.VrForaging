import os
from pathlib import Path

from aind_behavior_vr_foraging.data_contract import dataset as vr_foraging_dataset
from pydantic import Field, ValidationError

from ..depletion.metrics import DepletionCurriculumMetrics
from ..depletion.metrics import metrics_from_dataset as depletion_metrics_from_dataset
from .utils import estimate_replenishment_rate, get_replenishment_function

PAST_METRICS_RELATIVE_PATH = Path("behavior/Logs/past_metrics.jsonl")


class ReplenishmentSessionMetrics(DepletionCurriculumMetrics):
    stage_name: str = Field(description="Name of the stage the session was run in.")
    replenishment_rate: float = Field(description="Replenishment rate (1/s) the session was run with.")
    session_id: str | None = Field(default=None, description="Unique identifier for the session.")


class ReplenishmentCurriculumMetrics(ReplenishmentSessionMetrics):
    # Excluded from serialization so that serialized metrics can be appended to past_metrics.jsonl without nesting
    past_sessions: list[ReplenishmentSessionMetrics] = Field(
        default_factory=list,
        exclude=True,
        description="Metrics of previous sessions, oldest first.",
    )


def past_sessions_from_file(path: os.PathLike) -> list[ReplenishmentSessionMetrics]:
    """Reads a jsonl file of `ReplenishmentSessionMetrics`. A missing file means there is no history.
    Lines that cannot be deserialized are silently dropped."""
    path = Path(path)
    if not path.exists():
        return []
    sessions: list[ReplenishmentSessionMetrics] = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            try:
                sessions.append(ReplenishmentSessionMetrics.model_validate_json(line))
            except ValidationError:
                continue
    return sessions


def metrics_from_dataset(data_directory: os.PathLike) -> ReplenishmentCurriculumMetrics:
    base = depletion_metrics_from_dataset(data_directory)
    input_schemas = vr_foraging_dataset(data_directory)["Behavior"]["InputSchemas"]
    task_logic = input_schemas["TaskLogic"].load().data
    patches = task_logic.task_parameters.environment.blocks[0].environment.patches
    session_id = input_schemas["Session"].load().data.session_name
    rate = estimate_replenishment_rate(get_replenishment_function(patches[0]).probability.transition_matrix)
    return ReplenishmentCurriculumMetrics(
        **base.model_dump(),
        session_id=session_id,
        stage_name=task_logic.stage_name,
        replenishment_rate=rate,
        past_sessions=past_sessions_from_file(Path(data_directory) / PAST_METRICS_RELATIVE_PATH),
    )
