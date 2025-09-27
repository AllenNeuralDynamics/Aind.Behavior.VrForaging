import os
from typing import cast

import aind_behavior_services.task_logic.distributions as distributions
import numpy as np
from aind_behavior_curriculum import Stage, TrainerState
from scipy.linalg import expm

import aind_behavior_vr_foraging.task_logic as vr_task_logic
from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)


def ExponentialDistributionHelper(rate=1.0, minimum=0.0, maximum=1000.0):
    return distributions.ExponentialDistribution(
        distribution_parameters=distributions.ExponentialDistributionParameters(rate=rate),
        truncation_parameters=distributions.TruncationParameters(min=minimum, max=maximum, is_truncated=True),
        scaling_parameters=distributions.ScalingParameters(scale=1.0, offset=0.0),
    )


def compute_cmc_transition_probability(n_states, rep_rate, T=3.5, dt=0.1) -> np.ndarray:
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
    np.fill_diagonal(q, -rep_rate / T)
    np.fill_diagonal(q[:, 1:], rep_rate / T)
    q[-1, -1] = 0

    # compute replenishment probability function dependent on replenishment time (here experiment dt)
    p_t = expm(q * dt)
    assert p_t.ndim == 2
    return p_t


operation_control = vr_task_logic.OperationControl(
    movable_spout_control=vr_task_logic.MovableSpoutControl(enabled=False),
    audio_control=vr_task_logic.AudioControl(duration=0.2, frequency=9999),
    odor_control=vr_task_logic.OdorControl(),
    position_control=vr_task_logic.PositionControl(
        frequency_filter_cutoff=5,
        velocity_threshold=8,
    ),
)

# Define the patch statistics for the distance
minimum_interpatch_length = 200
maximum_interpatch_length = 600
minimum_intersite_length = 20
maximum_intersite_length = 100
rewardsite_length = 50
cm_second_average_speed = 40  # cm/s
reward_amount = 5  # microliters
rep_rates = [0.2, 0.2, 0.2]  # replenishment rate of each patch (5min, 4min, 2min to full replenishment)
# rep_rates = [0.2, 0.1, 0.1] #  alternatively  (5min, 8min, 5min to full replenishment)
num_ps_states = [16, 12, 7]  # number of discrete reward states within each patch
p_maxs = [
    1.0,
    0.7,
    0.4,
]  # maximum reward probability of each patch, in order for patch A, B and C (they come in order A, B, C, A, ...)
p_min = [0.2, 0.2, 0.2]  # minimum reward probability only used for stopping depletion
dep_rates = [0.9, 0.81, 0.73]  # depletion rate of each patch
inter_patch_time = np.array([3, 2, 1]) * 3.5  # delay before replenishment starts for each patch
rhos = [0.9, 0.9, 0.9]


def make_patch(
    label: str,
    state_index: int,
    odor_index: int,
    p_max: float,
    p_min: float,
    dep_rate: float,
    rep_rate: float,
    n_states: int,
    rho: float,
    inter_patch_time: float,
):
    depletion = vr_task_logic.PatchRewardFunction(
        probability=vr_task_logic.ClampedMultiplicativeRateFunction(
            minimum=p_min, maximum=p_max, rate=vr_task_logic.scalar_value(dep_rate)
        ),
        rule=vr_task_logic.RewardFunctionRule.ON_REWARD,
    )

    replenishment = vr_task_logic.OutsideRewardFunction(
        probability=vr_task_logic.CtcmFunction(
            transition_matrix=cast(list[list[float]], compute_cmc_transition_probability(n_states, rep_rate).tolist()),
            maximum=p_max,
            minimum=p_min,
            rho=rho,
        ),
        delay=inter_patch_time,
        rule=vr_task_logic.RewardFunctionRule.ON_TIME,
    )

    return vr_task_logic.Patch(
        label=label,
        state_index=state_index,
        odor_specification=vr_task_logic.OdorSpecification(index=odor_index, concentration=1),
        reward_specification=vr_task_logic.RewardSpecification(
            amount=vr_task_logic.scalar_value(reward_amount),
            probability=vr_task_logic.scalar_value(p_max),
            available=vr_task_logic.scalar_value(999999),
            delay=vr_task_logic.scalar_value(0.5),
            operant_logic=vr_task_logic.OperantLogic(
                is_operant=False,
                stop_duration=0.5,
                time_to_collect_reward=100000,
                grace_distance_threshold=10,
            ),
            reward_function=[depletion, replenishment],
        ),
        patch_virtual_sites_generator=vr_task_logic.PatchVirtualSitesGenerator(
            inter_patch=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=1),
                label=vr_task_logic.VirtualSiteLabels.INTERPATCH,
                length_distribution=vr_task_logic.scalar_value(inter_patch_time * cm_second_average_speed),
                treadmill_specification=None,
            ),
            inter_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.INTERSITE,
                length_distribution=ExponentialDistributionHelper(
                    rate=0.05, minimum=minimum_intersite_length, maximum=maximum_intersite_length
                ),
                # length_distribution=vr_task_logic.scalar_value(1/0.05 * 2) # Consider using deterministic intersite distance
                treadmill_specification=None,
            ),
            reward_site=vr_task_logic.VirtualSiteGenerator(
                render_specification=vr_task_logic.RenderSpecification(contrast=0.5),
                label=vr_task_logic.VirtualSiteLabels.REWARDSITE,
                length_distribution=vr_task_logic.scalar_value(rewardsite_length),
                treadmill_specification=None,
            ),
        ),
    )


patch1 = make_patch(
    label="A",
    state_index=0,
    odor_index=0,
    p_max=p_maxs[0],
    p_min=p_min[0],
    dep_rate=dep_rates[0],
    rep_rate=rep_rates[0],
    n_states=num_ps_states[0],
    rho=rhos[0],
    inter_patch_time=inter_patch_time[0],
)
patch2 = make_patch(
    label="B",
    state_index=1,
    odor_index=1,
    p_max=p_maxs[1],
    p_min=p_min[1],
    dep_rate=dep_rates[1],
    rep_rate=rep_rates[1],
    n_states=num_ps_states[1],
    rho=rhos[1],
    inter_patch_time=inter_patch_time[1],
)
patch3 = make_patch(
    label="C",
    state_index=2,
    odor_index=2,
    p_max=p_maxs[2],
    p_min=p_min[2],
    dep_rate=dep_rates[2],
    rep_rate=rep_rates[2],
    n_states=num_ps_states[2],
    rho=rhos[2],
    inter_patch_time=inter_patch_time[2],
)

environment_statistics = vr_task_logic.EnvironmentStatistics(
    first_state_occupancy=[0.33, 0.33, 0.33],
    transition_matrix=[[0, 1, 0], [0, 0, 1], [1, 0, 0]],
    patches=[patch1, patch2, patch3],
)


task_logic = AindVrForagingTaskLogic(
    task_parameters=AindVrForagingTaskParameters(
        rng_seed=None,
        environment=vr_task_logic.BlockStructure(
            blocks=[vr_task_logic.Block(environment_statistics=environment_statistics, end_conditions=[])],
            sampling_mode="Random",
        ),
        operation_control=operation_control,
    ),
    stage_name="mcm",
)


def main(path_seed: str = "./local/MCM_{schema}.json"):
    example_task_logic = task_logic
    example_trainer_state = TrainerState(
        stage=Stage(name="example_stage", task=example_task_logic), curriculum=None, is_on_curriculum=False
    )
    os.makedirs(os.path.dirname(path_seed), exist_ok=True)
    models = [example_task_logic, example_trainer_state]

    for model in models:
        with open(path_seed.format(schema=model.__class__.__name__), "w", encoding="utf-8") as f:
            f.write(model.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
