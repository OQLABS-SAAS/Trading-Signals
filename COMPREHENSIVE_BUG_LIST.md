# DOTVERSE COMPREHENSIVE BUG LIST — All Levels

Generated: 2026-05-26 from live endpoint testing + code audit + UI/UX audit
Every item below was verified against the deployed Railway app unless noted.

---

## PRIORITY 1 — CRITICAL (prevents basic functionality)

| # | Level | Bug | Evidence | Fix |
|---|-------|-----|----------|-----|
| 1 | Engine | **VIX threshold miscalibrated** — VIX 16.82 (below avg ~19) classed as REDUCED/"nervous" | `/api/vix` → `zone: "REDUCED"`, `score: 60` | Thresholds: REDUCED at 20+, NO_TRADE at 30+ |
| 2 | Data | **WTI → W&T Offshore stock ($4.18)** instead of crude oil futures (~$65) | `/api/prices WTI-USD` → price 4.18, `/api/analyze` → `asset_type: "stock"` | Map WTI→CL=F in normalise_ticker() |
| 3 | Data | **XAUUSD (Gold) → "Could not fetch data"** | `/api/analyze XAUUSD` → error response | Map XAUUSD→GC=F in normalise_ticker() |
| 4 | Backend | **All exchange endpoints return 404** — 13 paths tested | `GET /api/exchange/*` all 404 | Fix route registration in app.py |

---

## PRIORITY 2 — HIGH (broken data)

| # | Level | Bug | Evidence | Fix |
|---|-------|-----|----------|-----|
| 5 | Data | **MATIC → null price** — rebranded to POL Sept 2024 | `/api/prices MATIC-USD` → null | Update QP_TICKERS to POL-USD |
| 6 | Data | **FTM → null price** — rebranded to S (Sonic) Jan 2025 | `/api/prices FTM-USD` → null | Update QP_TICKERS to S-USD |
| 7 | Data | **ARB → $0.0008** — real price ~$0.30, wrong token mapping | `/api/prices ARB-USD` → 0.0008 | Check data provider symbol resolution |
| 8 | Data | **TON → $0.0064** — real price ~$2-3, wrong token mapping | `/api/prices TON-USD` → 0.0064 | Check data provider symbol resolution |
| 9 | Data | **BRENT → no symbol mapping** — not in normalise_ticker() | Code audit | Map BRENT→BZ=F |
| 10 | Data | **XPTUSD → no symbol mapping** — Platinum not mapped | Code audit | Map XPTUSD→PL=F |
| 11 | Data | **XPDUSD → no symbol mapping** — Palladium not mapped | Code audit | Map XPDUSD→PA=F |
| 12 | Backend | **macro_context, spread_cost, quality_score — presence unconfirmed** — signal quota exhausted before we could test | 5/5 signals used today | Test after daily reset or upgrade tier |

---

## PRIORITY 3 — MEDIUM (missing features / broken UX)

| # | Level | Bug | Evidence | Fix |
|---|-------|-----|----------|-----|
| 13 | UI | **Backend test tab — 5 emoji violations** in strategy icons: 📦⚖️📐🚀💧 | Code audit line ~19585-19590 | Replace with inline SVGs |
| 14 | UI | **Performance tab — 7 emoji violations** in empty states: 🔍📊📅🎯 etc | Code audit lines ~12135-12514 | Replace with inline SVGs |
| 15 | Data | **7+ agri-commodities missing** — Corn, Wheat, Soybeans, Coffee, Sugar, Cotton, Cocoa, Live Cattle, Lean Hogs | Not in QP_TICKERS or normalise_ticker() | Add to QP_TICKERS + normalise_ticker() |
| 16 | Data | **Scanner returns empty results** for all queries — no diagnostics, no spread fields | `POST /api/scan-list` → `count:0, results:[]` | Investigate why no signals match |
| 17 | Data | **Fear-greed endpoint returns crypto data** (alternative.me), not equity VIX | `GET /api/fear-greed` → `source: "alternative.me"` | Add equity fear-greed source |
| 18 | Backend | **/api/diag shows all data sources failing** — yahoo 429, TV no data, FMP/binance fail — misleading | `GET /api/diag` | Fix diag to use same data path as /api/prices |
| 19 | UI/UX | **20+ major cryptos missing from Quick Analyse** — TON, TRX, HBAR, VET, ICP, FIL, EOS, ALGO, S (Sonic), RUNE | Not in QP_TICKERS | Add to crypto list |
| 20 | UI/UX | **R:R used across 8+ tabs without explanation** — beginners don't know Risk-to-Reward ratio | Cross-tab audit | Plain-English label or tooltip on every instance |
| 21 | UI/UX | **Backtest tab: strategy names are jargon** — "Order Block", "Stop-hunt Sweeps", "Institutional order zones" | line ~19585-19590 | Add beginner tooltips |
| 22 | UI/UX | **Backtest tab: legacy stats grid shows "PnlUsd/ DdUsd/ WL/ PF"** — undecipherable labels | line ~19752-19757 | Rename to plain English |
| 23 | UI/UX | **Portfolio tab: "VaR" in health banner never explained** | line ~10853-10870 | Add tooltip / plain-English label |
| 24 | UI/UX | **Risk tab: "Compute VaR/ Run Stress Test/ Correlation/ Optimise"** — all jargon in primary CTA | line ~11545-11558 | Beginner tooltips |
| 25 | UI/UX | **Settings tab: entire sidebar + card-selectors have ZERO data-guide** | line ~6611-7142 | Add tooltips to all interactive elements |
| 26 | UI/UX | **News tab: ZERO data-guide coverage** across entire tab | line ~12966-13027 | Add tooltips |
| 27 | UI/UX | **"Scalp/ Day Trade/ Swing/ Position" mode labels** — beginner doesn't know the difference | line ~10417-10436 | Add plain-English tooltip per mode |
| 28 | UI/UX | **Signal Feed: dev text in user UI** — "rate-limited on Railway", "TWELVEDATA_API_KEY" | line ~8764 | Remove diagnostic text |
| 29 | UI/UX | **Act tab: "MT5" mentioned throughout** — beginner doesn't know what MT5 is | line ~17935-17939 | Add tooltip explaining MT5 |
| 30 | UI/UX | **Understand tab: "SMC/ CVD/ Order Block/ Breaker Block"** — never explained | line ~14287-14304 | Add beginner tooltips |
| 31 | UI/UX | **Verdict tab: "Run Analysis" button no tooltip** — beginner doesn't know what 8 AI agents do | line ~16062-16065 | Add data-guide tooltip |

---

## PRIORITY 4 — LOW (polish / enhancements)

| # | Level | Bug | Evidence | Fix |
|---|-------|-----|----------|-----|
| 32 | UI/UX | **~60+ elements missing data-guide across all tabs** | From 14-tab audit | Add tooltips per-tab |
| 33 | UI/UX | **~35+ jargon terms used without explanation** — confluence, divergence, regime, SMC, VaR, Sharpe, etc | Cross-tab audit | Add plain-English tooltips or rename labels |
| 34 | UI/UX | **6 tabs missing empty states** — cards show nothing when no data exists | Per-tab audit | Add empty state messages |
| 35 | UI/UX | **Quick Analyse can't scan all TFs or all assets at once** — one ticker/TF at a time | UX feature gap | Add "Scan All" mode |
| 36 | UI/UX | **Backtest tab: no beginner guidance on what backtesting is or why to use it** | UX feature gap | Add step-by-step onboarding |
| 37 | UI/UX | **Act tab Advanced Options: no explanation of WHEN to use each order type** | line ~18037-18153 | Add per-order-type tooltips with scenario examples |
| 38 | Automation | **Exchange order types (market/limit/stop) absent from automations** | Code audit | Add to AutomationSettings + UI |
| 39 | Automation | **Calibration confidence not used in automation recommendations** | Code audit | Wire into recommendation engine |
| 40 | Automation | **Quality score + win rate never in notification payloads (Push/SSE/Telegram)** | Code audit | Add to _push_notification |
| 41 | Automation | **Automation tab doesn't react to SSE events** — watch dashboard needs manual refresh | Code audit | Add SSE listener |
| 42 | Notifications | **Spread missing from Telegram fire_alert template** | Code audit line ~4719-4773 | Add spread line to message |
| 43 | Notifications | **Spread missing from Telegram scanner alert template** | Code audit line ~6848-6856 | Add spread line to message |
| 44 | Notifications | **Spread missing from scanner table rows** (only card views have it) | Code audit line ~9701-9733 | Add spread fields to scanner payload |

---

## TOTALS

| Severity | Count |
|----------|-------|
| CRITICAL | 4 |
| HIGH | 8 |
| MEDIUM | 19 |
| LOW | 13 |
| **TOTAL** | **44** |

---

## FIX PLAN — Batch Waves

### Wave 1: Symbol Mappings (non-overlapping dict entries)
- WTI→CL=F, BRENT→BZ=F, XAUUSD→GC=F, XPTUSD→PL=F, XPDUSD→PA=F
- All in normalise_ticker() dict ~line 7100

### Wave 2: Rebrands + Missing Tickers (frontend QP_TICKERS)
- MATIC→POL, FTM→S in QP_TICKERS
- Add TON, TRX, HBAR, VET, ICP, FIL, EOS, ALGO, S, RUNE to crypto list
- Add agri-commodities: CORN, WHEAT, SOYBEANS, COFFEE, SUGAR, etc.

### Wave 3: VIX + Exchange 404s
- VIX thresholds already patched (needs verification)
- Exchange route registration fix (investigate why routes 404)

### Wave 4: Spread in notifications
- Telegram fire_alert + scanner alert templates
- Scanner table row payload

### Wave 5: Emoji→SVG (frontend HTML)
- Backtest tab: 5 emojis
- Performance tab: 7 emojis

### Wave 6: Automation wiring
- Exchange order types, calibration, quality in notifications, SSE listener
