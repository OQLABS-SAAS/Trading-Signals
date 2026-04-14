# DotVerse — Claude Working Protocol

---

## THE SIX STOP GATES
### Answer every gate before touching anything. One NO = full stop.

| Gate | Question | If NO |
|---|---|---|
| 1 | Was I explicitly asked to do this? | Stop. Report. Ask. |
| 2 | Can I state the symptom, root cause, and mechanism? | Investigate first. No fix yet. |
| 3 | Have I written a valid plan and got explicit confirmation? | Write plan. Wait. |
| 4 | Am I certain or assuming? | Label it. Tell user. Ask to proceed. |
| 5 | Have I stated what could go wrong? | State risks now. |
| 6 | Is this verified at runtime or only code reading? | State Level 4. Do not claim verified. |

---

## WORKING AGREEMENT

**Before every session:** User says "Protocol active." Claude reads the six gates before responding to anything.

**Before every fix — Claude must state all five or the gate does not open:**
1. The problem
2. The root cause
3. The exact change and why
4. What could break
5. How it will be verified

**Task discipline:** One task at a time. Fully closed before the next opens.

**You hold the gate:** If any of the five are missing, reject it.

---

## MANDATORY MINDSET
- Think before acting — not act then explain
- Break complex tasks into substeps
- Show plan before executing
- Anticipate edge cases and dependencies
- Document as you go
- Provide status updates
- Verify against the original requirement

**Approach: Thorough → Systematic → Planned → Executed → Verified**

---

## CORE RULES — NON-NEGOTIABLE

### Bug Reports
- Do NOT open files immediately
- Do NOT start grepping
- First: reason out loud about the full user flow affected
- Then: identify what you need to verify before forming a conclusion
- Then: look at code to verify, not to fix

### Scope Discipline
- State precisely which files will be changed and why
- State precisely what will NOT be changed
- If a new issue is discovered mid-task: STOP — report it, ask whether to include it
- Never expand scope mid-task without explicit user approval
- One confirmation = one scope

### Feature Preservation — NON-NEGOTIABLE
- **Never remove any existing feature unless the user explicitly asks for it by name.**
- Before every commit, run a mental checklist of all known features and verify none have been accidentally removed.
- Known DotVerse features to check before every commit:
  - Auto-refresh (OFF / 15s / 30s / 1m / 5m / 15m buttons + spin indicator)
  - Signals tab: analyze, chart, indicators, MTF, RSI divergence trendlines
  - Scanner tab: scan all, scanner table, click-to-analyze
  - Backtest tab: run backtest, Pine Script (ATR research script)
  - Simulation tab: scenario cards, trade plan
  - Calculator: account, my trade, leverage, entry/SL/TP fields, RR bar, guidance coach
  - Journey panel: 5-step What To Do Next
  - Portfolio: positions table, VaR, stress test, correlation heatmap, optimisation
  - Watch/alert: toggleWatch, DotVerse alert
  - Fear & Greed, Latest News, Scenarios sidebar panels
- If a change touches a section of the page near any of the above, explicitly confirm the feature still renders after the edit.
- "I only changed X" is not sufficient — side-effects in shared CSS, JS scope, or HTML structure can silently break adjacent features.

### Understanding Before Acting
- Never assume intent — restate the requirement in your own words before starting
- If the instruction is ambiguous, ask one clarifying question before proceeding
- Do not infer scope from similar past tasks — treat every task as new

### Verification Hierarchy
"Verified" has a strict definition. In descending order of reliability:
1. **Runtime proof** — observed behaviour in a running browser/server
2. **Console/log evidence** — instrumentation confirming value or code path at execution time
3. **Execution trace** — manually stepping through every branch with real data values
4. **Code reading only** — weakest form; must be labelled "unverified assumption" when used

Static code analysis (grep, read, eyeball) is Level 4. Never sufficient alone for a bug fix. Always state which level of verification was used.

### Confidence Labelling
Every conclusion must carry an explicit label:
- **CONFIRMED** — verified at runtime or with instrumentation
- **LIKELY** — full execution trace completed, no contradicting evidence
- **HYPOTHESIS** — reasoning from code reading, not yet traced
- **UNCERTAIN** — incomplete information, state what is missing

Never present a hypothesis with the same tone as a confirmed fact.

### Completion Criteria
A task is only "done" when:
1. The fix is in the file (not just stated)
2. A verification method was stated and executed
3. The original requirement was re-read and matched
4. The user was told which verification level was reached

### Session Resume Rule
- Treat any context summary as a starting point, not ground truth
- Re-read relevant source files before forming any opinion
- Never state a conclusion about code behaviour based on summary alone
- If summary says something was fixed, verify it is actually in the file

### The "I Already Know This" Rule
Prior context, similar bugs, or pattern recognition never substitutes for tracing the current problem fresh. Every bug gets a full trace from scratch. Assumptions built on memory are the most common source of wrong fixes.

### Investigation Gate
For any task requiring more than 3 tool calls to investigate:
1. State the investigation plan upfront
2. List what questions need answering and how
3. Get user go-ahead before starting
4. Report findings before proposing fixes

Do not silently investigate then present conclusions and fixes together as if the investigation was obvious.

---

## QUICK REFERENCE — KEY RULES BY SITUATION

| Situation | Rule |
|---|---|
| Bug reported | Don't open files. Reason out loud first. |
| Session resumed | Re-read source files. Summary is not ground truth. |
| Ambiguous instruction | Ask one clarifying question. Do not infer. |
| Investigation needed | State plan. Get go-ahead. Report findings first. |
| Fix fails | Do not silently try another fix. Stop and report. |
| Architectural change | State all downstream effects before touching anything. |
| Long task | Break into substeps. Confirm scope at each stage. |
| Code copying | State what the code does before pasting it. Verify it fits. |
| Risk dismissal | Never skip risk statement. "Low risk" must be argued, not assumed. |
| Fix proposal | Five elements required: problem, root cause, change, risk, verification. |
| Before every commit | Run feature checklist. Confirm nothing was accidentally removed. |
| Feature removal | Only if user explicitly names the feature. Never as a side-effect. |

---

## SELF-AUDIT RULE
After writing any fix, re-read the original user requirement and ask:
**"Have I verified this works at runtime, or only that the code looks correct?"**
Static code analysis is not verification.

---

## KNOWN BUGS — READ THIS FIRST EVERY SESSION

These are unresolved bugs confirmed by the user. Do not mark any as fixed until runtime verified in a live browser.

---

### BUG 1 — RSI Divergence Trendlines Not Rendering
**Status:** RESOLVED — runtime verified by user on 2026-04-12. Deployed to Railway.
**Fix summary:** RSI panel height increased 90px → 160px. Flat-line guard added (if y-spread < 5px, draw at midpoint y). Pivot dot radius increased 3.5px → 5.5px. Root cause was sub-pixel line height due to small RSI value differences on tiny canvas.

---

### BUG 2 — Scanner → Signals Chart Zero-Width (RESOLVED)
**Status:** RESOLVED — runtime verified by user on 2026-04-12. Deployed to Railway.
**Fix summary:** `autoSize: true` in `_lwcCommonOpts`, `requestAnimationFrame` in `scannerLoadTicker`, all scanner entry points now use `scannerLoadTicker`.

---

### BUG 3 — `doAnalyze` Called Directly on 3 Code Paths (RESOLVED)
**Status:** RESOLVED — Phase 1b. `instChipLoad`, `instSwitchGo`, `runAnalyze` in `static/index.html` now route through `scannerLoadTicker`. Committed `a8adf2a`, deployed 2026-04-13.

---

### BUG 4 — `/api/backtest` Missing `@login_required` (RESOLVED)
**Status:** RESOLVED — Phase 1a. `@login_required` added to `backtest_route` in `app.py`. Committed `a8adf2a`, deployed 2026-04-13.

---

### SESSION HANDOFF NOTES — 2026-04-11
- User has been working 20+ hours. RSI divergence trendlines have been reported and "fixed" multiple times with no runtime verification. This is the primary unresolved issue.
- Git push failed due to HTTPS credentials — user must run `git push origin main` manually.
- `renderResults()` (old legacy function, ~lines 3413–3630) is dead code never called from `quickLoad`. Safe to remove eventually but not urgent.
- When user returns: ask them to say "Protocol active", then go straight to BUG 1 investigation — do NOT act before tracing the full render path.

---

### SESSION HANDOFF NOTES — 2026-04-12
**DotVerse (Railway — git push origin main):**
- BUG 1 (RSI divergence trendlines) — RESOLVED, runtime verified by user, deployed.
- BUG 2 (Scanner → Signals zero-width chart) — RESOLVED, runtime verified by user, deployed.
- BUG 3 and BUG 4 still UNRESOLVED — not touched this session.

**Quantverse PWA (Netlify — drag quantverse-pwa/ folder into Netlify deploy section):**
- Replaced 15-indicator TV-style vote engine with 7 strategy engines: Momentum, SMC/ICT, Price Action, Mean Reversion, Volume, Breakout, Harmonic Patterns.
- All signals computed locally from Binance/Frankfurter candles — no backend dependency.
- Strategy tab row added above ticker chips. Ticker chips now trigger on-demand analysis via `analyzeSym(sym)` → `analyzeInstrument(cfg)` → `runStrategy()`.
- Removed all DotVerse backend integration (authCheck, analyzeTicker, mapDvToSig, showOverlay).
- manifest.json and SW registration fixed for Netlify (start_url /, icons /icon-*.png, sw.js at /).
- Bug fixed this session: JSON.stringify in onclick HTML attribute caused SyntaxError on every ticker tap. Fixed by adding `analyzeSym(sym)` wrapper — no JSON in HTML attributes.
- Committed: 0f16861 (full rewrite), 9ee9ad4 (onclick fix).
- Verified at Level 4 (code reading) + user confirmed console errors were resolved after redeploying.

**Deploy reminder:**
- DotVerse: `git push origin main` → Railway auto-deploys.
- Quantverse: drag `quantverse-pwa/` folder into Netlify site's deploy section (NOT git push).

---

### SESSION HANDOFF NOTES — 2026-04-13

**Status of known bugs — unchanged:**
- BUG 3: UNRESOLVED. Lines 3252, 3263, 3317 in `static/index.html` call `doAnalyze` directly.
- BUG 4: UNRESOLVED. `app.py` line 3532 — `backtest_route` missing `@login_required`.

**Research audit completed this session (Level 4 — code reading):**
- Read actual source files in `research/gs-quant`, `research/backtesting.py`.
- Key gs-quant files confirmed: `gs_quant/timeseries/analysis.py` (`smooth_spikes`, `repeat`), `gs_quant/timeseries/datetime.py` (`align`, `union`, `interpolate`), `gs_quant/timeseries/statistics.py` (`zscores`, `winsorize`), `gs_quant/timeseries/helper.py` (`Window`, `apply_ramp`, `get_df_with_retries`).
- Key backtesting.py files confirmed: `backtesting/backtesting.py` (hard NaN gate, DatetimeIndex enforcement, monotonic sort), `backtesting/lib.py` (`resample_apply` — the multi-timeframe alignment pattern using `.reindex(..., method='ffill')`).
- Root cause of DotVerse data corruption CONFIRMED: `_fetch_binance` converts Unix timestamps to formatted strings immediately. `_build_chart_output` operates on position-indexed Python lists. All sources collapse to list position before any indicator runs. One bar offset between TradingView and Binance corrupts every indicator value silently.
- `safe_download` (Yahoo) already returns proper `DatetimeIndex` DataFrame — the fix is to standardise all fetch functions to this shape and rewrite `_build_chart_output` to accept DataFrame not lists.

**Five-phase enhancement plan approved by user — NOT YET IMPLEMENTED:**

PHASE 1 — Stop the Bleeding (app.py + static/index.html, no new infrastructure):
- 1a: BUG 4 — add `@login_required` to `/api/backtest` line 3532. One line.
- 1b: BUG 3 — route lines 3252, 3263, 3317 through `scannerLoadTicker`.
- 1c: Timestamp merge — rewrite `_build_chart_output` to accept DataFrame + DatetimeIndex. Standardise `_fetch_binance` and `_fetch_stooq` to return same shape as `safe_download`. Replace position merge with `combine_first` on timestamps.
- 1d: Minimum bar floor — `len(df) >= 30` → `len(df) >= 51`.

PHASE 2 — Signal Quality (app.py only, no new infrastructure):
- 2a: Per-asset NaN strategy — `dropna()` for stocks/indices/forex, bad-tick removal for crypto.
- 2b: Spike filter — `smooth_spikes` logic from `research/gs-quant/gs_quant/timeseries/analysis.py`. No GS API needed. Self-contained.
- 2c: Smoothed ATR + 4x stop — Wilder ATR14 smoothed over 100-bar rolling mean. Replace 1.5x stop with 4x.
- 2d: Net RR after fees — 0.2% round-trip deducted from every TP calculation.
- 2e: Forward-fill on complete date grid — build expected timestamp grid per timeframe before accepting source data, reindex with ffill.

PHASE 3 — Signal Intelligence (app.py + static/index.html, no new infrastructure):
- 3a: Confluence gate — signal fires only at ≥65% sub-indicator agreement. Below threshold → NEUTRAL.
- 3b: Asset-specific indicator settings — hardcoded per class: Crypto (RSI 10, ATR 5x, EMA 7/14), Forex (RSI 14, ATR 4x, EMA 9/21), Stocks (RSI 14, ATR 4x, EMA 9/21), Indices (RSI 21, ATR 3x, EMA 20/50), Commodities (RSI 14, ATR 5x, EMA 9/21).
- 3c: Position size output — `positionPct` on every signal for 1% account risk.
- 3d: Signal confidence label — CONFIRMED / LIKELY / HYPOTHESIS surfaced on signal card.

PHASE 4 — Infrastructure (Railway add-ons, user provisions before Phase 5 code starts):
- 4a: PostgreSQL Railway add-on. Schema: `positions (id, user_id, ticker, asset_type, size, entry_price, opened_at)` and `optimisation_results (id, asset_class, timeframe, rsi_period, atr_mult, sharpe, computed_at)`.
- 4b: Redis Railway add-on. Used for: OHLCV cache 5-min TTL, cross-asset shared data, task result storage.
- 4c: RQ Worker — second Railway service, same codebase, start command `rq worker` instead of `gunicorn`.

PHASE 5 — Features Unlocked by Infrastructure:
- 5a: Portfolio position tracking — traders log open positions stored in PostgreSQL.
- 5b: Parametric VaR — `VaR = portfolio_value × z_score × portfolio_std` from 252 days returns. No GS API needed.
- 5c: Stress testing — configurable % shock per asset class applied to stored positions, P&L impact computed.
- 5d: Cross-asset correlation dashboard — OHLCV from Redis cache, timestamp-aligned (Phase 1c prerequisite), numpy correlation matrix.
- 5e: Offline parameter optimisation — RQ worker runs backtesting.py grid search per asset class, results written to PostgreSQL, frontend reads recommended settings from there.

**Architecture target:**
```
Flask (Railway) ──→ PostgreSQL   (positions, optimisation results)
                ──→ Redis        (OHLCV cache, task queue, task results)
                ──→ RQ Worker    (backtesting, VaR, stress test jobs)
                ──→ Data sources (Binance, Stooq, Yahoo — cached via Redis)
```

**What is permanently excluded and why:**
- VaR via gs-quant: requires GS API key — open-source layer is interface only, confirmed from source files.
- Arbitrage detection: requires sub-millisecond WebSocket feeds and execution infrastructure. Different product.
- Stress testing without portfolio DB: requires Phase 4a (PostgreSQL) first.

**Session sequencing rule:**
Each phase must be runtime-verified in a live Railway deploy before the next phase starts. User confirms in browser. Claude does not mark a phase complete until user confirms.

**Phase 1 status — RUNTIME VERIFIED by user on 2026-04-13:**
- 1a: DONE + VERIFIED — `@login_required` on `/api/backtest`. Commit `a8adf2a`.
- 1b: DONE + VERIFIED — BUG 3 routed through `scannerLoadTicker`. Commit `a8adf2a`.
- 1c: DONE + VERIFIED — `_build_chart_output` accepts `pd.DataFrame` + `DatetimeIndex`. All 5 callers updated. Commit `a8adf2a`.
- 1d: DONE + VERIFIED — Bar floor `>= 30` → `>= 51`. Commit `a8adf2a`.
- Bonus fix: Fallback `calculate_indicators` on Stooq chart data → RSI divergence trendlines now render for stocks on Railway. Commit `545e090`. Runtime verified by user screenshot 2026-04-13.
- Bonus fix: `renderIndicators` null guard on `macd_hist`, `expandId` wired into card template. Commit `a8adf2a`.

---

### SESSION HANDOFF NOTES — 2026-04-13 (Phase 2 complete, Phase 3 next)

**Phase 1: COMPLETE — runtime verified.**
**Phase 2: COMPLETE — runtime verified by user on 2026-04-13. Commit `5e21bd7`.**

**Phase 2 items — all DONE + VERIFIED:**
- 2a: Per-asset NaN strategy — `calculate_indicators` gains `asset_type` param. Crypto: zeros → NaN, bars > 10× 20-bar rolling median → median. All types: `dropna()`. All 5 callers updated.
- 2b: Spike filter — bars where |close - 20-bar rolling median| / median > 20% replaced with median. High/Low clipped to match. Spike count logged.
- 2c: Smoothed ATR + 4× stop — `atr_raw = rma(tr, 14)`, `atr = atr_raw.rolling(100, min_periods=14).mean()`. Stop multiplier 1.5× → 4.0× at all three sites: `detect_counter_trade`, `get_analysis`, `get_watch_signal`.
- 2d: Net RR after fees — `fee_adj = entry * 0.002`. BUY: `tp -= fee_adj`. SELL: `tp += fee_adj`. Applied before RR calculation in all three TP blocks.
- 2e: Forward-fill date grid — `_fill_date_grid(df, timeframe, asset_type)` helper. Builds expected timestamp grid, reindexes with `ffill(limit=3)`. Weekends excluded for stocks/indices/commodities. Called in `analyze()` and `run_watch_job()` before `calculate_indicators`.

**Phase 3: COMPLETE — runtime verified by user on 2026-04-13. Commit `ef6774f`.**

**Phase 3 items — all DONE + VERIFIED:**
- 3a: Confluence gate — `bull_pct = bullish_count / total_votes`. Signal fires only at ≥65%. Below threshold → HOLD. Existing HTF/footprint/confidence-floor gates remain downstream.
- 3b: Asset-specific settings — `ASSET_CONFIG` dict. `get_rsi()` gains `period` param. `calculate_indicators()` uses per-asset RSI period and EMA fast/slow. Frontend EMA card label updates dynamically from `d.ema_fast_period` / `d.ema_slow_period`.
- 3c: Position size — `position_pct = round(min(entry / risk, 100.0), 1)`. Added to `get_analysis` result dict. Displayed as amber banner above Trade Management Plan.
- 3d: Confidence label — `confidence_label` field in result dict. CONFIRMED (TV used or net≥5) / LIKELY (net≥3) / HYPOTHESIS (weak). Displayed below confidence ring with colour coding and tooltip.

**Phase 4: COMPLETE — runtime verified by user on 2026-04-13. Commit `2417bb1`.**

**Phase 4 items — all DONE + VERIFIED:**
- 4a: PostgreSQL Railway add-on — Online, "Deployment successful". DATABASE_URL injected into web service.
- 4b: Redis Railway add-on — Online. REDIS_URL injected into web service.
- 4c: RQ Worker (Trading-Signals service) — Active, logs confirmed "*** Listening on default..." Commit `2417bb1` added `rq worker` to Procfile and added `redis>=5.0.0`, `rq>=1.16.0`, `psycopg2-binary>=2.9.0`, `sqlalchemy>=2.0.0` to requirements.txt.

---

### SESSION HANDOFF NOTES — 2026-04-13 (Phase 4 complete, Phase 5 next)

**Phase 1: COMPLETE — runtime verified.**
**Phase 2: COMPLETE — runtime verified.**
**Phase 3: COMPLETE — runtime verified.**
**Phase 4: COMPLETE — runtime verified by user on 2026-04-13. Commit `2417bb1`.**

**Phase 5 — next to implement:**
- 5a: Portfolio position tracking — `/api/positions` (GET/POST/DELETE). SQLAlchemy model `Position`. Frontend: position log panel below signal card.
- 5b: Parametric VaR — `VaR = portfolio_value × z_score × portfolio_std` from 252-day returns. `/api/var` endpoint. Cached in Redis 5-min TTL.
- 5c: Stress testing — configurable % shock per asset class applied to stored positions, P&L impact table. `/api/stress` endpoint.
- 5d: Cross-asset correlation dashboard — OHLCV from Redis cache, numpy correlation matrix. `/api/correlation` endpoint. Frontend heatmap.
- 5e: Offline parameter optimisation — RQ job runs grid search per asset class, writes to `optimisation_results` table, frontend reads recommended settings. `/api/optimise` (enqueue) + `/api/optimise/result` (poll).

**Session sequencing rule:** Each phase must be runtime-verified in a live Railway deploy before the next phase starts.

**Phase 5 code: COMPLETE — committed `932b6b1`, `f89eecf`. NOT YET runtime verified.**

**Phase 5 runtime verification BLOCKED by DATABASE_URL issue:**
- Web service (`rare-communication` project) and Postgres/Redis (`exquisite-upliftment` project) are in DIFFERENT Railway projects.
- Cross-project reference variables `${{Postgres.DATABASE_URL}}` resolve to empty string.
- Fix: set DATABASE_URL in web service to the `DATABASE_PUBLIC_URL` value from Postgres service (uses `metro.proxy.rlwy.net` hostname, not `.railway.internal`).
- User attempted fix but DATABASE_URL keeps showing `<empty string>` after deploy.
- User must: Raw Editor → paste actual postgresql://...@metro.proxy.rlwy.net:PORT/railway → save → redeploy.
- REDIS_URL may have same cross-project issue — check after DB is working.

**Phase 5 frontend validation fix:**
- `pfAddPosition()` now reads inputs as strings before parsing (Safari type=number bug). Committed `f89eecf`.
- Ticker field was showing placeholder "AAPL" — user must actually type the ticker.

---

### SESSION HANDOFF NOTES — 2026-04-13 (ALL PHASES COMPLETE)

**Phase 1: COMPLETE — runtime verified.**
**Phase 2: COMPLETE — runtime verified.**
**Phase 3: COMPLETE — runtime verified.**
**Phase 4: COMPLETE — runtime verified.**
**Phase 5: COMPLETE — runtime verified by user on 2026-04-13.**

**Phase 5 items — all DONE + VERIFIED:**
- 5a: Portfolio position tracking — AAPL BUY saved, appeared in table. `/api/positions` GET/POST/DELETE working.
- 5b: Parametric VaR — $246.51 (2.465%) at 95% confidence, Portfolio STD 1.4987%. `/api/var` working.
- 5c: Stress test — AAPL -20% shock → new price $160 → P&L $-100. `/api/stress` working.
- 5d: Cross-asset correlation — heatmap for BTC-USD, AAPL, GC=F, ^GSPC, EURUSD=X. `/api/correlation` working.
- 5e: Parameter optimisation — RQ job enqueued, completed: RSI 10, ATR 2×, EMA 20/50, Sharpe 4.948. `/api/optimise` + `/api/optimise/result` working.

**Infrastructure fixes required this session (cross-project Railway):**
- DATABASE_URL: Postgres and web service in different Railway projects. `${{Postgres.DATABASE_URL}}` resolves to empty string. Fix: use DATABASE_PUBLIC_URL from Postgres service (metro.proxy.rlwy.net:46116) with literal password. `sslmode=disable` required (metro proxy handles TLS at TCP level). The server at port 54321 was MySQL (user had wrong URL). The real Postgres port is 46116.
- REDIS_URL: Same cross-project issue. Fix: use public URL redis://default:PASSWORD@metro.proxy.rlwy.net:20577.
- SSL probe: Added auto-probe loop in app.py (commits `545e4d0`, `3db09f8`) that tests sslmode=disable then sslmode=require with SELECT 1 before committing to connection pool. Logs `[db] Connected with sslmode=X`.

**Key commits this session:**
- `545e4d0` — sslmode=disable fix
- `3db09f8` — SSL auto-probe loop (disable → require fallback)

**ALL FIVE PHASES COMPLETE. Full implementation report generated.**

**Next session — no pending items. System is fully deployed and verified.**
- If new features are needed, run Six Stop Gates before starting.
- PostgreSQL: metro.proxy.rlwy.net:46116 (sslmode=disable)
- Redis: metro.proxy.rlwy.net:20577
- Deploy: git push origin main → Railway auto-deploys web service.

---

### SESSION HANDOFF NOTES — 2026-04-13 (Calculator overhaul + UI fixes)

**Calculator rebuild — commits `f9e9c2d`, `34c7e55` — runtime verified by user:**

Root causes fixed:
- `winRateBadge`/`winRateVal`/`winRateSample` IDs were missing from HTML — `getElementById` returned null silently. Fixed by adding IDs to existing `.win-badge` div.
- `recalc()` showed dollar distances for all asset types. Rewrote to show pips for forex (0.0001, JPY 0.01), points/$ for crypto/stocks.
- `autoFillCalc(d)` — new function. Auto-populates `cEntry`, `cSL`, `cTP1/2/3`, `cAsset` from signal data on every analyze. HOLD-safe (no entry = no overwrite).
- `cVolume` (redundant with `cPosSize`) replaced with `cMarginReq` showing margin = posVal / leverage.
- Net profit after fees added to every TP row: 0.1% round-trip crypto, 0.05% stocks/forex.
- Win rate from `window._lastBt` shown in calculator output (updates after backtest completes).
- Indicator grid orphan card: CSS `:last-child:nth-child(3n+1)` selector — "Trading Activity" now spans full row.

**Strategy buttons — confirmed cosmetic only:**
- They do NOT change the signal. They show a text commentary panel interpreting the existing BUY/SELL result through a strategy lens. No backend recalculation. User was informed. Left as-is.

**Beginner mode — dropped:**
- Three design versions created (V1 Operator, V2 Meridian, V3 Command) but user rejected all. Feature permanently abandoned.

---

### SESSION HANDOFF NOTES — 2026-04-13 (Calculator guidance fix)

**Calculator guidance — commit `5eab9e7` — NOT YET runtime verified (needs git push):**

Problem: `recalc()` had `if (!acct || !risk || !entry || !sl) return` — SL=0 is falsy, so clicking "Calculate Position" with SL field empty did nothing. User saw all dashes, no feedback.

Root cause: Silent return with no user-visible message. Secondary root cause: `window.currentData` undefined — `currentData` is `let` not `var`, so it never attaches to `window`.

Fix (commits `5eab9e7`, `6b244d3`, `dcc553e`):
- Added `<div id="calcGuidance">` panel between "Calculate Position" button and results area.
- Fixed `window.currentData` → `currentData` throughout `recalc()` and `seMode()`.
- Rebuilt entire guidance section as a plain-English step-by-step trading coach for absolute beginners.

**Coaching states — runtime verified by user:**
- No signal: "Run an analysis first — I'll walk you through it step by step"
- HOLD: signal card + "no trade right now" in plain English + what to do next
- Missing account (Step 1): explains what account size means and why
- Missing risk % (Step 2): real dollar examples (1% of $10k = $100, 2% = $200) + beginner 1–2% rule
- Missing entry (Step 3): shows signal entry, explains auto-fill
- Missing SL (Step 4): plain English explanation of stop loss, exact $ loss at SL, amber "Use Signal Stop Loss $X" button that auto-fills and recalculates
- SL wrong side: direction mismatch in plain English
- All valid: coach hides, results show

**Signal card always shown** when signal is loaded: ticker, BUY/SELL/HOLD, entry, SL, TP1/2/3.
**Account footer always shown** when acct + risk filled: "$X at Y% risk = $Z max loss per trade".

**Deploy:** `git push origin main` → Railway auto-deploys.

---

### SESSION HANDOFF NOTES — 2026-04-13 (MTF + My Trade calculator + 1W/1M chips)

**All changes committed. NOT YET runtime verified — needs `git push origin main` then user to test.**

**Calculator: Risk % → My Trade ($) — commit `458493b`:**
- `cRisk` input replaced with `cCapital` ("My Trade ($)") — user enters how much they want to invest.
- Position sizing: `posSize = (capital / assetPrice) * lev`. posVal = capital (exactly what user invests). No more position-exceeds-account problem.
- `autoFillCalc(d)` still populates entry, SL, TP1/2/3 from signal — user only needs to set Account and My Trade.
- Coaching Step 2 updated to show 5%, 10%, 20% of account as dollar examples.
- Capital > account guard added.
- Margin display: `capital / lev`.

**MTF alignment fix — commit `416bc38`:**
- Root cause 1: `get_mtf_trend()` only computed 2 TFs (4H, 1D) via yfinance. All 6 now computed: 15m, 1H, 4H, 1D, 1W, 1M.
- Root cause 2: MTF 1D could show NEUTRAL while main signal showed BUY because EMA stacking ≠ 65% confluence gate. Fixed: after `get_analysis()` returns, MTF entry for the current TF is overridden with the actual signal result.
- `_tf_key_map` + `_sig_to_trend` added to `analyze()` endpoint.
- `get_mtf_trend()` expanded to 6 configs using yfinance at appropriate intervals.
- `TIMEFRAME_CONFIG` in app.py: added `"1w"` (1wk/5y) and `"1mo"` (1mo/10y) entries.

**1W and 1M timeframe chips — commit `b4f4f2d`:**
- Root cause: `gpill` timeframe buttons in the signals control bar (Row 2) only had 15M, 1H, 4H, 1D.
- Backend + hidden select + chart tf-pills already supported 1W/1M but the user had no visible button to select them.
- Fix: added two `gpill` buttons for 1W and 1M in the signals control bar.

**Key commits:**
- `416bc38` — MTF alignment fix + TIMEFRAME_CONFIG 1W/1M + expand get_mtf_trend() to 6 TFs
- `458493b` — Calculator: My Trade ($) replaces Risk %
- `b4f4f2d` — 1W and 1M gpill chips added to signals control bar

**Deploy:** `git push origin main` → Railway auto-deploys.
**Verify:** Click 1W chip → analysis should run on 1W → MTF should show all 6 cells with real data → MTF current TF should match main signal direction.

---

### SESSION HANDOFF NOTES — 2026-04-13 (UX journey + Pine Script exact levels)

**All changes committed. Deploy: `git push origin main`.**

**Pine Script exact levels — commit `f1f4dd6`:**
- `togglePineCode()` now calls `copyPineScript()` when a signal is loaded (instead of static ATR-based PINE_SIGNALS).
- `copyPineScript()` rewritten: hardcodes exact entry, SL, TP1/2/3 from `currentData`. Matches calculator exactly.
- Level lines labelled with 'take 50%', 'take 30%', 'take rest'. Dashboard mirrors signal card. 4 alert conditions generated.
- Backtest tab Pine Script renamed → **"Research Script · ATR-based · for backtesting only · not for live trades"**.

**Guided 'What To Do Next' journey panel — commit `d90e342`:**
- After every signal fires, a 5-step linear panel appears below the signal card.
- BUY/SELL: ① Understand risk → ② Set position → ③ Verify track record (Backtest) → ④ Copy to TradingView → ⑤ Set alerts.
- HOLD: simplified 2-step: wait / try another timeframe.
- Step ③ explains ATR Research Script = historical only. Step ④ explains exact levels = live trade.
- 'Pine Script' button removed from sig-btns — replaced by Step ④ CTA.
- No jargon decisions left for the user.

**UX improvements — commits `1ffb23b`, `e3e9fa3`, `6885448`:**
- Risk vs Reward summary bar: −$80 vs +$109 side by side above TP rows.
- SL label shows actual price: "if price hits $61,638".
- Redundant "Calculate Position" button removed → "RESULTS UPDATE AS YOU TYPE".
- Each RR box expandable: Worst Case explains stop loss in plain English; TP1/2/3 explain scaling out strategy.

**Calculator: My Trade ($) — commit `458493b`:**
- Risk % replaced with My Trade ($). posVal = capital exactly. No position-exceeds-account problem.

**Key commits this session (all unpushed — push together):**
- `416bc38` — MTF alignment + TIMEFRAME_CONFIG 1W/1M
- `458493b` — My Trade ($) calculator
- `b4f4f2d` — 1W/1M gpill chips
- `1ffb23b` — Risk vs Reward bar
- `e3e9fa3` — Remove Calculate button + SL price label
- `6885448` — Expandable RR boxes
- `f1f4dd6` — Exact-levels Pine Script
- `d90e342` — Guided journey panel

---

### SESSION HANDOFF NOTES — 2026-04-14 (Journey panel scroll-to fixes)

**All changes committed, deployed, and runtime verified by user on 2026-04-14.**

**nsScrollTo() — commit `07a692d`:**
- Journey panel step buttons called `nsScrollTo()` but the function did not exist. Added it to `static/index.html`.
- Behaviour: smooth-scrolls to any element by ID. If `expandCalc=true`, expands `calcBody` first then scrolls after 350ms reflow.

**onclick double-quote bug — commit `8bc9c34`:**
- Root cause: `onclick="nsScrollTo("rrAnchor")"` — inner double quotes closed the attribute early. Browser parsed `onclick="nsScrollTo("` and stopped — button was a dead no-op.
- Fix: changed all inner string literals to escaped single quotes (`nsScrollTo(\'rrAnchor\')`).
- Why Backtest and Alert worked: their ctaFn strings had no inner double quotes.

**Scroll into hidden element bug — commit `78eca72`:**
- Root cause: `rrAnchor` and `calcAnchor` are inside `calcBody` which starts collapsed (`display:none`). `scrollIntoView` on a hidden element silently does nothing.
- Fix: `nsScrollTo` now checks if the target is a descendant of `calcBody`. If it is and `calcBody` is collapsed, calls `toggleCalc()` first, waits 350ms for DOM reflow, then scrolls.
- Also removed dead lookup for `calcToggleBtn` (no such ID in the HTML — toggle fires via `onclick="toggleCalc()"`).

**Key commits:**
- `07a692d` — Add nsScrollTo() function
- `8bc9c34` — Fix onclick double-quote truncation on journey panel buttons
- `78eca72` — Fix scrollIntoView no-op on hidden calcBody children

---

### SESSION HANDOFF NOTES — 2026-04-14 (R2 signal history + calculator rebuild)

**All changes committed. Deploy: `git push origin main` → Railway auto-deploys.**

**R1: Mobile responsiveness — COMPLETE (prior session).**

**R2: Signal history log — commit `e8b871b` — runtime verified by user.**
- New `signal_history` Postgres table (auto-created on deploy via `_Base.metadata.create_all`).
- `SignalHistory` model: ticker, asset_type, timeframe, signal, price, entry, stop_loss, tp1, confidence, confidence_label, fired_at.
- Every `analyze()` call saves a row after building `response_data` (fire-and-forget, never blocks the response).
- `/api/signals/history` GET endpoint — returns last 30 signals for current user.
- Frontend: collapsible "Signal History" table inline on signals page (click header to expand). Loads from Postgres on login (`unlockApp()`) and after every analysis (`addToHistory()` calls `loadSigHistory()`). Each row clickable → re-analyzes that ticker.

**Pine Script button restored — commit `70dc6a5`:**
- Button re-added to `sig-btns` area (had been removed in prior session when journey panel was built).
- Calls `copyPineScript()` and scrolls to `pineCodeWrap`.

**R3: Telegram alerts — code already built (prior session). Waiting on user to set Railway env vars:**
- `TELEGRAM_BOT_TOKEN` = bot token from BotFather
- `TELEGRAM_CHAT_ID` = user's chat ID (message the bot, then call getUpdates URL)
- No code changes needed once vars are set.

**Calculator rebuild — commit `44f73ce` — runtime verified by user (EURUSD numbers correct).**

Root cause of old approach: "My Trade ($)" is not how professional traders size positions.

New approach (SonarLab / industry standard):
- `cCapital` (My Trade $) removed. `cRisk` (Risk %) replaces it as a real input.
- `moneyAtRisk = account × (riskPct / 100)`
- **Forex:** `lots = moneyAtRisk / (slPips × pipValuePerLot)`. Pip value per lot:
  - USD-quoted pairs (EURUSD, GBPUSD, AUDUSD): `pipSize × contractSize` → $10/pip per std lot
  - USD-base pairs (USDJPY, USDCHF, USDCAD): `(pipSize / entry) × contractSize`
  - Forex third field changed from "Leverage" to "Contract Size" (Standard 100k / Mini 10k / Micro 1k)
- **Crypto:** `units = moneyAtRisk / slDist` (leverage affects margin display only)
- **Stocks/indices/commodities:** `shares = moneyAtRisk / slDist`
- SL hit always = exactly `moneyAtRisk` by construction.
- Summary bar now shows: **Money at Risk** (amber, prominent) + position size.
- Coaching step 2 updated: explains Risk % with real dollar examples (1% = $X, 2% = $Y, 5% = $Z).
- Added >10% risk warning coaching state.
- `autoFillCalc(d)` still auto-fills entry/SL/TP1/2/3 from signal — user only needs Account + Risk %.

**Key commits this session:**
- `70dc6a5` — Pine Script button restored
- `e8b871b` — R2 signal history log
- `44f73ce` — Calculator rebuild (Risk % lot-size approach)

**Pending:**
- R3: Telegram — set `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in Railway → works immediately, no code needed.
- R4: Tighten signals page layout (not yet started).
