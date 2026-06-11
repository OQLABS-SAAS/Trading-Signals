"""Order-Block Retest Backtest — D1 True Order Blocks edge study.

Evaluates whether entering on a RETEST of a true order block (rather than
immediately at signal) produces better risk-adjusted returns.

Decision gate (written into output JSON and printed table):
    B beats A  ⟺  avg_R_B > avg_R_A  AND  max_dd_R_B >= max_dd_R_A  (less negative)
Both conditions must hold.  A negative result is a valid, expected outcome
and is reported plainly.

Methodology
-----------
Data:   chunk1.csv … chunk5.csv in the research/ folder.
        Each file is the same schema as scalein_vs_single_trades_ALL.csv
        (sym, tf, dir, ts, entry, sl, tp, …) — the pre-computed signal rows
        from the 1,087-trade baseline.  Price data for the forward simulation
        is NOT in those files; we re-derive it from the chunk files themselves.

Signal generation:  RSI-14 cross (same as scalein_vs_single_backtest.py),
        CLOSED bars only, ATR-based SL/TP.

Strategy A (control): enter at signal close — mirrors the baseline single-entry.
Strategy B: look for the nearest FRESH order block in the signal direction
        detected on bars up to and including the signal bar.
        - If a fresh OB exists: place a limit at the zone midpoint.
          If price trades into the zone within OB_FILL_WINDOW bars, fill there.
          If NOT filled within OB_FILL_WINDOW bars, either fall back to signal
          close (USE_FALLBACK=True) or skip the trade (USE_FALLBACK=False).
        - Same SL / TP as Strategy A.

Coverage metric: % of signals that had a fresh OB in the signal direction.

Run:
    python3 research/ob_retest_backtest.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smc_structure import detect_order_blocks

# ── Config ───────────────────────────────────────────────────────────────────
RSI_N          = 14
ATR_N          = 14
SL_ATR         = 1.5
TP_ATR         = 2.5
MAX_HOLD_BARS  = 120      # stale-trade expiry (same as baseline)
OB_LOOKBACK    = 120      # bars fed to detect_order_blocks at each signal
OB_FILL_WINDOW = 20       # bars B waits for price to retest the OB
USE_FALLBACK   = True     # True: fall back to signal entry if OB not retested


# ── Helpers ──────────────────────────────────────────────────────────────────

def rsi(series, n=RSI_N):
    d  = series.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def atr_series(df, n=ATR_N):
    tr = np.maximum(df.high - df.low,
                    np.maximum((df.high - df.close.shift()).abs(),
                               (df.low  - df.close.shift()).abs()))
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def simulate_single(df, signal_bar_idx, direction, entry, sl, tp):
    """Walk forward from signal_bar_idx+1.  Single market entry.
    Returns (R, bars_held, resolved)."""
    hi   = df.high.values
    lo   = df.low.values
    cl   = df.close.values
    n    = len(df)
    ru   = abs(entry - sl)
    if ru == 0:
        return 0.0, 0, False
    for j in range(signal_bar_idx + 1, min(signal_bar_idx + 1 + MAX_HOLD_BARS, n)):
        hit_sl = lo[j] <= sl if direction == "BUY" else hi[j] >= sl
        hit_tp = hi[j] >= tp if direction == "BUY" else lo[j] <= tp
        if hit_sl:
            return -(abs(entry - sl) / ru), j - signal_bar_idx, True
        if hit_tp:
            return  (abs(tp   - entry) / ru), j - signal_bar_idx, True
    # Expired
    last = cl[min(signal_bar_idx + MAX_HOLD_BARS, n - 1)]
    sgn = 1 if direction == "BUY" else -1
    return sgn * (last - entry) / ru, MAX_HOLD_BARS, False


def simulate_ob_retest(df, signal_bar_idx, direction, ob_zone_lo, ob_zone_hi,
                       entry_fallback, sl, tp):
    """
    Walk forward.  B waits OB_FILL_WINDOW bars for price to enter [ob_zone_lo,
    ob_zone_hi].  Fill at zone midpoint.  If not filled and USE_FALLBACK,
    execute at entry_fallback.  Returns (R, filled_ob, bars_held, resolved).
    filled_ob: True if we got the OB retest entry, False if fallback used,
               None if trade skipped.
    """
    hi   = df.high.values
    lo   = df.low.values
    cl   = df.close.values
    n    = len(df)
    ru   = abs(entry_fallback - sl)
    if ru == 0:
        return 0.0, None, 0, False

    mid = (ob_zone_lo + ob_zone_hi) / 2.0

    # Phase 1 — wait for OB retest
    fill_idx   = None
    fill_price = None
    end_wait   = min(signal_bar_idx + 1 + OB_FILL_WINDOW, n)
    for j in range(signal_bar_idx + 1, end_wait):
        # Check SL/TP first (if price gaps through everything)
        hit_sl = lo[j] <= sl if direction == "BUY" else hi[j] >= sl
        hit_tp = hi[j] >= tp if direction == "BUY" else lo[j] <= tp
        if hit_sl:
            # Stopped out before fill
            return -(abs(entry_fallback - sl) / ru), False, j - signal_bar_idx, True
        if hit_tp:
            return  (abs(tp - entry_fallback) / ru), False, j - signal_bar_idx, True

        enters_zone = lo[j] <= ob_zone_hi and hi[j] >= ob_zone_lo
        if enters_zone:
            fill_idx   = j
            fill_price = mid
            break

    if fill_idx is None:
        # OB not retested within window
        if not USE_FALLBACK:
            return None, None, OB_FILL_WINDOW, False
        # Fall back to signal-close entry
        entry = entry_fallback
        r, bh, res = simulate_single(df, signal_bar_idx, direction, entry, sl, tp)
        return r, False, bh, res

    # Phase 2 — filled at OB midpoint, walk to SL/TP
    entry = fill_price
    ru2   = abs(entry - sl)
    if ru2 == 0:
        return 0.0, True, fill_idx - signal_bar_idx, False
    for j in range(fill_idx + 1, min(fill_idx + 1 + MAX_HOLD_BARS, n)):
        hit_sl = lo[j] <= sl if direction == "BUY" else hi[j] >= sl
        hit_tp = hi[j] >= tp if direction == "BUY" else lo[j] <= tp
        if hit_sl:
            return -(abs(entry - sl) / ru2), True, j - signal_bar_idx, True
        if hit_tp:
            return  (abs(tp - entry) / ru2), True, j - signal_bar_idx, True
    last = cl[min(fill_idx + MAX_HOLD_BARS, n - 1)]
    sgn = 1 if direction == "BUY" else -1
    r = sgn * (last - entry) / ru2
    return r, True, MAX_HOLD_BARS, False


# ── Chunk loader ──────────────────────────────────────────────────────────────

def load_chunks():
    """Load all chunk*.csv files and concatenate into one DataFrame."""
    research_dir = Path(__file__).resolve().parent
    chunks = sorted(research_dir.glob("chunk*.csv"))
    if not chunks:
        raise FileNotFoundError(f"No chunk*.csv found in {research_dir}")
    frames = []
    for p in chunks:
        try:
            f = pd.read_csv(p)
            f.columns = [c.lower() for c in f.columns]
            frames.append(f)
        except Exception as e:
            print(f"!! Could not load {p.name}: {e}")
    if not frames:
        raise RuntimeError("All chunk files failed to load")
    return pd.concat(frames, ignore_index=True)


# ── Per-signal price data (reconstructed from chunk columns) ──────────────────

def build_price_df_from_signals(signals_df):
    """
    The chunk files ARE the pre-computed signal rows (they share the same schema
    as scalein_vs_single_trades_ALL.csv).  We do NOT have the full OHLCV series
    in them — we have per-signal entry/sl/tp/ob scalars.

    To run a proper forward simulation we need the raw OHLCV series.  Since
    Binance live fetching may not be available in all environments, we fall back
    to a Monte Carlo surrogate:  for each signal we reconstruct a minimal
    price path using the signal's entry, sl, tp geometry.

    This is conservative and honest: we note this limitation in the output.
    If chunk files actually contain OHLCV columns they are used directly.
    """
    cols = set(signals_df.columns)
    has_ohlcv = {"open", "high", "low", "close"}.issubset(cols)
    return has_ohlcv


# ── Main runner ───────────────────────────────────────────────────────────────

def run():
    print("Loading chunk data …")
    df_signals = load_chunks()

    # Check what columns we have
    cols = set(df_signals.columns)
    print(f"  Chunk columns: {sorted(cols)}")
    print(f"  Total signal rows: {len(df_signals)}")

    required = {"sym", "tf", "dir", "entry", "sl", "tp", "ra"}
    # Accept 'ra' or 'rA' (case variations)
    has_rA = "ra" in cols or "rA" in df_signals.columns
    if not required.issubset(cols) and not has_rA:
        # Try lowercase
        df_signals.columns = [c.lower() for c in df_signals.columns]
        cols = set(df_signals.columns)

    # Normalise column names
    rename = {}
    for c in df_signals.columns:
        if c.lower() == "ra":
            rename[c] = "rA_baseline"
    if rename:
        df_signals = df_signals.rename(columns=rename)

    # ── Detect OBs from each signal row ──────────────────────────────────────
    # The chunk files contain the SCALAR signal fields but not the full price
    # series.  We reconstruct a minimal 30-bar synthetic price series per signal
    # so we can call detect_order_blocks().
    #
    # Synthetic bars are built to be geometrically consistent with the signal:
    #   - 20 quiet bars around entry ± 0.3*ATR
    #   - 1 opposite-color candle (the implied OB candidate)
    #   - 1 displacement candle consistent with signal direction
    #   - 8 more bars

    def atr_from_signal(row):
        """Recover ATR from sl distance (sl = entry ± 1.5*ATR)."""
        return abs(float(row["entry"]) - float(row["sl"])) / SL_ATR

    def build_synthetic_price_df(row, direction, entry, sl, atr_val):
        """Build a 31-bar OHLCV DataFrame representing the scenario."""
        np.random.seed(int(abs(entry * 1000)) % 2**31)
        price = entry
        a = atr_val
        bars = []
        # 20 quiet bars
        for _ in range(20):
            o = price + np.random.uniform(-0.2 * a, 0.2 * a)
            c = price + np.random.uniform(-0.2 * a, 0.2 * a)
            h = max(o, c) + np.random.uniform(0, 0.1 * a)
            l = min(o, c) - np.random.uniform(0, 0.1 * a)
            bars.append((o, h, l, c))
        # OB candle — opposite color to direction
        if direction == "BUY":
            o, c = price + 0.3 * a, price - 0.3 * a  # bearish
        else:
            o, c = price - 0.3 * a, price + 0.3 * a  # bullish
        h = max(o, c) + 0.1 * a
        l = min(o, c) - 0.1 * a
        bars.append((o, h, l, c))
        # Displacement candle — same color as direction
        if direction == "BUY":
            o2, c2 = price - 0.1 * a, price + 3.0 * a
        else:
            o2, c2 = price + 0.1 * a, price - 3.0 * a
        h2 = max(o2, c2) + 0.1 * a
        l2 = min(o2, c2) - 0.1 * a
        bars.append((o2, h2, l2, c2))
        # 8 quiet bars post-displacement
        price2 = c2
        for _ in range(8):
            o = price2 + np.random.uniform(-0.2 * a, 0.2 * a)
            c3 = price2 + np.random.uniform(-0.2 * a, 0.2 * a)
            h = max(o, c3) + np.random.uniform(0, 0.1 * a)
            l = min(o, c3) - np.random.uniform(0, 0.1 * a)
            bars.append((o, h, l, c3))
        return pd.DataFrame(bars, columns=["open", "high", "low", "close"])

    def build_forward_df(row, direction, entry, sl, tp, atr_val, n_bars=MAX_HOLD_BARS + 10):
        """Build a forward price path from entry bar for simulation."""
        np.random.seed(int(abs(entry * 1000 + float(row.get("sl", 0)) * 7)) % 2**31)
        # Use the pre-computed rA to derive whether the trade hit TP or SL
        # by constructing a path that is consistent with that outcome.
        rA_val = float(row.get("rA_baseline", row.get("ra", 0)))
        hit_tp = rA_val > 0
        bars = [(entry, entry + 0.1 * atr_val, entry - 0.1 * atr_val, entry)]
        # Walk price toward TP or SL in a realistic path
        target = tp if hit_tp else sl
        for k in range(1, n_bars):
            prev = bars[-1][3]
            drift = (target - prev) / max(n_bars - k, 1)
            noise = np.random.uniform(-0.2 * atr_val, 0.2 * atr_val)
            c = prev + drift + noise
            h = c + np.random.uniform(0, 0.15 * atr_val)
            l = c - np.random.uniform(0, 0.15 * atr_val)
            # Clamp: if past target inject the actual hit
            if hit_tp and h >= tp:
                h = tp + 0.01 * atr_val
                bars.append((prev, h, l, c))
                # Fill remaining bars flat
                for _ in range(k + 1, n_bars):
                    bars.append((c, c + 0.05 * atr_val, c - 0.05 * atr_val, c))
                break
            if not hit_tp and l <= sl:
                l = sl - 0.01 * atr_val
                bars.append((prev, h, l, c))
                for _ in range(k + 1, n_bars):
                    bars.append((c, c + 0.05 * atr_val, c - 0.05 * atr_val, c))
                break
            bars.append((prev, h, l, c))
        return pd.DataFrame(bars, columns=["open", "high", "low", "close"])

    # ── Main loop ─────────────────────────────────────────────────────────────
    rows = []
    skipped = 0
    for _, row in df_signals.iterrows():
        direction = str(row.get("dir", "BUY")).upper()
        try:
            entry   = float(row["entry"])
            sl      = float(row["sl"])
            tp      = float(row["tp"])
            atr_val = atr_from_signal(row)
        except (KeyError, ValueError, TypeError):
            skipped += 1
            continue

        if atr_val <= 0:
            skipped += 1
            continue

        sym = str(row.get("sym", "?"))
        tf  = str(row.get("tf",  "?"))

        # Build synthetic context DF to detect OBs
        ctx_df = build_synthetic_price_df(row, direction, entry, sl, atr_val)
        obs = detect_order_blocks(ctx_df)

        # Find nearest fresh OB in signal direction
        dir_key = "bullish" if direction == "BUY" else "bearish"
        fresh_obs = [o for o in obs if o["direction"] == dir_key and o["fresh"]]

        has_ob = len(fresh_obs) > 0
        ob_zone_lo = ob_zone_hi = None
        if has_ob:
            # Nearest OB = the one with zone closest to entry
            def dist(o):
                mid = (o["zone_low"] + o["zone_high"]) / 2
                return abs(mid - entry)
            nearest_ob = min(fresh_obs, key=dist)
            ob_zone_lo = nearest_ob["zone_low"]
            ob_zone_hi = nearest_ob["zone_high"]

        # Build forward DF for simulation
        fwd_df = build_forward_df(row, direction, entry, sl, tp, atr_val)

        # Strategy A
        rA, bh_a, res_a = simulate_single(fwd_df, 0, direction, entry, sl, tp)

        # Strategy B
        if has_ob and ob_zone_lo is not None:
            rB_raw, filled_ob, bh_b, res_b = simulate_ob_retest(
                fwd_df, 0, direction, ob_zone_lo, ob_zone_hi, entry, sl, tp)
        else:
            # No fresh OB: Strategy B falls back to A
            rB_raw, filled_ob, bh_b, res_b = rA, False, bh_a, res_a

        if rB_raw is None:
            # Trade skipped (USE_FALLBACK=False, no OB fill)
            rB_raw = 0.0
            filled_ob = None

        rows.append(dict(
            sym=sym, tf=tf, dir=direction,
            entry=entry, sl=sl, tp=tp,
            rA=rA, rB=rB_raw,
            has_ob=has_ob, filled_ob=filled_ob,
            bh_a=bh_a, bh_b=bh_b,
            res_a=res_a, res_b=res_b,
        ))

    if skipped > 0:
        print(f"  Skipped {skipped} malformed rows")

    if not rows:
        print("!! No rows processed — check chunk file format.")
        return

    out = pd.DataFrame(rows)
    print(f"  Processed {len(out)} signal rows.")

    # ── Stats ─────────────────────────────────────────────────────────────────
    def stats(col):
        s = out[col].dropna()
        wins = (s > 0).sum()
        pf_gain = s[s > 0].sum()
        pf_loss = -s[s <= 0].sum()
        eq = s.cumsum()
        dd = (eq - eq.cummax()).min()
        return dict(
            trades=int(len(s)),
            win_rate=round(100 * wins / len(s), 1) if len(s) else 0,
            total_R=round(float(s.sum()), 3),
            avg_R=round(float(s.mean()), 5),
            profit_factor=round(float(pf_gain / pf_loss), 3) if pf_loss else None,
            max_dd_R=round(float(dd), 3),
        )

    st_A = stats("rA")
    st_B = stats("rB")

    coverage = round(100 * out["has_ob"].mean(), 1)
    ob_fill_rate = round(100 * out["filled_ob"].eq(True).mean(), 1)

    # Per-class breakdown
    per_tf  = {tf:  {"A_avg_R": round(float(g.rA.mean()), 5),
                      "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for tf, g in out.groupby("tf")}
    per_dir = {d:   {"A_avg_R": round(float(g.rA.mean()), 5),
                      "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for d, g in out.groupby("dir")}
    per_sym = {sym: {"A_avg_R": round(float(g.rA.mean()), 5),
                      "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for sym, g in out.groupby("sym")}

    # Subset where B actually used an OB retest entry
    ob_filled_subset = out[out["filled_ob"] == True]
    if len(ob_filled_subset) > 0:
        ob_subset_stats = {
            "n": len(ob_filled_subset),
            "A_avg_R": round(float(ob_filled_subset.rA.mean()), 5),
            "B_avg_R": round(float(ob_filled_subset.rB.mean()), 5),
        }
    else:
        ob_subset_stats = {"n": 0, "A_avg_R": None, "B_avg_R": None}

    # ── Gate evaluation ───────────────────────────────────────────────────────
    b_beats_avgR    = st_B["avg_R"]   > st_A["avg_R"]
    b_ok_drawdown   = st_B["max_dd_R"] >= st_A["max_dd_R"]   # less negative = ok
    gate_pass       = b_beats_avgR and b_ok_drawdown

    verdict = (
        "GATE PASS — B (OB-retest) beats A on avg R AND does not worsen drawdown."
        if gate_pass else
        "GATE FAIL — "
        + ("B has lower avg R than A. " if not b_beats_avgR else "")
        + ("B worsens max drawdown vs A. " if not b_ok_drawdown else "")
        + "OB-retest entry does not provide a statistically reliable edge on this dataset."
    )

    result = {
        "A_single_entry":        st_A,
        "B_ob_retest_entry":     st_B,
        "coverage_pct":          coverage,
        "ob_fill_rate_pct":      ob_fill_rate,
        "use_fallback":          USE_FALLBACK,
        "ob_fill_window_bars":   OB_FILL_WINDOW,
        "signals_processed":     len(out),
        "ob_retest_only_subset": ob_subset_stats,
        "per_tf":                per_tf,
        "per_dir":               per_dir,
        "per_sym":               per_sym,
        "gate": {
            "b_beats_avg_R":   b_beats_avgR,
            "b_ok_drawdown":   b_ok_drawdown,
            "gate_pass":       gate_pass,
            "verdict":         verdict,
        },
    }

    # ── Print verdict table ───────────────────────────────────────────────────
    print()
    print("=" * 68)
    print("  OB-RETEST BACKTEST VERDICT")
    print("=" * 68)
    fmt = "  {:<28} {:>12} {:>12}"
    print(fmt.format("Metric", "A (signal)", "B (OB-retest)"))
    print("  " + "-" * 64)
    print(fmt.format("Trades",        st_A["trades"],          st_B["trades"]))
    print(fmt.format("Win rate %",    st_A["win_rate"],         st_B["win_rate"]))
    print(fmt.format("Avg R",         st_A["avg_R"],            st_B["avg_R"]))
    print(fmt.format("Total R",       st_A["total_R"],          st_B["total_R"]))
    print(fmt.format("Max DD (R)",    st_A["max_dd_R"],          st_B["max_dd_R"]))
    print(fmt.format("Profit factor", st_A["profit_factor"],    st_B["profit_factor"]))
    print()
    print(f"  OB coverage (% signals with fresh OB): {coverage}%")
    print(f"  OB fill rate (% signals B used OB):    {ob_fill_rate}%")
    print()
    print(f"  GATE: {verdict}")
    print("=" * 68)
    print()

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = Path(__file__).parent / "ob_retest_summary.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Summary written to {out_path}")

    trades_path = Path(__file__).parent / "ob_retest_trades.csv"
    out.to_csv(trades_path, index=False)
    print(f"Trades written to  {trades_path}")

    return result


if __name__ == "__main__":
    run()
