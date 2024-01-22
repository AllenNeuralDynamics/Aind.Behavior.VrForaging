# Import core types
from __future__ import annotations

from enum import Enum

# Import core types
from typing import Annotated, Dict, List, Literal, Optional, Union

import aind_behavior_vr_foraging.distributions as distributions
from aind_data_schema.base import AindCoreModel, AindModel
from pydantic import BaseModel, Field, RootModel


def scalar_value(value: float) -> distributions.Scalar:
    """
    Helper function to create a scalar value distribution for a given value.

    Args:
        value (float): The value of the scalar distribution.

    Returns:
        distributions.Scalar: The scalar distribution type.
    """
    return distributions.Scalar(distribution_parameters=distributions.ScalarDistributionParameter(value=value))


class Size(AindModel):
    width: float = Field(default=0, description="Width of the texture")
    height: float = Field(default=0, description="Height of the texture")


class Vector2(AindModel):
    x: float = Field(default=0, description="X coordinate of the point")
    y: float = Field(default=0, description="Y coordinate of the point")


class Vector3(AindModel):
    x: float = Field(default=0, description="X coordinate of the point")
    y: float = Field(default=0, description="Y coordinate of the point")
    z: float = Field(default=0, description="Z coordinate of the point")


class Matrix2D(AindModel):
    data: List[List[float]] = Field([[1]], description="Defines a 2D matrix")


# Updaters
class NumericalUpdaterOperation(str, Enum):
    NONE = "None"
    OFFSET = "Offset"
    GAIN = "Gain"
    SET = "Set"
    OFFSETPERCENTAGE = "OffsetPercentage"


class NumericalUpdaterParameters(AindModel):
    initial_value: float = Field(default=0.0, description="Initial value of the parameter")
    increment: float = Field(default=0.0, description="Value to increment the parameter by")
    decrement: float = Field(default=0.0, description="Value to decrement the parameter by")
    minimum: float = Field(default=0.0, description="Minimum value of the parameter")
    maximum: float = Field(default=0.0, description="Minimum value of the parameter")


class NumericalUpdater(AindModel):
    operation: NumericalUpdaterOperation = Field(
        default=NumericalUpdaterOperation.NONE, description="Operation to perform on the parameter"
    )
    parameters: NumericalUpdaterParameters = Field(
        NumericalUpdaterParameters(), description="Parameters of the updater"
    )


class Texture(AindModel):
    name: str = Field(default="default", description="Name of the texture")
    size: Size = Field(default=Size(width=40, height=40), description="Size of the texture")


class OdorSpecification(AindModel):
    index: int = Field(..., ge=0, le=3, description="Index of the odor to be used")
    concentration: float = Field(default=1, ge=0, le=1, description="Concentration of the odor")


class OperantLogic(AindModel):
    is_operant: bool = Field(default=True, description="Will the trial implement operant logic")
    stop_duration: float = Field(
        default=0, ge=0, description="Duration (s) the animal must stop for to lock its choice"
    )
    time_to_collect_reward: float = Field(
        default=100000, ge=0, description="Time(s) the animal has to collect the reward"
    )
    grace_distance_threshold: float = Field(
        default=10, ge=0, description="Virtual distance (cm) the animal must be within to not abort the current choice"
    )


class PatchRewardFunction(AindModel):
    initial_amount: float = Field(default=99999999, ge=0, description="Initial amount of reward (a.u.)")


class RewardSpecification(AindModel):
    amount: float = Field(..., ge=0, description="Amount of reward (a.u.)")
    operant_logic: Optional[OperantLogic] = Field(None, description="The optional operant logic of the reward")
    probability: float = Field(default=1, ge=0, le=1, description="Probability of the reward")
    delay: distributions.Distribution = Field(
        default=scalar_value(0),
        description="The optional distribution where the delay to reward will be drawn from")
    reward_function: PatchRewardFunction = Field(
        default=PatchRewardFunction(), description="Reward function of the patch."
    )


class VirtualSiteLabels(str, Enum):
    UNSPECIFIED = "Unspecified"
    INTERPATCH = "InterPatch"
    REWARDSITE = "RewardSite"
    INTERSITE = "InterSite"


class RenderSpecification(AindModel):
    contrast: Optional[float] = Field(default=None, ge=0, le=1, description="Contrast of the texture")


class VirtualSiteGenerator(AindModel):
    render_specification: RenderSpecification = Field(
        default=RenderSpecification(), description="Contrast of the environment"
    )
    label: VirtualSiteLabels = Field(default=VirtualSiteLabels.UNSPECIFIED, description="Label of the virtual site")
    length_distribution: distributions.Distribution = Field(
        default=scalar_value(20),
        description="Distribution of the length of the virtual site",
    )


class VirtualSiteGeneration(AindModel):
    inter_site: VirtualSiteGenerator = Field(
        VirtualSiteGenerator(), description="Generator of the inter-site virtual sites"
    )
    inter_patch: VirtualSiteGenerator = Field(
        VirtualSiteGenerator(), description="Generator of the inter-patch virtual sites"
    )
    reward_site: VirtualSiteGenerator = Field(
        VirtualSiteGenerator(), description="Generator of the reward-site virtual sites"
    )


class VirtualSite(AindModel):
    id: int = Field(default=0, ge=0, description="Id of the virtual site")
    label: str = Field(default="VirtualSite", description="Label of the virtual site")
    length: float = Field(20, description="Length of the virtual site (cm)")
    start_position: float = Field(default=0, ge=0, description="Start position of the virtual site (cm)")
    odor_specification: Optional[OdorSpecification] = Field(
        None, description="The optional odor specification of the virtual site"
    )
    reward_specification: Optional[RewardSpecification] = Field(
        None, description="The optional reward specification of the virtual site"
    )
    render_specification: RenderSpecification = Field(
        RenderSpecification(), description="The optional render specification of the virtual site"
    )


class PatchStatistics(AindModel):
    label: str = Field(default="", description="Label of the patch")
    state_index: int = Field(default=0, ge=0, description="Index of the state")
    odor_specification: Optional[OdorSpecification] = Field(
        default=None, description="The optional odor specification of the patch"
    )
    reward_specification: Optional[RewardSpecification] = Field(
        default=None, description="The optional reward specification of the patch"
    )
    virtual_site_generation: VirtualSiteGeneration = Field(
        VirtualSiteGeneration(), description="Virtual site generation specification"
    )


class WallTextures(AindModel):
    floor: Texture = Field(..., description="The texture of the floor")
    ceiling: Texture = Field(..., description="The texture of the ceiling")
    left: Texture = Field(..., description="The texture of the left")
    right: Texture = Field(..., description="The texture of the right")


class VisualCorridor(AindModel):
    id: int = Field(default=0, ge=0, description="Id of the visual corridor object")
    size: Size = Field(default=Size(width=40, height=40), description="Size of the corridor (cm)")
    start_position: float = Field(default=0, ge=0, description="Start position of the corridor (cm)")
    length: float = Field(default=120, ge=0, description="Length of the corridor site (cm)")
    textures: WallTextures = Field(..., description="The textures of the corridor")


class EnvironmentStatistics(AindModel):
    patches: List[PatchStatistics] = Field(default_factory=list, description="List of patches")
    transition_matrix: Matrix2D = Field(default=Matrix2D(), description="Transition matrix between patches")
    first_state: Optional[int] = Field(
        default=None, ge=0, description="The first state to be visited. If None, it will be randomly drawn."
    )


class ServoMotor(AindModel):
    period: int = Field(default=20000, ge=1, description="Period", units="us")
    min_pulse_duration: int = Field(default=1000, ge=1, description="Minimum pulse duration", units="us")
    max_pulse_duration: int = Field(default=2000, ge=1, description="Maximum pulse duration", units="us")
    default_pulse_duration: int = Field(default=2000, ge=1, description="Default pulse duration", units="us")


class MovableSpoutControl(AindModel):
    enabled: bool = Field(default=False, description="Whether the movable spout is enabled")
    time_to_collect_after_reward: float = Field(default=1, ge=0, description="Time (s) to collect after reward")
    servo_motor: ServoMotor = Field(default=ServoMotor(), description="Servo motor settings")


class OdorControl(AindModel):
    valve_max_open_time: float = Field(
        default=10, ge=0, description="Maximum time (s) the valve can be open continuously"
    )
    target_total_flow: float = Field(
        default=1000, ge=100, le=1000, description="Target total flow (ml/s) of the odor mixture"
    )
    use_channel_3_as_carrier: bool = Field(default=True, description="Whether to use channel 3 as carrier")
    target_odor_flow: float = Field(
        default=100, ge=0, le=100, description="Target odor flow (ml/s) in the odor mixture"
    )


class PositionControl(AindModel):
    gain: Vector3 = Field(default=Vector3(x=1, y=1, z=1), description="Gain of the position control.")
    initial_position: Vector3 = Field(default=Vector3(x=0, y=2.56, z=0), description="Gain of the position control.")
    frequency_filter_cutoff: float = Field(
        default=0.5,
        ge=0,
        le=100,
        description="Cutoff frequency (Hz) of the low-pass filter used to filter the velocity signal.",
    )
    velocity_threshold: float = Field(
        default=1, ge=0, description="Threshold (cm/s) of the velocity signal used to detect when the animal is moving."
    )


class AudioControl(AindModel):
    duration: float = Field(default=0.2, ge=0, description="Duration", units="s")
    frequency: float = Field(default=1000, ge=100, description="Frequency", units="Hz")


class OperationControl(AindModel):
    movable_spout_control: MovableSpoutControl = Field(
        default=MovableSpoutControl(), description="Control of the movable spout"
    )
    odor_control: OdorControl = Field(default=OdorControl(), description="Control of the odor")
    position_control: PositionControl = Field(default=PositionControl(), description="Control of the position")
    audio_control: AudioControl = Field(default=AudioControl(), description="Control of the audio")


class TaskStage(str, Enum):
    HABITUATION = "HABITUATION"
    FORAGING = "FORAGING"


class TaskStageSettingsBase(AindModel):
    task_stage: TaskStage = Field(default=TaskStage.FORAGING, description="Stage of the task")


class HabituationSettings(TaskStageSettingsBase):
    task_stage: Literal[TaskStage.HABITUATION] = TaskStage.HABITUATION
    distance_to_reward: distributions.Distribution = Field(..., description="Distance (cm) to the reward")
    reward_specification: RewardSpecification = Field(..., description="specification of the reward")
    render_specification: RenderSpecification = Field(
        default=RenderSpecification(), description="Contrast of the environement"
    )


class ForagingSettings(TaskStageSettingsBase):
    task_stage: Literal[TaskStage.FORAGING] = TaskStage.FORAGING


TaskStageSettings = Annotated[
    Union[HabituationSettings, ForagingSettings], Field(discriminator="task_stage", title="TaskStage")
]


class AindVrForagingTaskLogic(AindCoreModel):
    describedBy: str = Field("")
    schema_version: Literal["0.1.0"] = "0.1.0"
    updaters: Dict[str, NumericalUpdater] = Field(default_factory=dict, description="List of numerical updaters")
    environment_statistics: EnvironmentStatistics = Field(..., description="Statistics of the environment")
    stage_settings: TaskStageSettings = Field(ForagingSettings(), description="Settings of the task stage")
    operation_control: OperationControl = Field(..., description="Control of the operation")
    dependencies: Optional[Dependencies] = Field(None, description="Dependencies of the task logic")


class Dependencies(BaseModel):
    visual_corridor: VisualCorridor
    virtual_site: VirtualSite
    distributions: distributions.Distribution

    class Config:
        json_schema_extra = {"x-abstract": "True"}


def schema() -> BaseModel:
    return AindVrForagingTaskLogic
