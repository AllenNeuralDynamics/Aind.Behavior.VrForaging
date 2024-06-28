# Import core types
from __future__ import annotations

# Import core types
from typing import Annotated, List, Literal, Optional

import aind_behavior_services.calibration.olfactometer as oc
import aind_behavior_services.calibration.water_valve as wvc
from aind_behavior_services.calibration import aind_manipulator
import aind_behavior_services.rig as rig
from aind_behavior_services.rig import HarpBehavior, HarpAnalogInput, HarpClockGenerator, HarpLickometer, HarpSniffDetector, Screen
from aind_behavior_services.rig import AindBehaviorRigModel
from pydantic import BaseModel, Field

__version__ = "0.3.0"


ValuePair = Annotated[List[float], Field(min_length=2, max_length=2, description="A tuple of two values")]


class Treadmill(rig.Treadmill):
    '''Overrides the default settings for the treadmill calibration by spec'ing brake_lookup_calibration field'''
    brake_lookup_calibration: List[ValuePair] = Field(
        default=[[0, 0], [1, 65535]],
        validate_default=True,
        min_length=2,
        description="Brake lookup calibration. Each Tuple is (0-1 (percent), 0-full-scale). \
            Values are linearly interpolated",
    )


class AindManipulatorAdditionalSettings(BaseModel):
    '''Additional settings for the manipulator device'''
    spout_axis: aind_manipulator.Axis = Field(default=aind_manipulator.Axis.Y1, description="Spout axis")


class AindManipulatorDevice(aind_manipulator.AindManipulatorDevice):
    '''Overrides the default settings for the manipulator device by spec'ing additional_settings field'''
    additional_settings: AindManipulatorAdditionalSettings = Field(default=AindManipulatorAdditionalSettings(), description="Additional settings")


class HarpTreadmill(rig.HarpTreadmill):
    '''Overrides the default settings for the treadmill calibration'''
    calibration: Treadmill = Field(Treadmill(), description="Treadmill calibration settings", validate_default=True)


class HarpOlfactometer(rig.HarpOlfactometer):
    '''Overrides the default settings for the olfactometer calibration'''
    calibration: Optional[oc.OlfactometerCalibration] = Field(default=None, description="Olfactometer calibration")


class RigCalibration(BaseModel):
    '''Container class for calibration models. In a future release these will be moved to the respective devices'''
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
    harp_lickometer: HarpLickometer = Field(..., description="Harp lickometer")
    harp_clock_generator: HarpClockGenerator = Field(..., description="Harp clock generator")
    harp_clock_repeaters: List[HarpClockGenerator] = Field(default=[], description="Harp clock repeaters")
    harp_analog_input: Optional[HarpAnalogInput] = Field(default=None, description="Harp analog input")
    harp_treadmill: HarpTreadmill = Field(..., description="Harp treadmill")
    harp_sniff_detector: Optional[HarpSniffDetector] = Field(None, description="Sniff detector settings")
    manipulator: AindManipulatorDevice = Field(..., description="Manipulator")
    screen: rig.Screen = Field(default=Screen(), description="Screen settings")
    calibration: RigCalibration = Field(..., description="Calibration models")
