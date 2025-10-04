import datetime
import os

import aind_behavior_services.rig as rig
from aind_behavior_services.calibration.aind_manipulator import (
    AindManipulatorCalibration,
    AindManipulatorCalibrationInput,
    AindManipulatorCalibrationOutput,
    Axis,
    AxisConfiguration,
    ManipulatorPosition,
)
from aind_behavior_services.calibration.olfactometer import (
    Olfactometer,
    OlfactometerCalibration,
    OlfactometerCalibrationInput,
    OlfactometerCalibrationOutput,
    OlfactometerChannel,
    OlfactometerChannelConfig,
    OlfactometerChannelType,
)
from aind_behavior_services.calibration.treadmill import (
    Treadmill,
    TreadmillCalibration,
    TreadmillCalibrationInput,
    TreadmillCalibrationOutput,
)
from aind_behavior_services.calibration.water_valve import (
    Measurement,
    WaterValveCalibration,
    WaterValveCalibrationInput,
)
from aind_behavior_services.rig.harp import (
    HarpBehavior,
    HarpLicketySplit,
    HarpSniffDetector,
    HarpWhiteRabbit,
)

from aind_behavior_vr_foraging.rig import (
    AindManipulatorDevice,
    AindVrForagingRig,
    RigCalibration,
)

manipulator_calibration = AindManipulatorCalibration(
    output=AindManipulatorCalibrationOutput(),
    input=AindManipulatorCalibrationInput(
        full_step_to_mm=(ManipulatorPosition(x=0.010, y1=0.010, y2=0.010, z=0.010)),
        axis_configuration=[
            AxisConfiguration(axis=Axis.Y1, min_limit=-0.01, max_limit=25),
            AxisConfiguration(axis=Axis.Y2, min_limit=-0.01, max_limit=25),
            AxisConfiguration(axis=Axis.X, min_limit=-0.01, max_limit=25),
            AxisConfiguration(axis=Axis.Z, min_limit=-0.01, max_limit=25),
        ],
        homing_order=[Axis.Y1, Axis.Y2, Axis.X, Axis.Z],
        initial_position=ManipulatorPosition(y1=0, y2=0, x=0, z=0),
    ),
)

olfactometer_calibration = OlfactometerCalibration(
    output=OlfactometerCalibrationOutput(),
    date=datetime.datetime.now(),
    input=OlfactometerCalibrationInput(
        channel_config={
            OlfactometerChannel.Channel0: OlfactometerChannelConfig(
                channel_index=OlfactometerChannel.Channel0,
                channel_type=OlfactometerChannelType.ODOR,
                flow_rate_capacity=100,
                flow_rate=100,
                odorant="Amyl Acetate",
                odorant_dilution=1.5,
            ),
            OlfactometerChannel.Channel1: OlfactometerChannelConfig(
                channel_index=OlfactometerChannel.Channel1,
                channel_type=OlfactometerChannelType.ODOR,
                flow_rate_capacity=100,
                flow_rate=100,
                odorant="Banana",
                odorant_dilution=1.5,
            ),
            OlfactometerChannel.Channel2: OlfactometerChannelConfig(
                channel_index=OlfactometerChannel.Channel2,
                channel_type=OlfactometerChannelType.ODOR,
                flow_rate_capacity=100,
                flow_rate=100,
                odorant="Apple",
                odorant_dilution=1.5,
            ),
            OlfactometerChannel.Channel3: OlfactometerChannelConfig(
                channel_index=OlfactometerChannel.Channel3,
                channel_type=OlfactometerChannelType.CARRIER,
                flow_rate_capacity=1000,
            ),
        }
    ),
)

water_valve_input = WaterValveCalibrationInput(
    measurements=[
        Measurement(valve_open_interval=0.2, valve_open_time=0.01, water_weight=[0.6, 0.6], repeat_count=200),
        Measurement(valve_open_interval=0.2, valve_open_time=0.02, water_weight=[1.2, 1.2], repeat_count=200),
    ]
)
water_valve_calibration = WaterValveCalibration(
    input=water_valve_input, output=water_valve_input.calibrate_output(), date=datetime.datetime.now()
)

video_writer = rig.cameras.VideoWriterFfmpeg(frame_rate=120, container_extension="mp4")

rig = AindVrForagingRig(
    rig_name="test_rig",
    triggered_camera_controller=rig.cameras.CameraController[rig.cameras.SpinnakerCamera](
        frame_rate=120,
        cameras={
            "FaceCamera": rig.cameras.SpinnakerCamera(
                serial_number="SerialNumber", binning=1, exposure=5000, gain=0, video_writer=video_writer
            ),
            "SideCamera": rig.cameras.SpinnakerCamera(
                serial_number="SerialNumber", binning=1, exposure=5000, gain=0, video_writer=video_writer
            ),
        },
    ),
    monitoring_camera_controller=rig.cameras.CameraController[rig.cameras.WebCamera](
        cameras={"WebCam0": rig.cameras.WebCamera(index=0)}
    ),
    harp_behavior=HarpBehavior(port_name="COM3"),
    harp_olfactometer=Olfactometer(port_name="COM4", calibration=olfactometer_calibration),
    harp_lickometer=HarpLicketySplit(port_name="COM5"),
    harp_clock_generator=HarpWhiteRabbit(port_name="COM6"),
    harp_analog_input=None,
    harp_sniff_detector=HarpSniffDetector(port_name="COM7"),
    harp_treadmill=Treadmill(
        port_name="COM8",
        calibration=TreadmillCalibration(
            input=TreadmillCalibrationInput(),
            output=TreadmillCalibrationOutput(
                wheel_diameter=15, pulses_per_revolution=28800, brake_lookup_calibration=[[0, 0], [1, 65535]]
            ),
        ),
    ),
    manipulator=AindManipulatorDevice(port_name="COM9", calibration=manipulator_calibration),
    screen=rig.visual_stimulation.Screen(display_index=1),
    calibration=RigCalibration(water_valve=water_valve_calibration),
)


def main(path_seed: str = "./local/{schema}.json"):
    os.makedirs(os.path.dirname(path_seed), exist_ok=True)
    models = [rig]

    for model in models:
        with open(path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
