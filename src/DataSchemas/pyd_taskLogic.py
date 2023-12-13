# Import core types
from typing import List, Literal, Optional, Union
from typing_extensions import Annotated
from pydantic import Field
from enum import Enum
import pyd_distributions as distributions
import pyd_common as common
from pydantic.config import ConfigDict

# Import aind-datas-schema types
from aind_data_schema.base import AindModel, AindCoreModel


class EnvironementStatistics(AindModel):
    patches: Annotated[List[common.PatchStatistics], Field(default=[], description="List of patches")]
    transitionMatrix: Annotated[common.Matrix2D, Field(default=common.Matrix2D(), description="Transition matrix between patches")]
    firstState: Optional[int] = Field(None, ge=0, description="The first state to be visited. If None, it will be randomly drawn.")

class OperationControlBase(AindModel):
    pass


class MovableSpoutControl(OperationControlBase):
    enabled: bool = Field(default=False, description="Whether the movable spout is enabled")
    timeToCollectAfterReward: float = Field(default=1, ge=0, description="Time (s) to collect after reward")


class OdorControl(OperationControlBase):
    valveMaxOpenTime: float = Field(default=10, ge=0, description="Maximum time (s) the valve can be open continuously")
    targetTotalFlow: float = Field(default=1000, ge=100, le=1000, description="Target total flow (ml/s) of the odor mixture")
    useChannel3AsCarrier: bool = Field(default=True, description="Whether to use channel 3 as carrier")
    targetOdorFlow: float = Field(default=100, ge=0, le=100, description="Target odor flow (ml/s) in the odor mixture")


class PositionControl(OperationControlBase):
    gain: common.Vector3 = Field(default=common.Vector3(x=1, y=1, z=1), description="Gain of the position control.")
    initialPosition: common.Vector3 = Field(default=common.Vector3(x=0, y=0, z=0), description="Gain of the position control.")
    frequencyFilterCutoff: float = Field(default=0.5, ge=0, le=100, description="Cutoff frequency (Hz) of the low-pass filter used to filter the velocity signal.")
    velocityThreshold: float = Field(default=1, ge=0, description="Threshold (cm/s) of the velocity signal used to detect when the animal is moving.")


class OperationControl(AindModel):
    movableSpoutControl: Annotated[MovableSpoutControl, Field(default=MovableSpoutControl(), description="Control of the movable spout")]
    odorControl: Annotated[OdorControl, Field(default=OdorControl(), description="Control of the odor")]
    positionControl: Annotated[PositionControl, Field(default=PositionControl(), description="Control of the position")]


class TaskStage(str, Enum):
    HABITUATION = "HABITUATION"
    FORAGING = "FORAGING"


class TaskStageSettings(AindModel):
    taskStage: Annotated[TaskStage, Field(description="Stage of the task")]


class HabituationSettings(TaskStageSettings):
    taskStage: Literal[TaskStage.HABITUATION] = Field(TaskStage.HABITUATION)
    distanceToReward: distributions.ExponentialDistribution = Field(description="Distance (cm) to the reward")
    rewardSpecifications: common.RewardSpecifications = Field(description="Specifications of the reward")
    renderSpecifications: common.RenderSpecifications = Field(default=common.RenderSpecifications(), description="Contrast of the environement")


class ForagingSettings(TaskStageSettings):
    taskStage: Literal[TaskStage.FORAGING] = Field(TaskStage.FORAGING)


class VirtualSiteLabels(str, Enum):
    UNSPECIFIED = "Unspecified"
    INTERPATCH = "InterPatch"
    REWARDSITE = "RewardSite"
    INTERSITE = "InterSite"


class VirtualSiteGenerator(AindModel):
    renderSpecifications: common.RenderSpecifications = Field(default=common.RenderSpecifications(), description="Contrast of the environement")
    label: Annotated[VirtualSiteLabels, Field(description="Label of the virtual site")]
    lengthDistribution: distributions.Distribution = Field(description="Distribution of the length of the virtual site")


class VirtualSiteGeneration(AindModel):
    interSite: Annotated[VirtualSiteGenerator, Field(description="Generator of the inter-site virtual sites")]
    interPatch: Annotated[VirtualSiteGenerator, Field(description="Generator of the inter-patch virtual sites")]
    rewardSite: Annotated[VirtualSiteGenerator, Field(description="Generator of the reward-site virtual sites")]


class AindVrForagingTask(AindCoreModel):
    describedBy: str = Field("pyd_taskLogic")
    schema_version: Literal["0.1.0"] = Field("0.1.0")
    updaters: Annotated[List[common.NumericalUpdater], Field(default=[], description="List of numerical updaters")]
    environementStatistics: EnvironementStatistics = Field(..., description="Statistics of the environement")
    taskStageSettings: Annotated[TaskStageSettings, Field(description="Settings of the task stage")]
    virtualSiteGeneration: Annotated[VirtualSiteGeneration, Field(description="Generation of the virtual sites")]
    operationControl: Annotated[OperationControl, Field(description="Control of the operation")]

AindVrForagingTask.write_standard_model()
