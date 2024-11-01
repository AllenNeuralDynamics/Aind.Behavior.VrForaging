import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_behavior_vr_foraging.data_mappers import (
    AindBehaviorSessionModel,
    AindRigDataMapper,
    AindSessionDataMapper,
    AindVrForagingRig,
    AindVrForagingTaskLogic,
)
from aind_data_schema.core.rig import Rig
from git import Repo

sys.path.append(".")
from examples.examples import mock_rig, mock_session, mock_task_logic  # isort:skip # pylint: disable=wrong-import-position


class TestAindSessionDataMapper(unittest.TestCase):
    def setUp(self):
        self.session_model = mock_session()
        self.rig_model = mock_rig()
        self.task_logic_model = mock_task_logic()
        self.repository = Repo(Path("./"))
        self.script_path = Path("./src/vr-foraging.bonsai")
        self.session_end_time = datetime.now()
        self.session_directory = Path("./")

        self.mapper = AindSessionDataMapper(
            session_model=self.session_model,
            rig_model=self.rig_model,
            task_logic_model=self.task_logic_model,
            repository=self.repository,
            script_path=self.script_path,
            session_end_time=self.session_end_time,
            session_directory=self.session_directory,
        )

    def test_validate(self):
        self.assertTrue(self.mapper.validate())

    @patch("aind_behavior_vr_foraging.data_mappers.logger")
    @patch("aind_behavior_vr_foraging.data_mappers.AindSessionDataMapper._map")
    def test_mock_map(self, mock_map, mock_logger):
        mock_map.return_value = MagicMock()
        result = self.mapper.map()
        self.assertIsNotNone(result)
        self.assertTrue(self.mapper.is_mapped())
        mock_logger.info.assert_called_with("Mapping successful.")

    def test_map(self):
        mapped = self.mapper.map()
        self.assertIsNotNone(mapped)

    @patch("aind_behavior_vr_foraging.data_mappers.model_from_json_file")
    def test_map_from_json_files(self, mock_model_from_json_file):
        mock_model_from_json_file.side_effect = [self.session_model, self.rig_model, self.task_logic_model]
        session_json = MagicMock()
        rig_json = MagicMock()
        task_logic_json = MagicMock()
        mapper = AindSessionDataMapper.map_from_json_files(
            session_json=session_json,
            rig_json=rig_json,
            task_logic_json=task_logic_json,
            session_model=AindBehaviorSessionModel,
            rig_model=AindVrForagingRig,
            task_logic_model=AindVrForagingTaskLogic,
            repository=self.repository,
            script_path=self.script_path,
            session_end_time=self.session_end_time,
        )
        self.assertIsInstance(mapper, AindSessionDataMapper)


class TestAindRigDataMapper(unittest.TestCase):
    def setUp(self):
        self.rig_schema_filename = "rig_schema.json"
        self.db_root = MagicMock()
        self.destination_dir = MagicMock()
        self.db_suffix = "test_suffix"
        self.mapper = AindRigDataMapper(
            rig_schema_filename=self.rig_schema_filename,
            db_root=self.db_root,
            destination_dir=self.destination_dir,
            db_suffix=self.db_suffix,
        )

    @patch("aind_behavior_vr_foraging.data_mappers.model_from_json_file")
    def test_mock_map(self, mock_model_from_json_file):
        mock_model_from_json_file.return_value = MagicMock(spec=Rig)
        result = self.mapper.map()
        self.assertIsNotNone(result)
        self.assertTrue(self.mapper.mapped)
        self.assertIsInstance(result, Rig)


if __name__ == "__main__":
    unittest.main()
