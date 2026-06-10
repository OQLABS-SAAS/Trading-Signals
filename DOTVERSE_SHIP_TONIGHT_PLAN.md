# DotVerse — SHIP TONIGHT Build Plan (2026-06-10)
**Goal:** the full money-path loop works for Omar on his demo MT5, with zero lies and zero
silent failures. **Scope:** single-user, MT5-only. **Rule:** nothing marked done without a
commit + live verification.

Continues prior plans (REIMAGINED_BUILD_PLAN.md Tier-0, IMPLEMENTATION_PLAN.md) — does NOT
replace them. This is the tonight slice only.

---

## ✅ ALREADY DONE + LIVE-VERIFIED TONIGHT (dv-v16, origin main ~2cf54e0)
1. MT5 connection truth + auto-registration (live EA = connected account) — verified
2. Canonical signal count everywhere (64=64) — verified
3. Portfolio value honesty ($37.57 = $37.57) — verified
4. Today scan progress + completion — verified
5. Market tab never hangs (12s timeout + 9s watchdog + chip recovery) — verified
6. Honest scan-error reporting — verified
7. Size concentration warning (cash-in ≥25%) — verified
8. Scale-out tooltip honesty — verified
9. **Order placement — 3 stacked root causes fixed:** no-account-row, missing account_id
   column, AND the unquoted `trailing` reserved word that silently aborted EVERY migration
   for months. Orders now save + queue + reach the EA + reach the broker. — verified live
10. Today criteria persist across reloads + seed from Settings — verified live
11. Lot-size plain-English explainer (Size tab + confirm modal) — verified live
12. Error hygiene (no raw SQL — human messages front+back) — verified live (Omar saw it)
13. EA double-place protection (telemetry reconcile, max 1 requeue, fail-safe) + 4 tests
14. Deep-health + admin schema-repair endpoints (kills silent schema drift)
15. EA now sends trade_mode/login/server → MODE shows DEMO, login 1084284, VTMarkets-Demo

## 🟡 THE ONE HONEST GATE (MT5 terminal, not our code)
The order pipeline is PROVEN (broker replies to every order). Remaining "Trade disabled"
(retcode 10017) is a MetaTrader terminal permission. Account-level trading was the 4-month
cause (logged in with read-only investor password → fixed via master-password login,
Journal confirmed "trading has been enabled"). Final layer: the running EA must re-read the
now-enabled permission. Build items A1 + A4 below make this self-diagnosing so it's a
one-line banner, never a 45-min hunt again. No app code can force a terminal to trade.

---

## 🔨 SHIP TONIGHT — buildable by Claude now, NO Omar hands needed

### A1. Broker-error translator  [error hygiene, highest tonight value]
**What:** map all ~20 MT5 broker retcodes to plain instructions, shown in Act tab + order list.
**Why:** tonight Omar stared at `retcode=10017` for 45 min. The app must say what to DO.
**How:** `_mt5RetcodeHuman(code)` in app.py (applied where orders serialize) + JS mirror.
  - 10017/10027 → "Automated trading is OFF in MetaTrader. Click the green 'Algo Trading'
    button, then reload the EA (remove + re-add to the chart)."
  - 10019 → "Not enough free margin for this size." · 10018 → "Market is closed for this
    symbol." · 10016 → "Invalid stop-loss/take-profit levels." · 10014 → "Invalid lot size."
    · 10006/10013 → "Broker rejected the request." · default → human fallback.
**Verify:** fire into the current disabled state → confirm Act tab shows the instruction, not the code.
**Effort:** ~45 min.

### A2. Ladder combined totals  [Omar long-standing ask, task #14]
**What:** one canonical "basket total" line — total cash-in, total risk, total profit target,
total position value, total # MT5 orders — at the Size ladder confirm AND the Size tab footer.
**Why:** combined total across all multi-ladder legs is missing/inconsistent in Size.
**How:** extract a `_dvBasketTotals(legs)` helper; render it in `_szConfirmTrade` and the Size
ladder summary; reuse the Today basket math so they never disagree.
**Verify:** build a 3-leg ladder → confirm modal shows the summed totals matching the rows.
**Effort:** ~1 hr.

### A3. Multi-ladder placement integrity  [task #13]
**What:** harden the N-leg submit: track every leg, report partial success ("3 of 4 placed"),
offer retry for ONLY the failed legs, reconcile combined total after.
**Why:** laddered submit fires N orders; a partial failure must be clear + recoverable.
**How:** already has per-leg result tracking in `_todaySendOrders`/`_szLadderSubmitGo`; add a
clear partial-result panel + failed-leg-only retry; unit-test the leg accounting.
**Verify:** unit test (mock 1 leg failing) + live once the terminal allows a fill.
**Effort:** ~1.5 hr.

### A4. EA self-diagnosis flags  [activates on Omar's next recompile, whenever]
**What:** EA reports TERMINAL_TRADE_ALLOWED, MQL_TRADE_ALLOWED, ACCOUNT_TRADE_ALLOWED,
ACCOUNT_TRADE_EXPERT each heartbeat → app shows a one-line banner naming the exact off switch.
**Why:** turns tonight's multi-layer hunt into "MetaTrader has automated trading disabled."
**How:** add 4 ints to the EA PushState JSON; surface in /api/mt5/state + a Settings banner.
**Verify:** code + unit; live on next recompile (no recompile required tonight).
**Effort:** ~45 min.

### A5. Audit quick-wins
- Header "TRADING DASHBOARD · —" missing date → real date.
- Demote "Reset All Data" away from "Journal" + add a confirm dialog (destructive).
- "MT5 UNKNOWN connected" wording → human phrasing.
**Effort:** ~45 min total.

---

## ORDER OF EXECUTION TONIGHT
A1 → A2 → A4 → A5 → A3 → (deploy in one verified batch, bump cache, live-verify each) →
update MASTER PLAN ledger. Each passes syntax + full pytest (currently 663 green) before deploy.

## NOT tonight (honest)
- D-track SMC engine (true OB / IDM / liquidity-trap avoidance / 13.2% density / conditional
  entry) = Phase 2, weeks of quant work behind backtest gates. In MASTER PLAN as the headline.
- Intent model / logon briefing / goal-aware Today / 93-tooltip rewrite = Phase 1.
- The MT5 terminal trade-permission toggle = Omar's hands, made self-diagnosing by A1+A4.
