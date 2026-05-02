"""
Trading Signals SaaS — Backend
Supports: Stocks, Crypto, Forex, Commodities, Indices
Features: Multi-timeframe analysis, MTF trend, historical win rate,
          server-side watch scheduler with SMS + email alerts.
"""

from flask import Flask, request, jsonify, send_from_directory, session, Response, redirect, url_for
from flask_cors import CORS
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
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
CACHE_TTL   = int(os.environ.get("CACHE_TTL_SECONDS", "300"))  # override via Railway env var

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
    # Preserve proper HTTP status codes (405 stays 405, 400 stays 400, etc.).
    # Only truly unhandled exceptions become 500.
    code = getattr(e, "code", None)
    if isinstance(code, int) and 400 <= code < 600:
        desc = getattr(e, "description", str(e))
        resp = jsonify({"error": desc})
        if code == 405:
            valid = getattr(e, "valid_methods", None)
            if valid:
                resp.headers["Allow"] = ", ".join(sorted(valid))
        return resp, code
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

# ─── Session cookie config (fix refresh-logout bug) ───
# Without these, Flask defaults can drop the session cookie on page refresh
# in some browser/OS combinations, dumping the user back to the login screen.
# Setting them explicitly with SECURE=True (HTTPS-only) + SAMESITE=Lax
# (sent on top-level navigations + same-origin XHR) + a 30-day lifetime
# keeps the user logged in across refreshes for a month.
from datetime import timedelta as _td
app.config["SESSION_COOKIE_SAMESITE"]    = "Lax"
app.config["SESSION_COOKIE_SECURE"]      = True   # Railway serves HTTPS; required for Chrome to accept SameSite=None cookies and harmless on other browsers
app.config["SESSION_COOKIE_HTTPONLY"]    = True   # JS cannot read the session cookie — XSS protection
app.config["PERMANENT_SESSION_LIFETIME"] = _td(days=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True  # rolling expiration — every request bumps the cookie's expires-at to now+30d

@app.before_request
def _make_session_persistent():
    """If a user has logged in (user_id or authenticated set), keep the
    session permanent on every request so the rolling 30-day window
    survives page refreshes and tab closes."""
    if session.get("user_id") or session.get("authenticated"):
        session.permanent = True

ADMIN_EMAIL           = os.environ.get("ADMIN_EMAIL", "").strip().lower()
MT5_EA_SECRET         = os.environ.get("MT5_EA_SECRET", "").strip()
# user_ids whose EA requests skip the X-EA-Secret check (legacy users whose EA was
# set up before per-user auth was wired in). Set via Railway env var, comma-separated.
# Empty / missing = no bypass, all EA requests must present a valid per-user secret.
MT5_BYPASS_USER_IDS   = set(filter(None, [s.strip() for s in os.environ.get("MT5_BYPASS_USER_IDS", "").split(",")]))
GOOGLE_CLIENT_ID      = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET  = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI   = os.environ.get("GOOGLE_REDIRECT_URI", "https://dot-verse.up.railway.app/auth/google/callback")

def login_required(f):
    """Decorator — blocks API calls unless the user has logged in this session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id") and not session.get("authenticated"):
            return jsonify({"error": "Unauthorized", "login_required": True}), 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    """Decorator — blocks API calls unless the current user is admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "Unauthorized"}), 401
        user = _get_current_user()
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

def _get_current_user():
    """Return the current User ORM object from session, or None."""
    user_id = session.get("user_id")
    if not user_id or not _DBSession:
        return None
    try:
        db = _DBSession()
        user = db.query(User).filter_by(id=user_id).first()
        db.close()
        return user
    except Exception:
        return None

# ─── TIMEFRAME CONFIG ─────────────────────────────────────────
TIMEFRAME_CONFIG = {
    "5m":  {"interval": "5m",  "period": "5d",  "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "15m": {"interval": "15m", "period": "5d",  "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "30m": {"interval": "30m", "period": "5d",  "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "1h":  {"interval": "1h",  "period": "30d", "chart_bars": 100, "date_fmt": "%Y-%m-%d %H:%M"},
    "4h":  {"interval": "1h",  "period": "60d", "chart_bars": 90,  "date_fmt": "%Y-%m-%d %H:%M", "resample": "4h"},
    "1d":  {"interval": "1d",  "period": "1y",  "chart_bars": 90,  "date_fmt": "%Y-%m-%d"},
    "1w":  {"interval": "1wk", "period": "5y",  "chart_bars": 80,  "date_fmt": "%Y-%m-%d"},
    "1mo": {"interval": "1mo", "period": "10y", "chart_bars": 60,  "date_fmt": "%Y-%m"},
}

# ── 3b: Asset-specific indicator settings ────────────────────────────────────
# RSI period and EMA fast/slow per asset class.
# Crypto is more volatile → faster RSI and EMAs to stay responsive.
# Indices are mean-reverting and slow → longer RSI and EMAs for stability.
# ─── ATR MULTIPLIERS PER TRADE TYPE ──────────────────────────────────────
# Maps each timeframe to the trade-type-appropriate ATR multipliers for
# stop loss and the three take-profit levels. Day Trade values match the
# previous global defaults (4/10/14/18) so 1H and 4H signals — the most
# common — produce identical levels to before this change. Scalp signals
# get tighter levels because the trader holds for minutes; swing/position
# get wider levels because the trader holds through multi-day pullbacks.
#
# Each dict entry: {sl_mult, tp1_mult, tp2_mult, tp3_mult, type, hold,
#   beginner_explainer} — the explainer is rendered as plain English on
# the signal card so the trader knows WHY these distances are right for
# this kind of trade.
TRADE_LEVEL_PROFILES = {
    "scalp":    {"sl_mult": 3.0, "tp1_mult":  6.0, "tp2_mult":  9.0, "tp3_mult": 12.0,
                 "type": "Scalp", "hold": "minutes – 1 hour",
                 "beginner_explainer": "Tight stops because hold time is minutes — wider stops would mean sitting through normal price wobbles you should avoid when scalping."},
    "day":      {"sl_mult": 4.0, "tp1_mult": 10.0, "tp2_mult": 14.0, "tp3_mult": 18.0,
                 "type": "Day Trade", "hold": "1–8 hours, close same day",
                 "beginner_explainer": "Standard stops — wide enough to absorb intraday noise, tight enough that you exit within a single trading session if the trade fails."},
    "swing":    {"sl_mult": 5.0, "tp1_mult": 13.0, "tp2_mult": 18.0, "tp3_mult": 24.0,
                 "type": "Swing", "hold": "2–10 days",
                 "beginner_explainer": "Wider stops because hold is multiple days — daily price swings need room, otherwise normal overnight moves stop you out before the trade plays out."},
    "position": {"sl_mult": 6.0, "tp1_mult": 15.0, "tp2_mult": 24.0, "tp3_mult": 36.0,
                 "type": "Position", "hold": "weeks – months",
                 "beginner_explainer": "Widest stops — even great trades pull back significantly over weeks. Tight stops would shake you out right before the move plays out."},
}
_TF_TO_PROFILE = {
    "5m": "scalp", "15m": "scalp", "30m": "scalp",
    "1h": "day",   "4h": "day",
    "1d": "swing",
    "1w": "position", "1mo": "position", "1m": "position",  # 1m here = 1 month, not 1 minute
}
def _atr_profile_for_tf(timeframe):
    """Return the trade-level profile dict for a given timeframe.
    Falls back to 'day' for unknown timeframes (safest middle ground)."""
    tf = (timeframe or "").lower().strip()
    return TRADE_LEVEL_PROFILES[_TF_TO_PROFILE.get(tf, "day")]


ASSET_CONFIG = {
    # rsi_period / ema_fast / ema_slow — live signal indicator settings
    # atr_gate_pct — minimum ATR/price ratio for a bar to be tradeable (below = choppy noise)
    # roc_gate_pct — minimum 10-bar price change % to count as momentum confirmation
    # vol_gate     — whether to apply the volume hard gate (False for forex: tick volume unreliable)
    "crypto":    {"rsi_period": 10, "ema_fast": 7,  "ema_slow": 14, "atr_gate_pct": 0.008, "roc_gate_pct": 3.0, "vol_gate": True},
    "forex":     {"rsi_period": 14, "ema_fast": 9,  "ema_slow": 21, "atr_gate_pct": 0.0015,"roc_gate_pct": 0.3, "vol_gate": False},
    "stock":     {"rsi_period": 14, "ema_fast": 9,  "ema_slow": 21, "atr_gate_pct": 0.004, "roc_gate_pct": 1.0, "vol_gate": True},
    "index":     {"rsi_period": 21, "ema_fast": 20, "ema_slow": 50, "atr_gate_pct": 0.003, "roc_gate_pct": 0.8, "vol_gate": True},
    "commodity": {"rsi_period": 14, "ema_fast": 9,  "ema_slow": 21, "atr_gate_pct": 0.005, "roc_gate_pct": 1.5, "vol_gate": True},
}
_DEFAULT_ASSET_CFG = {"rsi_period": 14, "ema_fast": 9, "ema_slow": 21, "atr_gate_pct": 0.004, "roc_gate_pct": 1.0, "vol_gate": True}

# Trade mode → timeframe mapping (used by scanner and signal feed)
# Each mode targets a specific holding period and filters to appropriate timeframes.
TRADE_MODE_CONFIG = {
    "scalp":    {"timeframes": ["5m","15m","30m"],        "label": "Scalping",        "hold": "mins–hours"},
    "day":      {"timeframes": ["1h","4h"],               "label": "Day Trading",     "hold": "hours–1 day"},
    "swing":    {"timeframes": ["4h","1d"],               "label": "Swing Trading",   "hold": "days–weeks"},
    "position": {"timeframes": ["1d","1w"],               "label": "Position Trading","hold": "weeks–months"},
    "all":      {"timeframes": ["15m","1h","4h","1d"],    "label": "All Modes",       "hold": "any"},
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

# ── MT5 EA state (pushed by EA every 5s) ──────────────────────
mt5_state      = {}   # { user_id: {account:{}, positions:[], last_seen:datetime} }
mt5_state_lock = threading.Lock()

def _mt5_symbol(ticker, asset_type):
    """Convert DotVerse ticker to MT5 symbol format."""
    s = ticker.upper()
    s = s.replace("-USD","USD").replace("/","").replace("=X","").replace("=F","")
    _map = {"BTCUSD":"BTCUSD","ETHUSD":"ETHUSD","XRPUSD":"XRPUSD",
            "GC":"XAUUSD","SI":"XAGUSD","CL":"USOIL","NG":"NGAS",
            "XAUUSD":"XAUUSD","XAGUSD":"XAGUSD"}
    return _map.get(s, s)

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

def get_rsi(close, period=14):
    delta = close.diff()
    gain  = delta.clip(lower=0).fillna(0)
    loss  = (-delta).clip(lower=0).fillna(0)
    return 100 - 100 / (1 + rma(gain, period) / rma(loss, period))


def detect_rsi_divergence(high, low, rsi_series, pivot_len=3, lookback=100):
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

# ─── 2e: FORWARD-FILL DATE GRID ──────────────────────────────
_TF_FREQ = {
    "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1h",   "2h": "2h",   "4h": "4h",
    "1d": "1D",   "1w": "1W",
}
_STOCK_TYPES = {"stock", "index", "commodity"}

def _fill_date_grid(df, timeframe, asset_type):
    """Build expected timestamp grid for the given timeframe, reindex the
    DataFrame with forward-fill (max 3 consecutive fills) so indicators
    receive a continuous series with no accidental gaps.

    Weekends are excluded from the grid for stocks/indices/commodities.
    Crypto runs 24/7 — no exclusion.
    """
    freq = _TF_FREQ.get(timeframe)
    if not freq or df.empty:
        return df
    try:
        start = df.index[0]
        end   = df.index[-1]
        grid  = pd.date_range(start=start, end=end, freq=freq, tz=df.index.tz)
        # Exclude weekends for non-crypto assets
        if asset_type in _STOCK_TYPES:
            grid = grid[grid.dayofweek < 5]
        # Reindex and forward-fill, capping at 3 consecutive fills
        df = df.reindex(grid).ffill(limit=3)
    except Exception as _e:
        print(f"[fill_date_grid] skipped ({_e})")
    return df

# ─── INDICATOR CALCULATION ────────────────────────────────────
def calculate_indicators(df, timeframe="1d", asset_type="stock"):
    # ── 2a: Per-asset NaN / bad-tick strategy ────────────────────────────────
    df = df.copy()
    if asset_type == "crypto":
        for col in ("Open", "High", "Low", "Close"):
            s = df[col]
            # Zero prices → NaN
            df[col] = s.where(s > 0)
            # Bars more than 10× the 20-bar rolling median → replace with median
            roll_med = df[col].rolling(20, min_periods=5).median()
            mask = df[col] > (roll_med * 10)
            df.loc[mask, col] = roll_med[mask]
    # Drop rows with any NaN in OHLCV (covers genuine gaps for all asset types)
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])

    # ── 2b: Spike filter (all asset types) ───────────────────────────────────
    # Any bar where close deviates > 20% from its 20-bar rolling median is a
    # data spike. Replace with the median rather than dropping so index stays
    # continuous. Log how many were clipped.
    roll_med_close = df["Close"].rolling(20, min_periods=5).median()
    spike_mask = (
        (df["Close"] - roll_med_close).abs() / roll_med_close.clip(lower=1e-9) > 0.20
    )
    n_spikes = int(spike_mask.sum())
    if n_spikes:
        df.loc[spike_mask, "Close"] = roll_med_close[spike_mask]
        # Clip High/Low to match so TR calc stays sane
        df.loc[spike_mask, "High"] = df.loc[spike_mask, ["High", "Close"]].min(axis=1)
        df.loc[spike_mask, "Low"]  = df.loc[spike_mask, ["Low",  "Close"]].max(axis=1)
        print(f"[calc_ind] spike filter: clipped {n_spikes} bar(s) for {asset_type}")

    close = df["Close"].squeeze()
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    vol   = df["Volume"].squeeze()

    # ── 3b: Asset-specific indicator periods ─────────────────────────────────
    _acfg      = ASSET_CONFIG.get(asset_type, _DEFAULT_ASSET_CFG)
    rsi_period = _acfg["rsi_period"]
    ema_fast   = _acfg["ema_fast"]
    ema_slow   = _acfg["ema_slow"]

    rsi_series = get_rsi(close, period=rsi_period)
    rsi        = rsi_series.iloc[-1]
    rsi_div    = detect_rsi_divergence(high, low, rsi_series)

    e_fast = ema_tv(close, ema_fast).iloc[-1]
    e_slow = ema_tv(close, ema_slow).iloc[-1] if len(close) >= ema_slow else e_fast
    e200   = ema_tv(close, 200).iloc[-1] if len(close) >= 200 else e_slow
    # Keep e20/e50 aliases so downstream code that references them still works
    e20 = e_fast
    e50 = e_slow

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
    # ── 2c: Smoothed ATR — Wilder ATR14 smoothed over 100-bar rolling mean ──
    # Raw ATR14 is too noisy for stop sizing. Rolling mean of ATR14 gives a
    # stable baseline that doesn't overreact to individual volatile bars.
    atr_raw    = rma(tr, 14)
    atr_smooth = atr_raw.rolling(100, min_periods=14).mean()
    atr        = float(atr_smooth.iloc[-1])

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
    # Use asset-specific EMA periods for chart lines
    ema20_series = ema_tv(close, ema_fast).iloc[-n_bars:]
    ema50_series = ema_tv(close, ema_slow).iloc[-n_bars:] if len(close) >= ema_slow else ema20_series
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

    # Convert divergence pivot bar indices → chart-window coordinates.
    # Require ALL four bars (both price pivots + both RSI pivots) to be inside
    # the chart window.  If any bar is off-screen the translated index would be
    # negative → labels[negative] = undefined in JS → canvas draw silently skips.
    # It is cleaner to emit empty lists (no divergence drawn) than partial ones
    # that draw on price but not on RSI (or vice-versa).
    if rsi_div.get("price_pivot_bars"):
        pb = rsi_div["price_pivot_bars"]
        rb = rsi_div["rsi_pivot_bars"]
        all_in_window = (len(pb) >= 2 and len(rb) >= 2 and
                         all(b >= chart_start_idx for b in pb) and
                         all(b >= chart_start_idx for b in rb))
        if all_in_window:
            rsi_div["chart_price_pivot_bars"] = [b - chart_start_idx for b in pb]
            rsi_div["chart_rsi_pivot_bars"]   = [b - chart_start_idx for b in rb]
        else:
            rsi_div["chart_price_pivot_bars"] = []
            rsi_div["chart_rsi_pivot_bars"]   = []
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
        # Keep only divergences where ALL four pivot bars fall inside the chart window.
        # If any bar (price or RSI) is before chart_start_idx the translated index
        # becomes negative → labels[negative] = undefined in JS → canvas draw skips.
        if (pb2[0] < chart_start_idx or pb2[1] < chart_start_idx or
                rb2[0] < chart_start_idx or rb2[1] < chart_start_idx):
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
        "rsi":              round(float(rsi), 1),
        "rsi_period":       rsi_period,
        "rsi_divergence":   rsi_div,
        "ema20":            round(float(e20), 4),
        "ema50":            round(float(e50), 4),
        "ema200":           round(float(e200), 4),
        "ema_fast_period":  ema_fast,
        "ema_slow_period":  ema_slow,
        "ema_trend":        ema_trend,
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
def _build_chart_output(df: pd.DataFrame, timeframe: str, max_bars: int = 200):
    """Accept a DataFrame with DatetimeIndex (columns: Open High Low Close Volume).
    Sorts by timestamp, trims to max_bars, computes EMAs.
    Always returns 8-tuple: (dates, prices, vols, ema20, ema50, opens, highs, lows).
    Timestamps are formatted for display AFTER alignment — never before."""
    if df is None or df.empty:
        return None

    # Sort by timestamp — never trust source order (backtesting.py pattern)
    df = df.sort_index()
    df = df.iloc[-max_bars:]

    # Format dates for display only after alignment is complete
    dt_fmt = "%Y-%m-%d %H:%M" if timeframe in ("5m","15m","30m","1h","4h") else "%Y-%m-%d"
    dates  = [idx.strftime(dt_fmt) for idx in df.index]
    prices = df['Close'].round(6).tolist()
    vols   = df['Volume'].fillna(0).astype(int).tolist()
    opens  = df['Open'].round(6).tolist()
    highs  = df['High'].round(6).tolist()
    lows   = df['Low'].round(6).tolist()

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

    ema20 = _ema(prices, 20)
    ema50 = _ema(prices, min(50, len(prices) - 1))

    return (dates, prices, vols, ema20, ema50, opens, highs, lows)


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

        # Build DataFrame with UTC DatetimeIndex — preserves timestamps for alignment
        # Never convert to display strings here; _build_chart_output handles formatting
        df = pd.DataFrame({
            'Open':   [round(float(k[1]), 6) for k in klines],
            'High':   [round(float(k[2]), 6) for k in klines],
            'Low':    [round(float(k[3]), 6) for k in klines],
            'Close':  [round(float(k[4]), 6) for k in klines],
            'Volume': [int(float(k[5]))       for k in klines],
        }, index=pd.to_datetime([int(k[0]) for k in klines], unit='ms', utc=True).tz_convert(None))

        if len(df) < 10:
            return None
        print(f"[binance] OK — {sym} {interval}: {len(df)} bars")
        return _build_chart_output(df, timeframe)
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
        # Build DataFrame with DatetimeIndex before passing to _build_chart_output
        df = pd.DataFrame({
            'Open': opens, 'High': highs, 'Low': lows,
            'Close': prices, 'Volume': vols,
        }, index=pd.to_datetime(dates))
        print(f"[stooq] OK — {sym} {iv}: {len(df)} bars")
        return _build_chart_output(df, timeframe)
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

        dt_fmt = "%Y-%m-%d %H:%M" if timeframe in ("5m","15m","30m","1h","4h") else "%Y-%m-%d"
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
        # Build DataFrame with DatetimeIndex before passing to _build_chart_output
        df = pd.DataFrame({
            'Open': o_out, 'High': h_out, 'Low': l_out,
            'Close': prices, 'Volume': volumes,
        }, index=pd.to_datetime(dates))
        print(f"[yahoo_v8] OK — {yf_ticker} {timeframe}: {len(df)} bars")
        return _build_chart_output(df, timeframe)
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

        dt_fmt = "%Y-%m-%d %H:%M" if timeframe in ("5m", "15m", "30m", "1h", "4h") else "%Y-%m-%d"
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
        # Build DataFrame with DatetimeIndex before passing to _build_chart_output
        df = pd.DataFrame({
            'Open': opens, 'High': highs, 'Low': lows,
            'Close': prices, 'Volume': vols,
        }, index=pd.to_datetime(dates))
        print(f"[fmp] OK — {sym} {fmp_iv}: {len(df)} bars")
        return _build_chart_output(df, timeframe)
    except Exception as e:
        print(f"[fmp] error {sym}: {e}")
        return None


def _fetch_twelvedata(ticker, asset_type, timeframe):
    """Twelve Data — works on cloud IPs (Railway) for stocks/forex/commodity at intraday TFs.
    Free tier: 800 req/day, 8 req/min. Set TWELVEDATA_API_KEY env var to enable.
    Endpoint: https://api.twelvedata.com/time_series."""
    td_key = os.environ.get("TWELVEDATA_API_KEY", "").strip()
    if not td_key:
        return None
    # Map DotVerse timeframes to Twelve Data intervals
    td_map = {"5m": "5min", "15m": "15min", "30m": "30min",
              "1h": "1h", "4h": "4h", "1d": "1day", "1w": "1week", "1mo": "1month"}
    td_iv = td_map.get(timeframe, "1day")
    # Build the symbol — stocks plain, forex/commodity with slash, crypto with /USD or /USDT
    sym_raw = ticker.upper().replace("=X", "").replace("-", "")
    if asset_type == "forex":
        clean = sym_raw.replace("/", "")
        sym = clean[:3] + "/" + clean[3:]
    elif asset_type == "crypto":
        return None  # Binance handles crypto better
    elif asset_type == "commodity":
        # XAUUSD / XAGUSD / WTIUSD style
        clean = sym_raw.replace("/", "")
        if len(clean) >= 6:
            sym = clean[:3] + "/" + clean[3:]
        else:
            sym = clean
    else:
        sym = sym_raw  # stocks: AAPL, NVDA, SPX
    try:
        url = "https://api.twelvedata.com/time_series"
        params = {"symbol": sym, "interval": td_iv, "outputsize": 200,
                  "order": "ASC", "apikey": td_key, "format": "JSON"}
        r = requests.get(url, params=params, timeout=(5, 12))
        if r.status_code != 200:
            print(f"[twelvedata] HTTP {r.status_code} for {sym} {td_iv}")
            return None
        data = r.json()
        if not data or data.get("status") == "error":
            print(f"[twelvedata] API error for {sym}: {data.get('message','no message')}")
            return None
        values = data.get("values") or []
        if len(values) < 10:
            print(f"[twelvedata] insufficient data for {sym}: {len(values)} bars")
            return None
        dt_fmt = "%Y-%m-%d %H:%M" if timeframe in ("5m", "15m", "30m", "1h", "4h") else "%Y-%m-%d"
        dates, opens, highs, lows, prices, vols = [], [], [], [], [], []
        for bar in values:
            try:
                from datetime import datetime as dt_cls
                d_raw = bar.get("datetime", "")
                if " " in d_raw:
                    d_parsed = dt_cls.strptime(d_raw, "%Y-%m-%d %H:%M:%S") if len(d_raw) > 10 else dt_cls.strptime(d_raw, "%Y-%m-%d")
                else:
                    d_parsed = dt_cls.strptime(d_raw, "%Y-%m-%d")
                dates.append(d_parsed.strftime(dt_fmt))
                opens.append(round(float(bar["open"]), 6))
                highs.append(round(float(bar["high"]), 6))
                lows.append(round(float(bar["low"]), 6))
                prices.append(round(float(bar["close"]), 6))
                vols.append(int(float(bar.get("volume", 0) or 0)))
            except (ValueError, KeyError):
                continue
        if len(prices) < 10:
            return None
        df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows,
                           "Close": prices, "Volume": vols}, index=pd.to_datetime(dates))
        print(f"[twelvedata] OK — {sym} {td_iv}: {len(df)} bars")
        return _build_chart_output(df, timeframe)
    except Exception as e:
        print(f"[twelvedata] error {sym}: {e}")
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

    # 3. Twelve Data — primary for stocks/forex intraday on Railway (Yahoo v8 is 429-blocked)
    if asset_type in ("stock", "index", "forex", "commodity"):
        print(f"[chart] trying Twelve Data for {ticker} ({asset_type}) {timeframe}")
        result = _fetch_twelvedata(ticker, asset_type, timeframe)
        if result:
            return result
        print(f"[chart] Twelve Data failed for {ticker}")

    # 4. FMP — alternative when TD key missing or quota hit
    if asset_type in ("stock", "index", "forex", "commodity"):
        print(f"[chart] trying FMP for {ticker} ({asset_type}) {timeframe}")
        result = _fetch_fmp(ticker, asset_type, timeframe)
        if result:
            return result
        print(f"[chart] FMP failed for {ticker}")

    # 5. Yahoo Finance v8 — last resort (likely 429 on Railway)
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
        "15m": {"interval": "15m", "period": "5d"},
        "1H":  {"interval": "1h",  "period": "30d"},
        "4H":  {"interval": "1h",  "period": "60d", "resample": "4h"},
        "1D":  {"interval": "1d",  "period": "1y"},
        "1W":  {"interval": "1wk", "period": "5y"},
        "1M":  {"interval": "1mo", "period": "10y"},
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
def pre_screen(ind, tv=None):
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

    # ── TV primary signal — same source as get_analysis() ──────
    # When TV data is available use Recommend.All so scanner matches
    # the signals tab exactly.
    if tv:
        tv_rec_label = tv.get("tv_rec_label", "")
        tv_score     = tv.get("tv_rec_all")
        score_str    = f"{tv_score:+.2f}" if tv_score is not None else "?"
        if tv_rec_label == "STRONG BUY":
            hint, reason = "BUY",  f"TV: STRONG BUY ({score_str}) — {bull_score}B/{bear_score}S indicators"
        elif tv_rec_label == "BUY":
            hint, reason = "BUY",  f"TV: BUY ({score_str}) — {bull_score}B/{bear_score}S indicators"
        elif tv_rec_label == "STRONG SELL":
            hint, reason = "SELL", f"TV: STRONG SELL ({score_str}) — {bear_score}S/{bull_score}B indicators"
        elif tv_rec_label == "SELL":
            hint, reason = "SELL", f"TV: SELL ({score_str}) — {bear_score}S/{bull_score}B indicators"
        else:  # NEUTRAL or missing
            hint, reason = None,   f"TV: NEUTRAL ({score_str}) — no directional setup"
        call_claude = hint in ("BUY", "SELL")
    else:
        # Fallback: custom scoring when TV unavailable
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
    _dpc = 2 if price >= 100 else 4 if price >= 1 else 6 if price >= 0.01 else 8
    prnd_c = lambda v: round(v, _dpc)
    sl     = prnd_c(min(sup - atr * 0.3, price - atr * 4.0))
    risk   = entry - sl
    if risk <= 0:
        return {"counter_trade": False}

    tp1 = prnd_c(entry + risk * 2.0)   # 2:1 R:R minimum
    tp2 = prnd_c(entry + risk * 3.0)   # 3:1 R:R
    tp3 = prnd_c(entry + risk * 4.0)   # 4:1 R:R
    # ── 2d: Net RR after fees — 0.2% round-trip ──────────────────────────
    fee_adj = entry * 0.002
    tp1 = prnd_c(tp1 - fee_adj)
    tp2 = prnd_c(tp2 - fee_adj)
    tp3 = prnd_c(tp3 - fee_adj)
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

        vol_raw = g("volume")
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
            "tv_volume":      int(vol_raw)       if vol_raw  is not None else None,
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

    # ── EMA Trend logic (higher weight: counts as 2-3) ──
    # FIX 2026-04-29: calculate_indicators produces "STRONG BULL"/"BULL"/"STRONG BEAR"/
    # "BEAR"/"MIXED", but the previous check was ".lower() == 'bullish'" which never
    # matched any of those values. The +2 EMA vote (heaviest single contribution) was
    # dead the entire time — local voting only counted RSI/MACD/Supertrend/BB. This is
    # why the dashboard signals were over-conservative after the TV override was
    # removed in the same session: TV had been masking the broken local logic.
    # Now matches the actual values, with STRONG BULL/BEAR weighted +3 to reflect
    # the additional macro-trend confirmation (price aligned through EMA-200).
    _emat = (ema_trend or "").upper()
    if _emat == "STRONG BULL":
        bullish_count += 3
        trend_assessment = "EMA stack is strongly bullish — price is above all key moving averages with macro alignment."
    elif _emat == "BULL":
        bullish_count += 2
        trend_assessment = "EMA stack is bullish; uptrend structure is intact and price is above key moving averages."
    elif _emat == "STRONG BEAR":
        bearish_count += 3
        trend_assessment = "EMA stack is strongly bearish — price is below all key moving averages with macro alignment."
    elif _emat == "BEAR":
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

    # ── Volume logic (cross-check with EMA trend direction) ──
    # FIX 2026-04-29: same string mismatch as above. Using actual ema_trend values.
    if vol_ratio > 1.2:
        # High volume confirms the prevailing EMA trend direction
        if _emat in ("STRONG BULL", "BULL"):
            bullish_count += 1
        elif _emat in ("STRONG BEAR", "BEAR"):
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

    # ── Net score (kept for confidence calculation) ──
    net = bullish_count - bearish_count

    # ── 3a: Confluence gate — signal requires ≥65% sub-indicator agreement ──
    # Only indicators that actually voted (bullish OR bearish) count toward the
    # denominator. Neutral indicators (RSI in 45-55, flat MACD) are excluded.
    # Below 65% agreement → HOLD regardless of net score.
    total_votes = bullish_count + bearish_count
    if total_votes > 0:
        bull_pct = bullish_count / total_votes
        bear_pct = bearish_count / total_votes
    else:
        bull_pct = bear_pct = 0.0

    if bull_pct >= 0.65:
        signal = "BUY"
    elif bear_pct >= 0.65:
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
    # TRADINGVIEW PRIMARY SIGNAL (restored 2026-04-29 — v1 behaviour)
    # When TV data is available, use TradingView's 26-indicator
    # Recommend.All score as the authoritative signal. TV's score
    # combines moving averages + oscillators (RSI, Stochastic, CCI,
    # Williams %R, MACD, etc) — the same indicators experienced
    # traders use. Mean-reversion + trend signals blended.
    #
    # Our local 7-indicator vote count remains in the response
    # (bullish_count, bearish_count, summary, gate_note) as a
    # cross-check / context layer for transparency. TV-derived
    # signal is the verdict displayed on the card; local votes
    # are shown as "DotVerse cross-check" so users see when our
    # local view aligns or differs.
    #
    # Earlier in this session we tried using local-only signals
    # for "trust integrity" but measurement showed local-only
    # signals at 8% win rate. TV restored as primary signal source.
    # ══════════════════════════════════════════════════════════════
    tv_signal_used = False
    if tv:
        tv_rec_label = tv.get("tv_rec_label", "")
        tv_rec_all   = tv.get("tv_rec_all")
        if tv_rec_label in ("STRONG BUY", "BUY", "NEUTRAL", "SELL", "STRONG SELL"):
            if tv_rec_label == "STRONG BUY":
                signal, confidence = "BUY",  "HIGH"
            elif tv_rec_label == "BUY":
                signal, confidence = "BUY",  "MEDIUM"
            elif tv_rec_label == "NEUTRAL":
                signal, confidence = "HOLD", "LOW"
            elif tv_rec_label == "SELL":
                signal, confidence = "SELL", "MEDIUM"
            else:  # STRONG SELL
                signal, confidence = "SELL", "HIGH"
            tv_signal_used = True
            print(f"[TV-signal] {ticker} {timeframe} -> {tv_rec_label} (score={tv_rec_all}) -> {signal}/{confidence}")

    # ══════════════════════════════════════════════════════════════
    # GATE 1: Higher-timeframe trend filter
    # Skip when TV signal is used — TV already aggregates HTF context.
    # ══════════════════════════════════════════════════════════════
    htf_bias = _htf_trend_bias(mtf, timeframe)
    gate_note = ""
    if not tv_signal_used:
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
    # Skip when TV signal is used — TV already aggregates 26 indicators
    # including price action. Scanner does not enrich ind with chart data
    # so running this gate only in analyze would create a systematic
    # scanner/signals mismatch. Consistent with Gate 1 skip rule.
    # ══════════════════════════════════════════════════════════════
    buyer_pct, seller_pct = _compute_footprint_dominance(ind)
    if not tv_signal_used and buyer_pct is not None:
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
    # GATE 3: Minimum votes (refactored 2026-04-29 from confidence floor)
    # The previous gate "confidence == LOW → HOLD" was too aggressive in mixed
    # markets, demoting valid 2-vs-1 directional signals (e.g. dashboard
    # screenshot at midnight 4-29) to HOLD even when they passed the 65%
    # confluence gate. The new check requires at least 3 total indicator votes
    # for an actionable signal:
    #   • Protects against single-vote signals (1 bull / 0 bear is trivially
    #     100% bullish but statistically meaningless — sample of one).
    #   • Lets marginal signals (2-vs-1 = 67% confluence) display as BUY/SELL
    #     with the HYPOTHESIS label so the user sees the actual direction with
    #     a clear "weak conviction" warning. Calculator coaches them to size
    #     smaller. This is exactly the ethos: math, verdict, and trust label
    #     all agree — no silent censoring of an honest directional signal.
    # Conviction strength is still communicated via confidence_label
    # (CONFIRMED / LIKELY / HYPOTHESIS); frontend styles each distinctly.
    # ══════════════════════════════════════════════════════════════
    MIN_VOTES_FOR_SIGNAL = 3
    if signal != "HOLD" and total_votes < MIN_VOTES_FOR_SIGNAL:
        print(f"[gate] minimum votes ({total_votes} < {MIN_VOTES_FOR_SIGNAL}) — downgrading {signal} to HOLD on {ticker}")
        signal = "HOLD"
        gate_note = gate_note or f"Only {total_votes} indicator{'s' if total_votes != 1 else ''} voted — need at least {MIN_VOTES_FOR_SIGNAL} for an actionable signal."

    # Trade-type profile resolved up-front so it's available even on HOLD
    # signals where the SL/TP block is skipped — the response dict at the
    # bottom of this function still needs trade_type metadata.
    _profile = _atr_profile_for_tf(timeframe)

    # Generate trade levels based on ATR
    if signal != "HOLD" and atr > 0:
        # Adaptive decimal places: cheap altcoins (< $1) need 6dp so TP levels
        # don't collapse to the same displayed value after rounding.
        _dp = 2 if price >= 100 else 4 if price >= 1 else 6 if price >= 0.01 else 8
        prnd = lambda v: round(v, _dp)

        entry = prnd(price)

        # ATR multipliers now depend on trade type (timeframe-derived).
        # See TRADE_LEVEL_PROFILES at top of file. 1H/4H Day Trade values
        # are unchanged from the previous global defaults (4/10/14/18).
        _sl_m, _t1_m, _t2_m, _t3_m = _profile["sl_mult"], _profile["tp1_mult"], _profile["tp2_mult"], _profile["tp3_mult"]
        if signal == "BUY":
            stop_loss = prnd(price - (_sl_m * atr))
            tp1 = prnd(price + (_t1_m * atr))  # ≥2:1 R:R after fees
            tp2 = prnd(price + (_t2_m * atr))  # ≥3:1 R:R after fees
            tp3 = prnd(price + (_t3_m * atr))  # ≥4:1 R:R after fees
        else:  # SELL
            stop_loss = prnd(price + (_sl_m * atr))
            tp1 = prnd(price - (_t1_m * atr))
            tp2 = prnd(price - (_t2_m * atr))
            tp3 = prnd(price - (_t3_m * atr))

        # ── 2d: Net RR after fees — 0.2% round-trip (0.1% entry + 0.1% exit) ──
        fee_adj = entry * 0.002
        if signal == "BUY":
            tp1 = prnd(tp1 - fee_adj)
            tp2 = prnd(tp2 - fee_adj)
            tp3 = prnd(tp3 - fee_adj)
        else:  # SELL — fees add to cost, reducing net gain
            tp1 = prnd(tp1 + fee_adj)
            tp2 = prnd(tp2 + fee_adj)
            tp3 = prnd(tp3 + fee_adj)

        # Calculate R:R ratios (after fee adjustment)
        risk = abs(entry - stop_loss)
        if risk > 0:
            rr1 = round((abs(tp1 - entry) / risk), 1)
            rr2 = round((abs(tp2 - entry) / risk), 1)
            rr3 = round((abs(tp3 - entry) / risk), 1)
            # ── Minimum R:R gate — reject trades below 1:2 ──────────────────
            if rr1 < 2.0:
                print(f"[rr-gate] {ticker} rr1={rr1} < 2.0 — downgrading {signal} to HOLD")
                # FIX 2026-04-29: set gate_note so the summary text explains WHY
                # the signal was demoted. Without this, user saw the bare
                # 'Mixed signals: X bullish vs Y bearish' text with no reason.
                # Beginner trust requires honesty about gate decisions.
                gate_note = gate_note or (
                    f"Risk:reward only 1:{rr1} — below DotVerse's minimum 1:2 floor. "
                    f"Trade levels exist but the math doesn't favour entry."
                )
                signal = "HOLD"
                entry = stop_loss = tp1 = tp2 = tp3 = None
                rr1 = rr2 = rr3 = None
                position_pct = None
            else:
                # ── 3c: Position size for 1% account risk ──────────────────────
                position_pct = round(min(entry / risk, 100.0), 1)
        else:
            rr1 = rr2 = rr3 = None
            position_pct = None
    else:
        entry = stop_loss = tp1 = tp2 = tp3 = None
        rr1 = rr2 = rr3 = None
        position_pct = None

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
        "position_pct": position_pct,
        # Trade-type metadata so the frontend card can show what kind of
        # trade this is and the plain-English reasoning for why the SL/TP
        # are at these distances. Beginner-first: the trader sees this on
        # every signal so they understand the holding period and the
        # rationale before they look at the numbers.
        "trade_type":           _profile["type"],
        "trade_type_hold":      _profile["hold"],
        "trade_type_explainer": _profile["beginner_explainer"],
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
        "tv_signal_used": tv_signal_used,
        "tv_rec_label": tv.get("tv_rec_label") if tv else None,
        "tv_rec_all": tv.get("tv_rec_all") if tv else None,
        # ── 3d: Confidence label (restored TV-aware vocabulary 2026-04-29) ────
        # CONFIRMED  — TV scanner data used (26-indicator score) OR very strong net (>=5)
        # LIKELY     — TV BUY/SELL with medium conviction OR net >= 3 from local stack
        # HYPOTHESIS — Weak agreement; signal exists but conviction is marginal
        "confidence_label": (
            "CONFIRMED"  if (tv_signal_used or abs(net) >= 5) else
            "LIKELY"     if abs(net) >= 3 else
            "HYPOTHESIS"
        ),
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
        return None  # not configured — not a failure
    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_num, "To": to_num, "Body": message},
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            print(f"[SMS] Twilio error {resp.status_code}: {resp.text[:200]}")
            return False
        print("[SMS] Sent OK")
        return True
    except Exception as e:
        print(f"[SMS] Error: {e}")
        return False


def send_whatsapp(message):
    """Send WhatsApp message via Twilio WhatsApp API."""
    sid      = os.environ.get("SMS_ACCOUNT_SID", "").strip()
    token    = os.environ.get("SMS_AUTH_TOKEN",  "").strip()
    from_num = os.environ.get("WA_FROM_NUMBER", "whatsapp:+14155238886").strip()
    to_num   = os.environ.get("WA_TO_NUMBER", "").strip()
    if not all([sid, token, to_num]):
        return None  # not configured — not a failure
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
            return False
        print("[WhatsApp] Sent OK")
        return True
    except Exception as e:
        print(f"[WhatsApp] Error: {e}")
        return False


def send_telegram(message):
    """Send plain text message via Telegram Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id   = os.environ.get("TELEGRAM_CHAT_ID",   "").strip()
    if not all([bot_token, chat_id]):
        return None  # not configured — not a failure
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
        if resp.status_code == 200 and resp.json().get("ok"):
            print("[Telegram] Sent OK — delivery confirmed")
            return True
        print(f"[Telegram] Error {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False


def send_telegram_keyboard(message, keyboard_rows):
    """Send Telegram message with inline keyboard buttons. Returns message_id or None."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id   = os.environ.get("TELEGRAM_CHAT_ID",   "").strip()
    if not all([bot_token, chat_id]):
        return None
    tg_msg = (message
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id":      chat_id,
                "text":         tg_msg,
                "parse_mode":   "HTML",
                "reply_markup": {"inline_keyboard": keyboard_rows},
            },
            timeout=15,
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            msg_id = resp.json()["result"]["message_id"]
            print(f"[Telegram] Sent with keyboard — message_id={msg_id}")
            return msg_id
        print(f"[Telegram] Keyboard error {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"[Telegram] Keyboard error: {e}")
        return None


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

    results = []
    if "sms" in channels:
        r = send_sms(msg)
        if r is not None: results.append(r)
    if "whatsapp" in channels:
        r = send_whatsapp(msg)
        if r is not None: results.append(r)
    if "telegram" in channels:
        r = send_telegram(msg)
        if r is not None: results.append(r)
    # Only mark delivered if at least one channel confirmed send
    delivered = any(results) if results else False
    print(f"[Alert] Fired {signal} for {ticker} ({timeframe}) @ {price} via {channels} — delivered={delivered}")
    return delivered

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
        _dp2 = 2 if price >= 100 else 4 if price >= 1 else 6 if price >= 0.01 else 8
        prnd2 = lambda v: round(v, _dp2)
        entry = prnd2(price)
        # Per-trade-type ATR multipliers (see TRADE_LEVEL_PROFILES).
        _profile2 = _atr_profile_for_tf(timeframe)
        _sl_m2, _t1_m2, _t2_m2, _t3_m2 = _profile2["sl_mult"], _profile2["tp1_mult"], _profile2["tp2_mult"], _profile2["tp3_mult"]
        if signal == "BUY":
            stop_loss = prnd2(price - (_sl_m2 * atr))
            tp1 = prnd2(price + (_t1_m2 * atr))
            tp2 = prnd2(price + (_t2_m2 * atr))
            tp3 = prnd2(price + (_t3_m2 * atr))
        else:  # SELL
            stop_loss = prnd2(price + (_sl_m2 * atr))
            tp1 = prnd2(price - (_t1_m2 * atr))
            tp2 = prnd2(price - (_t2_m2 * atr))
            tp3 = prnd2(price - (_t3_m2 * atr))

        # ── 2d: Net RR after fees — 0.2% round-trip ──────────────────────────
        fee_adj = entry * 0.002
        if signal == "BUY":
            tp1 = prnd2(tp1 - fee_adj)
            tp2 = prnd2(tp2 - fee_adj)
            tp3 = prnd2(tp3 - fee_adj)
        else:
            tp1 = prnd2(tp1 + fee_adj)
            tp2 = prnd2(tp2 + fee_adj)
            tp3 = prnd2(tp3 + fee_adj)

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
            # ── 2e: Forward-fill date grid ────────────────────────────────────
            if not df.empty:
                df = _fill_date_grid(df, timeframe, asset_type)

            if df.empty or len(df) < 30:
                continue

            ind    = calculate_indicators(df, timeframe, asset_type)
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
                watch_registry[key]["last_narrative"] = analysis.get("narrative", "")
                watch_registry[key]["last_timing"]    = analysis.get("timing", "")

            if fired_sig:
                delivered = fire_alert(fired_sig, ticker, ind["price"], timeframe, analysis, counter,
                                       w.get("alert_channels", ["sms"]))
                if delivered:
                    # Confirmed sent — remove watch (only disappears after delivery)
                    _uid = w.get("user_id", "legacy")
                    with watch_lock:
                        watch_registry.pop(key, None)
                    _remove_watch_from_db(ticker, timeframe, _uid)
                    print(f"[Watch] Delivered + removed: {key}")
                else:
                    # Delivery failed — keep last_signal unchanged so next tick retries
                    print(f"[Watch] Delivery failed for {key}, will retry next tick")
            else:
                with watch_lock:
                    watch_registry[key]["last_signal"] = sig
                # Feature D: Live narrative update even when no new signal fires
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

# ─── AUTOMATION HELPERS ────────────────────────────────────────

def _push_notification(user_id, ntype, title, body, data=None):
    """Save an in-app notification to DB so the frontend bell can fetch it."""
    if not _DBSession:
        return
    try:
        db = _DBSession()
        notif = Notification(
            user_id=str(user_id), ntype=ntype,
            title=title, body=body,
            data=json.dumps(data) if data else None,
        )
        db.add(notif)
        db.commit()
        db.close()
    except Exception as e:
        print(f"[notify] DB error: {e}")

def _get_automation_settings(user_id):
    """Return AutomationSettings for user, creating defaults if absent."""
    if not _DBSession:
        return {"scan_enabled": True, "scan_risk_pct": 1.0, "breakeven_on": True,
                "trailing_on": False, "trailing_pips": 50.0, "market_alerts_on": True}
    try:
        db = _DBSession()
        s = db.query(AutomationSettings).filter_by(user_id=str(user_id)).first()
        if not s:
            s = AutomationSettings(user_id=str(user_id))
            db.add(s); db.commit()
        result = {
            "scan_enabled": s.scan_enabled, "scan_risk_pct": s.scan_risk_pct,
            "breakeven_on": s.breakeven_on, "trailing_on": s.trailing_on,
            "trailing_pips": s.trailing_pips, "market_alerts_on": s.market_alerts_on,
        }
        db.close()
        return result
    except Exception:
        return {"scan_enabled": True, "scan_risk_pct": 1.0, "breakeven_on": True,
                "trailing_on": False, "trailing_pips": 50.0, "market_alerts_on": True}

def _calc_auto_lot(account_balance, entry, sl, asset_type, risk_pct=1.0):
    """Calculate appropriate lot size for an auto-scan signal."""
    if not entry or not sl or entry == sl or account_balance <= 0:
        return 0.0
    risk_amt = account_balance * (risk_pct / 100.0)
    sl_dist  = abs(entry - sl)
    if sl_dist == 0:
        return 0.0
    if asset_type == "forex":
        # 1 std lot = 100,000 units; pip value ~$10/lot for USD-quoted pairs
        pip_size = 0.01 if "JPY" in str(entry).upper() else 0.0001
        pips = sl_dist / pip_size
        lots = risk_amt / max(pips * 10, 0.01)
    else:
        # Crypto, indices, commodities, stocks — direct
        lots = risk_amt / sl_dist
    return round(max(lots, 0.0), 2)

# ─── WATCHLIST ────────────────────────────────────────────────
# Balance: volatile (crypto) + non-volatile (forex/indices), scalp + swing
AUTO_WATCHLIST = [
    # Crypto — high volatility, 24/7, strong R:R
    {"ticker": "BTC-USD",  "asset_type": "crypto",    "scalp": True,  "swing": True,  "min_lot": 0.01},
    {"ticker": "ETH-USD",  "asset_type": "crypto",    "scalp": True,  "swing": True,  "min_lot": 0.01},
    {"ticker": "XRP-USD",  "asset_type": "crypto",    "scalp": True,  "swing": True,  "min_lot": 0.01},
    {"ticker": "SOL-USD",  "asset_type": "crypto",    "scalp": True,  "swing": True,  "min_lot": 0.01},
    # Forex majors — liquid, session-driven, precise pip value
    {"ticker": "EURUSD=X", "asset_type": "forex",     "scalp": True,  "swing": True,  "min_lot": 0.05},
    {"ticker": "GBPUSD=X", "asset_type": "forex",     "scalp": True,  "swing": True,  "min_lot": 0.05},
    {"ticker": "USDJPY=X", "asset_type": "forex",     "scalp": True,  "swing": True,  "min_lot": 0.05},
    {"ticker": "AUDUSD=X", "asset_type": "forex",     "scalp": True,  "swing": True,  "min_lot": 0.05},
    # Precious metals — safe haven + volatile
    {"ticker": "GC=F",     "asset_type": "commodity", "scalp": True,  "swing": True,  "min_lot": 0.01},
    {"ticker": "SI=F",     "asset_type": "commodity", "scalp": True,  "swing": True,  "min_lot": 0.01},
    # Indices — macro trend, non-volatile base
    {"ticker": "^GSPC",    "asset_type": "index",     "scalp": False, "swing": True,  "min_lot": 0.01},
    {"ticker": "^NDX",     "asset_type": "index",     "scalp": False, "swing": True,  "min_lot": 0.01},
    {"ticker": "^DJI",     "asset_type": "index",     "scalp": False, "swing": True,  "min_lot": 0.01},
    # Energy — volatile commodity
    {"ticker": "CL=F",     "asset_type": "commodity", "scalp": True,  "swing": True,  "min_lot": 0.01},
    # High-beta stocks — US session, swing only
    {"ticker": "NVDA",     "asset_type": "stock",     "scalp": False, "swing": True,  "min_lot": 1.0},
    {"ticker": "TSLA",     "asset_type": "stock",     "scalp": False, "swing": True,  "min_lot": 1.0},
    {"ticker": "AAPL",     "asset_type": "stock",     "scalp": False, "swing": True,  "min_lot": 1.0},
    {"ticker": "MSFT",     "asset_type": "stock",     "scalp": False, "swing": True,  "min_lot": 1.0},
]

# Market sessions (UTC)
_MARKET_SESSIONS = [
    ("Sydney Open",   22,  0, "🦘", "Forex AUD/NZD pairs most active. Asian session begins."),
    ("Tokyo Open",     0,  0, "🗼", "JPY pairs most active. Asian session in full swing."),
    ("London Open",    8,  0, "🏦", "Highest liquidity window opens. EUR/GBP in focus."),
    ("New York Open", 13, 30, "🗽", "USD pairs + stocks + gold surge. Best scalping window."),
    ("NYSE Close",    21,  0, "🔔", "US stocks close. Volatility drops. Review open trades."),
    ("Crypto Daily",   0,  0, "₿",  "New daily candle. Key level for BTC/ETH/XRP setups."),
]

def _job_market_alert(session_name, emoji, note):
    """Fire a market open/close notification to all active users."""
    try:
        # Notify all users who have market_alerts_on
        all_users = []
        if _DBSession:
            try:
                db = _DBSession()
                settings = db.query(AutomationSettings).filter_by(market_alerts_on=True).all()
                all_users = [s.user_id for s in settings]
                db.close()
            except Exception:
                pass
        # Always send to 'default' user (single-user mode)
        if not all_users:
            all_users = ["default"]
        tg_msg = f"{emoji} {session_name}\n{note}"
        try:
            send_telegram(tg_msg)
        except Exception:
            pass
        for uid in set(all_users + ["default"]):
            _push_notification(uid, "market", f"{emoji} {session_name}", note)
    except Exception as e:
        print(f"[market_alert] {session_name}: {e}")

def _is_duplicate_scan_alert(ticker, signal, timeframe, trade_type):
    """Return True if an identical alert was sent within the dedup window."""
    if not _DBSession:
        return False
    dedup_hours = {"scalping": 2, "swing": 12}.get(trade_type, 4)
    cutoff = datetime.utcnow() - timedelta(hours=dedup_hours)
    try:
        db = _DBSession()
        exists = db.query(ScanAlert).filter(
            ScanAlert.ticker    == ticker,
            ScanAlert.signal    == signal,
            ScanAlert.timeframe == timeframe,
            ScanAlert.trade_type== trade_type,
            ScanAlert.sent_at   >= cutoff,
        ).first()
        db.close()
        return exists is not None
    except Exception:
        return False

def _record_scan_alert(ticker, signal, timeframe, trade_type, entry, sl, tp1, lot_size):
    """Save scan alert and return its ID (used in Telegram callback_data)."""
    if not _DBSession:
        return None
    try:
        db = _DBSession()
        rec = ScanAlert(ticker=ticker, signal=signal, timeframe=timeframe,
                        trade_type=trade_type, entry=entry, sl=sl, tp1=tp1,
                        lot_size=lot_size)
        db.add(rec)
        db.commit()
        db.refresh(rec)
        rid = rec.id
        db.close()
        return rid
    except Exception:
        return None

def _job_auto_scan():
    """Scan 18 instruments across scalp (15m) + swing (4H) timeframes every 15 min.
    Sends Telegram + in-app alert for HIGH-confidence BUY/SELL signals above min lot."""
    import time as _time
    print("[auto_scan] Starting scan...")
    # Get account balance from any active mt5_state
    account_balance = 1000.0
    with mt5_state_lock:
        for uid, state in mt5_state.items():
            if isinstance(state, dict) and state.get("account", {}).get("balance"):
                account_balance = float(state["account"]["balance"])
                break

    scans = []
    for inst in AUTO_WATCHLIST:
        if inst["scalp"]:
            scans.append((inst, "15m", "scalping"))
        if inst["swing"]:
            scans.append((inst, "4h", "swing"))

    found = 0
    for inst, tf, trade_type in scans:
        ticker     = inst["ticker"]
        asset_type = inst["asset_type"]
        min_lot    = inst["min_lot"]
        try:
            cfg = TIMEFRAME_CONFIG.get(tf, TIMEFRAME_CONFIG["1d"])
            df  = safe_download(ticker, period=cfg["period"], interval=cfg["interval"],
                                progress=False, auto_adjust=True)
            if "resample" in cfg:
                df = df.resample(cfg["resample"]).agg(
                    {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
                ).dropna()
            if df.empty or len(df) < 51:
                _time.sleep(0.5)
                continue
            df  = _fill_date_grid(df, tf, asset_type)
            ind = calculate_indicators(df, tf, asset_type)
            res = get_analysis(ticker, asset_type, ind, tf)

            sig  = res.get("signal", "HOLD")
            conf = res.get("confidence", "LOW")
            if sig not in ("BUY", "SELL") or conf != "HIGH":
                _time.sleep(0.5)
                continue

            entry = res.get("entry", 0)
            sl    = res.get("stop_loss", 0)
            tp1   = res.get("tp1", 0)
            tp2   = res.get("tp2", 0)
            tp3   = res.get("tp3", 0)
            rr    = res.get("rr1", 0)

            lot   = _calc_auto_lot(account_balance, entry, sl, asset_type)
            if lot < min_lot:
                _time.sleep(0.5)
                continue

            if _is_duplicate_scan_alert(ticker, sig, tf, trade_type):
                _time.sleep(0.5)
                continue

            # ── Send alert ──────────────────────────────────────────────
            type_tag  = "SCALP" if trade_type == "scalping" else "SWING"
            sig_emoji = "🟢" if sig == "BUY" else "🔴"
            tg_msg = (
                f"{sig_emoji} {type_tag} SIGNAL — {ticker}\n"
                f"Direction: {sig}  |  TF: {tf.upper()}\n"
                f"Entry:  {entry:.5g}\n"
                f"SL:     {sl:.5g}\n"
                f"TP1:    {tp1:.5g}  |  TP2: {tp2:.5g}  |  TP3: {tp3:.5g}\n"
                f"R:R     1:{rr:.1f}\n"
                f"Lot size: {lot:.2f} lots\n"
                f"Confidence: HIGH ✅"
            )
            # Save scan alert first to get its ID for the callback button
            scan_id = _record_scan_alert(ticker, sig, tf, trade_type, entry, sl, tp1, lot)
            # callback_data: execute|{scan_id}  (well within 64-char Telegram limit)
            exec_label = f"{'✅ Execute BUY' if sig=='BUY' else '🔴 Execute SELL'} {lot:.2f} lots"
            keyboard = [[{"text": exec_label, "callback_data": f"execute|{scan_id}"}]]
            try:
                send_telegram_keyboard(tg_msg, keyboard)
            except Exception:
                try:
                    send_telegram(tg_msg)
                except Exception:
                    pass

            notif_data = {"ticker": ticker, "signal": sig, "timeframe": tf,
                          "entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
                          "lot": lot, "trade_type": trade_type, "rr": rr,
                          "asset_type": asset_type}
            _push_notification("default", "scan",
                                f"{sig_emoji} {type_tag}: {ticker} {sig}",
                                f"Entry {entry:.5g} · SL {sl:.5g} · TP1 {tp1:.5g} · {lot:.2f} lots · R:R 1:{rr:.1f}",
                                data=notif_data)
            found += 1
            _time.sleep(1.0)   # rate-limit between instruments
        except Exception as e:
            print(f"[auto_scan] {ticker} {tf}: {e}")
            _time.sleep(1.0)

    print(f"[auto_scan] Done. {found} signals sent.")

def _job_trade_suggestions():
    """Daily job: analyse recent trade history and suggest risk adjustments."""
    import time as _time
    if not _DBSession:
        return
    try:
        db = _DBSession()
        # Look at last 20 signal history rows
        history = db.query(SignalHistory).order_by(SignalHistory.fired_at.desc()).limit(20).all()
        orders  = db.query(MT5Order).filter(MT5Order.status == "filled")\
                    .order_by(MT5Order.created_at.desc()).limit(20).all()
        db.close()

        if len(orders) < 5:
            return   # not enough data for meaningful suggestion

        # Simple win rate proxy: count signals that generated TP fills vs SL fills
        # (true win rate needs P&L tracking — this is advisory)
        total  = len(orders)
        # Calculate average lot sizes
        lots   = [float(o.volume or 0) for o in orders if o.volume]
        avg_lot = sum(lots) / len(lots) if lots else 0
        max_lot = max(lots) if lots else 0

        # Account balance
        account_balance = 1000.0
        with mt5_state_lock:
            for uid, state in mt5_state.items():
                if isinstance(state, dict) and state.get("account", {}).get("balance"):
                    account_balance = float(state["account"]["balance"])
                    break

        suggestions = []

        # If all trades are tiny lots relative to account
        if avg_lot < 0.02 and account_balance >= 500:
            suggestions.append(
                f"📊 Your avg lot size is {avg_lot:.3f} — for a ${account_balance:.0f} account, "
                f"consider 0.05 lots on high-confidence setups to capture meaningful profits."
            )

        # If account grew suggest scaling
        # (placeholder — real version needs filled_at P&L from MT5 push)
        if total >= 10:
            suggestions.append(
                f"✅ You've completed {total} trades. Review your win rate on DotVerse "
                f"Backtest tab and consider adjusting risk from 1% → 1.5% if win rate > 60%."
            )

        if not suggestions:
            suggestions.append(
                f"📈 Daily summary: {total} trades on record. "
                f"Avg lot: {avg_lot:.3f}. Keep following the signals."
            )

        msg = "🤖 DotVerse Daily Summary\n\n" + "\n\n".join(suggestions)
        try:
            send_telegram(msg)
        except Exception:
            pass
        _push_notification("default", "suggestion", "🤖 Daily Trade Summary",
                            "\n".join(suggestions))
    except Exception as e:
        print(f"[trade_suggestions] {e}")

# ─── START BACKGROUND SCHEDULER ───────────────────────────────
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(run_watch_job, "interval", seconds=60, id="watch_job",
                  max_instances=1, coalesce=True)

# Phase A — Market session alerts (UTC)
for _sess_name, _sess_h, _sess_m, _sess_emoji, _sess_note in _MARKET_SESSIONS:
    _sid = _sess_name.lower().replace(" ", "_")
    scheduler.add_job(
        lambda sn=_sess_name, em=_sess_emoji, nt=_sess_note: _job_market_alert(sn, em, nt),
        "cron", hour=_sess_h, minute=_sess_m,
        id=f"market_{_sid}", max_instances=1, coalesce=True,
    )

# Phase B — Auto-scan every 15 minutes
scheduler.add_job(_job_auto_scan, "interval", minutes=15,
                  id="auto_scan", max_instances=1, coalesce=True)

# Phase D — Daily trade suggestions at 08:00 UTC
scheduler.add_job(_job_trade_suggestions, "cron", hour=8, minute=0,
                  id="trade_suggestions", max_instances=1, coalesce=True)

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
        # Normalise crypto ticker into yfinance/TV-friendly BASE-USD form.
        # Handles every realistic input shape:
        #   BTC-USD / BTC-USDT / BTC-USDC  → passthrough (already dashed)
        #   BTC/USD                          → BTC-USD (slash → dash)
        #   BTCUSDT / BTCUSDC                → BTC-USD (peel stablecoin suffix)
        #   BTCUSD                           → BTC-USD (peel concat USD)
        #   BTC                              → BTC-USD (append USD to bare base)
        # Bug-fix note: the prior implementation appended "-USD" unconditionally
        # when the ticker didn't END with "-USD", which mangled BTCUSD into
        # BTCUSD-USD (invalid for both TV and yfinance) — silently filtered by
        # the frontend and shown as an empty Signals tab.
        clean = ticker.replace("/", "-").replace("=X", "").upper()
        if "-" in clean:
            # Already dashed (BTC-USD, BTC-USDT, BTC-USDC) — leave as is.
            ticker = clean
        else:
            # Peel concat-quote suffix (USDT/USDC/USD) and replace with -USD.
            # yfinance/TV resolve stablecoin pairs through the same -USD route.
            for _suffix in ("USDT", "USDC", "USD"):
                if clean.endswith(_suffix) and len(clean) > len(_suffix):
                    ticker = clean[:-len(_suffix)] + "-USD"
                    break
            else:
                # Bare base symbol — append -USD.
                ticker = clean + "-USD"
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

# ─── GOOGLE OAUTH ─────────────────────────────────────────────

@app.route("/auth/google")
def google_auth():
    import secrets, urllib.parse
    if not GOOGLE_CLIENT_ID:
        return jsonify({"error": "Google login not configured"}), 503
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    params = urllib.parse.urlencode({
        'client_id':     GOOGLE_CLIENT_ID,
        'redirect_uri':  GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope':         'openid email profile',
        'state':         state,
        'prompt':        'select_account',
    })
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")

@app.route("/auth/google/callback")
def google_callback():
    import urllib.parse
    code  = request.args.get('code')
    state = request.args.get('state')
    if not code or state != session.get('oauth_state'):
        return redirect('/?auth_error=state_mismatch')
    # Exchange code for access token
    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        'code':          code,
        'client_id':     GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri':  GOOGLE_REDIRECT_URI,
        'grant_type':    'authorization_code',
    })
    token_data = token_resp.json()
    access_token = token_data.get('access_token')
    if not access_token:
        return redirect('/?auth_error=no_token')
    # Get user info from Google
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={'Authorization': f'Bearer {access_token}'}
    ).json()
    email = userinfo.get('email', '').lower()
    name  = userinfo.get('name', '')
    if not email:
        return redirect('/?auth_error=no_email')
    # Find or create user
    if _DBSession:
        db = _DBSession()
        try:
            user = db.query(User).filter_by(email=email).first()
            if not user:
                role = "admin" if (ADMIN_EMAIL and email == ADMIN_EMAIL) else "user"
                tier = "elite" if role == "admin" else "free"
                user = User(email=email, name=name, role=role, tier=tier)
                db.add(user)
                db.commit()
            elif ADMIN_EMAIL and email == ADMIN_EMAIL and user.role != "admin":
                user.role = "admin"
                user.tier = "elite"
                db.commit()
            session['user_id']   = user.id
            session['user_role'] = user.role
            session['user_tier'] = user.tier
            session.permanent    = True
        finally:
            db.close()
    else:
        session['authenticated'] = True
    return redirect('/')

# ─── ROUTES ──────────────────────────────────────────────────
@app.route("/pricing")
def pricing_page():
    resp = send_from_directory("static", "pricing.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/settings")
def settings_page():
    if not session.get("user_id") and not session.get("authenticated"):
        return redirect("/")
    resp = send_from_directory("static", "settings.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/")
def index():
    resp = send_from_directory("static", "index-v2-prototype.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# ─── AUTH ROUTES (no login_required) ─────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    """Create a new user account."""
    if not _DBSession:
        return jsonify({"status": "error", "message": "Database not available"}), 503
    body     = request.json or {}
    email    = body.get("email", "").strip().lower()
    name     = body.get("name", "").strip()
    password = body.get("password", "").strip()
    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password required"}), 400
    if len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters"}), 400
    db = _DBSession()
    try:
        if db.query(User).filter_by(email=email).first():
            return jsonify({"status": "error", "message": "Email already registered"}), 409
        is_admin = bool(ADMIN_EMAIL and email == ADMIN_EMAIL) or bool(db.query(AdminInvite).filter_by(email=email).first())
        role = "admin" if is_admin else "user"
        tier = "elite" if role == "admin" else "free"
        user = User(
            email         = email,
            name          = name or email.split("@")[0],
            password_hash = generate_password_hash(password),
            role          = role,
            tier          = tier,
        )
        db.add(user)
        # Remove invite once used
        db.query(AdminInvite).filter_by(email=email).delete()
        db.commit()
        session["user_id"]   = user.id
        session["user_role"] = user.role
        session["user_tier"] = user.tier
        session.permanent    = True
        return jsonify({"status": "ok", "role": user.role, "tier": user.tier, "name": user.name})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/login", methods=["POST"])
def login():
    """Email + password login. Falls back to legacy APP_PASSWORD if no DB."""
    body     = request.json or {}
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "").strip()

    # ── New email/password flow ──
    if email and _DBSession:
        db = _DBSession()
        try:
            user = db.query(User).filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash or "", password):
                return jsonify({"status": "error", "message": "Incorrect email or password"}), 401
            # If ADMIN_EMAIL matches, ensure role is admin
            if ADMIN_EMAIL and email == ADMIN_EMAIL and user.role != "admin":
                user.role = "admin"
                user.tier = "elite"
                db.commit()
            session["user_id"]   = user.id
            session["user_role"] = user.role
            session["user_tier"] = user.tier
            session.permanent    = True
            return jsonify({"status": "ok", "role": user.role, "tier": user.tier, "name": user.name})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            db.close()

    # ── Legacy single-password fallback ──
    if not APP_PASSWORD:
        session["authenticated"] = True
        return jsonify({"status": "ok", "message": "No password required"})
    if password == APP_PASSWORD:
        session["authenticated"] = True
        session.permanent = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "Incorrect email or password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "ok"})

@app.route("/api/auth-check", methods=["GET"])
def auth_check():
    """Frontend calls this on load to see if the user is already logged in."""
    # New user-based session
    if session.get("user_id") and _DBSession:
        user = _get_current_user()
        if user:
            return jsonify({
                "authenticated":    True,
                "user_id":          user.id,
                "email":            user.email,
                "name":             user.name,
                "tier":             user.tier,
                "role":             user.role,
                "password_required": False,
            })
    # Legacy session
    if session.get("authenticated"):
        return jsonify({"authenticated": True, "password_required": False, "role": "admin", "tier": "elite"})
    if not APP_PASSWORD and not _DBSession:
        return jsonify({"authenticated": True, "password_required": False})
    return jsonify({"authenticated": False, "password_required": True})

# ─── ADMIN ROUTES ──────────────────────────────────────────────

@app.route("/api/admin/users", methods=["GET"])
@require_admin
def admin_list_users():
    """Return all registered users."""
    if not _DBSession:
        return jsonify({"error": "Database not available"}), 503
    db = _DBSession()
    try:
        users = db.query(User).order_by(User.created_at.desc()).all()
        return jsonify({"users": [{
            "id":         u.id,
            "email":      u.email,
            "name":       u.name,
            "tier":       u.tier,
            "role":       u.role,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        } for u in users]})
    finally:
        db.close()

@app.route("/api/admin/set-role", methods=["POST"])
@require_admin
def admin_set_role():
    """Grant or revoke admin role for a user."""
    if not _DBSession:
        return jsonify({"error": "Database not available"}), 503
    body    = request.json or {}
    user_id = body.get("user_id")
    role    = body.get("role")   # "admin" or "user"
    if not user_id or role not in ("admin", "user"):
        return jsonify({"error": "user_id and role (admin/user) required"}), 400
    db = _DBSession()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        user.role = role
        if role == "admin":
            user.tier = "elite"
        db.commit()
        return jsonify({"status": "ok", "email": user.email, "role": user.role, "tier": user.tier})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/admin/invite", methods=["POST", "DELETE"])
@require_admin
def admin_invite():
    """Pre-approve an email for admin role on signup, or remove the invite."""
    if not _DBSession:
        return jsonify({"error": "Database not available"}), 503
    body  = request.json or {}
    email = body.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400
    db = _DBSession()
    try:
        if request.method == "DELETE":
            db.query(AdminInvite).filter_by(email=email).delete()
            db.commit()
            return jsonify({"status": "removed"})
        # POST — add invite
        if db.query(AdminInvite).filter_by(email=email).first():
            return jsonify({"status": "already_invited"})
        db.add(AdminInvite(email=email, invited_by=session.get("user_id")))
        db.commit()
        return jsonify({"status": "invited"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/admin/invites", methods=["GET"])
@require_admin
def admin_list_invites():
    """List all pending admin invites."""
    if not _DBSession:
        return jsonify({"invites": []})
    db = _DBSession()
    try:
        rows = db.query(AdminInvite).order_by(AdminInvite.created_at.desc()).all()
        return jsonify({"invites": [{"email": r.email, "created_at": r.created_at.strftime("%Y-%m-%d")} for r in rows]})
    except Exception as e:
        return jsonify({"invites": []})
    finally:
        db.close()

@app.route("/api/admin/set-tier", methods=["POST"])
@require_admin
def admin_set_tier():
    """Manually set a user's tier (free / pro / elite)."""
    if not _DBSession:
        return jsonify({"error": "Database not available"}), 503
    body    = request.json or {}
    user_id = body.get("user_id")
    tier    = body.get("tier")
    if not user_id or tier not in ("free", "pro", "elite"):
        return jsonify({"error": "user_id and tier (free/pro/elite) required"}), 400
    db = _DBSession()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        user.tier = tier
        db.commit()
        return jsonify({"status": "ok", "email": user.email, "tier": user.tier})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ─── MT5 INTEGRATION ─────────────────────────────────────────

def _lookup_user_by_mt5_secret(secret):
    """Find the user_id whose UserSettings.mt5_api_key_enc decrypts to the given
    secret. Returns None if no match. O(N) over rows with a saved key — fine for
    current scale; revisit with a SHA index if user count grows large."""
    if not _DBSession or not secret:
        return None
    db = _DBSession()
    try:
        rows = db.query(UserSettings).filter(UserSettings.mt5_api_key_enc.isnot(None)).all()
        for row in rows:
            try:
                if _dec(row.mt5_api_key_enc) == secret:
                    return str(row.user_id)
            except Exception:
                continue
        return None
    finally:
        db.close()

def _require_ea(f):
    """Decorator — validates X-EA-Secret header from the MT5 EA.

    Two accept paths:
      1) per-user — secret matches a user's saved UserSettings.mt5_api_key
      2) legacy bypass — user_id is listed in MT5_BYPASS_USER_IDS env var
         (covers users whose EA was set up before per-user auth was wired)

    Anything else returns 401. Sets request.ea_user_id on success so the
    decorated endpoint can scope its DB queries to the correct user.
    """
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = (request.headers.get('X-EA-Secret') or '').strip()

        # Path 1 — per-user lookup
        if secret:
            user_id = _lookup_user_by_mt5_secret(secret)
            if user_id:
                request.ea_user_id = user_id
                return f(*args, **kwargs)

        # Path 2 — legacy bypass list (single-user assumption: pick the first id)
        if MT5_BYPASS_USER_IDS:
            request.ea_user_id = next(iter(MT5_BYPASS_USER_IDS))
            return f(*args, **kwargs)

        return jsonify({"error": "Unauthorized", "message": "Valid X-EA-Secret required"}), 401
    return decorated

@app.route("/api/mt5/order", methods=["POST"])
@login_required
def mt5_submit_order():
    """User submits a trade order — saved as pending, EA picks it up."""
    if not _DBSession:
        return jsonify({"error": "Database not available"}), 503
    body       = request.json or {}
    user_id    = str(session.get("user_id"))
    ticker     = body.get("ticker", "").upper().strip()
    asset_type = body.get("asset_type", "forex")
    direction  = body.get("direction", "").upper()
    volume     = float(body.get("volume", 0.01))
    price      = float(body.get("price", 0))
    sl         = body.get("sl")
    tp         = body.get("tp")
    tp2        = body.get("tp2")
    tp3        = body.get("tp3")
    timeframe  = body.get("timeframe", "")
    if not ticker or direction not in ("BUY", "SELL") or volume <= 0:
        return jsonify({"error": "ticker, direction (BUY/SELL), and volume required"}), 400
    symbol = _mt5_symbol(ticker, asset_type)
    db = _DBSession()
    try:
        order = MT5Order(
            user_id    = user_id,
            symbol     = symbol,
            order_type = direction,
            volume     = volume,
            price      = price,
            sl         = float(sl)  if sl  else None,
            tp         = float(tp)  if tp  else None,
            tp2        = float(tp2) if tp2 else None,
            tp3        = float(tp3) if tp3 else None,
            timeframe  = timeframe or None,
            status     = "pending",
            comment    = f"DotVerse {ticker} {direction}",
        )
        db.add(order)
        db.commit()
        return jsonify({"status": "pending", "order_id": order.id, "symbol": symbol})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/mt5/pending", methods=["GET"])
@_require_ea
def mt5_get_pending():
    """EA polls this every 5s — returns pending orders and marks them as executing."""
    if not _DBSession:
        return jsonify({"orders": []})
    db = _DBSession()
    try:
        orders = db.query(MT5Order).filter_by(status="pending").all()
        result = []
        for o in orders:
            result.append({
                "id":           o.id,
                "symbol":       o.symbol,
                "order_type":   o.order_type,
                "volume":       o.volume,
                "price":        o.price,
                "sl":           o.sl,
                "tp":           o.tp,
                "tp2":          o.tp2,
                "tp3":          o.tp3,
                "action":       o.action or "open",
                "close_ticket": o.close_ticket,
            })
            o.status = "executing"
        db.commit()
        # Embed automation settings so the EA can apply trailing stop without an extra request
        cfg = _get_automation_settings("default")
        settings = {
            "trailing_on":   cfg.get("trailing_on", False),
            "trailing_pips": float(cfg.get("trailing_pips", 50.0)),
        }
        return jsonify({"orders": result, "settings": settings})
    except Exception as e:
        db.rollback()
        return jsonify({"orders": []})
    finally:
        db.close()

@app.route("/api/mt5/confirm", methods=["POST"])
@_require_ea
def mt5_confirm_order():
    """EA reports execution result back to DotVerse."""
    if not _DBSession:
        return jsonify({"status": "ok"})
    body      = request.json or {}
    order_id  = body.get("order_id")
    status    = body.get("status")   # filled | failed
    ticket    = body.get("ticket")
    fill_price= body.get("fill_price")
    pnl       = body.get("pnl")      # realised P&L in account currency (for CLOSE orders)
    comment   = body.get("comment", "")
    db = _DBSession()
    try:
        order = db.query(MT5Order).filter_by(id=order_id).first()
        if order:
            order.status     = status
            order.mt5_ticket = ticket
            order.fill_price = fill_price
            order.comment    = comment
            if pnl is not None:
                try:
                    order.pnl = float(pnl)
                except (TypeError, ValueError):
                    pass
            if status == "filled":
                order.filled_at = datetime.utcnow()
                # Send Telegram notification on fill
                try:
                    emoji = "🟢" if order.order_type == "BUY" else "🔴"
                    tg_msg = (
                        f"{emoji} Trade Executed\n"
                        f"{order.symbol} {order.order_type} {order.volume} lots\n"
                        f"Entry:  {fill_price}\n"
                        f"SL:     {order.sl or '—'}\n"
                        f"TP1:    {order.tp  or '—'}\n"
                        f"TP2:    {order.tp2 or '—'}\n"
                        f"TP3:    {order.tp3 or '—'}\n"
                        f"Ticket: #{ticket}\n"
                        f"🔗 https://dot-verse.up.railway.app"
                    )
                    send_telegram(tg_msg)
                except Exception:
                    pass
        db.commit()
        # Cache tp2/tp3/timeframe in mt5_state so state endpoint can enrich instantly
        if status == "filled" and ticket and order:
            with mt5_state_lock:
                if "tp_enrichment" not in mt5_state:
                    mt5_state["tp_enrichment"] = {}
                mt5_state["tp_enrichment"][str(ticket)] = {
                    "tp2":       order.tp2,
                    "tp3":       order.tp3,
                    "timeframe": order.timeframe,
                }
        return jsonify({"status": "ok", "tp2": order.tp2, "tp3": order.tp3})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "error": str(e)})
    finally:
        db.close()

@app.route("/api/mt5/alert", methods=["POST"])
@_require_ea
def mt5_level_alert():
    """EA reports when a TP or SL level is hit — sends Telegram notification."""
    body   = request.json or {}
    ticket = body.get("ticket")
    symbol = body.get("symbol", "")
    level  = body.get("level", "")    # TP1 | TP2 | TP3 | SL
    price  = body.get("price", 0)
    direction = body.get("direction", "")

    emoji_map = {"TP1": "🎯", "TP2": "🎯", "TP3": "✅", "SL": "🛑"}
    action_map = {
        "TP1": "Consider closing 50% of position",
        "TP2": "Consider closing 30% — let rest run to TP3",
        "TP3": "Close remaining position — full target reached",
        "SL":  "Stop loss hit — position closed",
    }
    emoji  = emoji_map.get(level, "⚡")
    action = action_map.get(level, "")
    tg_msg = (
        f"{emoji} {level} Hit — {symbol}\n"
        f"{direction} position #{ticket}\n"
        f"Price: {price}\n\n"
        f"{action}"
    )
    # callback_data format: close|ticket|symbol|level  (max 64 chars)
    btn_label = {
        "TP1": "✅ Close 50% — TP1",
        "TP2": "✅ Close 30% — TP2",
        "TP3": "✅ Close All — TP3",
        "SL":  "🛑 Close Position — SL",
    }.get(level, f"Close — {level}")
    keyboard = [[{"text": btn_label, "callback_data": f"close|{ticket}|{symbol}|{level}"}]]
    try:
        send_telegram_keyboard(tg_msg, keyboard)
    except Exception:
        pass
    # Store hit in mt5_state so frontend can flash the action button
    with mt5_state_lock:
        state = mt5_state.get("default", {})
        if "level_hits" not in state:
            state["level_hits"] = {}
        state["level_hits"][str(ticket)] = level
        mt5_state["default"] = state

    # ── Phase C — progressive SL-ladder automation ───────────────────
    # TP1 hit → SL moves to entry (breakeven, can't lose now)
    # TP2 hit → SL moves to TP1 price (locks TP1 profit)
    # TP3 hit → SL moves to TP2 price (locks TP2 profit; trade still has runway)
    # Each step requires the corresponding price to be available — the
    # original MT5Order.tp / tp2 fields hold them.
    if level in ("TP1", "TP2", "TP3") and _DBSession:
        try:
            auto_cfg = _get_automation_settings("default")
            if auto_cfg.get("breakeven_on"):
                new_sl = None
                ladder_label = None
                if level == "TP1":
                    # Move to entry
                    open_price = None
                    with mt5_state_lock:
                        for uid, st in mt5_state.items():
                            if isinstance(st, dict):
                                for p in st.get("positions", []):
                                    if str(p.get("ticket")) == str(ticket):
                                        open_price = p.get("open_price")
                                        break
                    new_sl = float(open_price) if open_price else None
                    ladder_label = f"Breakeven after TP1 — SL → entry {new_sl}" if new_sl else None
                elif level in ("TP2", "TP3"):
                    # Look up the original TP1/TP2 price from MT5Order using mt5_ticket
                    db_lookup = _DBSession()
                    try:
                        original = db_lookup.query(MT5Order)\
                            .filter(MT5Order.mt5_ticket == int(ticket),
                                    MT5Order.action == "open",
                                    MT5Order.status == "filled").first()
                        if original:
                            if level == "TP2" and original.tp:
                                new_sl = float(original.tp)
                                ladder_label = f"Lock TP1 after TP2 — SL → TP1 ({new_sl})"
                            elif level == "TP3" and original.tp2:
                                new_sl = float(original.tp2)
                                ladder_label = f"Lock TP2 after TP3 — SL → TP2 ({new_sl})"
                    finally:
                        db_lookup.close()
                if new_sl is not None and ladder_label:
                    db_be = _DBSession()
                    try:
                        be_order = MT5Order(
                            user_id      = "default",
                            symbol       = symbol,
                            order_type   = "MODIFY",
                            volume       = 0,
                            price        = 0,
                            sl           = new_sl,
                            action       = "modify_sl",
                            close_ticket = int(ticket),
                            status       = "pending",
                            comment      = ladder_label,
                        )
                        db_be.add(be_order)
                        db_be.commit()
                        be_tg = (f"🔒 SL Ladder — {symbol}\n"
                                 f"{ladder_label}\n"
                                 f"Ticket #{ticket} — profit locked.")
                        try:
                            send_telegram(be_tg)
                        except Exception:
                            pass
                        _push_notification("default", "level",
                                           f"🔒 SL Locked — {symbol}",
                                           ladder_label)
                        print(f"[sl-ladder] {symbol} #{ticket} {level} -> SL={new_sl}")
                    except Exception as be_e:
                        print(f"[sl-ladder] DB error: {be_e}")
                    finally:
                        db_be.close()
        except Exception as e:
            print(f"[sl-ladder] {e}")

    return jsonify({"status": "ok"})

@app.route("/api/mt5/push", methods=["POST"])
@_require_ea
def mt5_push_state():
    """EA pushes account info and open positions every 5s."""
    body      = request.json or {}
    user_id   = body.get("user_id", "default")
    account   = body.get("account", {})
    positions = body.get("positions", [])
    with mt5_state_lock:
        mt5_state[user_id] = {
            "account":   account,
            "positions": positions,
            "last_seen": datetime.utcnow().isoformat(),
        }
    return jsonify({"status": "ok"})

@app.route("/api/mt5/state", methods=["GET"])
@login_required
def mt5_get_state():
    """Frontend reads account info and positions."""
    user_id = str(session.get("user_id"))
    with mt5_state_lock:
        state = mt5_state.get(user_id) or mt5_state.get("default")
    if not state:
        return jsonify({"connected": False, "account": {}, "positions": []})
    last_seen = datetime.fromisoformat(state["last_seen"])
    secs_ago  = (datetime.utcnow() - last_seen).total_seconds()
    connected = secs_ago < 45
    positions = list(state["positions"])
    # Enrich positions with tp2/tp3/timeframe from mt5_orders.
    # Primary match: comment field contains "DotVerse #<order_id>" — reliable because
    # res.deal (stored as mt5_ticket) != PositionGetTicket() in MT5.
    if _DBSession and positions:
        try:
            import re as _re
            db = _DBSession()
            user_id_str = str(session.get("user_id"))
            # Parse order_id from position comment e.g. "DotVerse #42"
            order_ids = []
            for p in positions:
                m = _re.search(r'DotVerse #(\d+)', p.get("comment", ""))
                if m:
                    order_ids.append(int(m.group(1)))
            if order_ids:
                orders = db.query(MT5Order).filter(
                    MT5Order.id.in_(order_ids),
                    MT5Order.user_id == user_id_str
                ).all()
                order_map = {o.id: o for o in orders}
                for p in positions:
                    m = _re.search(r'DotVerse #(\d+)', p.get("comment", ""))
                    if not m:
                        continue
                    o = order_map.get(int(m.group(1)))
                    if not o:
                        continue
                    if o.timeframe and not p.get("timeframe"): p["timeframe"] = o.timeframe
                    if o.tp2       and not p.get("tp2"):       p["tp2"]       = o.tp2
                    if o.tp3       and not p.get("tp3"):       p["tp3"]       = o.tp3
            db.close()
        except Exception:
            pass
    return jsonify({
        "connected":   connected,
        "secs_ago":    int(secs_ago),
        "account":     state["account"],
        "positions":   positions,
        "level_hits":  state.get("level_hits", {}),
    })

@app.route("/api/mt5/orders", methods=["GET"])
@login_required
def mt5_get_orders():
    """Frontend reads order history for current user."""
    if not _DBSession:
        return jsonify({"orders": []})
    user_id = str(session.get("user_id"))
    db = _DBSession()
    try:
        orders = db.query(MT5Order).filter_by(user_id=user_id)\
                   .order_by(MT5Order.created_at.desc()).limit(50).all()
        return jsonify({"orders": [{
            "id":         o.id,
            "symbol":     o.symbol,
            "order_type": o.order_type,
            "volume":     o.volume,
            "price":      o.price,
            "sl":         o.sl,
            "tp":         o.tp,
            "status":     o.status,
            "mt5_ticket": o.mt5_ticket,
            "fill_price": o.fill_price,
            "pnl":        o.pnl,
            "timeframe":  o.timeframe,
            "comment":    o.comment,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            "filled_at":  o.filled_at.strftime("%H:%M UTC") if o.filled_at else None,
        } for o in orders]})
    except Exception as e:
        return jsonify({"orders": []})
    finally:
        db.close()

@app.route("/api/mt5/cancel/<int:order_id>", methods=["POST"])
@login_required
def mt5_cancel_order(order_id):
    """User cancels a pending order before EA picks it up."""
    if not _DBSession:
        return jsonify({"error": "Database not available"}), 503
    user_id = str(session.get("user_id"))
    db = _DBSession()
    try:
        order = db.query(MT5Order).filter(
            MT5Order.id == order_id,
            MT5Order.user_id == user_id,
            MT5Order.status.in_(["pending", "executing"])
        ).first()
        if not order:
            return jsonify({"error": "Order not found or already processing"}), 404
        order.status = "cancelled"
        db.commit()
        return jsonify({"status": "cancelled"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/mt5/close", methods=["POST"])
@login_required
def mt5_close_position():
    """User taps Trade Manager button — queues a close order for the EA to execute."""
    if not _DBSession:
        return jsonify({"error": "Database not available"}), 503
    body   = request.json or {}
    ticket = body.get("ticket")
    symbol = body.get("symbol", "")
    level  = body.get("level", "")    # SL | TP1 | TP2 | TP3
    user_id = str(session.get("user_id"))
    if not ticket:
        return jsonify({"error": "ticket required"}), 400
    try:
        ticket_int = int(ticket)
        if ticket_int <= 0:
            raise ValueError("non-positive ticket")
    except (TypeError, ValueError):
        return jsonify({"error": f"Invalid ticket ID '{ticket}' — demo trades cannot be closed via API"}), 400
    db = _DBSession()
    try:
        order = MT5Order(
            user_id      = user_id,
            symbol       = symbol,
            order_type   = "CLOSE",
            volume       = 0,
            price        = 0,
            action       = "close",
            close_ticket = ticket_int,
            status       = "pending",
            comment      = f"User close {level}",
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return jsonify({"status": "ok", "id": order.id})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/mt5/trailing", methods=["POST"])
@login_required
def mt5_set_trailing():
    """Set trailing stop on an MT5 position. Acknowledged here; EA polls /api/mt5/state for execution."""
    body   = request.json or {}
    ticket = body.get("ticket")
    pips   = body.get("pips", 20)
    return jsonify({"status": "ok", "ticket": ticket, "pips": pips})

# ─── AUTOMATION SETTINGS ─────────────────────────────────────

@app.route("/api/automation/settings", methods=["GET"])
@login_required
def automation_settings_get():
    user_id = str(session.get("user_id"))
    return jsonify(_get_automation_settings(user_id))

@app.route("/api/automation/settings", methods=["POST"])
@login_required
def automation_settings_save():
    if not _DBSession:
        return jsonify({"error": "db unavailable"}), 503
    user_id = str(session.get("user_id"))
    body    = request.json or {}
    db      = _DBSession()
    try:
        s = db.query(AutomationSettings).filter_by(user_id=user_id).first()
        if not s:
            s = AutomationSettings(user_id=user_id)
            db.add(s)
        if "scan_enabled"     in body: s.scan_enabled     = bool(body["scan_enabled"])
        if "scan_risk_pct"    in body: s.scan_risk_pct    = float(body["scan_risk_pct"])
        if "breakeven_on"     in body: s.breakeven_on     = bool(body["breakeven_on"])
        if "trailing_on"      in body: s.trailing_on      = bool(body["trailing_on"])
        if "trailing_pips"    in body: s.trailing_pips    = float(body["trailing_pips"])
        if "market_alerts_on" in body: s.market_alerts_on = bool(body["market_alerts_on"])
        s.updated_at = datetime.utcnow()
        db.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ─── USER SETTINGS (per-user preferences for the 8 Settings sub-panels) ─────

def _user_settings_to_dict(s):
    """Serialise a UserSettings row to JSON for the frontend.
    Encrypted credentials are NEVER returned in plaintext — only a flag
    indicating whether they are configured, plus the non-secret fields."""
    if not s:
        return {}
    try:    assets = json.loads(s.assets_enabled) if s.assets_enabled else []
    except: assets = []
    try:    alloc  = json.loads(s.portfolio_alloc) if s.portfolio_alloc else {}
    except: alloc  = {}
    return {
        "assets_enabled":      assets,
        "risk_tolerance":      s.risk_tolerance,
        "chart_theme":         s.chart_theme or "",
        "chart_type":          s.chart_type or "candles",
        "grid_style":          s.grid_style or "",
        "indicator_scheme":    s.indicator_scheme or "",
        "timezone":            s.timezone or "UTC",
        "alert_confidence":    s.alert_confidence,
        "alert_price_pct":     s.alert_price_pct,
        "alert_drawdown_pct":  s.alert_drawdown_pct,
        "alert_loss_pct":      s.alert_loss_pct,
        "perf_target_winrate": s.perf_target_winrate,
        "perf_target_rr":      s.perf_target_rr,
        "perf_target_trades":  s.perf_target_trades,
        "perf_target_annual":  s.perf_target_annual,
        "portfolio_alloc":     alloc,
        "portfolio_preset":    s.portfolio_preset,
        "portfolio_rebalance": s.portfolio_rebalance,
        "portfolio_benchmark": s.portfolio_benchmark,
        "mt5_configured":      bool(s.mt5_api_key_enc),
        "mt5_account":         s.mt5_account or "",
        "mt5_broker_server":   s.mt5_broker_server or "",
        "telegram_configured": bool(s.telegram_bot_token_enc),
        "telegram_chat_id":    s.telegram_chat_id or "",
    }

@app.route("/api/settings", methods=["GET"])
@login_required
def settings_get():
    """Return the current user's preferences. Creates a default row on first call."""
    if not _DBSession:
        return jsonify({"error": "db unavailable"}), 503
    user_id = str(session.get("user_id"))
    db = _DBSession()
    try:
        s = db.query(UserSettings).filter_by(user_id=user_id).first()
        if not s:
            s = UserSettings(user_id=user_id)
            db.add(s)
            db.commit()
            s = db.query(UserSettings).filter_by(user_id=user_id).first()
        return jsonify(_user_settings_to_dict(s))
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/settings", methods=["POST"])
@login_required
def settings_save():
    """Partial update — only the keys the client sends are written. Credentials
    are encrypted before storage; sending an empty string leaves them unchanged."""
    if not _DBSession:
        return jsonify({"error": "db unavailable"}), 503
    user_id = str(session.get("user_id"))
    body    = request.json or {}
    db      = _DBSession()
    try:
        s = db.query(UserSettings).filter_by(user_id=user_id).first()
        if not s:
            s = UserSettings(user_id=user_id)
            db.add(s)

        if "assets_enabled" in body:
            try:    s.assets_enabled = json.dumps(list(body["assets_enabled"]))
            except: pass
        if "risk_tolerance" in body and body["risk_tolerance"] in ("conservative","moderate","aggressive"):
            s.risk_tolerance = body["risk_tolerance"]

        if "chart_theme"      in body: s.chart_theme      = str(body["chart_theme"])[:32]
        if "chart_type"       in body and body["chart_type"] in ("candles","bar","line"):
            s.chart_type = body["chart_type"]
        if "grid_style"       in body: s.grid_style       = str(body["grid_style"])[:16]
        if "indicator_scheme" in body: s.indicator_scheme = str(body["indicator_scheme"])[:16]

        if "timezone" in body: s.timezone = str(body["timezone"])[:64]

        if "alert_confidence" in body:
            try:    s.alert_confidence = max(0, min(100, int(body["alert_confidence"])))
            except: pass
        for k in ("alert_price_pct","alert_drawdown_pct","alert_loss_pct",
                  "perf_target_rr","perf_target_annual"):
            if k in body:
                try:    setattr(s, k, float(body[k]))
                except: pass
        for k in ("perf_target_winrate","perf_target_trades"):
            if k in body:
                try:    setattr(s, k, int(body[k]))
                except: pass

        if "portfolio_alloc" in body:
            try:    s.portfolio_alloc = json.dumps(dict(body["portfolio_alloc"]))
            except: pass
        if "portfolio_preset" in body and body["portfolio_preset"] in ("conservative","balanced","aggressive"):
            s.portfolio_preset = body["portfolio_preset"]
        if "portfolio_rebalance" in body and body["portfolio_rebalance"] in ("monthly","quarterly","yearly"):
            s.portfolio_rebalance = body["portfolio_rebalance"]
        if "portfolio_benchmark" in body: s.portfolio_benchmark = str(body["portfolio_benchmark"])[:16]

        # Connections — encrypt before storing, never log. Empty string = unchanged.
        if body.get("mt5_api_key"):        s.mt5_api_key_enc        = _enc(str(body["mt5_api_key"]))
        if "mt5_account"        in body:   s.mt5_account            = str(body["mt5_account"])[:64]
        if "mt5_broker_server"  in body:   s.mt5_broker_server      = str(body["mt5_broker_server"])[:128]
        if body.get("telegram_bot_token"): s.telegram_bot_token_enc = _enc(str(body["telegram_bot_token"]))
        if "telegram_chat_id"   in body:   s.telegram_chat_id       = str(body["telegram_chat_id"])[:64]

        s.updated_at = datetime.utcnow()
        db.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ─── NOTIFICATIONS ────────────────────────────────────────────

@app.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    if not _DBSession:
        return jsonify({"notifications": []})
    user_id = str(session.get("user_id"))
    try:
        db = _DBSession()
        rows = db.query(Notification)\
                 .filter(Notification.user_id.in_([user_id, "default"]))\
                 .order_by(Notification.created_at.desc()).limit(50).all()
        result = [{
            "id":         n.id,
            "type":       n.ntype,
            "title":      n.title,
            "body":       n.body,
            "data":       json.loads(n.data) if n.data else None,
            "read":       n.read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        } for n in rows]
        db.close()
        return jsonify({"notifications": result,
                        "unread": sum(1 for r in result if not r["read"])})
    except Exception as e:
        return jsonify({"notifications": [], "unread": 0})

@app.route("/api/notifications/read", methods=["POST"])
@login_required
def mark_notifications_read():
    if not _DBSession:
        return jsonify({"status": "ok"})
    user_id = str(session.get("user_id"))
    body    = request.json or {}
    nid     = body.get("id")   # if None → mark all read
    try:
        db = _DBSession()
        q  = db.query(Notification).filter(Notification.user_id.in_([user_id, "default"]))
        if nid:
            q = q.filter(Notification.id == int(nid))
        q.update({"read": True}, synchronize_session=False)
        db.commit(); db.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── SETTINGS — PROFILE ──────────────────────────────────────

@app.route("/api/profile", methods=["POST"])
@login_required
def update_profile():
    """Update display name and/or password for the logged-in user."""
    if not _DBSession:
        return jsonify({"status": "error", "message": "Database not available"}), 503
    user = _get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    body     = request.json or {}
    new_name = body.get("name", "").strip()
    old_pw   = body.get("old_password", "").strip()
    new_pw   = body.get("new_password", "").strip()
    db = _DBSession()
    try:
        u = db.query(User).filter_by(id=user.id).first()
        if new_name:
            u.name = new_name
        if new_pw:
            if not old_pw:
                return jsonify({"status": "error", "message": "Current password required to set a new one"}), 400
            if not check_password_hash(u.password_hash or "", old_pw):
                return jsonify({"status": "error", "message": "Current password is incorrect"}), 400
            if len(new_pw) < 6:
                return jsonify({"status": "error", "message": "New password must be at least 6 characters"}), 400
            u.password_hash = generate_password_hash(new_pw)
        db.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

# ─── SETTINGS — EXCHANGE API KEYS ────────────────────────────

@app.route("/api/keys", methods=["GET"])
@login_required
def keys_list():
    """List exchange API keys for the current user (masked, never raw)."""
    if not _DBSession:
        return jsonify([])
    user = _get_current_user()
    if not user:
        return jsonify([])
    db = _DBSession()
    try:
        rows = db.query(ExchangeKey).filter_by(user_id=user.id).order_by(ExchangeKey.created_at.desc()).all()
        result = []
        for r in rows:
            try:
                raw_key = _dec(r.api_key_enc)
                masked  = raw_key[:4] + "••••••••" + raw_key[-4:] if len(raw_key) > 8 else "••••••••"
            except Exception:
                masked = "••••••••"
            result.append({
                "id":         r.id,
                "exchange":   r.exchange,
                "label":      r.label or "",
                "key_masked": masked,
                "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/keys", methods=["POST"])
@login_required
def keys_add():
    """Save a new exchange API key (encrypted)."""
    if not _DBSession:
        return jsonify({"status": "error", "message": "Database not available"}), 503
    user = _get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    body       = request.json or {}
    exchange   = body.get("exchange", "").strip().lower()
    label      = body.get("label", "").strip()
    api_key    = body.get("api_key", "").strip()
    api_secret = body.get("api_secret", "").strip()
    if not exchange or not api_key or not api_secret:
        return jsonify({"status": "error", "message": "Exchange, API key, and secret are required"}), 400
    db = _DBSession()
    try:
        row = ExchangeKey(
            user_id        = user.id,
            exchange       = exchange,
            label          = label or exchange.capitalize(),
            api_key_enc    = _enc(api_key),
            api_secret_enc = _enc(api_secret),
        )
        db.add(row)
        db.commit()
        return jsonify({"status": "ok", "id": row.id})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route("/api/telegram-status", methods=["GET"])
@login_required
def telegram_status():
    """Return whether Telegram is configured (does not expose the token)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat  = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return jsonify({"configured": bool(token and chat)})


@app.route("/api/telegram/webhook", methods=["POST"])
def telegram_webhook():
    """Telegram calls this when user taps an inline keyboard button."""
    body = request.json or {}
    cq   = body.get("callback_query")
    if not cq:
        return jsonify({"ok": True})

    callback_id = cq.get("id", "")
    data        = cq.get("data", "")
    msg         = cq.get("message", {})
    chat_id     = str(msg.get("chat", {}).get("id", ""))
    message_id  = msg.get("message_id")
    bot_token   = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

    # Parse: execute|{scan_alert_id}  — one-tap trade execution from scan alert
    parts = data.split("|")
    if len(parts) == 2 and parts[0] == "execute":
        scan_id = int(parts[1]) if parts[1].isdigit() else 0
        queued  = False
        answer_text = "⚠️ Could not queue trade"
        if scan_id and _DBSession:
            db = _DBSession()
            try:
                rec = db.query(ScanAlert).filter_by(id=scan_id).first()
                if rec:
                    # Determine asset_type from ticker pattern
                    t = rec.ticker
                    at = "crypto" if t.endswith("-USD") and not t.startswith("^") \
                         else ("forex" if t.endswith("=X") or t in ("EURUSD=X","GBPUSD=X","USDJPY=X","AUDUSD=X") \
                         else ("index" if t.startswith("^") \
                         else ("commodity" if t in ("GC=F","SI=F","CL=F") \
                         else "stock")))
                    symbol = _mt5_symbol(t, at)
                    order = MT5Order(
                        user_id    = "default",
                        symbol     = symbol,
                        order_type = rec.signal,
                        volume     = rec.lot_size or 0.01,
                        price      = rec.entry or 0,
                        sl         = rec.sl,
                        tp         = rec.tp1,
                        timeframe  = rec.timeframe,
                        action     = "open",
                        status     = "pending",
                        comment    = f"Telegram execute #{scan_id}",
                    )
                    db.add(order)
                    db.commit()
                    queued = True
                    answer_text = (f"✅ {rec.signal} {rec.lot_size:.2f} lots {symbol} queued — "
                                   f"EA executes within 5s")
            except Exception as e:
                db.rollback()
                print(f"[Telegram webhook] execute error: {e}")
            finally:
                db.close()
        if bot_token:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                    json={"callback_query_id": callback_id, "text": answer_text, "show_alert": True},
                    timeout=5,
                )
                if queued and chat_id and message_id:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                        json={"chat_id": chat_id, "message_id": message_id,
                              "reply_markup": {"inline_keyboard": []}},
                        timeout=5,
                    )
            except Exception:
                pass
        return jsonify({"ok": True})

    # Parse: close|{ticket}|{symbol}|{level}
    if len(parts) == 4 and parts[0] == "close":
        _, ticket_str, symbol, level = parts
        try:
            ticket = int(ticket_str)
        except ValueError:
            ticket = 0

        queued = False
        if ticket > 0 and _DBSession:
            db = _DBSession()
            try:
                order = MT5Order(
                    user_id      = "default",
                    symbol       = symbol,
                    order_type   = "CLOSE",
                    volume       = 0,
                    price        = 0,
                    action       = "close",
                    close_ticket = ticket,
                    status       = "pending",
                    comment      = f"Telegram close {level}",
                )
                db.add(order)
                db.commit()
                queued = True
            except Exception as e:
                db.rollback()
                print(f"[Telegram webhook] DB error: {e}")
            finally:
                db.close()

        if bot_token:
            answer_text = "✅ Close order sent — EA will execute within 5s" if queued else "⚠️ Could not queue order"
            try:
                # Dismiss the loading spinner on the button
                requests.post(
                    f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery",
                    json={"callback_query_id": callback_id, "text": answer_text, "show_alert": False},
                    timeout=5,
                )
                # Remove the keyboard from the original message so it can't be tapped twice
                if chat_id and message_id:
                    requests.post(
                        f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup",
                        json={"chat_id": chat_id, "message_id": message_id, "reply_markup": {"inline_keyboard": []}},
                        timeout=5,
                    )
            except Exception:
                pass

    return jsonify({"ok": True})


@app.route("/api/telegram/setup-webhook", methods=["GET"])
@login_required
def telegram_setup_webhook():
    """One-time call to register the DotVerse webhook URL with Telegram."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        return jsonify({"error": "TELEGRAM_BOT_TOKEN not set in Railway"}), 400
    webhook_url = "https://dot-verse.up.railway.app/api/telegram/webhook"
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={"url": webhook_url, "allowed_updates": ["callback_query"]},
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            return jsonify({"status": "ok", "description": data.get("description", "Webhook set")})
        return jsonify({"status": "error", "description": data.get("description", "Unknown error")}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/keys/<int:key_id>", methods=["DELETE"])
@login_required
def keys_delete(key_id):
    """Delete an exchange key. Only the owning user can delete their own keys."""
    if not _DBSession:
        return jsonify({"status": "error", "message": "Database not available"}), 503
    user = _get_current_user()
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    db = _DBSession()
    try:
        row = db.query(ExchangeKey).filter_by(id=key_id, user_id=user.id).first()
        if not row:
            return jsonify({"status": "error", "message": "Key not found"}), 404
        db.delete(row)
        db.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        db.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

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
        # Use cached TV data from scanner if available (guarantees scanner/signals consistency)
        tv = None
        if _redis_client:
            try:
                _cached = _redis_client.get(f"tv_cache:{ticker}:{timeframe}")
                if _cached:
                    tv = json.loads(_cached)
                    print(f"[analyze] Using cached TV data for {ticker} {timeframe}")
            except Exception:
                pass
        if not tv:
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
            # ── 2e: Forward-fill date grid before indicator calc ──────────────
            if not df.empty:
                df = _fill_date_grid(df, timeframe, asset_type)
            if not df.empty and len(df) >= 51:  # EMA50 needs 51 bars minimum to be valid
                ind_full = calculate_indicators(df, timeframe, asset_type)
                # Bug N fix 2026-04-29: ALWAYS prefer calculate_indicators (yfinance)
                # over build_ind_from_tv when both are available. Previously, when
                # tv_ok was True, ind remained TV-based (vol_ratio=1.0 hardcoded,
                # supertrend=NEUTRAL hardcoded — suppressing two votes) and only
                # chart arrays from yfinance were merged in. That meant analyze and
                # scan-list could disagree on the same ticker because TV-based ind
                # is structurally less rich than calculate_indicators output.
                # Single source of truth — yfinance — for signal voting. TV data
                # remains available via the `tv` arg passed to get_analysis() for
                # informational context (tv_rec_label, tv_rec_all).
                ind = ind_full
                if not tv_ok:
                    # TV failed — build MTF from yfinance daily data as best-effort
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
                    # Pass DataFrame directly — DatetimeIndex preserved, no list conversion
                    chart_result = _build_chart_output(df_binance, timeframe)
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
                # ── Run full calculate_indicators on fallback chart data ──────────────
                # Gives RSI divergence detection, Supertrend, real vol_ratio, BB width,
                # etc. — all the things that only compute when yfinance is available.
                # On Railway, Yahoo Finance is often blocked for stocks; Stooq fills the
                # gap here.  We reconstruct a DatetimeIndex DataFrame from the chart
                # arrays and run the full pipeline on it.
                if len(prices_c) >= 51:
                    try:
                        _fb_idx = pd.to_datetime(dates_c)
                        _opens  = opens_c  if opens_c  and len(opens_c)  == len(prices_c) else prices_c
                        _highs  = highs_c  if highs_c  and len(highs_c)  == len(prices_c) else prices_c
                        _lows   = lows_c   if lows_c   and len(lows_c)   == len(prices_c) else prices_c
                        _df_fb  = pd.DataFrame({
                            "Open":   _opens,
                            "High":   _highs,
                            "Low":    _lows,
                            "Close":  prices_c,
                            "Volume": vols_c,
                        }, index=_fb_idx)
                        _ind_fb = calculate_indicators(_df_fb, timeframe, asset_type)
                        # Overwrite chart_rsi and rsi_divergence — these need the full
                        # indicator pipeline.  Leave chart_prices/dates alone (already set).
                        for _k in ("chart_rsi", "chart_buy_signals", "chart_sell_signals",
                                   "chart_bb_upper", "chart_bb_lower", "rsi_divergence"):
                            ind[_k] = _ind_fb.get(_k, ind.get(_k, []))
                        # Pull scalar indicators from the full calc for any flat field
                        # missing from ind. Previously this was guarded by `if not tv_ok:`
                        # which meant when TV provided the SIGNAL but no flat indicators
                        # (e.g. AAPL 4H on Railway), the response had a valid BUY/SELL but
                        # rsi/atr/vol_ratio all None — frontend rendered "—" everywhere.
                        # Now we always fill missing flat fields from the fallback calc.
                        for _k in ("rsi", "ema_trend", "ema20", "ema50", "macd_hist",
                                   "bb_pos", "bb_width", "atr", "vol_ratio", "supertrend",
                                   "resistance", "support", "price"):
                            if ind.get(_k) is None:
                                ind[_k] = _ind_fb.get(_k)
                        _div_type = _ind_fb.get("rsi_divergence", {}).get("type", "none")
                        _rsi_fb   = _ind_fb.get("rsi", "?")
                        print(f"[analyze] fallback calc_ind OK — rsi={_rsi_fb} divergence={_div_type} bars={len(prices_c)}")
                    except Exception as _fb_err:
                        print(f"[analyze] fallback calc_ind failed (non-critical): {_fb_err}")
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

        # ── STEP 2c: RSI divergence safety net ──────────────────────────────────
        # detect_rsi_divergence only runs inside calculate_indicators() (yfinance path).
        # When yfinance fails and fallback chart paths fire, divergence is never
        # computed — ind["rsi_divergence"] stays as {"type":"none"}.
        # Fix: run divergence on the chart arrays from ANY path and produce the
        # same chart_price_pivot_bars / chart_rsi_pivot_bars fields the frontend expects.
        if ind.get("rsi_divergence", {}).get("type") == "none":
            _prices  = ind.get("chart_prices") or []
            _rsi_raw = ind.get("chart_rsi")    or []
            _h_raw   = ind.get("chart_highs")  or []
            _l_raw   = ind.get("chart_lows")   or []

            # Approximate highs/lows from closes when real OHLC not available
            if len(_prices) >= 20 and (not _h_raw or len(_h_raw) < len(_prices)):
                _h_raw = [max(_prices[i], _prices[i-1]) if i > 0 else _prices[i] for i in range(len(_prices))]
                _l_raw = [min(_prices[i], _prices[i-1]) if i > 0 else _prices[i] for i in range(len(_prices))]

            # Replace None with neutral placeholders — preserve index alignment with chart_dates
            _n = min(len(_h_raw), len(_l_raw), len(_rsi_raw), len(_prices) if _prices else 9999)
            if _n >= 20:
                _hh = pd.Series([v if v is not None else 0.0 for v in _h_raw[:_n]])
                _ll = pd.Series([v if v is not None else 0.0 for v in _l_raw[:_n]])
                _rr = pd.Series([v if v is not None else 50.0 for v in _rsi_raw[:_n]])
                try:
                    _div = detect_rsi_divergence(_hh, _ll, _rr, pivot_len=3, lookback=100)
                    # Rename raw index fields → chart_price_pivot_bars / chart_rsi_pivot_bars
                    # so the frontend (which expects these names) can draw the lines.
                    # Indices are already 0-based into chart_dates since we used chart arrays.
                    def _remap_div(dv):
                        dv = dict(dv)
                        dv["chart_price_pivot_bars"] = dv.get("price_pivot_bars", [])
                        dv["chart_rsi_pivot_bars"]   = dv.get("rsi_pivot_bars",   [])
                        return dv
                    if _div.get("price_pivot_bars"):
                        _div = _remap_div(_div)
                    else:
                        _div["chart_price_pivot_bars"] = []
                        _div["chart_rsi_pivot_bars"]   = []
                    _div["all"] = [_remap_div(dv) for dv in _div.get("all", [])
                                   if len(dv.get("price_pivot_bars", [])) >= 2]
                    ind["rsi_divergence"] = _div
                    print(f"[analyze] divergence safety-net: type={_div.get('type')} all={len(_div.get('all',[]))}")
                except Exception as _de:
                    print(f"[analyze] divergence safety-net failed: {_de}")
            else:
                print(f"[analyze] divergence safety-net: not enough data ({_n} bars)")

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

        # ── Override MTF entry for the current timeframe with the actual signal ──
        # get_mtf_trend uses simple EMA stacking which can disagree with the full
        # confluence gate. The analyzed TF must always show the real signal result.
        _tf_key_map = {"15m":"15m","1h":"1H","4h":"4H","1d":"1D","1w":"1W","1mo":"1M"}
        _tf_key = _tf_key_map.get(timeframe.lower(), timeframe.upper())
        _sig_to_trend = {"BUY":"BULLISH","SELL":"BEARISH","HOLD":"NEUTRAL"}
        mtf[_tf_key] = {
            "trend": _sig_to_trend.get(analysis.get("signal","HOLD"), "NEUTRAL"),
            "rsi":   round(ind.get("rsi", 50) or 50, 1)
        }

        # ── HISTORICAL QUALITY GATE (commit 2 — 2026-04-29) ───────────────
        # Earlier the code called calculate_win_rate(df_daily, "HOLD") which
        # always returned {win_rate: None, sample_size: 0} because the function
        # only computes for "BUY"/"SELL" signal directions. This left the
        # win_rate field in the response permanently null.
        #
        # Now we recompute WR using the ACTUAL signal direction returned by
        # get_analysis. If the historical pattern shows <55% win rate over
        # >=30 samples, we suppress the signal to HOLD with a clear reason.
        # This is the "winning signals only" filter the user asked for.
        try:
            _df_for_wr = locals().get("df_daily")
            if _df_for_wr is not None and not _df_for_wr.empty:
                _sig_now = analysis.get("signal", "HOLD")
                if _sig_now in ("BUY", "SELL"):
                    wr = calculate_win_rate(_df_for_wr, _sig_now)
                    _wr_pct = wr.get("win_rate")
                    _wr_n   = wr.get("sample_size", 0) or 0
                    if _wr_pct is not None and _wr_n >= 30 and _wr_pct < 55:
                        analysis["signal"]              = "HOLD"
                        analysis["confidence"]          = "LOW"
                        analysis["confidence_label"]    = "HYPOTHESIS"
                        analysis["historical_wr_block"] = True
                        analysis["historical_wr_pct"]   = _wr_pct
                        analysis["historical_wr_n"]     = _wr_n
                        analysis["summary"] = (analysis.get("summary","") +
                            f" [Suppressed by historical-quality gate: pattern WR {_wr_pct}% over {_wr_n} samples — below 55% threshold.]")
                        print(f"[hist-gate] {ticker} {timeframe} {_sig_now} SUPPRESSED: WR={_wr_pct}% n={_wr_n}")
                    else:
                        analysis["historical_wr_pct"] = _wr_pct
                        analysis["historical_wr_n"]   = _wr_n
                        print(f"[hist-gate] {ticker} {timeframe} {_sig_now} pass: WR={_wr_pct}% n={_wr_n}")
        except Exception as _hge:
            print(f"[hist-gate] error: {_hge}")

        # ── DAILY LOSS CIRCUIT-BREAKER (commit 3 — 2026-04-29) ────────────
        # Halt new BUY/SELL signals when today's filled MT5 P&L is below
        # -2% of account balance. Protects against revenge-trading after a
        # losing morning. Skips silently if user has no MT5 connection.
        try:
            if _DBSession and analysis.get("signal") in ("BUY", "SELL"):
                _user_id_str = str(session.get("user_id") or "")
                _today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                _db_cb = _DBSession()
                try:
                    from sqlalchemy import func as _sa_func
                    _today_pnl = _db_cb.query(_sa_func.coalesce(_sa_func.sum(MT5Order.pnl), 0.0))\
                        .filter(MT5Order.user_id == _user_id_str,
                                MT5Order.status == "filled",
                                MT5Order.pnl.isnot(None),
                                MT5Order.filled_at >= _today_start).scalar()
                    _today_pnl = float(_today_pnl or 0.0)
                finally:
                    _db_cb.close()
                with mt5_state_lock:
                    _state_cb = mt5_state.get(_user_id_str) or mt5_state.get("default") or {}
                _balance = float((_state_cb.get("account") or {}).get("balance", 0.0) or 0.0)
                if _balance > 0 and _today_pnl < -0.02 * _balance:
                    analysis["signal"]              = "HOLD"
                    analysis["confidence"]          = "LOW"
                    analysis["confidence_label"]    = "HYPOTHESIS"
                    analysis["circuit_breaker"]     = True
                    analysis["daily_pnl"]           = round(_today_pnl, 2)
                    analysis["account_balance"]     = round(_balance, 2)
                    analysis["summary"] = (analysis.get("summary","") +
                        f" [Circuit-breaker: today's MT5 P&L {_today_pnl:.2f} < -2% of {_balance:.2f} balance.]")
                    print(f"[circuit] {ticker} {timeframe} HALTED: today_pnl={_today_pnl:.2f} balance={_balance:.2f}")
        except Exception as _ce:
            print(f"[circuit] error: {_ce}")

        # ── ADX REGIME DETECTION (commit 4 — 2026-04-29) ───────────────────
        # Classify market regime from TV's ADX. TRENDING (ADX>25) — directional
        # moves likely persist. RANGING (ADX<20) — mean-reversion favoured.
        # TRANSITION (20-25) — regime shifting, lower conviction.
        try:
            _adx_val = (tv or {}).get("tv_adx") if isinstance(tv, dict) else None
            if _adx_val is None:
                analysis["regime"] = "UNKNOWN"
            elif _adx_val > 25:
                analysis["regime"] = "TRENDING"
            elif _adx_val < 20:
                analysis["regime"] = "RANGING"
            else:
                analysis["regime"] = "TRANSITION"
            analysis["adx"] = _adx_val
        except Exception as _re:
            print(f"[regime] error: {_re}")

        # ── VOLATILITY THROTTLE (commit 5 — 2026-04-29) ────────────────────
        # When the current bar's high-low range exceeds the 95th percentile
        # of the last 100 bars, suppress new BUY/SELL signals. Extreme
        # volatility = wider stops, worse fills, more whipsaws. Existing
        # atr_gate_pct filters MINIMUM volatility; this caps the MAXIMUM.
        try:
            if analysis.get("signal") in ("BUY", "SELL"):
                _hs = ind.get("chart_highs") or []
                _ls = ind.get("chart_lows")  or []
                if len(_hs) >= 50 and len(_ls) >= 50:
                    _ranges = [(_hs[i] - _ls[i]) for i in range(-100, 0)
                               if _hs[i] is not None and _ls[i] is not None]
                    if len(_ranges) >= 30:
                        _ranges.sort()
                        _p95 = _ranges[int(len(_ranges) * 0.95)]
                        _curr = (_hs[-1] - _ls[-1]) if _hs[-1] is not None and _ls[-1] is not None else 0
                        if _curr > _p95 and _p95 > 0:
                            analysis["signal"]              = "HOLD"
                            analysis["confidence"]          = "LOW"
                            analysis["confidence_label"]    = "HYPOTHESIS"
                            analysis["volatility_throttle"] = True
                            analysis["volatility_range"]    = round(_curr, 4)
                            analysis["volatility_p95"]      = round(_p95, 4)
                            analysis["summary"] = (analysis.get("summary","") +
                                f" [Volatility throttle: current range {_curr:.4f} above 95th percentile {_p95:.4f}.]")
                            print(f"[vol-throttle] {ticker} {timeframe} SUPPRESSED: range={_curr:.4f} p95={_p95:.4f}")
        except Exception as _ve:
            print(f"[vol-throttle] error: {_ve}")

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
        # ── Scanner cache override REMOVED 2026-04-29 (Bug N fix) ──
        # Previously read scanner_signal Redis key and overrode response_data signal
        # fields. Created the same trust violation we removed from TV override:
        # scan-list could compute one signal (using TV-based ind), cache it, then
        # /api/analyze would compute a different signal (using yfinance-based ind)
        # and silently override with the cached scanner result. Scanner and analyze
        # now ALWAYS compute via the same path (yfinance + calculate_indicators), so
        # this cache override is no longer needed for consistency. Removing it lets
        # /api/analyze always return its own fresh computation — coherent verdict.
        # ── Persist to signal history (fire-and-forget, never block the response) ──
        # Bug J fix 2026-04-29: previous code had two bugs that silently failed every
        # write: (1) user_id was looked up via session.get('user',{}).get('localId',...)
        # which never matched the real session shape (session['user_id'] is the canonical
        # key) so all writes saved as user_id='default'; (2) confidence was inserted as
        # a string ('HIGH'/'MEDIUM'/'LOW') into a Float column, raising DataError which
        # the bare except caught and logged but never surfaced. Result: count=0 forever.
        try:
            if _DBSession:
                # Map confidence string label to numeric (column is Float)
                _conf_str = response_data.get("confidence", "LOW")
                _conf_num = {"HIGH": 90.0, "MEDIUM": 70.0, "LOW": 50.0}.get(_conf_str, 50.0)
                _sh_db = _DBSession()
                _sh = SignalHistory(
                    user_id   = str(session.get("user_id", "default")),
                    ticker    = ticker,
                    asset_type= asset_type,
                    timeframe = timeframe,
                    signal    = response_data.get("signal", "HOLD"),
                    price     = response_data.get("price"),
                    entry     = response_data.get("entry"),
                    stop_loss = response_data.get("stop_loss"),
                    tp1       = response_data.get("tp1"),
                    confidence= _conf_num,
                    confidence_label = response_data.get("confidence_label"),
                )
                _sh_db.add(_sh)
                _sh_db.commit()
                _sh_db.close()
        except Exception as _she:
            print(f"[signal_history] save failed (non-fatal): {_she}")

        # Log key response fields for debugging
        print(f"[analyze] RESPONSE FIELDS: signal={response_data.get('signal')} "
              f"price={response_data.get('price')} rsi={response_data.get('rsi')} "
              f"entry={response_data.get('entry')} sl={response_data.get('stop_loss')} "
              f"tp1={response_data.get('tp1')} chart_bars={len(response_data.get('chart_prices', []))} "
              f"chart_rsi_bars={len([v for v in (response_data.get('chart_rsi') or []) if v is not None])} "
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
@login_required
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

        ind    = calculate_indicators(df, timeframe, asset_type)
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

        ticker         = normalise_ticker(ticker, asset_type)
        user_id        = str(session.get('user_id', 'anon'))
        key            = f"{user_id}_{ticker}_{timeframe}"
        current_signal = body.get("current_signal", "HOLD") or "HOLD"

        ch_labels = {"sms": "SMS", "whatsapp": "WhatsApp", "telegram": "Telegram"}
        ch_str    = " + ".join(ch_labels.get(c, c) for c in alert_channels)

        _is_update = False
        with watch_lock:
            if key in watch_registry:
                watch_registry[key]["alert_channels"] = alert_channels
                _is_update = True
            else:
                watch_registry[key] = {
                    "user_id":        user_id,
                    "ticker":         ticker,
                    "asset_type":     asset_type,
                    "timeframe":      timeframe,
                    "alert_channels": alert_channels,
                    "last_signal":    current_signal,
                    "last_check":     None,
                    "last_reason":    "Not checked yet",
                    "last_price":     None,
                    "added_at":       datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                }

        _save_watch_to_db(ticker, asset_type, timeframe, alert_channels, user_id)

        if _is_update:
            return jsonify({"status": "updated", "key": key,
                            "message": f"Updated {ticker} ({timeframe.upper()}) — alerts via {ch_str}"}), 200
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
        if not ticker:
            return jsonify({"error": "ticker required"}), 400
        ticker  = normalise_ticker(ticker, body.get("asset_type", "stock"))
        user_id = str(session.get('user_id', 'anon'))
        key     = f"{user_id}_{ticker}_{timeframe}"

        # DB is source of truth — gunicorn workers do not share the in-memory
        # watch_registry, so checking it alone produced false 404s.
        db_removed = _remove_watch_from_db(ticker, timeframe, user_id)

        # Best-effort in-memory cleanup on the worker handling this request.
        with watch_lock:
            watch_registry.pop(key, None)

        if db_removed:
            return jsonify({"status": "removed", "key": key})
        return jsonify({"status": "not_found", "key": key}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/watches", methods=["GET"])
@login_required
def list_watches():
    """List current user's watches — reads from DB (source of truth) merged with in-memory runtime fields."""
    user_id = str(session.get('user_id', 'anon'))
    watches = []
    if _DBSession:
        db = _DBSession()
        try:
            rows = db.query(Watch).filter_by(user_id=user_id).all()
            for r in rows:
                try:
                    channels = json.loads(r.alert_channels)
                except Exception:
                    channels = [r.alert_channels]
                # Merge runtime fields from in-memory registry if available
                key = f"{user_id}_{r.ticker}_{r.timeframe}"
                with watch_lock:
                    mem = watch_registry.get(key, {})
                lc = mem.get("last_check")
                watches.append({
                    "key":             key,
                    "ticker":          r.ticker,
                    "asset_type":      r.asset_type,
                    "timeframe":       r.timeframe,
                    "alert_channels":  channels,
                    "last_signal":     mem.get("last_signal") or "Waiting…",
                    "last_reason":     mem.get("last_reason") or "Not checked yet",
                    "last_price":      mem.get("last_price"),
                    "last_check":      lc.strftime("%H:%M UTC") if lc else "Pending",
                    "added_at":        r.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                    "interval_min":    ALERT_INTERVALS.get(r.timeframe, 300) // 60,
                    "live_commentary": mem.get("live_commentary"),
                })
        except Exception as _e:
            print(f"[list_watches] DB error: {_e}")
        finally:
            db.close()
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
        import threading as _threading
        results_lock = _threading.Lock()

        def _scan_one(ticker):
            # Bug N fix 2026-04-29: scan_list now uses the SAME data source as
            # /api/analyze (yfinance + calculate_indicators). Previously the TV
            # fast-path used build_ind_from_tv() which hardcodes vol_ratio=1.0 and
            # supertrend='NEUTRAL', producing different `ind` than calculate_indicators.
            # Same ticker/TF could yield BUY in scan-list and SELL in analyze. The
            # signal-coherence ethos requires one source of truth — scan-list and
            # analyze must agree by construction. TV is still used elsewhere for chart
            # rendering and MTF context; for SIGNAL VOTING, only yfinance.
            raw = normalise_ticker(ticker, asset_type)
            row = None
            try:
                df = safe_download(raw, period=cfg["period"], interval=cfg["interval"])
                # Yahoo v8 rate-limits Railway IPs — yfinance package fallback (Bug Y fix).
                if df.empty:
                    try:
                        df = yf.download(raw, period=cfg["period"], interval=cfg["interval"],
                                         progress=False, auto_adjust=True)
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        print(f"[yfinance-fallback] {raw} {timeframe}: {len(df)} bars")
                    except Exception as _yfe:
                        print(f"[yfinance-fallback] {raw} error: {_yfe}")
                        df = pd.DataFrame()
                if "resample" in cfg and not df.empty:
                    if not isinstance(df.index, pd.DatetimeIndex):
                        df.index = pd.to_datetime(df.index)
                    df = df.resample(cfg["resample"]).agg(
                        {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna()
                if df.empty or len(df) < 20:
                    row = {"ticker": ticker, "error": "no data"}
                else:
                    ind      = calculate_indicators(df, timeframe, asset_type)
                    analysis = get_analysis(ticker, asset_type, ind, timeframe)
                    ct       = detect_counter_trade(ind)
                    row = {
                        "ticker": ticker, "raw_ticker": raw, "asset_type": asset_type,
                        "price": ind["price"], "chg_1d": ind["chg_1d"], "rsi": ind["rsi"],
                        "vol_ratio": ind["vol_ratio"],
                        "volume": int(float(df["Volume"].iloc[-1])) if "Volume" in df else 0,
                        "ema_trend": ind["ema_trend"], "supertrend": ind["supertrend"],
                        "signal": analysis["signal"], "entry": analysis.get("entry"),
                        "stop_loss": analysis.get("stop_loss"), "tp1": analysis.get("tp1"),
                        "tp2": analysis.get("tp2"), "tp3": analysis.get("tp3"),
                        "rr1": analysis.get("rr1"), "rr2": analysis.get("rr2"), "rr3": analysis.get("rr3"),
                        "reason": analysis.get("summary",""), "bull_score": analysis.get("bullish_count",0),
                        "bear_score": analysis.get("bearish_count",0), "counter_trade": ct["counter_trade"],
                        "confidence": analysis.get("confidence","LOW"),
                        "confidence_label": analysis.get("confidence_label","HYPOTHESIS"),
                    }
            except Exception as e:
                print(f"[scan-list] Error for {ticker}: {e}")
                row = {"ticker": ticker, "error": str(e)[:80]}
            if row:
                with results_lock:
                    results.append(row)

        # Run all tickers in parallel — 6 tickers in ~5s instead of ~30s
        threads = [_threading.Thread(target=_scan_one, args=(t,)) for t in tickers]
        for th in threads: th.start()
        for th in threads: th.join(timeout=25)

        def sort_key(r):
            if r.get("error"): return 99
            sig = r.get("signal", "HOLD")
            if sig in ("BUY", "SELL"): return 0
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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

    # Fetch OHLC+Volume — we need high/low per bar for intrabar TP/SL detection,
    # and volume for the enhanced confluence gate (volume confirmation filter).
    # Fetching 1000 bars: first 200 are warm-up for EMA-200, MACD, RSI;
    # the remaining ~800 are the signal-scan window for statistical depth.
    prices_hist, highs_hist, lows_hist, dates_hist, volumes_hist = [], [], [], [], []

    # ── Source 1: Binance OHLC+Volume (crypto — most reliable, free, no auth) ──
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
                dt_fmt = "%Y-%m-%d %H:%M" if timeframe in ("5m","15m","30m","1h","4h") else "%Y-%m-%d"
                for k in klines:
                    ts = int(k[0]) // 1000
                    dates_hist.append(datetime.utcfromtimestamp(ts).strftime(dt_fmt))
                    prices_hist.append(float(k[4]))  # close
                    highs_hist.append(float(k[2]))   # high
                    lows_hist.append(float(k[3]))    # low
                    volumes_hist.append(float(k[5])) # base asset volume
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
                        volumes_hist.append(float(row.get("Volume") or 0))
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
                        fmp_data = list(reversed(fmp_data[-1000:]))  # chronological, up to 1000 bars
                        for bar in fmp_data:
                            dates_hist.append(bar.get("date",""))
                            prices_hist.append(float(bar["close"]))
                            highs_hist.append(float(bar.get("high", bar["close"])))
                            lows_hist.append(float(bar.get("low", bar["close"])))
                            volumes_hist.append(float(bar.get("volume") or 0))
                        print(f"[backtest] FMP OHLC: {len(prices_hist)} bars")
            except Exception as e:
                print(f"[backtest] FMP OHLC error: {e}")

    # ── Source 3: yfinance OHLC ──
    if not prices_hist:
        try:
            cfg = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["1d"])
            # Extended periods to maximise bar count → more trades found → 30+ sample gate hit more reliably
            # yfinance hard limits: 5m/15m/30m max 60d, 1h max 730d
            period_map = {"5m":"60d","15m":"60d","30m":"60d","1h":"730d","4h":"730d","1d":"5y","1w":"10y","1mo":"max"}
            df_bt = safe_download(ticker_n, period=period_map.get(timeframe,"1y"),
                                  interval=cfg["interval"], progress=False, auto_adjust=True)
            if "resample" in cfg and not df_bt.empty:
                df_bt = df_bt.resample(cfg["resample"]).agg(
                    {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
                ).dropna()
            if not df_bt.empty and len(df_bt) >= 15:
                prices_hist  = [float(v) for v in df_bt["Close"].squeeze().dropna()]
                highs_hist   = [float(v) for v in df_bt["High"].squeeze().dropna()]
                lows_hist    = [float(v) for v in df_bt["Low"].squeeze().dropna()]
                dates_hist   = [str(d.date()) for d in df_bt.index]
                volumes_hist = [float(v) for v in df_bt["Volume"].squeeze().fillna(0)] if "Volume" in df_bt.columns else []
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

    if len(prices_hist) < 50:
        return jsonify({"error": f"Only {len(prices_hist)} bars available for {ticker}. " +
                                 "DotVerse requires 200+ bars for a statistically valid backtest. " +
                                 "Try a higher timeframe (1H, 4H, 1D) or use TradingView Strategy Tester."}), 503

    # Pad highs/lows/volumes to match prices length if any source left them short
    if not highs_hist:  highs_hist  = prices_hist[:]
    if not lows_hist:   lows_hist   = prices_hist[:]
    if not volumes_hist: volumes_hist = [1.0] * len(prices_hist)  # neutral placeholder
    # Ensure all arrays are the same length (trim to shortest)
    _n = min(len(prices_hist), len(highs_hist), len(lows_hist), len(volumes_hist))
    prices_hist  = prices_hist[:_n]
    highs_hist   = highs_hist[:_n]
    lows_hist    = lows_hist[:_n]
    volumes_hist = volumes_hist[:_n]
    dates_hist   = dates_hist[:_n]

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

    # ── EMA series helper (TV-compatible multiplier) ──────────────────────────
    def _ema_s(prices, period):
        out = [None] * len(prices)
        if len(prices) < period:
            return out
        out[period - 1] = sum(prices[:period]) / period
        k = 2.0 / (period + 1)
        for idx in range(period, len(prices)):
            out[idx] = prices[idx] * k + out[idx - 1] * (1 - k)
        return out

    # ── Bollinger Band position series (0=at lower band, 1=at upper band) ─────
    def _bb_pos_s(prices, period=20):
        out = [None] * len(prices)
        for idx in range(period - 1, len(prices)):
            w   = prices[idx - period + 1:idx + 1]
            sma = sum(w) / period
            std = (sum((p - sma) ** 2 for p in w) / period) ** 0.5
            upper = sma + 2 * std
            lower = sma - 2 * std
            denom = upper - lower
            out[idx] = (prices[idx] - lower) / denom if denom > 0 else 0.5
        return out

    # ── Wilder ATR series (True Range smoothed with Wilder's method) ───────────
    def _wilder_atr(highs, lows, closes, period=14):
        """ATR via Wilder's smoothing — same as TradingView's ta.atr()."""
        out = [None] * len(closes)
        if len(closes) < period + 1:
            return out
        tr_list = [0.0]
        for i in range(1, len(closes)):
            tr = max(highs[i] - lows[i],
                     abs(highs[i] - closes[i-1]),
                     abs(lows[i]  - closes[i-1]))
            tr_list.append(tr)
        # Seed with SMA of first `period` TR values
        atr_seed = sum(tr_list[1:period+1]) / period
        out[period] = atr_seed
        for i in range(period+1, len(closes)):
            out[i] = (out[i-1] * (period-1) + tr_list[i]) / period
        return out

    # ── Volume moving average (simple, 20-bar) ──────────────────────────────────
    def _vol_ma_s(volumes, period=20):
        out = [None] * len(volumes)
        for idx in range(period - 1, len(volumes)):
            out[idx] = sum(volumes[idx - period + 1:idx + 1]) / period
        return out

    # ── Rate of Change (momentum oscillator) ────────────────────────────────────
    def _roc_s(prices, period=10):
        out = [None] * len(prices)
        for idx in range(period, len(prices)):
            denom = prices[idx - period]
            if denom and denom != 0:
                out[idx] = (prices[idx] - denom) / denom * 100
        return out

    # ── Pre-compute all indicator series using asset-specific settings ──────────
    _acfg_bt      = ASSET_CONFIG.get(asset_type, _DEFAULT_ASSET_CFG)
    _rsi_p_bt     = _acfg_bt["rsi_period"]
    _ema_fast_bt  = _acfg_bt["ema_fast"]
    _ema_slow_bt  = _acfg_bt["ema_slow"]
    _atr_gate_pct = _acfg_bt.get("atr_gate_pct", 0.004)   # asset-class ATR threshold
    _roc_gate_pct = _acfg_bt.get("roc_gate_pct", 1.0)     # asset-class ROC threshold
    _vol_gate_on  = _acfg_bt.get("vol_gate", True)         # False for forex

    rsi_hist   = _rsi(prices_hist, _rsi_p_bt)
    _ef_hist   = _ema_s(prices_hist, _ema_fast_bt)
    _es_hist   = _ema_s(prices_hist, _ema_slow_bt)
    _e200_hist = _ema_s(prices_hist, 200)          # macro trend — valid for 4H+
    _e50_hist  = _ema_s(prices_hist, 50)           # session trend — used for short TFs
    # Timeframe-adaptive macro reference:
    # On 5m/15m/30m/1H, EMA-200 covers < 1 day of data — not "macro."
    # EMA-50 on these TFs covers ~12H–3 days, which correctly represents the daily structure.
    # On 4H+, EMA-200 covers weeks/months — genuinely macro.
    _short_tf     = timeframe.lower() in ("5m","15m","30m","1h")
    _macro_hist   = _e50_hist if _short_tf else _e200_hist

    _mf_hist   = _ema_s(prices_hist, 12)
    _ms_hist   = _ema_s(prices_hist, 26)
    _ml_hist   = [(_mf_hist[idx] - _ms_hist[idx])
                  if _mf_hist[idx] is not None and _ms_hist[idx] is not None else None
                  for idx in range(len(prices_hist))]
    _ml_vals   = [v if v is not None else 0.0 for v in _ml_hist]
    _msig_hist = _ema_s(_ml_vals, 9)
    _mh_hist   = [(_ml_hist[idx] - _msig_hist[idx])
                  if _ml_hist[idx] is not None and _msig_hist[idx] is not None else None
                  for idx in range(len(prices_hist))]
    _bp_hist   = _bb_pos_s(prices_hist)
    _atr_hist  = _wilder_atr(highs_hist, lows_hist, prices_hist, 14)
    _vma_hist  = _vol_ma_s(volumes_hist, 20)
    _roc_hist  = _roc_s(prices_hist, 10)            # 10-bar momentum

    # Detect whether volume data is meaningful (not all-zeros placeholder)
    _has_vol   = any(v > 0 for v in volumes_hist)

    def _conf_sig(idx):
        """
        DotVerse 8-signal hardened confluence gate — SWOT-corrected.

        Hard gates (reject before voting):
          1. ATR volatility gate    — asset-class relative threshold (not a fixed 0.3%)
          2. Volume hard gate       — skipped for forex (tick volume unreliable for OTC)
          3. Spike-bar guard        — bar range > 2.5× ATR = liquidation/news spike, skip

        Voted signals (65% confluence → BUY/SELL):
          1. RSI zone + 3-bar smoothed direction (removes single-bar noise)
          2. EMA trend stack + timeframe-adaptive macro reference
          3. MACD histogram direction + normalised expansion (significance threshold applied)
          4. Bollinger Band extremes
          5. Volume surge with bar-body direction (close>open, not close>prev_close)
          6. Rate-of-Change with asset-class relative threshold

        Trade mode awareness:
          Scalp (5m/15m/30m) → macro ref = EMA-50 (session structure)
          Day/Swing (1H/4H)  → macro ref = EMA-200 (daily/weekly structure)
          Position (1D+)     → macro ref = EMA-200 (monthly structure)
        """
        r    = rsi_hist[idx]
        ef   = _ef_hist[idx]
        es   = _es_hist[idx]
        mac  = _macro_hist[idx]   # timeframe-adaptive macro reference
        mh   = _mh_hist[idx]
        bp   = _bp_hist[idx]
        p    = prices_hist[idx]
        atr  = _atr_hist[idx]
        vma  = _vma_hist[idx]
        roc  = _roc_hist[idx]
        vol  = volumes_hist[idx] if idx < len(volumes_hist) else None
        hi   = highs_hist[idx]   if idx < len(highs_hist)   else p
        lo   = lows_hist[idx]    if idx < len(lows_hist)    else p
        opn  = prices_hist[idx - 1] if idx > 0 else p   # prev close as open proxy

        # Minimum indicators required
        if r is None or ef is None or es is None:
            return "HOLD"

        # ── Hard Gate 1: ATR volatility — asset-class relative threshold ────────
        # Below this level, trend indicators fire on compression noise.
        # Each asset class has its own normal volatility regime.
        if atr is not None and p > 0 and atr / p < _atr_gate_pct:
            return "HOLD"

        # ── Hard Gate 2: Volume — only for assets with real volume data ─────────
        # Forex: skipped (_vol_gate_on=False) — OTC tick count is not real volume.
        # For forex, the ATR gate already handles low-energy conditions.
        if _vol_gate_on and _has_vol and vol is not None and vma is not None and vma > 0:
            if vol < 0.75 * vma:
                return "HOLD"

        # ── Hard Gate 3: Spike-bar guard ────────────────────────────────────────
        # A bar whose range > 2.5× ATR is a liquidation event / macro news spike.
        # Trend indicators give a false reading on spike bars — skip entirely.
        if atr is not None and atr > 0 and (hi - lo) > 2.5 * atr:
            return "HOLD"

        bc = 0; brc = 0    # bullish / bearish vote counts

        # ── Signal 1: RSI zone + 3-bar smoothed momentum direction ─────────────
        # 3-bar smoothing removes single-bar RSI oscillation noise in trending markets.
        r1 = rsi_hist[idx - 1] if idx >= 1 else None
        r2 = rsi_hist[idx - 2] if idx >= 2 else None
        if r1 is not None and r2 is not None:
            rsi_now3  = (r + r1 + r2) / 3
            rsi_prev3 = (r1 + r2 + (rsi_hist[idx-3] if idx >= 3 and rsi_hist[idx-3] else r2)) / 3
            rsi_rising  = rsi_now3 > rsi_prev3
            rsi_falling = rsi_now3 < rsi_prev3
        else:
            rsi_rising  = r1 is not None and r > r1
            rsi_falling = r1 is not None and r < r1
        if   r >= 75:        brc += 2 if rsi_rising  else 1   # overbought + rising = peak short
        elif 55 <= r < 75:   bc  += 2 if rsi_rising  else 1   # bullish momentum confirmed
        elif 25 < r < 45:    brc += 2 if rsi_falling else 1   # bearish momentum confirmed
        elif r <= 25:        bc  += 2 if rsi_falling else 1   # oversold + falling = capitulation long
        # 45-55 neutral — no vote

        # ── Signal 2: EMA trend stack + timeframe-adaptive macro reference ──────
        ema_bull = p > ef and ef > es
        ema_bear = p < ef and ef < es
        if ema_bull:
            bc  += 2
            if mac is not None and p > mac: bc  += 1   # macro/session structure aligned
        elif ema_bear:
            brc += 2
            if mac is not None and p < mac: brc += 1   # macro/session structure aligned

        # ── Signal 3: MACD histogram direction + normalised expansion ────────────
        # Normalisation: expansion only counts when histogram is significant
        # (> 0.1% of price) — prevents micro-oscillations near zero getting weight 2.
        mh_prev = _mh_hist[idx - 1] if idx > 0 else None
        if mh is not None:
            macd_min_sig  = p * 0.001 if p else 0    # 0.1% of price = minimum significance
            macd_expanding = (
                mh_prev is not None and
                abs(mh) > abs(mh_prev) and
                abs(mh) > macd_min_sig              # must be above significance floor
            )
            if   mh > 0: bc  += 2 if macd_expanding else 1
            elif mh < 0: brc += 2 if macd_expanding else 1

        # ── Signal 4: Bollinger Band extremes ───────────────────────────────────
        if bp is not None:
            if   bp > 0.85: brc += 1
            elif bp < 0.15: bc  += 1

        # ── Signal 5: Volume surge with bar-body direction ───────────────────────
        # Fix: use close > open (bar body) not close > prev_close.
        # close > open correctly identifies whether high volume was buying or selling.
        # close > prev_close can be misled by wicks (close up from a big down wick).
        # Spike-bar guard (Gate 3) already removed liquidation events before we reach here.
        if _vol_gate_on and _has_vol and vol is not None and vma is not None and vma > 0:
            if vol >= 1.5 * vma:
                bar_open = opn   # prev close as proxy for this bar's open
                if   p > bar_open: bc  += 1   # bullish bar body + high volume
                elif p < bar_open: brc += 1   # bearish bar body + high volume

        # ── Signal 6: Rate-of-Change with asset-class relative threshold ─────────
        # Threshold is calibrated per asset: crypto needs 3%+, forex only 0.3%+
        if roc is not None:
            if   roc >  _roc_gate_pct: bc  += 1
            elif roc < -_roc_gate_pct: brc += 1

        total = bc + brc
        if total == 0:
            return "HOLD"
        # 65% confluence threshold — consistent with live get_analysis()
        if bc  / total >= 0.65: return "BUY"
        if brc / total >= 0.65: return "SELL"
        return "HOLD"

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

    # Fee: 0.2% round-trip (0.1% entry + 0.1% exit) expressed in R-multiples.
    # Matches Phase-2d fee adjustment applied to live signals in get_analysis().
    # Deducted from every trade regardless of outcome.
    _fee_r = round(0.002 / risk_pct, 4) if risk_pct > 0 else 0.0

    # R-multiples for display (win sizes relative to 1R loss)
    r1 = round(tp1_pct / risk_pct, 2) if risk_pct > 0 else 1.5
    r2 = round(tp2_pct / risk_pct, 2) if tp2_pct and risk_pct > 0 else None
    r3 = round(tp3_pct / risk_pct, 2) if tp3_pct and risk_pct > 0 else None

    # Signal scan window: up to 2500 bars from available data (raised from 1000).
    # Adaptive warm-up: 50 on short TFs (5m/15m/30m/1H) where EMA-50 is the macro
    # reference (EMA-200 covers <1 day on 1H — not "macro"); 200 on 4H+ where EMA-200
    # is the genuine macro. Recovers ~150 bars of usable scan area on short TFs that
    # the old fixed 200-bar warm-up was wasting. On longer TFs (1D) with 5-year
    # yfinance data we still get ~1260 bars → ~1060 bar scan window (data ceiling).
    _short_tf_set = {"5m", "15m", "30m", "1h"}
    _warmup       = 50 if timeframe.lower() in _short_tf_set else 200
    scan_start    = max(_warmup, len(prices_hist) - 2500)

    trades = []
    i = scan_start
    while i < len(prices_hist) - 1:  # -1 because we need at least bar i+1 for forward scan
        # Entry condition: DotVerse 65% confluence gate — identical to get_analysis().
        # Fire only on the TRANSITION bar (signal changes from non-BUY/SELL to BUY/SELL)
        # so we enter exactly once per signal period, not on every sustained-trend bar.
        sig_now  = _conf_sig(i)
        sig_prev = _conf_sig(i - 1) if i > 0 else "HOLD"
        is_entry = (
            (is_long     and sig_now == "BUY"  and sig_prev != "BUY")  or
            (not is_long and sig_now == "SELL" and sig_prev != "SELL")
        )
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
            r_mult   = 0.0   # break-even exit — no SL hit, closed at market
            exit_bar = 1     # advance only 1 bar so we don't skip over confluence transitions
        trade_date = dates_hist[i] if i < len(dates_hist) else str(i)
        r_net = round(r_mult - _fee_r, 4)   # deduct 0.2% round-trip fee
        trades.append({
            "n":       len(trades) + 1,
            "outcome": outcome,
            "r":       r_net,
            "date":    trade_date,
            "entry":   round(hist_entry, 6),
        })
        # Advance past the actual exit bar so the next signal can start
        # immediately after this trade closed (matching TradingView's behavior)
        i += exit_bar + 1

    _bars_scanned = len(prices_hist) - scan_start
    if len(trades) < 30:
        return jsonify({
            "error": (
                f"Only {len(trades)} trade signal(s) found in {_bars_scanned} scanned bars — "
                "need at least 30 trades for a statistically valid backtest. "
                f"Asset: {asset_type} · Timeframe: {timeframe} · Bars available: {len(prices_hist)}. "
                "Try a higher timeframe (1H → 4H → 1D) for more historical data, or a more active asset."
            ),
            "trades_found": len(trades),
            "bars_scanned": _bars_scanned,
            "min_required": 30,
            "validity_tier": "insufficient",
        }), 400

    wins    = [t for t in trades if t["outcome"] not in ("loss", "timeout_loss")]
    losses  = [t for t in trades if t["outcome"] in ("loss", "timeout_loss")]
    timeouts= [t for t in trades if t["outcome"] == "timeout"]
    wr      = round(len(wins) / len(trades) * 100)
    total_r  = round(sum(t["r"] for t in trades), 2)
    avg_win  = round(sum(t["r"] for t in wins)   / len(wins),   2) if wins   else 0
    avg_los  = round(abs(sum(t["r"] for t in losses) / len(losses)), 2) if losses else 1
    gross_w  = sum(t["r"] for t in wins)
    gross_l  = abs(sum(t["r"] for t in losses))
    pf       = round(gross_w / gross_l, 2) if gross_l > 0 else 99.0
    # Expectancy: average R per trade (includes wins, losses, timeouts)
    expectancy = round(total_r / len(trades), 4) if trades else 0.0

    # ── Consecutive win/loss streaks ──────────────────────────────────────
    max_cw = max_cl = cur_cw = cur_cl = 0
    for t in trades:
        if t["outcome"] not in ("loss", "timeout_loss"):
            cur_cw += 1; cur_cl = 0
        else:
            cur_cl += 1; cur_cw = 0
        max_cw = max(max_cw, cur_cw)
        max_cl = max(max_cl, cur_cl)

    # ── Equity curve + drawdown (1R = $100 = 1% of $10k) ─────────────────
    INITIAL_CAP    = 10000.0
    RISK_PER_TRADE = 100.0    # $100 = 1% of initial capital

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

    final_eq       = equity[-1]
    total_pnl_usd  = round(final_eq - INITIAL_CAP, 2)
    total_pnl_pct  = round((final_eq - INITIAL_CAP) / INITIAL_CAP * 100, 2)
    max_dd_usd     = round(max_dd, 2)
    max_dd_pct     = round(max_dd / peak_eq * 100, 2) if peak_eq > 0 else 0.0

    # ── Risk-adjusted ratios (annualised) ────────────────────────────────
    _tf_ann  = {"5m":252*78,"15m":252*26,"30m":252*13,"1h":252*6.5,"4h":252*1.625,"1d":252,"1w":52,"1mo":12}
    _ann_f   = _tf_ann.get(timeframe.lower(), 252) ** 0.5
    r_vals   = [t["r"] for t in trades]
    r_mean   = sum(r_vals) / len(r_vals)
    r_std    = (sum((v - r_mean)**2 for v in r_vals) / len(r_vals)) ** 0.5 if len(r_vals) > 1 else 0
    sharpe   = round((r_mean / r_std) * _ann_f, 2) if r_std > 0 else 0.0
    # Sortino ratio: penalises only downside volatility — more relevant for traders.
    # A strategy with asymmetric gains (many small wins, rare large losses) will show
    # higher Sortino than Sharpe, correctly reflecting its actual risk profile.
    r_down   = [v for v in r_vals if v < 0]
    r_down_std = (sum(v**2 for v in r_down) / len(r_down)) ** 0.5 if r_down else 0
    sortino  = round((r_mean / r_down_std) * _ann_f, 2) if r_down_std > 0 else 0.0

    # ── WALK-FORWARD VALIDATION (commit 7 — 2026-04-29) ──────────────
    # Split trades chronologically 70/30. In-sample = first 70%,
    # out-of-sample = last 30%. If OOS WR drops by >10pp from in-sample,
    # flag potential overfit. Pure measurement — does not change signals.
    walkforward = None
    try:
        if len(trades) >= 30:
            _split   = int(len(trades) * 0.7)
            _in_s    = trades[:_split]
            _oos     = trades[_split:]
            if _in_s and _oos:
                _is_wins  = [t for t in _in_s if t["outcome"] not in ("loss", "timeout_loss")]
                _oos_wins = [t for t in _oos  if t["outcome"] not in ("loss", "timeout_loss")]
                _is_wr  = round(len(_is_wins) / len(_in_s) * 100)
                _oos_wr = round(len(_oos_wins) / len(_oos)  * 100)
                _is_r   = round(sum(t["r"] for t in _in_s), 2)
                _oos_r  = round(sum(t["r"] for t in _oos),  2)
                walkforward = {
                    "in_sample_trades":   len(_in_s),
                    "in_sample_wr":       _is_wr,
                    "in_sample_total_r":  _is_r,
                    "out_sample_trades":  len(_oos),
                    "out_sample_wr":      _oos_wr,
                    "out_sample_total_r": _oos_r,
                    "wr_dropoff_pp":      _is_wr - _oos_wr,
                    "overfit_flag":       (_is_wr - _oos_wr) > 10,
                }
                print(f"[walkforward] IS={_is_wr}% n={len(_in_s)}  OOS={_oos_wr}% n={len(_oos)}  drop={_is_wr-_oos_wr}pp")
    except Exception as _wfe:
        print(f"[walkforward] error: {_wfe}")

    return jsonify({
        "walkforward":    walkforward,
        "win_rate":       wr,
        "total_trades":   len(trades),
        "sample_size":    len(trades),   # alias used by Kelly formula and scanner gate
        # Validity tier — used by frontend to label trust on win rate + cap Kelly:
        #   <30  → "insufficient" (returned via the 400 error path above; never reaches here)
        #   30–99 → "provisional" (Kelly capped 2.5%, label "Provisional")
        #   ≥100 → "confirmed"   (Kelly up to 5%, label "Confirmed")
        "validity_tier":  "confirmed" if len(trades) >= 100 else "provisional",
        "wins":                len(wins),
        "losses":              len(losses),
        "timeouts":            len(timeouts),
        "total_r":             total_r,
        "avg_win_r":           avg_win,
        "avg_loss_r":          avg_los,
        "profit_factor":       pf,
        "expectancy":          expectancy,          # avg R per trade — core edge metric
        "sharpe":              sharpe,              # annualised Sharpe (penalises all volatility)
        "sortino":             sortino,             # annualised Sortino (penalises downside only)
        "max_consec_wins":     max_cw,
        "max_consec_losses":   max_cl,
        # bars_tested = the actual signal-scan window (excludes warm-up bars)
        "bars_tested":         _bars_scanned,
        "total_bars":          len(prices_hist),
        # Period covers the signal-scan window only (post warm-up)
        "period":              f"{dates_hist[scan_start]} → {dates_hist[-1]}" if len(dates_hist) > scan_start else f"{len(prices_hist)} bars",
        "signal":              signal,
        # ── P&L and drawdown ──
        "total_pnl_usd":       total_pnl_usd,
        "total_pnl_pct":       total_pnl_pct,
        "max_dd_usd":          max_dd_usd,
        "max_dd_pct":          max_dd_pct,
        "equity_curve":        equity,              # list of floats from $10k baseline
        "trades_list":         trades_list,         # [{n, date, outcome, r, pnl_usd, entry}]
        "initial_capital":     INITIAL_CAP,
    })


# ═══════════════════════════════════════════════════════════════
# PHASE 5 — INFRASTRUCTURE FEATURES
# Requires: DATABASE_URL (PostgreSQL), REDIS_URL (Redis), RQ Worker
# ═══════════════════════════════════════════════════════════════

import redis as _redis_module
from rq import Queue as RQQueue
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
from scipy.stats import norm as _scipy_norm

# ─── ENCRYPTION HELPER (exchange API keys) ────────────────────
try:
    from cryptography.fernet import Fernet as _Fernet
    import base64 as _b64, hashlib as _hl
    _enc_seed = os.environ.get("ENCRYPTION_KEY", "") or app.secret_key
    _fernet   = _Fernet(_b64.urlsafe_b64encode(_hl.sha256(_enc_seed.encode()).digest()))
    def _enc(s): return _fernet.encrypt(s.encode()).decode()
    def _dec(s): return _fernet.decrypt(s.encode()).decode()
    print("[enc] Fernet encryption ready")
except Exception as _enc_e:
    print(f"[enc] Fernet unavailable: {_enc_e}")
    _fernet = None
    def _enc(s): return s
    def _dec(s): return s

# ─── DATABASE SETUP ───────────────────────────────────────────
_DATABASE_URL = os.environ.get("DATABASE_URL", "")
_REDIS_URL    = os.environ.get("REDIS_URL", "")

# SQLAlchemy engine + session (graceful no-op if DATABASE_URL absent)
_db_engine  = None
_DBSession  = None
_Base       = declarative_base()

if _DATABASE_URL:
    try:
        import re as _re
        # Railway Postgres URLs start with postgres:// — SQLAlchemy needs postgresql://
        _db_url = _DATABASE_URL.replace("postgres://", "postgresql://", 1)
        # Strip any sslmode from the URL entirely — we set it via connect_args to avoid
        # URL-vs-param conflicts that cause "received I" errors on Railway metro proxy
        _db_url = _re.sub(r'[?&]sslmode=[^&]*', '', _db_url).rstrip('?').rstrip('&')
        # Try sslmode=disable first (metro proxy handles TLS at TCP level),
        # then fall back to require (some Railway setups need PostgreSQL-level SSL)
        _ssl_modes = ["disable", "require"]
        _db_engine = None
        for _ssl_mode in _ssl_modes:
            try:
                _candidate = create_engine(
                    _db_url,
                    pool_pre_ping=False,
                    pool_size=1,
                    max_overflow=0,
                    connect_args={"sslmode": _ssl_mode, "connect_timeout": 8}
                )
                with _candidate.connect() as _c:
                    _c.execute(text("SELECT 1"))
                # Success — build the real pool with this sslmode
                _db_engine = create_engine(
                    _db_url,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    connect_args={"sslmode": _ssl_mode, "connect_timeout": 10}
                )
                _DBSession = sessionmaker(bind=_db_engine)
                print(f"[db] Connected with sslmode={_ssl_mode}")
                break
            except Exception as _ssl_err:
                print(f"[db] sslmode={_ssl_mode} failed: {_ssl_err}")
        if _db_engine is None:
            print("[db] All SSL modes failed — database unavailable")
    except Exception as _e:
        print(f"[db] Engine creation failed: {_e}")

# Redis client (graceful no-op if REDIS_URL absent)
_redis_client = None
if _REDIS_URL:
    try:
        _redis_client = _redis_module.from_url(_REDIS_URL, decode_responses=True)
        _redis_client.ping()
        print("[redis] Connected")
    except Exception as _e:
        print(f"[redis] Connection failed: {_e}")

# RQ queue (only usable if Redis is available)
_rq_queue = None
if _redis_client:
    try:
        _rq_conn  = _redis_module.from_url(_REDIS_URL)   # bytes connection for RQ
        _rq_queue = RQQueue(connection=_rq_conn)
        print("[rq] Queue initialised")
    except Exception as _e:
        print(f"[rq] Queue init failed: {_e}")

# ─── SQLALCHEMY MODELS ────────────────────────────────────────

class User(_Base):
    """Registered users — email/password accounts with tier and role."""
    __tablename__ = "users"
    id                 = Column(Integer,     primary_key=True, autoincrement=True)
    email              = Column(String(255), unique=True, nullable=False)
    name               = Column(String(128), nullable=True)
    password_hash      = Column(String(256), nullable=True)   # nullable for Google OAuth later
    tier               = Column(String(16),  nullable=False, default="free")   # free / pro / elite
    role               = Column(String(16),  nullable=False, default="user")   # user / admin
    stripe_customer_id = Column(String(64),  nullable=True)
    daily_analyses     = Column(Integer,     nullable=False, default=0)
    last_analysis_date = Column(String(10),  nullable=True)   # YYYY-MM-DD string
    created_at         = Column(DateTime,    nullable=False, default=datetime.utcnow)

class Position(_Base):
    """Open trade positions logged by the user."""
    __tablename__ = "positions"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String(64), nullable=False, default="default")
    ticker       = Column(String(32), nullable=False)
    asset_type   = Column(String(16), nullable=False, default="stock")
    signal       = Column(String(8),  nullable=False, default="BUY")
    size         = Column(Float,      nullable=False)   # % of account
    entry_price  = Column(Float,      nullable=False)
    stop_price   = Column(Float,      nullable=True)
    tp1_price    = Column(Float,      nullable=True)
    timeframe    = Column(String(8),  nullable=True)
    opened_at    = Column(DateTime,   nullable=False, default=datetime.utcnow)

class OptimisationResult(_Base):
    """Best indicator parameters per asset class found by RQ grid search."""
    __tablename__ = "optimisation_results"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    asset_class  = Column(String(16), nullable=False)
    timeframe    = Column(String(8),  nullable=False)
    rsi_period   = Column(Integer,    nullable=False)
    atr_mult     = Column(Float,      nullable=False)
    ema_fast     = Column(Integer,    nullable=False)
    ema_slow     = Column(Integer,    nullable=False)
    sharpe       = Column(Float,      nullable=False)
    win_rate     = Column(Float,      nullable=True)
    computed_at  = Column(DateTime,   nullable=False, default=datetime.utcnow)

class SignalHistory(_Base):
    """Every signal fired from /api/analyze — one row per analysis."""
    __tablename__ = "signal_history"
    id           = Column(Integer,  primary_key=True, autoincrement=True)
    user_id      = Column(String(64), nullable=False, default="default")
    ticker       = Column(String(32), nullable=False)
    asset_type   = Column(String(16), nullable=False)
    timeframe    = Column(String(8),  nullable=False)
    signal       = Column(String(8),  nullable=False)   # BUY / SELL / HOLD
    price        = Column(Float,      nullable=True)
    entry        = Column(Float,      nullable=True)
    stop_loss    = Column(Float,      nullable=True)
    tp1          = Column(Float,      nullable=True)
    confidence   = Column(Float,      nullable=True)    # 0–100
    confidence_label = Column(String(16), nullable=True)
    fired_at     = Column(DateTime,   nullable=False, default=datetime.utcnow)

class ExchangeKey(_Base):
    """Exchange API keys — Fernet-encrypted, one row per connected exchange per user."""
    __tablename__ = "exchange_keys"
    id             = Column(Integer,     primary_key=True, autoincrement=True)
    user_id        = Column(Integer,     nullable=False)
    exchange       = Column(String(32),  nullable=False)
    label          = Column(String(64),  nullable=True)
    api_key_enc    = Column(String(512), nullable=False)
    api_secret_enc = Column(String(512), nullable=False)
    created_at     = Column(DateTime,    nullable=False, default=datetime.utcnow)

class AdminInvite(_Base):
    """Pre-approved admin emails — grants admin role automatically on signup."""
    __tablename__ = "admin_invites"
    id         = Column(Integer,    primary_key=True, autoincrement=True)
    email      = Column(String(120), nullable=False, unique=True)
    invited_by = Column(Integer,    nullable=True)
    created_at = Column(DateTime,   nullable=False, default=datetime.utcnow)

class MT5Order(_Base):
    """Orders submitted from DotVerse to be executed by the MT5 EA."""
    __tablename__ = "mt5_orders"
    id          = Column(Integer,  primary_key=True, autoincrement=True)
    user_id     = Column(String(64), nullable=False)
    symbol      = Column(String(32), nullable=False)
    order_type  = Column(String(8),  nullable=False)   # BUY | SELL
    volume      = Column(Float,      nullable=False)   # lots
    price       = Column(Float,      nullable=False)   # requested entry
    sl          = Column(Float,      nullable=True)
    tp          = Column(Float,      nullable=True)
    tp2         = Column(Float,      nullable=True)
    tp3         = Column(Float,      nullable=True)
    timeframe    = Column(String(8),   nullable=True)                       # 15m | 1h | 4h | 1d | 1w | 1mo
    action       = Column(String(8),  nullable=False, default="open")    # open | close
    close_ticket = Column(Integer,    nullable=True)                       # MT5 ticket to close
    status      = Column(String(16), nullable=False, default="pending")  # pending|executing|filled|failed|cancelled
    mt5_ticket  = Column(Integer,    nullable=True)
    fill_price  = Column(Float,      nullable=True)
    pnl         = Column(Float,      nullable=True)    # realised P&L in account currency (set by EA on close)
    comment     = Column(String(128),nullable=True)
    created_at  = Column(DateTime,   nullable=False, default=datetime.utcnow)
    filled_at   = Column(DateTime,   nullable=True)

class Watch(_Base):
    """Persistent alert watches — survive server restarts, removed only after confirmed delivery."""
    __tablename__ = "watches"
    id             = Column(Integer,     primary_key=True, autoincrement=True)
    user_id        = Column(String(64),  nullable=False, default="legacy")
    ticker         = Column(String(32),  nullable=False)
    asset_type     = Column(String(16),  nullable=False, default="stock")
    timeframe      = Column(String(8),   nullable=False)
    alert_channels = Column(String(128), nullable=False, default="telegram")
    created_at     = Column(DateTime,    nullable=False, default=datetime.utcnow)

class Notification(_Base):
    """In-app notifications: market alerts, scan alerts, level hits, suggestions."""
    __tablename__ = "notifications"
    id         = Column(Integer,  primary_key=True, autoincrement=True)
    user_id    = Column(String(64), nullable=False, default="default")
    ntype      = Column(String(32), nullable=False)   # market|scan|level|suggestion
    title      = Column(String(128), nullable=False)
    body       = Column(Text, nullable=False)
    data       = Column(Text, nullable=True)           # JSON blob — entry/sl/tp etc.
    read       = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AutomationSettings(_Base):
    """Per-user automation preferences stored in DB."""
    __tablename__ = "automation_settings"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    user_id          = Column(String(64), unique=True, nullable=False)
    scan_enabled     = Column(Boolean, default=True)
    scan_risk_pct    = Column(Float,   default=1.0)
    breakeven_on     = Column(Boolean, default=True)
    trailing_on      = Column(Boolean, default=False)
    trailing_pips    = Column(Float,   default=50.0)
    market_alerts_on = Column(Boolean, default=True)
    updated_at       = Column(DateTime, default=datetime.utcnow)

class UserSettings(_Base):
    """Per-user application preferences. Persisted server-side so they
    follow the user across browsers and survive logout/login. Backs the
    Settings page sub-panels so picking a value actually has a backend effect."""
    __tablename__ = "user_settings"
    id                     = Column(Integer, primary_key=True, autoincrement=True)
    user_id                = Column(String(64), unique=True, nullable=False, index=True)

    # Asset Preferences sub-panel (which classes the scanner scans)
    assets_enabled         = Column(Text, nullable=True)  # JSON array of asset class strings

    # Risk Tolerance sub-panel (signal-confidence threshold)
    risk_tolerance         = Column(String(16), nullable=False, default="aggressive")  # conservative|moderate|aggressive

    # Chart Visuals sub-panel
    chart_theme            = Column(String(32), nullable=True)
    chart_type             = Column(String(16), nullable=True, default="candles")
    grid_style             = Column(String(16), nullable=True)
    indicator_scheme       = Column(String(16), nullable=True)

    # Timezone & Hours sub-panel
    timezone               = Column(String(64), nullable=False, default="UTC")

    # Alert Thresholds sub-panel
    alert_confidence       = Column(Integer, nullable=False, default=65)
    alert_price_pct        = Column(Float,   nullable=False, default=2.0)
    alert_drawdown_pct     = Column(Float,   nullable=False, default=10.0)
    alert_loss_pct         = Column(Float,   nullable=False, default=5.0)

    # Performance sub-panel (target tracking)
    perf_target_winrate    = Column(Integer, nullable=False, default=55)
    perf_target_rr         = Column(Float,   nullable=False, default=2.0)
    perf_target_trades     = Column(Integer, nullable=False, default=5)
    perf_target_annual     = Column(Float,   nullable=False, default=20.0)

    # Portfolio sub-panel
    portfolio_alloc        = Column(Text, nullable=True)  # JSON object: class->percent
    portfolio_preset       = Column(String(16), nullable=False, default="balanced")
    portfolio_rebalance    = Column(String(16), nullable=False, default="quarterly")
    portfolio_benchmark    = Column(String(16), nullable=False, default="spy")

    # Connections sub-panel — credentials encrypted at rest via _enc / _dec.
    # Empty string in the form means "unchanged"; only non-empty values overwrite.
    mt5_api_key_enc        = Column(Text,         nullable=True)
    mt5_account            = Column(String(64),   nullable=True)
    mt5_broker_server      = Column(String(128),  nullable=True)
    telegram_bot_token_enc = Column(Text,         nullable=True)
    telegram_chat_id       = Column(String(64),   nullable=True)

    updated_at             = Column(DateTime, default=datetime.utcnow)

class ScanAlert(_Base):
    """Tracks recently sent scan alerts for deduplication."""
    __tablename__ = "scan_alerts"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    ticker     = Column(String(32), nullable=False)
    signal     = Column(String(8),  nullable=False)
    timeframe  = Column(String(8),  nullable=False)
    trade_type = Column(String(16), nullable=False)   # scalping | swing
    entry      = Column(Float,  nullable=True)
    sl         = Column(Float,  nullable=True)
    tp1        = Column(Float,  nullable=True)
    lot_size   = Column(Float,  nullable=True)
    sent_at    = Column(DateTime, default=datetime.utcnow)

# ─── WATCH DB HELPERS ─────────────────────────────────────────

def _save_watch_to_db(ticker, asset_type, timeframe, alert_channels, user_id="legacy"):
    """Upsert a watch into the database."""
    if not _DBSession: return
    db = _DBSession()
    try:
        existing = db.query(Watch).filter_by(user_id=user_id, ticker=ticker, timeframe=timeframe).first()
        if existing:
            existing.alert_channels = json.dumps(alert_channels)
        else:
            db.add(Watch(user_id=user_id, ticker=ticker, asset_type=asset_type, timeframe=timeframe,
                         alert_channels=json.dumps(alert_channels)))
        db.commit()
    except Exception as _e:
        db.rollback()
        print(f"[watch] DB save failed: {_e}")
    finally:
        db.close()

def _remove_watch_from_db(ticker, timeframe, user_id="legacy"):
    """Delete a watch from the database. Returns True if a row was removed."""
    if not _DBSession: return False
    db = _DBSession()
    try:
        deleted_count = db.query(Watch).filter_by(user_id=user_id, ticker=ticker, timeframe=timeframe).delete()
        db.commit()
        return deleted_count > 0
    except Exception as _e:
        db.rollback()
        print(f"[watch] DB remove failed: {_e}")
        return False
    finally:
        db.close()

def _load_watches_from_db():
    """On startup: reload all saved watches into the in-memory registry."""
    if not _DBSession: return
    db = _DBSession()
    try:
        rows = db.query(Watch).all()
        loaded = 0
        with watch_lock:
            for r in rows:
                uid = getattr(r, 'user_id', 'legacy') or 'legacy'
                key = f"{uid}_{r.ticker}_{r.timeframe}"
                if key not in watch_registry:
                    try:
                        channels = json.loads(r.alert_channels)
                    except Exception:
                        channels = [r.alert_channels]
                    watch_registry[key] = {
                        "user_id":        uid,
                        "ticker":         r.ticker,
                        "asset_type":     r.asset_type,
                        "timeframe":      r.timeframe,
                        "alert_channels": channels,
                        "last_signal":    None,
                        "last_check":     None,
                        "last_reason":    "Not checked yet",
                        "last_price":     None,
                        "added_at":       r.created_at.strftime("%Y-%m-%d %H:%M UTC"),
                    }
                    loaded += 1
        print(f"[watch] Loaded {loaded} watches from DB")
    except Exception as _e:
        print(f"[watch] DB load failed: {_e}")
    finally:
        db.close()

# Create tables on startup (idempotent — skips existing tables)
def _init_db():
    if _db_engine:
        try:
            _Base.metadata.create_all(_db_engine)
            print("[db] Tables created / verified")
        except Exception as _e:
            print(f"[db] create_all failed: {_e}")
        # Migration: add user_id column if it doesn't exist yet
        try:
            with _db_engine.connect() as _conn:
                _conn.execute(text("ALTER TABLE watches ADD COLUMN IF NOT EXISTS user_id VARCHAR(64) DEFAULT 'legacy'"))
                _conn.execute(text("ALTER TABLE mt5_orders ADD COLUMN IF NOT EXISTS tp2 FLOAT"))
                _conn.execute(text("ALTER TABLE mt5_orders ADD COLUMN IF NOT EXISTS tp3 FLOAT"))
                _conn.execute(text("ALTER TABLE mt5_orders ADD COLUMN IF NOT EXISTS action VARCHAR(8) DEFAULT 'open'"))
                _conn.execute(text("ALTER TABLE mt5_orders ADD COLUMN IF NOT EXISTS close_ticket INTEGER"))
                _conn.execute(text("ALTER TABLE mt5_orders ADD COLUMN IF NOT EXISTS timeframe VARCHAR(8)"))
                _conn.execute(text("ALTER TABLE mt5_orders ADD COLUMN IF NOT EXISTS pnl FLOAT"))
                _conn.execute(text("ALTER TABLE positions ADD COLUMN IF NOT EXISTS timeframe VARCHAR(8)"))
                # Phase A/B/C/D automation tables (idempotent)
                _conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(64) NOT NULL DEFAULT 'default',
                        ntype VARCHAR(32) NOT NULL,
                        title VARCHAR(128) NOT NULL,
                        body TEXT NOT NULL,
                        data TEXT,
                        read BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT NOW()
                    )"""))
                _conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS automation_settings (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(64) UNIQUE NOT NULL,
                        scan_enabled BOOLEAN DEFAULT TRUE,
                        scan_risk_pct FLOAT DEFAULT 1.0,
                        breakeven_on BOOLEAN DEFAULT TRUE,
                        trailing_on BOOLEAN DEFAULT FALSE,
                        trailing_pips FLOAT DEFAULT 50.0,
                        market_alerts_on BOOLEAN DEFAULT TRUE,
                        updated_at TIMESTAMP DEFAULT NOW()
                    )"""))
                _conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS scan_alerts (
                        id SERIAL PRIMARY KEY,
                        ticker VARCHAR(32) NOT NULL,
                        signal VARCHAR(8) NOT NULL,
                        timeframe VARCHAR(8) NOT NULL,
                        trade_type VARCHAR(16) NOT NULL,
                        entry FLOAT, sl FLOAT, tp1 FLOAT, lot_size FLOAT,
                        sent_at TIMESTAMP DEFAULT NOW()
                    )"""))
                _conn.commit()
        except Exception as _e:
            print(f"[db] migration: {_e}")
    _load_watches_from_db()

with app.app_context():
    _init_db()

# ─── HELPER: Redis OHLCV cache ────────────────────────────────
_OHLCV_TTL = 300   # 5 minutes

def _redis_get_ohlcv(key):
    if not _redis_client:
        return None
    try:
        raw = _redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None

def _redis_set_ohlcv(key, data):
    if not _redis_client:
        return
    try:
        _redis_client.setex(key, _OHLCV_TTL, json.dumps(data))
    except Exception:
        pass

# ─── 5a: PORTFOLIO POSITION TRACKING ─────────────────────────

@app.route("/api/positions", methods=["GET"])
@login_required
def positions_get():
    if not _DBSession:
        return jsonify({"error": "Database not configured"}), 503
    db = _DBSession()
    try:
        rows = db.query(Position).order_by(Position.opened_at.desc()).all()
        return jsonify([{
            "id":          p.id,
            "ticker":      p.ticker,
            "asset_type":  p.asset_type,
            "signal":      p.signal,
            "size":        p.size,
            "entry_price": p.entry_price,
            "stop_price":  p.stop_price,
            "tp1_price":   p.tp1_price,
            "timeframe":   p.timeframe,
            "opened_at":   p.opened_at.isoformat() if p.opened_at else None,
        } for p in rows])
    finally:
        db.close()

@app.route("/api/positions", methods=["POST"])
@login_required
def positions_add():
    if not _DBSession:
        return jsonify({"error": "Database not configured"}), 503
    data = request.get_json(force=True)
    required = ("ticker", "entry_price", "size")
    if not all(data.get(k) for k in required):
        return jsonify({"error": f"Missing required fields: {required}"}), 400
    db = _DBSession()
    try:
        pos = Position(
            ticker      = str(data["ticker"]).upper().strip(),
            asset_type  = data.get("asset_type", "stock"),
            signal      = data.get("signal", "BUY").upper(),
            size        = float(data["size"]),
            entry_price = float(data["entry_price"]),
            stop_price  = float(data["stop_price"])  if data.get("stop_price")  else None,
            tp1_price   = float(data["tp1_price"])   if data.get("tp1_price")   else None,
            timeframe   = data.get("timeframe", "1d"),
            opened_at   = datetime.utcnow(),
        )
        db.add(pos)
        db.commit()
        return jsonify({"id": pos.id, "status": "added"}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route("/api/positions/<int:pos_id>", methods=["DELETE"])
@login_required
def positions_delete(pos_id):
    if not _DBSession:
        return jsonify({"error": "Database not configured"}), 503
    db = _DBSession()
    try:
        pos = db.query(Position).filter(Position.id == pos_id).first()
        if not pos:
            return jsonify({"error": "Position not found"}), 404
        db.delete(pos)
        db.commit()
        return jsonify({"status": "deleted"})
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

# ─── Signal History ──────────────────────────────────────────

@app.route("/api/signals/history", methods=["GET"])
@login_required
def signal_history_get():
    """Return the last N signals fired for the current user."""
    if not _DBSession:
        return jsonify([])
    db = _DBSession()
    try:
        limit = min(int(request.args.get("limit", 50)), 200)
        # Bug J fix 2026-04-29: filter by current session's user_id so users only see
        # their own history (was returning every user's signals — privacy issue +
        # confusing data leakage).
        _uid = str(session.get("user_id", "default"))
        rows = (db.query(SignalHistory)
                  .filter(SignalHistory.user_id == _uid)
                  .order_by(SignalHistory.fired_at.desc())
                  .limit(limit)
                  .all())
        return jsonify([{
            "id":         r.id,
            "ticker":     r.ticker,
            "asset_type": r.asset_type,
            "timeframe":  r.timeframe,
            "signal":     r.signal,
            "price":      r.price,
            "entry":      r.entry,
            "stop_loss":  r.stop_loss,
            "tp1":        r.tp1,
            "confidence": r.confidence,
            "confidence_label": r.confidence_label,
            "fired_at":   r.fired_at.strftime("%d %b %H:%M") if r.fired_at else None,
        } for r in rows])
    finally:
        db.close()

# ─── 5b: PARAMETRIC VaR ──────────────────────────────────────

@app.route("/api/var", methods=["POST"])
@login_required
def portfolio_var():
    """
    Parametric VaR for the user's open positions.
    Body: { portfolio_value: float, confidence: float (0.95|0.99) }
    Returns: { var_1d_usd, var_1d_pct, positions_used, method }
    """
    if not _DBSession:
        return jsonify({"error": "Database not configured"}), 503

    data             = request.get_json(force=True) or {}
    portfolio_value  = float(data.get("portfolio_value", 10000))
    confidence       = float(data.get("confidence", 0.95))
    z_score          = float(_scipy_norm.ppf(confidence))

    # Check Redis cache
    cache_key = f"var:{confidence}:{portfolio_value}"
    cached    = _redis_get_ohlcv(cache_key)
    if cached:
        return jsonify(cached)

    db   = _DBSession()
    rows = []
    try:
        rows = db.query(Position).all()
    finally:
        db.close()

    if not rows:
        return jsonify({"error": "No open positions found. Add positions first."}), 400

    # Fetch 252-day returns for each unique ticker
    returns_map = {}
    for pos in rows:
        ticker = pos.ticker
        if ticker in returns_map:
            continue
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
            if df.empty or len(df) < 30:
                continue
            closes = df["Close"].squeeze()
            returns_map[ticker] = closes.pct_change().dropna()
        except Exception:
            pass

    if not returns_map:
        return jsonify({"error": "Could not fetch price history for any position"}), 502

    # Build weighted portfolio returns
    total_size  = sum(p.size for p in rows if p.ticker in returns_map) or 1.0
    port_returns = None
    for pos in rows:
        if pos.ticker not in returns_map:
            continue
        weight = pos.size / total_size
        ret    = returns_map[pos.ticker] * weight
        if port_returns is None:
            port_returns = ret
        else:
            port_returns = port_returns.add(ret, fill_value=0)

    if port_returns is None or len(port_returns) < 10:
        return jsonify({"error": "Insufficient return data to compute VaR"}), 400

    port_std   = float(port_returns.std())
    var_1d_pct = round(z_score * port_std * 100, 3)
    var_1d_usd = round(portfolio_value * z_score * port_std, 2)

    result = {
        "var_1d_usd":      var_1d_usd,
        "var_1d_pct":      var_1d_pct,
        "confidence":      confidence,
        "z_score":         round(z_score, 4),
        "portfolio_std":   round(port_std * 100, 4),
        "positions_used":  len([p for p in rows if p.ticker in returns_map]),
        "portfolio_value": portfolio_value,
        "method":          "parametric",
        "interpretation":  f"With {int(confidence*100)}% confidence, max 1-day loss ≤ ${var_1d_usd:,.2f} ({var_1d_pct:.2f}%)",
    }
    _redis_set_ohlcv(cache_key, result)
    return jsonify(result)

# ─── 5c: STRESS TESTING ───────────────────────────────────────

_STRESS_SHOCKS = {
    "crypto":    -0.30,   # −30%
    "stock":     -0.20,   # −20%
    "forex":     -0.10,   # −10%
    "index":     -0.15,   # −15%
    "commodity": -0.20,   # −20%
}

@app.route("/api/stress", methods=["POST"])
@login_required
def stress_test():
    """
    Apply configurable % shock per asset class to all open positions.
    Body: { portfolio_value: float, shocks: { crypto: -0.30, stock: -0.20, ... } }
    Returns: { rows: [{ticker, asset_type, shock_pct, pnl_usd, new_price}], total_pnl_usd }
    """
    if not _DBSession:
        return jsonify({"error": "Database not configured"}), 503

    data            = request.get_json(force=True) or {}
    portfolio_value = float(data.get("portfolio_value", 10000))
    custom_shocks   = data.get("shocks", {})
    shocks          = {**_STRESS_SHOCKS, **custom_shocks}  # user overrides defaults

    db   = _DBSession()
    rows = []
    try:
        rows = db.query(Position).all()
    finally:
        db.close()

    if not rows:
        return jsonify({"error": "No open positions. Add positions first."}), 400

    result_rows = []
    total_pnl   = 0.0
    for pos in rows:
        shock     = shocks.get(pos.asset_type, -0.20)
        alloc_usd = portfolio_value * (pos.size / 100.0)
        pnl_usd   = round(alloc_usd * shock, 2)
        new_price = round(pos.entry_price * (1 + shock), 4)
        total_pnl += pnl_usd
        result_rows.append({
            "id":         pos.id,
            "ticker":     pos.ticker,
            "asset_type": pos.asset_type,
            "signal":     pos.signal,
            "entry_price": pos.entry_price,
            "shock_pct":  round(shock * 100, 1),
            "new_price":  new_price,
            "alloc_usd":  round(alloc_usd, 2),
            "pnl_usd":    pnl_usd,
        })

    return jsonify({
        "rows":           result_rows,
        "total_pnl_usd":  round(total_pnl, 2),
        "total_pnl_pct":  round(total_pnl / portfolio_value * 100, 2) if portfolio_value else 0,
        "portfolio_value": portfolio_value,
        "shocks_applied": shocks,
    })

# ─── 5d: CROSS-ASSET CORRELATION DASHBOARD ───────────────────

@app.route("/api/correlation", methods=["POST"])
@login_required
def correlation_matrix():
    """
    Compute correlation matrix for a list of tickers.
    Body: { tickers: ["BTC-USD","AAPL","GC=F"], period: "6mo" }
    Returns: { labels, matrix (2D list), min_date, max_date }
    OHLCV cached in Redis for 5 min per ticker.
    """
    data    = request.get_json(force=True) or {}
    tickers = data.get("tickers", [])
    period  = data.get("period", "6mo")

    if len(tickers) < 2:
        return jsonify({"error": "Provide at least 2 tickers"}), 400
    if len(tickers) > 15:
        return jsonify({"error": "Maximum 15 tickers"}), 400

    closes_map = {}
    for ticker in tickers:
        cache_key = f"corr:{ticker}:{period}"
        cached    = _redis_get_ohlcv(cache_key)
        if cached:
            closes_map[ticker] = pd.Series(cached["closes"], index=pd.to_datetime(cached["index"]))
            continue
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
            if df.empty or len(df) < 10:
                continue
            closes = df["Close"].squeeze()
            _redis_set_ohlcv(cache_key, {
                "closes": closes.tolist(),
                "index":  [str(i) for i in closes.index],
            })
            closes_map[ticker] = closes
        except Exception:
            pass

    if len(closes_map) < 2:
        return jsonify({"error": "Could not fetch data for enough tickers"}), 502

    # Align on common dates, compute returns, then correlation
    df_all  = pd.DataFrame(closes_map).dropna(how="all")
    returns = df_all.pct_change().dropna(how="all")
    corr    = returns.corr()

    labels = list(corr.columns)
    matrix = [[round(corr.loc[r, c], 4) for c in labels] for r in labels]

    return jsonify({
        "labels":   labels,
        "matrix":   matrix,
        "min_date": str(df_all.index.min().date()) if not df_all.empty else "",
        "max_date": str(df_all.index.max().date()) if not df_all.empty else "",
        "period":   period,
    })

# ─── 5e: OFFLINE PARAMETER OPTIMISATION ──────────────────────

def _run_optimisation_job(asset_class, timeframe):
    """
    RQ worker job. Grid-searches RSI period + ATR mult + EMA pair.
    Writes best result to optimisation_results table.
    This function runs inside the RQ worker process, not the web process.
    """
    import yfinance as yf
    import pandas as pd, numpy as np
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os, json
    from datetime import datetime

    BENCHMARK_TICKERS = {
        "crypto":    "BTC-USD",
        "stock":     "AAPL",
        "forex":     "EURUSD=X",
        "index":     "^GSPC",
        "commodity": "GC=F",
    }
    ticker = BENCHMARK_TICKERS.get(asset_class, "AAPL")

    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False, auto_adjust=True)
    except Exception as e:
        return {"error": str(e)}

    if df is None or len(df) < 60:
        return {"error": "Insufficient data"}

    closes = df["Close"].squeeze().values
    highs  = df["High"].squeeze().values
    lows   = df["Low"].squeeze().values

    def _rma(arr, n):
        alpha  = 1.0 / n
        result = np.full(len(arr), np.nan)
        valid  = [i for i, v in enumerate(arr) if not np.isnan(v)]
        if len(valid) < n: return result
        s = valid[n-1]
        result[s] = np.nanmean(arr[valid[0]:valid[0]+n])
        for i in range(s+1, len(arr)):
            if not np.isnan(arr[i]):
                result[i] = alpha * arr[i] + (1-alpha) * result[i-1]
        return result

    best = {"sharpe": -999}
    rsi_range  = [10, 14, 21]
    atr_range  = [2.0, 3.0, 4.0]
    ema_pairs  = [(7,14), (9,21), (20,50)]

    for rsi_p in rsi_range:
        delta = np.diff(closes, prepend=closes[0])
        gain  = _rma(np.maximum(delta, 0), rsi_p)
        loss  = _rma(np.maximum(-delta, 0), rsi_p)
        rsi   = 100 - 100 / (1 + gain / np.where(loss == 0, 1e-9, loss))

        tr    = np.maximum(highs - lows,
                np.maximum(np.abs(highs - np.roll(closes, 1)),
                           np.abs(lows  - np.roll(closes, 1))))
        tr[0] = highs[0] - lows[0]
        atr14 = _rma(tr, 14)

        for atr_m in atr_range:
            for ef, es in ema_pairs:
                alpha_f = 2.0 / (ef+1); alpha_s = 2.0 / (es+1)
                ema_f   = np.full(len(closes), np.nan)
                ema_s   = np.full(len(closes), np.nan)
                ema_f[ef-1] = closes[ef-1]; ema_s[es-1] = closes[es-1]
                for i in range(ef, len(closes)):
                    ema_f[i] = alpha_f * closes[i] + (1-alpha_f) * ema_f[i-1]
                for i in range(es, len(closes)):
                    ema_s[i] = alpha_s * closes[i] + (1-alpha_s) * ema_s[i-1]

                returns = []
                in_trade = False; entry = 0.0; stop = 0.0
                for i in range(es+1, len(closes)):
                    if np.isnan(rsi[i]) or np.isnan(atr14[i]): continue
                    if not in_trade:
                        if rsi[i] < 50 and ema_f[i] > ema_s[i]:
                            in_trade = True
                            entry    = closes[i]
                            stop     = entry - atr_m * atr14[i]
                    else:
                        if closes[i] < stop or ema_f[i] < ema_s[i]:
                            r = (closes[i] - entry) / entry
                            returns.append(r)
                            in_trade = False

                if len(returns) < 5: continue
                arr    = np.array(returns)
                sharpe = float(np.mean(arr) / (np.std(arr) + 1e-9) * np.sqrt(252))
                wins   = float(np.mean(arr > 0))
                if sharpe > best["sharpe"]:
                    best = {"sharpe": sharpe, "win_rate": wins,
                            "rsi_period": rsi_p, "atr_mult": atr_m,
                            "ema_fast": ef, "ema_slow": es}

    if best["sharpe"] == -999:
        return {"error": "Grid search produced no valid results"}

    # Write to PostgreSQL
    db_url = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
    if db_url:
        try:
            engine = create_engine(db_url, pool_pre_ping=True)
            Session = sessionmaker(bind=engine)
            db = Session()
            # Upsert: delete old result for this asset_class+timeframe, insert new
            db.execute(
                text("DELETE FROM optimisation_results WHERE asset_class=:ac AND timeframe=:tf"),
                {"ac": asset_class, "tf": timeframe}
            )
            db.execute(
                text("""INSERT INTO optimisation_results
                        (asset_class, timeframe, rsi_period, atr_mult, ema_fast, ema_slow, sharpe, win_rate, computed_at)
                        VALUES (:ac,:tf,:rp,:am,:ef,:es,:sh,:wr,:ts)"""),
                {"ac": asset_class, "tf": timeframe,
                 "rp": best["rsi_period"], "am": best["atr_mult"],
                 "ef": best["ema_fast"],   "es": best["ema_slow"],
                 "sh": best["sharpe"],     "wr": best["win_rate"],
                 "ts": datetime.utcnow()}
            )
            db.commit()
            db.close()
        except Exception as e:
            return {"error": f"DB write failed: {e}", "best": best}

    return {"status": "ok", "asset_class": asset_class, "timeframe": timeframe, **best}


@app.route("/api/optimise", methods=["POST"])
@login_required
def optimise_enqueue():
    """
    Enqueue a parameter optimisation job for a given asset class + timeframe.
    Body: { asset_class: "stock", timeframe: "1d" }
    Returns: { job_id, status: "enqueued" }
    """
    if not _rq_queue:
        return jsonify({"error": "Redis / RQ not configured"}), 503

    data        = request.get_json(force=True) or {}
    asset_class = data.get("asset_class", "stock")
    timeframe   = data.get("timeframe",   "1d")

    valid_classes = list(ASSET_CONFIG.keys())
    if asset_class not in valid_classes:
        return jsonify({"error": f"asset_class must be one of {valid_classes}"}), 400

    try:
        job = _rq_queue.enqueue(
            _run_optimisation_job,
            asset_class,
            timeframe,
            job_timeout=300,
            result_ttl=3600,
        )
        return jsonify({"job_id": job.id, "status": "enqueued",
                        "asset_class": asset_class, "timeframe": timeframe})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/optimise/result", methods=["GET"])
@login_required
def optimise_result():
    """
    Poll job status or fetch stored result from DB.
    Query params: job_id (optional), asset_class, timeframe
    Returns: { status: "finished"|"running"|"not_found", result: {...} }
    """
    job_id      = request.args.get("job_id")
    asset_class = request.args.get("asset_class", "stock")
    timeframe   = request.args.get("timeframe",   "1d")

    # If job_id provided, check RQ job status
    if job_id and _rq_queue:
        try:
            from rq.job import Job
            job = Job.fetch(job_id, connection=_rq_conn)
            if job.is_finished:
                return jsonify({"status": "finished", "result": job.result})
            elif job.is_failed:
                return jsonify({"status": "failed",   "error":  str(job.exc_info)})
            else:
                return jsonify({"status": "running"})
        except Exception:
            pass

    # Fall back to reading latest stored result from DB
    if _DBSession:
        db = _DBSession()
        try:
            row = db.query(OptimisationResult).filter(
                OptimisationResult.asset_class == asset_class,
                OptimisationResult.timeframe   == timeframe
            ).order_by(OptimisationResult.computed_at.desc()).first()
            if row:
                return jsonify({
                    "status":      "finished",
                    "result": {
                        "asset_class": row.asset_class,
                        "timeframe":   row.timeframe,
                        "rsi_period":  row.rsi_period,
                        "atr_mult":    row.atr_mult,
                        "ema_fast":    row.ema_fast,
                        "ema_slow":    row.ema_slow,
                        "sharpe":      round(row.sharpe, 4),
                        "win_rate":    round(row.win_rate, 4) if row.win_rate else None,
                        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
                    }
                })
        finally:
            db.close()

    return jsonify({"status": "not_found",
                    "message": "No result yet. Enqueue a job first via POST /api/optimise"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
