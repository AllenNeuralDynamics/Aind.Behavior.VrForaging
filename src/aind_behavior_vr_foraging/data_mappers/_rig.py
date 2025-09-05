import logging
import os
from pathlib import Path
from typing import Callable, Optional, Self

import pydantic
from aind_behavior_services.utils import model_from_json_file
from aind_data_schema.core import instrument
from clabe.data_mapper import aind_data_schema as ads
from clabe.launcher import DefaultBehaviorPicker, Launcher

logger = logging.getLogger(__name__)

_DATABASE_DIR = "AindDataSchemaRig"


class AindRigDataMapper(ads.AindDataSchemaRigDataMapper):
    def __init__(
        self,
        *,
        rig_schema_filename: str,
        db_root: os.PathLike,
        db_suffix: Optional[str] = None,
    ):
        super().__init__()
        self.filename = rig_schema_filename
        self.db_root = db_root
        self.db_dir = db_suffix if db_suffix else f"{_DATABASE_DIR}/{os.environ['COMPUTERNAME']}"
        self.target_file = Path(self.db_root) / self.db_dir / self.filename
        self._mapped: Optional[instrument.Instrument] = None

    def rig_schema(self):
        return self.mapped

    @property
    def session_name(self):
        raise NotImplementedError("Method not implemented.")

    def write_standard_file(self, directory: os.PathLike) -> None:
        self.mapped.write_standard_file(directory)

    def map(self) -> instrument.Instrument:
        logger.info("Mapping aind-data-schema Rig.")

        file_exists = self.target_file.exists()
        if not file_exists:
            raise FileNotFoundError(f"File {self.target_file} does not exist.")

        try:
            self._mapped = model_from_json_file(self.target_file, instrument.Instrument)
        except (pydantic.ValidationError, ValueError, IOError) as e:
            logger.error("Failed to map to aind-data-schema Session. %s", e)
            raise e
        else:
            return self.mapped

    @property
    def mapped(self) -> instrument.Instrument:
        if self._mapped is None:
            raise ValueError("Data has not been mapped yet.")
        return self._mapped

    def is_mapped(self) -> bool:
        return self.mapped is not None

    @classmethod
    def build_runner(cls, picker: DefaultBehaviorPicker) -> Callable[[Launcher], Self]:
        def _run(launcher: Launcher) -> Self:
            new = cls(
                rig_schema_filename=f"{launcher.get_rig(strict=True).rig_name}.json",
                db_suffix=f"{_DATABASE_DIR}/{launcher.computer_name}",
                db_root=picker.config_library_dir,
            )
            new.map()
            return new

        return _run
