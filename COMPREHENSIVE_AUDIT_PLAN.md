# DOTVERSE COMPREHENSIVE AUDIT + FIX PLAN

## CORE IDENTITY — TRADING INTELLIGENCE PARTNER AND GUIDE

Every feature must be evaluated through this lens: **Does this GUIDE the user, or does it just DISPLAY data?**

A guide:
- Tells you what to do next
- Explains why you're seeing what you're seeing
- Holds your hand through the signal pipeline
- Educates as you go (progressive disclosure)
- Never leaves you wondering "what now?"

Right now the app is a complicated system that shows numbers but doesn't guide. This audit adds a **Guidance Score** to every finding.

### Guidance Score Scale:
- **0 — No guide:** Shows data with jargon, no explanation, no next step
- **1 — Minimal:** Has data-guide tooltips but weak content
- **2 — Partial:** Explains what but not why or what next
- **3 — Full guide:** Explains what it is, why it matters, what to do next

All existing features scored 0-1 unless they have `_dvGuide` entries.

---

## SCOPE
Every feature, every button, every tab, every API endpoint, every visual element, every notification — frontend and backend — scanned against the live deployed app at https://dot-verse.up.railway.app

---

## WORKSTREAMS

### PHASE 1 — Backend API + Code Audit (8 agents, fully parallel)

| WS | Focus | What's tested | Previous findings to re-verify | User additions | Guidance Score |
|----|-------|--------------|-------------------------------|----------------|----------------|
| **WS-6** | Auth + User API | POST /api/register, /api/login, GET /api/auth-check, /api/user/features, POST /api/logout, POST /api/profile, admin routes | Free tier limits (5 signals/day) | — | Check if onboarding guides first-time user |
| **WS-7** | Signal + Price + Screening API | POST /api/analyze (BTC, AAPL, EURUSD), GET /api/live-price, POST /api/prices, POST /api/scan-list, GET /api/vix, /api/fear-greed, /api/econ-calendar, /api/news, /api/sectors, /api/daily-brief | WTI wrong mapping, XAUUSD not found, VIX threshold wrong, scanner empty results, fear-greed wrong source | — | Check if signal response includes educational text, not just data |
| **WS-8** | Exchange + Backtest + Performance API | POST/GET exchange/* routes, POST /api/backtest, GET /api/pine-script, POST /api/positions, GET /api/portfolio/drawdown, /api/performance/*, /api/signals/*, /api/calibration/*, /api/validate/montecarlo, /api/var, /api/stress, /api/correlation, /api/optimise | Exchange 404s (all 13 paths), backtest rate limit | — | Check if backtest results explain what to DO with the data |
| **WS-9** | Notifications + Automations API | POST /api/watch, GET /api/watches, POST /api/alert-test, GET /api/telegram-status, POST /api/telegram/webhook, GET /api/push/vapid-key, POST /api/push/subscribe, GET /api/events/stream (SSE), GET/POST /api/automation/settings, POST /api/recommend-automations, GET /api/diag, GET /api/docs | Automations wiring gaps (exchange order types, calibration, quality in notifications, SSE refresh), spread missing from Telegram alerts (2 templates) | **Telegram alerts are not educational** — no spread, no lot explanation, not beginner-friendly. **Guidance Score: 0** — raw numbers with no "this means X" | **KEY FINDING: Telegram alerts say "0.50 lots" but a beginner has no idea what a lot is, what it costs, or whether 0.50 is right for them** |
| **WS-10** | PWA + Pine Script + Static Assets | /manifest.json, /sw.js, icon assets, Add to Home Screen capability, /settings page, /pricing page, Pine Script files (.pine), /api/pine-script, /api/pine-divergence, /api/pine-strategy | — | — | Check if Pine Script section guides or just shows code |
| **WS-11** | Bug Re-Verification | Re-test ALL 12 known critical/high bugs against live app: (1) VIX threshold, (2) WTI wrong mapping, (3) XAUUSD not found, (4) exchange 404s, (5) MATIC→null, (6) FTM→null, (7) ARB wrong price, (8) TON wrong price, (9) BRENT unmapped, (10) XPTUSD unmapped, (11) XPDUSD unmapped, (12) macro_context/spread_cost/quality_score presence | All 12 from previous audit | — | — |
| **WS-13** | Ticker Coverage (all 7 asset classes) | Test EVERY ticker in QP_TICKERS: 18 crypto, 20 stocks, 14 forex, 8 commodities, 9 indices. Also test missing agri-commodities (CORN, WHEAT, SOYBEANS, COFFEE, SUGAR, COTTON, COCOA, etc.) and missing cryptos (TON, TRX, HBAR, VET, ICP, FIL, EOS, ALGO, S, RUNE) | MATIC→POL rebrand, FTM→S rebrand, 7 missing agri-commodities, 20 missing cryptos | — | — |
| **WS-14** | Branding + Design System Consistency | CSS audit across ALL tabs: button colors use gold (#c9a84c) not blue, min-height:44px touch targets, font family consistency (Syne/Space Grotesk/IBM Plex Mono), border-radius consistency (6px), button font-weight (400), red buttons (#e05555), no emoji icons, scrollbar theming, all active/hover states use gold | **Not covered in previous audit** — entirely new | Button colors, Pine Script button, alerts tab "horrible", branding mismatches | Also check: does visual design convey guidance (clear visual hierarchy, obvious next actions)? |

---

### PHASE 2 — Browser Visual Audit + Guidance Assessment (6 agents, share login session)

Each agent evaluates every element with the **Guidance Score** (0-3):

| WS | Focus | Guidance Questions to Answer |
|----|-------|----------------------------|
| **WS-1** | Login + Landing | Does the first-time experience guide you or overwhelm you? Is there onboarding? Does the landing page explain what DotVerse IS (trading partner)? Or just show a dashboard? |
| **WS-2** | Market, Signals, Scanner, Understand, Verdict | Does the 6-step pipeline (Market→Signal→Understand→Verdict) actually WALK you through a trade? Or is it just a navigation bar? When you see a signal, does the app say "here's what this means and here's what to do next"? |
| **WS-3** | Size, Act, Automations, Backtest, Risk | When you're about to execute a trade, does the app guide your sizing? Or just show risk %? Does the Act tab explain WHAT each order type does and WHEN to use it? Does the Risk tab tell you what "safe" means for YOU? |
| **WS-4** | Portfolio, Performance, Alerts, News, Settings | Does Performance tab show you your progress as a LEARNING journey, not just numbers? Do Alerts tell you what to DO about the alert? Does Settings explain what each toggle does in plain English? |
| **WS-5** | Quick Analyse + Sidebar | Does Quick Analyse guide you to the signal pipeline, or just dump you into raw analysis? Does sidebar show a clear path through the app? |
| **WS-12** | UX/Jargon Bug Validation | Every jargon term — is it explained IN CONTEXT at the point of first encounter? Or does the app assume you know what SMC, VaR, Order Block means? |

---

## KEY GUIDANCE GAPS (known before audit starts)

| Feature | What it says | What a GUIDE would say |
|---------|-------------|----------------------|
| Telegram alert | "0.50 lots (CONFIRMED — 100% allocation)" | "You're risking 0.50 standard lots = 50,000 units. At current price that's about $X. This is a normal position size for your $XX,XXX portfolio." |
| VIX message (current) | "Markets are more nervous than usual. Put in less money." | "VIX at 17 — this is actually normal. No special caution needed. Trade at your normal size." (my fix changes this) |
| Backtest dashboard | "Win Rate: 65%, Profit Factor: 1.8, Max Drawdown: -12%" | "Win Rate 65% means 65 out of 100 trades would make money. Profit Factor 1.8 means you'd earn $1.80 for every $1 lost. Max Drawdown -12% means the worst drop was 12% — you'd need a 13.6% gain to recover. Here's how this compares to a benchmark." |
| Understand SMC section | "Order Block detected, FVG bullish" | "Big money just left footprints in the chart. An Order Block means institutions bought heavily at this price level — they'll likely defend it. A Fair Value Gap means price jumped too fast and may return to fill the empty space." |
| Act Advanced Options | "Buy Limit / Sell Limit / Buy Stop / Sell Stop" with 3-word description | "Buy Limit = you want to buy CHEAPER than now. Set a price below current and if the market drops to it, your order fills. Good for: when you see a dip coming. Not good for: trending markets that never pull back." |

---

## PREVIOUS FINDINGS INVENTORY (to be merged into final report)

### From 14-Tab UI/UX Audit (92 issues):
- 13 emoji violations
- ~60+ elements missing data-guide
- ~35+ jargon terms
- 6 tabs with missing empty states
- Backtest legacy stats undecipherable
- Portfolio VaR never explained
- Risk: all jargon in primary CTA
- Settings + News: ZERO data-guide
- Signal Feed: dev text in user UI
- Cross-cutting: R:R never explained
- **Guidance Score for ALL tabs: 0-1 out of 3**

### From Live Endpoint Testing (16 bugs):
- 3 critical: VIX, WTI, XAUUSD, exchange 404s
- 5 high: rebrands + wrong mappings
- 6 medium: missing assets, scanner, fear-greed, diag

### From Automations Wiring Audit (4 issues):
- Exchange order types, calibration, quality, SSE — all missing

### From Spread/Telegram Audit (3 issues):
- Spread missing from scanner + 2 Telegram templates
- **Guidance Score for Telegram: 0 — raw numbers with no education**

---

## EXECUTION ORDER

1. Phase 1 starts NOW (8 parallel agents, all independent)
2. As Phase 1 agents complete, findings feed into COMPREHENSIVE_BUG_LIST.md
3. Phase 2 starts after WS-1 completes (login session established)
4. After ALL workstreams complete → consolidated master bug list with **Guidance Scores**
5. Then → fix pipeline using universal-verification-process (4-phase verification per fix)
