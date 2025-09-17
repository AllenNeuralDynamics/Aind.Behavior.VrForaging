import dataclasses
import logging
import os
import platform
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Optional, cast

import aind_behavior_services.rig as AbsRig
from aind_behavior_services import calibration as AbsCalibration
from aind_data_schema.base import GenericModel
from aind_data_schema.components import connections, coordinates, devices, measurements
from aind_data_schema.core import instrument
from aind_data_schema_models import coordinates as aind_schema_model_coordinates
from aind_data_schema_models import modalities, units
from clabe.data_mapper import aind_data_schema as ads
from clabe.launcher import Launcher

from aind_behavior_vr_foraging.rig import AindVrForagingRig

from ._utils import TrackedDevices, utcnow

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class _DeviceNode:
    """Helper class to keep track of devices, their connections and spawned devices"""

    device: devices.Device
    connections_from: list[connections.Connection] = dataclasses.field(default_factory=list)
    spawned_devices: list[devices.Device] = dataclasses.field(default_factory=list)

    @property
    def device_name(self) -> str:
        return self.device.name

    def get_spawned_device(self, name: str) -> devices.Device:
        for d in self.spawned_devices:
            if d.name == name:
                return d
        raise ValueError(f"Device {name} not found in spawned devices of {self.device_name}")


class AindRigDataMapper(ads.AindDataSchemaRigDataMapper):
    def __init__(
        self,
        rig_model: AindVrForagingRig,
    ):
        super().__init__()
        self.rig_model = rig_model
        self._mapped: Optional[instrument.Instrument] = None

    def rig_schema(self):
        return self.mapped

    @property
    def session_name(self):
        raise NotImplementedError("Method not implemented.")

    def write_standard_file(self, directory: os.PathLike) -> None:
        self.mapped.write_standard_file(Path(directory))

    def map(self) -> instrument.Instrument:
        logger.info("Mapping aind-data-schema Rig.")
        self._mapped = self._map(self.rig_model)
        return self.mapped

    @property
    def mapped(self) -> instrument.Instrument:
        if self._mapped is None:
            raise ValueError("Data has not been mapped yet.")
        return self._mapped

    def is_mapped(self) -> bool:
        return self.mapped is not None

    @classmethod
    def build_runner(cls) -> Callable[[Launcher[AindVrForagingRig, Any, Any]], "AindRigDataMapper"]:
        def _new(
            launcher: Launcher[AindVrForagingRig, Any, Any],
        ) -> "AindRigDataMapper":
            new = cls(rig_model=launcher.get_rig(strict=True))
            new.map()
            return new

        return _new

    ## From here on, private methods only!
    ## Lasciate ogne speranza, voi ch'entrate

    @classmethod
    def _map(cls, rig: AindVrForagingRig) -> instrument.Instrument:
        _modalities = [modalities.Modality.BEHAVIOR, modalities.Modality.BEHAVIOR_VIDEOS]
        _components, _connections = cls._get_all_components_and_connections(rig)
        _calibrations: list[measurements.Calibration] = cls._get_calibrations(rig)

        computer = cls._get_computer(rig)
        _connections.extend(
            cls._get_connections_from_computer_to_type(
                computer,
                [devices.HarpDevice, devices.Camera],
                _components,
                source_port="USB",
                target_port="USB",
                send_and_receive=True,
            )
        )
        _connections.extend(
            cls._get_connections_from_computer_to_type(
                computer, [devices.Monitor], _components, source_port="HDMI", target_port="HDMI", send_and_receive=False
            )
        )

        return instrument.Instrument(
            instrument_id=rig.rig_name,
            modalities=_modalities,
            modification_date=utcnow().date(),
            coordinate_system=coordinates.CoordinateSystemLibrary.BREGMA_ARI,  # this is going to change possibly
            components=_components,  # type: ignore [arg-type]
            connections=_connections,
            calibrations=_calibrations,
        )

    @staticmethod
    def _get_connections_from_computer_to_type(
        computer: devices.Computer,
        types: list[type[devices.Device]],
        devices: list[devices.Device],
        source_port: Optional[str] = None,
        target_port: Optional[str] = None,
        send_and_receive: bool = True,
    ) -> list[connections.Connection]:
        result_connections = []
        computer_name = computer.name

        for device in devices:
            if any(isinstance(device, device_type) for device_type in types):
                result_connections.append(
                    connections.Connection(
                        source_device=computer_name,
                        target_device=device.name,
                        source_port=source_port,
                        target_port=target_port,
                        send_and_receive=send_and_receive,
                    )
                )
        return result_connections

    @staticmethod
    def _get_computer(rig: AindVrForagingRig) -> devices.Computer:
        return devices.Computer(
            name=TrackedDevices.COMPUTER,
            manufacturer=devices.Organization.AIND,
            operating_system=platform.platform(),
            serial_number=rig.computer_name,
        )

    @staticmethod
    def _get_enclosure() -> devices.Enclosure:
        return devices.Enclosure(
            name=TrackedDevices.ENCLOSURE,
            size=coordinates.Scale(scale=[568, 540, 506]),
            size_unit=units.SizeUnit.MM,
            manufacturer=devices.Organization.AIND,
            internal_material="High density foam",
            external_material="Wood and aluminum frame",
            grounded=True,
            air_filtration=False,
            laser_interlock=False,
        )

    @staticmethod
    def _get_calibrations(rig: AindVrForagingRig) -> list[measurements.Calibration]:
        return []  # We will assume that all calibrations are stored in the session.

    @staticmethod
    def _get_harp_behavior_node(rig: AindVrForagingRig) -> _DeviceNode:
        _connections: list[connections.Connection] = []
        source_device = rig.harp_behavior.name or "harp_behavior"

        # Add triggered camera controller
        if rig.triggered_camera_controller:
            for _name in rig.triggered_camera_controller.cameras.keys():
                _connections.append(
                    connections.Connection(
                        source_device=source_device,
                        source_port="DO0",
                        target_device=_name,
                        target_port="OPTOIN",  # codespell:ignore
                    )
                )
        # speaker
        _connections.append(
            connections.Connection(
                source_device=source_device,
                source_port="DO2",
                target_device=TrackedDevices.SPEAKER,
            )
        )
        # photodiode
        _connections.append(
            connections.Connection(
                source_device=source_device,
                source_port="DIPort0",
                target_device=TrackedDevices.PHOTODIODE,
                target_port="0",
            )
        )

        # solenoid
        _connections.append(
            connections.Connection(
                source_device=source_device,
                source_port="SupplyPort0",
                target_device=TrackedDevices.WATER_VALVE_SOLENOID,
            )
        )

        speaker = devices.Speaker(
            name=TrackedDevices.SPEAKER,
            relative_position=[aind_schema_model_coordinates.AnatomicalRelative.SUPERIOR],
            manufacturer=devices.Organization.TYMPHANY,
            model="XT25SC90-04",
        )

        photodiode = devices.Device(
            name=TrackedDevices.PHOTODIODE,
            manufacturer=devices.Organization.AIND,
            model="",
        )

        water_valve = devices.Device(
            name=TrackedDevices.WATER_VALVE_SOLENOID,
            manufacturer=devices.Organization.THE_LEE_COMPANY,
            model="LHDB1233518H",
        )

        _daq_channels = [
            devices.DAQChannel(channel_name=connection.source_port, channel_type=_get_channel_type(connection))
            for connection in _connections
            if connection.source_port is not None
        ]

        _harp_device = devices.HarpDevice(
            name=source_device,
            harp_device_type=devices.HarpDeviceType.BEHAVIOR,
            manufacturer=devices.Organization.OEPS,
            is_clock_generator=False,
            channels=_daq_channels,
        )

        return _DeviceNode(
            device=_harp_device,
            connections_from=_connections,
            spawned_devices=[speaker, photodiode, water_valve],
        )

    @staticmethod
    def _get_harp_treadmill_node(rig: AindVrForagingRig) -> _DeviceNode:
        source_device = rig.harp_treadmill.name or "harp_treadmill"

        _connections = [
            connections.Connection(
                source_device=source_device, target_device=TrackedDevices.MAGNETIC_BRAKE, send_and_receive=True
            ),
            connections.Connection(
                source_device=source_device, target_device=TrackedDevices.TORQUE_SENSOR, send_and_receive=True
            ),
            connections.Connection(
                source_device=source_device, target_device=TrackedDevices.ROTARY_ENCODER, send_and_receive=True
            ),
        ]

        _daq_channels = [
            devices.DAQChannel(channel_name=TrackedDevices.MAGNETIC_BRAKE, channel_type=devices.DaqChannelType.AO),
            devices.DAQChannel(channel_name=TrackedDevices.TORQUE_SENSOR, channel_type=devices.DaqChannelType.AI),
            devices.DAQChannel(channel_name=TrackedDevices.ROTARY_ENCODER, channel_type=devices.DaqChannelType.DI),
        ]

        magnetic_brake = devices.Device(
            name=TrackedDevices.MAGNETIC_BRAKE,
            manufacturer=devices.Organization.PLACID_INDUSTRIES,
            model="B1-2FM",
        )

        encoder = devices.Device(
            name=TrackedDevices.ROTARY_ENCODER,
            manufacturer=devices.Organization.AIND,
            model="AMT102-V",
        )

        torque_sensor = devices.Device(
            name=TrackedDevices.TORQUE_SENSOR,
            manufacturer=devices.Organization.TRANSDUCER_TECHNIQUES,
            model="RTS-10",
        )

        _harp_device = devices.HarpDevice(
            name=source_device,
            harp_device_type=devices.HarpDeviceType.TREADMILL,
            manufacturer=devices.Organization.AIND,
            is_clock_generator=False,
            channels=_daq_channels,
        )

        return _DeviceNode(
            device=_harp_device, connections_from=_connections, spawned_devices=[magnetic_brake, encoder, torque_sensor]
        )

    @staticmethod
    def _get_harp_clock_generate_node(rig: AindVrForagingRig, components: list[devices.Device]) -> _DeviceNode:
        source_device = rig.harp_clock_generator.name or "harp_clock_generator"
        harp_devices = [d for d in components if isinstance(d, devices.HarpDevice)]
        _connections = [
            connections.Connection(
                source_device=source_device,
                target_device=device.name,
                source_port="ClkOut",
                target_port="ClkIn",
            )
            for device in harp_devices
            if device.name != source_device
        ]

        harp_device = devices.HarpDevice(
            name=source_device,
            harp_device_type=devices.HarpDeviceType.WHITERABBIT,
            manufacturer=devices.Organization.AIND,
            is_clock_generator=True,
            channels=[
                devices.DAQChannel(channel_name="ClkOut", channel_type=devices.DaqChannelType.DO),
            ],
        )

        return _DeviceNode(device=harp_device, connections_from=_connections)

    @staticmethod
    def _get_wheel(
        rig: AindVrForagingRig, encoder: devices.Device, magnetic_brake: devices.Device, torque_sensor: devices.Device
    ) -> devices.Wheel:
        if rig.harp_treadmill.calibration is None or rig.harp_treadmill.calibration.output is None:
            raise ValueError("Treadmill calibration is not set.")
        return devices.Wheel(
            name=TrackedDevices.WHEEL,
            manufacturer=devices.Organization.AIND,
            radius=Decimal(str(rig.harp_treadmill.calibration.output.wheel_diameter)) / 2,
            width=Decimal("3.5"),
            size_unit=units.SizeUnit.CM,
            encoder=encoder,
            magnetic_brake=magnetic_brake,
            torque_sensor=torque_sensor,
            pulse_per_revolution=rig.harp_treadmill.calibration.output.pulses_per_revolution,
            notes="https://tinyurl.com/AI-RunningWheel",
        )

    @classmethod
    def _get_all_components_and_connections(
        cls, rig: AindVrForagingRig
    ) -> tuple[list[devices.DataModel], list[connections.Connection]]:
        _components: list[devices.DataModel] = []
        _connections: list[connections.Connection] = []

        _components.append(cls._get_computer(rig))

        _components.append(cls._get_enclosure())

        harp_behavior_node = cls._get_harp_behavior_node(rig)
        _components.append(harp_behavior_node.device)
        _components.extend(harp_behavior_node.spawned_devices)
        _connections.extend(harp_behavior_node.connections_from)

        harp_treadmill_node = cls._get_harp_treadmill_node(rig)
        _components.append(harp_treadmill_node.device)
        _components.extend(harp_treadmill_node.spawned_devices)
        _connections.extend(harp_treadmill_node.connections_from)

        _components.append(cls._get_olfactometer(rig))

        # Get all other harp devices
        harp_lickometer = devices.HarpDevice(
            name=rig.harp_lickometer.name or "harp_lickometer",
            harp_device_type=devices.HarpDeviceType.LICKETYSPLIT,
            manufacturer=devices.Organization.AIND,
            is_clock_generator=False,
        )

        if rig.harp_sniff_detector is not None:
            _components.append(
                devices.HarpDevice(
                    name=rig.harp_sniff_detector.name or "harp_sniff_detector",
                    harp_device_type=devices.HarpDeviceType.SNIFFDETECTOR,
                    is_clock_generator=False,
                )
            )

        if rig.harp_environment_sensor is not None:
            _components.append(
                devices.HarpDevice(
                    name=rig.harp_environment_sensor.name or "harp_environment_sensor",
                    harp_device_type=devices.HarpDeviceType.ENVIRONMENTSENSOR,
                    is_clock_generator=False,
                )
            )

        # Leave the clock for last to bind all the devices to it
        harp_clock_generator_node = cls._get_harp_clock_generate_node(rig, _components)
        _components.append(harp_clock_generator_node.device)
        _connections.extend(harp_clock_generator_node.connections_from)

        _components.append(
            cls._get_wheel(
                rig=rig,
                encoder=harp_treadmill_node.get_spawned_device(TrackedDevices.ROTARY_ENCODER),
                magnetic_brake=harp_treadmill_node.get_spawned_device(TrackedDevices.MAGNETIC_BRAKE),
                torque_sensor=harp_treadmill_node.get_spawned_device(TrackedDevices.TORQUE_SENSOR),
            )
        )
        _components.extend(cls._get_monitors(rig))
        camera_assemblies, cameras = cls._get_camera_assemblies(rig)
        _components.extend(camera_assemblies)
        _components.extend(cameras)
        _components.extend(cls._get_optics())

        # Manipulator and lick spout assembly
        _components.append(
            cls._get_lickspout_assembly(
                rig=rig,
                harp_lickometer=harp_lickometer,
                water_valve=harp_behavior_node.get_spawned_device(TrackedDevices.WATER_VALVE_SOLENOID),
            )
        )

        return _components, _connections

    @staticmethod
    def _get_monitors(rig: AindVrForagingRig) -> list[devices.Monitor]:
        pos = {
            "left": [
                aind_schema_model_coordinates.AnatomicalRelative.ANTERIOR,
                aind_schema_model_coordinates.AnatomicalRelative.LEFT,
            ],
            "center": [
                aind_schema_model_coordinates.AnatomicalRelative.ANTERIOR,
                aind_schema_model_coordinates.AnatomicalRelative.MEDIAL,
            ],
            "right": [
                aind_schema_model_coordinates.AnatomicalRelative.ANTERIOR,
                aind_schema_model_coordinates.AnatomicalRelative.RIGHT,
            ],
        }

        def distance_from_vector(vector: AbsRig.visual_stimulation.Vector3):
            return (vector.x**2 + vector.y**2 + vector.z**2) ** 0.5

        def _get_monitors(display_name: str):
            display = cast(AbsRig.visual_stimulation.DisplayCalibration, getattr(rig.screen.calibration, display_name))
            return devices.Monitor(
                name=f"{str(TrackedDevices.SCREEN)}_{display_name}",
                manufacturer=devices.Organization.LG,
                relative_position=pos[display_name],
                model="LG LP097QX1",
                refresh_rate=int(rig.screen.target_render_frequency),
                width=int(display.intrinsics.display_width),
                height=int(display.intrinsics.display_height),
                size_unit=units.SizeUnit.PX,
                viewing_distance=Decimal(str(distance_from_vector(display.extrinsics.translation))),
                viewing_distance_unit=units.SizeUnit.CM,
                contrast=abs(int(rig.screen.contrast * 100)),
                brightness=abs(int(rig.screen.brightness * 100)),
            )

        return [_get_monitors(name) for name in ["left", "center", "right"]]

    @staticmethod
    def _get_lickspout_assembly(
        rig: AindVrForagingRig, harp_lickometer: devices.HarpDevice, water_valve: devices.Device
    ) -> devices.LickSpoutAssembly:
        manipulator = rig.manipulator
        calibration = manipulator.calibration
        if calibration is None:
            raise ValueError("Manipulator calibration is not set.")
        stage = devices.MotorizedStage(
            name=TrackedDevices.MOTORIZED_STAGE,
            manufacturer=devices.Organization.AIND,
            model="328-300-00",
            travel=Decimal("30"),
            travel_unit=units.SizeUnit.CM,
            notes="This stage is driven by the HarpStepperDriver device.",
        )

        return devices.LickSpoutAssembly(
            name=str(TrackedDevices.LICK_SPOUT) + "_assembly",
            lick_spouts=[
                devices.LickSpout(
                    name=TrackedDevices.LICK_SPOUT,
                    manufacturer=devices.Organization.OTHER,
                    model="89875K27",
                    spout_diameter=Decimal("1.2"),
                    spout_diameter_unit=units.SizeUnit.MM,
                    solenoid_valve=water_valve,
                    lick_sensor_type=devices.LickSensorType("Capacitive"),
                    lick_sensor=harp_lickometer,
                    notes="Lick spout for water delivery, the tube is ordered from McMaster, cut to size and shaped by AIND",
                )
            ],
            motorized_stage=stage,
        )

    @staticmethod
    def _get_olfactometer(rig: AindVrForagingRig) -> devices.Olfactometer:
        olf_calibration = rig.harp_olfactometer.calibration
        if olf_calibration is None or (calibration := olf_calibration.input) is None:
            raise ValueError("Olfactometer calibration is not set.")

        return devices.Olfactometer(
            name="harp_olfactometer",
            harp_device_type=devices.HarpDeviceType.OLFACTOMETER,
            manufacturer=devices.Organization.CHAMPALIMAUD,
            is_clock_generator=False,
            channels=list(map(_get_olfactometer_channel, calibration.channel_config.values())),
        )

    @staticmethod
    def _get_camera_assemblies(rig: AindVrForagingRig) -> tuple[list[devices.CameraAssembly], list[devices.Camera]]:
        controller = rig.triggered_camera_controller
        fps = float(controller.frame_rate) if controller.frame_rate else float("nan")
        cameras = [_get_camera(camera_name, camera, fps) for camera_name, camera in controller.cameras.items()]
        return [_get_camera_assembly(camera) for camera in cameras], cameras

    @staticmethod
    def _get_optics() -> list[devices.LightEmittingDiode | devices.Filter | devices.Lens]:
        filters = [
            devices.Filter(
                name=str(TrackedDevices.SCREEN) + "_hot_mirror",
                manufacturer=devices.Organization.OTHER,
                model="HM-VS-1150",
                filter_type=devices.FilterType.DICHROIC,
                cut_off_wavelength=750,
                notes="Dichroic filter to reflect visible light and pass infrared light; used to combine IR illumination with visible stimulus on the same screen.",
            )
        ]

        light_sources = [
            devices.LightEmittingDiode(
                name="face_ir_led",
                model="M810L5",
                manufacturer=devices.Organization.THORLABS,
                wavelength=810,
                wavelength_unit=units.SizeUnit.NM,
            ),
            devices.LightEmittingDiode(
                name="side_ir_led",
                model="M810L5",
                manufacturer=devices.Organization.THORLABS,
                wavelength=810,
                wavelength_unit=units.SizeUnit.NM,
            ),
        ]

        lenses = [
            devices.Lens(
                name="face_ir_led_lens",
                manufacturer=devices.Organization.THORLABS,
                model="LA1255-B",
            ),
            devices.Lens(
                name="side_ir_led_lens",
                manufacturer=devices.Organization.THORLABS,
                model="LA1805-B",
            ),
        ]
        return filters + light_sources + lenses


def _get_channel_type(connection: connections.Connection) -> devices.DaqChannelType:
    source_port = connection.source_port
    if source_port is None:
        raise ValueError("Source port is not set for connection {}".format(connection))
    if any(s in source_port for s in ["DO", "DigitalOutput", "SupplyPort"]):
        return devices.DaqChannelType.DO
    if any(s in source_port for s in ["DI", "DigitalInput"]):
        return devices.DaqChannelType.DI
    if any(s in source_port for s in ["AO", "AnalogOutput"]):
        return devices.DaqChannelType.AO
    if any(s in source_port for s in ["AI", "AnalogInput"]):
        return devices.DaqChannelType.AI
    raise ValueError("Cannot determine channel type from source port {}".format(source_port))


@dataclasses.dataclass(frozen=True)
class _PartialCameraAssembly:
    name: str
    target: devices.CameraTarget
    relative_position: list[aind_schema_model_coordinates.AnatomicalRelative]
    lens: devices.Lens
    filter: devices.Filter = dataclasses.field(
        default_factory=lambda: devices.Filter(
            name="long_pass_camera_filter",
            filter_type=devices.FilterType.LONGPASS,
            cut_on_wavelength=810,
            manufacturer=devices.Organization.THORLABS,
        )
    )


_camera_assembly_lookup = {
    "FaceCamera": _PartialCameraAssembly(
        name="face_camera",
        target=devices.CameraTarget.FACE,
        relative_position=[
            aind_schema_model_coordinates.AnatomicalRelative.POSTERIOR,
            aind_schema_model_coordinates.AnatomicalRelative.LEFT,
        ],
        lens=devices.Lens(
            name="face_camera_lens",
            manufacturer=devices.Organization.TAMRON,
            model="M112FM16",
        ),
    ),
    "SideCamera": _PartialCameraAssembly(
        name="side_camera",
        target=devices.CameraTarget.BODY,
        relative_position=[aind_schema_model_coordinates.AnatomicalRelative.LATERAL],
        lens=devices.Lens(
            name="side_camera_lens", manufacturer=devices.Organization.OTHER, model="LM5JCM", notes="manufacturer=Kowa"
        ),
    ),
    "FrontCamera": _PartialCameraAssembly(
        name="front_camera",
        target=devices.CameraTarget.FACE,
        relative_position=[
            aind_schema_model_coordinates.AnatomicalRelative.POSTERIOR,
            aind_schema_model_coordinates.AnatomicalRelative.SUPERIOR,
        ],
        lens=devices.Lens(
            name="front_camera_lens", manufacturer=devices.Organization.OTHER, model="LM5JCM", notes="manufacturer=Kowa"
        ),
    ),
}


def _get_camera(name: str, camera: AbsRig.cameras.SpinnakerCamera, fps: float) -> devices.Camera:
    return devices.Camera(
        name=name,
        manufacturer=devices.Organization.FLIR,
        chroma=devices.CameraChroma.BW,
        cooling=devices.Cooling.NO_COOLING,
        data_interface=devices.DataInterface.USB,
        sensor_format="1/2.9",
        sensor_format_unit=units.SizeUnit.IN,
        sensor_width=720,
        sensor_height=540,
        model="Blackfly S BFS-U3-04S2M",
        frame_rate=Decimal(str(fps)),
        frame_rate_unit=units.FrequencyUnit.HZ,
        gain=Decimal(str(camera.gain) if camera.gain is not None else "0"),
        serial_number=camera.serial_number,
        crop_offset_x=camera.region_of_interest.x if camera.region_of_interest.x > 0 else None,
        crop_offset_y=camera.region_of_interest.y if camera.region_of_interest.y > 0 else None,
        crop_width=camera.region_of_interest.width if camera.region_of_interest.width > 0 else None,
        crop_height=camera.region_of_interest.height if camera.region_of_interest.height > 0 else None,
        crop_unit=units.SizeUnit.PX,
        additional_settings=GenericModel.model_validate(camera.model_dump()),
    )


def _get_camera_assembly(camera: devices.Camera) -> devices.CameraAssembly:
    if camera.name not in _camera_assembly_lookup:
        raise ValueError(f"Camera assembly for {camera.name} is not defined.")
    partial = _camera_assembly_lookup[camera.name]
    return devices.CameraAssembly(
        name=camera.name + "_assembly",
        target=partial.target,
        relative_position=partial.relative_position,
        camera=camera,
        lens=partial.lens,
        filter=partial.filter,
    )


def _get_olfactometer_channel(
    ch: AbsCalibration.olfactometer.OlfactometerChannelConfig,
) -> devices.OlfactometerChannel:
    ch_type_to_ch_type = {
        AbsCalibration.olfactometer.OlfactometerChannelType.CARRIER: devices.OlfactometerChannelType.CARRIER,
        AbsCalibration.olfactometer.OlfactometerChannelType.ODOR: devices.OlfactometerChannelType.ODOR,
    }
    return devices.OlfactometerChannel(
        channel_index=ch.channel_index,
        channel_type=ch_type_to_ch_type[ch.channel_type],
        flow_capacity=ch.flow_rate_capacity,
    )
