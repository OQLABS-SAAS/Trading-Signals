# DotVerse Complete Audit — All 14 Pages
# 2026-05-06 | Verified via: MCP (Market, Understand) + Code Trace (all others)

## PAGE 1: LANDING / SIGN-IN
✅ Landing stats live | ✅ Breadcrumb clean | ✅ Sign-in form renders
🔴 Demo accounts hardcoded (L4863-4865)
🔴 "Forgot?" link dead (L4841)

## PAGE 2: MARKET (MCP Verified)
✅ Fear & Greed 46 | ✅ Sector Strength live | ✅ Heatmap live | ✅ Prices live
✅ Live Signals: 3 active, no LOW/HYPOTHESIS
🔴 Econ Calendar static (Finnhub not delivering on Railway)
🔴 Live Momentum empty (CoinGecko rate limiting)
🔴 VIX hardcoded "14.22" in trending conditions

## PAGE 3: SIGNALS (Code Verified)
✅ Multi-TF scan (1H/4H/1D) implemented | ✅ Verified Only toggle | ✅ TF comparison badge
🔴 Metrics cards hardcoded (73.4%, 71.8%, etc.) — _sfRender uses static values
🔴 HYPOTHESIS/LOW signals no visual warning

## PAGE 4: UNDERSTAND (MCP Verified)
✅ Confluence explainer | ✅ Multi-TF alignment 6 TFs | ✅ Backtest data (WR, PF, Max DD)
✅ Indicator Confluence panel | ✅ Plain English signal reasoning
🔴 BTC price $36.12 (ticker normalization bug from Quick Analyse)
🔴 Journey panel "0% confidence" display bug

## PAGE 5: SIZE (Code Verified)
✅ Flow-Scaled sizing with explanations | ✅ Kelly formula correct | ✅ Multi-trade ladder
🔴 Account default $10,000 hardcoded (L12135)
🔴 No live price fetch for current price

## PAGE 6: ACT (Code Verified)
✅ actExecute/actPaperTrade exist | ✅ Calls /api/mt5/order
🔴 0 API calls on page load — depends entirely on _activeSignal
🔴 EA indicator is 7px invisible dot
🔴 /api/mt5/trailing is stub endpoint

## PAGE 7: PORTFOLIO (Code Verified)
✅ Uses /api/positions | ✅ Uses /api/var for VaR
🔴 Position chart uses synthetic PRNG data (pfLoadPosChart)

## PAGE 8: ALERTS (Code Verified)
✅ Fetches /api/notifications + /api/watches
🔴 Rule toggles don't persist (local variable only)
🔴 Error state shows "No active watches" even on network failure

## PAGE 9: NEWS (Code Verified)
✅ Live articles from Finnhub/CryptoCompare | ✅ Filter buttons work
🔴 Trending tickers hardcoded (now partially live from articles)

## PAGE 10: PERFORMANCE (Code Verified)
✅ Uses /api/signals/history
🔴 Equity curve uses Math.random() (falls back to illustrative)
🔴 Monthly breakdown hardcoded values removed (shows empty state)

## PAGE 11: RISK MANAGER (Code Verified)
✅ VaR/Stress/Correlation/Optimisation all wired to real APIs
🔴 0 auto-load — everything is manual-trigger only
🔴 Signal picker empty if navigated directly (no fallback API)

## PAGE 12: BACKTEST (Code Verified)
✅ RQ worker async backtest working
🔴 WinRateBadge duplicate ID (shared with Signals page)

## PAGE 13: SETTINGS (Code Verified)
✅ Connections save to /api/settings | ✅ Chart visuals auto-persist
🔴 5 of 8 sub-panels save to localStorage only

## PAGE 14: AUTOMATIONS (Code Verified)
✅ Loads from /api/automation/settings
🔴 Slider changes never persist
🔴 Telegram status hardcoded "Telegram connected"

## SHIP-BLOCKERS (must fix before 100 customers)
1. Econ Calendar static (H1)
2. Live Momentum empty (H2)
3. Signal metrics hardcoded (C1)
4. BTC ticker normalization (QA Analyse sends "BTC" not "BTCUSD")
5. HYPOTHESIS signals no visual warning (C2)
6. EA indicator invisible (L8)
7. /api/mt5/trailing stub (H7)
8. Portfolio synthetic chart data (H5)
9. Settings localStorage-only panels (H6)
10. Alerts toggles don't persist (M3)
11. Automations sliders don't persist (M1)
