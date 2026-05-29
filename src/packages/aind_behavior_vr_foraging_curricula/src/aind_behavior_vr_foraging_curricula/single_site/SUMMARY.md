# Single Site Curriculum Summary

This document summarizes how the Single Site curriculum progresses and how task logic changes across stages.

## High-Level Progression

The curriculum is defined in `curriculum.py` and stages are built in `stages.py`.

Progression order:

1. `learn_to_stop`
2. `learn_to_stop_low_p` (fallback path)
3. `learn_to_choose`
4. `three_contrast`
5. `probability_grid_short_delay`
6. `probability_grid_long_delay`

Important behavior:

- From `learn_to_stop`, two transitions are registered:
  - Promote directly to `learn_to_choose` if saturation is met.
  - Otherwise fallback to `learn_to_stop_low_p` (unconditional `True`).
- This depends on transition evaluation order (promote check is added before fallback check).

## Transition Gates

| From stage | To stage | Gate condition |
| --- | --- | --- |
| `learn_to_stop` | `learn_to_choose` | `_learn_to_stop_saturation_met`: `last_stop_threshold_updater <= 8`, `last_stop_duration_offset_updater >= 1.0`, `n_patches_seen >= 300`, `n_patches_visited >= 150` |
| `learn_to_stop` | `learn_to_stop_low_p` | Always `True` fallback |
| `learn_to_stop_low_p` | `learn_to_choose` | Same `_learn_to_stop_saturation_met` gate |
| `learn_to_choose` | `three_contrast` | `n_patches_seen >= 200`, `n_patches_visited >= 50`, `visit_ratio = n_patches_visited/n_patches_seen <= 0.7`, `last_reward_delay_offset_updater >= 0.25` |
| `three_contrast` | `probability_grid_short_delay` | `n_patches_seen >= 250`, `n_patches_visited >= 80`, `0.3 <= visit_ratio <= 0.7`, `last_reward_delay_offset_updater >= 1.3`, `last_stop_duration_offset_updater <= -0.4` |
| `probability_grid_short_delay` | `probability_grid_long_delay` | `n_patches_seen >= 300`, `n_patches_visited >= 100`, `0.3 <= visit_ratio <= 0.7` |

## Main Task-Logic Changes By Stage

| Stage | Core objective | Odor/reward structure | Updaters | Start policy seeding | Key timing settings |
| --- | --- | --- | --- | --- | --- |
| `learn_to_stop` | Shape stop behavior with easy rewards | 2 odors (`A`, `B`) with `p_reward=(1.0, 1.0)` | `STOP_DURATION_OFFSET`: `0 -> 1.0` (`on_success=+0.0067`), `STOP_VELOCITY_THRESHOLD`: `60 -> 8` (`on_success=0.987`) | `p_learn_to_stop` seeds both stop updaters from previous session | `stop_duration=0.25`, velocity threshold in operation control = `60` |
| `learn_to_stop_low_p` | Same as S1, lower reward probability fallback | 2 odors with `p_reward=(0.8, 0.8)` | Same two stop updaters as S1 | `p_learn_to_stop` | Same as S1 |
| `learn_to_choose` | High-contrast discrimination between two odors | Two random blocks: `(0.9, 0.1)` and `(0.1, 0.9)` | `REWARD_DELAY_OFFSET`: `0 -> 0.3` (`on_success=+0.002`) | `p_seed_reward_delay` | `stop_duration=1.5`, velocity threshold = `8` |
| `three_contrast` | Expand to mirrored 3-contrast set, coupled delay/stop shaping | Five blocks: `(0.1,0.9)`, `(0.9,0.1)`, `(0.3,0.7)`, `(0.7,0.3)`, `(0.5,0.5)` | `REWARD_DELAY_OFFSET`: `0 -> 1.5` (`+0.005`), `STOP_DURATION_OFFSET`: `0 -> -0.5` (`-0.005`) | `p_seed_reward_delay` and `p_seed_stop_duration` | Base patch `stop_duration=1.5`, velocity threshold = `8` |
| `probability_grid_short_delay` | Begin graduated task with narrower delay variance | 13 blocks from 5x5 `p_A/p_B` grid (keeping summed prob in `{0.8, 1.0, 1.2}`) plus distractor `C` with `p=0.0` and occupancy `[0.475, 0.475, 0.05]`; per-site offered rate 0.38-0.57 | No updaters | None | Fixed `stop_duration=1.0`, delay sampled from truncated exponential: `offset=0.5`, `char=1.5`, max `5.25` |
| `probability_grid_long_delay` | Final graduated regime with wider delay range | Same 13-block probability grid as previous stage | No updaters | None | Fixed `stop_duration=1.0`, delay sampled from truncated exponential: `offset=0.0`, `char=2.1`, max `7.0` |

## Probability-Grid Band Design (stages 5–6)

Both `probability_grid_*` stages draw their blocks from the 5x5 grid of
`(p_A, p_B)` pairs over `GRADUATED_REWARD_PROBABILITIES = {0.1, 0.3, 0.5, 0.7, 0.9}`,
filtered to a **symmetric band** of summed reward probability:
`GRADUATED_ALLOWED_PROBABILITY_SUMS = {0.8, 1.0, 1.2}` (`round(p_A + p_B, 1)`
guards binary-float drift such as `0.1 + 0.7 == 0.7999999999999999`). This yields
**13 blocks** (vs the full 24-block `sum >= 0.4` grid).

Each block is a single fixed joint `(p_A, p_B)` pair: both odor probabilities are
**coupled** — set together at the block boundary and held constant for the block
(`probability = scalar_value(p_reward)`, no in-patch baiting/`PersistentRewardFunction`
in this no-matching variant). `sampling_mode="Random"` selects among the enumerated
joint pairs; only the per-visit Bernoulli reward realization is drawn independently.

The band carries two contrast axes simultaneously:

- **Relative value** — `|p_A - p_B|` (the matching signal), present at
  `{0.0, 0.2, 0.4, 0.6, 0.8}`.
- **Absolute value** — the summed reward probability / environment richness,
  present at `{0.8, 1.0, 1.2}`.

Per-site offered reward rate is `0.475 * (p_A + p_B)` (odors A/B at occupancy 0.475
each, dry distractor C at 0.05 with `p=0.0`), so blocks span **0.38 / 0.475 / 0.57**
per site. Mean summed prob is exactly 1.0, so the mean offered rate is ~0.475/site.

**Why the band is bounded on both sides (symmetric around sum = 1.0):**

- The achievable relative contrast `|p_A - p_B|` (and the reward ratio `p_A : p_B`)
  peaks at sum = 1.0 and falls off symmetrically; sums outside `[0.8, 1.2]` can only
  produce weak contrasts (e.g. `(0.9, 0.9)` at sum 1.8 has zero relative signal).
  The band keeps exactly the sums that can still reach `|diff| >= 0.6`.
- The **floor** (`>= 0.8`) lifts the worst-case per-site rate from 0.19 (the old
  `sum >= 0.4` blocks) to 0.38, so an animal landing in a lean block for 40+ patches
  is not reward-starved.
- The **cap** (`<= 1.2`) keeps mean richness symmetric and prevents rich-everywhere
  blocks that suppress the incentive to skip/discriminate — those push the visit
  ratio toward 1.0, which is both uninformative and would fail the `0.3 <= visit_ratio
  <= 0.7` transition gates out of the graduated stages.

To make a reward-starved animal's sessions easier, prefer raising the floor / reward
amount / shifting the whole band up uniformly over un-capping, since un-capping buys
reward with low-contrast blocks.

## Shared Task-Building Defaults

- `make_patch` creates one-harvest-one-reject patch terminators and non-operant reward collection.
- `make_block` builds a patch-count-limited block with an exponential draw and truncation.
- `make_operation_control` keeps movable spout disabled and uses stage-specific velocity threshold.

## Metrics Used For Progression

The metrics provider is `metrics_from_dataset` in `metrics.py`.

- `n_patches_visited`: count of `ChoiceFeedback` events.
- `n_patches_seen`: total `ActivePatch` events across patch indices in block 0.
- `last_stop_threshold_updater`, `last_stop_duration_offset_updater`, `last_reward_delay_offset_updater`: final observed updater values in session.
- `total_water_consumed`: summed `GiveReward` in mL.

Note: in practice, `n_patches_visited` is closer to "choices made" and `n_patches_seen` is closer to "ActivePatch event count".
 
