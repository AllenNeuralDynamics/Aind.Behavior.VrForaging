import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from aind_data_schema.core.rig import Rig
from git import Repo

from aind_behavior_vr_foraging.data_mappers import (
    AindRigDataMapper,
    AindSessionDataMapper,
)

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


class TestAindRigDataMapper(unittest.TestCase):
    def setUp(self):
        self.rig_schema_filename = "rig_schema.json"
        self.db_root = MagicMock()
        self.session_directory = MagicMock()
        self.db_suffix = "test_suffix"
        self.mapper = AindRigDataMapper(
            rig_schema_filename=self.rig_schema_filename,
            db_root=self.db_root,
            db_suffix=self.db_suffix,
        )

    @patch("pathlib.Path.exists", return_value=True)
    @patch("aind_behavior_vr_foraging.data_mappers.model_from_json_file")
    def test_mock_map(self, mock_model_from_json_file, mock_path_exists):
        mock_model_from_json_file.return_value = MagicMock(spec=Rig)
        result = self.mapper.map()
        self.assertIsNotNone(result)
        self.assertTrue(self.mapper.mapped)
        self.assertIsInstance(result, Rig)


if __name__ == "__main__":
    unittest.main()
