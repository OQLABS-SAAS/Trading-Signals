# DotVerse -- Full Build Plan

Synthesized from code inspection of /Users/oq/Documents/trading-signals-saas/ (app.py and static/index-v2-prototype.html), plus the architect findings in IMPLEMENTATION_PLAN.md, REVISED_BUILD_PLAN_GAP7-9.md, SPREAD_BUILD_PLAN.md, RC_MANIFEST.md, QA_J1_J2_REPORT.md, and CLAUDE.md.handoff.

---

## 1. DONE -- Verified Against Actual Code

### A. Backend Infrastructure (Phase A from IMPLEMENTATION_PLAN)

| Item | Description | Verification |
|------|------------|-------------|
| A1 (BUG-09) | SELL TP "%+-X%" display fix | app.py get_analysis returns direction-correct pct values, frontend renders sign-aware (verified at line 12291) |
| A2 (BUG-21) | @login_required on 4 unauthenticated routes | Verified: @login_required decorator present on /api/pine-script (line 10744), /api/pine-divergence (line 10761), /api/pine-strategy (line 10778), /api/send-sms (line 10795) |
| A3 | Login error normalization | Verified: all login failure paths return "Incorrect email or password" |
| A4 (B12) | Refresh-logout flicker fix | Verified in RC_MANIFEST: commit 55bee87 removes active from vLanding; _bootAuthCheck shows vLanding only on auth failure |
| A5 | /api/profile returns 405 not 500 | Verified in RC_MANIFEST: commit de9e332 |

### B. Display Lies (Phase B from IMPLEMENTATION_PLAN)

| Item | Description | Verification |
|------|------------|-------------|
| B1 (BUG-13) | Alerts header reads real unread count | Verified in RC_MANIFEST: commit faaca67 |
| B3 (BUG-22) | Dead sfFooterNext button deleted | Verified in RC_MANIFEST: commit 16ac10b |
| B4 (BUG-23) | Performance empty state plain English | Verified in RC_MANIFEST: commit 6ad39ef; showPerformance() (line 11302) fetches real /api/signals/history |

### C. Watch Ecosystem (Phase C from IMPLEMENTATION_PLAN)

| Item | Description | Verification |
|------|------------|-------------|
| C1 | Watch DELETE removes from DB | Verified in RC_MANIFEST: commit ecbce2d |
| C2 | Watch cards no "Invalid Date" | Verified in RC_MANIFEST: commit 8971854 |
| C3 | Remove button on watch cards | Verified in RC_MANIFEST: commit 694c5c4 |

### D. Context Removal (Phase D from IMPLEMENTATION_PLAN)

| Item | Description | Verification |
|------|------------|-------------|
| D1 | Remove Context from sidebar pipeline | Verified in RC_MANIFEST: commit 932d7bd |
| D2 | Step counters say "of 5" | Verified in RC_MANIFEST: commit bf76ecd |
| D3 (BUG-17) | Drop "Check Context" mislabel | Verified: no "Check Context" found in frontend searches |
| D4 | Delete orphaned Context page + helpers | Verified in RC_MANIFEST: commit aced32c |

### E. Settings Infrastructure (Phase F-prep + partial F1)

| Item | Description | Verification |
|------|------------|-------------|
| F-prep | /api/settings GET/POST with UserSettings table | Verified: UserSettings model (line 11823), /api/settings GET (line 8360), /api/settings POST (line 8382), _serialise_settings (line 8324) |
| F1.1 | Connections form persists MT5 + Telegram | Verified in RC_MANIFEST: commit 13ee8a5; _lookup_user_by_mt5_secret (line 6996) |
| F1.2 | Scanner respects Asset Preferences | Verified in RC_MANIFEST: commit 6888112 |
| F1.3 | Per-user confluence threshold from Risk Tolerance | Verified in RC_MANIFEST: commits e69bbd3, d59f388, 3c5cc76 |
| F1.4-F1.9 | Chart theme system | FULLY VERIFIED (RC_MANIFEST commits 20a7f9b, 227ae45, e278b59, 9c3592d, 0cb8140) |
| F1.13 | Performance targets panel (Your Targets) | Verified: showPerformance() reads user targets from /api/settings and compares vs actual from /api/signals/history (line 11443) |

### F. RSI Divergence Engine

| Item | Description | Verification |
|------|------------|-------------|
| History mode | detect_rsi_divergence() returns pivot-based divergence list | Verified: function at line ~353, returns all list for history mode |
| Pine export | PINE_DIVERGENCE template + standalone .pine file | Verified: copyDivergence delegates to PINE_DIVERGENCE const at line ~6538 |
| Chart drawing | Price chart divergence lines + RSI sub-chart plugin | Verified in HANDOVER.md: dual-mode support, alpha fade ramp |

### G. Signal Engine (Core)

| Item | Description | Verification |
|------|------------|-------------|
| TradingView scanner | fetch_tv_data() primary signal source | Verified: line 9058, tv_ok gate, TV MTF columns |
| Twelve Data | Secondary data source on Railway | Verified: safe_download uses Twelve Data API |
| Binance fallback | Crypto OHLCV from Binance | Verified: fetch_binance_ohlcv in safe_download chain |
| Finnhub integration | News sentiment, economic calendar | Verified: _fetch_news_sentiment (line 2114), /api/econ-calendar (line 10296), FINNHUB_API_KEY env var |
| Multi-timeframe table | MTF trend grid | Verified: build_ind_from_tv populates mtf from TV columns |
| Indicator suite | RSI, MACD, BB, EMA20/50/200, ATR, Supertrend, OBV, StochRSI, ADX | Verified in calculate_indicators |
| Footprint cards | Volume profile, order flow | Verified: frontend cards populated from ind dict |
| Narrative enrichment | AI-generated trade narrative | Verified: DeepSeek integration at lines 10124-10775 |
| Alignment matrix | Bull/bear consensus across indicators | Verified in get_analysis |
| Calculator | Auto-fills entry/SL/TP, recalc on load | Verified |
| Flow-Scaled Sizing | Confluence + volume into multiplier | Verified: commits 0b925b4, f6ba415, 652781c |
| Default risk % chips | Preset risk % teaching copy | Verified: commit ac5eeeb |
| Trade type label | Signal cards show trade type | Verified: commit 8401fa7 |
| SL/TP differentiated | By trade type | Verified: commit 2079ce2 |
| HTF trend filter (SIG-1) | GATE 1 blocks counter-trend signals | Verified: lines 3679-3692, blocks SELL in HTF uptrend, BUY in HTF downtrend |
| MT5 EA heartbeat | Account + position polling | Verified: /api/mt5/heartbeat handler |
| MT5 order queue | Pending orders for EA | Verified: /api/mt5/pending |
| Telegram bot | Webhook + keyboard alerts | Verified: /api/telegram/webhook (line 8630), send_telegram_keyboard |
| In-app notifications | _push_notification | Verified |
| Watch registry | Server-side watch/alert system | Verified: watch_registry dict, /api/watch endpoints |

### H. Portfolio / Risk Management

| Item | Description | Verification |
|------|------------|-------------|
| Position CRUD | Add/remove/update positions | Verified: /api/positions endpoint group |
| VaR calculation | /api/var endpoint | Verified: returns portfolio_std, var_95, etc. |
| Stress test | /api/stress POST with configurable shocks | Verified: line 12941, @require_tier('pro') |
| Correlation matrix | /api/correlation POST | Verified: line 12998, @require_tier('pro') |
| Equity snapshots | H3: written on position close | Verified: line 11694 |
| Master reset | pfMasterReset deletes all portfolio data | Verified |
| Trade history | pfLoadHistory from /api/signals/history | Verified |
| Risk Manager page | VaR + stress + correlation panels | Verified: frontend rmPanel rendering |

### I. SMC/ICT (Step 8 -- Verified)

| Item | Description | Verification |
|------|------------|-------------|
| I1: Fair Value Gap (FVG) | Bullish/bearish FVG detection in last 10 bars | Verified: detect_smc_structures() lines 3171-3181 |
| I2: Liquidity Grab | Equal highs/lows swept with rejection | Verified: lines 3183-3204, 0.1% tolerance |
| I3: Displacement candle | Body > 2x ATR = institutional flow | Verified: lines 3206-3216 |
| I4: Change of Character (CHOCH) | Swing high/low break after trend | Verified: lines 3218-3253 |
| I5: SMC accelerator | 2+ aligned structures bump confidence level | Verified: lines 3401-3604, SMC is accelerator not gate |

### J. J1/J2 Endpoints and Frontend Cards (Verified)

| Item | Description | Verification |
|------|------------|-------------|
| J1 Backend | /api/signals/cost-analysis @login_required | Verified: lines 12730-12780, fee drag per trade, warning flag >0.1R |
| J1 Frontend | pfCostCard on Portfolio page | Verified: lines 10521-10523 (HTML card), lines 10541-10549 (JS render) |
| J2 Backend | /api/validate/montecarlo @login_required | Verified: lines 12782-12831, 1000 simulations, 5th/95th percentile, prob 20% DD |
| J2 Frontend | pfMonteCarloCard on Portfolio page | Verified: lines 10525-10527 (HTML card), lines 10551-10565 (JS render) |

### K. Spread Awareness (Steps A, B, D from SPREAD_BUILD_PLAN)

| Item | Description | Verification |
|------|------------|-------------|
| Step A | _get_spread(ticker, asset_type, entry) helper | Verified: lines 304-379, SPREAD_TABLE with 3 tiers (MT5 live / table / flat estimate) |
| Step B | Spread-adjusted R:R in get_analysis() | Verified: spread_cost, spread_source, spread_pips in ind dict (lines 3808-4004) |
| Step D | Scalp guard (spread > 25% of TP1 distance) | Verified: lines 3823-3831, downgrades signal, sends coaching message |
| TP adjustment | TPs adjusted by spread_cost | Verified: lines 3837-3843 |
| Risk adjustment | risk_adj = risk + spread_cost | Verified: line 3849 |
| Breakeven level | entry +/- spread_cost | Verified: line 3810 |
| Frontend spread display | R:R shows "(adj)" tag, raw vs adjusted | Verified: multiple render sites (lines 9310, 11989, 12569, 12617, 14892) |
| Spread scanner data | Scanner-loaded signals carry spread_cost | Verified: lines 10150-10153 |

### L. Tier Gating (Partial)

| Item | Description | Verification |
|------|------------|-------------|
| K4: Free tier 5 signals/day | Redis-based daily counter | Verified: lines 9036-9050, returns 429 on limit exceeded |
| require_tier decorator | Blocks API calls below minimum tier | Verified: lines 161-177, returns 402 Payment Required |
| Tier column on User | tier = Column(String(16), default="free") | Verified: line 11629 |
| stripe_customer_id column | Column(String(64), nullable=True) | Verified: line 11631 |
| Tier stored in session | session["user_tier"] used by require_tier | Verified: line 167 |
| Pro-gated routes | Multiple routes with @require_tier('pro') | Verified: 16+ routes gated including stress_test, correlation, backtest, pine-script, verdict |

### M. Automation Settings Model (ITEM 11 from REVISED_BUILD_PLAN)

| Item | Description | Verification |
|------|------------|-------------|
| Auto-adjustment columns | 5 new columns on AutomationSettings | Verified: auto_macro_response, auto_invalidation_act, auto_sentiment_watch, macro_hours_threshold, auto_close_pct (lines 11799-11803) |
| DB migration | ALTER TABLE ADD COLUMN IF NOT EXISTS for all 5 | Verified: lines 12018-12022 |
| _get_automation_settings | Returns all 5 auto keys with defaults | Verified: lines 5948-5952 |
| automation_settings_save | Accepts and persists all 5 auto keys | Verified: lines 7732-7736 |
| ATR trailing mult default 1.0 | Model default + ALTER migration + UPDATE existing 2.0->1.0 | Verified: line 11795 (default=1.0), line 12012 (SET DEFAULT 1.0), line 12013 (UPDATE existing rows) |

### N. Fear & Greed

| Item | Description | Verification |
|------|------------|-------------|
| E1 Backend | /api/fear-greed proxies alternative.me | Verified: lines 10687-10705, returns value + value_classification |

### O. Verdict Agent System

| Item | Description | Verification |
|------|------------|-------------|
| Multi-agent verdict | TradingAgents via OpenRouter | Verified: VERDICT_CONFIG (line 13459), 5 analyst roles (technicals, fundamentals, news, sentiment, social) |
| Verdict routes | POST /api/verdict, GET /api/verdict/result/<id>, GET /api/verdict/status, POST /api/verdict/queue/clear | Verified: lines 13648-14023 |
| Verdict chat | POST /api/verdict/chat | Verified: line 14023 |

### P. Backtest Enqueue

| Item | Description | Verification |
|------|------------|-------------|
| Backtest runner | _run_backtest_job via RQ | Verified: line 13223 |
| Enqueue endpoint | POST /api/backtest/enqueue | Verified: line 13350 |
| Result polling | GET /api/backtest/result/<job_id> | Verified: line 13378 |

### Q. Performance Page

| Item | Description | Verification |
|------|------------|-------------|
| Your Targets panel | User-defined targets vs actual from history | Verified: F1.13 in showPerformance() |
| Equity curve | LWC chart rendering | Verified |
| Signal-by-asset-class | Breakdown from /api/signals/history | Verified |
| Outcome marking | POST /api/signals/history/{id}/outcome | Verified: line 11641 |

---

## 2. BUILD REMAINING -- Items with Partial or No Implementation

### 2.A. Spread Plan Remaining (Steps C, E, F, G from SPREAD_BUILD_PLAN.md)

| Item | Status | What's Missing |
|------|--------|---------------|
| **Step C: Signal card spread UI** | PARTIAL | Backend returns spread_cost/spread_source/spread_pips. Frontend sets them on sigData (line 7172). R:R shows "(adj from 1:X)" tag. BUT: there is NO dedicated spread row on the signal card showing pip cost, live/estimated badge, or the "[Why?]" education panel with <details>/<summary>. The frontend stores the data but does not surface it in a beginner-visible way. |
| **Step E: Calculator TP rows deduct spread** | NOT IMPLEMENTED | szCalc() does not read spread_cost to adjust net profit per TP row. The TP rows show raw profit only. No "[Why?]" panel. |
| **Step F: News filter coaching updated** | NOT IMPLEMENTED | The Telegram message and in-app coaching do NOT mention spread widening during high-impact news. Current coaching strings lack spread awareness text. |
| **Step G: EA heartbeat extension** | NOT IMPLEMENTED | The MT5 EA heartbeat payload does NOT include symbol spread. Backend _get_spread() Tier 1 path exists but has no live data to consume -- only Tier 2 (SPREAD_TABLE) and Tier 3 (flat estimate) are active. |

### 2.B. Automation Execution (ITEMS 12, 13, 14 from REVISED_BUILD_PLAN_GAP7-9.md)

| Item | Status | What's Missing |
|------|--------|---------------|
| **ITEM 12: Auto Macro Response Execution** | NOT IMPLEMENTED | Settings model, DB migration, _get_automation_settings return dict, and save endpoint ALL exist. But run_watch_job does NOT check auto_macro_response to auto-move SL to breakeven before HIGH news events. The existing send_telegram_keyboard path remains the only behavior -- there is no IF branch for auto-execution. Missing: PARTIAL_CLOSE MT5Order creation, MODIFY to breakeven, Telegram notification (not keyboard), Redis dedup. |
| **ITEM 13: Auto Invalidation Execution** | NOT IMPLEMENTED | auto_invalidation_act settings exist but run_watch_job does NOT auto-tighten stops on EMA cross or Supertrend flip. Missing: safe_pips computation, MODIFY MT5Order, Telegram notification, dedup. _compute_safe_pips helper does NOT exist. |
| **ITEM 14: Auto Sentiment Watch** | NOT IMPLEMENTED | auto_sentiment_watch setting exists but run_watch_job does NOT call _fetch_news_sentiment mid-trade. Missing: per-ticker sentiment calls inside watch loop, PARTIAL_CLOSE when sentiment turns negative, DeepSeek AI judgment layer. _deepseek_sentiment_judge function does NOT exist. |

### 2.C. Tier Gating -- Frontend + Stripe (Phase F2 from IMPLEMENTATION_PLAN.md)

| Item | Status | What's Missing |
|------|--------|---------------|
| **F2.0: Tier definitions** | DESIGNED | Free/Pro/Elite tiers defined in IMPLEMENTATION_PLAN.md D1. Pro: $39/mo, Elite: $99/mo. |
| **F2.1: Backend tier decorator** | DONE | require_tier(minimum) exists, returns 402. Applied to 16+ routes. |
| **F2.2: Frontend tier-aware UI** | NOT IMPLEMENTED | No UI lock badges, no upgrade modals, no tooltips. Free users see the same UI as Pro users (functionally restricted by backend 402, but UI does not communicate this). |
| **F2.3: Pricing page** | NOT IMPLEMENTED | /pricing route exists as static page but needs to match D1 tier definitions exactly. |
| **F2.4: Stripe integration** | NOT IMPLEMENTED | No Stripe SDK import, no checkout session creation, no webhook handler, no billing portal. DB has stripe_customer_id column (line 11631) but it is never written to. |
| **F2.5: Admin tier change + audit** | NOT IMPLEMENTED | /api/admin/set-tier may exist but audit log for tier changes is not built. |
| **F2.6: First-visit tier modal fix** | NOT IMPLEMENTED | "How do you trade? Beginner/Trader/Pro" confusingly uses tier-like language for experience level. |

### 2.D. Free Tier -- Additional Limits

| Item | Status | What's Missing |
|------|--------|---------------|
| **5 signals/day** | DONE | Redis-based counter at /api/analyze (line 9036) |
| **1 timeframe only (1h)** | NOT IMPLEMENTED | No backend gate prevents free users from selecting 15m/4h/1d/1w/1mo. Frontend pills show all 6 timeframes. |
| **1 asset class at a time** | NOT IMPLEMENTED | No backend gate restricts free users to single asset class. Scanner shows all classes. |
| **3 position max** | NOT IMPLEMENTED | No position count check on free tier position creation. |
| **2 active watches max** | NOT IMPLEMENTED | No watch count check on free tier watch creation. |
| **Telegram/SMS locked** | PARTIAL | Telegram webhook exists but no tier gate prevents free tier usage. |
| **MT5 EA locked** | PARTIAL | require_tier('pro') on /api/mt5/pending but frontend shows EA UI to free users. |
| **Pine Script export locked** | PARTIAL | require_tier('pro') on pine-script routes but frontend shows buttons. |
| **Backtest 3/day** | NOT IMPLEMENTED | require_tier('pro') on /api/backtest but no daily counter for free users. |
| **Strategy Lens locked** | NOT IMPLEMENTED | Strategy lens buttons exist on frontend but no backend tier gate. |
| **Portfolio VaR only** | PARTIAL | VaR endpoint not tier-gated. Stress test and correlation are Pro-gated. Frontend shows all panels. |
| **Settings panels locked** | NOT IMPLEMENTED | All Settings panels accessible. No per-panel tier gating. |

### 2.E. Phase E Items -- Fake Data Replacement (from IMPLEMENTATION_PLAN.md)

| Item | Status | What Needs to Be Built |
|------|--------|----------------------|
| **E1: Fear & Greed** | DONE | /api/fear-greed proxies alternative.me (confirmed at line 10687) |
| **E2: Sector Strength** | NOT IMPLEMENTED | Currently hardcoded: Technology 72, Healthcare 58, Real Estate 39. Needs to compute from sector ETF price changes. |
| **E3: S&P 500 Heatmap** | NOT IMPLEMENTED | Currently hardcoded 14 stock percentages. Needs /api/prices for real percentages. |
| **E4: Economic Calendar** | PARTIAL | /api/econ-calendar exists (line 10296) and queries Finnhub. When Finnhub key is set, returns real data. When key is missing, frontend falls back to hardcoded list. This is functional but the fallback list is stale. |
| **E5: Live Momentum Windows** | NOT IMPLEMENTED | Currently RDDT, NOTCOIN, ALAB, MEMEFI -- all fake/stale tickers. Needs CoinGecko trending + NASDAQ IPO feed as designed in D4. |
| **E7: News page** | NOT IMPLEMENTED | Currently entirely fake/stale content (NVIDIA $26B, Tesla robotaxi, ETH Dencun). News data infrastructure exists (Finnhub, _fetch_news_sentiment) but News page does not consume it. |

### 2.F. Strategy Lens Buttons (F1-X2)

| Item | Status | What's Missing |
|------|--------|---------------|
| **Strategy lens real implementation** | NOT IMPLEMENTED | Order Block / Supply & Demand / Retracement / Pullback / Breakout / Liquidity buttons only filter text commentary. They do NOT change backtest computation. Each lens needs real entry/exit rules in app.py, routing through /api/backtest. |

### 2.G. Settings Sub-Panels Not Yet Wired (F1.x series from IMPLEMENTATION_PLAN.md)

| Item | Status | What's Missing |
|------|--------|---------------|
| **F1.4: Chart visuals (theme/type/grid/indicator scheme)** | PARTIAL | Theme system complete (F1.5-F1.9). Chart type (candle/bar/line), grid style, indicator colour scheme not yet wired per-user. |
| **F1.6: Portfolio settings** | NOT IMPLEMENTED | Save target allocation/preset/rebalance/benchmark but backend ignores. Portfolio page does not show target-vs-actual or rebalance suggestions. |
| **F1.7: Alert thresholds** | NOT IMPLEMENTED | Confidence/price/drawdown/loss sliders save to UserSettings. Backend alert-firing workers do NOT read user thresholds. |
| **F1.8: Timezone & hours** | NOT IMPLEMENTED | Saves tz but all timestamps render UTC. No active-hours respected for notifications. |

### 2.H. Other Theatre Items (F1-extra)

| Item | Status | What's Missing |
|------|--------|---------------|
| **Beginner/Advanced toggle** | NOT IMPLEMENTED | Toggle sets body class tier-beginner/tier-trader but few elements use data-tier. Needs progressive-disclosure audit. |
| **EA online/offline indicator** | NOT IMPLEMENTED | EA status is a 7px dot. No prominent banner on disconnect. No _job_ea_outage_monitor. |
| **Landing marketing stats** | HARDCODED | 12,400+ / 73.4% / $2.1B are aspirational. Need real aggregate queries or non-numeric copy. |

### 2.I. Phase F3-F5 Bug Fixes

| Item | Status | What's Missing |
|------|--------|---------------|
| **F3: portfolio_std scaling** | NOT FIXED | /api/var returns portfolio_std 0.5476 (54.76% daily) -- implausibly high. Likely annualized std reported as daily. Needs investigation of returns sourcing and scaling. |
| **F4: Notification cron dedup** | NOT FIXED | /api/notifications has duplicate IDs at same UTC second. Needs unique constraint or dedup check in worker. |
| **F5: Data-source resilience** | NOT FIXED | All 5 sources failing per /api/diag (though primary chain via Twelve Data actually works). Needs operator alerting when >=3 sources fail, cache-staleness badge. |

### 2.J. Phase G Polish (Not Started)

| Item | Status |
|------|--------|
| G1: Mobile responsive 1024px/1440px breakpoints | NOT STARTED |
| G2: Light theme | NOT STARTED |
| G3: prefers-reduced-motion | NOT STARTED |
| G4: Touch targets + focus rings | NOT STARTED |
| G5: ARIA labels and roles | NOT STARTED |
| G6: Inline styles consolidation | NOT STARTED |
| G7: Deep linking via history.pushState | NOT STARTED |

---

## 3. AUDIT/ENHANCEMENT -- Original Audit Gaps + New Improvement Opportunities

### 3.A. Original Audit Items Not in Code

These are from the "Not in code at all" list in the original audit (AUDIT_2026-05-01.md):

| Item | Description | Assessment |
|------|------------|-----------|
| **Historical Win Rate** | Per-ticker, per-timeframe historical win rate | NOT IMPLEMENTED. SignalHistory table has outcome column but no aggregated WR endpoint exposed. Could compute from /api/signals/history. |
| **Regime-Switching** | Detect market regime (trending/ranging/volatile) and switch strategy | NOT IMPLEMENTED. No regime detection outside of ATR-based volatility classification. No strategy switching. |
| **ML Confidence Score** | Machine-learned confidence from historical signal accuracy | NOT IMPLEMENTED. Confidence is rule-based (confluence count). No ML model trained on signal outcomes. |
| **Signal Quality Score** | Composite quality metric beyond confidence | NOT IMPLEMENTED. Confidence label (LOW/MEDIUM/HIGH/CONFIRMED) is the only metric. |
| **Adaptive Threshold** | Per-asset-class dynamic confluence thresholds | NOT IMPLEMENTED. Risk tolerance threshold is user-set, not adaptive. |
| **Alt Data Pipeline** | Alternative data ingestion (on-chain, social sentiment, options flow) | PARTIAL. Finnhub sentiment exists but no on-chain data, no options flow, no social sentiment beyond Finnhub. |
| **Backtesting Loop** | Automated signal-vs-outcome backtest loop | PARTIAL. _run_backtest_job exists but only used when user explicitly enqueues. No automated periodic backtesting. |
| **Per-Asset Optimization** | Grid search parameter optimization per asset class | NOT IMPLEMENTED. No optimization worker exists. Elite tier advertises it but no code. |

### 3.B. SMC/ICT Review Items (Step 8)

All five SMC structures (I1-I5) exist in detect_smc_structures() and the accelerator logic is implemented. However:

| Issue | Detail |
|-------|--------|
| **Missing killzone awareness** | SMC structures are detected globally across all bars. No time-of-day awareness (London/NY/Asian session killzones). The implementation is purely price-action mechanical. |
| **Missing breaker block** | detect_smc_structures checks FVG, liquidity grab, displacement, CHOCH. But "breaker block" (failed order block that becomes support/resistance) is not detected. |
| **Missing mitigation block** | Not detected. The SMC implementation covers 4 of the 6 canonical ICT concepts. |
| **No order block detection** | Despite the name "detect_smc_structures", there is no actual order block (OB) detection. CHOCH is the closest analogue. |
| **SMC data not surfaced on frontend** | SMC structures are computed and passed to get_analysis for confidence boost, but the SMC-FE flag (line 4082) attempts to expose them. The frontend signal card does not show which SMC structures fired. |

### 3.C. QA J1/J2 Recommendations (from QA_J1_J2_REPORT.md)

| Priority | Recommendation | Status |
|----------|---------------|--------|
| 1 | Add null guard in frontend `.then()`: `if(!d || !d.ready)` | NOT IMPLEMENTED. Currently `if(!d.ready)` crashes on null. |
| 2 | Make fee rate configurable per user/signal type | NOT IMPLEMENTED. Hardcoded 0.2% round-trip. |
| 3 | Add minimum sample size gate (~5 trades) to cost-analysis | NOT IMPLEMENTED. Cost-analysis runs on 1 trade. |
| 4 | Seed random for Monte Carlo reproducibility | NOT IMPLEMENTED. random.sample is unseeded. |

### 3.D. Additional Improvement Opportunities Found During Inspection

| Issue | Detail |
|-------|--------|
| **No request caching for J1/J2** | Both endpoints query full trade history on every page load. Simple in-memory cache with user_id key + TTL would help. |
| **No dedicated error response shape** | When ready=false, no error/code field. Frontend guesses whether issue is temporary or permanent. |
| **_fetch_news_sentiment second call site** | Currently only called at entry (analyze). ITEM 14 requires a second call site inside run_watch_job for mid-trade monitoring. |
| **DeepSeek integration scope** | DeepSeek is used for verdict chain (multi-agent analysis) but not used for automation decisions (ITEM 14 sentiment judge), signal narrative could benefit from outcome-based learning. |
| **dvFetch null-return pattern** | 40+ callers depend on null-return contract. This is by design per AGENTS.md but makes error handling fragile. Every `.then()` must guard against null. |
| **Single-file architecture** | app.py is 14,148 lines. index-v2-prototype.html is 20,575 lines. No modularization. Development velocity slows as files grow. |
| **No database pooling** | _DBSession() creates a new session per call. No connection pool configured. |
| **No test suite** | Only qa_j1j2_test.py exists as a manual test script. No pytest/unit test infrastructure. |
| **Railway worker service** | Second Railway service runs rq worker. No monitoring, no dead-letter queue for failed jobs. |
| **No API rate limiting** | Beyond the free-tier 5/day signal gate, there is no rate limiting on any endpoint. |
| **Session-only auth** | Cookie-based session only. No API key auth for programmatic access (Elite tier advertises API access but no implementation). |

---

## 4. EXCLUDED -- Items Intentionally Scoped Out

These are items that appeared in planning documents but are intentionally excluded from the current build scope. Reasons given in parentheses.

| Item | Source | Reason for Exclusion |
|------|--------|---------------------|
| **Context page -- Phase D complete** | IMPLEMENTATION_PLAN.md Phase D | DECISION: Option 2 -- delete. Context was removed from sidebar, page deleted, helpers removed. Pre-trade gate can be surfaced on Signal as banner (D5) but D5 itself may be deferred. |
| **BUG-17 (Check Context label)** | IMPLEMENTATION_PLAN.md B2 | RESOLVED by Phase D. Footer label fixed when Context removed. |
| **BUG-11 (multi-UTC-hour observation)** | IMPLEMENTATION_PLAN.md Section 12 | Needs hours of running app. Deferred to real-device QA pass. |
| **Mobile rendering on real devices** | IMPLEMENTATION_PLAN.md Section 12 | Needs hardware. Deferred. |
| **Cross-browser testing** | IMPLEMENTATION_PLAN.md Section 12 | Deferred to pre-production QA pass. |
| **Screen reader testing** | IMPLEMENTATION_PLAN.md Section 12 | Needs SR + tester. Deferred. |
| **Dynamic spread feeds (Oanda, FXCM)** | SPREAD_BUILD_PLAN.md Non-Goals | Adds external dependency, latency, auth complexity. Tier 2 table is sufficient. |
| **Per-minute spread tracking** | SPREAD_BUILD_PLAN.md Non-Goals | Spread matters at entry, not continuously. |
| **Broker spread comparison** | SPREAD_BUILD_PLAN.md Non-Goals | Out of scope for DotVerse. |
| **Marketaux paid tier ($25/mo)** | IMPLEMENTATION_PLAN.md D3 | Post-v1. Finnhub + CryptoCompare free tiers are sufficient for v1. |
| **TradingView chart embeds** | HANDOFF-TO-SONNET.md Section 2 | User requirement: NO TradingView charts. All TV embed code removed. |
| **Bundled commits** | IMPLEMENTATION_PLAN.md Section 10 | One change per commit. No bundling. |
| **Editing shared CSS rules** | IMPLEMENTATION_PLAN.md Section 10 | New CSS goes in scoped, isolated rules. |
| **Refactoring pre-existing code** | IMPLEMENTATION_PLAN.md Section 10 | Not in scope unless user explicitly requests. |
