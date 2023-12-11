# Import core types
from typing import List, Literal, Optional
from pydantic import Field
from enum import Enum

# Import aind-datas-schema types
from aind_data_schema.base import AindCoreModel


class Size(AindCoreModel):
    width: float = Field(default=0, description="Width of the texture")
    height: float = Field(default=0, description="Height of the texture")


class Vector2(AindCoreModel):
    x: float = Field(default=0, description="X coordinate of the point")
    y: float = Field(default=0, description="Y coordinate of the point")


class Vector3(AindCoreModel):
    x: float = Field(default=0, description="X coordinate of the point")
    y: float = Field(default=0, description="Y coordinate of the point")
    z: float = Field(default=0, description="Z coordinate of the point")


class Matrix2D(AindCoreModel):
    data: List[List[float]] = Field(default=[[1]], description="Defines a 2D matrix")

# Updaters


class NumericalUpdaterOperation(str, Enum):
    NONE = "None"
    OFFSET = "Offset"
    GAIN = "Gain"
    SET = "Set"
    OFFSETPERCENTAGE = "OffsetPercentage"


class NumericalUpdaterParameters(AindCoreModel):
    initialValue: Field(default=0.0, description="Initial value of the parameter")
    increment: Field(default=0.0, description="Value to increment the parameter by")
    decrement: Field(default=0.0, description="Value to decrement the parameter by")
    minimum: Field(default=0.0, description="Minimum value of the parameter")
    maximum: Field(default=0.0, description="Minimum value of the parameter")


class NumericalUpdater(AindCoreModel):
    operation: NumericalUpdaterOperation = NumericalUpdaterOperation.NONE
    parameters: NumericalUpdaterParameters = NumericalUpdaterParameters()


class Texture(AindCoreModel):
    name: str = Field(default="default", description="Name of the texture")
    size: Size = Field(Size(width=40, height=40), description="Size of the texture")


class OdorSpecifications(AindCoreModel):
    index: Literal[0, 1, 2, 3] = Field(description="Index of the odor to be used")
    concentration: float = Field(default=1, ge=0, le=1, description="Concentration of the odor")


class OperantLogic(AindCoreModel):
    isOperant: bool = Field(default=True, description="Will the trial implement operant logic")
    stopDuration: float = Field(default=0, ge=0, description="Duration (s) the animal must stop for to lock its choice")
    timeToCollectReward: float = Field(default=100000, ge=0, description="Time(s) the animal has to collect the reward")
    graceDistanceThreshold: float = Field(default=10, ge=0, description="Virtual distance (cm) the animal must be within to not abort the current choice")


class PatchRewardFunction(AindCoreModel):
    initialAmount: float = Field(default=0, ge=0, description="Initial amount of reward (a.u.)")


#TODO
class Distribution(AindCoreModel):
    todo: int


class RewardSpecifications(AindCoreModel):
    amount: float = Field(ge=0, description="Amount of reward (a.u.)")
    operantLogic = Optional[OperantLogic] = Field(None, description="The optional operant logic of the reward")
    probability: float = Field(default=1, ge=0, le=1, description="Probability of the reward")
    delay: Distribution


class PatchStatistics(AindCoreModel):
    label: str = Field(default="", description="Label of the patch")
    stateIndex = int = Field(default=0, ge=0, description="Index of the state")
    odorSpecifications: Optional[OdorSpecifications] = Field(None, description="The optional odor specifications of the patch")
    rewardSpecifications: Optional[RewardSpecifications] = Field(None, description="The optional reward specifications of the patch")


class RenderSpecifications(AindCoreModel):
    contrast: Optional[float] = Field(default=None, ge=0, le=1, description="Contrast of the texture")


class VirtualSite(AindCoreModel):
    id: int = Field(default=0, ge=0, description="Id of the virtual site")
    label: str = Field(default="VirtualSite", description="Label of the virtual site")
    length: float = Field(default=120, ge=0, description="Length of the virtual site (cm)")
    startPosition: float = Field(default=0, ge=0, description="Start position of the virtual site (cm)")
    odor: Optional[OdorSpecifications] = Field(None, description="The optional odor specifications of the virtual site")
    reward: Optional[RewardSpecifications] = Field(None, description="The optional reward specifications of the virtual site")
    render: RenderSpecifications = Field(RenderSpecifications(), description="The optional render specifications of the virtual site")


class WallTextures(AindCoreModel):
    floor: Texture = Field(..., description="The texture of the floor")
    ceiling: Texture = Field(..., description="The texture of the ceiling")
    left: Texture = Field(..., description="The texture of the left wall")
    right: Texture = Field(..., description="The texture of the right wall")


class VisualCorridor(AindCoreModel):
    id: int = Field(default=0, ge=0, description="Id of the visual corridor object")
    size: Size = Field(Size(width=40, height=40), description="Size of the corridor (cm)")
    startPosition: float = Field(default=0, ge=0, description="Start position of the corridor (cm)")
    length: float = Field(default=120, ge=0, description="Length of the corridor site (cm)")
    textures: WallTextures = Field(..., description="The textures of the corridor")

