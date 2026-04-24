# DotVerse — Claude Working Protocol

---

# [PROJECT CONTEXT]

## Project Overview
- **App:** DotVerse — trading signals SaaS
- **Backend:** Flask / Python on Railway
- **Frontend:** Single-file `static/index.html` (~12,000+ lines), vanilla JS + inline CSS
- **Database:** PostgreSQL (metro.proxy.rlwy.net:46116, sslmode=disable)
- **Cache / Queue:** Redis (metro.proxy.rlwy.net:20577)
- **Worker:** RQ Worker — second Railway service, same codebase, `rq worker` start command
- **Deploy:** `git push origin main` → Railway auto-deploys web service
- **Quantverse PWA:** Netlify — drag `quantverse-pwa/` folder into Netlify deploy section

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

---

### SESSION HANDOFF NOTES — 2026-04-14 (Win badge, TP precision, scanner TF click, amber glow)

**All changes committed. Deploy: `git push origin main` → Railway auto-deploys.**
**NOT YET runtime verified — user must push and test.**

**Key commits this session:**
- `5eaca75` — Win badge colours, amber glow all buttons, scanner pre-screen label, calculator % note
- `7e62e6c` — TP level precision for low-price assets + scanner TF cell click fix

---

**Win badge — commit `5eaca75` — code complete, NOT YET runtime verified:**
- All 3 paths updated: `renderResultsV2`, `renderSignal(d)`, and backtest path (~line 9266).
- New class system: `wb-high` (≥55%), `wb-mid` (45–54%), `wb-low` (<45%).
- Animated bar fill (`#winRateBar`) via CSS transition on `width`.
- `@keyframes wbPop` spring entrance on every update.
- HTML: `<div class="win-badge" id="winRateBadge">` + `wb-bar-track` + `wb-bar-fill` + `wb-lbl` + `winRateSample`.

**Amber glow — commit `5eaca75` — code complete, NOT YET runtime verified:**
- `.gpill:not(.active):hover` — added `box-shadow` glow (was missing from prior hover glow pass).
- `.nav-tab:hover` — added `box-shadow` glow (prior rule only had `background` change, no glow).
- `.btn-primary`, `.btn-ghost`, `.rb-btn`, `.scan-filter-btn` already had glow from prior session.

**Calculator % of account — commit `5eaca75` — code complete, NOT YET runtime verified:**
- Added `<div id="tradeSizePctNote">` below Trade Size input.
- `recalc()` updates it immediately when `tradeSize > 0 && acct > 0` — no entry price required.
- Shows `= X.X% of your account` in amber mono text.

**Scanner pre-screen label — commit `5eaca75`:**
- Multi-TF table header now shows: "Signals shown are TradingView pre-screens. Click a cell → Run Full Analysis for DotVerse verdict."
- Expand panel button renamed "Run Full Analysis →" and shows disclaimer note below it.
- Root cause of "buy in scanner shows sell in signals": scanner uses `pre_screen()` (TV-based, no confluence gate). Full `doAnalyze` uses DotVerse's 65% confluence gate. Both correct — different algorithms. UX label sets expectations.

**TP level precision — commit `7e62e6c` — code complete, NOT YET runtime verified:**
- Root cause: `round(price, 2)` for all prices < $100 caused TP1 and TP2 to collapse to same displayed value for cheap altcoins (e.g. $0.25 asset with ATR 0.003: TP1=0.244→0.24, TP2=0.2395→0.24).
- Fix: adaptive decimal places via `prnd` lambda: `>=$100` → 2dp, `>=$1` → 4dp, `>=0.01` → 6dp, `<0.01` → 8dp.
- Applied to all 3 TP blocks: `get_analysis()` (lines ~2065–2087), `get_watch_signal()` (lines ~2412–2433), `detect_counter_trade()` (lines ~1395–1408).

**Scanner TF cell click fix — commit `7e62e6c` — code complete, NOT YET runtime verified:**
- Root cause: `<tr onclick="scannerLoadTicker()">` competed with `<td onclick="event.stopPropagation();scannerExpandTF()">`. Inline `stopPropagation()` silently lost the race to the row handler in some browser contexts → every cell click navigated to signals (1H default) instead of expanding.
- Fix: removed onclick entirely from `<tr>`. Ticker name column `<td>` now handles "go to signals" click (dotted underline hint). TF column `<td>`s handle "expand detail" click — no stopPropagation needed, zero conflict.
- Also: `scannerLoadTicker` now calls `syncPillsFromSelect('timeframe')` after setting `tfEl.value`, so the gpill active state matches the loaded TF.

**Scanner TF expand flow (how it works after fix):**
1. User clicks ticker name → `scannerLoadTicker(ticker, tickerAt)` → signals tab, default TF.
2. User clicks a TF cell (e.g. 4H BUY) → `scannerExpandTF()` → inline detail row toggles open below.
3. Detail row shows: ticker · TF, signal badge, RSI, EMA trend, bull%, reason snippet, "Run Full Analysis →" button.
4. "Run Full Analysis →" → `scannerLoadTicker(ticker, at, tf)` → signals tab on THAT exact TF.

**Known architecture note — scanner vs full analysis discrepancy:**
- Scanner `signal_hint` = TV recommendation OR custom net_bull/net_bear score (no confluence gate).
- Full `doAnalyze` = DotVerse 65% confluence gate on own indicators.
- BUY in scanner can legitimately become SELL in full analysis. Not a bug. Label added to UI.

**Deploy verification checklist:**
- [ ] Run market scanner (All Instruments or crypto preset)
- [ ] Click a TF cell → expand row should appear inline, not navigate
- [ ] Click "Run Full Analysis →" → signals tab opens on correct TF (not always 1H)
- [ ] Analyze a cheap altcoin (e.g. AVAX, MATIC, price < $1) → TP1, TP2, TP3 should show distinct values with 6dp
- [ ] Win badge: run backtest → badge should colour green/amber/red with animated bar fill
- [ ] Hover over gpill buttons and nav tabs → amber glow should be visible
- [ ] Hover over instrument chip buttons (BTC, ETH, AAPL etc) → amber glow visible

**Amber glow follow-up — commit `62e019c`:**
- Root cause of missing glow on ticker chips: `.inst-chip:hover`, `.sq-btn:hover`, `.bt-ticker-btn:hover` all had amber border/colour changes but no `box-shadow`. Prior glow pass only covered btn-primary, btn-ghost, rb-btn, scan-filter-btn, gpill, nav-tab.
- Fix: added `box-shadow` to all three missed hover rules.

**Amber glow REAL root cause — commit `0c83d6c`:**
- `updateInlineInst()` (line ~3481) generated `<button>` elements with inline `onmouseover="this.style.borderColor='var(--orange)';this.style.color='var(--orange)';"` and `onmouseout` handlers. These JS-written inline styles completely override CSS, so the `.inst-chip:hover` box-shadow CSS rule never applied.
- Additionally used `var(--orange)` not `var(--amber)`.
- Fix: stripped all inline style, onmouseover, onmouseout from the button template. Buttons now use only `class="inst-chip"`. All hover effects (glow, border, colour) handled purely by CSS `:hover` rule.

**Scanner TF expand data lookup — commit `0c83d6c`:**
- Root cause: `resJson = encodeURIComponent(JSON.stringify(...))` embedded in onclick HTML attribute. `encodeURIComponent` does NOT encode `'`, `(`, `)`, em-dashes. Reason strings from backend contain these characters — they silently truncate the onclick attribute, causing `scannerExpandTF` to receive corrupted or empty data → always showed first-TF (15M) data or nothing.
- Fix: store all scan data in `window._smtfData[ticker].tfs[tf]` at render time. `scannerExpandTF(ticker, tf, rowId)` — no JSON param — looks up data from the store. onclick attributes only carry simple `ticker` and `tf` strings which are always safe.

---

### SESSION HANDOFF NOTES — 2026-04-14 (RR $0 fix + scanner pill buttons)

**RUNTIME VERIFIED by user on 2026-04-14. Commit `ec4f263`.**

**RR section $0 display fix:**
- Root cause: `moneyAtRisk = 0` when no account/risk entered → `posSize = 0` → `netProfit = 0` → "+$0 net" rendered in all TP rows and RR bar.
- Fix: 3-line conditional change in `recalc()`. Lines 10412, 10455, 10471 — show "—" instead of "$X" when `moneyAtRisk === 0`. RR ratios and pip distances untouched.

**Scanner TF pills — converted to real buttons:**
- Root cause: `.scan-mtf-pill` was a plain `<div>` inside a clickable `<td>`. No hover state, no cursor change. Felt like the whole row was clicking.
- Fix: Changed to `<button>` element with direct `onclick="scannerLoadTicker(ticker, at, tf)"`. Each badge navigates straight to Signals on that exact TF. Removed `onclick` from `<td>`. Added hover glow CSS for buy/sell/hold states.

---

### SESSION HANDOFF NOTES — 2026-04-14 (Scanner full analysis upgrade)

**All changes committed. Deploy: `git push origin main` → Railway auto-deploys.**
**RUNTIME VERIFIED by user on 2026-04-14. Commit `ca432bc`.**

**Scanner full DotVerse analysis — RUNTIME VERIFIED:**

**Root cause of prior scanner/signals discrepancy:**
- Scanner used `pre_screen(ind, tv=tv)` — TradingView recommendation OR simple net_bull/net_bear score. No 65% confluence gate. No entry/SL/TP levels.
- Full signal used `get_analysis()` — DotVerse's full 65% confluence gate, asset-specific settings, entry/SL/TP from ATR.
- BUY in scanner could legitimately become SELL on signals tab. Different algorithms, not a bug.

**Fix applied:**
- `/api/scan-list` endpoint — both TV primary path and yfinance fallback: replaced `pre_screen()` with `get_analysis(ticker, asset_type, ind, timeframe, tv=tv)`.
- Backend result dict now contains: `signal`, `entry`, `stop_loss`, `tp1`, `tp2`, `tp3`, `rr1`, `rr2`, `rr3`, `confidence`, `confidence_label`, `bull_score` (mapped from `bullish_count`), `bear_score` (mapped from `bearish_count`), `reason` (mapped from `summary`).
- Removed `signal_hint`, `opportunity`, `call_claude` from response (pre_screen-specific fields).
- `sort_key` updated: sorts BUY/SELL first, HOLD last (was sorting by `call_claude` and `opportunity` which no longer exist).
- `confidence` is now a string ("HIGH"/"MEDIUM"/"LOW") not a number. `filterScanResults` highconf filter updated to check `r.confidence === 'HIGH'`.

**Frontend changes:**
- `renderScanResults` (single-TF): `r.signal_hint` → `r.signal`. Pill labels simplified to BUY/SELL/HOLD. Entry/SL/TP1 shown as sub-text below badge in signal cell.
- `renderScanResultsMultiTF`: header text updated ("Full DotVerse analysis. Click any TF cell..."). `res.signal_hint` → `res.signal`. `window._smtfData` store now includes `entry`, `stop_loss`, `tp1`, `tp2`, `tp3`, `rr1`, `conf_lbl`.
- `scannerExpandTF`: expand panel now shows ENTRY / STOP LOSS / TP1 / TP2 / TP3 in dedicated level blocks. Confidence label shown next to signal badge. "Pre-screen (TV)" disclaimer removed. Button renamed "Open on Signals →".
- `filterScanResults`: `r.signal_hint` → `r.signal`. `pillMatchesFilter` simplified (no POSSIBLE_BUY, COUNTER_BUY etc.). Highconf: `parseInt(r.confidence) >= 65` → `r.confidence === 'HIGH'`.

**Architecture note — `_narrate_data_openai` in scanner:**
- `get_analysis()` calls `_narrate_data_openai()` at the end. This function checks for OpenAI API key first — if not configured, it returns immediately without any LLM call. The scanner loop remains pure Python math. No additional latency introduced by this change.

**Deploy verification checklist:**
- [ ] Run market scanner (All Instruments or crypto preset, any TF)
- [ ] Single-TF results: BUY/SELL/HOLD badges with Entry/SL/TP1 sub-text below badge
- [ ] Multi-TF results: cells show BUY/SELL/HOLD (no POSSIBLE_BUY/CTR etc.)
- [ ] Click a TF cell → expand row shows ENTRY / STOP LOSS / TP1 / TP2 / TP3 levels
- [ ] Expand row signal matches what Signals tab shows for same ticker + TF (both now use DotVerse 65% gate)
- [ ] Scanner BUY filter shows only BUY signals (no POSSIBLE_BUY, CTR etc.)
- [ ] High Confidence filter shows only signals where DotVerse confidence = HIGH

---

### SESSION HANDOFF NOTES — 2026-04-14 (Scanner/Signals signal mismatch — RESOLVED)

**Status: RESOLVED — runtime verified by user on 2026-04-14.**

**Root cause (two layers):**
- Layer 1 (Gate 2): footprint sanity check in `get_analysis()` ran in analyze (which enriches `ind` with yfinance OHLCV) but was silently skipped in scanner (scanner uses `build_ind_from_tv` only, no chart arrays). Gate 2 could downgrade TV-sourced BUY → HOLD. Fixed by adding `if not tv_signal_used` guard to Gate 2. Commit `41046cb`.
- Layer 2 (TV timing): scanner and analyze fetch TV data at different moments. If TV was unavailable at scan time (scanner fell back to yfinance → HOLD), Redis cache was never written. When user clicked "Open on Signals →" seconds later, TV became available → TV override → BUY. Fix: scanner caches its final computed signal in Redis (`scanner_signal:{raw}:{tf}`, 300s TTL) on both TV and yfinance paths. Analyze reads this and overrides signal fields after building response. Chart, MTF, indicators stay fresh from analyze. Also extended TV cache TTL 120s → 300s. Commit `48d7c7a`.

**Key commits:**
- `41046cb` — Gate 2 `if not tv_signal_used` guard
- `48d7c7a` — Scanner signal cache (scanner_signal Redis key, analyze override, TV TTL 300s)

**Protocol addition this session — SELF-CHECK LOOP:**
Claude must never wait for the user to ask "how sure are you?" before reassessing confidence. The self-check loop runs continuously during investigation: keep digging until the root cause is confirmed, then verify in sandbox, then present the plan. Only then ask for commit confirmation. If confidence is below 90%, state the gap explicitly and keep investigating before proposing.

---

### SESSION HANDOFF NOTES — 2026-04-14 (Scanner/signals mismatch RESOLVED + protocol hardened)

**Status of all known bugs:**
- BUG 1 (RSI divergence trendlines): RESOLVED
- BUG 2 (Scanner zero-width chart): RESOLVED
- BUG 3 (doAnalyze called directly): RESOLVED
- BUG 4 (backtest missing login_required): RESOLVED
- Scanner/Signals signal mismatch: RESOLVED — commit `48d7c7a`, runtime verified by user 2026-04-14

**All five phases: COMPLETE and verified.**

**Protocol changes this session:**
- Universal three-path runtime verification added to CLAUDE.md (Path A backend, Path B frontend, Path C config)
- Visible gate check required in every response before any tool call
- Self-check loop rule: Claude must investigate fully and self-assess confidence continuously — never wait for user to prompt "how sure are you?"

**Deploy:** `git push origin main` → Railway auto-deploys.

**Next session:** No pending bugs. If new work is requested, run Six Stop Gates before starting.

---

### SESSION HANDOFF NOTES — 2026-04-14 (Protocol discipline additions)

**Additional protocol rules added this session — NON-NEGOTIABLE:**

**STOP FILLING SILENCE:**
- Do not add unsolicited commentary after completing a task. If the user says "save to CLAUDE.md" and it is saved, say nothing else. Do not summarise what was saved. Do not list contents. Do not mention push, deploy, or next steps unless asked.
- Every word after the task is done is noise unless the user asked for it.

**ACT AFTER THINKING, NOT BEFORE:**
- Before any response involving tool calls: think fully, trace the problem, reach a conclusion. Only then respond.
- Do not start tool calls while still forming the hypothesis. Investigation must complete before proposing.
- Do not respond to a question by immediately reaching for tools. Reason first, visibly, in the response.

**SELF-CHECK LOOP — MANDATORY:**
- During any investigation: keep digging until confidence is above 90%. Do not stop at a plausible theory. Do not surface a hypothesis as a plan.
- Do not wait for the user to ask "how sure are you?" — ask it of yourself after every conclusion before presenting it.
- If confidence is below 90%: state the gap, state what is still unknown, keep investigating.

**NO NOISE AFTER COMMIT:**
- After committing: state the commit hash and one line summary. Stop. Do not add deploy instructions, feature checklists, or next steps unless asked.

**Next session:** No pending bugs. Run Six Stop Gates before starting any new work.

---

### SESSION HANDOFF NOTES — 2026-04-23 (Protocol hybrid refactor)

**CLAUDE.md refactored into hybrid system — not a code change, protocol only.**

Structure: [PROJECT CONTEXT] → [KARPATHY MINDSET] → [EXECUTION & SAFETY GATES]

Changes from prior version:
- MANDATORY MINDSET section removed and replaced by [KARPATHY MINDSET] (4 Karpathy principles verbatim)
- Gate 3 enhanced: every plan must now include Success Criteria + Tradeoff Assessment before user can confirm
- Quick Reference table: two new rows added (After task complete / Simplicity check)
- Self-Audit Rule: second paragraph added (simplicity check)
- Project Overview section added at top of [PROJECT CONTEXT]
- All existing rules, paths, bugs, and handoff notes preserved verbatim

**Protocol addition — pushing CLAUDE.md to Railway is never required.**
CLAUDE.md is a local working protocol file. It lives in the repo but controls Claude's behaviour only. Never push CLAUDE.md changes to Railway as a standalone deploy action — Railway deploys are for app code only.

---

# [KARPATHY MINDSET]

Behavioral guidelines to reduce common LLM coding mistakes.
**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding
**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First
**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes
**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution
**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# [EXECUTION & SAFETY GATES]

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

**Gate check — VISIBLE IN EVERY RESPONSE before any tool call:**
Before every single action, write this line in the response:
Gate 1 — asked? Gate 2 — root cause known? Gate 3 — plan confirmed? Gate 4 — certain or assuming? Gate 5 — risks stated? Gate 6 — verification level?
If this line is missing before a tool call, the gate was skipped. This makes thinking visible and auditable without the user needing to read code.

**Gate 3 — Plan Confirmation — requires ALL FOUR before the gate opens:**
1. **The change** — exactly what will be modified and why
2. **Success Criteria** — what does DONE look like? How will it be verified?
3. **Tradeoff Assessment** — why is this the simplest path? What alternatives were considered and rejected?
4. **Risk Statement** — what could break, and how will that be caught?

A plan missing any of these four elements is not a confirmed plan. Gate 3 is not open.

**Before every fix — Claude must state all five or the gate does not open:**
1. The problem
2. The root cause
3. The exact change and why
4. What could break
5. How it will be verified

**Task discipline:** One task at a time. Fully closed before the next opens.

**Runtime verification protocol — MANDATORY FOR EVERY FIX — THREE PATHS:**

Before touching any code, identify what type of fix it is. Follow the correct path.

---

**PATH A — Backend fix (Python, Flask, app.py)**

Install all dependencies first: `pip install -r requirements.txt --break-system-packages --quiet`

Write a small Python test in the bash sandbox that imports the real functions directly from app.py. Never simulate or rewrite the logic:
```python
import sys, os
sys.path.insert(0, '/path/to/trading-signals-saas')
os.environ.setdefault('SECRET_KEY', 'test')
os.environ.setdefault('DATABASE_URL', '')
os.environ.setdefault('REDIS_URL', '')
from app import [the functions relevant to the bug]
```
Reproduce the exact bug first using the exact asset type, ticker, timeframe, and input values the user described. Use the boundary value that triggers the bug — not an obvious value that always passes. The output must show the failure. If it does not fail the bug is not reproduced — stop, do not proceed, find out why first.

Apply the fix in the same script and run it again. The output must change from failing to passing:
```
BEFORE FIX: [output showing the bug]   match=False
AFTER FIX:  [output showing it fixed]  match=True
```
If both show match=True the bug was never reproduced. Start over.

After the test passes, end with:
```
SANDBOX VERIFIED: [functions tested, exact inputs, scenarios, boundary values]
NOT VERIFIED:     [mocked services — live API, Redis, database, Railway env]
RESIDUAL RISK:    [what could still fail in production and why]
```

---

**PATH B — Frontend fix (JavaScript, CSS, HTML)**

Sandbox verification is not possible for frontend fixes.

Before touching any code: state every element ID and function name being changed. Grep to confirm each one exists in both the HTML and the JS. Confirm no other component shares the same class or ID. Confirm no CSS change affects adjacent components.

End with:
```
SANDBOX VERIFIED: not possible — frontend fix
CODE REVIEW DONE: [IDs checked, JS references checked, CSS side effects checked]
RESIDUAL RISK:    [what could break — adjacent components, shared classes, layout]
```

---

**PATH C — Configuration fix (Procfile, requirements.txt, Railway env vars)**

Sandbox verification is not possible for configuration fixes.

Before touching any config: state exactly which line is changing, what the current value is, what the new value is, and what breaks in production if the change is wrong. If changing requirements.txt confirm no package conflicts. If changing Railway env vars confirm the variable name matches exactly what the code reads.

After deployment confirm the Railway service started cleanly and is showing healthy status before doing anything else.

End with:
```
SANDBOX VERIFIED: not possible — configuration fix
CONFIG REVIEW DONE: [exact line changed, old value, new value, conflict check]
RESIDUAL RISK:    [what fails if wrong, how quickly visible after deploy]
```

---

**All three paths then follow these steps without exception:**

Ask the user before committing. Ask again before pushing. Two separate gates. State what was verified and the residual risk, then ask: "Shall I commit?" Wait for yes. Then ask: "Shall I push?" Wait for yes. Never do either without explicit confirmation.

After deployment, give the user plain browser steps to confirm the fix. No logs. No terminal. No code. Only what a non-technical person can do on screen. Only after the user confirms in the browser, mark the fix RESOLVED in CLAUDE.md with today's date.

---

**Strict definitions — these never change:**

SANDBOX VERIFIED — Python test using real app functions showed fail then pass with exact scenario and boundary values.
CODE REVIEW DONE — frontend or config change traced through every reference, no sandbox test possible.
FULLY VERIFIED — either of the above plus user confirmed in live browser.
RESOLVED — fully verified only, never before.
RUNTIME VERIFIED — never means the code looks right. That is Level 4 code reading. Always state which level was reached.

---

**What can never be sandbox verified — state this on every fix touching these:**

Live API responses, Redis cross-process caching, database queries, and Railway networking cannot be replicated locally. For any fix touching these write: "This path cannot be sandbox verified. Logic tested only. Residual risk: [specific risk]. Browser test that catches it: [exact step]."

---

**Mid-task message rule — NON-NEGOTIABLE:**

When the user sends a message while work is in progress, stop all tool calls immediately, read the message fully, respond to it, then ask whether to continue. Never keep executing after a user message arrives.

**You hold the gate:** If any element is missing, the gate does not open.

**The Clarifying Question Rule — NON-NEGOTIABLE:**
A plan that contains any unanswered behaviour question is NOT a confirmed plan. Gate 3 is not open.
Before writing any plan, identify every behaviour question — *"when X happens, should it do A or B?"* — and ask them explicitly, one at a time, before proposing the plan. User saying "you already stated the plan" or "proceed" without answering a specific behaviour question is NOT confirmation of that behaviour. Stop and ask the specific question. Speed is not a virtue here. One wrong assumption costs more time than the question would have.

---

## CORE RULES — NON-NEGOTIABLE

### UI Integrity — NON-NEGOTIABLE
- **The UI must never be broken, damaged, or visually degraded by any change.**
- Before every commit: grep for all new/changed element IDs and confirm each one exists in BOTH the HTML and the JS that writes to it.
- Before every commit: grep for any IDs removed from HTML and confirm no JS still references them.
- CSS changes must be checked for unintended side-effects on adjacent components.
- If a change touches shared CSS classes, explicitly confirm all components using that class still render correctly.
- "I only changed X" is never sufficient — always verify downstream.

### Branding Icons — NON-NEGOTIABLE
- **Never use emoji as icons anywhere in the UI.** Emoji render inconsistently across platforms and break visual consistency.
- All icons must be inline SVG only — stroke-based, no fill, matching the app's existing icon style.
- Icon colours must follow the B-ORE palette: amber `#d4870a` for neutral/action icons, green `#3dbe6c` for positive/safe features, red `#e05555` for destructive/risk features.
- Default stroke-width: `2.2` for body icons, `2.5` for small inline button icons.
- Before every commit involving new UI elements: grep for any emoji characters (`🔍`, `🔔`, `📊`, `⚡`, `💰`, `📈`, `🔒`, or any Unicode emoji) and replace with SVG.
- This rule applies to all locations: HTML template strings, JS-generated innerHTML, section headers, card labels, button text, and toast/coaching messages.

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
| After task complete | State what was done. Stop. No unsolicited commentary. |
| Simplicity check | Could 200 lines be 50? Could a new function reuse an existing one? |

---

## SELF-AUDIT RULE
After writing any fix, re-read the original user requirement and ask:
**"Have I verified this works at runtime, or only that the code looks correct?"**
Static code analysis is not verification.

Also ask: **"Is this the simplest correct solution? Could it be meaningfully shorter without losing correctness?"** Complexity that cannot be justified is a bug.
