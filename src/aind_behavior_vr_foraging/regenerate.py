from pathlib import Path
from typing import Union

import pydantic
from aind_behavior_services.schema import BonsaiSgenSerializers, convert_pydantic_to_bonsai
from aind_behavior_services.session import Session

import aind_behavior_vr_foraging.rig
import aind_behavior_vr_foraging.task

SCHEMA_ROOT = Path("./src/DataSchemas/")
EXTENSIONS_ROOT = Path("./src/Extensions/")
NAMESPACE_PREFIX = "AindVrForagingDataSchema"


def main():
    models = [
        aind_behavior_vr_foraging.task.AindVrForagingTaskLogic,
        aind_behavior_vr_foraging.rig.AindVrForagingRig,
        Session,
        aind_behavior_vr_foraging.task.VirtualSite,
        aind_behavior_vr_foraging.task.VisualCorridor,
    ]
    model = pydantic.RootModel[Union[tuple(models)]]

    convert_pydantic_to_bonsai(
        model,
        model_name="aind_behavior_vr_foraging",
        root_element="Root",
        cs_namespace=NAMESPACE_PREFIX,
        json_schema_output_dir=SCHEMA_ROOT,
        cs_output_dir=EXTENSIONS_ROOT,
        cs_serializer=[BonsaiSgenSerializers.JSON],
    )


if __name__ == "__main__":
    main()
