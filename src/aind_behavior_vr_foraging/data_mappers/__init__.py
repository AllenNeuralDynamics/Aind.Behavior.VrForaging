import logging
from pathlib import Path
from typing import TYPE_CHECKING

from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import model_from_json_file
from clabe.apps import BonsaiApp, CurriculumSuggestion
from git import Repo

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from ._rig import AindRigDataMapper
from ._session import AindSessionDataMapper

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aind_behavior_vr_foraging.cli import DataMapperCli


def cli_cmd(cli_settings: "DataMapperCli"):
    """Generate aind-data-schema metadata for the VR Foraging dataset located at the specified path."""
    logger.info("Mapping metadata directly from dataset.")
    abs_schemas_path = Path(cli_settings.data_path) / "Behavior" / "Logs"
    session = model_from_json_file(abs_schemas_path / "session_input.json", AindBehaviorSessionModel)
    rig = model_from_json_file(abs_schemas_path / "rig_input.json", AindVrForagingRig)
    task_logic = model_from_json_file(abs_schemas_path / "tasklogic_input.json", AindVrForagingTaskLogic)

    if cli_settings.curriculum_suggestion is not None:
        curriculum_suggestion = model_from_json_file(Path(cli_settings.curriculum_suggestion), CurriculumSuggestion)
    else:
        curriculum_suggestion = None

    repo = Repo(cli_settings.repo_path)
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
    logger.info("Writing session.json to %s", cli_settings.data_path)
    session_mapped.write_standard_file(Path(cli_settings.data_path))
    logger.info("Writing rig.json to %s", cli_settings.data_path)
    rig_mapped.write_standard_file(Path(cli_settings.data_path))
    logger.info("Mapping completed!")
