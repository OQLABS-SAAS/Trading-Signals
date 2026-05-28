# DotVerse — Reimagined Build Plan: Zero Fake Data

**Date:** 2026-05-28
**Audience:** Omar — this is the SLAUGHTERHOUSE honest version. No marketing gloss, no "we can do it all." Every item says what's fake, what replaces it, how hard it is, and whether it's worth it.

---

## EXECUTIVE SUMMARY: The Truth

DotVerse has **two faces** right now:

| Face | What works | State |
|------|-----------|-------|
| **Signals Engine** | SMC, confluence, voting, scan, EODHD, yfinance, TV scanner | ✅ Legit. The core differentiator works. |
| **Market Data Dashboard** | Prices (live via `/api/prices`), F&G, sectors, econ calendar, news | ✅ Mostly real — initial paint has stale placeholders but gets replaced in <2s |
| **Execution** | MT5 read-only state, paper trading, API key storage | ⚠️ Paper trade works but demo positions use non-integer tickets |
| **Trust Metrics** | Pattern WR badge exists (backend), performance page exists (partial) | ⚠️ No PnL curve, no Sharpe, no drawdown chart — the "proof" isn't proven |
| **Simulation** | `/api/simulate` | ❌ Template text + hardcoded probabilities. Educational toy, not analysis. |
| **TV Fallback Path** | `build_ind_from_tv()` | ❌ Fake 52w high/low, fake supertrend, empty chart arrays, fake divergence |

**The brutal truth:** DotVerse's signals engine is real and working. But the surrounding platform has 8 distinct areas where fake/mock data is presented as if it's real. Beginners will lose trust the moment they notice the 52w high is always price × 1.3, or the supertrend is always NEUTRAL, or the simulation probabilities never change.

---

## TIER 0 — KILL ALL FAKES IMMEDIATELY (Ship today)

**Theme:** Stop lying to users. Today. Every fake data point gets either a real source or an honest "unavailable" state. No mock data in any code path.

---

### T0.1 — `build_ind_from_tv()`: Replace ALL fake fallbacks with `ready:false`

**What's fake:**
- `high_52w = p * 1.3` and `low_52w = p * 0.7` — always exactly 30% above/below current price
- `supertrend = "NEUTRAL"` — hardcoded string, never computed
- `chg_1w = 0.0`, `chg_1m = 0.0` — always zero
- `rsi_divergence` — always `{"type":"none",...}` — fake "no divergence found"
- All chart arrays — empty `[]`
- All TA library fields — neutral defaults (adx, ichimoku, vwap, stochrsi)

**What to build:** Replace all fake fallbacks with `None` / empty arrays and add a `"ready": false` field at the dict root. The frontend already guards on `d.ready` — when TV path returns `ready: false`, the Understand tab shows "Detailed indicators unavailable for this scan — run full analysis via Quick Analyse" instead of fake numbers.

**Effort:** 2-3 hours. One function, return dict restructuring.

**User value:** High. Currently a user scanning via TV gets fake 52w metrics that are mathematically impossible (exactly 30% every time). They will notice. This stops that.

**Risks:** None. Frontend already handles `!d.ready` guards in the card render path. Verify all 5+ frontend accessors of these fields.

---

### T0.2 — Market tab initial paint: Show loading state, not stale prices

**What's fake:** Lines 10170-10186. Indices array shows SPY $524.80, QQQ $420.45, DIA $397.20, IWM $198.60. Crypto shows BTC $68,240, ETH $3,485. These are replaced after ~500ms by `_mktUpdateLiveData()`, but the first frame shows stale wrong numbers. A user with slow connection sees them for 2-5 seconds.

**What to build:** Replace hardcoded price/change strings with `"…"` (loading ellipsis). Set `up: true` (neutral styling). The live fetch replaces them within 500ms. Add CSS animation (pulse opacity) on loading state so it's clearly "loading" not "broken."

**Effort:** 30 minutes. 3 array literals + CSS class.

**User value:** Medium. Currently a user sees stale prices that flash to real prices — this looks like a glitch. Clear loading state signals "app is fetching data."

**Risks:** None. `_mktUpdateLiveData()` uses `textContent` to overwrite — it works on any initial value.

---

### T0.3 — Market heatmap: Replace hardcoded % changes with live data

**What's fake:** Lines 10189-10194. 14 S&P stocks with hardcoded percentages (AAPL +1.2, MSFT +0.8, NVDA +3.4, etc.). These ARE overridden by `_mktUpdateLiveData()` for the stock symbols that overlap... but only 8 of 14 symbols match the TM mapping. 6 symbols (UBER, PYPL, INTC, ORCL, ADBE, GOOG) plus GOOG→GOOGL mismatch never get updated.

**What to build:** 
1. Fix `_mktUpdateLiveData()` to add all 14 heatmap symbols with correct TM keys
2. Or — better — render the heatmap AFTER `_mktUpdateLiveData()` completes. Remove the heatmap HTML from the template entirely; have `_mktUpdateLiveData()` populate it after fetching prices.
3. Show "—" for any symbol where price fetch failed.

**Effort:** 1-2 hours. Either fix TM map or restructure render timing.

**User value:** Medium. Partially working today (8/14 update). The 6 stale symbols erode trust.

**Risks:** Low. Test that GOOG→GOOGL resolution works in `/api/prices`.

---

### T0.4 — Market sector bars: Remove hardcoded sector names that don't match live API

**What's fake:** Lines 10210-10217. 6 hardcoded sectors (Technology, Healthcare, Financials, Consumer, Energy, Real Estate) showing "—" until `_loadSectors()` fetches `/api/sectors`. The `/api/sectors` endpoint returns 10 sectors (XLK, XLF, XLV, XLE, XLRE, XLI, XLY, XLP, XLU, XLB). The frontend only renders 6 — 4 are silently dropped.

**What to build:** Make the sector list dynamic — read from `/api/sectors` response and render N bars dynamically, not 6 hardcoded `<div>` elements. Or match the hardcoded list to the API (add the 4 missing: Industrials, Consumer Disc, Consumer Staples, Utilities).

**Effort:** 1-2 hours. Template restructure + CSS for variable count.

**User value:** Low. Only a power user notices missing sectors. But it's fake data in the "DATA" section.

**Risks:** CSS layout needs testing with 10 bars vs 6.

---

### T0.5 — Economic calendar: Eliminate hardcoded fallback

**What's fake:** Lines 10228-10234. Static HTML with NFP at 09:30, ISM at 10:00, Powell at 14:00, UK PMI at 16:30. The `_mktUpdateLiveData()` function DOES replace these with live `/api/econ-calendar` data... but ONLY if at least one event has a valid time. If Finnhub returns events without times, the hardcoded stale list stays forever.

**What to build:** Always replace the econ calendar section after fetching. If `/api/econ-calendar` returns empty or error, show "Economic calendar unavailable — check back later" empty state. Never fall through to hardcoded events.

**Effort:** 30 minutes. Remove the `if(!hasValidTime) return;` guard, add empty-state render.

**User value:** Medium. Hardcoded stale events are obvious fake to anyone who trades.

**Risks:** The live API might return fewer events or different formatting. Test with actual Finnhub response.

---

### T0.6 — `/api/simulate`: Label as educational example or remove

**What's fake:** Lines 11774-11862. 80 lines of template text. Probabilities are always 55-60% / 20-25% / 15-20% based on BUY/SELL/HOLD. Descriptions are template strings with interpolated price levels. No statistical computation, no Monte Carlo, no data-driven path generation.

**What to build:** Option A (better): Rename to `/api/simulate-demo`, add `"type": "educational_demo"` to response, frontend labels it "Simulation Demo — shows template scenarios, not computed probabilities." Remove from production analysis pipeline. Option B (minimum): Add disclaimer text to the simulation card: "Illustrative scenarios only — not based on market data."

**Effort:** 30 minutes for Option B, 1-2 hours for Option A.

**User value:** Low (the feature isn't core to the beginner journey). But it's currently presented as analysis when it's template text.

**Risks:** This is called from Signal tab's Monte Carlo card. Make sure disclaimer doesn't break the card layout.

---

### T0.7 — Remove 3 stub functions

**What's fake:**
1. `startDashClock(){}` — line 5397
2. `_mt5UpdateStatePills(counts) { /* prototype stub */ }` — line 19030
3. `mt5LoadTradeChart(sym, type, tf, levels) { /* prototype stub — no chart panel in v2 */ }` — line 19032

**What to build:** Delete or inline as no-ops with comments. None are called from production paths (verify each call site and either wire them or delete the call).

**Effort:** 15 minutes.

**User value:** Zero visible impact. But cleans the codebase.

**Risks:** Check call sites before deleting — `_mt5UpdateStatePills` might be called after position updates. If so, replace with inline logic instead of deleting.

---

### T0.8 — Demo trade ticket system: Clean up non-integer ticket handling

**What's fake:** Lines 19036-19061. Demo trades (paper trades) use non-integer ticket IDs like 'T001'. The `mt5ClosePosition()` function has a guard at line 19036 that detects non-integer tickets and handles them as demo trades via `_demoPosCache` + localStorage. This means:
- Demo trades and live trades use the SAME close function but with different code paths
- localStorage `dv_exited_demos` tracks closed demo tickets — persists forever, never cleaned
- No backend tracking of paper trades

**What to build:** Either (a) move paper trade close to a separate frontend function (`_closePaperTrade()`) that never calls `mt5ClosePosition`, or (b) add a dedicated `/api/paper/close` endpoint that the UT tab paper trade button calls. Keep `mt5ClosePosition()` clean for real trades only.

**Effort:** 2-3 hours.

**User value:** Low (users don't see the implementation). Medium for maintainability.

**Risks:** High — the Act tab paper trade flow (actPaperTrade → `/api/positions` with `[PAPER]` suffix) works end-to-end today. Don't break it. The `_demoPosCache` is separate from this flow and only used for positions returned by `/api/mt5/state`.

---

### T0.9 — Frontend ticker options: Replace hardcoded `<option>` values

**What's fake:** Line 11039. Quick Analyse ticker selector uses 8 hardcoded `<option>` values: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, AMD. User can type custom tickers, but the dropdown suggests only mega-cap tech.

**What to build:** Fetch watchlist/popular tickers from backend (or current QP_TICKERS list from app.py). Populate `<datalist>` dynamically on page load.

**Effort:** 1-2 hours.

**User value:** Low for existing users, medium for new users who want to analyze non-tech stocks.

**Risks:** None.

---

## TIER 0 TOTALS

| Item | Effort | Impact | Ships alone? |
|------|--------|--------|-------------|
| T0.1 build_ind_from_tv() | 3h | High | ✅ Yes |
| T0.2 Market loading state | 30m | Medium | ✅ Yes |
| T0.3 Heatmap fix | 2h | Medium | ✅ Yes |
| T0.4 Sector bars | 2h | Low | ✅ Yes |
| T0.5 Econ calendar | 30m | Medium | ✅ Yes |
| T0.6 /api/simulate | 1h | Low | ✅ Yes |
| T0.7 Stub functions | 15m | None | ✅ Yes |
| T0.8 Demo tickets | 3h | Low-Med | ✅ Yes |
| T0.9 Ticker options | 2h | Low | ✅ Yes |
| **Total** | **~14h** | | **Can batch to 1-2 sessions** |

**Total user-visible impact of Tier 0:** DotVerse stops presenting any fake data. Every number is either live from a real source or honestly marked unavailable. The platform becomes reliable where it exists — even if it doesn't have everything yet.

---

## TIER 1 — Core Trust: Build Proof That Signals Work

**Theme:** The signals engine is DotVerse's differentiator. But nobody can see it work. Tier 1 builds the evidence layer — the transparent audit trail that converts "trust me" into "look at the data."

---

### T1.1 — Performance Dashboard: Equity Curve + PnL Chart

**What's fake:** Nothing fake — the performance page exists (`showPerformance()`), has signal history and stats. But it's missing the single most important trust metric: a visual PnL equity curve. Users can't see their account growing (or shrinking) over time.

**What to build:** 
- Backend: `/api/signals/equity-curve` — query `SignalHistory WHERE outcome IS NOT NULL AND actual_pnl_r IS NOT NULL`, compute cumulative PnL sorted by `analyzed_at`
- Frontend: Lightweight Charts (already used for price charts) — render equity curve on PERFORMANCE tab above the signal activity log
- Empty state: "No closed trades yet — your equity curve will appear here after logging your first trades"

**Effort:** 2-3 days.

**User value:** **Critical.** The equity curve is the single most convincing piece of proof that signals work. Without it, DotVerse asks for trust on faith.

**Replaces:** Nothing fake directly, but fills a gap where users currently see an empty "No monthly performance data yet" and walk away.

**Risks:** SignalHistory table may have sparse outcome data if users don't close trades. Test with empty dataset.

---

### T1.2 — Sharpe Ratio + Win Rate + Profit Factor Stats Row

**What's fake:** Nothing fake — but these stats don't exist anywhere in the UI.

**What to build:**
- Backend: Extend `/api/signals/performance-metrics` (or create new endpoint) to return:
  - Win rate % (closed trades with profit > 0 / total closed)
  - Profit factor (gross wins / gross losses)
  - Average R per trade
  - Sharpe ratio (annualized from daily PnL, 0% risk-free assumption)
  - Max drawdown %
  - Sample size (total closed trades)
- Frontend: 4-6 stat cards at top of PERFORMANCE tab. Monospace numbers, colored green/red
- Empty state: "Not enough data — log 10+ trades to see meaningful stats"

**Effort:** 1-2 days.

**User value:** High. A new user deciding whether to trust the signals sees: "Win rate: 48% · Sample: 142 trades · Sharpe: 1.8" — that's real proof.

**Risks:** Sharpe ratio needs daily PnL frequency. If trades are infrequent, use trade-level Sharpe (average R / std dev of R). Document the formula.

---

### T1.3 — Monthly Returns Heatmap

**What's fake:** The frontend renders empty heatmap state (line 12428): "No monthly performance data yet." The backend `/api/performance/monthly-heatmap` endpoint exists (line 12114 calls it) but the heatmap rendering code is placeholder.

**What to build:**
- Backend: `/api/signals/monthly-heatmap` — aggregate actual_pnl_r by month, return grid
- Frontend: Calendar-style heatmap using outcome data from backend
- Green = profit, red = loss, intensity scales with magnitude

**Effort:** 1-2 days.

**User value:** Medium. Nice-to-have vs equity curve. Lower priority than T1.1 and T1.2.

**Risks:** SignalHistory may not have enough monthly data for meaningful heatmap.

---

### T1.4 — Signal Track Record Per Pattern

**What's built (already):** Backend `/api/signals/winrate-by-pattern` exists. Pattern WR badge exists on signal cards.

**What's missing:** No dedicated tab or section showing "SMC Liquidity Grab: 64% WR (22 trades) · FVG: 58% WR (15 trades) · Order Block: 71% WR (7 trades)."

**What to build:** Frontend section on PERFORMANCE tab or as a popover on the Pattern WR badge showing the breakdown table. Each row: pattern name, win count, total count, win rate, average R, confidence band (95% CI Wilson score).

**Effort:** 1-2 days.

**User value:** High. Shows WHICH patterns actually work, not just "our signals average X%."

**Risks:** Low sample size per pattern (7-22 trades) means confidence intervals are wide. Show them honestly.

---

### T1.5 — Backtesting UI (Timeframe + Parameter Selector)

**What's fake:** The backend has `calculate_win_rate()` and backtest gate logic. But there's no user-facing backtesting interface where a user can say "test this strategy on AAPL for the last 6 months."

**What to build:**
- Backend: `/api/backtest` endpoint that accepts ticker, timeframe, start/end dates, optional parameters (confidence threshold, pattern filters). Runs the full analysis pipeline over historical data. Returns equity curve, win rate, Sharpe, max drawdown for that period.
- Frontend: Backtest tab or section with ticker input, timeframe selector, date range picker, "Run Backtest" button. Shows results: equity curve, stats summary, trade list.

**Effort:** 3-5 days.

**User value:** **High.** "Don't trust my word — backtest it yourself" is the strongest trust signal.

**Risks:** Compute-heavy. A 6-month daily backtest on one ticker requires 180 analysis runs. Cache results in Redis with 24h expiry. Consider limiting to 5 backtests/day for free tier.

---

## TIER 1 TOTALS

| Item | Effort | Value | Depends on |
|------|--------|-------|-----------|
| T1.1 Equity curve | 2-3d | Critical | SignalHistory with outcomes |
| T1.2 Stats row | 1-2d | High | T1.1 |
| T1.3 Monthly heatmap | 1-2d | Medium | T1.2 |
| T1.4 Per-pattern WR | 1-2d | High | Pattern WR badge (exists) |
| T1.5 Backtesting UI | 3-5d | High | Analysis pipeline (exists) |
| **Total** | **8-14d** | | |

**SLAUGHTERHOUSE HONEST assessment:** Tiers 1.1-1.4 are achievable within 2 weeks. T1.5 (backtesting) is the hardest — historical data access, compute cost, caching strategy. Realistic: ship T1.1-T1.4 in 10 days, leave T1.5 for Phase 2 if user demand justifies it.

---

## TIER 2 — Scale: Make It a Full Platform

**Theme:** DotVerse is currently a single-user web app with manual trading. Tier 2 adds execution, alerts, monetization, and API access. These are PLATFORM features, not core differentiators.

---

### T2.1 — Binance Spot Order Execution

**What's missing:** The `/api/keys` endpoint exists. Encrypted API key storage exists (EncryptionKey model). Binance data feed (`fetch_binance_ohlcv`, `_fetch_binance`) exists. But no actual order placement.

**What to build:**
- `/api/exchange/binance/order` — POST market/limit orders
- `/api/exchange/binance/cancel` — cancel open orders
- `/api/exchange/binance/status` — check order status
- Use CCXT or direct REST to Binance API
- Reuse existing EncryptionKey model for key storage

**Effort:** 5-7 days.

**User value:** **High for crypto traders.** Currently the Act tab only supports MT5 execution (forex/brokers). Binance opens crypto trading directly from DotVerse.

**Risks:** High. Real money. Every error path must be tested: invalid keys, insufficient funds, exchange downtime, order rejection. Requires robust error handling and user confirmation flows. No auto-execute on signal — always user-confirmed.

---

### T2.2 — Coinbase Advanced Trade Execution

**What's missing:** Identical to T2.1 but for Coinbase.

**What to build:** Same pattern as Binance. Coinbase Advanced Trade API. CCXT or direct REST.

**Effort:** 5-7 days (parallel with T2.1).

**User value:** High for US-based traders who prefer Coinbase.

**Risks:** Same as T2.1.

---

### T2.3 — Real-Time Push Alerts

**What's missing:** Alert settings UI exists. `/api/alert-test` endpoint exists. But no push notification infrastructure: no WebSocket, no Telegram bot webhook, no email delivery, no browser push notifications.

**What to build:**
- Telegram bot webhook connector (backend sends message when signal triggers or SL/TP hits)
- Email alerts via SendGrid or SMTP
- Browser push notifications (Service Worker + Push API)
- User preferences UI (which channels, which signal types, quiet hours)

**Effort:** 3-5 days.

**User value:** **High.** Beginners won't sit refreshing the app. Without push alerts, the "set and forget" promise is broken.

**Risks:** Telegram requires bot setup + webhook configuration. Email needs infrastructure. Browser push needs HTTPS (Railway provides).

---

### T2.4 — Mobile Responsive

**What's missing:** The frontend is ~23,000 lines of vanilla JS with fixed-width elements, hardcoded font sizes (9px, 10px in many places), and no responsive breakpoints. It works poorly on mobile.

**What to build:** Add responsive CSS breakpoints. Collapse sidebar to hamburger menu below 768px. Resize cards to full-width. Increase font sizes on mobile. Test on real devices.

**Effort:** 3-5 days (CSS only) to 1-2 weeks (if layout needs restructuring).

**User value:** **High for on-the-go traders.** Currently unusable on phone.

**Risks:** Vanilla JS + inline CSS in a single 23K-line file means CSS changes have high ripple risk. The AUDIT notes 285 instances of font-size:9px and font-size:10px. Changing these globally might break layouts. Use media queries selectively.

---

### T2.5 — Public API for Signal Feed

**What's missing:** No public API. All endpoints require session auth via Google OAuth.

**What to build:**
- API key authentication (separate from Google OAuth)
- Rate limiting per key
- Public endpoints: `/api/v1/signals` (latest signals), `/api/v1/analyze` (analyze a ticker), `/api/v1/scan` (scan tickers)
- Developer portal page with API key management and documentation
- Pricing: free tier (10 req/min) / paid tier (100 req/min)

**Effort:** 5-7 days.

**User value:** Medium. Enables integration with external tools (TradingView webhooks, custom dashboards, algorithmic trading).

**Risks:** API abuse, DDoS, cost of compute. Free tier must be carefully rate-limited.

---

### T2.6 — Stripe Monetization

**What's missing:** `require_tier` decorator exists. Free 5 signals/day counter exists. But Stripe is not wired — no subscription plans, no payment flow, no webhook handling.

**What to build:**
- Stripe subscription plans (Starter: 100 signals/mo, Pro: unlimited)
- Stripe Checkout integration
- Webhook handler for subscription lifecycle (created, updated, cancelled)
- Update user tier in DB on payment event
- Graceful degradation when free tier limit hit

**Effort:** 3-5 days.

**User value:** Enables the business model. Without it, DotVerse is free forever with no revenue.

**Risks:** PCI compliance (Stripe handles this). Refund policy. Free tier must be generous enough to demonstrate value. Begin testing with a single $9.99/mo plan before adding tiers.

---

### T2.7 — MT5 Write-Back (Actual Trade Automation)

**What's built (read-only):** MT5 connection state (`/api/mt5/state`), position list, account summary, close position endpoint (`/api/mt5/close`). The MT5 EA is installed and can execute close orders.

**What's missing:** Place new trades via MT5, modify SL/TP on open positions, partial close, automated trailing stop.

**What to build:**
- Extend MT5 EA to accept new trade orders
- `/api/mt5/order` — place market/pending orders
- `/api/mt5/modify` — modify SL/TP on open positions
- `/api/mt5/partial-close` — close X% of position
- Auto-trailing stop via EA

**Effort:** 3-5 days (EA changes + backend endpoints).

**User value:** **High for forex traders.** Currently MT5 is read-only — you can see positions but can't enter trades through DotVerse.

**Risks:** Modifying the compiled EA (.ex5) requires recompilation. The .mq5 source exists. But any EA changes need rigorous testing — bugs = real money losses.

---

## TIER 2 TOTALS

| Item | Effort | Value | Honest assessment |
|------|--------|-------|------------------|
| T2.1 Binance execution | 5-7d | High | Doable but real-money risk. |
| T2.2 Coinbase execution | 5-7d | High | Parallel with T2.1 if willing. |
| T2.3 Push alerts | 3-5d | High | Telegram is the fastest win. |
| T2.4 Mobile responsive | 5-10d | High | Harder than it sounds — 23K-line file. |
| T2.5 Public API | 5-7d | Medium | Only if there's demand. |
| T2.6 Stripe | 3-5d | Critical for business | Wire after core trust metrics exist. |
| T2.7 MT5 write-back | 3-5d | High | Depends on EA recompilation. |
| **Total** | **29-46d** | | **Realistic: 4-6 weeks full-time** |

**SLAUGHTERHOUSE HONEST:** Tiers 0-1 should be COMPLETE before starting any Tier 2 item. Execution with real money on an app that still has fake data in its indicators is a lawsuit waiting to happen. Push alerts (T2.3) is the one Tier 2 item that could move earlier — it's lower risk and high value.

---

## TIER 3 — Moat: Proprietary Alpha No One Else Has

**Theme:** This is where DotVerse becomes "the best platform" — proprietary models, alternative data, regime adaptation. These are moonshots. Be honest about what's realistic.

---

### T3.1 — Calibrated Confidence Scores (Isotonic Regression)

**What's built:** Raw confidence scores (0-100%) from indicator voting. SIGNAL analysis pipeline works end-to-end.

**What's missing:** The 73% confidence shown on a card means "5 of 7 indicators agree." But if those 5 indicators are wrong 60% of the time in current market conditions, the real win probability is 40%. No calibration.

**What to build:**
- `CalibrationLabel` table: stores (confidence_raw, outcome, timestamp) per signal
- Weekly isotonic regression fit: maps raw confidence → calibrated win probability
- Display calibrated confidence when N ≥ 50 labeled trades, otherwise show raw + "Needs more data"
- Reliability diagram (confidence bin → actual WR) on Performance tab

**Effort:** 3-5 days.

**User value:** **High.** "73% confident" means nothing without calibration. "73% confident — historically, signals at this level win 68% of the time (sample: 142 trades)" is real alpha.

**Replaces:** Nothing fake. But makes the confidence ring genuinely meaningful instead of just "number of indicator votes."

---

### T3.2 — Regime Detection and Adaptation

**What's built:** The regime session data exists in the analysis pipeline. Backend computes session quality, volatility regime, spread costs.

**What's missing:** The signal engine doesn't adapt to regime. A momentum strategy that works in trending markets gets applied in range-bound markets. The confidence doesn't adjust for regime quality.

**What to build:**
- Classify market regime: TRENDING / RANGE-BOUND / HIGH-VOL / LOW-VOL
- Score each signal strategy per regime type (e.g., "FVG patterns: 72% WR in trending, 38% WR in range-bound")
- Adjust confidence based on current regime match: if current regime is trending and signal is trending-optimized, boost confidence. If regime is range-bound and signal is momentum-based, drop confidence.
- Display regime overlay on signal cards: "Current: Trending · FVG Pattern: 72% WR in this regime"

**Effort:** 5-10 days.

**User value:** **Differentiator.** No beginner platform adjusts confidence based on market regime. This is institutional-level analysis made accessible.

**Risks:** Regime classification is subjective — different definitions produce different results. Start simple (volatility percentile + trend strength) and iterate.

---

### T3.3 — Alternative Data Integration

**What's built:** News sentiment (/api/news), Fear & Greed (/api/fear-greed), sector performance (/api/sectors).

**What's missing:** Options flow data, insider transactions, unusual options activity, dark pool prints, social sentiment (StockTwits, Reddit, Twitter), economic surprise indices.

**What to build:**
- Identify 2-3 high-signal alternative data sources (options flow is the most proven)
- Source: marketbeat.com (free insider trades), unusualwhales.com API, or paid data (Quiver Quantitative, BlackRock Aladdin)
- Alternative data dashboard card showing signal-relevant alt data
- Feed alternative data as additional votes into the confluence engine

**Effort:** 5-10 days per source.

**User value:** **High for serious traders.** Alternative data is the modern edge. But most sources cost money.

**Risks:** Data cost. API keys. Most alternative data providers charge $100-500/mo. Decide if the user value justifies the expense. Start with free sources (SEC filings via EDGAR, social sentiment via free APIs).

---

### T3.4 — Custom Strategy Builder

**What's missing:** Users can't create their own signal rules. They get the DotVerse engine or nothing.

**What to build:**
- Visual rule builder: IF [indicator] [operator] [threshold] AND [indicator] [operator] [threshold] → BUY/SELL/HOLD
- Pre-built blocks: RSI > 70, EMA20 > EMA50, BB width > 0.05, volume spike > 2x average
- Test strategy against historical data (reuses backtesting engine from T1.5)
- Save and share strategies
- Track custom strategy performance vs DotVerse engine

**Effort:** 10-15 days.

**User value:** **Moats are built by user-created value.** TradingView's moat isn't Pine Script — it's the community's 100,000+ scripts. A strategy builder that lets users create, test, and share strategies is the long-term moat. But this is 2-3 weeks of work for the MVP.

**Risks:** Complexity. Most users won't build strategies. The ones who do will generate support burden. Start with 5-10 indicator blocks, test with power users, then expand.

---

### T3.5 — Proprietary ML Signal Model

**What's missing:** The current signal engine is rule-based (indicator thresholds + voting). No ML anywhere.

**What to build:**
- Feature engineering: extract 20-50 features from raw OHLCV + indicators
- Label: does price move in predicted direction by at least 1 ATR within N periods?
- Train XGBoost/LightGBM classifier on 5+ years of historical data
- Cross-validate: walk-forward with 6-month training, 1-month test
- Compare against rule-based engine: Sharpe ratio, win rate, average R
- If ML demonstrably outperforms (statistically significant, p < 0.05), blend ML output with rule-based voting
- If ML does NOT outperform, publish the negative result — "We tested machine learning and it didn't beat our rules. Here's the data."

**Effort:** 10-20 days (data collection + training + validation + integration).

**User value:** **Maximum moat if it works.** A proprietary ML model that genuinely outperforms standard TA is worth $1000/mo. But it might not work — and being honest about that is the whole point of this document.

**SLAUGHTERHOUSE HONEST:** There is a **>50% chance** that a simple ML model does NOT meaningfully outperform a well-tuned rule-based system on this type of data. Markets change. ML overfits. The honest path is to build it, test it rigorously, and publish the results — even if they're negative. A platform that says "we tried ML, it didn't help, here's our data" is MORE trustworthy than one that silently ships a mediocre model and calls it AI.

---

### T3.6 — Multi-Agent AI Signal Review (Qwen)

**What's built:** The Understand tab has an "AI Analysis" section with 8 agent breakdown (Market Analyst, Fundamentals Analyst, etc.) at line 15607. Each agent has a hardcoded progress percentage (32%, etc.). This is a visual gimmick, not real analysis.

**What's fake:** Lines 15582-15607. Agent progress percentages are hardcoded. The "AI Analysis" section is template text, not actual LLM calls.

**What to build:**
- Real Qwen calls — pass indicators + regime + signal to Qwen 3.5 Plus
- Prompt: "Review this signal. Rate quality 1-10. List key risks. Any factors the technical engine might have missed?"
- Cache results per (ticker, timeframe, signal_hash) for 1 hour
- Replace fake agent progress bars with a single "AI Review" card showing real output
- Show loading state while Qwen runs (5-10 seconds typical)

**Effort:** 2-3 days.

**User value:** **High if real, damaging if fake.** Currently the AI section is theater. A real second opinion from an LLM adds genuine value — the LLM can catch macro risks (earnings, sector rotation) that pure TA misses.

**Replaces:** Fake agent progress bars and template-based AI analysis text.

**Risks:** Qwen API cost ($0.15-0.30 per call). Cache aggressively. Only run on user-initiated analysis, not background scans. Show "Premium feature" banner on free tier.

---

## TIER 3 TOTALS

| Item | Effort | Moat potential | SLAUGHTERHOUSE assessment |
|------|--------|---------------|--------------------------|
| T3.1 Calibrated confidence | 3-5d | Medium | Should be T2. Realistic, proven technique. |
| T3.2 Regime detection | 5-10d | Medium-High | Harder than it sounds. Start simple. |
| T3.3 Alternative data | 5-10d/source | High | Expensive. Focus on 1-2 free sources first. |
| T3.4 Strategy builder | 10-15d | **Maximum** | Long-term moat. 2-3 week build for MVP. |
| T3.5 Proprietary ML | 10-20d | **Maximum (if works)** | >50% chance it doesn't beat rules. Do it anyway for honesty. |
| T3.6 Multi-agent AI review | 2-3d | Medium | Replace fake AI with real Qwen calls. |
| **Total** | **35-63d** | | **Realistic: 6-10 weeks for the whole tier** |

|---|

## TIER 4 — Multi-Account MT5 Trading Platform (~15 days)

**Theme:** Turn DotVerse from a single-account tool into a multi-account trading management platform. Allow users to connect MULTIPLE MT5 accounts (different brokers, live/demo), each with own positions, balance, equity curve, trading journal, and PnL tracking — plus an aggregated portfolio view across all accounts.

---

### Phase 1 — Database Schema (2 days)

**Models to add:**
- `TradingAccount`: name, broker, server, account_number, type, currency, ea_secret_enc, status
- `TradingJournal`: account_id, signal_history_id, notes, tags, emotion, lesson, screenshot_url

**Existing models to extend:**
- Add `account_id` FK to `SignalHistory`, `MT5Order`, `EquitySnapshot`

---

### Phase 2 — Backend API (3 days)

- CRUD for `TradingAccount`
- Per-account performance endpoints
- Aggregated portfolio endpoints
- `TradingJournal` CRUD
- Refactor `mt5_state` to be account-keyed

---

### Phase 3 — MT5 EA Changes (2 days)

- EA sends `account_id` in push/confirm/alert payloads
- Backward compatible: missing `account_id` falls back to single-account

---

### Phase 4 — Frontend UI (5 days)

- Global account selector in top bar
- Account management page in Settings
- Per-account Act/Portfolio/Performance views
- Trading journal panel with entry form

---

### Phase 5 — Polish (3 days)

- SSE real-time multi-account updates
- Color-coded per-account visual identity
- CSV export per account
- Mobile responsive

---

### User value: HIGH

Turns DotVerse from a single-account tool into a multi-account trading management platform. The user manages 3+ MT5 accounts through one interface with aggregated performance tracking and trading journals.

---

## TIER 4 TOTALS

| Phase | Effort | Value | Depends on |
|-------|--------|-------|-----------|
| Phase 1 — Schema | 2d | — | Base models |
| Phase 2 — Backend | 3d | High | Phase 1 |
| Phase 3 — EA changes | 2d | Medium | Phase 1 |
| Phase 4 — Frontend | 5d | High | Phase 2 |
| Phase 5 — Polish | 3d | Medium | Phase 4 |
| **Total** | **~15d** | | |

---

## COMPLETE ROADMAP — HONEST TIMELINE

```
WEEK 1-2:    TIER 0 — Kill all fakes (14h actual, spread over sessions)
             Ship T0.1-T0.9 incrementally. Each ships alone.
             RESULT: DotVerse has zero fake data. Honest app.

WEEK 3-4:    TIER 1.1-1.4 — Core trust metrics (6-9 days)
             Equity curve, stats row, per-pattern WR, monthly heatmap
             RESULT: "See, our signals actually work. Here's the data."

WEEK 5-6:    TIER 1.5 — Backtesting UI (3-5 days)
             RESULT: "Don't believe us? Test it yourself."

WEEK 7-8:    TIER 2.3 — Push alerts (3-5 days)
             TIER 3.1 — Calibrated confidence (3-5 days)
             RESULT: Alerts work. Confidence is calibrated.

WEEK 9-12:   TIER 2.1-2.2 — Exchange execution (5-7 days)
             TIER 2.6 — Stripe monetization (3-5 days)
             RESULT: Users can trade and pay.

WEEK 13-16:  TIER 2.4 — Mobile responsive (5-10 days)
             TIER 3.6 — Real AI review (2-3 days)
             RESULT: Works on phone. AI is real.

WEEK 17-24:  TIER 3.2-3.5 — Moats (20-45 days)
             Regime detection, alt data, strategy builder, ML model
             RESULT: Best platform.
```

**Total: 24 weeks (6 months) of focused full-time work.**

---

## WHAT NOT TO BUILD

Some things should stay unimplemented or be removed entirely:

| Feature | Why not to build | Alternative |
|---------|-----------------|-------------|
| **Full Monte Carlo simulation** | `/api/simulate` is template text. Real Monte Carlo requires thousands of path simulations → expensive compute on Railway. | Show a disclaimer: "Scenarios are illustrative. Real outcome depends on market conditions." |
| **Walk-forward analysis** (old J4) | Requires 5+ years of tick data per symbol. Too expensive for a beginner platform. | Remove from plan entirely. |
| **Sentiment analysis** on every signal | LLM calls for sentiment on every scan would cost $50+/day. | Only run on user-initiated analysis. |
| **Real-time streaming prices** via WebSocket | Railway free tier can't maintain persistent connections. | Periodic polling (30s interval) is adequate for a beginner platform. |
| **Advanced order types** (OCO, trailing stop, bracket) | High implementation complexity for low beginner usage. | Start with market/limit orders. Add advanced types if users ask. |
| **Social features** (follow traders, copy trading) | Regulatory nightmare (securities laws, KYC/AML). | Not worth the risk for a solo founder. |

---

## THE ONE THING THAT MAKES DOTVERSE THE BEST PLATFORM

If you can only build ONE thing from this entire plan, build this:

> **T1.1 — Equity Curve + T1.2 — Stats Row + T1.5 — Backtesting**

A beginner opens DotVerse, backtests a strategy on AAPL for the last 6 months, sees a 58% win rate and 1.8 Sharpe, then executes the trade through the platform. That's the whole value proposition in 15 seconds. Everything else supports this core loop.

Honest assessment: Tiers 0 + 1 get you to "reliable and trustworthy." Tier 2 gets you to "functional platform." Only Tier 3 gets you to "best in class." Each tier compounds, but Tier 1 is the bottleneck — without proof, nobody trusts the signals enough to execute real money.

---

## APPENDIX: Current Fake Data Registry

Every fake/mock/placeholder in the codebase as of 2026-05-28:

| # | Location | What's fake | Severity | Tier to fix |
|---|----------|------------|----------|-------------|
| F1 | `build_ind_from_tv()` line 1396 | `high_52w = p * 1.3` | 🔴 FAKE MATH | T0.1 |
| F2 | `build_ind_from_tv()` line 1397 | `low_52w = p * 0.7` | 🔴 FAKE MATH | T0.1 |
| F3 | `build_ind_from_tv()` line 1409 | `supertrend = "NEUTRAL"` | 🔴 FAKE | T0.1 |
| F4 | `build_ind_from_tv()` line 1394-5 | `chg_1w = 0.0, chg_1m = 0.0` | 🔴 FAKE | T0.1 |
| F5 | `build_ind_from_tv()` line 1399 | `rsi_divergence` always "none" | 🟡 Partial fake | T0.1 |
| F6 | `build_ind_from_tv()` lines 1412-1424 | All chart arrays empty `[]` | 🟡 Missing (expected for TV path) | T0.1 |
| F7 | Frontend indices array L10170-74 | SPY $524.80, QQQ $420.45 — stale placeholders | 🟡 Stale data | T0.2 |
| F8 | Frontend crypto array L10176-81 | BTC $68,240, ETH $3,485 — stale placeholders | 🟡 Stale data | T0.2 |
| F9 | Frontend heatmap L10189-94 | 14 stocks with hardcoded % changes | 🟡 Stale (8/14 get updated) | T0.3 |
| F10 | Frontend econ calendar L10228-34 | Hardcoded NFP, ISM, Powell events | 🟡 Stale data | T0.5 |
| F11 | `/api/simulate` 11774-862 | Template text, hardcoded probabilities | 🟡 Educational theater | T0.6 |
| F12 | `startDashClock(){}` L5397 | Empty stub | 🟢 Harmless | T0.7 |
| F13 | `_mt5UpdateStatePills()` L19030 | Prototype stub | 🟢 Harmless | T0.7 |
| F14 | `mt5LoadTradeChart()` L19032 | Prototype stub | 🟢 Harmless | T0.7 |
| F15 | Demo tickets 'T001' L19036-61 | Non-integer ticket IDs in close function | 🟢 Low risk | T0.8 |
| F16 | AI Analysis agent progress L15582-7 | Hardcoded 32% progress bars | 🟡 Fake AI | T3.6 |
| F17 | Frontend ticker `<option>` values L11039 | 8 hardcoded tech tickers | 🟢 Low impact | T0.9 |
