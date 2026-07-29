"""One-off OFF-CURRICULUM trainer state for any single_site stage, with overrides.

Emits a single_site stage as an off-curriculum trainer state (curriculum=null,
is_on_curriculum=false) so the rig runs the stage's task exactly as stored and does
NOT re-derive it from the curriculum definition (an on-curriculum Trainer.evaluate
rebuilds the task from the stage, resetting any overrides back to the curriculum
default). You advance the mouse back onto the real curriculum by hand when ready.

Generalizes the earlier single-stage one-offs (oneoff_learn_to_choose_lowthresh.py,
whose learn_to_choose + 4 cm/s case is just `--stage learn_to_choose
--velocity-threshold 4`).

Overrides (all optional; omit to keep the stage's curriculum value):
  --velocity-threshold  stop-velocity threshold (cm/s). Set on
    operation_control.position_control. NOTE: this only sticks on stages WITHOUT a
    STOP_VELOCITY_THRESHOLD updater (learn_to_choose, probability_grid_short_delay,
    probability_grid_long_delay). learn_to_stop shapes velocity via an in-session
    updater that would override operation_control; the script warns if you try.

Run from the Aind.Behavior.VrForaging repo, e.g. the final stage at 4 cm/s:
    uv run python oneoff_offcurriculum_stage.py \
        --stage probability_grid_long_delay --velocity-threshold 4 \
        --output probability_grid_long_delay_lowthresh_state.json
"""

import argparse
import inspect
import sys

from aind_behavior_curriculum import Stage, Trainer, create_curriculum
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic

from aind_behavior_vr_foraging_curricula import __semver__
from aind_behavior_vr_foraging_curricula.single_site import stages as ss_stages


def _build_stages() -> dict[str, Stage]:
    """Build every single_site stage keyed by its name.

    Discovers the ``make_s_*`` factories in ``single_site.stages`` and calls each
    (skipping any that require arguments). Each factory returns a fresh instance, so
    the returned stages do not alias curriculum state.
    """
    built: dict[str, Stage] = {}
    for name, fn in inspect.getmembers(ss_stages, inspect.isfunction):
        if not name.startswith("make_s_"):
            continue
        sig = inspect.signature(fn)
        if any(p.default is p.empty for p in sig.parameters.values()):
            continue  # factory needs args; not a zero-arg stage builder
        stage = fn()
        built[stage.name] = stage
    return built


def make_stage(stage_name: str, velocity_threshold: float | None) -> Stage:
    """Return the named single_site stage with the requested overrides applied."""
    stages = _build_stages()
    if stage_name not in stages:
        raise SystemExit(f"Unknown stage: {stage_name!r}. Available: {sorted(stages)}")
    stage = stages[stage_name]

    if velocity_threshold is not None:
        if (
            task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD
            in stage.task.task_parameters.updaters
        ):
            print(
                f"WARNING: stage {stage_name!r} has a STOP_VELOCITY_THRESHOLD updater; the "
                "in-session updater will override this operation_control value.",
                file=sys.stderr,
            )
        stage.task.task_parameters.operation_control.position_control.velocity_threshold = velocity_threshold

    return stage


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--stage",
        required=True,
        help="single_site stage name (e.g. probability_grid_long_delay)",
    )
    parser.add_argument(
        "--velocity-threshold",
        type=float,
        default=None,
        help="Override the stop-velocity threshold (cm/s). Omit to keep the stage default.",
    )
    parser.add_argument(
        "--output", required=True, help="Path to write the trainer state JSON"
    )
    args = parser.parse_args()

    stage = make_stage(args.stage, args.velocity_threshold)

    # Off-curriculum, manual one-off. The throwaway curriculum exists only to obtain a
    # TrainerState model typed to AindVrForagingTaskLogic (so stage.task serializes
    # correctly); it is NOT embedded (curriculum=None). is_on_curriculum=False makes the
    # rig launcher skip curriculum resolution/evaluation and run stage.task as stored.
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
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
