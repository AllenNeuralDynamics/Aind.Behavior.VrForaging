from typing import Optional

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
# D-family ABA diagnostic (off-curriculum)
# ------------------------------------------------------------
# Tests the ephys D-family (ephys_task_updates_since_upload.md): a strict A-high<->B-high
# alternation at fixed |D|, T=1.0 -- an ABA perturb-and-return whose within-neuron control
# is the return (blocks 1 & 3 same state).
#
# 2026-08-10 REDESIGN after 14 sessions (860898/860900, 07-29..08-07) at 0.7/0.3 failed to
# produce an ABA return. The diagnosis is economic, not perceptual. Measured per-site time
# budget (t_stop = extra seconds a stop costs, t_travel = seconds per site not spent stopped):
# 898 (7.24, 4.08), 900 (5.54, 3.86). A stop is worth taking iff its reward probability exceeds
#
#     p* = t_stop * s * pbar / (t_travel + s * t_stop)
#
# (s = fraction of sites stopped at, pbar = mean reward prob over those sites; the reward AMOUNT
# cancels, which is why the 7->5 uL manipulation was null). Solved as an equilibrium this gives
# p* ~ 0.30 for both mice -- so at 0.7/0.3 the LOW odor sits essentially ON the indifference
# point (margins +0.03 and -0.01) and stopping at both odors is correct. 900 sat at "stop at
# everything" (P(stop|0.3) = 0.60), 898 just below it. The mice were right; the design was wrong.
#
# The pair must therefore straddle p*. What decides the choice is not the margin at the
# destination but the GRADIENT from where each mouse currently sits: both policies can be locally
# stable, and a better destination is worthless if nothing pushes the mouse out of the basin it is
# in. Evaluated at each mouse's measured stopping rates, under the compressed corridor below:
#
#             gradient from current       margin at destination
#   0.3/0.7   898 -0.110  900 -0.027      +0.06 / +0.03   both stuck (today)
#   0.2/0.8   898 +0.000  900 +0.077      +0.21 / +0.17   898 on a knife edge
#   0.1/0.9   898 +0.110  900 +0.181      +0.36 / +0.32   both move
#
# Hence 0.1/0.9. 898 gets no push at all from 0.2/0.8 -- its suppressed stopping drags its own
# reward rate down, which drags p* below 0.2 -- so the wider pair is what makes the manipulation
# work for BOTH mice rather than only the one the model fits well. It is also close to a regime
# both mice have already demonstrated: the older probability_grid_long_delay ran 0.0/0.9 and both
# correctly rejected the dead odor (P(stop|0.0) = 0.12 / 0.04).
#
# COST, and the intended ladder: |D|=0.8 is well above the 0.4 the ephys design wants, and the
# value axis is close to categorical here. That is deliberate sequencing, not the endpoint --
# establish that the ABA return works at all, then walk |D| back down (0.15/0.85, 0.2/0.8, ...)
# re-checking the gradient at each step, since every step the mice actually complete raises their
# reward rate and therefore p*, which makes the next narrower pair easier than it looks today.
#
# Odor C is OFF by default (q_c=0.0): at q_C=0.05 it was vestigial (its designed role is q_C=1/3
# in the deferred richness family), too sparse to read, and the two mice did opposite things with
# it (898 P(stop)=0.76-1.00 vs 900 0.00-0.13). Its channel assignment (odor_index=2) is positional
# in ``helpers.make_block``, so re-enabling it later restores the same channel.
PROBABILITY_GRID_DFAMILY_PAIR: tuple[float, float] = (0.9, 0.1)  # (p_high, p_low): |D|=0.8, T=1.0
PROBABILITY_GRID_DFAMILY_Q_C: float = 0.0  # odor-C occupancy; 0.0 omits the patch entirely

# Compressed corridor, D-FAMILY ONLY -- deliberately NOT folded into _POST_STOP_PATCH_KWARGS,
# which is shared with learn_to_choose and the on-curriculum grid stages.
#
# Purpose is throughput: 860898 runs a near-constant stint every session (duration CV 0.057,
# distance CV 0.071 -- 67.5 min / 1066 m) while its water varies 1.75x, so it is time/distance
# limited, not satiety limited. Shortening the cycle therefore converts directly into more reward
# sites, and a higher rate also widens 860900's gradient out of the stop-at-everything basin.
#
# What is NOT cut, and why:
#  - reward_site_length stays 50. It is load-bearing for 898, which approaches fast and needs the
#    distance to decelerate below the 4 cm/s stop threshold: its median stop is 34.8 cm into the
#    site with p75 at the 50 cm cap, so a 35 cm site would drop ~half its stops. (900 is the
#    opposite -- median 14.5 cm, 89% inside 35 -- but the corridor is kept common across mice.)
#  - The inter-patch EXPONENTIAL is cut only modestly (60 -> 40). Its spread is the dominant
#    source of inter-patch timing jitter (66-78% of Var(log duration); running speed supplies only
#    16-18%), and that jitter is what lets the ephys analysis separate odor-onset responses from
#    anticipatory ramping. SD 40 -> 33 cm keeps ~1.0 s of timing jitter, down from ~1.2 s.
#    Collapsing the exponential instead (e.g. to mean 5) would leave only ~0.3 s -- too little.
#  - The OFFSET is the efficient thing to cut: it adds to the mean while contributing no variance.
#    30 -> 25 matches the floor LEARN_TO_STOP_GEOMETRY_COMPRESSED already uses. It also sets the
#    worst-case odor-clearance gap, ~0.55 s at ~45 cm/s (was ~0.65 s) -- revisit if contamination
#    is ever suspected, since learn_to_stop is not an odor-discrimination stage.
#
# Net: inter-patch mean 78 -> 62 cm (SD 40 -> 34), cycle 158 -> 132 cm (-16.3%), +19.4% reward
# sites per unit distance. Clearance floor 0.67 -> 0.56 s at ~45 cm/s.
PROBABILITY_GRID_DFAMILY_GEOMETRY: dict[str, float] = {
    "inter_site_length": 10,  # was 15 (x2 per cycle); approach buffer, no decision cost
    "inter_patch_min_length": 25,  # was 30; offset adds mean without variance
    "inter_patch_mean_length": 40,  # was 60; the jitter-bearing term, cut conservatively
}
# Block length is set by the ENGAGED WINDOW, not by settling speed. Measured n_adapt is 8 (898)
# and 13 (900) odor-presentations, i.e. 16-26 sites -- well below any block length considered. The
# binding constraint is that the ABA return must land inside the ~140-site window over which the
# mice still discriminate: 3 blocks must fit, so n_min <= 46. At 50 only TWO blocks fit and the
# return falls outside the window, which is the failure being fixed. Re-derive both numbers after
# a session on the new pair -- a discriminable task should lengthen the window and shorten n_adapt.
PROBABILITY_GRID_DFAMILY_LEN: tuple[int, float, float] = (40, 5, 55)  # ~45 sites, jittered
# EVEN by construction: the rig cycles the block list (plan = block_index % n_blocks), so an odd
# count puts the last A-high block next to the first, producing a double-length A block at every
# wrap and silently breaking the alternation. Sessions routinely run past n_blocks.
PROBABILITY_GRID_DFAMILY_N_BLOCKS: int = 4  # A,B,A,B -- blocks 0-2 are the primary ABA return
PROBABILITY_GRID_DFAMILY_VELOCITY_THRESHOLD: float = 4.0  # cm/s stop gate

# Short tags for the corridor keys, used only when a caller deviates from the compressed default.
_DFAMILY_GEOMETRY_TAGS: dict[str, str] = {
    "inter_site_length": "is",
    "inter_patch_min_length": "ipmin",
    "inter_patch_mean_length": "ipmean",
    "inter_patch_max_length": "ipmax",
    "reward_site_length": "site",
    "stop_duration": "stop",
}


def dfamily_stage_name(
    start_high: str = "A",
    reward_amount: float = helpers.REWARD_AMOUNT_UL,
    block_length: tuple[int, float, float] = PROBABILITY_GRID_DFAMILY_LEN,
    n_blocks: int = PROBABILITY_GRID_DFAMILY_N_BLOCKS,
    prob_pair: tuple[float, float] = PROBABILITY_GRID_DFAMILY_PAIR,
    q_c: float = PROBABILITY_GRID_DFAMILY_Q_C,
    geometry: Optional[dict[str, float]] = None,
    velocity_threshold: float = PROBABILITY_GRID_DFAMILY_VELOCITY_THRESHOLD,
) -> str:
    """Stage name encoding the effective D-family config, e.g. ``..._startB_p80-20``.

    ``start_high`` is tagged UNCONDITIONALLY because it alternates session to session and is the
    one knob that must never be inferred from a filename: every session of the 07-29..08-07 run
    opened A-high, and because the name did not record it, analysis could not tell A-first from
    B-first sessions apart and pooled them under one stage name. Every other knob is tagged only
    when it deviates from the stage default, so the common case stays short and any name that
    carries an extra tag is a genuine deviation.
    """
    tags = [f"start{start_high.upper()}"]
    if tuple(prob_pair) != PROBABILITY_GRID_DFAMILY_PAIR:
        tags.append(f"p{100 * prob_pair[0]:.0f}-{100 * prob_pair[1]:.0f}")
    if q_c != PROBABILITY_GRID_DFAMILY_Q_C:
        tags.append(f"qC{100 * q_c:.0f}")
    if tuple(block_length) != PROBABILITY_GRID_DFAMILY_LEN:
        tags.append(f"bl{block_length[0]:g}-{block_length[2]:g}")
    if n_blocks != PROBABILITY_GRID_DFAMILY_N_BLOCKS:
        tags.append(f"x{n_blocks}")
    if reward_amount != helpers.REWARD_AMOUNT_UL:
        tags.append(f"{reward_amount:g}uL")
    if velocity_threshold != PROBABILITY_GRID_DFAMILY_VELOCITY_THRESHOLD:
        tags.append(f"vel{velocity_threshold:g}")
    # Resolve geometry exactly as the factory does, so the tag reflects what the rig will run.
    default = {**_POST_STOP_PATCH_KWARGS, **PROBABILITY_GRID_DFAMILY_GEOMETRY}
    geom = {**_POST_STOP_PATCH_KWARGS, **(PROBABILITY_GRID_DFAMILY_GEOMETRY if geometry is None else geometry)}
    if geom != default:
        diffs = [f"{_DFAMILY_GEOMETRY_TAGS.get(k, k)}{geom[k]:g}" for k in sorted(geom) if geom[k] != default.get(k)]
        tags.append("geom" + "-".join(diffs))
    return "_".join(["probability_grid_dfamily", *tags])


def dfamily_plan(
    start_high: str = "A",
    n_blocks: int = PROBABILITY_GRID_DFAMILY_N_BLOCKS,
    pair: tuple[float, float] = PROBABILITY_GRID_DFAMILY_PAIR,
) -> list[tuple[float, float]]:
    """Ordered ``(p_A, p_B)`` plan: strict A-high<->B-high alternation at fixed |D|.

    ``start_high`` in {"A", "B"} sets the first block; balance it across sessions (do not tie to
    a fixed calendar parity). ``pair`` is ``(p_high, p_low)``. With ``n_blocks=4`` the sequence is
    A,B,A,B (or B,A,B,A); blocks 0-2 are the primary ABA perturb-and-return. Keep ``n_blocks``
    even so the rig's block-list cycling preserves the alternation past the end of the list.
    """
    if start_high not in ("A", "B"):
        raise ValueError(f"start_high must be 'A' or 'B', got {start_high!r}")
    p_high, p_low = pair
    a_high, b_high = (p_high, p_low), (p_low, p_high)
    first, second = (a_high, b_high) if start_high == "A" else (b_high, a_high)
    return [first if i % 2 == 0 else second for i in range(n_blocks)]


def make_s_probability_grid_dfamily(
    start_high: str = "A",
    reward_amount: float = helpers.REWARD_AMOUNT_UL,
    block_length: tuple[int, float, float] = PROBABILITY_GRID_DFAMILY_LEN,
    n_blocks: int = PROBABILITY_GRID_DFAMILY_N_BLOCKS,
    prob_pair: tuple[float, float] = PROBABILITY_GRID_DFAMILY_PAIR,
    q_c: float = PROBABILITY_GRID_DFAMILY_Q_C,
    geometry: Optional[dict[str, float]] = None,
    velocity_threshold: float = PROBABILITY_GRID_DFAMILY_VELOCITY_THRESHOLD,
) -> Stage:
    """D-family fixed-|D| ABA diagnostic stage (off-curriculum), played Sequential.

    ``start_high`` picks the opening state -- balance it across sessions; leaving it fixed
    confounds odor identity with block position (all 14 sessions of the 07-29..08-07 run opened
    A-high). ``prob_pair`` is ``(p_high, p_low)``; it must straddle the indifference probability
    p* (~0.30 for both pilot mice) or P(stop) cannot separate the odors -- see the constants block
    above for the derivation. ``q_c`` is odor C's occupancy: 0.0 omits the patch, otherwise A and
    B split the remainder evenly and C runs at ``PROBABILITY_GRID_ODOR_C_REWARD_PROBABILITY``.

    ``reward_amount`` (uL) sets the per-stop volume. Note it does NOT affect selectivity: p* is
    invariant to reward amount because the rate scales with it, so use this for total-water and
    motivation only, never to de-saturate a ceilinged mouse.

    ``block_length`` is ``(n_min_patches, exp_mean, max)`` -- sites are drawn as
    ``n_min + Exp(exp_mean)`` truncated at ``max``. Size it from the engaged window, not from
    settling speed: three blocks must fit inside the window for the ABA return to land while the
    mouse still discriminates. ``n_blocks`` should stay EVEN (see the constants block).

    ``geometry`` overrides corridor lengths on top of ``_POST_STOP_PATCH_KWARGS``; it defaults to
    the compressed :data:`PROBABILITY_GRID_DFAMILY_GEOMETRY`. Pass ``_POST_STOP_PATCH_KWARGS`` (or
    ``{}``) to run the uncompressed corridor the on-curriculum grid stages use.

    The stage name is derived from the effective config by :func:`dfamily_stage_name`, so it always
    records ``start_high`` and any deviation from the defaults. Set ``velocity_threshold`` here
    rather than patching ``operation_control`` on the returned stage, or the name will not reflect
    what actually runs.
    """
    delay = helpers.make_reward_delay(offset=0.2, mean=1.0, max_delay=6.0)
    n_min, exp_mean, b_max = block_length
    if not 0.0 <= q_c < 1.0:
        raise ValueError(f"q_c must be in [0, 1), got {q_c}")
    p_c = PROBABILITY_GRID_ODOR_C_REWARD_PROBABILITY if q_c > 0 else None
    q_ab = (1.0 - q_c) / 2.0
    occupancy = [q_ab, q_ab] + ([q_c] if q_c > 0 else [])
    geom = PROBABILITY_GRID_DFAMILY_GEOMETRY if geometry is None else geometry
    make_patch_kwargs = {
        **_POST_STOP_PATCH_KWARGS,
        **geom,
        "delay": delay,
        "reward_amount": reward_amount,
    }
    blocks = [
        helpers.make_block(
            p_rewards=(p_a, p_b, p_c),
            n_min_patches=n_min,
            block_length_exp_mean=exp_mean,
            block_length_max=b_max,
            first_state_occupancy=occupancy,
            make_patch_kwargs=make_patch_kwargs,
        )
        for (p_a, p_b) in dfamily_plan(start_high, n_blocks=n_blocks, pair=prob_pair)
    ]
    name = dfamily_stage_name(
        start_high=start_high,
        reward_amount=reward_amount,
        block_length=block_length,
        n_blocks=n_blocks,
        prob_pair=prob_pair,
        q_c=q_c,
        geometry=geometry,
        velocity_threshold=velocity_threshold,
    )
    return Stage(
        name=name,
        task=AindVrForagingTaskLogic(
            stage_name=name,
            task_parameters=AindVrForagingTaskParameters(
                rng_seed=None,
                environment=task_logic.BlockStructure(blocks=blocks, sampling_mode="Sequential"),
                operation_control=helpers.make_default_operation_control(velocity_threshold=velocity_threshold),
            ),
        ),
        metrics_provider=MetricsProvider(metrics_from_dataset),
    )
