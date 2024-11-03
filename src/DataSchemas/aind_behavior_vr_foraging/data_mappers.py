import datetime
import logging
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Self, Tuple, Type, TypeVar, Union

import aind_behavior_services.rig as AbsRig
import aind_data_schema
import aind_data_schema.base
import aind_data_schema.components.coordinates
import aind_data_schema.components.devices
import aind_data_schema.components.stimulus
import aind_data_schema.core.rig
import aind_data_schema.core.session
import git
import pydantic
from aind_behavior_experiment_launcher.data_mappers import data_mapper_service
from aind_behavior_experiment_launcher.data_mappers.aind_data_schema import (
    AindDataSchemaRigDataMapper,
    AindDataSchemaSessionDataMapper,
)
from aind_behavior_experiment_launcher.launcher.behavior_launcher import BehaviorLauncher
from aind_behavior_experiment_launcher.records.subject import WaterLogResult
from aind_behavior_services.calibration import Calibration
from aind_behavior_services.calibration.olfactometer import OlfactometerChannelType
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import model_from_json_file, utcnow
from pydantic import BaseModel

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

TFrom = TypeVar("TFrom", bound=Union[BaseModel, dict])
TTo = TypeVar("TTo", bound=BaseModel)

T = TypeVar("T")

logger = logging.getLogger(__name__)

_DATABASE_DIR = "AindDataSchemaRig"


class AindRigDataMapper(AindDataSchemaRigDataMapper):
    def __init__(
        self,
        *,
        rig_schema_filename: str,
        db_root: os.PathLike,
        db_suffix: Optional[str] = None,
    ):
        super().__init__()
        self.filename = rig_schema_filename
        self.db_root = db_root
        self.db_dir = db_suffix if db_suffix else f"{_DATABASE_DIR}/{os.environ['COMPUTERNAME']}"
        self.target_file = Path(self.db_root) / self.db_dir / self.filename
        self._mapped: Optional[aind_data_schema.core.rig.Rig] = None

    @property
    def session_name(self):
        raise NotImplementedError("Method not implemented.")

    def write_standard_file(self, directory: os.PathLike) -> None:
        self.mapped.write_standard_file(directory)

    def map(self) -> aind_data_schema.core.rig.Rig:
        logger.info("Mapping aind-data-schema Rig.")

        file_exists = self.target_file.exists()
        if not file_exists:
            raise FileNotFoundError(f"File {self.target_file} does not exist.")

        try:
            self._mapped = model_from_json_file(self.target_file, aind_data_schema.core.rig.Rig)
        except (pydantic.ValidationError, ValueError, IOError) as e:
            logger.error("Failed to map to aind-data-schema Session. %s", e)
            raise e
        else:
            return self.mapped

    @property
    def mapped(self) -> aind_data_schema.core.rig.Rig:
        if self._mapped is None:
            raise ValueError("Data has not been mapped yet.")
        return self._mapped

    def is_mapped(self) -> bool:
        return self.mapped is not None


class AindSessionDataMapper(AindDataSchemaSessionDataMapper):
    def __init__(
        self,
        session_model: AindBehaviorSessionModel,
        rig_model: AindVrForagingRig,
        task_logic_model: AindVrForagingTaskLogic,
        repository: Union[os.PathLike, git.Repo],
        script_path: os.PathLike,
        session_end_time: Optional[datetime.datetime] = None,
        output_parameters: Optional[Dict] = None,
        subject_info: Optional[WaterLogResult] = None,
    ):
        self.session_model = session_model
        self.rig_model = rig_model
        self.task_logic_model = task_logic_model
        self.repository = repository
        self.script_path = script_path
        self.session_end_time = session_end_time
        self.output_parameters = output_parameters
        self.subject_info = subject_info
        self._mapped: Optional[aind_data_schema.core.session.Session] = None

    @property
    def session_name(self):
        raise self.session_model.session_name

    @property
    def mapped(self) -> aind_data_schema.core.session.Session:
        if self._mapped is None:
            raise ValueError("Data has not been mapped yet.")
        return self._mapped

    def is_mapped(self) -> bool:
        return self.mapped is not None

    def map(self) -> Optional[aind_data_schema.core.session.Session]:
        logger.info("Mapping aind-data-schema Session.")
        try:
            self._mapped = self._map(
                session_model=self.session_model,
                rig_model=self.rig_model,
                task_logic_model=self.task_logic_model,
                repository=self.repository,
                script_path=self.script_path,
                session_end_time=self.session_end_time,
                output_parameters=self.output_parameters,
                subject_info=self.subject_info,
            )
        except (pydantic.ValidationError, ValueError, IOError) as e:
            logger.error("Failed to map to aind-data-schema Session. %s", e)
            raise e
        else:
            return self._mapped

    def write_standard_file(self, directory: os.PathLike) -> None:
        self.mapped.write_standard_file(directory)

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
        subject_info: Optional[WaterLogResult] = None,
        **kwargs,
    ) -> aind_data_schema.core.session.Session:
        # Normalize repository
        if isinstance(repository, os.PathLike | str):
            repository = git.Repo(Path(repository))
        repository_remote_url = repository.remote().url
        repository_sha = repository.head.commit.hexsha
        repository_relative_script_path = Path(script_path).resolve().relative_to(repository.working_dir)

        # Populate calibrations:
        calibrations = [cls._mapper_calibration(rig_model.calibration.water_valve)]
        # Populate cameras
        cameras = data_mapper_service.get_cameras(rig_model, exclude_without_video_writer=True)
        # populate devices
        devices = [
            device[0]
            for device in data_mapper_service.get_fields_of_type(rig_model, AbsRig.HarpDeviceGeneric)
            if device[0]
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
        stimulation_parameters: List[
            aind_data_schema.core.session.AuditoryStimulation
            | aind_data_schema.core.session.OlfactoryStimulation
            | aind_data_schema.core.session.VisualStimulation
        ] = []
        stimulation_devices: List[str] = []
        # Olfactory Stimulation
        stimulus_modalities.append(aind_data_schema.core.session.StimulusModality.OLFACTORY)
        olfactory_stimulus_channel_config: List[aind_data_schema.components.stimulus.OlfactometerChannelConfig] = []
        for _, channel in rig_model.harp_olfactometer.calibration.input.channel_config.items():
            if channel.channel_type == OlfactometerChannelType.ODOR:
                olfactory_stimulus_channel_config.append(
                    coerce_to_aind_data_schema(channel, aind_data_schema.components.stimulus.OlfactometerChannelConfig)
                )
        stimulation_parameters.append(
            aind_data_schema.core.session.OlfactoryStimulation(
                stimulus_name="Olfactory", channels=olfactory_stimulus_channel_config
            )
        )

        _olfactory_device = data_mapper_service.get_fields_of_type(rig_model, AbsRig.HarpOlfactometer)
        if len(_olfactory_device) > 0:
            if _olfactory_device[0][0]:
                stimulation_devices.append(_olfactory_device[0][0])
        else:
            logger.error("Olfactometer device not found in rig model.")
            raise ValueError("Olfactometer device not found in rig model.")

        # Auditory Stimulation
        stimulus_modalities.append(aind_data_schema.core.session.StimulusModality.AUDITORY)

        stimulation_parameters.append(
            aind_data_schema.core.session.AuditoryStimulation(sitmulus_name="Beep", sample_frequency=0)
        )
        speaker_config = aind_data_schema.core.session.SpeakerConfig(name="Speaker", volume=60)
        stimulation_devices.append("speaker")
        # Visual/VR Stimulation
        stimulus_modalities.extend(
            [
                aind_data_schema.core.session.StimulusModality.VISUAL,
                aind_data_schema.core.session.StimulusModality.VIRTUAL_REALITY,
            ]
        )

        stimulation_parameters.append(
            aind_data_schema.core.session.VisualStimulation(
                stimulus_name="VrScreen",
                stimulus_parameters={},
            )
        )
        _screen_device = data_mapper_service.get_fields_of_type(rig_model, AbsRig.Screen)
        if len(_screen_device) > 0:
            if _screen_device[0][0]:
                stimulation_devices.append(_screen_device[0][0])
        else:
            logger.error("Screen device not found in rig model.")
            raise ValueError("Screen device not found in rig model.")

        stimulus_modalities.append(aind_data_schema.core.session.StimulusModality.WHEEL_FRICTION)
        # Mouse platform
        mouse_platform: str = "wheel"

        # Reward delivery
        if rig_model.manipulator.calibration is None:
            logger.error("Manipulator calibration is not set.")
            raise ValueError("Manipulator calibration is not set.")
        initial_position = rig_model.manipulator.calibration.input.initial_position
        reward_delivery_config = aind_data_schema.core.session.RewardDeliveryConfig(
            reward_solution=aind_data_schema.core.session.RewardSolution.WATER,
            reward_spouts=[
                aind_data_schema.core.session.RewardSpoutConfig(
                    side=aind_data_schema.components.devices.SpoutSide.CENTER,
                    variable_position=True,
                    starting_position=aind_data_schema.components.devices.RelativePosition(
                        device_position_transformations=[
                            aind_data_schema.components.coordinates.Translation3dTransform(
                                translation=[initial_position.x, initial_position.y2, initial_position.z]
                            )
                        ],
                        device_origin="Manipulator home",
                        device_axes=[
                            aind_data_schema.components.coordinates.Axis(
                                name=aind_data_schema.components.coordinates.AxisName.X, direction="Left"
                            ),
                            aind_data_schema.components.coordinates.Axis(
                                name=aind_data_schema.components.coordinates.AxisName.Y, direction="Front"
                            ),
                            aind_data_schema.components.coordinates.Axis(
                                name=aind_data_schema.components.coordinates.AxisName.Z, direction="Top"
                            ),
                        ],
                    ),
                )
            ],
        )

        end_time = datetime.datetime.now()

        # Construct aind-data-schema session
        aind_data_schema_session = aind_data_schema.core.session.Session(
            animal_weight_post=subject_info.weight_g if subject_info else None,
            reward_consumed_total=subject_info.water_earned_ml if subject_info else None,
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
                    stream_end_time=session_end_time if session_end_time else end_time,
                    camera_names=list(cameras.keys()),
                ),
            ],
            calibrations=calibrations,
            mouse_platform_name=mouse_platform,
            active_mouse_platform=True,
            stimulus_epochs=[
                aind_data_schema.core.session.StimulusEpoch(
                    stimulus_name=session_model.experiment,
                    stimulus_start_time=session_model.date,
                    stimulus_end_time=session_end_time if session_end_time else end_time,
                    stimulus_modalities=stimulus_modalities,
                    stimulus_parameters=stimulation_parameters,
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
                    speaker_config=speaker_config,
                    reward_consumed_during_epoch=subject_info.total_water_ml if subject_info else None,
                    stimulus_device_names=stimulation_devices,
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


def coerce_to_aind_data_schema(value: TFrom, target_type: Type[TTo]) -> TTo:
    _normalized_input: dict
    if isinstance(value, BaseModel):
        _normalized_input = value.model_dump()
    elif isinstance(value, dict):
        _normalized_input = value
    else:
        raise ValueError(f"Expected value to be a BaseModel or a dict, got {type(value)}")
    target_fields = target_type.model_fields
    _normalized_input = {k: v for k, v in _normalized_input.items() if k in target_fields}
    return target_type(**_normalized_input)


def aind_session_data_mapper_factory(launcher: BehaviorLauncher) -> AindSessionDataMapper:
    now = utcnow()
    return AindSessionDataMapper(
        session_model=launcher.session_schema,
        rig_model=launcher.rig_schema,
        task_logic_model=launcher.task_logic_schema,
        repository=launcher.repository,
        script_path=launcher.services_factory_manager.bonsai_app.workflow,
        session_end_time=now,
    )


def aind_rig_data_mapper_factory(
    launcher: BehaviorLauncher[AindVrForagingRig, AindBehaviorSessionModel, AindVrForagingTaskLogic],
) -> AindRigDataMapper:
    rig_schema: AindVrForagingRig = launcher.rig_schema
    return AindRigDataMapper(
        rig_schema_filename=f"{rig_schema.rig_name}.json",
        db_suffix=f"{_DATABASE_DIR}/{launcher.computer_name}",
        db_root=launcher.config_library_dir,
    )


class AindDataMapperWrapper(data_mapper_service.DataMapperService):
    def __init__(
        self,
        *,
        launcher: Optional[BehaviorLauncher] = None,
        rig_data_mapper_factory: Optional[Callable[[BehaviorLauncher], AindRigDataMapper]] = None,
        session_data_mapper_factory: Optional[Callable[[BehaviorLauncher], AindSessionDataMapper]] = None,
    ):
        super().__init__()
        self._rig_mapper_factory = rig_data_mapper_factory or aind_rig_data_mapper_factory
        self._session_mapper_factory = session_data_mapper_factory or aind_session_data_mapper_factory

        self._rig_mapper: Optional[AindRigDataMapper] = None
        self._session_mapper: Optional[AindSessionDataMapper] = None

        self._session_schema: Optional[aind_data_schema.core.session.Session] = None
        self._rig_schema: Optional[aind_data_schema.core.rig.Rig] = None

        self._launcher = launcher
        self._mapped: Optional[aind_data_schema.core.rig.Rig] = None

    @property
    def session_directory(self):
        return self._launcher.session_directory

    @property
    def session_name(self):
        if self._launcher.session_schema_model is not None:
            return self._launcher.session_schema_model.session_name
        else:
            raise ValueError("Can't infer session name from _launcher.")

    @classmethod
    def from_launcher(
        cls,
        launcher: BehaviorLauncher[AindVrForagingRig, AindBehaviorSessionModel, AindVrForagingTaskLogic],
        rig_data_mapper_factory: Optional[Callable[[BehaviorLauncher], AindRigDataMapper]] = None,
        session_data_mapper_factory: Optional[Callable[[BehaviorLauncher], AindSessionDataMapper]] = None,
    ) -> Self:
        return cls(
            launcher=launcher,
            rig_data_mapper_factory=rig_data_mapper_factory,
            session_data_mapper_factory=session_data_mapper_factory,
        )

    def map(self) -> Tuple[aind_data_schema.core.rig.Rig, aind_data_schema.core.session.Session]:
        if self._launcher is None:
            raise ValueError("Launcher is not set.")
        self._rig_mapper = self._rig_mapper_factory(self._launcher)
        self._session_mapper = self._session_mapper_factory(self._launcher)
        self._rig_schema = self._rig_mapper.map()
        self._session_schema = self._session_mapper.map()
        if self._rig_schema is None or self._session_schema is None:
            raise ValueError("Failed to map data.")
        self._session_schema.rig_id = self._rig_schema.rig_id
        logger.info("Writing session.json to %s", self.session_directory)
        self._session_schema.write_standard_file(self.session_directory)
        logger.info("Writing rig.json to %s", self.session_directory)
        self._rig_schema.write_standard_file(self.session_directory)
        return self.mapped

    @property
    def mapped(self) -> Tuple[aind_data_schema.core.rig.Rig, aind_data_schema.core.session.Session]:
        if self._rig_mapper is None or self._session_mapper is None:
            raise ValueError("Data has not been mapped yet.")
        return (self._rig_schema, self._session_schema)

    def is_mapped(self) -> bool:
        return (self._rig_schema is not None) and (self._session_schema is not None)
