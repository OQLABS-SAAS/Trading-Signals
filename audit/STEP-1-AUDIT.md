# AUDIT — STEP 1 — BUG 1 RSI Divergence Trendlines

**Original status in CLAUDE.md:** RESOLVED, runtime verified by user 2026-04-12.
**Audit triggered:** user requested full re-audit of all 30 prior steps under the failure-brainstorm protocol.
**Audit date:** 2026-05-02
**Auditor role:** senior principal engineer / system architect.
**Outcome:** **REGRESSION CONFIRMED.** Trendlines have not been drawing despite the RESOLVED label.

---

## ⚠️ FAILURE BRAINSTORM (mandatory per 2026-05-02 protocol — written BEFORE success criteria)

### 1. Data assumption gaps

a. Backend's `detect_rsi_divergence` return schema may have changed since the 2026-04-12 fix. Frontend's `_undDrawDiv` reads field names that may no longer exist.
b. Backend may emit pivot indices that are larger than `chart_dates.length` (chart is truncated to last 200 bars; pivot indices come from full series). Frontend's `dates[bars[i]]` would be undefined.
c. Backend may emit `type: "none"` with an empty `all[]` — frontend assumes a divergence exists if `sig.rsiDiv` is truthy.

### 2. Math edge cases

a. Two pivot bars at exactly the same index → x0 === x1 → vertical line of zero width. Visually invisible.
b. Two pivot vals at very close prices → y0 ≈ y1 → near-flat trendline. The 2026-04-12 fix added a `Math.abs(y1-y0)<5` guard to draw at midpoint — confirm still in code.
c. Pivot index outside the visible chart window (timeScale.timeToCoordinate returns null for off-screen times). Frontend has `if(x0==null||x1==null) return` — should handle gracefully.

### 3. Empty / malformed inputs

a. `sig.rsiDiv` is null when no divergence detected. Frontend `if(!sig.rsiDiv) return` handles.
b. `sig.rsiDiv` exists but `getBars(div)` returns undefined (field-name mismatch). **Hypothesised root cause from code reading.**
c. Pivot bar index references a date that's outside `sig.chartDates` (e.g., pivot is in the dropped historical window). `dates[bars[0]]` would be undefined → `toTs(undefined)` → null → early return. Silent failure.

### 4. What user sees when state is wrong

a. Chart renders with no trendlines, no error, no warning. User assumes "no divergence detected" when in fact divergence IS detected but rendering broke.
b. Backend emits divergence with `type: "bearish"` and `desc: "..."` — desc text might be displayed elsewhere (e.g., signal narrative) so user may see "RSI divergence detected" in narrative but no visual on chart. Cognitive mismatch.

### 5. Adversarial / fast-clicker / confused-beginner

a. User runs analysis on an asset with no divergence — no trendlines correctly. Cannot distinguish from broken case.
b. User scrolls / zooms chart while trendlines render — not relevant since canvas is overlay.

### 6. Cross-feature interactions

a. Chart theme switch (F1.5) calls `_initUndChart` which clears `inner.innerHTML` but NOT the divergence overlay canvases (`undDivPrice`, `undDivRsi`). Old trendlines could persist as ghosts on theme switch. Need to verify.
b. `_undDrawDiv` is called from `_applyChartBars` after `setData`. If chart re-renders without new data, divergence stale.
c. Canvas overlay is `position:absolute; pointer-events:none` — confirm doesn't block chart interactions.

---

## Root cause analysis

**Smoking gun — backend / frontend field name mismatch:**

| Frontend `_undDrawDiv` reads | Actual backend returns | Match? |
|---|---|---|
| `div.isBull` | `div.type` (string) | ✗ field absent |
| `div.priceBars` | `div.price_pivot_bars` | ✗ field absent |
| `div.priceVals` | `div.price_pivot_vals` | ✗ field absent |
| `div.rsiBars` | `div.rsi_pivot_bars` | ✗ field absent |
| `div.rsiVals` | `div.rsi_pivots` | ✗ field absent |
| `div.label` | `div.label` | ✓ |

Live test on AAPL 1d (2026-05-02): backend returned `keys=[type, label, strength, rsi_pivots, price_pivot_bars, price_pivot_vals, rsi_pivot_bars, confirm_bar, desc, all, chart_price_pivot_bars, chart_rsi_pivot_bars]`. None of the 5 frontend-expected keys present.

`_undDrawDiv` calls `getBars(div) = d => d.priceBars` → undefined. The `if(!bars||bars.length<2) return` exits silently. **Zero trendlines draw on any chart for any asset.**

The 2026-04-12 fix (panel height 90→160, flat-line guard, pivot dot radius 3.5→5.5) addressed the SYMPTOMS that had been present at that time, with whatever field names existed THEN. A subsequent refactor (likely Phase 1c when `_build_chart_output` was rewritten to accept DataFrame) changed the divergence response shape. The frontend was not updated.

**Additional finding:** the response includes `chart_price_pivot_bars` and `chart_rsi_pivot_bars` not present in `detect_rsi_divergence`'s direct return. These must be set later — likely the chart-window-aware indices remapped to `chart_dates` length. Need to find where they're added.

---

## Success criteria (derived from brainstorm)

1. **Backend response shape known.** `/api/analyze` returns `rsi_divergence` with the expected keys; the field-name contract is documented.
2. **Frontend reads the correct keys.** `_undDrawDiv`'s `getBars` / `getVals` return real arrays, not undefined.
3. **Bullish trendline draws** (regular bullish or hidden bullish): for an asset with a known bullish divergence, both price-pane and RSI-pane canvases get a visible green dashed trendline.
4. **Bearish trendline draws.**
5. **Pivot indices that reference chart-window-truncated bars are handled.** Indices >= `chart_dates.length` should not crash; either remapped or skipped.
6. **No crash when `rsi_divergence.type === "none"`.** No trendlines drawn, no console errors.
7. **No ghost trendlines on theme switch.** Switching theme on a chart with active divergence redraws cleanly without stale lines on overlay canvas.
8. **Chart-window remapping working.** Look for where `chart_price_pivot_bars` and `chart_rsi_pivot_bars` get added; verify they index correctly into chart_dates.

---

## Did NOT test

- **Performance impact of canvas redraw on every chart update** — out of scope; not a correctness issue.
- **Mobile rendering of overlay canvas** — out of scope.
- **Touch/pointer events on overlay canvas** — `pointer-events:none` makes this moot.

---

## Live audit findings (before fix)

Test 1 — AAPL 1d analyze response inspection:
```
type=bullish
keys=[type, label, strength, rsi_pivots, price_pivot_bars, price_pivot_vals,
      rsi_pivot_bars, confirm_bar, desc, all, chart_price_pivot_bars, chart_rsi_pivot_bars]
hasIsBull=false  hasPriceBars=false  hasPriceVals=false
hasRsiBars=false  hasRsiVals=false   hasPricePivotBars=true
```

Confirms field-name mismatch. Frontend's 5 expected fields ALL absent.

---

## Fix proposed

Translate backend → frontend at the boundary in `_undDrawDiv`:

```js
function _undDrawDiv(){
  const refs = window._undChartRefs;
  const sig  = window._activeSignal;
  if(!refs||!sig||!sig.rsiDiv) return;
  const raw = sig.rsiDiv;
  if(raw.type === 'none') return;  // no divergence detected, no draw

  // BUG-1-AUDIT-FIX: backend returns price_pivot_bars / price_pivot_vals / rsi_pivot_bars / rsi_pivots / type.
  // Translate to the camelCase shape the rest of this function expects.
  // Prefer chart_*_pivot_bars (chart-window remapped) when available, fall back to raw indices.
  const div = {
    isBull: (raw.type === 'bullish' || raw.type === 'hidden_bullish'),
    priceBars: raw.chart_price_pivot_bars || raw.price_pivot_bars,
    priceVals: raw.price_pivot_vals,
    rsiBars:   raw.chart_rsi_pivot_bars   || raw.rsi_pivot_bars,
    rsiVals:   raw.rsi_pivots,
    label:     raw.label,
    desc:      raw.desc
  };

  // ... rest of original function uses `div` as before
}
```

This keeps the rest of `_undDrawDiv` unchanged — only the field translation is added at the top. Minimum surgical change.

---

## Results — to be filled after fix is shipped

(deferred until fix lands)
