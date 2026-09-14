"""One-off OFF-CURRICULUM trainer state: single_site `learn_to_choose`
with the stop-velocity threshold lowered to 4 cm/s.

For a mouse that has (mostly) learned to stop under the rehab stage and is being eased
back into the regular single_site curriculum, but whose lower 4 cm/s stop-velocity
threshold must be preserved rather than reset to the curriculum default of 8.

Emitted OFF curriculum (curriculum=null, is_on_curriculum=false) so the rig runs the
stage's task exactly as stored and does NOT re-derive it from the curriculum definition
(an on-curriculum Trainer.evaluate rebuilds the task from the stage, restoring 8 cm/s).
The mouse is advanced back onto the real curriculum by hand when ready.

The stage is otherwise the genuine single_site learn_to_choose: high-contrast
discrimination, two odors in alternating (0.9, 0.1) / (0.1, 0.9) blocks, fixed 1.0 s
stop, with the in-session REWARD_DELAY_OFFSET ramp (0 -> 0.3 s). Only the stop-velocity
threshold is overridden; that stage has no velocity updater, so operation_control fully
determines it.

Run from the Aind.Behavior.VrForaging repo:
    uv run python oneoff_learn_to_choose_lowthresh.py --output learn_to_choose_lowthresh_state.json
"""

import argparse

from aind_behavior_curriculum import Stage, Trainer, create_curriculum
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic
from aind_behavior_vr_foraging_curricula import __semver__
from aind_behavior_vr_foraging_curricula.single_site.stages import (
    make_s_learn_to_choose,
)

# ---- knobs -----------------------------------------------------------------
VELOCITY_THRESHOLD = 4.0  # cm/s (single_site default for this stage is 8)
# ----------------------------------------------------------------------------


def make_s_learn_to_choose_lowthresh() -> Stage:
    """The real learn_to_choose stage, with velocity threshold set to 4 cm/s."""
    stage = make_s_learn_to_choose()
    stage.task.task_parameters.operation_control.position_control.velocity_threshold = (
        VELOCITY_THRESHOLD
    )
    return stage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="learn_to_choose_lowthresh_state.json",
        help="Path to write the trainer state JSON",
    )
    args = parser.parse_args()

    # Off-curriculum, manual one-off. The throwaway curriculum exists only to obtain a
    # TrainerState model typed to AindVrForagingTaskLogic (so stage.task serializes
    # correctly); it is NOT embedded (curriculum=None). is_on_curriculum=False makes the
    # rig launcher skip curriculum resolution/evaluation and run stage.task as stored.
    trainer = Trainer(
        create_curriculum(
            "SingleSiteChooseLowThresh",
            __semver__,
            (AindVrForagingTaskLogic,),
            pkg_location="one_off",
        )()
    )
    state = trainer.trainer_state_model(
        curriculum=None,
        stage=make_s_learn_to_choose_lowthresh(),
        is_on_curriculum=False,
        active_policies=None,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(state.model_dump_json(indent=2))
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
