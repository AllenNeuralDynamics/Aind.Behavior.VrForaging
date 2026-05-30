# Single Site curriculum

A **single-site, non-baited** patch-foraging bandit, similar to the dynamic
foraging uncoupled, unbaited task. Each patch is one odor-marked reward site (a
single accept/reject decision; no stored/baited reward). Two reward odors carry
block-switching reward probabilities, so the animal must track relative action
value. Code: `metrics.py`, `stages.py`, `policies.py`, `helpers.py`, `curriculum.py`.

## Stages

Four stages, in order; the first three shape, the last is terminal.

```
learn_to_stop → learn_to_choose → probability_grid_short_delay → probability_grid_long_delay
```

| stage | goal | environment | within-session updater | stop / delay |
|---|---|---|---|---|
| `learn_to_stop` | a real stop in one session | 2 odors A,B, both `p_reward=1.0` | `STOP_VELOCITY_THRESHOLD` 60→8 (gain ×0.93) | stop **1.0 s** (fixed); delay 0.5 s |
| `learn_to_choose` | high-contrast discrimination | alternating `(0.9, 0.1)` / `(0.1, 0.9)` blocks | `REWARD_DELAY_OFFSET` 0→0.3 (+0.002) | stop 1.0 s; delay 0.5→0.8 s |
| `probability_grid_short_delay` | grid + grow patience | 13-block band + distractor C (occ `0.475/0.475/0.05`) | `REWARD_DELAY_OFFSET` 0→1.5 (+0.01) | stop 1.0 s; delay `0.2 + Exp(0.4)`, [0.2, 2.5] s + the ramp |
| `probability_grid_long_delay` | terminal / analysis | same 13-block band | none | stop 1.0 s; delay `0.2 + Exp(2.1)`, [0.2, 7.0] s (stationary) |

Reward is 7 µL; velocity threshold is 8 cm/s from `learn_to_choose` on; `learn_to_stop`
starts at 60.

## Transition gates

| from → to | fires when |
|---|---|
| `learn_to_stop` → `learn_to_choose` | `last_stop_threshold_updater ≤ 8`, `n_seen ≥ 250`, `n_visited ≥ 150` |
| `learn_to_choose` → `probability_grid_short_delay` | `last_reward_delay_offset_updater ≥ 0.25`, `n_seen ≥ 200`, `n_visited ≥ 50`, `visit_ratio ≤ 0.7` |
| `probability_grid_short_delay` → `probability_grid_long_delay` | `last_reward_delay_offset_updater ≥ 1.3`, `n_seen ≥ 300`, `n_visited ≥ 100`, `0.3 ≤ visit_ratio ≤ 0.7` |

`visit_ratio = n_patches_visited / n_patches_seen`.

## Cross-session policies (start policies)

Applied on the next in-session day; on a stage transition the task resets to its
defaults and these apply from the following session.

- `p_learn_to_stop` — seed `STOP_VELOCITY_THRESHOLD` from the prior session end ×1.2
  (eased), clamped to [8, 60].
- `p_reward_water_gate` — hold `p_reward = 1.0` while the prior session collected
  < 0.6 mL water; drop to 0.8 once the animal reliably earns. Keys on water actually
  collected, so a non-earning animal is never penalized.
- `p_learn_to_run` — ease `learn_to_stop` geometry from compressed toward full,
  scaled by prior locomotion (`n_patches_seen / 150`).
- `p_seed_reward_delay` — seed `REWARD_DELAY_OFFSET` from the prior session end ×0.8.

## Probability-grid band

Blocks are `(p_A, p_B)` pairs from the 5×5 grid over `{0.1, 0.3, 0.5, 0.7, 0.9}`,
kept only where the **summed** reward probability is in `{0.8, 1.0, 1.2}` → **13
blocks** (vs the full 24). This holds environmental reward rate roughly constant
(per-site offered rate 0.38–0.57) while preserving relative-value contrast
`|p_A − p_B|` up to 0.8 — so an unlucky block can't reward-starve the animal, and
no rich-everywhere block kills the incentive to skip.

## Corridor geometry (cm)

| stage | reward site | inter-site | inter-patch |
|---|---|---|---|
| `learn_to_stop` (compressed → full) | 25 → 40 | 10 → 15 | `25 + Exp(50)`, [25,90] → `50 + Exp(120)`, [50,150] |
| later stages | 50 | 15 | `30 + Exp(60)`, [30,190] |

## Metrics (`metrics_from_dataset`)

`n_patches_visited` = `ChoiceFeedback` count · `n_patches_seen` = `ActivePatch` count ·
`last_{stop_threshold,reward_delay_offset}_updater` = last value of the in-session
updater · `total_water_consumed` = summed `GiveReward` (mL).
