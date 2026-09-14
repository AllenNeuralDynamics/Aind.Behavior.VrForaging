"""One-off trainer state: a `learn_to_stop`-style stage tuned for a poor stopper.

Built against the v1 `single_site` curriculum (aind_behavior_vr_foraging_curricula),
reusing its corridor geometry / helpers but:
  * fixes the stop-velocity threshold at 4 cm/s (no in-session decay),
  * stretches the required stop duration up to a 1.0 s cap with a linear (additive)
    ramp of +0.01 s per successful stop. 1.0 s matches single_site's fixed stop
    duration (learn_to_stop through probability_grid_*), so the mouse tops out at
    exactly what the real task demands instead of overshooting,
  * emitted as an OFF-CURRICULUM trainer state (curriculum=null, is_on_curriculum=false),
    so the rig runs this stage's task directly and does not try to resolve/advance a
    curriculum (scripts/aind.py `_run_curriculum_if_applicable` short-circuits on the
    False flag). You move the mouse off this stage by hand.

Rig combination (verified in Extensions/InstantiateSite.bonsai `CheckStop`):
    required_stop = max(0, base_stop_duration + StopDurationOffset)
Here base_stop_duration = 0, so the required stop equals the StopDurationOffset value.

Note: v1's stock `learn_to_stop` deliberately holds stop duration fixed at 1.0 s
and only shapes velocity ("avoid the learn-low-then-fail-high trap"). This one-off
intentionally does the opposite to rehab a specific poor-stopper mouse.

Run from the Aind.Behavior.VrForaging repo:
    uv run python oneoff_stop_rehab.py --output stop_rehab_state.json
"""

import argparse

from aind_behavior_curriculum import MetricsProvider, Stage, Trainer, create_curriculum
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import (
    AindVrForagingTaskLogic,
    AindVrForagingTaskParameters,
)
from aind_behavior_vr_foraging_curricula import __semver__
from aind_behavior_vr_foraging_curricula.single_site import helpers
from aind_behavior_vr_foraging_curricula.single_site.metrics import metrics_from_dataset
from aind_behavior_vr_foraging_curricula.single_site.policies import (
    LEARN_TO_STOP_GEOMETRY_COMPRESSED,
)

# ---- knobs -----------------------------------------------------------------
VELOCITY_THRESHOLD = 4.0  # cm/s, fixed
STOP_DURATION_START = 0.65  # s, required stop at session start
STOP_DURATION_CEILING = (
    1.0  # s, cap; matches single_site's fixed 1.0 s stop (no overshoot)
)
STOP_DURATION_STEP = 0.005  # s added per successful stop (linear/additive ramp)
REWARD_AMOUNT_UL = 3.0  # µL delivered per rewarded site
REWARD_DELAY_S = (
    0.0  # s, fixed delay from stop completion to reward (no updater -> stays fixed)
)
# Additive ramp: StopDurationOffset starts at STOP_DURATION_START and adds STOP_DURATION_STEP
# on each successful stop, up to STOP_DURATION_CEILING. base operant stop_duration = 0, so the
# logged StopDurationOffset value *is* the required stop. Reaches the cap after
# (ceiling - start) / step successful stops.
# ----------------------------------------------------------------------------


def make_s_stop_rehab() -> Stage:
    return Stage(
        name="learn_to_stop_rehab",
        task=AindVrForagingTaskLogic(
            stage_name="learn_to_stop_rehab",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    # Additive (linear) stretch: +STOP_DURATION_STEP per successful stop, capped
                    # at the ceiling. OFFSET is safe with on_failure=0.0 (adds 0 = hold), unlike GAIN.
                    task_logic.UpdaterTarget.STOP_DURATION_OFFSET: task_logic.NumericalUpdater(
                        operation=task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=task_logic.NumericalUpdaterParameters(
                            initial_value=STOP_DURATION_START,  # required stop == offset (base = 0)
                            on_success=STOP_DURATION_STEP,  # +0.01 s per successful stop
                            on_failure=0.0,  # hold on a failed stop
                            minimum=STOP_DURATION_START,  # floor: session-start stop
                            maximum=STOP_DURATION_CEILING,  # cap: 1.0 s (curriculum's fixed stop)
                        ),
                    ),
                    # Velocity threshold pinned at 4 cm/s (GAIN of 1.0 => never moves).
                    task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: task_logic.NumericalUpdater(
                        operation=task_logic.NumericalUpdaterOperation.GAIN,
                        parameters=task_logic.NumericalUpdaterParameters(
                            initial_value=VELOCITY_THRESHOLD,
                            on_success=1.0,
                            on_failure=1.0,
                            minimum=VELOCITY_THRESHOLD,
                            maximum=VELOCITY_THRESHOLD,
                        ),
                    ),
                },
                environment=task_logic.BlockStructure(
                    blocks=[
                        helpers.make_block(
                            p_rewards=(0.8, 0.8, None),
                            n_min_patches=100000,  # one block per session (never ends within a session)
                            make_patch_kwargs={
                                **LEARN_TO_STOP_GEOMETRY_COMPRESSED,
                                # base stop_duration = 0 so the required stop == the offset above
                                "stop_duration": 0.0,
                                "reward_amount": REWARD_AMOUNT_UL,
                                "delay": task_logic.scalar_value(REWARD_DELAY_S),
                            },
                        ),
                    ],
                    sampling_mode="Sequential",
                ),
                operation_control=helpers.make_default_operation_control(
                    velocity_threshold=VELOCITY_THRESHOLD
                ),
            ),
        ),
        start_policies=[],  # no cross-session seeding — this is a one-off
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="stop_rehab_state.json",
        help="Path to write the trainer state JSON",
    )
    args = parser.parse_args()

    # Off-curriculum, manual one-off. We build a throwaway curriculum ONLY to get a
    # TrainerState model typed to AindVrForagingTaskLogic (so stage.task serializes
    # correctly); the curriculum itself is NOT embedded (curriculum=None). With
    # is_on_curriculum=False the rig launcher skips curriculum resolution/evaluation
    # and just runs stage.task, so there is no nonexistent curriculum to look up.
    trainer = Trainer(
        create_curriculum(
            "SingleSiteStopRehab",
            __semver__,
            (AindVrForagingTaskLogic,),
            pkg_location="one_off",
        )()
    )
    state = trainer.trainer_state_model(
        curriculum=None,
        stage=make_s_stop_rehab(),
        is_on_curriculum=False,
        active_policies=None,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(state.model_dump_json(indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
