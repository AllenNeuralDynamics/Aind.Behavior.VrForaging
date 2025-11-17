import typing as t
from pathlib import Path

import pydantic
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import BonsaiSgenSerializers, convert_pydantic_to_bonsai

from aind_physiology_fip import rig

SCHEMA_ROOT = Path("./src/DataSchemas/")
EXTENSIONS_ROOT = Path("./src/Extensions/")
NAMESPACE_PREFIX = "AindPhysiologyFip"


def main():
    models = [
        rig.AindPhysioFipRig,
        AindBehaviorSessionModel,
    ]

    model = pydantic.RootModel[t.Union[tuple(models)]]
    convert_pydantic_to_bonsai(
        model,
        model_name="aind_physiology_fip",
        root_element="Root",
        cs_namespace=NAMESPACE_PREFIX,
        json_schema_output_dir=SCHEMA_ROOT,
        cs_output_dir=EXTENSIONS_ROOT,
        cs_serializer=[BonsaiSgenSerializers.JSON],
    )


if __name__ == "__main__":
    main()
