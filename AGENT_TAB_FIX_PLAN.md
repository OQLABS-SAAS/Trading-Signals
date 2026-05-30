# AGENT_TAB_FIX_PLAN.md — DotVerse Agent Tab Remediation Plan

**Document Type:** Systems Architecture / Build Plan
**Date:** 2026-05-30
**Status:** Pre-implementation design
**Target Repository:** `/Users/oq/Documents/trading-signals-saas/`

---

## Executive Summary

The Agent tab (recently delivered per `agent-tab-design-plan.md`) has three material defects that prevent production readiness:

1. **MT5 Account Recognition Failure:** All Agent tab backend endpoints query `TradingAccount.user_id` using only the logged-in session ID. The MT5 EA (Expert Advisor) pushes account state under `user_id="default"`, so any account connected via the EA is invisible to the Agent tab. The existing watch engine and `mt5_get_state` already handle this correctly with a dual-ID fallback — the Agent tab endpoints do not.

2. **Fake PnL Generation:** When `today_pnl` is absent from a `TradingAccount` row, the dashboard generates a random value (`random.uniform(-50, 150)` at line 18383). This violates the zero-fake-data principle and displays fabricated performance numbers to users.

3. **Performance Dashboard vs Agent Tab Boundary:** The BUILD_PLAN.md Performance Dashboard (P4) and the Agent tab Reports share overlapping domains (PnL, win rate, Sharpe) but draw from different data sources. Without documented boundaries, future development risks duplicating work or presenting conflicting numbers.

This plan documents the root cause of each issue with line-number evidence, proposes concrete fixes with file paths, defines implementation order, and provides acceptance criteria so each fix can be QA'd independently.

---

## Issue 1: Agent Tab Doesn't Recognize MT5-Connected Users

### 1.1 Root Cause Analysis

**The EA Push Pattern:**
The `mt5_push_state()` endpoint (line 8910–8958) receives MT5 account data from the EA and stores it in the in-memory `mt5_state` dict:

```python
# app.py line 8913
user_id = body.get("user_id", "default")
...
mt5_state[user_id] = { ... }   # line 8950
```

The EA always sends `user_id="default"` because it authenticates via `ea_secret_enc`, not via session login. Human users logging in via the web app have their own `user_id` (e.g., `"user_abc123"`). This means the EA's accounts sit in `mt5_state["default"]` while the logged-in user's DB query looks for `TradingAccount.user_id == "user_abc123"`.

**Existing Correct Patterns (Reference Implementation):**

The watch engine and the `mt5_get_state` endpoint already handle this dual-ID problem correctly:

- **Watch engine — line 5704:** `_z_uid = w.get("user_id", "default")` then `mt5_state.get(str(_z_uid)) or mt5_state.get("default", {})` (line 5708)
- **Watch engine — line 5795:** `cfg = _get_automation_settings(w.get("user_id", "default"))`
- **Watch engine — line 5804+:** `uid_str = str(w.get("user_id", "default"))` then `state = mt5_state.get(uid_str) or mt5_state.get("default", {})` with explicit comment "Bug Y fix: EA always pushes to mt5_state['default']" (lines 5804–5809)
- **Watch engine — line 5972:** `_tp_uid = str(w.get("user_id", "default"))`
- **`mt5_get_state` — line 8966:** `state = mt5_state.get(user_id) or mt5_state.get("default")`

**The Bug:** The Agent tab endpoints query only the session user's ID against `TradingAccount.user_id` with no fallback to `"default"`.

### 1.2 Affected Code — Complete Inventory

All of the following Agent tab endpoints have the same single-ID query pattern and need the dual-ID fix. Each also has a secondary acct_map query that needs the same treatment.

| # | Endpoint | Line | Current Pattern | Issue |
|---|----------|------|-----------------|-------|
| 1 | `GET /api/trading-agent/dashboard` | 18331–18332 | `TradingAccount.user_id == user_id` | EA accounts invisible |
| 2 | `GET /api/trading-agent/positions` | 18449–18451 | `TradingAccount.user_id == user_id` (join) | EA accounts invisible |
| 3 | `GET /api/trading-agent/trades` | 18510–18513 | `TradingAccount.user_id == user_id` (join) | EA accounts invisible |
| 4 | `GET /api/trading-agent/trades/export` | 18637–18640 | `TradingAccount.user_id == user_id` (join) | EA accounts invisible |
| 5 | `GET /api/trading-agent/trades/<id>` | 18702–18704 | `TradingAccount.user_id == user_id` (join) | EA accounts invisible |
| 6 | `PUT /api/trading-agent/trades/<id>` | 18738–18741 | `TradingAccount.user_id == user_id` (join) | EA accounts invisible |
| 7 | `GET /api/trading-agent/analytics` | 18800–18801 | `TradingAccount.user_id == user_id` | EA accounts invisible |
| 8 | `GET /api/trading-agent/portfolio` | 18905–18907 | `TradingAccount.user_id == user_id` | EA accounts invisible |
| 9 | `POST /api/trading-agent/accounts/<id>/archive` | 18964–18967 | `TradingAccount.user_id == user_id` | Can't archive EA accounts |
| 10 | `POST /api/trading-agent/accounts/<id>/sync` | ~18993+ | `TradingAccount.user_id == user_id` | Can't sync EA accounts |
| 11 | `GET /api/trading-agent/accounts/<id>/daily-metrics` | ~19030+ | `TradingAccount.user_id == user_id` | EA account metrics invisible |
| 12 | `POST /api/trading-agent/accounts/<id>/recompute-daily` | ~19082+ | `TradingAccount.user_id == user_id` | Can't recompute EA accounts |
| 13 | `POST /api/trading-agent/accounts` / `/connect` | ~19150+ | `TradingAccount.user_id == user_id` | New account ownership |
| 14 | `POST /api/trading-agent/trades` | 18577–18581 | `TradingAccount.user_id == user_id` | Can't create trades on EA accounts |

Additionally, each endpoint's **acct_map secondary query** (e.g., lines 18458–18460, 18532–18534, 18649–18651) also uses the same single-ID filter and needs the fix.

### 1.3 Proposed Solution

**Approach: Unified User-ID Resolution Helper**

Create a single helper function that all Agent tab endpoints call to resolve the valid set of user IDs to query against. This avoids repeating the dual-ID logic 14+ times and ensures consistency with the watch engine.

```python
# Insert after _agent_rate_limit (around line 679) or near the agent endpoints

def _agent_user_ids():
    """Return tuple of (session_user_id, fallback_user_ids) for Agent tab queries.
    """
    user_data = session.get("user_id")
    if user_data is None:
        user_data = session.get("user_email", session.get("authenticated", False))
        if user_data is True:
            user_data = "default"
        elif user_data is False or user_data is None:
            user_data = "default"
    session_uid = str(user_data)
    # Always include "default" as fallback — the EA pushes MT5 state
    # under user_id="default" regardless of which human user logged in.
    ids = [session_uid]
    if session_uid != "default":
        ids.append("default")
    return session_uid, ids
```

Then replace `TradingAccount.user_id == user_id` patterns with `TradingAccount.user_id.in_(ids)`. The filter also needs to handle `is_active == True`.

**Per-Endpoint Changes (app.py):**

For each endpoint, the pattern changes from:

```python
# BEFORE (single-ID)
accounts = db.query(TradingAccount).filter(
    TradingAccount.user_id == user_id,
    TradingAccount.is_active == True,
).all()
```

To:

```python
# AFTER (dual-ID)
session_uid, query_ids = _agent_user_ids()
accounts = db.query(TradingAccount).filter(
    TradingAccount.user_id.in_(query_ids),
    TradingAccount.is_active == True,
).all()
```

For joined queries (e.g., trades, positions):

```python
# BEFORE
query = db.query(AgentTrade).join(TradingAccount).filter(
    TradingAccount.user_id == user_id,
    TradingAccount.is_active == True,
)

# AFTER
query = db.query(AgentTrade).join(TradingAccount).filter(
    TradingAccount.user_id.in_(query_ids),
    TradingAccount.is_active == True,
)
```

For the `acct_map` secondary queries:

```python
# BEFORE
acct_map = {a.id: a.name for a in db.query(TradingAccount).filter(
    TradingAccount.user_id == user_id
).all()}

# AFTER
acct_map = {a.id: a.name for a in db.query(TradingAccount).filter(
    TradingAccount.user_id.in_(query_ids)
).all()}
```

### 1.4 Handling Missing TradingAccount Rows

**Scenario:** The EA is actively pushing MT5 data to `mt5_state["default"]` but no `TradingAccount` row has been created yet (user hasn't onboarded their MT5 account through the Agent tab UI).

**Proposed handling in `agent_dashboard()`:**

Before the DB query, check `mt5_state` for live data. If it exists but no `TradingAccount` rows match, surface the live data directly:

```python
# Check mt5_state for EA data without a matching TradingAccount row
with mt5_state_lock:
    ea_state = mt5_state.get("default", {})

if not accounts and ea_state:
    # Surface live MT5 data even without a TradingAccount row
    ea_account = ea_state.get("account", {})
    ea_positions = ea_state.get("positions", [])
    # Create a synthetic account entry for the frontend
    # Mark it with needs_onboarding=True so UI can prompt user
    synthetic = {
        "id": None,
        "name": "MT5 (Pending Setup)",
        "needs_onboarding": True,
        "balance": float(ea_account.get("balance", 0)),
        "equity": float(ea_account.get("equity", 0))
            or float(ea_account.get("balance", 0)),
        "positions": ea_positions,
        ...
    }
```

### 1.5 MT5 State Data to Surface in Agent Tab

The following fields from `mt5_state` should be surfaced by the Agent dashboard:

| mt5_state Field | Agent Tab Usage |
|----------------|-----------------|
| `account.balance` | Account balance card |
| `account.equity` | Account equity card |
| `account.margin` | Margin used (risk indicator) |
| `account.free_margin` | Available margin |
| `account.margin_level` | Margin level % |
| `account.leverage` | Account leverage |
| `account.name` | Account holder name |
| `account.server` | Broker server |
| `positions[]` (each has `symbol`, `type`, `volume`, `open_price`, `current_price`, `profit`, `swap`, `comment`) | Open positions table, unrealized PnL |
| `last_seen` | Connection status indicator |
| `spreads` | Spread monitoring (from Phase 1.2) |
| `spread_warning` | Warning flag for abnormal spreads |

### 1.6 Frontend Changes

**File:** `static/index-v2-prototype.html`

The Agent tab frontend currently calls these endpoints and renders the responses. The contract changes slightly:

- Accounts returned may now have `needs_onboarding: true` (synthetic EA accounts without DB rows)
- The frontend should render these accounts with a distinct visual treatment: ghosted/greyed card with a "Complete Setup" button that opens the `/connect` flow
- The `account_id` for synthetic accounts will be `None` — frontend must guard against passing `None` to endpoints that require a numeric `account_id`

Define the visual treatment in the design tokens:

```css
/* Synthetic / Pending-Onboarding Account Card */
.agent-account-card.pending {
    border: 1px dashed var(--gold-bord);
    background: var(--s1);
    opacity: 0.7;
}
.agent-account-card.pending:hover {
    opacity: 1;
    border-color: var(--gold);
}
```

---

## Issue 2: Fake PnL Generation

### 2.1 Root Cause

**Line 18383 of app.py:**

```python
# Generate today_pnl from recent trades if not in model
today_pnl = getattr(a, 'today_pnl', None)
if today_pnl is None:
    today_pnl = round(random.uniform(-50, 150), 2)   # <-- FAKE DATA
```

The `TradingAccount` model (line 14688–14707) does not have a `today_pnl` column. There is no column for daily PnL on the accounts table. The `AgentDailyMetrics` model (line 14739) has a `pnl` column scoped to `(account_id, date)`, but the dashboard does not query it.

The `getattr(a, 'today_pnl', None)` always returns `None`, making the fake-random branch fire for **every account every time** the dashboard loads.

### 2.2 Proposed Solution

**Policy: Zero Fake Data.** Never display fabricated numbers. If real data is unavailable, display `--` or "N/A" with a clear visual difference from real numbers.

**Recommended Approach — Three-Tier Fallback:**

| Priority | Data Source | Query | When Available |
|----------|------------|-------|----------------|
| **1 (Best)** | `AgentDailyMetrics.pnl` for today's date | `SELECT pnl FROM agent_daily_metrics WHERE account_id=? AND date=CURRENT_DATE` | After a daily recompute has run |
| **2 (Good)** | `mt5_state` balance delta | `current_balance - balance_at_midnight` (requires storing a midnight snapshot, or computing from `AgentDailyMetrics.starting_balance` if it exists) | When EA is connected and pushing |
| **3 (Fallback)** | `AgentTrade` realized PnL for today | `SELECT SUM(realized_pnl) FROM agent_trades WHERE account_id=? AND exit_time >= TODAY AND status='CLOSED'` | Always available if trades were closed today |
| **4 (Display)** | Show `--` or "N/A" | None | When no real data source is available |

**Implementation in `agent_dashboard()`:**

```python
# Compute today_pnl from real sources, never random
today_pnl = None

# Tier 1: AgentDailyMetrics
daily_row = db.query(AgentDailyMetrics).filter(
    AgentDailyMetrics.account_id == a.id,
    AgentDailyMetrics.date == datetime.utcnow().date(),
).first()
if daily_row and daily_row.pnl is not None:
    today_pnl = round(daily_row.pnl, 2)

# Tier 2: mt5_state balance delta
if today_pnl is None:
    with mt5_state_lock:
        state = mt5_state.get("default", {})
        acct_data = state.get("account", {})
    if acct_data:
        current_balance = float(acct_data.get("balance", 0) or 0)
        # If AgentDailyMetrics has starting_balance, use delta
        if daily_row and daily_row.starting_balance is not None:
            today_pnl = round(current_balance - daily_row.starting_balance, 2)

# Tier 3: AgentTrade realized PnL for today
if today_pnl is None:
    today_trades = db.query(
        func.coalesce(func.sum(AgentTrade.realized_pnl), 0)
    ).filter(
        AgentTrade.account_id == a.id,
        AgentTrade.status == "CLOSED",
        func.date(AgentTrade.exit_time) == datetime.utcnow().date(),
    ).scalar()
    if today_trades:
        today_pnl = round(float(today_trades), 2)

# Tier 4: None — frontend will render as "--" or "N/A"
```

**Frontend Handling:**

```javascript
// Render today_pnl
if (entry.today_pnl === null || entry.today_pnl === undefined) {
    // "N/A" state: muted text, no color
    return '<span class="pnl-na">--</span>';
}
// Real value: green/red colored
const cls = entry.today_pnl >= 0 ? 'pnl-positive' : 'pnl-negative';
const sign = entry.today_pnl >= 0 ? '+' : '';
return `<span class="${cls}">${sign}$${Math.abs(entry.today_pnl).toFixed(2)}</span>`;
```

**CSS:**

```css
.pnl-na { color: var(--t3); font-style: italic; }
.pnl-positive { color: var(--grn); }
.pnl-negative { color: var(--red); }
```

### 2.3 Removing the `random` Import

If `import random` is only used for the fake PnL line (it may be used elsewhere in the 19K-line file), it should be verified and removed. If other uses exist, the import stays but the fake-PnL usage is deleted.

**Check:** Search `app.py` for `random.uniform` and `random.randint` / `random.choice`. If line 18383 is the only `random.uniform` call, the `import random` at line 18363 can be removed. If other legitimate uses exist (e.g., in Monte Carlo simulation), the import stays.

---

## Issue 3: Performance Dashboard vs Agent Tab — Boundary Definition

### 3.1 The Overlap Problem

The BUILD_PLAN.md (Section 4, Priority 4) specifies a Performance Dashboard with equity curve, Sharpe ratio, drawdown chart, and monthly heatmap — all sourced from `SignalHistory` data. These are signal analytics: "how good is the signal engine?"

The Agent tab has its own analytics endpoint (`GET /api/trading-agent/analytics`, line 18779) that computes win rate, profit factor, total PnL, Sharpe, and equity curve from `AgentTrade` data. These are trade analytics: "how much money did the trader make?"

Both could show "Sharpe ratio" and "equity curve" but computed from different datasets, producing different numbers. Without documentation, future developers may:
- Implement the Performance Dashboard and accidentally duplicate the Agent analytics
- Show two different "Sharpe ratios" on two different tabs, confusing users
- Query the wrong data source for the wrong metric

### 3.2 Clear Boundaries

| Dimension | Performance Dashboard | Agent Tab Reports |
|-----------|----------------------|-------------------|
| **Tab Location** | PERFORMANCE tab (`showPerformance()`) | AGENT tab |
| **Data Source** | `SignalHistory` table | `AgentTrade` + `TradingAccount` + `AgentDailyMetrics` tables |
| **Unit of Analysis** | Signal quality (per-signal) | Trade performance (per-account, per-trader) |
| **Primary Audience** | Signal strategy developers | Account managers / traders |
| **Equity Curve** | Cumulative R-multiples from signal outcomes (`actual_pnl_r`) — normalized, no dollar amounts | Cumulative dollar PnL from trade `realized_pnl` — absolute dollar values |
| **Sharpe Ratio** | From R-multiple returns (signal-level) | From dollar PnL returns (account-level) |
| **Win Rate** | Signal outcome WIN/LOSS rate | Trade outcome WIN/LOSS rate |
| **Profit Factor** | Gross win R / gross loss R | Gross win $ / gross loss $ |
| **Drawdown** | Peak-to-trough in R-multiple equity curve | Peak-to-trough in dollar equity curve |
| **Heatmap** | Monthly R-multiple returns matrix | Not applicable (or: monthly dollar PnL matrix) |
| **Unique Metrics** | Signal confidence calibration curve, expectancy per pattern, regime breakdown | Account balances, margin usage, client P&L, connection status, trade duration |
| **API Endpoints** | `/api/signals/performance-metrics` (to be built — currently a TODO in BUILD_PLAN 4.1–4.4) | `/api/trading-agent/analytics`, `/api/trading-agent/dashboard`, `/api/trading-agent/accounts/<id>/daily-metrics` (already built) |

### 3.3 How They Complement Each Other

**Performance Dashboard — "Is my strategy good?"**
- Answers: Are my signals profitable in aggregate? What's my expectancy per signal? Does my win rate vary by pattern or regime? Am I improving over time?
- Uses normalized R-multiples so performance is comparable across accounts of different sizes.

**Agent Tab Reports — "Am I making money?"**
- Answers: What's my total PnL across all connected accounts? Which account is performing best? What's my current exposure? Are any accounts in drawdown danger?
- Uses absolute dollar amounts so traders see real monetary results.

**The handshake:** A trader uses the Performance Dashboard to validate their signal strategy, then uses the Agent Tab to execute and monitor actual trades. The Agent tab shows whether real execution matches signal expectations (slippage, missed entries, different position sizing).

### 3.4 Documentation for the BUILD_PLAN.md

Add a new section to BUILD_PLAN.md after the existing Priority 4 section:

```markdown
## PRIORITY 4b — Performance Dashboard vs Agent Tab Boundary

| Concern | Performance Dashboard | Agent Tab |
|---|---|---|
| Data source | SignalHistory | AgentTrade + TradingAccount |
| Currency | R-multiples (normalized) | Dollar amounts (absolute) |
| Purpose | Strategy validation | Trade/account monitoring |
| Sharpe source | R-multiple returns | Dollar PnL returns |
| Equity curve | Cumulative R | Cumulative $ |

**Rule:** Never compute the same metric from both sources on the same tab. If a metric appears on both tabs, clearly label the source.
```

---

## Implementation Order

### Phase 1: Remove Fake Data (Highest Priority — 30 min)

**Rationale:** This is a one-line fix with zero architectural risk. Fake numbers erode user trust and should be removed immediately.

1. Delete line 18383 (`today_pnl = round(random.uniform(-50, 150), 2)`)
2. Replace with `today_pnl = None` (or the three-tier fallback described in §2.2)
3. Verify `random` import can be removed from line 18363 (check for other uses)
4. Update frontend to render `null` as `--`
5. QA: Load Agent dashboard — PnL column shows `--` for accounts without real data, never a random number

### Phase 2: Fix MT5 Account Recognition (Core Fix — 2–3 hours)

**Rationale:** This is the blocking issue. Without it, EA-connected accounts are completely invisible.

1. Create `_agent_user_ids()` helper function near the existing `_agent_rate_limit` decorator
2. Update all 14+ endpoints (see §1.2 inventory) to use `TradingAccount.user_id.in_(query_ids)`
3. Update all `acct_map` secondary queries
4. Add synthetic account handling for EA data without DB rows in `agent_dashboard()`
5. Test with:
   - No EA connected → only session-user accounts shown (regression check)
   - EA connected with `user_id="default"` → EA accounts appear alongside session accounts
   - EA pushing but no TradingAccount row → synthetic entry with onboarding prompt

### Phase 3: Frontend Updates (1–2 hours)

**Rationale:** The frontend must handle the new data shapes: `today_pnl: null`, `needs_onboarding: true`, dual-ID accounts.

1. Update `--`/N/A rendering for null `today_pnl`
2. Add "Pending Setup" card style for synthetic accounts
3. Wire "Complete Setup" button to the `/connect` flow
4. Guard against `account_id: null` in downstream API calls

### Phase 4: BUILD_PLAN.md Boundary Documentation (15 min)

**Rationale:** Prevent future overlap.

1. Add Performance Dashboard vs Agent Tab boundary section
2. Document data source for each metric

---

## Dependencies and Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Dual-ID queries return accounts the user shouldn't see | Low | High | The `TradingAccount` rows with `user_id="default"` are created when the EA connects — these are the user's own accounts. The EA secret (`ea_secret_enc`) is unique per account. Cross-user leakage is not possible because only one EA instance connects per account. |
| `_agent_user_ids()` changes query performance | Low | Low | Adding `IN (?, ?)` instead of `= ?` adds negligible overhead. The `user_id` column is already indexed (line 14691: `index=True`). |
| Frontend breaks on `today_pnl: null` | Medium | Medium | Audit all frontend code that reads `today_pnl` from dashboard response. Add null guards. |
| Removing `random` import breaks other code | Low | Low | Verify before removing. If other uses exist, keep the import and only delete the fake-PnL line. |
| Synthetic accounts cause N+1 UI bugs | Medium | Low | Limit synthetic entries to one per EA instance. Clear visual treatment prevents confusion with real accounts. |

---

## Acceptance Criteria

### Issue 1: MT5 Recognition

- [ ] **AC1.1:** When an EA pushes MT5 data with `user_id="default"`, the Agent dashboard shows the account alongside accounts with the session user's ID
- [ ] **AC1.2:** The dashboard's `total_accounts`, `online_accounts`, `total_balance`, and `total_equity` fields include EA-connected accounts
- [ ] **AC1.3:** All 14 Agent tab endpoints (dashboard, positions, trades, trades/export, trade detail, trade update, analytics, portfolio, archive, sync, daily-metrics, recompute-daily, connect, create-trade) accept accounts with either the session user ID or `"default"`
- [ ] **AC1.4:** If the EA is pushing but no `TradingAccount` row exists, the dashboard returns a synthetic account entry with `needs_onboarding: true`
- [ ] **AC1.5:** Existing behavior is preserved when no EA is connected — session-user-only accounts still work

### Issue 2: Fake PnL

- [ ] **AC2.1:** `random.uniform()` is never called in the Agent dashboard code path
- [ ] **AC2.2:** When real PnL data is available (from `AgentDailyMetrics`, `mt5_state`, or `AgentTrade`), it is displayed
- [ ] **AC2.3:** When no real PnL data is available, the frontend renders `--` (not a random number, not $0.00)
- [ ] **AC2.4:** The `--` placeholder is visually distinct from real numbers (muted color, italic)

### Issue 3: Dashboard Boundaries

- [ ] **AC3.1:** BUILD_PLAN.md contains a documented boundary between Performance Dashboard and Agent tab
- [ ] **AC3.2:** The data source for each metric is documented (SignalHistory vs AgentTrade)
- [ ] **AC3.3:** No metric is ambiguously defined across both tabs without a documented source

---

## Files Changed (Summary)

| File | Change | Lines Affected |
|------|--------|---------------|
| `app.py` | Add `_agent_user_ids()` helper | ~15 new lines near line 679 |
| `app.py` | Fix 14 Agent endpoints to use dual-ID query | ~50 lines modified across endpoints |
| `app.py` | Add synthetic account handling in `agent_dashboard()` | ~30 new lines after line 18334 |
| `app.py` | Remove fake PnL, add three-tier fallback | Lines 18363, 18380–18383 replaced |
| `app.py` | Remove `import random` (if no other uses) | Line 18363 removed |
| `static/index-v2-prototype.html` | Add `--` rendering for null `today_pnl` | ~10 lines in Agent tab render |
| `static/index-v2-prototype.html` | Add pending-onboarding card style | ~5 lines CSS + ~10 lines JS |
| `BUILD_PLAN.md` | Add Performance Dashboard vs Agent Tab boundary section | ~20 new lines |

---

## Appendix A: Full Endpoint Modification Template

For reference during implementation, here is the complete pattern each endpoint should follow:

```python
@app.route("/api/trading-agent/<endpoint>", methods=["GET"])
@login_required
@_agent_rate_limit(60)
def agent_<endpoint>():
    if not _DBSession:
        return jsonify({"error": "db unavailable"}), 503

    # Use unified helper — returns (session_uid, [session_uid, "default"])
    session_uid, query_ids = _agent_user_ids()
    db = _DBSession()
    try:
        # PRIMARY QUERY — use .in_() for dual-ID support
        accounts = db.query(TradingAccount).filter(
            TradingAccount.user_id.in_(query_ids),
            TradingAccount.is_active == True,
        ).all()
        account_ids = [a.id for a in accounts]

        # ... endpoint logic ...

        # SECONDARY acct_map — also use .in_()
        acct_map = {a.id: a.name for a in db.query(TradingAccount).filter(
            TradingAccount.user_id.in_(query_ids)
        ).all()}

        return jsonify({...})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
```

---

## Appendix B: Verification Script (Post-Implementation)

```bash
# 1. Verify no more fake PnL
grep -n "random.uniform" app.py | grep -v "#"

# 2. Verify all agent endpoints use dual-ID
grep -n "TradingAccount.user_id ==" app.py | grep -A1 "agent_"

# 3. Verify mt5_state fallback exists in dashboard
grep -n "mt5_state" app.py | grep -A2 "agent_dashboard"

# 4. Count endpoints that need fixing (should return 0 after fix)
grep -c "TradingAccount.user_id == user_id" app.py
```
