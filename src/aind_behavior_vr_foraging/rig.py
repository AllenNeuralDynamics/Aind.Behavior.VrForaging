# Import core types
from __future__ import annotations

# Import core types
from typing import Literal, Optional

import aind_behavior_services.calibration.aind_manipulator as man
import aind_behavior_services.calibration.olfactometer as oc
import aind_behavior_services.calibration.treadmill as treadmill
import aind_behavior_services.calibration.water_valve as wvc
import aind_behavior_services.rig as rig
from pydantic import BaseModel, Field

from aind_behavior_vr_foraging import __version__


class AindManipulatorAdditionalSettings(BaseModel):
    """Additional settings for the manipulator device"""

    spout_axis: man.Axis = Field(default=man.Axis.Y1, description="Spout axis")


class AindManipulatorDevice(man.AindManipulatorDevice):
    """Overrides the default settings for the manipulator device by spec'ing additional_settings field"""

    additional_settings: AindManipulatorAdditionalSettings = Field(
        default=AindManipulatorAdditionalSettings(), description="Additional settings"
    )


class RigCalibration(BaseModel):
    """Container class for calibration models. In a future release these will be moved to the respective devices"""

    water_valve: wvc.WaterValveCalibration = Field(..., description="Water valve calibration")


class AindVrForagingRig(rig.AindBehaviorRigModel):
    version: Literal[__version__] = __version__
    triggered_camera_controller: rig.cameras.CameraController[rig.cameras.SpinnakerCamera] = Field(
        ..., description="Required camera controller to triggered cameras."
    )
    monitoring_camera_controller: Optional[rig.cameras.CameraController[rig.cameras.WebCamera]] = Field(
        default=None, description="Optional camera controller for monitoring cameras."
    )
    harp_behavior: rig.harp.HarpBehavior = Field(..., description="Harp behavior")
    harp_olfactometer: oc.Olfactometer = Field(..., description="Harp olfactometer")
    harp_lickometer: rig.harp.HarpLicketySplit = Field(..., description="Harp lickometer")
    harp_clock_generator: rig.harp.HarpWhiteRabbit = Field(..., description="Harp clock generator")
    harp_analog_input: Optional[rig.harp.HarpAnalogInput] = Field(default=None, description="Harp analog input")
    harp_treadmill: treadmill.Treadmill = Field(..., description="Harp treadmill")
    harp_sniff_detector: Optional[rig.harp.HarpSniffDetector] = Field(
        default=None, description="Sniff detector settings"
    )
    harp_environment_sensor: Optional[rig.harp.HarpEnvironmentSensor] = Field(
        default=None, description="Environment sensor"
    )
    manipulator: AindManipulatorDevice = Field(..., description="Manipulator")
    screen: rig.visual_stimulation.Screen = Field(
        default=rig.visual_stimulation.Screen(), description="Screen settings"
    )
    calibration: RigCalibration = Field(..., description="Calibration models")
