# WR Pattern Badge — Design Spec (Phase 2.5)

## Overview

A small, compact badge on each signal card displaying the **historical win rate
for the exact pattern** (ticker + timeframe + signal + trade_type combination).
This is different from the existing per-signal backtest badge (`_btWr`) — the
pattern WR aggregates outcomes from ALL past signals of the same pattern across
the user's history.

---

## 1. Placement in opp-card Template

### Current Card Layout (line ~8405 of index-v2-prototype.html)

```
.opp-card
  .opp-card-header          (rank + ticker/asset + BUY/SELL badge)
  .opp-card-mid             (flex row: gap 14px)
    .opp-conf-wrap          (52px ring + center %)
    .opp-card-right         (RR + conf label + entry/SL/TP levels)
  [btBadge row]             (BACKTEST VERIFIED ... WR xx% · PF xx · xx trades)
  .opp-reason
  [SMC badges]
  [live price strip]
  [verdict row]
  .opp-card-footer          (Analyse button)
```

### New Placement

The WR Pattern Badge is inserted **immediately after `.opp-conf-wrap`** inside
`.opp-card-mid`, as a new element. To keep the conf ring visually paired with
the badge, both are wrapped in a small columnar container.

**Insertion point (exact, in the oppCards map callback):**

After line 8423:
```javascript
+ '</svg><div class="opp-conf-center"><span class="opp-conf-pct" style="color:' + cc + '">' + o.conf + '</span></div>'
+ '</div>'
```

Replace the existing single `.opp-conf-wrap` with a wrapper column:

```html
<div class="wr-pat-conf-col">
  <div class="opp-conf-wrap">
    <!-- existing SVG + center -->
  </div>
  <div class="wr-pat-badge ...">...</div>
</div>
```

**Template pseudocode (exact insertion):**

```javascript
// After line 8423, replace the end of opp-conf-wrap section:
// OLD: ...'</div>'  (closes opp-conf-wrap)
//      + '<div class="opp-card-right">'...
//
// NEW: wraps conf-wrap + badge in wr-pat-conf-col

+ '</div>'  // closes opp-conf-center
+ '</div>'  // closes opp-conf-wrap

// --- WR Pattern Badge (new) ---
+ '<div class="wr-pat-badge ' + wrPatClass + '" data-wr="' + (wrPatPct||0) + '" title="How often this pattern wins historically.">'
+   '<span class="wr-pat-bar-fill" style="--wr-bar:' + (wrPatPct||0) + '%"></span>'
+   '<span class="wr-pat-text">' + wrPatLabel + '</span>'
+ '</div>'
+ '</div>'  // closes wr-pat-conf-col

+ '<div class="opp-card-right">'...
```

Where `wrPatClass`, `wrPatLabel`, and `wrPatPct` are computed per-card
(see Section 3 and Cache Strategy below).

---

## 2. CSS — All Classes (prefix: .wr-pat-*)

Insert CSS block **after the existing `.opp-conf-pct` rule** (line ~2141 in index-v2-prototype.html).

```css
/* ── WR Pattern Badge (Phase 2.5) ── isolated prefix .wr-pat-* ── */

/* Column wrapper: conf ring + badge stacked */
.wr-pat-conf-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

/* The badge itself */
.wr-pat-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 7px;
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .03em;
  line-height: 1;
  white-space: nowrap;
  cursor: default;
  position: relative;
  overflow: hidden;
  min-width: 0;
  max-width: 120px;
  animation: wrPatPop .42s cubic-bezier(.34,1.56,.64,1) both;
}

/* Bar track (background layer) */
.wr-pat-badge::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 4px;
  z-index: 0;
}

/* Bar fill element (animated width) */
.wr-pat-bar-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 4px;
  z-index: 0;
  width: 0%;
  animation: wrPatBarFill .65s cubic-bezier(.4,0,.2,1) .18s both;
}

/* Text sits above the bar */
.wr-pat-text {
  position: relative;
  z-index: 1;
}

/* ── Colour thresholds ── */
.wr-pat-high .wr-pat-bar-fill {
  background: rgba(38,166,91,.13);
}
.wr-pat-high {
  background: rgba(38,166,91,.05);
  border: 1px solid rgba(38,166,91,.22);
  color: #26a65b;
}

.wr-pat-mid .wr-pat-bar-fill {
  background: rgba(245,166,35,.13);
}
.wr-pat-mid {
  background: rgba(245,166,35,.05);
  border: 1px solid rgba(245,166,35,.22);
  color: #f5a623;
}

.wr-pat-low .wr-pat-bar-fill {
  background: rgba(224,85,85,.13);
}
.wr-pat-low {
  background: rgba(224,85,85,.05);
  border: 1px solid rgba(224,85,85,.22);
  color: #e05555;
}

.wr-pat-none,
.wr-pat-loading {
  background: rgba(255,255,255,.03);
  border: 1px solid rgba(255,255,255,.08);
  color: rgba(255,255,255,.35);
}

/* ── Loading state: subtle pulse ── */
.wr-pat-loading {
  min-width: 74px;
  justify-content: center;
  gap: 3px;
}
.wr-pat-loading .wr-pat-text {
  animation: wrPatPulse 1.4s ease-in-out infinite;
}
@keyframes wrPatPulse {
  0%, 100% { opacity: .35; }
  50%      { opacity: .7;  }
}
.wr-pat-loading .wr-pat-bar-fill {
  display: none;
}

/* ── No-data state: muted ── */
.wr-pat-none .wr-pat-bar-fill {
  display: none;
}

/* ── Tooltip (native title attr) ── */
.wr-pat-badge[title] {
  /* native title handles the hover tooltip */
}

/* ── Entrance animation ── */
@keyframes wrPatPop {
  from { opacity: 0; transform: scale(.88); }
  to   { opacity: 1; transform: scale(1);    }
}

/* ── Bar fill animation ── */
@keyframes wrPatBarFill {
  from { width: 0%; }
  to   { width: var(--wr-bar, 0%); }
}

/* ── Mobile: 375px width ── */
@media(max-width:480px) {
  .wr-pat-conf-col {
    gap: 4px;
  }
  .wr-pat-badge {
    font-size: 10px;
    padding: 2px 6px;
    max-width: 100px;
  }
}
```

**CSS insertion location:** Add after the `.opp-conf-pct {}` rule block (around line 2141)
and before the `.opp-card-right {}` rules. This keeps all card-middle styles
together.

---

## 3. Copy by State

| State               | Condition                               | CSS Class       | Display Text                 |
|----------------------|-----------------------------------------|-----------------|------------------------------|
| Loading              | WR data fetch not yet complete          | `wr-pat-loading` | `WR ...` (pulsing 3 dots)   |
| High win rate        | WR ≥ 55%                                | `wr-pat-high`   | `WR 65% (17)` (green)       |
| Mid win rate         | WR 45–54%                               | `wr-pat-mid`    | `WR 50% (6)` (amber)        |
| Low win rate         | WR < 45%                                | `wr-pat-low`    | `WR 35% (8)` (red)          |
| Not enough data      | sample_size < 5                         | `wr-pat-none`   | `Not enough data` (muted)   |
| Error / timeout      | fetch failed or 0 patterns matched      | *(badge hidden)* | *(empty string — omit)*     |

**Caveat:** The `<5 samples` state may also arise from the API's built-in
MIN_SAMPLES=5 filter (the API excludes groups <5 already). If the pattern is
not in the API response at all, the frontend treats it as "no data".

---

## 4. HOLD Signal Treatment

HOLD signals still show the WR pattern badge. The API endpoint already filters
on `SignalHistory.signal.in_(["BUY", "SELL"])` — meaning it only mines data
from decided BUY/SELL outcomes. So a HOLD signal on a pattern that was
previously BUY or SELL will still display the historical win rate for those
outcomes. This is correct: "BUY/SELL patterns have outcomes even if current
recommendation is HOLD."

No special logic needed in the frontend — just match by `(ticker, timeframe, sig, trade_type)` where `sig` comes from `o.sig` (which may be HOLD).

**Note:** If the current signal is HOLD, `o.sig` is `"HOLD"` but the API only
has entries for BUY/SELL. The frontend should **also** try matching with
`"BUY"` and `"SELL"` as fallback keys if the exact sig key is not found.
Since HOLD is just a recommendation — the pattern category is still the
underlying setup — showing the BUY or SELL WR gives better UX.

**Implementation:** When `o.sig === "HOLD"`, query the local cache for
keys with both `"BUY"` and `"SELL"` for the same ticker/tf/trade_type;
use whichever has more samples.

---

## 5. Colour Thresholds (Visual Reference)

```
WR ≥ 55%   →  .wr-pat-high   →  color: #26a65b, bg: rgba(38,166,91,.05),  border: rgba(38,166,91,.22)
WR 45-54%  →  .wr-pat-mid    →  color: #f5a623, bg: rgba(245,166,35,.05), border: rgba(245,166,35,.22)
WR < 45%   →  .wr-pat-low    →  color: #e05555, bg: rgba(224,85,85,.05),  border: rgba(224,85,85,.22)
No data    →  .wr-pat-none   →  color: rgba(255,255,255,.35), bg: rgba(255,255,255,.03), border: rgba(255,255,255,.08)
Loading    →  .wr-pat-loading→  same as none + pulse animation
Error      →  badge hidden   →  empty string renders nothing
```

These colours match the existing design language used across the site
(confidence ring colours, badge colours, backtest badge).

---

## 6. Mobile Behaviour (375px)

At 375px width, the card `.opp-card-mid` already handles wrapping via
its flex layout. The `.wr-pat-conf-col` wrapper is `flex-shrink: 0` and
the badge fits within the 52px width of the conf ring, so it does not
cause overflow.

- **Badge max-width:** 120px (desktop), 100px (mobile)
- **Font size:** 11px desktop, 10px mobile (still ≥ spec minimum 11px on desktop)
- **Gap reduced:** 6px → 4px on mobile
- The badge is centered below the conf ring via the column wrapper's `align-items:center`
- At 375px, the card is still a single column; the badge sits between
  the conf ring and the backtest badge row — no horizontal cramping

---

## 7. Animations

### Entrance: badgePop → wrPatPop
```
@keyframes wrPatPop {
  from { opacity: 0; transform: scale(.88); }
  to   { opacity: 1; transform: scale(1);    }
}
animation: wrPatPop .42s cubic-bezier(.34,1.56,.64,1) both;
```
Spring-in effect matching the existing MTF cell animations. The cubic-bezier
curve provides an overshoot-and-settle feel.

### Bar fill: barFill → wrPatBarFill
```
@keyframes wrPatBarFill {
  from { width: 0%; }
  to   { width: var(--wr-bar, 0%); }
}
animation: wrPatBarFill .65s cubic-bezier(.4,0,.2,1) .18s both;
```
The bar fills from 0% to the WR percentage over 0.65s, delayed 0.18s
(so entrance finishes first). The CSS variable `--wr-bar` is set inline
on the `.wr-pat-bar-fill` element.

---

## 8. Cache Strategy (Avoid N+1)

### API: `GET /api/signals/winrate-by-pattern` (already exists)

Returns all patterns for the user:
```json
{
  "patterns": [
    {
      "ticker": "BTCUSDT", "timeframe": "1H", "signal": "BUY",
      "trade_type": "Day Trade", "wr_pct": 65.3,
      "sample_size": 17, "wins": 11, "losses": 6, "avg_r": 0.42
    },
    ...
  ]
}
```

### Frontend Cache

Fetch once when the Signals tab loads, store in a local Map keyed by
`"ticker|timeframe|signal|trade_type"`.

**Implementation in `_sfDoScan()` (around line 8240):**

```javascript
// Fetch per-pattern WR data once and cache locally
var _wrPatCache = null;
var _wrPatPromise = null;

function _wrPatFetch() {
  if (_wrPatCache) return Promise.resolve(_wrPatCache);
  if (_wrPatPromise) return _wrPatPromise;
  _wrPatPromise = fetch('/api/signals/winrate-by-pattern')
    .then(function(r){ return r.json(); })
    .then(function(data){
      var map = {};
      (data.patterns || []).forEach(function(p){
        var key = [p.ticker, p.timeframe, p.signal, p.trade_type].join('|');
        map[key] = p;
      });
      _wrPatCache = map;
      return map;
    })
    .catch(function(){
      _wrPatCache = {};  // Don't retry on failure
      return {};
    });
  return _wrPatPromise;
}
```

**Lookup per card (inside oppCards map callback):**

```javascript
var _tt = _tradeTypeLabel(o.tf, window._stratMode);
var wrPatKey = [o.sym, o.tf, o.sig, _tt.label].join('|');
var wrPatData = _wrPatCache ? _wrPatCache[wrPatKey] : null;

// HOLD fallback: also check BUY and SELL keys
if (!wrPatData && o.sig === 'HOLD') {
  var wrPatKeyBuy = [o.sym, o.tf, 'BUY', _tt.label].join('|');
  var wrPatKeySell = [o.sym, o.tf, 'SELL', _tt.label].join('|');
  var buyData = _wrPatCache[wrPatKeyBuy];
  var sellData = _wrPatCache[wrPatKeySell];
  if (buyData && sellData) {
    wrPatData = buyData.sample_size >= sellData.sample_size ? buyData : sellData;
  } else {
    wrPatData = buyData || sellData || null;
  }
}
```

### Lifecycle

1. `_sfDoScan()` already has `_sfScanRunning` guard; WR fetch kicks off
   in parallel with backtest scans (non-blocking).
2. WR data is resolved before `oppCards` is generated (awaited).
3. Cache persists for the session — cleared on full page reload.
4. TTL: none needed (data only changes when new signals are decided,
   which requires a page reload or navigate-away/back).

**Integration point in `_sfDoScan()`:** After backtest results are processed
but before `displayOpps.map()`, await `_wrPatFetch()`.

---

## 9. Beginner-Friendly Tooltip

The native HTML `title` attribute on `.wr-pat-badge`:

```html
title="How often this pattern wins historically."
```

This provides a subtle tooltip on hover (desktop only — touch devices
don't show title tooltips, which is acceptable for mobile).

**Alternative for touch:** A small `ⓘ` icon could be added, but the
simplicity of the `title` approach keeps the badge clean and the
explanation discoverable. The text is self-explanatory enough
("WR 65% (17)" — even beginners understand win rate and sample count).

---

## 10. Edges & Error Handling

| Case | Behavior |
|------|----------|
| WR fetch in progress, cards rendering | Show `.wr-pat-loading` with pulsing "WR ..." |
| WR fetch completes after cards rendered | Update badges in-place via `document.querySelectorAll('.wr-pat-loading')` |
| WR fetch fails (network/timeout) | Show `.wr-pat-none` with "Not enough data" (graceful degradation) |
| Pattern has < 5 samples (API excluded it) | Key not in cache → `.wr-pat-none` with "Not enough data" |
| Pattern exists but all outcomes are BE | API excludes BE from `wr_pct` calculation; if win+loss < 5, key excluded |
| Card width < 375px | `.wr-pat-badge` max-width and font-size reduce via media query |
| Card re-renders (filter change) | WR cache is already populated — no re-fetch needed |
| HOLD signal, no BUY/SELL WR data | Badge hidden (null key fallback → render empty string) |
| Multiple cards for same ticker+tf+sig+type | Same cache key → all cards show same WR (correct) |

---

## 11. Build Steps Summary

### Files to modify
1. **static/index-v2-prototype.html** — Three insertions:

   **A. CSS block** (after line ~2141, before `.opp-card-right` rule):
   Add the full `.wr-pat-*` CSS block from Section 2.

   **B. JavaScript: _wrPatFetch function** (before `_sfDoScan`, around line 8200):
   Add the cache/fetch logic from Section 8.

   **C. Template: oppCards map callback** (inside `_sfDoScan`, around line 8419-8432):
   - Replace `.opp-conf-wrap` section with `.wr-pat-conf-col` wrapper
   - Add `.wr-pat-badge` element with computed class/text

   **D. Post-render update** (after `listNow.innerHTML = _finalHtml`, around line 8486):
   If WR fetch was still in-flight, update badges once resolved:

   ```javascript
   // Update any loading WR badges once pattern data resolves
   _wrPatFetch().then(function(cache){
     var badges = document.querySelectorAll('.wr-pat-loading');
     badges.forEach(function(b){ /* recompute and update class/text */ });
   });
   ```

### No new files created
All changes are inline in the single HTML file. This keeps deployment simple
(single static asset).

### Testing checklist
- [ ] Desktop: green badge for WR ≥ 55%
- [ ] Desktop: amber badge for WR 45-54%
- [ ] Desktop: red badge for WR < 45%
- [ ] Desktop: "Not enough data" for patterns with < 5 samples
- [ ] Desktop: loading pulse state visible briefly before cache populates
- [ ] Desktop: tooltip "How often this pattern wins historically." on hover
- [ ] Mobile 375px: badge does not overflow card width
- [ ] Mobile 375px: font-size ≥ 10px (legible)
- [ ] HOLD signal card still shows WR (from BUY or SELL key fallback)
- [ ] Animation plays on first render only (card re-render skips animation via cache)
- [ ] Existing backtest badge (line 8373-8382) unaffected by new badge
- [ ] No CSS class collisions — all new classes prefixed `.wr-pat-*`
