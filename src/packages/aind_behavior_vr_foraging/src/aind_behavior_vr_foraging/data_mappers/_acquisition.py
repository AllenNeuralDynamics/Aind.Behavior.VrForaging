import datetime
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, cast, get_args

import aind_behavior_services.rig as AbsRig
import git
import pydantic
from aind_behavior_curriculum import TrainerState
from aind_behavior_services.rig import cameras, visual_stimulation
from aind_behavior_services.session import Session
from aind_behavior_services.utils import get_fields_of_type, model_from_json_file, utcnow
from aind_data_schema.components import configs
from aind_data_schema.core import acquisition
from aind_data_schema_models import units
from aind_data_schema_models.modalities import Modality
from clabe.apps import BonsaiApp, CurriculumSuggestion
from clabe.data_mapper import aind_data_schema as ads
from clabe.data_mapper import helpers as data_mapper_helpers
from pydantic import AwareDatetime

from aind_behavior_vr_foraging.data_contract.utils import calculate_consumed_water
from aind_behavior_vr_foraging.rig import AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from ._utils import TrackedDevices, _get_water_calibration

logger = logging.getLogger(__name__)


class AindAcquisitionDataMapper(ads.AindDataSchemaSessionDataMapper):
    def __init__(
        self,
        data_path: os.PathLike,
        repo_path: os.PathLike,
        curriculum_suggestion: Optional[os.PathLike] | CurriculumSuggestion = None,
        session_end_time: Optional[AwareDatetime] = None,
    ):
        self._data_path = data_path
        self._repo_path = repo_path
        self._session_end_time = session_end_time

        abs_schemas_path = Path(self._data_path) / "Behavior" / "Logs"
        self.session_model = model_from_json_file(abs_schemas_path / "session_input.json", Session)
        self.rig_model = model_from_json_file(abs_schemas_path / "rig_input.json", AindVrForagingRig)
        self.task_model = model_from_json_file(abs_schemas_path / "tasklogic_input.json", AindVrForagingTaskLogic)

        self.trainer_state: TrainerState | None = None
        trainer_state_path = Path(self._data_path) / "Behavior" / "trainer_state.json"
        if trainer_state_path.exists():
            self.trainer_state = model_from_json_file(
                trainer_state_path,
                TrainerState,
            )

        if curriculum_suggestion is not None:
            if isinstance(curriculum_suggestion, CurriculumSuggestion):
                pass
            else:
                curriculum_suggestion = model_from_json_file(Path(curriculum_suggestion), CurriculumSuggestion)
        else:
            try:
                curriculum_suggestion = model_from_json_file(
                    Path(self._data_path) / "Behavior" / "Logs" / "suggestion.json",
                    CurriculumSuggestion,
                )
            except FileNotFoundError:
                logger.warning("Curriculum suggestion file not found. Proceeding without it.")
                curriculum_suggestion = None
        self.curriculum_suggestion = curriculum_suggestion
        self.repository = git.Repo(self._repo_path)
        assert self.repository.working_tree_dir is not None
        self.bonsai_app = BonsaiApp(
            executable=Path(self.repository.working_tree_dir) / "bonsai" / "bonsai.exe",
            workflow=Path(self.repository.working_tree_dir) / "src" / "main.bonsai",
        )

        self._mapped: Optional[acquisition.Acquisition] = None

    @property
    def session_end_time(self) -> datetime.datetime:
        if self._session_end_time is None:
            raise ValueError("Session end time is not set.")
        return self._session_end_time

    def session_schema(self):
        return self.mapped

    @property
    def session_name(self) -> str:
        if self.session_model.session_name is None:
            raise ValueError("Session name is not set in the session model.")
        return self.session_model.session_name

    @property
    def mapped(self) -> acquisition.Acquisition:
        if self._mapped is None:
            raise ValueError("Data has not been mapped yet.")
        return self._mapped

    def is_mapped(self) -> bool:
        return self.mapped is not None

    def map(self) -> acquisition.Acquisition:
        logger.info("Mapping aind-data-schema Session.")
        try:
            self._mapped = self._map()
        except (pydantic.ValidationError, ValueError, IOError) as e:
            logger.error("Failed to map to aind-data-schema Session. %s", e)
            raise e
        else:
            return self._mapped

    def _map(self) -> acquisition.Acquisition:
        if self._session_end_time is None:
            logger.warning("Session end time is not set. Using current time as end time.")
            self._session_end_time = utcnow()

        # Construct aind-data-schema session
        aind_data_schema_session = acquisition.Acquisition(
            subject_id=self.session_model.subject,
            subject_details=self._get_subject_details(),
            instrument_id=self.rig_model.rig_name,
            acquisition_end_time=utcnow(),
            acquisition_start_time=self.session_model.date,
            experimenters=self.session_model.experimenter,
            acquisition_type=self.task_model.name,
            coordinate_system=None,
            data_streams=self._get_data_streams(),
            calibrations=self._get_calibrations(),
            stimulus_epochs=self._get_stimulus_epochs(),
        )
        return aind_data_schema_session

    def _get_subject_details(self) -> acquisition.AcquisitionSubjectDetails:
        return acquisition.AcquisitionSubjectDetails(
            mouse_platform_name=TrackedDevices.WHEEL,
            reward_consumed_total=calculate_consumed_water(self._data_path),
            reward_consumed_unit=units.VolumeUnit.ML,
        )

    def _get_calibrations(self) -> List[acquisition.CALIBRATIONS]:
        calibrations = []
        calibrations += _get_water_calibration(self.rig_model)
        return calibrations

    @staticmethod
    def _include_device(device: AbsRig.Device) -> bool:
        if isinstance(device, visual_stimulation.ScreenAssembly):
            return False
        if isinstance(device, cameras.CameraController):
            return False
        if isinstance(device, get_args(cameras.CameraTypes)):
            return cast(cameras.CameraTypes, device).video_writer is not None
        return True

    def _get_data_streams(self) -> List[acquisition.DataStream]:
        assert self.session_end_time is not None, "Session end time is not set."

        modalities: list[Modality] = [getattr(Modality, "BEHAVIOR")]
        if len(self._get_cameras_config()) > 0:
            modalities.append(getattr(Modality, "BEHAVIOR_VIDEOS"))
        modalities = list(set(modalities))

        active_devices = [
            _device[0]
            for _device in get_fields_of_type(self.rig_model, AbsRig.Device, stop_recursion_on_type=False)
            if _device[0] is not None and self._include_device(_device[1])
        ]

        code = [self._get_bonsai_as_code(), self._get_python_as_code()]
        if (
            self.curriculum_suggestion is not None
            and self.curriculum_suggestion.trainer_state is not None
            and self.curriculum_suggestion.trainer_state.curriculum is not None
            and self.curriculum_suggestion.trainer_state.is_on_curriculum is True
        ):
            code.append(self._get_curriculum_as_code())

        data_streams: list[acquisition.DataStream] = [
            acquisition.DataStream(
                stream_start_time=self.session_model.date,
                stream_end_time=self.session_end_time,
                code=code,
                active_devices=active_devices,
                modalities=modalities,
                configurations=self._get_cameras_config(),
                notes=self.session_model.notes,
            )
        ]
        return data_streams

    def _get_stimulus_epochs(self) -> List[acquisition.StimulusEpoch]:
        stimulus_modalities: list[acquisition.StimulusModality] = []
        active_devices: List[str] = []
        stimulus_epoch_configurations: List = []

        # Auditory Stimulation
        stimulus_modalities.append(acquisition.StimulusModality.AUDITORY)
        stimulus_epoch_configurations.append(
            acquisition.SpeakerConfig(
                device_name=TrackedDevices.SPEAKER, volume=60.0, volume_unit=units.SoundIntensityUnit.DB
            )
        )
        active_devices.append(TrackedDevices.SPEAKER)

        # Visual/VR Stimulation
        stimulus_modalities.extend(
            [
                acquisition.StimulusModality.VISUAL,
                acquisition.StimulusModality.VIRTUAL_REALITY,
            ]
        )

        # Mouse platform
        stimulus_modalities.append(acquisition.StimulusModality.WHEEL_FRICTION)
        stimulus_epoch_configurations.append(
            acquisition.MousePlatformConfig(device_name=TrackedDevices.WHEEL, active_control=True)
        )

        # Stimulus code
        # Note: According to this discussion, if stimuli are programmatically generated, we can use this instead of configuration.
        # https://github.com/AllenNeuralDynamics/aind-data-schema/discussions/1550#discussioncomment-14246854
        _stim_code = self._get_bonsai_as_code()
        _stim_code.parameters = acquisition.GenericModel.model_validate(
            {
                "task_logic": "./Behavior/Logs/tasklogic_input.json",
                "rig": "./Behavior/Logs/rig_input.json",
                "session": "./Behavior/Logs/session_input.json",
            }
        )

        # Olfactory Stimulation
        import aind_data_schema.components.configs
        from aind_behavior_services.rig.olfactometer import OlfactometerChannelType

        stimulus_modalities.append(acquisition.StimulusModality.OLFACTORY)
        olfactory_stimulus_channel_info: List[aind_data_schema.components.configs.OlfactometerChannelInfo] = []
        olf_calibration = self.rig_model.harp_olfactometer.calibration
        if olf_calibration is None:
            raise ValueError("Olfactometer calibration is not set in the rig model.")
        for _, channel in olf_calibration.channel_config.items():
            if channel.channel_type == OlfactometerChannelType.ODOR:
                # These fields are required, so...
                if not (channel.odorant is None and channel.odorant_dilution is None):
                    olfactory_stimulus_channel_info.append(
                        aind_data_schema.components.configs.OlfactometerChannelInfo(
                            channel_index=channel.channel_index,
                            odorant=channel.odorant,
                            dilution=channel.odorant_dilution,
                        )
                    )
                else:
                    logger.warning(
                        "Olfactometer channel %d is configured as ODOR but odorant or dilution is not set. Skipping this channel.",
                        channel.channel_index,
                    )

        stimulus_epoch_configurations.append(
            aind_data_schema.components.configs.OlfactometerConfig(
                device_name=TrackedDevices.OLFACTOMETER, channel_configs=olfactory_stimulus_channel_info
            )
        )

        # Animal performance, curriculum, and metrics
        performance_metrics: Optional[acquisition.PerformanceMetrics] = None
        curriculum_status: Optional[str] = None
        training_protocol_name: Optional[str] = None

        if self.curriculum_suggestion is not None:
            logger.debug("Curriculum suggestion found. Setting performance metrics based on curriculum suggestion.")
            performance_metrics = acquisition.PerformanceMetrics(
                output_parameters=acquisition.GenericModel.model_validate(
                    self.curriculum_suggestion.metrics.model_dump()
                )
            )
        if self.trainer_state is not None:
            logger.debug("Trainer state found. Setting curriculum status based on trainer state.")
            if self.trainer_state.stage is not None:
                curriculum_status = str(self.trainer_state.stage.name)
            if self.trainer_state.curriculum is not None:
                training_protocol_name = str(self.trainer_state.curriculum.name)

        stimulus_epochs: list[acquisition.StimulusEpoch] = [
            acquisition.StimulusEpoch(
                active_devices=active_devices,
                code=_stim_code,
                stimulus_start_time=self.session_model.date,
                stimulus_end_time=self.session_end_time,
                configurations=stimulus_epoch_configurations,
                stimulus_name=self.task_model.name,
                stimulus_modalities=stimulus_modalities,
                performance_metrics=performance_metrics,
                curriculum_status=curriculum_status,
                training_protocol_name=training_protocol_name,
            )
        ]
        return stimulus_epochs

    def _get_cameras_config(self) -> list[acquisition.DetectorConfig]:
        def _map_camera(name: str, camera: cameras.CameraTypes) -> acquisition.DetectorConfig:
            assert camera.video_writer is not None, "Camera does not have a video writer configured."
            return acquisition.DetectorConfig(
                device_name=name,
                exposure_time=getattr(camera, "exposure", -1),
                exposure_time_unit=units.TimeUnit.US,
                trigger_type=configs.TriggerType.EXTERNAL,
                compression=_map_compression(camera.video_writer),
            )

        def _map_compression(compression: cameras.VideoWriter) -> acquisition.Code:
            if compression is None:
                raise ValueError("Camera does not have a video writer configured.")
            if isinstance(compression, cameras.VideoWriterFfmpeg):
                return acquisition.Code(
                    url="https://ffmpeg.org/",
                    name="FFMPEG",
                    parameters=acquisition.GenericModel.model_validate(compression.model_dump()),
                )
            elif isinstance(compression, cameras.VideoWriterOpenCv):
                bonsai = self._get_bonsai_as_code()
                bonsai.parameters = acquisition.GenericModel.model_validate(compression.model_dump())
                return bonsai
            else:
                raise ValueError("Camera does not have a valid video writer configured.")

        _cameras = data_mapper_helpers.get_cameras(self.rig_model, exclude_without_video_writer=True)

        return list(map(_map_camera, _cameras.keys(), _cameras.values()))

    def _get_bonsai_as_code(self) -> acquisition.Code:
        bonsai_folder = Path(self.bonsai_app.executable).parent
        bonsai_env = data_mapper_helpers.snapshot_bonsai_environment(bonsai_folder / "bonsai.config")
        bonsai_version = bonsai_env.get("Bonsai", "unknown")
        assert isinstance(self.repository, git.Repo)

        return acquisition.Code(
            url=self.repository.remote().url,
            name="Aind.Behavior.VrForaging",
            version=self.repository.head.commit.hexsha,
            # version=__semver__,  # TODO slot this in when this is solved https://github.com/AllenNeuralDynamics/aind-data-schema/issues/1789
            # sha=self.repository.head.commit.hexsha,
            language="Bonsai",
            language_version=bonsai_version,
            run_script=Path(self.bonsai_app.workflow),
        )

    def _get_python_as_code(self) -> acquisition.Code:
        assert isinstance(self.repository, git.Repo)
        # python_env = data_mapper_helpers.snapshot_python_environment()
        v = sys.version_info
        semver = f"{v.major}.{v.minor}.{v.micro}"
        if v.releaselevel != "final":
            semver += f"-{v.releaselevel}.{v.serial}"
        return acquisition.Code(
            url=self.repository.remote().url,
            name="aind-behavior-vr-foraging",
            version=self.repository.head.commit.hexsha,
            language="Python",
            language_version=semver,
        )

    def _get_curriculum_as_code(self) -> acquisition.Code:
        if self.curriculum_suggestion is None:
            raise ValueError("Curriculum suggestion is not set.")
        if (
            self.curriculum_suggestion.trainer_state is None
            or self.curriculum_suggestion.trainer_state.curriculum is None
        ):
            raise ValueError("Trainer state or curriculum is not set in the curriculum suggestion.")
        return acquisition.Code(
            url=self.repository.remote().url,
            # sha=self.repository.head.commit.hexsha, #  TODO see https://github.com/AllenNeuralDynamics/aind-data-schema/issues/1789
            name=self.curriculum_suggestion.trainer_state.curriculum.pkg_location,
            version=self.curriculum_suggestion.trainer_state.curriculum.version,
            language="aind-behavior-curriculum",
            language_version=self.curriculum_suggestion.dsl_version,
        )
