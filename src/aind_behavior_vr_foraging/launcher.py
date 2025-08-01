from pathlib import Path

from aind_behavior_services.session import AindBehaviorSessionModel
from clabe import resource_monitor
from clabe.apps import AindBehaviorServicesBonsaiApp
from clabe.data_transfer.aind_watchdog import WatchdogDataTransferService, WatchdogSettings
from clabe.launcher import DefaultBehaviorPicker, DefaultBehaviorPickerSettings, Launcher, LauncherCliArgs
from pydantic_settings import CliApp

from .data_mappers import AindRigDataMapper, AindSessionDataMapper
from .rig import AindVrForagingRig
from .task_logic import AindVrForagingTaskLogic


def make_launcher(settings: LauncherCliArgs) -> Launcher:
    monitor = resource_monitor.ResourceMonitor(
        constrains=[
            resource_monitor.available_storage_constraint_factory(settings.data_dir, 2e11),
        ]
    )
    app = AindBehaviorServicesBonsaiApp(Path(r"./src/main.bonsai"))
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

    launcher.register_callable(
        [
            picker.initialize,
            picker.pick_session,
            picker.pick_task_logic,
            picker.pick_rig,
        ]
    )
    launcher.register_callable(monitor.build_runner())
    launcher.register_callable(app.build_runner(allow_std_error=True))
    session_mapper_promise = launcher.register_callable(AindSessionDataMapper.build_runner(app))
    launcher.register_callable(AindRigDataMapper.build_runner(picker))
    launcher.register_callable(
        WatchdogDataTransferService.build_runner(
            settings=watchdog_settings, aind_session_data_mapper=session_mapper_promise
        )
    )
    return launcher


def main():
    args = CliApp().run(LauncherCliArgs)
    launcher = make_launcher(args)
    launcher.main()
    return None


if __name__ == "__main__":
    main()
