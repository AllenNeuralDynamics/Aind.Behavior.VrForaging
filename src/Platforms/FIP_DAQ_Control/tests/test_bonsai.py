import os
import sys
import unittest
import warnings
from pathlib import Path
from typing import Generic, List, Optional, TypeVar, Union

from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import run_bonsai_process
from pydantic import ValidationError

from aind_physiology_fip.rig import AindPhysioFipRig

sys.path.append(".")
from examples import example  # isort:skip # pylint: disable=wrong-import-position
from tests import JSON_ROOT  # isort:skip # pylint: disable=wrong-import-position

TModel = TypeVar("TModel", bound=Union[AindPhysioFipRig, AindBehaviorSessionModel])


class BonsaiTests(unittest.TestCase):
    def test_deserialization(self):
        example.main()

        models_to_test = [
            TestModel(bonsai_property="SessionPath", json_root=JSON_ROOT, model=AindBehaviorSessionModel),
            TestModel(bonsai_property="RigPath", json_root=JSON_ROOT, model=AindPhysioFipRig),
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

        with warnings.catch_warnings():  # suppress the warnings relative to the coercion of version across schemas
            warnings.simplefilter("ignore")
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
        if not self.input_model:
            raise ValueError("Input model is not set.")
        if not self.deserialized_model:
            raise ValueError("Deserialized model is not set.")
        _round_trip = self.input_model.model_validate_json(self.input_model.model_dump_json())
        return _round_trip == self.deserialized_model

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
