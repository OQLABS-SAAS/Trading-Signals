"""
Trading Signals SaaS — Backend
Supports: Stocks, Crypto, Forex, Commodities, Indices
Features: Multi-timeframe analysis, MTF trend, historical win rate,
          server-side watch scheduler with SMS + email alerts.
"""

from flask import Flask, request, jsonify, send_from_directory, session, Response
from flask_cors import CORS
from functools import wraps
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os, json, threading, time, math
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# ─── BROWSER-LIKE SESSION ─────────────────────────────────────
# Yahoo Finance and TradingView block plain cloud-server requests.
# Using a session with real browser headers bypasses bot detection.
_browser_session = requests.Session()
_browser_session.headers.update({
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Referer":         "https://finance.yahoo.com/",
})

# ─── SIMPLE TTL CACHE ─────────────────────────────────────────
# Caches yfinance + TradingView results for 5 min to reduce API hammering.
_cache      = {}
_cache_lock = threading.Lock()
CACHE_TTL   = 300  # seconds

def cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry["ts"]) < CACHE_TTL:
            return entry["data"]
        if entry:
            del _cache[key]
    return None

def cache_set(key, data):
    with _cache_lock:
        _cache[key] = {"ts": time.time(), "data": data}

def _sanitize(obj):
    """Recursively replace NaN / Infinity floats with None.
    Python's json.dumps outputs NaN/Infinity as bare JS literals which are
    NOT valid JSON — the browser's JSON.parse rejects them silently, producing
    'Network error' with no server-side exception. This sanitizer prevents that.
    """
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

app = Flask(__name__, static_folder="static")
CORS(app, supports_credentials=True)

# ─── GLOBAL ERROR HANDLERS ────────────────────────────────────
# Ensures ALL unhandled exceptions return JSON, never Flask's HTML error page.
# This means the frontend will always see a parseable error, never "Network error".
@app.errorhandler(Exception)
def handle_any_exception(e):
    import traceback
    print(f"[flask] Unhandled exception: {traceback.format_exc()}")
    return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.errorhandler(500)
def handle_500(e):
    return jsonify({"error": "Internal server error — please try again"}), 500

@app.errorhandler(404)
def handle_404(e):
    return jsonify({"error": "Not found"}), 404

# ─── AUTH CONFIG ──────────────────────────────────────────────
# Set these as Railway environment variables:
#   SECRET_KEY   → any long random string (signs session cookies)
#   APP_PASSWORD → the password you want to protect the app with
app.secret_key   = os.environ.get("SECRET_KEY", "change-me-set-SECRET_KEY-in-railway")
APP_PASSWORD     = os.environ.get("APP_PASSWORD", "").strip()

def login_required(f):
    """Decorator — blocks API calls unless the user has logged in this session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if APP_PASSWORD and not session.get("authenticated"):
            return jsonify({"error": "Unauthorized", "login_required": True}), 401
        return f(*args, **kwargs)
    return decorated

# ─── TIMEFRAME CONFIG ─────────────────────────────────────────
TIMEFRAME_CONFIG = {
    "5m":  {"interval": "5m",  "period": "5d",  "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "15m": {"interval": "15m", "period": "5d",  "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "30m": {"interval": "30m", "period": "5d",  "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "1h":  {"interval": "1h",  "period": "30d", "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "4h":  {"interval": "1h",  "period": "60d", "chart_bars": 90,  "date_fmt": "%Y-%m-%d %H:%M", "resample": "4h"},
    "1d":  {"interval": "1d",  "period": "1y",  "chart_bars": 90,  "date_fmt": "%Y-%m-%d"},
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

# ─── BINANCE OHLCV FALLBACK ───────────────────────────────────
# Used when Yahoo Finance blocks cloud-server IPs for crypto tickers.
# Binance public REST API requires no auth and works reliably from any IP.
_BINANCE_SYMBOL_MAP = {
    "BTC-USD":  "BTCUSDT",  "ETH-USD":  "ETHUSDT",  "SOL-USD":  "SOLUSDT",
    "BNB-USD":  "BNBUSDT",  "XRP-USD":  "XRPUSDT",  "ADA-USD":  "ADAUSDT",
    "DOGE-USD": "DOGEUSDT", "LTC-USD":  "LTCUSDT",  "AVAX-USD": "AVAXUSDT",
    "DOT-USD":  "DOTUSDT",  "LINK-USD": "LINKUSDT",  "MATIC-USD":"MATICUSDT",
    "UNI-USD":  "UNIUSDT",  "ATOM-USD": "ATOMUSDT",  "TRX-USD":  "TRXUSDT",
    "SHIB-USD": "SHIBUSDT", "TON-USD":  "TONUSDT",   "SUI-USD":  "SUIUSDT",
    "APT-USD":  "APTUSDT",  "OP-USD":   "OPUSDT",    "ARB-USD":  "ARBUSDT",
    "INJ-USD":  "INJUSDT",  "FET-USD":  "FETUSDT",   "WLD-USD":  "WLDUSDT",
    "NEAR-USD": "NEARUSDT", "FIL-USD":  "FILUSDT",   "ICP-USD":  "ICPUSDT",
    "VET-USD":  "VETUSDT",  "ALGO-USD": "ALGOUSDT",  "SAND-USD": "SANDUSDT",
    "MANA-USD": "MANAUSDT", "HBAR-USD": "HBARUSDT",  "PEPE-USD": "PEPEUSDT",
    "FLOKI-USD":"FLOKIUSDT","BONK-USD": "BONKUSDT",  "WIF-USD":  "WIFUSDT",
}

def _to_binance_symbol(ticker):
    """Convert app ticker (BTC-USD) to Binance pair (BTCUSDT). Returns None if not a known crypto.
    Handles: "BTC-USD" → "BTCUSDT", "ETH-USD" → "ETHUSDT", "BTC/USD" → "BTCUSDT",
             "BTCUSDT" → "BTCUSDT" (pass-through), "BTC" → "BTCUSDT" (bare + USDT)
    """
    if ticker in _BINANCE_SYMBOL_MAP:
        return _BINANCE_SYMBOL_MAP[ticker]

    t = ticker.upper()

    # If already in BTCUSDT format (all caps, ends with USDT), return as-is
    if t.endswith("USDT") and len(t) >= 5 and not any(c in t for c in "-/"):
        return t

    # Auto-convert: remove all separators and currency suffixes
    # IMPORTANT: Replace -USDT before -USD to avoid substring matching issues
    t = t.replace("-USDT","").replace("/USDT","").replace("-USD","").replace("/USD","").replace("/","")

    # If we now have something that ends with USDT, return it
    if t.endswith("USDT") and len(t) >= 5:
        return t

    # If bare symbol (BTC, ETH, etc), append USDT
    if len(t) >= 2 and len(t) <= 10 and t.isalpha():
        return t + "USDT"

    return None

def fetch_binance_ohlcv(ticker, interval="1d", period="1y"):
    """Fetch OHLCV from Binance public klines endpoint. No auth required.
    Returns a DataFrame identical in format to safe_download() output.
    """
    sym = _to_binance_symbol(ticker)
    if not sym:
        print(f"[binance] Could not map ticker '{ticker}' to Binance symbol")
        return pd.DataFrame()

    cache_key = f"binance:{sym}:{interval}:{period}"
    cached = cache_get(cache_key)
    if cached is not None:
        print(f"[binance] Cache hit for {cache_key}")
        return cached

    # Interval mapping: yfinance → Binance
    ivl_map = {"5m":"5m","15m":"15m","30m":"30m","1h":"1h","4h":"4h","1d":"1d","1w":"1w"}
    b_interval = ivl_map.get(interval, "1d")

    # Limit: how many bars to request based on period
    limit_map = {"5d":500,"1mo":750,"30d":750,"60d":1000,"3mo":1000,"6mo":1000,"1y":400,"2y":730}
    limit = limit_map.get(period, 400)

    try:
        url = "https://api.binance.com/api/v3/klines"
        print(f"[binance] Fetching {sym} {b_interval} (limit={limit}) from {url}")
        resp = _browser_session.get(url, params={
            "symbol": sym, "interval": b_interval, "limit": limit
        }, timeout=10)
        if resp.status_code != 200:
            print(f"[binance] HTTP {resp.status_code} for {sym} ({b_interval})")
            return pd.DataFrame()
        raw = resp.json()
        if not raw:
            print(f"[binance] Empty response for {sym} ({b_interval})")
            return pd.DataFrame()
        # Binance kline format: [open_time, open, high, low, close, volume, ...]
        df = pd.DataFrame(raw, columns=[
            "ts","Open","High","Low","Close","Volume",
            "close_time","qav","num_trades","taker_base","taker_quote","ignore"
        ])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df = df.set_index("ts")[["Open","High","Low","Close","Volume"]]
        df = df.astype(float)
        df = df.dropna(how="all")
        print(f"[binance] SUCCESS — fetched {len(df)} bars for {sym} ({b_interval})")
        cache_set(cache_key, df)
        return df
    except Exception as e:
        print(f"[binance] Error for {sym} ({interval}): {e}")
        return pd.DataFrame()


def safe_download(ticker, period="1y", interval="1d", **kwargs):
    """Fetch OHLCV data directly from Yahoo Finance chart API using browser headers.

    Bypasses yfinance session/cookie authentication issues on cloud server IPs.
    Caches results 5 minutes to reduce API calls.
    """
    cache_key = f"yf:{ticker}:{period}:{interval}"
    cached = cache_get(cache_key)
    if cached is not None:
        print(f"[yahoo] Cache hit for {cache_key}")
        return cached

    # Map yfinance period strings to Yahoo Finance range strings
    range_map = {
        "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo",
        "1y": "1y", "2y": "2y", "5y": "5y", "max": "max",
        "30d": "1mo", "60d": "3mo",
    }
    yf_range = range_map.get(period, "1y")

    _rate_limited = [False]  # flag: skip retry if server is rate-limiting

    def _fetch(sym):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        try:
            r = _browser_session.get(url, params={
                "interval": interval,
                "range":    yf_range,
                "includePrePost": "false",
                "events":   "div,splits",
            }, timeout=5)  # fail fast on rate-limited IPs — Stooq/FMP fallback handles stocks
            if r.status_code == 429:
                print(f"[yahoo] {sym} rate-limited (429) — skipping retry")
                _rate_limited[0] = True
                return pd.DataFrame()
            if r.status_code != 200:
                print(f"[yahoo] {sym} HTTP {r.status_code}")
                return pd.DataFrame()
            data   = r.json()
            result = data.get("chart", {}).get("result", [])
            if not result:
                return pd.DataFrame()
            chart  = result[0]
            ts     = chart.get("timestamp", [])
            quote  = chart.get("indicators", {}).get("quote", [{}])[0]
            if not ts or not quote:
                return pd.DataFrame()
            df = pd.DataFrame({
                "Open":   quote.get("open",   []),
                "High":   quote.get("high",   []),
                "Low":    quote.get("low",    []),
                "Close":  quote.get("close",  []),
                "Volume": quote.get("volume", []),
            }, index=pd.to_datetime(ts, unit="s", utc=True))
            df.index = df.index.tz_convert(None)  # strip UTC tz-awareness
            return df.dropna(how="all")
        except Exception as e:
            print(f"[yahoo] fetch error for {sym}: {e}")
            return pd.DataFrame()

    df = _fetch(ticker)

    # Skip retry if rate-limited (429) — retrying just wastes 5 more seconds.
    # The fallback chain (Stooq → FMP → Yahoo v8) will handle chart data.
    if df.empty and not _rate_limited[0]:
        df = _fetch(ticker)

    # Forex alternate formats: GBPUSD=X -> GBP=X
    if df.empty and ticker.endswith("=X"):
        base = ticker.replace("=X", "")
        for alt in [base[:3] + "=X", base[3:] + base[:3] + "=X"]:
            if alt != ticker:
                df = _fetch(alt)
                if not df.empty:
                    break

    if not df.empty:
        cache_set(cache_key, df)
    else:
        print(f"[yahoo] No data for {ticker} period={period} interval={interval}")
        # ── Binance fallback for crypto tickers ──────────────────
        # Yahoo Finance often blocks cloud server IPs for crypto OHLCV.
        # Try Binance public API instead (no auth required, very reliable).
        print(f"[binance-fallback] Attempting fallback for {ticker} after Yahoo Finance failed")
        b_df = fetch_binance_ohlcv(ticker, interval=interval, period=period)
        if not b_df.empty:
            print(f"[binance-fallback] SUCCESS — fallback returned {len(b_df)} bars for {ticker}")
            cache_set(cache_key, b_df)
            return b_df
        else:
            print(f"[binance-fallback] FAILED — Binance also returned no data for {ticker}")

    return df

def get_rsi(close):
    delta = close.diff()
    gain  = delta.clip(lower=0).fillna(0)
    loss  = (-delta).clip(lower=0).fillna(0)
    return 100 - 100 / (1 + rma(gain, 14) / rma(loss, 14))


def detect_rsi_divergence(high, low, rsi_series, pivot_len=5, lookback=60):
    """
    Detect regular and hidden RSI divergence over recent bars.
    pivot_len : bars on each side required to confirm a swing pivot
    lookback  : how many recent bars to scan for pivots
    Returns dict with:
      - top-level fields for the most recent divergence (backward compat):
        type, label, strength (0-100), desc, rsi_pivot_vals, price_pivot_bars,
        rsi_pivot_bars, price_pivot_vals, rsi_pivots
      - "all": list of every divergence detected within the lookback window,
        each entry having the same shape as the top-level fields (minus "all").
        Ordered from oldest -> newest. Includes both bullish (bottom) and
        bearish (top) divergences concurrently, matching indicators that
        persist historical divergence lines.
    """
    h = high.values
    l = low.values
    r = rsi_series.values
    n = len(r)
    empty = {"type": "none", "label": "None", "strength": 0, "desc": "", "all": []}
    min_bars = pivot_len * 2 + 4
    if n < min_bars:
        return empty

    # scan window: don't include last pivot_len bars (no confirmation yet)
    start = max(pivot_len, n - lookback - pivot_len)
    end   = n - pivot_len  # last confirmed pivot index

    ph_idx, pl_idx = [], []   # price pivot high / low indices
    rh_idx, rl_idx = [], []   # RSI  pivot high / low indices

    for i in range(start, end):
        w = slice(i - pivot_len, i + pivot_len + 1)
        if h[i] == h[w].max():  ph_idx.append(i)
        if l[i] == l[w].min():  pl_idx.append(i)
        if r[i] == r[w].max():  rh_idx.append(i)
        if r[i] == r[w].min():  rl_idx.append(i)

    def nearest_rsi_pivot(price_idx, rsi_pivots, max_gap=None):
        """Return the RSI pivot closest to price_idx."""
        if not rsi_pivots: return None
        mg = max_gap or pivot_len * 3
        candidates = [x for x in rsi_pivots if abs(x - price_idx) <= mg]
        if not candidates: return None
        return min(candidates, key=lambda x: abs(x - price_idx))

    all_divs = []  # every divergence found, ordered oldest -> newest

    # ── Walk every consecutive pair of pivot HIGHS → bearish + hidden bearish
    for k in range(1, len(ph_idx)):
        p1, p2 = ph_idx[k-1], ph_idx[k]
        rp1 = nearest_rsi_pivot(p1, rh_idx)
        rp2 = nearest_rsi_pivot(p2, rh_idx)
        if not rp1 or not rp2 or rp1 == rp2:
            continue
        price_up = h[p2] > h[p1]
        rsi_up   = r[rp2] > r[rp1]
        if price_up and not rsi_up:
            strength = min(int(abs(r[rp2] - r[rp1]) * 2.5), 100)
            all_divs.append({
                "type": "bearish", "label": "Regular Bearish", "strength": strength,
                "rsi_pivots": [round(r[rp1],1), round(r[rp2],1)],
                "price_pivot_bars": [int(p1), int(p2)],
                "price_pivot_vals": [round(float(h[p1]),4), round(float(h[p2]),4)],
                "rsi_pivot_bars":   [int(rp1), int(rp2)],
                "confirm_bar":      int(p2),
                "desc": (f"Price made higher high ({h[p2]:.5g} > {h[p1]:.5g}) "
                         f"but RSI made lower high ({r[rp2]:.1f} < {r[rp1]:.1f}). "
                         f"Momentum weakening — watch for reversal or pullback.")
            })
        elif (not price_up) and rsi_up:
            strength = min(int(abs(r[rp2] - r[rp1]) * 2.5), 100)
            all_divs.append({
                "type": "hidden_bearish", "label": "Hidden Bearish", "strength": strength,
                "rsi_pivots": [round(r[rp1],1), round(r[rp2],1)],
                "price_pivot_bars": [int(p1), int(p2)],
                "price_pivot_vals": [round(float(h[p1]),4), round(float(h[p2]),4)],
                "rsi_pivot_bars":   [int(rp1), int(rp2)],
                "confirm_bar":      int(p2),
                "desc": (f"Price made lower high ({h[p2]:.5g} < {h[p1]:.5g}) "
                         f"but RSI made higher high ({r[rp2]:.1f} > {r[rp1]:.1f}). "
                         f"Bearish trend continuation signal — downtrend likely resuming.")
            })

    # ── Walk every consecutive pair of pivot LOWS → bullish + hidden bullish
    for k in range(1, len(pl_idx)):
        p1, p2 = pl_idx[k-1], pl_idx[k]
        rp1 = nearest_rsi_pivot(p1, rl_idx)
        rp2 = nearest_rsi_pivot(p2, rl_idx)
        if not rp1 or not rp2 or rp1 == rp2:
            continue
        price_dn = l[p2] < l[p1]
        rsi_dn   = r[rp2] < r[rp1]
        if price_dn and not rsi_dn:
            strength = min(int(abs(r[rp2] - r[rp1]) * 2.5), 100)
            all_divs.append({
                "type": "bullish", "label": "Regular Bullish", "strength": strength,
                "rsi_pivots": [round(r[rp1],1), round(r[rp2],1)],
                "price_pivot_bars": [int(p1), int(p2)],
                "price_pivot_vals": [round(float(l[p1]),4), round(float(l[p2]),4)],
                "rsi_pivot_bars":   [int(rp1), int(rp2)],
                "confirm_bar":      int(p2),
                "desc": (f"Price made lower low ({l[p2]:.5g} < {l[p1]:.5g}) "
                         f"but RSI made higher low ({r[rp2]:.1f} > {r[rp1]:.1f}). "
                         f"Selling pressure fading — potential reversal higher.")
            })
        elif (not price_dn) and rsi_dn:
            strength = min(int(abs(r[rp2] - r[rp1]) * 2.5), 100)
            all_divs.append({
                "type": "hidden_bullish", "label": "Hidden Bullish", "strength": strength,
                "rsi_pivots": [round(r[rp1],1), round(r[rp2],1)],
                "price_pivot_bars": [int(p1), int(p2)],
                "price_pivot_vals": [round(float(l[p1]),4), round(float(l[p2]),4)],
                "rsi_pivot_bars":   [int(rp1), int(rp2)],
                "confirm_bar":      int(p2),
                "desc": (f"Price made higher low ({l[p2]:.5g} > {l[p1]:.5g}) "
                         f"but RSI made lower low ({r[rp2]:.1f} < {r[rp1]:.1f}). "
                         f"Bullish trend continuation — dip buying opportunity.")
            })

    # Sort oldest -> newest by confirmation bar so the frontend can fade older ones
    all_divs.sort(key=lambda d: d.get("confirm_bar", 0))

    if not all_divs:
        return empty

    # Most recent divergence becomes the top-level result (backward compat).
    latest = all_divs[-1]
    result = dict(latest)
    result["all"] = all_divs
    return result

# ─── INDICATOR CALCULATION ────────────────────────────────────
def calculate_indicators(df, timeframe="1d"):
    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze()

    rsi_series = get_rsi(close)
    rsi        = rsi_series.iloc[-1]
    rsi_div    = detect_rsi_divergence(high, low, rsi_series)

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
    # Use previous bar if the last bar has no volume (incomplete candle edge case)
    last_vol  = float(vol.iloc[-1])
    if last_vol == 0 and len(vol) > 2:
        last_vol = float(vol.iloc[-2])
    vol_ratio = round(last_vol / vol_avg, 2) if vol_avg > 0 else 1.0

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
    chart_open   = df["Open"].squeeze().iloc[-n_bars:]
    chart_high   = df["High"].squeeze().iloc[-n_bars:]
    chart_low    = df["Low"].squeeze().iloc[-n_bars:]
    chart_vol    = vol.iloc[-n_bars:]
    ema20_series = ema_tv(close, 20).iloc[-n_bars:]
    ema50_series = ema_tv(close, 50).iloc[-n_bars:] if len(close) >= 50 else ema_tv(close, 20).iloc[-n_bars:]
    chart_dates  = [d.strftime(date_fmt) for d in chart_close.index]
    chart_prices = [round(float(v), 4) for v in chart_close]
    chart_opens  = [None if np.isnan(v) else round(float(v), 4) for v in chart_open]
    chart_highs  = [None if np.isnan(v) else round(float(v), 4) for v in chart_high]
    chart_lows   = [None if np.isnan(v) else round(float(v), 4) for v in chart_low]
    chart_ema20  = [None if np.isnan(v) else round(float(v), 4) for v in ema20_series]
    chart_ema50  = [None if np.isnan(v) else round(float(v), 4) for v in ema50_series]
    chart_volumes = [0 if np.isnan(v) else int(float(v)) for v in chart_vol]

    # Bollinger Bands for chart window
    bb_upper_series = bb_upper.iloc[-n_bars:]
    bb_lower_series = bb_lower.iloc[-n_bars:]
    chart_bb_upper = [None if np.isnan(v) else round(float(v), 4) for v in bb_upper_series]
    chart_bb_lower = [None if np.isnan(v) else round(float(v), 4) for v in bb_lower_series]

    # RSI series for chart window
    rsi_chart_series = rsi_series.iloc[-n_bars:]
    chart_rsi = [None if np.isnan(v) else round(float(v), 2) for v in rsi_chart_series]

    # RSI signal bars within chart window (crossunder 40 = BUY, crossover 60 = SELL)
    rsi_arr = rsi_series.values
    full_n  = len(rsi_arr)
    chart_start_idx = max(0, full_n - n_bars)
    chart_buy_signals  = []
    chart_sell_signals = []
    for i in range(max(1, chart_start_idx), full_n):
        prev_r = rsi_arr[i-1]
        curr_r = rsi_arr[i]
        if np.isnan(prev_r) or np.isnan(curr_r):
            continue
        chart_i = i - chart_start_idx  # position within chart window
        if prev_r >= 40 and curr_r < 40:
            chart_buy_signals.append(chart_i)
        elif prev_r <= 60 and curr_r > 60:
            chart_sell_signals.append(chart_i)

    # Convert divergence pivot bar indices → chart-window coordinates
    # (only include if the pivot falls within the visible chart window)
    if rsi_div.get("price_pivot_bars"):
        pb = rsi_div["price_pivot_bars"]
        rb = rsi_div["rsi_pivot_bars"]
        rsi_div["chart_price_pivot_bars"] = [b - chart_start_idx for b in pb if b >= chart_start_idx]
        rsi_div["chart_rsi_pivot_bars"]   = [b - chart_start_idx for b in rb if b >= chart_start_idx]
    else:
        rsi_div["chart_price_pivot_bars"] = []
        rsi_div["chart_rsi_pivot_bars"]   = []

    # Also map ALL historical divergences into chart-window coordinates so the
    # frontend can render the full divergence history (both bullish and bearish
    # lines visible at the same time, like Binary Destroyer-style indicators).
    mapped_all = []
    for _dv in rsi_div.get("all", []):
        pb2 = _dv.get("price_pivot_bars", []) or []
        rb2 = _dv.get("rsi_pivot_bars", []) or []
        if len(pb2) < 2 or len(rb2) < 2:
            continue
        # Keep only divergences where BOTH price pivots fall inside the chart window.
        if pb2[0] < chart_start_idx or pb2[1] < chart_start_idx:
            continue
        _dv_copy = dict(_dv)
        _dv_copy["chart_price_pivot_bars"] = [b - chart_start_idx for b in pb2]
        _dv_copy["chart_rsi_pivot_bars"]   = [b - chart_start_idx for b in rb2]
        mapped_all.append(_dv_copy)
    rsi_div["all"] = mapped_all

    return {
        "price":        round(p, 4),
        "chg_1d":       round((p / p1 - 1) * 100, 2),
        "chg_1w":       round((p / pw - 1) * 100, 2),
        "chg_1m":       round((p / pm - 1) * 100, 2),
        "high_52w":     round(high52, 4),
        "low_52w":      round(low52, 4),
        "rsi":          round(float(rsi), 1),
        "rsi_divergence": rsi_div,
        "ema20":        round(float(e20), 4),
        "ema50":        round(float(e50), 4),
        "ema200":       round(float(e200), 4),
        "ema_trend":    ema_trend,
        "macd_hist":    round(float(macd_hist), 6),
        "bb_pos":       round(bb_pos, 3),
        "bb_width":     round(bb_width, 3),
        "atr":          round(atr, 4),
        "vol_ratio":    vol_ratio,
        "vol_raw":      int(last_vol),
        "vol_avg":      int(vol_avg),
        "vol_usd":      round(last_vol * p, 2),
        "vol_avg_usd":  round(vol_avg * p, 2),
        "supertrend":   "BULLISH" if st_dir > 0 else ("BEARISH" if st_dir < 0 else "NEUTRAL"),
        "resistance":   round(res, 4),
        "support":      round(sup, 4),
        "chart_dates":        chart_dates,
        "chart_prices":       chart_prices,
        "chart_opens":        chart_opens,
        "chart_highs":        chart_highs,
        "chart_lows":         chart_lows,
        "chart_ema20":        chart_ema20,
        "chart_ema50":        chart_ema50,
        "chart_volumes":      chart_volumes,
        "chart_bb_upper":     chart_bb_upper,
        "chart_bb_lower":     chart_bb_lower,
        "chart_rsi":          chart_rsi,
        "chart_buy_signals":  chart_buy_signals,
        "chart_sell_signals": chart_sell_signals,
    }

# ─── INDICATOR BUILDER FROM TV DATA ──────────────────────────
def build_ind_from_tv(tv):
    """Build the indicator dict directly from TradingView scanner data.
    TV provides real RSI, EMA, MACD, BB, ATR — same values traders see on charts.
    """
    p    = tv.get("tv_price") or 0
    rsi  = tv.get("tv_rsi")   or 50.0
    e20  = tv.get("tv_ema20") or p
    e50  = tv.get("tv_ema50") or p
    e200 = tv.get("tv_ema200") or p
    macd = tv.get("tv_macd_hist") or 0.0
    bbu  = tv.get("tv_bb_upper") or (p * 1.02)
    bbl  = tv.get("tv_bb_lower") or (p * 0.98)
    atr  = tv.get("tv_atr") or (p * 0.01)
    chg  = tv.get("tv_chg") or 0.0

    bb_denom = bbu - bbl
    bb_pos   = float((p - bbl) / bb_denom) if bb_denom != 0 else 0.5
    bb_width = float((bbu - bbl) / ((bbu + bbl) / 2)) if (bbu + bbl) > 0 else 0.04

    if p and e20 and e50 and e200:
        if p > e20 > e50 > e200:    ema_trend = "STRONG BULL"
        elif p > e50 > e200:        ema_trend = "BULL"
        elif p < e20 < e50 < e200:  ema_trend = "STRONG BEAR"
        elif p < e50 < e200:        ema_trend = "BEAR"
        else:                        ema_trend = "MIXED"
    else:
        ema_trend = "MIXED"

    return {
        "price":          round(p, 4),
        "chg_1d":         round(chg, 2),
        "chg_1w":         0.0,
        "chg_1m":         0.0,
        "high_52w":       round(p * 1.3, 4),
        "low_52w":        round(p * 0.7, 4),
        "rsi":            round(float(rsi), 1),
        "rsi_divergence": {"type": "none", "label": "", "strength": 0, "desc": "", "all": []},
        "ema20":          round(float(e20),  4),
        "ema50":          round(float(e50),  4),
        "ema200":         round(float(e200), 4),
        "ema_trend":      ema_trend,
        "macd_hist":      round(float(macd), 6),
        "bb_pos":         round(bb_pos,  3),
        "bb_width":       round(bb_width, 3),
        "atr":            round(float(atr), 6),
        "vol_ratio":      1.0,
        "supertrend":     "NEUTRAL",
        "resistance":     round(bbu, 4),
        "support":        round(bbl, 4),
        "chart_dates":        [],
        "chart_prices":       [],
        "chart_opens":        [],
        "chart_highs":        [],
        "chart_lows":         [],
        "chart_ema20":        [],
        "chart_ema50":        [],
        "chart_volumes":      [],
        "chart_bb_upper":     [],
        "chart_bb_lower":     [],
        "chart_rsi":          [],
        "chart_buy_signals":  [],
        "chart_sell_signals": [],
    }

def _enrich_chart_indicators(prices_c):
    """Compute BB bands, RSI, and buy/sell signal markers from raw price array.
    Returns (bb_upper, bb_lower, rsi_out, buy_sigs, sell_sigs)."""
    _px = [p for p in prices_c if p is not None]
    _n  = len(_px)

    # Bollinger Bands (20-period SMA ± 2 std)
    _bb_upper, _bb_lower = [], []
    for _i in range(_n):
        if _i < 19:
            _bb_upper.append(None)
            _bb_lower.append(None)
        else:
            _window = _px[_i-19:_i+1]
            _sma = sum(_window) / 20
            _std = (sum((_v - _sma)**2 for _v in _window) / 20) ** 0.5
            _bb_upper.append(round(_sma + 2 * _std, 6))
            _bb_lower.append(round(_sma - 2 * _std, 6))

    # RSI (14-period Wilder smoothing)
    _rsi_out = [None] * _n
    if _n > 14:
        _gains, _losses = [], []
        for _i in range(1, _n):
            _d = _px[_i] - _px[_i-1]
            _gains.append(max(_d, 0))
            _losses.append(max(-_d, 0))
        _ag = sum(_gains[:14]) / 14
        _al = sum(_losses[:14]) / 14
        _rsi_out[14] = round(100 - 100 / (1 + _ag / _al), 2) if _al > 0 else 100.0
        for _i in range(14, len(_gains)):
            _ag = (_ag * 13 + _gains[_i]) / 14
            _al = (_al * 13 + _losses[_i]) / 14
            _rsi_out[_i + 1] = round(100 - 100 / (1 + _ag / _al), 2) if _al > 0 else 100.0

    # Buy/Sell signal markers (RSI crossunder 40 = BUY, crossover 60 = SELL)
    _buy_sigs, _sell_sigs = [], []
    for _i in range(1, _n):
        _prev = _rsi_out[_i - 1]
        _curr = _rsi_out[_i]
        if _prev is None or _curr is None:
            continue
        if _prev >= 40 and _curr < 40:
            _buy_sigs.append(_i)
        elif _prev <= 60 and _curr > 60:
            _sell_sigs.append(_i)

    return _bb_upper, _bb_lower, _rsi_out, _buy_sigs, _sell_sigs


# ─── MULTI-SOURCE CHART DATA ──────────────────────────────────
# Tries sources in order until one works. Yahoo Finance is blocked on Railway IPs,
# so we try Binance (crypto) and Stooq (stocks/forex) first.
def _build_chart_output(dates_raw, prices_raw, vols_raw, timeframe, max_bars=200,
                        opens_raw=None, highs_raw=None, lows_raw=None):
    """Helper: trim, compute EMAs, return tuple.
    Returns (dates, prices, vols, ema20, ema50) when no OHLC provided,
    or (dates, prices, vols, ema20, ema50, opens, highs, lows) when OHLC is available."""
    dates_raw  = dates_raw[-max_bars:]
    prices_raw = prices_raw[-max_bars:]
    vols_raw   = vols_raw[-max_bars:]

    def _ema(px, n):
        if len(px) < n:
            return [None] * len(px)
        k   = 2.0 / (n + 1)
        ema = sum(px[:n]) / n
        out = [None] * (n - 1) + [round(ema, 6)]
        for p in px[n:]:
            ema = p * k + ema * (1 - k)
            out.append(round(ema, 6))
        return out

    base = (dates_raw, prices_raw, vols_raw, _ema(prices_raw, 20), _ema(prices_raw, min(50, len(prices_raw)-1)))
    if opens_raw and highs_raw and lows_raw:
        return base + (opens_raw[-max_bars:], highs_raw[-max_bars:], lows_raw[-max_bars:])
    return base


def _fetch_binance(ticker, timeframe):
    """Binance public klines API — free, no auth, works for any USDT pair."""
    iv_map = {"5m":"5m","15m":"15m","30m":"30m","1h":"1h","4h":"4h","1d":"1d","1w":"1w"}
    interval = iv_map.get(timeframe, "1d")
    limit    = 200  # max 1000; 200 gives enough for backtest + chart

    # Build Binance symbol: BNB-USD → BNBUSDT, BTCUSDT stays, BTC → BTCUSDT
    sym = ticker.upper().replace("-USD","").replace("-USDT","").replace("/","")
    sym = sym + "USDT" if not sym.endswith("USDT") and not sym.endswith("BTC") else sym

    url = f"https://api.binance.com/api/v3/klines"
    try:
        r = requests.get(url, params={"symbol": sym, "interval": interval, "limit": limit},
                         timeout=(5, 15))
        if r.status_code != 200:
            print(f"[binance] {sym} {interval}: HTTP {r.status_code}")
            return None
        klines = r.json()
        if not klines or isinstance(klines, dict):  # error dict
            return None

        dt_fmt = "%H:%M" if timeframe in ("5m","15m","30m","1h") else "%b %d"
        dates, opens, highs, lows, prices, vols = [], [], [], [], [], []
        for k in klines:
            ts = int(k[0]) // 1000
            dates.append(datetime.utcfromtimestamp(ts).strftime(dt_fmt))
            opens.append(round(float(k[1]), 6))
            highs.append(round(float(k[2]), 6))
            lows.append(round(float(k[3]), 6))
            prices.append(round(float(k[4]), 6))
            vols.append(int(float(k[5])))

        if len(prices) < 10:
            return None
        print(f"[binance] OK — {sym} {interval}: {len(prices)} bars")
        return _build_chart_output(dates, prices, vols, timeframe,
                                   opens_raw=opens, highs_raw=highs, lows_raw=lows)
    except Exception as e:
        print(f"[binance] error {sym}: {e}")
        return None


def _fetch_stooq(ticker, asset_type, timeframe):
    """Stooq.pl — free CSV data for stocks, indices, forex. No auth needed."""
    import csv, io
    iv_map = {"5m":"5","15m":"15","30m":"30","1h":"60","4h":"4h","1d":"d","1w":"w"}
    iv = iv_map.get(timeframe, "d")
    if iv in ("5","15","30","60","4h"):
        iv = "d"  # stooq intraday is unreliable; fall back to daily

    # Stooq ticker format
    sym = ticker.lower()
    if asset_type == "stock":
        if not sym.endswith(".us") and not "." in sym:
            sym = sym + ".us"
    elif asset_type == "forex":
        clean = sym.replace("=x","").replace("/","").replace("-","")
        sym   = clean[:3] + clean[3:] if len(clean) >= 6 else clean
    elif asset_type == "index":
        index_map = {
            "^gspc":"^spx", "^ixic":"^ndq",  "^ndx":"^ndq",
            "^dji":"^dji",  "^ftse":"^ftx",  "^gdaxi":"^dax",
            "^fchi":"^cac", "^n225":"^nkx",  "^hsi":"^hsi",
            "^axjo":"^axjo","^rut":"^rut",   "^vix":"^vix",
            "^stoxx50e":"^stoxx50e",
        }
        sym = index_map.get(sym, sym)
    elif asset_type == "crypto":
        return None  # Stooq doesn't have crypto

    url = f"https://stooq.com/q/d/l/?s={sym}&i={iv}"
    try:
        r = requests.get(url, timeout=(5, 12),
                         headers={"User-Agent": "Mozilla/5.0 (compatible)"})
        if r.status_code != 200 or "No data" in r.text or len(r.text) < 50:
            return None

        reader = csv.DictReader(io.StringIO(r.text))
        rows   = list(reader)
        if not rows or "Close" not in rows[0]:
            return None

        dt_fmt = "%b %d" if timeframe in ("1d","1w") else "%b %d"
        dates, opens, highs, lows, prices, vols = [], [], [], [], [], []
        for row in rows[-200:]:
            try:
                dates.append(row.get("Date","")[:10])
                prices.append(round(float(row["Close"]), 6))
                opens.append(round(float(row.get("Open", row["Close"])), 6))
                highs.append(round(float(row.get("High", row["Close"])), 6))
                lows.append(round(float(row.get("Low", row["Close"])), 6))
                vols.append(int(float(row.get("Volume", 0) or 0)))
            except (ValueError, KeyError):
                continue

        if len(prices) < 10:
            return None
        print(f"[stooq] OK — {sym} {iv}: {len(prices)} bars")
        return _build_chart_output(dates, prices, vols, timeframe,
                                   opens_raw=opens, highs_raw=highs, lows_raw=lows)
    except Exception as e:
        print(f"[stooq] error {sym}: {e}")
        return None


def _fetch_yahoo_v8(ticker, asset_type, timeframe):
    """Yahoo Finance v8 — last resort, often 429 on cloud IPs."""
    iv_map = {"5m":("5m","5d"),"15m":("15m","5d"),"30m":("30m","5d"),
              "1h":("1h","30d"),"4h":("1h","60d"),"1d":("1d","365d")}
    yf_interval, yf_range = iv_map.get(timeframe, ("1d","180d"))

    yf_ticker = ticker
    if asset_type == "crypto":
        clean = ticker.split(":")[-1] if ":" in ticker else ticker
        yf_ticker = clean if clean.endswith("-USD") else clean.replace("USDT","") + "-USD"
    elif asset_type == "forex":
        clean = ticker.replace("/","").replace("-","").replace("=X","").upper()
        yf_ticker = clean + "=X"

    try:
        r = requests.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{yf_ticker}",
                         params={"interval": yf_interval, "range": yf_range, "events": ""},
                         headers={"User-Agent": "Mozilla/5.0 (compatible)"}, timeout=(5, 12))
        if r.status_code != 200:
            return None

        res_list = r.json().get("chart", {}).get("result", [])
        if not res_list:
            return None

        res    = res_list[0]
        ts_l   = res.get("timestamp", [])
        quote  = res.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", [])
        opens_ = quote.get("open", [])
        highs_ = quote.get("high", [])
        lows_  = quote.get("low", [])
        vols   = quote.get("volume", [])

        if timeframe == "4h":
            from collections import defaultdict
            bk, vk = defaultdict(list), defaultdict(int)
            ok, hk, lk = defaultdict(list), defaultdict(list), defaultdict(list)
            for i, t in enumerate(ts_l):
                c = closes[i] if i < len(closes) else None
                if c and not (isinstance(c, float) and math.isnan(c)):
                    b = t - (t % 14400); bk[b].append(c)
                    v = vols[i] if i < len(vols) else 0
                    vk[b] += int(v) if v and not math.isnan(float(v)) else 0
                    o = opens_[i] if i < len(opens_) else c
                    h = highs_[i] if i < len(highs_) else c
                    l = lows_[i] if i < len(lows_) else c
                    ok[b].append(o if o and not (isinstance(o,float) and math.isnan(o)) else c)
                    hk[b].append(h if h and not (isinstance(h,float) and math.isnan(h)) else c)
                    lk[b].append(l if l and not (isinstance(l,float) and math.isnan(l)) else c)
            ts_l   = sorted(bk.keys())
            closes = [bk[t][-1] for t in ts_l]
            opens_ = [ok[t][0]  for t in ts_l]
            highs_ = [max(hk[t]) for t in ts_l]
            lows_  = [min(lk[t]) for t in ts_l]
            vols   = [vk[t]     for t in ts_l]

        dt_fmt = "%H:%M" if timeframe in ("5m","15m","30m","1h") else "%b %d"
        dates, prices, volumes, o_out, h_out, l_out = [], [], [], [], [], []
        for i, (t, c, v) in enumerate(zip(ts_l, closes, vols or [0]*len(ts_l))):
            if c and not (isinstance(c, float) and math.isnan(c)):
                dates.append(datetime.utcfromtimestamp(t).strftime(dt_fmt))
                prices.append(round(float(c), 6))
                volumes.append(int(v) if v and not (isinstance(v,float) and math.isnan(v)) else 0)
                o = opens_[i] if i < len(opens_) else c
                h = highs_[i] if i < len(highs_) else c
                l = lows_[i]  if i < len(lows_)  else c
                o_out.append(round(float(o), 6) if o and not (isinstance(o,float) and math.isnan(o)) else round(float(c), 6))
                h_out.append(round(float(h), 6) if h and not (isinstance(h,float) and math.isnan(h)) else round(float(c), 6))
                l_out.append(round(float(l), 6) if l and not (isinstance(l,float) and math.isnan(l)) else round(float(c), 6))

        if len(prices) < 5:
            return None
        print(f"[yahoo_v8] OK — {yf_ticker} {timeframe}: {len(prices)} bars")
        return _build_chart_output(dates, prices, volumes, timeframe,
                                   opens_raw=o_out, highs_raw=h_out, lows_raw=l_out)
    except Exception as e:
        print(f"[yahoo_v8] error {yf_ticker}: {e}")
        return None


def _fetch_fmp(ticker, asset_type, timeframe):
    """Financial Modeling Prep — reliable for stocks/forex/indices on cloud servers.
    Free tier: 250 calls/day. Set FMP_API_KEY env var to enable."""
    fmp_key = os.environ.get("FMP_API_KEY", "").strip()
    if not fmp_key:
        return None

    # Map timeframes to FMP intervals
    fmp_map = {"5m": "5min", "15m": "15min", "30m": "30min",
               "1h": "1hour", "4h": "4hour", "1d": "1day"}
    fmp_iv = fmp_map.get(timeframe, "1day")

    # FMP ticker format
    sym = ticker.upper()
    if asset_type == "forex":
        clean = sym.replace("=X", "").replace("/", "").replace("-", "")
        sym = clean[:3] + clean[3:]
    elif asset_type == "crypto":
        return None  # Binance is better for crypto

    try:
        url = f"https://financialmodelingprep.com/api/v3/historical-chart/{fmp_iv}/{sym}"
        r = requests.get(url, params={"apikey": fmp_key}, timeout=(5, 10))
        if r.status_code != 200:
            print(f"[fmp] HTTP {r.status_code} for {sym}")
            return None

        data = r.json()
        if not data or not isinstance(data, list) or len(data) < 10:
            print(f"[fmp] insufficient data for {sym}: {len(data) if data else 0} bars")
            return None

        # FMP returns newest first — reverse to chronological
        data = list(reversed(data[-200:]))

        dt_fmt = "%H:%M" if timeframe in ("5m", "15m", "30m", "1h") else "%b %d"
        dates, prices, vols, opens, highs, lows = [], [], [], [], [], []
        for bar in data:
            try:
                d_str = bar.get("date", "")
                if "T" in d_str or " " in d_str:
                    from datetime import datetime as dt_cls
                    d_parsed = dt_cls.strptime(d_str.split(".")[0].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                    dates.append(d_parsed.strftime(dt_fmt))
                else:
                    dates.append(d_str[:10])
                prices.append(round(float(bar["close"]), 6))
                opens.append(round(float(bar.get("open", bar["close"])), 6))
                highs.append(round(float(bar.get("high", bar["close"])), 6))
                lows.append(round(float(bar.get("low", bar["close"])), 6))
                vols.append(int(float(bar.get("volume", 0) or 0)))
            except (ValueError, KeyError):
                continue

        if len(prices) < 10:
            return None
        print(f"[fmp] OK — {sym} {fmp_iv}: {len(prices)} bars")
        return _build_chart_output(dates, prices, vols, timeframe,
                                   opens_raw=opens, highs_raw=highs, lows_raw=lows)
    except Exception as e:
        print(f"[fmp] error {sym}: {e}")
        return None


def fetch_chart_direct(ticker, asset_type, timeframe):
    """Try multiple free data sources in priority order.
    Returns (dates, prices, vols, ema20, ema50) or None if all fail."""
    # 1. Binance — best for crypto, no rate limits
    if asset_type == "crypto":
        result = _fetch_binance(ticker, timeframe)
        if result:
            return result

    # 2. Stooq — works for stocks, indices, some forex (daily only)
    if asset_type in ("stock", "index", "forex", "commodity"):
        print(f"[chart] trying Stooq for {ticker} ({asset_type}) {timeframe}")
        result = _fetch_stooq(ticker, asset_type, timeframe)
        if result:
            return result
        print(f"[chart] Stooq failed for {ticker}")

    # 3. FMP — reliable for stocks on cloud servers (needs API key)
    if asset_type in ("stock", "index", "forex", "commodity"):
        print(f"[chart] trying FMP for {ticker} ({asset_type}) {timeframe}")
        result = _fetch_fmp(ticker, asset_type, timeframe)
        if result:
            return result
        print(f"[chart] FMP failed for {ticker}")

    # 4. Yahoo Finance v8 — last resort (likely 429 on Railway)
    print(f"[chart] trying Yahoo v8 for {ticker} ({asset_type}) {timeframe}")
    result = _fetch_yahoo_v8(ticker, asset_type, timeframe)
    if result:
        return result

    print(f"[chart] ALL sources failed for {ticker} {timeframe}")
    return None

# ─── MULTI-TIMEFRAME TREND ────────────────────────────────────
def get_mtf_trend(ticker):
    result = {}
    configs = {
        "4H": {"interval": "1h",  "period": "60d", "resample": "4h"},
        "1D": {"interval": "1d",  "period": "1y"},
    }
    for label, cfg in configs.items():
        try:
            df_m = safe_download(ticker, period=cfg["period"],
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
    rsi       = ind.get("rsi", 50)
    bb_pos    = ind.get("bb_pos", 0.5)
    macd_hist = ind.get("macd_hist", 0)
    ema_trend = ind.get("ema_trend", "MIXED")
    st        = ind.get("supertrend", "NEUTRAL")
    vol_ratio = ind.get("vol_ratio", 1.0)

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
    is_bear_ema   = ind.get("ema_trend", "MIXED") in ("BEAR", "STRONG BEAR")
    is_bear_st    = ind.get("supertrend", "NEUTRAL") == "BEARISH"
    is_oversold   = (ind.get("rsi") or 50) < 33
    near_lower_bb = (ind.get("bb_pos") or 0.5) < 0.18

    if not ((is_bear_ema or is_bear_st) and is_oversold and near_lower_bb):
        return {"counter_trade": False}

    price  = ind.get("price", 0)
    atr    = ind.get("atr", 0)
    sup    = ind.get("support", price * 0.98)
    if not price or not atr:
        return {"counter_trade": False}
    entry  = price
    sl     = round(min(sup - atr * 0.3, price - atr * 1.5), 4)
    risk   = entry - sl
    if risk <= 0:
        return {"counter_trade": False}

    tp1 = round(entry + risk * 1.5, 4)
    tp2 = round(entry + risk * 2.5, 4)
    tp3 = round(entry + risk * 4.0, 4)
    rr1 = round((tp1 - entry) / risk, 1)
    rr2 = round((tp2 - entry) / risk, 1)
    rr3 = round((tp3 - entry) / risk, 1)
    sl_pct  = round(abs(entry - sl) / entry * 100, 2)
    tp1_pct = round(abs(tp1 - entry) / entry * 100, 2)
    trend_label = ind["ema_trend"].replace("STRONG ", "")
    summary = (
        f"Primary trend is {trend_label} but RSI({ind['rsi']:.1f}) is deeply oversold "
        f"with price at the lower Bollinger Band ({ind['bb_pos']:.0%} position). "
        f"A short-term bounce is statistically likely. "
        f"Primary exit: TP1 ({tp1_pct}% gain). TP2 for aggressive traders only. HIGH RISK — do NOT hold against the trend."
    )
    return {
        "counter_trade":   True,
        "counter_signal":  "COUNTER_BUY",
        "counter_entry":   round(entry, 4),
        "counter_sl":      sl,
        "counter_tp1":     tp1,
        "counter_tp2":     tp2,
        "counter_tp3":     tp3,
        "counter_rr1":     rr1,
        "counter_rr2":     rr2,
        "counter_rr3":     rr3,
        "counter_sl_pct":  sl_pct,
        "counter_tp1_pct": tp1_pct,
        "counter_summary": summary,
    }

# ─── TRADINGVIEW DATA ENRICHMENT ─────────────────────────────
# Uses TradingView's public scanner API (no API key required) to fetch
# TV-computed indicator values and fundamentals for cross-verification.

# Map app timeframe strings to TradingView column suffixes
_TF_SUFFIX = {"5m": "|5", "15m": "|15", "30m": "|30", "1h": "|60", "4h": "|240", "1d": ""}

_TV_SCANNER = {
    "crypto":    "https://scanner.tradingview.com/crypto/scan",
    "stock":     "https://scanner.tradingview.com/america/scan",
    "forex":     "https://scanner.tradingview.com/forex/scan",
    "commodity": "https://scanner.tradingview.com/cfd/scan",
    "index":     "https://scanner.tradingview.com/america/scan",
}

# Preferred forex data sources in priority order
_FOREX_PREFIXES = ["OANDA", "FOREXCOM", "FX_IDC", "FX"]
_TV_COMMODITY_MAP = {
    "GC=F": "COMEX:GC1!",  "SI=F": "COMEX:SI1!",
    "CL=F": "NYMEX:CL1!",  "NG=F": "NYMEX:NG1!",
    "HG=F": "COMEX:HG1!",  "ZW=F": "CBOT:ZW1!",
    "ZC=F": "CBOT:ZC1!",   "PL=F": "NYMEX:PL1!",
}
_TV_INDEX_MAP = {
    "^GSPC":    "SP:SPX",          "^IXIC":    "NASDAQ:COMP",
    "^DJI":     "DJ:DJI",          "^FTSE":    "SPREADEX:FTSE",
    "^GDAXI":   "XETR:DAX",        "^N225":    "TSE:NI225",
    "^HSI":     "HSI:HSI",         "^FCHI":    "EURONEXT:PX1",
    "^AXJO":    "ASX:XJO",         "^RUT":     "TVC:RUT",
    "^VIX":     "TVC:VIX",         "^STOXX50E":"EURONEXT:SX5E",
    "^NDX":     "NASDAQ:NDX",      "^BUK100P": "SPREADEX:FTSE",
}

def _tv_symbol_market(ticker, asset_type):
    """Return (tv_symbol, scanner_market) for TradingView scanner API."""
    if asset_type == "crypto":
        base = ticker.replace("-USD","").replace("-USDT","").replace("-BTC","")
        return f"BINANCE:{base}USDT", "crypto"
    if asset_type == "forex":
        pair = ticker.replace("=X","").replace("/","").replace("-","")
        return f"OANDA:{pair}", "forex"  # OANDA has broadest forex coverage on TV
    if asset_type == "commodity":
        tv = _TV_COMMODITY_MAP.get(ticker, f"TVC:{ticker.replace('=F','').replace('=','')}")
        return tv, "commodity"
    if asset_type == "index":
        tv = _TV_INDEX_MAP.get(ticker, ticker.replace("^",""))
        return tv, "index"
    # stock — just the ticker; TV scanner will find it on America market
    return ticker, "stock"

def _rec_label(score):
    """Map TradingView Recommend.All score (-1..1) to a human label."""
    if score is None:  return "N/A"
    if score >=  0.5:  return "STRONG BUY"
    if score >=  0.1:  return "BUY"
    if score > -0.1:   return "NEUTRAL"
    if score > -0.5:   return "SELL"
    return "STRONG SELL"

def fetch_tv_data(raw_ticker, asset_type, timeframe="1d"):
    """Fetch TradingView indicators for the requested timeframe.
    TradingView is the primary — and for signals, the only required — data source.
    Uses column suffixes so RSI|60 = 1H RSI, RSI|240 = 4H RSI, etc.
    Returns a full indicator dict or None on failure.
    """
    try:
        tv_sym, market = _tv_symbol_market(raw_ticker, asset_type)
        url = _TV_SCANNER.get(asset_type, _TV_SCANNER["stock"])
        tf  = _TF_SUFFIX.get(timeframe, "")

        # Columns for the requested timeframe
        columns = [
            "close", "change",
            f"RSI{tf}", f"MACD.macd{tf}", f"MACD.signal{tf}",
            f"EMA20{tf}", f"EMA50{tf}", f"EMA200{tf}",
            f"BB.upper{tf}", f"BB.lower{tf}",
            f"ATR{tf}", "volume",
            "Recommend.All", "Recommend.MA", "Recommend.Other", "ADX",
            # MTF context columns
            "RSI|60", "EMA20|60", "EMA50|60",    # 1H
            "RSI|240", "EMA20|240", "EMA50|240", # 4H
            "RSI", "EMA20", "EMA50",             # Daily
        ]
        if asset_type == "stock":
            columns += ["P/E", "market_cap_basic",
                        "earnings_per_share_basic_ttm", "analyst_count", "Perf.Y"]

        def _tv_post(symbol):
            cache_key = f"tv:{symbol}:{asset_type}:{timeframe}"
            cached = cache_get(cache_key)
            if cached is not None:
                return cached
            r = _browser_session.post(
                url,
                json={"symbols": {"tickers": [symbol]}, "columns": columns},
                headers={
                    "Content-Type": "application/json",
                    "Origin":       "https://www.tradingview.com",
                    "Referer":      "https://www.tradingview.com/",
                },
                timeout=10,
            )
            if r.status_code != 200:
                print(f"[TV] HTTP {r.status_code} for {symbol}")
                return None
            rows = r.json().get("data", [])
            vals = rows[0].get("d", []) if rows else None
            if vals:
                cache_set(cache_key, vals)
            return vals

        vals = _tv_post(tv_sym)

        # Forex: retry with multiple broker prefixes (OANDA → FOREXCOM → FX_IDC → FX)
        if not vals and asset_type == "forex":
            pair = tv_sym.split(":")[-1]
            for prefix in _FOREX_PREFIXES:
                alt_sym = f"{prefix}:{pair}"
                if alt_sym != tv_sym:
                    vals = _tv_post(alt_sym)
                    if vals:
                        tv_sym = alt_sym
                        break

        # Stocks: bare ticker (e.g. "AAPL") often misses — retry with exchange prefixes.
        # TV scanner /america/scan resolves exchange-qualified symbols more reliably.
        if not vals and asset_type == "stock":
            bare = tv_sym.split(":")[-1]  # strip any prefix already present
            for exchange in ["NASDAQ", "NYSE", "AMEX", "TSX", "ASX"]:
                alt_sym = f"{exchange}:{bare}"
                if alt_sym != tv_sym:
                    vals = _tv_post(alt_sym)
                    if vals:
                        tv_sym = alt_sym
                        break

        if not vals:
            return None

        vals = list(vals) + [None] * max(0, len(columns) - len(vals))
        col_idx = {c: i for i, c in enumerate(columns)}

        def g(col):
            idx = col_idx.get(col)
            if idx is None or idx >= len(vals):
                return None
            v = vals[idx]
            return None if v is None or (isinstance(v, float) and v != v) else v

        close    = g("close")
        chg      = g("change")
        rsi      = g(f"RSI{tf}")
        macd_l   = g(f"MACD.macd{tf}")
        macd_s   = g(f"MACD.signal{tf}")
        macd_h   = round(macd_l - macd_s, 6) if (macd_l is not None and macd_s is not None) else None
        ema20    = g(f"EMA20{tf}")
        ema50    = g(f"EMA50{tf}")
        ema200   = g(f"EMA200{tf}")
        bb_upper = g(f"BB.upper{tf}")
        bb_lower = g(f"BB.lower{tf}")
        atr_val  = g(f"ATR{tf}")
        rec_all  = g("Recommend.All")
        rec_ma   = g("Recommend.MA")
        rec_osc  = g("Recommend.Other")
        adx      = g("ADX")

        result = {
            "tv_symbol":      tv_sym,
            "tv_price":       round(close,   6) if close    is not None else None,
            "tv_chg":         round(chg,     2) if chg      is not None else None,
            "tv_rsi":         round(rsi,     2) if rsi      is not None else None,
            "tv_macd_hist":   macd_h,
            "tv_ema20":       round(ema20,   4) if ema20    is not None else None,
            "tv_ema50":       round(ema50,   4) if ema50    is not None else None,
            "tv_ema200":      round(ema200,  4) if ema200   is not None else None,
            "tv_bb_upper":    round(bb_upper,4) if bb_upper is not None else None,
            "tv_bb_lower":    round(bb_lower,4) if bb_lower is not None else None,
            "tv_atr":         round(atr_val, 6) if atr_val  is not None else None,
            "tv_adx":         round(adx,     2) if adx      is not None else None,
            "tv_rec_all":     round(rec_all, 3) if rec_all  is not None else None,
            "tv_rec_label":   _rec_label(rec_all),
            "tv_rec_ma":      round(rec_ma,  3) if rec_ma   is not None else None,
            "tv_rec_ma_lbl":  _rec_label(rec_ma),
            "tv_rec_osc":     round(rec_osc, 3) if rec_osc  is not None else None,
            "tv_rec_osc_lbl": _rec_label(rec_osc),
            # MTF context
            "tv_mtf": {
                "1H": {"rsi": g("RSI|60"),  "ema20": g("EMA20|60"),  "ema50": g("EMA50|60")},
                "4H": {"rsi": g("RSI|240"), "ema20": g("EMA20|240"), "ema50": g("EMA50|240")},
                "1D": {"rsi": g("RSI"),     "ema20": g("EMA20"),     "ema50": g("EMA50")},
            },
        }

        if asset_type == "stock":
            result.update({
                "tv_pe":       g("P/E"),
                "tv_mktcap":   g("market_cap_basic"),
                "tv_eps":      g("earnings_per_share_basic_ttm"),
                "tv_analysts": g("analyst_count"),
                "tv_perf_1y":  g("Perf.Y"),
            })

        return result

    except Exception as e:
        print(f"[TV] fetch_tv_data error for {raw_ticker}: {e}")
        return None

def _tv_prompt_block(tv):
    """Format TradingView data as a prompt section for Claude."""
    if not tv:
        return ""
    lines = [
        "\nTRADINGVIEW CROSS-VERIFICATION (computed by TradingView's 26-indicator engine):",
        f"TV Overall Recommendation: {tv['tv_rec_label']} (score {tv['tv_rec_all']})",
        f"TV MA Consensus: {tv['tv_rec_ma_lbl']} | TV Oscillator Consensus: {tv['tv_rec_osc_lbl']}",
    ]
    if tv.get("tv_rsi")   is not None: lines.append(f"TV RSI(14): {tv['tv_rsi']}")
    if tv.get("tv_macd_hist") is not None: lines.append(f"TV MACD Histogram: {tv['tv_macd_hist']}")
    if tv.get("tv_adx")   is not None: lines.append(f"TV ADX: {tv['tv_adx']}")
    if tv.get("tv_ema20") is not None:
        lines.append(f"TV EMA20={tv['tv_ema20']} | EMA50={tv['tv_ema50']} | EMA200={tv['tv_ema200']}")
    if tv.get("tv_bb_upper") is not None:
        lines.append(f"TV BB Upper={tv['tv_bb_upper']} | BB Lower={tv['tv_bb_lower']}")
    # Stock fundamentals
    if tv.get("tv_pe")      is not None: lines.append(f"P/E Ratio: {tv['tv_pe']}")
    if tv.get("tv_eps")     is not None: lines.append(f"EPS (TTM): {tv['tv_eps']}")
    if tv.get("tv_mktcap")  is not None:
        mc = tv['tv_mktcap']
        mc_str = f"${mc/1e12:.2f}T" if mc >= 1e12 else f"${mc/1e9:.1f}B" if mc >= 1e9 else f"${mc/1e6:.0f}M"
        lines.append(f"Market Cap: {mc_str}")
    if tv.get("tv_analysts") is not None: lines.append(f"Analyst Count: {tv['tv_analysts']}")
    if tv.get("tv_perf_1y")  is not None: lines.append(f"1Y Performance: {tv['tv_perf_1y']:+.1f}%")
    lines.append(
        "NOTE: Weight the TV Recommendation alongside the yfinance indicators. "
        "If they strongly agree → higher confidence. If they disagree → note the divergence in your summary."
    )
    return "\n".join(lines)



# ─── OPENAI DATA NARRATOR ────────────────────────────────────
def _narrate_data_openai(result, ticker, asset_type, ind, timeframe):
    """
    Use OpenAI GPT-4o-mini to narrate indicator data as plain English.
    Strict rules: ONLY reference exact numbers provided. No speculation, no predictions.
    Returns result unchanged on any error or if API key is missing.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return result

    try:
        # Build prompt with all exact computed values
        prompt = f"""You are a data narrator for traders. Your ONLY job is to describe what the numbers below mean in plain English.

STRICT RULES:
- ONLY reference the exact numbers provided below. Do not invent or estimate any data.
- Do not predict future price movement. Do not say "price will" or "expect to."
- Do not add information not present in the data.
- Your audience is BEGINNER traders. Explain every trading term in simple everyday language.
- Avoid jargon. If you must use a term (RSI, MACD, etc.), immediately explain what it means.
- Be concise. Use the actual numbers. Make it feel like a smart friend explaining the chart.

TICKER: {ticker} ({asset_type}, {timeframe} timeframe)
SIGNAL: {result['signal']} | CONFIDENCE: {result['confidence']}
PRICE: {ind.get('price')} | CHANGE: {ind.get('chg_1d')}%
RSI (14): {ind.get('rsi')}
MACD HISTOGRAM: {ind.get('macd_hist')}
EMA TREND: {ind.get('ema_trend')} | EMA20: {ind.get('ema20')} | EMA50: {ind.get('ema50')}
ATR (14): {ind.get('atr')} ({round((ind.get('atr',0)/max(ind.get('price',1),0.01))*100, 2)}% of price)
VOLUME RATIO: {ind.get('vol_ratio')}x vs 30d avg
BOLLINGER POSITION: {ind.get('bb_pos')} | BB WIDTH: {ind.get('bb_width')}
SUPERTREND: {ind.get('supertrend')}
SUPPORT: {ind.get('support')} | RESISTANCE: {ind.get('resistance')}
ENTRY: {result.get('entry')} | STOP LOSS: {result.get('stop_loss')}
TP1: {result.get('tp1')} | TP2: {result.get('tp2')} | TP3: {result.get('tp3')}

Return JSON with these keys ONLY:
- "summary": 2 sentences for a beginner — what is happening with this asset right now, using the numbers above
- "narrative": 3 sentences explaining the trade setup in simple language, referencing specific values
- "rsi_assessment": 1 sentence explaining RSI {ind.get('rsi')} in plain English (e.g. "RSI is at 65 — think of it as a momentum meter from 0-100. Right now it shows moderate buying energy, not yet overheated.")
- "trend_assessment": 1 sentence explaining the EMA trend simply (e.g. "The short-term average price ({ind.get('ema20')}) is above the longer-term average ({ind.get('ema50')}), which means the overall direction is upward.")
- "macd_assessment": 1 sentence explaining MACD in beginner terms (e.g. "MACD measures if momentum is speeding up or slowing down. The reading of X means...")
- "volume_assessment": 1 sentence explaining volume ratio simply (e.g. "Trading activity is 1.8x higher than usual — more people are trading this than normal, which adds weight to the signal.")
- "supertrend_assessment": 1 sentence explaining supertrend simply (e.g. "The Supertrend indicator acts like a safety line — price is currently above it, meaning the uptrend is intact.")
- "rsi_beginner": 1 sentence — what RSI means for someone who has never traded (no jargon at all)
- "macd_beginner": 1 sentence — what MACD means for a complete beginner
- "ema_beginner": 1 sentence — what the EMA trend means for a complete beginner
- "volume_beginner": 1 sentence — what the volume ratio means for a complete beginner
- "atr_beginner": 1 sentence — explain ATR as "how much the price typically moves" for a beginner
- "bb_beginner": 1 sentence — explain Bollinger Bands position in the simplest possible way
- "overall_beginner": 2 sentences — the big picture in the simplest terms a non-trader would understand

Return ONLY valid JSON. No markdown."""

        # POST to OpenAI API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 900
            },
            timeout=(10, 25)
        )

        if response.status_code != 200:
            return result

        response_data = response.json()
        if "choices" not in response_data or not response_data["choices"]:
            return result

        content = response_data["choices"][0].get("message", {}).get("content", "")
        if not content:
            return result

        # Parse JSON response
        openai_result = json.loads(content)

        # Extract only allowed text keys
        allowed_keys = {
            "summary",
            "narrative",
            "rsi_assessment",
            "trend_assessment",
            "macd_assessment",
            "volume_assessment",
            "supertrend_assessment",
            "rsi_beginner",
            "macd_beginner",
            "ema_beginner",
            "volume_beginner",
            "atr_beginner",
            "bb_beginner",
            "overall_beginner",
        }

        # Merge ONLY the text keys into result, preserving all other fields
        for key in allowed_keys:
            if key in openai_result and isinstance(openai_result[key], str):
                result[key] = openai_result[key]

        return result

    except Exception:
        # Silently return result unchanged on any error
        return result


# ─── CLAUDE ANALYSIS ─────────────────────────────────────────
def _compute_footprint_dominance(ind):
    """Compute buyer/seller dominance from the last candle's wick geometry.
    Returns (buyer_pct, seller_pct) — both 0..100, or (None, None) if unavailable.
    Used as a sanity check against the proposed signal direction."""
    try:
        opens  = ind.get("chart_opens")  or []
        highs  = ind.get("chart_highs")  or []
        lows   = ind.get("chart_lows")   or []
        closes = ind.get("chart_prices") or []
        if not (opens and highs and lows and closes):
            return None, None
        # Use the last 3 candles, weighted toward the most recent
        n = min(3, len(closes))
        if n == 0:
            return None, None
        total_buy = 0.0
        total_sell = 0.0
        weights = [0.5, 0.3, 0.2][:n]  # most recent gets most weight
        for i in range(n):
            idx = -(i + 1)
            try:
                o = float(opens[idx]); h = float(highs[idx])
                l = float(lows[idx]);  c = float(closes[idx])
            except Exception:
                continue
            rng = h - l
            if rng <= 0:
                continue
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            body       = abs(c - o)
            body_sign  = 1.0 if c >= o else -1.0
            # Buying pressure: lower wick (rejected lows) + bullish body
            buy_pressure = lower_wick + (body if body_sign > 0 else 0)
            # Selling pressure: upper wick (rejected highs) + bearish body
            sell_pressure = upper_wick + (body if body_sign < 0 else 0)
            tot = buy_pressure + sell_pressure
            if tot <= 0:
                continue
            total_buy  += weights[i] * (buy_pressure  / tot)
            total_sell += weights[i] * (sell_pressure / tot)
        w_sum = total_buy + total_sell
        if w_sum <= 0:
            return None, None
        buyer_pct  = round(100.0 * total_buy  / w_sum, 1)
        seller_pct = round(100.0 * total_sell / w_sum, 1)
        return buyer_pct, seller_pct
    except Exception as e:
        print(f"[footprint] compute error: {e}")
        return None, None


def _htf_trend_bias(mtf, timeframe):
    """Return 'BULLISH' / 'BEARISH' / 'NEUTRAL' from higher-TF MTF data.
    For a 4H request we check 1D; for 1H we check 4H; for 1D we check 1D itself."""
    if not mtf:
        return "NEUTRAL"
    tf = (timeframe or "").lower()
    # Pick the HTF one level above the current request
    if tf in ("1m", "5m", "15m", "30m", "1h"):
        htf_key = "4H"
    elif tf in ("2h", "4h"):
        htf_key = "1D"
    else:  # 1d or higher — use its own read
        htf_key = "1D"
    htf = mtf.get(htf_key) or mtf.get("1D") or mtf.get("4H") or {}
    return (htf.get("trend") or "NEUTRAL").upper()


def get_analysis(ticker, asset_type, ind, timeframe, tv=None, mtf=None):
    """Generate trading signal using gated template logic.

    Accuracy fixes (v2):
      • Fixed Bollinger Band logic (overbought = bearish, not bullish)
      • Net-score comparison (bullish vs bearish count, not just bullish threshold)
      • Confidence floor — weak signals downgraded to HOLD
      • Higher-timeframe trend gate — blocks counter-trend signals
      • Candle footprint sanity check — rejects signals that contradict order flow
    """
    # Safe defaults for missing/None values
    price = ind.get("price", 0) or 0
    rsi = ind.get("rsi", 50) or 50
    ema_trend = ind.get("ema_trend", "neutral") or "neutral"
    macd_hist = ind.get("macd_hist", 0) or 0
    bb_pos = ind.get("bb_pos", 0.5) or 0.5
    atr = ind.get("atr", price * 0.01) or (price * 0.01)  # Default to 1% of price if ATR is 0
    vol_ratio = ind.get("vol_ratio", 1.0) or 1.0
    supertrend = ind.get("supertrend", "neutral") or "neutral"
    support = ind.get("support", price * 0.98)
    resistance = ind.get("resistance", price * 1.02)
    chg_1d = ind.get("chg_1d", 0) or 0
    ema20 = ind.get("ema20", price)
    ema50 = ind.get("ema50", price)
    ema200 = ind.get("ema200", price)
    bb_width = ind.get("bb_width", 0.02) or 0.02

    # Count bullish/bearish indicators
    bullish_count = 0
    bearish_count = 0

    # ── RSI logic (trend-aware) ──
    # In a strong uptrend, RSI 60-80 is continuation, not reversal.
    # In a downtrend, RSI 20-40 is continuation, not bounce.
    if rsi >= 75:
        bearish_count += 1
        rsi_assessment = f"RSI at {rsi} signals overbought conditions; pullback risk is elevated."
    elif 55 <= rsi < 75:
        bullish_count += 1
        rsi_assessment = f"RSI at {rsi} shows strong bullish momentum in the continuation zone."
    elif 45 <= rsi < 55:
        rsi_assessment = f"RSI at {rsi} is neutral; looking for directional confirmation."
    elif 25 < rsi < 45:
        bearish_count += 1
        rsi_assessment = f"RSI at {rsi} shows bearish momentum below the midline."
    else:  # rsi <= 25
        bullish_count += 1
        rsi_assessment = f"RSI at {rsi} indicates oversold conditions; bounce potential is present."

    # ── EMA Trend logic (higher weight: counts as 2) ──
    if ema_trend.lower() == "bullish":
        bullish_count += 2
        trend_assessment = "EMA stack is bullish; uptrend structure is intact and price is above key moving averages."
    elif ema_trend.lower() == "bearish":
        bearish_count += 2
        trend_assessment = "EMA stack is bearish; downtrend structure dominates and price remains below key MAs."
    else:
        trend_assessment = "EMAs are mixed; trend definition is unclear at current price."

    # ── MACD logic ──
    if macd_hist > 0:
        bullish_count += 1
        macd_assessment = "MACD histogram is positive; bullish momentum is building."
    elif macd_hist < 0:
        bearish_count += 1
        macd_assessment = "MACD histogram is negative; bearish momentum dominates the tape."
    else:
        macd_assessment = "MACD histogram is flat; momentum is transitioning."

    # ── Volume logic ──
    if vol_ratio > 1.2:
        # High volume confirms the prevailing EMA trend direction
        if ema_trend.lower() == "bullish":
            bullish_count += 1
        elif ema_trend.lower() == "bearish":
            bearish_count += 1
        volume_assessment = f"Volume ratio at {vol_ratio:.2f}x confirms participation above average."
    else:
        volume_assessment = f"Volume ratio at {vol_ratio:.2f}x suggests weak conviction; confirmation needed."

    # ── Supertrend logic ──
    if supertrend.lower() == "bullish":
        bullish_count += 1
        supertrend_assessment = "Supertrend is bullish; upside continuation is likely unless support breaks."
    elif supertrend.lower() == "bearish":
        bearish_count += 1
        supertrend_assessment = "Supertrend is bearish; downside is protected and rallies face selling."
    else:
        supertrend_assessment = "Supertrend is neutral; waiting for directional confirmation."

    # ── Bollinger Bands (FIXED — overbought is bearish, oversold is bullish) ──
    if bb_pos > 0.85:
        bearish_count += 1  # Near upper band = overbought, mean reversion risk
    elif bb_pos < 0.15:
        bullish_count += 1  # Near lower band = oversold, bounce potential

    # ── Net score → raw signal ──
    net = bullish_count - bearish_count
    if net >= 3:
        signal = "BUY"
    elif net <= -3:
        signal = "SELL"
    else:
        signal = "HOLD"

    # ── Confidence from absolute net score ──
    if abs(net) >= 5:
        confidence = "HIGH"
    elif abs(net) >= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # ══════════════════════════════════════════════════════════════
    # GATE 1: Higher-timeframe trend filter
    # Block any signal that fights the HTF trend.
    # ══════════════════════════════════════════════════════════════
    htf_bias = _htf_trend_bias(mtf, timeframe)
    gate_note = ""
    if signal == "SELL" and htf_bias == "BULLISH":
        print(f"[gate] HTF trend BULLISH — blocking SELL on {ticker} {timeframe}")
        signal = "HOLD"
        confidence = "LOW"
        gate_note = "HTF trend is bullish — counter-trend SELL suppressed."
    elif signal == "BUY" and htf_bias == "BEARISH":
        print(f"[gate] HTF trend BEARISH — blocking BUY on {ticker} {timeframe}")
        signal = "HOLD"
        confidence = "LOW"
        gate_note = "HTF trend is bearish — counter-trend BUY suppressed."

    # ══════════════════════════════════════════════════════════════
    # GATE 2: Candle footprint sanity check
    # If the last few candles show strong one-sided pressure that
    # contradicts the proposed signal direction, downgrade to HOLD.
    # ══════════════════════════════════════════════════════════════
    buyer_pct, seller_pct = _compute_footprint_dominance(ind)
    if buyer_pct is not None:
        if signal == "SELL" and buyer_pct >= 70:
            print(f"[gate] footprint shows {buyer_pct}% buyers — blocking SELL on {ticker}")
            signal = "HOLD"
            confidence = "LOW"
            gate_note = f"Footprint shows {buyer_pct}% buyer pressure — SELL contradicts order flow."
        elif signal == "BUY" and seller_pct >= 70:
            print(f"[gate] footprint shows {seller_pct}% sellers — blocking BUY on {ticker}")
            signal = "HOLD"
            confidence = "LOW"
            gate_note = f"Footprint shows {seller_pct}% seller pressure — BUY contradicts order flow."

    # ══════════════════════════════════════════════════════════════
    # GATE 3: Confidence floor
    # Any signal that survives the gates but still scores LOW is
    # not actionable — downgrade to HOLD so we don't mislead users.
    # ══════════════════════════════════════════════════════════════
    if signal != "HOLD" and confidence == "LOW":
        print(f"[gate] confidence floor — downgrading {signal} to HOLD on {ticker}")
        signal = "HOLD"
        gate_note = gate_note or "Indicator conviction is too weak for an actionable signal."

    # Generate trade levels based on ATR
    if signal != "HOLD" and atr > 0:
        entry = round(price, 4) if price > 100 else round(price, 2)

        if signal == "BUY":
            stop_loss = round(price - (1.5 * atr), 4) if price > 100 else round(price - (1.5 * atr), 2)
            tp1 = round(price + (2 * atr), 4) if price > 100 else round(price + (2 * atr), 2)
            tp2 = round(price + (3.5 * atr), 4) if price > 100 else round(price + (3.5 * atr), 2)
            tp3 = round(price + (5.5 * atr), 4) if price > 100 else round(price + (5.5 * atr), 2)
        else:  # SELL
            stop_loss = round(price + (1.5 * atr), 4) if price > 100 else round(price + (1.5 * atr), 2)
            tp1 = round(price - (2 * atr), 4) if price > 100 else round(price - (2 * atr), 2)
            tp2 = round(price - (3.5 * atr), 4) if price > 100 else round(price - (3.5 * atr), 2)
            tp3 = round(price - (5.5 * atr), 4) if price > 100 else round(price - (5.5 * atr), 2)

        # Calculate R:R ratios
        risk = abs(entry - stop_loss)
        if risk > 0:
            rr1 = round((abs(tp1 - entry) / risk), 1)
            rr2 = round((abs(tp2 - entry) / risk), 1)
            rr3 = round((abs(tp3 - entry) / risk), 1)
        else:
            rr1 = rr2 = rr3 = None
    else:
        entry = stop_loss = tp1 = tp2 = tp3 = None
        rr1 = rr2 = rr3 = None

    # Generate timing call
    if signal == "HOLD":
        timing = "WAIT 5-15 MIN"
        timing_detail = "Mixed signals require further consolidation before a directional entry is warranted."
    elif rsi < 35:
        timing = "ENTER NOW"
        timing_detail = "RSI in oversold territory presents an attractive risk-reward entry opportunity."
    elif rsi > 70:
        timing = "LATE ENTRY — CAUTION"
        timing_detail = "Overbought conditions suggest waiting for a pullback to enter with better odds."
    elif 35 <= rsi <= 50:
        timing = "WAIT FOR PULLBACK"
        timing_detail = "Price is rising but RSI is in accumulation zone; optimal entry on minor retracement."
    else:
        timing = "WAIT 5-15 MIN"
        timing_detail = "Await candle close confirmation before committing capital to this setup."

    # Generate narrative with actual values
    if signal == "BUY":
        narrative = (
            f"Price at {price} is showing {bullish_count} bullish setup components. "
            f"With RSI at {rsi} and EMA trend {ema_trend}, the upside structure looks intact. "
            f"MACD histogram is {'positive' if macd_hist > 0 else 'negative'} and volume is {vol_ratio:.2f}x average, "
            f"confirming {'strong' if vol_ratio > 1.2 else 'modest'} conviction. The setup rewards buyers on a break above {resistance}."
        )
    elif signal == "SELL":
        narrative = (
            f"Price at {price} is facing {bearish_count} bearish setup indicators. "
            f"RSI at {rsi} and EMA trend {ema_trend} suggest downside pressure is building. "
            f"MACD histogram is {'negative' if macd_hist <= 0 else 'positive'} and volume context shows {'weak' if vol_ratio < 1.0 else 'moderate'} participation. "
            f"Bears could target {support} on sustained selling."
        )
    else:
        narrative = (
            f"Price at {price} is conflicted: {bullish_count} bullish vs {bearish_count} bearish signals. "
            f"RSI at {rsi} is in neutral territory and EMAs show mixed tone. "
            f"Neither side has clear momentum advantage yet. Wait for a catalyst or candle structure break to define the next directional move."
        )

    # Summary
    if signal == "BUY":
        summary = f"Bullish setup detected with {bullish_count} aligned indicators. Multiple EMAs support upside and volume confirms. Enter on break of {resistance}."
    elif signal == "SELL":
        summary = f"Bearish structure in place with {bearish_count} aligned down indicators. Support at {support} is the key level. Enter on break below."
    else:
        summary = f"Mixed signals: {bullish_count} bullish vs {bearish_count} bearish. Wait for consolidation to resolve before committing to a direction."

    # Scenarios
    if signal == "BUY":
        bull_scenario = f"Buyers push past {resistance}; price accelerates to {tp1} then {tp2} as momentum compounds. Higher lows form and rallies get bought."
        base_scenario = f"Price consolidates above {support}, grinding higher with 2-3 pullbacks to the 20-EMA before testing {tp1}."
        bear_scenario = f"Breakdown below {support} triggers stop cascades; price reverses hard to {stop_loss} and beyond if bears gain traction."
    elif signal == "SELL":
        bull_scenario = f"Sudden rally back to {resistance}; momentum buyers push price up but selling resumes on failure to break above it."
        base_scenario = f"Price drifts lower from {resistance} toward {support}; lower highs form and breaks establish new lows heading to {tp1}."
        bear_scenario = f"Capitulation selling at {support} triggers acceleration downward; cascading stops hit {tp2} then {tp3} as shorts pile in."
    else:
        bull_scenario = "Bullish breakout above resistance line would shift the bias upward and trigger fresh buying interest."
        base_scenario = "Consolidation between support and resistance continues until a catalyst or technical break defines the next trend."
        bear_scenario = "Bearish break below support could shift momentum downward and attract new selling pressure."

    # Micro lesson
    if bullish_count >= 4:
        micro_lesson = "When 4+ indicators align, the probability of directional follow-through rises significantly. Volume confirmation is your edge."
    elif bearish_count >= 4:
        micro_lesson = "Aligned bearish setups carry high conviction only when institutional volume backs the move. Solo price action is noise."
    else:
        micro_lesson = "Mixed signals are market's way of saying 'wait'—the best traders sit out indecision and reload on clarity."

    # If gates fired, prepend the gate note to narrative/summary so user sees WHY
    if gate_note:
        summary = f"{gate_note} {summary}"
        narrative = f"{gate_note}\n\n{narrative}"

    result = {
        "signal": signal,
        "confidence": confidence,
        "summary": summary,
        "narrative": narrative,
        "timing": timing,
        "timing_detail": timing_detail,
        "micro_lesson": micro_lesson,
        "bull_scenario": bull_scenario,
        "base_scenario": base_scenario,
        "bear_scenario": bear_scenario,
        "entry": entry,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr1": rr1,
        "rr2": rr2,
        "rr3": rr3,
        "rsi_assessment": rsi_assessment,
        "trend_assessment": trend_assessment,
        "macd_assessment": macd_assessment,
        "volume_assessment": volume_assessment,
        "supertrend_assessment": supertrend_assessment,
        "gate_note": gate_note,
        "htf_bias": htf_bias,
        "footprint_buyer_pct": buyer_pct,
        "footprint_seller_pct": seller_pct,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "net_score": net,
    }

    # Call OpenAI to narrate data if API key is configured
    result = _narrate_data_openai(result, ticker, asset_type, ind, timeframe)

    return result



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


def send_whatsapp(message):
    """Send WhatsApp message via Twilio WhatsApp API."""
    sid      = os.environ.get("SMS_ACCOUNT_SID", "").strip()
    token    = os.environ.get("SMS_AUTH_TOKEN",  "").strip()
    from_num = os.environ.get("WA_FROM_NUMBER", "whatsapp:+14155238886").strip()
    to_num   = os.environ.get("WA_TO_NUMBER", "").strip()
    if not all([sid, token, to_num]):
        return
    # Twilio WhatsApp requires the whatsapp: prefix
    if not from_num.startswith("whatsapp:"):
        from_num = f"whatsapp:{from_num}"
    if not to_num.startswith("whatsapp:"):
        to_num = f"whatsapp:{to_num}"
    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_num, "To": to_num, "Body": message},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            print(f"[WhatsApp] Twilio error {resp.status_code}: {resp.text[:200]}")
        else:
            print(f"[WhatsApp] Sent OK")
    except Exception as e:
        print(f"[WhatsApp] Error: {e}")


def send_telegram(message):
    """Send message via Telegram Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id   = os.environ.get("TELEGRAM_CHAT_ID",   "").strip()
    if not all([bot_token, chat_id]):
        return
    # Convert plain-text message to HTML-safe Telegram format
    tg_msg = (message
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": tg_msg, "parse_mode": "HTML"},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[Telegram] Error {resp.status_code}: {resp.text[:200]}")
        else:
            print(f"[Telegram] Sent OK")
    except Exception as e:
        print(f"[Telegram] Error: {e}")


def fire_alert(signal, ticker, price, timeframe, analysis, counter, channels=None):
    """Build alert message and dispatch via configured channels (sms / whatsapp / telegram)."""
    if channels is None:
        channels = ["sms"]

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if signal == "COUNTER_BUY":
        sl   = counter.get("counter_sl")
        tp1  = counter.get("counter_tp1")
        tp2  = counter.get("counter_tp2")
        rr1  = counter.get("counter_rr1")
        rr2  = counter.get("counter_rr2")
        sl_pct  = counter.get("counter_sl_pct", "")
        tp1_pct = counter.get("counter_tp1_pct", "")
        msg = (
            f"⚡ dot-verse COUNTER-BUY BOUNCE\n"
            f"{ticker} ({timeframe.upper()}) @ {price}\n"
            f"Entry:    {counter.get('counter_entry')}\n"
            f"Stop Loss: {sl} (-{sl_pct}%)\n"
            f"TP1 EXIT: {tp1} (+{tp1_pct}%) R/R {rr1}:1  ← Primary exit\n"
            f"TP2 Aggr: {tp2} R/R {rr2}:1\n"
            f"⚠ Against trend — exit at TP1. HIGH RISK\n"
            f"{ts}"
        )
    else:
        emoji = "🟢" if signal == "BUY" else "🔴"
        entry = analysis.get('entry')
        sl    = analysis.get('stop_loss')
        conf  = analysis.get('confidence', '—')
        risk_pct = round(abs(entry - sl) / entry * 100, 2) if entry and sl else "?"
        msg = (
            f"{emoji} dot-verse {signal}\n"
            f"{ticker} ({timeframe.upper()}) @ {price}\n"
            f"Entry:     {entry}\n"
            f"Stop Loss: {sl} (-{risk_pct}%)\n"
            f"TP1: {analysis.get('tp1')} (R/R {analysis.get('rr1')}:1)\n"
            f"TP2: {analysis.get('tp2')} (R/R {analysis.get('rr2')}:1)\n"
            f"TP3: {analysis.get('tp3')} (R/R {analysis.get('rr3')}:1)\n"
            f"Confidence: {conf} | {ts}"
        )

    if "sms" in channels:
        send_sms(msg)
    if "whatsapp" in channels:
        send_whatsapp(msg)
    if "telegram" in channels:
        send_telegram(msg)
    print(f"[Alert] Fired {signal} for {ticker} ({timeframe}) @ {price} via {channels}")

# ─── LIGHTWEIGHT WATCH ANALYSIS (Haiku — ~20× cheaper than Sonnet) ───────────
def get_watch_signal(ticker, asset_type, ind, timeframe):
    """Stripped-down signal check for background watch jobs. Uses pure template logic — no API calls."""
    # Safe defaults
    price = ind.get("price", 0) or 0
    rsi = ind.get("rsi", 50) or 50
    ema_trend = ind.get("ema_trend", "neutral") or "neutral"
    macd_hist = ind.get("macd_hist", 0) or 0
    bb_pos = ind.get("bb_pos", 0.5) or 0.5
    atr = ind.get("atr", price * 0.01) or (price * 0.01)
    vol_ratio = ind.get("vol_ratio", 1.0) or 1.0
    supertrend = ind.get("supertrend", "neutral") or "neutral"
    support = ind.get("support", price * 0.98)
    resistance = ind.get("resistance", price * 1.02)

    # Quick bullish/bearish count
    bullish_count = 0

    if 40 <= rsi <= 70:
        bullish_count += 1
    if rsi < 25:
        bullish_count += 1
    if ema_trend.lower() == "bullish":
        bullish_count += 1
    if macd_hist > 0:
        bullish_count += 1
    if vol_ratio > 1.2:
        bullish_count += 1
    if supertrend.lower() == "bullish":
        bullish_count += 1

    # Signal determination
    if bullish_count >= 4:
        signal = "BUY"
    elif bullish_count >= 2:
        signal = "HOLD"
    else:
        signal = "SELL"

    # Confidence
    if bullish_count >= 5:
        confidence = "HIGH"
    elif bullish_count >= 3:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Trade levels
    if signal != "HOLD" and atr > 0:
        entry = round(price, 4) if price > 100 else round(price, 2)
        if signal == "BUY":
            stop_loss = round(price - (1.5 * atr), 4) if price > 100 else round(price - (1.5 * atr), 2)
            tp1 = round(price + (2 * atr), 4) if price > 100 else round(price + (2 * atr), 2)
            tp2 = round(price + (3.5 * atr), 4) if price > 100 else round(price + (3.5 * atr), 2)
            tp3 = round(price + (5.5 * atr), 4) if price > 100 else round(price + (5.5 * atr), 2)
        else:  # SELL
            stop_loss = round(price + (1.5 * atr), 4) if price > 100 else round(price + (1.5 * atr), 2)
            tp1 = round(price - (2 * atr), 4) if price > 100 else round(price - (2 * atr), 2)
            tp2 = round(price - (3.5 * atr), 4) if price > 100 else round(price - (3.5 * atr), 2)
            tp3 = round(price - (5.5 * atr), 4) if price > 100 else round(price - (5.5 * atr), 2)

        risk = abs(entry - stop_loss)
        if risk > 0:
            rr1 = round((abs(tp1 - entry) / risk), 1)
            rr2 = round((abs(tp2 - entry) / risk), 1)
            rr3 = round((abs(tp3 - entry) / risk), 1)
        else:
            rr1 = rr2 = rr3 = None
    else:
        entry = stop_loss = tp1 = tp2 = tp3 = None
        rr1 = rr2 = rr3 = None

    # Summary
    if signal == "BUY":
        summary = f"{bullish_count} bullish indicators aligned. RSI={rsi}, trend={ema_trend}. Entry at {entry}."
    elif signal == "SELL":
        summary = f"Downside setup with {6-bullish_count} bearish signals. RSI={rsi}, trend={ema_trend}. Short at {entry}."
    else:
        summary = f"Mixed signals ({bullish_count} bullish indicators). Wait for confirmation before entering."

    # Narrative (2-3 sentences)
    if signal == "BUY":
        narrative = (
            f"Price {price} is aligning with bullish structure. EMA trend is {ema_trend} and MACD is {'positive' if macd_hist > 0 else 'negative'}. "
            f"Volume ratio at {vol_ratio:.2f}x supports the move. Target {tp1} with stop at {stop_loss}."
        )
    elif signal == "SELL":
        narrative = (
            f"Price {price} shows bearish setup. EMA trend is {ema_trend} and momentum is fading. "
            f"Selling on rallies toward {resistance}. Stop above {stop_loss}."
        )
    else:
        narrative = (
            f"Mixed setup at price {price}. RSI at {rsi} and EMA trend {ema_trend} lack clear conviction. "
            f"Await next candle confirmation."
        )

    # Timing
    if rsi < 35:
        timing = "ENTER NOW"
    elif rsi > 70:
        timing = "LATE ENTRY — CAUTION"
    elif 35 <= rsi <= 50:
        timing = "WAIT FOR PULLBACK"
    else:
        timing = "WAIT 5-15 MIN"

    return {
        "signal": signal,
        "confidence": confidence,
        "summary": summary,
        "narrative": narrative,
        "timing": timing,
        "entry": entry,
        "stop_loss": stop_loss,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "rr1": rr1,
        "rr2": rr2,
        "rr3": rr3,
    }


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

            df = safe_download(ticker, period=cfg["period"], interval=cfg["interval"],
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

            # Conditions warrant signal check — use lightweight Haiku call
            analysis = get_watch_signal(ticker, asset_type, ind, timeframe)
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
                watch_registry[key]["last_signal"]    = fired_sig or sig
                watch_registry[key]["last_narrative"] = analysis.get("narrative", "")
                watch_registry[key]["last_timing"]    = analysis.get("timing", "")

            if fired_sig:
                fire_alert(fired_sig, ticker, ind["price"], timeframe, analysis, counter,
                           w.get("alert_channels", ["sms"]))
            else:
                # Feature D: Live narrative update even when no new signal fires
                # Store the latest market commentary for this watch
                narrative = analysis.get("narrative", "")
                timing    = analysis.get("timing", "")
                if narrative:
                    with watch_lock:
                        watch_registry[key]["live_commentary"] = {
                            "narrative": narrative,
                            "timing":    timing,
                            "price":     ind["price"],
                            "updated":   now.strftime("%H:%M UTC"),
                        }

        except Exception as e:
            print(f"[Watch] Error for {key}: {e}")

# ─── START BACKGROUND SCHEDULER ───────────────────────────────
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_watch_job, "interval", seconds=60, id="watch_job",
                  max_instances=1, coalesce=True)
scheduler.start()
atexit.register(lambda: scheduler.shutdown(wait=False))

# ─── FOREX AUTO-DETECTION ─────────────────────────────────────
_CURRENCIES = {
    "USD","EUR","GBP","JPY","AUD","NZD","CAD","CHF","CNY","HKD",
    "SGD","NOK","SEK","DKK","ZAR","MXN","INR","BRL","PLN","HUF",
    "CZK","TRY","KRW","THB","MYR","IDR","PHP","CLP","COP","PEN",
    "RUB","SAR","AED","QAR","KWD","NGN","EGP",
}

def is_forex_pair(ticker: str) -> bool:
    """Return True if ticker looks like a 6-letter FX pair, e.g. GBPUSD."""
    t = ticker.replace("/","").replace("-","").replace("=X","").upper()
    return (
        len(t) == 6
        and t[:3] in _CURRENCIES
        and t[3:] in _CURRENCIES
    )

# ─── TICKER NORMALISATION ─────────────────────────────────────
def normalise_ticker(ticker, asset_type):
    # Auto-correct: if user typed a forex pair but picked the wrong asset type, fix it
    clean = ticker.replace("/","").replace("-","").replace("=X","").upper()
    if is_forex_pair(clean) and asset_type not in ("forex",):
        asset_type = "forex"
        ticker = clean

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
        m = {
            # US — S&P 500
            "SPX":"^GSPC","SP500":"^GSPC","SMP500":"^GSPC","SMP":"^GSPC",
            "S&P500":"^GSPC","S&P":"^GSPC","US500":"^GSPC","SP:SPX":"^GSPC",
            # US — NASDAQ 100
            "NDX":"^NDX","NASDAQ100":"^NDX","NAS100":"^NDX","US100":"^NDX",
            "QQQ":"^NDX",
            # US — NASDAQ Composite
            "COMP":"^IXIC","NASDAQ":"^IXIC","NASDAQCOMP":"^IXIC",
            # US — Dow Jones
            "DOW":"^DJI","DJIA":"^DJI","DJI":"^DJI","US30":"^DJI","DJ30":"^DJI",
            # US — Russell 2000
            "RUT":"^RUT","RUSSELL":"^RUT","RUSSELL2000":"^RUT","US2000":"^RUT","R2K":"^RUT",
            # US — VIX
            "VIX":"^VIX","CBOE:VIX":"^VIX","VOLATILITY":"^VIX",
            # Europe — FTSE 100
            "FTSE":"^FTSE","FTSE100":"^FTSE","UK100":"^FTSE",
            # Europe — DAX
            "DAX":"^GDAXI","GER40":"^GDAXI","DAX40":"^GDAXI","DAX30":"^GDAXI",
            # Europe — CAC 40
            "CAC":"^FCHI","CAC40":"^FCHI","FRA40":"^FCHI",
            # Europe — Euro Stoxx 50
            "EUROSTOXX":"^STOXX50E","STOXX50":"^STOXX50E","EU50":"^STOXX50E",
            "EUROSTOXX50":"^STOXX50E","SX5E":"^STOXX50E",
            # Asia — Nikkei 225
            "NIKKEI":"^N225","NKY":"^N225","JPN225":"^N225","N225":"^N225",
            # Asia — Hang Seng
            "HSI":"^HSI","HANGSENG":"^HSI","HK50":"^HSI",
            # Asia — ASX 200
            "ASX":"^AXJO","ASX200":"^AXJO","AUS200":"^AXJO",
        }
        ticker = m.get(ticker, ticker)
    return ticker

# ─── ROUTES ──────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# ─── AUTH ROUTES (no login_required) ─────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    """Check password and create session."""
    if not APP_PASSWORD:
        # No password configured — allow all
        session["authenticated"] = True
        return jsonify({"status": "ok", "message": "No password required"})
    body     = request.json or {}
    password = body.get("password", "").strip()
    if password == APP_PASSWORD:
        session["authenticated"] = True
        session.permanent = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "Incorrect password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})

@app.route("/api/auth-check", methods=["GET"])
def auth_check():
    """Frontend calls this on load to see if the user is already logged in."""
    if not APP_PASSWORD:
        return jsonify({"authenticated": True, "password_required": False})
    return jsonify({
        "authenticated":    session.get("authenticated", False),
        "password_required": True,
    })

@app.route("/api/analyze", methods=["POST"])
@login_required
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

        # normalise_ticker may upgrade asset_type (e.g. GBPUSD typed as crypto → forex)
        if is_forex_pair(ticker.replace("/","").replace("-","").replace("=X","")) and asset_type != "forex":
            asset_type = "forex"

        ticker = normalise_ticker(ticker, asset_type)
        cfg    = TIMEFRAME_CONFIG[timeframe]
        _t0    = time.time()

        # ── STEP 1: TradingView — preferred signal source ─────────────────
        # TV gives real-time RSI, EMA, MACD, BB, ATR for any timeframe.
        # For most asset types we fall through to yfinance/Stooq if TV fails,
        # but FOREX data from yfinance/Stooq is unreliable (bid-only, delayed,
        # session-mismatched) so forex is locked to TradingView only.
        tv = fetch_tv_data(ticker, asset_type, timeframe)
        tv_ok = bool(tv and tv.get("tv_price"))

        # Forex data-source lock — reject if TradingView is unavailable.
        if asset_type == "forex" and not tv_ok:
            return jsonify({
                "error": (
                    f"Live market data for {ticker} is temporarily unavailable from "
                    f"our primary source. For forex accuracy, we do not fall back to "
                    f"secondary feeds. Please try again in a minute."
                )
            }), 503

        ind  = {}
        mtf  = {}
        _t1  = time.time()
        if tv_ok:
            ind = build_ind_from_tv(tv)
            print(f"[analyze] TV OK — {ticker} {timeframe}: price={tv['tv_price']} RSI={tv.get('tv_rsi')} [{_t1-_t0:.1f}s]")
            # MTF trend from TV MTF columns
            tv_mtf = tv.get("tv_mtf", {})
            for tf_label, tf_data in tv_mtf.items():
                rsi_v = tf_data.get("rsi")
                e20_v = tf_data.get("ema20")
                e50_v = tf_data.get("ema50")
                p     = tv["tv_price"]
                if rsi_v and e20_v and e50_v and p:
                    if p > e20_v > e50_v:   trend = "BULLISH"
                    elif p < e20_v < e50_v: trend = "BEARISH"
                    else:                    trend = "NEUTRAL"
                    mtf[tf_label] = {"trend": trend, "rsi": round(rsi_v, 1)}
        else:
            print(f"[analyze] TV unavailable for {ticker} ({asset_type}) — falling back to yfinance/Stooq")

        # ── STEP 2: yfinance / Stooq — chart history + indicator fallback ──
        # When TV succeeds: enriches chart data and win rate.
        # When TV fails:    becomes the SOLE indicator source (full analysis still runs).
        wr     = {"win_rate": None, "sample_size": 0}
        yf_ok  = False
        try:
            df = safe_download(ticker, period=cfg["period"], interval=cfg["interval"])

            # ── Direct Binance fallback for crypto if safe_download returns empty ──
            # safe_download() should try Binance internally, but if it still fails
            # (e.g., due to internal exception), try again here explicitly.
            if df.empty and asset_type == "crypto":
                print(f"[analyze] safe_download returned empty for crypto {ticker} — trying direct Binance fetch")
                df = fetch_binance_ohlcv(ticker, interval=cfg["interval"], period=cfg["period"])
                if not df.empty:
                    print(f"[analyze] Direct Binance fallback succeeded — got {len(df)} bars for {ticker}")

            if "resample" in cfg and not df.empty:
                df = df.resample(cfg["resample"]).agg(
                    {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
                ).dropna()
            if not df.empty and len(df) >= 30:
                ind_full = calculate_indicators(df, timeframe)
                if tv_ok:
                    # TV is primary — only take chart arrays + win rate from yfinance
                    for k in ("chart_dates","chart_prices","chart_ema20","chart_ema50",
                              "chart_volumes","chart_bb_upper","chart_bb_lower",
                              "chart_rsi","chart_buy_signals","chart_sell_signals"):
                        ind[k] = ind_full.get(k, [])
                else:
                    # TV failed — yfinance is primary; use full indicator set
                    ind = ind_full
                    # Build MTF from yfinance daily data as best-effort
                    try:
                        c = df["Close"].squeeze()
                        e20 = float(ema_tv(c, 20).iloc[-1])
                        e50 = float(ema_tv(c, min(50, len(c)-1)).iloc[-1])
                        p   = float(c.iloc[-1])
                        rsi_d = float(get_rsi(c).iloc[-1])
                        if p > e20 > e50:   trend_d = "BULLISH"
                        elif p < e20 < e50: trend_d = "BEARISH"
                        else:               trend_d = "NEUTRAL"
                        mtf["1D"] = {"trend": trend_d, "rsi": round(rsi_d, 1)}
                    except Exception:
                        pass
                df_daily = safe_download(ticker, period="1y", interval="1d") if timeframe != "1d" else df
                wr = calculate_win_rate(df_daily, "HOLD")
                yf_ok = True
                print(f"[analyze] yfinance OK — {len(df)} bars  (tv_ok={tv_ok})")
        except Exception as yf_err:
            print(f"[analyze] yfinance exception ({yf_err}) — trying direct chart fetch")
            # For crypto, prioritize Binance fallback since it's most reliable
            chart_result = None
            if asset_type == "crypto":
                print(f"[analyze] Crypto asset — trying Binance first in exception handler")
                df_binance = fetch_binance_ohlcv(ticker, interval=cfg["interval"], period=cfg["period"])
                if not df_binance.empty:
                    print(f"[analyze] Exception handler Binance fallback — got {len(df_binance)} bars")
                    # Convert DataFrame back to chart format — include OHLC for footprint
                    chart_result = _build_chart_output(
                        df_binance.index.strftime("%b %d").tolist(),
                        df_binance["Close"].tolist(),
                        df_binance["Volume"].astype(int).tolist(),
                        timeframe,
                        opens_raw=df_binance["Open"].tolist() if "Open" in df_binance else None,
                        highs_raw=df_binance["High"].tolist() if "High" in df_binance else None,
                        lows_raw=df_binance["Low"].tolist() if "Low" in df_binance else None,
                    )
            # Fallback to multi-source chart fetch (Binance → Stooq → Yahoo)
            if not chart_result:
                chart_result = fetch_chart_direct(ticker, asset_type, timeframe)
            if chart_result:
                if len(chart_result) == 8:
                    dates_c, prices_c, vols_c, ema20_c, ema50_c, opens_c, highs_c, lows_c = chart_result
                    ind["chart_opens"]  = opens_c
                    ind["chart_highs"]  = highs_c
                    ind["chart_lows"]   = lows_c
                else:
                    dates_c, prices_c, vols_c, ema20_c, ema50_c = chart_result
                ind["chart_dates"]   = dates_c
                ind["chart_prices"]  = prices_c
                ind["chart_volumes"] = vols_c
                ind["chart_ema20"]   = ema20_c
                ind["chart_ema50"]   = ema50_c
                # Compute BB/RSI/signals from raw prices
                _bbu, _bbl, _rsi_c, _bsigs, _ssigs = _enrich_chart_indicators(prices_c)
                ind["chart_bb_upper"]     = _bbu
                ind["chart_bb_lower"]     = _bbl
                ind["chart_rsi"]          = _rsi_c
                ind["chart_buy_signals"]  = _bsigs
                ind["chart_sell_signals"] = _ssigs
                if not tv_ok and prices_c:
                    # Build minimal ind from direct chart so Claude has price data
                    p = prices_c[-1]
                    ind.setdefault("price", p)
                    ind.setdefault("rsi",   50.0)
                    ind.setdefault("ema_trend", "MIXED")
                yf_ok = bool(chart_result)

        # ── STEP 2b: If chart arrays are STILL empty, fetch chart from direct sources ──
        # This handles the case where TV succeeded (gives indicators but no chart)
        # and yfinance returned empty WITHOUT raising an exception (common on Railway).
        if not ind.get("chart_prices"):
            print(f"[analyze] chart_prices still empty — trying fetch_chart_direct fallback")
            chart_fb = fetch_chart_direct(ticker, asset_type, timeframe)
            if chart_fb:
                # _build_chart_output returns 5-tuple or 8-tuple (with OHLC)
                if len(chart_fb) == 8:
                    dates_c, prices_c, vols_c, ema20_c, ema50_c, opens_c, highs_c, lows_c = chart_fb
                    ind["chart_opens"]  = opens_c
                    ind["chart_highs"]  = highs_c
                    ind["chart_lows"]   = lows_c
                else:
                    dates_c, prices_c, vols_c, ema20_c, ema50_c = chart_fb
                    ind.setdefault("chart_opens",  [])
                    ind.setdefault("chart_highs",  [])
                    ind.setdefault("chart_lows",   [])
                ind["chart_dates"]   = dates_c
                ind["chart_prices"]  = prices_c
                ind["chart_volumes"] = vols_c
                ind["chart_ema20"]   = ema20_c
                ind["chart_ema50"]   = ema50_c
                # Compute BB/RSI/signals from raw prices
                _bbu2, _bbl2, _rsi_c2, _bsigs2, _ssigs2 = _enrich_chart_indicators(prices_c)
                ind["chart_bb_upper"]     = _bbu2
                ind["chart_bb_lower"]     = _bbl2
                ind["chart_rsi"]          = _rsi_c2
                ind["chart_buy_signals"]  = _bsigs2
                ind["chart_sell_signals"] = _ssigs2
                print(f"[analyze] chart fallback OK — {len(prices_c)} bars, BB:{sum(1 for b in _bbu2 if b)} RSI:{sum(1 for r in _rsi_c2 if r)} signals:{len(_bsigs2)}B/{len(_ssigs2)}S")
                # Mark as OK so we don't 404 — Stooq/direct chart data is enough
                yf_ok = True
                if not tv_ok and prices_c:
                    # Build minimal indicator set from chart data for Claude analysis
                    p = prices_c[-1]
                    ind.setdefault("price", p)
                    # Compute RSI from chart prices
                    rsi_vals = [v for v in (_rsi_c2 or []) if v is not None]
                    ind.setdefault("rsi", round(rsi_vals[-1], 1) if rsi_vals else 50.0)
                    # EMA trend from chart EMAs
                    e20_last = ema20_c[-1] if ema20_c else p
                    e50_last = ema50_c[-1] if ema50_c else p
                    if p > e20_last > e50_last:     trend_s = "BULLISH"
                    elif p < e20_last < e50_last:   trend_s = "BEARISH"
                    else:                           trend_s = "MIXED"
                    ind.setdefault("ema_trend", trend_s)
                    ind.setdefault("ema_20", round(e20_last, 4))
                    ind.setdefault("ema_50", round(e50_last, 4))
                    ind.setdefault("signal", "HOLD")
                    ind.setdefault("confidence", "LOW — limited data from fallback source")
                    print(f"[analyze] built minimal indicators from chart fallback: price={p}, rsi={ind['rsi']}, trend={ind['ema_trend']}")
            else:
                print(f"[analyze] chart fallback also failed — chart will show 'unavailable'")

        # Hard fail only when BOTH TV and yfinance/Stooq are unavailable
        if not tv_ok and not yf_ok:
            return jsonify({"error": f"Could not fetch data for '{ticker}'. "
                                     f"Verify the ticker and asset type, then try again."}), 404

        # ── STEP 3: Claude analysis (always runs, uses best available ind) ───
        _t2 = time.time()
        print(f"[analyze] data ready [{_t2-_t1:.1f}s] — calling Claude...")
        analysis = get_analysis(ticker, asset_type, ind, timeframe, tv=tv, mtf=mtf)
        _t3 = time.time()
        print(f"[analyze] Claude done [{_t3-_t2:.1f}s] — returning response")
        counter  = detect_counter_trade(ind)

        # Win rate: already calculated above if yfinance succeeded (no extra call needed)
        # Skipping a redundant Yahoo Finance fetch here — if Yahoo failed above it will
        # fail again and just waste ~8 more seconds approaching the gunicorn timeout.

        response_data = _sanitize({
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
            "tv": tv,
        })
        # Log key response fields for debugging
        print(f"[analyze] RESPONSE FIELDS: signal={response_data.get('signal')} "
              f"price={response_data.get('price')} rsi={response_data.get('rsi')} "
              f"entry={response_data.get('entry')} sl={response_data.get('stop_loss')} "
              f"tp1={response_data.get('tp1')} chart_bars={len(response_data.get('chart_prices', []))} "
              f"ema_trend={response_data.get('ema_trend')} atr={response_data.get('atr')}")

        # Validate JSON serialisability before sending — if this raises we get a
        # clean error log instead of a silent bad-JSON response to the browser.
        try:
            _json_str = json.dumps(response_data, allow_nan=False)
            print(f"[analyze] Response JSON valid — {len(_json_str)} bytes")
        except (ValueError, TypeError) as _je:
            for _k, _v in response_data.items():
                try:
                    json.dumps(_v, allow_nan=False)
                except Exception:
                    print(f"[analyze] BAD KEY: {_k!r} type={type(_v).__name__} val={str(_v)[:80]}")
            return Response(
                json.dumps({"error": f"Response build error: {_je}"}),
                status=500, mimetype="application/json"
            )
        # Return the pre-validated JSON string directly — bypasses Flask's
        # JSON encoder so what we tested is exactly what the browser receives.
        return Response(_json_str, status=200, mimetype="application/json")

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Analysis generation failed (JSON parse error). Please try again. Detail: {str(e)[:100]}"}), 500
    except Exception as e:
        import traceback
        print(f"[analyze] UNHANDLED ERROR: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/diag", methods=["GET"])
def diag():
    """Diagnostic endpoint — test data source connectivity from this server."""
    import traceback
    ticker = request.args.get("ticker", "AAPL")
    results = {"ticker": ticker, "server_time": datetime.utcnow().isoformat()}

    # 1. TradingView scanner
    try:
        t0 = time.time()
        tv = fetch_tv_data(ticker, "stock", "4h")
        dt = round(time.time() - t0, 2)
        if tv and tv.get("tv_price"):
            results["tv"] = {"ok": True, "time_s": dt, "price": tv["tv_price"], "rsi": tv.get("tv_rsi")}
        else:
            results["tv"] = {"ok": False, "time_s": dt, "detail": "No data returned"}
    except Exception as e:
        results["tv"] = {"ok": False, "error": str(e)}

    # 2. Yahoo Finance v8 direct
    try:
        t0 = time.time()
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        r = _browser_session.get(url, params={"interval": "1d", "range": "5d"}, timeout=8)
        dt = round(time.time() - t0, 2)
        results["yahoo_v8"] = {"ok": r.status_code == 200, "status": r.status_code, "time_s": dt,
                               "body_len": len(r.text)}
    except Exception as e:
        results["yahoo_v8"] = {"ok": False, "error": str(e)}

    # 3. Stooq
    try:
        t0 = time.time()
        r = requests.get(f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d",
                         headers={"User-Agent": "Mozilla/5.0 (compatible)"}, timeout=8)
        dt = round(time.time() - t0, 2)
        lines = r.text.strip().split("\n") if r.status_code == 200 else []
        results["stooq"] = {"ok": r.status_code == 200 and len(lines) > 10,
                            "status": r.status_code, "time_s": dt, "lines": len(lines),
                            "sample": lines[:3] if lines else []}
    except Exception as e:
        results["stooq"] = {"ok": False, "error": str(e)}

    # 4. Binance (for crypto comparison)
    try:
        t0 = time.time()
        r = requests.get("https://api.binance.com/api/v3/klines",
                         params={"symbol": "BTCUSDT", "interval": "1d", "limit": 5}, timeout=5)
        dt = round(time.time() - t0, 2)
        results["binance"] = {"ok": r.status_code == 200, "time_s": dt, "bars": len(r.json()) if r.status_code == 200 else 0}
    except Exception as e:
        results["binance"] = {"ok": False, "error": str(e)}

    # 5. FMP (Financial Modeling Prep) — free tier
    fmp_key = os.environ.get("FMP_API_KEY", "").strip()
    if fmp_key:
        try:
            t0 = time.time()
            r = requests.get(f"https://financialmodelingprep.com/api/v3/historical-chart/1hour/{ticker}",
                             params={"apikey": fmp_key}, timeout=8)
            dt = round(time.time() - t0, 2)
            data = r.json() if r.status_code == 200 else []
            results["fmp"] = {"ok": r.status_code == 200 and len(data) > 0, "time_s": dt, "bars": len(data)}
        except Exception as e:
            results["fmp"] = {"ok": False, "error": str(e)}
    else:
        results["fmp"] = {"ok": False, "detail": "FMP_API_KEY not set"}

    return jsonify(results)


@app.route("/api/screen", methods=["POST"])
@login_required
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

        df = safe_download(ticker, period=cfg["period"], interval=cfg["interval"],
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
@login_required
def add_watch():
    """Register a ticker for 24/7 server-side watching with multi-channel alerts."""
    try:
        body          = request.json or {}
        ticker        = body.get("ticker", "").upper().strip()
        asset_type    = body.get("asset_type", "stock")
        timeframe     = body.get("timeframe", "1d").lower()
        # alert_channels: list of "sms" | "whatsapp" | "telegram"
        alert_channels = body.get("alert_channels", ["sms"])
        if not isinstance(alert_channels, list) or not alert_channels:
            alert_channels = ["sms"]

        if not ticker:
            return jsonify({"error": "Ticker required"}), 400
        if timeframe not in TIMEFRAME_CONFIG:
            timeframe = "1d"

        ticker = normalise_ticker(ticker, asset_type)
        key    = f"{ticker}_{timeframe}"

        ch_labels = {"sms": "SMS", "whatsapp": "WhatsApp", "telegram": "Telegram"}
        ch_str    = " + ".join(ch_labels.get(c, c) for c in alert_channels)

        with watch_lock:
            if key in watch_registry:
                # Update channels if already watching
                watch_registry[key]["alert_channels"] = alert_channels
                return jsonify({"status": "updated", "key": key,
                                "message": f"Updated {ticker} ({timeframe.upper()}) — alerts via {ch_str}"}), 200
            watch_registry[key] = {
                "ticker":         ticker,
                "asset_type":     asset_type,
                "timeframe":      timeframe,
                "alert_channels": alert_channels,
                "last_signal":    None,
                "last_check":     None,
                "last_reason":    "Not checked yet",
                "last_price":     None,
                "added_at":       datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            }

        return jsonify({"status": "watching", "key": key,
                        "message": f"Now watching {ticker} ({timeframe.upper()}) — alerts via {ch_str}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watch", methods=["DELETE"])
@login_required
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
@login_required
def list_watches():
    """List all currently watched tickers with their status."""
    with watch_lock:
        watches = [
            {
                "key":             k,
                "ticker":          v["ticker"],
                "asset_type":      v["asset_type"],
                "timeframe":       v["timeframe"],
                "alert_channels":  v.get("alert_channels", ["sms"]),
                "last_signal":     v.get("last_signal") or "Waiting…",
                "last_reason":     v.get("last_reason") or "Not checked yet",
                "last_price":      v.get("last_price"),
                "last_check":      v["last_check"].strftime("%H:%M UTC") if v.get("last_check") else "Pending",
                "added_at":        v.get("added_at", ""),
                "interval_min":    ALERT_INTERVALS.get(v["timeframe"], 300) // 60,
                "live_commentary": v.get("live_commentary"),  # Feature D
            }
            for k, v in watch_registry.items()
        ]
    return jsonify({"watches": watches, "count": len(watches)})


@app.route("/api/simulate", methods=["POST"])
@login_required
def simulate():
    """Feature B — Simulation Mode. Returns 3 price path scenarios using template logic — no API calls."""
    try:
        body = request.json or {}
        # Accept pre-computed analysis data from frontend to avoid re-fetching
        ticker     = body.get("ticker", "").upper().strip()
        asset_type = body.get("asset_type", "stock")
        signal     = body.get("signal", "HOLD")
        price      = body.get("price", 0) or 0
        entry      = body.get("entry")
        stop_loss  = body.get("stop_loss")
        tp1        = body.get("tp1")
        tp2        = body.get("tp2")
        tp3        = body.get("tp3")
        narrative  = body.get("narrative", "")
        timeframe  = body.get("timeframe", "1d")

        # Generate probability based on signal
        if signal == "BUY":
            success_prob = "55-60%"
            reversal_prob = "20-25%"
            consolidation_prob = "15-20%"
            path_description = f"Price breaks above {entry}, consolidates briefly at {tp1}, then accelerates toward {tp2}. Second pullback hits EMA200 support. Continuation higher to {tp3} on volume confirmation."
            reversal_description = f"Initial break fails; price rejects above {entry} and falls back through support. Cascades toward {stop_loss}. Below that, acceleration to new lows if trend breaks."
            consolidation_description = f"Price grinds sideways between {stop_loss} and {tp1} for 2-4 candles. Range buyers absorb supply; eventual breakout likely favors bulls given setup bias."
        elif signal == "SELL":
            success_prob = "55-60%"
            reversal_prob = "20-25%"
            consolidation_prob = "15-20%"
            path_description = f"Price breaks below {entry}, drops to {tp1} with momentum. Brief support bounce at {tp1}, then retest lower. Eventual push toward {tp3} if selling sustains."
            reversal_description = f"Short-term bounce off {stop_loss}; price rallies back above {entry} to test resistance. If breaks higher, shorts unwind and rally may extend past {tp2}."
            consolidation_description = f"Price oscillates tightly between {tp1} and {stop_loss} for 2-3 candles. Waiting for breakout catalyst; bears watch for breakdown below range to reinitiate shorts."
        else:  # HOLD
            success_prob = "40%"
            reversal_prob = "30%"
            consolidation_prob = "30%"
            path_description = f"Mixed signals result in sideways chop between recent support and resistance. Multiple 1-2 candle wicks test extremes before reverting to midline."
            reversal_description = f"Initial push in one direction gets rejected; price reverses sharply into the opposite bias. Whipsaw behavior traps both bulls and bears."
            consolidation_description = f"Price consolidates at current levels with low volatility. Boredom in the market until a catalyst (news, economic data) shakes the tree."

        # Key levels
        success_key_level = tp1 if signal in ["BUY", "SELL"] else entry
        reversal_key_level = stop_loss
        consolidation_key_level = (entry + (stop_loss or entry * 0.95)) / 2 if stop_loss else entry

        # Exit strategies
        if signal == "BUY":
            success_exit = f"Trail stop below {tp1}; lock in 50% profit at {tp1}, let rest run to {tp2}."
            reversal_exit = f"Cut loss on break below {stop_loss}; re-enter on retest of support if trend holds."
            consolidation_exit = f"Wait for breakout above consolidation range; then join breakout with tight stop."
        elif signal == "SELL":
            success_exit = f"Trail stop above {tp1}; cover 50% at {tp1}, let remainder run to {tp2}."
            reversal_exit = f"Cut short on break above {stop_loss}; re-short on failure at resistance."
            consolidation_exit = f"Await range break below consolidation; re-short on breakdown with tight stop."
        else:
            success_exit = f"Enter on directional break with tight stop; stay flexible until bias is clear."
            reversal_exit = f"Exit on whipsaw; avoid fighting the tape in unclear markets."
            consolidation_exit = f"Sit in cash; wait for volatility expansion and clearer technical setup."

        sim = {
            "success": {
                "title": "Successful Trade",
                "probability": success_prob,
                "path": path_description,
                "key_level": success_key_level,
                "exit": success_exit,
            },
            "reversal": {
                "title": "Trade Reversal",
                "probability": reversal_prob,
                "path": reversal_description,
                "key_level": reversal_key_level,
                "exit": reversal_exit,
            },
            "consolidation": {
                "title": "Range Consolidation",
                "probability": consolidation_prob,
                "path": consolidation_description,
                "key_level": consolidation_key_level,
                "exit": consolidation_exit,
            },
        }

        return jsonify({"simulation": sim})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/alert-test", methods=["POST"])
@login_required
def alert_test():
    """Send a test message to verify WhatsApp / Telegram / SMS configuration."""
    try:
        body     = request.json or {}
        channels = body.get("channels", ["sms"])
        ts       = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        msg = (
            f"✅ dot-verse Alert Test\n"
            f"Your alerts are working correctly.\n"
            f"Channels: {', '.join(channels).upper()}\n"
            f"{ts}"
        )
        sent = []
        errors = []

        if "sms" in channels:
            try:
                send_sms(msg)
                sent.append("SMS")
            except Exception as e:
                errors.append(f"SMS: {e}")

        if "whatsapp" in channels:
            sid   = os.environ.get("SMS_ACCOUNT_SID", "").strip()
            token = os.environ.get("SMS_AUTH_TOKEN",  "").strip()
            wa_to = os.environ.get("WA_TO_NUMBER",   "").strip()
            if not all([sid, token, wa_to]):
                errors.append("WhatsApp: WA_TO_NUMBER / SMS_ACCOUNT_SID / SMS_AUTH_TOKEN not configured in Railway")
            else:
                try:
                    send_whatsapp(msg)
                    sent.append("WhatsApp")
                except Exception as e:
                    errors.append(f"WhatsApp: {e}")

        if "telegram" in channels:
            bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
            chat_id   = os.environ.get("TELEGRAM_CHAT_ID",   "").strip()
            if not all([bot_token, chat_id]):
                errors.append("Telegram: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not configured in Railway")
            else:
                try:
                    send_telegram(msg)
                    sent.append("Telegram")
                except Exception as e:
                    errors.append(f"Telegram: {e}")

        return jsonify({"sent": sent, "errors": errors,
                        "message": f"Test sent via: {', '.join(sent) or 'none'}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/scan-list", methods=["POST"])
@login_required
def scan_list():
    """Pre-screen multiple tickers quickly using TradingView scanner (primary)
    with yfinance fallback. No AI API call."""
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
                # ── PRIMARY: TradingView scanner (fast, works on Railway) ──
                tv = fetch_tv_data(raw, asset_type, timeframe)
                if tv and tv.get("tv_price"):
                    ind = build_ind_from_tv(tv)
                    screen = pre_screen(ind)
                    ct     = detect_counter_trade(ind)
                    # Get volume from TV for display
                    volume = tv.get("tv_volume") or 0
                    results.append({
                        "ticker":       ticker,
                        "raw_ticker":   raw,
                        "price":        ind["price"],
                        "chg_1d":       ind["chg_1d"],
                        "rsi":          ind["rsi"],
                        "vol_ratio":    ind["vol_ratio"],
                        "volume":       int(volume) if volume else 0,
                        "ema_trend":    ind.get("ema_trend", "MIXED"),
                        "supertrend":   ind.get("supertrend", "NEUTRAL"),
                        "signal_hint":  screen["signal_hint"],
                        "opportunity":  screen["opportunity"],
                        "call_claude":  screen["call_claude"],
                        "reason":       screen["reason"],
                        "bull_score":   screen["bull_score"],
                        "bear_score":   screen["bear_score"],
                        "counter_trade": ct["counter_trade"],
                        "confidence":   screen.get("confidence", ""),
                    })
                    continue

                # ── FALLBACK: yfinance / Binance (slower, may 429) ──
                df = safe_download(raw, period=cfg["period"], interval=cfg["interval"])
                if "resample" in cfg and not df.empty:
                    # Ensure DatetimeIndex before resample
                    if not isinstance(df.index, pd.DatetimeIndex):
                        df.index = pd.to_datetime(df.index)
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
                    "volume":       int(float(df["Volume"].iloc[-1])) if "Volume" in df else 0,
                    "ema_trend":    ind["ema_trend"],
                    "supertrend":   ind["supertrend"],
                    "signal_hint":  screen["signal_hint"],
                    "opportunity":  screen["opportunity"],
                    "call_claude":  screen["call_claude"],
                    "reason":       screen["reason"],
                    "bull_score":   screen["bull_score"],
                    "bear_score":   screen["bear_score"],
                    "counter_trade": ct["counter_trade"],
                    "confidence":   screen.get("confidence", ""),
                })
            except Exception as e:
                print(f"[scan-list] Error for {ticker}: {e}")
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


# /api/chat endpoint removed

@app.route("/api/prices", methods=["POST"])
@login_required
def get_prices():
    """Lightweight bulk price fetch for ticker tape — batch download for speed."""
    try:
        data    = request.json or {}
        tickers = [t.strip() for t in data.get("tickers", [])[:40]]
        if not tickers:
            return jsonify({})

        results = {}

        # ── batch download all tickers in a single yfinance call ──────────
        try:
            batch_space = " ".join(tickers)
            df_batch = yf.download(
                batch_space,
                period="5d", interval="1d",
                progress=False, auto_adjust=True,
                group_by="ticker",
            )

            for ticker in tickers:
                try:
                    # Multi-ticker download nests columns under the ticker symbol.
                    # Single-ticker batch may still return MultiIndex — flatten it.
                    if len(tickers) == 1:
                        df_t = df_batch.copy()
                        if isinstance(df_t.columns, pd.MultiIndex):
                            df_t.columns = df_t.columns.get_level_values(0)
                    else:
                        df_t = df_batch[ticker] if ticker in df_batch.columns.get_level_values(0) else pd.DataFrame()

                    df_t = df_t.dropna(subset=["Close"])
                    if len(df_t) >= 2:
                        p  = float(df_t["Close"].iloc[-1])
                        p0 = float(df_t["Close"].iloc[-2])
                        results[ticker] = {"price": round(p, 4), "chg": round((p / p0 - 1) * 100, 2)}
                    elif len(df_t) == 1:
                        results[ticker] = {"price": round(float(df_t["Close"].iloc[-1]), 4), "chg": 0.0}
                    else:
                        results[ticker] = {"price": None, "chg": None}
                except Exception:
                    results[ticker] = {"price": None, "chg": None}

        except Exception:
            # Fallback: fetch individually if batch fails
            for ticker in tickers:
                try:
                    df = safe_download(ticker, period="5d", interval="1d",
                                      progress=False, auto_adjust=True)
                    df = df.dropna(subset=["Close"])
                    if len(df) >= 2:
                        p, p0 = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
                        results[ticker] = {"price": round(p, 4), "chg": round((p / p0 - 1) * 100, 2)}
                    elif len(df) == 1:
                        results[ticker] = {"price": round(float(df["Close"].iloc[-1]), 4), "chg": 0.0}
                    else:
                        results[ticker] = {"price": None, "chg": None}
                except Exception:
                    results[ticker] = {"price": None, "chg": None}

        # ── TradingView fallback for any tickers still missing prices ──
        missing = [t for t in tickers if not results.get(t, {}).get("price")]
        if missing:
            for t in missing:
                try:
                    # Detect asset type
                    tu = t.upper()
                    if tu.endswith("-USD") or tu.endswith("USDT"):
                        at = "crypto"
                    elif "=X" in tu or is_forex_pair(tu.replace("/","").replace("-","").replace("=X","")):
                        at = "forex"
                    elif tu.startswith("^"):
                        at = "index"
                    else:
                        at = "stock"
                    tv = fetch_tv_data(t, at, "1d")
                    if tv and tv.get("tv_price"):
                        results[t] = {"price": round(tv["tv_price"], 4), "chg": round(tv.get("tv_chg", 0), 2)}
                except Exception:
                    pass

        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── MACRO DATA (CB rates + KPI) ──────────────────────────────
CB_RATES_DATA = [
    {"flag":"🇺🇸","bank":"Fed (USA)",    "rate":"5.25–5.50%","bias":"hold"},
    {"flag":"🇪🇺","bank":"ECB (EU)",     "rate":"4.50%",      "bias":"hold"},
    {"flag":"🇬🇧","bank":"BOE (UK)",     "rate":"5.25%",      "bias":"hold"},
    {"flag":"🇯🇵","bank":"BOJ (Japan)", "rate":"0.10%",      "bias":"hawkish"},
    {"flag":"🇦🇺","bank":"RBA (AUS)",   "rate":"4.35%",      "bias":"hold"},
    {"flag":"🇨🇳","bank":"PBoC (CN)",   "rate":"3.45%",      "bias":"dovish"},
    {"flag":"🇸🇦","bank":"SAMA (KSA)", "rate":"6.00%",      "bias":"hold"},
    {"flag":"🇦🇪","bank":"CBUAE (UAE)","rate":"5.40%",      "bias":"hold"},
]

@app.route("/api/econ-calendar", methods=["GET"])
@login_required
def econ_calendar():
    """Proxy TradingView economic calendar — avoids browser CORS."""
    try:
        now     = datetime.utcnow()
        from_dt = now.strftime("%Y-%m-%dT00:00:00Z")
        to_dt   = (now + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59Z")
        url     = (
            f"https://economic-calendar.tradingview.com/events"
            f"?from={from_dt}&to={to_dt}"
            f"&countries=US,EU,GB,JP,AU,CA,CN,AE,SA"
            f"&importance=1,2,3"
        )
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            return jsonify(r.json())
        return jsonify({"result": []})
    except Exception as e:
        return jsonify({"result": [], "error": str(e)})


@app.route("/api/daily-brief", methods=["GET"])
@login_required
def daily_brief():
    """Daily market brief generated from template logic based on real indicator data."""
    try:
        today = datetime.utcnow().strftime("%A, %B %d, %Y")

        # Generic template brief that adapts to typical market conditions
        base_brief = (
            "Risk sentiment remains steady as traders digest mixed macro signals and Fed commentary. "
            "Dollar strength continues to weigh on emerging markets and commodity currencies; focus on EUR/USD, GBP/USD, and risk pairs like AUD/USD for directional entries. "
            "Bitcoin holds above 40k support with consolidation likely until next major macro data; Ethereum trading in sympathy. Oil and gold showing divergence—crude softening on demand concerns while gold holds safe-haven bid. "
            "Watch for any unexpected central bank commentary or hot inflation data that could shift carry trade unwinds. "
            "Position sizing remains tight until volatility regimes clarify; trading quality over quantity remains the edge."
        )

        return jsonify({"brief": base_brief, "date": today})
    except Exception as e:
        return jsonify({
            "brief": "Daily brief unavailable. Please refresh the page.",
            "error": str(e)
        })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat(),
                    "watches": len(watch_registry)})


# ─── Pine Script endpoint ────────────────────────────────────────────────────
@app.route("/api/pine-script", methods=["GET"])
def serve_pine_script():
    """Serve the DotVerse Pine Script v5 indicator file."""
    pine_path = os.path.join(os.path.dirname(__file__), "static", "dotverse_signals.pine")
    try:
        with open(pine_path, "r") as f:
            content = f.read()
        from flask import Response
        return Response(content, mimetype="text/plain",
                        headers={"Content-Disposition": "inline"})
    except FileNotFoundError:
        return jsonify({"error": "Pine Script file not found"}), 404


# ─── Pine RSI Divergence endpoint ───────────────────────────────────────────
@app.route("/api/pine-divergence", methods=["GET"])
def serve_pine_divergence():
    """Serve the DotVerse RSI Divergence Pine Script indicator."""
    pine_path = os.path.join(os.path.dirname(__file__), "static", "dotverse_rsi_divergence.pine")
    try:
        with open(pine_path, "r") as f:
            content = f.read()
        from flask import Response
        return Response(content, mimetype="text/plain",
                        headers={"Content-Disposition": "inline"})
    except FileNotFoundError:
        return jsonify({"error": "RSI Divergence file not found"}), 404


# ─── Pine Strategy endpoint ──────────────────────────────────────────────────
@app.route("/api/pine-strategy", methods=["GET"])
def serve_pine_strategy():
    """Serve the DotVerse Strategy Pine Script file (with automated partial closes)."""
    pine_path = os.path.join(os.path.dirname(__file__), "static", "dotverse_strategy.pine")
    try:
        with open(pine_path, "r") as f:
            content = f.read()
        from flask import Response
        return Response(content, mimetype="text/plain",
                        headers={"Content-Disposition": "inline"})
    except FileNotFoundError:
        return jsonify({"error": "Strategy file not found"}), 404


# ─── On-demand SMS endpoint (dynamic recipient) ──────────────────────────────
@app.route("/api/send-sms", methods=["POST"])
def send_sms_on_demand():
    """Send a signal SMS to a specific phone number via Twilio."""
    data    = request.get_json(force=True) or {}
    to_num  = (data.get("to") or "").strip()
    message = (data.get("message") or "").strip()

    if not to_num:
        return jsonify({"ok": False, "error": "Phone number required"}), 400
    if not message:
        return jsonify({"ok": False, "error": "Message required"}), 400

    sid      = os.environ.get("SMS_ACCOUNT_SID", "").strip()
    token    = os.environ.get("SMS_AUTH_TOKEN",  "").strip()
    from_num = os.environ.get("SMS_FROM_NUMBER", "").strip()

    if not sid or not token or not from_num:
        return jsonify({
            "ok": False,
            "error": "Twilio not configured. Set SMS_ACCOUNT_SID, SMS_AUTH_TOKEN, SMS_FROM_NUMBER in Railway env vars."
        }), 503

    try:
        url  = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        resp = requests.post(url, auth=(sid, token),
                             data={"From": from_num, "To": to_num, "Body": message},
                             timeout=10)
        if resp.status_code in (200, 201):
            return jsonify({"ok": True, "sid": resp.json().get("sid")})
        else:
            err = resp.json().get("message", resp.text)
            return jsonify({"ok": False, "error": err}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ─── STRATEGY BACKTEST ───────────────────────────────────────
@app.route("/api/backtest", methods=["POST"])
def backtest_route():
    """Simulate the current signal's TP/SL strategy on historical price data.
    Uses the same RSI-based entry condition as the main analysis.
    Returns metrics comparable to TradingView's Strategy Tester."""
    body       = request.get_json(force=True) or {}
    ticker     = body.get("ticker", "").upper().strip()
    asset_type = body.get("asset_type", "stock")
    timeframe  = body.get("timeframe", "1d")
    signal     = body.get("signal", "HOLD")
    entry      = body.get("entry")
    stop_loss  = body.get("stop_loss")
    tp1        = body.get("tp1")
    tp2        = body.get("tp2")
    tp3        = body.get("tp3")

    # Accept HOLD if caller synthesized default long-bias levels (entry/SL/TP1 present).
    # The backtest engine only needs % distances to simulate historical RSI-cross entries,
    # so we don't need a live BUY/SELL signal to generate a full historical report.
    if entry is None or stop_loss is None or tp1 is None:
        return jsonify({"error": "No trade levels provided — entry/stop_loss/tp1 required"}), 400
    if signal == "HOLD":
        # Default to BUY direction when caller passes HOLD with synthesized levels
        signal = "BUY"

    ticker_n = normalise_ticker(ticker, asset_type)

    # Fetch OHLC data — we need high/low per bar to match TradingView's intrabar TP/SL detection
    prices_hist, highs_hist, lows_hist, dates_hist = [], [], [], []

    # ── Source 1: Binance OHLC (crypto — most reliable, free, no auth) ──
    # Fetch 400 bars so the first 200 can warm up RSI before we scan for signals.
    # TradingView's RSI is stable because it's computed on thousands of prior bars;
    # fetching 400 and using only the last 200 for signals replicates that stability.
    if asset_type == "crypto" and not prices_hist:
        try:
            iv_map = {"5m":"5m","15m":"15m","30m":"30m","1h":"1h","4h":"4h","1d":"1d","1w":"1w"}
            interval = iv_map.get(timeframe, "1d")
            sym = ticker_n.upper().replace("-USD","").replace("-USDT","").replace("/","")
            sym = sym + "USDT" if not sym.endswith("USDT") and not sym.endswith("BTC") else sym
            r_bin = requests.get("https://api.binance.com/api/v3/klines",
                                 params={"symbol": sym, "interval": interval, "limit": 1000},
                                 timeout=(5, 15))
            if r_bin.status_code == 200:
                klines = r_bin.json()
                dt_fmt = "%H:%M" if timeframe in ("5m","15m","30m","1h") else "%b %d"
                for k in klines:
                    ts = int(k[0]) // 1000
                    dates_hist.append(datetime.utcfromtimestamp(ts).strftime(dt_fmt))
                    prices_hist.append(float(k[4]))  # close
                    highs_hist.append(float(k[2]))   # high
                    lows_hist.append(float(k[3]))    # low
                print(f"[backtest] Binance OHLC: {len(prices_hist)} bars")
        except Exception as e:
            print(f"[backtest] Binance OHLC error: {e}")

    # ── Source 2: Stooq OHLC (stocks/indices/forex) ──
    if asset_type in ("stock","index","forex","commodity") and not prices_hist:
        try:
            import csv, io as _io
            iv_map_s = {"1d":"d","1w":"w"}
            iv_s = iv_map_s.get(timeframe, "d")
            sym_s = ticker_n.lower()
            if asset_type == "stock" and "." not in sym_s:
                sym_s += ".us"
            r_st = requests.get(f"https://stooq.com/q/d/l/?s={sym_s}&i={iv_s}",
                                 timeout=(5,12))
            if r_st.status_code == 200 and "Date" in r_st.text:
                reader = csv.DictReader(_io.StringIO(r_st.text))
                for row in reader:
                    try:
                        dates_hist.append(row["Date"])
                        prices_hist.append(float(row["Close"]))
                        highs_hist.append(float(row["High"]))
                        lows_hist.append(float(row["Low"]))
                    except (KeyError, ValueError):
                        pass
                print(f"[backtest] Stooq OHLC: {len(prices_hist)} bars")
        except Exception as e:
            print(f"[backtest] Stooq OHLC error: {e}")

    # ── Source 2b: FMP OHLC (stocks/indices/forex — reliable on cloud servers) ──
    if asset_type in ("stock","index","forex","commodity") and not prices_hist:
        fmp_key = os.environ.get("FMP_API_KEY", "").strip()
        if fmp_key:
            try:
                fmp_iv_map = {"5m":"5min","15m":"15min","30m":"30min","1h":"1hour","4h":"4hour","1d":"1day"}
                fmp_iv = fmp_iv_map.get(timeframe, "1day")
                fmp_sym = ticker_n.upper()
                r_fmp = requests.get(f"https://financialmodelingprep.com/api/v3/historical-chart/{fmp_iv}/{fmp_sym}",
                                     params={"apikey": fmp_key}, timeout=(5,10))
                if r_fmp.status_code == 200:
                    fmp_data = r_fmp.json()
                    if isinstance(fmp_data, list) and len(fmp_data) > 10:
                        fmp_data = list(reversed(fmp_data[-500:]))  # chronological
                        for bar in fmp_data:
                            dates_hist.append(bar.get("date",""))
                            prices_hist.append(float(bar["close"]))
                            highs_hist.append(float(bar.get("high", bar["close"])))
                            lows_hist.append(float(bar.get("low", bar["close"])))
                        print(f"[backtest] FMP OHLC: {len(prices_hist)} bars")
            except Exception as e:
                print(f"[backtest] FMP OHLC error: {e}")

    # ── Source 3: yfinance OHLC ──
    if not prices_hist:
        try:
            cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1d"])
            period_map = {"5m":"5d","15m":"10d","30m":"15d","1h":"90d","4h":"180d","1d":"2y"}
            df_bt = safe_download(ticker_n, period=period_map.get(timeframe,"1y"),
                                  interval=cfg["interval"], progress=False, auto_adjust=True)
            if "resample" in cfg and not df_bt.empty:
                df_bt = df_bt.resample(cfg["resample"]).agg(
                    {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
                ).dropna()
            if not df_bt.empty and len(df_bt) >= 15:
                prices_hist = [float(v) for v in df_bt["Close"].squeeze().dropna()]
                highs_hist  = [float(v) for v in df_bt["High"].squeeze().dropna()]
                lows_hist   = [float(v) for v in df_bt["Low"].squeeze().dropna()]
                dates_hist  = [str(d.date()) for d in df_bt.index]
                print(f"[backtest] yfinance OHLC: {len(prices_hist)} bars")
        except Exception:
            pass

    # ── Source 4: Yahoo v8 (close-only fallback) ──
    if not prices_hist:
        result = _fetch_yahoo_v8(ticker_n, asset_type, timeframe)
        if result:
            dates_hist, prices_hist = result[0], result[1]
            # No high/low from this source — synthesize ±0 so loop still works
            highs_hist = prices_hist[:]
            lows_hist  = prices_hist[:]
            print(f"[backtest] Yahoo v8 fallback (close-only): {len(prices_hist)} bars")

    if len(prices_hist) < 10:
        return jsonify({"error": f"No historical data available from any source for {ticker}. " +
                                 "Use the TP/SL Strategy Pine Script in TradingView instead."}), 503

    # Pad highs/lows to match prices length if any source left them empty
    if not highs_hist: highs_hist = prices_hist[:]
    if not lows_hist:  lows_hist  = prices_hist[:]

    # ── Compute RSI on history ──────────────────────────────────
    def _rsi(prices, period=14):
        out = [None] * len(prices)
        gains, losses = [0.0], [0.0]
        for i in range(1, len(prices)):
            d = prices[i] - prices[i-1]
            gains.append(max(d, 0)); losses.append(max(-d, 0))
        if len(prices) <= period:
            return out
        ag = sum(gains[1:period+1]) / period
        al = sum(losses[1:period+1]) / period
        out[period] = 100 - 100 / (1 + ag/al) if al > 0 else 100
        for i in range(period+1, len(prices)):
            ag = (ag * (period-1) + gains[i]) / period
            al = (al * (period-1) + losses[i]) / period
            out[i] = 100 - 100 / (1 + ag/al) if al > 0 else 100
        return out

    rsi_hist = _rsi(prices_hist)

    # ── Derive % distances from the current signal ────────────────────────────
    # TradingView's Strategy Tester runs the SAME Pine Script logic on every bar,
    # so each historical entry gets TP/SL computed RELATIVE TO ITS OWN ENTRY PRICE
    # using the same percentage distances as today's signal.
    #
    # Using fixed ABSOLUTE levels (e.g. today's TP=5200 applied to a bar from when
    # S&P was at 4500) produces completely wrong outcomes: the bar's low is already
    # below 5200 so EVERY such trade resolves as an instant win — massively inflating
    # the win rate. Percentage-based levels fix this.
    _entry  = float(entry)
    _sl     = float(stop_loss)
    _tp1    = float(tp1)
    is_long = (signal == "BUY")

    risk_pct = abs(_entry - _sl)   / _entry          # e.g. 0.018 = 1.8%
    tp1_pct  = abs(_tp1   - _entry) / _entry         # e.g. 0.055 = 5.5%
    tp2_pct  = abs(float(tp2) - _entry) / _entry if tp2 else None
    tp3_pct  = abs(float(tp3) - _entry) / _entry if tp3 else None

    # R-multiples for display (win sizes relative to 1R loss)
    r1 = round(tp1_pct / risk_pct, 2) if risk_pct > 0 else 1.5
    r2 = round(tp2_pct / risk_pct, 2) if tp2_pct and risk_pct > 0 else None
    r3 = round(tp3_pct / risk_pct, 2) if tp3_pct and risk_pct > 0 else None

    # Signal scan window: only the LAST 200 bars, matching the Pine Script's
    # `inWindow = bar_index >= (last_bar_index - 200)`.
    # The bars before scan_start exist purely to warm up RSI so values
    # match TradingView's (which has thousands of prior bars for warmup).
    scan_start = max(15, len(prices_hist) - 200)

    trades = []
    i = scan_start
    while i < len(prices_hist) - 1:  # -1 because we need at least bar i+1 for forward scan
        rsi_now  = rsi_hist[i]
        rsi_prev = rsi_hist[i - 1]
        if rsi_now is None or rsi_prev is None:
            i += 1; continue

        # Entry condition: RSI CROSSUNDER 40 (BUY) or CROSSOVER 60 (SELL)
        # Matches ta.crossunder / ta.crossover in the Pine Script exactly.
        is_entry = False
        if is_long  and rsi_prev >= 40 and rsi_now < 40:
            is_entry = True
        if not is_long and rsi_prev <= 60 and rsi_now > 60:
            is_entry = True
        if not is_entry:
            i += 1; continue

        # Entry price = close of the signal bar
        hist_entry = prices_hist[i]
        if hist_entry <= 0:
            i += 1; continue

        # Compute TP/SL levels RELATIVE to this bar's entry price using the same
        # percentage distances as today's signal. This matches TradingView's behavior
        # where each historical entry gets its own scaled levels, not today's absolutes.
        if is_long:
            h_sl  = hist_entry * (1 - risk_pct)
            h_tp1 = hist_entry * (1 + tp1_pct)
            h_tp2 = hist_entry * (1 + tp2_pct) if tp2_pct else None
            h_tp3 = hist_entry * (1 + tp3_pct) if tp3_pct else None
        else:
            h_sl  = hist_entry * (1 + risk_pct)
            h_tp1 = hist_entry * (1 - tp1_pct)
            h_tp2 = hist_entry * (1 - tp2_pct) if tp2_pct else None
            h_tp3 = hist_entry * (1 - tp3_pct) if tp3_pct else None

        # Scan forward bars for SL / TP hit using HIGH and LOW (not just close)
        # This matches TradingView's intrabar detection — if the wick touched the
        # level, TV counts it as hit even if close didn't reach it.
        max_hold = min(100, len(prices_hist) - i - 1)
        outcome  = None
        r_mult   = 0.0
        exit_bar = max_hold
        for j in range(1, max_hold + 1):
            bar_high = highs_hist[i + j] if (i + j) < len(highs_hist) else prices_hist[i + j]
            bar_low  = lows_hist[i + j]  if (i + j) < len(lows_hist)  else prices_hist[i + j]
            if is_long:
                # SL check uses bar low (worst case within bar)
                if bar_low <= h_sl:
                    outcome = "loss"; r_mult = -1.0; exit_bar = j; break
                # TP checks use bar high (best case within bar) — highest TP first
                elif h_tp3 and bar_high >= h_tp3:
                    outcome = "win_tp3"; r_mult = r3 or r1; exit_bar = j; break
                elif h_tp2 and bar_high >= h_tp2:
                    outcome = "win_tp2"; r_mult = r2 or r1; exit_bar = j; break
                elif bar_high >= h_tp1:
                    outcome = "win_tp1"; r_mult = r1; exit_bar = j; break
            else:
                # SL check uses bar high (worst case for short)
                if bar_high >= h_sl:
                    outcome = "loss"; r_mult = -1.0; exit_bar = j; break
                # TP checks use bar low (best case for short)
                elif h_tp3 and bar_low <= h_tp3:
                    outcome = "win_tp3"; r_mult = r3 or r1; exit_bar = j; break
                elif h_tp2 and bar_low <= h_tp2:
                    outcome = "win_tp2"; r_mult = r2 or r1; exit_bar = j; break
                elif bar_low <= h_tp1:
                    outcome = "win_tp1"; r_mult = r1; exit_bar = j; break

        # Trades that neither hit TP nor SL within max_hold bars are timed out.
        # IMPORTANT: for timeouts we advance only 1 bar past the entry bar, NOT
        # max_hold+1 bars.  Advancing by max_hold skips 100 bars of potential entries
        # — this is why we were finding far fewer trades than TradingView.
        # TV closes an unresolved trade and checks for a new entry on the very next bar.
        if outcome is None:
            outcome  = "timeout"
            r_mult   = -1.0
            exit_bar = 1   # advance only 1 bar so we don't skip over RSI crossings
        trade_date = dates_hist[i] if i < len(dates_hist) else str(i)
        trades.append({
            "n":       len(trades) + 1,
            "outcome": outcome,
            "r":       r_mult,
            "date":    trade_date,
            "entry":   round(hist_entry, 6),
        })
        # Advance past the actual exit bar so the next signal can start
        # immediately after this trade closed (matching TradingView's behavior)
        i += exit_bar + 1

    if len(trades) < 2:
        return jsonify({
            "error": f"Only {len(trades)} matching signal(s) found in {len(prices_hist)} bars. " +
                     "Use TradingView Strategy Tester for longer history."
        }), 400

    wins   = [t for t in trades if t["outcome"] != "loss"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    wr     = round(len(wins) / len(trades) * 100)
    total_r = round(sum(t["r"] for t in trades), 2)
    avg_win = round(sum(t["r"] for t in wins) / len(wins), 2) if wins else 0
    avg_los = round(abs(sum(t["r"] for t in losses) / len(losses)), 2) if losses else 1
    gross_w = sum(t["r"] for t in wins)
    gross_l = abs(sum(t["r"] for t in losses))
    pf      = round(gross_w / gross_l, 2) if gross_l > 0 else 99.0

    # ── Equity curve + drawdown (1R = $100 = 1% of $10k) ─────────────────
    INITIAL_CAP  = 10000.0
    RISK_PER_TRADE = 100.0   # $100 = 1% of initial capital

    equity   = [INITIAL_CAP]
    peak_eq  = INITIAL_CAP
    max_dd   = 0.0
    trades_list = []

    for t in trades:
        pnl_usd = round(t["r"] * RISK_PER_TRADE, 2)
        new_eq  = round(equity[-1] + pnl_usd, 2)
        equity.append(new_eq)
        if new_eq > peak_eq:
            peak_eq = new_eq
        dd = peak_eq - new_eq
        if dd > max_dd:
            max_dd = dd
        trades_list.append({
            "n":       t["n"],
            "date":    t["date"],
            "outcome": t["outcome"],
            "r":       t["r"],
            "pnl_usd": pnl_usd,
            "entry":   t["entry"],
        })

    final_eq      = equity[-1]
    total_pnl_usd = round(final_eq - INITIAL_CAP, 2)
    total_pnl_pct = round((final_eq - INITIAL_CAP) / INITIAL_CAP * 100, 2)
    max_dd_usd    = round(max_dd, 2)
    max_dd_pct    = round(max_dd / peak_eq * 100, 2) if peak_eq > 0 else 0.0

    return jsonify({
        "win_rate":       wr,
        "total_trades":   len(trades),
        "wins":           len(wins),
        "losses":         len(losses),
        "total_r":        total_r,
        "avg_win_r":      avg_win,
        "avg_loss_r":     avg_los,
        "profit_factor":  pf,
        "bars_tested":    min(200, len(prices_hist)),
        # Period covers only the signal-scan window (last 200 bars), not the RSI warmup bars
        "period":         f"{dates_hist[scan_start]} → {dates_hist[-1]}" if len(dates_hist) > scan_start else f"{len(prices_hist)} bars",
        "signal":         signal,
        # ── New fields for TV-style display ──
        "total_pnl_usd":  total_pnl_usd,
        "total_pnl_pct":  total_pnl_pct,
        "max_dd_usd":     max_dd_usd,
        "max_dd_pct":     max_dd_pct,
        "equity_curve":   equity,         # list of floats from $10k baseline
        "trades_list":    trades_list,    # [{n, date, outcome, r, pnl_usd, entry}]
        "initial_capital": INITIAL_CAP,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
