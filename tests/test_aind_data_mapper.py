import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import aind_behavior_curriculum
from aind_behavior_curriculum import Metrics, Stage, Trainer, create_curriculum
from aind_data_schema.core import acquisition, instrument
from aind_data_schema.utils import compatibility_check
from clabe.apps import CurriculumSuggestion

from aind_behavior_vr_foraging.data_mappers._acquisition import AindAcquisitionDataMapper
from aind_behavior_vr_foraging.data_mappers._instrument import AindInstrumentDataMapper

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

    @patch("aind_behavior_vr_foraging.data_mappers._acquisition.AindAcquisitionDataMapper._map")
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

    @patch("aind_behavior_vr_foraging.data_mappers._instrument.AindInstrumentDataMapper._map")
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


def _make_curriculum_suggestion() -> CurriculumSuggestion:
    """Create a minimal CurriculumSuggestion using aind_behavior_curriculum primitives.

    Uses the same pattern as the 'demo' mode of the template curriculum:
    trainer_state and metrics are constructed programmatically without real session data.
    """

    class _DemoMetrics(Metrics):
        reward_rate: float = 0.75
        trials_count: int = 100

    curriculum_class = create_curriculum(
        "DemoCurriculum",
        "0.0.0",
        (task_logic.__class__,),
        pkg_location="demo.curriculum",
    )
    curriculum = curriculum_class()
    stage = Stage(name="demo_stage", task=task_logic)
    curriculum.add_stage(stage)
    trainer = Trainer(curriculum)
    trainer_state = trainer.create_trainer_state(
        stage=stage,
        is_on_curriculum=True,
        active_policies=tuple(),
    )
    metrics = _DemoMetrics()
    return CurriculumSuggestion(
        trainer_state=trainer_state,
        metrics=metrics,
        version="0.0.0",
        dsl_version=aind_behavior_curriculum.__version__,
    )


class TestCurriculumIntegrationInDataMapper(unittest.TestCase):
    """Tests that AindAcquisitionDataMapper correctly integrates curriculum suggestion data."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = Path(self.temp_dir.name)

        logs_dir = self.data_path / "Behavior" / "Logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        with open(logs_dir / "session_input.json", "w", encoding="utf-8") as f:
            json.dump(session.model_dump(mode="json"), f, indent=2)
        with open(logs_dir / "rig_input.json", "w", encoding="utf-8") as f:
            json.dump(rig.model_dump(mode="json"), f, indent=2)
        with open(logs_dir / "tasklogic_input.json", "w", encoding="utf-8") as f:
            json.dump(task_logic.model_dump(mode="json"), f, indent=2)

        self.curriculum_suggestion = _make_curriculum_suggestion()

        # Write trainer_state.json so the mapper picks up curriculum_status / training_protocol_name
        trainer_state_path = self.data_path / "Behavior" / "trainer_state.json"
        trainer_state_path.write_text(self.curriculum_suggestion.trainer_state.model_dump_json(), encoding="utf-8")

        self.repo_path = Path("./")
        self.session_end_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _make_mapper(self, curriculum_suggestion=None) -> AindAcquisitionDataMapper:
        return AindAcquisitionDataMapper(
            data_path=self.data_path,
            repo_path=self.repo_path,
            session_end_time=self.session_end_time,
            curriculum_suggestion=curriculum_suggestion,
        )

    def test_curriculum_suggestion_instance_is_accepted(self):
        """Passing a CurriculumSuggestion instance is stored on the mapper."""
        mapper = self._make_mapper(self.curriculum_suggestion)
        self.assertIs(mapper.curriculum_suggestion, self.curriculum_suggestion)

    def test_curriculum_suggestion_from_json_file(self):
        """Passing a file path loads the suggestion via JSON round-trip."""
        suggestion_path = Path(self.temp_dir.name) / "suggestion.json"
        suggestion_path.write_text(self.curriculum_suggestion.model_dump_json(), encoding="utf-8")

        mapper = self._make_mapper(suggestion_path)
        self.assertIsNotNone(mapper.curriculum_suggestion)
        self.assertEqual(
            mapper.curriculum_suggestion.trainer_state.curriculum.name,
            self.curriculum_suggestion.trainer_state.curriculum.name,
        )

    def test_stimulus_epoch_has_performance_metrics(self):
        """Performance metrics from the suggestion appear in the mapped stimulus epoch."""
        mapped = self._make_mapper(self.curriculum_suggestion).map()
        epoch = mapped.stimulus_epochs[0]
        self.assertIsNotNone(epoch.performance_metrics)
        output_params = epoch.performance_metrics.output_parameters.model_dump()
        self.assertIn("reward_rate", output_params)
        self.assertAlmostEqual(output_params["reward_rate"], 0.75)

    def test_stimulus_epoch_has_curriculum_status(self):
        """curriculum_status in the stimulus epoch matches the stage name."""
        mapped = self._make_mapper(self.curriculum_suggestion).map()
        epoch = mapped.stimulus_epochs[0]
        self.assertEqual(epoch.curriculum_status, "demo_stage")

    def test_stimulus_epoch_has_training_protocol_name(self):
        """training_protocol_name in the stimulus epoch matches the curriculum name."""
        mapped = self._make_mapper(self.curriculum_suggestion).map()
        epoch = mapped.stimulus_epochs[0]
        self.assertEqual(epoch.training_protocol_name, "DemoCurriculum")

    def test_data_stream_includes_curriculum_code(self):
        """When on curriculum, the data stream code list includes the curriculum entry."""
        mapped = self._make_mapper(self.curriculum_suggestion).map()
        stream = mapped.data_streams[0]
        code_names = [c.name for c in stream.code if c.name is not None]
        self.assertIn("demo.curriculum", code_names)

    def test_curriculum_code_metadata(self):
        """Curriculum Code entry carries the expected metadata from the submodule and suggestion."""
        import git

        repo = git.Repo("./")
        submodule = next(sub for sub in repo.submodules if sub.path == "plugins/curricula")

        mapped = self._make_mapper(self.curriculum_suggestion).map()
        stream = mapped.data_streams[0]
        curriculum_code = next(c for c in stream.code if c.name == "demo.curriculum")

        self.assertEqual(curriculum_code.url, submodule.url)
        self.assertEqual(
            curriculum_code.version,
            self.curriculum_suggestion.trainer_state.curriculum.version,
        )
        self.assertEqual(curriculum_code.language, "aind-behavior-curriculum")
        self.assertEqual(curriculum_code.language_version, self.curriculum_suggestion.dsl_version)

    def test_no_curriculum_suggestion_omits_curriculum_fields(self):
        """Without a suggestion, performance_metrics is absent.

        Note: curriculum_status and training_protocol_name are sourced from the
        trainer_state.json file (self.trainer_state), which is independent of the
        curriculum_suggestion argument.  They will be set whenever trainer_state.json
        exists, regardless of whether a suggestion is provided.
        """
        mapped = self._make_mapper(curriculum_suggestion=None).map()
        epoch = mapped.stimulus_epochs[0]
        self.assertIsNone(epoch.performance_metrics)

    def test_acquisition_round_trip_with_curriculum(self):
        """Mapped acquisition with curriculum data survives a JSON round-trip."""
        mapped = self._make_mapper(self.curriculum_suggestion).map()
        acquisition.Acquisition.model_validate_json(mapped.model_dump_json())


if __name__ == "__main__":
    unittest.main()
