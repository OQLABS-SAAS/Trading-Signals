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

## Results — to be filled

| # | Criterion | Method ran | Raw evidence | PASS/FAIL |
|---|---|---|---|---|
| 1 | persist | | | |
| 2 | login load | | | |
| 3 | targets panel renders | | | |
| 4 | trades vs target | | | |
| 5 | rr vs target | | | |
| 6 | survives reload | | | |
| 7 | independence | | | |
| 8 | no KPI regression | | | |

---

## Commit log (this step)

(To be appended)
