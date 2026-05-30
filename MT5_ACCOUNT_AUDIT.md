# DotVerse → Trading Agent Platform: Full Gap Audit

**Audit Date:** May 29, 2026  
**Codebase:** `/Users/oq/Documents/trading-signals-saas/`  
**Files Audited:** `app.py` (17,538 lines), `static/index-v2-prototype.html` (24,182 lines)  
**Spec Reference:** "Trading Agent Platform" — Multi-MT5 Account Management System

---

## 1. Trade Model (Entry/Exit Prices, SL/TP, PnL — Separate from SignalHistory?)

### EXISTS
- **`Position` model** (`app.py:13984`): Has entry/close prices, SL, TP1, outcome, but no dedicated PnL field. The `outcome` (WIN/LOSS/BE) is categorical, and `close_price` exists. No explicit PnL in currency terms — only `actual_pnl_r` (R-multiple) lives on `SignalHistory`.
- **`SignalHistory` model** (`app.py:14018`): Has entry, stop_loss, tp1, outcome, actual_exit_price, actual_pnl_r (R-multiples). Has `account_id` FK to `trading_accounts`. This doubles as a trade log.
- **`MT5Order` model** (`app.py:14135`): Has `pnl` field (realised P&L in account currency) — set by EA on close.
- **`Position`** and **`SignalHistory`** both track outcomes, but they're separate tables used for different purposes (manual position logging vs. signal-triggered trades).

### MISSING
- No unified **`Trade` model** that cleanly separates the concept of "trade" from "signal". Currently, `Position`, `SignalHistory`, and `TradingJournal` all store overlapping trade data.
- No dedicated PnL field (in account currency) on `Position` or `SignalHistory` — only R-multiples.
- No per-trade fields for: commission, swap/financing costs, slippage, execution quality.

### PARTIAL
- Trade tracking exists but is fragmented across 3 tables (`Position`, `SignalHistory`, `MT5Order`) with overlapping semantics.
- Entry/exit/SL/TP are tracked. PnL in R-multiples exists. PnL in currency only exists on `MT5Order`.

---

## 2. DailyMetrics Model

### MISSING
- **No `DailyMetrics` model exists.** The spec requires a model that aggregates daily performance (daily PnL, win/loss count, total trades, drawdown) per account.
- No table for daily snapshots of account-level metrics.
- `EquitySnapshot` (`app.py:14062`) tracks equity index over time but is not a full DailyMetrics model — it only stores a single equity value per snapshot.

### PARTIAL
- `EquitySnapshot` could serve as the basis for DailyMetrics but lacks: daily PnL, trade counts, win/loss breakdown, Sharpe contribution.

---

## 3. Dashboard (Account Selector, Equity Widget, P&L Card, Open Positions Table, Today's Trades, Equity Chart, Risk Gauge)

### EXISTS
- **Dashboard view** exists at `index-v2-prototype.html:5083` — "Trading Dashboard" header with clock, date, session bar.
- **Global MT5 Connection Indicator** (`:5088`): Shows total/online account count.
- **Open positions table** in Portfolio tab (`:11868`): Renders with ticker, direction, size, entry, SL, TP, P&L.
- **Equity chart / PnL curve** in Performance tab (`:13391`): Canvas-based cumulative PnL chart using R-multiples.
- **Drawdown card** (`:13266`): Current/max DD, equity chart with drawdown shading.
- **Performance stats** (`:13191`): Sharpe, win rate, profit factor, expectancy, max DD, avg R/trade.
- **Monthly heatmap** (`:13303`): R-multiples by month.
- **Drawdown gauge** (`:11744`): Portfolio-level drawdown severity indicator.

### MISSING
- **No dedicated account selector dropdown** on the dashboard. The global connection indicator shows aggregate counts but doesn't let the user switch between accounts.
- **No equity widget** showing real-time equity for a selected account on the main dashboard view.
- **No P&L card** showing today's P&L prominently on the dashboard.
- **No "Today's Trades" list** widget on the dashboard. Today's activity is only visible in the Performance tab's "Recent Signal Activity".
- **No risk gauge widget** on the main dashboard — risk gauge only exists in Portfolio tab context.
- **No dedicated dashboard widgets grid** — the dashboard content area is blank on initial load unless navigating to a specific tab.

### PARTIAL
- Dashboard structure exists but the initial dashboard content (`#dashContent`) is empty — populated only when navigating to specific tabs (Market, Portfolio, Performance, etc.).
- The "Trading Dashboard" label at `:5083` is a header but not a functional dashboard with widgets.

---

## 4. Account Management (Real-time Connection Status, Nickname, Labels, Account-Level Stats, Equity History)

### EXISTS
- **`TradingAccount` model** (`app.py:14073`): Full CRUD with name, broker, server, account_number, account_type, currency, platform, status, last_seen, error_message, color, sort_order, is_active.
- **Real-time connection status**: `_account_to_dict()` (`:10108`) computes `connected` status based on `last_seen` (< 45 seconds = connected).
- **Account CRUD endpoints**: `GET /api/accounts` (`:10147`), `POST /api/accounts` (`:10166`), `PUT /api/accounts/<id>` (`:10221`), `DELETE /api/accounts/<id>` (`:10272`).
- **Account summary endpoint**: `GET /api/accounts/<id>/summary` (`:10305`) returns balance, equity, margin, margin_free, margin_level, connected status.
- **Account list UI** (`index-v2-prototype.html:6529`): Renders account cards with name, broker, balance, equity, status, connection dot.
- **mt5_state** (`app.py:366`): In-memory dict tracking account state with positions, account info, and last_seen timestamp.

### MISSING
- **No nickname field** on `TradingAccount` — only `name` exists. The spec calls for a separate nickname that can differ from the account's broker-assigned name.
- **No labels/tags** field on `TradingAccount` — spec requires labels (e.g., "scalping", "swing", "prop firm").
- **No account-level stats** endpoint that returns per-account metrics (total trades, win rate, PnL, Sharpe, etc.).
- **No equity history endpoint** per-account — `EquitySnapshot` is user-level, not account-level.
- **No equity history chart** per-account in the UI.
- **No MT5 feed connection flow** in the frontend — accounts are created manually, not discovered from a live MT5 terminal.
- `mt5_state` is in-memory (lost on restart) — no persistence of connection state.

### PARTIAL
- Connection status computed from `last_seen` is adequate for real-time tracking.
- The TradingAccount model has most base fields but lacks the richer metadata the spec requires.

---

## 5. Trading Journal (Auto-capture from MT5 Feed, Entry/Exit Logging, Risk/Reward Setup, Trade Rationale)

### EXISTS
- **`TradingJournal` model** (`app.py:14095`): Full journal entry model with notes, tags, emotion, lesson_learned, screenshot_url, trade_rating, FK to SignalHistory and TradingAccount.
- **CRUD endpoints**: `GET /api/accounts/<id>/journal` (`:10333`), `POST /api/accounts/<id>/journal` (`:10397`), `PUT /api/journal/<id>` (`:10488`), `DELETE /api/journal/<id>` (`:10576`).
- **Journal UI** toggle button in Portfolio tab (`:11868: "📓 Journal"`).
- **Emotion tracking**: Validates against set: confident, anxious, frustrated, neutral, greedy, fearful, hopeful, excited (`:10418`).
- **Trade rating**: 1-5 scale (`:10426`).
- **Linked trade info**: Journal entries can link to `SignalHistory` via `signal_history_id`, showing ticker, signal, outcome, confidence.

### MISSING
- **No auto-capture from MT5 feed** — journal entries are all manual. The spec requires automatic journal entry creation when MT5 sends a trade close event.
- **No risk/reward setup capture** in the journal — the spec wants pre-trade R:R, stop distance, and risk amount recorded automatically.
- **No trade rationale field** — journal has `notes` but no dedicated `rationale` or `thesis` field.
- **No entry/exit logging automation** — entry/exit prices are not auto-populated from MT5 order fills into the journal.
- **No journal entry timeline/history view** in the Performance tab — only the Portfolio tab has a toggle.

### PARTIAL
- The journal model is well-structured for manual data entry but lacks the automated capture the spec requires.
- Links to SignalHistory provide limited auto-population of trade metadata.

---

## 6. P&L Analytics (Sharpe, Drawdown, Equity Curve, Monthly Heatmap, P&L Distribution, Drawdown Chart)

### EXISTS
- **`GET /api/performance/stats`** (`app.py:15592`): Returns Sharpe ratio, win rate, profit factor, avg win/loss, expectancy.
- **`GET /api/performance/pnl`** (`app.py:15536`): Returns cumulative PnL series, running peak, drawdown series, dates.
- **`GET /api/portfolio/drawdown`** (`app.py:14954`): Returns current drawdown %, max drawdown %, peak equity, consecutive losses, equity snapshot series.
- **`GET /api/performance/monthly-heatmap`** (`app.py:15664`): Returns monthly returns matrix with trade counts.
- **Equity curve chart** (`index-v2-prototype.html:13391`): Canvas-rendered PnL curve with peak/DD lines in Performance tab.
- **Drawdown chart** (`:13266-13281`): Canvas-rendered drawdown sub-chart.
- **Monthly heatmap table** (`:13303-13324`): HTML table with color-coded R-multiples by month.
- **Drawdown gauge** (`:11744`): Portfolio risk indicator in Portfolio tab.

### MISSING
- **No P&L distribution endpoint/chart** — no histogram of trade outcomes. The spec requires a P&L distribution chart showing the frequency of R-multiple outcomes.
- **No per-account P&L analytics** — all analytics are user-level, not account-scoped. The `account_id` field exists on `SignalHistory` but is not used in analytics queries.
- **No drawdown chart as a standalone visualization** — the drawdown is shown as part of the PnL curve card but not as a separate interactive chart.

### PARTIAL
- Sharpe, drawdown, equity curve, and monthly heatmap are fully implemented at the user level.
- Missing P&L distribution and account-scoped analytics.

---

## 7. Multi-Account Management with Combined Portfolio Metrics

### EXISTS
- **Multi-account CRUD**: Full support for multiple `TradingAccount` records per user.
- **Account listing**: `GET /api/accounts` returns all active accounts with connection status.
- **Account summary**: `GET /api/accounts/<id>/summary` returns per-account balance/equity/margin.
- **Global connection indicator**: Shows total vs online account count.
- **Aggregated portfolio data available**: Equity snapshots, signals, and drawdown are aggregated at the user level.

### MISSING
- **No combined portfolio metrics endpoint** — no endpoint that aggregates balance, equity, PnL across all accounts.
- **No portfolio-level P&L** that sums PnL from multiple accounts.
- **No combined equity curve** across accounts.
- **No account grouping/organization** features (folders, groups, color-coded categories beyond `color`).
- **No cross-account position aggregation** in the UI.
- **No dedicated portfolio overview** that shows all accounts side-by-side with combined totals.

### PARTIAL
- Basic multi-account infrastructure exists (model, CRUD, per-account state tracking).
- Aggregation is not implemented — each account is treated independently.

---

## 8. WebSocket for Real-Time Updates

### EXISTS
- **SSE (Server-Sent Events) endpoint**: `GET /api/events/stream` (`app.py:10661-10697`) — a full SSE implementation with heartbeat, client queues, and broadcast via `_sse_broadcast()` (`:81`).
- **Frontend EventSource** (`index-v2-prototype.html:24091`): Connects to `/api/events/stream`, handles notifications, auto-reconnects with exponential backoff.
- **SSE broadcast happens on**: Notification creation, portfolio reset events.

### MISSING
- **No WebSocket** protocol implementation — SSE is used instead. WebSocket would provide bidirectional communication (needed for real-time trade execution commands, MT5 EA commands from the browser).
- **No real-time price stream** via WebSocket — price data comes from polling or SSE, not a persistent WebSocket connection.
- **No real-time position/equity updates** pushed to the UI — the UI must poll `GET /api/accounts/<id>/summary` to see updated balance/equity.
- **No real-time trade execution status** via SSE/WebSocket — order submission uses REST + polling for status.

### PARTIAL
- SSE infrastructure exists and works for one-way notifications (alerts, scan results).
- Missing the bidirectional real-time channel that a proper WebSocket would provide.

---

## 9. Proper Encryption for MT5 Credentials

### EXISTS
- **Fernet encryption** (`app.py:13883-13896`): `_enc()` and `_dec()` functions using `cryptography.fernet.Fernet` with SHA-256 derived key from `ENCRYPTION_KEY` or `SECRET_KEY`.
- **EA secrets encrypted**: `ea_secret_enc` on `TradingAccount` is encrypted with Fernet before storage.
- **Exchange API keys encrypted**: `api_key_enc`, `api_secret_enc`, `api_passphrase_enc` on `ExchangeKey` are Fernet-encrypted.
- **Never expose secrets in API responses**: `_account_to_dict()` explicitly excludes `ea_secret`. The secret is shown only once on account creation.

### MISSING
- **No separate encryption key** for MT5 credentials vs. exchange keys — they share the same Fernet instance.
- **No key rotation mechanism** — encryption key cannot be rotated without re-encrypting all stored secrets.
- **No HSM/enclave** protection — key is derived from an environment variable.
- **No encryption for MT5 connection credentials** (account number, server, broker) — only the EA secret is encrypted. The account number and server are stored in plaintext.

### PARTIAL
- Encryption exists and is correctly applied to secrets.
- Fernet is an appropriate choice for symmetric encryption at rest.

---

## 10. Rate Limiting, Audit Logging

### EXISTS — Rate Limiting
- **API key rate limiting** (`app.py:17272-17321`): Tier-based limits (free=10, pro=60, elite=300 req/min) for the `_api_key_auth` decorator. Uses Redis sliding window.
- **Volatility throttle** (`:11695`): Suppresses signals when volatility exceeds 95th percentile.
- **External API rate limiting**: Yahoo Finance/TradingView rate limit detection with skip-retry.

### MISSING — Rate Limiting
- **No session-based rate limiting** — the rate limiter only applies to API key-authenticated endpoints (`_api_key_auth` decorator), not regular session-authenticated routes. Most routes use `@login_required` which has no rate limiting.
- **No per-endpoint rate limits** — all API key routes share the same global limit.
- **No Redis-based rate limiter for session routes** — free-tier users can hammer session-authenticated endpoints without limits.

### MISSING — Audit Logging
- **No audit logging infrastructure at all.** There is no `AuditLog` model, no audit decorator, no audit trail table.
- **No logging of**: Who modified which account when, what trades were submitted/modified/cancelled, what settings were changed, what API keys were created/revoked.
- **No security audit trail** for compliance purposes.

### PARTIAL
- Rate limiting exists only for the external API key authentication path.
- Session-based routes and all audit logging are completely absent.

---

## SUMMARY TABLE

| # | Requirement | Status | Notes |
|---|-------------|--------|-------|
| 1 | Trade model (entry/exit/SL/TP/PnL) | **PARTIAL** | Spread across 3 tables; no unified Trade model; PnL only as R-multiples in SignalHistory |
| 2 | DailyMetrics model | **MISSING** | No DailyMetrics model or table exists |
| 3 | Dashboard widgets | **PARTIAL** | Structure exists but initial dashboard is empty; missing account selector, equity widget, P&L card, risk gauge on dashboard |
| 4 | Account management | **PARTIAL** | Basic CRUD + connection status exist; missing nicknames, labels, per-account stats, equity history |
| 5 | Trading journal | **PARTIAL** | Full manual journal exists; no auto-capture from MT5, no risk/reward setup, no rationale field |
| 6 | P&L analytics | **PARTIAL** | Sharpe, equity curve, drawdown, monthly heatmap exist; missing P&L distribution chart, per-account analytics |
| 7 | Multi-account management | **PARTIAL** | Multi-account CRUD exists; no combined portfolio metrics, no aggregated views |
| 8 | WebSocket real-time | **PARTIAL** | SSE exists for one-way notifications; no WebSocket for bidirectional communication |
| 9 | Encryption for MT5 creds | **PARTIAL** | EA secrets encrypted; account number/server in plaintext; no key rotation |
| 10 | Rate limiting + audit | **MISSING** | Rate limit only for API key auth; no session rate limiting; no audit logging at all |

---

## KEY GAPS (Highest Priority)

1. **Session-based rate limiting is absent** — any authenticated user can hammer the API without limits. This is a security risk.
2. **Zero audit logging** — no compliance trail for account/trade/settings changes. Regulatory risk.
3. **No DailyMetrics model** — no way to track day-over-day performance per account.
4. **Dashboard is empty on initial load** — users see a blank content area when they first log in.
5. **No combined portfolio metrics** — multi-account support exists in data model but not in aggregation.
6. **No P&L distribution chart** — the spec visualization is missing from an otherwise complete analytics suite.
7. **No auto-capture from MT5 feed into journal** — journal is entirely manual.
8. **Account-level analytics missing** — all metrics are user-level, not per-account.
9. **MT5 credential encryption incomplete** — account number/server stored in plaintext.
