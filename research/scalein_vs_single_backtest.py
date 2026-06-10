"""Smart Entry research: SINGLE-ENTRY vs SCALE-IN AT THE ORDER BLOCK.

Decision gate for the Smart Entry Engine (DOTVERSE_SMART_ENTRY_ENGINE_BUILD_PLAN.md):
build scale-in ONLY if this study shows a real edge. Pure research — no live
orders, no app changes.

Methodology (designed to isolate ENTRY PLACEMENT, holding everything else fixed):
- Data: Binance public klines (no auth), several majors, 1h + 4h, up to 3000 bars.
- Signals: the same mechanical entry family the app's backtester uses (RSI-14
  cross up through 30 = BUY setup, cross down through 70 = SELL setup), on
  CLOSED bars only. ATR-based levels: SL = 1.5*ATR, TP = 2.5*ATR from signal close.
- Order block proxy: the repo's own detect_smc_structures() on data up to the
  signal bar (no look-ahead). For BUY: nearest bullish FVG / bull liquidity-grab
  level BELOW entry (fallback entry - 0.5*ATR). Symmetric for SELL.
- Strategy A (what the app does today): full 1R position at the signal close.
- Strategy B (scale-in): 3 limit legs of 1/3 risk each at [entry, midpoint, OB],
  legs fill only if price actually trades there before the trade resolves.
  Shared SL/TP. Unfilled legs = missed size (the real cost of scale-in).
- Same-bar TP+SL ambiguity counted as LOSS (conservative, both strategies).
- Risk-normalised: every result in R of the trade's total intended risk, so A
  and B are directly comparable.

Run:  python research/scalein_vs_single_backtest.py
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from smc_structure import detect_smc_structures

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT"]
INTERVALS = {"1h": 3000, "4h": 3000}
RSI_N = 14
ATR_N = 14
SL_ATR = 1.5
TP_ATR = 2.5
MAX_HOLD_BARS = 120          # expire stale trades (both strategies)
OB_LOOKBACK = 120            # bars fed to detect_smc_structures at each signal


def fetch_klines(symbol, interval, want):
    """Paginate Binance klines back from now. Returns DataFrame O/H/L/C/V."""
    rows, end = [], None
    while len(rows) < want:
        url = (f"https://api.binance.com/api/v3/klines?symbol={symbol}"
               f"&interval={interval}&limit=1000" + (f"&endTime={end}" if end else ""))
        with urllib.request.urlopen(url, timeout=15) as r:
            batch = json.loads(r.read().decode())
        if not batch:
            break
        rows = batch + rows
        end = batch[0][0] - 1
        if len(batch) < 1000:
            break
        time.sleep(0.15)
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "vol",
                                     "ct", "qv", "n", "tb", "tq", "ig"])
    for c in ("open", "high", "low", "close", "vol"):
        df[c] = df[c].astype(float)
    df.index = pd.to_datetime(df["t"], unit="ms")
    return df[["open", "high", "low", "close", "vol"]].tail(want)


def rsi(series, n=RSI_N):
    d = series.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def atr(df, n=ATR_N):
    tr = np.maximum(df.high - df.low,
                    np.maximum((df.high - df.close.shift()).abs(),
                               (df.low - df.close.shift()).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def order_block_level(df_upto, direction, entry, a):
    """Repo SMC detector on closed bars up to signal. Returns OB price or fallback."""
    s = detect_smc_structures(df_upto.tail(OB_LOOKBACK))
    cands = []
    if direction == "BUY":
        for k in ("fvg_bullish_level", "liquidity_grab_bull_level", "choch_bull_level"):
            v = s.get(k)
            if v and v < entry:
                cands.append(v)
        fallback = entry - 0.5 * a
        lvl = max(cands) if cands else fallback          # nearest below entry
        return max(lvl, entry - 1.2 * a), bool(cands)    # never below ~SL zone
    else:
        for k in ("fvg_bearish_level", "liquidity_grab_bear_level", "choch_bear_level"):
            v = s.get(k)
            if v and v > entry:
                cands.append(v)
        fallback = entry + 0.5 * a
        lvl = min(cands) if cands else fallback
        return min(lvl, entry + 1.2 * a), bool(cands)


def simulate(df, i, direction, entry, sl, tp, legs):
    """Walk forward from bar i+1. legs = [(price, frac), ...] limit orders.
    Returns (R_result, filled_fraction, avg_fill, bars_held, resolved).
    R is measured against TOTAL intended risk (sum frac * |leg - sl| / |entry - sl|
    normalisation keeps A and B comparable: A risks 1.0R by construction)."""
    hi, lo = df.high.values, df.low.values
    n = len(df)
    filled = [False] * len(legs)
    filled[0] = True                       # leg 1 is a market order at signal close
    risk_unit = abs(entry - sl)
    for j in range(i + 1, min(i + 1 + MAX_HOLD_BARS, n)):
        bar_hit_sl = lo[j] <= sl if direction == "BUY" else hi[j] >= sl
        bar_hit_tp = hi[j] >= tp if direction == "BUY" else lo[j] <= tp
        # limit fills happen before exits if price passes through the level
        for k, (px, _) in enumerate(legs):
            if not filled[k]:
                touched = lo[j] <= px if direction == "BUY" else hi[j] >= px
                if touched:
                    filled[k] = True
        if bar_hit_sl:                      # conservative: SL wins same-bar ties
            r = sum(-f * abs(px - sl) / risk_unit
                    for (px, f), ok in zip(legs, filled) if ok)
            return r, _ffrac(legs, filled), _afill(legs, filled), j - i, True
        if bar_hit_tp:
            r = sum(f * abs(tp - px) / risk_unit
                    for (px, f), ok in zip(legs, filled) if ok)
            return r, _ffrac(legs, filled), _afill(legs, filled), j - i, True
    # expired: close at last close
    last = df.close.values[min(i + MAX_HOLD_BARS, n - 1)]
    sgn = 1 if direction == "BUY" else -1
    r = sum(sgn * f * (last - px) / risk_unit
            for (px, f), ok in zip(legs, filled) if ok)
    return r, _ffrac(legs, filled), _afill(legs, filled), MAX_HOLD_BARS, False


def _ffrac(legs, filled):
    return sum(f for (_, f), ok in zip(legs, filled) if ok)


def _afill(legs, filled):
    tot = _ffrac(legs, filled)
    if tot <= 0:
        return None
    return sum(px * f for (px, f), ok in zip(legs, filled) if ok) / tot


def run():
    rows = []
    for sym in SYMBOLS:
        for iv, want in INTERVALS.items():
            try:
                df = fetch_klines(sym, iv, want)
            except Exception as e:
                print(f"!! {sym} {iv}: fetch failed: {e}")
                continue
            if len(df) < 300:
                print(f"!! {sym} {iv}: only {len(df)} bars, skipping")
                continue
            r = rsi(df.close)
            a = atr(df)
            sigs = 0
            for i in range(OB_LOOKBACK, len(df) - 2):
                buy = r.iloc[i - 1] < 30 <= r.iloc[i]
                sell = r.iloc[i - 1] > 70 >= r.iloc[i]
                if not (buy or sell):
                    continue
                direction = "BUY" if buy else "SELL"
                entry = float(df.close.iloc[i])
                av = float(a.iloc[i])
                if av <= 0:
                    continue
                sl = entry - SL_ATR * av if buy else entry + SL_ATR * av
                tp = entry + TP_ATR * av if buy else entry - TP_ATR * av
                ob, ob_real = order_block_level(df.iloc[: i + 1], direction, entry, av)
                mid = (entry + ob) / 2
                # Strategy A: single full entry
                ra, _, _, ha, res_a = simulate(df, i, direction, entry, sl, tp,
                                               [(entry, 1.0)])
                # Strategy B: 3-leg scale-in toward the OB
                rb, fb, ab, hb, res_b = simulate(df, i, direction, entry, sl, tp,
                                                 [(entry, 1 / 3), (mid, 1 / 3), (ob, 1 / 3)])
                rows.append(dict(sym=sym, tf=iv, dir=direction, ts=str(df.index[i]),
                                 entry=entry, sl=sl, tp=tp, ob=ob, ob_real=ob_real,
                                 rA=ra, rB=rb, fillB=fb, avgFillB=ab,
                                 resolvedA=res_a, resolvedB=res_b))
                sigs += 1
            print(f"   {sym} {iv}: {len(df)} bars, {sigs} signals")
    out = pd.DataFrame(rows)
    out.to_csv(Path(__file__).parent / "scalein_vs_single_trades.csv", index=False)

    def stats(col):
        s = out[col]
        wins = (s > 0).sum()
        pf_gain = s[s > 0].sum()
        pf_loss = -s[s <= 0].sum()
        eq = s.cumsum()
        dd = (eq - eq.cummax()).min()
        return dict(trades=len(s), win_rate=round(100 * wins / len(s), 1),
                    total_R=round(s.sum(), 1), avg_R=round(s.mean(), 4),
                    profit_factor=round(pf_gain / pf_loss, 3) if pf_loss else None,
                    max_dd_R=round(dd, 1))

    res = {"A_single_entry": stats("rA"), "B_scale_in_OB": stats("rB"),
           "B_avg_filled_fraction": round(out.fillB.mean(), 3),
           "B_pct_full_fill": round(100 * (out.fillB > 0.99).mean(), 1),
           "OB_from_real_structure_pct": round(100 * out.ob_real.mean(), 1),
           "signals": len(out),
           "per_tf": {tf: {"A_avg_R": round(g.rA.mean(), 4),
                            "B_avg_R": round(g.rB.mean(), 4),
                            "n": len(g)} for tf, g in out.groupby("tf")},
           "per_dir": {d: {"A_avg_R": round(g.rA.mean(), 4),
                            "B_avg_R": round(g.rB.mean(), 4),
                            "n": len(g)} for d, g in out.groupby("dir")}}
    print(json.dumps(res, indent=2))
    (Path(__file__).parent / "scalein_vs_single_summary.json").write_text(
        json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    run()
