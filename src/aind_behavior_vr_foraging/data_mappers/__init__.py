import logging
import os
import typing as t
from pathlib import Path

from pydantic import AwareDatetime, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DataMapperCli(BaseSettings, cli_kebab_case=True):
    data_path: os.PathLike = Field(description="Path to the session data directory.")
    repo_path: os.PathLike = Field(
        default=Path("."), description="Path to the repository. By default it will use the current directory."
    )
    curriculum_suggestion: t.Optional[os.PathLike] = Field(
        default=None, description="Path to curriculum suggestion file."
    )
    session_end_time: AwareDatetime | None = Field(
        default=None,
        description="End time of the session in ISO format. If not provided, will use the time the data mapping is run.",
    )
    suffix: t.Optional[str] = Field(default="vrforaging", description="Suffix to append to the output filenames.")

    def cli_cmd(self):
        """Generate aind-data-schema metadata for the VR Foraging dataset located at the specified path."""
        from ._rig import AindInstrumentDataMapper
        from ._session import AindAcquisitionDataMapper

        session_mapper = AindAcquisitionDataMapper(
            data_path=Path(self.data_path),
            repo_path=Path(self.repo_path),
            session_end_time=self.session_end_time,
        )
        session_mapper.map()

        rig_mapper = AindInstrumentDataMapper(data_path=Path(self.data_path))
        rig_mapper.map()

        assert session_mapper.mapped is not None
        assert rig_mapper.mapped is not None

        session_mapper.mapped.instrument_id = rig_mapper.mapped.instrument_id
        session_mapper.mapped.write_standard_file(output_directory=Path(self.data_path), filename_suffix=self.suffix)
        rig_mapper.mapped.write_standard_file(output_directory=Path(self.data_path), filename_suffix=self.suffix)
        logger.info(
            "Mapping completed! Saved acquisition.json and instrument.json to %s",
            self.data_path,
        )
