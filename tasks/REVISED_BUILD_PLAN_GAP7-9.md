# DotVerse — Revised Build Plan
## Original GAPs 2–6 (remaining) + New GAPs 7–9 (Auto-Adjustment Automation)
### Date: 2026-05-14

---

## GitNexus Architecture Audit — Pre-Plan

Run before this document was written. Key findings:

| Symbol | Direction | Risk | Callers / Dependants | Safe to extend? |
|---|---|---|---|---|
| `run_watch_job` | downstream | CRITICAL | 28 symbols, 5 modules | YES — additive branches only, never restructure outer loop |
| `_get_automation_settings` | upstream | MEDIUM | 5 callers (run_watch_job, _job_auto_scan, mt5_get_pending, mt5_level_alert, automation_settings_get) | YES — adding new keys to return dict is additive, existing callers ignore unknowns |
| `AutomationSettings` (model) | upstream | LOW | run_worker.py (import only), tests | YES — adding new columns is safe, no callers break |
| `telegram_webhook` | upstream | LOW | 0 upstream callers | YES — adding new elif handlers is completely self-contained |
| `_fetch_news_sentiment` | upstream | LOW | 1 caller (analyze only) | YES — will add a second call site in run_watch_job |
| `send_telegram_keyboard` | upstream | LOW | called from run_watch_job | YES — existing calls stay, new auto-path bypasses them conditionally |

**DeepSeek status:** Already integrated at lines 10124–10775. Used for verdict chain via `deepseek-chat`. API key: `DEEPSEEK_API_KEY` env var. Will be reused for auto-adjustment AI reasoning layer — no new infrastructure needed.

**_fetch_news_sentiment status:** Exists at line 2114. Currently called only at entry (analyze(), line 7030). Needs a second call site in run_watch_job for mid-trade sentiment monitoring.

---

## Current State

| Item | Description | Status |
|---|---|---|
| ITEMs 1–7b | RangeIndex fix, null leak, Act tab HOLD, EMA cross, Supertrend flip, diagnostic pip text, news sentiment backend + frontend | COMPLETE — all committed |
| ITEM 8 | GAP 6: ATR trailing default 2.0→1.0 | PENDING |
| ITEM 9 | Flow-scaled sizing feedback loop | PENDING |
| ITEM 10/11 | Refresh-logout flicker | PENDING |
| GAPs 7–9 | Auto-adjustment automation (NEW) | NOT YET PLANNED |

---

## Phase 1 — Remaining Original Items (3 commits)

### ITEM 8 — GAP 6: ATR Trailing Default 2.0× → 1.0×
**Priority:** MEDIUM | **Path:** A | **GitNexus risk:** LOW

**The problem:** PDF Chapter 8 explicitly states trail distance = 1.0× ATR. Code default is 2.0×.  
At BTC ATR 480 pips: 2.0× = 960 pip trail. 1.0× = 480 pip trail.  
Positions give back 2× the intended profit before the trail closes them.

**Three locations — one commit:**
- `AutomationSettings` model: `trailing_atr_mult = Column(Float, default=1.0)`
- `_init_db` migration: `ALTER TABLE automation_settings ALTER COLUMN trailing_atr_mult SET DEFAULT 1.0`
- `_get_automation_settings` fallback: `"trailing_atr_mult": getattr(s, "trailing_atr_mult", 1.0) or 1.0`

**Identity contract:** AutomationSettings rows created by human users AND EA path ("default"). No change to query logic.

**Failure brainstorm:**
1. Existing DB rows already have 2.0 — ALTER changes column default for NEW inserts only. Existing rows unaffected. Correct.
2. `getattr` fallback for 0.0 — `or 1.0` handles falsy 0.0 value. Safe.
3. All 5 callers of `_get_automation_settings` receive the value — no change to their code needed.

**Success criteria:** Fresh user (new row) gets `trailing_atr_mult = 1.0` from `/api/automation/settings`. Existing user row unchanged.

---

### ITEM 9 — Flow-Scaled Sizing Feedback Loop
**Priority:** MEDIUM | **Path:** B | **GitNexus risk:** N/A (frontend)

**The problem:** `updateFlowBadge` reads `szRisk` input value. APPLY writes to `szRisk`. Each APPLY → re-fires updateFlowBadge → reads reduced value → suggests further reduction → loop. Value spirals down on every APPLY click.

**Pre-verify FIRST (before writing code):** Open DevTools console. Type `document.getElementById('szRisk').value = '5'` and check whether `oninput` fires. If yes, need `window._isApplyingFlow` flag. If no, no flag needed.

**The fix (Option 1):**
- Page load: `window._userBaseRisk = parseFloat(szRisk?.value) || 1.0`
- `szRisk` oninput: `window._userBaseRisk = parseFloat(this.value) || 1.0`
- `updateFlowBadge`: read `window._userBaseRisk` instead of `szRisk.value`
- APPLY writes to `szRisk` only — does NOT touch `window._userBaseRisk`

**Success criteria:** Set szRisk to 5%. Click APPLY. Click APPLY again. Value does not drop. `window._userBaseRisk` remains 5 throughout.

---

### ITEM 10/11 — Refresh-Logout Flicker
**Priority:** LOW | **Path:** B | **GitNexus risk:** N/A (frontend)

**The problem:** `vLanding` has `active` class by default at line 4046. Auth check is async. Sign-in view briefly flashes on every hard refresh even when logged in.

**Two changes:**
1. Remove `active` from `<div class="view active" id="vLanding">` at line 4046
2. In `_bootAuthCheck` IIFE else-branch (unauthenticated path): add `showView('vLanding')`

**Pre-verify:** grep for all `showView` calls to confirm it accepts 'vLanding'. Confirm no other path relies on vLanding having `active` by default.

**Success criteria:** Hard refresh while logged in → no sign-in flash. Hard refresh while logged out → sign-in appears immediately.

---

## Phase 2 — Auto-Adjustment Automation (NEW — GAPs 7, 8, 9)

### The Gap Being Closed

Currently: system detects conditions (macro event, EMA cross, Supertrend flip, sentiment change) and fires Telegram alerts with buttons. Trader must tap to execute.

Target: trader sets automation preferences ONCE before sleeping. When conditions trigger, system executes automatically. Telegram sends a notification (what was done), not a decision (what should you do).

The loop: **detect condition → check user's automation preference → if auto ON → execute MT5 order directly → notify via Telegram → if auto OFF → existing keyboard behavior unchanged.**

No existing behavior is removed. Auto-execute is an additive branch inside each condition block.

---

### ITEM 11 — Automation Settings Extension
**Priority:** HIGH | **Path:** A + B | **GitNexus risk:** LOW (model) / MEDIUM (_get_automation_settings)

**New fields in `AutomationSettings` model:**
```python
# Auto-adjustment fields — all default OFF (safe for existing users)
auto_macro_response    = Column(Boolean, default=False)  # Auto move SL to breakeven on approaching HIGH event
auto_invalidation_act  = Column(Boolean, default=False)  # Auto tighten stop on EMA cross / ST flip
auto_sentiment_watch   = Column(Boolean, default=False)  # Auto partial close on negative sentiment shift
macro_hours_threshold  = Column(Float,   default=4.0)    # Hours before event to trigger auto response
auto_close_pct         = Column(Float,   default=50.0)   # % of position to close on macro/sentiment trigger
```

**`_init_db` migration (5 ALTER TABLE statements):**
```sql
ALTER TABLE automation_settings ADD COLUMN IF NOT EXISTS auto_macro_response BOOLEAN DEFAULT FALSE;
ALTER TABLE automation_settings ADD COLUMN IF NOT EXISTS auto_invalidation_act BOOLEAN DEFAULT FALSE;
ALTER TABLE automation_settings ADD COLUMN IF NOT EXISTS auto_sentiment_watch BOOLEAN DEFAULT FALSE;
ALTER TABLE automation_settings ADD COLUMN IF NOT EXISTS macro_hours_threshold FLOAT DEFAULT 4.0;
ALTER TABLE automation_settings ADD COLUMN IF NOT EXISTS auto_close_pct FLOAT DEFAULT 50.0;
```

**`_get_automation_settings` return dict additions:**
```python
"auto_macro_response":   getattr(s, "auto_macro_response",   False) or False,
"auto_invalidation_act": getattr(s, "auto_invalidation_act", False) or False,
"auto_sentiment_watch":  getattr(s, "auto_sentiment_watch",  False) or False,
"macro_hours_threshold": getattr(s, "macro_hours_threshold", 4.0)   or 4.0,
"auto_close_pct":        getattr(s, "auto_close_pct",        50.0)  or 50.0,
```

**`automation_settings_save` endpoint additions:** Accept the 5 new fields from the frontend POST body. Same pattern as existing fields.

**Frontend — Act tab automation panel:**
Add 3 new toggle rows below existing settings. Each toggle has a plain-English label and a one-line explanation (beginner principle):
- **Auto Macro Response** — "When a HIGH impact news event is within [X] hours and your position is in profit, DotVerse will automatically move your stop to breakeven. You won't lose what you made."
- **Auto Invalidation Tighten** — "When the trend signal that started your trade reverses (EMA cross or Supertrend flip), DotVerse will automatically tighten your stop to lock partial profit."
- **Auto Sentiment Watch** — "When news sentiment for this asset turns sharply negative mid-trade, DotVerse will automatically close [X]% of your position to protect against news-driven reversals."
- Threshold inputs: "Hours before event" (default 4), "Close %" (default 50)

**Identity contract:** AutomationSettings rows created under human user_id OR "default". All 5 new fields default to False/safe values — existing behaviour unchanged for every user who hasn't touched the new settings.

**Failure brainstorm:**
1. Existing rows don't have new columns → `ADD COLUMN IF NOT EXISTS` + `getattr` fallback handles this.
2. `automation_settings_save` endpoint currently saves only existing fields → must add new fields to the save logic or they will never persist.
3. Frontend toggle renders but doesn't POST new fields → verify network request includes all 5 new keys.
4. All 5 callers of `_get_automation_settings` receive new keys → they don't use them (only run_watch_job will). No breakage.

**Success criteria:** Save auto_macro_response=true from UI → GET /api/automation/settings returns it as true. Railway logs show new columns in DB after migration.

---

### ITEM 12 — GAP 7: Auto Macro Response Execution
**Priority:** HIGH | **Path:** A | **GitNexus risk:** LOW (additive branch in run_watch_job)

**What it replaces:** The existing `send_telegram_keyboard` call in the macro event detection block of `run_watch_job`. That call stays — it becomes the ELSE branch.

**The new IF branch (when `settings['auto_macro_response']` is True):**
```python
if settings.get('auto_macro_response') and _profit_pips > 0:
    # 1. Create PARTIAL_CLOSE MT5Order for auto_close_pct% of the position
    # 2. Create MODIFY MT5Order to move SL to entry price (breakeven)
    # 3. Send Telegram NOTIFICATION (not keyboard): "Auto-adjusted: closed X% + moved SL to breakeven before [event]. You wake up protected."
    # 4. Set Redis dedup key so this doesn't fire again for same event
else:
    # existing send_telegram_keyboard call — unchanged
```

**pip_size:** Reuse existing `_atr_to_pips` function — already handles JPY pairs and all asset classes.

**MT5Order pattern:** Same as existing `tighten` handler in `telegram_webhook` — MODIFY order with `user_id="default"`. EA picks up on next 5s poll.

**Identity contract:** MT5Orders created here use `user_id="default"`. Same as all Telegram-triggered orders.

**Failure brainstorm:**
1. Position already at breakeven → `_profit_pips <= 0` check prevents pointless action.
2. Partial close order for a position already partially closed → guard: check open_volume > 0 before creating order.
3. MODIFY order for SL already at breakeven → guard: only queue if current_sl != open_price.
4. Redis dedup key missing (Redis down) → graceful fallback to keyboard behavior. Do not crash.
5. auto_close_pct is 0 → guard: `if auto_close_pct > 0`.
6. Multiple positions on same symbol all trigger simultaneously → each position has its own dedup key by ticket. Correct.

**Success criteria:** With `auto_macro_response=True`, HIGH event within 4 hours, position in profit → no Telegram keyboard appears. Two MT5Orders created in DB (PARTIAL_CLOSE + MODIFY). Telegram notification sent saying what was done. EA picks up and executes within 5 seconds.

---

### ITEM 13 — GAP 8: Auto Invalidation Execution
**Priority:** HIGH | **Path:** A | **GitNexus risk:** LOW (additive branch in run_watch_job)

**What it replaces:** The existing `send_telegram_keyboard` calls in both the EMA cross block (ITEM 4) and the Supertrend flip block (ITEM 5) of `run_watch_job`. Both keyboard calls become ELSE branches.

**The new IF branch (when `settings['auto_invalidation_act']` is True):**
```python
if settings.get('auto_invalidation_act'):
    # 1. Calculate safe_pips using same formula as ITEM 6 (GAP 4)
    # 2. Compute new_sl_price from safe_pips
    # 3. Create MODIFY MT5Order with new SL — user_id="default"
    # 4. Send Telegram NOTIFICATION: "Auto-adjusted: stop tightened to +X pips on [ticker] — EMA cross detected. Position protected."
    # 5. Set Redis dedup key
else:
    # existing send_telegram_keyboard call — unchanged
```

**Reuse:** `safe_pips` formula is already built in ITEM 6 (GAP 4). Do not duplicate — extract to a shared `_compute_safe_pips(profit_pips, tp1_distance_pips, pip_size)` helper so both ITEM 6 alert text and ITEM 13 auto-execute use the same calculation.

**Failure brainstorm:**
1. `safe_pips <= 0` (position barely in profit) → fall back to keyboard behavior, do not create a pointless order.
2. EMA cross AND Supertrend flip fire on same tick → two separate dedup keys, two separate MODIFY orders. Both correct. Last one written wins for the SL price — guard by checking if a MODIFY already queued for this ticket in the last 60s.
3. `new_sl_price` computation error → try/except, fall back to keyboard behavior.

**Success criteria:** With `auto_invalidation_act=True`, EMA cross on a live BUY in profit → no Telegram keyboard. One MODIFY MT5Order in DB with tightened SL. Telegram notification sent. EA executes within 5s.

---

### ITEM 14 — GAP 9: Auto Sentiment Watch (Mid-Trade)
**Priority:** MEDIUM | **Path:** A | **GitNexus risk:** LOW (additive to run_watch_job, new call to _fetch_news_sentiment)

**The gap:** `_fetch_news_sentiment` is currently called only at entry (analyze()). Live positions have no mid-trade sentiment monitoring. If news turns sharply negative mid-trade, the system is blind to it.

**What to add in `run_watch_job`:**
For each live position (per ticker, not per ticket — one sentiment call per unique symbol per tick):
```python
if settings.get('auto_sentiment_watch'):
    _news = _fetch_news_sentiment(ticker, asset_type)  # Redis-cached hourly — no extra API calls
    if _news and _news.get('negative', 0) >= 3 and _news.get('verdict') == 'NEGATIVE PRESS':
        # Auto partial close using auto_close_pct
        # Telegram notification: "Auto-adjusted: closed X% of [ticker] — 3+ negative headlines detected. Sentiment: [top_headline]"
```

**Redis cache:** `_fetch_news_sentiment` already caches per ticker per hour. The watch job calls it once per unique symbol per tick. If 5 positions are open on BTC, only 1 Finnhub API call per hour. Zero rate-limit risk.

**DeepSeek AI layer (within ITEM 14):** Instead of a hardcoded `negative >= 3` threshold, pass the news sentiment data + current position state to DeepSeek for a judgment call:
```python
_ai_verdict = _deepseek_sentiment_judge(ticker, _news, _profit_pips, order_type)
# Returns: {"action": "close_partial"|"tighten"|"hold", "reason": "...", "confidence": 0.85}
```
`_deepseek_sentiment_judge` is a new ~30-line function. Calls DeepSeek with a structured prompt: "Given these news headlines [X], this position [BUY ticker, +Y pips profit], should I close 50%, tighten stop, or hold? Answer in JSON." Parses response. Falls back to hardcoded threshold if DeepSeek returns error or confidence < 0.7.

**Identity contract:** No user_id involved. Market data function. MT5Orders created use `user_id="default"`.

**Failure brainstorm:**
1. Finnhub returns no news (forex pairs) → `_news` is None or `available=False` → skip. No action.
2. DeepSeek API call fails → fall back to hardcoded `negative >= 3` threshold. Never crash the watch job.
3. DeepSeek call latency (1-3s) → the watch job is already sleeping 60s between ticks. 1-3s is acceptable. Only call DeepSeek when `auto_sentiment_watch=True` AND sentiment threshold is met — not on every tick.
4. Position closes between sentiment check and order creation → MT5Order PARTIAL_CLOSE on a closed ticket → EA handles this gracefully (ticket not found = skip). Acceptable.
5. Same ticker, multiple positions → one sentiment call (Redis cache), one action decision, but one PARTIAL_CLOSE order per unique ticket. Correct.

**Success criteria:** With `auto_sentiment_watch=True`, live BTC position, simulate 3+ negative headlines in Redis cache → PARTIAL_CLOSE MT5Order created. Telegram notification sent with top headline. No crash if Finnhub returns empty.

---

## Complete Revised Commit Sequence

| # | Item | Functions | Risk | Path | Verification |
|---|---|---|---|---|---|
| NEXT | ITEM 8 | AutomationSettings + _init_db + _get_automation_settings | LOW | A | New row gets 1.0× trailing. Existing row unchanged. |
| NEXT | ITEM 9 | index-v2-prototype.html — updateFlowBadge + szRisk + APPLY | LOW | B | APPLY twice: value stable. |
| NEXT | ITEM 10/11 | index-v2-prototype.html — line 4046 vLanding | LOW | B | No flash on hard refresh while logged in. |
| NEW | ITEM 11 | AutomationSettings (5 new cols) + _init_db + _get_automation_settings + automation_settings_save + frontend | MEDIUM | A+B | Save from UI → GET returns it. All 5 keys in response. |
| NEW | ITEM 12 | run_watch_job macro event block | LOW | A | auto_macro_response=True + HIGH event + profit → 2 MT5Orders in DB. No keyboard sent. |
| NEW | ITEM 13 | run_watch_job EMA cross + ST flip blocks + new _compute_safe_pips helper | LOW | A | auto_invalidation_act=True + EMA cross + profit → 1 MODIFY in DB. No keyboard. |
| NEW | ITEM 14 | run_watch_job + _fetch_news_sentiment (new call site) + _deepseek_sentiment_judge (new fn) | MEDIUM | A | auto_sentiment_watch=True + 3 negative headlines → PARTIAL_CLOSE in DB. No crash on Finnhub empty. |

**Total remaining commits: 7**  
**One commit per item. No bundling. Two gates per commit (diff → commit? → push?).**

---

## Non-Negotiable Rules (unchanged)

1. run_watch_job is CRITICAL blast radius — every change is an ADDITIVE BRANCH inside an existing conditional. Never restructure the outer loop.
2. All new auto-execute MT5Orders use `user_id="default"` — identity contract.
3. All new auto-execute paths have an ELSE branch that preserves existing keyboard behavior when the setting is OFF.
4. All defaults are OFF/False/safe — existing users are unaffected until they turn features on.
5. DeepSeek is called only when a condition triggers + the setting is ON — never on every watch tick.
6. GitNexus impact run before every function touched.
7. Correct served file: `static/index-v2-prototype.html` (NOT index.html).
