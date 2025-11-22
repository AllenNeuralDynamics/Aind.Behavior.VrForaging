import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_data_schema.core import acquisition, instrument
from aind_data_schema.utils import compatibility_check

from aind_behavior_vr_foraging.data_mappers._rig import AindInstrumentDataMapper
from aind_behavior_vr_foraging.data_mappers._session import AindAcquisitionDataMapper

sys.path.append(".")
from aind_behavior_vr_foraging.cli import DataMapperCli
from examples.rig import rig
from examples.session import session
from examples.task_patch_foraging import task_logic


class TestAindDataMappers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = Path(self.temp_dir.name)

        logs_dir = self.data_path / "Behavior" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        session_input_path = logs_dir / "session_input.json"
        with open(session_input_path, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(mode="json"), f, indent=2)

        rig_input_path = logs_dir / "rig_input.json"
        with open(rig_input_path, "w", encoding="utf-8") as f:
            json.dump(rig.model_dump(mode="json"), f, indent=2)

        tasklogic_input_path = logs_dir / "tasklogic_input.json"
        with open(tasklogic_input_path, "w", encoding="utf-8") as f:
            json.dump(task_logic.model_dump(mode="json"), f, indent=2)

        self.repo_path = Path("./")
        self.session_end_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        self.session_mapper = AindAcquisitionDataMapper(
            data_path=self.data_path,
            repo_path=self.repo_path,
            session_end_time=self.session_end_time,
        )

        self.rig_mapper = AindInstrumentDataMapper(data_path=self.data_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("aind_behavior_vr_foraging.data_mappers._session.AindAcquisitionDataMapper._map")
    def test_session_mock_map(self, mock_map):
        mock_map.return_value = MagicMock()
        result = self.session_mapper.map()
        self.assertIsNotNone(result)
        self.assertTrue(self.session_mapper.is_mapped())

    def test_session_map(self):
        mapped = self.session_mapper.map()
        self.assertIsNotNone(mapped)

    def test_session_round_trip(self):
        mapped = self.session_mapper.map()
        assert mapped is not None
        acquisition.Acquisition.model_validate_json(mapped.model_dump_json())

    @patch("aind_behavior_vr_foraging.data_mappers._rig.AindInstrumentDataMapper._map")
    def test_rig_mock_map(self, mock_map):
        mock_map.return_value = MagicMock()
        result = self.rig_mapper.map()
        self.assertIsNotNone(result)
        self.assertTrue(self.rig_mapper.is_mapped())

    def test_rig_map(self):
        mapped = self.rig_mapper.map()
        self.assertIsNotNone(mapped)

    def test_rig_round_trip(self):
        mapped = self.rig_mapper.map()
        assert mapped is not None
        instrument.Instrument.model_validate_json(mapped.model_dump_json())

    def test_instrument_acquisition_compatibility(self):
        session_mapped = self.session_mapper.map()
        assert session_mapped is not None
        rig_mapped = self.rig_mapper.map()
        assert rig_mapped is not None
        compatibility_check.InstrumentAcquisitionCompatibility(
            instrument=rig_mapped, acquisition=session_mapped
        ).run_compatibility_check(raise_for_missing_devices=True)

    def test_mapper_cli(self):
        DataMapperCli(
            data_path=self.data_path,
            repo_path=self.repo_path,
            session_end_time=self.session_end_time,
        ).cli_cmd()
        instrument_path = self.data_path / "instrument_vrforaging.json"
        acquisition_path = self.data_path / "acquisition_vrforaging.json"

        self.assertTrue(instrument_path.exists())
        self.assertTrue(acquisition_path.exists())


if __name__ == "__main__":
    unittest.main()
