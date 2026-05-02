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

## Results — verified live 2026-05-02 on dot-verse.up.railway.app

| # | Criterion | Method ran | Raw evidence | PASS/FAIL | Confidence |
|---|---|---|---|---|---|
| 1a | candle | Sample undChartInner pixels with theme=constellation, type=candle | `93,232,160 @ 4221` (upCol exact) + `232,112,110 @ 2672` (dnCol exact). Total 7 canvases. | PASS | CONFIRMED |
| 1b | bar | Same, type=bar | `93,232,160 @ 3937` + `232,112,110 @ 2294` — same colours, lower hit counts (thinner shapes). | PASS | CONFIRMED |
| 1c | line | Same, type=line | `238,232,216 @ 3894` + `237,232,216 @ 964` (lineCol family dominates). **No upCol or dnCol in top 5** — proven candle-less. | PASS | CONFIRMED |
| 1d | area | Same, type=area | `93,232,160 @ 4642` (upCol line) + alpha-blended variants `94,231,159 @ 276`, `92,231,159 @ 202` (gradient fill). | PASS | CONFIRMED |
| 1e | hollow | Same, type=hollow | `232,112,110 @ 2672` (dnCol full — down candles still filled) + `93,232,160 @ 1834` (upCol reduced — only borders/wicks) + `0,0,0 @ 757` (transparent up bodies show black). | PASS | CONFIRMED |
| 2 | live re-render | Cycle 5 types in sequence on same AAPL 4H data; check canvas count and colour signature per type | All 5 types produced distinct, expected pixel signatures. Canvas count stable at 7 across all types — no leak. | PASS | CONFIRMED |
| 3 | backend persist | `setChartType('bar')` → fetch `/api/settings` | Backend returned `chart_type=bar` immediately after click. | PASS | CONFIRMED |
| 4 | login load | POST `chart_type=area`, clear localStorage, reload, observe values | After reload, `_activeChartType=area`, `localStorage.dvChartType=area`, `localStorage.dv_sett_ctype=area`, `_settChartType=area`. All four loaded from backend within 800ms. | PASS | CONFIRMED |
| 5 | var sync | After `setChartType('bar')`, read all 4 sources | `_active=bar / lsCType=bar / lsSettCType=bar / settVar=bar`. | PASS | CONFIRMED |
| 6 | sel highlight | After `setChartType('bar')`, navigate to Settings → Chart Visuals, count `.cv-type-card.sel` | `cards=5, selCount=1, which=bar`. | PASS | CONFIRMED |
| 7 | independence | Set theme=obsidian, type=line. Then set theme=aurora. Read type. | After theme=aurora, type still `line`. Theme switch did not reset type. | PASS | CONFIRMED |
| 8 | step-25 regression | Sweep all 6 themes with type=candle; sample top 2 colours per theme; compare to spec | All 6 themes still produce their exact spec upCol/dnCol pixels (constellation `93,232,160 / 232,112,110`, minimal `74,222,128 / 248,113,113`, terminal `160,208,128 / 208,96,96`, midnight `52,211,153 / 244,114,182`, obsidian `0,255,136 / 255,68,68`, aurora `45,212,191 / 244,63,94`). | PASS | CONFIRMED |

**All 12 criteria PASSED at runtime in the live browser.** Step 26 closed.

---

## Commit log (this step)

- F1.10a: backend `/api/settings` accepts all 5 chart_type values (candle/bar/line/area/hollow); GET default updated `candles` → `candle`
- F1.10b: frontend setChartType auto-persists + redraws + syncs both vars; `_initUndChart` branches series on `_activeChartType`; `_applyChartBars` switches data shape for line/area; `goDash` F1.7 block also loads chart_type
- All shipped under one commit: `F1.10: chart_type wiring (Understand chart series + auto-persist + login load + verification ledger)`
