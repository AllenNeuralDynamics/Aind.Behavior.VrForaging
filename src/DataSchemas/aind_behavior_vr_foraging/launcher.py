import datetime
import os
from functools import partial
from pathlib import Path
from typing import Callable, Optional

import aind_behavior_experiment_launcher.launcher.behavior_launcher as behavior_launcher
import aind_behavior_video_transformation as abvt
from aind_behavior_experiment_launcher import resource_monitor
from aind_behavior_experiment_launcher.apps import BonsaiApp
from aind_behavior_experiment_launcher.data_transfer import aind_watchdog
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_watchdog_service.models.manifest_config import (
    BasicUploadJobConfigs,
    ModalityConfigs,
)

from aind_behavior_vr_foraging.data_mappers import AindDataMapperWrapper
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic


def make_launcher() -> behavior_launcher.BehaviorLauncher:
    data_dir = r"C:/Data"
    remote_dir = Path(r"\\allen\aind\scratch\vr-foraging\data")
    srv = behavior_launcher.BehaviorServicesFactoryManager()
    srv.attach_bonsai_app(BonsaiApp(r"./src/vr-foraging.bonsai"))
    srv.attach_data_mapper(AindDataMapperWrapper.from_launcher)
    srv.attach_data_transfer(
        watchdog_data_transfer_factory(
            remote_dir,
            project_name="Cognitive flexibility in patch foraging",
            upload_job_configs=[video_compression_job],
        )
    )

    srv.attach_resource_monitor(
        resource_monitor.ResourceMonitor(
            constrains=[
                resource_monitor.available_storage_constraint_factory(data_dir, 2e11),
                resource_monitor.remote_dir_exists_constraint_factory(Path(remote_dir)),
            ]
        )
    )

    return behavior_launcher.BehaviorLauncher(
        rig_schema_model=AindVrForagingRig,
        session_schema_model=AindBehaviorSessionModel,
        task_logic_schema_model=AindVrForagingTaskLogic,
        data_dir=data_dir,
        config_library_dir=r"\\allen\aind\scratch\AindBehavior.db\AindVrForaging",
        temp_dir=r"./local/.temp",
        allow_dirty=False,
        skip_hardware_validation=False,
        debug_mode=False,
        group_by_subject_log=True,
        services=srv,
        validate_init=True,
    )


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


def video_compression_job(
    compression_request_settings: Optional[abvt.CompressionRequest] = None,
) -> Callable[[aind_watchdog.WatchdogDataTransferService], ModalityConfigs]:
    if compression_request_settings is None:
        compression_request_settings = abvt.CompressionRequest(compression_enum=abvt.CompressionEnum.GAMMA_ENCODING)

    def _video_compression_job_factory(watchdog: aind_watchdog.WatchdogDataTransferService) -> BasicUploadJobConfigs:
        return ModalityConfigs(
            modality=aind_watchdog.Modality.BEHAVIOR_VIDEOS,
            source=watchdog.source / aind_watchdog.Modality.BEHAVIOR_VIDEOS.abbreviation,
            job_settings=compression_request_settings,
            compress_raw_data=True,
        )

    return _video_compression_job_factory


def main():
    launcher = make_launcher()
    launcher.main()
    return None


if __name__ == "__main__":
    main()
