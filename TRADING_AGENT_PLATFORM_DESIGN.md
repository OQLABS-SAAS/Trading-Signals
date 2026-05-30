# Trading Agent Platform — System Design

**Version:** 1.0
**Date:** May 29, 2026
**Codebase:** `/Users/oq/Documents/trading-signals-saas/`
**Status:** Design-Phase Specification

---

## Overview

The Trading Agent Platform extends DotVerse with multi-account trade management, daily performance metrics, P&L analytics, and a polished trading journal — all built on the existing Flask + PostgreSQL + vanilla JS stack. This document defines the data models, API contracts, frontend behavior, and cross-cutting concerns for the feature set.

---

## 1. Data Models

### 1.1 TradingAccount (Refined)

The existing `TradingAccount` model (`app.py:14073`) is extended with the following new columns:

| Column | Type | Purpose |
|---|---|---|
| `deleted_at` | DateTime, nullable | Soft-delete timestamp. NULL = active account. Non-NULL = archived. |
| `nickname` | String(64), nullable | User-assigned display name distinct from `name` (broker-assigned). |
| `labels` | Text, nullable | JSON array of tag strings, e.g., `["scalping", "prop firm"]`. |

**Soft-Delete Contract (QA Gap 7):**
- Accounts are **never** hard-deleted via the API.
- `PATCH /api/trading-agent/accounts/<id>/archive` sets `deleted_at = now()`.
- Associated `MT5Order` rows, `TradingJournal` entries, and `DailyMetrics` rows **remain in the database** with their `account_id` FK intact. This preserves the audit trail and prevents dangling references.
- All dashboard/list queries filter to `WHERE deleted_at IS NULL` by default.
- A future admin panel may expose archived accounts with a `?include_archived=true` query parameter. Not required for MVP.

### 1.2 DailyMetrics (New — QA Gap 5)

A new model for per-account daily performance snapshots. Created **only on days with at least one closed trade**.

```python
class DailyMetrics(Base):
    __tablename__ = "daily_metrics"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    account_id    = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False, index=True)
    user_id       = Column(String(64), nullable=False, index=True)
    date          = Column(Date, nullable=False)
    trades_total  = Column(Integer, nullable=False, default=0)
    trades_won    = Column(Integer, nullable=False, default=0)
    trades_lost   = Column(Integer, nullable=False, default=0)
    pnl_r         = Column(Float, nullable=True)      # Sum of R-multiples for the day
    pnl_currency  = Column(Float, nullable=True)      # Sum of PnL in account currency
    start_equity  = Column(Float, nullable=True)      # Account equity at start of day
    end_equity    = Column(Float, nullable=True)       # Account equity at end of day
    max_drawdown  = Column(Float, nullable=True)      # Intraday max drawdown %
    created_at    = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_account_date"),
    )
```

**Idle Day Policy (QA Gap 5):**
- `_compute_daily_metrics()` **only** inserts a row when `COUNT(closed trades for that account on that date) >= 1`.
- Days with zero closed trades produce **no row** in `daily_metrics`. There are no zero-trade gap-filler rows.
- The equity curve and frontend charting interpolate naturally across missing days (gaps in the date series are filled by connecting adjacent data points).
- On account creation or after a long idle period, the dashboard shows "No trading activity yet — metrics will appear after your first closed trade."

**Computation trigger:**
- Called after every trade close event (MT5 order fill with `status='filled'` + `close_ticket` present, or manual position close via `POST /api/positions/<id>/close`).
- Also available as a background reconciliation job: `POST /api/trading-agent/accounts/<id>/recompute-daily` (runs once on demand, idempotent due to the unique constraint).

### 1.3 Trade Model (Consolidated)

The existing `Position`, `SignalHistory`, and `MT5Order` models serve overlapping purposes. The design retains them (no breaking schema changes for MVP) but adds a **read-only unified view** — `GET /api/trading-agent/trades` — that joins across the three tables and presents a single trade-list shape:

```json
{
  "id": "pos-42",
  "source": "mt5_order",       // "position" | "signal_history" | "mt5_order"
  "account_id": 1,
  "ticker": "EURUSD",
  "direction": "BUY",
  "entry_price": 1.0850,
  "exit_price": 1.0872,
  "entry_time": "2026-05-28T14:30:00Z",
  "exit_time": "2026-05-28T18:45:00Z",
  "pnl_r": 1.2,
  "pnl_currency": 45.60,
  "currency": "USD",
  "outcome": "WIN",
  "commission": null,
  "swap_cost": null,
  "linked_signal_id": 591
}
```

This view is the data source for the CSV export and the dashboard trade list.

---

## 2. API Endpoints

### 2.1 Account Archive (QA Gap 7)

```
PATCH /api/trading-agent/accounts/<id>/archive
```

**Request:** No body required.
**Response:**
```json
{
  "ok": true,
  "deleted_at": "2026-05-29T10:15:00Z",
  "message": "Account archived. Trades and metrics are preserved."
}
```

**Behavior:**
- Sets `TradingAccount.deleted_at = now()`.
- Does NOT cascade-delete any related rows.
- Returns 404 if account doesn't exist or `deleted_at` is already set (idempotent — second call returns 200 with the existing timestamp).
- Returns 403 if the account belongs to a different user.

**Frontend:**
- Account card in the sidebar/dashboard shows a small "Archived" badge if `deleted_at` is non-null.
- Account list query (`GET /api/accounts`) excludes archived accounts by default.
- A "Show Archived" toggle in the settings panel adds `?include_archived=true` to the query.

### 2.2 Daily Metrics Query

```
GET /api/trading-agent/accounts/<id>/daily-metrics
```

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `from` | ISO date | 30 days ago | Start of range (inclusive) |
| `to` | ISO date | today | End of range (inclusive) |

**Response:**
```json
{
  "account_id": 1,
  "metrics": [
    {
      "date": "2026-05-28",
      "trades_total": 3,
      "trades_won": 2,
      "trades_lost": 1,
      "pnl_r": 2.4,
      "pnl_currency": 52.30,
      "start_equity": 10250.00,
      "end_equity": 10302.30,
      "max_drawdown": 1.2
    }
  ],
  "has_gaps": true
}
```

- `has_gaps` is `true` when the date series has missing days (no-trade days). The frontend uses this flag to render the equity curve with interpolation rather than zero-fill.
- Returns an empty `metrics` array (not an error) for accounts with no trade activity.

### 2.3 CSV Export (QA Gap 6)

```
GET /api/trading-agent/trades/export
```

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `account_id` | int | (all) | Filter to one account |
| `from` | ISO date | (90 days ago) | Start of trade range |
| `to` | ISO date | today | End of trade range |
| `max_rows` | int | 10000 | Maximum rows to export. Prevents memory exhaustion. |
| `format` | string | `csv` | Output format. Only `csv` supported for MVP. |

**Implementation (streaming — never loads full result set into memory):**

```python
@app.route("/api/trading-agent/trades/export", methods=["GET"])
@login_required
def export_trades():
    user_id = session.get("user_id", "default")
    account_id = request.args.get("account_id", type=int)
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    max_rows = min(request.args.get("max_rows", 10000, type=int), 50000)

    def generate():
        # Write CSV header
        yield "id,account_id,ticker,direction,entry_price,exit_price,entry_time,exit_time,pnl_r,pnl_currency,currency,outcome\n"

        db = _DBSession()
        try:
            # Build query across all three trade sources with ORDER BY exit_time DESC
            # Use yield_per() for server-side cursors if available, else paginate
            query = _build_unified_trade_query(db, user_id, account_id, date_from, date_to)
            row_count = 0

            for trade in query.yield_per(500):
                if row_count >= max_rows:
                    yield f"# Truncated at {max_rows} rows. Use filters to narrow the date range.\n"
                    break
                yield _trade_to_csv_row(trade)
                row_count += 1
        finally:
            db.close()

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=trades_export.csv",
            "X-Row-Count": str(row_count),  # set via streaming, or omit
        }
    )
```

**Key rules:**
- The generator function `generate()` yields one CSV row at a time. Flask's `Response` with a generator iterates lazily — Python never holds the full row set in memory.
- `yield_per(500)` instructs SQLAlchemy to batch-fetch 500 rows at a time, releasing each batch after the generator advances past it.
- `max_rows` defaults to 10,000. Users can override up to 50,000. Exceeding the max appends a truncation comment to the CSV.
- Content-Disposition header forces a file download in the browser.
- The frontend trigger is a "Download CSV" button on the Performance tab that opens the URL in a new tab/window (since streaming CSV can't be fetched via `dvFetch` and rendered in-page).

### 2.4 Portfolio Overview — Multi-Currency (QA Gap 8)

```
GET /api/trading-agent/portfolio
```

**Response:**
```json
{
  "total_accounts": 3,
  "active_accounts": 2,
  "by_currency": {
    "USD": {
      "account_count": 2,
      "total_balance": 15200.00,
      "total_equity": 15350.75,
      "total_margin": 1200.00,
      "free_margin": 14150.75,
      "margin_level_pct": 1279.23,
      "open_positions": 4,
      "daily_pnl": 58.30,
      "monthly_pnl": 342.10,
      "total_pnl_r": 5.8,
      "win_rate": 0.62,
      "sharpe": 1.4,
      "max_drawdown_pct": 8.2,
      "accounts": [1, 3]
    },
    "EUR": {
      "account_count": 1,
      "total_balance": 5000.00,
      "total_equity": 5120.40,
      "total_margin": 450.00,
      "free_margin": 4670.40,
      "margin_level_pct": 1137.87,
      "open_positions": 1,
      "daily_pnl": -22.00,
      "monthly_pnl": 120.40,
      "total_pnl_r": 2.1,
      "win_rate": 0.55,
      "sharpe": 0.9,
      "max_drawdown_pct": 5.3,
      "accounts": [2]
    }
  },
  "base_currency": "USD",
  "converted_totals": null,
  "_note": "MVP — per-currency breakdown only. Cross-currency conversion is a future enhancement."
}
```

**Multi-Currency Policy (QA Gap 8):**
- Each `TradingAccount` has a `currency` field (USD, EUR, GBP, JPY, etc.).
- The portfolio endpoint **does NOT naively sum PnL across currencies**. Raw summation of USD + EUR + JPY values is mathematically meaningless.
- Instead, the response groups metrics **per currency** in the `by_currency` object.
- **MVP scope:** Show the per-currency breakdown only. No cross-currency conversion.
- **Future enhancement path:**
  1. Add a `base_currency` column to the `User` model (String(8), nullable, default `"USD"`).
  2. Maintain a hardcoded forex rate table refreshed daily from the existing `/api/prices` endpoint (which already supports forex pairs like EURUSD, GBPUSD, USDJPY).
  3. When `base_currency` is set, add a `converted_totals` block to the portfolio response that converts all currency buckets to the base currency using the latest available rate.
  4. Document that converted totals are estimates using daily close rates and may differ from real-time conversion.

### 2.5 Recompute Daily Metrics

```
POST /api/trading-agent/accounts/<id>/recompute-daily
```

**Behavior:** Rebuilds `DailyMetrics` rows for the account from its trade history. Idempotent — uses `INSERT … ON CONFLICT (account_id, date) DO UPDATE`. Returns the count of rows recomputed.

**Use case:** Manual reconciliation after a data import, bug fix, or outlier trade correction.

---

## 3. Frontend Behavior

### 3.1 XSS Sanitization (QA Gap 10)

**Policy:** ALL user-supplied text fields MUST be rendered via `textContent` or HTML-entity-escaped before any `innerHTML` interpolation. This applies to every string that originates from user input (notes, rationale, labels, tags, account_name, broker notes, trade comments, journal entries, emotion labels).

**Affected fields (non-exhaustive):**
- `TradingAccount.name`, `.nickname`, `.labels`
- `TradingJournal.notes`, `.tags`, `.emotion`, `.lesson_learned`
- `MT5Order.comment`
- `Position.ticker`, `SignalHistory.ticker` (user-input tickers)
- Any custom label or tag string entered by the user

**Implementation approach (two-tier):**

**Tier A — textContent (preferred, simpler):**
When rendering a user-supplied string into a standalone DOM element (span, div, td, etc.), assign it via `.textContent`:
```javascript
// ✅ Safe: textContent is always text, never HTML
el.textContent = trade.notes || '';
el.textContent = account.name;
```

This is the preferred approach for all cases where the rendered value is plain text with no inline formatting.

**Tier B — Escape helper (for template-literal contexts where innerHTML is required):**
For cases where the value MUST be interpolated into a larger `innerHTML` template string (e.g., building a card with mixed markup), use an escape helper:
```javascript
function _esc(s) {
    if (typeof s !== 'string') return String(s ?? '');
    return s.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
}

// Usage in innerHTML template:
el.innerHTML = `<div class="note">${_esc(trade.notes)}</div>`;
```

**Verification checklist:**
- [ ] All 296 `innerHTML` assignments audited for user-data interpolation.
- [ ] Every instance of `.notes`, `.tags`, `.name`, `.comment`, `.label` in an `innerHTML` template replaced with `_esc()` wrapping or refactored to `textContent`.
- [ ] No raw user field appears unescaped inside a template literal string assigned to `.innerHTML`.
- [ ] Backend is NOT a substitute for frontend escaping — escape at the rendering layer even if the backend sanitizes.

**Why backend-only escaping is insufficient:** The backend may store data from sources that bypass server-side validation (MT5 EA direct db writes, data migrations, admin panel). Defense in depth requires escaping at the **rendering boundary** where data transitions from storage to DOM.

### 3.2 Dashboard Widgets

The main dashboard (`#dashContent`) renders a grid of widgets on login:

| Widget | Data Source | Empty State |
|---|---|---|
| Account Selector Dropdown | `GET /api/accounts` | "No accounts — connect MT5 to get started" |
| Equity Widget | `GET /api/trading-agent/portfolio` | Equity curve with interpolation over empty days |
| P&L Card (today) | `GET /api/trading-agent/portfolio` | "No closed trades today" |
| Open Positions Table | `GET /api/accounts/<id>/summary` | "No open positions" |
| Risk Gauge | Computed from `max_drawdown_pct` | Greyed out when no data |
| Recent Trades (last 10) | `GET /api/trading-agent/trades?limit=10` | "No trades recorded yet" |

### 3.3 Equity Curve Rendering

The equity curve chart handles missing `DailyMetrics` days naturally:
- The chart x-axis is date-based (not sequential index).
- Data points exist only for days with trades (`DailyMetrics` rows exist).
- The line/area between two existing data points is drawn by the chart library (Lightweight Charts) using linear interpolation.
- Days with no trades appear as a flat segment on the chart (the line from the last trade day extends horizontally to the next trade day).

This is the correct behavior — it accurately represents that the account equity didn't change on idle days (no new PnL to move it).

---

## 4. Cross-Cutting Concerns

### 4.1 Rate Limiting
Session-authenticated routes under `/api/trading-agent/*` inherit the same tier-based rate limits as the rest of the API:
- Free tier: 10 req/min
- Pro tier: 60 req/min
- Elite tier: 300 req/min

The CSV export endpoint is excluded from strict rate limiting (one export per minute per user) due to the streaming nature of the response.

### 4.2 Audit Trail
Every mutation on `TradingAccount` (create, update, archive) writes an audit log entry (future workstream — not in MVP scope but the archive endpoint is designed to emit an audit event via SSE).

### 4.3 Error Handling
All endpoints return structured JSON errors:
```json
{
  "error": true,
  "code": "ACCOUNT_NOT_FOUND",
  "message": "Account #42 does not exist or has been archived."
}
```

Never return HTML error pages from `/api/trading-agent/*` routes (consistent with the global `handle_any_exception` handler in `app.py:97`).

---

## 5. Database Migration Plan

| Migration | Action |
|---|---|
| `daily_metrics` table | `CREATE TABLE` — new |
| `trading_accounts.deleted_at` | `ALTER TABLE ADD COLUMN` — nullable, no default |
| `trading_accounts.nickname` | `ALTER TABLE ADD COLUMN` — nullable, no default |
| `trading_accounts.labels` | `ALTER TABLE ADD COLUMN` — nullable `TEXT` |
| `users.base_currency` | `ALTER TABLE ADD COLUMN` — `VARCHAR(8)`, nullable, default `'USD'` (future enhancement) |

All migrations are additive — no column drops, no destructive changes. Rollback is safe.

---

## 6. QA Gap Resolution — Summary

| Gap | Issue | Resolution | Section |
|---|---|---|---|
| **5** | DailyMetrics on idle days | Only create rows when ≥1 closed trade. No zero-trade gap-filler rows. Equity curve uses interpolation across missing dates. | §1.2, §3.3 |
| **6** | CSV export memory for 10k+ trades | Streaming `Response(generate(), mimetype='text/csv')` with `yield_per(500)`. `max_rows` param (default 10k, max 50k). Never loads full result set into memory. | §2.3 |
| **7** | Account deletion with trade history | Soft-delete via `deleted_at` timestamp. Trades, journal entries, and DailyMetrics preserved. `PATCH /api/trading-agent/accounts/<id>/archive`. Dashboard filters archived accounts by default. | §1.1, §2.1 |
| **8** | Multi-currency combined PnL | Portfolio endpoint returns `by_currency` breakdown. No naive cross-currency sum. MVP: per-currency only. Future: `base_currency` on User model with forex rate conversion. | §2.4 |
| **10** | XSS via innerHTML | ALL user-supplied text rendered via `textContent` (Tier A) or HTML-entity-escaped via `_esc()` helper before innerHTML interpolation (Tier B). Defense in depth at the rendering boundary. | §3.1 |

---

## 7. Implementation Order (Recommended)

1. **Data model changes** — Add `deleted_at`, `nickname`, `labels` to `TradingAccount`. Create `DailyMetrics` table.
2. **Archive endpoint** — `PATCH /api/trading-agent/accounts/<id>/archive`.
3. **DailyMetrics computation** — `_compute_daily_metrics()` with idle-day policy. Recompute endpoint.
4. **Portfolio endpoint** — Multi-currency `GET /api/trading-agent/portfolio`.
5. **Trade unified view + CSV export** — `GET /api/trading-agent/trades` and `GET /api/trading-agent/trades/export` with streaming.
6. **Frontend XSS audit** — Retrofit all user-data `innerHTML` interpolations with `_esc()` or `textContent`.
7. **Dashboard widgets** — UI components wired to the new endpoints.
8. **base_currency (future)** — Add to User model, implement conversion table.
