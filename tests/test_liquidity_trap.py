"""Unit tests for assess_entry_liquidity_risk() — D3 Liquidity-Trap Avoidance.

Synthetic OHLC frames are built so that geometry is fully deterministic and
the detector's internal ATR and cluster logic behave predictably.

Key geometry design rules (learned from calibration):
  - Use large-body bars (body=2.0, wick=0.5) to produce ATR ≈ 2.5–3.0.
    This gives a wide eq_tol (0.1×ATR ≈ 0.25–0.30) making cluster detection
    robust to small rounding.
  - Flat-bar lows sit at price - body/2 - wick = 200 - 1 - 0.5 = 198.5
    and highs at 201.5.  These are ABOVE a BUY entry near 196 and BELOW a
    SELL entry near 204, so the direction filter naturally ignores them.
  - The explicit cluster bars are placed CLEARLY within or outside proximity
    and verified to be the nearest at-risk cluster.

Covered scenarios
-----------------
1. BUY entry within proximity of an equal-lows cluster below entry
   → at_risk True, cluster_type 'equal_lows', sensible suggestion.
2. BUY entry far from any cluster (> proximity away) → at_risk False.
3. SELL entry within proximity of an equal-highs cluster above entry
   → at_risk True, cluster_type 'equal_highs'.
4. Cluster present below entry but explicitly beyond proximity → at_risk False.
5. Short df (< 20 bars) returns {at_risk: False} without raising.
6. detect_smc_structures() output contains 'liquidity_clusters' key (list).
7. Swing-pool (fractal swing low within proximity of BUY entry)
   → at_risk True, cluster_type 'swing_pool'.

Run:
    python3 -m pytest tests/test_liquidity_trap.py -q -p no:cacheprovider
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smc_structure import assess_entry_liquidity_risk, detect_smc_structures


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_df(bars):
    """bars = list of (open, high, low, close)."""
    return pd.DataFrame(bars, columns=["open", "high", "low", "close"])


def uniform_bars(n, price, body=2.0, wick=0.5):
    """
    Generate n alternating bull/bear candles at `price` with fixed body and wick.
    Body=2.0, wick=0.5 → ATR ≈ 2.5–3.0 after EWM warm-up.
    Lows sit at price - body/2 - wick;  highs at price + body/2 + wick.
    """
    rows = []
    for i in range(n):
        if i % 2 == 0:
            o, c = price - body / 2, price + body / 2
        else:
            o, c = price + body / 2, price - body / 2
        rows.append((o, c + wick, c - wick, c))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: BUY entry within proximity of an equal-lows cluster → at_risk True
# ─────────────────────────────────────────────────────────────────────────────

def test_buy_entry_on_equal_lows_cluster():
    """
    Geometry:
      30 uniform bars at price=200 (body=2.0, wick=0.5) → ATR ≈ 2.8.
      eq_tol ≈ 0.28, so lows differing by ≤ 0.28 form an equal-lows cluster.
      Two bars with lo=196.00 and lo=196.10 — diff=0.10 < eq_tol ✓
      Cluster level ≈ 196.05, sits BELOW BUY entry=197.0.
      Distance ≈ 0.33 ATR  < default proximity_atr=0.5 ✓.

    Flat-bar lows ≈ 198.5 are ABOVE entry=197.0, so BUY direction filter
    skips them — only the explicit equal-lows cluster is flagged.
    """
    rows = uniform_bars(30, price=200.0)
    # Equal-lows cluster: two wicks ending at ≈196.0
    rows.append((200.0, 201.0, 196.00, 200.5))
    rows.append((200.0, 201.0, 196.10, 200.5))
    rows.append((200.5, 201.5, 200.0, 201.0))   # live bar (stripped)

    df = make_df(rows)
    result = assess_entry_liquidity_risk(df, entry_price=197.0, direction="BUY",
                                         proximity_atr=0.5)

    assert result["at_risk"] is True, f"Expected at_risk=True, got: {result}"
    assert result["cluster_type"] == "equal_lows", \
        f"Expected cluster_type='equal_lows', got: {result['cluster_type']}"
    assert result["cluster_price"] < 197.0, \
        "cluster_price must be below BUY entry"
    assert 195.8 <= result["cluster_price"] <= 196.3, \
        f"cluster_price unexpected: {result['cluster_price']}"
    assert result["distance_atr"] > 0
    assert result["touches"] >= 2

    sug = result["suggestion"]
    assert sug["wait_for"] == "sweep_and_reclaim"
    assert "description" in sug and len(sug["description"]) > 20
    assert "sweep" in sug["description"].lower()
    assert sug["alt_entry_hint"] > result["cluster_price"], \
        "alt_entry_hint should be above the cluster level for a BUY reclaim"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: BUY entry far from any cluster → at_risk False
# ─────────────────────────────────────────────────────────────────────────────

def test_buy_entry_far_from_cluster_no_risk():
    """
    Same equal-lows cluster at ≈196 (ATR ≈ 2.8) but BUY entry at 210.
    Distance ≈ (210 - 196) / 2.8 ≈ 5 ATR >> default proximity_atr=0.5.
    Flat-bar lows at 198.5 are BELOW 210, but their distance from entry
    (≈1.5/2.8 ≈ 0.54 ATR) is just outside proximity_atr=0.5.
    Result must be at_risk=False.
    """
    rows = uniform_bars(30, price=200.0)
    rows.append((200.0, 201.0, 196.00, 200.5))
    rows.append((200.0, 201.0, 196.10, 200.5))
    # live bar — price well above cluster and flat-bar region
    rows.append((209.0, 210.5, 208.5, 210.0))

    df = make_df(rows)
    result = assess_entry_liquidity_risk(df, entry_price=210.0, direction="BUY",
                                         proximity_atr=0.5)
    assert result["at_risk"] is False, f"Expected at_risk=False, got: {result}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: SELL entry within proximity of an equal-highs cluster → at_risk True
# ─────────────────────────────────────────────────────────────────────────────

def test_sell_entry_on_equal_highs_cluster():
    """
    Geometry:
      30 uniform bars at price=200 → ATR ≈ 2.7, eq_tol ≈ 0.27.
      Two bars with hi=204.00 and hi=204.10 — equal-highs cluster at ≈204.05.
      SELL entry at 203.0 — cluster is ABOVE entry, which is stop-side for SELL.
      Distance ≈ (204.05 - 203.0) / 2.7 ≈ 0.39 ATR  < proximity_atr=0.5 ✓.

    Flat-bar highs ≈ 201.5 are BELOW entry=203.0 — SELL filter skips them.
    """
    rows = uniform_bars(30, price=200.0)
    rows.append((202.0, 204.00, 201.5, 202.5))
    rows.append((202.0, 204.10, 201.5, 202.5))
    rows.append((202.5, 203.0, 202.0, 202.7))   # live bar

    df = make_df(rows)
    result = assess_entry_liquidity_risk(df, entry_price=203.0, direction="SELL",
                                         proximity_atr=0.5)

    assert result["at_risk"] is True, f"Expected at_risk=True, got: {result}"
    assert result["cluster_type"] == "equal_highs", \
        f"Expected cluster_type='equal_highs', got: {result['cluster_type']}"
    assert result["cluster_price"] > 203.0, \
        "cluster_price must be above SELL entry"
    assert 203.8 <= result["cluster_price"] <= 204.3, \
        f"cluster_price unexpected: {result['cluster_price']}"
    assert result["touches"] >= 2

    sug = result["suggestion"]
    assert sug["wait_for"] == "sweep_and_reclaim"
    assert sug["alt_entry_hint"] < result["cluster_price"], \
        "alt_entry_hint should be below cluster for SELL reclaim"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Cluster present below entry but beyond proximity → at_risk False
# ─────────────────────────────────────────────────────────────────────────────

def test_cluster_beyond_proximity_returns_false():
    """
    Equal-lows cluster at ≈193 is ≈2.5 ATR below BUY entry=200.
    Default proximity_atr=0.5 — cluster is 5× beyond the threshold.
    Flat-bar lows at ≈198.5 are ≈0.54 ATR from entry=200, just outside
    the default 0.5 ATR proximity, so they also do not trigger.
    Result must be at_risk=False.
    """
    rows = uniform_bars(30, price=200.0)
    rows.append((195.0, 196.0, 193.00, 195.5))
    rows.append((195.0, 196.0, 193.10, 195.5))
    rows.append((199.5, 200.5, 199.0, 200.0))   # live bar

    df = make_df(rows)
    result = assess_entry_liquidity_risk(df, entry_price=200.0, direction="BUY",
                                         proximity_atr=0.5)
    assert result["at_risk"] is False, \
        f"Expected at_risk=False (cluster beyond proximity), got: {result}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Short df → {at_risk: False}, no exception
# ─────────────────────────────────────────────────────────────────────────────

def test_short_df_returns_not_at_risk():
    """df with < 20 bars must return {at_risk: False} without raising."""
    rows = uniform_bars(10, price=100.0)
    df = make_df(rows)
    result = assess_entry_liquidity_risk(df, entry_price=100.0, direction="BUY")
    assert result == {"at_risk": False}


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: detect_smc_structures includes 'liquidity_clusters' key
# ─────────────────────────────────────────────────────────────────────────────

def test_smc_structures_has_liquidity_clusters_key():
    """
    detect_smc_structures() must return a dict with key 'liquidity_clusters'
    (a list) and must not drop any pre-existing keys.
    """
    rows = uniform_bars(30, price=200.0)
    df = make_df(rows)
    result = detect_smc_structures(df)

    assert "liquidity_clusters" in result, \
        "'liquidity_clusters' key missing from detect_smc_structures output"
    assert isinstance(result["liquidity_clusters"], list)

    for key in ("fvg_bullish", "fvg_bearish", "choch_bull", "choch_bear",
                "displacement_bull", "displacement_bear",
                "liquidity_grab_bull", "liquidity_grab_bear",
                "order_blocks", "inducement"):
        assert key in result, f"Pre-existing key '{key}' dropped from result"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Swing-pool fractal near BUY entry → at_risk True, type swing_pool
# ─────────────────────────────────────────────────────────────────────────────

def test_buy_entry_on_swing_pool():
    """
    Build a clear fractal swing low at lo=195.0 (lookback=3):
      - 3 bars before and after have lo=197.5  (> 195.0 ✓)
    BUY entry at 196.0.
    ATR ≈ 2.1 (bars use body=2.0, wick=0.5 + the 197.5/195.0 neighbourhood).
    Distance = (196.0 - 195.0) / 2.1 ≈ 0.47 ATR  < proximity_atr=0.5 ✓.

    Flat-bar lows at ≈198.5 are ABOVE entry=196.0, so BUY filter skips them.
    """
    rows = uniform_bars(30, price=200.0)
    # Left wing: 3 bars with lo=197.5 (> fractal lo=195.0)
    for _ in range(3):
        rows.append((198.0, 199.5, 197.5, 199.0))
    # Fractal pivot: lo=195.0 (lower than all 3 bars on each side)
    rows.append((197.0, 198.0, 195.0, 197.5))          # bar 33
    # Right wing: 3 bars with lo=197.5
    for _ in range(3):
        rows.append((198.0, 199.5, 197.5, 199.0))
    # 5 quiet post-fractal bars so it is fully confirmed
    for _ in range(5):
        rows.append((199.0, 200.0, 198.5, 199.5))
    # Live bar (stripped)
    rows.append((199.5, 200.0, 199.0, 199.8))

    df = make_df(rows)
    result = assess_entry_liquidity_risk(df, entry_price=196.0, direction="BUY",
                                         proximity_atr=0.5)

    assert result["at_risk"] is True, \
        f"Expected at_risk=True for swing_pool near BUY, got: {result}"
    assert result["cluster_type"] == "swing_pool", \
        f"Expected cluster_type='swing_pool', got: {result['cluster_type']}"
    assert result["cluster_price"] < 196.0, \
        "swing_pool cluster must be below BUY entry"
    assert result["cluster_price"] == pytest.approx(195.0, abs=0.1)
