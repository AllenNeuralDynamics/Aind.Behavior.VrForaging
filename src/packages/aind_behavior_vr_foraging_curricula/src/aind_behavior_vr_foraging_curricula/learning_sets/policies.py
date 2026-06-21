from typing import Callable

from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from . import helpers
from .metrics import LearningSetsMetrics

PolicyType = Callable[[LearningSetsMetrics, AindVrForagingTaskLogic], AindVrForagingTaskLogic]


def _iter_patches(task: AindVrForagingTaskLogic):
    for block in task.task_parameters.environment.blocks:
        for patch in block.environment.patches:
            yield patch


def p_introduce_negative_sites(
    metrics: LearningSetsMetrics, task: AindVrForagingTaskLogic
) -> AindVrForagingTaskLogic:
    """Progress the negative-site proportion according to ``N_NEG_RAMP`` and regenerate
    the session sequence.

    Session 1 (no prior metrics): n_neg_each = 0 — all sites are rewarded.
    Subsequent sessions: walk 0 → 1 → 3 → 5 using ``N_NEG_RAMP``, then stay at 5.
    Total sites per pair is always ``N_SITES_EACH * 2``; positive sites fill the
    remainder.  The ramp is read from ``last_n_neg_sites_per_pair``; None means
    session 1 (pre-ramp).
    """
    prior = metrics.last_n_neg_sites_per_pair
    if prior is None:
        n_neg_each = 0
    else:
        ramp = helpers.N_NEG_RAMP
        # Advance to the next step in the ramp, or stay at the last step
        idx = next((i for i, v in enumerate(ramp) if v > prior), len(ramp) - 1)
        n_neg_each = ramp[idx]

    n_pos_each = helpers.N_SITES_EACH * 2 - n_neg_each
    for block in task.task_parameters.environment.blocks:
        environment = block.environment
        if isinstance(environment, task_logic.SequenceEnvironment):
            environment.patch_indices = helpers.make_sequence(
                n_pos_each=n_pos_each, n_neg_each=n_neg_each
            )
        else:
            raise ValueError(f"Unexpected environment type {type(environment)}")
    return task


def p_seed_stop_duration(metrics: LearningSetsMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Seed this session's stop-duration offset from the prior session's end value,
    eased down (``STOP_DURATION_LEARNING_FACTOR``) so the subject re-ramps from a little
    below the longest stop it reached rather than starting at the top."""
    if metrics.last_stop_duration_offset_updater is None:
        return task
    updater = task.task_parameters.updaters.get(task_logic.UpdaterTarget.STOP_DURATION_OFFSET, None)
    if updater is None:
        return task
    updater.parameters.initial_value = helpers.clamp(
        metrics.last_stop_duration_offset_updater * helpers.STOP_DURATION_LEARNING_FACTOR,
        minimum=updater.parameters.minimum,
        maximum=updater.parameters.maximum,
    )
    return task


def p_seed_stop_velocity(metrics: LearningSetsMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Seed this session's stop-velocity threshold from the prior session's floored
    value, eased up slightly (``STOP_VELOCITY_LEARNING_FACTOR``) so the subject does not
    start straight at the floor. Once the threshold has asymptoted at the floor this is
    effectively a no-op, so the policy can simply be dropped from later stages."""
    if metrics.last_stop_velocity_threshold_updater is None:
        return task
    updater = task.task_parameters.updaters.get(task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD, None)
    if updater is None:
        return task
    updater.parameters.initial_value = helpers.clamp(
        metrics.last_stop_velocity_threshold_updater * helpers.STOP_VELOCITY_LEARNING_FACTOR,
        minimum=updater.parameters.minimum,
        maximum=updater.parameters.maximum,
    )
    return task


def p_ease_geometry(metrics: LearningSetsMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Ease the corridor geometry from the compressed (day-1, easy) values toward full
    spacing, scaled by how many sites the subject travelled in the prior session
    (``n_patches_seen / GEOMETRY_EASE_SITES``, clamped to 1). On the first session (no
    prior metrics) the geometry stays compressed. Inter-site spacing is left fixed."""
    fraction = helpers.clamp(metrics.n_patches_seen / helpers.GEOMETRY_EASE_SITES, 0.0, 1.0)
    compressed, full = helpers.GEOMETRY_COMPRESSED, helpers.GEOMETRY_FULL
    inter_patch_min = helpers.lerp(compressed.inter_patch_min_length, full.inter_patch_min_length, fraction)
    inter_patch_mean = helpers.lerp(compressed.inter_patch_mean_length, full.inter_patch_mean_length, fraction)
    inter_patch_max = helpers.lerp(compressed.inter_patch_max_length, full.inter_patch_max_length, fraction)
    reward_site_length = helpers.lerp(compressed.reward_site_length, full.reward_site_length, fraction)
    for patch in _iter_patches(task):
        generator = patch.patch_virtual_sites_generator
        inter_patch_distribution = generator.inter_patch.length_distribution
        if isinstance(inter_patch_distribution, distributions.ExponentialDistribution):
            inter_patch_distribution.distribution_parameters.rate = 1.0 / inter_patch_mean
            if inter_patch_distribution.scaling_parameters is not None:
                inter_patch_distribution.scaling_parameters.offset = inter_patch_min
            if inter_patch_distribution.truncation_parameters is not None:
                inter_patch_distribution.truncation_parameters.min = inter_patch_min
                inter_patch_distribution.truncation_parameters.max = inter_patch_max
        generator.reward_site.length_distribution.distribution_parameters.value = reward_site_length
    return task


def p_water_cap(metrics: LearningSetsMetrics, task: AindVrForagingTaskLogic) -> AindVrForagingTaskLogic:
    """Steer reward volume toward the target water window ``[WATER_FLOOR_ML, WATER_CAP_ML]``.
    Trims by ``REWARD_AMOUNT_STEP_UL`` when the prior session exceeded the cap; raises by
    the same step when it fell below the floor. Both directions are clamped to
    ``[REWARD_AMOUNT_UL_MIN, REWARD_AMOUNT_UL_MAX]``."""
    amount = metrics.last_reward_amount if metrics.last_reward_amount is not None else helpers.REWARD_AMOUNT_UL_DEFAULT
    if metrics.total_water_consumed > helpers.WATER_CAP_ML:
        amount = amount - helpers.REWARD_AMOUNT_STEP_UL
    elif metrics.total_water_consumed < helpers.WATER_FLOOR_ML:
        amount = amount + helpers.REWARD_AMOUNT_STEP_UL
    amount = helpers.clamp(amount, helpers.REWARD_AMOUNT_UL_MIN, helpers.REWARD_AMOUNT_UL_MAX)
    for patch in _iter_patches(task):
        patch.reward_specification.amount = task_logic.scalar_value(amount)
    return task
