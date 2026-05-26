# QA Report: J1 Cost Analysis & J2 Monte Carlo Endpoints + Frontend

**Date:** 2026-05-26
**Files examined:**
- Backend: `/Users/oq/Documents/trading-signals-saas/app.py` lines 12695–12792
- Frontend: `/Users/oq/Documents/trading-signals-saas/static/index-v2-prototype.html` lines 10529–10551
- Fetch helper: same file, line 6985 (`dvFetch`)

---

## TEST 1: User has 0 closed trades (`ready=false` path)

### Backend — cost-analysis (line 12695)
- **Condition:** Query returns empty list (no rows matching outcome + pnl + entry + stop_loss).
- **Response:** `{ready: false, message: "No closed trades yet."}` — **PASS**
- **Also:** If rows exist but all fail the `sl_dist > 0` check (entry == stop_loss), `fee_drags` will be empty, returning `{ready: false, message: "Insufficient data."}` — **PASS**

### Backend — montecarlo (line 12740)
- **Condition:** Fewer than 10 rows with `actual_pnl_r` not null.
- **Response:** `{ready: false, message: "Monte Carlo needs 10 closed trades — you have N."}` — **PASS**
- **Note:** Query filter is looser than cost-analysis (does not require outcome in WIN/LOSS/BE, only `actual_pnl_r.isnot(None)`). This is intentional — it captures all R-multiples, but means trades without an outcome classification still count.

### Frontend handling (both endpoints)
- Lines 10542 and 10542: `if(!d.ready){ el.innerHTML='... '+d.message+'...'; return; }` renders the backend message. **PASS**

---

## TEST 2: Cost-analysis returns `warning=true`

### Backend (line 12724)
- `warning = avg_drag > 0.1` — i.e., average fee drag exceeds 0.1R per trade.
- The `message` field changes depending on warning flag:
  - Warning: "Your broker costs are reducing your edge by an average of XR per trade. Consider tighter spreads or fewer trades."
  - No warning: "Fee drag is acceptable at XR per trade."
- **PASS** — logic is sound. Fee is hardcoded as `entry * 0.002 / sl_dist` (0.2% round-trip). No configurable fee rate — **minor design limitation**, but not a bug.

### Frontend (lines 10534–10536)
- `var col = d.warning ? 'rgba(224,85,85,.85)' : 'rgba(93,232,160,.85)';`
- Applies red color for warning, green for acceptable. Message displayed below.
- **PASS**

### Edge case: what if `warning` is `undefined` (e.g. future code change)?
- `d.warning` evaluates to `undefined` → falsy → green color shown. Msg still renders. Not a crash.

---

## TEST 3: Monte Carlo response shape for <10 trades

- **Backend:** Returns `{ready: false, message: "..."}` — no simulation fields. **PASS**
- **Frontend:** `!d.ready` check catches this and renders the message. **PASS**

---

## TEST 4: Null/undefined edge cases in frontend JS

### Core problem: `dvFetch` swallows errors, returns `null`
```
async function dvFetch(path,opts={}){
  try{const r=await fetch(BASE_URL+path,...); if(!r.ok)throw new Error('HTTP '+r.status); return await r.json();}
  catch(e){console.warn('[dvFetch]',path,e.message); return null;}
}
```
- On ANY network failure, HTTP error, or CORS issue: returns `null`, does NOT reject.
- `.then(function(d){ ... })` executes with `d === null`.
- `d.ready` throws `TypeError: Cannot read properties of null (reading 'ready')`.
- `.catch(...)` catches this TypeError → shows fallback message. **It works, but is fragile.**

### Specific null-field scenarios (if backend returned incomplete success object)

| Field accessed | If null/undefined | Result |
|---|---|---|
| `d.ready` | TypeError | `.catch` handles it |
| `d.warning` | undefined → falsy | Renders green (wrong color, no crash) |
| `d.avg_fee_drag_r` | null/undefined | Renders literal "nullR" or "undefinedR" |
| `d.trades_analysed` | null/undefined | Renders "Based on null closed trades" |
| `d.message` | null/undefined | Renders literal "null" or "undefined" |
| `d.p5_drawdown_pct` | null/undefined | Renders literal "null%" |
| `d.prob_20pct_drawdown` | null/undefined | `d.prob_20pct_drawdown > 20` → false, renders green |
| `d.simulations` / `d.trades_used` | null/undefined | Renders literal "null simulations · null trades" |

**Risk assessment:** LOW. Backend always returns complete objects for success paths. However, if the schema changes or backend has a bug, the UI degrades with "null" / "undefined" strings rather than failing gracefully.

### Recommendation:
Add a null-guard at the top of each `.then()`:
```js
if(!d || typeof d !== 'object'){ /* show unavailable */ return; }
```

---

## TEST 5: Network failure — does `.catch` handle it?

### Analysis of the chain:

```
dvFetch('/api/signals/cost-analysis')   // returns null on failure
  .then(function(d){                      // d === null
    ... d.ready ...                       // TypeError thrown
    ...
  })
  .catch(function(){                      // TypeError caught HERE
    el.innerHTML = '... Cost data unavailable ...';
  });
```

**Verdict: YES, `.catch` handles it** — but indirectly:
- `dvFetch` catches network errors and returns `null` instead of rejecting.
- The `.then` handler crashes on `null.ready`.
- The `.catch` at the end catches the resulting TypeError.
- Fallback messages:
  - Cost analysis: "Cost data unavailable"
  - Monte Carlo: "Simulation unavailable"
- **PASS** — users see a degraded but non-breaking UI.

### Same pattern works for:
- HTTP 401 (unauthorized), 500 (server error), 404 (not found), CORS errors, DNS failures, certificate errors.
- All result in `dvFetch` returning `null` → TypeError → `.catch` fallback.

### Gap: Non-JSON responses
If the backend returns a non-JSON response with HTTP 200, `r.json()` throws → dvFetch catches → returns `null` → same path. **Covered.**

---

## ADDITIONAL FINDINGS

### J1: cost-analysis

1. **Fee calculation hardcoded** (line 12716): `fee = float(r.entry) * 0.002` — 0.2% round-trip. No way for users or admins to configure a different fee rate.

2. **No distinction between asset classes**: Same 0.2% fee applied regardless of whether it's crypto, stock, forex. Different asset classes have very different fee structures.

3. **Silent data loss** (lines 12713–12720): Individual trade calculations that fail (non-numeric entry/stop_loss, zero sl_dist) are silently skipped. A trade with `entry == stop_loss` (which happens in real trading) is omitted from `fee_drags` without any warning.

4. **No minimum sample size gate**: Unlike montecarlo (which requires 10 trades), cost-analysis runs on as few as 1 trade with valid data. A single trade's fee drag is not statistically meaningful.

### J2: Monte Carlo

1. **Equity floor at 0** (line 12765): `equity = max(0.0, equity + r * 0.01)`. This means if equity hits 0, it never recovers even if subsequent trades are positive. This is standard for risk analysis but worth documenting.

2. **Position sizing is implicit**: `r * 0.01` means each trade risks 1% of current equity. No way to configure position size. Users with different risk-per-trade (e.g., 2%, 3%, 0.5%) can't model their actual risk profile.

3. **No seed/reproducibility**: `random.sample` is not seeded. Repeated calls will give different results for the same portfolio. This is fine for a live dashboard but bad for audit trails.

4. **Drawdown percentile off-by-one?** (line 12773–12774): `int(0.05 * 1000) = 50`, `int(0.95 * 1000) = 950`. For 1000 simulations sorted ascending, index 50 is the 51st element (0-indexed). The 5th percentile is at position 50, and the 95th at position 950. This is correct for the "nearest-rank" method.

5. **`prob_20pct_drawdown`** (line 12776): Uses `d >= 0.20` (>= 20%). This measures "20% or worse" drawdown probability. Naming implies "probability of exactly 20%+" which matches the implementation.

### General

6. **No request caching**: Both endpoints query the full trade history from the DB on every page load. For users with thousands of trades, this is wasteful. Simple in-memory cache with user_id key + TTL would help.

7. **No dedicated error response shape**: When `ready=false`, the response includes `message` but no `error` or `code` field. The frontend has to guess whether the issue is temporary or permanent.

8. **Both endpoints are GET-only**: No auth token in headers (relies on session cookie). CSRF risk is low for GET-only endpoints, but worth noting if these become POST later.

---

## SUMMARY

| Test | Result | Severity |
|---|---|---|
| 1. 0 closed trades (both endpoints) | PASS | — |
| 2. warning=true (cost-analysis) | PASS | — |
| 3. <10 trades (Monte Carlo) | PASS | — |
| 4. Null/undefined edge cases | PASS (defensive .catch) | LOW |
| 5. Network failure handling | PASS (indirect, but works) | LOW |

**Overall:** Both endpoints and frontend integration are functional and handle the expected failure modes. The frontend `.catch` blocks cover the `dvFetch` null-return pattern, though the path is fragile (relies on TypeError from `null.ready`). The main risks are: (1) incomplete backend responses would render "null"/"undefined" strings in the UI, (2) no configurable fee rate or position size parameters, and (3) no seeding for Monte Carlo reproducibility.

**Recommended fixes (priority order):**
1. Add `if(!d || !d.ready)` guard in frontend `.then()` instead of `if(!d.ready)`.
2. Make fee rate configurable per user/signal type.
3. Add minimum sample size gate (~5 trades) to cost-analysis, consistent with Monte Carlo's gate.
4. Seed `random` for Monte Carlo reproducibility.
