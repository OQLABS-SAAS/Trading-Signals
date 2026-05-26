# DOTVERSE — COMPREHENSIVE AUDIT & SHIP PLAN

**Date:** 2026-05-26  
**Scope:** Every tab, every feature, every button — evaluated from beginner trader, UI/UX, and user journey lenses  
**Sources:** Live endpoint testing (curl), code audit (search_files across 22,957-line frontend + 16,690-line backend), 3 parallel audit agents  

---

## THE BIG PICTURE

DotVerse claims to be a "trading intelligence partner and guide." Right now it's a complicated system that shows data but doesn't guide. The 6-step pipeline (Market→Signal→Understand→Verdict→Size→Act) exists in the breadcrumb but doesn't function as an actual guided flow.

**Overall Guidance Score: 1.2 / 3**  
(Best: Automations/Risk at 2.5. Worst: Alerts/News at 0.)

---

## PART 1: TAB-BY-TAB AUDIT

### QUICK ANALYSE BAR (persistent on all tabs)

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — core entry point for analysis. Should be the first thing a new user sees. |
| **Guidance** | ZERO. No explanation of what it does. No hint that clicking "Analyse" teleports you to Understand tab. |
| **UI/UX** | 0 data-guide tooltips. Looks like a toolbar but acts like a navigation. |
| **What needs refinement** | Add guidance text. Add tooltips to each TF button. Show where the user will land. Fix `_dvTF` not initialized on page load (sends `undefined` timeframe on first click). Show scan results inline instead of teleporting. |

---

### MARKET TAB (Step 1 of 6 — supposed to be the starting dashboard)

| Lens | Assessment |
|------|-----------|
| **Relevance** | LOW in current form. Markets change every second; this tab shows mostly hardcoded mock data that's stale on first paint. A beginner sees stale prices and thinks the app is broken. |
| **Jargon count** | 12 terms a beginner wouldn't understand: Scalp, tight stops, breakouts, catalyst, intraday noise, momentum, NFP, ISM PMI, EIA, directional moves, range-bound. |
| **Guidance** | POOR. "Step 1 of 6" footer is at the bottom after 1000px of scrolling. The 4 mode cards (Scalp/Day Trade/Swing/Position) are supposed to filter the Signal tab but this isn't explained anywhere. |
| **What's irrelevant** | IPO/New Listings section (most users don't trade IPOs). Static ticker strip with 8 hardcoded symbols. Heatmap with 14 hardcoded S&P stocks (not configurable). |
| **What needs refinement** | Complete redesign. Should be a simple onboarding screen: "What do you want to trade?" with clear asset class selection + "Analyse your first signal" CTA. Move detailed market data to a secondary view. Fix the broken conditions chip tooltip (keys `trending`/`mixed`/`risk-off` don't exist in `_dvGuide`). Add `data-tier` attributes for mode toggle. |

---

### SIGNAL FEED TAB (Step 2 of 6)

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — this is where signals actually appear. |
| **Guidance** | CRITICAL GAP: NO flow-footer, NO "Step 2 of 6" indicator, NO breadcrumb. User has no idea this is part of a pipeline. "Analyse →" buttons on cards exist but the overall tab lacks journey context. |
| **Jargon** | Moderate: "Confidence", "R:R", "CVD", "SMC Structures", "Order Block", "Kelly criterion". |
| **What needs refinement** | Add flow-footer with "Step 2 of 6 · SIGNAL" + "View in Understand →" button. Add breadcrumb. Add inline explanations for R:R and confidence on signal cards. Remove diagnostic text ("rate-limited on Railway", "TWELVEDATA_API_KEY"). |

---

### UNDERSTAND TAB (Step 3 of 6)

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — core analysis view. Has the best pipeline integration. |
| **Guidance** | GOOD. Has "What To Do Next" panel with 5 numbered journey steps. Has flow-footer: "Step 3 of 6 · UNDERSTAND" with ← SIGNAL and → SIZE. 20+ data-guide tooltips. |
| **Jargon** | HIGHEST in the app: SMC, FVG, Liquidity Grab, Displacement, CHOCH, Order Flow, CVD, RSI Gauge, Monte Carlo, Cost Review — ~15+ terms a beginner wouldn't understand. Left sidebar is overwhelming for beginners. |
| **What needs refinement** | Add `data-tier="beginner"` to simplify the left sidebar when in beginner mode (hide SMC details, show simplified signal reasoning). Add inline jargon explainers. The journey step panel is gold — keep and enhance. |

---

### VERDICT TAB (Step 4 of 6)

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — AI analysis of the signal. Content is useful. |
| **Guidance** | GOOD before analysis (has flow-footer, empty state instructions). **CRITICAL REGRESSION after analysis**: flow-footer disappears, replaced by standalone "Open in Size" button with no step indicator. |
| **What needs refinement** | Fix the post-analysis flow-footer regression. Move the flow-footer outside the DOM region that gets replaced by `_vRenderLive()`. Change the "Open in Size" CTA from green back to gold. |

---

### SIZE TAB (Step 5 of 6)

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — position sizing is essential. |
| **Guidance** | GOOD. Has flow-footer with "Step 5 of 6 · SIZE" + "← Understand" and "Execute Trade → ACT". Signal summary pre-filled. Live price bar. Verdict plan loaded banner. |
| **Jargon** | Moderate: "Risk %", "Lot size", "Slippage", "VaR" — but tooltips exist for input fields. |
| **What needs refinement** | Rename "SL"/"TP"/"R:R" column labels to plain English. Add data-guide to "Clear" button. Consider adding position size explanation for beginners ("Why this size? Your account is $X, you're risking 2% = $Y, which gives you Z lots"). |

---

### ACT TAB (Step 6 of 6)

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — execution. Best-designed tab for beginners. |
| **Guidance** | BEST in pipeline. Has "What Will Happen" plain English explanation. "Practice without real money" button. Pre-filled lot size from Size tab. Flow-footer with "Step 6 of 6 · ACT". |
| **What needs refinement** | No circular flow — after "Log to Portfolio →" there's no "Analyse another signal" button. Add a "Back to Signal Feed" or "Analyse Next Signal" CTA. Advanced Options order types need "when to use this" tooltips explaining scenarios for each. Explain "MT5" in tooltip. |

---

### PORTFOLIO TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH for ongoing users, LOW for first-time (empty until trades logged). |
| **Guidance** | POOR for beginners. 13 data-guide tooltips but core metrics are jargon: VaR, Monte Carlo, Drawdown, Cost Analysis — none explained in the UI itself. No "what to do next" guidance. |
| **What needs refinement** | Add "Welcome back, here's your portfolio" banner when data exists. Add plain-English metric explanations. Show empty state that guides "Go to Signal tab to start trading." |

---

### AUTOMATIONS TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH for regular traders, LOW for first-time. |
| **Guidance** | **GOLD STANDARD.** Every toggle has `what`, `when_on`, `risk_if_off` in plain English. SAFE/CAUTION/ADVANCED tags. Expandable details. Best coaching in the entire app. |
| **What needs refinement** | Minor: Add exchange order types (market/limit/stop) to auto-scan settings. Wire calibration confidence into recommendation engine. Add quality score/win rate to notification payloads. Add SSE listener for live refresh. |

---

### RISK TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — risk management is critical. |
| **Guidance** | **GOLD STANDARD** for beginner journey. Has 5-step "HOW TO USE THIS PAGE" banner with numbered plain-English steps. Expandable guides for every panel. Explains VaR as "On a typical bad day, how much could I lose?" Historical crash examples. |
| **What needs refinement** | Only 4 data-guide tooltips — could use more (on "Run Safety Check" button, on the HOW TO USE banner itself). Otherwise, best beginner guidance in the app. |

---

### PERFORMANCE TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — tracks progress over time. |
| **Guidance** | DECENT. 16 data-guide tooltips. Good empty-state guidance ("0/30 results logged"). Explains expectancy well. |
| **Jargon** | Heavy: "Sharpe Ratio", "Profit Factor", "Expectancy", "R-multiples", "Isotonic regression", "ECE (Expected Calibration Error)" — none have inline definitions. |
| **What needs refinement** | Add plain-English definitions for Sharpe, PF, Drawdown on the cards themselves. Replace 2 remaining emoji HTML entities with SVGs. "Isotonic regression" should be renamed "Confidence Calibration" with tooltip. |

---

### ALERTS TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH — notifications are essential. |
| **Guidance** | **WORST TAB.** 0 data-guide tooltips. No explanation of what alerts do. No "why should I care." Conditions use jargon without context (TP1/2/3, Daily PnL limit, High-impact event). User says "looks horrible." |
| **What needs refinement** | Complete rewrite: Add step-by-step setup guide ("Step 1: Add to Watchlist → Step 2: Configure alerts → Step 3: Connect Telegram"). Add data-guide tooltips to every element. Improve visual hierarchy. Explain what each alert condition means with examples. |

---

### NEWS TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | MEDIUM — news is supplementary, not core. |
| **Guidance** | **2ND WORST.** 0 data-guide tooltips. Sentiment badges (Bull/Bear/Neutral) never explained. No "how to use news for trading" context. |
| **What needs refinement** | Add data-guide tooltips. Explain sentiment: "Bullish — positive for price. Bearish — negative for price. Neutral — no strong directional signal." Add "See a bearish article on BTC? → Analyse BTC in Understand tab" callout. |

---

### BACKTEST TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | HIGH for serious traders, LOW for beginners (can ignore initially). |
| **Guidance** | POOR for beginners. No explanation of what backtesting is. All 5 dashboard metrics (Win Rate, Profit Factor, Max Drawdown, Total Trades, Avg Trade R) displayed without definition. Strategy picker has emoji icons. |
| **What needs refinement** | Add beginner intro banner: "Backtesting checks if this strategy would have made money historically. It's NOT a guarantee of future results — but it helps you avoid obvious losing strategies." Replace 4 emoji icons with SVGs. Add plain-English explanations for each dashboard metric. Rename "PnlUsd/DdUsd/WL/PF" legacy stats to plain English. |

---

### SETTINGS TAB

| Lens | Assessment |
|------|-----------|
| **Relevance** | LOW for first visit, HIGH for ongoing use. |
| **Guidance** | **3RD WORST.** 0 data-guide tooltips across all sub-tabs. Chart Visuals theme picker is beautiful but unexplained. Risk Tolerance settings use "drawdown", "volatility" without definition. |
| **What needs refinement** | Add data-guide tooltips to every settings sub-tab section. Add plain-English explanations for each setting. The sidebar nav items themselves need tooltips. |

---

## PART 2: CROSS-CUTTING ISSUES

| # | Issue | Tabs Affected |
|---|-------|---------------|
| 1 | **Beginner/Advanced toggle does nothing** — only 4 elements in entire app have `data-tier` attributes | ALL |
| 2 | **No circular pipeline flow** — after Act, user must manually click nav to trade again | Signal→Act |
| 3 | **R:R never explained** — used across 8+ tabs without a single "Risk-to-Reward ratio" definition | ALL pipeline tabs |
| 4 | **Mobile responsiveness incomplete** — only 10 @media queries, content not resized for small screens | ALL |
| 5 | **Railway cold start 30-60s** — makes the app borderline unusable on first load | ALL |
| 6 | **CSS cascade wars** — 5 conflicting !important blocks for button styles | ALL with buttons |
| 7 | **Pine Script buttons too small** — 9px font, 3px padding, ~20px height | Backtest |
| 8 | **Non-brand colors used** — blue (#60a5fa) and purple (#a78bfa) in badges | Multiple |

---

## PART 3: WHAT'S WORKING WELL (keep)

| Feature | Why |
|---------|-----|
| Automations GUIDES system | `what`/`when_on`/`risk_if_off` pattern per toggle |
| Risk tab step-by-step banner | 5 numbered steps with plain-English guides |
| Understand tab "What To Do Next" | Journey step panel showing the full pipeline |
| Flow-footer pattern | Step X of 6 with forward/back navigation (when present) |
| Act tab "What Will Happen" | Plain English execution explanation |
| Quality ring tooltip | CSS tooltip with 5-component breakdown |
| Chart Visuals theme picker | Beautiful, showing real previews |

---

## PART 4: SHIP READINESS

**Current state:** NOT SHIP-READY. ~100+ issues across all levels.

**Minimum viable ship criteria:**
1. Fix 8 critical bugs (Quick Analyse, Market, SignalFeed flow-footer, Verdict regression, Alerts/News/Settings 0% tooltips, mode toggle)
2. Remove all emoji violations (Backtest)
3. Add flow-footer + breadcrumb to SignalFeed
4. Fix Verdict post-analysis flow-footer regression
5. Add `data-tier` attributes so mode toggle actually does something
6. Add beginner journey guidance to Alerts, News, Backtest

**Gold standard (after MVP):**
7. Replicate Automations GUIDES system across all tabs
8. Mobile responsive overhaul
9. Fix CSS cascade wars + Pine Script buttons
10. Railway cold-start mitigation

---

## PART 5: FIX PRIORITY

| Priority | What | Effort | Impact |
|----------|------|--------|--------|
| P0 | Railway cold start | Low (keep-alive ping or upgrade) | CRITICAL — app is unusable |
| P1 | SignalFeed flow-footer + breadcrumb | Low (copied from Understand) | Fixes pipeline starting point |
| P1 | Verdict post-analysis flow-footer | Low (move outside replaced DOM) | Fixes pipeline continuity |
| P1 | Alerts/News/Settings tooltips | Medium (copy Automations pattern) | Fixes worst UX offenders |
| P2 | Beginner/Advanced toggle wiring | Medium (add data-tier attributes) | Makes mode toggle actually work |
| P2 | Backtest emoji→SVG + beginner guidance | Medium | Fixes visual + guidance gap |
| P2 | Quick Analyse guidance + _dvTF init | Low | Fixes first-user experience |
| P3 | Market tab redesign | High | Improves starting dashboard |
| P3 | Pipeline circular flow | Low (add "back to feed" button) | Closes the loop |
| P3 | CSS cascade cleanup | Medium | Visual consistency |
| P4 | Mobile responsive | High | Reach |
| P4 | Automations wiring gaps | Medium | Power features |
