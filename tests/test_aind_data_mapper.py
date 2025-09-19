import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_data_schema.core import acquisition, instrument
from aind_data_schema.utils import compatibility_check
from git import Repo

from aind_behavior_vr_foraging.data_mappers import AindRigDataMapper, AindSessionDataMapper

sys.path.append(".")
from examples.examples import mock_rig, mock_session, mock_task_logic  # isort:skip # pylint: disable=wrong-import-position


class TestAindSessionDataMapper(unittest.TestCase):
    def setUp(self):
        self.session_model = mock_session()
        self.rig_model = mock_rig()
        self.task_logic_model = mock_task_logic()
        self.repository = Repo(Path("./"))
        self.script_path = Path("./src/main.bonsai")
        self.session_end_time = datetime.now()
        self.session_directory = None

        self.mapper = AindSessionDataMapper(
            session_model=self.session_model,
            rig_model=self.rig_model,
            task_logic_model=self.task_logic_model,
            repository=self.repository,
            script_path=self.script_path,
            session_end_time=self.session_end_time,
        )

    @patch("aind_behavior_vr_foraging.data_mappers.AindSessionDataMapper._map")
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
        self.rig_model = mock_rig()
        self.mapper = AindRigDataMapper(
            rig_model=self.rig_model,
        )

    @patch("aind_behavior_vr_foraging.data_mappers.AindRigDataMapper._map")
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
        self.rig_model = mock_rig()
        self.session_model = mock_session()
        self.task_logic_model = mock_task_logic()
        self.rig_mapper = AindRigDataMapper(
            rig_model=self.rig_model,
        )
        self.session_mapper = AindSessionDataMapper(
            session_model=self.session_model,
            rig_model=self.rig_model,
            task_logic_model=self.task_logic_model,
            repository=Repo(Path("./")),
            script_path=Path("./src/main.bonsai"),
            session_end_time=datetime.now(),
        )

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
