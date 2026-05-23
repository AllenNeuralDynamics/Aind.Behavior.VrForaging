from typing import Any, Optional

import aind_behavior_services.task.distributions as distributions
import aind_behavior_vr_foraging.task_logic as vr_task_logic
from aind_behavior_curriculum import MetricsProvider, Policy, Stage
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from .metrics import metrics_from_dataset
from .policies import p_learn_to_stop, p_seed_reward_delay, p_seed_stop_duration


def make_patch(
    label: str,
    state_index: int,
    odor_index: int,
    p_reward: float,
    stop_duration: float = 0.5,
    reward_amount: float = 7.0,
    inter_site_length: float = 15,
    reward_site_length: float = 40,
    inter_patch_min_length: float = 50,
    inter_patch_mean_length: float = 150,
    inter_patch_max_length: float = 500,
    delay: Optional[distributions.Distribution] = None,
):
    if delay is None:
        delay = vr_task_logic.scalar_value(0.5)
    return vr_task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=[1 if i == odor_index else 0 for i in range(3)],
        patch_terminators=[
            vr_task_logic.PatchTerminatorOnChoice(count=vr_task_logic.scalar_value(1)),
            vr_task_logic.PatchTerminatorOnRejection(count=vr_task_logic.scalar_value(1)),
        ],
        reward_specification=vr_task_logic.RewardSpecification(
            amount=vr_task_logic.scalar_value(reward_amount),
            probability=vr_task_logic.scalar_value(p_reward),
            available=vr_task_logic.scalar_value(999999),
            delay=delay,
            operant_logic=vr_task_logic.OperantLogic(
                is_operant=False,
                stop_duration=stop_duration,
                time_to_collect_reward=100000,
                grace_distance_threshold=10,
            ),
        ),
        patch_virtual_sites_generator=vr_task_logic.PatchVirtualSitesGenerator(
            inter_patch=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=1),
                label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
                length_distribution=distributions.ExponentialDistribution(
                    distribution_parameters=distributions.ExponentialDistributionParameters(
                        rate=1.0 / inter_patch_mean_length
                    ),
                    scaling_parameters=distributions.ScalingParameters(offset=inter_patch_min_length),
                    truncation_parameters=distributions.TruncationParameters(
                        min=inter_patch_min_length,
                        max=inter_patch_max_length,
                    ),
                ),
            ),
            inter_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.INTERSITE,
                length_distribution=vr_task_logic.scalar_value(inter_site_length),
            ),
            reward_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
                length_distribution=vr_task_logic.scalar_value(reward_site_length),
            ),
        ),
    )


def make_block(
    p_rew: tuple[float, Optional[float], Optional[float]],
    n_min_patches: int = 100,
    block_length_exp_mean: float = 25,
    block_length_max: Optional[float] = None,
    first_state_occupancy: Optional[list[float]] = None,
    make_patch_kwargs: Optional[dict[str, Any]] = None,
) -> vr_task_logic.Block:
    make_patch_kwargs = make_patch_kwargs or {}
    patches = [
        make_patch(
            label="OdorA",
            state_index=0,
            odor_index=0,
            p_reward=p_rew[0],
            **make_patch_kwargs,
        )
    ]
    if p_rew[1] is not None:
        patches.append(
            make_patch(
                label="OdorB",
                state_index=1,
                odor_index=1,
                p_reward=p_rew[1],
                **make_patch_kwargs,
            )
        )
    if p_rew[2] is not None:
        patches.append(
            make_patch(
                label="OdorC",
                state_index=2,
                odor_index=2,
                p_reward=p_rew[2],
                **make_patch_kwargs,
            )
        )

    if first_state_occupancy is None:
        per_p = 1.0 / len(patches)
        first_state_occupancy = [per_p] * len(patches)
    if block_length_max is None:
        block_length_max = n_min_patches + 50
    return vr_task_logic.Block(
        environment_statistics=vr_task_logic.EnvironmentStatistics(
            first_state_occupancy=list(first_state_occupancy),
            transition_matrix=[list(first_state_occupancy) for _ in range(len(patches))],
            patches=patches,
        ),
        end_conditions=[
            vr_task_logic.BlockEndConditionPatchCount(
                value=distributions.ExponentialDistribution(
                    distribution_parameters=distributions.ExponentialDistributionParameters(
                        rate=1 / block_length_exp_mean
                    ),
                    scaling_parameters=distributions.ScalingParameters(offset=n_min_patches),
                    truncation_parameters=distributions.TruncationParameters(min=n_min_patches, max=block_length_max),
                )
            )
        ],
    )


def make_operation_control(velocity_threshold: float) -> vr_task_logic.OperationControl:
    return vr_task_logic.OperationControl(
        movable_spout_control=vr_task_logic.MovableSpoutControl(enabled=False),
        audio_control=vr_task_logic.AudioControl(duration=0.2, frequency=9999),
        odor_control=vr_task_logic.OdorControl(),
        position_control=vr_task_logic.PositionControl(
            frequency_filter_cutoff=5,
            velocity_threshold=velocity_threshold,
        ),
    )


# ============================================================
# Stage definition
# ============================================================


def _make_learn_to_stop_task(p_reward: float, stage_name: str) -> AindVrForagingTaskLogic:
    return AindVrForagingTaskLogic(
        stage_name=stage_name,
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=None,
            updaters={
                vr_task_logic.UpdaterTarget.STOP_DURATION_OFFSET: vr_task_logic.NumericalUpdater(
                    operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
                    parameters=vr_task_logic.NumericalUpdaterParameters(
                        initial_value=0, on_success=0.0067, minimum=0, maximum=1.0
                    ),
                ),
                vr_task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: vr_task_logic.NumericalUpdater(
                    operation=vr_task_logic.NumericalUpdaterOperation.GAIN,
                    parameters=vr_task_logic.NumericalUpdaterParameters(
                        initial_value=60,
                        on_success=0.987,
                        minimum=8,
                        maximum=60,
                    ),
                ),
            },
            environment=vr_task_logic.BlockStructure(
                blocks=[
                    make_block(
                        p_rew=(p_reward, p_reward, None),
                        n_min_patches=100000,
                        make_patch_kwargs={
                            "inter_patch_min_length": 50,
                            "inter_patch_mean_length": 120,
                            "inter_patch_max_length": 150,
                            "inter_site_length": 15,
                            "reward_site_length": 40,
                            "reward_amount": 7.0,
                        },
                    ),
                ],
                sampling_mode="Sequential",
            ),
            operation_control=make_operation_control(velocity_threshold=60),
        ),
    )


def make_s_learn_to_stop() -> Stage:
    return Stage(
        name="learn_to_stop",
        task=_make_learn_to_stop_task(p_reward=1.0, stage_name="learn_to_stop"),
        start_policies=[Policy(p_learn_to_stop)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_learn_to_stop_low_p() -> Stage:
    """Fallback shaping stage for animals that don't graduate S1 in one session.
    Same task as S1 but with p_reward=0.8 to discourage stickiness. Saturation
    gates to S2 are identical to S1's. p_learn_to_stop carries the updater state
    from the prior session so within-session shaping picks up where it left off."""
    return Stage(
        name="learn_to_stop_low_p",
        task=_make_learn_to_stop_task(p_reward=0.8, stage_name="learn_to_stop_low_p"),
        start_policies=[Policy(p_learn_to_stop)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_learn_to_choose() -> Stage:
    """High-contrast discrimination stage. Two odors, alternating blocks with
    p_rew=(0.9, 0.1) and (0.1, 0.9). REWARD_DELAY_OFFSET ramps 0 -> 0.3 s within
    session; carried forward across S2 sessions via p_seed_reward_delay."""
    _make_patch_kwargs = {
        "inter_patch_min_length": 30,
        "inter_patch_mean_length": 60,
        "inter_patch_max_length": 190,
        "inter_site_length": 15,
        "reward_site_length": 50,
        "reward_amount": 7.0,
        "stop_duration": 1.5,
    }
    return Stage(
        name="learn_to_choose",
        task=AindVrForagingTaskLogic(
            stage_name="learn_to_choose",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    vr_task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: vr_task_logic.NumericalUpdater(
                        operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=vr_task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=0.002, minimum=0, maximum=0.3
                        ),
                    ),
                },
                environment=vr_task_logic.BlockStructure(
                    blocks=[
                        make_block(
                            p_rew=(0.9, 0.1, None),
                            n_min_patches=60,
                            block_length_exp_mean=15,
                            block_length_max=100,
                            make_patch_kwargs=_make_patch_kwargs,
                        ),
                        make_block(
                            p_rew=(0.1, 0.9, None),
                            n_min_patches=60,
                            block_length_exp_mean=15,
                            block_length_max=100,
                            make_patch_kwargs=_make_patch_kwargs,
                        ),
                    ],
                    sampling_mode="Random",
                ),
                operation_control=make_operation_control(velocity_threshold=8),
            ),
        ),
        start_policies=[Policy(p_seed_reward_delay)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


THREE_CONTRAST_PROBABILITY_PAIRS: list[tuple[float, float]] = [
    (0.1, 0.9),
    (0.9, 0.1),
    (0.3, 0.7),
    (0.7, 0.3),
    (0.5, 0.5),
]
GRADUATED_REWARD_PROBABILITIES: tuple[float, ...] = (0.10, 0.30, 0.50, 0.70, 0.90)
# Applied to the 5-value graduated grid: skip (p_A, p_B) pairs whose sum is below
# this floor. With 0.4 the only excluded combo is (0.1, 0.1).
GRADUATED_MIN_PROBABILITY_SUM: float = 0.4


def make_s_three_contrast() -> Stage:
    """Two-odor paired-block stage. Five blocks covering three contrasts:
    (0.1/0.9, 0.3/0.7, 0.5/0.5) with mirrored variants for symmetric odor exposure.
    REWARD_DELAY_OFFSET ramps 0 -> 1.5 s while STOP_DURATION_OFFSET ramps 0 -> -0.5 s
    at mirrored rates, so effective stop+delay stays at 2.0 s until stop saturates
    at 1.0 s, after which total grows to 3.0 s as delay finishes saturating. Both
    offsets are seeded across sessions via p_seed_reward_delay / p_seed_stop_duration."""
    _make_patch_kwargs = {
        "inter_patch_min_length": 30,
        "inter_patch_mean_length": 60,
        "inter_patch_max_length": 190,
        "inter_site_length": 15,
        "reward_site_length": 50,
        "reward_amount": 7.0,
        "stop_duration": 1.5,
    }

    blocks = [
        make_block(
            p_rew=(p_a, p_b, None),
            n_min_patches=50,
            block_length_exp_mean=10,
            block_length_max=80,
            make_patch_kwargs=_make_patch_kwargs,
        )
        for p_a, p_b in THREE_CONTRAST_PROBABILITY_PAIRS
    ]

    return Stage(
        name="three_contrast",
        task=AindVrForagingTaskLogic(
            stage_name="three_contrast",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    vr_task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: vr_task_logic.NumericalUpdater(
                        operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=vr_task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=0.005, minimum=0, maximum=1.5
                        ),
                    ),
                    vr_task_logic.UpdaterTarget.STOP_DURATION_OFFSET: vr_task_logic.NumericalUpdater(
                        operation=vr_task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=vr_task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=-0.005, minimum=-0.5, maximum=0
                        ),
                    ),
                },
                environment=vr_task_logic.BlockStructure(
                    blocks=blocks,
                    sampling_mode="Random",
                ),
                operation_control=make_operation_control(velocity_threshold=8),
            ),
        ),
        start_policies=[Policy(p_seed_reward_delay), Policy(p_seed_stop_duration)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def _graduated_reward_delay(
    max_delay: float = 5.25, char: float = 2.0, offset: float = 0.5
) -> distributions.Distribution:
    return distributions.ExponentialDistribution(
        distribution_parameters=distributions.ExponentialDistributionParameters(rate=1.0 / char),
        scaling_parameters=distributions.ScalingParameters(offset=offset),
        truncation_parameters=distributions.TruncationParameters(min=offset, max=max_delay),
    )


def make_s_graduated_narrow_delay() -> Stage:
    """Narrow-variance graduated stage. Same 24-block 5x5 grid as the wider
    graduated stage (with the 5% no-reward distractor odor C). Delay is
    `offset=0.5 + Exp(char=1.5)` clamped to [0.5, 5.25] → mean ~1.94 s,
    sum~2.94 s, std~1.5 s. Stop duration is held fixed at 1.0 s, matching where
    the coupled ramps in S4 (`three_contrast`) land. No updaters and no start
    policies — all shaping is finished by S4."""
    _make_patch_kwargs = {
        "inter_patch_min_length": 30,
        "inter_patch_mean_length": 60,
        "inter_patch_max_length": 190,
        "inter_site_length": 15,
        "reward_site_length": 50,
        "reward_amount": 7.0,
        "stop_duration": 1.0,
        "delay": _graduated_reward_delay(max_delay=5.25, char=1.5),
    }

    blocks = [
        make_block(
            p_rew=(p_a, p_b, 0.0),
            n_min_patches=40,
            block_length_exp_mean=10,
            block_length_max=70,
            first_state_occupancy=[0.475, 0.475, 0.05],
            make_patch_kwargs=_make_patch_kwargs,
        )
        for p_a in GRADUATED_REWARD_PROBABILITIES
        for p_b in GRADUATED_REWARD_PROBABILITIES
        if p_a + p_b >= GRADUATED_MIN_PROBABILITY_SUM
    ]

    return Stage(
        name="graduated_narrow_delay",
        task=AindVrForagingTaskLogic(
            stage_name="graduated_narrow_delay",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=vr_task_logic.BlockStructure(
                    blocks=blocks,
                    sampling_mode="Random",
                ),
                operation_control=make_operation_control(velocity_threshold=8),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_graduated_stage() -> Stage:
    _graduated_make_patch_kwargs = {
        "inter_patch_min_length": 30,
        "inter_patch_mean_length": 60,
        "inter_patch_max_length": 190,
        "inter_site_length": 15,
        "reward_site_length": 50,
        "reward_amount": 7.0,
        "stop_duration": 1.0,
        "delay": _graduated_reward_delay(max_delay=7.0, char=2.1, offset=0.0),
    }

    blocks = [
        make_block(
            p_rew=(p_a, p_b, 0.0),
            n_min_patches=30,
            block_length_exp_mean=10,
            block_length_max=60,
            first_state_occupancy=[0.475, 0.475, 0.05],
            make_patch_kwargs=_graduated_make_patch_kwargs,
        )
        for p_a in GRADUATED_REWARD_PROBABILITIES
        for p_b in GRADUATED_REWARD_PROBABILITIES
        if p_a + p_b >= GRADUATED_MIN_PROBABILITY_SUM
    ]

    return Stage(
        name="graduated_stage",
        task=AindVrForagingTaskLogic(
            stage_name="graduated_stage",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=vr_task_logic.BlockStructure(
                    blocks=blocks,
                    sampling_mode="Random",
                ),
                operation_control=make_operation_control(velocity_threshold=8),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )
