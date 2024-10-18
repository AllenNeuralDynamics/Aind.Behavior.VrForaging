import datetime
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Type, TypeVar, Union

import aind_behavior_services.rig as AbsRig
import aind_data_schema
import aind_data_schema.components.devices
import aind_data_schema.core.session
import git
import pydantic
from aind_behavior_experiment_launcher.data_mappers import data_mapper_service
from aind_behavior_experiment_launcher.records.subject_info import SubjectInfo
from aind_behavior_services.calibration import Calibration
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import model_from_json_file, utcnow

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

T = TypeVar("T")

logger = logging.getLogger(__name__)


class VrForagingToAindDataSchemaDataMapper(data_mapper_service.DataMapperService):
    def validate(self, *args, **kwargs):
        return True

    @classmethod
    def map(
        cls,
        *args,
        schema_root: os.PathLike,
        session_model: Type[AindBehaviorSessionModel],
        rig_model: Type[AindVrForagingRig],
        task_logic_model: Type[AindVrForagingTaskLogic],
        repository: Union[os.PathLike, git.Repo],
        script_path: os.PathLike,
        session_end_time: Optional[datetime.datetime] = None,
        output_parameters: Optional[Dict] = None,
        subject_info: Optional[SubjectInfo] = None,
        session_directory: Optional[os.PathLike] = None,
        **kwargs,
    ) -> Optional[aind_data_schema.core.session.Session]:
        logger.info("Mapping to aind-data-schema Session")
        try:
            ads_session = cls.map_from_session_root(
                schema_root=schema_root,
                session_model=session_model,
                rig_model=rig_model,
                task_logic_model=task_logic_model,
                repository=repository,
                script_path=script_path,
                session_end_time=session_end_time,
                output_parameters=output_parameters,
                subject_info=subject_info,
                **kwargs,
            )
            if session_directory is not None:
                logger.info("Writing session.json to %s", session_directory)
                ads_session.write_standard_file(session_directory)
            logger.info("Mapping successful.")
        except (pydantic.ValidationError, ValueError, IOError) as e:
            logger.error("Failed to map to aind-data-schema Session. %s", e)
            raise e
        else:
            return ads_session

    @classmethod
    def map_from_session_root(
        cls,
        schema_root: os.PathLike,
        session_model: Type[AindBehaviorSessionModel],
        rig_model: Type[AindVrForagingRig],
        task_logic_model: Type[AindVrForagingTaskLogic],
        repository: Union[os.PathLike, git.Repo],
        script_path: os.PathLike,
        session_end_time: Optional[datetime.datetime] = None,
        output_parameters: Optional[Dict] = None,
        subject_info: Optional[SubjectInfo] = None,
        **kwargs,
    ) -> aind_data_schema.core.session.Session:
        return cls._map(
            session_model=model_from_json_file(Path(schema_root) / "session_input.json", session_model),
            rig_model=model_from_json_file(Path(schema_root) / "rig_input.json", rig_model),
            task_logic_model=model_from_json_file(Path(schema_root) / "tasklogic_input.json", task_logic_model),
            repository=repository,
            script_path=script_path,
            session_end_time=session_end_time if session_end_time else utcnow(),
            output_parameters=output_parameters,
            subject_info=subject_info,
            **kwargs,
        )

    @classmethod
    def _map(
        cls,
        session_model: AindBehaviorSessionModel,
        rig_model: AindVrForagingRig,
        task_logic_model: AindVrForagingTaskLogic,
        repository: Union[os.PathLike, git.Repo],
        script_path: os.PathLike,
        session_end_time: Optional[datetime.datetime] = None,
        output_parameters: Optional[Dict] = None,
        subject_info: Optional[SubjectInfo] = None,
        **kwargs,
    ) -> aind_data_schema.core.session.Session:
        # Normalize repository
        if isinstance(repository, os.PathLike | str):
            repository = git.Repo(Path(repository))
        repository_remote_url = repository.remote().url
        repository_sha = repository.head.commit.hexsha
        repository_relative_script_path = Path(script_path).resolve().relative_to(repository.working_dir)

        # Populate calibrations:
        calibrations = [
            cls._mapper_calibration(_calibration_model[1])
            for _calibration_model in data_mapper_service.get_fields_of_type(rig_model, Calibration)
        ]
        # Populate cameras
        cameras = data_mapper_service.get_cameras(rig_model, exclude_without_video_writer=True)
        # populate devices
        devices = [
            device[0] for device in data_mapper_service.get_fields_of_type(rig_model, AbsRig.Device) if device[0]
        ]
        # Populate modalities
        modalities: list[aind_data_schema.core.session.Modality] = [
            getattr(aind_data_schema.core.session.Modality, "BEHAVIOR")
        ]
        if len(cameras) > 0:
            modalities.append(getattr(aind_data_schema.core.session.Modality, "BEHAVIOR_VIDEOS"))
        modalities = list(set(modalities))
        # Populate stimulus modalities
        stimulus_modalities: list[aind_data_schema.core.session.StimulusModality] = []

        if data_mapper_service.get_fields_of_type(rig_model, AbsRig.Screen):
            stimulus_modalities.extend(
                [
                    aind_data_schema.core.session.StimulusModality.VISUAL,
                    aind_data_schema.core.session.StimulusModality.VIRTUAL_REALITY,
                ]
            )
        if data_mapper_service.get_fields_of_type(rig_model, AbsRig.HarpOlfactometer):
            stimulus_modalities.append(aind_data_schema.core.session.StimulusModality.OLFACTORY)
        if data_mapper_service.get_fields_of_type(rig_model, AbsRig.HarpTreadmill):
            stimulus_modalities.append(aind_data_schema.core.session.StimulusModality.WHEEL_FRICTION)

        # Mouse platform
        mouse_platform: str
        if isinstance(rig_model.harp_treadmill, AbsRig.HarpTreadmill):
            mouse_platform = "Treadmill"
            active_mouse_platform = True
        else:
            raise ValueError("Mouse platform is of unexpected type.")

        # Reward delivery
        reward_delivery_config = aind_data_schema.core.session.RewardDeliveryConfig(
            reward_solution=aind_data_schema.core.session.RewardSolution.WATER, reward_spouts=[]
        )

        # Construct aind-data-schema session
        aind_data_schema_session = aind_data_schema.core.session.Session(
            animal_weight_post=subject_info.animal_weight_post if subject_info else None,
            animal_weight_prior=subject_info.animal_weight_prior if subject_info else None,
            reward_consumed_total=subject_info.reward_consumed_total if subject_info else None,
            reward_delivery=reward_delivery_config,
            experimenter_full_name=session_model.experimenter,
            session_start_time=session_model.date,
            session_end_time=session_end_time,
            session_type=session_model.experiment,
            rig_id=rig_model.rig_name,
            subject_id=session_model.subject,
            notes=session_model.notes,
            data_streams=[
                aind_data_schema.core.session.Stream(
                    daq_names=devices,
                    stream_modalities=modalities,
                    stream_start_time=session_model.date,
                    stream_end_time=session_end_time if session_end_time else session_model.date,
                    camera_names=list(cameras.keys()),
                ),
            ],
            calibrations=calibrations,
            mouse_platform_name=mouse_platform,
            active_mouse_platform=active_mouse_platform,
            stimulus_epochs=[
                aind_data_schema.core.session.StimulusEpoch(
                    stimulus_name=session_model.experiment,
                    stimulus_start_time=session_model.date,
                    stimulus_end_time=session_end_time if session_end_time else session_model.date,
                    stimulus_modalities=stimulus_modalities,
                    software=[
                        aind_data_schema.core.session.Software(
                            name="Bonsai",
                            version=f"{repository_remote_url}/blob/{repository_sha}/bonsai/Bonsai.config",
                            url=f"{repository_remote_url}/blob/{repository_sha}/bonsai",
                            parameters=data_mapper_service.snapshot_bonsai_environment(
                                config_file=kwargs.get("bonsai_config_path", Path("./bonsai/bonsai.config"))
                            ),
                        ),
                        aind_data_schema.core.session.Software(
                            name="Python",
                            version=f"{repository_remote_url}/blob/{repository_sha}/pyproject.toml",
                            url=f"{repository_remote_url}/blob/{repository_sha}",
                            parameters=data_mapper_service.snapshot_python_environment(),
                        ),
                    ],
                    script=aind_data_schema.core.session.Software(
                        name=Path(script_path).stem,
                        version=session_model.commit_hash if session_model.commit_hash else repository_sha,
                        url=f"{repository_remote_url}/blob/{repository_sha}/{repository_relative_script_path}",
                        parameters=task_logic_model.model_dump(),
                    ),
                    output_parameters=output_parameters if output_parameters else {},
                )  # type: ignore
            ],
        )  # type: ignore
        return aind_data_schema_session

    @staticmethod
    def _mapper_calibration(calibration: Calibration) -> aind_data_schema.components.devices.Calibration:
        return aind_data_schema.components.devices.Calibration(
            device_name=calibration.device_name,
            input=calibration.input.model_dump() if calibration.input else {},
            output=calibration.output.model_dump() if calibration.output else {},
            calibration_date=calibration.date if calibration.date else utcnow(),
            description=calibration.description if calibration.description else "",
            notes=calibration.notes,
        )
