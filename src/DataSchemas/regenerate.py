import json
from pathlib import Path

import aind_behavior_vr_foraging.rig
import aind_behavior_vr_foraging.session
import aind_behavior_vr_foraging.task_logic
from aind_behavior_services.utils import BonsaiSgenSerializers, bonsai_sgen, export_schema, snake_to_pascal_case

SCHEMA_ROOT = Path("./src/DataSchemas/")
EXTENSIONS_ROOT = Path("./src/Extensions/")
NAMESPACE_PREFIX = "AindVrForagingDataSchema"
SGEN_SERIALIZERS = [BonsaiSgenSerializers.JSON, BonsaiSgenSerializers.YAML]


def main():
    models = {
        "aind_vr_foraging_task": aind_behavior_vr_foraging.task_logic.schema(),
        "aind_vr_foraging_session": aind_behavior_vr_foraging.session.schema(),
        "aind_vr_foraging_rig": aind_behavior_vr_foraging.rig.schema(),
    }
    for output_model_name, model in models.items():
        with open(SCHEMA_ROOT / f"{output_model_name}.json", "w") as f:
            json_model = json.dumps(export_schema(model), indent=2)
            json_model = json_model.replace("$defs", "definitions")
            f.write(json_model)
        cmd_return = bonsai_sgen(
            schema_path=SCHEMA_ROOT / f"{output_model_name}.json",
            output_path=EXTENSIONS_ROOT / f"{snake_to_pascal_case(output_model_name)}.cs",
            namespace=f"{NAMESPACE_PREFIX}.{snake_to_pascal_case(output_model_name)}",
            serializer=SGEN_SERIALIZERS,
        )
        print(cmd_return.stdout)


if __name__ == "__main__":
    main()
