from typing import Callable

from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from . import helpers
from .metrics import SingleSiteMetrics

# ============================================================
# learn_to_stop geometry easing
# ============================================================
# learn_to_stop starts compressed (reward sites close together -> dense stop
# practice in the motivated early window) and eases toward full spacing across
# sessions, scaled by prior locomotion (n_patches_seen). Reaches full geometry
# once the subject has traversed GEOMETRY_EASE_PATCHES patches in a session.
GEOMETRY_EASE_PATCHES: float = 150.0
LEARN_TO_STOP_GEOMETRY_COMPRESSED: dict[str, float] = {
    "inter_patch_min_length": 25.0,
    "inter_patch_mean_length": 50.0,
    "inter_patch_max_length": 90.0,
    "inter_site_length": 10.0,
    "reward_site_length": 25.0,
}
LEARN_TO_STOP_GEOMETRY_FULL: dict[str, float] = {
    "inter_patch_min_length": 50.0,
    "inter_patch_mean_length": 120.0,
    "inter_patch_max_length": 150.0,
    "inter_site_length": 15.0,
    "reward_site_length": 40.0,
}

# ============================================================
# learn_to_stop reward-probability water gate
# ============================================================
# Cross-session: keep p_reward = 1.0 while the subject is struggling (prior-session
# water below the gate) so it still earns water; once it reliably earns water, drop
# to GATED_REWARD_PROBABILITY to introduce mild probabilistic reward.
WATER_GATE_ML: float = 0.6
GATED_REWARD_PROBABILITY: float = 0.8

# ============================================================
# Cross-session seeding factors
# ============================================================
# An updater's prior-session end value is eased before re-use as the next session's
# starting point, so the subject does not face a cliff between days.
STOP_THRESHOLD_EASE_FACTOR: float = 1.2  # start a bit looser than where velocity floored
REWARD_DELAY_SEED_FACTOR: float = 0.8  # re-ramp the reward delay a shorter distance

#: Signature shared by every policy in this module.
PolicyType = Callable[[SingleSiteMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic]


def p_learn_to_stop(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Seed the next session's stop-velocity threshold from the prior session's end
    value, eased slightly (STOP_THRESHOLD_EASE_FACTOR) so the subject is not dropped
    straight at the floor. Stop duration is fixed (no offset updater), so only the
    velocity threshold is seeded."""
    if metrics.last_stop_threshold_updater is None:
        return task
    updater = task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD]
    updater.parameters.initial_value = helpers.clamp(
        metrics.last_stop_threshold_updater * STOP_THRESHOLD_EASE_FACTOR,
        minimum=updater.parameters.minimum,
        maximum=updater.parameters.maximum,
    )
    return task


def p_reward_water_gate(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Cross-session reward-probability gate. If the subject earned at least
    WATER_GATE_ML in the prior session, set reward probability to
    GATED_REWARD_PROBABILITY (introduce probabilistic reward); otherwise keep it at
    1.0 so a struggling subject still gets water at every stop."""
    p = GATED_REWARD_PROBABILITY if metrics.total_water_consumed >= WATER_GATE_ML else 1.0
    for block in task.task_parameters.environment.blocks:
        for patch in block.environment.patches:
            patch.reward_specification.probability = task_logic.scalar_value(p)
    return task


def p_learn_to_run(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Cross-session geometry easing. Interpolate inter-patch / inter-site /
    reward-site lengths from the compressed start toward full spacing, scaled by
    prior locomotion (n_patches_seen / GEOMETRY_EASE_PATCHES, clamped to 1). On the
    first session (no prior metrics) the geometry stays compressed."""
    ease_fraction = helpers.clamp(metrics.n_patches_seen / GEOMETRY_EASE_PATCHES, 0.0, 1.0)
    compressed, full = LEARN_TO_STOP_GEOMETRY_COMPRESSED, LEARN_TO_STOP_GEOMETRY_FULL
    inter_patch_min = helpers.lerp(compressed["inter_patch_min_length"], full["inter_patch_min_length"], ease_fraction)
    inter_patch_mean = helpers.lerp(
        compressed["inter_patch_mean_length"], full["inter_patch_mean_length"], ease_fraction
    )
    inter_patch_max = helpers.lerp(compressed["inter_patch_max_length"], full["inter_patch_max_length"], ease_fraction)
    inter_site_length = helpers.lerp(compressed["inter_site_length"], full["inter_site_length"], ease_fraction)
    reward_site_length = helpers.lerp(compressed["reward_site_length"], full["reward_site_length"], ease_fraction)
    for block in task.task_parameters.environment.blocks:
        for patch in block.environment.patches:
            patch_generator = patch.patch_virtual_sites_generator
            inter_patch_distribution = patch_generator.inter_patch.length_distribution
            if isinstance(inter_patch_distribution, distributions.ExponentialDistribution):
                inter_patch_distribution.distribution_parameters.rate = 1.0 / inter_patch_mean
                if inter_patch_distribution.scaling_parameters is not None:
                    inter_patch_distribution.scaling_parameters.offset = inter_patch_min
                if inter_patch_distribution.truncation_parameters is not None:
                    inter_patch_distribution.truncation_parameters.min = inter_patch_min
                    inter_patch_distribution.truncation_parameters.max = inter_patch_max
            else:
                raise ValueError(f"Unexpected inter-patch distribution type: {type(inter_patch_distribution)}")
            patch_generator.inter_site.length_distribution.distribution_parameters.value = inter_site_length
            patch_generator.reward_site.length_distribution.distribution_parameters.value = reward_site_length
    return task


def p_seed_reward_delay(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Ease the reward-delay offset in from where the previous session ended
    (REWARD_DELAY_SEED_FACTOR), so each session re-ramps a shorter distance rather
    than starting from zero."""
    if metrics.last_reward_delay_offset_updater is None:
        return task
    updater = task.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET]
    updater.parameters.initial_value = helpers.clamp(
        metrics.last_reward_delay_offset_updater * REWARD_DELAY_SEED_FACTOR,
        minimum=updater.parameters.minimum,
        maximum=updater.parameters.maximum,
    )
    return task
