"""Per-session OFF-CURRICULUM trainer state for the ephys D-family diagnostic.

Emits ``probability_grid_dfamily_start{A,B}[...]`` (fixed |D| A-high<->B-high ABA alternation,
T=1.0) as an off-curriculum trainer state (curriculum=null, is_on_curriculum=false) so the rig runs
the stage's task exactly as stored.

The stage name records the effective config: ``start_high`` always, and any knob that deviates from
the stage default. This matters because the name is the only handle the session record and the
analysis scripts have -- it is written to both ``trainer_state.json`` (``stage.name``) and
``tasklogic_input.json`` (``stage_name``). While the name was the bare ``probability_grid_dfamily``
for every variant, A-first and B-first sessions were indistinguishable without diffing the block
probabilities, and analysis pooled them under one name.

Defaults encode the 2026-08-10 redesign:

  * pair 0.9/0.1 -- the previous 0.7/0.3 put the low odor on the economic indifference point, so
    stopping at BOTH odors was correct and P(stop) could not separate them. 0.8/0.2 clears it for
    860900 but leaves 860898 on a knife edge, hence the wider pair. |D|=0.8 is above the 0.4 the
    ephys design wants; the intent is to walk it back down once the ABA return is established.
  * odor C off, ~45-site blocks, and an EVEN block count so the rig's block-list cycling keeps
    alternating instead of emitting two same-state blocks at the wrap.
  * compressed corridor (cycle 158 -> 132 cm, +19% reward sites) for throughput.

See ``single_site/stages.py`` for the derivation of each.

ALWAYS balance ``--start-high`` across sessions -- every session of the 07-29..08-07 run opened
A-high, which confounds odor identity with block position.

Examples:
    # 860898, opening B-high (the first B-start after 14 A-start sessions)
    #   -> stage probability_grid_dfamily_startB
    uv run python generate_dfamily_state.py --start-high B --output dfamily_898_state.json
    # 860900, same design; alternate --start-high on the next session
    #   -> stage probability_grid_dfamily_startA
    uv run python generate_dfamily_state.py --start-high A --output dfamily_900_state.json
    # a deviation is tagged, so it cannot be confused with the standard config
    #   -> stage probability_grid_dfamily_startA_p80-20
    uv run python generate_dfamily_state.py --start-high A --prob-pair 0.8 0.2 --output probe.json
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
        help="Odor that is high-value in the FIRST block. Balance across sessions -- leaving it "
        "fixed confounds odor identity with block position.",
    )
    parser.add_argument(
        "--reward-volume",
        type=float,
        default=None,
        help="Per-stop reward volume (uL). Omit to keep the stage default (7). Affects total "
        "water and motivation only -- NOT selectivity, which is invariant to reward amount.",
    )
    parser.add_argument(
        "--prob-pair",
        nargs=2,
        type=float,
        metavar=("P_HIGH", "P_LOW"),
        default=None,
        help="Reward probabilities as (high, low). Omit to keep the stage default (0.9 0.1). "
        "The pair must straddle the indifference probability p* (~0.30 for the pilot mice) or "
        "P(stop) cannot separate the odors.",
    )
    parser.add_argument(
        "--q-c",
        type=float,
        default=None,
        help="Odor-C occupancy fraction. Omit to keep the stage default (0.0 = C omitted). "
        "Use 0.05 to restore the old mid-value reference probe.",
    )
    parser.add_argument(
        "--geometry",
        choices=("compressed", "full"),
        default="compressed",
        help="Corridor geometry. 'compressed' (default) shortens the cycle 158->132 cm (+19% "
        "reward sites); 'full' restores the corridor the on-curriculum grid stages use.",
    )
    parser.add_argument(
        "--inter-patch",
        nargs=2,
        type=float,
        metavar=("MIN", "MEAN"),
        default=None,
        help="Override inter-patch offset and exponential mean (cm), on top of --geometry. MIN "
        "sets the worst-case odor-clearance gap; MEAN carries the timing jitter the ephys "
        "analysis needs (~1 s at MEAN=40), so cut MIN in preference to MEAN.",
    )
    parser.add_argument(
        "--velocity-threshold",
        type=float,
        default=None,
        help="Override the stop-velocity threshold (cm/s). Omit to keep the stage default (4).",
    )
    parser.add_argument(
        "--block-length",
        nargs=3,
        type=float,
        metavar=("MIN", "EXP_MEAN", "MAX"),
        default=None,
        help=(
            "Block length as n_min + Exp(EXP_MEAN) truncated at MAX. Omit to keep the stage "
            "default (40 5 55, ~45 sites). Size this from the engaged window (~140 sites over "
            "which the mice still discriminate), not from settling speed: three blocks must fit "
            "inside it or the ABA return lands after discrimination has already collapsed."
        ),
    )
    parser.add_argument(
        "--n-blocks",
        type=int,
        default=None,
        help="Number of alternating blocks. Omit to keep the stage default (4). Keep it EVEN: "
        "the rig cycles the block list, so an odd count yields two same-state blocks at the wrap.",
    )
    parser.add_argument(
        "--output", required=True, help="Path to write the trainer state JSON"
    )
    args = parser.parse_args()

    kwargs = {"start_high": args.start_high}
    if args.reward_volume is not None:
        kwargs["reward_amount"] = args.reward_volume
    if args.block_length is not None:
        b_min, b_mean, b_max = args.block_length
        kwargs["block_length"] = (int(b_min), b_mean, b_max)
    if args.n_blocks is not None:
        kwargs["n_blocks"] = args.n_blocks
    if args.prob_pair is not None:
        kwargs["prob_pair"] = (args.prob_pair[0], args.prob_pair[1])
    if args.q_c is not None:
        kwargs["q_c"] = args.q_c
    geom = dict(
        ss_stages.PROBABILITY_GRID_DFAMILY_GEOMETRY
        if args.geometry == "compressed"
        else ss_stages._POST_STOP_PATCH_KWARGS
    )
    if args.inter_patch is not None:
        geom["inter_patch_min_length"], geom["inter_patch_mean_length"] = (
            args.inter_patch
        )
    kwargs["geometry"] = geom
    if args.velocity_threshold is not None:
        kwargs["velocity_threshold"] = args.velocity_threshold
    stage = ss_stages.make_s_probability_grid_dfamily(**kwargs)

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
    blocks = stage.task.task_parameters.environment.blocks
    trunc = blocks[0].end_conditions[0].value.truncation_parameters
    patches = blocks[0].environment.patches
    reward = patches[0].reward_specification.amount.distribution_parameters.value
    probs = {
        p.label[-1]: p.reward_specification.probability.distribution_parameters.value
        for p in patches
    }
    seq = " -> ".join(
        "A"
        if p.environment.patches[
            0
        ].reward_specification.probability.distribution_parameters.value
        > 0.5
        else "B"
        for p in blocks
    )
    gen = patches[0].patch_virtual_sites_generator
    ip = gen.inter_patch.length_distribution
    ip_min = ip.truncation_parameters.min
    ip_mean = ip_min + 1.0 / ip.distribution_parameters.rate
    site_len = gen.reward_site.length_distribution.distribution_parameters.value
    inter_site = gen.inter_site.length_distribution.distribution_parameters.value
    cycle = site_len + 2 * inter_site + ip_mean
    print(
        f"Wrote {args.output}\n"
        f"  stage_name={stage.name}\n"
        f"  start_high={args.start_high}  sequence={seq}  n_blocks={len(blocks)}\n"
        f"  block_sites={trunc.min:.0f}-{trunc.max:.0f}  reward_uL={reward}\n"
        f"  p_reward={probs}  occupancy={blocks[0].environment.first_state_occupancy}\n"
        f"  geometry={args.geometry}: site={site_len:.0f} inter_site={inter_site:.0f} "
        f"inter_patch={ip_min:.0f}+Exp({1.0 / ip.distribution_parameters.rate:.0f})"
        f"->mean~{ip_mean:.0f} max={ip.truncation_parameters.max:.0f}\n"
        f"  cycle~{cycle:.0f} cm/site"
    )


if __name__ == "__main__":
    main()
