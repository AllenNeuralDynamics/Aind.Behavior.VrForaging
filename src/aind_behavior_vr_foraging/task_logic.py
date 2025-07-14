from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Annotated, Dict, List, Literal, Optional, Self, Union

import aind_behavior_services.task_logic.distributions as distributions
from aind_behavior_services.task_logic import AindBehaviorTaskLogicModel, TaskParameters
from pydantic import BaseModel, Field, NonNegativeFloat, field_validator, model_validator
from typing_extensions import TypeAliasType

from aind_behavior_vr_foraging import (
    __version__,
)


def scalar_value(value: float) -> distributions.Scalar:
    """
    Helper function to create a scalar value distribution for a given value.

    Args:
        value (float): The value of the scalar distribution.

    Returns:
        distributions.Scalar: The scalar distribution type.
    """
    return distributions.Scalar(distribution_parameters=distributions.ScalarDistributionParameter(value=value))


class Size(BaseModel):
    width: float = Field(default=0, description="Width of the texture")
    height: float = Field(default=0, description="Height of the texture")


class Vector2(BaseModel):
    x: float = Field(default=0, description="X coordinate of the point")
    y: float = Field(default=0, description="Y coordinate of the point")


class Vector3(BaseModel):
    x: float = Field(default=0, description="X coordinate of the point")
    y: float = Field(default=0, description="Y coordinate of the point")
    z: float = Field(default=0, description="Z coordinate of the point")


# Updaters
class NumericalUpdaterOperation(str, Enum):
    NONE = "None"
    OFFSET = "Offset"
    GAIN = "Gain"
    SET = "Set"
    OFFSETPERCENTAGE = "OffsetPercentage"


class NumericalUpdaterParameters(BaseModel):
    initial_value: float = Field(default=0.0, description="Initial value of the parameter")
    increment: float = Field(default=0.0, description="Value to increment the parameter by")
    decrement: float = Field(default=0.0, description="Value to decrement the parameter by")
    minimum: float = Field(default=0.0, description="Minimum value of the parameter")
    maximum: float = Field(default=0.0, description="Minimum value of the parameter")


class NumericalUpdater(BaseModel):
    operation: NumericalUpdaterOperation = Field(
        default=NumericalUpdaterOperation.NONE, description="Operation to perform on the parameter"
    )
    parameters: NumericalUpdaterParameters = Field(
        default=NumericalUpdaterParameters(), description="Parameters of the updater"
    )


class UpdaterTarget(str, Enum):
    STOP_DURATION_OFFSET = "StopDurationOffset"
    STOP_VELOCITY_THRESHOLD = "StopVelocityThreshold"
    REWARD_DELAY_OFFSET = "RewardDelayOffset"


class Texture(BaseModel):
    name: str = Field(default="default", description="Name of the texture")
    size: Size = Field(default=Size(width=40, height=40), description="Size of the texture")


class OdorSpecification(BaseModel):
    index: int = Field(..., ge=0, le=3, description="Index of the odor to be used")
    concentration: float = Field(default=1, ge=0, le=1, description="Concentration of the odor")


class OperantLogic(BaseModel):
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


class PowerFunction(BaseModel):
    function_type: Literal["PowerFunction"] = "PowerFunction"
    minimum: float = Field(default=0, description="Minimum value of the function")
    maximum: float = Field(default=1, description="Maximum value of the function")
    a: float = Field(default=1, description="Coefficient a of the function: value = a * pow(b, c * x) + d")
    b: float = Field(
        default=2.718281828459045, description="Coefficient b of the function: value = a * pow(b, c * x) + d"
    )
    c: float = Field(default=-1, description="Coefficient c of the function: value = a * pow(b, c * x) + d")
    d: float = Field(default=0, description="Coefficient d of the function: value = a * pow(b, c * x) + d")


class LinearFunction(BaseModel):
    function_type: Literal["LinearFunction"] = "LinearFunction"
    minimum: float = Field(default=0, description="Minimum value of the function")
    maximum: float = Field(default=9999, description="Maximum value of the function")
    a: float = Field(default=1, description="Coefficient a of the function: value = a * x + b")
    b: float = Field(default=0, description="Coefficient b of the function: value = a * x + b")


class ConstantFunction(BaseModel):
    function_type: Literal["ConstantFunction"] = "ConstantFunction"
    value: float = Field(default=1, description="Value of the function")


class LookupTableFunction(BaseModel):
    function_type: Literal["LookupTableFunction"] = "LookupTableFunction"
    lut_keys: List[float] = Field(..., description="List of keys of the lookup table", min_length=1)
    lut_values: List[float] = Field(..., description="List of values of the lookup table", min_length=1)

    @model_validator(mode="after")
    def _validate_lut(self) -> Self:
        if len(self.lut_keys) != len(self.lut_values):
            raise ValueError("The number of keys and values must be the same.")
        return self


if TYPE_CHECKING:
    RewardFunction = Union[ConstantFunction, LinearFunction, PowerFunction, LookupTableFunction]
else:
    RewardFunction = TypeAliasType(
        "RewardFunction",
        Annotated[
            Union[ConstantFunction, LinearFunction, PowerFunction, LookupTableFunction],
            Field(discriminator="function_type"),
        ],
    )


class DepletionRule(str, Enum):
    ON_REWARD = "OnReward"
    ON_CHOICE = "OnChoice"
    ON_TIME = "OnTime"
    ON_DISTANCE = "OnDistance"


class PatchRewardFunction(BaseModel):
    amount: RewardFunction = Field(
        default=ConstantFunction(value=1),
        description="Determines the amount of reward to be delivered. The value is in microliters",
        validate_default=True,
    )
    probability: RewardFunction = Field(
        default=ConstantFunction(value=1),
        description="Determines the probability that a reward will be delivered",
        validate_default=True,
    )
    available: RewardFunction = Field(
        default=LinearFunction(minimum=0, a=-1, b=5),
        description="Determines the total amount of reward available left in the patch. The value is in microliters",
        validate_default=True,
    )
    depletion_rule: DepletionRule = Field(default=DepletionRule.ON_CHOICE, description="Depletion")


class RewardSpecification(BaseModel):
    operant_logic: Optional[OperantLogic] = Field(default=None, description="The optional operant logic of the reward")
    delay: distributions.Distribution = Field(
        default=scalar_value(0),
        description="The optional distribution where the delay to reward will be drawn from",
        validate_default=True,
    )
    reward_function: PatchRewardFunction = Field(
        default=PatchRewardFunction(), description="Reward function of the patch."
    )


class VirtualSiteLabels(str, Enum):
    UNSPECIFIED = "Unspecified"
    INTERPATCH = "InterPatch"
    POSTPATCH = "PostPatch"
    REWARDSITE = "RewardSite"
    INTERSITE = "InterSite"


class RenderSpecification(BaseModel):
    contrast: Optional[float] = Field(default=None, ge=0, le=1, description="Contrast of the texture")


class TreadmillSpecification(BaseModel):
    friction: Optional[distributions.Distribution] = Field(
        default=None,
        description="Friction of the treadmill (0-1). The drawn value must be between 0 and 1",
    )


class VirtualSiteGenerator(BaseModel):
    render_specification: RenderSpecification = Field(
        default=RenderSpecification(), description="Contrast of the environment", validate_default=True
    )
    label: VirtualSiteLabels = Field(default=VirtualSiteLabels.UNSPECIFIED, description="Label of the virtual site")
    length_distribution: distributions.Distribution = Field(
        default=scalar_value(20), description="Distribution of the length of the virtual site", validate_default=True
    )
    treadmill_specification: Optional[TreadmillSpecification] = Field(
        default=None, description="Treadmill specification", validate_default=True
    )


class VirtualSiteGeneration(BaseModel):
    inter_site: VirtualSiteGenerator = Field(
        default=VirtualSiteGenerator(label=VirtualSiteLabels.INTERSITE),
        validate_default=True,
        description="Generator of the inter-site virtual sites",
    )
    inter_patch: VirtualSiteGenerator = Field(
        default=VirtualSiteGenerator(label=VirtualSiteLabels.INTERPATCH),
        validate_default=True,
        description="Generator of the inter-patch virtual sites",
    )
    post_patch: Optional[VirtualSiteGenerator] = Field(
        default=None,
        validate_default=True,
        description="Generator of the post-patch virtual sites",
    )
    reward_site: VirtualSiteGenerator = Field(
        default=VirtualSiteGenerator(label=VirtualSiteLabels.REWARDSITE),
        validate_default=True,
        description="Generator of the reward-site virtual sites",
    )


class VirtualSite(BaseModel):
    id: int = Field(default=0, ge=0, description="Id of the virtual site")
    label: VirtualSiteLabels = Field(default=VirtualSiteLabels.UNSPECIFIED, description="Label of the virtual site")
    length: float = Field(default=20, description="Length of the virtual site (cm)")
    start_position: float = Field(default=0, ge=0, description="Start position of the virtual site (cm)")
    odor_specification: Optional[OdorSpecification] = Field(
        default=None, description="The optional odor specification of the virtual site"
    )
    reward_specification: Optional[RewardSpecification] = Field(
        default=None, description="The optional reward specification of the virtual site"
    )
    render_specification: RenderSpecification = Field(
        default=RenderSpecification(), description="The optional render specification of the virtual site"
    )
    treadmill_specification: Optional[TreadmillSpecification] = Field(
        default=None, description="Treadmill specification"
    )


class PatchStatistics(BaseModel):
    label: str = Field(default="", description="Label of the patch")
    state_index: int = Field(default=0, ge=0, description="Index of the state")
    odor_specification: Optional[OdorSpecification] = Field(
        default=None, description="The optional odor specification of the patch"
    )
    reward_specification: Optional[RewardSpecification] = Field(
        default=None, description="The optional reward specification of the patch"
    )
    virtual_site_generation: VirtualSiteGeneration = Field(
        default=VirtualSiteGeneration(), validate_default=True, description="Virtual site generation specification"
    )


class WallTextures(BaseModel):
    floor: Texture = Field(..., description="The texture of the floor")
    ceiling: Texture = Field(..., description="The texture of the ceiling")
    left: Texture = Field(..., description="The texture of the left")
    right: Texture = Field(..., description="The texture of the right")


class VisualCorridor(BaseModel):
    id: int = Field(default=0, ge=0, description="Id of the visual corridor object")
    size: Size = Field(default=Size(width=40, height=40), description="Size of the corridor (cm)")
    start_position: float = Field(default=0, ge=0, description="Start position of the corridor (cm)")
    length: float = Field(default=120, ge=0, description="Length of the corridor site (cm)")
    textures: WallTextures = Field(..., description="The textures of the corridor")


class EnvironmentStatistics(BaseModel):
    patches: List[PatchStatistics] = Field(default_factory=list, description="List of patches", min_length=1)
    transition_matrix: List[List[NonNegativeFloat]] = Field(
        default=[[1]],
        description="Determines the transition probabilities between patches",
        validate_default=True,
    )
    first_state_occupancy: Optional[List[NonNegativeFloat]] = Field(
        default=None,
        description="Determines the first state the animal will be in. If null, it will be randomly drawn.",
    )

    @field_validator("transition_matrix", mode="after")
    @classmethod
    def _validate_transition_matrix(cls, value: List[List[NonNegativeFloat]]) -> List[List[NonNegativeFloat]]:
        if any(len(row) != len(value) for row in value):
            raise ValueError("Transition matrix must be square.")
        return value


class MovableSpoutControl(BaseModel):
    enabled: bool = Field(default=False, description="Whether the movable spout is enabled")
    time_to_collect_after_reward: float = Field(default=1, ge=0, description="Time (s) to collect after reward")
    retracting_distance: float = Field(
        default=0, ge=0, description="The distance, relative to the default position, the spout will be retracted by"
    )


class OdorControl(BaseModel):
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


class PositionControl(BaseModel):
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


class AudioControl(BaseModel):
    duration: float = Field(default=0.2, ge=0, description="Duration")
    frequency: float = Field(default=1000, ge=100, description="Frequency")


class OperationControl(BaseModel):
    movable_spout_control: MovableSpoutControl = Field(
        default=MovableSpoutControl(), description="Control of the movable spout"
    )
    odor_control: OdorControl = Field(default=OdorControl(), description="Control of the odor", validate_default=True)
    position_control: PositionControl = Field(
        default=PositionControl(), description="Control of the position", validate_default=True
    )
    audio_control: AudioControl = Field(
        default=AudioControl(), description="Control of the audio", validate_default=True
    )


class TaskMode(str, Enum):
    DEBUG = "DEBUG"
    HABITUATION = "HABITUATION"
    FORAGING = "FORAGING"


class TaskModeSettingsBase(BaseModel):
    task_mode: TaskMode = Field(default=TaskMode.FORAGING, description="Stage of the task")


class HabituationSettings(TaskModeSettingsBase):
    task_mode: Literal[TaskMode.HABITUATION] = TaskMode.HABITUATION
    distance_to_reward: distributions.Distribution = Field(..., description="Distance (cm) to the reward")
    render_specification: RenderSpecification = Field(
        RenderSpecification(),
        description="The optional render specification of the virtual site",
        validate_default=True,
    )


class DebugSettings(TaskModeSettingsBase):
    """This class is not currently implemented"""

    task_mode: Literal[TaskMode.DEBUG] = TaskMode.DEBUG
    visual_corridors: List[VisualCorridor]
    virtual_sites: List[VirtualSite]


class ForagingSettings(TaskModeSettingsBase):
    task_mode: Literal[TaskMode.FORAGING] = TaskMode.FORAGING


if TYPE_CHECKING:
    TaskModeSettings = Union[HabituationSettings, ForagingSettings, DebugSettings]
else:
    TaskModeSettings = TypeAliasType(
        "TaskModeSettings",
        Annotated[Union[HabituationSettings, ForagingSettings, DebugSettings], Field(discriminator="task_mode")],
    )


class _BlockEndConditionBase(BaseModel):
    condition_type: str


class BlockEndConditionDuration(_BlockEndConditionBase):
    condition_type: Literal["Duration"] = "Duration"
    value: distributions.Distribution = Field(..., description="Time after which the block ends.")


class BlockEndConditionDistance(_BlockEndConditionBase):
    condition_type: Literal["Distance"] = "Distance"
    value: distributions.Distribution = Field(..., description="Distance after which the block ends.")


class BlockEndConditionChoice(_BlockEndConditionBase):
    condition_type: Literal["Choice"] = "Choice"
    value: distributions.Distribution = Field(..., description="Number of choices after which the block ends.")


class BlockEndConditionReward(_BlockEndConditionBase):
    condition_type: Literal["Reward"] = "Reward"
    value: distributions.Distribution = Field(..., description="Number of rewards after which the block ends.")


class BlockEndConditionPatchCount(_BlockEndConditionBase):
    condition_type: Literal["PatchCount"] = "PatchCount"
    value: distributions.Distribution = Field(..., description="Number of patches after which the block will end.")


if TYPE_CHECKING:
    BlockEndCondition = Union[
        BlockEndConditionDuration, BlockEndConditionDistance, BlockEndConditionChoice, BlockEndConditionReward
    ]
else:
    BlockEndCondition = TypeAliasType(
        "BlockEndCondition",
        Annotated[
            Union[
                BlockEndConditionDuration,
                BlockEndConditionDistance,
                BlockEndConditionChoice,
                BlockEndConditionReward,
                BlockEndConditionPatchCount,
            ],
            Field(discriminator="condition_type"),
        ],
    )


class Block(BaseModel):
    environment_statistics: EnvironmentStatistics = Field(..., description="Statistics of the environment")
    end_conditions: List[BlockEndCondition] = Field(
        [], description="List of end conditions that must be true for the block to end."
    )


class BlockStructure(BaseModel):
    blocks: List[Block] = Field(..., description="Statistics of the environment", min_length=1)
    sampling_mode: Literal["Random", "Sequential"] = Field("Sequential", description="Sampling mode of the blocks.")


class AindVrForagingTaskParameters(TaskParameters):
    updaters: Dict[UpdaterTarget, NumericalUpdater] = Field(
        default_factory=dict, description="Look-up table for numeric updaters"
    )
    environment: BlockStructure = Field(..., description="Statistics of the environment")
    task_mode_settings: TaskModeSettings = Field(
        default=ForagingSettings(), description="Settings of the task stage", validate_default=True
    )
    operation_control: OperationControl = Field(..., description="Control of the operation")


class AindVrForagingTaskLogic(AindBehaviorTaskLogicModel):
    version: Literal[__version__] = __version__
    name: Literal["AindVrForaging"] = Field(default="AindVrForaging", description="Name of the task logic", frozen=True)
    task_parameters: AindVrForagingTaskParameters = Field(..., description="Parameters of the task logic")
