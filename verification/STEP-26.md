# STEP 26 — Chart Type wiring (F1.4 sub-item)

**Plan reference:** IMPLEMENTATION_PLAN.md → Phase F → F1.4 Chart Visuals → "Chart type switches between candle / bar / line series"
**Date:** 2026-05-02
**Status:** IN PROGRESS

---

## Scope

Setting Chart Type in Settings → Chart Visuals must change the actual price-action rendering on the Understand chart. Five types defined in `_spVisuals` `chartTypes` array: `candle`, `line`, `area`, `bar`, `hollow`.

Out of scope (deliberately): per-position `pfchart-*` charts respecting type, Backtest equity curve respecting type, MT5 mini-chart respecting type. Those are separate steps in the plan.

---

## Success criteria — written before any code touches

1. **Each of 5 types renders its correct LWC series:**
   - `candle` → addCandlestickSeries (existing behaviour)
   - `bar` → addBarSeries (OHLC bars)
   - `line` → addLineSeries (close prices line)
   - `area` → addAreaSeries (close prices filled area)
   - `hollow` → addCandlestickSeries with `wickVisible:true, borderVisible:true, transparent body for up`

2. **Switching type from Settings card click re-renders the visible Understand chart immediately** (no re-analyse needed). Same data, different visualisation.

3. **chart_type persists to backend via `/api/settings`** on click (auto-persist, like F1.8 did for theme).

4. **chart_type loads on login** via the existing F1.7 `goDash` `/api/settings` fetch — `_activeChartType` is set from backend value, both localStorage keys synced.

5. **Both internal variables stay in sync:** `_activeChartType` and any `_settChartType` (if it exists).

6. **Setting card `.sel` highlight follows the active type** the same way themes do.

7. **Chart type follows the active theme.** Switching theme should NOT reset type. Switching type should NOT reset theme.

8. **No regressions on theme system.** Step 25's pixel verification for all 6 themes must still pass.

---

## Verification methods (one per criterion)

| # | Method |
|---|---|
| 1a candle | Sample `undChartInner` candle canvas, expect non-zero up/dn theme colours. |
| 1b bar | Sample candle canvas, expect bar-shaped pixel pattern (vertical lines + horizontal ticks rather than rectangles). |
| 1c line | Sample candle canvas, expect single dominant line colour matching `_th.lineCol`. No upCol/dnCol pixels. |
| 1d area | Sample candle canvas, expect line + filled area below in upCol-with-alpha. |
| 1e hollow | Sample candle canvas, expect up candles to have border but no fill (mostly transparent body, coloured outline). |
| 2 live re-render | Without re-analysing, click each type card and confirm `undChartInner` canvas pixel content changes per type. |
| 3 backend persist | After clicking type card, fetch `/api/settings` and confirm `chart_type` matches click. |
| 4 login load | Set chart_type to non-default via API, clear localStorage, reload, confirm `_activeChartType` matches backend. |
| 5 var sync | Confirm `_activeChartType === _settChartType` (if defined) === `localStorage.dvChartType`. |
| 6 sel highlight | Click type card, open Settings → Chart Visuals, confirm exactly 1 card has `.cv-type-card.sel`. |
| 7 theme + type independent | Set theme=obsidian, type=line. Confirm both apply. Switch theme=aurora. Confirm type still line. |
| 8 no regression | Re-run Step 25's 6-theme sweep with `chart_type=candle`. All 6 should still produce their spec upCol/dnCol pixels. |

---

## Did NOT test (with reason)

- **Per-position `pfchart-*` chart type** — out of scope for this step (separate plan item).
- **Backtest equity curve type** — out of scope.
- **Type interaction with MTF mini-charts** — those don't use LWC series; static rendering, no type to switch.
- **Hollow candle behaviour with very high zoom** — visual edge case, not part of step.

---

## Results — to be filled after implementation

(Empty until verification runs)

| # | Criterion | Method ran | Raw evidence | PASS/FAIL | Confidence |
|---|---|---|---|---|---|
| 1a | candle | | | | |
| 1b | bar | | | | |
| 1c | line | | | | |
| 1d | area | | | | |
| 1e | hollow | | | | |
| 2 | live re-render | | | | |
| 3 | backend persist | | | | |
| 4 | login load | | | | |
| 5 | var sync | | | | |
| 6 | sel highlight | | | | |
| 7 | independence | | | | |
| 8 | step-25 regression | | | | |

---

## Commit log (this step)

(To be appended)
