# STEP 30 — Portfolio Settings wiring (F1.6)

**Plan reference:** IMPLEMENTATION_PLAN.md → Phase F → F1.6 Portfolio Settings → "Portfolio page shows the user's target allocation alongside actual. Rebalance suggestion fires when actual drifts >5% from target. Benchmark line on the equity chart."
**Date:** 2026-05-02
**Status:** IN PROGRESS

---

## Honest scope (after investigation)

Settings → Portfolio captures 4 backend-supported fields:
- `portfolio_alloc` (object: `{crypto:30, stocks:30, forex:20, commodities:15, cash:5}`)
- `portfolio_preset` (`conservative` | `balanced` | `aggressive`)
- `portfolio_rebalance` (`monthly` | `quarterly` | `yearly`)
- `portfolio_benchmark` (ticker, e.g. `spy`)

Frontend stores `_settAlloc` as `[{label,pct}, ...]` array. Backend stores as object keyed by asset class. Translation needed at the boundary.

**Frontend gap:**
- `_settSaveAll` writes to localStorage but doesn't POST any portfolio fields to backend.
- `goDash` F1.7 doesn't load any portfolio fields.
- `showPortfolio` (Portfolio page) renders positions + VaR + heatmap + per-position charts. Does NOT reference target allocation, preset, rebalance, or benchmark anywhere.

**Plan promises (graded by feasibility):**
- Target allocation shown alongside actual: **DOABLE** — actual computed from `/api/positions` notional values.
- Rebalance suggestion at >5% drift: **DOABLE** — simple drift compare.
- Benchmark line on equity chart: **DEFERRED** — current equity chart in showPortfolio is illustrative random data; adding a benchmark line atop fake data would be theatre. Will revisit when real equity data exists.

**Step 30 wires:**
1. `_settSaveAll` POSTs `portfolio_alloc`, `portfolio_preset`, `portfolio_rebalance`, `portfolio_benchmark` (with array→object translation for alloc).
2. `goDash` F1.7 loads all 4 from backend (with object→array translation for alloc), respecting per-field touched-tracking from F1.13.5.
3. New touched-keys: `portfolio_alloc`, `portfolio_preset`, `portfolio_rebalance`, `portfolio_benchmark`. Each setter on Settings → Portfolio marks its key.
4. `showPortfolio` adds a "Target Allocation vs Actual" card showing each asset class with target %, actual % (from positions), and drift indicator. If any drift >5%, surface a "Rebalance recommended" callout.

Out of scope: benchmark equity-curve line; cadence (`_settCad`) which has no backend column.

---

## Success criteria — written before any code

1. **Backend persist** — clicking Save on Settings → Portfolio writes all 4 fields to `/api/settings`. GET returns matching values.

2. **Login load** — POST non-default values to backend, clear `dv_sett_alloc / dv_sett_psm / dv_sett_reb / dv_sett_bench` localStorage, reload, confirm `_settAlloc / _settPsm / _settReb / _settBench` populated from backend after F1.7.

3. **Touched tracking** — touching alloc / preset / rebalance / benchmark on Settings page sets `window._settTouched.portfolio_*`. F1.7 skips touched fields.

4. **Target Allocation panel renders on Portfolio page** — query DOM after `showPortfolio()`, confirm new panel exists with rows for each asset class showing target %.

5. **Actual % computed from positions** — query DOM, confirm actual % column shows numbers derived from `/api/positions` notional values (or "—" when no positions).

6. **Drift indicator** — for each row, confirm a status indicator (under / on / over target) reflects drift.

7. **Rebalance recommended callout** — when at least one asset class drifts >5%, a callout banner appears. When all drifts ≤5%, no banner.

8. **Independence** — saving portfolio settings doesn't reset chart-visuals / perf targets / assets / risk.

9. **No regression** — existing Portfolio page elements (positions table, VaR, heatmap, per-position charts) still render.

10. **F1.13.3 protection holds** — when `_settLoadedFromBackend=false`, _settSaveAll doesn't POST portfolio fields either (full POST suppressed).

---

## Verification methods

| # | Method |
|---|---|
| 1 | Mutate `_settAlloc/_settPsm/_settReb/_settBench`, call `_settSaveAll`, GET `/api/settings`, compare. |
| 2 | POST values to backend, clear 4 localStorage keys, reload, read 4 frontend vars after F1.7. |
| 3 | After interacting with each setter, confirm `window._settTouched.portfolio_*` is true. Then run F1.7 logic and confirm touched fields not overwritten. |
| 4 | Open Portfolio page, query DOM for new alloc-vs-actual panel. |
| 5 | Read DOM rows, confirm actual % column populated. |
| 6 | Read drift indicator class/text. |
| 7 | Set non-zero drift, confirm callout appears. Set zero drift, confirm no callout. |
| 8 | Change portfolio settings, verify other sub-panel state unchanged. |
| 9 | Confirm positions table / VaR / heatmap still render. |
| 10 | Set `_settLoadedFromBackend=false`, modify portfolio settings, call _settSaveAll, fetch backend → unchanged. |

---

## Did NOT test

- **Benchmark equity-curve line** — out of scope, current curve is illustrative.
- **Cadence (`_settCad`)** — no backend column; localStorage-only persists, behaviour unchanged.
- **Rebalance scheduler firing on schedule** — that's a backend job, not in scope.

---

## Results — to be filled

| # | Criterion | Method ran | Raw evidence | PASS/FAIL |
|---|---|---|---|---|
| 1 | persist | | | |
| 2 | login load | | | |
| 3 | touched tracking | | | |
| 4 | panel renders | | | |
| 5 | actual % populated | | | |
| 6 | drift indicator | | | |
| 7 | rebalance callout | | | |
| 8 | independence | | | |
| 9 | no regression | | | |
| 10 | F1.13.3 holds | | | |

---

## Commit log (this step)

(To be appended)
