# DOTVERSE — FINAL DETAILED BUILD PLAN (2026-06-10, reconciled)
Single source of truth. Every item: WHAT · WHY · HOW (with code locations) · VERIFY · EFFORT.
Reconciled against current code (prior plans REIMAGINED Tier-0 + IMPLEMENTATION A–F = mostly
already built; confirmed below). Scope: single-user, MT5-only. Gate on every item: commit +
live verification; full pytest green (663) before deploy.

---

# SECTION 0 — RECONCILIATION (prior plans vs CURRENT code) — VERIFIED DONE
- T0.1 fake TV indicators → DONE: `build_ind_from_tv()` returns `ready:false`; supertrend computed (app.py ~2063/2094).
- T0.4 sector bars (was 6 of 10) → DONE: dynamic `r.sectors.map` (index-v2 ~16722).
- T0.5 econ calendar fake fallback → DONE: honest "unavailable" empty-state (~16647).
- T0.6 `/api/simulate` fake probabilities → DONE: `type:educational_demo` + disclaimer (~13807).
- C1 watch DELETE → DONE: `/api/watch` DELETE + `_remove_watch_from_db` (~13636).
- E8 fake sign-in stats (12,400 / 73.4% / $2.1B) → DONE: removed.
- Phase-D Context page → DONE: removed (0 refs to showContext).
- A2 auth → 115 `@login_required` routes.
**Still to verify next pass:** IMPLEMENTATION Phase B (alerts header, dead `sfFooterNext`,
perf em-dash), Phase C2/C3 (watch "Invalid Date", remove button), Phase F (tier gating) —
status unknown, not yet grep-confirmed.

---

# SECTION 1 — ALREADY SHIPPED + LIVE-VERIFIED TODAY (dv-v16)
MT5 connection truth + auto-register · canonical signal count (64=64) · portfolio $37.57=$37.57 ·
Today scan progress · Market tab anti-hang (frontend) · honest scan errors · concentration
warning · scale-out tooltip · ORDER PLACEMENT 3 root causes (no-account-row, missing account_id
column, unquoted `trailing` reserved word aborting all migrations) · Today criteria persist +
seed from Settings · lot-size explainer · error hygiene (no raw SQL) · double-place protection +
4 tests · deep-health + schema-repair endpoints · EA demo/live + login (MODE=DEMO, login 1084284).

---

# SECTION 2 — REMAINING SHIP ITEMS (code-only, no Omar input)

## A1 — Broker-error translator
WHAT: map ~20 MT5 retcodes to plain instructions, surfaced on every failed order.
WHY: tonight Omar stared at `retcode=10017` for 45 min; the app must say what to DO.
HOW: `_mt5_retcode_message(comment,status)` + `_MT5_RETCODE_MESSAGES` dict in app.py; add
  `status_message` to `mt5_get_orders` serialization (~9899); frontend reads `order.status_message`
  in Act tab status + order list (mirror of existing `_dvHumanizeError`). 10017/10027→"Algo
  Trading off — turn it on + reload EA"; 10019→margin; 10018→market closed; 10016→bad SL/TP;
  10014→bad lot; default→human fallback.
VERIFY: fire into current disabled state → Act tab shows instruction, not the code.
EFFORT: ~45 min. STATUS: STARTED (uncommitted local edit, not deployed).

## A2 — Ladder combined totals
WHAT: one canonical basket total (total cash-in, risk, profit target, position value, # MT5
  orders) at the Size ladder confirm modal AND the Size tab footer.
WHY: combined total across legs is missing/inconsistent in Size (Omar's long-standing ask).
HOW: extract `_dvBasketTotals(legs)` from the Today basket math (reuse `_todayLadderTotals`);
  render in `_szConfirmTrade` (~24147) and Size ladder summary; numbers must equal the rows.
VERIFY: build a 3-leg ladder → totals in modal == sum of rows.
EFFORT: ~1 hr.

## A3 — Multi-ladder placement integrity
WHAT: harden N-leg submit: track each leg, report "3 of 4 placed", retry ONLY failed legs.
WHY: a partial ladder failure must be clear + recoverable, not silent.
HOW: per-leg result arrays already exist in `_todaySendOrders` / `_szLadderSubmitGo`; add a
  partial-result panel + failed-leg-only retry; unit-test the leg accounting.
VERIFY: unit test (mock 1 leg failing) + live once terminal allows a fill.
EFFORT: ~1.5 hr.

## A4 — EA self-diagnosis flags
WHAT: EA reports TERMINAL_TRADE_ALLOWED, MQL_TRADE_ALLOWED, ACCOUNT_TRADE_ALLOWED,
  ACCOUNT_TRADE_EXPERT each heartbeat → app shows a one-line banner naming the off switch.
WHY: turns the multi-layer "Trade disabled" hunt into "MetaTrader has automated trading off."
HOW: add 4 ints to EA `PushState()` JSON (DotVerse_EA.mq5 ~358); surface in `/api/mt5/state`
  + a Settings/Act banner. Activates on Omar's next recompile (no recompile needed to build).
VERIFY: code + unit now; live on next recompile.
EFFORT: ~45 min.

## A5 — Audit quick-wins
- Header "TRADING DASHBOARD · —" → real date.
- Demote "Reset All Data" away from "Journal" + add confirm dialog (destructive, prime spot).
- "MT5 UNKNOWN connected" → human phrasing.
EFFORT: ~45 min total.

## #21 — Allocation guidance
WHAT: when actual allocation diverges hard from target (e.g. Forex 100% vs 20% target), show a
  plain action line: "You're 80% over your Forex target — diversify or adjust the target."
WHY: today it shows the divergence with zero guidance (audit finding).
HOW: in the Portfolio allocation render, compare actual vs target %; threshold ≥2x → warn line.
VERIFY: load Portfolio with a skewed allocation → guidance appears.
EFFORT: ~30 min.

## #24 — /api/prices backend stall
WHAT: server-side timeout on the price provider chain so `/api/prices` never hangs.
WHY: today only the frontend recovers; the backend itself can stall (provider chain).
HOW: wrap each provider call in a per-provider timeout; return partial/error fast; never block.
VERIFY: simulate a slow provider → endpoint returns within the cap.
EFFORT: ~1 hr.

---

# SECTION 3 — TRACK D: THE SMC/QUANT ENGINE (the product's brain)
Discipline on EVERY item: **detect → prove on history (vs 1,087-trade baseline, per setup class)
→ only then authority over a live entry.** Today the engine only DECORATES (badges, confidence
points); no structure DECIDES anything. D1–D4 need NO staging/NO MT5 (buildable immediately);
D5 (live entry placement) needs staging.

## D1 — True Order Block detection
WHAT: replace the FVG/liquidity proxy with real OBs = the last opposing candle before a
  displacement move, refined to a zone, with freshness/mitigation/volume metadata.
HOW: in smc_structure.py, on closed bars: find displacement (body>2×ATR, already detected) →
  step back to last opposite-color candle → emit zone [high,low] + flags (mitigated? fresh?
  volume-at-formation). Add "OB freshness" (untested zones score higher).
GATE: backtest "enter on retest of fresh OB" vs single-entry → must beat on avg R + drawdown.
EFFORT: ~1 day build + ~0.5 day backtest.

## D2 — IDM / inducement detection (ZERO today)
WHAT: detect the minor opposing liquidity pool (bait) between price and the true zone; enables
  "wait — price will likely sweep this inducement first, then reverse."
HOW: after a structural swing, scan for a shallow opposing swing / equal-H-L cluster between
  current price and the OB/zone; flag as IDM. Hardest + most subjective → highest evidence bar;
  opt-in, transparent ("we waited because price sat above an inducement level"), never silent.
GATE: "skip/delay entry when an unswept IDM sits between price and zone" must improve fill
  quality + reduce stop-outs.
EFFORT: ~2 days build + backtest (most uncertain).

## D3 — Liquidity-trap AVOIDANCE (detection → protection)
WHAT: at signal time, warn if the planned entry sits ON a liquidity pool / equal-H-L cluster;
  offer "wait for the sweep-and-reclaim, then enter." The protective half missing today (engine
  only detects grabs AFTER the fact).
HOW: at signal build, compare entry price to detected liquidity clusters within X×ATR; if on a
  cluster → pre-trade warning + alternative entry suggestion.
GATE: "enter-at-signal" vs "enter-after-sweep-reclaim" on win rate + adverse excursion.
EFFORT: ~1 day build + backtest.

## D4 — The 13.2% density problem (KEY finding)
WHAT: usable SMC structure sat near entry in only 13.2% of signals → even perfect detection
  rarely influences a trade. Two prongs: (a) RAISE density honestly — multi-timeframe structure
  (an H1 entry references H4/D1 OBs), graded proximity windows, the new D1/D2 detectors; MEASURE
  new coverage %. (b) Be HONEST where absent — "no clean institutional level near this entry;
  this is a momentum/indicator signal, not a structure signal."
GATE: move 13% → a measured, validated number; label the rest truthfully.
EFFORT: ~1.5 days (depends on D1/D2).

## D5 — Conditional entry/decision engine (the multiladder brain)
WHAT: once D1–D3 each earn authority, per-trade DECIDE single / scale-out / scale-in based on
  which PROVEN structure is present. Scale toward a fresh OB when one exists and data says it
  helps; single entry when no structure; never a fixed rule (fixed 3-leg failed at −0.014R).
  Every decision shows its evidence.
HOW: a decision layer that reads D1–D4 outputs + their per-class backtest verdicts and emits an
  entry plan. Opt-in, transparent, conservative by default.
GATE: live entry-placement change → needs staging env; ship only after per-rule backtest passes.
EFFORT: ~2–3 days after D1–D4.
- Calibrated probabilities: shown win-chance anchored to real outcomes, not indicator agreement.

---

# SECTION 4 — PHASE 1: THE PARTNER WAKES UP

## P1 — Intent model (Capability 1, KNOW ME)
WHAT: one model holding daily + weekly + monthly goals (auto-reconciled: daily pace rolls into
  weekly into monthly), risk ceiling, markets, tradeable hours. Set once, persisted, read by
  every tab. Every hardcoded user assumption (default risk 3%, default markets) replaced by this.
HOW: a `dvIntent` store (backend per-user + localStorage cache); one Settings editor; Today,
  Size, Portfolio read from it. Horizon-agnostic from day one (not "weekly" with daily bolted on).
VERIFY: set goals → reload → persisted → Today/Size reflect them.
EFFORT: ~1–1.5 days.

## P2 — Logon briefing (Capability 2, BRIEF ME)
WHAT: every login opens with: position vs each goal horizon, open risk, what changed overnight,
  today's recommendation + WHY.
HOW: a briefing panel that pulls account state + open positions + goal pace + last-session diff
  + the Today stance; uses askClaude/Haiku for the natural-language summary.
VERIFY: log in → briefing shows real numbers + a sensible stance.
EFFORT: ~1–1.5 days.

## P3 — Goal-aware Today (Capability 3, FIND FOR ME)
WHAT: the basket SOLVES for goal pace — ahead of target → more selective; behind → never forces
  junk; always the user's criteria.
HOW: `_todaySelectPlan` reads the intent model's pace; tightens QFLOOR / max-trades when ahead.
VERIFY: set a goal already met → Today gets selective; set behind → broader but still gated.
EFFORT: ~0.5–1 day.

## P4 — Tooltip rewrite wave (Capability 5/honesty)
WHAT: rewrite the 93 FAIL tooltips (of 205: 71 PASS / 41 WEAK / 93 FAIL) to explain the trade,
  not the box. Template = the lot-size explainer.
HOW: work from research/tooltip_inventory_2026-06-10.csv; rewrite each FAIL/WEAK entry in the
  guide-content object; re-grade.
VERIFY: re-run the inventory grader → FAIL count → 0.
EFFORT: ~1 day.

## P5 — "Robot Omar" (kills "same bug 4 months")
WHAT: scripted post-deploy E2E walk of the money path on the demo account: login → criteria →
  scan → size → place → verify in MT5 → close. Deploy goes red if any step breaks.
HOW: a headless/Chrome-driven script + the deep-health endpoint; runs on each deploy.
VERIFY: intentionally break a step → robot catches it.
EFFORT: ~1 day.

---

# SECTION 5 — PHASE 3: THE MEMORY (learning loop, Capability 8)
- Journal every closed outcome → edge-by-setup-type analytics → weekly "your trading reviewed."
- Feed results back into the entry engine + signal weighting → DotVerse becomes Omar-specific.
- Honest caveat: learns from closed trades, so intelligence compounds with trade volume + time.
EFFORT: ~1 week build; wisdom accrues with use.

---

# SECTION 6 — THE HONEST GATE (MT5 terminal)
Order pipeline is PROVEN (broker replies to every order). The trade FILLING needs MetaTrader to
allow it (the "Trade disabled" terminal toggle / account trade permission). No app code forces a
terminal to trade. A1 + A4 make this self-diagnosing (one-line banner) instead of a 45-min hunt.

# SECTION 7 — RULES OF ENGAGEMENT
1. Nothing "done" without commit + live verification. 2. Every claim has checkable evidence.
3. Ledger states "not done" plainly. 4. Money-path: built → reviewed → demo-tested → live.
5. Omar's click on anything irreversible. 6. Every hardcoded user assumption is a bug.
7. Plumbing serves the Partner Loop. 8. Build only on Omar's explicit go-ahead.
