from pathlib import Path
from typing import Any

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
from clabe.launcher import (
    DefaultBehaviorPicker,
    DefaultBehaviorPickerSettings,
    Launcher,
    LauncherCliArgs,
    Promise,
)
from pydantic_settings import CliApp

from .data_mappers import AindRigDataMapper, AindSessionDataMapper, write_ads_mappers
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
    picker = DefaultBehaviorPicker[AindVrForagingRig, AindBehaviorSessionModel, AindVrForagingTaskLogic](
        settings=DefaultBehaviorPickerSettings()  # type: ignore[call-arg]
    )
    launcher = Launcher(
        rig=AindVrForagingRig,
        session=AindBehaviorSessionModel,
        task_logic=AindVrForagingTaskLogic,
        settings=settings,
    )

    # Get user input
    launcher.register_callable(
        [
            picker.initialize,
            picker.pick_session,
            picker.pick_trainer_state,
            picker.pick_rig,
        ]
    )

    # Check resources
    launcher.register_callable(monitor.build_runner())

    # Run the task via Bonsai
    launcher.register_callable(bonsai_app.build_runner(allow_std_error=True))

    # Curriculum
    suggestion = launcher.register_callable(
        trainer.build_runner(input_trainer_state=Promise(lambda x: picker.trainer_state))
    )
    launcher.register_callable(lambda launcher: _dump_suggestion(launcher, suggestion))

    # Mappers
    session_mapper_promise = launcher.register_callable(AindSessionDataMapper.build_runner(bonsai_app))
    rig_mapper_promise = launcher.register_callable(AindRigDataMapper.build_runner(picker))
    launcher.register_callable(write_ads_mappers(session_mapper_promise, rig_mapper_promise))

    # Watchdog
    launcher.register_callable(
        WatchdogDataTransferService.build_runner(
            settings=watchdog_settings, aind_session_data_mapper=session_mapper_promise
        )
    )
    return launcher


def _dump_suggestion(launcher: Launcher[Any, Any, Any], suggestion: Promise[Any, CurriculumSuggestion]) -> None:
    with open(launcher.session_directory / "Behavior" / "Logs" / "suggestion.json", "w", encoding="utf-8") as f:
        f.write(suggestion.result.model_dump_json(indent=2))


class ClabeCli(LauncherCliArgs):
    def cli_cmd(self):
        launcher = make_launcher(self)
        launcher.main()
        return None


def main() -> None:
    CliApp().run(ClabeCli)


if __name__ == "__main__":
    main()
