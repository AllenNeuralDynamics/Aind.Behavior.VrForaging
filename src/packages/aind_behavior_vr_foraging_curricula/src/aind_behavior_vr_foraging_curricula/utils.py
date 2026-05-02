import os
from pathlib import Path
from typing import Any, TypeVar

import pydantic
from aind_behavior_curriculum import Curriculum, Metrics, Trainer, TrainerState

TModel = TypeVar("TModel", bound=pydantic.BaseModel)
TCurriculum = TypeVar("TCurriculum", bound=Curriculum)


def model_from_json_file(json_path: os.PathLike | str, model: type[TModel]) -> TModel:
    with open(Path(json_path), "r", encoding="utf-8") as file:
        return model.model_validate_json(file.read())


def trainer_state_from_file(path: str | os.PathLike, trainer: Trainer[TCurriculum]) -> TrainerState[TCurriculum]:
    return model_from_json_file(path, trainer.trainer_state_model)


def metrics_from_dataset_path(dataset_path: str | os.PathLike, trainer_state: TrainerState[Any]) -> Metrics:
    stage = trainer_state.stage
    if stage is None:
        raise ValueError("Trainer state does not have a stage")
    if stage.metrics_provider is None:
        raise ValueError("Stage does not have a metrics provider")
    metrics_provider = stage.metrics_provider
    return metrics_provider.callable(dataset_path)
