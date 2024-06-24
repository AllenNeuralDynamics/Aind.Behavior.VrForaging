import inspect
from pathlib import Path
from pydantic import BaseModel

import aind_behavior_vr_foraging.rig
import aind_behavior_vr_foraging.task_logic
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import (
    convert_pydantic_to_bonsai,
    pascal_to_snake_case,
    snake_to_pascal_case,
)

SCHEMA_ROOT = Path("./src/DataSchemas/")
EXTENSIONS_ROOT = Path("./src/Extensions/")
NAMESPACE_PREFIX = "AindVrForagingDataSchema"


class SchemaContainer(BaseModel):
    rig: aind_behavior_vr_foraging.rig.AindVrForagingRig
    task_logic: aind_behavior_vr_foraging.task_logic.AindVrForagingTaskLogic
    session: AindBehaviorSessionModel


def main():

    models = [
        SchemaContainer
    ]

    for model in models:
        module_name = inspect.getmodule(model).__name__
        module_name = module_name.split(".")[-1]
        schema_name = f"{pascal_to_snake_case(model.__name__)}"
        namespace = "AindVrForaging"

        print((schema_name, namespace))
        convert_pydantic_to_bonsai(
            {schema_name: model}, schema_path=SCHEMA_ROOT, output_path=EXTENSIONS_ROOT, namespace=namespace
        )


if __name__ == "__main__":
    main()
