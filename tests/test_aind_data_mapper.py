import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_data_schema.core import acquisition, instrument
from aind_data_schema.utils import compatibility_check

from aind_behavior_vr_foraging.data_mappers import AindRigDataMapper, AindSessionDataMapper

sys.path.append(".")
from examples.rig import rig
from examples.session import session
from examples.task_patch_foraging import task_logic


class TestAindSessionDataMapper(unittest.TestCase):
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

        self.mapper = AindSessionDataMapper(
            data_path=self.data_path,
            repo_path=self.repo_path,
            session_end_time=self.session_end_time,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("aind_behavior_vr_foraging.data_mappers._session.AindSessionDataMapper._map")
    def test_mock_map(self, mock_map):
        mock_map.return_value = MagicMock()
        result = self.mapper.map()
        self.assertIsNotNone(result)
        self.assertTrue(self.mapper.is_mapped())

    def test_map(self):
        mapped = self.mapper.map()
        self.assertIsNotNone(mapped)

    def test_round_trip(self):
        mapped = self.mapper.map()
        assert mapped is not None
        acquisition.Acquisition.model_validate_json(mapped.model_dump_json())


class TestAindRigDataMapper(unittest.TestCase):
    def setUp(self):
        self.rig = rig
        self.mapper = AindRigDataMapper(
            rig=self.rig,
        )

    @patch("aind_behavior_vr_foraging.data_mappers._rig.AindRigDataMapper._map")
    def test_mock_map(self, mock_map):
        mock_map.return_value = MagicMock()
        result = self.mapper.map()
        self.assertIsNotNone(result)
        self.assertTrue(self.mapper.is_mapped())

    def test_map(self):
        mapped = self.mapper.map()
        self.assertIsNotNone(mapped)

    def test_round_trip(self):
        mapped = self.mapper.map()
        assert mapped is not None
        instrument.Instrument.model_validate_json(mapped.model_dump_json())


class TestInstrumentAcquisitionCompatibility(unittest.TestCase):
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

        self.rig_mapper = AindRigDataMapper(rig=rig)

        self.session_mapper = AindSessionDataMapper(
            data_path=self.data_path,
            repo_path=self.repo_path,
            session_end_time=datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compatibility(self):
        session_mapped = self.session_mapper.map()
        assert session_mapped is not None
        rig_mapped = self.rig_mapper.map()
        assert rig_mapped is not None
        compatibility_check.InstrumentAcquisitionCompatibility(
            instrument=rig_mapped, acquisition=session_mapped
        ).run_compatibility_check()


if __name__ == "__main__":
    unittest.main()
