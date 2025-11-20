import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ._rig import AindRigDataMapper
from ._session import AindSessionDataMapper

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aind_behavior_vr_foraging.cli import DataMapperCli


def cli_cmd(cli_settings: "DataMapperCli"):
    """Generate aind-data-schema metadata for the VR Foraging dataset located at the specified path."""
    session_mapped = AindSessionDataMapper(
        data_path=Path(cli_settings.data_path),
        repo_path=Path(cli_settings.repo_path),
        session_end_time=cli_settings.session_end_time,
    ).map()

    rig_mapped = AindRigDataMapper(data_path=Path(cli_settings.data_path)).map()

    assert session_mapped is not None

    session_mapped.instrument_id = rig_mapped.instrument_id
    logger.info("Writing session.json to %s", cli_settings.data_path)
    session_mapped.write_standard_file(Path(cli_settings.data_path))
    logger.info("Writing rig.json to %s", cli_settings.data_path)
    rig_mapped.write_standard_file(Path(cli_settings.data_path))
    logger.info("Mapping completed!")
