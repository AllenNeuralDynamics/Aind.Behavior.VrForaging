import json
import os
from datetime import date, datetime

from aind_behavior_vr_foraging.rig import AindVrForagingRig

from datetime import date, datetime, timezone

from aind_data_schema_models.modalities import Modality
from aind_data_schema_models.units import FrequencyUnit, SizeUnit, PowerUnit, VolumeUnit, TimeUnit
from aind_data_schema.components.measurements import Calibration
from aind_data_schema.components.devices import (
    CameraAssembly,
    Camera,
    Computer,
    Organization,
    Lens,
    HarpDevice,
    HarpDeviceType,
    DAQChannel,
    DaqChannelType,
    DataInterface,
    Olfactometer,
    OlfactometerChannel,
    OlfactometerChannelType,
    LickSpoutAssembly,
    LickSpout,
    Device,
    LickSensorType,
    MotorizedStage,
    LightEmittingDiode,
    Filter,
    Speaker,
    Monitor,
    Wheel,
    Enclosure
)

from aind_data_schema.components.connections import Connection
from aind_data_schema.core.instrument import Instrument
from aind_data_schema.components.identifiers import Software
from aind_data_schema.components.coordinates import (
    CoordinateSystemLibrary,
    Scale,
)

from aind_data_schema_models.coordinates import AnatomicalRelative
from aind_data_schema_models.devices import CameraTarget


class AindRigSchemaMapper:
    def __init__(self, model: AindVrForagingRig, output_directory: str) -> None:
        self.rig = model
        self.output_directory = output_directory

    def load(self):
        behavior_computer = self.rig.computer_name
        rig_name = self.rig.rig_name

        computer = Computer(
            name=behavior_computer,
            manufacturer=Organization.from_name("AIND"),
            operating_system="Windows 11"
        )

        enclosure = Enclosure(
            name="Behavior enclosure",
            size=Scale(scale = [568, 540, 506]),
            size_unit=SizeUnit.MM,
            manufacturer=Organization.AIND,
            internal_material="High density foam",
            external_material="Wood and aluminium frame",
            grounded=True,
            air_filtration=False,
            laser_interlock=False
        )

        components = {}

        water_calibration_date = self.rig.calibration.water_valve.date

        measurements = [(m.valve_open_time, m.water_weight[0]) for m in self.rig.calibration.water_valve.input.measurements]
        # then unpack if needed
        times, volumes = zip(*measurements)
        repeats = self.rig.calibration.water_valve.input.measurements[0].repeat_count

        calibrations = [
            Calibration(
                    calibration_date=water_calibration_date,
                    device_name='Solenoid',
                    description="Water calibration for Lick spout. The input is the valve open time in seconds and the output is the volume of water delivered in microliters.",
                    input=times,
                    input_unit=TimeUnit.S,
                    output=volumes,
                    output_unit=VolumeUnit.ML,
                    repeats=repeats
            )
        ]
        
        ## Connections

        # 1. Connections from Behavior to multiple devices with specific ports
        behavior_connections = [
            Connection(source_device="Behavior", source_port=port, target_device=target)
            for port, target in [
                ("DO0", "SideCamera"),
                ("DO0", "FrontCamera"),
                ("DO0", "FaceCamera"),
                ("PwmDO2", "Speaker"),
                ("DIPort0", "Photodiode")
            ]
        ]

        treadmill_connections = [
            Connection(source_device="Treadmill", target_device="Magnetic brake", send_and_receive=True),
            Connection(source_device="Treadmill",  target_device="Torque sensor", send_and_receive=True),
            Connection(source_device="Treadmill", target_device="Encoder", send_and_receive=True),
        ]

        # 2. Other devices connecting to behavior_computer
        other_devices = ["Olfactometer", "LicketySplit", "FrontCamera", "SideCamera", "FaceCamera", "Treadmill", "SniffSensor", "StepperDriver", "WhiteRabbit"]

        other_connections = [
            Connection(source_device=device, target_device=behavior_computer, send_and_receive=True)
            for device in other_devices
        ]

        clock_connections = [
            Connection(source_device='WhiteRabbit', target_device=device)
            for device in other_devices[:-1]
        ]

        # Combine all connections
        connections = behavior_connections + other_connections + treadmill_connections + clock_connections

        # Devices and channels

        channels_for_behavior=[
            DAQChannel(channel_name="DO0", channel_type=DaqChannelType.DO),
            DAQChannel(channel_name="DO0", channel_type=DaqChannelType.DO),
            DAQChannel(channel_name="DO0", channel_type=DaqChannelType.DO),
            DAQChannel(channel_name="DIPort0", channel_type=DaqChannelType.DI),
            DAQChannel(channel_name="PwmDO2", channel_type=DaqChannelType.DO)
        ]


        channels=[
            DAQChannel(channel_name="Magnetic brake", channel_type=DaqChannelType.AO),
            DAQChannel(channel_name="Torque sensor", channel_type=DaqChannelType.AI),
            DAQChannel(channel_name="Encoder", channel_type=DaqChannelType.AI)
        ]

        # -------------------------------  Mouse platform
        torque_sensor_channel = DAQChannel(
            channel_name="Torque sensor",
            channel_type="Analog Output",
        )
        encoder_channel = DAQChannel(
            channel_name="Encoder",
            channel_type="Analog Output",
        )
        magnetic_brake_channel = DAQChannel(
            channel_name="Magnetic brake",
            channel_type="Analog Output",
        )

        magnetic_brake = Device(
            name="Magnetic brake",
            manufacturer=Organization.from_name("Placid"),
            model="B1-2FM",
        )

        encoder = Device(
            name="Encoder",
            manufacturer=Organization.from_name("CUI"),
            model="AMT102-V",
        )

        torque_sensor = Device(
            name="Torque sensor",
            manufacturer=Organization.from_name("Transducer Techniques"),
            model="RTS-10",
        )

        photo_diode = Device(
            name="Photodiode",
            manufacturer=Organization.from_name("AIND"),
            model="",
        )

        harpTreadmill = HarpDevice(
            name="Treadmill",
            harp_device_type=HarpDeviceType.TREADMILL,
            manufacturer=Organization.AIND,
            is_clock_generator=False,
            channels=[torque_sensor_channel, encoder_channel, magnetic_brake_channel],
            notes="https://github.com/AllenNeuralDynamics/harp.device.treadmill-driver"
        )

        harpBehavior = HarpDevice(
            name="Behavior",
            harp_device_type=HarpDeviceType.BEHAVIOR,
            manufacturer=Organization.AIND,
            channels=channels_for_behavior,
            is_clock_generator=False,
        )

        harpLicksensor = HarpDevice(
            name="LicketelySplit",
            harp_device_type=HarpDeviceType.LICKETYSPLIT,
            manufacturer=Organization.AIND,
            is_clock_generator=False,
            notes="Lick sensor with low noise artifacts; https://github.com/AllenNeuralDynamics/harp.device.lickety-split",
        )

        harpOlfactometer = HarpDevice(
            name="Olfactometer",
            harp_device_type=HarpDeviceType.OLFACTOMETER,
            manufacturer=Organization.AIND,
            is_clock_generator=False,
        )

        # -------------- Harp devices
        harpWhiteRabbit = HarpDevice(
            name="WhiteRabbit",
            harp_device_type=HarpDeviceType.WHITERABBIT,
            manufacturer=Organization.AIND,
            is_clock_generator=True,
            notes="White Rabbit clock for synchronization: https://github.com/AllenNeuralDynamics/harp.device.white-rabbit",
        )

        # -------------- Harp devices
        harpSniffSensor = HarpDevice(
            name="SniffSensor",
            harp_device_type=HarpDeviceType.SNIFFDETECTOR,
            manufacturer=Organization.AIND,
            is_clock_generator=True,
        )

        harpStepperDriver = HarpDevice(
            name="Stepper driver",
            harp_device_type=HarpDeviceType.STEPPERDRIVER,
            manufacturer=Organization.AIND,
            is_clock_generator=False,
            notes="Stepper driver for positioning the lick spout and the odor tubes; https://allenneuraldynamics.github.io/Bonsai.AllenNeuralDynamics/articles/aind-manipulator.html",
        )

        wheel = Wheel(
            name="VR Wheel",
            manufacturer=Organization.AIND,
            radius=self.rig.harp_treadmill.calibration.output.wheel_diameter / 2,
            width=3.5,
            size_unit=SizeUnit.CM,
            encoder=encoder,
            pulse_per_revolution=self.rig.harp_treadmill.calibration.output.pulses_per_revolution,
            magnetic_brake=magnetic_brake,
            torque_sensor=torque_sensor,
            notes="VR Wheel for mouse platform: https://tinyurl.com/AI-RunningWheel"
        )


        harpdevices = [
            harpTreadmill,
            harpBehavior,
            harpLicksensor,
            harpOlfactometer,
            harpWhiteRabbit,
            harpSniffSensor,
            harpStepperDriver
        ]

        wheel_assembly = [
            wheel,
            torque_sensor,
            magnetic_brake,
            encoder
        ]

        # Olfactometer config

        # Olfactometer stimulus
        channel0 = OlfactometerChannel(
            channel_index=0,
            channel_type=OlfactometerChannelType.ODOR,
            flow_capacity=100,
        )

        channel1 = OlfactometerChannel(
            channel_index=1,
            channel_type=OlfactometerChannelType.ODOR,
            flow_capacity=100,
        )

        channel2 = OlfactometerChannel(
            channel_index=2,
            channel_type=OlfactometerChannelType.ODOR,
            flow_capacity=100,
        )

        channel3 = OlfactometerChannel(
            channel_index=3,
            channel_type=OlfactometerChannelType.CARRIER,
            flow_capacity=1000,
        )

        carrier = OlfactometerChannel(
            channel_index=4,
            channel_type=OlfactometerChannelType.CARRIER,
            flow_capacity=1000,
        )

        olfactometer = Olfactometer(
            name="Olfactometer",
            harp_device_type=HarpDeviceType.OLFACTOMETER,
            manufacturer=Organization.CHAMPALIMAUD,
            is_clock_generator=False,
            channels=[channel0, channel1, channel2, channel3, carrier],
        )


        # Lickspot assembly
        stage = MotorizedStage(
            name="Motorized stage",
            manufacturer=Organization.AIND,
            model="328-300-00",
            travel=30,
            notes="Motorized stage for positioning",
        )

        lick_spout_assembly = LickSpoutAssembly(
            name='LickSpout',
            lick_spouts=[
                LickSpout(
                    name="Lick spout",
                    manufacturer=Organization.OTHER,
                    model="89875K27",
                    spout_diameter=1.2,
                    spout_diameter_unit=SizeUnit.MM,
                    solenoid_valve=Device(
                        name="Solenoid",
                        manufacturer=Organization.from_name("The Lee Company"),
                        model="LHDB1233518H",
                    ),
                    lick_sensor_type=LickSensorType("Capacitive"),
                    lick_sensor=harpLicksensor,
                    notes="Lick spout for water delivery, the tube is ordered from McMaster, cut to size and shaped by AIND",
                )
            ],
            motorized_stage=stage
        )

        # REst of stimulus

        speaker = Speaker(
            name="Speaker",
            relative_position=[AnatomicalRelative.SUPERIOR],
            manufacturer=Organization.TYMPHANY,
            model="XT25SC90-04"
        )

        monitor_left = Monitor(
            name="Screen Left",
            manufacturer=Organization.LG,
            relative_position=[AnatomicalRelative.ANTERIOR, AnatomicalRelative.LEFT],
            model="LG LP097QX1",
            refresh_rate=self.rig.screen.target_render_frequency,
            width=2048,
            height=1536,
            viewing_distance=15.5,
            viewing_distance_unit=SizeUnit.CM
        )
        monitor_center = Monitor(
            name="Screen Center",
            manufacturer=Organization.LG,
            relative_position=[AnatomicalRelative.ANTERIOR, AnatomicalRelative.MEDIAL],
            model="LG LP097QX1",
            refresh_rate=self.rig.screen.target_render_frequency,
            width=2048,
            height=1536,
            viewing_distance=17.5,
            viewing_distance_unit=SizeUnit.CM
        )
        monitor_right = Monitor(
            name="Screen Right",
            manufacturer=Organization.LG,
            relative_position=[AnatomicalRelative.ANTERIOR, AnatomicalRelative.RIGHT],
            model="LG LP097QX1",
            refresh_rate=self.rig.screen.target_render_frequency,
            width=2048,
            height=1536,
            viewing_distance=17.5,
            viewing_distance_unit=SizeUnit.CM
        )

        monitors = [
            monitor_left,
            monitor_center,
            monitor_right
        ]

        # Camera and light related devices
        filt = Filter(
            name="LP filter",
            filter_type="Long pass",
            cut_on_wavelength=810,
            manufacturer=Organization.THORLABS,
            notes="810 nm longpass filter",
        )

        cameras = [
            CameraAssembly(
                name="FaceCamera",
                target=CameraTarget.FACE,
                relative_position=[AnatomicalRelative.POSTERIOR, AnatomicalRelative.LEFT],
                lens=Lens(
                    name="Behavior Video Lens Face View",
                    manufacturer=Organization.TAMRON,
                    model="M112FM16",
                ),
                camera=Camera(
                    name="FaceCamera",
                    detector_type="Camera",
                    manufacturer=Organization.FLIR,
                    chroma="Monochrome",
                    cooling="Air",
                    sensor_format="1/2.9",
                    sensor_format_unit=SizeUnit.IN,
                    sensor_width=720,
                    sensor_height=540,
                    data_interface=DataInterface.USB,
                    model="Blackfly S BFS-U3-04S2M",
                    frame_rate=self.rig.triggered_camera_controller.frame_rate,
                    frame_rate_unit=FrequencyUnit.HZ,
                    # exposure_time=rig_bonsai.triggered_camera_controller.cameras['FaceCamera'].exposure,
                    gain=self.rig.triggered_camera_controller.cameras["FaceCamera"].gain,
                    serial_number=self.rig.triggered_camera_controller.cameras["FaceCamera"].serial_number,
                ),
                filter=filt,
            ),
            CameraAssembly(
                name="SideCamera",
                target=CameraTarget.BODY,
                relative_position=[AnatomicalRelative.LATERAL],
                lens=Lens(
                    name="Behavior Video Lens Side View",
                    manufacturer=Organization.OTHER,
                    model="LM5JCM",
                    notes="Manufacturer is KOWA",
                ),
                camera=Camera(
                    name="SideCamera",
                    detector_type="Camera",
                    manufacturer=Organization.FLIR,
                    chroma="Monochrome",
                    cooling="Air",
                    data_interface=DataInterface.USB,
                    sensor_format="1/2.9",
                    sensor_format_unit=SizeUnit.IN,
                    sensor_width=720,
                    sensor_height=540,
                    model="Blackfly S BFS-U3-04S2M",
                    frame_rate=self.rig.triggered_camera_controller.frame_rate,
                    frame_rate_unit=FrequencyUnit.HZ,
                    # exposure_time=rig_bonsai.triggered_camera_controller.cameras['SideCamera'].exposure,
                    gain=self.rig.triggered_camera_controller.cameras["SideCamera"].gain,
                    serial_number=self.rig.triggered_camera_controller.cameras["SideCamera"].serial_number,
                ),
                filter=filt,
            ),
            CameraAssembly(
                name="FrontCamera",
                target=CameraTarget.FACE,
                relative_position=[AnatomicalRelative.POSTERIOR, AnatomicalRelative.SUPERIOR],
                lens=Lens(
                    name="Behavior Video Lens Front View",
                    manufacturer=Organization.OTHER,
                    model="LM25HC",
                    notes="Manufacturer is KOWA",
                ),
                camera=Camera(
                    name="FrontCamera",
                    detector_type="Camera",
                    manufacturer=Organization.FLIR,
                    chroma="Monochrome",
                    cooling="Air",
                    data_interface=DataInterface.USB,
                    sensor_format="1/2.9",
                    sensor_format_unit=SizeUnit.IN,
                    sensor_width=720,
                    sensor_height=540,
                    model="Blackfly S BFS-U3-04S2M",
                    frame_rate=self.rig.triggered_camera_controller.frame_rate,
                    frame_rate_unit=FrequencyUnit.HZ,
                    # exposure_time=rig_bonsai.triggered_camera_controller.cameras['FrontCamera'].exposure,
                    gain=self.rig.triggered_camera_controller.cameras["FrontCamera"].gain,
                    serial_number=self.rig.triggered_camera_controller.cameras["FrontCamera"].serial_number,
                ),
                filter=filt,
            ),
            CameraAssembly(
                name="USB_top_view",
                target="Body",
                relative_position=[AnatomicalRelative.SUPERIOR],
                camera=Camera(
                    name="Bottom face Camera",
                    detector_type="Camera",
                    manufacturer=Organization.AILIPU,
                    model="ELP-USBFHD05MT-KL170IR",
                    notes="The target is top of the body",
                    data_interface=DataInterface.USB,
                    frame_rate=self.rig.monitoring_camera_controller.frame_rate,
                    frame_rate_unit=FrequencyUnit.HZ,
                    sensor_width=640,
                    sensor_height=480,
                    chroma="Color",
                    cooling="Air",
                    bin_mode="Additive",
                    recording_software=Software(name="Bonsai", version="2.5"),
                ),
                lens=Lens(
                    name="Xenocam 2",
                    model="XC0922LENS",
                    serial_number="unknown",
                    manufacturer=Organization.OTHER,
                    notes='Focal Length 9-22mm 1/3" IR F1.4',
                ),
            ),
        ]

        filters = Filter(
            name="Hot Mirror Filter",
            manufacturer=Organization.OTHER,
            model="HM-VS-1150",
            filter_type="Dichroic",
            cut_off_wavelength=750,
            notes='Dichroic filter to reflect visible light and pass infrared light; used to combine IR illumination with visible stimulus on the same screen')


        light_sources = [
            LightEmittingDiode(
                name="IR LED - Face",
                model="M810L5",
                manufacturer=Organization.THORLABS,
                wavelength=810,
                wavelength_unit=SizeUnit.NM,
            ),
            LightEmittingDiode(
                name="IR LED - Side",
                model="M810L5",
                manufacturer=Organization.THORLABS,
                wavelength=810,
                wavelength_unit=SizeUnit.NM,
            )
        ]


        lenses = [
            Lens(
                name="IR LED - Face lens",
                manufacturer=Organization.THORLABS,
                model="LA1255-B",
            ),
            Lens(
                name="IR LED - Side lens",
                manufacturer=Organization.THORLABS,
                model="LA1805-B",
            )
        ]

        # Assemble rig schema
        modification_date = date.today().strftime("%Y%m%d")
        rig_id = f"{rig_name}"

        modalities = [Modality.BEHAVIOR, Modality.BEHAVIOR_VIDEOS]

        instrument = Instrument(
            instrument_id=rig_id,
            modification_date=date.today(),
            modalities=modalities,
            components=[
                enclosure,
                computer,
                lick_spout_assembly,
                *monitors,
                *harpdevices,
                *wheel_assembly,
                photo_diode,
                speaker,
                olfactometer,
                *lenses,
                filters,
                *cameras,
                *light_sources
            ],
            coordinate_system=CoordinateSystemLibrary.BREGMA_ARI, # this is going to change possibly
            connections=connections,
            calibrations=calibrations
        )
        
        self.instrument = instrument
        
    def dump(self):
        serialized = self.instrument.model_dump_json()
        deserialized = Instrument.model_validate_json(serialized)
        deserialized.write_standard_file(output_directory=self.output_directory)
        