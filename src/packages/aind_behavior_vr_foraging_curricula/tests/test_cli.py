import importlib
import logging
import os
import tempfile

from aind_behavior_curriculum import __version__ as dsl_version
from pydantic_settings import CliApp

from aind_behavior_vr_foraging_curricula import __version__ as version
from aind_behavior_vr_foraging_curricula.cli import _KNOWN_CURRICULA, CurriculumAppCliArgs, CurriculumInitCliArgs
from aind_behavior_vr_foraging_curricula.template import TRAINER, __test_placeholder


def test_known_curricula(capsys):
    CliApp.run(CurriculumAppCliArgs, cli_args=["list"])
    captured = capsys.readouterr()
    lines = captured.out.strip().split("\n")
    # Extract curriculum names from lines like " - template"
    recovered = [line.strip(" -") for line in lines if line.strip().startswith("-")]
    assert set(recovered) == set(_KNOWN_CURRICULA)


def test_version(capsys):
    CliApp.run(CurriculumAppCliArgs, cli_args=["version"])
    captured = capsys.readouterr()
    assert captured.out.strip() == version


def test_dsl_version(capsys):
    CliApp.run(CurriculumAppCliArgs, cli_args=["dsl-version"])
    captured = capsys.readouterr()
    assert captured.out.strip() == dsl_version


def test_known_curricula_implement_runner():
    for curriculum in _KNOWN_CURRICULA:
        module = importlib.import_module(f"aind_behavior_vr_foraging_curricula.{curriculum}")
        runner = getattr(module, "run_curriculum")
        del module, runner


def test_curriculum_name_inference(caplog):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp_file:
        trainer_state, _ = __test_placeholder.make()
        tmp_file.write(trainer_state.model_dump_json(indent=2))
        tmp_file_path = tmp_file.name
    try:
        assert os.path.exists(tmp_file_path)
        CliApp.run(
            CurriculumAppCliArgs, cli_args=["run", "--data-directory", "demo", "--input-trainer-state", tmp_file_path]
        )
        # Check stderr for any errors
        with caplog.at_level(logging.ERROR, logger="aind_behavior_vr_foraging_curricula"):
            error_msgs = [m.getMessage() for m in caplog.records if m.levelno >= logging.ERROR]
            assert len(error_msgs) == 0, f"Unexpected errors: {error_msgs}"
    finally:
        os.unlink(tmp_file_path)


def test_cli_enroll(capsys):
    CliApp.run(
        CurriculumInitCliArgs,
        cli_args=[
            "--curriculum",
            "template",
        ],
    )
    captured = capsys.readouterr()
    json_output = captured.out.strip()
    assert len(json_output) > 0, "No JSON output to stdout"
    assert TRAINER.create_enrollment() == TRAINER.trainer_state_model.model_validate_json(json_output)


def test_cli_enroll_with_stage(capsys):
    CliApp.run(
        CurriculumInitCliArgs,
        cli_args=[
            "--curriculum",
            "template",
            "--stage",
            "stage_b",
        ],
    )

    captured = capsys.readouterr()
    json_output = captured.out.strip()
    assert len(json_output) > 0, "No JSON output to stdout"
    deserialized = TRAINER.trainer_state_model.model_validate_json(json_output)

    assert deserialized.stage is not None, "Stage should not be None"
    assert deserialized.stage.name == "stage_b"
    assert deserialized.is_on_curriculum is True

    stages = TRAINER.curriculum.see_stages()
    stage_b = [s for s in stages if s.name == "stage_b"][0]
    expected_policies = stage_b.start_policies
    assert deserialized.stage.start_policies is not None
    assert len(deserialized.stage.start_policies) == len(expected_policies)
