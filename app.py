"""
Trading Signals SaaS — Backend
Fetches real market data, calculates indicators, calls Claude API for analysis.
Supports: Stocks, Crypto, Forex
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os, json
from datetime import datetime

app = Flask(__name__, static_folder="static")
CORS(app)

# ─── INDICATOR HELPERS (TradingView-compatible) ───────────────
def rma(series, length):
    alpha  = 1.0 / length
    vals   = series.values if hasattr(series, "values") else np.array(series)
    result = np.full(len(vals), np.nan)
    valid  = [i for i, v in enumerate(vals) if not np.isnan(v)]
    if len(valid) < length:
        return pd.Series(result, index=getattr(series, "index", None))
    start  = valid[length - 1]
    result[start] = np.nanmean(vals[valid[0]:valid[0] + length])
    for i in range(start + 1, len(vals)):
        if not np.isnan(vals[i]):
            result[i] = alpha * vals[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=getattr(series, "index", None))

def ema_tv(series, span):
    alpha  = 2.0 / (span + 1)
    vals   = series.values if hasattr(series, "values") else np.array(series)
    result = np.full(len(vals), np.nan)
    valid  = [i for i, v in enumerate(vals) if not np.isnan(v)]
    if len(valid) < span:
        return pd.Series(result, index=getattr(series, "index", None))
    start  = valid[span - 1]
    result[start] = np.nanmean(vals[valid[0]:valid[0] + span])
    for i in range(start + 1, len(vals)):
        if not np.isnan(vals[i]):
            result[i] = alpha * vals[i] + (1 - alpha) * result[i - 1]
    return pd.Series(result, index=getattr(series, "index", None))

# ─── INDICATOR CALCULATION ────────────────────────────────────
def calculate_indicators(df):
    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze()

    # RSI 14
    delta = close.diff()
    gain  = delta.clip(lower=0).fillna(0)
    loss  = (-delta).clip(lower=0).fillna(0)
    rsi   = (100 - 100 / (1 + rma(gain, 14) / rma(loss, 14))).iloc[-1]

    # EMAs
    e20  = ema_tv(close, 20).iloc[-1]
    e50  = ema_tv(close, 50).iloc[-1]
    e200 = ema_tv(close, 200).iloc[-1]

    # MACD (12,26,9)
    macd_line = ema_tv(close, 12) - ema_tv(close, 26)
    macd_sig  = ema_tv(macd_line.dropna().reindex(macd_line.index), 9)
    macd_hist = (macd_line - macd_sig).iloc[-1]

    # Bollinger Bands (20, 2σ)
    bb_mid   = close.rolling(20).mean()
    bb_std   = close.rolling(20).std(ddof=0)
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_pos   = float(((close - bb_lower) / (bb_upper - bb_lower)).iloc[-1])
    bb_width = float(((bb_upper - bb_lower) / bb_mid).iloc[-1])

    # ATR 14
    tr  = pd.concat([high - low,
                     (high - close.shift()).abs(),
                     (low  - close.shift()).abs()], axis=1).max(axis=1)
    atr = float(rma(tr, 14).iloc[-1])

    # Volume ratio
    vol_avg   = float(vol.rolling(20).mean().iloc[-1])
    vol_ratio = round(float(vol.iloc[-1]) / vol_avg, 2) if vol_avg > 0 else 1.0

    # Supertrend (3×ATR10)
    atr10  = rma(tr, 10).values
    hl2    = ((high + low) / 2).values
    cv     = close.values
    n      = len(cv)
    bu, bl = hl2 + 3.0 * atr10, hl2 - 3.0 * atr10
    fu, fl = bu.copy(), bl.copy()
    dirn   = np.zeros(n)
    for i in range(1, n):
        fu[i] = bu[i] if (bu[i] < fu[i-1] or cv[i-1] > fu[i-1]) else fu[i-1]
        fl[i] = bl[i] if (bl[i] > fl[i-1] or cv[i-1] < fl[i-1]) else fl[i-1]
        if   cv[i] > fu[i-1]: dirn[i] =  1
        elif cv[i] < fl[i-1]: dirn[i] = -1
        else:                  dirn[i] =  dirn[i-1]
    st_dir = dirn[-1]

    # Price changes
    p  = float(close.iloc[-1])
    p1 = float(close.iloc[-2])  if len(close) > 1  else p
    pw = float(close.iloc[-6])  if len(close) > 6  else float(close.iloc[0])
    pm = float(close.iloc[-22]) if len(close) > 22 else float(close.iloc[0])

    # 52-week range
    high52 = float(high.iloc[-252:].max()) if len(high) >= 252 else float(high.max())
    low52  = float(low.iloc[-252:].min())  if len(low)  >= 252 else float(low.min())

    # Pivot support / resistance (10-bar)
    res = float(high.rolling(10).max().iloc[-1])
    sup = float(low.rolling(10).min().iloc[-1])

    ema_trend = (
        "STRONG BULL" if p > e20 > e50 > e200 else
        "BULL"        if p > e50 and e50 > e200 else
        "STRONG BEAR" if p < e20 < e50 < e200 else
        "BEAR"        if p < e50 and e50 < e200 else
        "MIXED"
    )

    # Chart data — last 90 days
    chart_close  = close.iloc[-90:]
    ema20_series = ema_tv(close, 20).iloc[-90:]
    ema50_series = ema_tv(close, 50).iloc[-90:]
    chart_dates  = [d.strftime("%b %d") for d in chart_close.index]
    chart_prices = [round(float(v), 4) for v in chart_close]
    chart_ema20  = [None if np.isnan(v) else round(float(v), 4) for v in ema20_series]
    chart_ema50  = [None if np.isnan(v) else round(float(v), 4) for v in ema50_series]

    return {
        "price":        round(p, 4),
        "chg_1d":       round((p / p1 - 1) * 100, 2),
        "chg_1w":       round((p / pw - 1) * 100, 2),
        "chg_1m":       round((p / pm - 1) * 100, 2),
        "high_52w":     round(high52, 4),
        "low_52w":      round(low52, 4),
        "rsi":          round(float(rsi), 1),
        "ema20":        round(float(e20), 4),
        "ema50":        round(float(e50), 4),
        "ema200":       round(float(e200), 4),
        "ema_trend":    ema_trend,
        "macd_hist":    round(float(macd_hist), 6),
        "bb_pos":       round(bb_pos, 3),
        "bb_width":     round(bb_width, 3),
        "atr":          round(atr, 4),
        "vol_ratio":    vol_ratio,
        "supertrend":   "BULLISH" if st_dir > 0 else ("BEARISH" if st_dir < 0 else "NEUTRAL"),
        "resistance":   round(res, 4),
        "support":      round(sup, 4),
        "chart_dates":  chart_dates,
        "chart_prices": chart_prices,
        "chart_ema20":  chart_ema20,
        "chart_ema50":  chart_ema50,
    }

# ─── CLAUDE ANALYSIS ─────────────────────────────────────────
def get_analysis(ticker, asset_type, ind):
    rsi_tag = "[OVERSOLD]" if ind["rsi"] < 30 else "[OVERBOUGHT]" if ind["rsi"] > 70 else "[NEUTRAL]"
    macd_tag = "[BULLISH MOMENTUM]" if ind["macd_hist"] > 0 else "[BEARISH MOMENTUM]"
    bb_tag = "near lower band" if ind["bb_pos"] < 0.2 else "near upper band" if ind["bb_pos"] > 0.8 else "mid-range"

    prompt = f"""You are a professional quantitative analyst. Analyze {ticker} ({asset_type}) using the indicator data below and return ONLY a valid JSON object — no markdown, no explanation outside the JSON.

INDICATOR DATA:
Price: {ind['price']} | 1D: {ind['chg_1d']:+}% | 1W: {ind['chg_1w']:+}% | 1M: {ind['chg_1m']:+}%
52W Range: {ind['low_52w']} – {ind['high_52w']}
RSI(14): {ind['rsi']} {rsi_tag}
EMA Trend: {ind['ema_trend']} | EMA20={ind['ema20']} | EMA50={ind['ema50']} | EMA200={ind['ema200']}
MACD Histogram: {ind['macd_hist']} {macd_tag}
Bollinger Position: {ind['bb_pos']:.2f} ({bb_tag}) | BB Width: {ind['bb_width']:.3f}
ATR(14): {ind['atr']} | Volume: {ind['vol_ratio']}x 20-day average
Supertrend: {ind['supertrend']}
10-day Support: {ind['support']} | Resistance: {ind['resistance']}

Return this exact JSON structure:
{{
  "signal": "BUY" or "HOLD" or "SELL",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "summary": "2-3 sentence plain English signal explanation",
  "bull_scenario": "What happens if bulls take control (1-2 sentences)",
  "base_scenario": "Most likely scenario (1-2 sentences)",
  "bear_scenario": "What happens if bears take control (1-2 sentences)",
  "entry": <ideal entry price as number>,
  "stop_loss": <stop loss price as number — place below key support for BUY, above resistance for SELL>,
  "tp1": <conservative take profit — 1:1.5 R/R minimum>,
  "tp2": <moderate take profit — 1:2.5 R/R minimum>,
  "tp3": <aggressive take profit — 1:4 R/R minimum>,
  "rr1": <risk/reward ratio for TP1 rounded to 1dp>,
  "rr2": <risk/reward ratio for TP2 rounded to 1dp>,
  "rr3": <risk/reward ratio for TP3 rounded to 1dp>,
  "rsi_assessment": "one line RSI interpretation",
  "trend_assessment": "one line trend interpretation",
  "macd_assessment": "one line MACD interpretation",
  "volume_assessment": "one line volume interpretation",
  "supertrend_assessment": "one line supertrend interpretation"
}}"""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      "claude-sonnet-4-6",
            "max_tokens": 1500,
            "messages":   [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise Exception(f"Anthropic API error {resp.status_code}: {resp.text[:200]}")

    text = resp.json()["content"][0]["text"].strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

# ─── ROUTES ──────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        body        = request.json or {}
        ticker      = body.get("ticker", "").upper().strip()
        asset_type  = body.get("asset_type", "stock")

        if not ticker:
            return jsonify({"error": "Ticker symbol is required"}), 400

        # Normalise ticker for yfinance
        if asset_type == "crypto" and "-USD" not in ticker:
            ticker = ticker.replace("/", "-")
            if not ticker.endswith("-USD"):
                ticker += "-USD"
        elif asset_type == "forex":
            ticker = ticker.replace("/", "").replace("-", "")
            if not ticker.endswith("=X"):
                ticker += "=X"
        elif asset_type == "commodity":
            commodity_map = {
                "GOLD": "GC=F",   "XAUUSD": "GC=F",
                "SILVER": "SI=F", "XAGUSD": "SI=F",
                "OIL": "CL=F",    "WTI": "CL=F", "CRUDE": "CL=F", "CRUDEOIL": "CL=F",
                "NATGAS": "NG=F", "GAS": "NG=F",
                "COPPER": "HG=F", "WHEAT": "ZW=F", "CORN": "ZC=F", "PLATINUM": "PL=F",
            }
            ticker = commodity_map.get(ticker, ticker)
        elif asset_type == "index":
            index_map = {
                "SPX": "^GSPC",    "SP500": "^GSPC",  "SMP500": "^GSPC",
                "S&P500": "^GSPC", "S&P": "^GSPC",    "US500": "^GSPC",
                "NDX": "^IXIC",    "NASDAQ": "^IXIC",  "NAS100": "^IXIC",  "US100": "^IXIC",
                "DOW": "^DJI",     "DJIA": "^DJI",     "DJI": "^DJI",       "US30": "^DJI",
                "FTSE": "^FTSE",   "FTSE100": "^FTSE", "UK100": "^FTSE",
                "DAX": "^GDAXI",   "GER40": "^GDAXI",
                "NIKKEI": "^N225", "NKY": "^N225",     "JPN225": "^N225",
                "HSI": "^HSI",     "HANGSENG": "^HSI",
                "CAC": "^FCHI",    "CAC40": "^FCHI",
                "ASX": "^AXJO",    "ASX200": "^AXJO",
            }
            ticker = index_map.get(ticker, ticker)

        # Fetch OHLCV
        df = yf.download(ticker, period="1y", interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 50:
            return jsonify({"error": f"No data found for '{ticker}'. Check the symbol and try again."}), 404

        # Indicators + AI analysis
        ind      = calculate_indicators(df)
        analysis = get_analysis(ticker, asset_type, ind)

        return jsonify({
            "ticker":     ticker,
            "asset_type": asset_type,
            "timestamp":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            **ind,
            **analysis,
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Analysis generation failed. Please try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── HEALTH CHECK ────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
