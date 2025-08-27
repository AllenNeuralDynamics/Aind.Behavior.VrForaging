import datetime
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

import aind_behavior_services.calibration as AbsCalibration
import aind_behavior_services.rig as AbsRig
import git
import pydantic
from aind_behavior_services.session import AindBehaviorSessionModel
from aind_behavior_services.utils import get_fields_of_type, utcnow
from aind_data_schema.components import configs, coordinates, measurements
from aind_data_schema.core import acquisition
from aind_data_schema_models import units
from aind_data_schema_models.modalities import Modality
from clabe.apps import CurriculumSuggestion
from clabe.data_mapper import aind_data_schema as ads
from clabe.data_mapper import helpers as data_mapper_helpers
from clabe.launcher import Launcher, Promise

from aind_behavior_vr_foraging.rig import AindManipulatorDevice, AindVrForagingRig
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

logger = logging.getLogger(__name__)


class AindSessionDataMapper(ads.AindDataSchemaSessionDataMapper):
    def __init__(
        self,
        session_model: AindBehaviorSessionModel,
        rig_model: AindVrForagingRig,
        task_logic_model: AindVrForagingTaskLogic,
        repository: Union[os.PathLike, git.Repo],
        script_path: os.PathLike = Path("./src/main.bonsai"),
        session_end_time: Optional[datetime.datetime] = None,
        curriculum: Optional[CurriculumSuggestion] = None,
        output_parameters: Optional[Dict] = None,
    ):
        self.session_model = session_model
        self.rig_model = rig_model
        self.task_logic_model = task_logic_model
        self.repository = repository
        self.script_path = script_path
        self.session_end_time = session_end_time
        self.output_parameters = output_parameters
        self._mapped: Optional[acquisition.Acquisition] = None
        self.curriculum = curriculum

    def session_schema(self):
        return self.mapped

    @classmethod
    def build_runner(cls) -> Callable[[Launcher], "AindSessionDataMapper"]:
        def _new(
            launcher: Launcher, curriculum: Optional[Promise[[Any], CurriculumSuggestion]] = None
        ) -> "AindSessionDataMapper":
            new = cls(
                session_model=launcher.get_session(strict=True),
                rig_model=launcher.get_rig(strict=True),
                task_logic_model=launcher.get_task_logic(strict=True),
                repository=launcher.repository,
                curriculum=curriculum.result if curriculum is not None else None,
            )
            new.map()
            return new

        return _new

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

    def map(self) -> Optional[acquisition.Acquisition]:
        logger.info("Mapping aind-data-schema Session.")
        try:
            self._mapped = self._map()
        except (pydantic.ValidationError, ValueError, IOError) as e:
            logger.error("Failed to map to aind-data-schema Session. %s", e)
            raise e
        else:
            return self._mapped

    def write_standard_file(self, directory: os.PathLike) -> None:
        self.mapped.write_standard_file(Path(directory))

    def get_calibrations(self) -> List[acquisition.CALIBRATIONS]:
        calibrations = []
        calibrations += self.get_water_calibration()
        calibrations += self.get_other_calibrations()
        return calibrations

    def get_other_calibrations(
        self, exclude: List[Type] = [AbsCalibration.water_valve.WaterValveCalibration]
    ) -> List[measurements.Calibration]:
        def _mapper(device_name: Optional[str], calibration: AbsCalibration.Calibration) -> measurements.Calibration:
            device_name = device_name or calibration.device_name
            if device_name is None:
                raise ValueError("Device name is not set.")
            description = calibration.description or calibration.__doc__ or ""
            return measurements.Calibration(
                device_name=device_name,
                calibration_date=calibration.date if calibration.date else utcnow(),
                description=description,
                notes=calibration.notes,
                input=[calibration.input.model_dump_json() if calibration.input else ""],
                output=[calibration.output.model_dump_json() if calibration.output else ""],
                output_unit=units.UnitlessUnit.PERCENT,
                input_unit=units.UnitlessUnit.PERCENT,
            )

        calibrations = get_fields_of_type(self.rig_model, AbsCalibration.Calibration)
        calibrations = [c for c in calibrations if not (isinstance(c[1], tuple(exclude)))]
        return list(map(lambda tup: _mapper(*tup), calibrations)) if len(calibrations) > 0 else []

    def get_water_calibration(self) -> List[measurements.VolumeCalibration]:
        def _mapper(
            device_name: Optional[str], water_calibration: AbsCalibration.water_valve.WaterValveCalibration
        ) -> measurements.VolumeCalibration:
            device_name = device_name or water_calibration.device_name
            if device_name is None:
                raise ValueError("Device name is not set.")
            c = water_calibration.output
            if c is None:
                c = water_calibration.input.calibrate_output()
            assert c.interval_average is not None

            return measurements.VolumeCalibration(
                device_name=device_name,
                calibration_date=water_calibration.date if water_calibration.date else utcnow(),
                notes=water_calibration.notes,
                input=list(c.interval_average.keys()),
                output=list(c.interval_average.values()),
                input_unit=units.TimeUnit.S,
                output_unit=units.VolumeUnit.ML,
                fit=measurements.CalibrationFit(fit_type=measurements.FitType.LINEAR, fit_parameters=c.model_dump()),
            )

        water_calibration = get_fields_of_type(self.rig_model, AbsCalibration.water_valve.WaterValveCalibration)
        return list(map(lambda tup: _mapper(*tup), water_calibration)) if len(water_calibration) > 0 else []

    def _map(self) -> acquisition.Acquisition:
        # Normalize repository
        if isinstance(self.repository, os.PathLike | str):
            self.repository = git.Repo(Path(self.repository))

        if self.session_end_time is None:
            self.session_end_time = utcnow()

        calibrations = self.get_calibrations()

        # Populate cameras
        # populate devices
        # Populate modalities
        modalities: list[Modality] = [getattr(Modality, "BEHAVIOR")]
        if len(self.get_cameras_config()) > 0:
            modalities.append(getattr(Modality, "BEHAVIOR_VIDEOS"))
        modalities = list(set(modalities))

        # Populate stimulus modalities
        stimulus_modalities: list[acquisition.StimulusModality] = []
        active_devices: List[str] = []
        stimulus_epoch_configurations: List = []
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

        # Auditory Stimulation
        stimulus_modalities.append(acquisition.StimulusModality.AUDITORY)
        stimulus_epoch_configurations.append(
            acquisition.SpeakerConfig(device_name="Speaker", volume=60.0, volume_unit=units.SoundIntensityUnit.DB)
        )
        active_devices.append("Speaker")

        # Visual/VR Stimulation
        stimulus_modalities.extend(
            [
                acquisition.StimulusModality.VISUAL,
                acquisition.StimulusModality.VIRTUAL_REALITY,
            ]
        )

        stimulus_modalities.append(acquisition.StimulusModality.WHEEL_FRICTION)
        # Mouse platform
        stimulus_epoch_configurations.append(acquisition.MousePlatformConfig(device_name="wheel", active_control=True))
        _stim_code = self.get_bonsai_as_code()
        _stim_code.parameters = self.task_logic_model.model_dump()

        stimulus_epochs: list[acquisition.StimulusEpoch] = [
            acquisition.StimulusEpoch(
                active_devices=active_devices,
                code=_stim_code,
                stimulus_start_time=self.session_model.date,
                stimulus_end_time=self.session_end_time,
                configurations=stimulus_epoch_configurations,
                stimulus_name=self.session_model.experiment,
                stimulus_modalities=stimulus_modalities,
            )
        ]

        data_streams: list[acquisition.DataStream] = [
            acquisition.DataStream(
                stream_start_time=self.session_model.date,
                stream_end_time=self.session_end_time,
                code=[self.get_bonsai_as_code(), self.get_python_as_code()],
                active_devices=[
                    d[0]
                    for d in get_fields_of_type(self.rig_model, AbsRig.Device, stop_recursion_on_type=False)
                    if d[0] is not None
                ],
                modalities=modalities,
                configurations=self.get_cameras_config() + self.get_manipulators_config(),
                notes=self.session_model.notes,
            )
        ]
        # Construct aind-data-schema session
        aind_data_schema_session = acquisition.Acquisition(
            subject_id=self.session_model.subject,
            instrument_id=self.rig_model.rig_name,
            acquisition_end_time=utcnow(),
            acquisition_start_time=self.session_model.date,
            experimenters=self.session_model.experimenter,
            acquisition_type=self.session_model.experiment,
            coordinate_system=self.make_coordinate_system(),
            data_streams=data_streams,
            calibrations=calibrations,
            stimulus_epochs=stimulus_epochs,
        )
        return aind_data_schema_session

    def get_cameras_config(self) -> List[acquisition.DetectorConfig]:
        def _map_camera(name: str, camera: AbsRig.cameras.CameraTypes) -> acquisition.DetectorConfig:
            return acquisition.DetectorConfig(
                device_name=name,
                exposure_time=getattr(camera, "exposure", -1),
                exposure_time_unit=units.TimeUnit.US,
                trigger_type=configs.TriggerType.EXTERNAL,
                compression=_map_compression(camera.video_writer),
            )

        def _map_compression(compression: AbsRig.cameras.VideoWriter):
            if compression is None:
                raise ValueError("Camera does not have a video writer configured.")
            if isinstance(compression, AbsRig.cameras.VideoWriterFfmpeg):
                return acquisition.Code(url="https://ffmpeg.org/", name="FFMPEG", parameters=compression.model_dump())
            elif isinstance(compression, AbsRig.cameras.VideoWriterOpenCv):
                bonsai = self.get_bonsai_as_code()
                bonsai.parameters = compression.model_dump()
                return bonsai
            else:
                raise ValueError("Camera does not have a valid video writer configured.")

        cameras = data_mapper_helpers.get_cameras(self.rig_model, exclude_without_video_writer=True)

        return list(map(_map_camera, cameras.keys(), cameras.values()))

    def get_manipulators_config(self) -> List[acquisition.ManipulatorConfig]:
        def _mapper(name: Optional[str], manipulator: AindManipulatorDevice) -> acquisition.ManipulatorConfig:
            if name is None:
                raise ValueError("Manipulator device name is None.")
            return acquisition.ManipulatorConfig(
                device_name=name,
                coordinate_system=self.make_coordinate_system(),
                local_axis_positions=coordinates.Translation(translation=[0, 0, 0]),
            )  # TODO what should this be?

        _manipulator = get_fields_of_type(self.rig_model, AindManipulatorDevice)
        if len(_manipulator) == 0:
            raise ValueError("Manipulator device not found in rig model.")
        return list(map(lambda tup: _mapper(*tup), _manipulator))

    def get_bonsai_as_code(self) -> acquisition.Code:
        bonsai_env = data_mapper_helpers.snapshot_bonsai_environment(Path("./bonsai/bonsai.config"))
        bonsai_version = bonsai_env.get("Bonsai", "unknown")
        assert isinstance(self.repository, git.Repo)

        return acquisition.Code(
            url=self.repository.remote().url,
            name="Aind.Behavior.VrForaging",
            version=self.repository.head.commit.hexsha,
            language="Bonsai",
            language_version=bonsai_version,
            run_script=Path("./src/main.bonsai"),
            parameters=bonsai_env,
        )

    def get_python_as_code(self) -> acquisition.Code:
        assert isinstance(self.repository, git.Repo)
        python_env = data_mapper_helpers.snapshot_python_environment()
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
            parameters=python_env,
        )

    @staticmethod
    def make_coordinate_system() -> coordinates.CoordinateSystem:
        return coordinates.CoordinateSystem(
            name="origin",
            origin=coordinates.Origin.BREGMA,
            axis_unit=coordinates.SizeUnit.MM,
            axes=[
                coordinates.Axis(name=coordinates.AxisName.X, direction=coordinates.Direction.LR),
                coordinates.Axis(name=coordinates.AxisName.Y, direction=coordinates.Direction.FB),
                coordinates.Axis(name=coordinates.AxisName.Z, direction=coordinates.Direction.UD),
            ],
        )
