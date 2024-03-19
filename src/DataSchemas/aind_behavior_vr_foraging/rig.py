# Import core types
from __future__ import annotations

# Import core types
from typing import Literal, Optional
from pydantic import BaseModel, Field

import aind_behavior_services.rig as rig
from aind_behavior_services.rig import AindBehaviorRigModel
import aind_behavior_services.calibration.olfactometer as oc
import aind_behavior_services.calibration.water_valve as wvc

__version__ = "0.2.0"


class HarpTreadmill(rig.HarpTreadmill):
    additional_settings: rig.Treadmill = Field(default=rig.Treadmill(), description="Additional treadmill settings")


class RigCalibration(BaseModel):
    water_valve: wvc.WaterValveCalibration = Field(default=..., description="Water valve calibration")
    olfactometer: Optional[oc.OlfactometerCalibration] = Field(default=None, description="Olfactometer calibration")


class AindVrForagingRig(AindBehaviorRigModel):
    describedBy: Literal[
        "https://raw.githubusercontent.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/main/src/DataSchemas/aind_vr_foraging_rig.json"
    ] = Field(
        "https://raw.githubusercontent.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/main/src/DataSchemas/aind_vr_foraging_rig.json"
    )
    schema_version: Literal[__version__] = __version__
    auxiliary_camera0: Optional[rig.WebCamera] = Field(default=rig.WebCamera(index=0), description="Auxiliary camera 0")
    auxiliary_camera1: Optional[rig.WebCamera] = Field(default=rig.WebCamera(index=1), description="Auxiliary camera 1")
    harp_behavior: rig.HarpBehavior = Field(..., description="Harp behavior")
    harp_olfactometer: rig.HarpOlfactometer = Field(..., description="Harp olfactometer")
    harp_lickometer: rig.HarpLickometer = Field(..., description="Harp lickometer")
    harp_clock_generator: rig.HarpClockGenerator = Field(..., description="Harp clock generator")
    harp_analog_input: Optional[rig.HarpAnalogInput] = Field(default=None, description="Harp analog input")
    harp_treadmill: HarpTreadmill = Field(..., description="Treadmill settings")
    harp_sniff_detector: rig.HarpSniffDetector = Field(..., description="Sniff detector settings")
    face_camera: rig.SpinnakerCamera = Field(..., description="Face camera")
    top_body_camera: Optional[rig.SpinnakerCamera] = Field(default=None, description="Top body camera")
    side_body_camera: Optional[rig.SpinnakerCamera] = Field(default=None, description="Side body camera")
    screen: rig.Screen = Field(default=rig.Screen(), description="Screen settings")
    calibration: RigCalibration = Field(..., description="Calibration models")


def schema() -> BaseModel:
    return AindVrForagingRig
