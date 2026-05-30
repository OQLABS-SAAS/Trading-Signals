# DotVerse — Consolidated Build Plan

**Updated:** 2026-05-26
**Order:** User priority stack merged with original build plan phases. Every item is placed where it belongs, not where the old plan guessed.

---

## PLAN CORRECTIONS — What The Original Plan Got Wrong

| Wrong Claim | Reality |
|---|---|
| Phase 1: "Ship J1/J2/MT5 cards" | These **already render** on UNDERSTAND tab. J1/J2 fetch live from `/api/signals/cost-analysis` + `/api/validate/montecarlo`. MT5 Positions + Account Summary cards exist with live data. |
| "Pattern WR — needs Phase 2.1" | Pattern WR **already exists** — backend `/api/signals/winrate-by-pattern` + frontend badge on signal cards. Committed, QA'd, verified. |
| "Phase 0: Performance Dashboard" | Performance page **exists** (`showPerformance()`) with signal history, stats, expectancy card. But missing PnL curve, Sharpe ratio, drawdown chart, monthly heatmap — so partially done. |

---

## PRIORITY 1 — Direct Exchange Execution (NEW)

### 1.1 Binance Spot Trading
**Status:** TODO | **Effort:** 5-7 days | **Depends on:** Nothing
Implement Binance spot order placement via REST API: market/limit orders, cancel, order status. Store API keys encrypted per-user (extend existing EncryptionKey model). Add `/api/exchange/binance/order` endpoints. Already have Binance data feed (`fetch_binance_ohlcv`, `_fetch_binance`) — trading is the missing half.

### 1.2 Coinbase Advanced Trade
**Status:** TODO | **Effort:** 5-7 days | **Depends on:** Nothing (parallel with 1.1)
Implement Coinbase Advanced Trade API: spot market/limit orders, cancel, fills. Encrypted API key storage. Add `/api/exchange/coinbase/order` endpoints. CoinMarketCap data fallback already integrated — trading layer is net-new.

### 1.3 Exchange Order UI (Act Tab)
**Status:** TODO | **Effort:** 3-4 days | **Depends on:** 1.1, 1.2
Frontend order ticket on ACT tab: exchange selector, market/limit toggle, quantity + price inputs, confirm dialog, order status feed. Replace or extend existing "Execute via MT5" flow. Reuse `sizeTab` position-sizing calculator for order quantity.

### 1.4 One-Click Signal-to-Order
**Status:** TODO | **Effort:** 2-3 days | **Depends on:** 1.3
"Trade This Signal" button on signal cards that pre-fills the order ticket with signal's entry/stop/tp. Works for both Binance and Coinbase. Reduces friction from signal → execution to 1 click.

---

## PRIORITY 2 — AI/ML Confidence Calibration

### 2.1 Outcome-Labeled Dataset Pipeline
**Status:** TODO | **Effort:** 2-3 days | **Depends on:** Nothing (uses existing SignalHistory)
Query `SignalHistory WHERE outcome IS NOT NULL AND actual_pnl_r IS NOT NULL`. Build per-user labeled dataset: (confidence_raw, indicators_vector, regime, spread_cost → WIN/LOSS). Store in new `CalibrationLabel` table keyed by (user_id, signal_id). Minimum 50 labels before calibration is meaningful.

### 2.2 Isotonic Regression Calibration
**Status:** TODO | **Effort:** 3-4 days | **Depends on:** 2.1
Fit isotonic regression on confidence_raw → actual win probability. Output calibrated confidence (0-100) that reflects true historical probability. Run weekly via APScheduler. Surface as `calibrated_confidence` field on analysis response. Replace raw confidence display when calibrated version is available.

### 2.3 Qwen Deep Reasoning on Signal Quality
**Status:** TODO | **Effort:** 2-3 days | **Depends on:** 2.2
Use Qwen 3.5 Plus (already configured today) to review signal quality. Pass indicators + regime + calibrated confidence → Qwen returns: signal_quality_score, key_risks, confidence_agreement. Adds an AI second-opinion layer. Cache result per (ticker, timeframe, signal_hash) for 1 hour.

### 2.4 Calibration Dashboard Card
**Status:** TODO | **Effort:** 1-2 days | **Depends on:** 2.2
Frontend card showing: reliability curve (confidence bin → actual WR), calibration error, sample size. Renders on PERFORMANCE tab. Shows "Not enough data — log more outcomes" until 50+ labeled trades.

---

## PRIORITY 3 — Better Market Data Sources ✅ DONE (2026-05-26)

### 3.1 Twelve Data Primary
**Status:** DONE | **Effort:** Completed 2026-05-26
Promoted Twelve Data to primary data source. `safe_download()` multi-source fallback implemented.

### 3.2 CoinMarketCap Crypto Fallback
**Status:** DONE | **Effort:** Completed 2026-05-26
CoinMarketCap integration added for crypto asset data fallback when Twelve Data / Yahoo fail.

### 3.3 FMP Key Configured
**Status:** DONE | **Effort:** Completed 2026-05-26
Financial Modeling Prep API key set on Railway. FMP already integrated as 5th data source fallback (line ~10089).

### 3.4 Quality Ring Tooltip Fix
**Status:** DONE | **Effort:** Completed 2026-05-26
Tooltip hover fixed: white-space, max-width, overflow:visible on confidence ring tooltips.

---

## PRIORITY 4 — Performance Dashboard (Phase 0, partially done)

### 4.1 PnL / Equity Curve Chart
**Status:** TODO | **Effort:** 2-3 days | **Depends on:** Outcome data exists in SignalHistory
Plot cumulative PnL over time from closed trades (outcome + actual_pnl_r). Lightweight Charts canvas — same library already used for price charts. Add to PERFORMANCE tab above the signal activity log.

### 4.2 Sharpe Ratio + Win Rate Stats Row
**Status:** TODO | **Effort:** 1-2 days | **Depends on:** 4.1
Compute from closed trades: Sharpe ratio (annualized, assume 0% risk-free), win rate %, profit factor (gross win / gross loss), avg R per trade. Display as stat row (4 cards) at top of PERFORMANCE tab. Backend: `/api/signals/performance-metrics`.

### 4.3 Drawdown Chart
**Status:** TODO | **Effort:** 1-2 days | **Depends on:** 4.1
Drawdown curve below equity curve: peak-to-trough % over time. Mark max drawdown. Same chart library, separate pane.

### 4.4 Monthly Returns Heatmap
**Status:** TODO | **Effort:** 1-2 days | **Depends on:** 4.2
Calendar-style heatmap: months as rows, weeks as columns, cells colored by net R for that week. Uses outcome data. Pure frontend rendering from the same `/api/signals/performance-metrics` response.

### 4.5 Performance Dashboard vs Agent Tab Boundary
**Status:** DONE | **Effort:** Documented 2026-05-30
These two tabs share overlapping metrics (PnL, Sharpe, win rate) but compute them from **different data sources** for different purposes. Clear boundaries prevent duplicate work and conflicting numbers.

| Concern | Performance Dashboard | Agent Tab |
|---------|----------------------|-----------|
| **Tab** | PERFORMANCE tab (`showPerformance()`) | AGENT tab |
| **Data source** | `SignalHistory` table | `AgentTrade` + `TradingAccount` + `AgentDailyMetrics` |
| **Unit of analysis** | Signal quality (per-signal) | Trade performance (per-account, per-trader) |
| **Audience** | Signal strategy developers | Account managers / traders |
| **Equity curve** | Cumulative R-multiples from signal outcomes (`actual_pnl_r`) — normalized | Cumulative dollar PnL from trade `realized_pnl` — absolute dollar |
| **Sharpe ratio** | From R-multiple returns (signal-level) | From dollar PnL returns (account-level) |
| **Win rate** | Signal outcome WIN/LOSS rate | Trade outcome WIN/LOSS rate |
| **Profit factor** | Gross win R / gross loss R | Gross win $ / gross loss $ |
| **Drawdown** | Peak-to-trough in R-multiple equity curve | Peak-to-trough in dollar equity curve |
| **Heatmap** | Monthly R-multiple returns matrix | Monthly dollar PnL matrix |
| **Unique metrics** | Signal confidence calibration, expectancy per pattern, regime breakdown | Account balances, margin usage, client P&L, connection status |
| **API endpoints** | `/api/signals/performance-metrics` (to be built) | `/api/trading-agent/dashboard`, `/api/trading-agent/analytics` (already built) |

**Rule:** Never compute the same metric from both sources on the same tab. If a metric appears on both tabs, clearly label the source (e.g., "Sharpe (Signal)" vs "Sharpe (Account)").

---

## PHASE 1 — Already Done (No Work Needed)

### 5.1 J1 Cost Review Card
**Status:** DONE | **Effort:** 0 (already shipped)
Backend `/api/signals/cost-analysis` returns fee drag, warning flag, trade count. Frontend renders on UNDERSTAND tab as Cost Review card. QA'd 2026-05-26.

### 5.2 J2 Monte Carlo Card
**Status:** DONE | **Effort:** 0 (already shipped)
Backend `/api/validate/montecarlo` returns P5/P95 drawdown, prob_20pct_drawdown. Frontend renders on UNDERSTAND tab. QA'd 2026-05-26.

### 5.3 MT5 Positions Card
**Status:** DONE | **Effort:** 0 (already shipped)
Renders live MT5 positions from `mt5_state`. Updates every 5s via polling.

### 5.4 MT5 Account Summary Card
**Status:** DONE | **Effort:** 0 (already shipped)
Live account balance, equity, margin, free margin from MT5 EA push.

### 5.5 Pattern WR Badge
**Status:** DONE | **Effort:** 0 (already shipped)
Backend + frontend. Shows "WR: 65% (17)" on signal cards. Color thresholding. QA'd and verified.

---

## PHASE 2 — Real-Time & Backtesting (in progress)

### 6.1 Real-Time WebSocket Data Feed
**Status:** TODO | **Effort:** 4-5 days | **Depends on:** Nothing
Replace current polling (setInterval 60s) with WebSocket stream for live price updates. Use Binance WebSocket for crypto, Twelve Data WebSocket for stocks/forex. Push updates to frontend via Socket.IO or Server-Sent Events. Reduces latency from 60s to <1s.

### 6.2 Backtesting UI — Strategy Selector + Results View
**Status:** IN PROGRESS | **Effort:** 3-4 days | **Depends on:** Backend exists (`/backtest/enqueue` + RQ)
Backend `_run_backtest_job` exists with RQ queue. Frontend needs: strategy picker (Full Report, Order Block, S/D, Retracement, Pullback, Breakout, Liquidity lenses), results dashboard (win rate, profit factor, max drawdown, trade list). Partially wired — requires `/backtest/result/{job_id}` polling.

### 6.3 Push Alerts — Web + Mobile
**Status:** IN PROGRESS | **Effort:** 2-3 days | **Depends on:** 6.1 (better with real-time)
Backend `_push_notification` already sends Telegram alerts. Add: browser push notifications (Service Worker + Web Push API), signal threshold alerts (e.g., "BTC breaks $70k"), daily digest email. PWA manifest exists (quantverse-pwa/).

---

## PHASE 3 — Monetization

### 7.1 Stripe Checkout Integration
**Status:** TODO | **Effort:** 3-4 days | **Depends on:** Nothing
Create Stripe Products/Prices for Pro ($39/mo) and Elite ($99/mo). Implement `/api/stripe/create-checkout-session` and `/api/stripe/portal`. Webhook handler for subscription status sync. Frontend: upgrade buttons on pricing page and tier-gated features. `stripe_customer_id` column already exists on User model.

### 7.2 Free Tier Caps — Beyond 5/Day
**Status:** IN PROGRESS | **Effort:** 2-3 days | **Depends on:** Nothing (5/day cap already in Redis)
Current cap: 5 signals/day (line 9425). Need to add: 3 backtests/day cap, 2 active watches cap, 3 positions cap, 1 asset class cap, 1h timeframe only. All gated by User.tier check + Redis counters. Upgrade prompts at each cap hit.

### 7.3 Tier-Gated Feature Flags
**Status:** TODO | **Effort:** 1-2 days | **Depends on:** 7.2
Centralized feature flag system: `/api/user/features` returns tier-gated flags. Frontend reads flags on load to show/hide: multi-timeframe selectors, indicator layers, risk manager modules, Pine export, EA access. Removes hardcoded tier checks scattered across code.

---

## PHASE 4 — Mobile Responsive (User: last priority)

### 8.1 Mobile Layout Pass
**Status:** TODO | **Effort:** 4-5 days | **Depends on:** All features stable
Single-column mobile layout. Collapse sidebar to bottom tab bar. Stack UNDERSTAND cards vertically. Responsive charts (Lightweight Charts handles this). Touch-friendly tap targets (min 44px). Test on iOS Safari + Android Chrome. CSS breakpoints already exist in stylesheet — need systematic pass.

### 8.2 PWA Offline Mode
**Status:** TODO | **Effort:** 2-3 days | **Depends on:** 8.1
Service Worker caching for signal history, settings, saved analyses. Offline indicator banner. PWA manifest exists at `quantverse-pwa/` — needs wiring to production `index-v2-prototype.html`.

---

## PHASE 5 — Revenue Loop (Original Phase 4)

### 9.1 ML Parameter Optimization (Elite Tier)
**Status:** TODO | **Effort:** 4-5 days | **Depends on:** 2.1 (needs labeled data), 7.1 (Elite tier)
Weekly grid search per asset class: optimize RSI period, EMA periods, ATR mult, BB period. Store in OptimisationResult table. Elite users get optimised params in signal engine. RQ background job.

### 9.2 Alternative Data — On-Chain + Sentiment
**Status:** TODO | **Effort:** 5-7 days | **Depends on:** 7.1 (Elite tier)
On-chain metrics for crypto (Glassnode/CoinMetrics API), options flow data, social sentiment multiplexer (Twitter/LunarCrush). Elite-tier feature. Data surfaces as additional cards on UNDERSTAND tab.

### 9.3 Public API
**Status:** TODO | **Effort:** 3-4 days | **Depends on:** 7.3 (tier gating)
Read-only REST API with personal API keys. Rate-limited per tier. OpenAPI spec. Elite-only feature per IMPLEMENTATION_PLAN.md.

---

## DEFERRED (Original Plan)

| Item | Reason |
|---|---|
| Multi-broker support (beyond Binance/Coinbase) | P1 is Binance + Coinbase. BYBIT/Kraken/FTX later. |
| Regime-switching weights | Useful but lower priority than calibration. |
| Strategy lens backtesting (all 7 lenses) | Backend structure exists, needs frontend building. |
| Telegram bot DCA / recurring buys | Separate product line. |

---

## QUICK STATUS SUMMARY

| # | Item | Status | Priority Order |
|---|---|---|---|
| 1 | Binance trading execution | TODO | P1 |
| 2 | Coinbase trading execution | TODO | P1 |
| 3 | Exchange order UI | TODO | P1 |
| 4 | One-click signal-to-order | TODO | P1 |
| 5 | Outcome dataset pipeline | TODO | P2 |
| 6 | Isotonic calibration | TODO | P2 |
| 7 | Qwen signal quality review | TODO | P2 |
| 8 | Calibration dashboard card | TODO | P2 |
| 9 | Twelve Data primary source | DONE | P3 ✅ |
| 10 | CoinMarketCap crypto fallback | DONE | P3 ✅ |
| 11 | FMP key configured | DONE | P3 ✅ |
| 12 | Quality ring tooltip fix | DONE | P3 ✅ |
| 13 | PnL / equity curve chart | TODO | P4 |
| 14 | Sharpe + win rate stats | TODO | P4 |
| 15 | Drawdown chart | TODO | P4 |
| 16 | Monthly returns heatmap | TODO | P4 |
| 17 | J1 Cost Review card | DONE | ✅ (was Phase 1) |
| 18 | J2 Monte Carlo card | DONE | ✅ (was Phase 1) |
| 19 | MT5 Positions card | DONE | ✅ (was Phase 1) |
| 20 | MT5 Account Summary card | DONE | ✅ (was Phase 1) |
| 21 | Pattern WR badge | DONE | ✅ (was Phase 2) |
| 22 | WebSocket real-time feed | TODO | Phase 2 |
| 23 | Backtesting UI | IN PROGRESS | Phase 2 |
| 24 | Push alerts (web + mobile) | IN PROGRESS | Phase 2 |
| 25 | Stripe checkout | TODO | Phase 3 |
| 26 | Free tier caps (beyond 5/day) | IN PROGRESS | Phase 3 |
| 27 | Tier-gated feature flags | TODO | Phase 3 |
| 28 | Mobile responsive layout | TODO | Phase 4 (last) |
| 29 | PWA offline mode | TODO | Phase 4 |
| 30 | ML parameter optimization | TODO | Phase 5 |
| 31 | Alternative data pipeline | TODO | Phase 5 |
| 32 | Public API | TODO | Phase 5 |
