# Import core types
from __future__ import annotations

# Import core types
from typing import Literal, Optional

import aind_behavior_services.rig as rig
from aind_behavior_services.rig import AindBehaviorRigModel
from pydantic import BaseModel, Field

__version__ = "0.1.1"


class AindVrForagingRig(AindBehaviorRigModel):
    describedBy: Literal[
        "https://raw.githubusercontent.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/main/src/DataSchemas/aind_vr_foraging_rig.json"
    ] = Field(
        "https://raw.githubusercontent.com/AllenNeuralDynamics/Aind.Behavior.VrForaging/main/src/DataSchemas/aind_vr_foraging_rig.json"
    )
    schema_version: Literal[__version__] = __version__
    auxiliary_camera0: Optional[rig.WebCamera] = Field(default=rig.WebCamera(), description="Auxiliary camera 0")
    auxiliary_camera1: Optional[rig.WebCamera] = Field(default=rig.WebCamera(), description="Auxiliary camera 1")
    harp_behavior: rig.HarpBehavior = Field(..., description="Harp behavior")
    harp_olfactometer: rig.HarpOlfactometer = Field(..., description="Harp olfactometer")
    harp_lickometer: rig.HarpLickometer = Field(..., description="Harp lickometer")
    harp_clock_generator: rig.HarpClockGenerator = Field(..., description="Harp clock generator")
    harp_analog_input: Optional[rig.HarpAnalogInput] = Field(default=None, description="Harp analog input")
    face_camera: rig.SpinnakerCamera = Field(..., description="Face camera")
    top_body_camera: Optional[rig.SpinnakerCamera] = Field(default=None, description="Top body camera")
    side_body_camera: Optional[rig.SpinnakerCamera] = Field(default=None, description="Side body camera")
    screen: rig.Screen = Field(default=rig.Screen(), description="Screen settings")
    treadmill: rig.Treadmill = Field(default=rig.Treadmill(), description="Treadmill settings")
    water_valve: rig.Valve = Field(default=rig.Valve(), description="Water valve settings")


def schema() -> BaseModel:
    return AindVrForagingRig
