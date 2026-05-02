import logging
from pathlib import Path
from typing import Any, cast

from aind_behavior_services.rig.aind_manipulator import ManipulatorPosition
from aind_behavior_services.session import Session
from aind_behavior_services.utils import utcnow
from clabe import resource_monitor
from clabe.apps import (
    AindBehaviorServicesBonsaiApp,
    CurriculumApp,
    CurriculumSettings,
    CurriculumSuggestion,
)
from clabe.data_transfer.aind_watchdog import (
    WatchdogDataTransferService,
    WatchdogSettings,
)
from clabe.launcher import Launcher, LauncherCliArgs, experiment
from clabe.pickers import ByAnimalModifier, DefaultBehaviorPickerSettings
from clabe.pickers.dataverse import DataversePicker
from contraqctor.contract.json import SoftwareEvents
from pydantic_settings import CliApp

from aind_behavior_vr_foraging import data_contract
from aind_behavior_vr_foraging.data_mappers import DataMapperCli
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

logger = logging.getLogger(__name__)

_DEFAULT_PICKER_SETTINGS = DefaultBehaviorPickerSettings(
    config_library_dir=r"\\allen\aind\scratch\AindBehavior.db\AindVrForaging"
)


async def _run_curriculum_if_applicable(
    picker: DataversePicker, input_trainer_state_path: Path, launcher: Launcher
) -> tuple[CurriculumSuggestion | None, Path | None]:
    if (
        (picker.trainer_state is None)
        or (picker.trainer_state.is_on_curriculum is False)
        or (picker.trainer_state.stage is None)
    ):
        return None, None
    trainer = CurriculumApp(
        settings=CurriculumSettings(
            input_trainer_state=input_trainer_state_path.resolve(),
            data_directory=launcher.session_directory,
            project_directory=Path("./src/aind_behavior_vr_foraging_curricula"),
        )
    )
    await trainer.run_async()
    suggestion = trainer.process_suggestion()
    suggestion_path = _dump_suggestion(suggestion, launcher.session_directory)
    picker.push_new_suggestion(suggestion.trainer_state)
    return suggestion, suggestion_path


def _run_data_qc(picker: DataversePicker, launcher: Launcher) -> None:
    if not picker.ui_helper.prompt_yes_no_question(
        "Would you like to generate a qc report?"
    ):
        return
    try:
        import webbrowser

        from contraqctor.qc.reporters import HtmlReporter

        from aind_behavior_vr_foraging.data_qc.data_qc import make_qc_runner

        vr_dataset = data_contract.dataset(launcher.session_directory)
        runner = make_qc_runner(vr_dataset)
        qc_path = launcher.session_directory / "Behavior" / "Logs" / "qc_report.html"
        reporter = HtmlReporter(output_path=qc_path)
        runner.run_all_with_progress(reporter=reporter)
        webbrowser.open(qc_path.as_uri(), new=2)
    except Exception as e:
        logger.error("Failed to run data QC: %s", e)


def _run_data_transfer(
    picker: DataversePicker, launcher: Launcher, session: Session
) -> None:
    if not picker.ui_helper.prompt_yes_no_question("Would you like to transfer data?"):
        logger.info("Data transfer skipped by user.")
        return
    watchdog_settings = WatchdogSettings()
    watchdog_settings.destination = (
        Path(watchdog_settings.destination) / launcher.session.subject
    )
    WatchdogDataTransferService(
        source=launcher.session_directory,
        settings=watchdog_settings,
        session=session,
    ).transfer()


@experiment()
async def aind_experiment_protocol(launcher: Launcher) -> None:
    # Start experiment setup
    picker = DataversePicker(launcher=launcher, settings=_DEFAULT_PICKER_SETTINGS)

    # Pick and register session
    session = picker.pick_session(Session)

    # Fetch the task settings
    trainer_state, task_logic = picker.pick_trainer_state(AindVrForagingTaskLogic)

    # Fetch rig settings
    rig = picker.pick_rig(AindVrForagingRig)

    launcher.register_session(session, rig.data_directory)

    resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(
                rig.data_directory, 2e11
            ),
        ]
    ).run()

    input_trainer_state_path = (
        launcher.session_directory / "behavior" / "trainer_state.json"
    )
    input_trainer_state_path.parent.mkdir(parents=True, exist_ok=True)
    input_trainer_state_path.write_text(
        trainer_state.model_dump_json(indent=2), encoding="utf-8"
    )

    # Post-fetching modifications
    manipulator_modifier = ByAnimalManipulatorModifier(
        subject_db_path=picker.subject_dir / session.subject,
        model_path="manipulator.calibration.initial_position",
        model_name="manipulator_init.json",
        launcher=launcher,
    )
    manipulator_modifier.inject(rig)

    # Run the task via Bonsai
    bonsai_app = AindBehaviorServicesBonsaiApp(
        workflow=Path(r"./src/main.bonsai"),
        temp_directory=launcher.temp_dir,
        rig=rig,
        session=session,
        task=task_logic,
    )
    await bonsai_app.run_async()

    # Update manipulator initial position for next session
    try:
        manipulator_modifier.dump()
    except Exception as e:
        logger.error("Failed to update manipulator initial position: %s", e)

    # Curriculum
    suggestion, suggestion_path = await _run_curriculum_if_applicable(
        picker, input_trainer_state_path, launcher
    )

    # Mappers
    assert launcher.repository.working_tree_dir is not None

    DataMapperCli(
        data_path=launcher.session_directory,
        repo_path=launcher.repository.working_tree_dir,  # type: ignore[arg-type]
        curriculum_suggestion=suggestion_path,
        session_end_time=utcnow(),
    ).cli_cmd()

    # Run data qc
    _run_data_qc(picker, launcher)

    # Watchdog
    launcher.copy_logs()
    _run_data_transfer(picker, launcher, session)


@experiment()
async def calibration_protocol(launcher: Launcher) -> None:
    # Start experiment setup
    picker = DataversePicker(launcher=launcher, settings=_DEFAULT_PICKER_SETTINGS)

    # Pick and register session
    session = Session(subject="CALIBRATION", experiment="CALIBRATION", date=utcnow())

    # Fetch rig settings
    rig = picker.pick_rig(AindVrForagingRig)

    launcher.register_session(session, rig.data_directory)

    # Run the task via Bonsai
    bonsai_app = AindBehaviorServicesBonsaiApp(
        workflow=Path(r"./src/main.bonsai"),
        temp_directory=launcher.temp_dir,
        rig=rig,
    )
    await bonsai_app.run_async()
    logger.info("Calibration protocol completed successfully.")


def _dump_suggestion(suggestion: CurriculumSuggestion, session_directory: Path) -> Path:
    path = session_directory / "Behavior" / "Logs" / "suggestion.json"
    logger.info("Dumping curriculum suggestion to: %s", path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(suggestion.model_dump_json(indent=2))
    return path


class ByAnimalManipulatorModifier(ByAnimalModifier[AindVrForagingRig]):
    """Modifier to set and update manipulator initial position based on animal-specific data."""

    def __init__(
        self,
        subject_db_path: Path,
        model_path: str,
        model_name: str,
        *,
        launcher: Launcher,
        **kwargs,
    ) -> None:
        super().__init__(subject_db_path, model_path, model_name, **kwargs)
        self._launcher = launcher

    def _process_before_dump(self) -> ManipulatorPosition:
        _dataset = data_contract.dataset(self._launcher.session_directory)
        manipulator_parking_position: SoftwareEvents = cast(
            SoftwareEvents,
            _dataset["Behavior"]["SoftwareEvents"]["SpoutParkingPositions"].load(),
        )
        data: dict[str, Any] = manipulator_parking_position.data.iloc[0]["data"][
            "ResetPosition"
        ]
        position = ManipulatorPosition.model_validate(data)
        return position


@experiment()
async def recover_session(launcher: Launcher) -> None:
    # Start experiment setup
    picker = DataversePicker(launcher=launcher, settings=_DEFAULT_PICKER_SETTINGS)
    session_path = Path(
        picker.ui_helper.input("Enter the path to the session you want to recover:")
    )
    if not session_path.exists():
        logger.error("Session path does not exist: %s", session_path)
        return
    session_model = Session.model_validate_json(
        (session_path / "behavior/Logs/session_input.json").read_text(encoding="utf-8")
    )
    rig_model = AindVrForagingRig.model_validate_json(
        (session_path / "behavior/Logs/rig_input.json").read_text(encoding="utf-8")
    )
    trainer_state_files = list((session_path / "behavior").glob("trainer_state*.json"))
    if trainer_state_files:
        input_trainer_state_path = trainer_state_files[0]
    else:
        raise FileNotFoundError("Trainer state file not found.")

    launcher.register_session(session_model, rig_model.data_directory)

    # Curriculum
    suggestion, suggestion_path = await _run_curriculum_if_applicable(
        picker, input_trainer_state_path, launcher
    )

    # Mappers
    assert launcher.repository.working_tree_dir is not None

    DataMapperCli(
        data_path=launcher.session_directory,
        repo_path=launcher.repository.working_tree_dir,  # type: ignore[arg-type]
        curriculum_suggestion=suggestion_path,
        session_end_time=utcnow(),
    ).cli_cmd()

    # Run data qc
    _run_data_qc(picker, launcher)

    # Watchdog
    _run_data_transfer(picker, launcher, session_model)


class ClabeCli(LauncherCliArgs):
    def cli_cmd(self):
        launcher = Launcher(settings=self)
        launcher.run_experiment(aind_experiment_protocol)
        return None


def main() -> None:
    CliApp().run(ClabeCli)


if __name__ == "__main__":
    main()
