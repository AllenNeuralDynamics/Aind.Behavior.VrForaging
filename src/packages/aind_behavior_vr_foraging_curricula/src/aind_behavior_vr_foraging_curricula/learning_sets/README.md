# LearningSets

A two-stage curriculum for the **learning-set** task: every session is a single block of
single-reward-site patches drawn from 7 odors. The odor ordering is regenerated each day
under the same pairing rules as
[`examples/task_learning_sets.py`](../../../../../../examples/task_learning_sets.py)
(each trial is a `(negative, positive)` pair; no odor that appeared in the last pair may
reappear). Each odor has a *positive* variant (always rewarded, p=1) and a *negative*
variant (always unrewarded, p=0). The curriculum shapes difficulty by gradually
**increasing the proportion of negative sites** rather than stepping reward probability.

## Background: Harlow's learning sets

The paradigm is inspired by Harry Harlow's classic *learning set* ("learning to learn")
experiments from the late 1940s–50s (Harlow, *The Formation of Learning Sets*,
Psychological Review, 1949). Harlow gave rhesus monkeys a long series of two-choice
object-discrimination problems: in each problem one object was consistently rewarded
and the other was not, but the rewarded object changed from problem to problem. Early
problems were solved slowly and trial-by-trial, but across hundreds of problems the
animals learned the *rule* itself — that one object is always correct — and eventually
solved each new problem in essentially a single trial ("win-stay, lose-shift"). The key
finding was that they were not just learning individual discriminations but acquiring a
transferable strategy: a learning set.

This curriculum recreates that structure in the VR foraging task. Each day presents
fresh `(negative, positive)` odor pairs drawn under the same rules, so the specific
rewarded odor keeps changing while the underlying rule stays constant — letting us ask
whether the animal forms a learning set and discriminates new pairs faster over time.

## Stages

| Stage | Neg sites / pair | Stop duration | Velocity threshold | Geometry | Reward µL |
|-------|-----------------|---------------|--------------------|----------|-----------|
| `shaping` | 0 → 1 → 3 → 5 (ramped across sessions) | ramps 0.1 → 3 s (within session) | shaped 60 → 8 cm/s | eased compressed → full | 6 default, trimmed in `graduated` |
| `graduated` | 5 (fixed, full 5+5 ratio) | 3 s (fixed) | 8 cm/s (fixed) | full (fixed) | trimmed toward water budget |

Within the `shaping` stage the difficulty knobs evolve concurrently:

- **Negative-site proportion** — session 1: all 10 sites per pair are positive (n_neg = 0,
  every stop is rewarded). Subsequent sessions walk `0 → 1 → 3 → 5` neg sites per pair via
  `N_NEG_RAMP`, while positive sites fill the remainder to keep the total fixed at 10. This
  means the animal first just learns to stop (session 1), then is progressively challenged
  to discriminate which odor is worth stopping for.
- **Speed** — the stop-velocity threshold (cm/s below which a stop counts) starts lenient
  (60 cm/s) and a GAIN updater drives it down to the final floor (8 cm/s) across sessions.
- **Geometry** — inter-patch spacing (mean/max `40/70 → 60/190`) and reward-site length
  (`25 → 40` cm) ease from compressed (easy, day-1) toward full, scaled by how many sites
  the subject travelled in the prior session (`n_patches_seen`). Inter-site spacing is
  fixed at 15 cm.
- **Stop duration** — a tiny operant base (0.1 s) plus a within-session offset that ramps
  to 3 s, so on the first days a brief dip below the velocity threshold earns reward by
  chance.

## Cross-session policies (`start_policies`)

- **`p_introduce_negative_sites`** (both stages) — reads `last_n_neg_sites_per_pair` from
  prior metrics, advances to the next step in `N_NEG_RAMP = (1, 3, 5)`, and regenerates
  `patch_indices` with the new neg/pos split. None → 0 (first session, all positive);
  saturates at 5. In the `graduated` stage the ramp is already at 5 and stays there.
- **`p_seed_stop_velocity`** (`shaping`) — starts the stop-velocity threshold a little
  above where the prior session floored (`× 1.2`, clamped to bounds). Dropped from
  `graduated`, which runs fixed at the floor.
- **`p_seed_stop_duration`** (`shaping`) — starts the stop-duration offset a little below
  where the prior session ended (`× 0.85`), so the subject re-ramps rather than being
  dropped at the longest stop.
- **`p_ease_geometry`** (`shaping`) — eases the geometry from compressed toward full,
  scaled by sites travelled in the prior session.
- **`p_water_cap`** (`graduated`) — if the prior session delivered more than 1.0 mL the
  per-reward amount is trimmed by 0.5 µL; if it fell below 0.7 mL the amount is raised by
  0.5 µL (both clamped to `[4, 8]` µL), steering total water toward the target window.

## Graduation

`shaping → graduated`: negative sites per pair have reached the full ratio (5) **and**
the stop-velocity threshold has been shaped to its final floor (8 cm/s) **and** the
subject is discriminating (visit ratio ≤ 0.7, i.e. skipping a meaningful fraction of
negative-odor patches).

## Metrics

`LearningSetsMetrics`: `total_water_consumed`, `n_patches_seen`, `n_patches_visited`,
`last_stop_duration_offset_updater`, `last_stop_velocity_threshold_updater`,
`last_n_neg_sites_per_pair`, `last_reward_amount`.
