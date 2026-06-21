from aind_behavior_curriculum import MetricsProvider, Policy, Stage
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from . import helpers
from .metrics import metrics_from_dataset
from .policies import (
    p_ease_geometry,
    p_introduce_negative_sites,
    p_seed_stop_duration,
    p_seed_stop_velocity,
    p_water_cap,
)


def make_s_shaping() -> Stage:
    """The single shaping stage. Everything is shaped here by cross-session policies:

    * speed -- the stop-velocity threshold ramps ``60 -> 8`` cm/s within session, seeded
      across days;
    * geometry -- ``p_ease_geometry`` eases inter-patch / reward-site lengths from the
      compressed (easy) values toward full, scaled by sites travelled;
    * negative proportion -- starts at 0 neg sites (all positive), then ramps 1 → 3 → 5
      per pair via ``p_introduce_negative_sites``; negative patches are always p=0;
    * stop duration -- ramps from a tiny base toward 3 s, seeded across days.
    """
    return Stage(
        name="shaping",
        task=AindVrForagingTaskLogic(
            stage_name="shaping",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: helpers.make_stop_velocity_updater(),
                    task_logic.UpdaterTarget.STOP_DURATION_OFFSET: helpers.make_stop_duration_updater(),
                },
                environment=task_logic.BlockStructure(
                    blocks=[helpers.make_block(negative_probability=0.0, positive_probability=1.0, n_neg_each=0)],
                    sampling_mode="Sequential",
                ),
                operation_control=helpers.make_operation_control(velocity_threshold=helpers.VELOCITY_THRESHOLD_START),
            ),
        ),
        start_policies=[
            Policy(p_introduce_negative_sites),
            Policy(p_seed_stop_velocity),
            Policy(p_seed_stop_duration),
            Policy(p_ease_geometry),
        ],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_graduated() -> Stage:
    """Negative odor fixed at 0%, stop duration fixed at 3 s, velocity fixed at the floor,
    geometry at full spacing, full 5+5 site ratio (no updaters). The water-cap policy
    trims reward volume across days if the prior session over-delivered water."""
    return Stage(
        name="graduated",
        task=AindVrForagingTaskLogic(
            stage_name="graduated",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=task_logic.BlockStructure(
                    blocks=[
                        helpers.make_block(
                            negative_probability=0.0,
                            positive_probability=1.0,
                            stop_duration=helpers.STOP_DURATION_GRADUATED,
                            geometry=helpers.GEOMETRY_FULL,
                            n_neg_each=helpers.N_SITES_EACH,
                        )
                    ],
                    sampling_mode="Sequential",
                ),
                operation_control=helpers.make_operation_control(velocity_threshold=helpers.VELOCITY_THRESHOLD_FLOOR),
            ),
        ),
        start_policies=[Policy(p_introduce_negative_sites), Policy(p_water_cap)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )
