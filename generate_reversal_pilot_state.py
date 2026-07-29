"""Per-session OFF-CURRICULUM trainer state for the reversal-adaptation pilot.

Emits ``probability_grid_reversal_pilot`` as an off-curriculum trainer state
(curriculum=null, is_on_curriculum=false) so the rig runs the stage's task exactly as
stored. This is the reversal-pilot's own generator (cf. oneoff_offcurriculum_stage.py,
which builds only zero-arg stages and so can't pass ``rotation``).

Regenerate it once per session and cycle ``--rotation`` in {0, 1, 2} so the |D| ladder is
counterbalanced against the satiety-limited engaged window (which |D| the mouse meets first,
right after the warm-up):
  rotation 0 -> |D|=0.4 first,
  rotation 1 -> |D|=0.2 first,
  rotation 2 -> |D|=0.6 first.
The simplest schedule keys it off the session ordinal: rotation = session_index % 3.

Examples:
    uv run python generate_reversal_pilot_state.py --rotation 0 \
        --output reversal_pilot_rot0_state.json
    uv run python generate_reversal_pilot_state.py --rotation 1 \
        --output reversal_pilot_rot1_state.json
    uv run python generate_reversal_pilot_state.py --rotation 2 \
        --output reversal_pilot_rot2_state.json
"""

import argparse

from aind_behavior_curriculum import Trainer, create_curriculum
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula import __semver__
from aind_behavior_vr_foraging_curricula.single_site import stages as ss_stages


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--rotation",
        type=int,
        default=0,
        help="Menu rotation in {0,1,2} (0->|D|=0.4 first, 1->|D|=0.2 first, 2->|D|=0.6 first). "
        "Cycle per session (session_index %% 3).",
    )
    parser.add_argument(
        "--velocity-threshold",
        type=float,
        default=None,
        help="Override the stop-velocity threshold (cm/s). Omit to keep the stage default (4).",
    )
    parser.add_argument(
        "--output", required=True, help="Path to write the trainer state JSON"
    )
    args = parser.parse_args()

    stage = ss_stages.make_s_probability_grid_reversal_pilot(rotation=args.rotation)
    if args.velocity_threshold is not None:
        stage.task.task_parameters.operation_control.position_control.velocity_threshold = args.velocity_threshold

    # Off-curriculum, manual one-off. The throwaway curriculum only supplies a TrainerState
    # model typed to AindVrForagingTaskLogic; it is NOT embedded (curriculum=None), and
    # is_on_curriculum=False makes the rig run stage.task verbatim (no Trainer.evaluate).
    trainer = Trainer(
        create_curriculum(
            "SingleSiteOffCurriculum",
            __semver__,
            (AindVrForagingTaskLogic,),
            pkg_location="one_off",
        )()
    )
    state = trainer.trainer_state_model(
        curriculum=None,
        stage=stage,
        is_on_curriculum=False,
        active_policies=None,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(state.model_dump_json(indent=2))
    print(f"Wrote {args.output} (rotation={args.rotation})")


if __name__ == "__main__":
    main()
