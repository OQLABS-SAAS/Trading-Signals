# STEP 28 — Indicator Scheme wiring (F1.4 sub-item)

**Plan reference:** IMPLEMENTATION_PLAN.md → Phase F → F1.4 Chart Visuals → "Indicator scheme switches the colour palette for EMA20/50/200, MACD, etc."
**Date:** 2026-05-02
**Status:** IN PROGRESS

---

## Honest scope (after investigation)

The Settings UI offers 4 schemes (crystal / mono / vivid / signal) and the preview swatch shows colours for **EMA 9, EMA 21, MACD, RSI, BB**.

**Reality check:** the only indicator that actually exists as a chart overlay in the v2 prototype is the **RSI line** in `undRsiInner`. EMA, MACD, BB are not drawn as LWC series on the Understand chart — they're consumed only as numeric values inside the indicator cards in the right-rail. The Settings preview swatches already react to scheme changes via `setIndScheme` calling `_renderIndPreview`.

**Therefore step 28 wires:**

1. RSI line colour follows active scheme (uses the scheme's RSI colour)
2. `setIndScheme` auto-persists to backend
3. `setIndScheme` syncs the legacy localStorage key
4. `setIndScheme` re-renders the chart so colour change takes effect immediately
5. `setIndScheme` fires toast (UX consistency with theme/type/grid)
6. `goDash` F1.7 block also loads indicator_scheme

Adding EMA / MACD / BB lines to the chart is a feature, not wiring — explicitly out of scope.

---

## Success criteria — written before any code

1. **Each of 4 schemes paints the RSI line in its scheme-specific colour:**
   - `crystal` → `rgba(167,139,250,.8)` (purple)
   - `mono` → `rgba(255,255,255,.5)` (faded white)
   - `vivid` → `#a78bfa` (solid purple)
   - `signal` → `rgba(237,232,216,.7)` (cream)

2. **Switching scheme live re-renders chart** without re-analyse.

3. **indicator_scheme auto-persists** on click.

4. **indicator_scheme loads on login** via `goDash` F1.7 fetch.

5. **Both legacy keys stay in sync:** `localStorage.dvIndScheme` + `localStorage.dv_sett_ind`.

6. **Settings card `.cv-opt-card.sel`** follows the active scheme.

7. **Toast fires on click** with the scheme name (matching theme/type/grid pattern).

8. **Independence** — switching scheme does NOT reset theme, type, or grid. Vice-versa.

9. **Settings preview swatch** (the one in `_renderIndPreview`) continues working — the row of EMA 9 / 21 / MACD / RSI / BB colour swatches updates per scheme in the Settings UI itself.

10. **No regressions** — Steps 25, 26, 27 still pass with scheme applied.

---

## Verification methods

| # | Method |
|---|---|
| 1a-d | Sample `undRsiInner` canvas pixels per scheme, expect dominant colour to change. crystal=purple-ish, mono=white-ish, vivid=#a78bfa solid, signal=cream. |
| 2 live re-render | Cycle 4 schemes on same data; confirm RSI canvas pixel signature changes per scheme. |
| 3 backend persist | `setIndScheme('crystal')` → fetch `/api/settings`; expect `indicator_scheme=crystal`. |
| 4 login load | POST scheme=mono, clear localStorage, reload; expect `_activeIndicatorScheme=mono` after fetch. |
| 5 var sync | After click, read both legacy keys + active var. |
| 6 sel highlight | After click, navigate to Settings → Chart Visuals; exactly 1 scheme card has `.sel`. |
| 7 toast | Read `dvToast.textContent` after each scheme click. |
| 8 independence | Set theme=obsidian, type=line, grid=dotted, scheme=crystal. Switch scheme=mono. Verify theme+type+grid unchanged. |
| 9 settings preview | Open Settings → Chart Visuals; click each scheme card; verify the swatches in `cvIndPreview` update per scheme (already works pre-step). |
| 10 regression | Quick sweep: 2 themes × 2 types × 2 grids × 2 schemes; confirm no breakage. |

---

## Did NOT test

- **EMA / MACD / BB lines on chart** — they don't exist as LWC overlays. Out of scope.
- **Scheme effect on indicator card text/values** — current implementation doesn't tie card colors to scheme.
- **Scheme persistence inside RSI 70/30 dashed lines** — those follow theme (F1.6), not scheme. Intentional.

---

## Results — to be filled

| # | Criterion | Method ran | Raw evidence | PASS/FAIL | Confidence |
|---|---|---|---|---|---|
| 1a | crystal | | | | |
| 1b | mono | | | | |
| 1c | vivid | | | | |
| 1d | signal | | | | |
| 2 | live re-render | | | | |
| 3 | backend persist | | | | |
| 4 | login load | | | | |
| 5 | var sync | | | | |
| 6 | sel highlight | | | | |
| 7 | toast | | | | |
| 8 | independence | | | | |
| 9 | settings preview | | | | |
| 10 | regression | | | | |

---

## Commit log (this step)

(To be appended)
