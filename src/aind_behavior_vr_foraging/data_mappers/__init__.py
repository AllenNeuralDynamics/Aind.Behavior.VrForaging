import logging
import os
from pathlib import Path
from typing import Optional

import pydantic
import pydantic_settings
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import model_from_json_file
from clabe.apps import BonsaiApp, CurriculumSuggestion
from git import Repo

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from ._rig import AindRigDataMapper
from ._session import AindSessionDataMapper

logger = logging.getLogger(__name__)


class DataMapperCli(pydantic_settings.BaseSettings, cli_kebab_case=True):
    data_path: os.PathLike = pydantic.Field(description="Path to the session data directory.")
    repo_path: os.PathLike = pydantic.Field(
        default=Path("."), description="Path to the repository. By default it will use the current directory."
    )
    curriculum_suggestion: Optional[os.PathLike] = pydantic.Field(
        default=None, description="Path to curriculum suggestion file."
    )

    def cli_cmd(self):
        logger.info("Mapping metadata directly from dataset.")
        abs_schemas_path = Path(self.data_path) / "Behavior" / "Logs"
        session = model_from_json_file(abs_schemas_path / "session_input.json", AindBehaviorSessionModel)
        rig = model_from_json_file(abs_schemas_path / "rig_input.json", AindVrForagingRig)
        task_logic = model_from_json_file(abs_schemas_path / "tasklogic_input.json", AindVrForagingTaskLogic)

        if self.curriculum_suggestion is not None:
            curriculum_suggestion = model_from_json_file(Path(self.curriculum_suggestion), CurriculumSuggestion)
        else:
            curriculum_suggestion = None

        repo = Repo(self.repo_path)
        settings = BonsaiApp(
            workflow=Path(repo.working_dir) / "src" / "main.bonsai",
            executable=Path(repo.working_dir) / "bonsai/bonsai.exe",
        )

        session_mapped = AindSessionDataMapper(
            session=session,
            rig=rig,
            task_logic=task_logic,
            repository=repo,
            bonsai_app=settings,
            curriculum_suggestion=curriculum_suggestion,
        ).map()
        rig_mapped = AindRigDataMapper(rig=rig).map()

        assert session.session_name is not None
        assert session_mapped is not None

        session_mapped.instrument_id = rig_mapped.instrument_id
        logger.info("Writing session.json to %s", self.data_path)
        session_mapped.write_standard_file(Path(self.data_path))
        logger.info("Writing rig.json to %s", self.data_path)
        rig_mapped.write_standard_file(Path(self.data_path))
        logger.info("Mapping completed!")


if __name__ == "__main__":
    pydantic_settings.CliApp().run(DataMapperCli)
