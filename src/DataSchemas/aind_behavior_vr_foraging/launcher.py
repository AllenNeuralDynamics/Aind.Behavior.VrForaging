import logging
from pathlib import Path
from typing import List, Optional, Self, Type

from aind_behavior_experiment_launcher.apps import app_service
from aind_behavior_experiment_launcher.data_transfer import robocopy_service, watchdog_service
from aind_behavior_experiment_launcher.launcher import Launcher as BaseLauncher
from aind_behavior_experiment_launcher.resource_monitor import resource_monitor_service
from aind_behavior_experiment_launcher.services import Services
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import utcnow

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .data_mappers import VrForagingToAindDataSchemaDataMapper

logger = logging.getLogger(__name__)


class VrForagingLauncher(BaseLauncher):
    rig_schema_model: Type[AindVrForagingRig]
    session_schema_model: Type[AindBehaviorSessionModel]
    task_logic_schema_model: Type[AindVrForagingTaskLogic]

    def __init__(
        self,
        rig_schema_model: Type[AindVrForagingRig],
        session_schema_model: Type[AindBehaviorSessionModel],
        task_logic_schema_model: Type[AindVrForagingTaskLogic],
        data_dir,
        config_library_dir,
        temp_dir=...,
        repository_dir=...,
        allow_dirty=...,
        skip_hardware_validation=...,
        debug_mode=...,
        logger=...,
        group_by_subject_log=...,
        services=...,
        validate_init=...,
    ):
        super().__init__(
            rig_schema_model,
            session_schema_model,
            task_logic_schema_model,
            data_dir,
            config_library_dir,
            temp_dir,
            repository_dir,
            allow_dirty,
            skip_hardware_validation,
            debug_mode,
            logger,
            group_by_subject_log,
            services,
            validate_init,
        )

    def _prompt_session_input(self, directory=...) -> AindBehaviorSessionModel:
        session: AindBehaviorSessionModel = super()._prompt_session_input(directory)
        session.experimenter = self._prompt_experimenter()
        return session

    @staticmethod
    def _prompt_experimenter() -> List[str]:
        experimenter: Optional[List[str]] = None
        while experimenter is None:
            _user_input = input("Experimenter name: ")
            if _user_input:
                if not _user_input == "":
                    experimenter = _user_input.replace(",", " ").split()
            else:
                logger.error("Experimenter name is not valid.")
        return experimenter

    @staticmethod
    def validate_services(services: Services, *args, **kwargs) -> None:
        # Validate services
        # Bonsai app is required
        if services.app is None:
            raise ValueError("Bonsai app not set.")
        else:
            if not isinstance(services.app, app_service.BonsaiApp):
                raise ValueError("Bonsai app is not an instance of BonsaiApp.")
            if not services.app.validate():
                raise ValueError("Bonsai app failed to validate.")
            else:
                logger.info("Bonsai app validated.")

        # data_transfer_service is optional
        if services.data_transfer is None:
            logger.warning("Data transfer service not set.")
        else:
            if not services.data_transfer.validate():
                raise ValueError("Data transfer service failed to validate.")
            else:
                logger.info("Data transfer service validated.")

        # Resource monitor service is optional
        if services.resource_monitor is None:
            logger.warning("Resource monitor service not set.")
        else:
            if not services.resource_monitor.validate():
                raise ValueError("Resource monitor service failed to validate.")
            else:
                logger.info("Resource monitor service validated.")

        # Data mapper service is optional
        if services.data_mapper is None:
            logger.warning("Data mapper service not set.")
        else:
            if not isinstance(services.data_mapper, VrForagingToAindDataSchemaDataMapper):
                raise ValueError("Data mapper service is not an instance of VrForagingToAindDataSchemaDataMapper.")
            if not services.data_mapper.validate():
                raise ValueError("Data mapper service failed to validate.")
            else:
                logger.info("Data mapper service validated.")

    def _post_run_hook(self, *args, **kwargs) -> Self:
        self.logger.info("Post-run hook started.")
        if self.services.app is None:
            raise ValueError("Bonsai app not set.")
        self._subject_info = self.subject_info.prompt_field("animal_weight_post", None)
        self._subject_info = self.subject_info.prompt_field("reward_consumed_total", None)
        try:
            self.logger.info("Subject Info: %s", self.subject_info.model_dump_json(indent=4))
        except Exception as e:
            self.logger.error("Failed to log subject info. %s", e)

        mapped = None
        if self.services.data_mapper is not None:
            if not isinstance(self.services.data_mapper, VrForagingToAindDataSchemaDataMapper):
                raise ValueError("Data mapper service is not an instance of VrForagingToAindDataSchemaDataMapper.")
            try:
                mapped = self.services.data_mapper.map(
                    schema_root=self.session_directory / "Behavior" / "Logs",
                    session_model=self.session_schema_model,
                    rig_model=self.rig_schema_model,
                    task_logic_model=self.task_logic_schema_model,
                    repository=self.repository,
                    script_path=Path(self.services.app.workflow).resolve(),
                    session_end_time=utcnow(),
                    subject_info=self.subject_info,
                    session_directory=self.session_directory,
                )
                self.logger.info("Mapping successful.")
            except Exception as e:
                self.logger.error("Data mapper service has failed: %s", e)

        if self.services.data_transfer is not None:
            try:
                if isinstance(self.services.data_transfer, robocopy_service.RobocopyService):
                    self.services.data_transfer.transfer(
                        source=self.session_directory,
                        destination=self.services.data_transfer.destination / self.session_schema.session_name,
                        overwrite=False,
                        force_dir=True,
                    )
                elif isinstance(self.services.data_transfer, watchdog_service.WatchdogDataTransferService):
                    self.services.data_transfer.transfer(
                        session_schema=self.session_schema,
                        ads_session=mapped,
                        session_directory=self.session_directory,
                    )
                else:
                    raise ValueError(
                        "Data transfer service is not an instance of RobocopyService or WatchdogDataTransferService."
                    )
            except Exception as e:
                self.logger.error("Data transfer service has failed: %s", e)
        return self


def default_services_factory():
    return Services(
        app=app_service.BonsaiApp(Path(r"./src/vr-foraging.bonsai")),
        data_transfer=robocopy_service.RobocopyService(destination=Path(r"\\allen\aind\scratch\vr-foraging\data")),
        resource_monitor=resource_monitor_service.ResourceMonitor(
            constrains=[resource_monitor_service.available_storage_constraint_factory(drive=r"C:\\", min_bytes=2e11)]
        ),
        data_mapper=None,
    )
