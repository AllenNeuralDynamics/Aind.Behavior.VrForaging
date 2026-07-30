from aind_behavior_curriculum import MetricsProvider, Policy, Stage
from aind_behavior_services.task import distributions
from aind_behavior_vr_foraging import task_logic
from aind_behavior_vr_foraging.task_logic import AindVrForagingTaskLogic, AindVrForagingTaskParameters

from . import helpers
from .metrics import metrics_from_dataset
from .policies import (
    LEARN_TO_STOP_GEOMETRY_COMPRESSED,
    p_learn_to_run,
    p_learn_to_stop,
    p_reward_water_gate,
    p_seed_reward_delay,
)

# ============================================================
# T x D probability grid
# ============================================================
# The probability_grid_* stages draw each block's (p_A, p_B) from the orthogonal T x D
# factorial: T = p_A + p_B (richness) in {0.8, 1.0, 1.2}; D = p_A - p_B (relative value)
# in {-0.4, 0, +0.4}. Even probabilities in {0.2 .. 0.8} give the clean 3 T x 3 D = 9-cell
# grid, keeping every offered probability in the behaviorally-resolvable, orthogonal-design
# range. (This replaces the earlier sum-band over {0.1 .. 0.9}, which produced
# non-orthogonal |D| in {0.2, 0.4, 0.6, 0.8} and used the saturated 0.1/0.9 extremes.)
# round() guards binary-float drift (e.g. 0.2 + 0.6 == 0.8000000000000001).
PROBABILITY_GRID_REWARD_PROBABILITIES: tuple[float, ...] = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
PROBABILITY_GRID_ALLOWED_SUMS: frozenset[float] = frozenset({0.8, 1.0, 1.2})
PROBABILITY_GRID_ALLOWED_ABSD: frozenset[float] = frozenset({0.0, 0.4})
# Odor C is a fixed MID-value reference: pinned at the centre of the 0.2-0.8 A/B range, so
# its local value stays constant while T_AB / D_AB vary across blocks -- a stable anchor for
# context modulation. At 0.5 (vs the earlier 0.8 high-value setting) its P(stop) isn't
# ceilinged, so it still reads out engagement/context, and it stays distinct from the
# reversal pilot's alternating 0.3 / 0.7 pair rather than coinciding with the high odor.
PROBABILITY_GRID_ODOR_C_REWARD_PROBABILITY: float = 0.5

# --- Reversal pilot: an explicit, intentional block plan (played Sequential) ---
# What we measure: reversal n_adapt and how it scales with |D|, at fixed T=1.0 so |D| is
# isolated. sign(D) flips on EVERY transition (each boundary is a reversal), and |D| appears
# in BOTH directions (A-high and B-high) so value stays identifiable from odor identity.
#
# Redesign after the 2026-07-24 first sessions (860898/860900). Those ran a 6-block
# {0.4,0.4,0.2,0.2,0.6,0.6} ladder at ~60-80 patches/block and exposed:
#   - Engagement is front-loaded: only the first ~250-300 sites (~half the session) are
#     worked; both mice disengaged before reaching the |D|=0.6 blocks, so |D| was confounded
#     with session position (satiety). => rotate block order per session (see rotation below).
#   - Discrimination also collapses at the OTHER end: very thirsty (early/high-value) the mouse
#     stops at ~everything (900 hit a 0.96 stop ceiling), which suppresses selectivity too. So
#     discrimination needs an intermediate satiety band -- neither floor nor ceiling.
#   - |D|=0.2 looked unmeasurable (asymptote ~0), BUT every |D|=0.2 block ran either disengaged,
#     at the stop-ceiling, or mid-declining -- never in the good band. That verdict is
#     confounded with position, so |D|=0.2 is KEPT and rotation is relied on to finally give it
#     a fair (engaged, non-ceiling) test; drop it only if it still fails when sampled early.
#   - Where a clean rise existed (|D| 0.4/0.6), reversal settling was fast (~9-13
#     presentations/odor): floor ~ ramp 15 + plateau 10 = ~25/odor => ~53 sites. |D|=0.2's
#     n_adapt is still unmeasured, so it keeps a longer block (~65) for a possibly slower ramp.
#
# Block 0 is initial acquisition (warm-up), at the EASIEST contrast (|D|=0.6) for fast
# re-acquisition; it is a reversal only in the trivial sense and is discarded from n_adapt.
PROBABILITY_GRID_REVERSAL_PILOT_WARMUP: tuple[float, float] = (0.8, 0.2)  # |D|=0.6 A-high, discarded
# The recurring reversal menu: 6 distinct blocks covering {0.2, 0.4, 0.6} x {A-high, B-high} in
# a fixed cyclic order whose sign strictly alternates (-, +, -, +, -, +). Because it alternates
# and has even length, tiling it (and the rig's Repeat) keeps every boundary a reversal, and a
# cyclic shift by an EVEN number of steps preserves the leading sign -- which is how rotation
# swaps which |D| is met first without ever breaking sign-alternation.
PROBABILITY_GRID_REVERSAL_PILOT_MENU: tuple[tuple[float, float], ...] = (
    (0.3, 0.7),  # D=-0.4  B-high
    (0.8, 0.2),  # D=+0.6  A-high
    (0.4, 0.6),  # D=-0.2  B-high
    (0.7, 0.3),  # D=+0.4  A-high
    (0.2, 0.8),  # D=-0.6  B-high
    (0.6, 0.4),  # D=+0.2  A-high
)
# Block length (n_min, exp_mean, max) BY |D| for reversal blocks; warm-up has its own.
# Realized length ~ n_min + min(Exp(mean), max-n_min). |D|=0.2 is longer (n_adapt unmeasured,
# and the small value gap needs the mouse in the selective band longer to reveal a plateau).
PROBABILITY_GRID_REVERSAL_PILOT_WARMUP_LEN: tuple[int, float, float] = (60, 8, 80)  # ~67 sites
PROBABILITY_GRID_REVERSAL_PILOT_LEN_BY_ABSD: dict[float, tuple[int, float, float]] = {
    0.2: (55, 10, 80),  # ~65 sites
    0.4: (45, 8, 65),  # ~53 sites
    0.6: (45, 8, 65),  # ~53 sites
}
# How many reversal blocks to emit after the warm-up. Deliberately > what a mouse gets through
# in the engaged window (~5-6 blocks) so the rig never wraps back onto the warm-up mid-session.
PROBABILITY_GRID_REVERSAL_PILOT_N_REVERSAL_BLOCKS: int = 8

# Corridor geometry / stop shared by every stage after learn_to_stop (learn_to_choose
# and both probability_grid_* stages). The grid stages additionally set a stochastic
# `delay`; reward amount defaults to helpers.REWARD_AMOUNT_UL.
_POST_STOP_PATCH_KWARGS: dict[str, float] = {
    "inter_patch_min_length": 30,
    "inter_patch_mean_length": 60,
    "inter_patch_max_length": 190,
    "inter_site_length": 15,
    "reward_site_length": 50,
    "stop_duration": 1.0,
}


# ============================================================
# Stage definitions
# ============================================================


def _make_learn_to_stop_task() -> AindVrForagingTaskLogic:
    """Stage-1 task: teach a genuine stop within one session.

    Only the stop-velocity threshold is shaped, and quickly (GAIN on_success=0.93
    floors 60 -> 4 in ~37 rewarded stops) so the velocity slack closes early and
    most of the session is spent practicing real stops. Stop duration is held
    fixed at 1.0 s (no offset updater) to avoid the learn-low-then-fail-high trap.
    Geometry starts compressed (dense reward sites) and is eased toward full across
    sessions by p_learn_to_run; reward probability is gated by p_reward_water_gate.
    """
    return AindVrForagingTaskLogic(
        stage_name="learn_to_stop",
        task_parameters=AindVrForagingTaskParameters(
            rng_seed=None,
            updaters={
                task_logic.UpdaterTarget.STOP_VELOCITY_THRESHOLD: task_logic.NumericalUpdater(
                    operation=task_logic.NumericalUpdaterOperation.GAIN,
                    parameters=task_logic.NumericalUpdaterParameters(
                        initial_value=60, on_success=0.93, minimum=4, maximum=60
                    ),
                ),
            },
            environment=task_logic.BlockStructure(
                blocks=[
                    helpers.make_block(
                        p_rewards=(1.0, 1.0, None),
                        n_min_patches=100000,  # one block per session (never ends within a session)
                        make_patch_kwargs={**LEARN_TO_STOP_GEOMETRY_COMPRESSED, "stop_duration": 1.0},
                    ),
                ],
                sampling_mode="Sequential",
            ),
            operation_control=helpers.make_default_operation_control(velocity_threshold=60),
        ),
    )


def make_s_learn_to_stop() -> Stage:
    return Stage(
        name="learn_to_stop",
        task=_make_learn_to_stop_task(),
        start_policies=[Policy(p_learn_to_stop), Policy(p_reward_water_gate), Policy(p_learn_to_run)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_learn_to_choose() -> Stage:
    """High-contrast discrimination stage. Two odors, alternating blocks with
    p_reward (0.9, 0.1) and (0.1, 0.9). REWARD_DELAY_OFFSET ramps 0 -> 0.3 s within
    session, carried forward across learn_to_choose sessions via p_seed_reward_delay.
    Stop duration is held fixed at 1.0 s (established in learn_to_stop)."""
    return Stage(
        name="learn_to_choose",
        task=AindVrForagingTaskLogic(
            stage_name="learn_to_choose",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: task_logic.NumericalUpdater(
                        operation=task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=0.002, minimum=0, maximum=0.3
                        ),
                    ),
                },
                environment=task_logic.BlockStructure(
                    blocks=[
                        helpers.make_block(
                            p_rewards=(0.9, 0.1, None),
                            n_min_patches=60,
                            block_length_exp_mean=15,
                            block_length_max=100,
                            make_patch_kwargs=_POST_STOP_PATCH_KWARGS,
                        ),
                        helpers.make_block(
                            p_rewards=(0.1, 0.9, None),
                            n_min_patches=60,
                            block_length_exp_mean=15,
                            block_length_max=100,
                            make_patch_kwargs=_POST_STOP_PATCH_KWARGS,
                        ),
                    ],
                    # Two blocks only: Sequential gives clean A-rich -> B-rich
                    # alternation. Reversal timing is still unpredictable because
                    # each block's length is random (block_length_exp_mean).
                    sampling_mode="Sequential",
                ),
                operation_control=helpers.make_default_operation_control(velocity_threshold=4),
            ),
        ),
        start_policies=[Policy(p_seed_reward_delay)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def _probability_grid_blocks(
    n_min_patches: int,
    block_length_exp_mean: float,
    block_length_max: float,
    delay: distributions.Distribution,
) -> list[task_logic.Block]:
    """The 9-cell T x D grid (T in {0.8,1.0,1.2} x D in {-0.4,0,+0.4}), plus the 5%
    fixed mid-value reference odor C at p_C=0.5 (occupancy 0.475 / 0.475 / 0.05).

    C is a *fixed mid-value reference*: pinned at the centre of the 0.2-0.8 A/B range, so its
    local value stays constant while T_AB / D_AB / policy state vary across blocks — a clean
    anchor for context modulation and a near-engagement check (a disengaged mouse skips even
    a decent odor). At 0.5 its P(stop) isn't ceilinged, so it still reads out engagement.
    Shared by BOTH grid stages. (History: never-rewarded distractor p_C=0.0 -> 0.5 mid-value
    -> 0.8 high-value anchor -> 0.5 mid-value again; each change needs brief retraining.)"""
    make_patch_kwargs = {**_POST_STOP_PATCH_KWARGS, "delay": delay}
    return [
        helpers.make_block(
            p_rewards=(p_a, p_b, PROBABILITY_GRID_ODOR_C_REWARD_PROBABILITY),
            n_min_patches=n_min_patches,
            block_length_exp_mean=block_length_exp_mean,
            block_length_max=block_length_max,
            first_state_occupancy=[0.475, 0.475, 0.05],
            make_patch_kwargs=make_patch_kwargs,
        )
        for p_a in PROBABILITY_GRID_REWARD_PROBABILITIES
        for p_b in PROBABILITY_GRID_REWARD_PROBABILITIES
        if round(p_a + p_b, 1) in PROBABILITY_GRID_ALLOWED_SUMS
        and round(abs(p_a - p_b), 1) in PROBABILITY_GRID_ALLOWED_ABSD
    ]


def make_s_probability_grid_short_delay() -> Stage:
    """First probability-grid stage; absorbs the old `three_contrast` shaping.

    9-cell T x D grid plus the 5% mid-value reference odor C (p_C=0.5, shared with the
    terminal stage). The reward delay is a
    stochastic base (0.2 s floor + Exp, mean ~0.6 s) plus a `REWARD_DELAY_OFFSET`
    that ramps 0 -> 1.5 s within session (seeded across sessions by
    p_seed_reward_delay), growing patience on the grid while keeping trial-to-trial
    delay variance. This is still a shaping stage (non-stationary delay within a
    session), not a clean-analysis stage. Stop duration is fixed at 1.0 s."""
    return Stage(
        name="probability_grid_short_delay",
        task=AindVrForagingTaskLogic(
            stage_name="probability_grid_short_delay",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                updaters={
                    task_logic.UpdaterTarget.REWARD_DELAY_OFFSET: task_logic.NumericalUpdater(
                        operation=task_logic.NumericalUpdaterOperation.OFFSET,
                        parameters=task_logic.NumericalUpdaterParameters(
                            initial_value=0, on_success=0.01, minimum=0, maximum=1.5
                        ),
                    ),
                },
                environment=task_logic.BlockStructure(
                    blocks=_probability_grid_blocks(
                        n_min_patches=40,
                        block_length_exp_mean=10,
                        block_length_max=70,
                        delay=helpers.make_reward_delay(offset=0.2, mean=0.4, max_delay=2.5),
                    ),
                    sampling_mode="Random",
                ),
                operation_control=helpers.make_default_operation_control(velocity_threshold=4),
            ),
        ),
        start_policies=[Policy(p_seed_reward_delay)],
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def make_s_probability_grid_long_delay() -> Stage:
    """Terminal (ephys) stage: the 9-cell T x D grid with a stationary reward delay and no
    updaters.

    NB the stage name says "long_delay" for historical continuity (mice enroll under it),
    but the delay is now a **moderate, light-tailed stationary** exponential — see below.

    Delay: 0.2 s floor + Exp(mean 1.0 s), truncated to [0.2, 6.0] s (median ~0.9, mean
    ~1.1). The max was pushed 4 -> 6 s after the first pilot sessions: at the 4 s cap the
    mice waited through essentially the whole distribution (max delay actually waited ~3.9 s)
    and abandoned only ~2-3 %, so the endogenous patience deadline sits BEYOND 3.9 s and the
    delay never reached it. Raising only the max re-positions the exponential's existing tail
    (with mean 1.0, ~exp(-3.8) ~= 2 % of trials fall past 4 s) out to 4-6 s to LOCATE the
    deadline; it does NOT raise the abandonment *rate* (that tail fraction is set by the
    mean/rate, not the max -- lowering the rate would be needed to put more mass near the
    deadline, at the cost of lengthening every trial). Watch the first sessions: if the ~2 %
    tail now abandons in 4-6 s the deadline is bracketed; if they still wait it through, push
    the max further. Exponential (not Gaussian) so the mouse can't infer a precise
    leave-time, keeping abandonment an opportunity-cost decision.

    Block length: 80 + Exp(15), truncated [80, 120] presented patches (variable,
    identity-independent) -- deliberately long. This is a **block-length pilot**: the prior
    [30, 50] blocks (~17 presentations/odor) were too short to tell whether within-block
    selectivity converges. Over-long blocks (~45 presentations/odor, ~5 blocks/session)
    expose the full adaptation curve out to a clean plateau, so n_adapt can be fit and a
    shorter production B_min set afterward. Trades T x D breadth for adaptation depth; also
    improves block-identity recovery (each odor gets ~40 stops/block, so far fewer blocks
    drop out to a fully-skipped odor)."""
    return Stage(
        name="probability_grid_long_delay",
        task=AindVrForagingTaskLogic(
            stage_name="probability_grid_long_delay",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=task_logic.BlockStructure(
                    blocks=_probability_grid_blocks(
                        n_min_patches=80,
                        block_length_exp_mean=15,
                        block_length_max=120,
                        delay=helpers.make_reward_delay(offset=0.2, mean=1.0, max_delay=6.0),
                    ),
                    sampling_mode="Random",
                ),
                operation_control=helpers.make_default_operation_control(velocity_threshold=4),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


def reversal_pilot_plan(
    rotation: int = 0,
    n_reversal_blocks: int = PROBABILITY_GRID_REVERSAL_PILOT_N_REVERSAL_BLOCKS,
) -> list[tuple[float, float]]:
    """Ordered ``(p_A, p_B)`` plan for one session: warm-up + rotated reversal menu.

    ``rotation`` cyclically shifts the reversal menu by ``2*rotation`` steps (an even shift,
    so the leading sign -- and thus the reversal at the warm-up boundary -- is preserved).
    With the length-4 menu, ``rotation=0`` meets |D|=0.4 first and ``rotation=1`` meets
    |D|=0.6 first, counterbalancing |D| against the (satiety-limited) engaged window across
    sessions. The menu is then tiled to ``n_reversal_blocks``. Block 0 is the warm-up.
    """
    menu = PROBABILITY_GRID_REVERSAL_PILOT_MENU
    shift = (2 * rotation) % len(menu)
    rotated = menu[shift:] + menu[:shift]
    reversal = [rotated[i % len(rotated)] for i in range(n_reversal_blocks)]
    return [PROBABILITY_GRID_REVERSAL_PILOT_WARMUP, *reversal]


def _reversal_pilot_blocks(
    plan: list[tuple[float, float]],
    delay: distributions.Distribution,
) -> list[task_logic.Block]:
    """Build the explicit, ordered block list for a reversal-pilot ``plan``.

    Each ``(p_A, p_B)`` becomes one block (odor C held at the fixed mid-value reference).
    Block 0 gets the generous warm-up length; every later block gets its |D|-dependent
    reversal length. Order is preserved exactly -- the caller plays it ``Sequential`` -- so
    ``plan`` alone defines the design.
    """
    p_c = PROBABILITY_GRID_ODOR_C_REWARD_PROBABILITY
    make_patch_kwargs = {**_POST_STOP_PATCH_KWARGS, "delay": delay}
    blocks = []
    for i, (p_a, p_b) in enumerate(plan):
        n_min, exp_mean, b_max = (
            PROBABILITY_GRID_REVERSAL_PILOT_WARMUP_LEN
            if i == 0
            else PROBABILITY_GRID_REVERSAL_PILOT_LEN_BY_ABSD[round(abs(p_a - p_b), 1)]
        )
        blocks.append(
            helpers.make_block(
                p_rewards=(p_a, p_b, p_c),
                n_min_patches=n_min,
                block_length_exp_mean=exp_mean,
                block_length_max=b_max,
                first_state_occupancy=[0.475, 0.475, 0.05],
                make_patch_kwargs=make_patch_kwargs,
            )
        )
    return blocks


def make_s_probability_grid_reversal_pilot(rotation: int = 0) -> Stage:
    """Focused reversal-adaptation pilot (off-curriculum): an explicit, intentional block
    sequence played Sequential, designed to measure reversal n_adapt vs |D|.

    Why this exists. In a long-block session (~5 blocks) the 9-cell grid under Random
    sampling cannot guarantee the two things the adaptation measurement needs, and the first
    pilot sessions failed both: (1) *reversals at all* -- 860900 drew zero sign-flips; and
    (2) *both odors appearing as the high-value odor within one session* -- when odor A is
    never high (also 860900), value and odor identity are perfectly collinear and
    "discrimination" cannot be separated from a fixed odor preference. A scripted, sign-
    flipping sequence fixes both.

    Design (revised after the 2026-07-24 sessions -- see the module-level constants block for
    the data that drove each choice). ``reversal_pilot_plan(rotation)`` builds an ordered
    ``(p_A, p_B)`` list (all T=1.0): a warm-up block at the easiest contrast (|D|=0.6), then a
    sign-alternating menu covering |D| in {0.2, 0.4, 0.6} in both directions, tiled past the
    engaged window. ``sampling_mode="Sequential"`` plays it verbatim and the rig Repeat's it, so
    the plan *is* the design. Reversal blocks are short (~53 sites for |D| 0.4/0.6, ~65 for the
    harder |D|=0.2; ~67 warm-up) and stochastic in length so switch timing stays unpredictable.
    Block 0 is acquisition -- discard it from n_adapt.

    ``rotation`` counterbalances |D| against the satiety-limited engaged window by even-shifting
    the length-6 menu: rotation 0 meets |D|=0.4 first, rotation 1 meets |D|=0.2 first, rotation 2
    meets |D|=0.6 first. Cycle it per session (e.g. rotation = session_index % 3) via
    generate_reversal_pilot_state.py; the default 0 keeps this factory zero-arg-callable for the
    generic deploy tool.

    Delay / stop / velocity match the terminal grid stage (stationary, no updaters), incl.
    the delay max pushed to 6 s (see make_s_probability_grid_long_delay).
    """
    delay = helpers.make_reward_delay(offset=0.2, mean=1.0, max_delay=6.0)
    blocks = _reversal_pilot_blocks(reversal_pilot_plan(rotation), delay)
    return Stage(
        name="probability_grid_reversal_pilot",
        task=AindVrForagingTaskLogic(
            stage_name="probability_grid_reversal_pilot",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=task_logic.BlockStructure(blocks=blocks, sampling_mode="Sequential"),
                operation_control=helpers.make_default_operation_control(velocity_threshold=4),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )


# ------------------------------------------------------------
# D-family fixed-|D|=0.4 ABA diagnostic (off-curriculum)
# ------------------------------------------------------------
# Tests the ephys D-family (ephys_task_updates_since_upload.md): a strict A-high<->B-high
# alternation at fixed |D|=0.4, T=1.0 -- an ABA perturb-and-return whose within-neuron control
# is the return (blocks 1 & 3 same state). Purpose here is the Phase-2 readiness check: does a
# DIRECT |D|=0.4 reversal SETTLE within a block? The 07-27/28 pilot could not clear this (898's
# direct |D|=0.4 reversal did not settle by ~48 sites; 900 ceilinged), confounded by the ladder
# changing |D| every block. Here |D| is FIXED so only the sign flips -- a simpler, learnable
# structure that should settle faster.
#
# Block length is DIAGNOSTIC-LONG (~75 sites, above the intended final 55-65) so we can locate
# where the reversal settles rather than truncating it. Shrink toward 55-65 once n_adapt is known.
PROBABILITY_GRID_DFAMILY_A_HIGH: tuple[float, float] = (0.7, 0.3)  # |D|=0.4 A-high
PROBABILITY_GRID_DFAMILY_B_HIGH: tuple[float, float] = (0.3, 0.7)  # |D|=0.4 B-high
PROBABILITY_GRID_DFAMILY_LEN: tuple[int, float, float] = (65, 10, 90)  # ~75 sites, jittered
PROBABILITY_GRID_DFAMILY_N_BLOCKS: int = 5  # A,B,A,B,A -- blocks 0-2 are the primary ABA return


def dfamily_plan(
    start_high: str = "A",
    n_blocks: int = PROBABILITY_GRID_DFAMILY_N_BLOCKS,
) -> list[tuple[float, float]]:
    """Ordered ``(p_A, p_B)`` plan: strict A-high<->B-high alternation (fixed |D|=0.4, T=1.0).

    ``start_high`` in {"A", "B"} sets the first block; balance it across sessions (do not tie to
    a fixed calendar parity). With ``n_blocks=5`` the sequence is A,B,A,B,A (or B,A,B,A,B); blocks
    0-2 are the primary ABA perturb-and-return, blocks 3-4 are bonus repeats if still engaged.
    """
    if start_high not in ("A", "B"):
        raise ValueError(f"start_high must be 'A' or 'B', got {start_high!r}")
    first, second = (
        (PROBABILITY_GRID_DFAMILY_A_HIGH, PROBABILITY_GRID_DFAMILY_B_HIGH)
        if start_high == "A"
        else (PROBABILITY_GRID_DFAMILY_B_HIGH, PROBABILITY_GRID_DFAMILY_A_HIGH)
    )
    return [first if i % 2 == 0 else second for i in range(n_blocks)]


def make_s_probability_grid_dfamily(
    start_high: str = "A",
    reward_amount: float = helpers.REWARD_AMOUNT_UL,
    block_length: tuple[int, float, float] = PROBABILITY_GRID_DFAMILY_LEN,
    n_blocks: int = PROBABILITY_GRID_DFAMILY_N_BLOCKS,
) -> Stage:
    """D-family fixed-|D|=0.4 ABA diagnostic stage (off-curriculum), played Sequential.

    ``start_high`` picks the opening state (balance across sessions). ``reward_amount`` (uL)
    overrides the per-stop reward volume per mouse -- used to de-saturate the value axis for a
    ceiling-limited mouse (e.g. 860900 at 5 uL vs 860898 at the default 7). Odor C is held at the
    fixed mid-value reference (p_C=0.5, q_C=0.05); delay / stop / velocity match the terminal grid
    stage. See the constants block above for the design rationale.

    ``block_length`` is ``(n_min_patches, exp_mean, max)`` -- sites are drawn as
    ``n_min + Exp(exp_mean)`` truncated at ``max``. Lengthen it when a mouse perseverates and needs
    more sites to overcome a standing odor bias before the block ends. ``n_blocks`` trades against
    it: the engaged window is roughly a fixed ~250 sites regardless of how blocks are cut, so
    ``n_min * 3`` above ~250 pushes the ABA return block past the satiety cliff -- drop ``n_blocks``
    rather than let the return land in the disengaged tail.
    """
    p_c = PROBABILITY_GRID_ODOR_C_REWARD_PROBABILITY
    delay = helpers.make_reward_delay(offset=0.2, mean=1.0, max_delay=6.0)
    n_min, exp_mean, b_max = block_length
    make_patch_kwargs = {**_POST_STOP_PATCH_KWARGS, "delay": delay, "reward_amount": reward_amount}
    blocks = [
        helpers.make_block(
            p_rewards=(p_a, p_b, p_c),
            n_min_patches=n_min,
            block_length_exp_mean=exp_mean,
            block_length_max=b_max,
            first_state_occupancy=[0.475, 0.475, 0.05],
            make_patch_kwargs=make_patch_kwargs,
        )
        for (p_a, p_b) in dfamily_plan(start_high, n_blocks=n_blocks)
    ]
    return Stage(
        name="probability_grid_dfamily",
        task=AindVrForagingTaskLogic(
            stage_name="probability_grid_dfamily",
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=task_logic.BlockStructure(blocks=blocks, sampling_mode="Sequential"),
                operation_control=helpers.make_default_operation_control(velocity_threshold=4),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )
