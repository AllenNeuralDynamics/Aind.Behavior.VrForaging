from pathlib import Path

import aind_behavior_vr_foraging.rig
import aind_behavior_vr_foraging.session
import aind_behavior_vr_foraging.task_logic
from aind_behavior_services.utils import convert_pydantic_to_bonsai

SCHEMA_ROOT = Path("./src/DataSchemas/")
EXTENSIONS_ROOT = Path("./src/Extensions/")
NAMESPACE_PREFIX = "AindVrForagingDataSchema"


def main():
    models = {
        "aind_vr_foraging_task": aind_behavior_vr_foraging.task_logic.schema(),
        "aind_vr_foraging_session": aind_behavior_vr_foraging.session.schema(),
        "aind_vr_foraging_rig": aind_behavior_vr_foraging.rig.schema(),
    }
    convert_pydantic_to_bonsai(
        models, schema_path=SCHEMA_ROOT, output_path=EXTENSIONS_ROOT, namespace_prefix=NAMESPACE_PREFIX
    )


if __name__ == "__main__":
    main()
