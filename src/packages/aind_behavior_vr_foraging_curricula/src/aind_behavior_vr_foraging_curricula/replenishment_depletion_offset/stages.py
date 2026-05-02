from aind_behavior_curriculum import Stage
from aind_behavior_vr_foraging import task_logic as vr_task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from ..depletion import helpers
from ..depletion.metrics import metrics_from_dataset
from .policies import p_update_replenishment_rate
from .utils import make_patch

# ============================================================
# Stage definition
# ============================================================
p_maxs = [
    1.0,
    0.8,
    0.4,
]  # maximum reward probability of each patch, in order for patch A, B and C (they come in order A, B, C, A, ...)
p_min = [0.3, 0.3, 0.3]  # minimum reward probability only used for stopping depletion
dep_rates = [0.9, 0.9, 0.9]  # depletion rate of each patch
replenishment_delay = [5, 5, 5]  # delay (in seconds) before replenishment starts for each patch
# Define the patch statistics for the distance
interpatch_length = [140.0, 140.0, 140.0]  # inter-patch distance in cm
reward_amount = 5  # microliters
rep_rates = [0.1, 0.1, 0.1]  # replenishment rate of each patch (already scaled)
num_ps_states = [16, 12, 7]  # number of discrete reward states within each patch
rhos = [0.9, 0.9, 0.9]


def make_s_mcm_final_stage() -> Stage:
    patch1 = make_patch(
        label="High",
        state_index=0,
        odor_index=0,
        p_reward_max=p_maxs[0],
        p_reward_min=p_min[0],
        depletion_rate=dep_rates[0],
        replenishment_rate=rep_rates[0],
        n_states=num_ps_states[0],
        rho=rhos[0],
        replenishment_delay=replenishment_delay[0],
        inter_patch_length=interpatch_length[0],
        reward_amount=reward_amount,
    )
    patch2 = make_patch(
        label="Medium",
        state_index=1,
        odor_index=1,
        p_reward_max=p_maxs[1],
        p_reward_min=p_min[1],
        depletion_rate=dep_rates[1],
        replenishment_rate=rep_rates[1],
        n_states=num_ps_states[1],
        rho=rhos[1],
        replenishment_delay=replenishment_delay[1],
        inter_patch_length=interpatch_length[1],
        reward_amount=reward_amount,
    )
    patch3 = make_patch(
        label="Low",
        state_index=2,
        odor_index=2,
        p_reward_max=p_maxs[2],
        p_reward_min=p_min[2],
        depletion_rate=dep_rates[2],
        replenishment_rate=rep_rates[2],
        n_states=num_ps_states[2],
        rho=rhos[2],
        replenishment_delay=replenishment_delay[2],
        inter_patch_length=interpatch_length[2],
        reward_amount=reward_amount,
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
            operation_control=helpers.make_default_operation_control(velocity_threshold=8),
        ),
        stage_name="mcm_final_stage",
    )

    return Stage(
        name="mcm_final_stage",
        task=task_logic,
        start_policies=[p_update_replenishment_rate],
        metrics_provider=metrics_from_dataset,
    )
