import sys

sys.path.append(".")
import datetime
import unittest
from pathlib import Path

from aind_behavior_vr_foraging.data_mappers import VrForagingToAindDataSchemaDataMapper

from examples.examples import mock_rig, mock_session, mock_task_logic


class AindServicesTests(unittest.TestCase):
    def test_session_mapper(self):
        VrForagingToAindDataSchemaDataMapper.map(
            schema_root=None,
            session_model=mock_session(),
            rig_model=mock_rig(),
            task_logic_model=mock_task_logic(),
            session_end_time=datetime.datetime(2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            repository=Path("./"),
            script_path=Path("./src/unit_test.bonsai"),
            bonsai_config_path=Path("./tests/assets/bonsai.config").resolve(),
        )
