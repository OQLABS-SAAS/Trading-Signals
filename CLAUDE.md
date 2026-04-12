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

### SESSION HANDOFF NOTES — 2026-04-13 (Phase 2 start)

**Phase 1: COMPLETE — runtime verified. All known bugs resolved.**

**Phase 2 — Signal Quality (app.py only, no new infrastructure):**
All five items to be implemented sequentially. Each must be committed and runtime verified before moving to the next.

- 2a: Per-asset NaN strategy — `dropna()` for stocks/indices/forex. Crypto: bad-tick filter (price = 0, or close > 10× rolling median of last 20 bars → replace with median). Applied in `calculate_indicators` after DataFrame is received.
- 2b: Spike filter — bar-to-bar % change > 3× ATR20 flagged, replaced with 20-bar rolling median. Applied before indicators run. Exemption: stocks on earnings dates (if identifiable — skip for now, add note).
- 2c: Smoothed ATR + 4× stop — ATR14 smoothed over 100-bar rolling mean. Replace 1.5× stop multiplier with 4×. Applied in stop/TP calculation section.
- 2d: Net RR after fees — 0.2% round-trip deducted from every TP1/TP2/TP3 calculation. Applied after ATR stop is computed.
- 2e: Forward-fill date grid — build expected timestamp grid per timeframe before accepting source data, reindex with ffill, cap at 3 consecutive fills max. Stocks: exclude weekends from grid. Applied in `_build_chart_output` or at top of `calculate_indicators`.

**Risks stated before implementation:**
- 2a: Threshold for crypto bad-tick too aggressive → real flash moves removed. Mitigation: use 10× rolling median, not absolute value.
- 2b: Spike filter clips genuine gap-ups (earnings). Mitigation: flag only, log, do not silently discard without trace.
- 2c: 4× stop widens SL — reduces signal frequency on short timeframes. Expected and acceptable.
- 2d: All three TP levels must get fee deduction — not just TP1.
- 2e: Weekend exclusion for stocks requires asset_type detection before grid construction.

**Verification level for Phase 2:** Level 4 (code reading) until Railway deploy + user confirms in browser.

**Next session — start here:**
Say "Protocol active." Re-read this file. Begin Phase 2, item 2a. Read `calculate_indicators` in `app.py` first. State exact insertion point. Get confirmation. Then implement.
