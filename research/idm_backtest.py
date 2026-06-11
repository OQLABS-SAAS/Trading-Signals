"""IDM/Inducement Backtest — D2 Inducement Detection edge study.

Evaluates whether waiting for an unswept inducement (IDM) to be swept
before entering a trade improves fill quality and reduces stop-outs.

Decision gate (written to output JSON):
    B beats A  ⟺  avg_R_B > avg_R_A  AND  max_dd_R_B >= max_dd_R_A
Both conditions must hold; a negative result is valid and reported plainly.

Strategy A (control):  enter at signal close.
Strategy B (IDM-wait): if an unswept IDM sits between price and the target
    OB zone at signal time, delay entry until the IDM is swept.
    - IDM swept = price trades through the IDM level (lo < idm_price for a
      bullish IDM low, hi > idm_price for a bearish IDM high) within
      IDM_WAIT_BARS bars after the signal.
    - Entry: the bar AFTER the sweep bar (open of next bar, simulated as
      close of sweep bar ± 0.05×ATR — conservative approximation).
    - If IDM is NOT swept within IDM_WAIT_BARS, fall back to signal-close
      entry (USE_FALLBACK=True) or skip the trade (USE_FALLBACK=False).
    - Same SL/TP as Strategy A, recalculated from the actual fill price
      so the risk-unit stays consistent.

Coverage metric: % of signals where an unswept IDM was present.

Methodology & honest caveats
-----------------------------
Data:   chunk1.csv … chunk5.csv — pre-computed signal rows from the
        1,087-trade baseline.  These do NOT contain the full OHLCV series.

Forward simulation: synthetic paths are generated from each signal's
    entry/sl/tp geometry (same approach as ob_retest_backtest.py).
    The synthetic path is built to be geometrically consistent with the
    baseline rA outcome (hit TP or SL).

CRITICAL CAVEAT: because forward paths are synthetic, all numeric results
(avg R, win rate, drawdown) are MODEL OUTPUTS, NOT live-data estimates.
They reflect the internal consistency of our geometric assumptions, not
real market outcomes.  Treat them as:
  - DIRECTIONAL ONLY: does the IDM-wait strategy tend to enter closer to
    the OB zone, and does that reduce stop-outs on the synthetic paths?
  - NOT as absolute win rates or profit factors.
The verdict should drive code architecture decisions (implement / skip /
re-examine on real data), not position sizing.

Run:
    python3 research/idm_backtest.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smc_structure import detect_order_blocks, detect_inducement

# ── Config ────────────────────────────────────────────────────────────────────
SL_ATR          = 1.5
TP_ATR          = 2.5
MAX_HOLD_BARS   = 120       # stale-trade expiry
IDM_WAIT_BARS   = 30        # bars B waits for IDM sweep before giving up
USE_FALLBACK    = True      # fallback to signal-close entry if IDM not swept
OB_LOOKBACK     = 30        # synthetic bars fed to detectors at each signal


# ── Helpers ───────────────────────────────────────────────────────────────────

def atr_from_signal(row):
    """Recover ATR from sl distance (sl = entry ± 1.5×ATR)."""
    return abs(float(row["entry"]) - float(row["sl"])) / SL_ATR


def build_synthetic_ctx_df(direction, entry, atr_val):
    """
    Minimal 32-bar OHLCV context DF that produces a detectable OB and
    an IDM minor swing between the OB zone and entry level.

    Structure (bars 0-31):
      0-19:  quiet bars at entry ± 0.2×ATR (ATR-setting region)
      20:    opposite-colour OB candle (zone ≈ entry ± 0.4 ATR)
      21:    displacement candle in signal direction (body = 3×ATR)
      22-24: quiet bars above/below displacement close
      25:    minor swing point that creates an IDM between OB and current price
             (a low for bullish, high for bearish, at ≈ entry ± 1.0×ATR)
      26-30: bars after the IDM formation so it qualifies as a fractal
             (lookback-2 fractal: bars 23-24 and 27-28 must be on the same side)
    """
    np.random.seed(int(abs(entry * 1000)) % 2**31)
    a = atr_val
    bars = []

    # Quiet context (build ATR)
    price = entry
    for _ in range(20):
        o = price + np.random.uniform(-0.15 * a, 0.15 * a)
        c = price + np.random.uniform(-0.15 * a, 0.15 * a)
        h = max(o, c) + np.random.uniform(0, 0.08 * a)
        l = min(o, c) - np.random.uniform(0, 0.08 * a)
        bars.append((o, h, l, c))

    # OB candle (opposite colour to direction)
    if direction == "BUY":
        ob_o, ob_c = price + 0.3 * a, price - 0.3 * a   # bearish
    else:
        ob_o, ob_c = price - 0.3 * a, price + 0.3 * a   # bullish
    ob_h = max(ob_o, ob_c) + 0.1 * a
    ob_l = min(ob_o, ob_c) - 0.1 * a
    bars.append((ob_o, ob_h, ob_l, ob_c))

    # Displacement candle
    if direction == "BUY":
        d_o, d_c = price - 0.1 * a, price + 3.0 * a
    else:
        d_o, d_c = price + 0.1 * a, price - 3.0 * a
    d_h = max(d_o, d_c) + 0.1 * a
    d_l = min(d_o, d_c) - 0.1 * a
    bars.append((d_o, d_h, d_l, d_c))
    post_disp = d_c

    # Bars 22-24: quiet after displacement, well away from IDM level
    for _ in range(3):
        o = post_disp + np.random.uniform(-0.15 * a, 0.15 * a)
        c = post_disp + np.random.uniform(-0.15 * a, 0.15 * a)
        h = max(o, c) + 0.08 * a
        l = min(o, c) - 0.08 * a
        bars.append((o, h, l, c))

    # Bar 25: minor swing point (IDM)
    # For BUY: a swing LOW at post_disp - 1.5*a (above OB zone, below post_disp)
    # For SELL: a swing HIGH at post_disp + 1.5*a (below OB zone, above post_disp)
    if direction == "BUY":
        idm_lo = post_disp - 1.5 * a
        # Neighbouring bars (24 and 26) must have lo > idm_lo for fractal
        # We already ensured bar 24 has lo ≈ post_disp - 0.23a (> idm_lo)
        idm_bar_o = idm_lo + 0.6 * a
        idm_bar_c = idm_lo + 0.4 * a
        idm_bar_h = idm_lo + 0.8 * a
        idm_bar_l = idm_lo
    else:
        idm_hi = post_disp + 1.5 * a
        idm_bar_o = idm_hi - 0.6 * a
        idm_bar_c = idm_hi - 0.4 * a
        idm_bar_h = idm_hi
        idm_bar_l = idm_hi - 0.8 * a
    bars.append((idm_bar_o, idm_bar_h, idm_bar_l, idm_bar_c))

    # Bars 26-30: back to post_disp level (so IDM bar is local extreme)
    for _ in range(5):
        o = post_disp + np.random.uniform(-0.15 * a, 0.15 * a)
        c = post_disp + np.random.uniform(-0.15 * a, 0.15 * a)
        h = max(o, c) + 0.08 * a
        l = min(o, c) - 0.08 * a
        bars.append((o, h, l, c))

    # Bar 31: live bar (will be stripped by detector)
    bars.append((post_disp, post_disp + 0.1 * a, post_disp - 0.1 * a, post_disp))

    return pd.DataFrame(bars, columns=["open", "high", "low", "close"])


def build_forward_df(direction, entry, sl, tp, atr_val,
                     rA_baseline, n_bars=MAX_HOLD_BARS + 20):
    """
    Synthetic forward path consistent with the baseline rA outcome.
    Identical approach to ob_retest_backtest.py: walk toward TP or SL
    with small noise, clamp when the target is hit.
    """
    np.random.seed(int(abs(entry * 1000 + sl * 7)) % 2**31)
    hit_tp = rA_baseline > 0
    target = tp if hit_tp else sl
    bars = [(entry, entry + 0.1 * atr_val, entry - 0.1 * atr_val, entry)]
    for k in range(1, n_bars):
        prev = bars[-1][3]
        drift = (target - prev) / max(n_bars - k, 1)
        noise = np.random.uniform(-0.2 * atr_val, 0.2 * atr_val)
        c = prev + drift + noise
        h = c + np.random.uniform(0, 0.15 * atr_val)
        l = c - np.random.uniform(0, 0.15 * atr_val)
        if hit_tp and h >= tp:
            h = tp + 0.01 * atr_val
            bars.append((prev, h, l, c))
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


def simulate_single(fwd_df, direction, entry, sl, tp):
    """Walk forward from bar 0. Market entry. Returns (R, bars_held, resolved)."""
    hi = fwd_df.high.values
    lo = fwd_df.low.values
    cl = fwd_df.close.values
    n  = len(fwd_df)
    ru = abs(entry - sl)
    if ru == 0:
        return 0.0, 0, False
    for j in range(1, min(1 + MAX_HOLD_BARS, n)):
        hit_sl = lo[j] <= sl if direction == "BUY" else hi[j] >= sl
        hit_tp = hi[j] >= tp if direction == "BUY" else lo[j] <= tp
        if hit_sl:
            return -(abs(entry - sl) / ru), j, True
        if hit_tp:
            return  (abs(tp - entry) / ru), j, True
    last = cl[min(MAX_HOLD_BARS, n - 1)]
    sgn = 1 if direction == "BUY" else -1
    return sgn * (last - entry) / ru, MAX_HOLD_BARS, False


def simulate_idm_wait(fwd_df, direction, entry_fallback, sl, tp, atr_val,
                      idm_price, idm_side):
    """
    B strategy: wait up to IDM_WAIT_BARS for the IDM to be swept,
    then enter at the bar after the sweep.

    IDM sweep:
      - side='low' (bullish IDM): sweep when lo[j] < idm_price
      - side='high' (bearish IDM): sweep when hi[j] > idm_price

    Entry after sweep: open of next bar, approximated as close of sweep bar.
    SL/TP are recalculated from the sweep-entry price to keep risk geometry
    consistent (same ATR multiples).

    Returns (R, swept_and_entered, bars_held, resolved).
    """
    hi = fwd_df.high.values
    lo = fwd_df.low.values
    cl = fwd_df.close.values
    n  = len(fwd_df)

    sweep_bar = None
    for j in range(1, min(1 + IDM_WAIT_BARS, n)):
        if idm_side == "low" and lo[j] < idm_price:
            sweep_bar = j
            break
        if idm_side == "high" and hi[j] > idm_price:
            sweep_bar = j
            break

    if sweep_bar is None:
        # IDM not swept within wait window
        if not USE_FALLBACK:
            return None, None, IDM_WAIT_BARS, False
        r, bh, res = simulate_single(fwd_df, direction, entry_fallback, sl, tp)
        return r, False, bh, res

    # Entered at close of sweep bar (post-sweep bar open approximation)
    sweep_entry = float(cl[sweep_bar])
    # Recalculate SL/TP from sweep_entry with same ATR multiples
    if direction == "BUY":
        new_sl = sweep_entry - SL_ATR * atr_val
        new_tp = sweep_entry + TP_ATR * atr_val
    else:
        new_sl = sweep_entry + SL_ATR * atr_val
        new_tp = sweep_entry - TP_ATR * atr_val

    ru = abs(sweep_entry - new_sl)
    if ru == 0:
        return 0.0, True, sweep_bar, False

    for j in range(sweep_bar + 1, min(sweep_bar + 1 + MAX_HOLD_BARS, n)):
        hit_sl = lo[j] <= new_sl if direction == "BUY" else hi[j] >= new_sl
        hit_tp = hi[j] >= new_tp if direction == "BUY" else lo[j] <= new_tp
        if hit_sl:
            return -(abs(sweep_entry - new_sl) / ru), True, j, True
        if hit_tp:
            return  (abs(new_tp - sweep_entry) / ru), True, j, True
    last = cl[min(sweep_bar + MAX_HOLD_BARS, n - 1)]
    sgn = 1 if direction == "BUY" else -1
    r = sgn * (last - sweep_entry) / ru
    return r, True, MAX_HOLD_BARS, False


# ── Chunk loader ──────────────────────────────────────────────────────────────

def load_chunks():
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


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print("Loading chunk data …")
    df_signals = load_chunks()

    cols = set(df_signals.columns)
    print(f"  Chunk columns: {sorted(cols)}")
    print(f"  Total signal rows: {len(df_signals)}")

    # Normalise rA column
    rename = {c: "rA_baseline" for c in df_signals.columns if c.lower() == "ra"}
    if rename:
        df_signals = df_signals.rename(columns=rename)

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

        rA_baseline = float(row.get("rA_baseline", row.get("ra", 0)))
        sym = str(row.get("sym", "?"))
        tf  = str(row.get("tf",  "?"))

        # Build context DF and detect IDMs
        ctx_df = build_synthetic_ctx_df(direction, entry, atr_val)
        obs    = detect_order_blocks(ctx_df)
        idms   = detect_inducement(ctx_df, order_blocks=obs)

        # Find unswept IDMs between price and the target OB zone
        # (for IDM-wait logic we care about IDMs that are not yet swept)
        dir_key   = "bullish" if direction == "BUY" else "bearish"
        fresh_idm = [x for x in idms
                     if x["ob_direction"] == dir_key and not x["swept"]]

        has_idm  = len(fresh_idm) > 0
        idm_price = None
        idm_side  = None
        if has_idm:
            # Nearest unswept IDM to the current price
            nearest = min(fresh_idm,
                          key=lambda x: abs(x["idm_price"] - entry))
            idm_price = nearest["idm_price"]
            idm_side  = nearest["side"]

        # Build forward path
        fwd_df = build_forward_df(direction, entry, sl, tp, atr_val, rA_baseline)

        # Strategy A — signal-close entry
        rA, bh_a, res_a = simulate_single(fwd_df, direction, entry, sl, tp)

        # Strategy B — wait for IDM sweep, then enter
        if has_idm:
            rB_raw, swept_entered, bh_b, res_b = simulate_idm_wait(
                fwd_df, direction, entry, sl, tp, atr_val, idm_price, idm_side)
        else:
            # No IDM: B is same as A
            rB_raw, swept_entered, bh_b, res_b = rA, False, bh_a, res_a

        if rB_raw is None:
            rB_raw = 0.0
            swept_entered = None

        rows.append(dict(
            sym=sym, tf=tf, dir=direction,
            entry=entry, sl=sl, tp=tp,
            rA=rA, rB=rB_raw,
            has_idm=has_idm,
            swept_entered=swept_entered,
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

    # ── Stats ──────────────────────────────────────────────────────────────────
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

    idm_coverage = round(100 * out["has_idm"].mean(), 1)
    idm_swept_rate = round(100 * out["swept_entered"].eq(True).mean(), 1)

    per_tf  = {tf:  {"A_avg_R": round(float(g.rA.mean()), 5),
                     "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for tf, g in out.groupby("tf")}
    per_dir = {d:   {"A_avg_R": round(float(g.rA.mean()), 5),
                     "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for d, g in out.groupby("dir")}
    per_sym = {sym: {"A_avg_R": round(float(g.rA.mean()), 5),
                     "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for sym, g in out.groupby("sym")}

    # Subset where B actually used a swept-IDM entry
    idm_entered = out[out["swept_entered"] == True]
    if len(idm_entered) > 0:
        idm_subset_stats = {
            "n": len(idm_entered),
            "A_avg_R": round(float(idm_entered.rA.mean()), 5),
            "B_avg_R": round(float(idm_entered.rB.mean()), 5),
        }
    else:
        idm_subset_stats = {"n": 0, "A_avg_R": None, "B_avg_R": None}

    # Subset where IDM was present
    idm_present = out[out["has_idm"]]
    if len(idm_present) > 0:
        idm_present_stats = {
            "n": len(idm_present),
            "A_avg_R": round(float(idm_present.rA.mean()), 5),
            "B_avg_R": round(float(idm_present.rB.mean()), 5),
        }
    else:
        idm_present_stats = {"n": 0, "A_avg_R": None, "B_avg_R": None}

    # ── Gate ──────────────────────────────────────────────────────────────────
    b_beats_avgR  = st_B["avg_R"]    > st_A["avg_R"]
    b_ok_drawdown = st_B["max_dd_R"] >= st_A["max_dd_R"]
    gate_pass     = b_beats_avgR and b_ok_drawdown

    verdict = (
        "GATE PASS — B (IDM-wait) beats A on avg R AND does not worsen drawdown. "
        "However, results are SYNTHETIC-DATA ONLY: do not trade on this number."
        if gate_pass else
        "GATE FAIL — "
        + ("B has lower avg R than A. " if not b_beats_avgR else "")
        + ("B worsens max drawdown vs A. " if not b_ok_drawdown else "")
        + "IDM-wait does not provide a reliable edge on synthetic paths. "
        "This is expected: synthetic paths are built from the baseline outcome "
        "and do not model the real micro-structure around the IDM sweep."
    )

    # Honest synthetic-data caveat
    caveat = (
        "SYNTHETIC DATA WARNING: forward paths are Monte Carlo simulations "
        "derived from each signal's entry/sl/tp geometry and baseline rA outcome. "
        "They do NOT represent real OHLCV data. All R/win-rate/drawdown figures "
        "are model artifacts. The only valid use of this backtest is to verify "
        "that the IDM detector emits signals in the expected % of cases and that "
        "the IDM-wait entry logic is implemented correctly. "
        "Re-run on real tick or 1-min OHLCV data before drawing any trading conclusions."
    )

    result = {
        "A_signal_entry":           st_A,
        "B_idm_wait_entry":         st_B,
        "idm_coverage_pct":         idm_coverage,
        "idm_sweep_entry_rate_pct": idm_swept_rate,
        "use_fallback":             USE_FALLBACK,
        "idm_wait_bars":            IDM_WAIT_BARS,
        "signals_processed":        len(out),
        "idm_entered_subset":       idm_subset_stats,
        "idm_present_subset":       idm_present_stats,
        "per_tf":                   per_tf,
        "per_dir":                  per_dir,
        "per_sym":                  per_sym,
        "gate": {
            "b_beats_avg_R":   b_beats_avgR,
            "b_ok_drawdown":   b_ok_drawdown,
            "gate_pass":       gate_pass,
            "verdict":         verdict,
        },
        "caveat": caveat,
    }

    # ── Print table ────────────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("  IDM-WAIT BACKTEST VERDICT")
    print("=" * 72)
    fmt = "  {:<32} {:>12} {:>12}"
    print(fmt.format("Metric", "A (signal)", "B (IDM-wait)"))
    print("  " + "-" * 68)
    print(fmt.format("Trades",        st_A["trades"],          st_B["trades"]))
    print(fmt.format("Win rate %",    st_A["win_rate"],         st_B["win_rate"]))
    print(fmt.format("Avg R",         st_A["avg_R"],            st_B["avg_R"]))
    print(fmt.format("Total R",       st_A["total_R"],          st_B["total_R"]))
    print(fmt.format("Max DD (R)",    st_A["max_dd_R"],          st_B["max_dd_R"]))
    print(fmt.format("Profit factor", st_A["profit_factor"],    st_B["profit_factor"]))
    print()
    print(f"  IDM coverage (% signals with unswept IDM): {idm_coverage}%")
    print(f"  IDM sweep entry rate (% trades B used IDM): {idm_swept_rate}%")
    print()
    if len(idm_entered) > 0:
        print(f"  IDM-entered subset ({idm_subset_stats['n']} trades):")
        print(f"    A avg R = {idm_subset_stats['A_avg_R']}  |  B avg R = {idm_subset_stats['B_avg_R']}")
    print()
    print(f"  GATE: {verdict}")
    print()
    print(f"  CAVEAT: {caveat}")
    print("=" * 72)
    print()

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = Path(__file__).parent / "idm_summary.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Summary written to {out_path}")

    trades_path = Path(__file__).parent / "idm_trades.csv"
    out.to_csv(trades_path, index=False)
    print(f"Trades written to  {trades_path}")

    return result


if __name__ == "__main__":
    run()
