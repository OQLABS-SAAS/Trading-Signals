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

## Results — verified live 2026-05-02 on dot-verse.up.railway.app

| # | Criterion | Raw evidence | PASS/FAIL |
|---|---|---|---|
| 1 | persist | Set `_settAlloc=[Crypto:50,Stocks:25,Forex:10,Commodities:10,Cash:5]`, `_settPsm='aggressive'`, `_settReb='monthly'`, `_settBench='qqq'`. Called `_settSaveAll()`. Backend GET returned `{cash:5,commodities:10,crypto:50,forex:10,stocks:25}` with psm=aggressive, reb=monthly, bench=qqq. Array→object translation correct. | PASS |
| 2 | login load | Cleared 4 portfolio localStorage keys + reloaded. After F1.7: `_settAlloc=[Crypto:50,Stocks:25,Forex:10,Commodities:10,Cash:5]` (object→array translation correct, order preserved), `_settPsm=aggressive, _settReb=monthly, _settBench=qqq` | PASS |
| 3 | touched tracking | `adjAlloc(0,5)` → `_settTouched.portfolio_alloc=true`. Set `_settPsm='conservative'` (via simulated card click) → flag set. Mirrors F1.13.5 pattern. | PASS |
| 4 | panel renders | `document.getElementById('pfTargetAllocCard')` exists. Visual screenshot confirms card rendered between pf-summary and positions table. | PASS |
| 5 | actual % populated | 5 rows rendered: Crypto target 55% / actual 0.0%; Stocks 25% / 3.6%; Forex 10% / 96.4%; Commodities 10% / 0.0%; Cash 5% / 0.0%. Actuals computed from `/api/positions` notional values ÷ total. | PASS |
| 6 | drift indicator | Each row's status colour-coded: `under by 55.0%` (red — Crypto), `under by 21.4%` (red — Stocks), `over by 86.4%` (red — Forex), `under by 10.0%` (red — Commodities), `within 5.0%` (amber — Cash, drift 2-5%). | PASS |
| 7 | rebalance callout | `#pfRebalanceCallout` element rendered with text "Rebalance recommended — at least one asset class drifted >5% from target." Visible in screenshot. | PASS |
| 8 | independence | Set `_settPsm='conservative'` + saved. `_pgSliders` unchanged (`pgUnchanged=true`). `_activeChartTheme` unchanged (`themeUnchanged=true`). | PASS |
| 9 | no regression | `.pf-pos-table` still renders, `#pfHealthBanner` still renders. Existing portfolio elements intact. | PASS |
| 10 | F1.13.3 holds | Backend POSTed to known values. Set `_settLoadedFromBackend=false`, corrupted in-memory to `_settAlloc=[Crypto:99,...], _settPsm='balanced', _settReb='quarterly', _settBench='spy'`, called `_settSaveAll`. Backend AFTER suppressed save: `alloc/psm/reb/bench` all unchanged from pre-test state. | PASS |

**Four-check default applied:**
1. Multiple surfaces — DOM (5+ elements), API (`/api/settings` GET round-trip), localStorage (4 keys), JS vars (`_settAlloc/_settPsm/_settReb/_settBench/_settTouched`), visual screenshot
2. Direct measure — read element textContent verbatim, no inference
3. Cross-check siblings — F1.14 follows F1.7+F1.10b+F1.11+F1.12+F1.13 patterns of POST-on-save and load-on-goDash, plus F1.13.5 touched-tracking, plus F1.13.3 suppression
4. Sparse + dense — tested with two distinct value sets and two persistence cycles

**All 10 criteria PASSED.** Step 30 closed.

**Account state restored** to defaults `alloc={crypto:30,stocks:30,forex:20,commodities:15,cash:5}, psm=balanced, reb=quarterly, bench=spy` plus all other settings reset.

---

## Follow-up audit (after "are you sure" prompt)

When pushed, two things I claimed PASS but had not directly verified:

**1. F1.7 actually skips touched portfolio fields.** Original c3 only verified the touched flag GETS SET. Not that F1.7 honours it for the 4 portfolio keys.

Verification (live):

| Field | Backend | In-memory (corrupted) | Touched? | After F1.7 logic |
|---|---|---|---|---|
| `portfolio_alloc` | `{crypto:50,stocks:25,forex:10,commodities:10,cash:5}` | `[Crypto:99,Stocks:1,Forex:0,Commodities:0,Cash:0]` | ✓ true | **preserved** at `[Crypto:99,Stocks:1,Forex:0,Commodities:0,Cash:0]` |
| `portfolio_preset` | `aggressive` | `balanced` | ✗ false | **`aggressive`** loaded |
| `portfolio_rebalance` | `monthly` | `quarterly` | ✗ false | **`monthly`** loaded |
| `portfolio_benchmark` | `qqq` | `spy` | ✗ false | **`qqq`** loaded |

Per-field independence verified for all 4 portfolio fields. Touched alloc protected; non-touched fields loaded from backend.

**2. Save button labels on Portfolio Settings sub-panel** — F1.13.4 helper is shared across sub-panels but I had only directly verified it on Performance. Re-verified on Portfolio:

| State | Button text |
|---|---|
| Original | `"Save Changes"` |
| Click with `_settLoadedFromBackend=false` | `"Sync failed — refresh"` ✓ |
| 2.2s reset | `"Save Changes"` ✓ |
| Click with `_settLoadedFromBackend=true` | `"Saved to device!"` ✓ |

F1.13.4 mechanism works regardless of which sub-panel renders the button.

No further soft spots.

---

## Commit log (this step)

- `1991cde` F1.14: Portfolio settings persist + load + Target Allocation vs Actual panel + rebalance callout (+ touched tracking)
  - `_settSaveAll` POSTs `portfolio_alloc / portfolio_preset / portfolio_rebalance / portfolio_benchmark`, with array → object translation for alloc
  - `goDash` F1.7 block loads all 4 portfolio fields from backend on login, with object → array translation preserving frontend order; respects per-field `_settTouched` flags from F1.13.5
  - `adjAlloc`, alloc-card onclick, preset-card onclick, rebalance-card onclick, benchmark-card onclick — each marks its corresponding `_settTouched.portfolio_*` key
  - `showPortfolio` adds Target Allocation vs Actual panel between pf-summary and positions table: 4-column row layout (Class / Target / Actual / Status), drift colour-coded, rebalance callout when any class >5% drift
