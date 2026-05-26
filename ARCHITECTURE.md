# DotVerse Architecture Map

> Generated: 2026-05-26 · Single-server Flask monolith + vanilla JS SPA  
> **Source**: `app.py` (14,178 lines) + `static/index.html` (14,322 lines)

---

## BACKEND — `app.py`

### Tech Stack
- **Framework**: Flask (sync, single-worker)
- **Scheduler**: APScheduler `BackgroundScheduler` (runs `run_watch_job` every 60s)
- **DB**: PostgreSQL via SQLAlchemy ORM (`_DBSession` SessionLocal)
- **Cache**: In-process dict TTL cache (5 min) + optional Redis for veredict queue
- **External data**: yfinance, Binance API, TradingView scraper, FMP, Twelve Data, Stooq
- **Notifications**: Telegram Bot API (+ SMS via Twilio, email via SendGrid)

---

### API Routes — Complete Index with Line Numbers

#### App Pages (serve `static/index.html`)
| Route | Line | Auth | Notes |
|---|---|---|---|
| `GET /` | 6593 | No | SPA shell, auth gate in JS |
| `GET /pricing` | 6579 | No | Pricing page |
| `GET /settings` | 6585 | No | Settings page |

#### Auth Routes
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /auth/google` | 6508 | No | Google OAuth redirect |
| `GET /auth/google/callback` | 6525 | No | Google OAuth callback |
| `POST /api/register` | 6603 | No | Email+password registration |
| `POST /api/login` | 6646 | No | Email+password login, sets session |
| `POST /api/logout` | 6685 | login_required | Clears session |
| `GET /api/auth-check` | 6690 | No | Returns `{authenticated, email, tier, role}` |

#### Admin Routes (all `require_admin`)
| Route | Line | Description |
|---|---|---|
| `GET /api/admin/users` | 6715 | List all users |
| `POST /api/admin/set-role` | 6735 | Set user role (user/admin) |
| `POST /api/admin/set-tier` | 6951 | Set user tier (free/pro/elite) |
| `POST /api/admin/invite` | 6781 | Create pre-approved invite |
| `DELETE /api/admin/invite` | 6781 | Delete invite |
| `GET /api/admin/invites` | 6823 | List all invites |
| `POST /api/admin/resend-invite` | 6838 | Resend invite email |
| `POST /api/admin/grant` | 6881 | Grant tier days to user |

#### Analysis — `/api/analyze`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/analyze` | 9014 | login_required | **Core signal engine**. Takes `{ticker, asset_type, timeframe}`, returns full analysis with signal, indicators, SMC structures, chart data. Also writes row to `signal_history`. |

#### Scanner — `/api/scan-list`, `/api/screen`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/scan-list` | 10083 | login_required | Bulk analyze array of tickers (scanner tab) |
| `POST /api/screen` | 9722 | login_required | Pre-screener — quick indicator check before full analysis |

#### Watch / Alert System — `/api/watch*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/watch` | 9763 | login_required | Create/update a price alert watch |
| `DELETE /api/watch` | 9857 | login_required | Remove a watch entry |
| `GET /api/watches` | 9885 | login_required | List active watches for current user |
| `POST /api/alert-test` | 10029 | login_required | Send test alert via Telegram/SMS |

#### Signals History — `/api/signals/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/signals/history` | 12554 | login_required | Last N signals for user |
| `PATCH /api/signals/history/<sig_id>/outcome` | 12596 | login_required | Log outcome on a signal (WIN/LOSS/BE) |
| `GET /api/signals/stats` | 12637 | login_required | Win rate, R-multiple stats per user/timeframe |
| `GET /api/signals/cost-analysis` | 12760 | login_required | Commission/slippage impact analysis |

#### Positions — `/api/positions/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/positions` | 12143 | login_required | List open positions |
| `POST /api/positions` | 12170 | login_required | Open a new position |
| `DELETE /api/positions/<pos_id>` | 12252 | login_required | Delete a position |
| `POST /api/positions/<pos_id>/close` | 12354 | login_required | Close position + log outcome + update equity snapshot |
| `GET /api/positions/correlation-risk` | 12437 | login_required | Correlation heatmap for open positions |

#### Portfolio — `/api/portfolio/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/portfolio/drawdown` | 12490 | login_required | Drawdown metrics from equity snapshots |
| `POST /api/portfolio/reset` | 12726 | login_required | Reset equity index to 100.0 |

#### MT5 Integration — `/api/mt5/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/mt5/order` | 7045 | login_required | Submit order to MT5 EA |
| `GET /api/mt5/pending` | 7096 | login_required | List pending orders |
| `POST /api/mt5/confirm` | 7152 | No (EA secret) | EA reports fill/close/pnl |
| `POST /api/mt5/alert` | 7228 | No (EA secret) | EA pushes TA signal alert |
| `POST /api/mt5/push` | 7456 | No (EA secret) | EA pushes full state sync (positions, account) |
| `GET /api/mt5/state` | 7506 | login_required | Get current EA state (positions, account) |
| `GET /api/mt5/orders` | 7562 | login_required | List historical orders |
| `POST /api/mt5/cancel/<order_id>` | 7598 | login_required | Cancel pending order |
| `POST /api/mt5/close` | 7624 | login_required | Close MT5 position |
| `POST /api/mt5/trailing` | 7667 | login_required | Set trailing stop |

#### Validate / Risk — `/api/validate/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/validate/montecarlo` | 12812 | login_required | Monte Carlo simulation on trade history |
| `POST /api/var` | 12876 | login_required | Value-at-Risk calculation |
| `POST /api/stress` | 12971 | login_required | Stress test scenarios |
| `POST /api/correlation` | 13028 | login_required | Correlation matrix for set of tickers |

#### Backtest — `/api/backtest/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/backtest` | 10833 | login_required | Run async OHLCV backtest (direct) |
| `POST /api/backtest/enqueue` | 13380 | login_required | Enqueue backtest via RQ worker |
| `GET /api/backtest/result/<job_id>` | 13408 | login_required | Poll RQ backtest result |

#### Optimisation — `/api/optimise*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/optimise` | 13219 | login_required | Grid search indicator params |
| `GET /api/optimise/result` | 13427 | login_required | Get stored optimisation result |

#### Simulation — `/api/simulate`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/simulate` | 9938 | login_required | Monte Carlo path simulation |

#### Veredict (AI Agent) — `/api/verdict/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `POST /api/verdict` | 13963 | login_required | Enqueue TradingAgents analysis (RQ) |
| `GET /api/verdict/result/<job_id>` | 14011 | login_required | Poll verdict result |
| `GET /api/verdict/status` | 13678 | login_required | Check worker/TradingAgents availability |
| `POST /api/verdict/queue/clear` | 13728 | login_required | Clear verdict job queue |
| `POST /api/verdict/chat` | 14053 | login_required | Chat with TradingAgents about signal |

#### Settings — `/api/settings/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/settings` | 8360 | login_required | Get `UserSettings` for current user |
| `POST /api/settings` | 8382 | login_required | Update `UserSettings` |
| `POST /api/profile` | 8499 | login_required | Update name |

#### Automation — `/api/automation/*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/automation/settings` | 7706 | login_required | Get `AutomationSettings` |
| `POST /api/automation/settings` | 7712 | login_required | Update `AutomationSettings` |
| `POST /api/recommend-automations` | 8300 | login_required | Suggest automation presets from signal stats |

#### Keys / Connections — `/api/keys*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/keys` | 8535 | login_required | List exchange API keys (decrypted labels) |
| `POST /api/keys` | 8567 | login_required | Add/update exchange API key (encrypts) |
| `DELETE /api/keys/<key_id>` | 8971 | login_required | Delete exchange key |

#### Telegram — `/api/telegram*`
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/telegram-status` | 8601 | login_required | Check Telegram bot connection |
| `POST /api/telegram/webhook` | 8630 | No (Telegram) | Receive Telegram bot messages |
| `GET /api/telegram/setup-webhook` | 8949 | No | Set up Telegram webhook |

#### Market Data
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/live-price` | 8994 | login_required | Live price quote |
| `POST /api/prices` | 10192 | login_required | Bulk price fetch |
| `GET /api/vix` | 8314 | login_required | VIX data + regime analysis |
| `GET /api/econ-calendar` | 10296 | login_required | Economic calendar events |
| `GET /api/news` | 10363 | login_required | Market news headlines |
| `GET /api/sectors` | 10429 | login_required | Sector performance |
| `GET /api/new-listings` | 10478 | login_required | New ETF/IPOs |
| `GET /api/daily-brief` | 10657 | login_required | Daily market brief |
| `GET /api/fear-greed` | 10686 | login_required | Fear & Greed Index |

#### Utilities
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /health` | 10681 | No | Health check |
| `GET /api/stats` | 10716 | login_required | Global signal stats |
| `GET /api/diag` | 9650 | login_required | Diagnostic info |
| `GET /api/pine-script` | 10743 | login_required | Pine Script indicator export |
| `GET /api/pine-divergence` | 10760 | login_required | RSI divergence Pine Script |
| `GET /api/pine-strategy` | 10777 | login_required | Full strategy Pine Script |
| `POST /api/send-sms` | 10794 | login_required | Send SMS alert |

#### Notifications
| Route | Line | Auth | Description |
|---|---|---|---|
| `GET /api/notifications` | 8452 | login_required | Get in-app notifications |
| `POST /api/notifications/read` | 8478 | login_required | Mark notifications read |

---

### Database Models — 13 Tables

#### `User` (line 11622) — `users` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| email | String(255) | unique, not null |
| name | String(128) | nullable |
| password_hash | String(256) | nullable (for Google OAuth) |
| tier | String(16) | free/pro/elite, default "free" |
| role | String(16) | user/admin, default "user" |
| stripe_customer_id | String(64) | nullable |
| daily_analyses | Integer | default 0 |
| last_analysis_date | String(10) | YYYY-MM-DD |
| created_at | DateTime | default utcnow |

#### `Position` (line 11636) — `positions` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | default "default" |
| ticker | String(32) | |
| asset_type | String(16) | stock/crypto/forex/etc |
| signal | String(8) | BUY/SELL, default BUY |
| size | Float | % of account |
| entry_price | Float | |
| stop_price | Float | nullable |
| tp1_price | Float | nullable |
| timeframe | String(8) | nullable |
| opened_at | DateTime | default utcnow |
| outcome | String(10) | WIN/LOSS/BE, nullable |
| close_price | Float | nullable |
| closed_at | DateTime | nullable |
| hit_tp | Integer | 1/2/3 or NULL |

#### `SignalHistory` (line 11670) — `signal_history` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | default "default" |
| ticker | String(32) | |
| asset_type | String(16) | |
| timeframe | String(8) | |
| signal | String(8) | BUY/SELL/HOLD |
| price | Float | nullable |
| entry | Float | nullable |
| stop_loss | Float | nullable |
| tp1 | Float | nullable |
| confidence | Float | 0-100, nullable |
| confidence_label | String(16) | nullable |
| fired_at | DateTime | default utcnow |
| trade_type | String(16) | scalp/day/swing/position, nullable |
| expires_at | DateTime | nullable |
| outcome | String(10) | WIN/LOSS/BE, nullable |
| actual_exit_price | Float | nullable |
| actual_pnl_r | Float | R-multiples, nullable |

#### `OptimisationResult` (line 11656) — `optimisation_results` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| asset_class | String(16) | |
| timeframe | String(8) | |
| rsi_period | Integer | |
| atr_mult | Float | |
| ema_fast | Integer | |
| ema_slow | Integer | |
| sharpe | Float | |
| win_rate | Float | nullable |
| computed_at | DateTime | default utcnow |

#### `EquitySnapshot` (line 11693) — `equity_snapshots` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | default "default" |
| equity_index | Float | default 100.0 |
| snapshotted_at | DateTime | default utcnow |

#### `ExchangeKey` (line 11703) — `exchange_keys` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | Integer | |
| exchange | String(32) | e.g. "binance" |
| label | String(64) | nullable |
| api_key_enc | String(512) | Fernet encrypted |
| api_secret_enc | String(512) | Fernet encrypted |
| created_at | DateTime | default utcnow |

#### `AdminInvite` (line 11714) — `admin_invites` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| email | String(120) | unique |
| invited_by | Integer | nullable |
| created_at | DateTime | default utcnow |
| role | String(20) | default 'user' |
| tier | String(20) | default 'free' |

#### `MT5Order` (line 11724) — `mt5_orders` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | |
| symbol | String(32) | |
| order_type | String(8) | BUY/SELL |
| volume | Float | lots |
| price | Float | requested entry |
| sl | Float | nullable |
| tp | Float | nullable |
| tp2 | Float | nullable |
| tp3 | Float | nullable |
| timeframe | String(8) | nullable |
| action | String(32) | open/close/modify_sl/partial_close/trailing |
| close_ticket | Integer | MT5 ticket to close, nullable |
| status | String(16) | pending/executing/filled/failed/cancelled |
| mt5_ticket | Integer | nullable |
| fill_price | Float | nullable |
| pnl | Float | realised P&L, nullable |
| comment | String(128) | nullable |
| entry_confluence | Float | bull_pct at submit, nullable |
| entry_atr | Float | ATR at submit, nullable |
| created_at | DateTime | default utcnow |
| filled_at | DateTime | nullable |

#### `Watch` (line 11750) — `watches` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | default "legacy" |
| ticker | String(32) | |
| asset_type | String(16) | default "stock" |
| timeframe | String(8) | |
| alert_channels | String(128) | JSON array, default "telegram" |
| be_on | Boolean | Break even at 1 ATR, default False |
| trail_on | Boolean | ATR trailing stop, default False |
| macro_on | Boolean | News guard, default False |
| inval_on | Boolean | EMA/Supertrend invalidation, default False |
| sent_on | Boolean | Sentiment watch, default False |
| tp1_on | Boolean | TP1 alert, default False |
| tp2_on | Boolean | TP2 alert, default False |
| weekend_on | Boolean | Weekend close prompt, default False |
| entry_price | Float | nullable |
| entry_atr | Float | nullable |
| created_at | DateTime | default utcnow |

#### `Notification` (line 11773) — `notifications` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | default "default" |
| ntype | String(32) | market/scan/level/suggestion |
| title | String(128) | |
| body | Text | |
| data | Text | JSON blob, nullable |
| read | Boolean | default False |
| created_at | DateTime | default utcnow |

#### `AutomationSettings` (line 11785) — `automation_settings` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | unique |
| scan_enabled | Boolean | default True |
| scan_risk_pct | Float | default 1.0 |
| breakeven_on | Boolean | default False |
| trailing_on | Boolean | default False |
| trailing_pips | Float | default 50.0 |
| trailing_atr_mult | Float | default 1.0 |
| market_alerts_on | Boolean | default True |
| auto_macro_response | Boolean | default False |
| auto_invalidation_act | Boolean | default False |
| auto_sentiment_watch | Boolean | default False |
| macro_hours_threshold | Float | default 4.0 |
| auto_close_pct | Float | default 50.0 |
| auto_tp1 | Boolean | default True |
| auto_tp2 | Boolean | default False |
| auto_tp3 | Boolean | default False |
| weekend_close | Boolean | default True |
| min_confidence | Integer | default 75 |
| max_trades | Integer | default 3 |
| daily_loss_limit | Boolean | default True |
| daily_loss_max | Float | default 3.0 |
| drawdown_pause | Boolean | default True |
| drawdown_max | Float | default 10.0 |
| news_filter | Boolean | default True |
| ai_reanalyze | Boolean | default True |
| ai_interval | Integer | default 15 (minutes) |
| alert_tp | Boolean | default True |
| alert_sl | Boolean | default True |
| alert_daily_summary | Boolean | default False |
| alert_time | String(5) | default "08:00" |
| updated_at | DateTime | default utcnow |

#### `UserSettings` (line 11823) — `user_settings` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| user_id | String(64) | unique, indexed |
| assets_enabled | Text | JSON array, nullable |
| risk_tolerance | String(16) | conservative/moderate/aggressive |
| chart_theme | String(32) | nullable |
| chart_type | String(16) | default "candles" |
| grid_style | String(16) | nullable |
| indicator_scheme | String(16) | nullable |
| timezone | String(64) | default "UTC" |
| alert_confidence | Integer | default 65 |
| alert_price_pct | Float | default 2.0 |
| alert_drawdown_pct | Float | default 10.0 |
| alert_loss_pct | Float | default 5.0 |
| perf_target_winrate | Integer | default 55 |
| perf_target_rr | Float | default 2.0 |
| perf_target_trades | Integer | default 5 |
| perf_target_annual | Float | default 20.0 |
| portfolio_alloc | Text | JSON object, nullable |
| portfolio_preset | String(16) | default "balanced" |
| portfolio_rebalance | String(16) | default "quarterly" |
| portfolio_benchmark | String(16) | default "spy" |
| mt5_api_key_enc | Text | Fernet encrypted, nullable |
| mt5_account | String(64) | nullable |
| mt5_broker_server | String(128) | nullable |
| telegram_bot_token_enc | Text | Fernet encrypted, nullable |
| telegram_chat_id | String(64) | nullable |
| updated_at | DateTime | default utcnow |

#### `ScanAlert` (line 11874) — `scan_alerts` table
| Column | Type | Notes |
|---|---|---|
| id | Integer PK | autoincrement |
| ticker | String(32) | |
| signal | String(8) | |
| timeframe | String(8) | |
| trade_type | String(16) | scalping/swing |
| entry | Float | nullable |
| sl | Float | nullable |
| tp1 | Float | nullable |
| tp2 | Float | nullable |
| tp3 | Float | nullable |
| lot_size | Float | nullable |
| entry_confluence | Float | nullable |
| entry_atr | Float | nullable |
| sent_at | DateTime | default utcnow |

---

### Key Backend Functions

#### `calculate_indicators(df, timeframe, asset_type)` — line 787
Computes all technical indicators from OHLCV DataFrame. Returns dict with:
- Price, RSI, MACD (histogram + signal), ATR, ATR regime (LOW/NORMAL/HIGH), ATR stop
- EMA 8/13/20/50/200, EMA trend label (STRONG BULL/BULL/MIXED/BEAR/STRONG BEAR)
- Supertrend (bullish/bearish/neutral with price level)
- Bollinger Bands (upper/lower, position %, width)
- Support/Resistance (closest recent pivots)
- Volume ratio, On-Balance Volume
- Chart-ready data: `_chart_df` (last N bars as arrays for lightweight-charts)
- SMC structures dict from `detect_smc_structures()`

#### `detect_smc_structures(df)` — line 3124
Pure mechanical SMC detection on OHLCV. Returns dict with 8 boolean flags + price levels:
- **FVG** (Fair Value Gap): Bullish/Bearish — gap between candle[i-2] and candle[i]
- **Liquidity Grab**: Bullish (equal lows swept + rejection) / Bearish (equal highs swept + rejection)
- **Displacement**: Body > 2× ATR in last 5 bars
- **CHOCH** (Change of Character): First swing high break after downtrend / swing low break after uptrend
Uses 0.1% tolerance for equal highs/lows detection. Minimum 20 bars required.

#### `get_analysis(ticker, asset_type, ind, timeframe, tv, mtf, user_id)` — line 3263
Core signal engine. Gated template logic:
1. Count bullish/bearish indicators: RSI (regime-adaptive zones), EMA trend, MACD hist, Supertrend, BB position
2. Apply higher-timeframe trend gate (blocks counter-trend signals)
3. Apply footprint dominance sanity check (rejects signals contradicting order flow)
4. Compute confidence score (0-100) from net score, volume ratio, ATR regime
5. Apply confidence floor — weak signals downgraded to HOLD
6. Generate entry/stop/target levels (ATR-based)
7. Determine trade type (scalp/day/swing/position)
8. Include SMC structures and counter-trade detect

Also calls `_narrate_data_openai()` for GPT narrative when available, `calculate_win_rate()` for historical stats, and writes to `SignalHistory` DB.

#### `run_watch_job()` — line 4546
APScheduler job (every 60s). For each active watch:
1. Check timeframe-based interval (5m=60s, 1h=300s, etc.)
2. Download fresh OHLCV via `safe_download()`
3. Run `calculate_indicators()` → `pre_screen()`
4. Check account-level circuit breakers (daily loss limit, drawdown pause)
5. Check per-watch automations: BE trail, EMA/Supertrend invalidation, macro news guard, sentiment watch
6. Fire alerts via Telegram/SMS using `send_telegram_keyboard()`
7. Track EMA cross / Supertrend flips for invalidation triggers
8. Dedup via in-memory + optional Redis to avoid spam

---

### Signal Pipeline Flow

```
User Input (ticker, asset_type, timeframe)
    │
    ▼
┌─ fetch_chart_direct() ─────────────────────────────────┐
│  Multi-source data fetcher (priority order):            │
│  1. Binance (crypto)                                    │
│  2. Stooq (forex, indices)                              │
│  3. Yahoo Finance v8 (stocks, ETFs)                     │
│  4. Financial Modeling Prep API                         │
│  5. Twelve Data API                                     │
│  Returns: OHLCV DataFrame                               │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ fetch_tv_data() ──────────────────────────────────────┐
│  TradingView scraper for TA summary (osc/moving/other)  │
│  Used to cross-validate or augment local indicators     │
│  Returns: dict with RSI, MACD, STOCH, etc.             │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ calculate_indicators(df, timeframe, asset_type) ──────┐
│  • RSI, MACD, ATR, ATR regime, ATR stop                │
│  • EMAs 8/13/20/50/200 + trend label                   │
│  • Supertrend, Bollinger Bands, Support/Resistance      │
│  • Volume ratio, OBV, chart-ready data                  │
│  • detect_smc_structures() inline                       │
│  Returns: indicator dict (ind)                          │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ pre_screen(ind) ──────────────────────────────────────┐
│  Quick gateway check before full signal logic.          │
│  Rejects: resting/choppy markets, no clear structure    │
│  Returns: {pass: bool, reason: str}                     │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ get_analysis(ticker, asset_type, ind, timeframe) ─────┐
│  Gated template logic — see detailed function above     │
│  • Count bullish/bearish votes                          │
│  • HTF trend gate                                       │
│  • Footprint dominance check                            │
│  • Confidence score + label                             │
│  • Entry/Stop/TP levels (ATR-based)                     │
│  • Trade type classification                            │
│  • SMC structures narration                             │
│  • Counter-trade detection                              │
│  • OpenAI narrative (optional)                          │
│  • Writes SignalHistory row                              │
│  Returns: full analysis JSON                            │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌─ /api/analyze response ────────────────────────────────┐
│  { signal, confidence, entry, stop_loss, tp1, tp2,      │
│    indicators, smc_structures, chart_dates,              │
│    chart_prices, trade_type, mtf_trend, win_rate, ... }  │
└────────────────────────────────────────────────────────┘
```

---

## FRONTEND — `static/index.html`

### Tech Stack
- **Framework**: Vanilla JS (no React/Vue) — single-file SPA
- **Charting**: `lightweight-charts` (TradingView library v4) via CDN
- **CSS**: Inline `<style>` block (~1300 lines), monolith file
- **State**: Global JS variables (`currentData`, `watchRegistry`, `mt5State`, etc.)
- **Fonts**: Anybody (display), Fira Code (mono), Sora (body)

---

### CSS Architecture (line 9–1330)

Single massive `<style>` block in `<head>`, organized by visual sections:

| Section | Lines | Description |
|---|---|---|
| CSS Variables (`:root`) | 18–45 | Color palette: amber/warm-black brutalist theme |
| Base/Reset | 16, 47–55 | Box-sizing, body background, font |
| Ambient Grid/Noise | 57–74 | CSS grid background + noise texture overlay |
| Scrollbar | 76–96 | Custom amber scrollbar |
| Header Components | 119–203 | Logo, nav, right-side controls |
| Signals Layout | 205–403 | Search bar, ticker pills, signal cards, confidence ring, win badge |
| Charts | 405–536 | Chart controls, canvas, sub-charts (RSI, volume) |
| Cards (Macro/KPI) | 537–580 | News tab macro cards |
| Scanner | 581–644 | Table styles, expandable rows |
| Simulation | 645–751 | Path cards, path detail, pips breakdown |
| Portfolio | 752–786 | Position cards, equity curve |
| Watchlist | 781–830 | Watch items, pulse dot animation |
| Tabs/Mobile | 831–850 | Mobile tab bar at bottom |
| Settings | 851–950 | Settings panel drawer |
| Trade/MT5 | 951–1100 | MT5 order panel, position list |
| Admin | 1101–1180 | Admin panel styles |
| Responsive | 1181–1330 | Mobile/small-screen breakpoints |

Theme: Brutalist/Industrial — Amber on warm black (`#0C0A08`). All tokens in CSS custom properties for consistency.

---

### Tab Navigation Structure

Seven main tabs, controlled by `switchMainTab(name, btn)` (line 10372):

| Tab ID | Name | Nav Button | Panel Line | Data Load Trigger |
|---|---|---|---|---|
| `tab-signals` | Signals | `.nav-tab` at 1335 | 1398 | On analyze (user action) |
| `tab-scanner` | Scanner | `.nav-tab` at 1336 | 2262 | `runScanner()` on tab switch |
| `tab-backtest` | Backtest | `.nav-tab` at 1337 | 2301 | `runBacktest()` on user action |
| `tab-simulation` | Simulation | `.nav-tab` at 1338 | 2489 | `runSimulation()` on tab switch if data loaded |
| `tab-news` | News | `.nav-tab` at 1339 | 2556 | `loadNewsTab()` on tab switch |
| `tab-portfolio` | Portfolio | `.nav-tab` at 1340 | 2602 | On tab switch (loads positions + equity) |
| `tab-trade` | Trade | `.nav-tab` at 1341 | 11870 | `mt5LoadTab()` on tab switch (polls MT5 state every 5s) |

`switchMainTab()` adds/removes `active` class on tab panels and nav buttons, then calls tab-specific loader.

---

### Key Frontend Functions

| Function | Line | Description |
|---|---|---|
| `showGate()` | 3163 | Renders login/register gate overlay |
| `showAdminBtn()` | 3215 | Shows admin panel button if user is admin |
| `showToast(msg)` | 6825 | Toast notification (auto-dismiss 3s) |
| `showError(msg)` | 6820 | Error banner |
| `showNoResults(totalCount)` | 5665 | Empty state with scan line animation |
| `showMobileTab(tab)` | 6656 | Mobile tab bar handler |
| `showCopyCheck()` | 9798 | Copy-to-clipboard checkmark animation |
| `switchMainTab(name, btn)` | 10372 | Tab navigation dispatcher |
| `runScanner()` | 5275 | Scanner tab: iterates watchlist + presets, calls `/api/scan-list` per batch |
| `loadNewsTab()` | 6535 | News tab: fetches `/api/econ-calendar`, `/api/daily-brief`, `/api/fear-greed` |
| `runBacktest(d, showPanel)` | 9483 | Backtest tab: POST to `/api/backtest`, renders results |
| `mt5LoadTab()` | 14091 | Trade tab: polls `/api/mt5/state` every 5s |
| `mt5LoadTradeChart()` | 13378 | Trade tab: renders LW chart for MT5 symbol |

---

### Per-Tab Data Flows (API Endpoint Dependencies)

#### Signals Tab
- User types ticker → `fetch('/api/analyze')` POST `{ticker, asset_type, timeframe}` (line 3797)
- Signal rendered via `currentData` global: chart (LW candles + RSI/BB overlays), signal card, SMC structures, win rate, counter-trade info
- Watch button: `fetch('/api/watch')` POST (line 5830)
- Signal history: `fetch('/api/signals/history?limit=30')` (line 5943)
- Veredict (AI): `fetch('/api/verdict')` POST (optional deep analysis)

#### Scanner Tab
- Loads watchlist + preset ticker lists
- Per batch: `fetch('/api/scan-list')` POST `{tickers, asset_type, timeframe}` (lines 5310, 5324)
- Also bulk pre-checks via `/api/screen` for filtering
- Alert test: `fetch('/api/alert-test')` POST (line 5757)

#### Backtest Tab
- `fetch('/api/backtest')` POST `{ticker, asset_type, timeframe, ...}` (line 9577)
- Also async: `fetch('/api/backtest/enqueue')` + poll `/api/backtest/result/<job_id>`

#### Simulation Tab
- `fetch('/api/simulate')` POST (line 11666) — Monte Carlo paths
- Uses `currentData` from last analysis

#### News Tab
- `fetch('/api/econ-calendar')` (line 6582)
- `fetch('/api/daily-brief')` (line 6632)
- `fetch('https://api.alternative.me/fng/?limit=1')` (line 6947) — external Fear & Greed

#### Portfolio Tab
- `fetch('/api/positions')` GET (line 12329) — position list
- `fetch('/api/var')` POST (line 12485) — VaR calculation
- `fetch('/api/stress')` POST (line 12530) — stress test
- `fetch('/api/correlation')` POST (line 12721) — correlation matrix
- `fetch('/api/optimise')` POST (line 12799) — param optimisation
- `fetch('/api/optimise/result?...')` GET (line 12825) — stored results
- `fetch('/api/signals/stats')` — win rate stats
- `fetch('/api/simulate')` — Monte Carlo paths

#### Trade Tab (MT5)
- `fetch('/api/mt5/state')` GET (polled every 5s, line 14076)
- `fetch('/api/mt5/order')` POST — submit orders
- `fetch('/api/mt5/close')` POST — close positions
- `fetch('/api/mt5/cancel/<id>')` POST — cancel pending

#### Settings / Profile (side panels)
- `fetch('/api/settings')` GET/POST — user preferences
- `fetch('/api/profile')` POST — update name
- `fetch('/api/keys')` GET/POST/DELETE — exchange keys
- `fetch('/api/automation/settings')` GET/POST — automation config
- `fetch('/api/notifications')` GET — in-app alerts

---

## DEPENDENCY MAP

### Frontend → Backend API Dependencies

```
Signals Tab
  ├── POST /api/analyze          ← Core signal engine
  ├── POST /api/watch            ← Price alerts
  ├── DELETE /api/watch          ← Remove alert
  ├── GET  /api/signals/history   ← Recent signals
  ├── POST /api/verdict          ← AI agent deep analysis
  └── GET  /api/live-price       ← Real-time quote

Scanner Tab
  ├── POST /api/scan-list        ← Bulk analysis
  ├── POST /api/screen           ← Pre-filter
  ├── GET  /api/watches           ← Watchlist
  └── POST /api/alert-test       ← Test notifications

Backtest Tab
  ├── POST /api/backtest         ← Direct backtest
  ├── POST /api/backtest/enqueue ← Async backtest (RQ)
  └── GET  /api/backtest/result/<job_id>

Simulation Tab
  └── POST /api/simulate         ← Monte Carlo simulation

News Tab
  ├── GET  /api/econ-calendar    ← Economic events
  ├── GET  /api/daily-brief      ← Market brief
  ├── GET  /api/vix              ← VIX data
  ├── GET  /api/news             ← Headlines
  ├── GET  /api/sectors          ← Sector perf
  └── GET  /api/fear-greed       ← Fear & Greed

Portfolio Tab
  ├── GET  /api/positions        ← Open positions
  ├── POST /api/positions        ← Add position
  ├── DELETE /api/positions/<id> ← Remove position
  ├── POST /api/positions/<id>/close   ← Close + log outcome
  ├── GET  /api/positions/correlation-risk
  ├── GET  /api/portfolio/drawdown
  ├── POST /api/portfolio/reset  ← Reset equity index
  ├── GET  /api/signals/stats     ← Win rate / R-multiples
  ├── POST /api/simulate         ← Path simulation
  ├── POST /api/var              ← Value-at-Risk
  ├── POST /api/stress           ← Stress test
  └── POST /api/correlation       ← Correlation matrix

Trade Tab (MT5)
  ├── GET  /api/mt5/state        ← EA state (polled)
  ├── POST /api/mt5/order        ← Submit order
  ├── POST /api/mt5/close        ← Close position
  ├── POST /api/mt5/cancel/<id>  ← Cancel order
  ├── GET  /api/mt5/orders       ← Order history
  └── GET  /api/mt5/pending      ← Pending orders

Settings / Profile
  ├── GET|POST /api/settings         ← User preferences
  ├── POST /api/profile              ← Update name
  ├── GET|POST|DELETE /api/keys      ← Exchange keys
  ├── GET|POST /api/automation/settings  ← Automation config
  ├── GET /api/notifications         ← In-app alerts
  ├── POST /api/notifications/read   ← Mark read
  ├── GET /api/telegram-status       ← Bot connection check
  └── POST /api/recommend-automations ← Auto suggestions

Auth
  ├── POST /api/register             ← Sign up
  ├── POST /api/login                ← Sign in
  ├── POST /api/logout               ← Sign out
  └── GET  /api/auth-check           ← Session check

Admin
  ├── GET  /api/admin/users          ← User list
  ├── POST /api/admin/set-role       ← Set role
  ├── POST /api/admin/set-tier       ← Set tier
  ├── POST|DELETE /api/admin/invite  ← Invite management
  ├── GET  /api/admin/invites        ← List invites
  └── POST /api/admin/grant          ← Grant tier days
```

### API Endpoint → DB Model Dependencies

```
POST /api/analyze              → SignalHistory  (writes analysis result)
POST /api/register             → User           (creates new user)
POST /api/login                → User           (validates, sets session)
POST /api/settings             → UserSettings   (upsert)
POST /api/profile              → User           (update name)
POST|DELETE /api/watch         → Watch          (upsert/delete)
GET  /api/watches              → Watch          (read)
POST|GET|DELETE /api/positions → Position       (CRUD)
POST /api/positions/<id>/close → Position + EquitySnapshot (close + record equity)
GET  /api/signals/history      → SignalHistory  (read)
PATCH /api/signals/history/outcome → SignalHistory (update outcome)
GET  /api/signals/stats        → SignalHistory  (aggregate)
POST /api/mt5/order            → MT5Order       (create)
GET  /api/mt5/orders           → MT5Order       (read)
GET  /api/mt5/pending          → MT5Order       (filter by status)
POST /api/mt5/confirm          → MT5Order       (update status/fill)
GET  /api/notifications        → Notification   (read)
POST /api/notifications/read   → Notification   (update read)
GET|POST /api/automation/settings → AutomationSettings (read/upsert)
POST|GET /api/keys             → ExchangeKey     (CRUD)
DELETE /api/keys/<id>          → ExchangeKey     (delete)
GET  /api/admin/users          → User           (list)
POST /api/admin/set-role       → User           (update role)
POST /api/admin/set-tier       → User           (update tier)
POST|DELETE /api/admin/invite  → AdminInvite    (CRUD)
GET  /api/admin/invites        → AdminInvite    (list)
GET  /api/portfolio/drawdown   → EquitySnapshot (aggregate)
POST /api/portfolio/reset      → EquitySnapshot (create reset record)
GET  /api/optimise/result      → OptimisationResult (read)
POST /api/optimise             → OptimisationResult (write)
```

### Auth Flow

```
1. REGISTRATION:
   POST /api/register {email, password, name}
   → Creates User row (bcrypt hash)
   → Checks AdminInvite for auto-role/tier assignment
   → Sets session['user_id'], session['authenticated']=True, session['user_tier']
   → Sets session.permanent=True (30-day rolling cookie)
   → Redirects to /

2. LOGIN:
   POST /api/login {email, password}
   → Validates User.password_hash
   → Sets session as above
   → Returns {authenticated: true, email, tier, role}

3. GOOGLE OAUTH:
   GET /auth/google → redirect to Google
   GET /auth/google/callback → verify token, find/create User, set session

4. SESSION PERSISTENCE:
   @before_request → session.permanent = True for logged-in users
   SESSION_COOKIE_SECURE=True  (HTTPS only)
   SESSION_COOKIE_SAMESITE=Lax
   SESSION_COOKIE_HTTPONLY=True
   PERMANENT_SESSION_LIFETIME = 30 days
   SESSION_REFRESH_EACH_REQUEST = True  (rolling window)

5. PROTECTED ROUTES:
   @login_required  → checks session['user_id'] or session['authenticated'], returns 401
   @require_admin   → checks user.role == 'admin', returns 403
   @require_tier(N) → checks numeric tier level, returns 402

6. MT5 AUTH (separate):
   X-EA-Secret header → per-user secret from UserSettings.mt5_api_key_enc
   MT5_BYPASS_USER_IDS → legacy users with no per-user secret requirement
```

### External Service Dependencies

| Service | Purpose | References |
|---|---|---|
| Yahoo Finance | Primary OHLCV source (stocks, ETFs) | `safe_download()` |
| Binance API | Crypto OHLCV | `fetch_binance_ohlcv()` |
| TradingView | TA indicator summary, chart data | `fetch_tv_data()` |
| Stooq | Forex, indices | `_fetch_stooq()` |
| FMP API | Fallback OHLCV | `_fetch_fmp()` |
| Twelve Data | Fallback OHLCV | `_fetch_twelvedata()` |
| Alternative.me | Fear & Greed Index | Frontend direct call |
| Telegram Bot API | Alert delivery (webhook + polling) | `send_telegram_keyboard()` |
| Twilio | SMS alerts | `/api/send-sms` |
| SendGrid | Email alerts (invites, notifications) | Admin routes |
| Google OAuth | Social login | `/auth/google/*` |
| Redis | RQ queue broker, verdict cache, dedup | `_redis_client` |
| OpenAI API | AI narrative on signals | `_narrate_data_openai()` |
| TradingAgents | AI agent verdicts | `/api/verdict/*` |

---

### File Summary

```
/Users/oq/Documents/trading-signals-saas/
├── app.py                    # 14,178 lines — Backend monolith (Flask + SQLAlchemy)
├── static/
│   └── index.html            # 14,322 lines — Frontend SPA (HTML + CSS + JS)
├── requirements.txt          # Python dependencies
├── ARCHITECTURE.md           # This file
└── ... (docs, previews, handoffs)
```
