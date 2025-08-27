import logging
import os
from pathlib import Path

import pydantic
import pydantic_settings
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import model_from_json_file
from git import Repo

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from ._rig import AindRigDataMapper
from ._session import AindSessionDataMapper

logger = logging.getLogger(__name__)


class MapperCli(pydantic_settings.BaseSettings, cli_kebab_case=True):
    data_path: os.PathLike = pydantic.Field(description="Path to the session data directory.")
    db_root: os.PathLike = pydantic.Field(
        default=Path(r"\\allen\aind\scratch\AindBehavior.db\AindVrForaging"),
        description="Root directory for the database for additional metadata.",
    )
    repo_path: os.PathLike = pydantic.Field(
        default=Path("."), description="Path to the repository. By default it will use the current directory."
    )

    def cli_cmd(self):
        logger.info("Mapping metadata directly from dataset.")
        abs_schemas_path = Path(self.data_path) / "Behavior" / "Logs"
        session = model_from_json_file(abs_schemas_path / "session_input.json", AindBehaviorSessionModel)
        rig = model_from_json_file(abs_schemas_path / "rig_input.json", AindVrForagingRig)
        task_logic = model_from_json_file(abs_schemas_path / "tasklogic_input.json", AindVrForagingTaskLogic)
        repo = Repo(self.repo_path)
        session_mapped = AindSessionDataMapper(
            session_model=session,
            rig_model=rig,
            task_logic_model=task_logic,
            repository=repo,
            script_path=Path("./src/main.bonsai"),
        ).map()
        rig_mapped = AindRigDataMapper(rig_schema_filename=f"{rig.rig_name}.json", db_root=Path(self.db_root)).map()

        assert session.session_name is not None
        assert session_mapped is not None

        session_mapped.rig_id = rig_mapped.rig_id
        logger.info("Writing session.json to %s", self.data_path)
        session_mapped.write_standard_file(Path(self.data_path))
        logger.info("Writing rig.json to %s", self.data_path)
        rig_mapped.write_standard_file(Path(self.data_path))
        logger.info("Mapping completed!")


if __name__ == "__main__":
    pydantic_settings.CliApp().run(MapperCli)
