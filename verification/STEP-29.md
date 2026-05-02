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

## Third follow-up audit (after third "are you sure" prompt)

Pushing once more surfaced a real **pre-existing data-loss bug** that F1.13's Save flow could trigger. F1.7 (the goDash auto-load) was loading chart_theme / chart_type / grid_style / indicator_scheme / perf_target_* from backend — but **NOT** assets_enabled or risk_tolerance.

**The failure path:** user saved `assets_enabled=['stocks']` and `risk_tolerance='conservative'` on backend. Visited on a fresh device (no localStorage). F1.7 fired but skipped these two fields. `_settAssets` defaulted to all 5 classes; `_settRisk` defaulted to `'moderate'`. User opened any Settings sub-panel (perf, chart visuals, etc.) and clicked Save → `_settSaveAll` POSTed the in-memory defaults → backend overwrote saved values with defaults. Silent data loss.

**Fix shipped (`5b75bef` F1.13.1):** F1.7 now loads `assets_enabled` and `risk_tolerance` along with the other settings, syncing both legacy localStorage keys (`dv_sett_assets`, `dv_sett_risk`).

**Verification (live, this session):**
1. POSTed `{assets_enabled:['stocks'], risk_tolerance:'conservative'}` to backend
2. Cleared `dv_sett_assets` and `dv_sett_risk` localStorage keys
3. Reloaded
4. After F1.7 fired: `_settAssets=['stocks']`, `_settRisk='conservative'`, both localStorage keys synced
5. Called `_settSaveAll()` without changing anything in UI
6. Backend GET after save: `assets_enabled=['stocks'], risk_tolerance='conservative'` — **unchanged**

Without F1.13.1 step 6 would have written `['stocks','crypto','forex','commodity','index']` and `'moderate'`. The data-loss path is closed.

This was rooted in F1.2 (assets_enabled wiring) and F1.3 (risk_tolerance wiring) shipping save-only without round-trip load. Catching it now means earlier panels' verification ledgers (if backfilled per the audit pass) should re-test cross-device persistence — not just same-device localStorage clear.

**Account state restored** to original `assets=['stocks','crypto','forex'], risk='aggressive'` after this round.

---

## Fourth follow-up (F1.13.2 — F1.7 failure-mode protection)

**Pre-existing risk surfaced after F1.13.1:** F1.13.1 fixed the cross-device case (F1.7 succeeds). But what if F1.7 itself fails (network error, 5xx, /api/settings unreachable)? The `.then` never fires, `_settAssets` and `_settRisk` retain in-memory defaults, and a subsequent `_settSaveAll` call would still overwrite backend.

**Fix shipped (`058f781` F1.13.2):**
- F1.7's successful `.then()` now sets `window._settLoadedFromBackend = true`.
- `_settSaveAll` checks the flag before including `assets_enabled` and `risk_tolerance` in its POST body. If false → those fields are EXCLUDED from the POST, backend keeps its current values.
- `chart_theme` and `perf_target_*` are still POSTed unconditionally (they have safe defaults that match backend defaults).

**Verification (live):**

Setup:
- POSTed `assets=['stocks'], risk='conservative', winrate=50` to backend
- Deliberately corrupted in-memory: `_settAssets=['stocks','forex','crypto','commodity','index']`, `_settRisk='moderate'`, `_pgSliders.winrate=88`
- Set `window._settLoadedFromBackend=false` to simulate F1.7 failure
- Called `_settSaveAll()`

Result:

| Field | Backend before | After save | Status |
|---|---|---|---|
| assets_enabled | `['stocks']` | `['stocks']` | PROTECTED — not in POST body |
| risk_tolerance | `conservative` | `conservative` | PROTECTED — not in POST body |
| perf_target_winrate | `50` | `88` | POSTed normally (safe field) |

The gate works as designed. Risky fields safely excluded under F1.7-failure conditions. Safe fields still saveable so user UX isn't blocked.

**Account state restored** after test.

---

## Step 29 — final closing summary

| Item | State |
|---|---|
| Original 8 criteria | ALL PASS |
| UI Save button + slider drag flow | PASS |
| All 5 status colour branches | PASS |
| Settings UI sliders show F1.7-loaded values | PASS |
| Save button "Saved to device!" feedback | PASS |
| Annual slider step=1 rounds 35.5 → 36 | NOTED — pre-existing UI behaviour, not a regression |
| F1.13.1 data-loss fix (assets_enabled/risk_tolerance loaded by F1.7) | PASS |
| F1.13.2 failure-mode gate (F1.7 fails → save excludes risky fields) | PASS |
| Real logout/login cycle | DEFERRED — F1.7 mechanism verified for theme in step 25 |
| Empty signal-history "no data" R:R | CODE REVIEW only |
| Multi-tab concurrency | OUT OF SCOPE — pre-existing pattern |

Step 29 closed at the depth the user-pushed audit reached. Three follow-up rounds surfaced and fixed two real risks (data-loss on cross-device save, data-loss on F1.7 failure).

---

## Fifth follow-up (F1.13.3 — F1.13.2 was incomplete)

**Pushing again surfaced a hole in my own F1.13.2 fix.** I had claimed `chart_theme` and `perf_target_*` were "safe to POST always" because their hard-coded defaults match backend defaults. **Wrong.** Backend defaults match in-memory defaults only when the user has never changed the setting. If user has `chart_theme=obsidian` and visits a fresh device where F1.7 fails, in-memory defaults to `'constellation'` and `_settSaveAll` silently overwrites backend `obsidian → constellation`. Same data-loss path I supposedly fixed.

F1.13.2 protected 2 of 5 vulnerable fields. The other 3 (chart_theme + 4 perf_target_*) had the same vulnerability.

**Fix shipped (F1.13.3):** when `window._settLoadedFromBackend !== true`, suppress the entire `_settSaveAll` POST. Show toast "Settings not synced — refresh and try again". localStorage write still happens (user's local input not lost).

**Verification (live):**

Setup:
- Backend POSTed `theme=obsidian, wr=85, rr=3, tr=12, an=40, ass=['stocks','crypto','forex'], rsk=aggressive`
- Corrupted in-memory to all defaults: `_activeChartTheme='constellation', _pgSliders={55,2,5,20}, _settAssets=[all 5], _settRisk='moderate'`
- Set `window._settLoadedFromBackend=false`
- Called `_settSaveAll()`

Result — backend after save:

| Field | Before | After (F1.13.3) | Status |
|---|---|---|---|
| chart_theme | obsidian | obsidian | PROTECTED |
| perf_target_winrate | 85 | 85 | PROTECTED |
| perf_target_rr | 3 | 3 | PROTECTED |
| perf_target_trades | 12 | 12 | PROTECTED |
| perf_target_annual | 40 | 40 | PROTECTED |
| assets_enabled | ['stocks','crypto','forex'] | ['stocks','crypto','forex'] | PROTECTED |
| risk_tolerance | aggressive | aggressive | PROTECTED |

Toast verified separately (isolated test): `dvToast.textContent="Settings not synced — refresh and try again"`, `class="dv-toast show"`.

ALL 7 fields safe under F1.7 failure. Entire POST is suppressed, user gets explicit feedback.

**Honest disclosure:** F1.13.2 was an incomplete fix shipped without catching that `chart_theme` and `perf_target_*` had the same vulnerability. The user surfaced it by asking "are you sure" again. Pattern: every push-back finds another hole.

---

## Sixth follow-up (F1.13.4 — UX consistency on suppression)

**Pushed once more.** F1.13.3 closed the data-loss path but the Save button's `onclick` still always declared `"Saved to device!"` regardless of whether the POST went through. User saw two contradictory signals: the green-check label and the failure toast.

**Fix shipped (F1.13.4):**
- `_settSaveAll` returns `false` when suppressed, `true` when POSTed.
- New helper `_saveBtnHandler(btn, label)` checks the return value and shows either `"✓ Saved to device!"` or `"× Sync failed — refresh"` (with X icon). After 2s, resets to the original "Save Changes" label.
- `_saveBtn` template's onclick replaced with `_saveBtnHandler(this, '${label}')`.

**Verification (live, this session):**

| State | Button text | Toast |
|---|---|---|
| Default | `"Save Changes"` | — |
| Happy click (flag=true) | `"Saved to device!"` ✓ | (no toast) |
| Reset 2.2s later | `"Save Changes"` | — |
| Failure click (flag=false) | `"× Sync failed — refresh"` ✓ | `"Settings not synced — refresh and try again"` ✓ |
| Reset 2.2s later | `"Save Changes"` | — |

Visual screenshot confirmed: button rendered `× Sync failed — refresh` and toast rendered `Settings not synced — refresh and try again` simultaneously. UI state agrees end-to-end.

Both happy and failure paths verified. No more contradictory messaging.

**Sixth round caught yet another hole I had introduced.** Pattern continues — my "fix" rounds aren't reliable on first pass.

---

## Commit log (this step)

- `32875ca` F1.13: Performance targets persist + load on login + render on Performance page (with computable actual-vs-target widgets)
  - `_settSaveAll` now POSTs all 4 `perf_target_*` fields to `/api/settings`
  - `goDash` F1.7 block reads `perf_target_*` from response and writes to `_pgSliders` + legacy `dv_sett_pg` localStorage key
  - `showPerformance` adds a "Your Targets" card with 4 sub-cards (winrate / rr / trades / annual)
  - Trades card shows today's signal count vs cap with status colour
  - R:R card computes actual avg from `entry/SL/TP1` on signal_history rows and labels above/below target
  - Win-rate and annual cards show target only with "needs closed-trade data" / "needs portfolio P&L" notes (honest about data limits)
