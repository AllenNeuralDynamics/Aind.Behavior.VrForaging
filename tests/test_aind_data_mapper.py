import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_data_schema.core import acquisition, instrument
from aind_data_schema.utils import compatibility_check
from clabe.apps import BonsaiAppSettings
from git import Repo

from aind_behavior_vr_foraging.data_mappers import AindRigDataMapper, AindSessionDataMapper

sys.path.append(".")
from examples.rig import rig
from examples.session import session
from examples.task_patch_foraging import task_logic


class TestAindSessionDataMapper(unittest.TestCase):
    def setUp(self):
        self.session = session
        self.rig = rig
        self.task_logic = task_logic
        self.repository = Repo(Path("./"))
        self.bonsai_app_settings = BonsaiAppSettings(workflow=Path("./src/main.bonsai"))
        self.session_end_time = datetime.now()
        self.session_directory = None

        self.mapper = AindSessionDataMapper(
            session=self.session,
            rig=self.rig,
            task_logic=self.task_logic,
            repository=self.repository,
            bonsai_app_settings=self.bonsai_app_settings,
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
        self.rig = rig
        self.mapper = AindRigDataMapper(
            rig=self.rig,
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
        self.rig = rig
        self.session = session
        self.task_logic = task_logic
        self.rig_mapper = AindRigDataMapper(
            rig=self.rig,
        )
        self.bonsai_app_settings = BonsaiAppSettings(workflow=Path("./src/main.bonsai"))

        self.session_mapper = AindSessionDataMapper(
            session=self.session,
            rig=self.rig,
            task_logic=self.task_logic,
            repository=Repo(Path("./")),
            bonsai_app_settings=self.bonsai_app_settings,
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
