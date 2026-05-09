from typing import Callable

import aind_behavior_services.task.distributions as distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from . import helpers
from .metrics import SingleSiteMatchingMetrics

# ============================================================
# Policies to update task parameters based on metrics
# ============================================================

# Useful type hints for generic policies
PolicyType = Callable[
    [SingleSiteMatchingMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting


def p_learn_to_stop(metrics: SingleSiteMatchingMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    assert metrics.last_stop_threshold_updater is not None
    task.task_parameters.updaters[
        task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD
    ].parameters.initial_value = helpers.clamp(
        metrics.last_stop_threshold_updater * 1.2,  # make it easier than last stop
        minimum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.minimum,
        maximum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD].parameters.maximum,
    )
    assert metrics.last_stop_duration_offset_updater is not None

    task.task_parameters.updaters[
        task_logic.UpdaterTarget.STOP_DURATION_OFFSET
    ].parameters.initial_value = helpers.clamp(
        metrics.last_stop_duration_offset_updater * 0.8,  # make it easier than last stop
        minimum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.minimum,
        maximum=task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_DURATION_OFFSET].parameters.maximum,
    )

    return task


# Graduated-stage target sizes (from make_s_graduated_stage)
_ENV_GROW_TARGETS = {
    "inter_patch_min_length": 30.0,
    "inter_patch_mean_length": 60.0,
    "inter_patch_max_length": 190.0,
    "reward_site_length": 50.0,
}

# Per-session multiplicative gains: (target / start) ^ (1/4) for a ~4-session ramp
# inter_patch_min:  (30/25)^0.25  ≈ 1.0466
# inter_patch_mean: (60/40)^0.25  ≈ 1.1067
# inter_patch_max:  (190/75)^0.25 ≈ 1.2618
# reward_site:      (50/40)^0.25  ≈ 1.0574
_ENV_GROW_GAINS = {
    "inter_patch_min_length": 1.0466,
    "inter_patch_mean_length": 1.1067,
    "inter_patch_max_length": 1.2618,
    "reward_site_length": 1.0574,
}

_ENV_GROW_MIN_PATCHES_VISITED = 100


def p_grow_environment(metrics: SingleSiteMatchingMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Progressively grow environment geometry toward the graduated-stage target.

    The update is conditional on the animal having visited at least
    ``_ENV_GROW_MIN_PATCHES_VISITED`` patches in the previous session.
    Sizes increase multiplicatively each qualifying session, reaching the
    graduated-stage target values in approximately 4 sessions.
    """
    if metrics.n_patches_visited < _ENV_GROW_MIN_PATCHES_VISITED:
        return task

    for block in task.task_parameters.environment.blocks:
        for patch in block.environment_statistics.patches:
            gen = patch.patch_virtual_sites_generator

            # --- inter-patch geometry (ExponentialDistribution) ---
            inter_patch_dist = gen.inter_patch.length_distribution
            assert isinstance(inter_patch_dist, distributions.ExponentialDistribution)

            # inter_patch_min_length (stored as both offset and truncation min)
            assert inter_patch_dist.truncation_parameters is not None
            assert inter_patch_dist.scaling_parameters is not None
            current_min = inter_patch_dist.truncation_parameters.min
            new_min = helpers.clamp(
                current_min * _ENV_GROW_GAINS["inter_patch_min_length"],
                minimum=current_min,
                maximum=_ENV_GROW_TARGETS["inter_patch_min_length"],
            )
            inter_patch_dist.scaling_parameters.offset = new_min
            inter_patch_dist.truncation_parameters.min = new_min

            # inter_patch_mean_length (stored as 1/rate)
            current_mean = 1.0 / inter_patch_dist.distribution_parameters.rate
            new_mean = helpers.clamp(
                current_mean * _ENV_GROW_GAINS["inter_patch_mean_length"],
                minimum=current_mean,
                maximum=_ENV_GROW_TARGETS["inter_patch_mean_length"],
            )
            inter_patch_dist.distribution_parameters.rate = 1.0 / new_mean

            # inter_patch_max_length
            current_max = inter_patch_dist.truncation_parameters.max
            new_max = helpers.clamp(
                current_max * _ENV_GROW_GAINS["inter_patch_max_length"],
                minimum=current_max,
                maximum=_ENV_GROW_TARGETS["inter_patch_max_length"],
            )
            inter_patch_dist.truncation_parameters.max = new_max

            # --- reward-site length (Scalar distribution) ---
            reward_site_dist = gen.reward_site.length_distribution
            assert isinstance(reward_site_dist, distributions.Scalar)

            current_rsl = reward_site_dist.distribution_parameters.value
            new_rsl = helpers.clamp(
                current_rsl * _ENV_GROW_GAINS["reward_site_length"],
                minimum=current_rsl,
                maximum=_ENV_GROW_TARGETS["reward_site_length"],
            )
            reward_site_dist.distribution_parameters.value = new_rsl

    return task


# ---------------------------------------------------------------------------
# p_drop_reward_probability
# ---------------------------------------------------------------------------
# Drops p_reward on both odors from 1.0 → 0.5 over ~4 qualifying sessions.
# The per-session step scales linearly with water consumed (in mL):
#   < 700 µL (0.7 mL)  → no update
#   700 µL – 1000 µL   → step scales linearly from 0 to full step
#   ≥ 1000 µL (1.0 mL) → full step = (1.0 - 0.5) / 4 = 0.125
# ---------------------------------------------------------------------------

_P_REW_DROP_WATER_MIN_ML = 0.7  # 700 µL threshold – no update below this
_P_REW_DROP_WATER_MAX_ML = 1.0  # 1000 µL – full step at this value (clamped above)
_P_REW_DROP_START = 1.0
_P_REW_DROP_TARGET = 0.6
_P_REW_DROP_N_DAYS = 4
_P_REW_DROP_FULL_STEP = (_P_REW_DROP_START - _P_REW_DROP_TARGET) / _P_REW_DROP_N_DAYS  # 0.1


def p_drop_reward_probability(
    metrics: SingleSiteMatchingMetrics, task: AindVrForagingTaskLogic
) -> AindVrForagingTaskLogic:
    """Scale down p_reward toward 0.5 proportional to water consumed.

    Below 700 µL the update is skipped entirely. Between 700 µL and 1000 µL
    the step size grows linearly; above 1000 µL it is clamped to the full step
    of ``(1.0 - 0.5) / 4 = 0.125``.  After ~4 sessions where the animal
    drinks ≥ 1000 µL the probability reaches the target of 0.5.
    """
    if metrics.total_water_consumed < _P_REW_DROP_WATER_MIN_ML:
        return task

    water_fraction = helpers.clamp(
        (metrics.total_water_consumed - _P_REW_DROP_WATER_MIN_ML)
        / (_P_REW_DROP_WATER_MAX_ML - _P_REW_DROP_WATER_MIN_ML),
        minimum=0.0,
        maximum=1.0,
    )
    step = water_fraction * _P_REW_DROP_FULL_STEP

    for block in task.task_parameters.environment.blocks:
        for patch in block.environment_statistics.patches:
            # --- reward_specification.probability (Scalar) ---
            assert isinstance(patch.reward_specification.probability, distributions.Scalar)
            current_p = patch.reward_specification.probability.distribution_parameters.value
            new_p = helpers.clamp(current_p - step, minimum=_P_REW_DROP_TARGET, maximum=_P_REW_DROP_START)
            patch.reward_specification.probability.distribution_parameters.value = new_p

            # --- per-reward-function updates ---
            for rf in patch.reward_specification.reward_function:
                if isinstance(rf, task_logic.PatchRewardFunction):
                    # depletion function: SetValueFunction(Scalar)
                    assert isinstance(rf.probability, task_logic.SetValueFunction)
                    assert isinstance(rf.probability.value, distributions.Scalar)
                    rf.probability.value.distribution_parameters.value = new_p

                elif isinstance(rf, task_logic.PersistentRewardFunction):
                    # baiting function: SetValueFunction(BinomialDistribution)
                    # p_reward is stored as BinomialDistribution offset and truncation min
                    assert isinstance(rf.probability, task_logic.SetValueFunction)
                    assert isinstance(rf.probability.value, distributions.BinomialDistribution)
                    binom = rf.probability.value
                    assert binom.scaling_parameters is not None
                    assert binom.truncation_parameters is not None
                    binom.scaling_parameters.offset = new_p
                    binom.truncation_parameters.min = new_p

    return task
