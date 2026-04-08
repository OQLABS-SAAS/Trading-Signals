# DotVerse — Handoff Brief for Sonnet
## Chart Fix + UI/UX Build Instructions
### Compiled by Opus from live investigation on April 8, 2026

---

## 1. THE CHART PROBLEM (Critical — Must Fix First)

### Root Cause: Two Separate Bugs

**Bug A: `renderResultsV2()` never calls `renderChart(d)`**

The analysis flow in `doAnalyze()` (line ~3094 in index.html) calls:
1. `renderResultsV2(d)` — updates signal hero, info strip, indicators, footprint, calculator, etc.
2. `renderResults(d)` — the OLD render function, which CRASHES at line 3113 with `TypeError: Cannot set properties of null`

`renderChart(d)` lives inside the old `renderResults()` at line 3136. Because `renderResults()` crashes BEFORE reaching that line, `renderChart(d)` is NEVER executed.

**Fix already applied (committed but NOT pushed):** Added `try { renderChart(d); } catch(e) { console.warn('renderChart:', e); }` at the end of `renderResultsV2()` (around line 6963).

**Bug B: Backend returns EMPTY chart arrays for crypto on Railway**

Verified via live browser JS console:
```json
{
  "ticker": "BTC-USD",
  "timeframe": "1h",
  "chart_prices_len": 0,
  "chart_opens_len": 0,
  "chart_volumes_len": 0,
  "chart_rsi_len": 0,
  "has_tv": true,
  "tv_symbol": "BINANCE:BTCUSDT"
}
```

The backend data pipeline in `app.py` `/api/analyze` (line 1725):
1. **Step 1 — TradingView scanner** (`fetch_tv_data`): Returns indicator values (RSI, EMA, MACD) but NO OHLCV history. This succeeds (`tv_ok = true`).
2. **Step 2 — yfinance** (`safe_download`): Supposed to return OHLC chart arrays. Uses Yahoo Finance chart API at `https://query1.finance.yahoo.com/v8/finance/chart/{ticker}`. For BTC-USD on Railway's IP, Yahoo returns 429 (rate-limited) or empty data.
3. **Binance fallback** (`fetch_binance_ohlcv`): Exists at line 313 of `app.py`. Called when Yahoo fails. Uses `https://api.binance.com/api/v3/klines`. This SHOULD work but apparently isn't returning data either, OR the result doesn't flow into the chart arrays properly.

**The backend flow at lines 1786-1830:**
```python
if not df.empty and len(df) >= 30:
    ind_full = calculate_indicators(df, timeframe)
    if tv_ok:
        # TV is primary — only take chart arrays from yfinance
        for k in ("chart_dates","chart_prices","chart_ema20",...):
            ind[k] = ind_full.get(k, [])
```

If `df` is empty (yfinance failed) AND Binance fallback also failed, `ind` never gets chart arrays. The `calculate_indicators()` function (line ~420) is what generates `chart_prices`, `chart_dates`, etc.

**What needs to happen:**
- When yfinance fails, the Binance fallback data needs to go through `calculate_indicators()` to generate the chart arrays
- Currently `safe_download()` calls `fetch_binance_ohlcv()` internally (line 313), but by the time control returns to `/api/analyze`, the check at line 1786 (`if not df.empty and len(df) >= 30`) should pass if Binance succeeded
- Need to add logging or test to confirm Binance is actually being hit and returning data on Railway
- TIMEFRAME_CONFIG for "1h": `{"interval": "1h", "period": "30d", "chart_bars": 100, "date_fmt": "%b%d %H:%M"}`
- Binance interval map at line 196: `{"1h":"1h"}` — should work

**Likely issue:** Railway's outbound IP may also be blocked by Binance, OR `_to_binance_symbol("BTC-USD")` mapping is failing. Check the `_to_binance_symbol()` function.

### What the renderChart function expects (frontend)

`renderChart(d)` at line ~3751 in index.html:
- Reads: `d.chart_dates`, `d.chart_prices`, `d.chart_opens`, `d.chart_highs`, `d.chart_lows`, `d.chart_ema20`, `d.chart_ema50`, `d.chart_volumes`, `d.chart_bb_upper`, `d.chart_bb_lower`, `d.chart_rsi`, `d.chart_buy_signals`, `d.chart_sell_signals`
- If `prices.length === 0`: Falls to TradingView embed (BUT USER SAYS NO TRADINGVIEW — see section 3)
- If prices exist: Creates Chart.js candlestick chart with:
  - Price line or OHLC candles (based on `chartOHLC`)
  - EMA 20 (amber) and EMA 50 (gray) overlays
  - BB bands (blue, togglable)
  - Buy/sell signal arrows (green ▲ / red ▼)
  - Volume bars (separate canvas below)
  - RSI sub-chart (separate canvas below)

### Canvas elements (already added to HTML):
```html
<canvas id="priceChart" style="width:100%;height:100%;"></canvas>  <!-- in 300px div -->
<canvas id="volChart" style="width:100%;height:100%;"></canvas>    <!-- in 80px div -->
<canvas id="rsiChart" style="width:100%;height:100%;"></canvas>    <!-- in 80px div, wrapped in #rsiChartWrap -->
<div id="tvChartEmbed" style="display:none;"></div>                <!-- REMOVE THIS -->
```

Chart.js 4.4.1 CDN already added:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
```

---

## 2. CRITICAL USER REQUIREMENT: NO TRADINGVIEW CHARTS

Per Omar's explicit instruction: **"we are never going to use TradingView charts"**

All TradingView embed code must be removed from the frontend:
- Remove `<div id="tvChartEmbed">` from HTML
- Remove `rebuildTVEmbed()` function
- Remove TV fallback path in `renderChart()` (lines 3846-3889)
- When no OHLC data available, show a styled "Chart data unavailable — retrying..." message instead
- Remove all `tvMode`, `tvStudies`, `tvParams` variables

---

## 3. UI/UX BUILD INSTRUCTIONS (Signals Tab — Empty State)

### Design System:
- Background: `#0C0A08` (warm black)
- Amber: `#f5a623` (primary accent)
- Green: `#00c98d` (bullish)
- Red: `#ff4459` (bearish)
- Fonts: Anybody (display/brutalist), Fira Code (mono), Sora (body), 14px base

### Empty State (before analysis):
The main-col has this structure:
```
main-col (flex column, min-height: calc(100vh - 90px))
  ├── sigHeroWrap (display:none)
  ├── cmdBar (ticker input + pills + instruments)
  ├── signalResults (display:none)
  └── signalEmpty (flex:1, centers its content vertically)
```

**Current state (committed):**
- cmdBar sits at top with input, asset pills (Crypto/Stock/Forex/Commodity/Index), timeframe pills (15M/1H/4H/1D), auto-refresh, and instrument quick-select row
- signalEmpty has flex:1 and centers a breathing animated dotverse logo (280px SVG with CSS scale animation), brand name, tagline, and instruction text
- CSS: `.gpill` and instrument buttons have `border-radius:20px` (pill shape)
- Instrument row has `justify-content:center; flex-wrap:wrap`

### After Analysis State:
When `renderResultsV2(d)` runs:
- `sigHeroWrap` shown → signal hero with BUY/SELL/HOLD badge, entry/SL/TP levels, confidence ring, win rate
- `signalResults` shown → info strip, chart, indicators, footprint, alignment, narrative, calculator, MTF
- `signalEmpty` hidden

### What Works (verified on live site):
- Signal hero populates correctly (signal, entry price, confidence ring, win rate)
- Info strip populates (Change, R:R, ATR, Volume, MACD, RSI, Timeframe)
- Chart title + indicator tags update (EMA20, EMA50, BB values)
- Calculator auto-fills entry/SL/TP values AND auto-calls recalc()
- Indicator cards, footprint cards, MTF grid all populate
- Click-to-expand works on info cells, indicator cards, fp-cards, mtf-cells, alignment rows

### What's Broken:
1. **Chart area is blank** — renderChart never called (Bug A above) + no OHLC data (Bug B above)
2. **SL/TP values show 0.0000** — Backend sometimes returns 0 for stop_loss/tp1/tp2/tp3 (Claude analysis didn't produce them)
3. **TradingView embed code still present** — needs removal per user requirement

---

## 4. OTHER TABS STATUS (from audit)

### Strategy Engine (tab-strategy, lines 1952-2235):
- UI renders correctly with 12 strategy cards
- sePickTab() works, seMode() works, seQPCat() works
- **BROKEN:** seRunBtn has NO onclick handler — dead button
- **BROKEN:** No backend API wiring for strategy execution

### Scanner (tab-scanner, lines 2236-2282):
- **FULLY FUNCTIONAL** — runScanner() calls /api/scan-list, renders results
- Filter buttons toggle visual state but don't actually filter

### Backtest (tab-backtest, lines 2286-2367):
- **COMPLETELY BROKEN** — 25+ element IDs referenced in JS don't exist in HTML
- backtestPanel, backtestResults, btPnlUsd, btTradesTbody, etc. all missing
- The runBacktest() function exists but renders to non-existent elements
- Tab shows hardcoded static data only

### Simulation (tab-simulation, lines 2371-2427):
- Static mockup only — not connected to /api/simulate results
- Simulation output goes to a modal (simModal), not to this tab

### News (tab-news, lines 2431-2474):
- Completely static — 3 hardcoded news cards
- No API integration

---

## 5. COMMITS MADE (not yet pushed)

All on branch `main`, repository `OQLABS-SAAS/Trading-Signals`:

1. `965408a` — Center command bar + animated logo on empty state, replace static SVG chart with Chart.js canvas
2. `1ceac56` — Fix empty state vertical centering
3. `887efec` — Fix empty state: signalEmpty fills remaining space with flex:1, bigger logo (140px)
4. `77fff5f` — Fix calculator: call recalc() after populating fields, update asset price
5. `7ba4a32` — Make empty state logo much bigger — 280px
6. `132657b` — Breathing animated logo, centered controls, rounded pill buttons
7. `bcfb138` — Critical fix: call renderChart(d) from renderResultsV2 + canvas sizing

**NONE OF THESE HAVE BEEN PUSHED YET.**

To push: `cd ~/Documents/trading-signals-saas && git push origin main`

---

## 6. FILES MODIFIED

- `static/index.html` — All changes are in this single file (~8500 lines)
- `app.py` — NOT modified (backend changes needed but not yet made)

---

## 7. PRIORITY FIX ORDER

1. **Backend:** Fix yfinance/Binance to return OHLC data for crypto on Railway (app.py)
2. **Frontend:** Remove all TradingView embed code (index.html)
3. **Frontend:** Verify renderChart(d) renders Chart.js candles when OHLC data present
4. **Frontend:** Add "Chart data unavailable" fallback message when no OHLC data
5. **Backtest tab:** Add missing HTML elements that runBacktest() references
6. **Strategy Engine:** Wire seRunBtn to backend
