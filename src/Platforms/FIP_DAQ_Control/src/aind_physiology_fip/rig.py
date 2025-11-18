from enum import IntFlag
from typing import Annotated, Dict, List, Literal, Optional, Self

from aind_behavior_services import calibration, rig
from aind_behavior_services.rig.cameras import Circle, Point2f
from aind_behavior_services.rig.network import ZmqConnection
from pydantic import BaseModel, Field, model_validator

from . import __semver__


class FipCamera(rig.Device):
    """Camera device configuration for FIP photometry system."""

    device_type: Literal["FipCamera"] = "FipCamera"
    serial_number: str = Field(..., description="Camera serial number")
    gain: float = Field(default=0, ge=0, description="Gain")
    offset: Point2f = Field(default=Point2f(x=0, y=0), description="Offset (px)", validate_default=True)


def _make_default_rois() -> List[Circle]:
    return [Circle(center=Point2f(x=x, y=y), radius=20) for x in (50, 150) for y in (50, 150)]


class RoiSettings(BaseModel):
    """Region of Interest (ROI) settings for camera channels in the FIP system."""

    camera_green_iso_background: Circle = Field(
        default=Circle(center=Point2f(x=10, y=10), radius=10),
        description="ROI to compute the background for the green/iso camera channel",
    )
    camera_red_background: Circle = Field(
        default=Circle(center=Point2f(x=10, y=10), radius=10),
        description="ROI to compute the background for the red camera channel",
    )
    camera_green_iso_roi: List[Circle] = Field(
        default=_make_default_rois(), description="ROI for the green/iso camera channel"
    )
    camera_red_roi: List[Circle] = Field(default=_make_default_rois(), description="ROI for the red camera channel")


class Networking(BaseModel):
    """Network configuration settings for ZeroMQ communication."""

    zmq_publisher: ZmqConnection = Field(
        default=ZmqConnection(connection_string="@tcp://localhost:5556", topic="fip"), validate_default=True
    )
    zmq_subscriber: ZmqConnection = Field(
        default=ZmqConnection(connection_string="@tcp://localhost:5557", topic="fip"), validate_default=True
    )


LightSourcePower = Annotated[float, Field(default=0, ge=0, description="Power (mW)")]
DutyCycle = Annotated[float, Field(default=0, ge=0, le=1, description="Duty cycle (0-100%)")]


class LightSourceCalibrationOutput(BaseModel):
    """Output of the light source calibration process."""

    power_lut: Dict[DutyCycle, LightSourcePower] = Field(
        ..., description="Look-up table for LightSource power vs. duty cycle"
    )


class LightSourceCalibration(calibration.Calibration):
    """Calibration model for converting light source duty cycle to power output."""

    output: LightSourceCalibrationOutput = Field(..., title="Lookup table to convert duty cycle to power (mW)")


class Ports(IntFlag):
    """Available hardware ports in the FIP cuttlefish board."""

    NONE = 0
    IO0 = 1 << 0
    IO1 = 1 << 1
    IO2 = 1 << 2
    IO3 = 1 << 3
    IO4 = 1 << 4
    IO5 = 1 << 5
    IO6 = 1 << 6
    IO7 = 1 << 7


class FipTask(BaseModel):
    """Task configuration for FIP timing and triggering parameters."""

    delta_1: int = Field(default=15650, ge=0, description="Delta 1 (us)")
    delta_2: int = Field(default=666, ge=0, description="Delta 2 (us)")
    delta_3: int = Field(default=300, ge=0, description="Delta 3 (us)")
    delta_4: int = Field(default=50, ge=0, description="Delta 4 (us)")
    light_source_port: Ports = Field(description="Port that triggers the light source.")
    camera_port: Ports = Field(description="Port that triggers the camera.")
    events_enabled: bool = Field(
        default=True,
        description="Whether to enable events for the task. If False, the task will not trigger any events.",
    )
    mute_output: bool = Field(
        default=False,
        description="Whether to mute the output of the task. If True, the task will not trigger any outputs but timing will be preserved.",
    )
    pwm_frequency: float = Field(default=10000, ge=10000, description="PWM frequency (Hz) of the light source output.")


class LightSource(rig.Device):
    """Light source device configuration with power control and timing tasks."""

    device_type: Literal["LightSource"] = "LightSource"
    power: float = Field(default=0, ge=0, description="Power (mW)")
    calibration: Optional[LightSourceCalibration] = Field(
        default=None,
        title="Calibration",
        description="Calibration for the LightSource. If left empty, 'power' will be used as duty-cycle (0-100).",
    )
    task: FipTask = Field(title="Task", description="Task for the light source")

    @model_validator(mode="after")
    def _validate_power(self) -> Self:
        if self.calibration is None:
            if self.power < 0 or self.power > 1:
                raise ValueError("Power must be between 0 and 1 when no calibration is provided.")
        return self


class AindPhysioFipRig(rig.AindBehaviorRigModel):
    """Complete rig configuration model for AIND FIP photometry system."""

    version: Literal[__semver__] = __semver__
    camera_green_iso: FipCamera = Field(title="G/Iso Camera", description="Camera for the green and iso channels")
    camera_red: FipCamera = Field(title="Red Camera", description="Red camera")
    light_source_uv: LightSource = Field(title="UV light source", description="UV (415nm) light source")
    light_source_blue: LightSource = Field(title="Blue light source", description="Blue (470nm) light source")
    light_source_lime: LightSource = Field(title="Lime light source", description="Lime (560nm) light source")
    roi_settings: Optional[RoiSettings] = Field(
        default=None,
        title="Region of interest settings",
        description="Region of interest settings. Leave empty to attempt to load from local file or manually define it in the program.",
    )
    cuttlefish_fip: rig.harp.HarpCuttlefishfip = Field(
        title="CuttlefishFip",
        description="CuttlefishFip board for controlling the trigger of cameras and light-sources",
    )
    networking: Networking = Field(Networking(), title="Networking", description="Networking settings")
