# STEP 27 — Grid Style wiring (F1.4 sub-item)

**Plan reference:** IMPLEMENTATION_PLAN.md → Phase F → F1.4 Chart Visuals → "Grid style switches major/minor grid line style"
**Date:** 2026-05-02
**Status:** IN PROGRESS

---

## Scope

Setting Grid Style in Settings → Chart Visuals must change the actual grid rendering on the Understand chart. Four styles in `_spVisuals` `gridStyles` array: `subtle`, `none`, `dotted`, `full`.

Out of scope: grid on per-position chart, backtest equity, MTF mini-charts.

---

## Success criteria — written before any code

1. **Each of 4 styles renders distinct grid:**
   - `subtle` → faint grid lines using theme `gridCol` (current default behaviour)
   - `none` → NO grid lines (vertical and horizontal both hidden)
   - `dotted` → dotted-style grid lines (LightweightCharts.LineStyle.Dotted)
   - `full` → more prominent solid grid lines (higher-opacity colour than subtle)

2. **Switching grid style live re-renders chart** without re-analyse.

3. **grid_style auto-persists to backend** on click.

4. **grid_style loads on login** via existing `goDash` F1.7 fetch.

5. **All 4 sources stay in sync:** `_activeGridStyle`, any `_settGridStyle` legacy var, `localStorage.dvGridStyle`, `localStorage.dv_sett_grid`.

6. **Settings card `.cv-opt-card.sel` follows active grid style.**

7. **Independence** — switching grid style does NOT reset theme or chart type. Vice-versa.

8. **No regressions** — Step 25 (theme) and Step 26 (type) verifications still pass with grid style applied.

---

## Verification methods

| # | Method |
|---|---|
| 1a subtle | Set theme=constellation, grid=subtle, type=candle. Sample `undChartInner` for `_th.gridCol` colour family pixels. Expect non-zero. |
| 1b none | Set grid=none. Sample `undChartInner` for grid colour pixels. Expect dramatic drop relative to baseline. |
| 1c dotted | Set grid=dotted. Sample for grid colour family pixels. Expect non-zero, distributed in dotted pattern (verifiable by total count being lower than subtle solid). |
| 1d full | Set grid=full. Sample for grid colour family pixels. Expect higher count than subtle (more prominent). |
| 2 live re-render | Cycle 4 styles on same data; canvas count stable; pixel signatures change. |
| 3 backend persist | After click, fetch `/api/settings`; expect `grid_style` updated. |
| 4 login load | POST grid_style=dotted, clear localStorage, reload; expect `_activeGridStyle=dotted` after fetch. |
| 5 var sync | After click, read all 4 sources, all match. |
| 6 sel highlight | After click, open Settings → Chart Visuals; exactly 1 grid card has `.sel`. |
| 7 independence | Set theme=obsidian, type=line, grid=dotted. All three apply. Switch theme → grid+type stay. |
| 8 regression | Re-run a slice of step-25 + step-26 checks with grid=subtle. All pass. |

---

## Did NOT test

- **Per-position chart grid style** — out of scope.
- **Backtest equity curve grid** — out of scope.
- **The exact dot density of `dotted` style** — visual subjective.

---

## Results — to be filled

| # | Criterion | Method ran | Raw evidence | PASS/FAIL | Confidence |
|---|---|---|---|---|---|
| 1a | subtle | | | | |
| 1b | none | | | | |
| 1c | dotted | | | | |
| 1d | full | | | | |
| 2 | live re-render | | | | |
| 3 | backend persist | | | | |
| 4 | login load | | | | |
| 5 | var sync | | | | |
| 6 | sel highlight | | | | |
| 7 | independence | | | | |
| 8 | regression | | | | |

---

## Commit log (this step)

(To be appended)
