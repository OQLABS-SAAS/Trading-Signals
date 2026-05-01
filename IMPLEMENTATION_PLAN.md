# DotVerse — Final-Build Implementation Plan

**Author note:** this plan is written under the discipline of `CLAUDE.md` — one change per commit, no bundling, sandbox-verify-before-push, no behavioural promises ("I'll be careful"). Only mechanical actions and observable verifications.

**Source of truth:** `AUDIT_2026-05-01.md` sections 13.A through 13.F, browser-verified live on 2026-05-02.

---

## DECISIONS RECEIVED FROM OMAR (2026-05-02)

These three decisions are now binding scope for this plan:

1. **Phase D — Context page:** Option 2. Remove Context from the pipeline. Context's content (mode-card duplicates of Market + hardcoded IPO list) does not justify a dedicated step. Context page itself: **delete** (not kept as reference) since its content is either fake or duplicated. The "Pre-trade gate · GO / WAIT" function the sidebar advertises will be folded into Market's mode cards (which already do this) or surfaced on Signal as a pre-trade banner.

2. **Phase F1 — Settings:** **Wire everything for real.** Every Settings sub-panel must have a backend effect that matches its description. No "Coming soon" labels. No theatre. The same principle applies to every other faux-functional element in the app — strategy lens buttons, beginner/advanced toggle, marketing stats, anything that exists for a reason must do what it says.

3. **Phase F2 — Tier gating:** DotVerse has pricing tiers. Implement gating fully. Each tier must lock features that are not included in that tier. Free users must see upgrade prompts where Pro/Elite features would normally appear.

4. **Connections form:** Per-user. Each DotVerse user enters their own MT5 credentials and Telegram bot/chat. Stored encrypted in the existing `EncryptionKey` table.

5. **EA outage handling:** Avoid first, escalate if it happens. Layered escalation defined in section "DESIGN DECISIONS — DOTVERSE-DESIGNED" below.

6. **News source, trending tickers, tier definitions:** Omar asked me to design these. Designs are in the next section.

These decisions expand Phase F substantially. The plan below has been rewritten accordingly. Total realistic effort moved from 15–25 sessions to 30–45 sessions because "wire everything for real" is a much larger surface than "fix the documented bugs."

---

## DESIGN DECISIONS — DOTVERSE-DESIGNED (2026-05-02)

Omar asked me to design the open items. These designs are now binding unless Omar overrides specific points.

### D1. Tier definitions and pricing

Three tiers. Anchored on Pro. Free is generous enough to be usable but caps at 5 signals/day so committed traders hit the wall fast. Elite captures the high-compute use case (optimisation grid search, priority data feeds).

**Pricing:**
- **Free** — $0/month
- **Pro** — $39/month or $390/year (save 17%)
- **Elite** — $99/month or $990/year (save 17%)

**FREE — "Get Started"**

The hook. Generous enough for a beginner to learn the platform and build trust. Caps that force a real trader to upgrade.

| Feature | Free |
|---|---|
| Market page | Full access |
| Signal page | **Max 5 signals fired per day** |
| Timeframes | **1h only** (no 15m, 4h, 1d, 1w, 1mo) |
| Asset classes (simultaneous) | **1 class at a time** — user picks crypto OR stocks OR forex |
| Understand page | Chart + RSI + MTF table (no MACD overlay, no Bollinger Bands, no Supertrend, no RSI Divergence trendlines) |
| Size calculator | Full access (educational, kept generous) |
| Backtest | **3 backtests/day**, "Full Report" lens only (no Order Block / Supply & Demand / etc.) |
| Portfolio | **Max 3 positions** |
| Watches/Alerts | **Max 2 active watches**, **in-app only** (no Telegram, no SMS) |
| Performance page | Read-only |
| Risk Manager | Read-only VaR (no stress test, no correlation) |
| News page | Full access |
| Settings panels | Connections (locked), Asset Preferences (1 class), Risk Tolerance, Timezone — others locked |
| Pine Script export | Locked |
| MT5 EA | Locked |

**PRO — "Active Trader"** ($39/mo)

The natural upgrade for someone trading with real money. Removes the caps that frustrate Free users.

| Feature | Pro |
|---|---|
| Everything in Free | + |
| Signals | **Unlimited** |
| Timeframes | **All 6** (15m, 1h, 4h, 1d, 1w, 1mo) |
| Asset classes | **All 5 simultaneously** |
| Understand page | All indicators, RSI Divergence trendlines, full chart |
| Backtests | **Unlimited** |
| Strategy lens | **All 7** (Full Report, Order Block, Supply & Demand, Retracement, Pullback, Breakout, Liquidity) |
| Portfolio | **Unlimited positions** |
| Watches/Alerts | **Unlimited**, **Telegram + SMS delivery** |
| Risk Manager | **Full** (VaR + stress test + correlation) |
| MT5 EA integration | **Unlocked** (the main hook) |
| Pine Script export | **Unlocked** |
| Performance page | Full (target tracking vs actual) |
| Settings panels | All except Optimisation (Elite-only) |

**ELITE — "Power User"** ($99/mo)

For the user who wants every edge. Captures the high-compute use case.

| Feature | Elite |
|---|---|
| Everything in Pro | + |
| **Optimisation worker** (parameter grid search per asset class) | Unlocked |
| **Priority data sources** (FMP + Twelve Data API access — no Yahoo 429s) | Unlocked |
| **Custom indicator colour schemes** | Unlocked |
| **API access** (read-only personal-use API key) | Unlocked |
| **Direct Telegram support channel** | Unlocked |
| **Early access** to new features | Yes |

**Annual discount:** 17% off when billing annually. Pro becomes $390/year, Elite becomes $990/year.

**Trial:** Free tier acts as the trial — no time-limited Pro trial. Users can upgrade and downgrade freely.

**Refund policy:** Stripe handles. 7-day refund window for Pro/Elite, no questions asked.

---

### D2. EA outage escalation (Q3 answer)

EA outages happen — Wine on Mac is fragile, broker servers reboot, network blips. The system avoids them via heartbeat + auto-reconnect, but escalates when avoidance fails.

**Layered escalation (per-user, respects user's notification preferences):**

| Time offline | Action |
|---|---|
| 0–60s | Nothing — transient. EA's auto-reconnect handles it. Heartbeat misses one cycle. |
| 60s–5min | Yellow banner on Act page: "EA reconnecting…" + sidebar notification dot. No autonomous-trade pause yet. |
| 5min–15min | Red banner on Act page: "EA offline for X minutes — trades paused" + Telegram message to user (their bot) + pause `_job_auto_scan` for that user (no new auto-trades fire). Existing open positions are not closed. |
| 15min+ | SMS to user (via Twilio) + email. Banner stays red. Auto-trading remains paused. |
| 30min+ | The autonomous trading remains paused until the EA reconnects AND the user manually clicks "Resume autonomous trading" on the banner. Prevents zombie reconnect from racing through stale orders. |

**Operator-level escalation (DotVerse admin):**
When **5+ users' EAs disconnect within a 5-minute window**, the system fires a notification to the **DotVerse admin Telegram channel** (a dedicated chat, separate from any user). This catches systemic issues — broker outage, Twilio outage, Railway issue — before users start filing tickets.

Admin Telegram channel is configured via Railway env var: `OPS_TELEGRAM_CHAT_ID`. New backend route `/api/internal/ops-alert` (no auth, restricted by Railway internal network).

**Worker:** new RQ job `_job_ea_outage_monitor` runs every 60s. Reads MT5 last-heartbeat per user from /api/mt5/state. Computes minutes since last heartbeat per user. Fires escalation per user. Counts simultaneous outages — if >5, fires ops alert.

**Commit messages:**
- `feat(ea): per-user outage escalation Telegram + SMS`
- `feat(ops): admin alert when ≥5 EAs disconnect simultaneously`

---

### D3. News source (Q4 answer)

**Two real sources, free tier:**

1. **Finnhub.io** — for **stocks, forex, indices, commodities news**. Free tier: 60 API calls/minute. Returns news headlines, summaries, source name, URL, datetime, related tickers, and sentiment (where available). Stable and well-documented.
2. **CryptoCompare** — for **crypto news**. Free tier: 100k calls/month. Returns headlines, summaries, source, URL, datetime, sentiment.

**Architecture:**
- Backend new route `/api/news?asset_class=crypto|stocks|forex|all`
- Caches Redis 10 min per asset_class (free tiers can't sustain heavy traffic)
- Backend tags each article with sentiment: `Bull` / `Bear` / `Neut` based on the source's sentiment field, falling back to keyword heuristic if absent
- Frontend News page replaces hardcoded items with live data
- News badge ("3h ago") rendered from `datetime` field

**Why Finnhub + CryptoCompare specifically:**
- Both have free tiers generous enough for v1 traffic
- Both return structured JSON (no HTML scraping)
- Both have wide coverage (Finnhub covers Reuters, AP, Bloomberg, etc.)
- Both have stable APIs that don't break weekly
- Both are commonly used in the trading-tools space, so existing community knowledge / fallback patterns

**API keys:**
- New Railway env vars: `FINNHUB_API_KEY`, `CRYPTOCOMPARE_API_KEY`
- Sign up at finnhub.io and cryptocompare.com — both have instant API key on free signup

**Future (post-v1):** Marketaux paid tier ($25/mo) when DotVerse scales beyond Finnhub free limits.

**Commit messages:**
- `feat(news): /api/news real feed from Finnhub + CryptoCompare`
- `feat(news): replace hardcoded News page with live feed`

---

### D4. Trending tickers — "Live Momentum Windows" definition (Q5 answer)

The original panel name is "LIVE MOMENTUM WINDOWS · NEW LISTINGS & COINS." I'm honouring that intent and defining "trending" as **recent listings showing strong momentum** — not just generic % gainers.

**Definition:**

A ticker qualifies for the panel if:
1. It was **listed within the last 30 days** (IPO, new coin launch, re-listing), **AND**
2. It currently has either:
   - **% gain since listing > 25%**, OR
   - **Volume today > 3× average daily volume since listing**

**Score per ticker:**
```
score = pct_gain_since_listing × log(1 + volume_today / avg_volume_since_listing)
```
Top 4 by score render in the panel.

**Data sources:**

- **Crypto side (2 cards):** CoinGecko `/search/trending` endpoint (free, no API key, rate-limited but cacheable). Returns the top 7 trending coins by user search activity, with price + price change. Filter to coins listed <30d ago using their `genesis_date`.
- **Stock side (2 cards):** combine
  - NASDAQ recent IPOs feed (free CSV, scraped + parsed once per day)
  - Compute % gain from /api/prices for those tickers
  - Take top 2 by score

**Cache:** Redis, 30 min TTL. Refreshes 48 times/day — well within free-tier limits.

**Score interpretation per card:**
- "Momentum 91/100" = score percentile rank against the 30-day momentum-window cohort
- Beginner-friendly framing: "Strong momentum · use caution" / "Window closing · early buyers exiting"

**Fallback:** if both sources are down, panel shows empty state "No trending tickers right now — check back in 30 minutes" instead of the current fake hardcoded list.

**Commit messages:**
- `feat(market): real trending tickers panel from CoinGecko + NASDAQ IPO feed`
- `feat(market): trending-ticker scoring + caching`

---

### D5. Connections — per-user MT5 + Telegram (Q2 answer, decided)

Per Omar's confirmation: per-user.

**Architecture:**
- New columns on UserSettings (or a sibling `UserCredentials` table) for `mt5_api_key`, `mt5_account`, `mt5_broker_server`, `telegram_bot_token`, `telegram_chat_id`
- All values **encrypted at rest** using the existing `EncryptionKey` table + Fernet (already in `app.py`)
- Decryption happens only inside the EA-poll endpoint (`/api/mt5/pending`) and the Telegram-send endpoint (`send_telegram`)
- Frontend Connections form persists via `/api/settings` (specifically `/api/settings/credentials` to keep the encryption boundary clean)
- The EA must include the user's `mt5_api_key` in every poll request — this is how the backend knows which user is polling, and which orders to return

**EA distribution:**
- Each user downloads a personalized `.ex5` file (or .mq5) from `/account/download-ea` that has their API key compiled in
- OR a generic .ex5 file that prompts for the API key on first connect

**Migration risk:** the existing Marcus Chen account already has an MT5 EA connected with Railway-env-var-based credentials. The migration plan needs to:
1. Create UserSettings rows for existing users
2. Copy current Railway env-var credentials into Marcus's row (one-time)
3. Switch the EA endpoints to read from UserSettings instead of env vars
4. Remove the env vars after verifying migration

**Commit messages:**
- `feat(settings): UserCredentials table with Fernet encryption`
- `feat(api): /api/settings/credentials POST/GET`
- `migrate(ea): MT5 secret reads from UserCredentials, not env var`
- `feat(ea): personalized .ex5 download per user`

---

## 0. NON-NEGOTIABLE PROTOCOL FOR EVERY FIX

These rules apply to every commit in this plan. They are written down so they cannot drift mid-session.

**One change per commit.** No bundling. If a fix touches both backend and frontend, that is two commits.

**Three verification paths from CLAUDE.md** — pick the right one per fix and follow it exactly:
- **Path A — backend (`app.py`):** small Python test in the bash sandbox that imports the real functions. Reproduce the bug at the exact boundary value, apply the fix in the same script, run again. Output must change from fail to pass.
- **Path B — frontend (`static/index-v2-prototype.html`):** sandbox verification not possible. State every element ID and function name being changed. Grep both HTML and JS to confirm each one exists. Confirm no shared CSS class is touched.
- **Path C — config (Procfile, requirements.txt, env vars):** state exact line, current value, new value, conflict check. Confirm nothing else depends on the prior value.

**Two-gate commit protocol.** State the diff before committing. Wait for "yes" before commit. Wait for "yes" again before push. Two separate gates.

**Feature preservation checklist before every commit:**
- Auto-refresh (OFF / 15s / 30s / 1m / 5m / 15m + countdown)
- Signals tab: analyze, chart, indicators, MTF, RSI divergence trendlines
- Scanner tab: scan all, scanner table, click-to-analyse
- Backtest tab: run backtest, Pine Script
- Calculator: account, my trade, leverage, entry/SL/TP, RR bar, guidance coach
- Journey panel: 5-step What To Do Next
- Portfolio: positions, VaR, stress, correlation, optimisation
- Watch / alert: toggleWatch, DotVerse alert
- Fear & Greed, Latest News, Scenarios sidebar
- MT5 EA banner + Active Trades + Order History

**No edits to shared CSS rules.** When fixing one component, scope a new isolated rule to that component's specific class. Do not modify `[class$="-card"]` selector lists or universal-glass rules.

**No CSS rules inserted into the middle of an open selector list.** Always find the previous `}` and add new rules AFTER it.

**Behavioural promises are worthless.** Only state mechanical actions and observable verifications.

**Mid-task message rule.** If the user sends a message while a commit is in flight, stop, read, respond, ask whether to continue.

---

## 1. PRE-FLIGHT — BEFORE ANY CODE CHANGE

These are not commits. These are setup actions to do once at the start.

### 1.1 Confirm the working tree is clean

```
cd /Users/oq/Documents/trading-signals-saas
git status         # must be clean
git log -1 --oneline   # capture starting hash for rollback
```

### 1.2 Read the audit one more time

Re-read sections 13.A–13.F of `AUDIT_2026-05-01.md`. Prior summaries become drift.

### 1.3 Confirm the live app is up

```
curl -s https://dot-verse.up.railway.app/health
# Expected: short OK response
```

### 1.4 Confirm Chrome MCP is connected to the live app

If Chrome MCP is not connected, do not push frontend fixes — Path B verification depends on browser inspection.

### 1.5 Capture current production state for rollback witness

```
git log -20 --oneline > /tmp/dotverse_pre_plan_state.txt
```

If anything goes wrong, this is the file used to identify the last-good commit.

---

## 2. EXECUTION ORDER — RATIONALE

The order below is by **risk × value × dependency**, not alphabetical.

- Phase A first because it's high-value, low-risk, single-file. If anything in this phase damages adjacent features, blast radius is small.
- Phase B uses the muscle memory built in A and addresses display lies that erode beginner trust.
- Phase C bundles all watch-system fixes because they share a code path and the bugs compound (broken DELETE + missing UI button + Invalid Date are all Alerts page).
- Phase D is the pipeline-consistency block. Context, step counter, and BUG-22 are all symptoms of the same orphan.
- Phase E is the long fake-data replacement. Each surface is its own commit.
- Phase F is architectural — settings, tier gating, std math. These are decisions, not patches.
- Phase G is polish — mobile, a11y, light theme. Lowest user impact, highest engineering cost.

**Stop after each phase. Smoke-click with the user before starting the next phase.**

---

## 3. PHASE A — SHIP-STOPPERS

Five fixes. All small. All in priority order by user-impact / security exposure.

### A1. BUG-09 — SELL signal "+-X%" display (FRONTEND)

**File:** `static/index-v2-prototype.html`
**Lines:** 12266 (compute pct) and 12291 (render with literal `+`)

**Current behaviour:** SELL TPs render `+-6.42%`. Verified live with ETHUSD 4H SELL on 2026-05-02.

**Change:** at line 12291, replace `'+'+t.pct+'%'` with a sign-aware formatter:
```js
(t.pct >= 0 ? '+' : '') + t.pct.toFixed(2) + '%'
```
Negative numbers already carry a `-`; positive numbers gain a `+`. No need to special-case direction.

**Path B verification:**
- Grep `szTP1Pct`, `szTP2Pct`, `szTP3Pct` to confirm only this one render site uses the broken concatenation
- Grep for any other `'+'+t.pct` pattern; if more exist, fix all in the same commit (they're the same bug)
- Confirm `t.pct` is a Number (not a String) at line 12266 `(tp-entry)/entry*100`

**Browser verify after deploy:**
- Load any SELL signal, navigate to Size, confirm TP rows show `-6.42%` not `+-6.42%`
- Load any BUY signal, confirm TP rows still show `+5.20%`

**Risk:** zero — this is a string-formatting change. No state, no side effects.

**Rollback:** revert the single line.

**Commit message:** `fix(size): SELL TP percentages no longer render as +-X% (BUG-09)`

---

### A2. BUG-21 — 4 unauthenticated backend routes (BACKEND, security)

**File:** `app.py`
**Routes:** `/api/pine-script`, `/api/pine-divergence`, `/api/pine-strategy`, `/api/send-sms`

**Current behaviour:** all four return 200 (or 400 validation) without a session cookie. Verified live 2026-05-02.

**Change:** add `@login_required` decorator to each route handler.

**Path A verification:**
```python
import sys, os
sys.path.insert(0, '/Users/oq/Documents/trading-signals-saas')
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DATABASE_URL', '')
os.environ.setdefault('REDIS_URL', '')
from app import app
client = app.test_client()
# Each route should return 401 without auth
for path, method in [('/api/pine-script','GET'),('/api/pine-divergence','GET'),
                      ('/api/pine-strategy','GET'),('/api/send-sms','POST')]:
    resp = client.open(path, method=method, json={})
    print(path, resp.status_code)  # Must be 401 after fix
```

**Browser verify:**
- Logged out: each URL returns 401 / `{"error":"Unauthorized","login_required":true}`
- Logged in: previous behaviour preserved (Pine Script still downloadable)

**Risk:** if any legitimate caller exists that doesn't carry the cookie, it breaks. Audit `static/index-v2-prototype.html` for fetch calls to these four routes:
- `togglePineCode`, `copyPineScript`, `_undDrawDiv` for divergence — likely send credentials by default with same-origin fetch
- `/api/send-sms` — only used by alert flow which already auth-required

**Rollback:** remove the four decorators.

**Commit message:** `security: require auth on Pine Script and SMS endpoints (BUG-21)`

---

### A3. Login error message normalization (BACKEND, security)

**File:** `app.py` — `/api/login` handler

**Current behaviour:** empty payload → "Incorrect password". Wrong email → "Incorrect email or password". Mismatch enables email-enumeration. Verified live 2026-05-02.

**Change:** every failure path returns the same string `"Incorrect email or password"` — including the empty-payload path that today says "Incorrect password".

**Path A verification:** test client posts `{}`, `{"email":"fake@x.com"}`, `{"email":"fake@x.com","password":"wrong"}`. All three must return identical `{"status":"error","message":"Incorrect email or password"}` and identical 401 status.

**Risk:** zero. Strictly a string change.

**Commit message:** `security: normalise login error to prevent email enumeration`

---

### A4. B12 — Refresh-logout flicker (FRONTEND)

**File:** `static/index-v2-prototype.html`
**Search target:** `<div class="view active" id="vLanding">` (around line 4046 per CLAUDE.md history)

**Current behaviour:** every page reload shows the sign-in landing page for ~1 second before the dashboard takes over. Verified live 2026-05-02 with two screenshots 1 second apart.

**Change:**
1. Remove `active` from `vLanding`'s default class. New: `<div class="view" id="vLanding">`
2. In `_bootAuthCheck` IIFE, on the auth-check **failure** branch, explicitly call `showView('vLanding')` so the sign-in page appears for unauthenticated users only after the auth check fails.

**Path B verification:**
- Grep `_bootAuthCheck` to find the IIFE
- Grep `showView('vLanding')` to confirm there's already an explicit show call somewhere; if not, add one
- Confirm the auth-check fetch is awaited before any view switching

**Browser verify:**
- Authenticated: reload → no sign-in flash, dashboard appears immediately
- Logged out: reload → sign-in page appears (after auth check completes; small loading state acceptable)

**Risk:** medium. If the auth-check fetch fails silently (offline, network error), the user might see no view at all. Add a fallback so a network-failed auth check defaults to `vLanding`.

**Rollback:** restore `active` class on `vLanding`.

**Commit message:** `fix(boot): no sign-in flicker on authenticated reload (B12)`

---

### A5. /api/profile GET returns 500 (BACKEND)

**File:** `app.py` — `/api/profile` handler

**Current behaviour:** GET returns `{"error":"Server error: 405 Method Not Allowed: ..."}` with status 500.

**Change:** explicitly declare allowed methods. The route should return a clean 405 with `Allow: POST` header for GET requests.

**Path A verification:** test client does `client.get('/api/profile')`. After fix: status == 405, response includes `Allow` header, no Python stack trace text in body.

**Risk:** zero. Cosmetic-cleanup.

**Commit message:** `chore(api): /api/profile returns 405 not 500 on GET`

---

**End of Phase A.** Five commits. Five fixes. All low-risk. Smoke-click checklist after Phase A:
- Calculator works on a SELL signal
- Pine Script copy still works while logged in
- Login still works with correct credentials
- Refresh on dashboard does not flicker
- /api/profile no longer 500s

---

## 4. PHASE B — DISPLAY LIES

Four fixes. Each one removes a falsehood the page is currently telling the user.

### B1. BUG-13 — Alerts page header reads from real data

**File:** `static/index-v2-prototype.html` — `showAlerts()` function

**Current behaviour:** Header reads "Alerts · 3 unread · 2 require action" — both numbers hardcoded. Real `/api/notifications` returns 50 unread. Verified live 2026-05-02.

**Change:** in `showAlerts`:
1. Fetch `/api/notifications` first
2. Compute `unread = notifications.filter(n => !n.read).length`
3. Compute `requireAction = notifications.filter(n => !n.read && n.type === 'suggestion').length` (or similar — whatever "require action" actually means; if undefined, decide and document)
4. Render header dynamically: `${unread} unread · ${requireAction} require action`

**Path B verification:**
- Grep for "3 unread · 2 require action" — must find exactly one occurrence in the source, in `showAlerts` body
- Grep for `/api/notifications` to confirm the fetch wrapper exists (`dvFetch`)
- After change, grep for the literal "3 unread" string — must return zero matches

**Browser verify:** load Alerts page → header shows real counts matching `/api/notifications` response.

**Risk:** low.

**Commit message:** `fix(alerts): header reads real unread count from API (BUG-13)`

---

### B2. BUG-17 — "Check Context → UNDERSTAND" footer label

**File:** `static/index-v2-prototype.html` — Signal page footer text

**Current behaviour:** Signal footer reads "← MARKET   Check Context → UNDERSTAND". Button onclick correctly routes to UNDERSTAND. Label says "Check Context" but action is Understand.

**Decision required from user (Omar) before commit:** is Context being kept in the pipeline (then label is correct, button is wrong) or removed from the pipeline (then label is wrong, button is correct)?

This is a Phase D dependency. Defer this commit until Phase D resolves the Context decision.

**Don't fix yet.**

---

### B3. BUG-22 — Dead `sfFooterNext` button

**File:** `static/index-v2-prototype.html`

**Current behaviour:** Button id `sfFooterNext` (class `flow-btn-next`, inline `style="display: none"`) never unhides — even after a signal is loaded. The unhide trigger is broken or removed. Verified live 2026-05-02.

**Decision required:** does this button serve a real purpose in the user flow? If yes, wire its unhide on signal load. If no, delete the element from the DOM.

**Recommendation:** delete. The journey panel below the signal card already has a "What To Do Next" set of action steps with explicit calls to action. A second next-step button in the footer is redundant — and was already invisible in production for an unknown duration.

If deleted: also delete `flow-footer-right` if `sfFooterNext` is its only meaningful child.

**Path B verification:**
- Grep for `sfFooterNext` — find every reference (HTML id + any JS)
- Confirm no JS event handler depends on the element existing

**Risk:** low. Element is invisible already; deleting it can't break anything visible.

**Commit message:** `chore(ui): delete dead sfFooterNext button (BUG-22)`

---

### B4. BUG-23 — Performance page em-dash empty state

**File:** `static/index-v2-prototype.html` — `showPerformance()` function

**Current behaviour:** SIGNALS, AVG CONF, BUY BIAS render as `—` (em dash) when no signals are evaluated. The Equity Curve and Signals-by-Asset-Class panels do this correctly with plain-English copy.

**Change:** in `showPerformance`, when `signals.length === 0`:
- SIGNALS: replace `—` with "Run your first analysis"
- AVG CONF: replace `—` with "—"  but add subtitle "(no signals yet)"
- HIGH CONF: keep `0` (already correct)
- BUY BIAS: replace `—` with subtitle "(no signals yet)"

Use the same empty-state copy already on the asset-class panel for consistency.

**Path B verification:** grep for the four DOM ids and confirm all four render sites are touched.

**Browser verify:** on a fresh account or one with no analysis history, Performance page reads sensibly without em-dashes.

**Risk:** zero.

**Commit message:** `fix(performance): plain-English empty state replaces em-dashes (BUG-23)`

---

**End of Phase B.** Three commits (B2 deferred to Phase D). Smoke-click after Phase B:
- Alerts header matches real unread count
- Performance page reads correctly with no signals
- No invisible dead button in DOM

---

## 5. PHASE C — WATCH ECOSYSTEM

Three fixes. Tied together by data + UI.

### C1. Watch DELETE endpoint actually deletes (BACKEND)

**File:** `app.py` — DELETE handler on `/api/watch`

**Current behaviour:** POST creates a watch; the row appears in `/api/watches`. DELETE with the exact same body returns 404 "not_found" but the row stays. Verified live 2026-05-02.

**Investigation required first:**
1. Read the DELETE handler in `app.py`
2. Identify how it looks up the watch (by what key, in what data store)
3. Compare with how POST stores the watch
4. Find the mismatch

**Hypothesis:** POST and DELETE compute the lookup key from different inputs, or DELETE queries a Redis cache that is stale.

**Path A verification:** create a watch via test client, delete it via test client, query /api/watches via test client. After fix: count goes from N → N+1 → N.

**Risk:** medium. If the lookup logic is shared with `/api/watches` GET, a wrong fix could break the list.

**Commit message:** `fix(watch): DELETE actually removes the row`

---

### C2. Watch cards show "Invalid Date" (FRONTEND)

**File:** `static/index-v2-prototype.html` — watch card render in `dvLoadWatchAlerts` or `_alRender`

**Current behaviour:** All watch cards show `Invalid Date` even though the API returns properly formatted strings like `"2026-04-25 17:10 UTC"`. Verified live 2026-05-02.

**Change:** the format `"YYYY-MM-DD HH:mm UTC"` is not parsable by `new Date()`. Either:
1. Backend changes to ISO 8601: `"2026-04-25T17:10:00Z"` (preferred — universal parse)
2. Frontend parses the existing format manually

Pick option 1 if the backend is changed cleanly. Pick option 2 if the format is exposed in too many places.

**Path A or B verification depending on choice:**
- Option 1 (backend): test client GETs /api/watches, confirms `added_at` is ISO 8601
- Option 2 (frontend): grep for the date-format helper, fix the parse

**Browser verify:** Alerts page watch cards show real human-readable date.

**Risk:** option 1 may break other consumers of the same string. Search for `added_at` in source first.

**Commit message:** `fix(watch): added_at is ISO 8601 (or: frontend parses the existing format)`

---

### C3. Add Remove button on watch cards (FRONTEND)

**File:** `static/index-v2-prototype.html` — watch card template

**Current behaviour:** Each watch card has only Acknowledge and Dismiss buttons. There is no Remove / Stop watching / Delete button. Verified live 2026-05-02.

**Change:** add a third button "Remove" that calls a new helper `removeWatch(ticker, timeframe, asset_type)` which POSTs to `/api/watch` with DELETE method and the proper body.

**Dependency:** C1 must ship before C3 (the DELETE endpoint must work first).

**Path B verification:**
- Grep for the watch card template in source
- Confirm the new `Remove` button only appears on watch-style cards, not on notification-style cards

**Browser verify:** click Remove on a watch → card disappears, /api/watches GET reflects the deletion.

**Risk:** low.

**Commit message:** `feat(alerts): Remove button on watch cards`

---

**End of Phase C.** Three commits. Smoke-click:
- Add a watch → it appears in the list with a real date
- Click Remove → the watch is gone from /api/watches
- Acknowledge / Dismiss still behave as before

---

## 6. PHASE D — REMOVE CONTEXT FROM PIPELINE (decision: Option 2 + delete page)

Six commits, executed in this order.

### D1. Remove Context from the sidebar

**File:** `static/index-v2-prototype.html`

**Change:** find the sidebar `Pipeline` section. Remove the `Context` nav item entirely. The remaining pipeline items are: Market, Signal, Scanner, Understand, Size, Act.

**Path B verification:**
- Grep for `setNav('context')` and `showContext` in source — count occurrences
- Confirm the sidebar nav-item HTML for Context is the only block being removed in this commit
- Confirm no breadcrumb anywhere depends on Context being in this nav

**Browser verify:** sidebar shows 6 pipeline items, no Context.

**Commit message:** `feat(nav): remove Context from sidebar pipeline (BUG-05)`

### D2. Step counter normalization

**File:** `static/index-v2-prototype.html`

**Change:** find every `STEP \d+ OF \d+` and `Step \d+ of \d+` string. Standardize denominators to 5. Update Signal footer from "Step 2 of 6" to "Step 2 of 5". Confirm Market = "Step 1 of 5", Signal = "Step 2 of 5", Understand = "Step 3 of 5", Size = "Step 4 of 5", Act = "Step 5 of 5".

**Path B verification:**
- Grep `STEP \d OF \d` and `Step \d of \d` — list every match
- Confirm each match is on the right page

**Commit message:** `fix(footer): step counters use 'of 5' on every page`

### D3. BUG-17 — Footer label "Check Context → UNDERSTAND" cleanup

**File:** `static/index-v2-prototype.html`

**Change:** Signal page footer text "Check Context → UNDERSTAND" becomes "Next: UNDERSTAND" or just "→ UNDERSTAND". The button onclick stays `setNav('understand'); showUnderstand()`.

**Path B verification:**
- Grep "Check Context" — confirm one match on Signal page footer
- After change, grep "Check Context" — must return zero matches

**Commit message:** `fix(footer): drop 'Check Context' mislabel (BUG-17)`

### D4. Delete Context page from the front-end

**File:** `static/index-v2-prototype.html`

**Change:** delete the `showContext` function definition. Delete `ctxSetMode` and `ctxIpoAnalyse` helpers. Delete the Context view div from the HTML. Delete any `onclick="showContext()"` references found anywhere.

**Path B verification:**
- Grep `showContext`, `ctxSetMode`, `ctxIpoAnalyse`, `setNav('context')` — list every match
- Each match must be removed
- Confirm no other function still calls into Context helpers

**Commit message:** `chore: delete orphaned Context page and helpers`

### D5. Surface "Pre-Trade Gate" GO/WAIT inline on Signal

**File:** `static/index-v2-prototype.html`

**Change:** Context's only meaningful function was the "Pre-trade gate · GO / WAIT" verdict per trade type. The same data is already shown on Market via mode cards. Add a single-line banner at the top of the Signal page that surfaces the current trade-type's GO/WAIT status:
- "GO — Day Trade window open" / "WAIT — thin market, hold off" etc.

This preserves the user-value Context was supposedly providing, without the orphaned page.

**Path B verification:**
- Confirm the banner reads from the same UTC-driven mode logic Market uses
- Confirm the banner is hidden if no signal is loaded yet (no false context)

**Commit message:** `feat(signal): inline pre-trade gate banner replaces Context page`

### D6. Database / API cleanup

**File:** `app.py`

**Change:** if there's any backend route that exists only to serve Context (likely none — Context renders client-side), audit and decide. There is no Context-specific backend route per the audit's route inventory.

If `bug-10` IPO list was sourced from a backend endpoint, remove that endpoint too. Per the audit, the IPO list was hardcoded in the frontend HTML, not from an API.

**Path A verification:** grep `app.py` for any `context` route handler — confirm none exists or remove if found.

**Commit message (only if backend has Context-specific routes):** `chore(api): remove unused Context routes`

---

**End of Phase D.** 5–6 commits. Smoke-click:
- Sidebar shows 6 items, no Context
- Top breadcrumb still 5 steps
- Every footer reads "of 5"
- No "Check Context" anywhere
- No 404 from any prior link to Context
- Signal page shows the new pre-trade banner

---

## 7. PHASE E — FAKE DATA REPLACEMENT

Every item in this phase is its own commit. Do not bundle.

### E1. Fear & Greed (Market page)

**Current:** static `47` in the HTML.

**Options:**
- Add backend endpoint `/api/fear-greed` that proxies a real source (CNN F&G, Alternative.me crypto F&G)
- Or remove the F&G gauge entirely and replace with a meaningful real metric

**Recommendation:** add the proxy endpoint, cache 5 min in Redis. Crypto-F&G from Alternative.me is free and stable.

**Commit message:** `feat(market): real Fear & Greed from Alternative.me`

### E2. Sector Strength (Market page)

**Current:** Technology 72, Healthcare 58, Real Estate 39 — hardcoded.

**Options:**
- Compute sector strength from sector ETFs' relative price changes (XLF, XLK, XLV, XLE, etc.) — call /api/prices on these tickers and rank by 1d change
- Or remove the panel until a real source is wired

**Commit message:** `feat(market): sector strength from sector-ETF price changes`

### E3. S&P 500 Heatmap (Market page)

**Current:** 14 stocks with hardcoded percentages.

**Options:**
- Compute percentages from /api/prices for the 14 tickers
- Or expand to a real S&P heatmap using a paid data source

**Commit message:** `feat(market): heatmap percentages from real prices`

### E4. Economic Calendar (Market page)

**Current:** /api/econ-calendar returns empty array; page silently falls back to hardcoded list (NFP 09:30, ISM 10:00, Powell 14:00, etc.).

**Options:**
- Fix /api/econ-calendar to return real events from a free source (Forex Factory, Trading Economics free tier, or scraping a published calendar)
- Or remove the panel until a real source is wired

**Commit message:** `feat(market): real economic calendar from <source>`

### E5. Live Momentum Windows (Market page)

**Current:** RDDT, NOTCOIN, ALAB, MEMEFI — all fake/stale tickers.

**Options:**
- Replace with a real "trending tickers" panel powered by a real source
- Remove the panel

**Commit message:** `feat(market): real trending tickers panel`

### E6. Context IPO list

**Current:** RDZN, ALAB, LPSN, FROG hardcoded.

**Options:**
- Wire to a real IPO calendar source (ICE, NASDAQ public feed)
- Or remove the panel

**Note:** if Phase D Option 2 was chosen and Context is removed entirely, this commit is unnecessary.

**Commit message:** `feat(context): real IPO list from <source>` OR `chore: remove Context IPO list`

### E7. News page

**Current:** entirely fake / stale (NVIDIA $26B from May 2024, Tesla robotaxi from Aug 2024, ETH Dencun from March 2024).

**Options:**
- Wire a real news source: NewsAPI.org free tier, or RSS aggregation from Bloomberg / Reuters / FT
- Or replace the page with an empty state ("News feed coming soon · powered by [source]")

**Recommendation:** start with empty state in this phase, then a follow-up commit wires the real source. Removing fake news first prevents misleading users while the real source is being built.

**Commit message (sub-commit 1):** `chore(news): empty state until real source is wired`
**Commit message (sub-commit 2):** `feat(news): real news feed from <source>`

### E8. Sign-in landing marketing stats (12,400+ / 73.4% / $2.1B)

**Current:** hardcoded marketing copy. Same `73.4%` as in-app Avg Confidence.

**Decision:** if these numbers are accurate marketing claims, keep them but add fine-print disclaimer ("as of [date]"). If they're aspirational placeholders, replace with non-numeric copy.

**Commit message:** `docs(landing): real or removed — pick one`

---

**End of Phase E.** 8+ commits. Smoke-click after each E commit individually — fake data replacement is the most boring kind of risk.

---

## 8. PHASE F — WIRE EVERYTHING FOR REAL + TIER GATING

This phase makes the app match what it shows users. Two big tracks: **F1** (wire every Settings sub-panel + every other piece of theatre) and **F2** (build the tier-gating system end to end).

---

### F-prep. Backend foundation: UserSettings table + per-user preferences API

Before any individual setting can be wired, the backend needs a place to store per-user settings persistently. localStorage is per-device — preferences must follow the user across browsers and survive logout/login.

**File:** `app.py`

**Change:**
1. Add a SQLAlchemy model `UserSettings` keyed by `user_id` with columns matching the existing `dv_sett_*` localStorage keys plus the alert-threshold sliders:
   - `assets_enabled` (JSON: ["crypto","stocks","forex","commodity","index"])
   - `risk_tolerance` (string: "conservative" | "moderate" | "aggressive")
   - `chart_theme` (string)
   - `chart_type` (string: "candles" | "bar" | "line")
   - `grid_style` (string)
   - `indicator_scheme` (string)
   - `timezone` (string: e.g. "America/New_York")
   - `alert_confidence` (int: minimum signal confidence for an alert)
   - `alert_price_pct` (float: % move that triggers a price alert)
   - `alert_drawdown_pct` (float: drawdown % that triggers a panic alert)
   - `alert_loss_pct` (float: daily loss % that triggers the circuit breaker)
   - `perf_target_winrate` (int)
   - `perf_target_rr` (float)
   - `perf_target_trades` (int)
   - `perf_target_annual` (float)
   - `portfolio_alloc` (JSON: {"crypto":30,"stocks":30,"forex":20,"commodities":10,"indices":10})
   - `portfolio_preset` (string: "conservative" | "balanced" | "aggressive")
   - `portfolio_rebalance` (string: "monthly" | "quarterly" | "yearly")
   - `portfolio_benchmark` (string: ticker)

2. Add `/api/settings` GET — returns the current user's UserSettings row (creates a default row on first call)
3. Add `/api/settings` POST — accepts a partial JSON of the keys above and persists them
4. On first user login (or any session where UserSettings row doesn't exist), seed with sensible defaults

**Path A verification:** test client POSTs partial settings, GETs back, confirms persistence.

**Commit message:** `feat(api): /api/settings GET/POST persists user preferences server-side`

---

### F1. Wire each Settings sub-panel for real

Each sub-panel below is its own commit. Frontend calls `/api/settings` on load, populates from server values, and POSTs on save.

#### F1.1 Connections — already real (no work)

MT5 EA secret + Telegram bot token already use Railway env vars at the EA/worker level. The on-screen form fields, however, currently only save to localStorage and aren't read by the backend. **Decision needed:** is the on-screen form supposed to let users enter their own MT5 / Telegram credentials per-user? If yes, wire to backend. If the keys are global (one DotVerse-controlled MT5 EA), the form should be read-only or removed.

**Provisionally:** assume per-user secrets (since the page asks for them). Wire to UserSettings columns `mt5_api_key`, `telegram_bot_token`, `telegram_chat_id`. Encrypt at rest using the existing EncryptionKey table.

**Commit message:** `feat(settings): Connections form persists per-user MT5/Telegram credentials`

#### F1.2 Asset Preferences

**Currently:** saves `dv_sett_assets: ["stocks","forex"]` to localStorage. Signal feed scans 6 hardcoded crypto tickers regardless.

**Wire:** modify `/api/scan-list` to accept an `assets` param. Frontend passes the user's `assets_enabled` from `/api/settings`. Backend filters its scan universe to only those classes.

**Browser verify:** select "stocks" only in Asset Preferences → Signal feed shows only stock tickers; deselect crypto → no BTC/ETH cards.

**Commit message:** `feat(scanner): respect user's Asset Preferences`

#### F1.3 Risk Tolerance

**Currently:** saves `dv_sett_risk: "conservative" | "moderate" | "aggressive"`. Backend ignores.

**Wire:** the existing 65% confluence gate in `get_analysis` becomes per-user:
- Conservative: minimum 85% bull/bear consensus to fire BUY/SELL (else HOLD)
- Moderate: minimum 75%
- Aggressive: minimum 65% (current default)

`get_analysis` reads the user's `risk_tolerance` from UserSettings and applies the appropriate threshold.

**Browser verify:** switch from Aggressive → Conservative → most signals downgrade to HOLD. Switch back → signals return.

**Commit message:** `feat(signals): risk-tolerance threshold gates BUY/SELL`

#### F1.4 Chart Visuals (Theme, Chart type, Grid, Indicator scheme)

**Currently:** saves keys but no chart actually reads them.

**Wire:** the LightweightCharts options in `_lwcCommonOpts` (Understand chart, Backtest equity curve, Portfolio charts) read from the user's UserSettings on chart init. Theme switches the candle colours. Chart type switches between candle / bar / line series. Grid style switches major/minor grid line style. Indicator scheme switches the colour palette for EMA20/50/200, MACD, etc.

This is multiple commits because it touches multiple chart implementations. One commit per chart surface.

**Commit messages:**
- `feat(chart): Understand chart respects user theme + type`
- `feat(chart): Backtest equity curve respects user theme`
- `feat(chart): Portfolio charts respect user theme`
- `feat(indicators): per-user colour scheme on chart overlays`

#### F1.5 Performance Settings

**Currently:** saves performance targets (winrate, rr, trades, annual). Backend ignores.

**Wire:** Performance page renders user's targets as goal lines on the equity curve. KPI tiles show actual vs target with "on track" / "behind" badges.

**Commit message:** `feat(performance): user-defined targets shown vs actual`

#### F1.6 Portfolio Settings

**Currently:** saves allocation %, preset mode, rebalance frequency, benchmark, cadence. Backend ignores.

**Wire:** Portfolio page shows the user's target allocation alongside actual. Rebalance suggestion fires when actual drifts >5% from target. Benchmark line on the equity chart.

**Commit message:** `feat(portfolio): target allocation + rebalance suggestions`

#### F1.7 Alert Thresholds

**Currently:** saves four sliders (confidence, price, drawdown, loss). Backend ignores.

**Wire:** the alert-firing worker (`run_watch_job`, `_job_market_alert`) reads each user's UserSettings:
- Don't fire signal alerts below `alert_confidence`
- Don't fire price alerts below `alert_price_pct` move
- Fire panic alert at `alert_drawdown_pct` drawdown
- Trigger circuit-breaker (pause autonomous trading) at `alert_loss_pct` daily loss

**Commit message:** `feat(alerts): per-user thresholds gate alert firing`

#### F1.8 Timezone & Hours

**Currently:** saves `dv_sett_tz`. Backend and frontend both display UTC everywhere.

**Wire:**
- Frontend: every visible timestamp (header clock, signal `fired_at`, watch `added_at`, notification `created_at`, EA order `time`) renders in the user's timezone
- Backend: notification scheduling respects user's "active hours" (don't push at 3 AM local)

**Commit messages:**
- `feat(ui): all timestamps render in user timezone`
- `feat(notifications): respect user's active hours`

---

### F1-extra. Other theatre items (per Omar's "everything wired for real")

Pieces of the app that look functional but aren't, beyond the Settings page:

#### F1-X1. Beginner / Advanced toggle

**Currently:** sets body class `tier-beginner` or `tier-trader`. Only 9 elements in the DOM use `data-tier` attribute, so the toggle barely changes anything.

**Wire:** audit every advanced UI surface (Kelly Criterion, ATR multiplier inputs, indicator weight sliders, raw API data panels) and gate them behind `data-tier="trader,pro"`. Beginner mode actually hides all the jargon. Advanced mode reveals them. Make the toggle a real progressive-disclosure switch.

**Commit message:** `feat(ux): Beginner/Advanced toggle is a real progressive disclosure`

#### F1-X2. Strategy Lens buttons on Backtest

**Currently:** Order Block / Supply & Demand / Retracement / Pullback / Breakout / Liquidity buttons only filter the displayed text commentary. They don't change the backtest computation.

**Wire:** each lens runs the backtest with strategy-specific entry/exit rules:
- Order Block: enter on retest of last bullish/bearish order block
- Supply & Demand: enter on pullback to nearest unmitigated zone
- Retracement: enter on Fibonacci 38.2/50/61.8 retracements
- Pullback: enter on EMA9/EMA21 retests
- Breakout: enter on prior-day-high/low breaks with volume confirmation
- Liquidity: enter on liquidity sweeps (stop-hunts) at session highs/lows

Each lens produces a different equity curve and different win-rate stats. This is real engineering work — each strategy needs implementation in `app.py` and a routing parameter in `/api/backtest`.

**Commit message:** `feat(backtest): strategy lens runs the strategy, not just commentary`

#### F1-X3. Sign-in landing marketing stats (12,400+ / 73.4% / $2.1B)

**Currently:** hardcoded.

**Wire:**
- "Signals Fired" reads from a daily aggregate query on the SignalHistory table
- "Avg Accuracy" reads from a daily aggregate of confirmed signals' actual win rate
- "Volume Tracked" reads from a daily aggregate of MT5 order notional value, or removed if there's no real source

If real data isn't compelling, replace with non-numeric copy ("AI-powered · MT5-integrated · Beginner-first") rather than fake numbers.

**Commit message:** `fix(landing): real stats or non-numeric copy (no fake numbers)`

#### F1-X4. EA online/offline indicator size

**Currently:** EA status is a 7px dot, visually buried.

**Wire:** when EA disconnects, surface a prominent banner across the top of Act page: "EA disconnected — last seen 8 minutes ago". When connected, a small "EA · CONNECTED" pill stays visible in the dashboard header.

**Commit message:** `feat(ea): prominent online/offline banner on Act page`

---

### F2. Tier gating — full implementation

#### F2.0 Tier definitions (BLOCKING — see "Open questions" at end)

Cannot start F2 commits until Omar defines what each tier (Free / Pro / Elite) includes. See open questions.

#### F2.1 Backend tier-aware decorator

**File:** `app.py`

**Change:** add a `@require_tier(['pro', 'elite'])` decorator that, when applied to a route, returns 402 Payment Required + `{"error": "Pro tier required", "upgrade_url": "/pricing#pro"}` for Free users.

Apply the decorator to the routes the tier definitions specify as Pro+ or Elite-only.

**Path A verification:** test client with a Free user gets 402 on a Pro-only route; Pro user gets 200; Elite user gets 200.

**Commit message:** `feat(tier): @require_tier decorator + 402 upgrade response`

#### F2.2 Frontend tier-aware UI

**File:** `static/index-v2-prototype.html`

**Change:** every UI surface that shows a Pro+ feature reads the user's tier on load. Free users see a "🔒 Pro" badge on locked features and a tooltip "Upgrade to unlock". Clicking the locked feature opens an upgrade modal that links to /pricing.

**Commit message:** `feat(ui): tier locks visible on Pro+ features for Free users`

#### F2.3 Pricing page (`/pricing`)

**File:** `app.py` route + new template

**Current:** /pricing is a static 27KB HTML page. Verify what's there before deciding if it needs a rewrite.

**Change:** if not already, build a real pricing page showing the three tiers with feature lists matching F2.0 definitions, with upgrade CTAs.

**Commit message:** `feat(pricing): real pricing page matching tier definitions`

#### F2.4 Stripe / payment integration

**File:** `app.py` + new route group

**Change:** add `/api/checkout/create-session` (POST), `/api/checkout/webhook` (POST from Stripe), `/api/checkout/portal` (GET — billing portal). Use Stripe checkout sessions for subscription. Webhook updates `User.tier` on `checkout.session.completed` event.

**Path A verification:** test client mocks a webhook → user tier upgrades.

**Risk:** medium-high — payment integration requires real Stripe keys, real webhook URL, real test mode.

**Commit messages:**
- `feat(billing): Stripe checkout session creation`
- `feat(billing): Stripe webhook updates user tier`
- `feat(billing): customer billing portal`

#### F2.5 Tier change as admin

**File:** `app.py` + admin panel

**Change:** the existing `/api/admin/set-tier` already exists per the audit. Verify it works correctly. Add `/api/admin/set-tier` audit log so admin tier changes are tracked.

**Commit message:** `feat(admin): tier-change audit log`

#### F2.6 First-visit tier modal

**Currently:** on fresh localStorage, user sees "How do you trade? · Beginner / Trader / Pro" — but that's the **view-mode toggle**, not the **subscription tier**. Two different concepts using overlapping language. This is confusing.

**Change:**
- Rename the first-visit modal to "What's your experience level? · Beginner / Trader / Pro" with descriptions that talk about UI complexity, not subscription
- Remove any implication that picking "Pro" gives them Pro-tier access
- The actual subscription tier comes from Stripe

**Commit message:** `fix(onboarding): separate experience-level from subscription tier`

---

### F3. portfolio_std math investigation (unchanged from prior plan)

**Current:** /api/var returns portfolio_std 0.5476 (54.76% daily) — implausibly high.

**Investigation steps:**
1. Read the std calculation in `app.py` near `/api/var`
2. Trace how returns are sourced (252-day daily? annualized? log returns?)
3. Compute std manually for the same 2 positions in a Python script
4. Identify the scaling error

**Most likely:** annualized std reported as daily.

**Commit message:** `fix(var): correct daily std scaling`

### F4. Notification cron deduplication (unchanged)

**Current:** /api/notifications has duplicate IDs at the same UTC second.

**Fix:** unique constraint on (user_id, type, title, created_at) OR dedup check in worker before insert.

**Commit message:** `fix(cron): dedup market-open notifications`

### F5. Data-source resilience (unchanged)

**Current:** all 5 sources currently failing per /api/diag.

**Two-part fix:**
- Operator alerting via Telegram when ≥3 sources fail
- User-facing "data from cache" badge

**Commit messages:**
- `feat(ops): alert when ≥3 data sources fail`
- `feat(ui): cache-staleness badge on data-driven pages`

---

**End of Phase F.** Approximately 20–25 commits. Smoke-click after each Settings sub-panel commit and after each tier-gating commit individually — these are the highest-risk, highest-blast-radius changes.

---

## 9. PHASE G — POLISH

Lowest priority. Each is its own commit.

### G1. Mobile responsive — add 1024px and 1440px breakpoints

CSS already has 480 / 600 / 760 / 768. Missing 1024 (tablet landscape) and 1440 (laptop). Audit the layout at each breakpoint, add scoped media queries.

### G2. Light theme

No `(prefers-color-scheme: light)` rules anywhere in CSS. Build a real light theme that respects user preference, OR document that DotVerse is dark-only and add a manual toggle if needed.

### G3. `prefers-reduced-motion`

Currently only 3 selectors respect it. Audit ticker-tape animation, max-height transitions, glow effects. Add reduced-motion variants.

### G4. Touch targets and focus rings

Audit the layout for sub-44px touch targets. Add `:focus-visible` rules globally.

### G5. ARIA labels and roles

Currently no aria-labels on interactive elements. Audit by tab/button category; add labels.

### G6. Inline styles consolidation

1,200 inline style attributes. Extract to scoped classes for predictability and CSP-compatibility.

### G7. Deep linking via history.pushState

Currently URL never changes. Add deep-link support so users can bookmark "Signal · BTC-USD · 4h" directly.

---

**End of Phase G.** 7+ commits. None are urgent.

---

## 10. WHAT THIS PLAN WILL NOT DO

- Will not bundle multiple fixes into one commit.
- Will not edit shared CSS rules. New CSS goes in scoped, isolated rules.
- Will not "improve" adjacent code while in a fix.
- Will not push without explicit user approval at the diff gate AND the push gate.
- Will not promise to be careful. Will only state mechanical actions and observable verifications.
- Will not start Phase D before the Context decision is made.
- Will not start Phase F before each architectural decision is made.
- Will not add features the user did not request.
- Will not refactor code the user did not ask to refactor.
- Will not delete pre-existing dead code (other than `sfFooterNext`, which is in scope).

---

## 11. ROLLBACK STRATEGY

Per fix:
- Each commit is reversible with `git revert <hash>`.
- No squash merges in this plan — every fix has a discrete commit.

Per phase:
- Phase boundaries are smoke-click checkpoints with the user.
- If a phase introduces a regression, revert all phase commits with `git revert <first..last>`.

Per session:
- Capture starting hash in `/tmp/dotverse_pre_plan_state.txt` before any commit.
- If a session goes off the rails, `git reset --hard <starting hash>` (warn if commits are pushed; revert via PR instead).

---

## 12. SCOPE NOT IN THIS PLAN

These are documented but require user decisions or are out of scope:
- BUG-11 multi-UTC-hour observation (needs hours of running app)
- Mobile rendering on real devices (needs hardware)
- iOS Safari 100vh behaviour
- Cross-browser testing (Firefox / Edge / Safari)
- Screen reader testing (needs SR + tester)
- EA outage mid-trade scenarios (needs running EA + intentional disconnect)
- Memory leaks under realistic load (needs load test rig)

These don't appear in any phase because they cannot be done from a Chrome MCP browser. They go in a separate "real-device QA pass" run before any production launch.

---

## 13. ESTIMATED EFFORT (revised after decisions)

- **Phase A** (ship-stoppers): 1 session of ~2 hours · 5 commits
- **Phase B** (display lies): 1 session of ~2 hours · 3 commits (B2 deferred → handled in Phase D)
- **Phase C** (watch ecosystem): 1 session of ~3 hours · 3 commits
- **Phase D** (Context removal): 1 session of ~2 hours · 5–6 commits
- **Phase E** (fake data replacement): 3–5 sessions of ~2–3 hours each · 8+ commits
- **Phase F-prep** (UserSettings table + /api/settings): 1 session of ~2 hours · 1 commit
- **Phase F1** (wire all 8 Settings sub-panels): 8–10 sessions of ~2–3 hours each · ~12 commits
- **Phase F1-extra** (Beginner/Advanced toggle, Strategy Lens, marketing stats, EA banner): 4–6 sessions · ~5 commits
- **Phase F2** (tier gating end-to-end including Stripe): 6–10 sessions · ~8–10 commits
- **Phase F3–F5** (std math, cron dedup, data-source resilience): 2 sessions · ~4 commits
- **Phase G** (polish — mobile / a11y / light theme): 4–6 sessions · ~7 commits

**Total realistic effort: 30–45 focused sessions.**

That's the honest number after the F1 scope expansion (wire EVERY panel) and F2 expansion (full tier gating including Stripe, pricing page, billing portal). Anyone telling you it's faster is overpromising.

If a faster MVP is needed, the cuts I would suggest (in order):
1. Defer Phase G entirely (mobile + a11y + light theme = 4–6 sessions saved)
2. Defer Strategy Lens real-implementation (F1-X2) — keep the buttons cosmetic with a "Coming soon" hover; saves 4–5 sessions
3. Defer Stripe integration to a follow-up release; ship tier-gating with manual admin tier-grant first; saves 3–4 sessions

Even with all three cuts, the floor is ~18–25 sessions for a credible "every visible thing actually works" build.

---

## 14. OPEN QUESTIONS — ALL ANSWERED 2026-05-02

All five open questions are now answered. Q1, Q3, Q4, Q5 designed by Claude (binding unless Omar overrides specific points). Q2 answered by Omar directly.

- **Q1 — Tier definitions and pricing:** see "DESIGN DECISIONS — D1" above. Free / Pro $39 / Elite $99. Generous Free with caps that force serious traders to upgrade. Pro unlocks MT5 EA + unlimited everything. Elite adds optimisation, priority data, API access.
- **Q2 — Connections ownership:** per-user. Encrypted at rest. See "D5".
- **Q3 — EA outage strategy:** layered escalation. 5-tier timeline from 60s yellow banner → SMS at 15min → ops alert at 5+ simultaneous outages. See "D2".
- **Q4 — News source:** Finnhub (stocks/forex/indices/commodities) + CryptoCompare (crypto). Free tiers, well-documented APIs. See "D3".
- **Q5 — Trending tickers definition:** "recent listings (≤30d) showing strong momentum" — score = `pct_gain × log(1 + volume_today/avg_volume)`. Sources: CoinGecko trending + NASDAQ IPO feed. See "D4".

**The plan now has zero blockers. Every phase can execute.**

Recommended execution sequence:

1. **Today/this week:** Phases A → B → C → D (~12–15 commits, ~4–5 sessions). Ship-stoppers, display lies, watch ecosystem, Context removal. No blockers, all small commits.
2. **Next:** F-prep (UserSettings table + /api/settings) (~1 commit, ~1 session). Foundation for F1.
3. **Next:** F1.2 → F1.8 + F1-extra (wire each Settings panel + theatre items) (~17 commits, ~12–14 sessions).
4. **Next:** F2 tier gating (~10 commits, ~6–8 sessions). Tier definitions are now fixed so this is unblocked.
5. **In parallel where possible:** Phase E fake-data replacement (~8 commits, ~3–5 sessions). News (E7) + trending tickers (E5) now have concrete sources.
6. **Last:** F3, F4, F5 (std math, cron dedup, data resilience) (~4 commits, ~2 sessions).
7. **Optional final:** Phase G polish (~7 commits, ~4–6 sessions). Mobile, a11y, light theme.

**Total: 30–45 sessions of focused work for the full final-build.**

---

**End of plan.** This document is the operating spec. Reference it before every commit. Every fix below the surface depth "1 of 1" is its own conversation gate. The decisions captured at the top are now binding scope.
