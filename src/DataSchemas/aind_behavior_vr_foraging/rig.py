# Import core types
from __future__ import annotations

from enum import Enum

# Import core types
from typing import Annotated, Literal, Optional, Union, Dict, Any

from aind_data_schema.base import AindCoreModel, AindModel
from pydantic import Field, BaseModel


class SpinnakerCamera(AindModel):
    serial_number: str = Field(..., description="Camera serial number")
    binning: int = Field(1, ge=1, description="Binning")
    color_processing: Literal["Default", "NoColorProcessing"] = Field("Default", description="Color processing")
    exposure: int = Field(1000, ge=100, description="Exposure time", units="us")
    frame_rate: int = Field(30, ge=1, le=350, description="Frame rate", units="Hz")
    gain: float = Field(0, ge=0, description="Gain", units="dB")


class HarpDeviceType(Enum):
    BEHAVIOR = "behavior"
    OLFACTOMETER = "olfactometer"
    CLOCKGENERATOR = "clockgenerator"
    TREADMILL = "treadmill"
    LICKOMETER = "lickometer"
    ANALOGINPUT = "analoginput"
    GENERIC = "generic"


class HarpDeviceBase(AindModel):
    who_am_i: Optional[int] = Field(None, le=9999, ge=0, description="Device WhoAmI")
    device_type: HarpDeviceType = Field(HarpDeviceType.GENERIC, description="Device type")
    serial_number: Optional[str] = Field(None, description="Device serial number")
    port_name: str = Field(..., description="Device port name")
    additional_settings: Optional[Any] = Field(None, description="Additional settings")


class HarpBehavior(HarpDeviceBase):
    device_type: Literal[HarpDeviceType.BEHAVIOR] = HarpDeviceType.BEHAVIOR
    who_am_i: Literal[1216] = 1216


class HarpOlfactometer(HarpDeviceBase):
    device_type: Literal[HarpDeviceType.OLFACTOMETER] = HarpDeviceType.OLFACTOMETER
    who_am_i: Literal[1140] = 1140


class HarpClockGenerator(HarpDeviceBase):
    device_type: Literal[HarpDeviceType.CLOCKGENERATOR] = HarpDeviceType.CLOCKGENERATOR
    who_am_i: Literal[1158] = 1158


class HarpAnalogInput(HarpDeviceBase):
    device_type: Literal[HarpDeviceType.ANALOGINPUT] = HarpDeviceType.ANALOGINPUT
    who_am_i: Literal[1236] = 1236


class HarpLickometer(HarpDeviceBase):
    device_type: Literal[HarpDeviceType.LICKOMETER] = HarpDeviceType.LICKOMETER
    who_am_i: Literal[None] = None


class HarpTreadmill(HarpDeviceBase):
    device_type: Literal[HarpDeviceType.TREADMILL] = HarpDeviceType.TREADMILL
    who_am_i: Literal[None] = None


from pydantic import RootModel


class HarpDevice(RootModel):
    root: Annotated[
        Union[HarpBehavior, HarpOlfactometer, HarpClockGenerator, HarpAnalogInput, HarpLickometer, HarpTreadmill],
        Field(discriminator="device_type"),
    ]


class WebCamera(AindModel):
    index: int = Field(0, ge=0, description="Camera index")


class Screen(AindModel):
    display_index: int = Field(1, description="Display index")
    target_render_frequency: float = Field(60, description="Target render frequency")
    target_update_frequency: float = Field(120, description="Target update frequency")
    calibration_directory: str = Field("Calibration\\Monitors\\", description="Calibration directory")
    texture_assets_directory: str = Field("Textures", description="Calibration directory")


class Treadmill(AindModel):
    wheel_diameter: float = Field(15, ge=0, description="Wheel diameter", units="cm")
    pulses_per_revolution: int = Field(28800, ge=1, description="Pulses per revolution")
    invert_direction: bool = Field(False, description="Invert direction")


class Valve(AindModel):
    calibration_intercept: float = Field(0, description="Calibration intercept")
    calibration_slope: float = Field(1, description="Calibration slope")


#class AindVrForagingRig(AindCoreModel):
#    describedBy: str = Field("pyd_taskLogic")
#    schema_version: Literal["0.1.0"] = "0.1.0"
#    harp_devices: Dict[str, HarpDevice] = Field(default_factory=dict, description="Harp devices")
#    spinnaker_cameras: Dict[str, SpinnakerCamera] = Field(default_factory=dict, description="Spinnaker cameras")
#    web_cameras: Dict[str, WebCamera] = Field(default_factory=dict, description="Web cameras")
#    screen: Screen = Field(Screen(), description="Screen settings")
#    treadmill: Treadmill = Field(Treadmill(), description="Treadmill settings")
#    water_valve: Valve = Field(Valve(), description="Water valve settings")


class AindVrForagingRig(AindCoreModel):
    describedBy: str = Field("pyd_taskLogic")
    schema_version: Literal["0.1.0"] = "0.1.0"
    auxiliary_camera0: Optional[WebCamera] = Field(WebCamera(), description="Auxiliary camera 0")
    auxiliary_camera1: Optional[WebCamera] = Field(WebCamera(), description="Auxiliary camera 1")
    harp_behavior: HarpBehavior = Field(..., description="Harp behavior")
    harp_olfactometer: HarpOlfactometer = Field(..., description="Harp olfactometer")
    harp_lickometer: HarpLickometer = Field(..., description="Harp lickometer")
    harp_clock_generator: HarpClockGenerator = Field(..., description="Harp clock generator")
    harp_analog_input: Optional[HarpAnalogInput] = Field(None, description="Harp analog input")
    face_camera: SpinnakerCamera = Field(..., description="Face camera")
    top_body_camera: Optional[SpinnakerCamera] = Field(None, description="Top body camera")
    side_body_camera: Optional[SpinnakerCamera] = Field(None, description="Side body camera")
    screen: Screen = Field(Screen(), description="Screen settings")
    treadmill: Treadmill = Field(Treadmill(), description="Treadmill settings")
    water_valve: Valve = Field(Valve(), description="Water valve settings")




def schema() -> BaseModel:
    return AindVrForagingRig
