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

## Second follow-up (F1.14.1 — math correctness fixes)

After yet another "are you sure", surfaced two real bugs in the original F1.14:

**Bug 1: Index positions silently distorted displayed actuals.**
`typeMap` mapped `index → indices`, but no `Indices` row exists in default `_settAlloc`. Index positions were added to `totalNotional` (the denominator) but never displayed, so every other class's actual % was understated proportional to the user's index exposure.

**Bug 2: Cash row always showed `0%` actual.**
Positions data has no concept of cash holdings. The Cash bucket has no asset_type that maps to it. The row would always render `target X% / actual 0% / under by X%` — misleading because the user can never act on this.

**Fix shipped (`7bab9ab` F1.14.1):**
- Built `displayedBuckets` set from `_settAlloc` labels. Skip positions whose mapped bucket isn't displayed → don't add to `totalNotional`.
- Built `trackableBuckets` set from `typeMap` values. Bucket rows whose label isn't in this set render as `target X% / — / tracking unavailable` instead of computed against an always-zero numerator.

**Verification (live):**

Test 1 — Cash row honest display:
- Default Portfolio page renders Cash as `5% / — / tracking unavailable` (dim grey) instead of misleading `under by 5%` red.

Test 2 — Index positions don't dilute math:
- Before adding index: `Forex 96.4%, Stocks 3.6%`
- POSTed `^GSPC × 50 @ $5800` ($290k notional, asset_type='index')
- After adding index: `Forex 96.4%, Stocks 3.6%` — **identical**
- Without the fix, Forex would have dropped to ~40% as the index inflated `totalNotional`. It didn't. Index correctly excluded.
- Test position deleted, account clean.

Visual screenshot confirms Cash row reads "tracking unavailable" in dim grey.

No further soft spots after this round.

---

## Third follow-up (F1.14.2 — backend value validation guard, found via failure brainstorm protocol)

**Context:** This was the first time the failure-brainstorm protocol was applied. Brainstorming "Empty / malformed inputs" surfaced a real bug Claude had missed across the original step + 2 follow-ups.

**Bug:** Backend `/api/settings` POST handler accepts `portfolio_alloc` as `dict(body)` — JSON-encodes whatever it receives without value validation. So a value like `"abc"` or `1000` or `-5` lands in the database. When F1.7 reads it, `+s.portfolio_alloc[k]` produces `NaN` or out-of-range numbers. These were assigned directly to `_settAlloc[i].pct` and rendered in the UI as `NaN%` or `1000%`.

**Fix shipped (F1.14.2):**
```js
var v = +s.portfolio_alloc[k];
if(isFinite(v) && v >= 0 && v <= 100){ a.pct = v; changed = true; }
```
Per-key validation: bad values silently dropped, valid values still update independently.

**Verification (live):**

Inline test against the guard logic, 9 scenarios:

| Input | Crypto pct after | Pass |
|---|---|---|
| `"abc"` | 30 (unchanged) | ✓ |
| `1000` | 30 (unchanged) | ✓ |
| `-5` | 30 (unchanged) | ✓ |
| `NaN` | 30 (unchanged) | ✓ |
| `50` | 50 | ✓ |
| `0` | 0 (boundary accepted) | ✓ |
| `100` | 100 (boundary accepted) | ✓ |
| `100.5` | 30 (just-out-of-range rejected) | ✓ |
| Mixed: `{crypto:"abc",stocks:40,forex:1000,commodities:10,cash:-5}` | crypto unchanged, **stocks→40**, forex unchanged, **commodities→10**, cash unchanged | ✓ Per-key independence |

End-to-end with real backend round-trip:
- POST `{crypto:"abc",stocks:30,forex:15,commodities:10,cash:5}` to backend (backend stored "abc" as-is)
- Cleared localStorage + reloaded
- F1.7 fired with guard → Crypto retained valid prior value (NOT NaN); Stocks/Forex/Commodities/Cash all loaded normally

**Without F1.14.2** the same test would have produced `_settAlloc.Crypto.pct = NaN`, rendering as `NaN%` on the Portfolio page.

Account restored after test.

**Failure-brainstorm protocol earned its first catch on the very first application.** The remaining brainstorm items (negative target via tampering, SHORT direction handling, sum>100% allocation) are documented as known limitations rather than fixes — they require either tampering or are defensible interpretations of the data.

---

## Fourth follow-up (F1.14.3 — defense-in-depth enum guard for preset/rebalance)

**Honest correction:** when surfacing this gap I claimed backend "accepts any string" for `portfolio_preset` / `portfolio_rebalance`. **That was wrong.** Backend already enum-validates both at app.py L4416 and L4418. I had misread the handler.

**What F1.14.3 actually protects against (defense-in-depth):**
- Direct DB tampering (someone edits the postgres row by hand)
- Schema migration leaving invalid values
- Future backend regression dropping the enum check

The guard wraps F1.7's per-field load with `indexOf >= 0` against the known enum so even if invalid data reaches the GET response, frontend rejects it instead of leaving the UI with no card highlighted.

**Verification:**

Inline mock test (since backend correctly rejects invalid POSTs, can't trigger the guard via real e2e):

| Test | Input | Result |
|---|---|---|
| Both garbage | `{preset:'garbage',rebalance:'whatever'}` | Both rejected, defaults retained ✓ |
| Valid preset only | `{preset:'aggressive'}` | psm→aggressive, reb unchanged ✓ |
| Valid rebal only | `{rebalance:'monthly'}` | reb→monthly, psm unchanged ✓ |
| Mixed valid+invalid | `{preset:'balanced',rebalance:'garbage'}` | psm→balanced, reb rejected ✓ Per-key independence |
| Empty string | `{preset:'',rebalance:''}` | Both rejected (empty-string check) ✓ |
| Null | `{preset:null,rebalance:null}` | Both rejected (typeof check) ✓ |
| Wrong case | `{preset:'BALANCED'}` | Rejected (case-sensitive) — fine because backend stores lowercase ✓ |

End-to-end happy path with valid values:
- POST `{preset:'aggressive',rebalance:'monthly'}` → backend stores
- Cleared localStorage + reload → F1.7 with guard
- Result: `_settPsm=aggressive`, `_settReb=monthly` ✓

Guard doesn't break valid input. Defense-in-depth working.

**Lesson logged:** before claiming a server-side gap, READ the actual handler code carefully. F1.14.3 is still defensive-useful, but the framing in my brainstorm-result message overstated the problem.

Account restored: `psm=balanced, reb=quarterly, bench=spy`.

---

## Fifth follow-up (F1.14.4 — chart-visuals enum guards, brainstorm caught a parallel gap outside step 30 scope)

After F1.14.3 closed the preset/rebalance enum guard, applying the failure brainstorm to the broader `goDash` F1.7 block surfaced the same defense-in-depth gap for `chart_theme`, `chart_type`, `grid_style`, `indicator_scheme`:

- **Backend handlers:** `chart_theme/grid_style/indicator_scheme` are str-cap only with no enum check. `chart_type` already has enum validation.
- **F1.7 load:** all 4 only checked `typeof === 'string'`. No enum validation.
- **Failure mode:** if invalid value reaches frontend (DB tampering, schema regression, future backend bug), `_active*` becomes garbage. Settings card `.sel` highlight breaks (no card matches). Downstream rendering still works because `_getTheme/_gridOpts/_initUndChart` branches all fall back to defaults — but UI looks broken.

**Fix shipped (F1.14.4):**
Added `_VALID_THEMES / _VALID_TYPES / _VALID_GRIDS / _VALID_SCHEMES` enum arrays inside F1.7. Each per-field load wrapped with `&& _VALID_X.indexOf(s.X) >= 0`. Garbage rejected, valid loaded.

**Verification (live):**

Inline mock tests, 5 scenarios covering all 4 fields:

| Test | Theme | Type | Grid | Scheme | Pass |
|---|---|---|---|---|---|
| All garbage `{fakeTheme, pie, mesh, rainbow}` | aurora (default) | candle (default) | subtle (default) | crystal (default) | All rejected ✓ |
| All valid `{obsidian, line, dotted, mono}` | obsidian | line | dotted | mono | All loaded ✓ |
| Mixed: theme valid, type invalid, grid valid, scheme invalid | midnight ✓ | candle (rejected) | subtle ✓ | crystal (rejected) | Per-field independence ✓ |
| Wrong case `{OBSIDIAN, CANDLE}` | aurora | candle | (no change) | (no change) | Case-sensitive rejected ✓ |
| Empty + null | (no change) | (no change) | (no change) | (no change) | Both rejected ✓ |

End-to-end happy path:
- POST `{chart_theme:'midnight', chart_type:'bar', grid_style:'dotted', indicator_scheme:'vivid'}` to backend
- Cleared 8 localStorage keys + reloaded
- Result: all 4 values loaded correctly (`th=midnight, ty=bar, gr=dotted, sc=vivid`); localStorage synced

Guards don't break valid input. Defense-in-depth working across all 4 chart-visuals enum-bound settings.

**Honest scope note:** this fix is technically across F1.4 (chart visuals, steps 25-28) not Phase F portfolio (step 30). It's logged here because the failure brainstorm in step 30 surfaced it, and applying the protocol strictly means fixing it when found rather than deferring. The fix lives in the same `goDash` F1.7 function that step 30's portfolio loaders extended.

Account restored: `theme=aurora, type=candle, grid=subtle, scheme=crystal`.

---

## Sixth follow-up (F1.14.5 — XSS defense for portfolio_benchmark)

**Brainstorm finding:** the showPortfolio panel header concatenates `_settBench` directly into innerHTML. `_settPsm` and `_settReb` are now enum-guarded so safe; `_settBench` is free-form (any ticker), so XSS-shaped strings could in principle reach innerHTML if they pass backend's 16-char str-cap.

**Fix shipped (F1.14.5) — two layers:**

1. **F1.7 format guard** — accept `_settBench` only when it matches `/^[A-Za-z0-9./^=-]{1,16}$/` (ticker-shaped). Rejects `<`, `>`, `"`, `'`, spaces, unicode, anything that could break HTML parsing.

2. **Render-time HTML escape** — in showPortfolio's panel header, the dynamic `_settBench` insertion is now passed through a `replace(/[&<>"']/g, ...)` escape so any character that did slip through (DB tampering bypassing the format guard, or future code change) is rendered as entities.

**Verification (live):**

Layer 1 (format guard): 13 inline scenarios:

| Input | Result | Pass |
|---|---|---|
| `SPY`, `^GSPC`, `EURUSD=X`, `GC=F`, `BTC-USD`, `BRK.A` | All loaded ✓ |
| `<img onerr` | rejected (defaults to `spy`) ✓ |
| `a"b` | rejected ✓ |
| `spy onmouseover=` (space) | rejected ✓ |
| 17 chars | rejected ✓ |
| `SPY€` (unicode) | rejected ✓ |
| Empty string | rejected ✓ |
| Boundary 16 chars | accepted ✓ |

Layer 2 (render escape): set `_settBench = '<img onerror=alert(1)>'` directly in JS (bypassing layer 1), called `showPortfolio()`, inspected DOM:
- `imgInside = 0` — no `<img>` element rendered inside panel
- `hasHtmlEntities = true` — innerHTML contains `&lt;` and `&gt;`
- `hasRawImgTag = false` — no raw `<img` in HTML
- textContent shows the payload as plain text, not parsed as HTML

End-to-end happy path: POST `portfolio_benchmark='qqq'` → cleared localStorage → reload → `_settBench=qqq`, localStorage synced. ✓

**Defense in depth confirmed.** Layer 1 catches the common case at load time; layer 2 catches anything that bypasses layer 1.

Account restored: `bench=spy`.

---

## Step 30 — final close summary across SIX follow-up rounds

Real bugs / gaps caught and fixed:
- F1.7 portfolio touched-skip + Save button labels (round 1, user-prompted)
- F1.14.1 untracked positions distort math + Cash always-zero (round 2, user-prompted)
- F1.14.2 portfolio_alloc value validation (NaN/range guard) (round 3, **failure-brainstorm caught**)
- F1.14.3 preset/rebalance enum guard (round 4, defense-in-depth)
- F1.14.4 chart-visuals enum guards (theme/type/grid/scheme) (round 5, parallel scope, **failure-brainstorm caught**)
- F1.14.5 portfolio_benchmark XSS defense (format guard + render escape) (round 6, **failure-brainstorm caught**)

3 of 6 rounds caught by the failure-brainstorm protocol independently of user push. Pattern of overclaiming hasn't gone away (rounds 1+2 still required user push), but the protocol IS shifting catches earlier.

---

## Commit log (this step)

- `1991cde` F1.14: Portfolio settings persist + load + Target Allocation vs Actual panel + rebalance callout (+ touched tracking)
  - `_settSaveAll` POSTs `portfolio_alloc / portfolio_preset / portfolio_rebalance / portfolio_benchmark`, with array → object translation for alloc
  - `goDash` F1.7 block loads all 4 portfolio fields from backend on login, with object → array translation preserving frontend order; respects per-field `_settTouched` flags from F1.13.5
  - `adjAlloc`, alloc-card onclick, preset-card onclick, rebalance-card onclick, benchmark-card onclick — each marks its corresponding `_settTouched.portfolio_*` key
  - `showPortfolio` adds Target Allocation vs Actual panel between pf-summary and positions table: 4-column row layout (Class / Target / Actual / Status), drift colour-coded, rebalance callout when any class >5% drift
