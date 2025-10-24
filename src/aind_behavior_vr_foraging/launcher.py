import logging
from pathlib import Path
from typing import Any, cast

from aind_behavior_services.calibration.aind_manipulator import ManipulatorPosition
from aind_behavior_services.session import AindBehaviorSessionModel
from clabe import resource_monitor
from clabe.apps import (
    AindBehaviorServicesBonsaiApp,
    BonsaiAppSettings,
    CurriculumApp,
    CurriculumSettings,
    CurriculumSuggestion,
)
from clabe.data_transfer.aind_watchdog import WatchdogDataTransferService, WatchdogSettings
from clabe.launcher import Launcher, LauncherCliArgs
from clabe.pickers import DefaultBehaviorPickerSettings
from clabe.pickers.dataverse import DataversePicker
from contraqctor.contract.json import SoftwareEvents
from pydantic_settings import CliApp

from . import data_contract
from .data_mappers import AindRigDataMapper, AindSessionDataMapper
from .rig import AindVrForagingRig
from .task_logic import AindVrForagingTaskLogic

logger = logging.getLogger(__name__)


def experiment(launcher: Launcher) -> None:
    monitor = resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(launcher.settings.data_dir, 2e11),
        ]
    )

    # Validate resources
    monitor.run()

    # Start experiment setup
    picker = DataversePicker(launcher=launcher, settings=DefaultBehaviorPickerSettings())
    manipulator_modifier = ByAnimalManipulatorModifier(picker, launcher)

    # Pick and register session
    session = picker.pick_session(AindBehaviorSessionModel)
    launcher.register_session(session)

    # Fetch the task settings
    trainer_state, task_logic = picker.pick_trainer_state(AindVrForagingTaskLogic)
    input_trainer_state_path = launcher.save_temp_model(trainer_state)

    # Fetch rig settings
    rig = picker.pick_rig(AindVrForagingRig)

    # Post-fetching modifications
    manipulator_modifier.inject(rig)

    # Run the task via Bonsai
    bonsai_app = AindBehaviorServicesBonsaiApp(BonsaiAppSettings(workflow=Path(r"./src/main.bonsai")))
    bonsai_app.add_app_settings(launcher, rig=rig, session=session, task_logic=task_logic)
    bonsai_app.run().get_result(allow_stderr=True)

    # Update manipulator initial position for next session
    manipulator_modifier.dump()

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
        suggestion = trainer.run().get_result(allow_stderr=True)
        # Dump suggestion for debugging (for now, but we will prob remove this later)
        _dump_suggestion(launcher, suggestion)
        # Push updated trainer state back to the database
        picker.push_new_suggestion(suggestion.trainer_state)

    # Mappers
    ads_session = AindSessionDataMapper(
        rig=rig,
        session=session,
        task_logic=task_logic,
        curriculum_suggestion=suggestion,
        bonsai_app_settings=bonsai_app.settings,
    ).map()
    ads_session.write_standard_file(launcher.session_directory)
    ads_rig = AindRigDataMapper(rig=rig).map()
    ads_rig.write_standard_file(launcher.session_directory)

    # Watchdog
    is_transfer = picker.ui_helper.prompt_yes_no_question("Would you like to transfer data?")
    if not is_transfer:
        logger.info("Data transfer skipped by user.")
        launcher.copy_logs()
        return

    launcher.copy_logs()
    watchdog_settings = WatchdogSettings()
    watchdog_settings.destination = Path(watchdog_settings.destination) / launcher.session.subject
    WatchdogDataTransferService(
        source=launcher.session_directory,
        settings=watchdog_settings,
        aind_data_schema_session=ads_session,
        session_name=session.session_name,
    ).transfer()

    return


def _dump_suggestion(launcher: Launcher, suggestion: CurriculumSuggestion) -> None:
    launcher.logger.info(
        f"Dumping curriculum suggestion to: {launcher.session_directory / 'Behavior' / 'Logs' / 'suggestion.json'}"
    )
    with open(launcher.session_directory / "Behavior" / "Logs" / "suggestion.json", "w", encoding="utf-8") as f:
        f.write(suggestion.model_dump_json(indent=2))


class ByAnimalManipulatorModifier:
    def __init__(self, picker: DataversePicker, launcher: Launcher) -> None:
        self._picker = picker
        self._launcher = launcher

    def inject(self, rig: AindVrForagingRig) -> AindVrForagingRig:
        subject = self._launcher.session.subject
        target_folder = self._picker.subject_dir / subject
        target_file = target_folder / "manipulator_init.json"
        if not target_file.exists():
            logger.warning(f"Manipulator initial position file not found: {target_file}. Using default.")
        else:
            cached = ManipulatorPosition.model_validate_json(target_file.read_text(encoding="utf-8"))
            logger.info(f"Loading manipulator initial position from: {target_file}. Deserialized: {cached}")
            assert rig.manipulator.calibration is not None
            rig.manipulator.calibration.input.initial_position = cached
        return rig

    def dump(self) -> None:
        target_folder = self._picker.subject_dir / self._launcher.session.subject
        target_file = target_folder / "manipulator_init.json"
        _dataset = data_contract.dataset(self._launcher.session_directory)
        try:
            manipulator_parking_position: SoftwareEvents = cast(
                SoftwareEvents, _dataset["Behavior"]["SoftwareEvents"]["SpoutParkingPositions"].load()
            )
            data: dict[str, Any] = manipulator_parking_position.data.iloc[0]["data"]["ResetPosition"]
            position = ManipulatorPosition.model_validate(data)
        except Exception as e:
            logger.error(f"Failed to load manipulator parking position: {e}")
            return
        else:
            logger.info(f"Saving manipulator initial position to: {target_file}. Serialized: {position}")
            target_folder.mkdir(parents=True, exist_ok=True)
            target_file.write_text(position.model_dump_json(indent=2), encoding="utf-8")


class ClabeCli(LauncherCliArgs):
    def cli_cmd(self):
        launcher = Launcher(settings=self)
        launcher.run_experiment(experiment)
        return None


def main() -> None:
    CliApp().run(ClabeCli)


if __name__ == "__main__":
    main()
