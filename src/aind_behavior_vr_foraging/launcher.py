import logging
import os
from pathlib import Path
from typing import Any, Optional, cast

from aind_behavior_services.calibration.aind_manipulator import ManipulatorPosition
from aind_behavior_services.session import AindBehaviorSessionModel
from clabe import resource_monitor
from clabe.apps import (
    AindBehaviorServicesBonsaiApp,
    CurriculumApp,
    CurriculumSettings,
    CurriculumSuggestion,
)
from clabe.data_transfer.aind_watchdog import WatchdogDataTransferService, WatchdogSettings
from clabe.launcher import Launcher, LauncherCliArgs
from clabe.pickers import ByAnimalModifier, DefaultBehaviorPickerSettings
from clabe.pickers.dataverse import DataversePicker
from contraqctor.contract.json import SoftwareEvents
from pydantic_settings import CliApp

from . import data_contract
from .data_mappers import AindRigDataMapper, AindSessionDataMapper
from .rig import AindVrForagingRig
from .task_logic import AindVrForagingTaskLogic

logger = logging.getLogger(__name__)


async def experiment(launcher: Launcher) -> None:
    monitor = resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(launcher.settings.data_dir, 2e11),
        ]
    )

    # Validate resources
    monitor.run()

    # Start experiment setup
    picker = DataversePicker(launcher=launcher, settings=DefaultBehaviorPickerSettings())

    # Pick and register session
    session = picker.pick_session(AindBehaviorSessionModel)
    launcher.register_session(session)

    # Fetch the task settings
    trainer_state, task_logic = picker.pick_trainer_state(AindVrForagingTaskLogic)
    input_trainer_state_path = launcher.save_temp_model(trainer_state)

    # Fetch rig settings
    rig = picker.pick_rig(AindVrForagingRig)

    # Post-fetching modifications
    manipulator_modifier = ByAnimalManipulatorModifier(
        subject_db_path=picker.subject_dir / picker.session.subject,
        model_path="manipulator.calibration.input.initial_position",
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
    if not (
        (picker.trainer_state is None)
        or (picker.trainer_state.is_on_curriculum is False)
        or (picker.trainer_state.stage is None)
    ):
        trainer = CurriculumApp(
            settings=CurriculumSettings(
                input_trainer_state=input_trainer_state_path, data_directory=launcher.session_directory
            )
        )
        # Run the curriculum
        await trainer.run_async()
        suggestion = trainer.process_suggestion()
        # Dump suggestion for debugging (for now, but we will prob remove this later)
        _dump_suggestion(suggestion, launcher.session_directory)
        # Push updated trainer state back to the database
        picker.push_new_suggestion(suggestion.trainer_state)

    try:
        total_water_consumed = calculate_consumed_water(launcher.session_directory)
    except Exception as e:
        logger.warning(f"Could not calculate consumed water: {e}")
        total_water_consumed = None

    # Mappers
    ads_session = AindSessionDataMapper(
        rig=rig,
        session=session,
        task_logic=task_logic,
        curriculum_suggestion=suggestion,
        bonsai_app=bonsai_app,
        water_consumed_ml=total_water_consumed,
    ).map()
    ads_session.write_standard_file(launcher.session_directory)
    ads_rig = AindRigDataMapper(rig=rig).map()
    ads_rig.write_standard_file(launcher.session_directory)

    # Run data qc
    if picker.ui_helper.prompt_yes_no_question("Would you like to generate a qc report?"):
        try:
            import webbrowser

            from contraqctor.qc.reporters import HtmlReporter

            from .data_qc.data_qc import make_qc_runner

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


def _dump_suggestion(suggestion: CurriculumSuggestion, session_directory: Path) -> None:
    logger.info(f"Dumping curriculum suggestion to: {session_directory / 'Behavior' / 'Logs' / 'suggestion.json'}")
    with open(session_directory / "Behavior" / "Logs" / "suggestion.json", "w", encoding="utf-8") as f:
        f.write(suggestion.model_dump_json(indent=2))


def calculate_consumed_water(session_path: os.PathLike) -> Optional[float]:
    """Calculate the total volume of water consumed during a session.

    Args:
        session_path (os.PathLike): Path to the session directory.

    Returns:
        Optional[float]: Total volume of water consumed in milliliters, or None if unavailable.
    """
    from aind_behavior_vr_foraging.data_contract import dataset

    return dataset(session_path)["Behavior"]["SoftwareEvents"]["GiveReward"].load()["data"].sum()


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


class ClabeCli(LauncherCliArgs):
    def cli_cmd(self):
        launcher = Launcher(settings=self)
        launcher.run_experiment(experiment)
        return None


def main() -> None:
    CliApp().run(ClabeCli)


if __name__ == "__main__":
    main()
