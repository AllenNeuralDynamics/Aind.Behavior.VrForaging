import datetime
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Self, Tuple, Type, TypeVar, Union

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
import pydantic_settings
from aind_behavior_services.calibration import Calibration
from aind_behavior_services.calibration.olfactometer import OlfactometerChannelType
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import model_from_json_file, utcnow
from clabe.apps import BonsaiApp
from clabe.behavior_launcher import BehaviorLauncher, DefaultBehaviorPicker
from clabe.data_mapper import DataMapper
from clabe.data_mapper import aind_data_schema as ads
from clabe.data_mapper import helpers as data_mapper_helpers
from git import Repo

from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

TTo = TypeVar("TTo", bound=pydantic.BaseModel)

T = TypeVar("T")

logger = logging.getLogger(__name__)

_DATABASE_DIR = "AindDataSchemaRig"


class AindRigDataMapper(ads.AindDataSchemaRigDataMapper):
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

    @classmethod
    def from_launcher(cls, launcher: BehaviorLauncher) -> Self:
        picker = launcher.picker
        if isinstance(picker, DefaultBehaviorPicker):
            return cls(
                rig_schema_filename=f"{launcher.rig_schema.rig_name}.json",
                db_suffix=f"{_DATABASE_DIR}/{launcher.computer_name}",
                db_root=picker.config_library_dir,
            )
        else:
            raise NotImplementedError("Only DefaultBehaviorPicker is supported.")


class AindSessionDataMapper(ads.AindDataSchemaSessionDataMapper):
    def __init__(
        self,
        session_model: AindBehaviorSessionModel,
        rig_model: AindVrForagingRig,
        task_logic_model: AindVrForagingTaskLogic,
        repository: Union[os.PathLike, git.Repo],
        script_path: os.PathLike,
        session_end_time: Optional[datetime.datetime] = None,
        output_parameters: Optional[Dict] = None,
    ):
        self.session_model = session_model
        self.rig_model = rig_model
        self.task_logic_model = task_logic_model
        self.repository = repository
        self.script_path = script_path
        self.session_end_time = session_end_time
        self.output_parameters = output_parameters
        self._mapped: Optional[aind_data_schema.core.session.Session] = None

    @classmethod
    def from_launcher(cls, launcher: BehaviorLauncher) -> Self:
        script_path: os.PathLike

        if isinstance(launcher.services_factory_manager.app, BonsaiApp):
            script_path = launcher.services_factory_manager.app.workflow
        else:
            raise NotImplementedError(
                f"Type of app is not supported for mapping. Got {type(launcher.services_factory_manager.app)}"
            )

        return cls(
            session_model=launcher.session_schema,
            rig_model=launcher.rig_schema,
            task_logic_model=launcher.task_logic_schema,
            repository=launcher.repository,
            script_path=script_path,
            session_end_time=utcnow(),
        )

    @property
    def session_name(self) -> str:
        if self.session_model.session_name is None:
            raise ValueError("Session name is not set in the session model.")
        return self.session_model.session_name

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
            )
        except (pydantic.ValidationError, ValueError, IOError) as e:
            logger.error("Failed to map to aind-data-schema Session. %s", e)
            raise e
        else:
            return self._mapped

    def write_standard_file(self, directory: os.PathLike) -> None:
        self.mapped.write_standard_file(Path(directory))

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
        **kwargs,
    ) -> aind_data_schema.core.session.Session:
        # Normalize repository
        if isinstance(repository, os.PathLike | str):
            repository = git.Repo(Path(repository))
        repository_remote_url = repository.remote().url
        repository_sha = repository.head.commit.hexsha
        repository_relative_script_path = Path(script_path).resolve().relative_to(repository.working_dir)

        # Populate calibrations:
        calibrations: List[aind_data_schema.components.devices.Calibration] = []
        calibrations.append(cls._mapper_calibration(rig_model.calibration.water_valve))

        # Populate cameras
        cameras = data_mapper_helpers.get_cameras(rig_model, exclude_without_video_writer=True)
        # populate devices
        devices = [
            device[0]
            for device in data_mapper_helpers.get_fields_of_type(rig_model, AbsRig.harp._HarpDeviceBase)
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
        olf_calibration = rig_model.harp_olfactometer.calibration
        if olf_calibration is None:
            raise ValueError("Olfactometer calibration is not set in the rig model.")
        for _, channel in olf_calibration.input.channel_config.items():
            if channel.channel_type == OlfactometerChannelType.ODOR:
                olfactory_stimulus_channel_config.append(
                    coerce_to_aind_data_schema(channel, aind_data_schema.components.stimulus.OlfactometerChannelConfig)
                )
        stimulation_parameters.append(
            aind_data_schema.core.session.OlfactoryStimulation(
                stimulus_name="Olfactory", channels=olfactory_stimulus_channel_config
            )
        )
        
        _olfactory_device = data_mapper_helpers.get_fields_of_type(rig_model, AbsRig.harp.HarpOlfactometer)
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
        _screen_device = data_mapper_helpers.get_fields_of_type(rig_model, AbsRig.visual_stimulation.Screen)
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
            animal_weight_post=None,
            reward_consumed_total=None,
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
                            parameters=data_mapper_helpers.snapshot_bonsai_environment(
                                config_file=kwargs.get("bonsai_config_path", Path("./bonsai/bonsai.config"))
                            ),
                        ),
                        aind_data_schema.core.session.Software(
                            name="Python",
                            version=f"{repository_remote_url}/blob/{repository_sha}/pyproject.toml",
                            url=f"{repository_remote_url}/blob/{repository_sha}",
                            parameters=data_mapper_helpers.snapshot_python_environment(),
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
                    reward_consumed_during_epoch=None,
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
            description=calibration.description
            if calibration.description
            else f"Calibration for {calibration.device_name}",
            notes=calibration.notes,
        )


def coerce_to_aind_data_schema(value: Union[pydantic.BaseModel, dict], target_type: Type[TTo]) -> TTo:
    if isinstance(value, pydantic.BaseModel):
        _normalized_input = value.model_dump()
    elif isinstance(value, dict):
        _normalized_input = value
    else:
        raise ValueError(f"Expected value to be a pydantic.BaseModel or a dict, got {type(value)}")
    target_fields = target_type.model_fields
    _normalized_input = {k: v for k, v in _normalized_input.items() if k in target_fields}
    return target_type(**_normalized_input)


class AindDataMapperWrapper(DataMapper[Tuple[aind_data_schema.core.rig.Rig, aind_data_schema.core.session.Session]]):
    def __init__(
        self,
        session_name: str,
        session_directory: os.PathLike,
        rig_data_mapper: AindRigDataMapper,
        session_data_mapper: AindSessionDataMapper,
    ):
        super().__init__()

        self._rig_mapper = rig_data_mapper
        self._session_mapper = session_data_mapper

        self._session_schema: Optional[aind_data_schema.core.session.Session] = None
        self._rig_schema: Optional[aind_data_schema.core.rig.Rig] = None

        self._mapped: Optional[Tuple[aind_data_schema.core.rig.Rig, aind_data_schema.core.session.Session]] = None

        self._session_directory = session_directory
        self._session_name = session_name

    @property
    def session_directory(self):
        return self._session_directory

    @property
    def session_name(self):
        return self._session_name

    @classmethod
    def from_launcher(
        cls,
        launcher: BehaviorLauncher[AindVrForagingRig, AindBehaviorSessionModel, AindVrForagingTaskLogic],
    ) -> Self:
        session_name: str
        session_directory: Path
        if launcher.session_schema:
            session_name = launcher.session_schema.session_name  # type: ignore  # this is guaranteed to be set
        else:
            raise ValueError("Can't infer session name from launcher.")
        session_directory = launcher.session_directory

        return cls(
            session_name,
            session_directory,
            rig_data_mapper=AindRigDataMapper.from_launcher(launcher),
            session_data_mapper=AindSessionDataMapper.from_launcher(launcher),
        )

    def map(self) -> Tuple[aind_data_schema.core.rig.Rig, aind_data_schema.core.session.Session]:
        self._rig_schema = self._rig_mapper.map()
        self._session_schema = self._session_mapper.map()
        if self._rig_schema is None or self._session_schema is None:
            raise ValueError("Failed to map data.")
        self._session_schema.rig_id = self._rig_schema.rig_id
        logger.info("Writing session.json to %s", self.session_directory)
        self._session_schema.write_standard_file(Path(self.session_directory))
        logger.info("Writing rig.json to %s", self.session_directory)
        self._rig_schema.write_standard_file(Path(self.session_directory))
        return self.mapped

    @property
    def mapped(self) -> Tuple[aind_data_schema.core.rig.Rig, aind_data_schema.core.session.Session]:
        if self._rig_mapper is None or self._session_mapper is None:
            raise ValueError("Data has not been mapped yet.")
        return (self._rig_schema, self._session_schema)

    def is_mapped(self) -> bool:
        return (self._rig_schema is not None) and (self._session_schema is not None)


class _MapperCli(pydantic_settings.BaseSettings, cli_prog_name="data-mapper", cli_kebab_case=True):
    data_path: os.PathLike = pydantic.Field(description="Path to the session data directory.")
    db_root: os.PathLike = pydantic.Field(
        default=Path(r"\\allen\aind\scratch\AindBehavior.db\AindVrForaging"),
        description="Root directory for the database for additional metadata.",
    )


if __name__ == "__main__":
    cli = pydantic_settings.CliApp()
    parsed_args = cli.run(_MapperCli)
    abs_schemas_path = Path(parsed_args.data_path) / "Behavior" / "Logs"
    session = model_from_json_file(abs_schemas_path / "session_input.json", AindBehaviorSessionModel)
    rig = model_from_json_file(abs_schemas_path / "rig_input.json", AindVrForagingRig)
    task_logic = model_from_json_file(abs_schemas_path / "tasklogic_input.json", AindVrForagingTaskLogic)
    repo = Repo()
    session_mapper = AindSessionDataMapper(
        session_model=session,
        rig_model=rig,
        task_logic_model=task_logic,
        repository=repo,
        script_path=Path("./src/vr-foraging.bonsai"),
    )
    rig_mapper = AindRigDataMapper(rig_schema_filename=f"{rig.rig_name}.json", db_root=Path(parsed_args.db_root))

    assert session.session_name is not None
    wrapped_mapper = AindDataMapperWrapper(
        session_name=session.session_name,
        session_directory=parsed_args.data_path,
        rig_data_mapper=rig_mapper,
        session_data_mapper=session_mapper,
    )
    wrapped_mapper.map()
