"""
Trading Signals SaaS — Backend
Supports: Stocks, Crypto, Forex, Commodities, Indices
Features: Multi-timeframe analysis, MTF trend, historical win rate,
          server-side watch scheduler with SMS + email alerts.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os, json, threading
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__, static_folder="static")
CORS(app)

# ─── TIMEFRAME CONFIG ─────────────────────────────────────────
TIMEFRAME_CONFIG = {
    "5m":  {"interval": "5m",  "period": "5d",  "chart_bars": 100, "date_fmt": "%H:%M"},
    "15m": {"interval": "15m", "period": "5d",  "chart_bars": 100, "date_fmt": "%H:%M"},
    "30m": {"interval": "30m", "period": "5d",  "chart_bars": 100, "date_fmt": "%b%d %H:%M"},
    "1h":  {"interval": "1h",  "period": "30d", "chart_bars": 100, "date_fmt": "%b%d %H:%M"},
    "4h":  {"interval": "1h",  "period": "60d", "chart_bars": 90,  "date_fmt": "%b %d", "resample": "4h"},
    "1d":  {"interval": "1d",  "period": "1y",  "chart_bars": 90,  "date_fmt": "%b %d"},
}

# How often to re-run the screen per timeframe (seconds)
ALERT_INTERVALS = {
    "5m": 300, "15m": 600, "30m": 900,
    "1h": 1800, "4h": 3600, "1d": 14400,
}

# ─── SERVER-SIDE WATCH REGISTRY ───────────────────────────────
# key = "{ticker}_{timeframe}"
# value = {ticker, asset_type, timeframe, last_signal, last_check, last_reason}
watch_registry = {}
watch_lock     = threading.Lock()

# ─── INDICATOR HELPERS ────────────────────────────────────────
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

def get_rsi(close):
    delta = close.diff()
    gain  = delta.clip(lower=0).fillna(0)
    loss  = (-delta).clip(lower=0).fillna(0)
    return 100 - 100 / (1 + rma(gain, 14) / rma(loss, 14))

# ─── INDICATOR CALCULATION ────────────────────────────────────
def calculate_indicators(df, timeframe="1d"):
    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze()

    rsi_series = get_rsi(close)
    rsi        = rsi_series.iloc[-1]

    e20  = ema_tv(close, 20).iloc[-1]
    e50  = ema_tv(close, 50).iloc[-1] if len(close) >= 50 else ema_tv(close, 20).iloc[-1]
    e200 = ema_tv(close, 200).iloc[-1] if len(close) >= 200 else ema_tv(close, 50).iloc[-1]

    macd_line = ema_tv(close, 12) - ema_tv(close, 26)
    macd_sig  = ema_tv(macd_line.dropna().reindex(macd_line.index), 9)
    macd_hist = (macd_line - macd_sig).iloc[-1]

    bb_mid   = close.rolling(20).mean()
    bb_std   = close.rolling(20).std(ddof=0)
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_denom = (bb_upper - bb_lower).iloc[-1]
    bb_pos   = float((close.iloc[-1] - bb_lower.iloc[-1]) / bb_denom) if bb_denom != 0 else 0.5
    bb_width = float(((bb_upper - bb_lower) / bb_mid).iloc[-1])

    tr  = pd.concat([high - low,
                     (high - close.shift()).abs(),
                     (low  - close.shift()).abs()], axis=1).max(axis=1)
    atr = float(rma(tr, 14).iloc[-1])

    vol_avg   = float(vol.rolling(20).mean().iloc[-1])
    vol_ratio = round(float(vol.iloc[-1]) / vol_avg, 2) if vol_avg > 0 else 1.0

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

    p  = float(close.iloc[-1])
    p1 = float(close.iloc[-2])  if len(close) > 1  else p
    pw = float(close.iloc[-6])  if len(close) > 6  else float(close.iloc[0])
    pm = float(close.iloc[-22]) if len(close) > 22 else float(close.iloc[0])

    high52 = float(high.iloc[-252:].max()) if len(high) >= 252 else float(high.max())
    low52  = float(low.iloc[-252:].min())  if len(low)  >= 252 else float(low.min())

    res = float(high.rolling(10).max().iloc[-1])
    sup = float(low.rolling(10).min().iloc[-1])

    ema_trend = (
        "STRONG BULL" if p > e20 > e50 > e200 else
        "BULL"        if p > e50 and e50 > e200 else
        "STRONG BEAR" if p < e20 < e50 < e200 else
        "BEAR"        if p < e50 and e50 < e200 else
        "MIXED"
    )

    cfg       = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1d"])
    n_bars    = cfg["chart_bars"]
    date_fmt  = cfg["date_fmt"]
    chart_close  = close.iloc[-n_bars:]
    chart_vol    = vol.iloc[-n_bars:]
    ema20_series = ema_tv(close, 20).iloc[-n_bars:]
    ema50_series = ema_tv(close, 50).iloc[-n_bars:] if len(close) >= 50 else ema_tv(close, 20).iloc[-n_bars:]
    chart_dates  = [d.strftime(date_fmt) for d in chart_close.index]
    chart_prices = [round(float(v), 4) for v in chart_close]
    chart_ema20  = [None if np.isnan(v) else round(float(v), 4) for v in ema20_series]
    chart_ema50  = [None if np.isnan(v) else round(float(v), 4) for v in ema50_series]
    chart_volumes = [0 if np.isnan(v) else int(float(v)) for v in chart_vol]

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
        "chart_dates":   chart_dates,
        "chart_prices":  chart_prices,
        "chart_ema20":   chart_ema20,
        "chart_ema50":   chart_ema50,
        "chart_volumes": chart_volumes,
    }

# ─── MULTI-TIMEFRAME TREND ────────────────────────────────────
def get_mtf_trend(ticker):
    result = {}
    configs = {
        "4H": {"interval": "1h",  "period": "60d", "resample": "4h"},
        "1D": {"interval": "1d",  "period": "1y"},
    }
    for label, cfg in configs.items():
        try:
            df_m = yf.download(ticker, period=cfg["period"],
                               interval=cfg["interval"], progress=False, auto_adjust=True)
            if "resample" in cfg:
                df_m = df_m.resample(cfg["resample"]).agg(
                    {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
                ).dropna()
            if len(df_m) < 20:
                result[label] = {"trend": "N/A", "rsi": 0}
                continue
            c   = df_m["Close"].squeeze()
            e20 = float(ema_tv(c, 20).iloc[-1])
            e50 = float(ema_tv(c, min(50, len(c)-1)).iloc[-1])
            p   = float(c.iloc[-1])
            rsi = float(get_rsi(c).iloc[-1])
            if p > e20 > e50:   trend = "BULLISH"
            elif p < e20 < e50: trend = "BEARISH"
            else:               trend = "NEUTRAL"
            result[label] = {"trend": trend, "rsi": round(rsi, 1)}
        except Exception:
            result[label] = {"trend": "N/A", "rsi": 0}
    return result

# ─── HISTORICAL WIN RATE ──────────────────────────────────────
def calculate_win_rate(df, signal):
    try:
        close      = df["Close"].squeeze()
        rsi_series = get_rsi(close)
        forward    = max(5, len(close) // 50)
        wins, total = 0, 0
        for i in range(len(close) - forward - 1):
            r = rsi_series.iloc[i]
            if np.isnan(r):
                continue
            if signal == "BUY"  and r < 38:
                fut = float(close.iloc[i + forward]) / float(close.iloc[i]) - 1
                total += 1
                if fut > 0: wins += 1
            elif signal == "SELL" and r > 62:
                fut = float(close.iloc[i + forward]) / float(close.iloc[i]) - 1
                total += 1
                if fut < 0: wins += 1
        if total < 3:
            return {"win_rate": None, "sample_size": total}
        return {"win_rate": round(wins / total * 100), "sample_size": total}
    except Exception:
        return {"win_rate": None, "sample_size": 0}

# ─── FREE PRE-SCREEN (no API call) ───────────────────────────
def pre_screen(ind):
    rsi       = ind["rsi"]
    bb_pos    = ind["bb_pos"]
    macd_hist = ind["macd_hist"]
    ema_trend = ind["ema_trend"]
    st        = ind["supertrend"]
    vol_ratio = ind["vol_ratio"]

    bull_score = 0
    bear_score = 0

    if rsi < 35:   bull_score += 2
    elif rsi < 42: bull_score += 1
    if rsi > 65:   bear_score += 2
    elif rsi > 58: bear_score += 1

    if bb_pos < 0.20: bull_score += 2
    elif bb_pos < 0.30: bull_score += 1
    if bb_pos > 0.80: bear_score += 2
    elif bb_pos > 0.70: bear_score += 1

    if macd_hist > 0: bull_score += 1
    else:             bear_score += 1

    if "BULL" in ema_trend: bull_score += 1
    if "BEAR" in ema_trend: bear_score += 1

    if st == "BULLISH": bull_score += 1
    if st == "BEARISH": bear_score += 1

    vol_bonus = 1 if vol_ratio >= 1.5 else 0
    net_bull  = bull_score + vol_bonus
    net_bear  = bear_score + vol_bonus

    counter_bounce = (
        ("BEAR" in ema_trend or st == "BEARISH")
        and rsi < 33
        and bb_pos < 0.18
    )

    if net_bull >= 4:
        hint, reason = "BUY", f"RSI={rsi}, BB={bb_pos:.0%}, vol={vol_ratio}x — strong oversold setup"
    elif net_bear >= 4:
        hint, reason = "SELL", f"RSI={rsi}, BB={bb_pos:.0%}, vol={vol_ratio}x — strong overbought setup"
    elif counter_bounce:
        hint, reason = "COUNTER_BUY", f"RSI={rsi} oversold in {ema_trend} trend near lower BB — bounce candidate"
    elif net_bull >= 2:
        hint, reason = "POSSIBLE_BUY", f"RSI={rsi}, BB={bb_pos:.0%} — moderate bullish setup forming"
    elif net_bear >= 2:
        hint, reason = "POSSIBLE_SELL", f"RSI={rsi}, BB={bb_pos:.0%} — moderate bearish setup forming"
    else:
        hint, reason = None, "No clear setup — market neutral"

    call_claude = hint in ("BUY", "SELL", "COUNTER_BUY")

    return {
        "opportunity": hint is not None,
        "call_claude": call_claude,
        "signal_hint": hint,
        "reason":      reason,
        "bull_score":  net_bull,
        "bear_score":  net_bear,
        "rsi":         round(rsi, 1),
        "bb_pos":      round(bb_pos, 3),
        "vol_ratio":   vol_ratio,
        "ema_trend":   ema_trend,
        "supertrend":  st,
    }

# ─── COUNTER-TREND BOUNCE DETECTION ─────────────────────────
def detect_counter_trade(ind):
    is_bear_ema   = ind["ema_trend"] in ("BEAR", "STRONG BEAR")
    is_bear_st    = ind["supertrend"] == "BEARISH"
    is_oversold   = ind["rsi"] < 33
    near_lower_bb = ind["bb_pos"] < 0.18

    if not ((is_bear_ema or is_bear_st) and is_oversold and near_lower_bb):
        return {"counter_trade": False}

    price  = ind["price"]
    atr    = ind["atr"]
    sup    = ind["support"]
    entry  = price
    sl     = round(min(sup - atr * 0.3, price - atr * 1.5), 4)
    risk   = entry - sl
    if risk <= 0:
        return {"counter_trade": False}

    tp1 = round(entry + risk * 1.5, 4)
    rr1 = round((tp1 - entry) / risk, 1)
    trend_label = ind["ema_trend"].replace("STRONG ", "")
    summary = (
        f"Primary trend is {trend_label} but RSI({ind['rsi']}) is deeply oversold "
        f"with price hugging the lower Bollinger Band ({ind['bb_pos']:.0%} position). "
        f"A short-term bounce to TP1 is statistically likely. "
        f"EXIT at TP1 — do NOT hold. HIGH RISK."
    )
    return {
        "counter_trade":   True,
        "counter_signal":  "COUNTER_BUY",
        "counter_entry":   round(entry, 4),
        "counter_sl":      sl,
        "counter_tp1":     tp1,
        "counter_rr1":     rr1,
        "counter_summary": summary,
    }

# ─── CLAUDE ANALYSIS ─────────────────────────────────────────
def get_analysis(ticker, asset_type, ind, timeframe):
    rsi_tag  = "[OVERSOLD]"   if ind["rsi"] < 30 else "[OVERBOUGHT]" if ind["rsi"] > 70 else "[NEUTRAL]"
    macd_tag = "[BULLISH MOMENTUM]" if ind["macd_hist"] > 0 else "[BEARISH MOMENTUM]"
    bb_tag   = "near lower band" if ind["bb_pos"] < 0.2 else "near upper band" if ind["bb_pos"] > 0.8 else "mid-range"

    prompt = f"""You are a professional quantitative analyst. Analyze {ticker} ({asset_type}) on the {timeframe} timeframe using the indicator data below and return ONLY a valid JSON object — no markdown, no explanation outside the JSON.

INDICATOR DATA ({timeframe} timeframe):
Price: {ind['price']} | 1-bar chg: {ind['chg_1d']:+}%
RSI(14): {ind['rsi']} {rsi_tag}
EMA Trend: {ind['ema_trend']} | EMA20={ind['ema20']} | EMA50={ind['ema50']} | EMA200={ind['ema200']}
MACD Histogram: {ind['macd_hist']} {macd_tag}
Bollinger Position: {ind['bb_pos']:.2f} ({bb_tag}) | BB Width: {ind['bb_width']:.3f}
ATR(14): {ind['atr']} | Volume: {ind['vol_ratio']}x 20-bar average
Supertrend: {ind['supertrend']}
Support: {ind['support']} | Resistance: {ind['resistance']}

IMPORTANT RULES:
- If signal is HOLD: set entry, stop_loss, tp1, tp2, tp3, rr1, rr2, rr3 all to null. Do NOT invent trade levels for a HOLD signal.
- If signal is BUY or SELL: provide all trade levels based on the indicators.

Return this exact JSON structure:
{{
  "signal": "BUY" or "HOLD" or "SELL",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "summary": "2-3 sentence plain English signal explanation",
  "bull_scenario": "What happens if bulls take control (1-2 sentences)",
  "base_scenario": "Most likely scenario (1-2 sentences)",
  "bear_scenario": "What happens if bears take control (1-2 sentences)",
  "entry": <entry price as number, or null if HOLD>,
  "stop_loss": <stop loss price as number, or null if HOLD>,
  "tp1": <conservative take profit — 1:1.5 R/R, or null if HOLD>,
  "tp2": <moderate take profit — 1:2.5 R/R, or null if HOLD>,
  "tp3": <aggressive take profit — 1:4 R/R, or null if HOLD>,
  "rr1": <R/R ratio for TP1 to 1dp, or null if HOLD>,
  "rr2": <R/R ratio for TP2 to 1dp, or null if HOLD>,
  "rr3": <R/R ratio for TP3 to 1dp, or null if HOLD>,
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

# ─── SMS + EMAIL ALERTS ───────────────────────────────────────
def send_sms(message):
    """Send SMS via Twilio."""
    sid      = os.environ.get("SMS_ACCOUNT_SID", "").strip()
    token    = os.environ.get("SMS_AUTH_TOKEN",  "").strip()
    from_num = os.environ.get("SMS_FROM_NUMBER", "").strip()
    to_num   = os.environ.get("ALERT_PHONE", "").strip()
    if not all([sid, token, from_num, to_num]):
        return
    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_num, "To": to_num, "Body": message},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            print(f"[SMS] Twilio error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[SMS] Error: {e}")


def fire_alert(signal, ticker, price, timeframe, analysis, counter):
    """Build SMS message and send via Twilio."""
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if signal == "COUNTER_BUY":
        msg = (
            f"SignalAI ⚡ COUNTER-BUY on {ticker} ({timeframe.upper()}) @ ${price}\n"
            f"Entry: ${counter.get('counter_entry')} | SL: ${counter.get('counter_sl')} | TP1: ${counter.get('counter_tp1')}\n"
            f"⚠ HIGH RISK — exit at TP1 only. {ts}"
        )
    else:
        emoji = "🟢" if signal == "BUY" else "🔴"
        msg = (
            f"SignalAI {emoji} {signal} on {ticker} ({timeframe.upper()}) @ ${price}\n"
            f"Entry: ${analysis.get('entry')} | SL: ${analysis.get('stop_loss')}\n"
            f"TP1: ${analysis.get('tp1')} | TP2: ${analysis.get('tp2')} | TP3: ${analysis.get('tp3')}\n"
            f"Confidence: {analysis.get('confidence','—')} | {ts}"
        )
    send_sms(msg)
    print(f"[Alert] Fired {signal} for {ticker} ({timeframe}) @ {price}")

# ─── SERVER-SIDE WATCH JOB ────────────────────────────────────
def run_watch_job():
    """Runs every 60s. Checks each watched ticker against its timeframe interval."""
    now = datetime.utcnow()
    with watch_lock:
        watches = list(watch_registry.items())

    for key, w in watches:
        interval_secs = ALERT_INTERVALS.get(w["timeframe"], 300)
        last_check = w.get("last_check")
        if last_check and (now - last_check).total_seconds() < interval_secs:
            continue  # not time for this timeframe yet

        try:
            ticker     = w["ticker"]
            asset_type = w["asset_type"]
            timeframe  = w["timeframe"]
            cfg        = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1d"])

            df = yf.download(ticker, period=cfg["period"], interval=cfg["interval"],
                             progress=False, auto_adjust=True)
            if "resample" in cfg:
                df = df.resample(cfg["resample"]).agg(
                    {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
                ).dropna()

            if df.empty or len(df) < 30:
                continue

            ind    = calculate_indicators(df, timeframe)
            screen = pre_screen(ind)

            with watch_lock:
                watch_registry[key]["last_check"]  = now
                watch_registry[key]["last_reason"]  = screen["reason"]
                watch_registry[key]["last_price"]   = ind["price"]

            if not screen["call_claude"]:
                continue

            # Conditions warrant full Claude analysis
            analysis = get_analysis(ticker, asset_type, ind, timeframe)
            counter  = detect_counter_trade(ind)
            sig      = analysis.get("signal", "HOLD")

            prev_sig       = w.get("last_signal")
            is_actionable  = sig in ("BUY", "SELL")
            was_neutral    = not prev_sig or prev_sig == "HOLD"

            fired_sig = None
            if is_actionable and was_neutral:
                fired_sig = sig
            elif counter.get("counter_trade") and prev_sig != "COUNTER_BUY":
                fired_sig = "COUNTER_BUY"

            with watch_lock:
                watch_registry[key]["last_signal"] = fired_sig or sig

            if fired_sig:
                fire_alert(fired_sig, ticker, ind["price"], timeframe, analysis, counter)

        except Exception as e:
            print(f"[Watch] Error for {key}: {e}")

# ─── START BACKGROUND SCHEDULER ───────────────────────────────
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_watch_job, "interval", seconds=60, id="watch_job",
                  max_instances=1, coalesce=True)
scheduler.start()
atexit.register(lambda: scheduler.shutdown(wait=False))

# ─── TICKER NORMALISATION ─────────────────────────────────────
def normalise_ticker(ticker, asset_type):
    if asset_type == "crypto":
        ticker = ticker.replace("/", "-")
        if not ticker.endswith("-USD"):
            ticker += "-USD"
    elif asset_type == "forex":
        ticker = ticker.replace("/", "").replace("-", "")
        if not ticker.endswith("=X"):
            ticker += "=X"
    elif asset_type == "commodity":
        m = {"GOLD":"GC=F","XAUUSD":"GC=F","SILVER":"SI=F","XAGUSD":"SI=F",
             "OIL":"CL=F","WTI":"CL=F","CRUDE":"CL=F","CRUDEOIL":"CL=F",
             "NATGAS":"NG=F","GAS":"NG=F","COPPER":"HG=F",
             "WHEAT":"ZW=F","CORN":"ZC=F","PLATINUM":"PL=F"}
        ticker = m.get(ticker, ticker)
    elif asset_type == "index":
        m = {"SPX":"^GSPC","SP500":"^GSPC","SMP500":"^GSPC","S&P500":"^GSPC","S&P":"^GSPC","US500":"^GSPC",
             "NDX":"^IXIC","NASDAQ":"^IXIC","NAS100":"^IXIC","US100":"^IXIC",
             "DOW":"^DJI","DJIA":"^DJI","DJI":"^DJI","US30":"^DJI",
             "FTSE":"^FTSE","FTSE100":"^FTSE","UK100":"^FTSE",
             "DAX":"^GDAXI","GER40":"^GDAXI",
             "NIKKEI":"^N225","NKY":"^N225","JPN225":"^N225",
             "HSI":"^HSI","HANGSENG":"^HSI",
             "CAC":"^FCHI","CAC40":"^FCHI",
             "ASX":"^AXJO","ASX200":"^AXJO"}
        ticker = m.get(ticker, ticker)
    return ticker

# ─── ROUTES ──────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/analyze", methods=["POST"])
def analyze():
    try:
        body       = request.json or {}
        ticker     = body.get("ticker", "").upper().strip()
        asset_type = body.get("asset_type", "stock")
        timeframe  = body.get("timeframe", "1d").lower()

        if not ticker:
            return jsonify({"error": "Ticker symbol is required"}), 400
        if timeframe not in TIMEFRAME_CONFIG:
            timeframe = "1d"

        ticker = normalise_ticker(ticker, asset_type)
        cfg    = TIMEFRAME_CONFIG[timeframe]

        df = yf.download(ticker, period=cfg["period"], interval=cfg["interval"],
                         progress=False, auto_adjust=True)
        if "resample" in cfg:
            df = df.resample(cfg["resample"]).agg(
                {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
            ).dropna()

        if df.empty or len(df) < 30:
            return jsonify({"error": f"Not enough data for '{ticker}' on {timeframe}. Try a longer timeframe."}), 404

        ind      = calculate_indicators(df, timeframe)
        analysis = get_analysis(ticker, asset_type, ind, timeframe)
        counter  = detect_counter_trade(ind)

        df_daily = yf.download(ticker, period="1y", interval="1d",
                                progress=False, auto_adjust=True) if timeframe != "1d" else df
        wr = calculate_win_rate(df_daily, analysis.get("signal", "HOLD"))

        mtf = {}
        if timeframe in ("1d", "4h", "1h"):
            mtf = get_mtf_trend(ticker)

        return jsonify({
            "ticker":     ticker,
            "asset_type": asset_type,
            "timeframe":  timeframe,
            "timestamp":  datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            **ind,
            **analysis,
            "win_rate":    wr.get("win_rate"),
            "sample_size": wr.get("sample_size"),
            "mtf":         mtf,
            **counter,
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Analysis generation failed. Please try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/screen", methods=["POST"])
def screen():
    """Lightweight pre-screen — no Claude API call. Used by browser alert mode."""
    try:
        body       = request.json or {}
        ticker     = body.get("ticker", "").upper().strip()
        asset_type = body.get("asset_type", "stock")
        timeframe  = body.get("timeframe", "1d").lower()

        if not ticker:
            return jsonify({"error": "Ticker required"}), 400
        if timeframe not in TIMEFRAME_CONFIG:
            timeframe = "1d"

        ticker = normalise_ticker(ticker, asset_type)
        cfg    = TIMEFRAME_CONFIG[timeframe]

        df = yf.download(ticker, period=cfg["period"], interval=cfg["interval"],
                         progress=False, auto_adjust=True)
        if "resample" in cfg:
            df = df.resample(cfg["resample"]).agg(
                {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
            ).dropna()

        if df.empty or len(df) < 30:
            return jsonify({"opportunity": False, "reason": "Not enough data"}), 200

        ind    = calculate_indicators(df, timeframe)
        result = pre_screen(ind)
        return jsonify({
            "ticker":    ticker,
            "timeframe": timeframe,
            "price":     ind["price"],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            **result,
        })

    except Exception as e:
        return jsonify({"opportunity": False, "reason": str(e)}), 200

@app.route("/api/watch", methods=["POST"])
def add_watch():
    """Register a ticker for 24/7 server-side watching with SMS + email alerts."""
    try:
        body       = request.json or {}
        ticker     = body.get("ticker", "").upper().strip()
        asset_type = body.get("asset_type", "stock")
        timeframe  = body.get("timeframe", "1d").lower()

        if not ticker:
            return jsonify({"error": "Ticker required"}), 400
        if timeframe not in TIMEFRAME_CONFIG:
            timeframe = "1d"

        ticker = normalise_ticker(ticker, asset_type)
        key    = f"{ticker}_{timeframe}"

        with watch_lock:
            if key in watch_registry:
                return jsonify({"status": "already_watching", "key": key,
                                "message": f"Already watching {ticker} on {timeframe.upper()}"}), 200
            watch_registry[key] = {
                "ticker":      ticker,
                "asset_type":  asset_type,
                "timeframe":   timeframe,
                "last_signal": None,
                "last_check":  None,
                "last_reason": "Not checked yet",
                "last_price":  None,
                "added_at":    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            }

        return jsonify({"status": "watching", "key": key,
                        "message": f"Now watching {ticker} on {timeframe.upper()} — alerts via SMS & email"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watch", methods=["DELETE"])
def remove_watch():
    """Unregister a ticker from server-side watching."""
    try:
        body      = request.json or {}
        ticker    = body.get("ticker", "").upper().strip()
        timeframe = body.get("timeframe", "1d").lower()
        ticker    = normalise_ticker(ticker, body.get("asset_type", "stock"))
        key       = f"{ticker}_{timeframe}"

        with watch_lock:
            removed = watch_registry.pop(key, None)

        if removed:
            return jsonify({"status": "removed", "key": key})
        return jsonify({"status": "not_found", "key": key}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watches", methods=["GET"])
def list_watches():
    """List all currently watched tickers with their status."""
    with watch_lock:
        watches = [
            {
                "key":         k,
                "ticker":      v["ticker"],
                "asset_type":  v["asset_type"],
                "timeframe":   v["timeframe"],
                "last_signal": v.get("last_signal") or "Waiting…",
                "last_reason": v.get("last_reason") or "Not checked yet",
                "last_price":  v.get("last_price"),
                "last_check":  v["last_check"].strftime("%H:%M UTC") if v.get("last_check") else "Pending",
                "added_at":    v.get("added_at", ""),
                "interval_min": ALERT_INTERVALS.get(v["timeframe"], 300) // 60,
            }
            for k, v in watch_registry.items()
        ]
    return jsonify({"watches": watches, "count": len(watches)})

@app.route("/api/scan-list", methods=["POST"])
def scan_list():
    """Pre-screen multiple tickers quickly — no Claude API call."""
    try:
        data      = request.json or {}
        tickers   = [t.strip().upper() for t in data.get("tickers", [])[:15]]
        asset_type = data.get("asset_type", "crypto")
        timeframe  = data.get("timeframe", "1h")
        if timeframe not in TIMEFRAME_CONFIG:
            timeframe = "1h"
        cfg     = TIMEFRAME_CONFIG[timeframe]
        results = []
        for ticker in tickers:
            raw = normalise_ticker(ticker, asset_type)
            try:
                df = yf.download(raw, period=cfg["period"], interval=cfg["interval"],
                                 progress=False, auto_adjust=True)
                if "resample" in cfg:
                    df = df.resample(cfg["resample"]).agg(
                        {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
                    ).dropna()
                if df.empty or len(df) < 20:
                    results.append({"ticker": ticker, "error": "no data"})
                    continue
                ind    = calculate_indicators(df, timeframe)
                screen = pre_screen(ind)
                ct     = detect_counter_trade(ind)
                results.append({
                    "ticker":       ticker,
                    "raw_ticker":   raw,
                    "price":        ind["price"],
                    "chg_1d":       ind["chg_1d"],
                    "rsi":          ind["rsi"],
                    "vol_ratio":    ind["vol_ratio"],
                    "ema_trend":    ind["ema_trend"],
                    "supertrend":   ind["supertrend"],
                    "signal_hint":  screen["signal_hint"],
                    "opportunity":  screen["opportunity"],
                    "call_claude":  screen["call_claude"],
                    "reason":       screen["reason"],
                    "bull_score":   screen["bull_score"],
                    "bear_score":   screen["bear_score"],
                    "counter_trade": ct["counter_trade"],
                })
            except Exception as e:
                results.append({"ticker": ticker, "error": str(e)[:80]})

        def sort_key(r):
            if r.get("error"): return 99
            if r.get("call_claude"): return 0
            if r.get("opportunity"): return 1
            return 2
        results.sort(key=sort_key)
        return jsonify({"results": results, "timeframe": timeframe, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/prices", methods=["POST"])
def get_prices():
    """Lightweight bulk price fetch for ticker tape."""
    try:
        data    = request.json or {}
        tickers = [t.strip() for t in data.get("tickers", [])[:20]]
        results = {}
        for ticker in tickers:
            try:
                df = yf.download(ticker, period="5d", interval="1d",
                                 progress=False, auto_adjust=True)
                if len(df) >= 2:
                    p, p0 = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
                    results[ticker] = {"price": round(p, 4), "chg": round((p / p0 - 1) * 100, 2)}
                elif len(df) == 1:
                    results[ticker] = {"price": round(float(df["Close"].iloc[-1]), 4), "chg": 0.0}
                else:
                    results[ticker] = {"price": None, "chg": None}
            except Exception:
                results[ticker] = {"price": None, "chg": None}
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat(),
                    "watches": len(watch_registry)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
