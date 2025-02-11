# Import core types
from __future__ import annotations

# Import core types
from typing import List, Literal, Optional

import aind_behavior_services.calibration.olfactometer as oc
import aind_behavior_services.calibration.water_valve as wvc
import aind_behavior_services.rig as rig
from aind_behavior_services.calibration import aind_manipulator
from aind_behavior_services.calibration.treadmill import Treadmill
from aind_behavior_services.rig import (
    AindBehaviorRigModel,
    HarpAnalogInput,
    HarpBehavior,
    HarpWhiteRabbit,
    HarpLicketySplit,
    HarpSniffDetector,
)
from pydantic import BaseModel, Field

__version__ = "0.5.0"


class AindManipulatorAdditionalSettings(BaseModel):
    """Additional settings for the manipulator device"""

    spout_axis: aind_manipulator.Axis = Field(default=aind_manipulator.Axis.Y1, description="Spout axis")


class AindManipulatorDevice(aind_manipulator.AindManipulatorDevice):
    """Overrides the default settings for the manipulator device by spec'ing additional_settings field"""

    additional_settings: AindManipulatorAdditionalSettings = Field(
        default=AindManipulatorAdditionalSettings(), description="Additional settings"
    )


class HarpOlfactometer(rig.HarpOlfactometer):
    """Overrides the default settings for the olfactometer calibration"""

    calibration: oc.OlfactometerCalibration = Field(description="Olfactometer calibration")


class RigCalibration(BaseModel):
    """Container class for calibration models. In a future release these will be moved to the respective devices"""

    water_valve: wvc.WaterValveCalibration = Field(..., description="Water valve calibration")


class AindVrForagingRig(AindBehaviorRigModel):
    version: Literal[__version__] = __version__
    triggered_camera_controller: rig.CameraController[rig.SpinnakerCamera] = Field(
        ..., description="Required camera controller to triggered cameras."
    )
    monitoring_camera_controller: Optional[rig.CameraController[rig.WebCamera]] = Field(
        default=None, description="Optional camera controller for monitoring cameras."
    )
    harp_behavior: HarpBehavior = Field(..., description="Harp behavior")
    harp_olfactometer: HarpOlfactometer = Field(..., description="Harp olfactometer")
    harp_lickometer: HarpLicketySplit = Field(..., description="Harp lickometer")
    harp_clock_generator: HarpWhiteRabbit = Field(..., description="Harp clock generator")
    harp_analog_input: Optional[HarpAnalogInput] = Field(default=None, description="Harp analog input")
    harp_treadmill: Treadmill = Field(..., description="Harp treadmill")
    harp_sniff_detector: Optional[HarpSniffDetector] = Field(default=None, description="Sniff detector settings")
    harp_environment_sensor: Optional[rig.HarpEnvironmentSensor] = Field(default=None, description="Environment sensor")
    manipulator: AindManipulatorDevice = Field(..., description="Manipulator")
    screen: rig.Screen = Field(default=rig.Screen(), description="Screen settings")
    calibration: RigCalibration = Field(..., description="Calibration models")
