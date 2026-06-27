"""Reusable builders for the single-site curriculum: small task-logic constructors
plus numeric helpers. Stage definitions live in ``stages.py``; this module is only
construction plumbing."""

from typing import Any, Optional

from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic

#: Water volume (microlitres) delivered per harvested reward.
REWARD_AMOUNT_UL: float = 7.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def lerp(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def make_default_operation_control(velocity_threshold: float) -> task_logic.OperationControl:
    """Operation control shared by every stage: movable spout off, audio effectively
    silent, no odor flow, only the stop-velocity threshold varies."""
    return task_logic.OperationControl(
        audio_control=task_logic.AudioControl(duration=0.2, frequency=9999),
        odor_control=task_logic.OdorControl(),
        position_control=task_logic.PositionControl(
            frequency_filter_cutoff=5,
            velocity_threshold=velocity_threshold,
        ),
    )


def make_reward_delay(offset: float, mean: float, max_delay: float) -> distributions.ExponentialDistribution:
    """Stochastic reward delay: ``offset + Exp(mean)`` truncated to ``[offset, max_delay]`` (s)."""
    return distributions.ExponentialDistribution(
        distribution_parameters=distributions.ExponentialDistributionParameters(rate=1.0 / mean),
        scaling_parameters=distributions.ScalingParameters(offset=offset),
        truncation_parameters=distributions.TruncationParameters(min=offset, max=max_delay),
    )


def make_patch(
    label: str,
    state_index: int,
    odor_index: int,
    p_reward: float,
    stop_duration: float = 0.5,
    reward_amount: float = REWARD_AMOUNT_UL,
    inter_site_length: float = 15,
    reward_site_length: float = 40,
    inter_patch_min_length: float = 50,
    inter_patch_mean_length: float = 150,
    inter_patch_max_length: float = 500,
    delay: Optional[distributions.Distribution] = None,
) -> task_logic.Patch:
    """A single odor-marked reward site. One accept/reject decision per patch
    (``OnChoice``/``OnRejection`` count 1); reward is non-baited."""
    if delay is None:
        delay = task_logic.scalar_value(0.5)
    return task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=[1 if i == odor_index else 0 for i in range(3)],
        patch_terminators=[
            task_logic.PatchTerminatorOnChoice(count=task_logic.scalar_value(1)),
            task_logic.PatchTerminatorOnRejection(count=task_logic.scalar_value(1)),
        ],
        reward_specification=task_logic.RewardSpecification(
            amount=task_logic.scalar_value(reward_amount),
            probability=task_logic.scalar_value(p_reward),
            available=task_logic.scalar_value(999999),
            delay=delay,
            operant_logic=task_logic.OperantLogic(
                is_operant=False,
                stop_duration=stop_duration,
                time_to_collect_reward=100000,
                grace_distance_threshold=10,
            ),
        ),
        patch_virtual_sites_generator=task_logic.PatchVirtualSitesGenerator(
            inter_patch=task_logic.VirtualSiteGenerator(
                render_specification=task_logic.RenderSpecification(contrast=1),
                label=task_logic.VirtualSiteLabels.INTERPATCH,
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
            inter_site=task_logic.VirtualSiteGenerator(
                render_specification=task_logic.RenderSpecification(contrast=0.5),
                label=task_logic.VirtualSiteLabels.INTERSITE,
                length_distribution=task_logic.scalar_value(inter_site_length),
            ),
            reward_site=task_logic.VirtualSiteGenerator(
                render_specification=task_logic.RenderSpecification(contrast=0.5),
                label=task_logic.VirtualSiteLabels.REWARDSITE,
                length_distribution=task_logic.scalar_value(reward_site_length),
            ),
        ),
    )


def make_block(
    p_rewards: tuple[float, Optional[float], Optional[float]],
    n_min_patches: int = 100,
    block_length_exp_mean: float = 25,
    block_length_max: Optional[float] = None,
    first_state_occupancy: Optional[list[float]] = None,
    make_patch_kwargs: Optional[dict[str, Any]] = None,
) -> task_logic.Block:
    """A block of OdorA/B/C patches. ``p_rewards`` gives each odor's reward
    probability; a ``None`` entry omits that odor (so ``(1.0, 1.0, None)`` is a
    two-odor block). Block length is ``n_min_patches + Exp(block_length_exp_mean)``
    truncated to ``[n_min_patches, block_length_max]`` patches."""
    make_patch_kwargs = make_patch_kwargs or {}
    patches = [make_patch(label="OdorA", state_index=0, odor_index=0, p_reward=p_rewards[0], **make_patch_kwargs)]
    if p_rewards[1] is not None:
        patches.append(
            make_patch(label="OdorB", state_index=1, odor_index=1, p_reward=p_rewards[1], **make_patch_kwargs)
        )
    if p_rewards[2] is not None:
        patches.append(
            make_patch(label="OdorC", state_index=2, odor_index=2, p_reward=p_rewards[2], **make_patch_kwargs)
        )

    if first_state_occupancy is None:
        first_state_occupancy = [1.0 / len(patches)] * len(patches)
    if block_length_max is None:
        block_length_max = n_min_patches + 50
    return task_logic.Block(
        environment=task_logic.MarkovEnvironment(
            first_state_occupancy=list(first_state_occupancy),
            transition_matrix=[list(first_state_occupancy) for _ in range(len(patches))],
            patches=patches,
        ),
        end_conditions=[
            task_logic.BlockEndConditionPatchCount(
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
