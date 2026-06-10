# DOTVERSE MASTER PLAN — Trade Intelligence Partner (Omar Edition)
**Date:** 2026-06-10 · **Owner:** Omar · **Mode:** single-user, perfect for Omar · **Scope decided by Omar: EVERYTHING — all goal horizons, all intelligence layers, MT5 + Binance**

---

## 1. NORTH STAR (the product, in Omar's terms)

> The moment I log on, DotVerse already understands my needs — my goals on every
> horizon, my markets, my risk — and works FOR me: finds the trades that fit,
> proves why with data, sizes them safely, fires them reliably on my broker,
> decides the right entry/exit style per trade from evidence, protects every
> position, learns my personal edge, and explains everything in plain language.
> A partner with a brain — not a dashboard waiting for instructions.

**The anti-goals (what burned 4 months):** claiming "done" without proof ·
features that decorate instead of decide · tooltips that name the box instead of
explaining the trade · silent failures on the money path · forgetting the user's
criteria · raw error codes shown to a trader.

---

## 2. THE PARTNER LOOP — 8 capabilities. Every feature serves one. Anything that serves none gets cut.

| # | Capability | Promise to the trader |
|---|-----------|----------------------|
| 1 | **KNOW ME** | One intent model: daily+weekly+monthly goals (auto-reconciled), risk ceiling, markets, schedule. Set once, remembered forever, read by every tab. |
| 2 | **BRIEF ME** | Logon = briefing: position vs goals, open risk, what changed overnight, today's recommendation and WHY. |
| 3 | **FIND FOR ME** | Plans backward from goal pace. Ahead of target → more selective. Behind → never forces junk. Always MY criteria. |
| 4 | **PROVE IT** | Every candidate carries evidence: setup-class win rate, regime, structure, calibrated probability. The multiladder becomes an ENGINE: per-trade scale-in / scale-out / single decided by data. |
| 5 | **SIZE IT SAFELY** | Plain-English lots, concentration warnings, basket caps. A beginner always knows what a size MEANS. |
| 6 | **EXECUTE RELIABLY** | One click → broker, every time. Singles + full ladders + combined totals. Double-place impossible. Errors speak human. |
| 7 | **PROTECT & MANAGE** | BE, trailing, invalidation, alerts — active and truthfully displayed. |
| 8 | **LEARN & REPORT** | Every outcome journaled → YOUR edge by setup type → feeds back into #4. The partner becomes more Omar's every week. |

---

## 3. PHASES

### PHASE 0 — SHIP TONIGHT (the trustworthy core; all build-and-verify today)
Definition of shipped: Omar uses the full loop on his demo MT5 with zero lies and zero silent failures.

- [x] MT5 connection truth + auto-registration (live EA = connected account) — **DEPLOYED, live-verified**
- [x] Canonical signal counts everywhere — **DEPLOYED, live-verified (64=64)**
- [x] Portfolio value honesty ($37.57 = $37.57) — **DEPLOYED, live-verified**
- [x] Today scan progress + completion — **DEPLOYED, live-verified**
- [x] Market tab never hangs (timeout + watchdog + retry recovery) — **DEPLOYED, live-verified**
- [x] Honest scan-error reporting — **DEPLOYED, live-verified**
- [x] Concentration warning (cash-in ≥25%) — **DEPLOYED, live-verified**
- [x] Scale-out tooltip honesty — **DEPLOYED, live-verified**
- [x] ROOT FIX 1: order placement — account resolution (auto-register from EA) — **DEPLOYED, account id=1 created**
- [x] ROOT FIX 2: order placement — missing mt5_orders.account_id column + transaction-poison guard — **DEPLOYED**
- [ ] **PROOF ORDER: Omar's click → EURUSD 0.02 lots lands in MT5** ← waiting on the click, modal armed
- [ ] Multi-ladder placement E2E on demo (all legs, verified in MT5)
- [ ] Ladder combined totals visible at placement
- [ ] EA double-place protection verified/hardened
- [ ] Error hygiene: no raw SQL/stack traces anywhere — human messages only
- [ ] Lot-size plain-English explainer (Size tab, confirm modals, Today rows)
- [ ] Criteria persistence live-verified (built, deploying)
- [ ] Consolidated ledger + this plan committed to the repo

### PHASE 1 — THE PARTNER WAKES UP (next build, days not months)
- Intent model v1: daily/weekly/monthly goals, auto-reconciled; one place to edit; every tab reads it (Capability 1)
- Logon briefing v1: account state, open risk, goal pace, overnight changes, today's stance (Capability 2)
- Goal-aware Today: basket solves for goal pace, gets selective when ahead (Capability 3)
- Tooltip total rewrite: every explainer graded + rewritten to "what this value means for YOUR trade" (audit standard)

### PHASE 2 — THE BRAIN (evidence layer)
- Evidence Entry Engine: per-setup-class backtests decide single / scale-out / scale-in per trade; conditional rules, never one frozen rule (Capability 4). Research harness already exists (1,087-trade study, repo `research/`).
- Calibrated probabilities: shown win-chance anchored to real outcomes, not indicator agreement
- Binance testnet execution + exchange SL/TP (needs Omar's free testnet keys — 10 min)

### PHASE 3 — THE MEMORY (learning loop)
- Outcome journaling → edge-by-setup analytics → weekly "your trading reviewed" report (Capability 8)
- Feedback into the entry engine and signal weighting: DotVerse becomes Omar-specific

### PARKED (single-user decision): multi-user security migration, SCIM/teams — revisit only if Omar opens DotVerse to others.

---

## 4. CONSOLIDATED DEFECT LEDGER (every known issue, all sources, honest status)

### Fixed & live-verified today
1. "No account / 0 accts" while EA streams — fixed (normalizer + auto-registration)
2. Signal counts 49/178/195 chaos — fixed (canonical unique count)
3. Portfolio $38 vs "$37.572" — fixed (real cause: decimal formatting)
4. Today scan frozen progress — fixed (live counter + completion)
5. Market tab eternal "Loading…" — fixed (timeout + watchdog + chip recovery)
6. "14 sources had errors" scare-number — fixed (honest impact + causes)
7. No concentration warning — fixed (≥25% cash-in warning, single + ladder)
8. Scale-in lie in ladder tooltip — fixed
9. **Orders never fire on MT5 (4 months)** — TWO root causes found & deployed: (a) order rejected when no saved account exists; (b) mt5_orders.account_id column never migrated → aborted transactions. Awaiting Omar's proof click.
10. MODE UNKNOWN displayed as DEMO anywhere — fixed (three-way badges, safety-first)

### Built today, deploying/verifying
11. Today forgets criteria on reload (Omar-reported) — fixed: persistence + seeded from Settings Asset Preferences; auto-place never persists (safety)
12. Settings Asset Preferences ignored by Today — fixed (same change)

### Open — Phase 0 (tonight)
13. Multi-ladder placement E2E unproven on broker (was blocked by #9's root causes; same fix likely clears it — must be PROVEN, not assumed)
14. No combined total across ladder legs at placement review (partially exists in Today confirm; missing/inconsistent in Size)
15. EA double-place risk (poll race) — guards exist in code; must be verified under repeat polling
16. Raw psycopg2/SQL errors shown to the user (Omar screenshot) — error hygiene pass
17. Lot sizes unexplained — "what is 0.02 lots, is it good?" (Omar, 3.5 months) — explainer + size-class labels
18. EA doesn't send demo/live flag — EA source fixed; **Omar must recompile in MetaEditor (guide written)** — until then app honestly shows MODE UNKNOWN

### Open — found in today's audit passes (not yet fixed)
19. "TRADING DASHBOARD · —" missing date in header (auditor)
20. "Reset All Data" placed next to "Journal" in Portfolio — destructive action with prime placement (auditor)
21. Allocation: Forex 100% actual vs 20% target shown without guidance (auditor)
22. Act tab wording "MT5 UNKNOWN connected" — reads like an error, needs human phrasing
23. Virtual EA account card shows empty "#" when login unknown (cosmetic, fixed by EA recompile)
24. /api/prices intermittently hangs server-side (provider chain) — frontend now recovers; backend stall itself unfixed
25. Tooltips systemically name the box, not the trade meaning (Omar) — full inventory + rewrite scheduled Phase 1
26. Beginner/Advanced mode differences unaudited; user-journey breaks unaudited tab-by-tab — full 7-check audit scheduled (method agreed)

### Open — questions to settle with data
27. Signal quality itself (are the signals any good?) — needs the calibration loop (Phase 2/3); until then app must not overclaim
28. Scale-in conditional edge (when DOES it win?) — Phase 2 research; static version already disproven (1,087 trades)

---

## 5. RULES OF ENGAGEMENT (how we work, so 4 months never repeats)
1. Nothing is "done" until verified live on Omar's screen with a commit behind it.
2. Every claim ships with evidence Omar can check in under a minute.
3. The ledger tells the truth — including "not done" and "not found yet."
4. Money-path changes: built → independently reviewed → tested on demo → then live.
5. Omar's final click on anything irreversible; Claude drives everything else.
6. Every hardcoded assumption about the user is a bug.
7. Plumbing serves the Partner Loop — features that decide nothing get questioned.
