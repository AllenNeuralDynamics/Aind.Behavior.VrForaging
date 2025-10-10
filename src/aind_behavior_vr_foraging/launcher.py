from pathlib import Path
from typing import Any, cast

from aind_behavior_curriculum import TrainerState
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
from clabe.launcher import Launcher, LauncherCliArgs, MaybeResult, Promise, run_if
from clabe.pickers import DefaultBehaviorPickerSettings
from clabe.pickers.dataverse import DataversePicker
from contraqctor.contract.json import SoftwareEvents
from pydantic_settings import CliApp

from . import data_contract
from .data_mappers import AindRigDataMapper, AindSessionDataMapper
from .data_mappers._utils import write_ads_mappers
from .rig import AindVrForagingRig
from .task_logic import AindVrForagingTaskLogic


def make_launcher(settings: LauncherCliArgs) -> Launcher:
    monitor = resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(settings.data_dir, 2e11),
        ]
    )
    bonsai_app = AindBehaviorServicesBonsaiApp(BonsaiAppSettings(workflow=Path(r"./src/main.bonsai")))
    trainer = CurriculumApp(settings=CurriculumSettings())
    watchdog_settings = WatchdogSettings()  # type: ignore[call-arg]
    picker = DataversePicker[AindVrForagingRig, AindBehaviorSessionModel, AindVrForagingTaskLogic](
        settings=DefaultBehaviorPickerSettings()
    )
    launcher = Launcher(
        rig=AindVrForagingRig,
        session=AindBehaviorSessionModel,
        task_logic=AindVrForagingTaskLogic,
        settings=settings,
    )
    manipulator_modifier = ByAnimalManipulatorModifier(picker)

    # Get user input
    launcher.register_callable(picker.initialize)
    launcher.register_callable(picker.pick_session)
    launcher.register_callable(picker.pick_rig)
    launcher.register_callable(manipulator_modifier.inject)
    launcher.register_callable(picker.pick_trainer_state)

    # Check resources
    launcher.register_callable(monitor.build_runner())

    # Run the task via Bonsai
    launcher.register_callable(bonsai_app.build_runner(allow_std_error=True))

    # Update manipulator initial position for next session
    launcher.register_callable(manipulator_modifier.dump)

    # Curriculum
    suggestion = launcher.register_callable(
        run_if(lambda: trainer_state_exists_predicate(picker.trainer_state))(
            trainer.build_runner(input_trainer_state=lambda: picker.trainer_state, allow_std_error=True)
        )
    )

    launcher.register_callable(
        run_if(lambda: suggestion.result.has_result() and (not suggestion.result.result))(
            lambda launcher: _dump_suggestion(launcher, suggestion.result.result)
        )
    )

    launcher.register_callable(
        run_if(lambda: suggestion.result.has_result() and (not suggestion.result.result))(
            lambda launcher: picker.push_new_suggestion(launcher, suggestion.result.result.trainer_state)
        )
    )

    # Mappers
    session_mapper_promise = launcher.register_callable(
        AindSessionDataMapper.build_runner(curriculum_suggestion=lambda: _resolve_trainer_suggestion(suggestion))
    )
    rig_mapper_promise = launcher.register_callable(AindRigDataMapper.build_runner())
    launcher.register_callable(write_ads_mappers(session_mapper_promise, rig_mapper_promise))

    # Watchdog
    launcher.register_callable(lambda x: x.copy_logs())
    launcher.register_callable(
        WatchdogDataTransferService.build_runner(
            settings=watchdog_settings, aind_session_data_mapper=session_mapper_promise.as_callable()
        )
    )
    return launcher


def _dump_suggestion(launcher: Launcher[Any, Any, Any], suggestion: CurriculumSuggestion) -> None:
    launcher.logger.info(
        f"Dumping curriculum suggestion to: {launcher.session_directory / 'Behavior' / 'Logs' / 'suggestion.json'}"
    )
    with open(launcher.session_directory / "Behavior" / "Logs" / "suggestion.json", "w", encoding="utf-8") as f:
        f.write(suggestion.model_dump_json(indent=2))


def _resolve_trainer_suggestion(
    input_trainer_state: Promise[Any, MaybeResult[CurriculumSuggestion]],
) -> CurriculumSuggestion | None:
    if not input_trainer_state.has_result():
        return None
    if not input_trainer_state.result.has_result():
        return None
    return input_trainer_state.result.result


class ByAnimalManipulatorModifier:
    def __init__(self, picker: DataversePicker) -> None:
        self._picker = picker

    def inject(self, launcher: Launcher[AindVrForagingRig, Any, Any]) -> None:
        rig = launcher.get_rig(strict=True)
        if launcher.subject is None:
            raise ValueError("Launcher subject is not defined!")
        target_folder = self._picker.subject_dir / launcher.subject
        target_file = target_folder / "manipulator_init.json"
        if not target_file.exists():
            launcher.logger.warning(f"Manipulator initial position file not found: {target_file}. Using default.")
            return
        else:
            cached = ManipulatorPosition.model_validate_json(target_file.read_text(encoding="utf-8"))
            launcher.logger.info(f"Loading manipulator initial position from: {target_file}. Deserialized: {cached}")
            assert rig.manipulator.calibration is not None
            rig.manipulator.calibration.input.initial_position = cached
            launcher.set_rig(rig, force=True)
        return

    def dump(self, launcher: Launcher[AindVrForagingRig, Any, Any]) -> None:
        assert launcher.subject is not None
        target_folder = self._picker.subject_dir / launcher.subject
        target_file = target_folder / "manipulator_init.json"
        _dataset = data_contract.dataset(launcher.session_directory)
        try:
            manipulator_parking_position: SoftwareEvents = cast(
                SoftwareEvents, _dataset["Behavior"]["SoftwareEvents"]["SpoutParkingPositions"].load()
            )
            data: dict[str, Any] = manipulator_parking_position.data.iloc[0]["data"]["ResetPosition"]
            position = ManipulatorPosition.model_validate(data)
        except Exception as e:
            launcher.logger.error(f"Failed to load manipulator parking position: {e}")
            return
        else:
            launcher.logger.info(f"Saving manipulator initial position to: {target_file}. Serialized: {position}")
            target_folder.mkdir(parents=True, exist_ok=True)
            target_file.write_text(position.model_dump_json(indent=2), encoding="utf-8")


def trainer_state_exists_predicate(input_trainer_state: TrainerState | Promise[Any, TrainerState]) -> bool:
    if isinstance(input_trainer_state, Promise):
        input_trainer_state = input_trainer_state.result
    if input_trainer_state is None:
        return False
    if input_trainer_state.is_on_curriculum is False:
        return False
    if input_trainer_state.stage is None:
        return False
    return True


class ClabeCli(LauncherCliArgs):
    def cli_cmd(self):
        launcher = make_launcher(self)
        launcher.main()
        return None


def main() -> None:
    CliApp().run(ClabeCli)


if __name__ == "__main__":
    main()
