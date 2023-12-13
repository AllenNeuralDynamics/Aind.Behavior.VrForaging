# Import core types
from typing import List, Literal, Optional, Union
from typing_extensions import Annotated
from pydantic import Field
from enum import Enum
import pyd_distributions as distributions
from pydantic.config import ConfigDict

# Import aind-datas-schema types
from aind_data_schema.base import AindModel


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
    data: Annotated[List[List[float]], Field(description="Defines a 2D matrix")] = [[1]]


# Updaters
class NumericalUpdaterOperation(str, Enum):
    NONE = "None"
    OFFSET = "Offset"
    GAIN = "Gain"
    SET = "Set"
    OFFSETPERCENTAGE = "OffsetPercentage"


class NumericalUpdaterParameters(AindModel):
    initialValue: Field(default=0.0, description="Initial value of the parameter")
    increment: Field(default=0.0, description="Value to increment the parameter by")
    decrement: Field(default=0.0, description="Value to decrement the parameter by")
    minimum: Field(default=0.0, description="Minimum value of the parameter")
    maximum: Field(default=0.0, description="Minimum value of the parameter")


class NumericalUpdater(AindModel):
    operation: Annotated[NumericalUpdaterOperation, Field(description="Operation to perform on the parameter")] = NumericalUpdaterOperation.NONE
    parameters: Annotated[NumericalUpdaterParameters, Field(description="Parameters of the updater")] = NumericalUpdaterParameters()


class Texture(AindModel):
    name: str = Field(default="default", description="Name of the texture")
    size: Size = Field(default=Size(width=40, height=40), description="Size of the texture")


class OdorSpecifications(AindModel):
    index: Annotated[Literal[0, 1, 2, 3], Field(description="Index of the odor to be used")]
    concentration: float = Field(default=1, ge=0, le=1, description="Concentration of the odor")


class OperantLogic(AindModel):
    isOperant: bool = Field(default=True, description="Will the trial implement operant logic")
    stopDuration: float = Field(default=0, ge=0, description="Duration (s) the animal must stop for to lock its choice")
    timeToCollectReward: float = Field(default=100000, ge=0, description="Time(s) the animal has to collect the reward")
    graceDistanceThreshold: float = Field(default=10, ge=0, description="Virtual distance (cm) the animal must be within to not abort the current choice")


class PatchRewardFunction(AindModel):
    initialAmount: float = Field(default=0, ge=0, description="Initial amount of reward (a.u.)")


class RewardSpecifications(AindModel):
    amount: float = Field(ge=0, description="Amount of reward (a.u.)")
    operantLogic: Annotated[Optional[OperantLogic], Field(description="The optional operant logic of the reward")] = None
    probability: float = Field(default=1, ge=0, le=1, description="Probability of the reward")
    delay: Annotated[Union[distributions.Distribution, float], Field(default=0, description="The optional distribution where the delay to reward will be drawn from")]


class PatchStatistics(AindModel):
    label: str = Field(default="", description="Label of the patch")
    stateIndex = int = Field(default=0, ge=0, description="Index of the state")
    odorSpecifications: Annotated[Optional[OdorSpecifications], Field(description="The optional odor specifications of the patch")] = None
    rewardSpecifications: Annotated[Optional[RewardSpecifications], Field(description="The optional reward specifications of the patch")] = None


class RenderSpecifications(AindModel):
    contrast: Optional[float] = Field(default=None, ge=0, le=1, description="Contrast of the texture")


class VirtualSite(AindModel):
    id: int = Field(default=0, ge=0, description="Id of the virtual site")
    label: str = Field(default="VirtualSite", description="Label of the virtual site")
    length: float = Field(default=120, ge=0, description="Length of the virtual site (cm)")
    startPosition: float = Field(default=0, ge=0, description="Start position of the virtual site (cm)")
    odor: Annotated[Optional[OdorSpecifications], Field(None, description="The optional odor specifications of the virtual site")] = None
    reward: Annotated[Optional[RewardSpecifications], Field(description="The optional reward specifications of the virtual site")] = None
    render: Annotated[RenderSpecifications, Field(description="The optional render specifications of the virtual site")] = RenderSpecifications()


class WallTextures(AindModel):
    floor: Annotated[Texture, Field(description="The texture of the floor")]
    ceiling: Annotated[Texture, Field(description="The texture of the ceiling")]
    left: Annotated[Texture, Field(description="The texture of the left")]
    right: Annotated[Texture, Field(description="The texture of the right")]


class VisualCorridor(AindModel):
    id: int = Field(default=0, ge=0, description="Id of the visual corridor object")
    size: Annotated[Size, Field(description="Size of the corridor (cm)")] = Size(width=40, height=40)
    startPosition: float = Field(default=0, ge=0, description="Start position of the corridor (cm)")
    length: float = Field(default=120, ge=0, description="Length of the corridor site (cm)")
    textures: Annotated[WallTextures, Field(description="The textures of the corridor")]

