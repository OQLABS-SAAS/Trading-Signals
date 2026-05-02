# STEP 29 — Performance Settings wiring (F1.5)

**Plan reference:** IMPLEMENTATION_PLAN.md → Phase F → F1.5 Performance Settings → "Performance page renders user's targets as goal lines on the equity curve. KPI tiles show actual vs target with on track / behind badges."
**Date:** 2026-05-02
**Status:** IN PROGRESS

---

## Honest scope (after investigation)

The 4 targets defined in Settings → Performance:
- `perf_target_winrate` (int, default 55) — minimum acceptable win rate %
- `perf_target_rr` (float, default 2.0) — target avg risk/reward multiple
- `perf_target_trades` (int, default 5) — max daily trades cap
- `perf_target_annual` (float, default 20.0) — annual return target %

**Backend support:** `/api/settings` GET already returns all 4. POST accepts them with int/float coercion. Already shipped.

**Frontend gap (current state):**
- `_settSaveAll` writes to localStorage only — does NOT POST `perf_target_*` to backend.
- `goDash` F1.7 fetch does NOT read `perf_target_*` — preferences only sit in localStorage.
- Performance page (`showPerformance`) renders signal-history KPIs (Signals / Avg Conf / High Conf / Buy Bias). It never references the user's targets.

**Plan's claim limited by data availability:**
- Realised win rate can't be computed (no closed-trade outcome data).
- Annual return can't be computed (no portfolio P&L history).
- Avg R:R per signal IS computable from `entry / stop_loss / tp1` already stored, but it's planned not realised.
- Daily trade count IS computable from today's signal_history rows.

**Therefore step 29 wires:**
1. `_settSaveAll` POSTs all 4 perf targets to backend.
2. `goDash` F1.7 block also loads all 4 perf targets from backend on login, mirrors into `_pgSliders` and the legacy localStorage key.
3. Performance page renders a new "Your Targets" panel so the user can see their 4 numbers.
4. Performance page shows today's signal count vs the daily-trades target (the only actual-vs-target comparison data exists for).
5. Performance page shows the avg-planned-R:R from recent signals vs the R:R target.

Out of scope: equity curve "goal line" — current curve is illustrative random data per its own caption "Illustrative — run backtest for real curve". Adding a goal line on illustrative data would be theatre.

---

## Success criteria — written before any code

1. **Backend persist** — clicking "Save" on Performance settings POSTs all 4 targets to `/api/settings`. GET round-trip returns them.

2. **Login load** — POST non-default targets, clear `dv_sett_pg` localStorage, reload, confirm `_pgSliders` populated from backend.

3. **Performance page renders targets** — opening the Performance page shows a visible "Your Targets" card displaying the 4 numbers (winrate %, rr ×, trades, annual %).

4. **Today's signal count vs daily trades target** — the trades target panel shows `actual_today / target` with a status indicator (under, on, over).

5. **Avg planned R:R vs target** — the R:R target panel shows `actual_avg / target` from recent signals' planned R:R (where `entry`, `stop_loss`, `tp1` are populated).

6. **Targets persist across logout/login** — set non-default targets, log out (or full reload after backend confirm), log in, confirm targets retained.

7. **Independence** — changing perf targets doesn't reset chart-visuals settings (theme/type/grid/scheme). Vice-versa.

8. **No regression on signal-history KPIs** — the existing 4 KPI tiles (Signals / Avg Conf / High Conf / Buy Bias) still render correctly.

---

## Verification methods

| # | Method |
|---|---|
| 1 | After changing slider + clicking Save, fetch `/api/settings` and check 4 values match. |
| 2 | POST non-defaults via API, clear localStorage `dv_sett_pg`, reload, read `_pgSliders` after F1.7 fires. |
| 3 | Open Performance page, query DOM for the targets panel, confirm it contains the 4 displayed numbers. |
| 4 | Read DOM for the "today's trades vs target" element, confirm it shows count and status. |
| 5 | Read DOM for the avg-R:R element, confirm it shows a number derived from recent signals. |
| 6 | After full reload, open Performance, confirm targets unchanged. |
| 7 | Set targets, change theme, re-read targets — unchanged. |
| 8 | Open Performance, confirm the 4 existing tiles still render (Signals/AvgConf/HighConf/BuyBias). |

---

## Did NOT test

- **Realized win rate** — not computable without closed-trade outcome data.
- **Annual return** — not computable without portfolio P&L.
- **Equity curve goal line** — current curve is illustrative; goal line would be on fake data.
- **"On track" / "behind" badges with full traffic-light semantics** — out of scope; using simple under/on/over indicators only.

---

## Results — verified live 2026-05-02 on dot-verse.up.railway.app

| # | Criterion | Raw evidence | PASS/FAIL |
|---|---|---|---|
| 1 | persist | Set `_pgSliders={winrate:65,rr:2.5,trades:8,annual:30}` and called `_settSaveAll()`. Subsequent `/api/settings` GET returned `perf_target_winrate=65, perf_target_rr=2.5, perf_target_trades=8, perf_target_annual=30` | PASS |
| 2 | login load | POSTed `{winrate:72, rr:3.2, trades:11, annual:42.5}` directly to backend, removed `dv_sett_pg` from localStorage, reloaded → after F1.7 fired, `_pgSliders={"winrate":72,"rr":3.2,"trades":11,"annual":42.5}` and `localStorage.dv_sett_pg` matches | PASS |
| 3 | targets panel renders | DOM check: `#perfTargetsCard, #perfTgtWinrate, #perfTgtRr, #perfTgtTrades, #perfTgtAnnual` all present (`card_y_w_y_r_y_t_y_a_y`). Visual screenshot confirms 4 cards rendered below the KPI overview. | PASS |
| 4 | trades vs target | `#perfTgtTrades` textContent: `"DAILY TRADES CAP 8 0 today · under cap"` — shows target 8, actual 0 today, status "under cap" in green | PASS |
| 5 | rr vs target | `#perfTgtRr` textContent: `"AVG R:R TARGET 2.5× actual 2.45× · below target"` — shows target 2.5×, actual 2.45× computed from real `entry/SL/TP1` on signal_history rows, status "below target" in red because 2.45 < 2.5 | PASS |
| 6 | survives reload | After full reload, `_pgSliders` retained `{72, 3.2, 11, 42.5}` from backend | PASS |
| 7 | independence | After `setChartTheme('obsidian')`, `_pgSliders` unchanged, `_activeChartTheme=obsidian` updated independently | PASS |
| 8 | no KPI regression | `document.querySelectorAll('.perf-mc').length === 4` confirms 4 original tiles still render. Visual screenshot confirms SIGNALS 100, AVG CONF 58.8%, HIGH CONF 67, BUY BIAS 26% all visible | PASS |

**Four-check default applied:**
1. Multiple surfaces — DOM (5 elements), API (`/api/settings` GET round-trip), localStorage (`dv_sett_pg`), JS var (`_pgSliders`), visual screenshot
2. Direct measure — read element textContent verbatim, no inference
3. Cross-check siblings — F1.13 follows F1.7+F1.10b+F1.11+F1.12 pattern of POST-on-save and load-on-goDash
4. Sparse + dense — tested with two distinct value sets (`65/2.5/8/30` and `72/3.2/11/42.5`)

**All 8 criteria PASSED.** Step 29 closed.

---

## Follow-up audit (after "are you sure" prompt)

When pressed I flagged 3 things the original criteria didn't cover:
1. UI Save button click flow (I had called `_settSaveAll()` from JS console, not via button)
2. Slider drag flow (I had set `_pgSliders` directly, not via slider input)
3. Status colour branches I didn't trigger

**1. UI Save button click — VERIFIED.**
Located the rendered button via `[...document.querySelectorAll('.sett-save-btn')].find(b => b.getAttribute('onclick').includes('_settSaveAll'))`. Set `_pgSliders={80,1.5,25,60}`. Called `saveBtn.click()`. Backend returned `perf_target_winrate=80, rr=1.5, trades=25, annual=60` — exact match. Button click triggers `_settSaveAll` which POSTs.

**2. Slider drag flow — VERIFIED.**
4 sliders (`input.pg-range`) rendered. Located winrate slider by its `oninput` attribute containing `'winrate'`. Set value=88, dispatched `Event('input', {bubbles:true})`. Result: `_pgSliders.winrate=85` (slider clamped to its max of 85, correct behaviour). Subsequent UI Save click → backend `perf_target_winrate=85`. Full slider→state→save→backend chain proven via real DOM events, not just direct JS state mutation.

**3. Status colour branches — ALL TESTED.**

| Branch | Conditions | Element text | Branch hit |
|---|---|---|---|
| Trades `<` cap (green) | `0 today, cap=8` | "8 / 0 today / under cap" | `_trStatusCol = '#5de8a0'` ✓ |
| Trades `===` cap (amber) | `0 today, cap=0` | "0 / 0 today / at cap" | `_trStatusCol = '#c9a84c'` ✓ |
| Trades `>` cap (red) | `0 today, cap=-1` | "-1 / 0 today / over cap" | `_trStatusCol = '#e8706e'` ✓ |
| R:R `>=` target (green) | `actual 2.45, target 2.0` | "2.0× / actual 2.45× / on target" | `_rrStatusCol = '#5de8a0'` ✓ |
| R:R `<` target (red) | `actual 2.45, target 5.0` | "5.0× / actual 2.45× / below target" | `_rrStatusCol = '#e8706e'` ✓ |

**Empty-data R:R fallback** (`_rrVals.length === 0 → _avgRR=null → "no data" gray`) — code path verified by inspection, can't trigger live without a fresh-no-history account.

**Test artifact disclosure:** my tests wrote intermediate values to the user's backend record. After verification, the account was restored to defaults `{55, 2.0, 5, 20}` via direct API POST. No residual test data.

---

## Second follow-up audit (after second "are you sure" prompt)

3 more checks I had not directly run:

**1. Settings UI sliders show F1.7-loaded values correctly — VERIFIED.**
POSTed `{winrate:78, rr:3.7, trades:14, annual:35.5}` to backend, cleared `dv_sett_pg`, reloaded, navigated to Settings → Performance.
- `_pgSliders` after F1.7: `{winrate:78, rr:3.7, trades:14, annual:35.5}` ✓
- Slider input values: `{winrate:78, rr:3.7, trades:14, annual:36}` — annual slider's `step=1` config rounded 35.5 → 36 (slider position only)
- Display labels (`pgv-X` elements): `78% / 3.7x / 14 / 35.5%` ✓ — labels show the actual stored value
- Visual screenshot confirms slider knobs visibly sit at correct positions

**2. Save button "Saved to device!" feedback — VERIFIED.**
- Before click: `"Save Changes"`
- 300ms after click: `"Saved to device!"` ✓
- 2.5s after click: `"Save Changes"` (auto-reset) ✓
Existing UX feedback cycle still works after my F1.13 changes.

**3. Annual slider step=1 rounding — pre-existing behaviour, not a step-29 regression.**
The `pgCard('annual', ..., 5, 100, 1, ...)` call defines step=1 (existing code, predates F1.13). Float values like 35.5 are persisted exactly to backend (verified) and rendered correctly in the displayed label, but the slider knob position rounds to nearest integer. If this ever becomes a UX problem, change `pgCard` step argument from 1 to 0.5 for annual. Outside scope of step 29.

**Still soft (acknowledged):**
- Real logout/login cycle for perf targets — not run; relies on F1.7 mechanism which IS verified for theme.
- "No data" R:R fallback — code-review only; can't trigger without a fresh-no-history account.

**Account state restored** to defaults `55/2/5/20` after this round.

---

## Commit log (this step)

- `32875ca` F1.13: Performance targets persist + load on login + render on Performance page (with computable actual-vs-target widgets)
  - `_settSaveAll` now POSTs all 4 `perf_target_*` fields to `/api/settings`
  - `goDash` F1.7 block reads `perf_target_*` from response and writes to `_pgSliders` + legacy `dv_sett_pg` localStorage key
  - `showPerformance` adds a "Your Targets" card with 4 sub-cards (winrate / rr / trades / annual)
  - Trades card shows today's signal count vs cap with status colour
  - R:R card computes actual avg from `entry/SL/TP1` on signal_history rows and labels above/below target
  - Win-rate and annual cards show target only with "needs closed-trade data" / "needs portfolio P&L" notes (honest about data limits)
