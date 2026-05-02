from typing import cast

import numpy as np
from aind_behavior_vr_foraging import task_logic as vr_task_logic
from scipy.linalg import expm


def compute_cmc_transition_probability(n_states: int, rep_rate: float, dt: float = 0.1) -> np.ndarray:
    """
     Computes the replenishment transition probability matrix for each patch
    Parameters
    -----------
    n_states: int
        number reward states per patch.
    rep_rate: float
       replenishment rate.
    T: float
        model time step
    dt: float
        experiment time step


    Returns
    -------
    p_t: nd-array
        matrix of replenishment probabilities (#states * #states)
    """

    q = np.zeros((n_states, n_states))
    np.fill_diagonal(q, -rep_rate)
    np.fill_diagonal(q[:, 1:], rep_rate)
    q[-1, -1] = 0

    # compute replenishment probability function dependent on replenishment time (here experiment dt)
    p_t = expm(q * dt)
    assert p_t.ndim == 2
    return p_t


def make_patch_replenishment_function(
    n_states: int, replenishment_rate: float, p_reward_max: float, p_reward_min: float, rho: float
) -> vr_task_logic.CtcmFunction:
    return vr_task_logic.CtcmFunction(
        transition_matrix=cast(
            list[list[float]], compute_cmc_transition_probability(n_states, replenishment_rate).tolist()
        ),
        maximum=p_reward_max,
        minimum=p_reward_min,
        rho=rho,
    )


def make_patch(
    label: str,
    state_index: int,
    odor_index: int,
    p_reward_max: float,
    p_reward_min: float,
    depletion_rate: float,
    replenishment_rate: float,
    n_states: int,
    rho: float,
    replenishment_delay: float,
    inter_patch_length: float,
    reward_amount: float = 5.0,
):
    depletion = vr_task_logic.PatchRewardFunction(
        probability=vr_task_logic.ClampedMultiplicativeRateFunction(
            minimum=p_reward_min, maximum=p_reward_max, rate=vr_task_logic.scalar_value(depletion_rate)
        ),
        rule=vr_task_logic.RewardFunctionRule.ON_REWARD,
    )

    replenishment = vr_task_logic.OutsideRewardFunction(
        probability=make_patch_replenishment_function(n_states, replenishment_rate, p_reward_max, p_reward_min, rho),
        delay=replenishment_delay,
        rule=vr_task_logic.RewardFunctionRule.ON_TIME,
    )

    return vr_task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=[1 if i == odor_index else 0 for i in range(3)],
        reward_specification=vr_task_logic.RewardSpecification(
            amount=vr_task_logic.scalar_value(reward_amount),
            probability=vr_task_logic.scalar_value(p_reward_max),
            available=vr_task_logic.scalar_value(999999),
            delay=vr_task_logic.scalar_value(0.5),
            operant_logic=vr_task_logic.OperantLogic(
                is_operant=False,
                stop_duration=vr_task_logic.scalar_value(0.5),
                time_to_collect_reward=100000,
                grace_distance_threshold=10,
            ),
            reward_function=[depletion, replenishment],
        ),
        patch_virtual_sites_generator=vr_task_logic.PatchVirtualSitesGenerator(
            inter_patch=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=1),
                label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
                length_distribution=vr_task_logic.scalar_value(inter_patch_length),
                treadmill_specification=None,
            ),
            inter_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.INTERSITE,
                length_distribution=vr_task_logic.distributions.ExponentialDistribution(
                    distribution_parameters=vr_task_logic.distributions.ExponentialDistributionParameters(
                        rate=1.0 / 20
                    ),
                    truncation_parameters=vr_task_logic.distributions.TruncationParameters(
                        min=20,
                        max=100,
                    ),
                ),
                treadmill_specification=None,
            ),
            reward_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
                length_distribution=vr_task_logic.scalar_value(50.0),
                treadmill_specification=None,
            ),
        ),
    )
