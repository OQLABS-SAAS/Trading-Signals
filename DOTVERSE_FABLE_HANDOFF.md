# DOTVERSE — HANDOFF FOR FABLE (read this first)
**From:** the 2026-06-10 ship-day session · **For:** the next session that builds + deploys.
**Companion (full item detail):** `DOTVERSE_FINAL_BUILD_PLAN.md`. **Vision:** `DOTVERSE_MASTER_PLAN.md`.
**Owner:** Omar — beginner trader, this is his livelihood, 4 months of frustration. Treat every
money-path change as real money. NEVER claim "done" without a commit + live verification on his
screen. Build only on Omar's explicit go-ahead — he corrects hard when a session jumps ahead.

Omar's directive for tonight: **"everything will be ready for ship tonight — testing can take
weeks, but the BUILD will be ready tonight."** So: WRITE all the code tonight; the proof
(backtests, live verify) runs for weeks. Building ≠ proven — never conflate them.

---

## 1. CURRENT STATE (verify first)
- Repo `OQLABS-SAAS/Trading-Signals`, branch `main` → Railway → https://dot-verse.up.railway.app
- **origin/main HEAD = `2cf54e0`**, live cache = **`dv-v16`**, `/health` = 200, `pytest tests/ -q` = **663 passed, 9 skipped**.
- Working tree is CLEAN (the A1 broker-translator edit was reverted at Omar's request — re-build it, see §4 A1).
- Frontend: ONE file `static/index-v2-prototype.html` (~30k lines, inline CSS/JS). Backend `app.py` (~20k lines) + `smc_structure.py`, `money_math.py`. MT5 execution via `DotVerse_EA.mq5` (the 30KB updated version is already in Omar's MT5 Experts folder + repo root).

## 2. DEPLOY MECHANISM (the .git lock workaround — this WILL bite you)
The mounted `.git` blocks normal commits ("Operation not permitted" on unlink). Use a writable copy:
```
rm -rf /tmp/dvgit && cp -r <repo>/.git /tmp/dvgit && rm -f /tmp/dvgit/*.lock /tmp/dvgit/index.lock
cd <repo> && export GIT_DIR=/tmp/dvgit GIT_WORK_TREE=$PWD
git remote set-url origin "https://x-access-token:<OMAR_PAT>@github.com/OQLABS-SAAS/Trading-Signals.git"
git add <files> && git commit -q -m "..." && git push origin HEAD:refs/heads/main
git ls-remote origin main | cut -c1-7   # confirm SHA matches
```
- Omar pastes a GitHub fine-grained PAT (Contents: read+write). **Tell him to DELETE it at github.com/settings/tokens when done — it was pasted in chat.**
- To revert a working file (unlink blocked): reverse the edits with the Edit tool, don't `git checkout`.

## 3. GOTCHAS (each cost real time today)
1. **Bump `CACHE_VER` in `dotverse-pwa/sw.js` on every frontend deploy** (now dv-v16 → use dv-v17…). Verify in the BROWSER not curl; to force-refresh: unregister SW + `caches.delete()` + reload.
2. **Railway build lag ~3–4 min.** Poll `curl -s .../sw.js | grep dv-v` until the new cache shows before live-verifying. Omar's clicks during a deploy hit the OLD instance — wait for the new SHA.
3. **Test gate:** `python -m pytest tests/ -q -p no:cacheprovider` must be 663 green before every deploy. Pip deps: install in batches with `--break-system-packages` (flask, sqlalchemy, pandas, numpy, scipy, scikit-learn, ta, cryptography, redis, rq, APScheduler, psycopg2-binary, yfinance, ccxt, gevent, pytest).
4. **Live verify** via Claude-in-Chrome (Omar's Chrome is logged in as OMAR/admin): `tabs_context_mcp` → tab id → `javascript_tool` fetch `/api/...` + read DOM. Don't click Place/Submit/Delete without Omar.

## 4. THE BUILD PLAN — execution-ready (full detail in DOTVERSE_FINAL_BUILD_PLAN.md)

### TONIGHT — code-only, no Omar hands, DEPLOYABLE
**A1 — Broker-error translator** (revert was requested; re-build identical):
  - app.py: add `_MT5_RETCODE_MESSAGES` dict + `_mt5_retcode_message(comment,status)` BEFORE
    `mt5_get_orders` (~line 9872); add `"status_message": _mt5_retcode_message(o.comment,o.status)`
    to the orders serialization (~9899). Codes: 10004 requote,10006 reject,10013 bad request,
    10014 bad lot,10015 bad price,10016 bad SL/TP,10017 "Algo Trading off — turn on + reload EA",
    10018 market closed,10019 no margin,10027 autotrading disabled,10030 fill mode,10031 no server.
  - Frontend: in the order-list render (~26875) and Act status, when `o.status==='failed'` show
    `o.status_message` (falls back to existing `_dvHumanizeError`). Verify: fire into the current
    disabled MT5 → Act shows the instruction, not `retcode=10017`.
**A2 — Ladder combined totals** (Omar's long ask): extract `_dvBasketTotals(legs)` from
  `_todayLadderTotals`; render total cash-in/risk/profit/position-value/#orders in `_szConfirmTrade`
  (~24147) + Size footer. Verify: 3-leg ladder → modal totals == sum of rows.
**A4 — EA self-diagnosis flags**: add TERMINAL_TRADE_ALLOWED, MQL_TRADE_ALLOWED,
  ACCOUNT_TRADE_ALLOWED, ACCOUNT_TRADE_EXPERT to `PushState()` JSON in DotVerse_EA.mq5 (~358);
  surface in `/api/mt5/state` + a Settings/Act banner naming the OFF switch. (Activates on Omar's
  next recompile.) This would have saved tonight's 45-min "Trade disabled" hunt.
**A5 — Audit quick-wins**: header "TRADING DASHBOARD · —" → real date; demote "Reset All Data"
  away from "Journal" + add confirm; "MT5 UNKNOWN connected" → human phrasing.
**#21 — Allocation guidance**: Portfolio allocation, when actual vs target diverges ≥2x, show a
  plain action line ("You're 80% over your Forex target — diversify or adjust the target").
**#24 — /api/prices backend stall**: per-provider timeout in the price provider chain so the
  endpoint never hangs (today only the frontend recovers).
Order: A1→A2→A4→A5→#21→#24. One verified batch each (or small batches), 663-green gate, bump cache.

### TRACK D — THE SMC ENGINE (the actual product; build code tonight, prove over weeks)
Discipline: **detect → backtest-prove (vs the 1,087-trade baseline, per setup class) → only then
authority over a live entry.** Today the engine only DECORATES; nothing DECIDES. Build in
`smc_structure.py` + a new `research/` backtest per item (harness pattern exists at
`research/scalein_vs_single_backtest.py`).
- **D1 True Order Blocks** — last opposing candle before displacement, refined zone, freshness/
  mitigation/volume. (Today only an FVG/liquidity PROXY exists.) Gate: OB-retest beats single-entry.
- **D2 IDM/inducement** — ZERO today. Detect bait liquidity between price and the true zone →
  "wait, price sweeps this first." Highest evidence bar; opt-in, transparent, never silent.
- **D3 Liquidity-trap AVOIDANCE** — today detects grabs AFTER the fact; add a PRE-trade warning
  when entry sits ON a liquidity cluster + "wait for sweep-and-reclaim."
- **D4 The 13.2% density problem** — usable structure near entry in only 13.2% of signals.
  Raise it (multi-timeframe structure: H1 entry refs H4/D1 OBs; graded proximity; D1/D2) AND be
  honest where absent ("momentum signal, not structure"). Measure new coverage %.
- **D5 Conditional entry engine** — per-trade single/scale-out/scale-in by PROVEN structure
  (NEVER a fixed rule — fixed 3-leg failed at −0.014R in the 1,087-trade study). Shows its
  evidence. Live entry-placement change → needs the staging env before going live.
- Calibrated probabilities (win-chance from real outcomes, not indicator agreement).

### PHASE 1 — THE PARTNER (build code tonight if time)
- **Intent model**: daily+weekly+monthly goals (auto-reconciled), risk ceiling, markets; set once,
  persisted, read by EVERY tab. Replace hardcoded defaults (risk 3%, default markets). Horizon-
  agnostic from day one (Omar explicitly wants daily AND weekly AND monthly, not weekly-only).
- **Logon briefing**: on login show position vs each goal, open risk, overnight changes, today's
  stance + why (use the Haiku/askClaude helper for the summary).
- **Goal-aware Today**: `_todaySelectPlan` reads goal pace → more selective when ahead, never
  forces junk when behind.
- **Tooltip rewrite wave**: 93 FAIL tooltips (of 205: 71 PASS/41 WEAK/93 FAIL) → explain the
  trade, not the box. Source: `research/tooltip_inventory_2026-06-10.csv`. Template = the new
  lot-size explainer. Re-grade to FAIL=0.
- **Robot Omar**: scripted post-deploy E2E walk of the money path on demo (login→criteria→scan→
  size→place→verify in MT5→close); deploy goes red if a step breaks. Kills "same bug 4 months."

### PHASE 3 — LEARNING LOOP
Journal closed outcomes → edge-by-setup analytics → weekly "your trading reviewed" → feed back
into the entry engine. Compounds with trade volume + time.

## 5. THE HONEST MT5 GATE (not our code)
Order pipeline is PROVEN end-to-end: DotVerse → EA → broker; the broker REPLIES to every order.
The 4-month "trades don't fire" bug had THREE root causes, ALL fixed + deployed: (1) no saved
TradingAccount → auto-register from EA push; (2) `mt5_orders.account_id` never migrated; (3) the
killer — an UNQUOTED Postgres reserved word `trailing` in the startup migration block, a syntax
error that silently aborted EVERY migration for months (8 columns missing in prod). The remaining
"Trade disabled" (retcode 10017) is a MetaTrader TERMINAL permission, not our code:
- Omar's account was logged in with the READ-ONLY investor password (the deep 4-month cause).
  Fixed via master-password login (Journal: "trading has been enabled - hedging mode").
- After that, the global "Algo Trading" toggle + per-EA permission must be on AND the EA must be
  reloaded AFTER they're on (a running EA reads permission once at init). A1+A4 make this a
  one-line banner instead of a hunt. NO app code can force a terminal to accept a trade.
- Omar's MT5 quirks: Navigator window is FROZEN (avoid it; use chart-right-click / Tools menu /
  timeframe-flip to reload the EA). The smiley face indicator NEVER renders on his Mac/Wine build
  — do NOT use it as a diagnostic; judge by retcode + positions[].

## 6. MEMORY ENTITIES TO LOAD (auto-loaded next session)
`DotVerse`, `DotVerse SMC Engine Gap (Track D)`, `DotVerse Ship-Tonight Session 2026-06-10`,
`DotVerse OPEN BUGS`, `dotverse-deploy-git-lock-workaround`, `dotverse-live-verification-chrome`.

## 7. RULES OF ENGAGEMENT
1. Nothing "done" without commit + live verification. 2. Every claim has checkable evidence.
3. The ledger states "not done" plainly. 4. Money-path: built → reviewed → demo-tested → live.
5. Omar clicks anything irreversible. 6. Every hardcoded user assumption is a bug.
7. Plumbing serves the Partner Loop. 8. **Build only on Omar's explicit go-ahead.**
