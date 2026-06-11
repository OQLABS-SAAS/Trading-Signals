"""Structure-density measurement — D4 uplift quantification.

Runs structure_context() over the 1,087-signal chunk dataset and compares
old (binary, single-TF) vs new (graded, multi-TF) density metrics.

HONEST CAVEAT (same as ob_retest_backtest.py)
----------------------------------------------
The chunk files contain per-signal scalar fields (entry, sl, tp, direction,
ob_real) but NOT the full OHLCV price series.  We reconstruct a synthetic
31-bar context frame per signal using ob_real to branch geometry:
  - ob_real=True  → OB candle placed at entry ± 0.3 ATR (close, structure present)
  - ob_real=False → OB candle placed 6 ATR away (distant, no nearby structure)
This means:

  - The absolute density % APPROXIMATELY MATCHES the real ob_real distribution
    (i.e. ~13.2% baseline) for the old binary metric.
  - The relative uplift from graded/multi-TF adds signals that the old binary
    metric missed: FVGs, liquidity clusters, and OBs in the 0.5–4 ATR window.
  - Absolute %s are still synthetic — re-run with real OHLCV klines for
    production-quality numbers.
  - What IS fully production-ready:
      (a) The INFRASTRUCTURE: structure_context() invocation, grade breakdown,
          source_tf tagging, and the density_summary.json schema.
      (b) The RELATIVE uplift mechanics: graded proximity vs binary cutoff.

Output
------
  research/density_summary.json — full breakdown by grade, source_tf, dir, tf
  Printed table — quick read of old vs new

Run:
    python3 research/density_measurement.py
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from smc_structure import structure_context

# ── Config ────────────────────────────────────────────────────────────────────
SL_ATR     = 1.5   # how SL distance was set (entry ± 1.5 × ATR)
QUIET_BARS = 20    # pre-OB quiet bars in the synthetic frame
# Old binary threshold (approximates the 13.2% baseline):
#   "has structure" iff at least one OB is within ≤0.5 ATR on the entry TF only
OLD_BINARY_THRESHOLD_ATR = 0.5


# ── Chunk loader (reused from ob_retest_backtest.py) ─────────────────────────

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


# ── Synthetic context frame builder (mirrors ob_retest_backtest.py exactly) ──

def atr_from_signal(row):
    return abs(float(row["entry"]) - float(row["sl"])) / SL_ATR


def build_synthetic_price_df(row, direction, entry, atr_val, ob_close_to_entry):
    """
    Reconstruct a minimal 31-bar OHLCV DataFrame consistent with the signal.

    ob_close_to_entry : bool
        When True  — the OB candle is placed at entry ± 0.3*ATR, so
                     structure_context() will find an OB within 0.5 ATR
                     (replicates the ob_retest_backtest geometry).
        When False — the OB candle and its displacement are placed 6*ATR
                     AWAY from entry (a distant historical move), so the
                     detected OB zone will be far from entry and
                     structure_context() correctly returns grade=None or
                     'context' at best.  This models a signal generated
                     by momentum/RSI with no fresh nearby OB.

    Source of ground truth for ob_close_to_entry:
        The chunk files contain 'ob_real' (True/False from the original
        backtest) recording whether a native order block existed near the
        signal.  We use that flag to branch geometry here, so the synthetic
        measurement respects the real ob_real distribution.

    This is a synthetic surrogate — see module-level caveat.
    """
    np.random.seed(int(abs(entry * 1000)) % 2**31)
    a = atr_val
    bars = []

    if ob_close_to_entry:
        # ── Geometry A: OB close to entry (the 13.2% case) ───────────────────
        price = entry
        for _ in range(QUIET_BARS):
            o = price + np.random.uniform(-0.2 * a, 0.2 * a)
            c = price + np.random.uniform(-0.2 * a, 0.2 * a)
            h = max(o, c) + np.random.uniform(0, 0.1 * a)
            l = min(o, c) - np.random.uniform(0, 0.1 * a)
            bars.append((o, h, l, c))
        # OB candle — opposite colour to direction, zone midpoint ≈ entry
        if direction == "BUY":
            o, c = price + 0.3 * a, price - 0.3 * a
        else:
            o, c = price - 0.3 * a, price + 0.3 * a
        h = max(o, c) + 0.1 * a
        l = min(o, c) - 0.1 * a
        bars.append((o, h, l, c))
        # Displacement
        if direction == "BUY":
            o2, c2 = price - 0.1 * a, price + 3.0 * a
        else:
            o2, c2 = price + 0.1 * a, price - 3.0 * a
        h2 = max(o2, c2) + 0.1 * a
        l2 = min(o2, c2) - 0.1 * a
        bars.append((o2, h2, l2, c2))
        price2 = c2
        for _ in range(8):
            o = price2 + np.random.uniform(-0.2 * a, 0.2 * a)
            c3 = price2 + np.random.uniform(-0.2 * a, 0.2 * a)
            h = max(o, c3) + np.random.uniform(0, 0.1 * a)
            l = min(o, c3) - np.random.uniform(0, 0.1 * a)
            bars.append((o, h, l, c3))

    else:
        # ── Geometry B: OB far from entry (the 86.8% case) ───────────────────
        # Model: price has been ranging at entry for the entire lookback window.
        # The historical OB/displacement happened 6+ ATR away and is NOT in
        # this window.  Bars are deliberately flat with tiny identical body+wick
        # so detect_order_blocks finds NO displacement (body never > 2×ATR) and
        # detect_liquidity_clusters / FVG detection finds nothing near entry.
        #
        # We use alternating bull/bear bars with a very small body (0.05×ATR)
        # and tiny wick (0.02×ATR).  This produces:
        #   - ATR  ≈ 0.07 × atr_val  (much smaller than the passed-in atr_val,
        #     but that is fine: structure_context computes ATR from the frame)
        #   - No displacement (body 0.05×ATR << 2×internal ATR)
        #   - No equal-highs/lows clusters (every bar is slightly different)
        #   - No FVGs (bars are contiguous, no gap > 0 between hi[i-2] and lo[i])
        #
        # CAVEAT: This is an idealised "no structure" frame.  Real momentum
        # signals will have more micro-structure near entry than this.  The
        # measurement remains approximate; re-run on real klines.
        body_b = 0.05 * a
        wick_b = 0.02 * a
        for k in range(QUIET_BARS + 10):   # 30 total bars
            if k % 2 == 0:
                o, c = entry - body_b / 2, entry + body_b / 2
            else:
                o, c = entry + body_b / 2, entry - body_b / 2
            # Add a tiny per-bar offset so no two lows/highs are identical
            jitter = (k * 0.003 * a) % (0.01 * a)
            h = max(o, c) + wick_b + jitter
            l = min(o, c) - wick_b - jitter
            bars.append((o, h, l, c))

    return pd.DataFrame(bars, columns=["open", "high", "low", "close"])


# ── Structure checks ──────────────────────────────────────────────────────────

def old_binary_has_structure(ctx):
    """
    Approximate the 13.2% baseline:  True iff any 'order_block' item on the
    'entry' TF has distance_atr <= OLD_BINARY_THRESHOLD_ATR.
    This is what the pre-D4 code effectively measured.
    """
    return any(
        it["type"] == "order_block"
        and it["source_tf"] == "entry"
        and it["distance_atr"] <= OLD_BINARY_THRESHOLD_ATR
        for it in ctx["items"]
    )


def new_ob_graded_has_structure(ctx):
    """
    New graded — OB only, entry TF — at/near (<=1.5 ATR).
    Apples-to-apples with old binary: same structure type, wider window.
    This is the honest uplift from relaxing the 0.5->1.5 ATR threshold.
    """
    return any(
        it["type"] == "order_block"
        and it["source_tf"] == "entry"
        and it["distance_atr"] <= 1.5
        for it in ctx["items"]
    )


def new_full_has_structure(ctx):
    """
    New full — OB + FVG + liquidity cluster, at/near (<=1.5 ATR), entry TF.
    Maximum uplift from adding structure types. On synthetic frames the
    liquidity-cluster detector will over-fire; on real klines it's meaningful.
    Reported separately so the reader can judge each source of uplift.
    """
    return any(
        it["source_tf"] == "entry"
        and it["distance_atr"] <= 1.5
        for it in ctx["items"]
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print("Loading chunk data …")
    df_signals = load_chunks()
    print(f"  Total signal rows: {len(df_signals)}")

    # Counters
    total   = 0
    skipped = 0

    old_has      = 0   # OLD: entry-TF OB only, <=0.5 ATR (the 13.2% baseline)
    new_ob_wide  = 0   # NEW-A (apples-to-apples): entry-TF OB, <=1.5 ATR
    new_full     = 0   # NEW-B (all types): OB+FVG+cluster, <=1.5 ATR, entry-TF

    # Grade breakdown (all-types grader — reflects what structure_context returns)
    grade_counts   = defaultdict(int)
    source_counts  = defaultdict(int)   # source_tf → signals touching that TF
    type_counts    = defaultdict(int)   # structure type → item count

    # Per-signal attribute breakdown
    by_dir  = defaultdict(lambda: {"old": 0, "new_ob_wide": 0, "new_full": 0, "total": 0})
    by_tf   = defaultdict(lambda: {"old": 0, "new_ob_wide": 0, "new_full": 0, "total": 0})

    print("Processing signals …")
    for _, row in df_signals.iterrows():
        direction = str(row.get("dir", "BUY")).upper()
        try:
            entry   = float(row["entry"])
            sl      = float(row["sl"])
            atr_val = atr_from_signal(row)
        except (KeyError, ValueError, TypeError):
            skipped += 1
            continue

        if atr_val <= 0:
            skipped += 1
            continue

        sig_tf = str(row.get("tf", "?"))

        # Use ob_real from the chunk data to branch geometry:
        #   ob_real=True  → OB was genuinely close to entry in the original data
        #   ob_real=False → no nearby OB; build a frame with distant structure
        # This makes the synthetic density measurement respect the real
        # ob_real distribution rather than fabricating structure for every signal.
        raw_ob_real = row.get("ob_real", "False")
        if isinstance(raw_ob_real, bool):
            ob_close = raw_ob_real
        else:
            ob_close = str(raw_ob_real).strip().lower() in ("true", "1", "yes")

        # Build synthetic context frame
        ctx_df = build_synthetic_price_df(row, direction, entry, atr_val, ob_close)

        # Supply the signal's ATR (recovered from SL distance) as atr_series so
        # structure_context grades distances in real-market ATR units, not in the
        # synthetic frame's internal micro-ATR (which would be artificially small
        # for the flat geometry-B frames and inflate the grade).
        atr_s = pd.Series(
            [atr_val] * len(ctx_df),
            index=ctx_df.index,
            dtype=float,
        )

        # structure_context: entry-TF only (no higher_tf_frames)
        # — matches how it would be called for a real signal without live higher-TF fetch
        ctx = structure_context(ctx_df, entry_price=entry, direction=direction,
                                atr_series=atr_s)

        total += 1

        # Three-metric evaluation
        old_flag     = old_binary_has_structure(ctx)
        ob_wide_flag = new_ob_graded_has_structure(ctx)
        full_flag    = new_full_has_structure(ctx)

        if old_flag:     old_has     += 1
        if ob_wide_flag: new_ob_wide += 1
        if full_flag:    new_full    += 1

        # Grade breakdown (structure_context's own grader covers all types)
        grade = ctx["grade"]
        grade_counts[grade if grade is not None else "none"] += 1

        # Source TF breakdown — count unique source_tfs per signal
        seen_src = set()
        for it in ctx["items"]:
            seen_src.add(it["source_tf"])
            type_counts[it["type"]] += 1
        for src in seen_src:
            source_counts[src] += 1

        # Per-direction / per-TF breakdown
        by_dir[direction]["total"]   += 1
        by_tf[sig_tf]["total"]       += 1
        if old_flag:
            by_dir[direction]["old"] += 1
            by_tf[sig_tf]["old"]     += 1
        if ob_wide_flag:
            by_dir[direction]["new_ob_wide"] += 1
            by_tf[sig_tf]["new_ob_wide"]     += 1
        if full_flag:
            by_dir[direction]["new_full"] += 1
            by_tf[sig_tf]["new_full"]     += 1

    if skipped:
        print(f"  Skipped {skipped} malformed rows")

    if total == 0:
        print("!! No rows processed.")
        return

    def pct(n):
        return round(100.0 * n / total, 1)

    # ── Print table ───────────────────────────────────────────────────────────
    print()
    print("=" * 76)
    print("  STRUCTURE DENSITY: OLD BINARY vs NEW GRADED (D4)")
    print("=" * 76)
    print(f"  Signals processed : {total}  (skipped: {skipped})")
    print()
    print("  ── Overall density ──────────────────────────────────────────────────")
    print("  Three metrics (explained below):")
    fmt = "  {:<52} {:>6}  ({:>5}%)"
    print(fmt.format("OLD:   entry-TF OB <=0.5 ATR  [13.2% real baseline anchor]",
                     old_has, pct(old_has)))
    print(fmt.format("NEW-A: entry-TF OB <=1.5 ATR  [wider window, same type]",
                     new_ob_wide, pct(new_ob_wide)))
    print(fmt.format("NEW-B: OB+FVG+cluster <=1.5 ATR  [all types, entry-TF]",
                     new_full, pct(new_full)))
    print()
    print("  Interpretation:")
    print(f"  OLD->NEW-A uplift (OB only, wider window):   "
          f"{pct(new_ob_wide) - pct(old_has):+.1f} pp")
    print(f"  NEW-A->NEW-B uplift (adding FVG+clusters):   "
          f"{pct(new_full) - pct(new_ob_wide):+.1f} pp")
    print(f"  Total uplift OLD->NEW-B:                     "
          f"{pct(new_full) - pct(old_has):+.1f} pp")
    print()
    print("  NOTE: NEW-B uplift on synthetic frames is inflated by liquidity-")
    print("  cluster detection firing on flat-bar geometry.  On real klines,")
    print("  OB-only NEW-A uplift is the reliable figure.")
    print()
    print("  ── Grade breakdown (structure_context grader, all types) ────────────")
    for g in ("at", "near", "context", "none"):
        print(f"  {g:<12}  {grade_counts[g]:>6}  ({pct(grade_counts[g]):>5}%)")
    print()
    print("  ── Source TF breakdown (signals touching each TF) ───────────────────")
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        print(f"  {src:<12}  {cnt:>6}  ({pct(cnt):>5}%)")
    print()
    print("  ── Structure type breakdown (items, not signals) ────────────────────")
    for typ, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {typ:<22}  {cnt:>8}")
    print()
    print("  ── By direction ─────────────────────────────────────────────────────")
    print(f"  {'Dir':<6} {'N':>6}  {'OLD%':>6}  {'NEW-A%':>7}  {'NEW-B%':>7}")
    for d, v in sorted(by_dir.items()):
        n = v["total"]
        op  = round(100.0 * v["old"]       / n, 1) if n else 0.0
        na  = round(100.0 * v["new_ob_wide"] / n, 1) if n else 0.0
        nb  = round(100.0 * v["new_full"]  / n, 1) if n else 0.0
        print(f"  {d:<6} {n:>6}  {op:>5}%  {na:>6}%  {nb:>6}%")
    print()
    print("  ── By entry TF ──────────────────────────────────────────────────────")
    print(f"  {'TF':<8} {'N':>6}  {'OLD%':>6}  {'NEW-A%':>7}  {'NEW-B%':>7}")
    for tf_, v in sorted(by_tf.items()):
        n = v["total"]
        op  = round(100.0 * v["old"]       / n, 1) if n else 0.0
        na  = round(100.0 * v["new_ob_wide"] / n, 1) if n else 0.0
        nb  = round(100.0 * v["new_full"]  / n, 1) if n else 0.0
        print(f"  {tf_:<8} {n:>6}  {op:>5}%  {na:>6}%  {nb:>6}%")
    print()
    print("  HONEST CAVEAT: frames branch on ob_real from chunk data.")
    print("  OLD anchors to real 13.2% baseline.  NEW-A (OB wider window)")
    print("  is the reliable uplift signal.  NEW-B inflated by cluster noise")
    print("  on synthetic flat bars — re-run on real OHLCV for true figure.")
    print("=" * 76)
    print()

    # ── Save JSON ─────────────────────────────────────────────────────────────
    summary = {
        "caveat": (
            "Synthetic frames branch on ob_real from chunk data: ob_real=True places the OB "
            "close to entry (≈0.3 ATR), ob_real=False places it 6 ATR away. "
            "The old binary metric anchors to ~13.2% (the real baseline). "
            "The new graded metric adds uplift from FVGs, liquidity clusters, and the wider "
            "0.5–4 ATR window. Absolute %s are still synthetic; "
            "re-run with real OHLCV klines for production-quality numbers."
        ),
        "signals_processed": total,
        "signals_skipped":   skipped,
        "old_binary": {
            "description": "single-TF OB ≤ 0.5 ATR (approximates 13.2% baseline)",
            "count": old_has,
            "pct":   pct(old_has),
        },
        "new_graded": {
            "description_A": "OB only, entry-TF, <=1.5 ATR (apples-to-apples wider window)",
            "new_ob_wide_count": new_ob_wide, "new_ob_wide_pct": pct(new_ob_wide),
            "uplift_A_vs_old_pp": round(pct(new_ob_wide) - pct(old_has), 1),
            "description_B": "OB+FVG+cluster, entry-TF, <=1.5 ATR (all types, inflated on synthetic)",
            "new_full_count": new_full, "new_full_pct": pct(new_full),
            "uplift_B_vs_old_pp": round(pct(new_full) - pct(old_has), 1),
        },
        "grade_breakdown": {g: {"count": grade_counts[g], "pct": pct(grade_counts[g])}
                            for g in ("at", "near", "context", "none")},
        "source_tf_breakdown": {src: {"count": cnt, "pct": pct(cnt)}
                                 for src, cnt in source_counts.items()},
        "structure_type_breakdown": dict(type_counts),
        "by_direction": {
            d: {
                "n": v["total"],
                "old_pct":       round(100.0 * v["old"]        / v["total"], 1) if v["total"] else 0.0,
                "new_ob_wide_pct": round(100.0 * v["new_ob_wide"] / v["total"], 1) if v["total"] else 0.0,
                "new_full_pct":  round(100.0 * v["new_full"]   / v["total"], 1) if v["total"] else 0.0,
            }
            for d, v in by_dir.items()
        },
        "by_entry_tf": {
            tf_: {
                "n": v["total"],
                "old_pct":       round(100.0 * v["old"]        / v["total"], 1) if v["total"] else 0.0,
                "new_ob_wide_pct": round(100.0 * v["new_ob_wide"] / v["total"], 1) if v["total"] else 0.0,
                "new_full_pct":  round(100.0 * v["new_full"]   / v["total"], 1) if v["total"] else 0.0,
            }
            for tf_, v in by_tf.items()
        },
        "what_to_do_for_real_data": (
            "1. Fetch OHLCV klines for each signal's symbol+tf around the signal timestamp. "
            "2. Optionally fetch H4 and D1 klines and pass as higher_tf_frames={}. "
            "3. Call structure_context(df_entry, entry_price, direction, higher_tf_frames). "
            "4. Record ctx['has_structure'], ctx['grade'], and ctx['items']. "
            "5. Re-run this script with real frames substituted."
        ),
    }

    out_path = Path(__file__).parent / "density_summary.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"Summary written to {out_path}")

    return summary


if __name__ == "__main__":
    run()
