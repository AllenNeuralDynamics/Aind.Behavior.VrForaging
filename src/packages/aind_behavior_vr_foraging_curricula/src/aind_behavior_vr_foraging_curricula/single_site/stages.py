from aind_behavior_curriculum import MetricsProvider, Policy, Stage
from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from . import helpers
from .metrics import metrics_from_dataset
from .policies import (
    LEARN_TO_STOP_GEOMETRY_COMPRESSED,
    p_learn_to_run,
    p_learn_to_stop,
    p_reward_water_gate,
    p_seed_reward_delay,
)

# ============================================================
# Probability-grid band
# ============================================================
# The probability_grid_* stages draw each block's (p_A, p_B) from this 5-value grid,
# keeping only pairs whose summed reward probability lands in the allowed band.
# Restricting to {0.8, 1.0, 1.2} holds the per-site offered rate in 0.38-0.57 (vs
# 0.19-0.86 for the full sum>=0.4 grid) while preserving relative contrast
# |p_A - p_B| up to 0.8. Yields 13 blocks. round() guards binary-float drift
# (e.g. 0.1 + 0.7 == 0.7999999999999999).
PROBABILITY_GRID_REWARD_PROBABILITIES: tuple[float, ...] = (0.10, 0.30, 0.50, 0.70, 0.90)
PROBABILITY_GRID_ALLOWED_SUMS: frozenset[float] = frozenset({0.8, 1.0, 1.2})

# Corridor geometry / stop shared by every stage after learn_to_stop (learn_to_choose
# and both probability_grid_* stages). The grid stages additionally set a stochastic
# `delay`; reward amount defaults to helpers.REWARD_AMOUNT_UL.
_POST_STOP_PATCH_KWARGS: dict[str, float] = {
    "inter_patch_min_length": 30,
    "inter_patch_mean_length": 60,
    "inter_patch_max_length": 190,
    "inter_site_length": 15,
    "reward_site_length": 50,
    "stop_duration": 1.0,
}


# ============================================================
# Stage definitions
# ============================================================


def _make_learn_to_stop_task() -> AindVrForagingTaskLogic:
    """Stage-1 task: teach a genuine stop within one session.

    Only the stop-velocity threshold is shaped, and quickly (GAIN on_success=0.93
    floors 60 -> 8 in ~28 rewarded stops) so the velocity slack closes early and
    most of the session is spent practicing real stops. Stop duration is held
    fixed at 1.0 s (no offset updater) to avoid the learn-low-then-fail-high trap.
    Geometry starts compressed (dense reward sites) and is eased toward full across
    sessions by p_learn_to_run; reward probability is gated by p_reward_water_gate.
    """
    return AindVrForagingTaskLogic(
        stage_name="learn_to_stop",
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=None,
            updaters={
                task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: task_logic.NumericalUpdater(
                    operation=task_logic.NumericalUpdaterOperation.GAIN,
                    parameters=task_logic.NumericalUpdaterParameters(
                        initial_value=60, on_success=0.93, minimum=8, maximum=60
                    ),
                ),
            },
            environment=task_logic.BlockStructure(
                blocks=[
                    helpers.make_block(
                        p_rewards=(1.0, 1.0, None),
                        n_min_patches=100000,  # one block per session (never ends within a session)
                        make_patch_kwargs={**LEARN_TO_STOP_GEOMETRY_COMPRESSED, "stop_duration": 1.0},
                    ),
                ],
                sampling_mode="Sequential",
            ),
            operation_control=helpers.make_default_operation_control(velocity_threshold=60),
        ),
    )


def make_s_learn_to_stop() -> Stage:
    return Stage(
        name="learn_to_stop",
        task=_make_learn_to_stop_task(),
        start_policies=[Policy(p_learn_to_stop), Policy(p_reward_water_gate), Policy(p_learn_to_run)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_learn_to_choose() -> Stage:
    """High-contrast discrimination stage. Two odors, alternating blocks with
    p_reward (0.9, 0.1) and (0.1, 0.9). REWARD_DELAY_OFFSET ramps 0 -> 0.3 s within
    session, carried forward across learn_to_choose sessions via p_seed_reward_delay.
    Stop duration is held fixed at 1.0 s (established in learn_to_stop)."""
    return Stage(
        name="learn_to_choose",
        task=AindVrForagingTaskLogic(
            stage_name="learn_to_choose",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: task_logic.NumericalUpdater(
                        operation=task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=0.002, minimum=0, maximum=0.3
                        ),
                    ),
                },
                environment=task_logic.BlockStructure(
                    blocks=[
                        helpers.make_block(
                            p_rewards=(0.9, 0.1, None),
                            n_min_patches=60,
                            block_length_exp_mean=15,
                            block_length_max=100,
                            make_patch_kwargs=_POST_STOP_PATCH_KWARGS,
                        ),
                        helpers.make_block(
                            p_rewards=(0.1, 0.9, None),
                            n_min_patches=60,
                            block_length_exp_mean=15,
                            block_length_max=100,
                            make_patch_kwargs=_POST_STOP_PATCH_KWARGS,
                        ),
                    ],
                    sampling_mode="Random",
                ),
                operation_control=helpers.make_default_operation_control(velocity_threshold=8),
            ),
        ),
        start_policies=[Policy(p_seed_reward_delay)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def _probability_grid_blocks(
    n_min_patches: int,
    block_length_exp_mean: float,
    block_length_max: float,
    delay: distributions.Distribution,
) -> list[task_logic.Block]:
    """The 13-block band: every grid (p_A, p_B) whose sum is allowed, plus the 5%
    no-reward distractor odor C (occupancy 0.475 / 0.475 / 0.05)."""
    make_patch_kwargs = {**_POST_STOP_PATCH_KWARGS, "delay": delay}
    return [
        helpers.make_block(
            p_rewards=(p_a, p_b, 0.0),
            n_min_patches=n_min_patches,
            block_length_exp_mean=block_length_exp_mean,
            block_length_max=block_length_max,
            first_state_occupancy=[0.475, 0.475, 0.05],
            make_patch_kwargs=make_patch_kwargs,
        )
        for p_a in PROBABILITY_GRID_REWARD_PROBABILITIES
        for p_b in PROBABILITY_GRID_REWARD_PROBABILITIES
        if round(p_a + p_b, 1) in PROBABILITY_GRID_ALLOWED_SUMS
    ]


def make_s_probability_grid_short_delay() -> Stage:
    """First probability-grid stage; absorbs the old `three_contrast` shaping.

    13-block band plus the 5% no-reward distractor odor C. The reward delay is a
    stochastic base (0.2 s floor + Exp, mean ~0.6 s) plus a `REWARD_DELAY_OFFSET`
    that ramps 0 -> 1.5 s within session (seeded across sessions by
    p_seed_reward_delay), growing patience on the grid while keeping trial-to-trial
    delay variance. This is still a shaping stage (non-stationary delay within a
    session), not a clean-analysis stage. Stop duration is fixed at 1.0 s."""
    return Stage(
        name="probability_grid_short_delay",
        task=AindVrForagingTaskLogic(
            stage_name="probability_grid_short_delay",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: task_logic.NumericalUpdater(
                        operation=task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=0.01, minimum=0, maximum=1.5
                        ),
                    ),
                },
                environment=task_logic.BlockStructure(
                    blocks=_probability_grid_blocks(
                        n_min_patches=40,
                        block_length_exp_mean=10,
                        block_length_max=70,
                        delay=helpers.make_reward_delay(offset=0.2, mean=0.4, max_delay=2.5),
                    ),
                    sampling_mode="Random",
                ),
                operation_control=helpers.make_default_operation_control(velocity_threshold=8),
            ),
        ),
        start_policies=[Policy(p_seed_reward_delay)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_probability_grid_long_delay() -> Stage:
    """Terminal stage: the same 13-block band, but with a stationary, longer and
    heavier-tailed reward delay (0.2 s floor + Exp, mean ~2.0 s, capped at 7 s) and
    no updaters. Tests value-tracking and patience/abandonment under genuine delay
    uncertainty rather than continuing to shape."""
    return Stage(
        name="probability_grid_long_delay",
        task=AindVrForagingTaskLogic(
            stage_name="probability_grid_long_delay",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=task_logic.BlockStructure(
                    blocks=_probability_grid_blocks(
                        n_min_patches=30,
                        block_length_exp_mean=10,
                        block_length_max=60,
                        delay=helpers.make_reward_delay(offset=0.2, mean=2.1, max_delay=7.0),
                    ),
                    sampling_mode="Random",
                ),
                operation_control=helpers.make_default_operation_control(velocity_threshold=8),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )
