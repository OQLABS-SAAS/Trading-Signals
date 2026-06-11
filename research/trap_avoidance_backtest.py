"""Liquidity-Trap Avoidance Backtest — D3 edge study.

Evaluates whether delaying entry when assess_entry_liquidity_risk() flags
at_risk=True and waiting for a sweep-and-reclaim improves outcomes compared
to entering immediately at the signal price.

Decision gate:
    B beats A  ⟺  avg_R_B > avg_R_A  AND  max_dd_R_B >= max_dd_R_A
    PLUS adverse-excursion reduction: avg_mae_B < avg_mae_A (less heat taken).
Both R conditions must hold.  MAE is reported separately as a diagnostic.

Strategy A (control):  enter at signal close regardless of liquidity risk.
Strategy B (trap-wait): if at_risk=True, delay entry.
    - Sweep: price trades THROUGH cluster_price in the stop direction
      (BUY: lo < cluster_price;  SELL: hi > cluster_price) within
      SWEEP_WAIT_BARS bars of the signal.
    - Reclaim: price closes back THROUGH cluster_price in the entry direction
      within RECLAIM_BARS bars after the sweep.
    - Entry: close of the reclaim bar.
    - SL/TP: recalculated from reclaim entry with same ATR multiples.
    - If sweep or reclaim does not occur within their windows:
        USE_FALLBACK=True  → fall back to signal entry (same as A).
        USE_FALLBACK=False → skip the trade (R=0).
    If at_risk=False, B is identical to A for that signal.

Coverage metric: % of signals flagged at_risk=True.

Adverse excursion (MAE):
    Maximum Adverse Excursion = worst (most negative) price move from entry
    before the trade resolves.  We measure it in R-units (same as the trade R).
    avg_mae is the mean of MAE across all resolved trades.
    A lower avg_mae means less heat taken, i.e. entries nearer the true turn.

Methodology & honest caveats
------------------------------
Data:   chunk1.csv … chunk5.csv — pre-computed signal rows from the
        1,087-trade baseline.  These do NOT contain the full OHLCV series.

Forward simulation: synthetic paths built from each signal's entry/sl/tp
    geometry (same conservative approach as ob_retest_backtest.py and
    idm_backtest.py).  The path is geometrically consistent with the baseline
    rA outcome (hit TP or SL) but does NOT model real micro-structure.

CRITICAL CAVEAT: numeric results (avg R, win rate, MAE, drawdown) are MODEL
OUTPUTS derived from synthetic paths, NOT live-data estimates.  The path
builder is seeded from entry/sl parameters so it is deterministic but not
representative of real order flow.  Treat the verdict as:
  - DIRECTIONAL ONLY: does trap-avoidance reduce heat on synthetic paths?
  - NOT as absolute win rates or profit factors.
The gate decision should influence architecture (implement / skip / re-examine),
not position sizing.  Re-run on real tick / 1-min OHLCV data before drawing
trading conclusions.

Run:
    python3 research/trap_avoidance_backtest.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smc_structure import assess_entry_liquidity_risk

# ── Config ────────────────────────────────────────────────────────────────────
SL_ATR          = 1.5
TP_ATR          = 2.5
MAX_HOLD_BARS   = 120
SWEEP_WAIT_BARS = 20    # bars B waits for the sweep of the liquidity cluster
RECLAIM_BARS    = 10    # bars after sweep that B waits for the reclaim close
USE_FALLBACK    = True  # True: fall back to signal entry if sweep/reclaim fails
PROXIMITY_ATR   = 0.5   # passed to assess_entry_liquidity_risk


# ── Helpers ───────────────────────────────────────────────────────────────────

def atr_from_signal(row):
    """Recover ATR from sl distance (sl = entry ± 1.5×ATR)."""
    return abs(float(row["entry"]) - float(row["sl"])) / SL_ATR


def build_context_df(direction, entry, atr_val):
    """
    32-bar synthetic OHLCV context that includes an equal-lows (BUY) or
    equal-highs (SELL) cluster just inside the stop side of entry.

    Structure:
      0-19:  quiet bars at entry (sets ATR ≈ atr_val)
      20-21: two bars with nearly-equal lo (BUY) or hi (SELL) at
             entry ∓ 0.3×ATR — a detectable equal-levels cluster
      22-29: quiet bars back at entry
      30:    live bar (stripped by detector)

    The cluster sits 0.3×ATR inside the stop side, i.e. within default
    proximity_atr=0.5.  So ~all signals will be flagged at_risk on this
    synthetic context.  That is intentional: we want the flag rate to reflect
    how often the detector fires on geometry that is clearly risky, not
    on real market data.  The honest caveat in the output covers this.
    """
    np.random.seed(int(abs(entry * 1000)) % 2**31)
    a = atr_val
    bars = []
    price = entry
    for _ in range(20):
        o = price + np.random.uniform(-0.15 * a, 0.15 * a)
        c = price + np.random.uniform(-0.15 * a, 0.15 * a)
        h = max(o, c) + np.random.uniform(0.0, 0.08 * a)
        l = min(o, c) - np.random.uniform(0.0, 0.08 * a)
        bars.append((o, h, l, c))

    # Cluster bars: equal lows for BUY, equal highs for SELL
    if direction == "BUY":
        cluster_lo = entry - 0.3 * a
        bars.append((entry, entry + 0.2 * a, cluster_lo,       entry + 0.1 * a))
        bars.append((entry, entry + 0.2 * a, cluster_lo + 0.02 * a, entry + 0.1 * a))
    else:
        cluster_hi = entry + 0.3 * a
        bars.append((entry, cluster_hi,        entry - 0.2 * a, entry - 0.1 * a))
        bars.append((entry, cluster_hi + 0.02 * a, entry - 0.2 * a, entry - 0.1 * a))

    for _ in range(8):
        o = price + np.random.uniform(-0.15 * a, 0.15 * a)
        c = price + np.random.uniform(-0.15 * a, 0.15 * a)
        h = max(o, c) + np.random.uniform(0.0, 0.08 * a)
        l = min(o, c) - np.random.uniform(0.0, 0.08 * a)
        bars.append((o, h, l, c))

    # Live bar (stripped)
    bars.append((entry, entry + 0.1 * a, entry - 0.1 * a, entry))

    return pd.DataFrame(bars, columns=["open", "high", "low", "close"])


def build_forward_df(direction, entry, sl, tp, atr_val, rA_baseline,
                     n_bars=MAX_HOLD_BARS + 30):
    """
    Synthetic forward path consistent with the baseline rA outcome.
    Identical approach to ob_retest_backtest.py and idm_backtest.py.

    When the trade is flagged at_risk, we also inject a sweep-and-reclaim
    sequence in the first SWEEP_WAIT_BARS bars so Strategy B can find it:
      - One bar that dips/spikes through the cluster level (sweep)
      - One bar that closes back through cluster_price (reclaim)
    The remaining path then proceeds toward the original target (TP or SL).
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


def inject_sweep_reclaim(fwd_df, direction, cluster_price, atr_val,
                         insert_at=3):
    """
    Insert a sweep bar (briefly beyond cluster_price) and a reclaim bar
    (close back through it) at bars insert_at and insert_at+1 of fwd_df.
    Used to ensure Strategy B can exercise the sweep-and-reclaim path.
    Returns modified DataFrame.
    """
    bars = list(fwd_df.itertuples(index=False, name=None))
    if insert_at + 1 >= len(bars):
        return fwd_df

    if direction == "BUY":
        # Sweep: lo dips below cluster_price; reclaim: close above cluster_price
        sweep_bar   = (cluster_price + 0.1 * atr_val,
                       cluster_price + 0.3 * atr_val,
                       cluster_price - 0.15 * atr_val,   # lo below cluster
                       cluster_price + 0.05 * atr_val)
        reclaim_bar = (cluster_price + 0.05 * atr_val,
                       cluster_price + 0.5 * atr_val,
                       cluster_price - 0.05 * atr_val,
                       cluster_price + 0.4 * atr_val)    # close above cluster
    else:
        # Sweep: hi spikes above cluster_price; reclaim: close below cluster_price
        sweep_bar   = (cluster_price - 0.1 * atr_val,
                       cluster_price + 0.15 * atr_val,   # hi above cluster
                       cluster_price - 0.3 * atr_val,
                       cluster_price - 0.05 * atr_val)
        reclaim_bar = (cluster_price - 0.05 * atr_val,
                       cluster_price + 0.05 * atr_val,
                       cluster_price - 0.5 * atr_val,
                       cluster_price - 0.4 * atr_val)    # close below cluster

    bars.insert(insert_at, sweep_bar)
    bars.insert(insert_at + 1, reclaim_bar)
    return pd.DataFrame(bars, columns=["open", "high", "low", "close"])


def simulate_mae(hi_arr, lo_arr, direction, entry, sl, ru, start_bar):
    """
    Walk forward from start_bar and record the maximum adverse excursion
    (worst move against entry, in R-units) before SL or TP is hit or
    MAX_HOLD_BARS expires.

    For a BUY: MAE = max(entry - min(lo[start_bar:])) / ru
    For a SELL: MAE = max(max(hi[start_bar:]) - entry) / ru
    """
    if ru <= 0:
        return 0.0
    n = len(hi_arr)
    worst = 0.0
    for j in range(start_bar, min(start_bar + MAX_HOLD_BARS, n)):
        if direction == "BUY":
            adverse = (entry - lo_arr[j]) / ru
        else:
            adverse = (hi_arr[j] - entry) / ru
        if adverse > worst:
            worst = adverse
    return round(float(worst), 5)


def simulate_single_with_mae(fwd_df, direction, entry, sl, tp):
    """
    Walk forward from bar 1.  Market entry at bar 0.
    Returns (R, bars_held, resolved, mae_R).
    """
    hi = fwd_df.high.values
    lo = fwd_df.low.values
    cl = fwd_df.close.values
    n  = len(fwd_df)
    ru = abs(entry - sl)
    if ru == 0:
        return 0.0, 0, False, 0.0
    for j in range(1, min(1 + MAX_HOLD_BARS, n)):
        hit_sl = lo[j] <= sl if direction == "BUY" else hi[j] >= sl
        hit_tp = hi[j] >= tp if direction == "BUY" else lo[j] <= tp
        if hit_sl:
            mae = simulate_mae(hi, lo, direction, entry, sl, ru, 1)
            return -(abs(entry - sl) / ru), j, True, mae
        if hit_tp:
            mae = simulate_mae(hi, lo, direction, entry, sl, ru, 1)
            return  (abs(tp - entry) / ru), j, True, mae
    last = cl[min(MAX_HOLD_BARS, n - 1)]
    sgn = 1 if direction == "BUY" else -1
    mae = simulate_mae(hi, lo, direction, entry, sl, ru, 1)
    return sgn * (last - entry) / ru, MAX_HOLD_BARS, False, mae


def simulate_trap_wait_with_mae(fwd_df, direction, entry_fallback, sl, tp,
                                 atr_val, cluster_price):
    """
    B strategy: scan up to SWEEP_WAIT_BARS for sweep of cluster_price,
    then up to RECLAIM_BARS for a close-back-through (reclaim).
    Entry at close of the reclaim bar.  SL/TP recalculated from reclaim entry.

    Returns (R, used_trap_wait, bars_held, resolved, mae_R).
    used_trap_wait: True if strategy B got the sweep+reclaim entry, False if
                    fallback was used, None if trade was skipped.
    """
    hi = fwd_df.high.values
    lo = fwd_df.low.values
    cl = fwd_df.close.values
    n  = len(fwd_df)

    # Phase 1 — find sweep of cluster_price
    sweep_bar = None
    for j in range(1, min(1 + SWEEP_WAIT_BARS, n)):
        if direction == "BUY" and lo[j] < cluster_price:
            sweep_bar = j
            break
        if direction == "SELL" and hi[j] > cluster_price:
            sweep_bar = j
            break

    if sweep_bar is None:
        if not USE_FALLBACK:
            return None, None, SWEEP_WAIT_BARS, False, 0.0
        r, bh, res, mae = simulate_single_with_mae(
            fwd_df, direction, entry_fallback, sl, tp)
        return r, False, bh, res, mae

    # Phase 2 — find reclaim (close back through cluster_price)
    reclaim_bar = None
    end_reclaim = min(sweep_bar + 1 + RECLAIM_BARS, n)
    for j in range(sweep_bar + 1, end_reclaim):
        if direction == "BUY" and cl[j] > cluster_price:
            reclaim_bar = j
            break
        if direction == "SELL" and cl[j] < cluster_price:
            reclaim_bar = j
            break

    if reclaim_bar is None:
        if not USE_FALLBACK:
            return None, None, sweep_bar + RECLAIM_BARS, False, 0.0
        r, bh, res, mae = simulate_single_with_mae(
            fwd_df, direction, entry_fallback, sl, tp)
        return r, False, bh, res, mae

    # Entered at close of reclaim bar
    reclaim_entry = float(cl[reclaim_bar])
    if direction == "BUY":
        new_sl = reclaim_entry - SL_ATR * atr_val
        new_tp = reclaim_entry + TP_ATR * atr_val
    else:
        new_sl = reclaim_entry + SL_ATR * atr_val
        new_tp = reclaim_entry - TP_ATR * atr_val

    ru = abs(reclaim_entry - new_sl)
    if ru == 0:
        return 0.0, True, reclaim_bar, False, 0.0

    mae = simulate_mae(hi, lo, direction, reclaim_entry, new_sl, ru,
                       reclaim_bar + 1)

    for j in range(reclaim_bar + 1, min(reclaim_bar + 1 + MAX_HOLD_BARS, n)):
        hit_sl = lo[j] <= new_sl if direction == "BUY" else hi[j] >= new_sl
        hit_tp = hi[j] >= new_tp if direction == "BUY" else lo[j] <= new_tp
        if hit_sl:
            return -(abs(reclaim_entry - new_sl) / ru), True, j, True, mae
        if hit_tp:
            return  (abs(new_tp - reclaim_entry) / ru), True, j, True, mae

    last = cl[min(reclaim_bar + MAX_HOLD_BARS, n - 1)]
    sgn = 1 if direction == "BUY" else -1
    r = sgn * (last - reclaim_entry) / ru
    return r, True, MAX_HOLD_BARS, False, mae


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
    flagged_at_risk = 0

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

        # Build context DF and run liquidity-risk check
        ctx_df  = build_context_df(direction, entry, atr_val)
        risk    = assess_entry_liquidity_risk(
            ctx_df, entry_price=entry, direction=direction,
            proximity_atr=PROXIMITY_ATR)
        at_risk = risk.get("at_risk", False)

        if at_risk:
            flagged_at_risk += 1
            cluster_price = risk["cluster_price"]
        else:
            cluster_price = None

        # Build forward path; if at_risk, inject a sweep-and-reclaim sequence
        fwd_df = build_forward_df(direction, entry, sl, tp, atr_val, rA_baseline)
        if at_risk and cluster_price is not None:
            fwd_df = inject_sweep_reclaim(fwd_df, direction, cluster_price, atr_val)

        # Strategy A — market entry at signal
        rA, bh_a, res_a, mae_a = simulate_single_with_mae(
            fwd_df, direction, entry, sl, tp)

        # Strategy B — trap-wait entry
        if at_risk and cluster_price is not None:
            rB_raw, used_trap, bh_b, res_b, mae_b = simulate_trap_wait_with_mae(
                fwd_df, direction, entry, sl, tp, atr_val, cluster_price)
        else:
            rB_raw, used_trap, bh_b, res_b, mae_b = rA, False, bh_a, res_a, mae_a

        if rB_raw is None:
            rB_raw = 0.0
            used_trap = None
            mae_b = 0.0

        rows.append(dict(
            sym=sym, tf=tf, dir=direction,
            entry=entry, sl=sl, tp=tp,
            rA=rA, rB=rB_raw,
            mae_a=mae_a, mae_b=mae_b,
            at_risk=at_risk,
            used_trap=used_trap,
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
    def stats(r_col, mae_col):
        s = out[r_col].dropna()
        m = out[mae_col].dropna()
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
            avg_mae=round(float(m.mean()), 5),
        )

    st_A = stats("rA", "mae_a")
    st_B = stats("rB", "mae_b")

    total = len(out)
    flag_rate   = round(100 * flagged_at_risk / total, 1) if total else 0.0
    trap_rate   = round(100 * out["used_trap"].eq(True).mean(), 1)

    # Subset where at_risk=True
    risk_subset = out[out["at_risk"]]
    if len(risk_subset) > 0:
        risk_st = dict(
            n=len(risk_subset),
            A_avg_R=round(float(risk_subset.rA.mean()), 5),
            B_avg_R=round(float(risk_subset.rB.mean()), 5),
            A_avg_mae=round(float(risk_subset.mae_a.mean()), 5),
            B_avg_mae=round(float(risk_subset.mae_b.mean()), 5),
        )
    else:
        risk_st = {"n": 0}

    # Subset where B actually used sweep-and-reclaim
    trap_used = out[out["used_trap"] == True]
    if len(trap_used) > 0:
        trap_st = dict(
            n=len(trap_used),
            A_avg_R=round(float(trap_used.rA.mean()), 5),
            B_avg_R=round(float(trap_used.rB.mean()), 5),
            A_avg_mae=round(float(trap_used.mae_a.mean()), 5),
            B_avg_mae=round(float(trap_used.mae_b.mean()), 5),
        )
    else:
        trap_st = {"n": 0}

    per_tf  = {tf:  {"A_avg_R": round(float(g.rA.mean()), 5),
                     "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for tf, g in out.groupby("tf")}
    per_dir = {d:   {"A_avg_R": round(float(g.rA.mean()), 5),
                     "B_avg_R": round(float(g.rB.mean()), 5), "n": len(g)}
               for d, g in out.groupby("dir")}

    # ── Gate ──────────────────────────────────────────────────────────────────
    b_beats_avgR    = st_B["avg_R"]    > st_A["avg_R"]
    b_ok_drawdown   = st_B["max_dd_R"] >= st_A["max_dd_R"]
    b_lower_mae     = st_B["avg_mae"]  <  st_A["avg_mae"]
    gate_pass       = b_beats_avgR and b_ok_drawdown

    verdict = (
        "GATE PASS — B (trap-wait) beats A on avg R AND does not worsen drawdown. "
        + ("MAE also improved (less adverse heat). " if b_lower_mae else
           "MAE did NOT improve (more heat before resolution). ")
        + "SYNTHETIC DATA: directional only — do not trade on this result."
        if gate_pass else
        "GATE FAIL — "
        + ("B has lower avg R than A. " if not b_beats_avgR else "")
        + ("B worsens max drawdown vs A. " if not b_ok_drawdown else "")
        + ("MAE reduced. " if b_lower_mae else "MAE not reduced. ")
        + "Trap-wait does not provide a reliable edge on synthetic paths. "
        "SYNTHETIC DATA WARNING — see caveat."
    )

    caveat = (
        "SYNTHETIC DATA WARNING: forward paths are Monte Carlo simulations "
        "derived from each signal's entry/sl/tp geometry and baseline rA outcome. "
        "The context DF is constructed to always contain an equal-levels cluster "
        "near entry (0.3×ATR inside stop side), so the flag rate is artificially "
        "inflated (~100%) relative to real market data.  On real data the flag rate "
        "will be lower (clusters occur perhaps 20–50% of the time near entries). "
        "All R/win-rate/MAE/drawdown figures are model artifacts.  Use this backtest "
        "to verify detector logic and sweep-reclaim entry mechanics, NOT to size "
        "positions or claim a live edge.  Re-run on real tick/1-min OHLCV data before "
        "drawing any trading conclusions."
    )

    result = {
        "A_signal_entry":         st_A,
        "B_trap_wait_entry":      st_B,
        "signals_processed":      total,
        "flagged_at_risk_pct":    flag_rate,
        "trap_wait_entry_rate_pct": trap_rate,
        "at_risk_subset":         risk_st,
        "trap_used_subset":       trap_st,
        "per_tf":                 per_tf,
        "per_dir":                per_dir,
        "sweep_wait_bars":        SWEEP_WAIT_BARS,
        "reclaim_bars":           RECLAIM_BARS,
        "proximity_atr":          PROXIMITY_ATR,
        "use_fallback":           USE_FALLBACK,
        "gate": {
            "b_beats_avg_R":    b_beats_avgR,
            "b_ok_drawdown":    b_ok_drawdown,
            "b_lower_mae":      b_lower_mae,
            "gate_pass":        gate_pass,
            "verdict":          verdict,
        },
        "caveat": caveat,
    }

    # ── Print verdict table ────────────────────────────────────────────────────
    print()
    print("=" * 72)
    print("  TRAP-AVOIDANCE BACKTEST VERDICT  (D3)")
    print("=" * 72)
    fmt = "  {:<34} {:>12} {:>12}"
    print(fmt.format("Metric", "A (signal)", "B (trap-wait)"))
    print("  " + "-" * 68)
    print(fmt.format("Trades",        st_A["trades"],       st_B["trades"]))
    print(fmt.format("Win rate %",    st_A["win_rate"],      st_B["win_rate"]))
    print(fmt.format("Avg R",         st_A["avg_R"],         st_B["avg_R"]))
    print(fmt.format("Total R",       st_A["total_R"],       st_B["total_R"]))
    print(fmt.format("Max DD (R)",    st_A["max_dd_R"],      st_B["max_dd_R"]))
    print(fmt.format("Profit factor", st_A["profit_factor"], st_B["profit_factor"]))
    print(fmt.format("Avg MAE (R)",   st_A["avg_mae"],       st_B["avg_mae"]))
    print()
    print(f"  Signals flagged at_risk:           {flag_rate}%")
    print(f"  Trap-wait entry rate (B used it):  {trap_rate}%")
    print()
    if risk_st.get("n", 0) > 0:
        print(f"  At-risk subset ({risk_st['n']} trades):")
        print(f"    A avg R={risk_st['A_avg_R']}, B avg R={risk_st['B_avg_R']}")
        print(f"    A avg MAE={risk_st['A_avg_mae']}, B avg MAE={risk_st['B_avg_mae']}")
    if trap_st.get("n", 0) > 0:
        print(f"  Trap-used subset ({trap_st['n']} trades):")
        print(f"    A avg R={trap_st['A_avg_R']}, B avg R={trap_st['B_avg_R']}")
        print(f"    A avg MAE={trap_st['A_avg_mae']}, B avg MAE={trap_st['B_avg_mae']}")
    print()
    print(f"  GATE: {verdict}")
    print()
    print(f"  CAVEAT: {caveat}")
    print("=" * 72)
    print()

    # ── Save ──────────────────────────────────────────────────────────────────
    out_path = Path(__file__).parent / "trap_avoidance_summary.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Summary written to {out_path}")

    trades_path = Path(__file__).parent / "trap_avoidance_trades.csv"
    out.to_csv(trades_path, index=False)
    print(f"Trades written to  {trades_path}")

    return result


if __name__ == "__main__":
    run()
