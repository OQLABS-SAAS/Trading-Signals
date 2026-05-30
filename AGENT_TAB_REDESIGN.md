# Agent Tab — Cleanup & DotVerse UI Redesign Plan

**Version:** 1.0  
**Date:** May 29, 2026  
**Status:** Design-Phase Specification  
**Design Tokens Source:** DotVerse Brand Guidelines  
**Spec Reference:** `/tmp/trading_agent_spec.txt` + `TRADING_AGENT_PLATFORM_DESIGN.md`

---

## Table of Contents

1. [Research Summary: Old vs New Code](#1-research-summary)
2. [Cleanup: What to Remove](#2-cleanup-what-to-remove)
3. [DotVerse Design Tokens Reference](#3-dotverse-design-tokens-reference)
4. [Agent Tab — Complete UI Design](#4-agent-tab--complete-ui-design)
5. [Sub-Tab Navigation Structure](#5-sub-tab-navigation-structure)
6. [Component-by-Component Specification](#6-component-by-component-specification)
7. [SVG Icon Inventory](#7-svg-icon-inventory)
8. [Implementation Order](#8-implementation-order)
9. [File List: What Gets Touched](#9-file-list-what-gets-touched)

---

## 1. Research Summary

### 1.1 Codebase Landscape

The DotVerse codebase at `/Users/oq/Documents/trading-signals-saas/` contains **two overlapping frontend files** plus a monolithic backend:

| File | Role | Status |
|---|---|---|
| `static/index.html` (14,322 lines) | Old "Momentum" theme — amber/warm-black palette, Anybody/Fira Code/Sora fonts | **DEPRECATED** — kept as fallback |
| `static/index-v2-prototype.html` (24,182 lines) | Current DotVerse-branded UI — gold/warm-white palette, Syne/Space Grotesk/IBM Plex Mono fonts | **ACTIVE** — the real UI |
| `app.py` (18,207 lines) | Monolithic Flask backend — all models, routes, business logic | **ACTIVE** |

### 1.2 What's "Old" — The Forced-Fitted TradingJournal

The Trading Journal UI was **embedded into the v2 prototype's Portfolio/Performance tab** as an afterthought. It uses:

- **Emoji-based emotion selectors** (😌 Confident, 😰 Anxious, 😤 Frustrated, 😐 Neutral, 🤑 Greedy, 😨 Fearful, 🤞 Hopeful, 😃 Excited) — *against DotVerse design philosophy*
- **★ star character ratings** (1–5 stars with Unicode `★`) instead of SVGs
- **Section title "📓 New Journal Entry"** — emoji in heading
- **Inline styles** mixed with minimal CSS classes (`jrnl-emoji-btn`, `jrnl-star`)
- **No sub-tab navigation** — journal is buried inside the Portfolio view
- **Functions:** `selectEmotion()`, `setStarRating()`, `toggleJournal()`

**Location in code:** `static/index-v2-prototype.html` lines ~11,818–11,848 (HTML) and ~12,086–12,107+ (JS)

**Backend model:** `TradingJournal` in `app.py` lines 14,665–14,679 has fields for `emotion`, `trade_rating`, `lesson_learned`, `tags`, `screenshot_url` — these were designed for the emoji/star UI pattern.

### 1.3 What's "New" — The Spec-Compliant Agent Platform

The `TRADING_AGENT_PLATFORM_DESIGN.md` defines:

- **TradingAccount** extended with `deleted_at`, `nickname`, `labels` columns
- **DailyMetrics** model — per-account daily performance with idle-day policy
- **Trade Model consolidation** — unified view across Position/SignalHistory/MT5Order
- **API Endpoints:** `/api/trading-agent/portfolio`, `/api/trading-agent/trades`, `/api/trading-agent/trades/export`, `/api/trading-agent/accounts/<id>/archive`, `/api/trading-agent/accounts/<id>/daily-metrics`, `/api/trading-agent/accounts/<id>/recompute-daily`
- **No emoji/star UI** — the spec focuses on quantitative performance metrics, not emotional journaling

### 1.4 What's Missing — The Agent Tab Itself

Neither `index.html` nor `index-v2-prototype.html` has a dedicated "Agent" tab in the sidebar. The v2 prototype sidebar has:
- Signals → Understand → Scanner → Verdict → Size → Act → Automations → Backtest → Track Record
- Account section: Risk Manager → Portfolio → Performance → Alerts → News → Settings

The spec envisions the Agent as a **focused trade management and analytics hub** — it needs its own top-level sidebar entry.

---

## 2. Cleanup: What to Remove

### 2.1 Frontend — Remove From `static/index-v2-prototype.html`

| Line Range | Content | Action |
|---|---|---|
| ~11,818–11,848 | `jrnlPanel` HTML block (emoji buttons, star ratings, journal form) | **DELETE** — replace with new SVG-based component |
| ~11,849–12,109 | `selectEmotion()`, `setStarRating()`, `toggleJournal()`, `submitJournal()` functions and related journal JS | **DELETE** — replace with clean agent tab rendering |
| Any `.jrnl-emoji-btn`, `.jrnl-star`, `.jrnl-select`, `.jrnl-section-title` CSS | CSS rules | **DELETE** — replace with DotVerse token classes |
| `_journalEmotion`, `_journalRating`, `_journalTicket` global vars | JS globals | **DELETE** |
| `window._journalAccountId` references | Wiring | **DELETE** |
| `📓` emoji in any `innerHTML` | Emoji use | **DELETE** |

### 2.2 Backend — Refactor `app.py`

| Element | Action | Rationale |
|---|---|---|
| `TradingJournal.emotion` field | **DEPRECATE** — keep column for data integrity, stop writing to it from UI | Emotional journaling is not spec-aligned |
| `TradingJournal.trade_rating` field | **DEPRECATE** — keep column, stop writing | Stars are not DotVerse design language |
| `TradingJournal.screenshot_url` field | **DEPRECATE** — keep column | Screenshot upload isn't in MVP spec |
| `/api/accounts/<id>/journal` endpoints (GET/POST) | **KEEP existing** but stop referencing emotion/rating in render path | Backward compatibility |
| `TradingJournal.lesson_learned` | **KEEP** — remap to "Notes" field in new UI | Still useful as trade annotation |

### 2.3 What Stays / Gets Renamed

| Old Element | New Identity |
|---|---|
| `TradingJournal` model | Kept as-is (DB table stays) |
| `TradingJournal.notes` | Renamed/reused as "Trade Notes" in the Trade detail card |
| `TradingJournal.tags` | Renamed as "Labels" (JSON string array → rendered as label chips) |
| Journal list endpoints | Kept — queried by the new Trade Journal sub-tab |

---

## 3. DotVerse Design Tokens Reference

### 3.1 CSS Variable Definitions (EXACT — Copy These)

```css
:root {
  /* ── Backgrounds ── */
  --bg:     #07080c;
  --s1:     rgba(255,248,230,.03);
  --s2:     rgba(255,248,230,.05);
  --s3:     rgba(255,248,230,.08);

  /* ── Borders ── */
  --bd:     rgba(201,168,76,.12);
  --bd2:    rgba(201,168,76,.22);

  /* ── Gold — DotVerse brand ── */
  --gold:        #c9a84c;
  --gold2:       rgba(201,168,76,.08);
  --gold-glow:   rgba(201,168,76,.28);
  --gold-bord:   rgba(201,168,76,.32);

  /* ── Text hierarchy ── */
  --t1:     #ede8d8;
  --t2:     rgba(237,232,216,.62);
  --t3:     rgba(237,232,216,.30);
  --mut:    rgba(237,232,216,.38);

  /* ── Signal colors ── */
  --grn:    #5de8a0;
  --red:    #e8706e;
  --grn2:   rgba(93,232,160,.08);
  --red2:   rgba(232,112,110,.08);
  --hold:   rgba(237,232,216,.55);

  /* ── Fonts ── */
  --mono:   'IBM Plex Mono', monospace;
  --ui:     'Space Grotesk', sans-serif;
  --syne:   'Syne', sans-serif;
}
```

### 3.2 Glass Card Template

```css
.agent-card {
  background: rgba(9,8,13,.66);
  backdrop-filter: blur(18px) saturate(160%) brightness(1.05);
  border: 1px solid rgba(237,232,216,.08);
  border-radius: 8px;
  padding: 20px;
}
```

### 3.3 Gold Shimmer Accent

```css
.agent-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent,
    rgba(237,232,216,.24),
    transparent
  );
}
```

### 3.4 Sub-Tab Navigation (sett-snav Pattern)

The `/static/index-v2-prototype.html` Settings panel uses this established pattern:

```html
<div class="sett-body">
  <div class="sett-snav">
    <div class="sett-snav-item on" onclick="...">Tab Name</div>
    ...
  </div>
  <div class="sett-panel">
    <!-- Active sub-tab content -->
  </div>
</div>
```

```css
.sett-snav {
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid var(--bd);
  padding: 10px 8px;
}
.sett-snav-item {
  padding: 9px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 400;
  color: var(--t2);
  cursor: pointer;
  transition: all .12s;
  margin-bottom: 2px;
}
.sett-snav-item:hover {
  background: var(--s2);
  color: var(--t1);
}
.sett-snav-item.on {
  background: var(--sel-bg);       /* rgba(255,255,255,.06) */
  color: var(--sel-txt);            /* #c9a84c */
  border: 1px solid var(--sel-bd);  /* rgba(201,168,76,.45) */
  font-weight: 500;
}
```

### 3.5 Selection Colors (from v2 prototype)

```css
--sel-bg:   rgba(255,255,255,.06);
--sel-bd:   rgba(201,168,76,.45);
--sel-glow: rgba(201,168,76,.22);
--sel-txt:  #c9a84c;
```

---

## 4. Agent Tab — Complete UI Design

### 4.1 Sidebar Entry

Add a new `nav-item` in the "Account" section of the sidebar:

```html
<div class="nav-item" data-nav="agent" onclick="setNav('agent');showAgent();">
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <!-- Dashboard/analytics icon — see SVG Inventory -->
    <rect x="3" y="3" width="18" height="18" rx="2"/>
    <line x1="3" y1="9" x2="21" y2="9"/>
    <line x1="9" y1="21" x2="9" y2="9"/>
  </svg>
  <span>Agent</span>
</div>
```

### 4.2 Layout Structure

The Agent tab follows the **same sett-snav pattern** as Settings — a left sub-navigation sidebar with a right content panel:

```
┌────────────────────────────────────────────────────────┐
│  Agent Heading: "Trading Agent" / "Account Management"  │
├──────────────┬─────────────────────────────────────────┤
│ SUB-NAV      │  CONTENT PANEL                          │
│ (200px)      │                                         │
│              │  ┌─────────────────────────────────┐    │
│ ● Dashboard  │  │ Glass Card: Account Summary      │    │
│ ● Positions  │  │ (balance, equity, P&L, risk)     │    │
│ ● Trades     │  └─────────────────────────────────┘    │
│ ● Analytics  │                                         │
│ ● Journal    │  ┌─────────────────────────────────┐    │
│ ● Accounts   │  │ Glass Card: Quick Stats Grid     │    │
│              │  │ (win rate, profit factor, etc.)  │    │
│              │  └─────────────────────────────────┘    │
│              │                                         │
│              │  ┌─────────────────────────────────┐    │
│              │  │ Glass Card: Equity Curve Chart   │    │
│              │  └─────────────────────────────────┘    │
└──────────────┴─────────────────────────────────────────┘
```

### 4.3 Page Header

```html
<div class="sett-hd">
  <div class="sett-hd-ico">
    <!-- gold-tinted icon background -->
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
         stroke="var(--gold)" stroke-width="2" stroke-linecap="round"
         stroke-linejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2"/>
      <line x1="3" y1="9" x2="21" y2="9"/>
      <line x1="9" y1="21" x2="9" y2="9"/>
    </svg>
  </div>
  <div>
    <div class="sett-hd-title">Trading Agent</div>
    <div class="sett-hd-sub">Multi-account trade management & analytics</div>
  </div>
</div>
```

---

## 5. Sub-Tab Navigation Structure

### 5.1 Sub-Tab Definitions

```
┌──────────────┬──────────────────────────────────────────────┐
│ Sub-Tab      │ Content                                      │
├──────────────┼──────────────────────────────────────────────┤
│ Dashboard    │ Account summary cards, equity curve, P&L,    │
│              │ open positions snapshot, risk gauge           │
├──────────────┼──────────────────────────────────────────────┤
│ Positions    │ Full open positions table with live data,    │
│              │ close/modify controls, per-position P&L       │
├──────────────┼──────────────────────────────────────────────┤
│ Trades       │ Closed trade history table with filters,     │
│              │ date range, CSV export button                 │
├──────────────┼──────────────────────────────────────────────┤
│ Analytics    │ KPI grid (win rate, profit factor, Sharpe,   │
│              │ drawdown), monthly heatmap, P&L distribution  │
├──────────────┼──────────────────────────────────────────────┤
│ Journal      │ Trade notes, labels, linked trade detail,    │
│              │ no emoji — SVG status indicators only         │
├──────────────┼──────────────────────────────────────────────┤
│ Accounts     │ Account list, add/remove, connection status,  │
│              │ archive toggle, per-account stats             │
└──────────────┴──────────────────────────────────────────────┘
```

### 5.2 Sub-Nav HTML Template

```html
<div class="sett-body">
  <div class="sett-snav" id="agentSubNav">
    <div class="sett-snav-item on" onclick="agentSwitchTab('dashboard',this)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" style="margin-right:7px;vertical-align:-2px;">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
      Dashboard
    </div>
    <div class="sett-snav-item" onclick="agentSwitchTab('positions',this)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" style="margin-right:7px;vertical-align:-2px;">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
      Positions
    </div>
    <div class="sett-snav-item" onclick="agentSwitchTab('trades',this)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" style="margin-right:7px;vertical-align:-2px;">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
      Trades
    </div>
    <div class="sett-snav-item" onclick="agentSwitchTab('analytics',this)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" style="margin-right:7px;vertical-align:-2px;">
        <line x1="18" y1="20" x2="18" y2="10"/>
        <line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="14"/>
      </svg>
      Analytics
    </div>
    <div class="sett-snav-item" onclick="agentSwitchTab('journal',this)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" style="margin-right:7px;vertical-align:-2px;">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      </svg>
      Journal
    </div>
    <div class="sett-snav-item" onclick="agentSwitchTab('accounts',this)">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" style="margin-right:7px;vertical-align:-2px;">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
      Accounts
    </div>
  </div>
  <div class="sett-panel" id="agentPanel">
    <!-- Sub-tab content rendered here -->
  </div>
</div>
```

---

## 6. Component-by-Component Specification

### 6.1 Dashboard Sub-Tab

#### 6.1.1 Account Selector

```html
<div class="agent-card" style="margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <label style="font-family:var(--mono);font-size:10px;color:var(--t3);
                  letter-spacing:.8px;text-transform:uppercase;">
      Active Account
    </label>
    <select id="agentAcctSelect" onchange="agentSwitchAccount()"
      style="flex:1;max-width:280px;
             background:var(--s2);
             border:1px solid var(--bd);
             border-radius:6px;
             color:var(--t1);
             font-family:var(--mono);
             font-size:12px;
             padding:8px 12px;
             outline:none;">
      <option>Loading accounts…</option>
    </select>
    <span id="agentConnDot" style="width:6px;height:6px;border-radius:50%;
      background:var(--t3);" title="Connection status"></span>
    <span id="agentConnLabel" style="font-family:var(--mono);font-size:9px;
      color:var(--t3);text-transform:uppercase;letter-spacing:.5px;">
      —</span>
  </div>
</div>
```

#### 6.1.2 Stats Grid (2×3 glass cards)

Each stat card:
- Header: mono font, uppercase, color `var(--t3)`
- Value: Syne heading, large, color `var(--t1)` or `var(--grn)` / `var(--red)` for P&L
- Sub-value: mono font, small, color `var(--t2)`

```html
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px;">
  <div class="agent-card">
    <div style="font-family:var(--mono);font-size:9px;color:var(--t3);
                letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">
      Balance
    </div>
    <div style="font-family:var(--syne);font-size:26px;font-weight:400;
                color:var(--t1);letter-spacing:-.02em;">
      $12,450.00
    </div>
    <div style="font-family:var(--mono);font-size:10px;color:var(--t2);margin-top:4px;">
      USD · Demo Account
    </div>
  </div>
  <!-- Equity, Today's P&L, Open P&L, Margin Used, Free Margin -->
</div>
```

#### 6.1.3 Equity Curve Chart

Full-width glass card with TradingView Lightweight Charts area chart:
- Gold gradient fill (rgba(201,168,76,.08) to transparent)
- Gold line stroke (#c9a84c)
- Date-based x-axis, text color `--t3`
- Gridlines: `rgba(237,232,216,.04)`

#### 6.1.4 Risk Gauge + Quick Actions

Split card: left side shows drawdown gauge (SVG arc), right side has action buttons.

```html
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
  <!-- Risk gauge card -->
  <div class="agent-card">
    <div style="font-family:var(--mono);font-size:9px;color:var(--t3);
                letter-spacing:1px;text-transform:uppercase;">
      Risk Exposure
    </div>
    <!-- SVG gauge arc: colored segments green→gold→red -->
  </div>
  <!-- Quick actions card -->
  <div class="agent-card">
    <button class="agent-btn">Download CSV</button>
    <button class="agent-btn">Recompute Metrics</button>
  </div>
</div>
```

### 6.2 Positions Sub-Tab

Full-width table in a glass card:

```
┌───────────────────────────────────────────────────────┐
│ Symbol │ Side │ Size │ Entry │ Current │ P&L │ SL │ TP │ Actions │
│ EURUSD │ BUY  │ 0.10 │1.0850 │ 1.0872  │+$22 │ —  │ —  │ [Close] │
│ BTCUSD │ SELL │ 0.05 │68420  │ 68100   │+$16 │ —  │ —  │ [Close] │
└───────────────────────────────────────────────────────┘
```

- Table header: mono font, 10px, color `var(--t3)`, uppercase, letter-spacing
- Table rows: 12px mono, color `var(--t1)`
- BUY side: color `var(--grn)`
- SELL side: color `var(--red)`
- Positive P&L: color `var(--grn)`, negative: `var(--red)`
- Hover row: background `var(--s1)`
- Zebra striping: alternating `var(--s1)` / transparent
- Empty state: "No open positions" in `var(--t3)`, centered

### 6.3 Trades Sub-Tab

- Date range filter bar (inputs + "Apply" gold button)
- Account selector (if multiple accounts)
- Sortable table (same styling as Positions)
- **"Download CSV"** button — opens `GET /api/trading-agent/trades/export` in new tab
- Row click expands a trade detail card (slide-down, glass border)

### 6.4 Analytics Sub-Tab

- KPI grid (4 cards): Win Rate, Profit Factor, Sharpe Ratio, Max Drawdown
- Each card: mono label, Syne number, SVG mini-sparkline or trend arrow
- Equity curve chart (full-width, same as Dashboard)
- Monthly returns heatmap (calendar grid view)
- Uses colors: `--grn` for green months, `--red` for red months, `var(--s2)` for idle

### 6.5 Journal Sub-Tab

This is the **replacement for the old emoji/star journal**. Clean, data-focused.

#### 6.5.1 Journal Entry Form Card

```html
<div class="agent-card" style="margin-bottom:14px;">
  <div style="font-family:var(--syne);font-size:16px;color:var(--t1);
              letter-spacing:-.02em;margin-bottom:14px;">
    New Trade Note
  </div>

  <!-- Linked trade selector -->
  <select id="jrnlTradeSelect"
    style="width:100%;margin-bottom:10px;background:var(--s2);border:1px solid
           var(--bd);border-radius:6px;color:var(--t1);font-family:var(--mono);
           font-size:12px;padding:8px 12px;outline:none;">
    <option value="">— Select linked trade (optional) —</option>
  </select>

  <!-- Notes textarea -->
  <textarea id="jrnlNotes" placeholder="Trade rationale, observations, lessons…"
    style="width:100%;background:var(--s2);border:1px solid var(--bd);
           border-radius:6px;color:var(--t1);font-family:var(--mono);
           font-size:11px;padding:10px;resize:vertical;min-height:60px;
           outline:none;margin-bottom:10px;"></textarea>

  <!-- Labels (chips) -->
  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
    <span style="font-family:var(--mono);font-size:9px;color:var(--t3);
                 letter-spacing:.8px;text-transform:uppercase;">
      Labels
    </span>
    <button class="agent-chip" onclick="toggleLabel('scalping')">Scalping</button>
    <button class="agent-chip" onclick="toggleLabel('swing')">Swing</button>
    <button class="agent-chip" onclick="toggleLabel('breakout')">Breakout</button>
    <button class="agent-chip" onclick="toggleLabel('reversal')">Reversal</button>
    <button class="agent-chip" onclick="toggleLabel('ranged')">Ranged</button>
    <button class="agent-chip on" onclick="toggleLabel('news')">News</button>
    <!-- "+" add custom label -->
    <button class="agent-chip" style="border-style:dashed;" onclick="addCustomLabel()">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
      </svg>
    </button>
  </div>

  <!-- Outcome selector — SVG-based not emoji -->
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="font-family:var(--mono);font-size:9px;color:var(--t3);
                 letter-spacing:.8px;text-transform:uppercase;">
      Outcome
    </span>
    <button class="agent-outcome-btn" data-outcome="win" onclick="setOutcome('win',this)">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="3">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      Win
    </button>
    <button class="agent-outcome-btn" data-outcome="loss" onclick="setOutcome('loss',this)">
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="3">
        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
      Loss
    </button>
  </div>

  <!-- Submit button -->
  <button class="sett-save-btn" onclick="submitJournal()">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2.5">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
    Save Note
  </button>
</div>
```

#### 6.5.2 Agent Chip CSS

```css
.agent-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 14px;
  border: 1px solid var(--bd);
  background: var(--s1);
  color: var(--t2);
  font-family: var(--mono);
  font-size: 10px;
  cursor: pointer;
  transition: all .12s;
}
.agent-chip:hover {
  border-color: var(--bd2);
  background: var(--s2);
  color: var(--t1);
}
.agent-chip.on {
  background: rgba(201,168,76,.10);
  border-color: rgba(201,168,76,.30);
  color: var(--gold);
}
```

#### 6.5.3 Outcome Button CSS

```css
.agent-outcome-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: 6px;
  border: 1px solid var(--bd);
  background: var(--s1);
  color: var(--t2);
  font-family: var(--mono);
  font-size: 11px;
  cursor: pointer;
  transition: all .12s;
}
.agent-outcome-btn:hover {
  background: var(--s2);
}
.agent-outcome-btn[data-outcome="win"].selected {
  background: var(--grn2);
  border-color: rgba(93,232,160,.25);
  color: var(--grn);
}
.agent-outcome-btn[data-outcome="loss"].selected {
  background: var(--red2);
  border-color: rgba(232,112,110,.25);
  color: var(--red);
}
```

#### 6.5.4 Journal Entry List

Same table pattern as Trades sub-tab:

| Date | Trade | Notes (truncated) | Labels | Outcome |
|---|---|---|---|---|
| Row hover expands to show full notes |

- **No emoji anywhere**
- Outcome column uses SVG checkmark (`var(--grn)`) or X (`var(--red)`)
- Labels render as `.agent-chip` components
- Empty state: "No trade notes yet" in `var(--t3)`

### 6.6 Accounts Sub-Tab

- Account cards in a 2-column grid (glass cards)
- Each card shows: account name, broker/server, connection status dot, currency, balance
- "Add Account" card with dashed border and `+` SVG
- Archive toggle (checkbox + "Show Archived")
- Archived accounts: reduced opacity, "Archived" badge

---

## 7. SVG Icon Inventory

ALL icons must use inline SVG. Zero emoji. Zero icon fonts.

| Icon | Usage | SVG Source |
|---|---|---|
| Grid (dashboard) | Dashboard sub-nav | 2×2 rect grid (feather: grid) |
| Activity (chart) | Positions sub-nav | polyline heartbeat (feather: activity) |
| File-text | Trades sub-nav | document + lines (feather: file-text) |
| Bar-chart | Analytics sub-nav | 3 vertical bars (feather: bar-chart-2) |
| Book | Journal sub-nav | open book (feather: book-open) |
| Users | Accounts sub-nav | 2 people (feather: users) |
| Check | Win indicator, save button | polyline checkmark |
| X | Loss indicator, close button | 2 diagonal lines |
| Plus | Add account, add label | cross |
| Download | CSV export | arrow down + line |
| Circle-dot | Connection status | filled circle with stroke |
| Alert-triangle | Risk warning | triangle + exclamation |
| Shield | Risk gauge header | shield outline |
| Trending-up/down | P&L direction | arrow + line |
| Chevron-right | Expand rows | small right angle |
| Refresh | Recompute metrics | circular arrow |

---

## 8. Implementation Order

### Phase 1: Kill the Old (1–2 hours)

1. **Remove emoji/star journal section** from `index-v2-prototype.html`
   - Lines ~11,818–11,848 (HTML block)
   - Lines ~12,086–12,160 (JS functions: `selectEmotion`, `setStarRating`, `toggleJournal`, `submitJournal`, `setStarRating`)
   - Any `.jrnl-*` CSS rules
   - Global vars: `_journalEmotion`, `_journalRating`

2. **Remove emoji section title** references (📓, etc.)

### Phase 2: Add Agent Sidebar Entry (30 min)

3. Add `nav-item[data-nav="agent"]` to sidebar in `index-v2-prototype.html`
4. Add `showAgent()` function

### Phase 3: Skeleton Layout (1 hour)

5. Create the Agent page HTML structure with `sett-hd`, `sett-body`, `sett-snav`, `sett-panel`
6. Wire up `agentSwitchTab()` function
7. Create empty panel render functions for all 6 sub-tabs

### Phase 4: Data Wiring (4–6 hours)

8. **Dashboard:** Wire to `GET /api/trading-agent/portfolio`, `GET /api/accounts/<id>/summary`
9. **Positions:** Wire to `GET /api/accounts/<id>/summary` (positions array)
10. **Trades:** Wire to `GET /api/trading-agent/trades` + `GET /api/trading-agent/trades/export`
11. **Analytics:** Wire to `GET /api/trading-agent/accounts/<id>/daily-metrics`
12. **Journal:** Wire to `GET/POST /api/accounts/<id>/journal` (keep backend, change frontend render)
13. **Accounts:** Wire to `GET/POST /api/accounts`

### Phase 5: Charts & Polish (3–4 hours)

14. Integrate Lightweight Charts for equity curve
15. Build monthly heatmap for Analytics sub-tab
16. Risk gauge SVG arc component
17. Empty state components for all sub-tabs
18. Responsive adjustments

---

## 9. File List: What Gets Touched

### 9.1 Frontend — Modify

| File | Changes |
|---|---|
| `static/index-v2-prototype.html` | **Primary target.** Remove old journal code (Phase 1). Add Agent tab sidebar entry. Add full Agent UI: CSS classes, HTML structure, JavaScript functions for all 6 sub-tabs. Add `showAgent()`, `agentSwitchTab()`, `agentSwitchAccount()`, `agentRenderDashboard()`, etc. |
| `static/index.html` | **No changes** — this is the deprecated Momentum theme file. |

### 9.2 Backend — Add/Modify

| File | Changes |
|---|---|
| `app.py` | Add new endpoints from spec: `/api/trading-agent/portfolio`, `/api/trading-agent/trades`, `/api/trading-agent/trades/export`, `/api/trading-agent/accounts/<id>/archive`, `/api/trading-agent/accounts/<id>/daily-metrics`, `/api/trading-agent/accounts/<id>/recompute-daily`. Add `DailyMetrics` model. Add `TradingAccount` column migrations (`deleted_at`, `nickname`, `labels`). |

### 9.3 Database Migrations

| Migration | SQL |
|---|---|
| `daily_metrics` table | `CREATE TABLE` |
| `trading_accounts.deleted_at` | `ALTER TABLE ADD COLUMN` |
| `trading_accounts.nickname` | `ALTER TABLE ADD COLUMN` |
| `trading_accounts.labels` | `ALTER TABLE ADD COLUMN` |

### 9.4 Design Docs — Create

| File | Purpose |
|---|---|
| `AGENT_TAB_REDESIGN.md` | This document |

---

## Appendix A: Color Usage Reference

```
Element                          Background          Border            Text
────────────────────────────────────────────────────────────────────────────
Glass card                       rgba(9,8,13,.66)   rgba(237,232,216,.08)  —
  + blur/saturate/brightness backdrop-filter
Sub-nav sidebar                  transparent         border-right: var(--bd) —
Sub-nav item (idle)              transparent         none              var(--t2)
Sub-nav item (hover)             var(--s2)            none              var(--t1)
Sub-nav item (active)            var(--sel-bg)        var(--sel-bd)     var(--sel-txt)
Stat card heading                —                    —                 var(--t3)
Stat card value                  —                    —                 var(--t1)
Stat card P&L (positive)         —                    —                 var(--grn)
Stat card P&L (negative)         —                    —                 var(--red)
Table header                     transparent         border-bottom: var(--bd) var(--t3)
Table row (odd)                  var(--s1)            —                 var(--t1)
Table row (hover)                var(--s2)            —                 var(--t1)
Label chip (idle)                var(--s1)            var(--bd)         var(--t2)
Label chip (active)              rgba(201,168,76,.10) rgba(201,168,76,.30) var(--gold)
Outcome btn (idle)               var(--s1)            var(--bd)         var(--t2)
Outcome btn (win selected)       var(--grn2)          rgba(93,232,160,.25) var(--grn)
Outcome btn (loss selected)      var(--red2)          rgba(232,112,110,.25) var(--red)
Action button                    rgba(237,232,216,.07) rgba(237,232,216,.44) rgba(237,232,216,.88)
Chart line (equity)              —                    —                 var(--gold) #c9a84c
Chart gridlines                  —                    rgba(237,232,216,.04) —
Chart area fill                  rgba(201,168,76,.08)→transparent gradient —
Empty state text                 —                    —                 var(--t3)
Connection dot (connected)       var(--grn)           —                 —
Connection dot (disconnected)    var(--t3)            —                 —
```

---

## Appendix B: Font Usage Reference

```
Context                          Font Family              Size    Weight   Color
────────────────────────────────────────────────────────────────────────────────
Page heading (.sett-hd-title)    Syne                     18px    400      var(--t1)
Page subtitle (.sett-hd-sub)     IBM Plex Mono            11.5px  400      var(--t3)
Sub-nav items                    Space Grotesk            13px    400      var(--t2)
Sub-nav items (active)           Space Grotesk            13px    500      var(--sel-txt)
Stat card labels                 IBM Plex Mono            9px     400      var(--t3)
Stat card values                 Syne                     26px    400      var(--t1)
Stat card sub-values             IBM Plex Mono            10px    400      var(--t2)
Table headers                    IBM Plex Mono            10px    400      var(--t3)
Table cells                      IBM Plex Mono            12px    400      var(--t1)
Table BUY/SELL                   IBM Plex Mono            12px    600      var(--grn)/var(--red)
Label chips                      IBM Plex Mono            10px    400      var(--t2)
Form inputs                      IBM Plex Mono            12px    400      var(--t1)
Buttons                          Space Grotesk            13.5px  400      var(--t1)
Section titles                   Syne                     16px    400      var(--t1)
Empty states                     Space Grotesk            12px    400      var(--t3)
```

---

**End of Design Document**
