from typing import Callable

import aind_behavior_services.task.distributions as distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from .metrics import SingleSiteMetrics


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _lerp(a: float, b: float, frac: float) -> float:
    return a + (b - a) * frac


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


# Useful type hints for generic policies
PolicyType = Callable[
    [SingleSiteMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic
]  # This should generally work for type hinting


def p_learn_to_stop(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Seed the next session's stop-velocity threshold from the prior session's end
    value, eased slightly (x1.2) so the subject is not dropped straight at the floor.
    Stop duration is now fixed (no offset updater), so only the velocity threshold is
    seeded."""
    if metrics.last_stop_threshold_updater is None:
        return task
    updater = task.task_parameters.updaters[task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD]
    updater.parameters.initial_value = _clamp(
        metrics.last_stop_threshold_updater * 1.2,
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
        for patch in block.environment_statistics.patches:
            patch.reward_specification.probability = task_logic.scalar_value(p)
    return task


def p_learn_to_run(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Cross-session geometry easing. Interpolate inter-patch / inter-site /
    reward-site lengths from the compressed start toward full spacing, scaled by
    prior locomotion (n_patches_seen / GEOMETRY_EASE_PATCHES, clamped to 1). On the
    first session (no prior metrics) the geometry stays compressed."""
    frac = _clamp(metrics.n_patches_seen / GEOMETRY_EASE_PATCHES, 0.0, 1.0)
    c, f = LEARN_TO_STOP_GEOMETRY_COMPRESSED, LEARN_TO_STOP_GEOMETRY_FULL
    ip_min = _lerp(c["inter_patch_min_length"], f["inter_patch_min_length"], frac)
    ip_mean = _lerp(c["inter_patch_mean_length"], f["inter_patch_mean_length"], frac)
    ip_max = _lerp(c["inter_patch_max_length"], f["inter_patch_max_length"], frac)
    is_len = _lerp(c["inter_site_length"], f["inter_site_length"], frac)
    rs_len = _lerp(c["reward_site_length"], f["reward_site_length"], frac)
    for block in task.task_parameters.environment.blocks:
        for patch in block.environment_statistics.patches:
            gen = patch.patch_virtual_sites_generator
            inter_patch = gen.inter_patch.length_distribution
            if isinstance(inter_patch, distributions.ExponentialDistribution):
                inter_patch.distribution_parameters.rate = 1.0 / ip_mean
                if inter_patch.scaling_parameters is not None:
                    inter_patch.scaling_parameters.offset = ip_min
                if inter_patch.truncation_parameters is not None:
                    inter_patch.truncation_parameters.min = ip_min
                    inter_patch.truncation_parameters.max = ip_max
            gen.inter_site.length_distribution.distribution_parameters.value = is_len
            gen.reward_site.length_distribution.distribution_parameters.value = rs_len
    return task


def p_seed_reward_delay(metrics: SingleSiteMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Ease the reward-delay offset in from where the previous session ended (x0.8),
    so each session re-ramps a shorter distance rather than starting from zero."""
    if metrics.last_reward_delay_offset_updater is None:
        return task
    updater = task.task_parameters.updaters[task_logic.UpdaterTarget.REWARD_DELAY_OFFSET]
    updater.parameters.initial_value = _clamp(
        metrics.last_reward_delay_offset_updater * 0.8,
        minimum=updater.parameters.minimum,
        maximum=updater.parameters.maximum,
    )
    return task
