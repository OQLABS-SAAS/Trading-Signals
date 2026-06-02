# DotVerse "Today" — LOCKED DESIGN

> Status: **LOCKED** (2026-06-02). The front door. A scared beginner opens DotVerse and sees one calm, live screen: what to trade today, sized to their real account, net of real costs, with their goal progress — and DotVerse keeps it honest and keeps them safe.
>
> Core frame: **Today is a live trading cockpit, not a static list.** Every trade is a living thing with a price drifting right now.

---

## A. Core flow
1. Today is the landing tab (the front door).
2. One-click **"Build my plan"**: scans all classes → quality gate → diversifies → auto-sizes → renders review cards + summary.
3. Quality over quota — if only 2 good setups exist, show 2 and say so.

## B. Selection & diversification
4. Across asset classes (max-per-class control).
5. Across direction (blends longs and shorts).
6. Across timeframes/styles (scalp / day / swing).
7. De-correlated — won't stack BTC+ETH+SOL all long.
8. Single-variable risk detector — names the hidden bet.
9. "Why NOT" — shows rejected setups with a one-line reason.
10. Regime-aware selectivity — fewer/smaller setups in risk-off/high-volatility conditions.

## C. Sizing & capital
11. Real account auto-pulled from live MT5 balance (editable).
12. Capital-per-trade control (the trade-size option) + max-risk-per-trade cap.
13. Each card shows capital allocated $ and % of account, clearly.
14. Size in units/lots, rounded to valid broker lots, with margin/leverage check.
15. Net of costs — spread + fees + estimated slippage factored into max loss AND reward.
16. Broker-cost line per card (spread / fees / slippage breakdown).
17. Total-risk cap across the basket (respects daily-loss limit).
18. Cash-buffer line — shows you're not over-deployed.
19. Learn real costs from the user's own fills — calibrate spread/slippage to what their broker actually does, over time.
20. Equity-curve-aware risk — trade slightly smaller in a drawdown.

## D. Live cockpit / dynamic efficiency
21. Per-card live entry monitor — AT ENTRY / DRIFTED / ENTRY PASSED / STOP BREACHED, real time.
22. Entry zone (± ATR band), not a single price.
23. Cards sort by time-sensitivity (price-at-entry first).
24. Auto-expire stale setups; auto-replace with next-best.
25. Live projection cone — updates as trades resolve.
26. Market-hours awareness ("opens in 3h").
27. News/event + session awareness ("FOMC in 2h"; liquidity windows).
28. Auto-refresh prices; one-tap rebuild.

## E. Execution
29. Per-card "Review & place" → pre-trade confirmation (verdict + max loss + close-anytime).
30. "Review & place all" — batch with live status, combined risk, final gut-check.
31. Pending/limit orders at entry — EA fills when price arrives (real fix for missed entries).
32. "Alert me at entry" (Telegram) for setups not yet at entry.
33. Pre-flight health check — MT5 connected? margin OK? quote fresh? not a duplicate?
34. Slippage-protected orders (max deviation).
35. The trader always clicks — DotVerse never auto-fires.
36. Server-side stops — SL/TP live at the broker; protected even if app/internet/computer dies.

## F. Smart automations
37. Per-trade /api/recommend-automations — BE/trail/partials differ by buy/sell/type/trend.
38. Honest break-even wording (only protects after TP1).

## G. Trust & proof
39. Backtest-verified edge per card (historical win rate / expectancy).
40. "Why this trade" — reason + confluence + verdict.
41. DotVerse-checked trust list per card.
42. Honesty ledger — recent plan record, wins AND losses.
43. Assumptions panel — exact costs, nothing hidden.
44. Plan-health badge — diversification, total risk, exposure, correlation at a glance.

## H. Behavioral guardrails (protect the trader from themselves)
45. Tilt / revenge-trade protection after a loss.
46. Loss cooldown after consecutive stops.
47. Discipline streak — rewards process, not P&L.
48. Pre-commitment — set the day's rules up front.

## I. Portfolio-aware risk
49. Factor existing open MT5 positions.
50. Daily risk-budget meter.
51. Net exposure view (long/short, currency concentration).

## J. Goals & money management
52. Goal progress over time — never a daily quota.
53. Honest compounding projection.
54. Profit-banking nudges.

## K. Confidence / beginner
55. Paper/practice mode — run the exact plan simulated before risking a cent.
56. "Just the essentials" card + collapsible details.
57. Jargon tooltips on every scary term.
58. Emotional acknowledgement + start-small nudge.
59. Plain "what the button does / how to exit" line.

## L. Lifecycle
60. Live management after placement — running P&L, which automation fired, "BE moved ✓".
61. Post-trade note ("BTC hit TP1 +$18, trail locked the rest").
62. Feeds goal progress.

## M. Friction reduction
63. Morning auto-build + Telegram push (scheduled).
64. Mobile-friendly layout.

## N. Hard guardrails (non-negotiable)
65. Respects max-trades and daily-loss-max.
66. Never increases size to chase a target.
67. A flat / trade-free day is shown calmly as a correct outcome.
68. Every placement goes through confirmation + verdict.

---

## Build order (phased — each ships verified before the next)

**Phase 1 — Live cockpit core**
Real account (11) · capital control + max-risk cap (12) · capital allocated shown (13) · valid lots + margin (14) · net-of-costs sizing + broker-cost line (15, 16) · total-risk cap + cash buffer (17, 18) · per-card live entry monitor + entry zone (21, 22) · time-sensitivity sort (23) · per-card review & place (29) · review & place all + final gut-check (30) · server-side stop assurance (36) · smart per-trade automations (37, 38) · plan summary + honest projection (44, 52, 53) · hard guardrails (65–68).

**Phase 2 — Execution depth & portfolio risk**
Pending/limit orders at entry (31) · alert-me-at-entry (32) · pre-flight health check (33) · slippage protection (34) · portfolio-aware risk: open positions + daily budget + exposure (49, 50, 51) · auto-expire + auto-replace (24).

**Phase 3 — Proof & behavior**
Backtest-verified edge (39) · why-this-trade + why-NOT (40, 9) · DotVerse-checked list (41) · honesty ledger (42) · assumptions panel (43) · plan-health + single-variable risk (44, 8) · tilt/cooldown/discipline/pre-commitment (45–48) · regime-aware + equity-curve risk (10, 20).

**Phase 4 — Confidence, lifecycle, reach**
Paper/practice mode (55) · essentials card + tooltips + reassurance (56–59) · live management after placement + post-trade notes (60, 61) · learn real costs from fills (19) · live projection cone (25) · market-hours/news/session (26, 27) · profit-banking (54) · morning auto-build + Telegram push (63) · mobile (64).
