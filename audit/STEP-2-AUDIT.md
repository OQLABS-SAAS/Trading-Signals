# AUDIT — STEP 2 — BUG 2 Scanner → Signals Chart Zero-Width

**Original status in CLAUDE.md:** RESOLVED, runtime verified by user 2026-04-12.
**Original fix:** `autoSize: true` in `_lwcCommonOpts`, `requestAnimationFrame` in `scannerLoadTicker`, all scanner entry points routed through `scannerLoadTicker`.
**Audit date:** 2026-05-02
**Auditor role:** senior principal engineer / system architect.
**Initial finding:** `scannerLoadTicker` doesn't exist in current v2 prototype. Architecture changed. Need to verify equivalent flow.

---

## ⚠️ FAILURE BRAINSTORM (mandatory per 2026-05-02 protocol — written BEFORE success criteria)

### 1. Data assumption gaps

a. v1 used `scannerLoadTicker` as the single canonical entry. v2 uses `loadSignalContext` and `loadScannerSignal` — TWO entry points. Either could regress the zero-width fix.
b. `_initUndChart` uses explicit width with fallback `wrap.clientWidth || wrap.parentElement?.clientWidth || 800`. The `|| 800` fallback fires when neither has width. If user window is narrower than 800px, chart overflows. If wider, chart is too small.
c. `requestAnimationFrame` in `showUnderstand` waits one frame for layout. But on slow devices or when DOM is heavy, one frame may not be enough — `wrap.clientWidth` could still be 0.

### 2. Math edge cases

a. `wrap.clientWidth === 0` → fallback to parentElement.clientWidth. If parent also 0 (newly-mounted, hidden, display:none) → 800.
b. Window resize after chart renders → chart doesn't auto-resize unless LWC's autoSize is true. Currently NOT enabled on Understand chart.
c. User clicks scanner row while Understand was previously hidden (display:none) → showUnderstand makes it visible → wrap.clientWidth was 0 before nav, may be 0 momentarily after.

### 3. Empty / malformed inputs

a. Scanner row clicked with `entry: null` (HOLD signal) → `loadScannerSignal` still navigates to Understand → chart tries to render with no entry/SL/TP price lines. Trendline overlay + chart should still work but no entry markers.
b. Scanner returns `signal: ''` or undefined → loadSignalContext still fires, sig.sig may be undefined.
c. `o.sym` empty → showUnderstand renders chart for unknown ticker → backend returns error.

### 4. What user sees when state is wrong

a. **Zero-width chart:** chart canvases exist but width=0, so no candles visible. User clicks scanner expecting chart, sees blank. Original BUG 2 symptom.
b. **800px fallback overflow:** chart wider than container → horizontal scrollbar or clipping.
c. Chart renders correctly but RSI divergence overlay canvas (`undDivPrice`) still has stale width from previous asset → BUG-1-AUDIT-FIX-2 should clear, but only when `_undDrawDiv` runs. If chart inits without divergence, overlay never resizes. Needs check.
d. Scanner click during analysis spinner → race condition.

### 5. Adversarial / fast-clicker / confused-beginner

a. User clicks 5 scanner rows in 200ms → 5 navigations to Understand → 5 chart inits stacking. LWC should clear inner.innerHTML each time, but races possible.
b. User clicks scanner row, Understand opens with 0-width chart, clicks scanner row again — does second click recover or compound the issue?
c. User on mobile / narrow viewport → 800px fallback definitely overflows.

### 6. Cross-feature interactions

a. BUG-1-AUDIT-FIX-2's `clearOverlays` resizes `undDivPrice` canvas to its `offsetWidth/offsetHeight`. If those are 0 (chart wrap not rendered yet), overlay canvas becomes 0×0. Subsequent draw calls would silently fail.
b. F1.5 theme switch triggers `_initUndChart(window._activeSignal)` via `_applyAllCharts`. If the chart was zero-width when theme switched, redraw still uses zero width.
c. Window resize → chart doesn't auto-resize. Scanner→signal path doesn't address this.

---

## Honest scope for BUG 2 audit

The original BUG 2 was about a specific symptom: clicking a scanner row showed a zero-width chart on Signals page. The v1 fix used `scannerLoadTicker` as a canonical route. v2 uses different functions but same symptom risk.

**Audit should:**
1. Verify the current v2 flow (`loadScannerSignal`, `loadSignalContext` → `showUnderstand` → `_initUndChart`) doesn't produce zero-width charts on click.
2. Verify the explicit-width fallback chain works: `wrap.clientWidth || parentElement.clientWidth || 800`.
3. Identify any edge cases where width=0 could still slip through.
4. Surface any cross-feature regression with BUG-1-AUDIT-FIX-2 (clearOverlays may itself create zero-sized overlay canvases).

**NOT in scope:** rewriting scanner UI, switching to LWC autoSize across the board (would be invasive).

---

## Success criteria (derived from brainstorm)

1. **Scanner → Signal navigation produces a visible chart.** Click a scanner result, verify Understand page shows LWC chart with non-zero width canvases drawing candles.
2. **`_initUndChart` width fallback works.** Programmatically simulate `wrap.clientWidth = 0` and verify the chart still renders with the parent or 800px fallback.
3. **Window resize tolerated.** Resize browser after chart renders, verify chart at least doesn't error out (perfect resize is bonus).
4. **Rapid clicks don't accumulate canvases.** Click 5 scanner rows in fast succession, verify final chart state is clean.
5. **Theme switch on scanner-loaded chart still works.** Load via scanner, switch theme, confirm chart redraws with non-zero width.
6. **BUG-1-AUDIT-FIX-2 doesn't break overlay sizing.** If `clearOverlays` runs when wrap is 0×0, overlay canvas should still recover when draw fires later. Verify the overlay canvas dimensions are healthy after a normal load.
7. **Mobile viewport / narrow window.** Resize to 600px width, click scanner row, verify chart fits container without overflow.
8. **HOLD signal with null entry** (no chart price lines) still renders chart correctly.

---

## Did NOT test

- **Touch events on canvases** — out of scope; pointer-events:none on overlays makes this moot.
- **Server response time impact** — unrelated to chart rendering.
- **Chart performance with 1000+ bars** — chart limited to 200 bars by design.

---

## Results — to be filled after live verification
