# D5 Entry Engine — What It Does, Why It's Off, and How to Turn It On

## What it does

`entry_engine.py` is the DotVerse D5 conditional entry/decision engine.  Given
a trade setup (DataFrame, entry price, direction, stop, target, account risk),
it calls the SMC detectors from `smc_structure.py` — order blocks, inducement
zones, liquidity-trap risk, and structural context — then proposes one of three
plan modes:

| Mode | Meaning |
|---|---|
| `single` | Full-size entry at market (conservative default) |
| `scale_in` | 2-leg split: portion at market + portion at OB zone mid |
| `wait` | Annotate the signal as "not yet" with a plain-English reason |

Every plan carries:
- `total_risk` always equal to `account_risk_amount` (asserted in tests)
- `legs` with fractions summing to 1.0 (invariant enforced)
- At most 3 legs (hard limit)
- `decision_basis`: one human sentence naming the evidence
- `evidence`: list of plain-English structural observations
- `rule_statuses`: current proof status of every rule
- `analysis`: full detector outputs + hypothetical mode, so the UI can show
  "here is what the engine sees" without any live plan being affected

### calibrated_win_chance

The `calibrated_win_chance(features, history_df)` stub intentionally returns
`(None, explanation_string)` until ≥100 real closed trades are available.  It
will later anchor to the user's trade journal via Platt-scaled logistic
regression.  Invented probabilities are explicitly forbidden.

---

## Why it is gated off

The `enabled` parameter defaults to `False`.  When disabled, the engine
returns a single-entry plan and populates `analysis` with what it *would*
consider — purely for UI transparency.  It has zero authority over live
entries.

**All four rules are currently `unproven`:**

| Rule | Backtest file | Gate result | Synthetic? | Status |
|---|---|---|---|---|
| `ob_retest` | ob_retest_summary.json | PASS | Yes (`use_fallback=true`) | unproven |
| `idm_wait` | idm_summary.json | PASS | Yes (caveat flag) | unproven |
| `trap_avoidance` | trap_avoidance_summary.json | **FAIL** | Yes (caveat flag) | **failed** |
| `structure_context` | density_summary.json | n/a | Yes (caveat flag) | unproven |

Synthetic-data backtests verify that the detectors *emit signals in expected
proportions* and that the entry mechanics are *implemented correctly*.  They
do NOT constitute evidence of a live edge.  `ob_retest` technically passed the
gate criterion on synthetic paths, but its backtest used Monte Carlo forward
paths (`use_fallback=true`) — not real OHLCV klines — so it still loads as
`unproven`.

`trap_avoidance` was a **gate fail** even on synthetic data: B avg_R was lower
than A, drawdown worsened, and MAE increased.  This rule must not be promoted
until a real-data run shows a positive edge.

---

## Promotion path — how to turn a rule on

A rule may only influence a live plan after ALL of the following steps are
complete:

### Step 1 — Real-kline backtest

Re-run the per-rule backtest script against real OHLCV klines (not Monte Carlo
/ synthetic paths).  Minimum bar count: ≥500 real closed trades per class
(timeframe × direction × symbol).

Backtest scripts:
- `research/ob_retest_backtest.py` → replace synthetic forward paths with real
  OHLCV fetched from Binance or MT5 1-min/tick data
- `research/idm_backtest.py`
- `research/trap_avoidance_backtest.py`
- `research/density_measurement.py`

### Step 2 — Gate criteria (per class)

For a rule to pass:
- Strategy B avg_R > Strategy A avg_R
- Strategy B max_dd_R ≤ Strategy A max_dd_R
- `gate_pass: true` in the output JSON
- **No synthetic-data markers** in the JSON (no `caveat` key, no
  `use_fallback: true`)

### Step 3 — Omar reviews and promotes

Once the real-kline backtest JSON is saved (overwriting the synthetic one),
re-run `_load_rule_registry()` and confirm the rule loads as `proven`.  Omar
explicitly reviews the per-class breakdown (TF, direction, symbol) and sets the
JSON as the authoritative source.

### Step 4 — Staging verification

Deploy to the staging environment.  Call `propose_entry_plan(..., enabled=True)`
on at least 10 representative setups.  Confirm:
- The UI shows updated plan annotations
- `decision_basis` strings are sensible
- No rules alter plans they should not alter

### Step 5 — Production deploy

Merge to `main`, bump the cache version, deploy.  Monitor the first 50 live
signals; confirm no unexpected `scale_in` or `wait` annotations.

---

## What the fixed 3-leg scale-out study showed

A fixed 3-leg scale-out applied uniformly across all 1,087 trades produced
−0.014R avg vs −0.004R for single entry
(`research/scalein_vs_single_summary_ALL.json`).  Fixed rules are therefore
**forbidden**.  All multi-leg decisions must be per-trade and evidence-based —
only when a fresh OB sits on the correct side of the entry does the engine
propose a 2-leg split.
