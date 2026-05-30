# QA Review: AGENT_TAB_FIX_PLAN.md — Edge Cases, Corner Cases, and Failure Modes

**Reviewer:** Hermes Agent (automated QA pass)
**Date:** 2026-05-30
**Status:** Pre-implementation design review
**Source Document:** `/Users/oq/Documents/trading-signals-saas/AGENT_TAB_FIX_PLAN.md` (545 lines)
**Code Under Review:** `app.py` (19,199 lines) + `static/index-v2-prototype.html` (25,440 lines)

---

## Summary

The plan correctly identifies three root problems and proposes a coherent architecture for remediation. **However, 14 distinct edge cases, corner cases, and failure modes were found** — including 1 HIGH severity security concern, 2 MEDIUM severity frontend mismatches, and several correctness gaps in the three-tier PnL fallback logic.

---

## Risk Matrix

| # | Finding | Severity | Phase | New Code Required? |
|---|---------|----------|-------|--------------------|
| 1 | Archive/sync endpoints allow cross-user mutation of `"default"` accounts | **HIGH** | Phase 2 | Yes (mitigation) |
| 2 | Frontend hardcodes `pnlVal = 0`; never reads API `today_pnl` | **HIGH** | Phase 3 | Yes |
| 3 | Tier 3 PnL query conflates "no trades" with "net zero PnL" | **MEDIUM** | Phase 1 | Yes |
| 4 | Multiple DB accounts sharing `user_id="default"` get identical PnL | **MEDIUM** | Phase 1-2 | No (design note) |
| 5 | Synthetic `id: null` breaks `_agentClientData` key-based access | **MEDIUM** | Phase 3 | Yes |
| 6 | `_agent_user_ids()` fallback chain over-engineered for `@login_required` | **LOW** | Phase 2 | Optional |
| 7 | Tier 2 balance delta vulnerable to EA push race condition | **LOW** | Phase 1 | Design note |
| 8 | `datetime.utcnow()` is deprecated in Python 3.12 | **LOW** | Phase 1-2 | Optional (migration) |
| 9 | Per-account N+1 DB queries; 2 extra queries per account per dashboard load | **LOW** | Phase 1 | Optional (batch) |
| 10 | Analytics endpoint (endpoint 7) uses list-based filter; plan notes but no template | **LOW** | Phase 2 | Yes |
| 11 | `import random` at line 18355 inside for-loop is sloppy | **LOW** | Phase 1 | Already covered |
| 12 | Frontend positions/history fetch without `account_id` filter | **LOW** | Phase 3 | Existing behavior |
| 13 | `user_id` type mismatch risk: `session["user_id"]` vs `TradingAccount.user_id` column | **LOW** | Phase 2 | Already OK |
| 14 | 16 SQL patterns need fixing, not 14 endpoints | **INFO** | Phase 2 | Verified |

---

## Detailed Findings

### Finding 1: ARCHIVE/SYNC SECURITY — Cross-User Mutation of "default" Accounts (HIGH)

**Lines affected:** app.py 18877-19042 (agent_archive_account, agent_sync_account, agent_daily_metrics, agent_recompute_daily)

**Root cause:** After the dual-ID fix, endpoints 9-12 check ownership via `TradingAccount.user_id.in_([session_uid, "default"])`. Any logged-in user can now archive, sync, recompute metrics, or view daily-metrics for accounts with `user_id="default"`.

**Scenario:**
1. User A connects their MT5 EA — creates `TradingAccount(id=1, user_id="default", name="User A's Acct")`
2. User B logs into the web app — the dual-ID query returns account 1 alongside User B's own accounts
3. User B navigates to the accounts tab and archives account 1
4. User A's EA data disappears

**The plan's risk assessment (line 443-444) claims:** *"Cross-user leakage is not possible because only one EA instance connects per account."* This is correct for *mt5_state* (in-memory) but **incorrect for TradingAccount rows** — these persist in the DB and are shared by all users with `user_id="default"`.

**Recommended mitigation:**
1. For **read** endpoints (dashboard, positions, trades, analytics, portfolio, daily-metrics): The dual-ID `.in_()` is correct — reading EA accounts is the whole point.
2. For **write/mutate** endpoints (archive, sync, recompute-daily, create-trade, update-trade): After finding the account with `.in_()`, add a secondary ownership check:
   ```python
   # After finding the account via dual-ID query
   if acct.user_id == "default" and acct.user_id != session_uid:
       return jsonify({"error": "Cannot modify shared EA account"}), 403
   ```
   Or alternatively: scope the write back to the session user only if the account is owned by `"default"`.

3. Alternatively: When the EA creates/generates a `TradingAccount` row, use a unique non-"default" key (like the `ea_secret_enc` hash) as the user_id, and map session users to that via a join table. This is a larger architectural change.

**Severity rationale:** For a single-user deployment this is harmless. For multi-user SaaS, this is a data integrity issue where User B can destroy User A's data. If the EA data is per-installation (one EA per deployment), the risk is minimal but should be documented.

---

### Finding 2: FRONTEND IGNORES API `today_pnl` — Hardcoded to `0` (HIGH)

**Lines affected:** `static/index-v2-prototype.html` line 7678

**Current code:**
```javascript
var pnlVal = 0; // Real P&L comes from API data when available
```

The backend already sends `today_pnl` in the dashboard response for each account (app.py line 18394: `"today_pnl": today_pnl`), but the frontend **never reads it**. The `a.today_pnl` field from the API is available in the `_agentClientData` object but is completely ignored.

**Impact:** Even after Phase 1 removes the fake random PnL and implements the three-tier fallback, the frontend will still show `Today: +$0.00` for every account. The backend fix alone is insufficient.

**Required fix (not in the plan):** Change line 7678 from:
```javascript
var pnlVal = 0; // Real P&L comes from API data when available
```
To:
```javascript
var pnlVal = (a.today_pnl != null) ? Number(a.today_pnl) : null;
var pnlSign = pnlVal != null ? (pnlVal >= 0 ? '+' : '') : '';
var pnlColor = pnlVal != null ? (pnlVal >= 0 ? 'var(--grn)' : 'var(--red)') : 'var(--t3)';
var pnlDisplay = pnlVal != null ? (pnlSign + '$' + Math.abs(pnlVal).toFixed(2)) : '--';
```

And update line 7683 accordingly.

---

### Finding 3: Tier 3 PnL Query — "No Trades" vs "Net Zero PnL" Conflation (MEDIUM)

**Plan section:** §2.2, Tier 3 (lines 291-301 of the plan)

**Problem:** The plan's Tier 3 code uses:
```python
today_trades = db.query(
    func.coalesce(func.sum(AgentTrade.realized_pnl), 0)
).filter(...).scalar()
if today_trades:
    today_pnl = round(float(today_trades), 2)
```

`func.coalesce(func.sum(...), 0).scalar()` returns `0` when no trades match (SQL returns NULL, coalesce converts to 0). But Python `0` is falsy, so `if today_trades:` is `False`. This correctly avoids setting today_pnl when there are no trades.

**BUT:** If there ARE trades today and the net PnL is exactly `0.00` (possible — e.g., one +$50 trade and one -$50 trade), the scalar() returns `0` or `0.0`, which is ALSO falsy. The code would skip setting today_pnl, leaving it as `None`. The frontend would then show `--` instead of `$0.00`.

**Fix:** Use a two-step approach:
```python
# Check if any closed trades exist today
has_trades_today = db.query(AgentTrade).filter(
    AgentTrade.account_id == a.id,
    AgentTrade.status == "CLOSED",
    func.date(AgentTrade.exit_time) == datetime.utcnow().date(),
).first() is not None

if has_trades_today:
    today_sum = db.query(
        func.coalesce(func.sum(AgentTrade.realized_pnl), 0.0)
    ).filter(
        AgentTrade.account_id == a.id,
        AgentTrade.status == "CLOSED",
        func.date(AgentTrade.exit_time) == datetime.utcnow().date(),
    ).scalar()
    today_pnl = round(float(today_sum or 0), 2)
```

**Alternative:** Use `is not None` check on the non-coalesced query, but this adds complexity. The two-step approach is clearer.

---

### Finding 4: Multiple Accounts Sharing `user_id="default"` Get Identical PnL (MEDIUM)

**Scenario:** If two TradingAccount rows exist with `user_id="default"` (both created during EA onboarding), the Tier 2 PnL calculation (balance delta from `mt5_state["default"]`) would produce the **exact same today_pnl for both accounts**, which is misleading.

**Why this happens:** `mt5_state` is keyed by user_id (a single string "default"), and each entry has exactly one `account` sub-dict. Two TradingAccount rows mapped to the same `user_id="default"` share one `mt5_state` entry. The balance delta will be identical even if the accounts represent different MT5 terminals.

**Mitigation:** 
- Document this as a known limitation in the design doc.
- In Phase 1, the Tier 2 code should only apply the mt5_state delta if there is exactly ONE TradingAccount row with `user_id="default"` visible to the current user, OR if the mt5_state account data includes an `account_id` field that can be matched.
- For multi-account EA setups, users should create accounts with their own user_id (not "default") using the `/connect` flow (endpoint 13).

---

### Finding 5: Synthetic Account `id: null` Breaks Frontend Key Access (MEDIUM)

**Plan section:** §1.4 (lines 171-187)

**Problem:** The plan's synthetic account has `"id": None`. In the frontend:

1. `_agentClientData[a.id]` becomes `_agentClientData[null]` — JavaScript converts `null` to the string `"null"` when used as an object key. This creates an entry with key `"null"` instead of a proper numeric ID.
2. `_agentSelectClient("null")` would be called when the user clicks the synthetic card.
3. Lines 7678 and 7680 use `a.id` in `onclick="_agentSelectClient(''+a.id+'')"` — with `null`, this becomes `onclick="_agentSelectClient('null')"`, which is confusing but won't crash.
4. The account-card rendering on line 7834 (`data-id="${a.id}"`) would produce `data-id="null"`.

**Fix:** Use a sentinel string for synthetic accounts:
```python
synthetic = {
    "id": "pending__default",  # sentinel, not numeric
    ...
}
```
And in the frontend, add a guard:
```javascript
if (!c || c.needs_onboarding) {
    // Skip or show special treatment
    return;
}
```

---

### Finding 6: `_agent_user_ids()` Fallback Over-Engineered (LOW)

**Plan section:** §1.3, lines 81-100

**Problem:** The helper function has a complex fallback chain:
```python
user_data = session.get("user_id")
if user_data is None:
    user_data = session.get("user_email", session.get("authenticated", False))
    if user_data is True:
        user_data = "default"
    elif user_data is False or user_data is None:
        user_data = "default"
session_uid = str(user_data)
```

All Agent tab endpoints are decorated with `@login_required`, which means `session["user_id"]` is guaranteed to exist and be truthy. The fallback chain would only execute if:
- `@login_required` is somehow bypassed (bug)
- The session has `authenticated=True` but no `user_id` (impossible with current auth flow)

**Simplification suggestion:**
```python
def _agent_user_ids():
    """Return (session_uid, [session_uid, 'default']) for Agent tab dual-ID queries."""
    session_uid = str(session.get("user_id"))
    ids = [session_uid]
    if session_uid != "default":
        ids.append("default")
    return session_uid, ids
```

The `@login_required` decorator already handles unauthenticated states. If defensive coding is desired, a single `if not session.get("user_id"): return "default", ["default"]` is sufficient.

**Counter-argument:** The current fallback is robust against future refactors where @login_required might be removed. Keeping it as-is is reasonable for defense-in-depth.

---

### Finding 7: Tier 2 Balance Delta Race Condition (LOW)

**Plan section:** §2.2, Tier 2 (lines 280-288)

**Problem:** The Tier 2 code reads `daily_row` from the DB **outside** the `mt5_state_lock`, then acquires the lock to read `mt5_state`. If the EA pushes new data between these two reads:
- `daily_row.starting_balance` = 10000 (old, from DB)
- `mt5_state["default"]["account"]["balance"]` = 10200 (new, just pushed)

The delta would be 200, which is correct since the starting balance was from midnight and current balance is after today's activity. But if the EA push includes an overnight balance change, this could be wrong.

**This is actually correct for the intended use case** — the starting_balance is midnight's snapshot, and the current balance is live. The race window only matters if `AgentDailyMetrics` was just created (no starting_balance yet) and the EA pushes simultaneously, which is theoretically possible but extremely unlikely.

**Verdict:** Low risk. Document the assumption that `AgentDailyMetrics.starting_balance` reflects today's opening balance.

---

### Finding 8: `datetime.utcnow()` Deprecated (LOW)

**Plan sections affected:** §2.2 (multiple calls to `datetime.utcnow()`)

**Problem:** `datetime.utcnow()` is deprecated as of Python 3.12. The plan uses it in:
- `datetime.utcnow().date()` for "today" date comparison
- `datetime.utcnow` in SQLAlchemy defaults (existing code)

The existing app.py already uses `datetime.utcnow()` extensively (not a plan-introduced issue), but new code should prefer `datetime.now(datetime.UTC)` or `datetime.now(datetime.timezone.utc)`.

**Verdict:** Low risk. The plan can keep `datetime.utcnow()` for consistency with the existing codebase, but add a note that a future migration is needed.

---

### Finding 9: Per-Account N+1 Query Pattern (LOW)

**Plan section:** §2.2 — the three-tier fallback

**Problem:** The Tier 1 and Tier 3 queries run inside `for a in accounts:` (line 18356), producing 2 extra DB queries per account per dashboard load. For N=10 accounts, that's 20 extra queries.

**Optimization (optional, not required for implementation):**
```python
# Batch-fetch all AgentDailyMetrics rows for today
account_ids = [a.id for a in accounts]
daily_rows = db.query(AgentDailyMetrics).filter(
    AgentDailyMetrics.account_id.in_(account_ids),
    AgentDailyMetrics.date == datetime.utcnow().date(),
).all() if account_ids else []
daily_by_acct = {r.account_id: r for r in daily_rows}

# Batch-fetch all today's trade sums
from sqlalchemy import func
trade_sums = db.query(
    AgentTrade.account_id,
    func.coalesce(func.sum(AgentTrade.realized_pnl), 0.0)
).filter(
    AgentTrade.account_id.in_(account_ids),
    AgentTrade.status == "CLOSED",
    func.date(AgentTrade.exit_time) == datetime.utcnow().date(),
).group_by(AgentTrade.account_id).all() if account_ids else []
trade_sum_by_acct = {r[0]: r[1] for r in trade_sums}

# Then in the loop, use these dicts instead of individual queries
```

**Verdict:** Not a correctness bug, but a performance note. Acceptable for Phase 1; optimize in a follow-up if needed.

---

### Finding 10: Analytics Endpoint (endpoint 7) — List-Based Filter Pattern (LOW)

**Plan section:** §1.2, endpoint 7

**Problem Confirmed:** Line 18736 uses `acct_filter = [TradingAccount.user_id == user_id, TradingAccount.is_active == True]` as a list, then unpacks with `filter(*acct_filter)`. The plan correctly identifies this needs to change to `TradingAccount.user_id.in_(query_ids)` but doesn't provide a concrete template for the list-based pattern (Appendix A only covers the `.filter()` pattern).

**Fix template:**
```python
acct_filter = [TradingAccount.user_id.in_(query_ids), TradingAccount.is_active == True]
if account_id:
    acct_filter.append(TradingAccount.id == int(account_id))
accts = db.query(TradingAccount).filter(*acct_filter).all()
```

This is straightforward; just flagging that the plan's Appendix A template doesn't cover this variant.

---

### Finding 11: `import random` Inside For Loop (LOW)

**Confirmed:** Line 18355 has `import random` inside the for loop. The first iteration actually imports the module; subsequent iterations are no-ops (Python caches). Line 16544 has a separate `import random` for the Monte Carlo endpoint.

**Plan coverage:** The plan correctly notes this at §2.3. The `import` at line 18355 should be removed when the `random.uniform(...)` call at line 18375 is removed. The module-level `random` usage at line 16544 (`random.sample`) is legitimate and must be preserved.

**Verdict:** Already covered in the plan. No additional finding.

---

### Finding 12: Frontend Positions/History Fetch Without `account_id` Filter (LOW)

**Lines affected:** `static/index-v2-prototype.html` lines 7690 and 7731

**Observation:** The frontend fetches positions and history WITHOUT passing `account_id`:
```javascript
var data = await dvFetch('/api/trading-agent/positions');  // line 7690
var data = await dvFetch('/api/trading-agent/trades?status=CLOSED');  // line 7731
```

The `_agentSelectClient()` function (line 7860) doesn't re-fetch with an account filter — it only re-renders the existing panel. This means after the dual-ID fix, both the session user's own positions AND "default" user's positions will appear in a single list. This is probably the intended behavior (the Agent tab is meant to aggregate all accounts), but should be verified against product requirements.

**Verdict:** Not a bug, but worth confirming with product that showing all accounts' positions together is the desired UX after the dual-ID fix.

---

### Finding 13: `user_id` Type Consistency (LOW — Already OK)

**Verified:** `session.get("user_id")` returns a string in the current code, and `TradingAccount.user_id` is `Column(String(64))`. The `str()` conversion at line 18320 (`user_id = str(session.get("user_id"))`) is already in place across all endpoint entry points.

**The `_agent_user_ids()` helper also does `str(user_data)`**, so type consistency is maintained.

**Edge case:** If `session["user_id"]` were ever an integer, `str(12345)` would produce `"12345"`, which would match `TradingAccount.user_id == "12345"` — consistent.

**Verdict:** No issue.

---

### Finding 14: 16 SQL Patterns, Not 14 (INFO — Verification)

The plan correctly lists 14 **endpoints** but the count of actual `TradingAccount.user_id == user_id` SQL patterns within the agent section is **16**:

| # | Endpoint | Lines | Pattern |
|---|----------|-------|---------|
| 1 | agent_dashboard | 18324 | Primary filter |
| 2 | agent_positions | 18434 | Primary join filter |
| 3 | agent_positions | 18443 | acct_map secondary |
| 4 | agent_trades | 18487 | Primary join filter |
| 5 | agent_trades | 18509 | acct_map secondary |
| 6 | agent_create_trade | 18547 | Ownership gate |
| 7 | agent_trades_export | 18598 | Primary join filter |
| 8 | agent_trades_export | 18610 | acct_map secondary |
| 9 | agent_trade_detail | 18656 | Primary join filter |
| 10 | agent_update_trade | 18684 | Ownership gate |
| 11 | agent_analytics | 18736 | acct_filter list |
| 12 | agent_portfolio | 18834 | Primary filter |
| 13 | agent_archive_account | 18886 | Ownership gate |
| 14 | agent_sync_account | 18918 | Ownership gate |
| 15 | agent_daily_metrics | 18954 | Ownership gate |
| 16 | agent_recompute_daily | 18999 | Ownership gate |

Plus the 6 non-agent `TradingAccount.user_id == user_id` patterns at lines 10728, 10760, 10804, 10854, 10920, 10982 that should **NOT** be changed.

The plan implicitly covers all 16 (it mentions "acct_map secondary queries" separately), but an explicit count of 16 would reduce the risk of missing one during implementation.

---

## Items the Plan Already Addresses Correctly

The following concerns from the original task description are already well-handled by the plan:

| Concern | Plan Coverage | Verdict |
|---------|--------------|---------|
| `session.get("user_id")` returns None | Lines 87-93 handle with fallback chain | ✅ Covered |
| Non-string types from session | `str(user_data)` at line 94 handles this | ✅ Covered |
| `session_uid == "default"` deduplication | Line 98: `if session_uid != "default": ids.append("default")` | ✅ Covered |
| `agent_add_account` creates with session user_id only | Line 19062 unchanged; correctly uses `user_id=user_id` (session) | ✅ Covered |
| `random` import removal | Line 16544 keeps `import random` for Monte Carlo; line 18355 removed | ✅ Covered |
| Frontend null rendering for today_pnl | Plan §2.2 has JS/CSS for `--` rendering | ✅ Covered (but see Finding 2 for hardcoded-0 bug) |
| BUILD_PLAN.md boundary documentation | Plan §3.4 has clear template | ✅ Covered |
| Performance impact of `.in_()` | Plan risk table says "negligible overhead" — correct, user_id is indexed | ✅ Covered |

---

## Gaps in the Plan

### Gap 1: No Test Plan
The plan provides acceptance criteria (AC1.1–AC3.3) but no test scenarios for edge cases like:
- What happens when `mt5_state["default"]` exists but `TradingAccount` has 0 rows? (Covered by §1.4)
- What happens when `AgentDailyMetrics` has a row but `pnl` is NULL? (Tier 1 fallback — `daily_row.pnl is not None` handles this)
- What happens when user is logged in but has 0 accounts of their own AND no EA is connected? (Should show empty state)

### Gap 2: No Rollback Plan
If the Phase 2 dual-ID change introduces unexpected behavior, how do we roll back? Simply reverting the changes would work since they're additive.

### Gap 3: Missing Frontend Bug — `today_pnl` Ignored
As documented in Finding 2, the frontend has a pre-existing bug where `pnlVal` is hardcoded to `0` at line 7678. The plan's Phase 3 only mentions adding `--` rendering for null, not fixing the hardcoded zero.

---

## Recommended Additions to the Plan

1. **Add to Phase 2 (after line 421):** A step to add secondary ownership checks for write endpoints on `"default"` accounts (Finding 1).
2. **Add to Phase 3 (line 427):** Explicitly note that line 7678 must change from `var pnlVal = 0` to reading `a.today_pnl` (Finding 2).
3. **Add to Phase 1 (after line 406):** Fix the Tier 3 "net zero PnL" edge case (Finding 3).
4. **Add to §1.4 (line 177):** Change synthetic account `id` from `None` to `"pending__default"` to avoid JS key confusion (Finding 5).
5. **Add implementation count:** 16 SQL patterns need the `.in_()` fix, not 14 (Finding 14 — informational).

---

## Implementation Checklist (Derived from Review)

### Phase 1 — Before Implementation:
- [ ] Fix Tier 3 query: distinguish "no trades" from "net zero PnL"
- [ ] Remove `import random` at line 18355 (verify no other uses in the function)
- [ ] Keep `import random` at line 16544 (Monte Carlo uses `random.sample`)

### Phase 2 — Before Implementation:
- [ ] Add secondary ownership check for write endpoints on `"default"` accounts
- [ ] Use `_agent_user_ids()` pattern for acct_map queries (not just primary)
- [ ] Fix analytics endpoint (line 18736): `acct_filter[0]` → `.in_(query_ids)`
- [ ] Verify all 16 SQL patterns are updated (not just the 14 primary queries)

### Phase 3 — Before Implementation:
- [ ] Fix line 7678: replace `var pnlVal = 0` with reading `a.today_pnl` from API
- [ ] Add null-guard for synthetic account `id` in `_agentSelectClient`
- [ ] Add `needs_onboarding` visual treatment for synthetic accounts
- [ ] Guard against `null`/`"pending__default"` account_id in downstream API calls

---

## Verdict

**The plan is fundamentally sound.** The architecture (unified helper, three-tier fallback, dual-ID pattern) is well-designed and consistent with the existing watch engine patterns. The 14 findings above are implementation-detail concerns that can be addressed without changing the plan's architecture. The highest-risk finding (#1, archive security) may be a non-issue for single-user deployments but should be documented and mitigated for multi-user SaaS.

**Recommended action:** Proceed with implementation, but add the 5 recommended additions to the plan before coding begins.
