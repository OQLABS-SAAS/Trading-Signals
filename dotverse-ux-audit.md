# DotVerse — UI/UX Pro Max Audit
**Date:** 2026-04-15  
**Auditor:** UI/UX Pro Max Skill  
**Source:** `static/index.html` (11,927 lines) + design system search (fintech/trading/dark SaaS)  
**Severity scale:** 🔴 Critical → 🟠 High → 🟡 Medium → 🟢 Low

---

## Executive Summary

DotVerse has a strong design identity — the amber/warm-black brutalist aesthetic is distinctive and appropriate for a trading tool. The core information architecture is sound. However the codebase has accumulated significant technical debt across six categories: accessibility is almost entirely absent, touch targets are too small throughout, sub-12px text is pervasive (285 instances), inline styles have multiplied to 1,200 instances creating drift and inconsistency, there is zero `prefers-reduced-motion` support, and the muted text color `#6b6050` fails WCAG AA contrast. These issues range from critical compliance failures to polish deficits that reduce the app's perceived quality.

---

## Category 1 — Accessibility 🔴 CRITICAL

### 1.1 Zero focus states on interactive elements
**Finding:** Only `calc-input:focus` and `calc-select:focus` have a focus rule (border-color change). Every other interactive element — nav tabs, gpill buttons, instrument chips, scan table rows, MTF cells, scanner pills, refresh buttons — has no `:focus` or `:focus-visible` style at all.  
**Impact:** Keyboard-only users and screen-reader users cannot see where they are on the page.  
**Rule:** `focus-states` — visible focus rings 2–4px on all interactive elements.  
**Fix:** Add globally:
```css
:focus-visible {
  outline: 2px solid var(--amber);
  outline-offset: 2px;
  border-radius: 2px;
}
```

### 1.2 Zero aria-labels on any element
**Finding:** `grep aria-label` returns 0 results across all 11,927 lines. No `role` attributes on custom controls (tabs, pills, scanner rows used as buttons). No `aria-live` regions on the signal output, loading state, or error output.  
**Impact:** Screen readers announce generic "button" or nothing. The real-time signal card updates silently for AT users.  
**Rules:** `aria-labels`, `dynamic-type`, `voiceover-sr`  
**Priority fixes:**
- `<button id="analyzeBtn">` → add `aria-label="Analyze signal"`
- Nav tabs → add `role="tablist"` on container, `role="tab"` + `aria-selected` on each
- Signal output div → add `aria-live="polite"` so updates are announced
- Loading state → add `role="status"` to loading indicator

### 1.3 `--muted` color fails WCAG AA
**Finding:** `#6b6050` on `#1a1710` (bg2) = **2.91:1** — FAIL for normal text.  
**Used for:** scanner table text, muted labels, secondary data across the app.  
**Rule:** `color-contrast` — minimum 4.5:1 for normal text.  
**Fix:** Lighten `--muted` from `#6b6050` to `#8a7864` (≥4.5:1 on bg2).

### 1.4 Color-only signal conveying (charts + indicators)
**Finding:** BUY/SELL/HOLD in scanner and MTF cells is conveyed by color alone (green/red/amber text). Indicator badges use color + label text — that is fine. MTF cells and scan pills use only colored text with no icon or shape differentiation.  
**Rule:** `color-not-only`  
**Fix:** Add a small directional icon (▲ / ▼ / —) alongside BUY/SELL/HOLD text in MTF cells and scanner signal pills.

### 1.5 No `prefers-reduced-motion` support
**Finding:** 15 animation blocks (tapeScroll 55s, pulseDot 2s, scanline animations, stagger animations) — none wrapped in `@media (prefers-reduced-motion: no-preference)` or reduced in a `prefers-reduced-motion: reduce` block.  
**Rule:** `reduced-motion`  
**Fix:** Wrap all `@keyframes` animations:
```css
@media (prefers-reduced-motion: reduce) {
  .tape-track { animation: none; }
  .sess-dot .dot { animation: none; }
  /* etc. */
}
```

---

## Category 2 — Touch & Interaction 🟠 HIGH

### 2.1 Touch targets critically undersized
**Finding:** The following interactive elements have effective tap heights well below the 44px minimum:
- `rb-btn` (refresh): `padding:2px 6px; font-size:9px` → ~20px tap height
- `gpill` (asset/TF buttons): `padding:3px 7px; font-size:10px` → ~22px tap height  
- `scan-mtf-pill`: `padding:3px 8px; font-size:9px` → ~20px tap height
- `.bt-tf-btn`: `padding:4px 10px; font-size:10px` → ~24px tap height
- Pine Script "Copy" / "✕ Close" buttons: `padding:3px 10px` → ~22px

**Rule:** `touch-target-size` — minimum 44×44px (iOS) / 48×48dp (Android).  
**Fix:** Increase padding on all pill/button elements to minimum `padding:10px 14px` or add `min-height:44px`. For compact rows, use CSS `min-height:44px` with `display:flex; align-items:center` to meet tap area without visual inflation.

### 2.2 Analyze button has no visual loading feedback in CSS
**Finding:** The JS correctly sets `btn.disabled = true` during analysis, but there is no CSS rule for `#analyzeBtn:disabled` — it looks identical to the enabled state. Users get no visual signal the request is processing.  
**Rule:** `loading-buttons`  
**Fix:**
```css
#analyzeBtn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  position: relative;
}
#analyzeBtn:disabled::after {
  content: '';
  width: 12px; height: 12px;
  border: 2px solid rgba(12,10,8,0.3);
  border-top-color: #0C0A08;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  display: inline-block;
  margin-left: 8px;
  vertical-align: middle;
}
```

### 2.3 Hover-only interactions on scanner rows
**Finding:** Scanner table rows have `onclick` handlers but the only feedback is a CSS `transition:background .15s` hover state. On mobile (touch devices), hover states never fire — the row appears to do nothing on first tap.  
**Rule:** `hover-vs-tap`, `press-feedback`  
**Fix:** Add `:active` state matching the hover background so mobile users get immediate visual feedback on tap.

---

## Category 3 — Typography 🟠 HIGH

### 3.1 285 instances of sub-12px text
**Finding:** `font-size:9px`, `font-size:10px`, and `font-size:7.5px` appear 285 times. Key affected areas:
- Logo tag: `7.5px` — below any readable threshold
- Refresh buttons (OFF/15s/30s): `9px`
- Scanner MTF pills: `9px`
- Ticker tape: `12px` (acceptable) — but change delta: `11px`
- Info-cell labels, indicator card labels, section sub-labels: `9px–10px`

**Rule:** `readable-font-size` — 12px absolute minimum for any visible text; 14px minimum for body-readable text.  
**Impact:** At 9px, text is unreadable on non-Retina displays and for users with any vision impairment.  
**Fix:** Establish a minimum floor of `11px` for the smallest label tier, `12px` for all interactive element text. The logo tag can stay visually small via `letter-spacing` rather than tiny `font-size`.

### 3.2 Font pairing is good — preserve it
**Finding:** Anybody (display) + Fira Code (mono) + Sora (body) is a strong, distinctive three-family system. Anybody italic for the brand mark, Fira Code for all data/numbers, Sora for prose — this is correct and distinctive.  
**Assessment:** ✅ This is above average. The skill database rates this close to the "Developer Mono" pairing (JetBrains + IBM Plex) in terms of technical/financial mood. Keep it.

### 3.3 No `font-display: swap` on Google Fonts
**Finding:** The `<link>` import for Google Fonts does not include `&display=swap`. On slow connections, text will be invisible (FOIT) until fonts load.  
**Rule:** `font-loading`  
**Fix:** Add `&display=swap` to the Google Fonts URL:
```html
<link href="https://fonts.googleapis.com/css2?family=Anybody:...&display=swap" rel="stylesheet">
```

---

## Category 4 — Layout & Responsive 🟡 MEDIUM

### 4.1 Only two breakpoints: 768px and 480px
**Finding:** The entire responsive system is two `@media` blocks. No 1024px (tablet landscape) or 1440px (wide desktop) breakpoints exist.  
**Rule:** `breakpoint-consistency` — systematic breakpoints at 375 / 768 / 1024 / 1440.  
**Impact:** On a 1024px–1280px viewport (iPad landscape, smaller laptops), the three-column desktop layout can become cramped.  
**Fix:** Add a 1024px breakpoint that adjusts the signals layout sidebar width and scanner table column visibility.

### 4.2 Inline styles: 1,200 instances
**Finding:** 1,200 inline `style="..."` attributes. This is the largest maintainability and consistency risk in the codebase. Style drift is inevitable — the same element type has different font-size, padding, or color in different parts of the file.  
**Rule:** `color-semantic` — semantic tokens in CSS classes, not per-element inline styles.  
**Examples of drift found:**
- gpill buttons: some have `border-radius:3px`, some `border-radius:2px` — same component, different inline styles
- Button font sizes: mix of `font-size:10px`, `font-size:11px`, `font-size:12px` on similar buttons
- Padding inconsistency: `padding:3px 10px` vs `padding:4px 12px` on equivalent-tier buttons

**Fix strategy:** Refactor inline styles into named CSS classes. Priority order: all `<button>` elements first, then `<div>` structural wrappers, then labels/badges.

### 4.3 No `min-height: 100dvh` — iOS Safari address bar issue
**Finding:** `body { min-height: 100vh }` — on iOS Safari, `100vh` includes the address bar height, causing the footer content to be clipped under the bar.  
**Rule:** `viewport-units`  
**Fix:** `min-height: 100dvh` with `100vh` fallback:
```css
body { min-height: 100vh; min-height: 100dvh; }
```

---

## Category 5 — Animation 🟡 MEDIUM

### 5.1 Ticker tape animation: 55s linear — too mechanical
**Finding:** `animation: tapeScroll 55s linear infinite`. `linear` easing on a scrolling ticker feels robotic compared to the natural feel of Bloomberg-style tapes which use subtle ease.  
**Rule:** `easing` — avoid linear for UI transitions.  
**Fix:** Not critical, but switching to `cubic-bezier(0.25, 0.1, 0.25, 1.0)` gives a marginally more organic feel. Low priority.

### 5.2 No `prefers-reduced-motion` (repeated from Accessibility — escalated)
This is both an accessibility violation and an animation issue. Marked as 🔴 Critical above. The tape, pulseDot, scanline, and stagger animations will play continuously for users who have motion sickness accommodations enabled at the OS level.

### 5.3 `max-height` animation on news cards causes jank
**Finding:** `.nc-body { transition: max-height .3s ease }` — animating `max-height` from `0` to `200px` triggers layout recalculation on every frame.  
**Rule:** `transform-performance` — use transform/opacity only; avoid animating max-height.  
**Fix:** Replace with a `grid-template-rows: 0fr → 1fr` technique or `opacity + transform` approach for smoother expansion.

---

## Category 6 — Forms & Feedback 🟡 MEDIUM

### 6.1 Calculator inputs have no visible labels
**Finding:** Calculator fields (`cAccount`, `cRisk`, `cEntry`, `cSL`, etc.) use placeholder text only. When the user starts typing, the label disappears.  
**Rule:** `input-labels` — visible label per input, not placeholder-only.  
**Fix:** Each calc input needs a `<label>` element positioned above the input, or a floating label pattern.

### 6.2 Error messages are not announced to screen readers
**Finding:** `calcGuidance` div updates innerHTML with coaching/error states, but has no `aria-live` attribute. Screen readers will not announce the guidance text when it changes.  
**Rule:** `aria-live-errors`  
**Fix:** Add `aria-live="polite"` to `#calcGuidance`.

### 6.3 Analyze button: no `aria-busy` during loading
**Finding:** When analysis is running, `analyzeBtn` is disabled but no `aria-busy="true"` is set to tell screen readers the system is processing.  
**Rule:** `submit-feedback`  
**Fix:** In `runAnalyze()`, add `analyzeBtn.setAttribute('aria-busy','true')` when starting and `removeAttribute('aria-busy')` on completion.

---

## Category 7 — Navigation 🟡 MEDIUM

### 7.1 Nav tabs have no semantic role
**Finding:** The centered nav tabs are `<button>` elements inside a `.nav-wrap` div. They have no `role="tab"`, no `role="tablist"` on the container, no `aria-selected` state, no `aria-controls` pointing to the tab panels.  
**Rule:** `nav-label-icon`, `nav-state-active`  
**Fix:**
```html
<div class="nav-wrap" role="tablist" aria-label="Main navigation">
  <button class="nav-tab active" role="tab" aria-selected="true" aria-controls="panel-signals">Signals</button>
  ...
</div>
```

### 7.2 No deep-linking — all state lives in JS
**Finding:** URL never changes on tab navigation. Refreshing the page always lands on the default tab. Sharing a specific view (e.g. Scanner or Portfolio) requires manual instructions to the recipient.  
**Rule:** `deep-linking`  
**Fix:** Implement `history.pushState` on tab switch, read `window.location.hash` on load to restore tab state. Low-effort, high-value for shareability.

---

## Category 8 — Charts & Data 🟢 LOW

### 8.1 Chart library choice: correct
**Finding:** LightweightCharts (TradingView) for the price chart. This matches the skill database recommendation for financial OHLC/real-time data. ✅ No change needed.

### 8.2 Chart has no table fallback for accessibility
**Finding:** The LightweightCharts canvas has no `aria-label` and no accessible data table alternative. Screen readers see only a blank canvas element.  
**Rule:** `data-table`, `screen-reader-summary`  
**Fix:** Add `aria-label="BTC price chart, 1H timeframe"` to the chart container div. Optionally add a visually-hidden `<table>` with OHLCV data for the visible candles.

### 8.3 Correlation heatmap: color-only encoding
**Finding:** The heatmap uses only background color intensity to convey correlation strength. No numerical values are shown by default (hover-only).  
**Rule:** `pattern-texture`, `direct-labeling`  
**Fix:** Show correlation values as text inside each cell (e.g. `0.42`) rather than requiring hover.

---

## Positive Findings — What's Working Well

| Area | Finding |
|------|---------|
| **Color system** | `--muted2 #9a8e7e` → 6.16:1 ✅, `--white #ede6d6` → 15.9:1 ✅, amber → 9.75:1 ✅ |
| **Design identity** | Amber/warm-black with Anybody + Fira Code is distinctive and appropriate for trading |
| **Loading discipline** | JS correctly disables buttons and shows spinners on async ops |
| **Ambient grid** | Subtle amber grid overlay adds depth without competing with data |
| **Dark mode** | Single-mode dark design is correct for a trading tool — no light mode needed |
| **Mobile layout** | Two-breakpoint responsive system handles the key layout shifts correctly |
| **Font family** | Three-family system (display + mono + body) is above average for fintech |
| **Color tokens** | CSS custom properties used consistently — `--amber`, `--green`, `--red`, `--bg` etc. |
| **Scanner loading** | `btn.disabled` + text change on scan is correct pattern |

---

## Priority Fix Order

| # | Issue | Severity | Effort |
|---|-------|----------|--------|
| 1 | Add global `:focus-visible` rule | 🔴 Critical | 5 min |
| 2 | Fix `--muted #6b6050` contrast | 🔴 Critical | 5 min |
| 3 | Add `prefers-reduced-motion` block | 🔴 Critical | 30 min |
| 4 | Add directional icon to BUY/SELL/HOLD in MTF + scanner | 🔴 Critical | 1h |
| 5 | Increase gpill/rb-btn/pill touch targets to min 44px | 🟠 High | 2h |
| 6 | Add `aria-live="polite"` to signal output + calcGuidance | 🟠 High | 30 min |
| 7 | Add `#analyzeBtn:disabled` visual CSS (spinner) | 🟠 High | 30 min |
| 8 | Raise minimum font-size floor to 11px | 🟠 High | 2h |
| 9 | Add `&display=swap` to Google Fonts link | 🟡 Medium | 2 min |
| 10 | Add `role="tablist"` / `role="tab"` / `aria-selected` to nav | 🟡 Medium | 1h |
| 11 | Add `:active` states to scanner rows for mobile tap feedback | 🟡 Medium | 30 min |
| 12 | Add `min-height: 100dvh` fallback | 🟡 Medium | 2 min |
| 13 | Add visible labels to calculator inputs | 🟡 Medium | 1h |
| 14 | Deep-link tab navigation via `history.pushState` | 🟡 Medium | 2h |
| 15 | Show correlation values as text in heatmap cells | 🟢 Low | 30 min |
| 16 | Replace `max-height` transition with grid-rows animation | 🟢 Low | 1h |

---

## Design System Recommendation (from skill database)

The skill database confirms DotVerse's current direction is correct for the product type:
- **Style:** Dark Mode (OLED) — correct ✅
- **Color system:** Fintech/Crypto palette — `#F59E0B` amber primary, `#0F172A` deep bg, `#00c98d` green, `#EF4444` red — DotVerse's actual palette closely matches ✅
- **Typography:** "Modern Dark Cinema" (Inter) or "Developer Mono" (JetBrains + IBM Plex) — current Anybody+FiraCode+Sora is equally valid and more distinctive ✅
- **Anti-patterns to avoid:** The current design avoids light mode, slow rendering, and blob/liquid backgrounds — all correct ✅

**The design direction is right. The execution gaps are in accessibility, touch targets, and text size — not in visual identity.**
