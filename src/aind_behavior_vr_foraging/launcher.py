import datetime
import os
from functools import partial
from pathlib import Path
from typing import Callable, Optional

import clabe.behavior_launcher as behavior_launcher
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_data_schema_models.modalities import Modality
from aind_watchdog_service.models.manifest_config import (
    ModalityConfigs,
)
from clabe import resource_monitor
from clabe.apps import AindBehaviorServicesBonsaiApp
from clabe.data_transfer import aind_watchdog
from clabe.logging_helper import aibs as aibs_logging
from pydantic_settings import CliApp

from aind_behavior_vr_foraging import __version__
from aind_behavior_vr_foraging.data_mappers import AindDataMapperWrapper
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic


def make_launcher(settings: behavior_launcher.BehaviorCliArgs) -> behavior_launcher.BehaviorLauncher:
    data_dir = r"C:/Data"
    remote_dir = Path(r"\\allen\aind\scratch\vr-foraging\data")
    project_name = "Cognitive flexibility in patch foraging"
    srv = behavior_launcher.BehaviorServicesFactoryManager()
    srv.attach_app(AindBehaviorServicesBonsaiApp(Path(r"./src/main.bonsai")))
    srv.attach_data_mapper(AindDataMapperWrapper.from_launcher)
    srv.attach_data_transfer(
        watchdog_data_transfer_factory(
            remote_dir,
            project_name=project_name,
            transfer_endpoint="http://aind-data-transfer-service/api/v1/submit_jobs",
            upload_job_configs=[
                ModalityConfigs(
                    modality=Modality.BEHAVIOR_VIDEOS, source="This will get replaced later", compress_raw_data=True
                )
            ],
            delete_modalities_source_after_success=True,
        )
    )

    srv.attach_resource_monitor(
        resource_monitor.ResourceMonitor(
            constrains=[
                resource_monitor.available_storage_constraint_factory(Path(data_dir), 2e11),
                resource_monitor.remote_dir_exists_constraint_factory(Path(remote_dir)),
            ]
        )
    )

    launcher: behavior_launcher.BehaviorLauncher = behavior_launcher.BehaviorLauncher(
        rig_schema_model=AindVrForagingRig,
        session_schema_model=AindBehaviorSessionModel,
        task_logic_schema_model=AindVrForagingTaskLogic,
        services=srv,
        settings=settings,
        picker=behavior_launcher.DefaultBehaviorPicker(
            config_library_dir=Path(r"\\allen\aind\scratch\AindBehavior.db\AindVrForaging")
        ),
    )
    aibs_logging.attach_to_launcher(
        launcher,
        logserver_url="eng-logtools.corp.alleninstitute.org:9000",
        project_name=project_name,
        version=__version__,
    )
    return launcher


def watchdog_data_transfer_factory(
    destination: os.PathLike,
    schedule_time: Optional[datetime.time] = datetime.time(hour=20),
    project_name: Optional[str] = None,
    **watchdog_kwargs,
) -> Callable[[behavior_launcher.BehaviorLauncher], aind_watchdog.WatchdogDataTransferService]:
    return partial(
        _watchdog_data_transfer_factory,
        destination=destination,
        schedule_time=schedule_time,
        project_name=project_name,
        **watchdog_kwargs,
    )


def _watchdog_data_transfer_factory(
    launcher: behavior_launcher.BehaviorLauncher,
    destination: os.PathLike,
    **watchdog_kwargs,
) -> aind_watchdog.WatchdogDataTransferService:
    if launcher.services_factory_manager.data_mapper is None:
        raise ValueError("Data mapper service is not set. Cannot create watchdog.")
    if not isinstance(launcher.services_factory_manager.data_mapper, AindDataMapperWrapper):
        raise ValueError(
            "Data mapper service is not of the correct type (AindDataMapperWrapper). Cannot create watchdog."
        )
    if not launcher.services_factory_manager.data_mapper.is_mapped():
        raise ValueError("Data mapper has not mapped yet. Cannot create watchdog.")

    if not isinstance(launcher.session_schema, AindBehaviorSessionModel):
        raise ValueError(
            "Session schema is not of the correct type (AindBehaviorSessionModel). Cannot create watchdog."
        )

    if not launcher.session_schema.session_name:
        raise ValueError("Session name is not set. Cannot create watchdog.")

    destination = Path(destination)
    if launcher.group_by_subject_log:
        destination = destination / launcher.session_schema.subject

    watchdog = aind_watchdog.WatchdogDataTransferService(
        source=launcher.session_directory,
        aind_session_data_mapper=launcher.services_factory_manager.data_mapper._session_mapper,
        session_name=launcher.session_schema.session_name,
        destination=destination,
        **watchdog_kwargs,
    )
    return watchdog


def main():
    args = CliApp().run(behavior_launcher.BehaviorCliArgs)
    launcher = make_launcher(args)
    launcher.main()
    return None


if __name__ == "__main__":
    main()
