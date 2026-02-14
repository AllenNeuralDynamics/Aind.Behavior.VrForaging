import logging
import os
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
from clabe.data_transfer.aind_watchdog import WatchdogDataTransferService, WatchdogSettings
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


@experiment()
async def aind_experiment_protocol(launcher: Launcher) -> None:
    # Start experiment setup
    picker = DataversePicker(launcher=launcher, settings=DefaultBehaviorPickerSettings())

    # Pick and register session
    session = picker.pick_session(Session)

    # Fetch the task settings
    trainer_state, task_logic = picker.pick_trainer_state(AindVrForagingTaskLogic)

    # Fetch rig settings
    rig = picker.pick_rig(AindVrForagingRig)
    ensure_rig_and_computer_name(rig)

    launcher.register_session(session, rig.data_directory)

    resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(rig.data_directory, 2e11),
        ]
    ).run()

    input_trainer_state_path = launcher.save_temp_model(trainer_state)

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
        task_logic=task_logic,
    )
    await bonsai_app.run_async()

    # Update manipulator initial position for next session
    try:
        manipulator_modifier.dump()
    except Exception as e:
        logger.error(f"Failed to update manipulator initial position: {e}")

    # Curriculum
    suggestion: CurriculumSuggestion | None = None
    suggestion_path: Path | None = None
    if not (
        (picker.trainer_state is None)
        or (picker.trainer_state.is_on_curriculum is False)
        or (picker.trainer_state.stage is None)
    ):
        trainer = CurriculumApp(
            settings=CurriculumSettings(
                input_trainer_state=input_trainer_state_path.resolve(), data_directory=launcher.session_directory
            )
        )
        # Run the curriculum
        await trainer.run_async()
        suggestion = trainer.process_suggestion()
        # Dump suggestion for debugging (for now, but we will prob remove this later)
        suggestion_path = _dump_suggestion(suggestion, launcher.session_directory)
        # Push updated trainer state back to the database
        picker.push_new_suggestion(suggestion.trainer_state)

    # Mappers
    assert launcher.repository.working_tree_dir is not None

    DataMapperCli(
        data_path=launcher.session_directory,
        repo_path=launcher.repository.working_tree_dir,  # type: ignore[arg-type]
        curriculum_suggestion=suggestion_path,
        session_end_time=utcnow(),
    ).cli_cmd()

    # Run data qc
    if picker.ui_helper.prompt_yes_no_question("Would you like to generate a qc report?"):
        try:
            import webbrowser

            from contraqctor.qc.reporters import HtmlReporter

            from ..src.aind_behavior_vr_foraging.data_qc.data_qc import make_qc_runner

            vr_dataset = data_contract.dataset(launcher.session_directory)
            runner = make_qc_runner(vr_dataset)
            qc_path = launcher.session_directory / "Behavior" / "Logs" / "qc_report.html"
            reporter = HtmlReporter(output_path=qc_path)
            runner.run_all_with_progress(reporter=reporter)
            webbrowser.open(qc_path.as_uri(), new=2)
        except Exception as e:
            logger.error(f"Failed to run data QC: {e}")

    # Watchdog
    is_transfer = picker.ui_helper.prompt_yes_no_question("Would you like to transfer data?")
    if not is_transfer:
        logger.info("Data transfer skipped by user.")
        return

    launcher.copy_logs()
    watchdog_settings = WatchdogSettings()
    watchdog_settings.destination = Path(watchdog_settings.destination) / launcher.session.subject
    WatchdogDataTransferService(
        source=launcher.session_directory,
        settings=watchdog_settings,
        session=session,
    ).transfer()

    return


@experiment()
async def calibration_protocol(launcher: Launcher) -> None:
    # Start experiment setup
    picker = DataversePicker(launcher=launcher, settings=DefaultBehaviorPickerSettings())

    # Pick and register session
    session = Session(subject="CALIBRATION", experiment="CALIBRATION", date=utcnow())

    # Fetch rig settings
    rig = picker.pick_rig(AindVrForagingRig)

    launcher.register_session(session, rig.data_directory)

    resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(rig.data_directory, 2e11),
        ]
    ).run()

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
        self, subject_db_path: Path, model_path: str, model_name: str, *, launcher: Launcher, **kwargs
    ) -> None:
        super().__init__(subject_db_path, model_path, model_name, **kwargs)
        self._launcher = launcher

    def _process_before_dump(self) -> ManipulatorPosition:
        _dataset = data_contract.dataset(self._launcher.session_directory)
        manipulator_parking_position: SoftwareEvents = cast(
            SoftwareEvents, _dataset["Behavior"]["SoftwareEvents"]["SpoutParkingPositions"].load()
        )
        data: dict[str, Any] = manipulator_parking_position.data.iloc[0]["data"]["ResetPosition"]
        position = ManipulatorPosition.model_validate(data)
        return position


def ensure_rig_and_computer_name(rig: AindVrForagingRig) -> None:
    """Ensures rig and computer name are set from environment variables if available, otherwise defaults to rig configuration values."""
    rig_name = os.environ.get("aibs_comp_id", None)
    computer_name = os.environ.get("hostname", None)

    if rig_name is None:
        logger.warning(
            "'aibs_comp_id' environment variable not set. Defaulting to rig name from configuration. %s", rig.rig_name
        )
        rig_name = rig.rig_name
    if computer_name is None:
        computer_name = rig.computer_name
        logger.warning(
            "'hostname' environment variable not set. Defaulting to computer name from configuration. %s",
            rig.computer_name,
        )

    if rig_name != rig.rig_name or computer_name != rig.computer_name:
        logger.warning(
            "Rig name or computer name from environment variables do not match the rig configuration. "
            "Forcing rig name: %s and computer name: %s from environment variables.",
            rig_name,
            computer_name,
        )
        rig.rig_name = rig_name
        rig.computer_name = computer_name


class ClabeCli(LauncherCliArgs):
    def cli_cmd(self):
        launcher = Launcher(settings=self)
        launcher.run_experiment(aind_experiment_protocol)
        return None


def main() -> None:
    CliApp().run(ClabeCli)


if __name__ == "__main__":
    main()
