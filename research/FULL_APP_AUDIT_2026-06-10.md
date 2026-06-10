# DotVerse Full App Audit — 2026-06-10
Method: 7-check owner audit (reload test · button-promise test · same-number-everywhere ·
journey-survival · tooltip standard · beginner-stuck · contradiction sweep) + API-vs-UI diffing
+ mechanical tooltip inventory. Companion: DOTVERSE_MASTER_PLAN.md (ledger §4 = canonical status).

## Headline finding — the teaching layer fails at scale
**205 tooltip/guide entries inventoried (research/tooltip_inventory_2026-06-10.csv):**
- **PASS 71 (35%)** — explain what the value means for the trade
- **WEAK 41 (20%)** — trade words, no consequence
- **FAIL 93 (45%)** — describe the box, not the trade ("Entry Price: the entry price")
A beginner app whose explainers fail 65% of the time is teaching people to click, not to trade.
→ Phase 1: full rewrite against the standard: every entry must state money/risk/action consequence.
The new lot-size explainer is the template ("0.02 lots = $2,408 controlled with $24 cash; stop hit = −$6.25 = 0.25%").

## CRITICAL (money/safety) — found & fixed today, live-verified
1. Orders never reached MT5 (4 months): (a) submit rejected without saved account → auto-registration from EA push; (b) mt5_orders.account_id never migrated → aborted transactions on every INSERT. Both deployed.
2. Unbounded double-place on lost confirms: stale 'executing' orders requeued forever → now telemetry-reconciled, max 1 retry, fail-safe. 4 unit tests.
3. Raw psycopg2/SQL dumps shown to the trader → human messages front+back; technical detail server-side only.
4. MODE UNKNOWN could read as DEMO in places → three-way badges; UNKNOWN always amber + warning. (Full fix needs EA recompile — guide delivered.)

## HIGH (broken features) — fixed today, live-verified
5. Today forgot all criteria each load + ignored Settings Asset Preferences entirely → persistence + seeding (reload-tested live).
6. Market tab could hang forever on one stalled fetch → 12s timeout + 9s watchdog + chip recovery (watched it self-heal at ~20s).
7. Signal counts contradicted across header/badge/list (49/178/195 class) → one canonical deduped count (live: 64=64).
8. Portfolio banner vs card ($38 vs "$37.572" — same $37.57!) → formatting root cause, both pinned to 2dp.

## MEDIUM (misleading/confusing) — open, prioritized for Phase 1
9. 93 FAIL tooltips (see CSV) — rewrite wave.
10. "TRADING DASHBOARD · —" date placeholder in header.
11. "Reset All Data" sits beside "Journal" in Portfolio — destructive action, prime placement, needs demotion + confirm.
12. Allocation "Forex 100% vs 20% target" shown with no guidance on what to do.
13. Act tab "MT5 UNKNOWN connected" phrasing reads like an error — needs human wording.
14. Virtual EA account card shows empty "#" until EA recompile supplies login.
15. Beginner/Advanced mode differences unaudited tab-by-tab (scheduled; mode toggle promise unclear to a new user).

## Server-side (open)
16. /api/prices intermittently hangs (provider chain) — frontend now recovers; backend stall unfixed.

## Verification protocol used (and to be kept)
Build → syntax + full pytest (663 green) → independent agent review for money-path code →
deploy → SW cache clear → live verification on the owner's screen → ledger update.
Phase 1 adds "Robot Omar": scripted post-deploy E2E walk of the money path on the demo account.

## Top remaining (in order)
1. PROOF ORDER click (owner) → certify pipeline → then multi-ladder E2E + totals verify.
2. EA recompile (owner, 5 min) → real DEMO/LIVE detection + login on cards.
3. Tooltip rewrite wave (93 FAIL first).
4. Robot Omar + deep health endpoint.
5. Intent model + logon briefing (Partner Phase 1).
