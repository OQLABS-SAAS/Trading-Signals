# DotVerse Subtask Decomposition: Quality Ring Tooltip CSS Fix

## Overview
Fix 3 CSS issues causing the quality ring tooltip (`.qual-tip`) on signal opportunity
cards (`.opp-card`) to display incorrectly — clipped, non-wrapping, and unbounded.

## File
- `static/index-v2-prototype.html`
  - `.qual-tip`: lines 2199-2216
  - `.opp-card`: lines 2113-2121

---

## Subtask 1: BLAST RADIUS ANALYSIS
**Agent:** SYSTEMS ARCHITECT
**Depends on:** none

### Objective
Analyze the risk of changing `.opp-card { overflow: hidden }` → `overflow: visible`.

### What to check
1. `.opp-card::before` (line 2122-2124): absolute-positioned 2px gradient bar at top.
   - With `overflow:hidden` this is clipped within border-radius (10px).
   - With `overflow:visible` it will STILL be within bounds (height:2px, top:0, left:0,
     right:0) — NO risk from the ::before element itself.

2. Children that might overflow:
   - `.opp-card-header` (padding 14px 16px 10px) — well-contained
   - `.opp-card-mid` (padding 0 16px 12px) — well-contained
   - `.opp-card-footer` (padding 8px 16px 14px) — well-contained
   - All child elements are flex items with standard padding; unlikely to overflow
     horizontally or vertically beyond the card boundary.

3. Animation: `cardIn` uses `translateY(12px)` with `animation-fill-mode: both`.
   - During the 0.3s entry animation, cards enter from below. With `overflow:visible`,
     the card content could be visible during the brief translate. However, since the
     card itself moves as a unit (not its children), this is visually indistinguishable
     from `overflow:hidden` during entry — the card body moves, not internal content
     spilling out.

4. Other `.opp-card` overrides:
   - Line 2946 (dark mode): overrides background, border, box-shadow — does NOT touch
     overflow. Safe.
   - Line 3106 (premium theme): overrides background, border, box-shadow — does NOT
     touch overflow. Safe.
   - Line 3013 (reduced-motion): disables animation — no overflow concern.

5. The original intent of `overflow:hidden`:
   - Likely added to clip the `::before` gradient bar to the `border-radius:10px`.
   - Without it, the `::before` bar (a 2px line at top:0, left:0, right:0) will extend
     to the full width of the card. Since `border-radius:10px` rounds all 4 corners,
     the top corners won't clip the gradient bar anymore — the bar will appear to span
     full width edge-to-edge instead of being slightly rounded in. This is a minor
     visual change but unlikely to be noticed since it's only 2px tall.

### Deliverable
- Written assessment: safe to proceed, no blast radius concerns beyond a barely
  perceptible change to the top gradient bar rendering. No child elements depend on
  `overflow:hidden` for layout integrity.

---

## Subtask 2: APPLY CSS CHANGES
**Agent:** CODER
**Depends on:** Subtask 1 (blast radius sign-off)

### Objective
Apply the three targeted CSS changes in `static/index-v2-prototype.html`.

### Changes (3 edits)

#### Change A — `.qual-tip` white-space (line 2212)
```
-  white-space: nowrap;
+  white-space: normal;
```

#### Change B — `.qual-tip` max-width (insert after line 2211)
```
   line-height: 1.6;
+  max-width: 280px;
   white-space: normal;  /* (after Change A) */
```

#### Change C — `.opp-card` overflow (line 2120)
```
-  position:relative;overflow:hidden;
+  position:relative;overflow:visible;
```

### Deliverable
- All 3 edits applied, syntax verified (CSS is inline in HTML `<style>` block)

---

## Subtask 3: QA — SIDE-EFFECT REGRESSION CHECK
**Agent:** QA
**Depends on:** Subtask 2 (changes applied)

### Objective
Verify no visual regressions from changing `.opp-card` overflow to `visible`.

### Test checklist
1. **Card rendering at rest**: Verify `.opp-card` children (header, mid, footer, rings,
   badges) render identically — no content spills outside card boundaries.

2. **Gradient bar**: Verify the `::before` 2px gradient bar at top still renders
   correctly (minor edge rounding difference acceptable).

3. **Card hover state**: Verify hover transitions (background, border, box-shadow)
   still work and no content flickers.

4. **Card entry animation**: Verify the `cardIn` animation (slide-up) plays without
   visual glitches — no content visible before the card arrives.

5. **Border-radius integrity**: Verify all 4 rounded corners render correctly (10px
   radius), no sharp corners or clipped edges.

6. **Grid layout**: Verify `.opp-list` grid (2-column) layouts identically across
   typical signal counts (0-8 cards).

7. **Responsive**: Test at viewports: 1920px, 1440px, 1280px, 1024px, 768px — verify
   cards don't break layout.

8. **Dark mode / premium theme**: Verify the `.opp-card` overrides at lines 2946-2947
   and 3106-3107 still apply correctly.

### Deliverable
- Pass/fail report per checklist item with notes on any issues found.

---

## Subtask 4: VERIFIER — E2E BROWSER CHECK
**Agent:** VERIFIER
**Depends on:** Subtask 3 (QA pass)

### Objective
End-to-end browser verification that the fix resolves the original 3 issues.

### Test steps
1. **Launch**: Open `static/index-v2-prototype.html` in a browser at width 800-1024px
   (narrow viewport where the bug was most visible).

2. **Tooltip wrapping (issue #1)**: Hover over a quality ring. Verify the `.qual-tip`
   tooltip text wraps naturally instead of extending in a single line to 244px.

3. **Tooltip max-width (issue #2)**: Hover over a quality ring with a long score
   breakdown. Verify the tooltip does not exceed 280px width.

4. **Tooltip clipping (issue #3)**: Hover over a quality ring that's near the edge of
   its card. Verify the tooltip extends above the card boundary without being clipped.

5. **Narrow viewport**: At viewport width ~480px, verify the tooltip is fully visible
   and wraps to fit within the screen.

6. **Multiple cards**: Verify the tooltip works on all 8 cards (index 1-8) without
   clipping, including the right-column cards where the tooltip might shift.

7. **Regression check**: Quick visual scan of card layout, hover effects, and
   animations — confirm nothing looks broken.

### Deliverable
- Screenshot or written confirmation of all 7 checks passing.

---

## Task Dependency Graph

```
Subtask 1 (ARCHITECT) ──► Subtask 2 (CODER) ──► Subtask 3 (QA) ──► Subtask 4 (VERIFIER)
```

## Summary of Changes
| Line | Class | Old | New |
|------|-------|-----|-----|
| 2120 | `.opp-card` | `overflow:hidden` | `overflow:visible` |
| 2212 | `.qual-tip` | `white-space: nowrap` | `white-space: normal` |
| ~2212 | `.qual-tip` | *(none)* | `max-width: 280px` |
