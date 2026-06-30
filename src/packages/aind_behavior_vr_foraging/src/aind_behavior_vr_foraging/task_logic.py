import logging
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Dict, List, Literal, Optional, Self, TypeAlias, Union, cast

import aind_behavior_services.task.distributions as distributions
from aind_behavior_services.common import Size, Vector3
from aind_behavior_services.task import Task, TaskParameters
from pydantic import (
    BaseModel,
    BeforeValidator,
    Field,
    NonNegativeFloat,
    field_serializer,
    field_validator,
    model_validator,
)
from typing_extensions import TypeAliasType, deprecated

from aind_behavior_vr_foraging import (
    __semver__,
)

logger = logging.getLogger(__name__)


def scalar_value(value: float) -> distributions.Scalar:
    """
    Helper function to create a scalar value distribution for a given value.

    Args:
        value (float): The value of the scalar distribution.

    Returns:
        distributions.Scalar: The scalar distribution type.
    """
    return distributions.Scalar(distribution_parameters=distributions.ScalarDistributionParameter(value=value))


# ==================== NUMERICAL UPDATERS ====================
class NumericalUpdaterOperation(str, Enum):
    """
    Enumeration of operations that can be performed by numerical updaters.

    These operations define how parameter values are modified during task execution,
    allowing for dynamic adjustment of task parameters based on performance or other criteria.
    """

    NONE = "None"
    """Does not perform any update"""
    OFFSET = "Offset"
    """Adds (or subtracts) the update value to the current value. The update value can be positive or negative."""
    GAIN = "Gain"
    """Multiplies the current value by the update value. The update value can be greater or less than 1."""
    SET = "Set"
    """Sets the current value to the update value."""


class NumericalUpdaterParameters(BaseModel):
    """
    Parameters that control how numerical updates are applied to task values.

    These parameters define the bounds and increments for updating numerical values
    during task execution, ensuring values stay within acceptable ranges.
    """

    initial_value: float = Field(default=0.0, description="Initial value of the parameter")
    on_success: float = Field(default=0.0, description="Value used to update the parameter by on success")
    on_failure: float = Field(default=0.0, description="Value used to update the parameter by on failure")
    increment: float = Field(
        default=0.0,
        description="Value to increment the parameter by",
        deprecated="This field is deprecated, use on_success instead",
    )
    decrement: float = Field(
        default=0.0,
        description="Value to decrement the parameter by",
        deprecated="This field is deprecated, use on_failure instead",
    )
    minimum: float = Field(default=0.0, description="Minimum value of the parameter")
    maximum: float = Field(default=0.0, description="Minimum value of the parameter")

    @model_validator(mode="before")
    @classmethod
    def _ensure_backwards_compatibility(cls, data: Any) -> Any:
        if isinstance(data, dict):
            __map = {
                "increment": "on_success",
                "decrement": "on_failure",
            }
            for old_key, new_key in __map.items():
                if old_key in data and new_key not in data:
                    data[new_key] = data.pop(old_key)
                    logger.warning("'%s' is deprecated. Please use '%s' instead.", old_key, new_key)
        return data

    @model_validator(mode="after")
    def _ensure_backwards_compatibility_after(self) -> Self:
        self.increment = self.on_success
        self.decrement = self.on_failure
        return self


class NumericalUpdater(BaseModel):
    """
    A numerical updater that modifies task parameters during execution.

    This class combines an operation type with parameters to define how values
    should be updated dynamically during the task, enabling adaptive behavior
    based on animal performance or other criteria.
    """

    operation: NumericalUpdaterOperation = Field(
        default=NumericalUpdaterOperation.NONE, description="Operation to perform on the parameter"
    )
    parameters: NumericalUpdaterParameters = Field(
        default=NumericalUpdaterParameters(), description="Parameters of the updater"
    )


class UpdaterTarget(str, Enum):
    """
    Enumeration of parameters that can be targeted by numerical updaters.

    These targets define which task parameters can be dynamically modified
    during task execution to adapt to animal performance or experimental needs.
    """

    STOP_DURATION_OFFSET = "StopDurationOffset"
    STOP_VELOCITY_THRESHOLD = "StopVelocityThreshold"
    REWARD_DELAY_OFFSET = "RewardDelayOffset"


# ==================== SENSORY STIMULUS SPECIFICATIONS ====================


class Texture(BaseModel):
    """
    Defines visual texture properties for VR environment surfaces.

    Textures are applied to walls, floors, and other surfaces in the virtual
    environment to provide visual cues and context for the foraging task.

    Texture name must correspond to a valid texture asset loaded in the workflow.
    """

    name: str = Field(default="default", description="Name of the texture")
    size: Size = Field(default=Size(width=40, height=40), description="Size of the texture")


class WallTextures(BaseModel):
    """
    Defines textures for all walls of a visual corridor in the VR environment.

    This class specifies the visual appearance of corridor surfaces including
    floor, ceiling, and side walls, allowing for complex visual environments
    with different textures on each surface.
    """

    floor: Texture = Field(description="The texture of the floor")
    ceiling: Texture = Field(description="The texture of the ceiling")
    left: Texture = Field(description="The texture of the left")
    right: Texture = Field(description="The texture of the right")


class VisualCorridor(BaseModel):
    """
    Defines a visual corridor segment in the VR environment.

    Visual corridors are the basic building blocks of the VR environment,
    defining spatial regions with specific textures, dimensions, and positions.
    """

    id: int = Field(default=0, ge=0, description="Id of the visual corridor object")
    size: Size = Field(default=Size(width=40, height=40), description="Size of the corridor (cm)")
    start_position: float = Field(default=0, ge=0, description="Start position of the corridor (cm)")
    length: float = Field(default=120, ge=0, description="Length of the corridor site (cm)")
    textures: WallTextures = Field(description="The textures of the corridor")


# ==================== PATCH REWARD LOGIC ====================


class OperantLogic(BaseModel):
    """
    Defines operant conditioning logic for reward delivery in the VR foraging task.

    This class controls when and how rewards are delivered based on animal behavior,
    implementing stopping requirements, collection timeouts, and spatial constraints.
    """

    is_operant: bool = Field(default=True, description="Will the trial implement operant logic")
    stop_duration: distributions.Distribution = Field(
        default=scalar_value(0),
        validate_default=True,
        description="Duration (s) the animal must stop for to lock its choice",
    )
    time_to_collect_reward: float = Field(
        default=100000, ge=0, description="Time(s) the animal has to collect the reward"
    )
    grace_distance_threshold: float = Field(
        default=10, ge=0, description="Virtual distance (cm) the animal must be within to not abort the current choice"
    )
    abort_velocity_threshold: Optional[float] = Field(
        default=None,
        ge=0,
        description="Velocity (cm/s) above which an in-progress operant choice is aborted. This is an ADDITIONAL "
        "abort source: the choice aborts if velocity exceeds this OR displacement exceeds grace_distance_threshold "
        "OR the animal leaves the reward site. None disables only the velocity source (grace + leave-site still apply). "
        "Interaction with the stop threshold: this is evaluated on the SAME filtered velocity signal as stop "
        "detection, which locks a choice when velocity falls BELOW StopVelocityThreshold "
        "(UpdaterTarget.STOP_VELOCITY_THRESHOLD, seeded from the position-control velocity_threshold and shaped "
        "within/across sessions). The two gates partition the same velocity axis in opposite directions, so this "
        "value must be >= the operative StopVelocityThreshold: if it is lower, the band "
        "(abort_velocity_threshold, StopVelocityThreshold) lets the animal lock a stop while already too fast to "
        "hold it, forfeiting every such choice. Because StopVelocityThreshold is dynamic (e.g. shaped 60 -> 8 cm/s "
        "by a GAIN updater) whereas this is a fixed absolute, only enable the velocity abort on stages where the "
        "stop threshold is already floored below it (e.g. a static stop threshold of 8 with this set to 15); never "
        "pair a low fixed abort with an actively-shaped, still-high stop threshold.",
    )


class _PatchUpdateFunction(BaseModel):
    """
    Base class for patch update functions.

    This is an internal base class that defines the common interface for all
    patch update function types. Should not be instantiated directly.
    """

    function_type: str


class LookupTableFunction(_PatchUpdateFunction):
    """
    A patch update function that uses lookup table interpolation.

    Update in the form of x = lut_values[lerp(lut_keys, lut_values, tick_value)].
    This function maps input values to output values using a lookup table with
    linear interpolation between defined points. Useful for complex, non-linear
    reward schedules or parameter updates.
    """

    function_type: Literal["LookupTableFunction"] = "LookupTableFunction"
    lut_keys: List[float] = Field(description="List of keys of the lookup table", min_length=1)
    lut_values: List[float] = Field(description="List of values of the lookup table", min_length=1)

    @model_validator(mode="after")
    def _validate_lut(self) -> Self:
        if len(self.lut_keys) != len(self.lut_values):
            raise ValueError("The number of keys and values must be the same.")
        return self


class ClampedRateFunction(_PatchUpdateFunction):
    """
    A patch update function that applies a clamped rate-based update.

    Update in the form of x = clamp(x + rate * tick_value).
    This function updates values at a specified rate while keeping results within
    defined minimum and maximum bounds. The rate is applied per rule unit (e.g.,
    time, distance, choices).
    """

    function_type: Literal["ClampedRateFunction"] = "ClampedRateFunction"
    minimum: Optional[float] = Field(default=0, description="Minimum value of the rate")
    maximum: Optional[float] = Field(description="Maximum value of the rate")
    rate: distributions.Distribution = Field(description="Rate of the replenishment, in value per rule unit.")


class ClampedMultiplicativeRateFunction(_PatchUpdateFunction):
    """
    A patch update function that applies multiplicative rate updates with bounds.

    Update in the form of x = clamp(x * rate ** tick_value).
    This function multiplies the current value by the rate parameter, maintaining
    the result within specified minimum and maximum bounds. Useful for percentage-
    based changes and exponential decay/growth patterns.
    """

    function_type: Literal["ClampedMultiplicativeRateFunction"] = "ClampedMultiplicativeRateFunction"
    minimum: Optional[float] = Field(default=0, description="Minimum value of the rate")
    maximum: Optional[float] = Field(description="Maximum value of the rate")
    rate: distributions.Distribution = Field(description="Rate of the replenishment, in value per rule unit.")


class SaturatingMultiplicativeRateFunction(_PatchUpdateFunction):
    """
    Multiplicative updater with configurable out-of-bounds rectification.

    The raw update is computed as ``x_raw = x * rate ** tick_value``.
    If ``x_raw`` is within bounds, it is returned unchanged.
    If it falls below ``minimum`` or above ``maximum``, the output is rectified to
    ``below_minimum_to`` or ``above_maximum_to`` respectively when provided;
    otherwise it falls back to the corresponding bound.
    """

    function_type: Literal["SaturatingMultiplicativeRateFunction"] = "SaturatingMultiplicativeRateFunction"
    minimum: Optional[float] = Field(default=0, description="Minimum value of the rate")
    maximum: Optional[float] = Field(description="Maximum value of the rate")
    below_minimum_to: Optional[float] = Field(
        default=None, description="If the value is below minimum, it will be set to this value instead of the minimum"
    )
    above_maximum_to: Optional[float] = Field(
        default=None, description="If the value is above maximum, it will be set to this value instead of the maximum"
    )
    rate: distributions.Distribution = Field(description="Rate of the replenishment, in value per rule unit.")


class SetValueFunction(_PatchUpdateFunction):
    """
    A patch update function that sets the target to a specific value.

    Update in the form of x = value.
    This function directly sets the target parameter to a value drawn from the
    specified distribution, ignoring the current value. Useful for resetting
    parameters or applying discrete changes.
    """

    function_type: Literal["SetValueFunction"] = "SetValueFunction"
    value: distributions.Distribution = Field(description="Sets the value of the target to this value.")


class CtcmFunction(_PatchUpdateFunction):
    """
    A patch update function that uses a continuous-time Markov chain (CTMC)
    to determine patch updates based on a transition probability matrix.

    It expects a transition matrix that takes the current value of the variable
    of interest (e.g. Probability), and outputs a new value based on the defined
    stochastic process in the transition matrix.
    """

    function_type: Literal["CtcmFunction"] = "CtcmFunction"
    transition_matrix: List[List[NonNegativeFloat]] = Field(description="Transition matrix between states")
    rho: float = Field(description="The underlying value governing the stochastic process")
    dt: Literal[0.1] = Field(default=0.1, description="Sampling time step (s)")
    rate: Optional[float] = Field(
        default=None,
        description="Rate of the replenishment used to generate the matrix. This value is used for metadata keep sake only",
    )
    minimum: float = Field(gt=0, description="Minimum value after update")
    maximum: float = Field(description="Maximum value after update")

    @field_validator("transition_matrix", mode="after")
    @classmethod
    def validate_transition_matrix(cls, value):
        """Ensures matrix is of valid format and normalized to 1 within rows"""
        if not value:
            raise ValueError("Transition matrix must not be empty.")
        if any(len(row) != len(value) for row in value):
            raise ValueError("Transition matrix must be square (same number of rows and columns).")
        for row in value:
            row_sum = sum(row)
            for col in row:
                col /= row_sum
        return value

    @field_serializer("transition_matrix")
    def serialize_transition_matrix(self, value: List[List[NonNegativeFloat]]) -> List[List[NonNegativeFloat]]:
        """Round to 15 significant digits for deterministic serialization across platforms."""
        return [[round(v, 15) for v in row] for row in value]

    @classmethod
    def from_replenishment_rate(
        cls, n_states: int, replenishment_rate: float, rho: float, dt: Optional[float] = 0.1
    ) -> "CtcmFunction":
        """
        Computes the replenishment transition probability matrix for each patch
        Parameters
        -----------
        n_states: int
            number reward states per patch.
        replenishment_rate: float
            replenishment rate.
        rho: float
            The underlying value governing the stochastic process
        dt: float
            experiment time step


        Returns
        -------
        CtcmFunction
            Instance of CtcmFunction with computed transition matrix.
        """
        import numpy as np
        from scipy.linalg import expm

        if dt is None:
            dt = cls.model_fields["dt"].default
        q = np.zeros((n_states, n_states))
        np.fill_diagonal(q, -replenishment_rate)
        np.fill_diagonal(q[:, 1:], replenishment_rate)
        q[-1, -1] = 0

        p_t = expm(q * dt)
        assert p_t.ndim == 2
        transition_matrix = cast(list[list[float]], p_t.tolist())
        return cls(
            transition_matrix=transition_matrix,
            rho=rho,
            dt=dt,
            rate=replenishment_rate,
        )


if TYPE_CHECKING:
    PatchUpdateFunction = Union[
        ClampedRateFunction,
        ClampedMultiplicativeRateFunction,
        SaturatingMultiplicativeRateFunction,
        SetValueFunction,
        LookupTableFunction,
        CtcmFunction,
    ]
else:
    PatchUpdateFunction = TypeAliasType(
        "PatchUpdateFunction",
        Annotated[
            Union[
                ClampedRateFunction,
                ClampedMultiplicativeRateFunction,
                SaturatingMultiplicativeRateFunction,
                SetValueFunction,
                LookupTableFunction,
                CtcmFunction,
            ],
            Field(discriminator="function_type"),
        ],
    )


class RewardFunctionRule(str, Enum):
    """
    Enumeration of rules that trigger reward function updates.

    These rules define when and how reward replenishment occurs, with different
    triggers based on animal behavior, time passage, or spatial navigation.
    """

    ON_REWARD = "OnReward"
    """Triggers after a reward is delivered. The tick value is always 1."""
    ON_REWARD_AMOUNT = "OnRewardAmount"
    """Triggers after a reward is delivered. The tick value is the amount of reward."""
    ON_CHOICE = "OnChoice"
    """Triggers after a choice is made. The tick value is always 1."""
    ON_TIME = "OnTime"
    """Triggers periodically. The tick value is the elapsed time since the last update (s)."""
    ON_DISTANCE = "OnDistance"
    """Triggers periodically. The tick value is the distance traveled since the last update (cm)."""
    ON_THIS_PATCH_ENTRY = "OnThisPatchEntry"
    """Triggers when the animal enters the patch. The tick value is always 1."""
    ON_PATCH_ENTRY = "OnPatchEntry"
    """Triggers when the animal enters any patch. The tick value is always 1."""
    ON_CHOICE_ACCUMULATED = "OnChoiceAccumulated"
    """Triggers after a choice is made. The tick value is the accumulated number of choices."""
    ON_REWARD_ACCUMULATED = "OnRewardAccumulated"
    """Triggers after a reward is delivered. The tick value is the accumulated number of rewarded events."""
    ON_TIME_ACCUMULATED = "OnTimeAccumulated"
    """Triggers periodically. The tick value is the accumulated elapsed time since patch creation (s)."""
    ON_DISTANCE_ACCUMULATED = "OnDistanceAccumulated"
    """Triggers periodically. The tick value is the accumulated distance traveled since patch creation (cm)."""


class _RewardFunction(BaseModel):
    """
    Base class for reward functions.

    This is an internal base class that defines the common interface for all
    reward function types. Should not be instantiated directly.
    """

    function_type: str
    amount: Optional[PatchUpdateFunction] = Field(
        default=None, description="Defines the amount of reward replenished per rule unit."
    )
    probability: Optional[PatchUpdateFunction] = Field(
        default=None, description="Defines the probability of reward replenished per rule unit."
    )
    available: Optional[PatchUpdateFunction] = Field(
        default=None, description="Defines the amount of reward available replenished in the patch per rule unit."
    )


class PatchRewardFunction(_RewardFunction):
    """
    A RewardFunction that is applied when the animal is inside the patch.
    For the purposes of this function post-patch and inter-patch are excluded.
    """

    function_type: Literal["PatchRewardFunction"] = "PatchRewardFunction"
    rule: Literal[
        RewardFunctionRule.ON_REWARD,
        RewardFunctionRule.ON_REWARD_AMOUNT,
        RewardFunctionRule.ON_CHOICE,
        RewardFunctionRule.ON_TIME,
        RewardFunctionRule.ON_DISTANCE,
        RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        RewardFunctionRule.ON_REWARD_ACCUMULATED,
        RewardFunctionRule.ON_TIME_ACCUMULATED,
        RewardFunctionRule.ON_DISTANCE_ACCUMULATED,
    ] = Field(
        default=RewardFunctionRule.ON_REWARD, description="Rule to trigger reward function", validate_default=True
    )


class OutsideRewardFunction(_RewardFunction):
    """
    A RewardFunction that is applied when the animal is outside of the patch.
    """

    function_type: Literal["OutsideRewardFunction"] = "OutsideRewardFunction"
    rule: Literal[
        RewardFunctionRule.ON_TIME,
        RewardFunctionRule.ON_DISTANCE,
        RewardFunctionRule.ON_TIME_ACCUMULATED,
        RewardFunctionRule.ON_DISTANCE_ACCUMULATED,
    ] = Field(default=RewardFunctionRule.ON_TIME, description="Rule to trigger reward function")
    delay: float = Field(
        default=0, ge=0, description="Delay (s) before the replenishment starts after the rule is triggered."
    )


class OnThisPatchEntryRewardFunction(_RewardFunction):
    """
    A RewardFunction that is applied when the animal enters the patch.
    """

    function_type: Literal["OnThisPatchEntryRewardFunction"] = "OnThisPatchEntryRewardFunction"
    rule: Literal[RewardFunctionRule.ON_THIS_PATCH_ENTRY] = Field(
        default=RewardFunctionRule.ON_THIS_PATCH_ENTRY, description="Rule to trigger reward function"
    )


class PersistentRewardFunction(_RewardFunction):
    """
    A RewardFunction that is always active.
    """

    function_type: Literal["PersistentRewardFunction"] = "PersistentRewardFunction"
    rule: Literal[
        RewardFunctionRule.ON_REWARD,
        RewardFunctionRule.ON_CHOICE,
        RewardFunctionRule.ON_TIME,
        RewardFunctionRule.ON_DISTANCE,
        RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        RewardFunctionRule.ON_REWARD_ACCUMULATED,
        RewardFunctionRule.ON_TIME_ACCUMULATED,
        RewardFunctionRule.ON_DISTANCE_ACCUMULATED,
        RewardFunctionRule.ON_PATCH_ENTRY,
    ]


if TYPE_CHECKING:
    RewardFunction = Union[
        PatchRewardFunction, OutsideRewardFunction, OnThisPatchEntryRewardFunction, PersistentRewardFunction
    ]
else:
    RewardFunction = TypeAliasType(
        "RewardFunction",
        Annotated[
            Union[PatchRewardFunction, OutsideRewardFunction, OnThisPatchEntryRewardFunction, PersistentRewardFunction],
            Field(discriminator="function_type"),
        ],
    )


class RewardSpecification(BaseModel):
    """
    Specifies reward parameters and behavior for a patch.

    This class defines all aspects of reward delivery including amounts, probabilities,
    delays, operant logic, and dynamic update functions. It serves as the complete
    specification for how rewards are managed in a given Patch.
    """

    operant_logic: Optional[OperantLogic] = Field(default=None, description="The optional operant logic of the reward")
    delay: distributions.Distribution = Field(
        default=scalar_value(0),
        description="The optional distribution where the delay to reward will be drawn from",
        validate_default=True,
    )
    amount: distributions.Distribution = Field(
        default=scalar_value(5), description="Initial amount of reward in microliters", validate_default=True
    )
    probability: distributions.Distribution = Field(
        default=scalar_value(1), description="Initial probability of reward delivery", validate_default=True
    )
    available: distributions.Distribution = Field(
        default=scalar_value(10),
        description="Initial amount of reward available in the patch in microliters",
        validate_default=True,
    )
    reward_function: List[RewardFunction] = Field(default=[], description="Reward function of the patch")


# ==================== VIRTUAL SITE LOGIC ====================


class VirtualSiteLabels(str, Enum):
    """
    Enumeration of virtual site types in the VR foraging environment.

    These labels categorize different regions of the virtual environment,
    each serving different functional roles in the foraging task.
    """

    UNSPECIFIED = "Unspecified"
    """Placeholder"""
    INTERPATCH = "InterPatch"
    """Region rendered before entering a patch"""
    POSTPATCH = "PostPatch"
    """Region rendered after leaving a patch"""
    REWARDSITE = "RewardSite"
    """Region where rewards are delivered"""
    INTERSITE = "InterSite"
    """Region between sites within a patch"""


class RenderSpecification(BaseModel):
    """
    Defines visual rendering properties for virtual environment elements.

    This class controls the visual appearance of virtual sites, including
    contrast and other visual parameters that affect how elements are rendered
    in the VR environment.
    """

    contrast: Optional[float] = Field(default=None, ge=0, le=1, description="Contrast of the texture")


class TreadmillSpecification(BaseModel):
    """
    Defines treadmill friction properties for virtual sites.

    This class controls the friction experienced by the animal when moving
    through different virtual sites, allowing for varied locomotion dynamics
    across different regions of the environment.
    """

    friction: Optional[distributions.Distribution] = Field(
        default=None,
        description="Friction of the treadmill (0-1). The drawn value must be between 0 and 1",
    )


class VirtualSiteGenerator(BaseModel):
    """
    Generates virtual site specifications with randomized properties.

    This class defines templates for creating virtual sites with variable properties
    like length and rendering specifications. It's used to generate diverse virtual
    environments for the foraging task.
    """

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


class PatchVirtualSitesGenerator(BaseModel):
    """
    Defines the generation specifications for all virtual site types within a patch.

    This class contains generators for all the different types of virtual sites
    that can appear within a patch environment. Each generator defines how sites
    of that type should be created with their properties and distributions.
    """

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


class VirtualSiteRewardSpecification(BaseModel):
    """
    THIS CLASS IS NOT MEANT TO BE DIRECTLY INSTANTIATED.
    Specifies reward parameters and behavior for a virtual site.

    Note: This class is primarily used internally for runtime site generation
    and is not meant to be directly instantiated in task configuration DSL.
    """

    operant_logic: OperantLogic = Field(description="The optional operant logic of the reward")
    delay: distributions.Distribution = Field(
        default=scalar_value(0),
        description="The optional distribution where the delay to reward will be drawn from",
        validate_default=True,
    )


def _odor_mixture_from_odor_specification(value: Any):
    if isinstance(value, list):
        return value
    else:
        try:
            odor_spec = _OdorSpecification.model_validate(value)
            return [odor_spec.concentration if i == odor_spec.index else 0 for i in range(3)]
        except ValueError:
            pass
    return value


OdorMixture: TypeAlias = Annotated[
    List[NonNegativeFloat],
    Field(description="The optional odor specification of the virtual site"),
    BeforeValidator(_odor_mixture_from_odor_specification),
]


@deprecated("_OdorSpecification has been deprecated and will be removed in a future release. Use OdorMixture instead")
class _OdorSpecification(BaseModel):
    """
    Specifies odor delivery parameters for olfactory cues in the VR environment.

    Odors can be delivered at specific locations to provide additional sensory
    information for navigation and foraging decisions.
    """

    index: int = Field(ge=0, le=3, description="Index of the odor to be used")
    concentration: float = Field(default=1, ge=0, le=1, description="Concentration of the odor")


class VirtualSite(BaseModel):
    """
    THIS CLASS IS NOT MEANT TO BE DIRECTLY INSTANTIATED.
    Represents a specific virtual site instance in the VR environment.

    This class defines a concrete virtual site with specific properties like position,
    length, and associated specifications. It is typically generated from VirtualSiteGenerator
    templates rather than being directly instantiated in the DSL.

    Note: This class is primarily used internally for runtime site generation
    and is not meant to be directly instantiated in task configuration DSL.
    """

    id: int = Field(default=0, ge=0, description="Id of the virtual site")
    label: VirtualSiteLabels = Field(default=VirtualSiteLabels.UNSPECIFIED, description="Label of the virtual site")
    length: float = Field(default=20, description="Length of the virtual site (cm)")
    start_position: float = Field(default=0, ge=0, description="Start position of the virtual site (cm)")
    odor_specification: Optional[OdorMixture] = Field(
        default=None, description="The optional odor specification of the virtual site"
    )
    reward_specification: Optional[VirtualSiteRewardSpecification] = Field(
        default=None, description="The optional reward specification of the virtual site"
    )
    render_specification: RenderSpecification = Field(
        default=RenderSpecification(), description="The optional render specification of the virtual site"
    )
    treadmill_specification: Optional[TreadmillSpecification] = Field(
        default=None, description="Treadmill specification"
    )


class _PatchTerminator(BaseModel):
    terminator_type: str


class PatchTerminatorOnRejection(_PatchTerminator):
    """Terminates the patch after a reward site where the animal does not stop in "count" reward sites."""

    terminator_type: Literal["OnRejection"] = "OnRejection"
    count: distributions.Distribution = Field(
        default=scalar_value(1),
        validate_default=True,
        description="Number of reward sites the animal must not stop in to terminate the patch",
    )


class PatchTerminatorOnChoice(_PatchTerminator):
    """Terminates the patch after "count" choices."""

    terminator_type: Literal["OnChoice"] = "OnChoice"
    count: distributions.Distribution = Field(
        default=scalar_value(1),
        validate_default=True,
        description="Number of choices the animal must make to terminate the patch",
    )


class PatchTerminatorOnReward(_PatchTerminator):
    """Terminates the patch after "count" rewards."""

    terminator_type: Literal["OnReward"] = "OnReward"
    count: distributions.Distribution = Field(
        default=scalar_value(1),
        validate_default=True,
        description="Number of rewards the animal must collect to terminate the patch",
    )


class PatchTerminatorOnTime(_PatchTerminator):
    """Terminates the patch after a "count" seconds."""

    terminator_type: Literal["OnTime"] = "OnTime"
    count: distributions.Distribution = Field(description="Number of seconds to wait before terminating the patch")


class PatchTerminatorOnDistance(_PatchTerminator):
    """Terminates the patch after a "count" distance."""

    terminator_type: Literal["OnDistance"] = "OnDistance"
    count: distributions.Distribution = Field(
        description="Number of distance units to wait before terminating the patch"
    )


class PatchTerminatorOnRewardSite(_PatchTerminator):
    """Terminates the patch after visiting a specific site count."""

    terminator_type: Literal["OnRewardSite"] = "OnRewardSite"
    count: distributions.Distribution = Field(
        description="Number of sites the animal visits before terminating the patch."
    )


if TYPE_CHECKING:
    PatchTerminator = Union[
        PatchTerminatorOnRejection,
        PatchTerminatorOnChoice,
        PatchTerminatorOnReward,
        PatchTerminatorOnTime,
        PatchTerminatorOnDistance,
        PatchTerminatorOnRewardSite,
    ]
else:
    PatchTerminator = TypeAliasType(
        "PatchTerminator",
        Annotated[
            Union[
                PatchTerminatorOnRejection,
                PatchTerminatorOnChoice,
                PatchTerminatorOnReward,
                PatchTerminatorOnTime,
                PatchTerminatorOnDistance,
                PatchTerminatorOnRewardSite,
            ],
            Field(discriminator="terminator_type"),
        ],
    )


class Patch(BaseModel):
    """
    Represents statistics for a patch in the VR foraging task.
    """

    @model_validator(mode="before")
    @classmethod
    def _ensure_backwards_compatibility(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Old schema had odor_specification: Optional[OdorSpecification] (nullable).
            # New schema has odor_specification: OdorMixture (non-optional list).
            # Treat explicit null as "use default" by removing the key.
            if "odor_specification" in data and data["odor_specification"] is None:
                data = dict(data)
                del data["odor_specification"]
                logger.warning(
                    "'odor_specification' was null in Patch. Removing key so the field default is used instead."
                )
        return data

    label: str = Field(default="", description="Label of the patch")
    state_index: int = Field(default=0, ge=0, description="Index of the state")
    odor_specification: OdorMixture = Field(
        default=[1.0, 0.0, 0.0],
        description="A list of odor concentrations for the patch, where the index of the list corresponds to the odor channel",
        validate_default=True,
    )
    reward_specification: RewardSpecification = Field(
        default=RewardSpecification(),
        description="The optional reward specification of the patch",
        validate_default=True,
    )
    patch_virtual_sites_generator: PatchVirtualSitesGenerator = Field(
        default=PatchVirtualSitesGenerator(), validate_default=True, description="Virtual site generation specification"
    )
    patch_terminators: List[PatchTerminator] = Field(
        default=[PatchTerminatorOnRejection()],
        validate_default=True,
        description="The optional termination specification of the patch",
    )


# ==================== ENVIRONMENT AND PATCH CONFIGURATION ====================


class _Environment(BaseModel):
    """
    Defines the statistical properties of the foraging environment.

    This class specifies the patches available in the environment, their transition
    probabilities, and initial state occupancy. It forms the core specification
    for the foraging environment structure.
    """

    environment_type: str
    patches: List[Patch] = Field(default=[Patch()], description="List of patches", min_length=1, validate_default=True)


class MarkovEnvironment(_Environment):
    """
    Defines the statistical properties of the foraging environment.

    This class specifies the patches available in the environment, their transition
    probabilities, and initial state occupancy. It forms the core specification
    for the foraging environment structure.
    """

    environment_type: Literal["Markov"] = "Markov"
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


class SequenceEnvironment(_Environment):
    """
    Defines a sequence-based foraging environment.

    This class specifies a fixed sequence of patches that the animal will experience,
    without any probabilistic transitions. It is used for deterministic environment
    configurations where the order of patches is predefined.
    """

    environment_type: Literal["Sequence"] = "Sequence"
    patch_indices: List[int] = Field(
        default=[0],
        description="Determines the sequence of patches the animal will experience. The index corresponds to Patch.state_index",
        min_length=1,
    )
    sampling_mode: Literal["RandomWithoutReplacement", "Ordered", "RandomWithReplacement"] = Field(
        default="RandomWithoutReplacement", description="Determines how the sequence is sampled"
    )

    @model_validator(mode="after")
    def _validate_patch_indices(self) -> Self:
        """Ensures that patch_indices correspond to valid Patch.state_index values."""
        valid_state_indices = {patch.state_index for patch in self.patches}
        invalid = [index for index in self.patch_indices if index not in valid_state_indices]
        if invalid:
            raise ValueError(
                f"patch_indices {invalid} do not correspond to any patch.state_index "
                f"(available: {sorted(valid_state_indices)})."
            )
        return self


Environment = TypeAliasType(
    "Environment",
    Annotated[
        Union[MarkovEnvironment, SequenceEnvironment],
        Field(discriminator="environment_type"),
    ],
)


# ==================== OP CONTROL SPECIFICATIONS ====================


class PositionControl(BaseModel):
    """
    Controls the position tracking and movement detection parameters.

    This class manages the position control system including coordinate transformations,
    initial positioning, signal filtering, and movement detection thresholds for the
    virtual reality foraging task.
    """

    gain: Vector3 = Field(default=Vector3(x=1, y=1, z=1), description="Gain of the position control.")
    initial_position: Vector3 = Field(
        default=Vector3(x=0, y=2.56, z=0), description="Initial position of the subject in the VR world."
    )
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
    """
    Controls audio feedback parameters for the task.

    This class manages audio cue generation including tone duration and frequency
    for auditory feedback during the behavioral task.
    """

    duration: float = Field(default=0.2, ge=0, description="Duration")
    frequency: float = Field(default=9999, ge=100, le=9999, description="Frequency (Hz) of the audio cue")


class OdorControl(BaseModel):
    """
    Controls the odor delivery system parameters.

    This class manages the olfactory stimulus delivery system, including flow rates,
    valve timing, and carrier gas configuration. It ensures proper odor concentration
    and delivery timing for the behavioral task.
    """

    target_total_flow: int = Field(
        default=1000, ge=100, le=1000, description="Target total flow (ml/s) of the odor mixture"
    )
    target_odor_flow: int = Field(default=100, ge=0, le=100, description="Target odor flow (ml/s) in the odor mixture")


class OperationControl(BaseModel):
    """
    Master control class for all operational hardware systems.

    This class aggregates all the hardware control specifications including
    odor delivery, position tracking, and audio systems.
    It provides a centralized configuration point for all task hardware.
    """

    odor_control: OdorControl = Field(
        default=OdorControl(target_odor_flow=100, target_total_flow=1000),
        description="Control of the odor",
        validate_default=True,
    )
    position_control: PositionControl = Field(
        default=PositionControl(), description="Control of the position", validate_default=True
    )
    audio_control: AudioControl = Field(
        default=AudioControl(), description="Control of the audio", validate_default=True
    )
    wait_to_start_duration: float = Field(default=0, ge=0, description="Duration to wait before starting the task")
    wait_to_finish_duration: float = Field(default=0, ge=0, description="Duration to wait after finishing the task")


# ==================== BLOCK END CONDITIONS ====================


class _BlockEndConditionBase(BaseModel):
    """
    Base class for block end conditions.

    This is an internal base class that defines the common interface for all
    block end condition types. Should not be instantiated directly.
    """

    condition_type: str


class BlockEndConditionDuration(_BlockEndConditionBase):
    """
    Block end condition based on time duration.

    This condition ends a block after a specified amount of time has elapsed.
    """

    condition_type: Literal["Duration"] = "Duration"
    value: distributions.Distribution = Field(description="Time after which the block ends.")


class BlockEndConditionDistance(_BlockEndConditionBase):
    """
    Block end condition based on distance traveled.

    This condition ends a block after the animal has traveled a specified distance.
    """

    condition_type: Literal["Distance"] = "Distance"
    value: distributions.Distribution = Field(description="Distance after which the block ends.")


class BlockEndConditionChoice(_BlockEndConditionBase):
    """
    Block end condition based on number of choices made.

    This condition ends a block after the animal has made a specified number
    of choices (e.g., patch visits or reward attempts).
    """

    condition_type: Literal["Choice"] = "Choice"
    value: distributions.Distribution = Field(description="Number of choices after which the block ends.")


class BlockEndConditionReward(_BlockEndConditionBase):
    """
    Block end condition based on number of rewards obtained.

    This condition ends a block after the animal has obtained a specified
    number of rewards.
    """

    condition_type: Literal["Reward"] = "Reward"
    value: distributions.Distribution = Field(description="Number of rewards after which the block ends.")


class BlockEndConditionPatchCount(_BlockEndConditionBase):
    """
    Block end condition based on number of patches visited.

    This condition ends a block after the animal has visited a specified
    number of unique patches.
    """

    condition_type: Literal["PatchCount"] = "PatchCount"
    value: distributions.Distribution = Field(description="Number of patches after which the block will end.")


if TYPE_CHECKING:
    BlockEndCondition = Union[
        BlockEndConditionDuration,
        BlockEndConditionDistance,
        BlockEndConditionChoice,
        BlockEndConditionReward,
        BlockEndConditionPatchCount,
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
    """
    Configuration for a single experimental block.

    A block represents a period of the experiment with specific environment
    statistics and ending conditions. Each block defines the environmental
    parameters and termination criteria for that experimental phase.
    """

    environment: Environment = Field(
        default=MarkovEnvironment(), description="Statistics of the environment", validate_default=True
    )
    end_conditions: List[BlockEndCondition] = Field(
        default=[], description="List of end conditions that must be true for the block to end."
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_environment(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        # Remap old field name "environment_statistics" -> "environment"
        if "environment_statistics" in data and "environment" not in data:
            data = dict(data)
            data["environment"] = data.pop("environment_statistics")
            logger.warning("Deprecated field 'environment_statistics' found in Block. Remapping to 'environment'.")
        # Inject discriminator when missing (old EnvironmentStatistics = MarkovEnvironment)
        env = data.get("environment")
        if isinstance(env, dict) and "environment_type" not in env:
            data = dict(data)
            data["environment"] = dict(env, environment_type="Markov")
            logger.warning(
                "Field 'environment_type' missing in environment dict. Defaulting to 'Markov' for backwards compatibility."
            )
        return data


class BlockStructure(BaseModel):
    """
    Structure defining the sequence and sampling of experimental blocks.

    This class manages multiple experimental blocks and determines how they
    are presented during the experiment (sequentially or randomly).
    """

    blocks: List[Block] = Field(
        default=[Block()], description="Statistics of the environment", min_length=1, validate_default=True
    )
    sampling_mode: Literal["Random", "Sequential"] = Field(
        default="Sequential", description="Sampling mode of the blocks."
    )


# ==================== MAIN TASK LOGIC CLASSES ====================


class AindVrForagingTaskParameters(TaskParameters):
    """
    Complete parameter specification for the AIND VR Foraging task.

    This class contains all configurable parameters for the VR foraging task,
    including environment structure, task mode settings, operation control,
    and numerical updaters for dynamic parameter modification.
    """

    updaters: Dict[UpdaterTarget, NumericalUpdater] = Field(
        default_factory=dict, description="Look-up table for numeric updaters"
    )
    environment: BlockStructure = Field(
        default=BlockStructure(), description="Statistics of the environment", validate_default=True
    )
    operation_control: OperationControl = Field(
        default=OperationControl(), description="Control of the operation", validate_default=True
    )


class AindVrForagingTaskLogic(Task):
    """
    Main task logic model for the AIND VR Foraging task.

    This is the top-level class that encapsulates the complete task logic
    specification for the virtual reality foraging behavioral experiment.
    It includes all task parameters, environment specifications, and control settings.
    """

    version: Literal[__semver__] = __semver__
    name: Literal["AindVrForaging"] = Field(default="AindVrForaging", description="Name of the task logic", frozen=True)
    task_parameters: AindVrForagingTaskParameters = Field(
        default=AindVrForagingTaskParameters(), description="Parameters of the task logic", validate_default=True
    )
