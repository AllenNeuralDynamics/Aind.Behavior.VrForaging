from typing import Literal, Optional, Self

import aind_behavior_services.rig as rig
import aind_behavior_services.rig.cameras as cameras
import aind_behavior_services.rig.harp as harp
import aind_behavior_services.rig.olfactometer as oc
import aind_behavior_services.rig.treadmill as treadmill
import aind_behavior_services.rig.visual_stimulation as visual_stimulation
import aind_behavior_services.rig.water_valve as wvc
from aind_behavior_services.rig import aind_manipulator as man
from pydantic import BaseModel, Field, model_validator

from aind_behavior_vr_foraging import __semver__


class AindManipulatorDevice(man.AindManipulator):
    """Appends a task specific configuration to the base manipulator model."""

    spout_axis: man.Axis = Field(default=man.Axis.Y1, description="Spout axis")


class RigCalibration(BaseModel):
    """Container class for calibration models."""

    water_valve: wvc.WaterValveCalibration = Field(description="Water valve calibration")


class AindVrForagingRig(rig.Rig):
    """Represents the schema, and concrete instantiation, of a rig configuration to run the VrForaging behavior task."""

    version: Literal[__semver__] = __semver__
    triggered_camera_controller: cameras.CameraController[cameras.SpinnakerCamera] = Field(
        description="Required camera controller to triggered cameras."
    )
    monitoring_camera_controller: Optional[cameras.CameraController[cameras.WebCamera]] = Field(
        default=None, description="Optional camera controller for monitoring cameras."
    )
    harp_behavior: harp.HarpBehavior = Field(description="Harp behavior")
    harp_olfactometer: oc.Olfactometer = Field(description="Harp olfactometer")
    harp_olfactometer_extension: list[oc.Olfactometer] = Field(
        default_factory=list,
        description="A collection of subordinate olfactometers that can be added to increase the number of independently delivered odors. The order of the list determines the order by which odors are numbered",
    )
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

    @model_validator(mode="after")
    def _validate_olfactometer_configuration(self) -> Self:
        olfactometers = [self.harp_olfactometer] + self.harp_olfactometer_extension
        for olfactometer in olfactometers:
            if len(olfactometer.calibration.channel_config) < 4:
                raise ValueError(
                    f"Olfactometer {olfactometer} has fewer than 4 channels configured. All channels must be configured in VrForaging task."
                )
        for olfactometer in self.harp_olfactometer_extension:
            for channel in olfactometer.calibration.channel_config.values():
                if channel.channel_type != oc.OlfactometerChannelType.ODOR:
                    raise ValueError(
                        f"All channels in olfactometer extensions must be of type 'Odor'. Found channel with type {channel.channel_type} in olfactometer {olfactometer}"
                    )
        if (
            self.harp_olfactometer.calibration.channel_config[oc.OlfactometerChannel.Channel3].channel_type
            != oc.OlfactometerChannelType.CARRIER
        ):
            raise ValueError(
                f"Channel 3 of the main olfactometer must be configured as 'Carrier'. Found type {self.harp_olfactometer.calibration.channel_config[oc.OlfactometerChannel.Channel3].channel_type}"
            )

        return self
