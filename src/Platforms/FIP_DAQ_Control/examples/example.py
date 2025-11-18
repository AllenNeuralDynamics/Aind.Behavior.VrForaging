import argparse
import datetime
import os

from aind_behavior_services.rig.harp import HarpCuttlefishfip
from aind_behavior_services.session import AindBehaviorSessionModel

from aind_physiology_fip.rig import (
    AindPhysioFipRig,
    FipCamera,
    FipTask,
    LightSource,
    LightSourceCalibration,
    LightSourceCalibrationOutput,
    Networking,
    Ports,
    RoiSettings,
)


def mock_session() -> AindBehaviorSessionModel:
    """Generates a mock AindBehaviorSessionModel model"""
    return AindBehaviorSessionModel(
        date=datetime.datetime.now(tz=datetime.timezone.utc),
        experiment="AindPhysioFip",
        root_path="c://",
        subject="test",
        notes="test session",
        experiment_version="0.0.0",
        allow_dirty_repo=True,
        skip_hardware_validation=False,
        experimenter=["Foo", "Bar"],
    )


def mock_rig() -> AindPhysioFipRig:
    mock_calibration = LightSourceCalibration(
        device_name="mock_device", output=LightSourceCalibrationOutput(power_lut={0: 0, 0.1: 10, 0.2: 20})
    )

    return AindPhysioFipRig(
        rig_name="test_rig",
        computer_name="test_computer",
        camera_green_iso=FipCamera(serial_number="000000"),
        camera_red=FipCamera(serial_number="000001"),
        light_source_blue=LightSource(
            power=10,
            calibration=mock_calibration,
            task=FipTask(
                camera_port=Ports.IO0,  # GreenCamera + 470nm
                light_source_port=Ports.IO2,
            ),
        ),
        light_source_lime=LightSource(
            power=20,
            calibration=mock_calibration,
            task=FipTask(
                camera_port=Ports.IO1,  # RedCamera + 560nm
                light_source_port=Ports.IO4,
            ),
        ),
        light_source_uv=LightSource(
            power=0.1,
            calibration=None,
            task=FipTask(
                camera_port=Ports.IO0,  # GreenCamera + 410nm
                light_source_port=Ports.IO3,
            ),
        ),
        roi_settings=RoiSettings(),
        networking=Networking(),
        cuttlefish_fip=HarpCuttlefishfip(
            port_name="COM1",
        ),
    )


def main():
    parser = argparse.ArgumentParser(description="Generate mock session and rig JSON files")
    parser.add_argument(
        "--path-seed",
        default="./local/{schema}.json",
        help="Path template for output files (default: ./local/{schema}.json)",
    )
    args = parser.parse_args()

    example_session = mock_session()
    example_rig = mock_rig()

    os.makedirs(os.path.dirname(args.path_seed), exist_ok=True)

    for model in [example_session, example_rig]:
        with open(args.path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
