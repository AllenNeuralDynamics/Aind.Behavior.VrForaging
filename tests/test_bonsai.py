import os
import sys
import unittest
from pathlib import Path
from typing import Generic, List, Optional, TypeVar, Union

from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import run_bonsai_process
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from pydantic import ValidationError

sys.path.append(".")
from examples import examples  # noqa: E402 # isort:skip # pylint: disable=wrong-import-position
from tests import JSON_ROOT  # noqa: E402 # isort:skip # pylint: disable=wrong-import-position

TModel = TypeVar("TModel", bound=Union[AindVrForagingRig, AindVrForagingTaskLogic, AindBehaviorSessionModel])


class BonsaiTests(unittest.TestCase):
    def test_deserialization(self):

        examples.main("./local/{schema}.json")

        models_to_test = [
            TestModel(bonsai_property="SessionPath", json_root=JSON_ROOT, model=AindBehaviorSessionModel),
            TestModel(bonsai_property="RigPath", json_root=JSON_ROOT, model=AindVrForagingRig),
            TestModel(bonsai_property="TaskLogicPath", json_root=JSON_ROOT, model=AindVrForagingTaskLogic),
        ]

        workflow_props = {
            bonsai_prop: path
            for bonsai_prop, path in zip(
                [model.bonsai_property for model in models_to_test], [model.json_path for model in models_to_test]
            )
        }

        completed_proc = run_bonsai_process(
            workflow_file=Path("./src/test_deserialization.bonsai").resolve(),
            is_editor_mode=False,
            layout=None,
            additional_properties=workflow_props,
        )
        stdout = completed_proc.stdout.decode().split("\n")
        stdout = [line for line in stdout if (line or line != "")]

        for model in models_to_test:
            try:
                model.try_deserialization(stdout)
            except ValueError:
                self.fail(f"Could not find a match for {model.input_model.__class__.__name__}.")


class TestModel(Generic[TModel]):
    def __init__(self, bonsai_property: str, json_root: Path, model: TModel):
        self.bonsai_property: str = bonsai_property
        self.json_path: Path = json_root / f"{model.__name__}.json"
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"File {self.json_path} does not exist")
        self.input_model: TModel = model.model_validate_json(self.read_json(self.json_path))
        self.deserialized_model: Optional[TModel] = None

    def validate_deserialization(self) -> bool:
        return self.input_model == self.deserialized_model

    def try_deserialization(self, json_str: Union[str, List[str]]) -> TModel:
        _deserialized: Optional[TModel] = None
        if isinstance(json_str, list):
            for json_file in json_str:
                _deserialized = self._deserialize(self.input_model, json_file)
                if _deserialized:
                    break
        else:
            _deserialized = self._deserialize(self.input_model, json_str)

        if _deserialized:
            self.deserialized_model = _deserialized
            return _deserialized
        else:
            raise ValueError("Could not deserialize any of the input models.")

    @staticmethod
    def read_json(json_path: Path) -> str:
        with open(json_path, "r", encoding="utf-8") as json_file:
            return json_file.read()

    @staticmethod
    def _deserialize(model: TModel, json_str: str) -> Optional[TModel]:
        try:
            return model.model_validate_json(json_str, strict=True)
        except ValidationError:
            return None

    def __str__(self) -> str:
        return f"{self.bonsai_property} - {self.input_model.__class__.__name__} @ {self.json_path}"

    def __repr__(self) -> str:
        return self.__str__()


if __name__ == "__main__":
    unittest.main()
