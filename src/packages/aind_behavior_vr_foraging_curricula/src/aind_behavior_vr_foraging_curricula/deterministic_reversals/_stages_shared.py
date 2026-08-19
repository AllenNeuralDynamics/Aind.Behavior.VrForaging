import dataclasses
from typing import Literal, Optional

import numpy as np
from aind_behavior_curriculum import MetricsProvider, Stage
from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from ..depletion import helpers
from ..depletion.metrics import metrics_from_dataset


@dataclasses.dataclass(frozen=True)
class DelaySpec:
    """How long reward delivery is withheld after the animal commits to a choice.

    The FAMILY matters behaviourally, not just the mean: an exponential delay is memoryless, so
    the animal cannot time its wait, whereas a tight normal is nearly deterministic and can be
    anticipated. That is why the delay lives here rather than in a generator flag -- swapping
    families is a change of task, not a retune.
    """

    family: Literal["exponential", "normal"] = "exponential"
    mean: float = 0.5
    std: float = 0.15
    """Only used when ``family="normal"``."""
    minimum: float = 0.0
    maximum: float = 1.0

    def build(self) -> distributions.Distribution:
        """Construct a fresh distribution instance (never share one across patches)."""
        if self.family == "normal":
            return helpers.make_normal_distribution(
                mean=self.mean,
                standard_deviation=self.std,
                minimum=self.minimum,
                maximum=self.maximum,
            )
        return helpers.make_exponential_distribution(rate=1 / self.mean, minimum=self.minimum, maximum=self.maximum)


@dataclasses.dataclass(frozen=True)
class CorridorGeometry:
    """Lengths, in cm, of the virtual corridor a patch is embedded in."""

    rewardsite: float = 50
    interpatch_min: float = 100
    interpatch_max: float = 250
    intersite_min: float = 20
    intersite_max: float = 80


#: Corridor and delay used by the on-curriculum stages.
GRADUATION_GEOMETRY = CorridorGeometry()
GRADUATION_DELAY = DelaySpec()
GRADUATION_STOP_DURATION = 0.5

#: The task the batch-8 reversal cohort actually runs. It differs from graduation in exactly
#: three deliberate ways -- a longer inter-patch corridor, a doubled stop requirement, and a
#: predictable (normal) reward delay -- chosen to slow the animals down and make the delayed
#: contingency timeable. Every other parameter is inherited, so the two stages cannot drift
#: apart in any respect nobody chose.
REVERSAL_GEOMETRY = CorridorGeometry(interpatch_min=150, interpatch_max=400)
REVERSAL_DELAY = DelaySpec(family="normal", mean=0.5, std=0.15)
REVERSAL_STOP_DURATION = 1.0


def deterministic_curves(
    amount_drop: float = 5.0,
    option: Optional[Literal["single", "delayed"]] = "single",
    *,
    cap_delayed_rewards: bool = False,
) -> list[task_logic.RewardFunction]:
    if option == "delayed":
        lut_values = [0.5, 1, 1, 1, 0]
        probability = task_logic.LookupTableFunction(
            lut_keys=list(np.arange(len(lut_values)) + 1), lut_values=lut_values
        )
        reward_function_prob = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        )
        if cap_delayed_rewards:
            reward_available = amount_drop * 3
            available = task_logic.ClampedRateFunction(
                rate=task_logic.scalar_value(-amount_drop), minimum=0, maximum=reward_available
            )
            reward_function_avail = task_logic.PatchRewardFunction(
                available=available,
                rule=task_logic.RewardFunctionRule.ON_REWARD,
            )
            reset_function = task_logic.OnThisPatchEntryRewardFunction(
                probability=task_logic.SetValueFunction(value=task_logic.scalar_value(1)),
                available=task_logic.SetValueFunction(value=task_logic.scalar_value(reward_available)),
            )
            return [reward_function_prob, reward_function_avail, reset_function]
        else:
            reward_available = 100
            reset_function = task_logic.OnThisPatchEntryRewardFunction(
                probability=task_logic.SetValueFunction(value=task_logic.scalar_value(1)),
                available=task_logic.SetValueFunction(value=task_logic.scalar_value(reward_available)),
            )
            return [reward_function_prob, reset_function]

    elif option == "single":
        lut_values = [1, 0]
        probability = task_logic.LookupTableFunction(lut_keys=[1, 2], lut_values=lut_values)
        reward_function = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE_ACCUMULATED,
        )
        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(1)),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(100)),
        )
        return [reward_function, reset_function]

    elif option is None:
        probability = task_logic.SetValueFunction(value=task_logic.scalar_value(0))
        reward_function = task_logic.PatchRewardFunction(
            probability=probability,
            rule=task_logic.RewardFunctionRule.ON_CHOICE,
        )
        reset_function = task_logic.OnThisPatchEntryRewardFunction(
            probability=task_logic.SetValueFunction(value=task_logic.scalar_value(0)),
            available=task_logic.SetValueFunction(value=task_logic.scalar_value(0)),
        )
        return [reward_function, reset_function]

    else:
        raise ValueError(f"Option {option} not recognized. Valid options are 'single', 'delayed', and None.")


def make_patch(
    label: str,
    state_index: int,
    odor_index: list[float],
    patch_type: Optional[Literal["single", "delayed"]],
    reward_amount: float = 5.0,
    first_p: float = 0.5,
    reward_available: float = 9999,
    stop_duration: float = GRADUATION_STOP_DURATION,
    delay: Optional[DelaySpec] = None,
    geometry: Optional[CorridorGeometry] = None,
    cap_delayed_rewards: bool = False,
) -> task_logic.Patch:
    delay = delay if delay is not None else GRADUATION_DELAY
    geometry = geometry if geometry is not None else GRADUATION_GEOMETRY
    agent = task_logic.RewardSpecification(
        operant_logic=helpers.make_operant_logic(stop_duration=stop_duration, is_operant=False),
        delay=delay.build(),
        amount=task_logic.scalar_value(value=reward_amount),
        probability=task_logic.scalar_value(first_p),
        available=task_logic.scalar_value(reward_available),
        reward_function=deterministic_curves(
            amount_drop=reward_amount, option=patch_type, cap_delayed_rewards=cap_delayed_rewards
        ),
    )
    return task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=odor_index,
        reward_specification=agent,
        patch_virtual_sites_generator=helpers.make_patch_virtual_sites_generator(
            rewardsite=geometry.rewardsite,
            interpatch_min=geometry.interpatch_min,
            interpatch_max=geometry.interpatch_max,
            intersite_min=geometry.intersite_min,
            intersite_max=geometry.intersite_max,
        ),
    )


def make_s_stage_all_odors_rewarded(
    delayed_reward_available: float = 100,
    cap_delayed_rewards: bool = False,
) -> Stage:
    return Stage(
        name="all_odors_rewarded",
        task=AindVrForagingTaskLogic(
            stage_name="all_odors_rewarded",
            task_parameters=AindVrForagingTaskParameters(
                operation_control=helpers.make_default_operation_control(velocity_threshold=8),
                environment=task_logic.BlockStructure(
                    blocks=[
                        task_logic.Block(
                            environment=task_logic.MarkovEnvironment(
                                first_state_occupancy=[0.5, 0.5],
                                transition_matrix=[[0.5, 0.5], [0.5, 0.5]],
                                patches=[
                                    make_patch(
                                        label="patch_single",
                                        state_index=0,
                                        odor_index=[0, 0, 1],
                                        patch_type="single",
                                        reward_amount=5.0,
                                        first_p=1,
                                        reward_available=100,
                                        cap_delayed_rewards=cap_delayed_rewards,
                                    ),
                                    make_patch(
                                        label="patch_delayed",
                                        state_index=1,
                                        odor_index=[0, 1, 0],
                                        patch_type="delayed",
                                        reward_amount=5.0,
                                        first_p=0.5,
                                        reward_available=delayed_reward_available,
                                        cap_delayed_rewards=cap_delayed_rewards,
                                    ),
                                ],
                            ),
                            end_conditions=[],
                        )
                    ],
                ),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def _make_three_patch_stage(
    name: str,
    *,
    stop_duration: float,
    delay: DelaySpec,
    geometry: CorridorGeometry,
    delayed_reward_available: float,
    cap_delayed_rewards: bool,
) -> Stage:
    """Build the three-contingency stage (null / delayed / single) shared by the reversal task.

    ``graduation`` and ``reversal_baseline`` differ ONLY in the keyword arguments above, so a
    change to the contingency structure necessarily lands on both.
    """
    return Stage(
        name=name,
        task=AindVrForagingTaskLogic(
            stage_name=name,
            task_parameters=AindVrForagingTaskParameters(
                operation_control=helpers.make_default_operation_control(velocity_threshold=8),
                environment=task_logic.BlockStructure(
                    blocks=[
                        task_logic.Block(
                            environment=task_logic.MarkovEnvironment(
                                first_state_occupancy=[1 / 3, 1 / 3, 1 / 3],
                                transition_matrix=[
                                    [1 / 3, 1 / 3, 1 / 3],
                                    [1 / 3, 1 / 3, 1 / 3],
                                    [1 / 3, 1 / 3, 1 / 3],
                                ],
                                patches=[
                                    make_patch(
                                        label="patch_null",
                                        state_index=0,
                                        odor_index=[1, 0, 0],
                                        patch_type=None,
                                        reward_amount=0.0,
                                        first_p=0,
                                        reward_available=0,
                                        stop_duration=stop_duration,
                                        delay=delay,
                                        geometry=geometry,
                                        cap_delayed_rewards=cap_delayed_rewards,
                                    ),
                                    make_patch(
                                        label="patch_delayed",
                                        state_index=1,
                                        odor_index=[0, 1, 0],
                                        patch_type="delayed",
                                        reward_amount=5.0,
                                        first_p=0.5,
                                        reward_available=delayed_reward_available,
                                        stop_duration=stop_duration,
                                        delay=delay,
                                        geometry=geometry,
                                        cap_delayed_rewards=cap_delayed_rewards,
                                    ),
                                    make_patch(
                                        label="patch_single",
                                        state_index=2,
                                        odor_index=[0, 0, 1],
                                        patch_type="single",
                                        reward_amount=5.0,
                                        first_p=1,
                                        reward_available=100,
                                        stop_duration=stop_duration,
                                        delay=delay,
                                        geometry=geometry,
                                        cap_delayed_rewards=cap_delayed_rewards,
                                    ),
                                ],
                            ),
                            end_conditions=[],
                        )
                    ],
                ),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_stage_graduation(
    delayed_reward_available: float = 100,
    cap_delayed_rewards: bool = False,
) -> Stage:
    """Terminal on-curriculum stage: all three contingencies, curriculum geometry."""
    return _make_three_patch_stage(
        "graduation",
        stop_duration=GRADUATION_STOP_DURATION,
        delay=GRADUATION_DELAY,
        geometry=GRADUATION_GEOMETRY,
        delayed_reward_available=delayed_reward_available,
        cap_delayed_rewards=cap_delayed_rewards,
    )


def make_s_stage_reversal_baseline(
    delayed_reward_available: float = 100,
    cap_delayed_rewards: bool = False,
) -> Stage:
    """``graduation`` adjusted for the reversal cohort -- longer corridor, longer stop, normal delay.

    Not wired into the curriculum graph: reversal sessions are generated off-curriculum by
    ``examples/task_reversal.py``, which selects this stage with ``--baseline reversal``. It lives
    here so the task the animals actually run is a versioned, reviewable object rather than a set
    of flags that must be retyped identically every day.
    """
    return _make_three_patch_stage(
        "reversal_baseline",
        stop_duration=REVERSAL_STOP_DURATION,
        delay=REVERSAL_DELAY,
        geometry=REVERSAL_GEOMETRY,
        delayed_reward_available=delayed_reward_available,
        cap_delayed_rewards=cap_delayed_rewards,
    )
