# DotVerse Market Tab — UX Design for Beginner Traders

**Date:** May 29, 2026
**Status:** Design Document (Read-Only)
**Audience:** Beginner traders logging into DotVerse for the first time
**Goal:** A beginner should understand what the market is doing, why, and what to do next — within 3 seconds of landing on this tab.

---

## Design Philosophy

**The problem:** The current Market tab shows data (a heatmap, sector bars, prices) but not *meaning*. A beginner sees numbers without context and has no idea whether today is a good day to trade or what they should click next.

**The fix:** Every element on this page answers exactly one of these questions:
1. **"Is today a good day to trade?"** → Section 1 verdict + gauge
2. **"What's causing this?"** → Section 2 news
3. **"What should I do about it?"** → Section 3 signals + CTA

---

## Layout Overview (3 Scrollable Sections)

```
┌──────────────────────────────────────────────────────┐
│  🟢 DotVerse Market  ● LIVE ●  [Find Trades →]      │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ═══ SECTION 1: WHAT'S HAPPENING RIGHT NOW ═══      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Markets are 🟢 BULLISH today                  │  │
│  │                                                │  │
│  │  "Stocks are broadly rising. Volatility is low │  │
│  │   (VIX 14.2 — calm conditions). Fear & Greed  │  │
│  │   is at 62 (Greed). S&P 500 is up 0.8%. This  │  │
│  │   is a favorable environment for trading."     │  │
│  │                                                │  │
│  │  ┌──────────────────┐  ┌──────────────────┐   │  │
│  │  │  S&P 500 ▲ 0.8%  │  │  VIX  14.2       │   │  │
│  │  │  "Stocks up —    │  │  "Low — markets   │   │  │
│  │  │   broad rally"   │  │   are calm"       │   │  │
│  │  └──────────────────┘  └──────────────────┘   │  │
│  │  ┌──────────────────┐  ┌──────────────────┐   │  │
│  │  │  NASDAQ ▲ 1.2%   │  │  Fear & Greed    │   │  │
│  │  │  "Tech leading — │  │  62 — Greed      │   │  │
│  │  │   strong day"    │  │  "Optimistic but  │   │  │
│  │  │                  │  │   not overdone"  │   │  │
│  │  └──────────────────┘  └──────────────────┘   │  │
│  │                                                │  │
│  │  [🟢 GOOD DAY TO TRADE — View Opportunities ↓] │  │
│  └────────────────────────────────────────────────┘  │
│                                                       │
│  ═══ SECTION 2: WHAT'S MOVING MARKETS ═══           │
│  ┌────────────────────────────────────────────────┐  │
│  │  📰 Fed signals rate hold — dollar steady      │  │
│  │  What this means: Good for bonds, neutral for  │  │
│  │  stocks. No surprise = no volatility spike.    │  │
│  │  Affects: DXY, TLT, SPY          Reuters · 2h  │  │
│  ├────────────────────────────────────────────────┤  │
│  │  📰 NVDA announces new AI chip — up 3.4%       │  │
│  │  What this means: Strong buying pressure in    │  │
│  │  semiconductors. Other chip stocks may follow. │  │
│  │  Affects: NVDA, AMD, SMH          Bloomberg·4h │  │
│  ├────────────────────────────────────────────────┤  │
│  │  📰 Oil inventories drop — crude up 0.9%       │  │
│  │  What this means: Energy stocks getting a      │  │
│  │  boost. Oil below recent highs still.          │  │
│  │  Affects: XLE, XOM, CVX             EIA · 6h   │  │
│  └────────────────────────────────────────────────┘  │
│                                                       │
│  ═══ SECTION 3: TODAY'S OPPORTUNITIES ═══           │
│  ┌────────────────────────────────────────────────┐  │
│  │  3 high-confidence signals active across       │  │
│  │  4 markets                                     │  │
│  │                                                │  │
│  │  ★ BEST SIGNAL TODAY                           │  │
│  │  ┌────────────────────────────────────────┐   │  │
│  │  │  BTC/USD  BUY                           │   │  │
│  │  │  Confidence: 92%  ·  4-hour timeframe   │   │  │
│  │  │  Entry: $68,240   ·  R:R 2.8           │   │  │
│  │  │                                         │   │  │
│  │  │  [ VIEW ALL DETAILS IN SIGNALS → ]      │   │  │
│  │  └────────────────────────────────────────┘   │  │
│  │                                                │  │
│  │  Other active signals:                         │  │
│  │  ┌────┐ ┌────┐ ┌────┐                         │  │
│  │  │NVDA│ │GOLD│ │EUR │                         │  │
│  │  │BUY │ │BUY │ │SELL│                         │  │
│  │  │87% │ │85% │ │73% │                         │  │
│  │  └────┘ └────┘ └────┘                         │  │
│  │                                                │  │
│  │  [ VIEW ALL SIGNALS → SIGNAL TAB ]             │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## Section 1 — "What's Happening Right Now"

### Purpose
Answer in <3 seconds: **"Is today a good day to trade?"**

### Layout
Vertical stack containing:
1. **Verdict banner** — one-line summary with emoji + label
2. **Plain English summary** — 2-3 sentences explaining what's happening
3. **4 key metric cards** — S&P 500, VIX, NASDAQ, Fear & Greed (each with context)
4. **CTA button** — either "Good day to trade" (green) or "Caution today" (amber) that scrolls to Section 3

### Data Sources
| Data Point | Source | How to Explain It |
|---|---|---|
| S&P 500 change | `/api/prices` | "S&P 500 is the broad U.S. stock market index" |
| NASDAQ change | `/api/prices` | "NASDAQ tracks tech stocks" |
| VIX value | `/api/vix` | "VIX = market fear gauge. Low = calm. High = panic." |
| Fear & Greed | `/api/fear-greed` | "Measures investor emotion. 0=Extreme Fear, 100=Extreme Greed" |
| Sector breadth | `/api/sectors` | "% of sectors in the green today" |

### Composite Verdict Algorithm
Compute a simple beginner-facing verdict from:

1. **VIX Zone** (primary signal — the "fear gauge"):
   - VIX < 14: 🟢 "Calm — good for trading"
   - VIX 14–20: 🟢 "Normal — favorable"
   - VIX 20–25: 🟡 "Elevated — be selective"
   - VIX 25–30: 🟠 "Nervous — caution advised"
   - VIX ≥ 30: 🔴 "Stressed — defensive posture"

2. **Fear & Greed** (secondary):
   - 0–25: 🔴 Extreme Fear
   - 25–45: 🟡 Fear
   - 45–55: 🟡 Neutral
   - 55–75: 🟢 Greed
   - 75–100: 🟢 Extreme Greed

3. **Market Direction** (tertiary):
   - S&P 500 % positive
   - Most sectors green

**Final verdict labels:**
- 🟢 **GOOD DAY TO TRADE** — Low fear, broad strength
- 🟡 **CAUTION — BE SELECTIVE** — Mixed signals, elevated VIX
- 🔴 **DEFENSIVE — WATCH ONLY** — High fear, broad weakness

### Plain English Summary Templates

**Bullish template:**
> "Markets are 🟢 bullish today. The VIX is low (14.2 — meaning markets are calm), sectors are broadly green, and investor sentiment is positive following yesterday's Fed comments. S&P 500 is up 0.8%. This is a favorable environment for trading."

**Mixed template:**
> "Markets are 🟡 mixed today. The VIX is elevated (22.1 — some nervousness), and sectors are split between winners and losers. The NASDAQ is up but financials are dragging. Proceed with selective trades."

**Bearish template:**
> "Markets are 🔴 under pressure today. The VIX is elevated (27.3 — investors are nervous), most sectors are in the red, and the Fear & Greed index shows Fear (38/100). Consider waiting or using defensive strategies."

### Metric Cards — Design Rules

Each card MUST include:
- **The number**
- **Plain English context** in parentheses
- **Direction arrow** (▲/▼/→)
- **1-line explanation** of why you should care

Examples:

| Card | Display |
|---|---|
| S&P 500 | `S&P 500 ▲ +0.8%` → "Broad market is rising today" |
| VIX | `VIX 14.2` → "Low (calm) — good trading conditions" |
| NASDAQ | `NASDAQ ▲ +1.2%` → "Tech stocks are leading today" |
| Fear & Greed | `Fear & Greed: 62` → "Greed — investors are optimistic" |

### States

**Loading:** Shimmer skeleton for each card + "Reading the markets..." text
**Error:** Each card shows "—" with "Data pending" + retry icon
**Pre-market:** Show context "Market opens in 2h 15m" + pre-market indicators if available

### CTA Button Behavior

Based on the verdict:
- 🟢 **"🟢 Good day to trade — See opportunities ↓"** → Scrolls to Section 3
- 🟡 **"🟡 Cautious market — Find selective trades →"** → Scrolls to Section 3 (filtered to highest-confidence only)
- 🔴 **"🔴 Defensive market — Monitor only"** → Shows modal: "Today's conditions favor waiting. Check back later or use the SIGNAL tab for alerts."

---

## Section 2 — "What's Moving Markets"

### Purpose
Answer: **"Why is the market doing what it's doing?"** A beginner needs to connect news events to market movement.

### Layout
Scrollable vertical list of news cards (not a grid — easier to read). Show 3 by default, expandable to show up to 8.

### Data Source
`/api/news` (Finnhub) — already returns structured articles with headlines, sources, timestamps, URLs.

### News Card Design

```
┌─────────────────────────────────────────────────────┐
│ 📰  Fed signals rate hold · dollar steady           │
│                                                     │
│  What this means for your trading:                  │
│  No surprise = markets stay calm. Bonds look good   │
│  for conservative traders. Stocks neutral.          │
│                                                     │
│  Tickers affected: DXY · TLT · SPY                  │
│                                Reuters · 2h ago  ↗  │
└─────────────────────────────────────────────────────┘
```

**Each card contains exactly:**
1. **Headline** — the news title (from Finnhub)
2. **"What this means for your trading"** — 1-2 sentences of plain-English explanation. Classified on the backend or frontend using keyword heuristics.
3. **"Tickers affected"** — comma-separated symbols this news impacts (derived from headline + category mapping)
4. **Source + timestamp** — e.g., "Reuters · 2h ago"
5. **Click behavior** — opens article URL in new tab (use existing `url` field from Finnhub)

### Classifying News Direction

Use simple keyword matching on the headline:

| Direction | Keywords | Icon |
|---|---|---|
| Bullish | "surge" "rally" "beat" "upgrade" "bullish" "gains" "positive" "boost" | ⬆ |
| Bearish | "plunge" "crash" "miss" "downgrade" "fear" "slump" "sell-off" "woes" | ⬇ |
| Neutral | (default if no strong keywords) | ➡ |

Or use `/api/news` sentiment field if available from Finnhub.

### Empty State
If no recent news:
> "No recent news for your active markets. Markets may be in a quiet period. Check the SIGNAL tab for technical opportunities."

### Expand/Collapse
- "Show 3 more news →" button below the 3 visible cards
- After expanding: "Show less ↑"

---

## Section 3 — "Today's Opportunities"

### Purpose
Answer: **"What should I trade right now?"** and **"Where do I click to take action?"**

### Layout
1. **Summary header** — "X high-confidence signals active across Y markets"
2. **Best Signal card** — hero card with highest-confidence signal
3. **Signal chips** — smaller cards for remaining active signals
4. **Global CTA** — "View all in SIGNALS →"

### Data Sources
| Data Point | Endpoint |
|---|---|
| Latest signals | `/api/signals/history?limit=50` |
| Signal stats | `/api/signals/stats` |
| Performance stats | `/api/performance/stats` |

### Summary Header
Calculated from filtering `/api/signals/history` for signals where `confidence_label` is "HIGH" or "CONFIRMED".

**Examples:**
- "3 high-confidence signals active across 4 markets"
- "No high-confidence signals active right now"

### Best Signal Card

The signal with the highest confidence value from the filtered list.

```
┌─────────────────────────────────────────────────────┐
│ ★ BEST SIGNAL TODAY                                 │
│                                                     │
│  BTC/USD     BUY ▲                                  │
│  Confidence: 92%  ·  Timeframe: 4-hour chart        │
│                                                     │
│  Entry price:  $68,240                              │
│  Stop loss:    $66,500  (risk: -2.5%)               │
│  Take profit:  $70,000  (reward: +2.6%)             │
│                                                     │
│  Risk/Reward ratio: 1 : 2.8                         │
│  (For every $1 you risk, you could make $2.80)      │
│                                                     │
│  [ VIEW FULL DETAILS IN SIGNALS → ]                 │
└─────────────────────────────────────────────────────┘
```

**Design rules for the best signal card:**
- ★ badge clearly marks it as "Best Today"
- Direction visualization: BUY in green badge, SELL in red badge
- **Every number has context:**
  - R:R explained: "For every $1 you risk, you could make $2.80"
  - Confidence explained: "92 out of 100 — very high conviction"
  - Timeframe explained: "4-hour chart (medium-term setup)"
- [VIEW IN SIGNALS →] button navigates to the SIGNAL tab with this signal focused

### Signal Chips (other active signals)

If there are 2+ active signals, show the next best ones as smaller chips:

```
┌───────┐ ┌───────┐ ┌───────┐
│ NVDA  │ │ GOLD  │ │ EUR   │
│  BUY  │ │  BUY  │ │ SELL  │
│  87%  │ │  85%  │ │  73%  │
│  1D   │ │  4H   │ │  1H   │
└───────┘ └───────┘ └───────┘
```

Each chip shows: ticker, direction (BUY/SELL colored badge), confidence %, timeframe.
Click → navigates to SIGNAL tab with that signal focused.

### Empty State (no signals)

```
┌─────────────────────────────────────────────────────┐
│  No high-confidence signals active right now         │
│                                                     │
│  Market conditions aren't generating clear          │
│  entry signals at this moment. You can:             │
│                                                     │
│  [ SCAN MARKETS TO FIND OPPORTUNITIES → ]           │
│  [ SET UP ALERTS IN SIGNALS TAB ]                   │
└─────────────────────────────────────────────────────┘
```

Both buttons navigates to the SIGNAL tab.

### Loading State
Shimmer pill shapes for each chip + "Analyzing market conditions..." text.

---

## Interaction Behavior Matrix

| Element | Click | Hover | Animation |
|---|---|---|---|
| Verdict banner | Scrolls to Section 3 | Subtle glow | Gentle pulse on load |
| Metric card | Open in chart viewer | Slight scale + shadow | Fade in staggered |
| "Good day" CTA | Scroll to Section 3 | Color brighten | None |
| News card headline | Open article in new tab | Card lifts slightly | Slide-up on load |
| "Show more news" | Expand news list | Underline | Smooth expand |
| Best Signal card | Navigate to SIGNAL tab | Glow border + shadow | Hero entrance (scale up) |
| Signal chip | Navigate to SIGNAL tab | Scale + border highlight | Staggered fade-in |
| "View all" CTA | Navigate to SIGNAL tab | Color change | None |
| Empty state buttons | Navigate to SIGNAL tab | Standard hover | Gentle fade-in |

---

## Color & Visual Design

### Existing DotVerse Palette (preserve)
- Background: `rgba(9,8,13,.68)` with backdrop blur
- Text primary: `rgba(226,221,245,.92)`
- Text secondary: `rgba(226,221,245,.45)`
- Green (up/bullish): `#62f29d` / `#5de8a0`
- Red (down/bearish): `#f07070` / `#e8706e`
- Amber (neutral/caution): `#c9a84c`
- Accent: `rgba(148,175,220,.*)` — soft blue-gray

### New CSS Classes Needed

```css
/* Section containers */
.mkt-section { }                    /* Spacer + section header */
.mkt-section-header { }             /* "What's Happening Right Now" heading */

/* Section 1 — Verdict & Metrics */
.mkt-verdict-banner { }             /* The big green/yellow/red pill at top */
.mkt-verdict-summary { }            /* Plain English text block */
.mkt-metric-card { }                /* Individual metric (S&P, VIX, etc.) */
.mkt-metric-card .value { }         /* Big number */
.mkt-metric-card .context { }       /* Plain English explanation */
.mkt-cta-button { }                 /* "Good day to trade" / "Caution" button */

/* Section 2 — News */
.mkt-news-card { }                  /* News item card */
.mkt-news-impact { }                /* "What this means" section */
.mkt-news-tickers { }               /* Ticker badges row */
.mkt-news-source { }                /* Source + time */
.mkt-news-expand { }                /* "Show more" toggle */

/* Section 3 — Signals */
.mkt-signal-summary { }             /* "X signals active" header */
.mkt-signal-best { }                /* Best signal hero card */
.mkt-signal-chip { }                /* Small signal pills */
.mkt-signal-empty { }               /* Empty state container */
```

### Emoji Legend
Use emoji consistently for quick scanning:

| Emoji | Meaning |
|---|---|
| 🟢 / 🟡 / 🔴 | Verdict (Good / Caution / Defensive) |
| 📰 | News headline |
| ⬆ / ➡ / ⬇ | Direction classification |
| ★ | Best signal badge |
| 🎯 | Key metric |

---

## Error & Edge Cases

### API Failure (per section)

**Section 1 — Metrics**
- Show "—" for each failed metric
- Verdict falls back to last known good state: "Data updating — showing last reading"
- If all metrics fail: "Unable to read market conditions right now. Please check back in a few minutes."

**Section 2 — News**
- Hide the section header and show: "Market news temporarily unavailable"
- Do NOT block the rest of the page

**Section 3 — Signals**
- Show empty state: "Unable to load signals. [Retry]"
- If signals are cached: show cached data with "(Cached)" label

### Slow Connections
- Progressive loading: Section 1 renders first (it's the most important), then Section 2, then Section 3
- Each section has its own loading skeleton
- 10-second timeout per API call before showing error state

### Pre-Market / After-Hours
- Verdict shows: "Pre-market data — markets open in Xh Ym"
- Metric cards show pre-market or futures data with label: "Futures"
- News and signals still load normally

### Weekends / Holidays
- Verdict shows: "Markets closed — [Day name]"
- Summary: "No trading today. Check back [next trading day]."
- News section shows past 48h
- Signals section shows last active signals

---

## Implementation Notes

### Functions to Create

```javascript
function showMarket() {                    // Entry point
  renderMarketShell();                     // Layout skeleton
  loadMarketVerdict();                     // Section 1: composite verdict + plain English
  loadMetricCards();                       // Section 1: S&P, VIX, NASDAQ, F&G
  loadNewsSection();                       // Section 2: /api/news + classification
  loadSignalsOverview();                   // Section 3: /api/signals/history + stats
}
```

### State Object

```javascript
const marketState = {
  verdict: { label: 'Loading...', emoji: '🔄', color: 'neutral', summary: '' },
  metrics: {
    sp500: { value: null, change: null, context: '' },
    vix: { value: null, zone: '', context: '' },
    nasdaq: { value: null, change: null, context: '' },
    fearGreed: { value: null, label: '', context: '' }
  },
  news: [],               // [{ headline, impact, tickers, source, timeAgo, url, direction }]
  signals: {
    total: 0,
    marketCount: 0,
    best: null,           // { ticker, direction, confidence, timeframe, entry, stopLoss, takeProfit, rr }
    active: []            // [{ ticker, direction, confidence, timeframe }]
  }
};
```

### API Integration Summary

| Endpoint | Used By | Purpose |
|---|---|---|
| `GET /api/vix` | Section 1 | VIX value + zone for verdict |
| `GET /api/fear-greed` | Section 1 | Fear & Greed value for verdict |
| `GET /api/sectors` | Section 1, Verdict | Sector breadth for composite score |
| `GET /api/prices` | Section 1 | S&P 500, NASDAQ prices + changes |
| `GET /api/news` | Section 2 | Finnhub news articles |
| `GET /api/signals/history?limit=50` | Section 3 | Active signals for chips + best |
| `GET /api/signals/stats` | Section 3 | Signal performance context |

---

## Beginner UX Principles Applied

1. **3-second verdict** — The very first line of the page tells the user if today is good for trading. No scrolling required.

2. **Plain English always** — Every number has an explanation in parentheses. "VIX: 14.2" is never shown alone; it's always "VIX: 14.2 (Low — calm markets)".

3. **"Why should I care?"** — Every section header answers this question:
   - Section 1: "Is today a good day to trade?"
   - Section 2: "Why is the market moving like this?"
   - Section 3: "What should I trade right now?"

4. **One click to action** — Every section has a clear button that takes the user to the next logical step. No nested menus, no searching for where to click.

5. **Progressive disclosure** — Beginners see the big picture first. Details (charts, full signal analysis) are one click away, not pushed in their face.

6. **Scannable by emoji** — 🟢/🟡/🔴 verdicts, 📰 for news, ★ for best signal — users can scan visually before reading text.

7. **Graceful empty states** — No section ever says "No data." Instead, it tells the user what to do next: "Scan markets to find opportunities →"

8. **Consistent color language** — Green = up/good, Red = down/bad, Amber = mixed/caution. Never green for "HOLD" or any non-obvious meaning.

---

## Migration Path (No Code Changes)

This document is a READ-ONLY design spec. The implementation should:

1. Replace the existing `showMarket()` function structure with the 3-section layout
2. Add the composite verdict algorithm to the existing VIX/F&G data pipeline
3. Add news classification (keywords or sentiment API)
4. Restyle heatmap/sector data into Section 1's metric cards
5. Keep the existing ticker strip and Fear & Greed gauge but reposition them

**Do NOT modify existing code based on this document alone.** This is a UX specification for planning and review.
