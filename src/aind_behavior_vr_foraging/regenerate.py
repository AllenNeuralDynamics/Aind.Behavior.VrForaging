import json
from pathlib import Path
from typing import Union

import pydantic
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import (
    CustomGenerateJsonSchema,
    bonsai_sgen,
)

import aind_behavior_vr_foraging.rig
import aind_behavior_vr_foraging.task_logic

SCHEMA_ROOT = Path("./src/DataSchemas/")
EXTENSIONS_ROOT = Path("./src/Extensions/")
NAMESPACE_PREFIX = "AindVrForagingDataSchema"


def main():
    models = [
        aind_behavior_vr_foraging.task_logic.AindVrForagingTaskLogic,
        aind_behavior_vr_foraging.rig.AindVrForagingRig,
        AindBehaviorSessionModel,
        aind_behavior_vr_foraging.task_logic.VirtualSite,
        aind_behavior_vr_foraging.task_logic.VisualCorridor,
    ]
    model = pydantic.RootModel[Union[tuple(models)]]
    json_schema = model.model_json_schema(schema_generator=CustomGenerateJsonSchema, mode="serialization")
    for to_remove in ["$schema", "title", "description", "properties", "required", "type", "oneOf"]:
        json_schema.pop(to_remove, None)

    with open(schema_path := SCHEMA_ROOT / "aind-vr-foraging.json", "w", encoding="utf-8") as f:
        literal = json.dumps(json_schema, indent=2)
        f.write(literal)

    bonsai_sgen(
        schema_path=schema_path,
        root_element="Root",
        namespace=NAMESPACE_PREFIX,
        output_path=EXTENSIONS_ROOT / "AindBehaviorVrForaging.cs",
    )


if __name__ == "__main__":
    main()
