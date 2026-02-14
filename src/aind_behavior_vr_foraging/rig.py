from typing import Literal, Optional

import aind_behavior_services.rig as rig
import aind_behavior_services.rig.cameras as cameras
import aind_behavior_services.rig.harp as harp
import aind_behavior_services.rig.olfactometer as oc
import aind_behavior_services.rig.treadmill as treadmill
import aind_behavior_services.rig.visual_stimulation as visual_stimulation
import aind_behavior_services.rig.water_valve as wvc
from aind_behavior_services.rig import aind_manipulator as man
from pydantic import BaseModel, Field

from aind_behavior_vr_foraging import __semver__


class AindManipulatorDevice(man.AindManipulator):
    """Appends a task specific configuration to the base manipulator model."""

    spout_axis: man.Axis = Field(default=man.Axis.Y1, description="Spout axis")


class RigCalibration(BaseModel):
    """Container class for calibration models."""

    water_valve: wvc.WaterValveCalibration = Field(description="Water valve calibration")


class AindVrForagingRig(rig.Rig):
    version: Literal[__semver__] = __semver__
    triggered_camera_controller: cameras.CameraController[cameras.SpinnakerCamera] = Field(
        description="Required camera controller to triggered cameras."
    )
    monitoring_camera_controller: Optional[cameras.CameraController[cameras.WebCamera]] = Field(
        default=None, description="Optional camera controller for monitoring cameras."
    )
    harp_behavior: harp.HarpBehavior = Field(description="Harp behavior")
    harp_olfactometer: oc.Olfactometer = Field(description="Harp olfactometer")
    harp_lickometer: harp.HarpLicketySplit = Field(description="Harp lickometer")
    harp_clock_generator: harp.HarpWhiteRabbit = Field(description="Harp clock generator")
    harp_analog_input: Optional[harp.HarpAnalogInput] = Field(default=None, description="Harp analog input")
    harp_treadmill: treadmill.Treadmill = Field(description="Harp treadmill")
    harp_sniff_detector: Optional[harp.HarpSniffDetector] = Field(default=None, description="Sniff detector settings")
    harp_environment_sensor: Optional[harp.HarpEnvironmentSensor] = Field(
        default=None, description="Environment sensor"
    )
    manipulator: AindManipulatorDevice = Field(description="Manipulator")
    screen: visual_stimulation.ScreenAssembly = Field(
        default=visual_stimulation.ScreenAssembly(), description="Screen settings", validate_default=True
    )
    calibration: RigCalibration = Field(description="Calibration models")
