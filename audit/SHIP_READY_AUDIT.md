# DotVerse Ship-Ready Audit — 2026-05-06
# Verified: MCP (Market, Understand) + Code Trace (all pages)

## SHIP BLOCKERS

| # | Page | Issue | Severity |
|---|------|-------|----------|
| 1 | Market | Econ Calendar shows static NFP/ISM events — Finnhub not delivering valid times on Railway | CRITICAL |
| 2 | Market | Live Momentum Windows empty — CoinGecko rate limiting on Railway IP | CRITICAL |
| 3 | Understand | BTC analysed as stock ($36.12) instead of crypto ($81K) — ticker normalization bug in Quick Analyse | HIGH |
| 4 | Understand | Journey panel shows "0% confidence" — display bug | MEDIUM |
| 5 | Signals | Metrics cards show static numbers (73.4%, 71.8%) | MEDIUM |
| 6 | Signals | HYPOTHESIS/LOW signals shown without visual warning | HIGH |
| 7 | Sidebar | "Marcus Chen" hardcoded | LOW |

## WORKING — VERIFIED

| Feature | Status |
|---------|--------|
| Backtest via RQ worker | ✅ Live (27% WR, 11 trades, PF 0.75, Max DD 0.5%) |
| Backtest expandable boxes | ✅ Click to expand with explanations |
| Backtest drawdown | ✅ Shows 0.5% |
| Fear & Greed | ✅ 46 from Alternative.me |
| Sector Strength | ✅ Live from yfinance ETFs |
| Heatmap | ✅ Live from /api/prices |
| Market prices | ✅ Live |
| Live Signals confidence filter | ✅ No LOW/HYPOTHESIS on Market |
| Confluence explainer | ✅ "indicator agreement, not win rate" |
| Multi-TF Alignment | ✅ 6 timeframes render with data |
| Landing stats | ✅ Live from /api/stats |
| Sign-in form | ✅ Renders on page load |
| Auth | ✅ Login/logout work |
| Tier gating | ✅ 14 endpoints protected |
| Flow-Scaled sizing | ✅ Code verified |
| Cross-pair forex | ✅ Code verified |
| Kelly formula | ✅ Code verified |

## PENDING FIXES (committed, not pushed)

| Commit | Fix |
|--------|-----|
| f8371ae | Remove signal dedup (all TFs visible) + holding period label |
| uncommitted | MTF "backend unreachable" error message fix |

## PAGES NOT LIVE-VERIFIED (need user browser)

| Page | Verification Steps |
|------|-------------------|
| Signals | Click tab → verify multi-TF signals visible, Verified toggle works, WR comparison shows |
| Size | Load signal → verify calculator auto-fills, Flow-Scaled badge, multi-trade ladder |
| Portfolio | Click tab → verify positions load from /api/positions |
| Alerts | Click tab → verify notifications render, rule toggles work |
| News | Click tab → verify live articles, Most Mentioned shows real tickers |
| Performance | Click tab → verify equity curve, monthly chart |
| Act | Click tab → verify MT5 connection, trade execution |
| Settings | Click tab → verify connections, preferences, visuals save |
| Automations | Click tab → verify rules render |
| Risk Manager | Click tab → verify VaR, stress test, correlation |
