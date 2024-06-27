# Import core types
from __future__ import annotations

# Import core types
from typing import Annotated, List, Literal, Optional

import aind_behavior_services.calibration.olfactometer as oc
import aind_behavior_services.calibration.water_valve as wvc
import aind_behavior_services.rig as rig
from aind_behavior_services.rig import AindBehaviorRigModel
from pydantic import BaseModel, Field

__version__ = "0.3.0"


ValuePair = Annotated[List[float], Field(min_length=2, max_length=2, description="A tuple of two values")]


class Treadmill(rig.Treadmill):
    brake_lookup_calibration: List[ValuePair] = Field(
        default=[[0, 0], [1, 65535]],
        validate_default=True,
        min_length=2,
        description="Brake lookup calibration. Each Tuple is (0-1 (percent), 0-full-scale). \
            Values are linearly interpolated",
    )


class HarpTreadmill(rig.HarpTreadmill):
    calibration: Treadmill = Field(Treadmill(), description="Treadmill calibration settings", validate_default=True)


class RigCalibration(BaseModel):
    water_valve: wvc.WaterValveCalibration = Field(default=..., description="Water valve calibration")
    olfactometer: Optional[oc.OlfactometerCalibration] = Field(default=None, description="Olfactometer calibration")


class AindVrForagingRig(AindBehaviorRigModel):
    version: Literal[__version__] = __version__
    triggered_camera_controller: rig.CameraController[rig.SpinnakerCamera] = Field(
        ..., description="Required camera controller to triggered cameras."
    )
    monitoring_camera_controller: Optional[rig.CameraController[rig.WebCamera]] = Field(
        default=None, description="Optional camera controller for monitoring cameras."
    )
    harp_behavior: rig.HarpBehavior = Field(..., description="Harp behavior")
    harp_olfactometer: rig.HarpOlfactometer = Field(..., description="Harp olfactometer")
    harp_lickometer: rig.HarpLickometer = Field(..., description="Harp lickometer")
    harp_clock_generator: rig.HarpClockGenerator = Field(..., description="Harp clock generator")
    harp_clock_repeaters: List[rig.HarpClockGenerator] = Field(default=[], description="Harp clock repeaters")
    harp_analog_input: Optional[rig.HarpAnalogInput] = Field(default=None, description="Harp analog input")
    harp_treadmill: HarpTreadmill = Field(..., description="Harp treadmill")
    harp_sniff_detector: Optional[rig.HarpSniffDetector] = Field(None, description="Sniff detector settings")
    screen: rig.Screen = Field(default=rig.Screen(), description="Screen settings")
    calibration: RigCalibration = Field(..., description="Calibration models")
