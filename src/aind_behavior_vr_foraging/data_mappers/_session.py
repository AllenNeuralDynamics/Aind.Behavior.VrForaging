import datetime
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, cast, get_args

import aind_behavior_services.rig as AbsRig
import git
import pydantic
from aind_behavior_services.session import AindBehaviorSessionModel
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


class AindSessionDataMapper(ads.AindDataSchemaSessionDataMapper):
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
        self.session_model = model_from_json_file(abs_schemas_path / "session_input.json", AindBehaviorSessionModel)
        self.rig_model = model_from_json_file(abs_schemas_path / "rig_input.json", AindVrForagingRig)
        self.task_logic_model = model_from_json_file(abs_schemas_path / "tasklogic_input.json", AindVrForagingTaskLogic)

        if curriculum_suggestion is not None:
            if isinstance(curriculum_suggestion, CurriculumSuggestion):
                pass
            else:
                curriculum_suggestion = model_from_json_file(Path(curriculum_suggestion), CurriculumSuggestion)
        else:
            try:
                curriculum_suggestion = model_from_json_file(
                    Path(self._data_path) / "Behavior" / "Logs" / "curriculum_suggestion.json",
                    CurriculumSuggestion,
                )
            except FileNotFoundError:
                logger.warning("Curriculum suggestion file not found. Proceeding without it.")
                curriculum_suggestion = None
        self.curriculum = curriculum_suggestion
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
            acquisition_type=self.session_model.experiment or self.task_logic_model.name,
            coordinate_system=None,
            data_streams=self._get_data_streams(),
            calibrations=self._get_calibrations(),
            stimulus_epochs=self._get_stimulus_epochs(),
        )
        return aind_data_schema_session

    def write_standard_file(self) -> None:
        self.mapped.write_standard_file(Path(self._data_path))

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
        if isinstance(device, AbsRig.visual_stimulation.Screen):
            return False
        if isinstance(device, AbsRig.cameras.CameraController):
            return False
        if isinstance(device, get_args(AbsRig.cameras.CameraTypes)):
            return cast(AbsRig.cameras.CameraTypes, device).video_writer is not None
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

        data_streams: list[acquisition.DataStream] = [
            acquisition.DataStream(
                stream_start_time=self.session_model.date,
                stream_end_time=self.session_end_time,
                code=[self._get_bonsai_as_code(), self._get_python_as_code()],
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
        # TODO needs aind-data-schema to be updated
        # stimulus_modalities.append(acquisition.StimulusModality.OLFACTORY)
        # olfactory_stimulus_channel_config: List[aind_data_schema.components.stimulus.OlfactometerChannelConfig] = []
        # olf_calibration = rig_model.harp_olfactometer.calibration
        # if olf_calibration is None:
        #     raise ValueError("Olfactometer calibration is not set in the rig model.")
        # for _, channel in olf_calibration.input.channel_config.items():
        #     if channel.channel_type == OlfactometerChannelType.ODOR:
        #         olfactory_stimulus_channel_config.append(
        #             coerce_to_aind_data_schema(channel, aind_data_schema.components.stimulus.OlfactometerChannelConfig)
        #         )
        # stimulation_parameters.append(
        #     aind_data_schema.core.session.OlfactoryStimulation(
        #         stimulus_name="Olfactory", channels=olfactory_stimulus_channel_config
        #     )
        # )

        # _olfactory_device = get_fields_of_type(rig_model, AbsRig.harp.HarpOlfactometer)
        # if len(_olfactory_device) > 0:
        #     if _olfactory_device[0][0]:
        #         stimulation_devices.append(_olfactory_device[0][0])
        # else:
        #     logger.error("Olfactometer device not found in rig model.")
        #     raise ValueError("Olfactometer device not found in rig model.")

        if self.curriculum is not None:
            performance_metrics = acquisition.PerformanceMetrics(
                output_parameters=acquisition.GenericModel.model_validate(self.curriculum.metrics.model_dump())
            )
            curriculum_status = str(self.curriculum.trainer_state.is_on_curriculum)
        else:
            curriculum_status = "false"
            performance_metrics = None

        stimulus_epochs: list[acquisition.StimulusEpoch] = [
            acquisition.StimulusEpoch(
                active_devices=active_devices,
                code=_stim_code,
                stimulus_start_time=self.session_model.date,
                stimulus_end_time=self.session_end_time,
                configurations=stimulus_epoch_configurations,
                stimulus_name=self.session_model.experiment or self.task_logic_model.name,
                stimulus_modalities=stimulus_modalities,
                performance_metrics=performance_metrics,
                curriculum_status=curriculum_status,
            )
        ]
        return stimulus_epochs

    def _get_cameras_config(self) -> List[acquisition.DetectorConfig]:
        def _map_camera(name: str, camera: AbsRig.cameras.CameraTypes) -> acquisition.DetectorConfig:
            assert camera.video_writer is not None, "Camera does not have a video writer configured."
            return acquisition.DetectorConfig(
                device_name=name,
                exposure_time=getattr(camera, "exposure", -1),
                exposure_time_unit=units.TimeUnit.US,
                trigger_type=configs.TriggerType.EXTERNAL,
                compression=_map_compression(camera.video_writer),
            )

        def _map_compression(compression: AbsRig.cameras.VideoWriter) -> acquisition.Code:
            if compression is None:
                raise ValueError("Camera does not have a video writer configured.")
            if isinstance(compression, AbsRig.cameras.VideoWriterFfmpeg):
                return acquisition.Code(
                    url="https://ffmpeg.org/",
                    name="FFMPEG",
                    parameters=acquisition.GenericModel.model_validate(compression.model_dump()),
                )
            elif isinstance(compression, AbsRig.cameras.VideoWriterOpenCv):
                bonsai = self._get_bonsai_as_code()
                bonsai.parameters = acquisition.GenericModel.model_validate(compression.model_dump())
                return bonsai
            else:
                raise ValueError("Camera does not have a valid video writer configured.")

        cameras = data_mapper_helpers.get_cameras(self.rig_model, exclude_without_video_writer=True)

        return list(map(_map_camera, cameras.keys(), cameras.values()))

    def _get_bonsai_as_code(self) -> acquisition.Code:
        bonsai_folder = Path(self.bonsai_app.executable).parent
        bonsai_env = data_mapper_helpers.snapshot_bonsai_environment(bonsai_folder / "bonsai.config")
        bonsai_version = bonsai_env.get("Bonsai", "unknown")
        assert isinstance(self.repository, git.Repo)

        return acquisition.Code(
            url=self.repository.remote().url,
            name="Aind.Behavior.VrForaging",
            version=self.repository.head.commit.hexsha,
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
