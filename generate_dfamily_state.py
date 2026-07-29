"""Per-session OFF-CURRICULUM trainer state for the ephys D-family diagnostic.

Emits ``probability_grid_dfamily`` (fixed |D|=0.4 A-high<->B-high ABA alternation, T=1.0) as an
off-curriculum trainer state (curriculum=null, is_on_curriculum=false) so the rig runs the stage's
task exactly as stored.

Phase-2 readiness use: test whether a DIRECT |D|=0.4 reversal settles within a block (blocks are
diagnostic-long ~75 sites here). ``--reward-volume`` overrides per-stop uL to de-saturate the value
axis for a ceiling-limited mouse. Balance ``--start-high`` across sessions.

Examples:
    # 860898: default 7 uL, start A-high
    uv run python generate_dfamily_state.py --start-high A --output dfamily_898_state.json
    # 860900: reduced 5 uL to break the stop-ceiling
    uv run python generate_dfamily_state.py --start-high A --reward-volume 5 \
        --output dfamily_900_state.json
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
        "--start-high",
        choices=("A", "B"),
        default="A",
        help="Opening high-value odor (A=0.7/0.3, B=0.3/0.7). Balance across sessions.",
    )
    parser.add_argument(
        "--reward-volume",
        type=float,
        default=None,
        help="Per-stop reward volume (uL). Omit to keep the stage default (7).",
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

    kwargs = {"start_high": args.start_high}
    if args.reward_volume is not None:
        kwargs["reward_amount"] = args.reward_volume
    stage = ss_stages.make_s_probability_grid_dfamily(**kwargs)
    if args.velocity_threshold is not None:
        stage.task.task_parameters.operation_control.position_control.velocity_threshold = args.velocity_threshold

    # Off-curriculum, manual one-off (cf. generate_reversal_pilot_state.py). The throwaway
    # curriculum only supplies a TrainerState model typed to AindVrForagingTaskLogic; it is NOT
    # embedded (curriculum=None), and is_on_curriculum=False runs stage.task verbatim.
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
    reward = args.reward_volume if args.reward_volume is not None else "default(7)"
    print(f"Wrote {args.output} (start_high={args.start_high}, reward_uL={reward})")


if __name__ == "__main__":
    main()
