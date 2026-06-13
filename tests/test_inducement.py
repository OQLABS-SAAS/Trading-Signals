"""Unit tests for detect_inducement() — D2 IDM/Inducement detection.

Synthetic OHLC frames are constructed so that geometry is fully
deterministic and independent of floating-point EWM accumulation.

Covered scenarios
-----------------
1. Minor opposing swing between price and a bullish OB → detected, unswept.
2. Price sweeps the IDM level  → swept=True.
3. No fresh OB → no inducement emitted.
4. Equal-lows cluster detected as 'equal_hl' type.
5. detect_smc_structures() output contains 'inducement' key (list).
6. Short df (<20 bars) returns empty list.
7. Bearish OB: equal-highs IDM between price and supply zone.

Run:
    python3 -m pytest tests/test_inducement.py -q -p no:cacheprovider
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smc_structure import detect_inducement, detect_order_blocks


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_df(bars):
    """bars = list of (open, high, low, close)."""
    return pd.DataFrame(bars, columns=["open", "high", "low", "close"])


def flat_bars(n, price=100.0, body=0.5, wick=0.1):
    """Generate n quiet candles alternating bull/bear."""
    rows = []
    for i in range(n):
        if i % 2 == 0:
            o, c = price - body / 2, price + body / 2
        else:
            o, c = price + body / 2, price - body / 2
        rows.append((o, c + wick, c - wick, c))
    return rows


def build_bullish_ob_frame():
    """
    Returns (df, atr_approx) for a frame that has:
      - 20 quiet bars at price=100 (ATR ≈ 1.0)
      - 1 bearish OB candle at bar 20 (zone [99.6, 100.8])
      - 1 bullish displacement at bar 21 (body=8)
      - 8 quiet bars at price ≈ 108
    Price ends near 108, OB zone is at 99.6–100.8.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    # Bearish OB candle
    rows.append((100.6, 100.8, 99.6, 99.8))   # bar 20
    # Bullish displacement (body=8 >> 2×ATR≈1)
    rows.append((99.8, 108.2, 99.6, 107.8))   # bar 21
    # 8 quiet bars at 108
    rows += flat_bars(8, price=108.0, body=0.5, wick=0.2)
    return make_df(rows), 1.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: minor_swing IDM between price and bullish OB — detected, unswept
# ─────────────────────────────────────────────────────────────────────────────

def test_minor_swing_idm_detected_unswept():
    """
    After the bullish OB (zone ≈ 99.6–100.8), price rallied to ~108.
    We insert a minor swing LOW at ~103 (between zone_high=100.8 and price=108).
    The IDM should be detected, side='low', swept=False.

    Bar layout (after the 8 quiet bars at 108):
      bar 30: swing low at 103 (lo[30] < lo[29] and lo[30] < lo[31])
      bars 31-33: quiet bars above 103
    Then the live bar (index 34) is stripped.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    rows.append((100.6, 100.8, 99.6, 99.8))   # bar 20 — bearish OB
    rows.append((99.8,  108.2, 99.6, 107.8))  # bar 21 — bull displacement
    # 8 quiet bars at 108 (bars 22-29)
    rows += flat_bars(8, price=108.0, body=0.5, wick=0.2)
    # Minor swing low at bar 30: lo=103.0 — lower than neighbours
    rows.append((106.0, 107.0, 103.0, 106.5))  # bar 30
    # 3 bars above 103 so bar 30 qualifies as a local fractal
    rows += flat_bars(3, price=107.0, body=0.3, wick=0.2)   # bars 31-33
    # Live bar (will be stripped)
    rows.append((107.0, 107.5, 106.5, 107.2))              # bar 34

    df = make_df(rows)
    obs = detect_order_blocks(df)
    idms = detect_inducement(df, order_blocks=obs)

    # At least one IDM for the bullish OB
    bull_idms = [x for x in idms if x["ob_direction"] == "bullish"]
    assert bull_idms, f"Expected bullish IDM, got: {idms}"

    idm = bull_idms[0]
    assert idm["side"] == "low", f"Expected side='low', got {idm['side']}"
    assert idm["swept"] is False, "IDM should not be swept yet"
    assert idm["idm_type"] == "minor_swing"
    # IDM price should be at or near 103.0
    assert 102.5 <= idm["idm_price"] <= 103.5, f"IDM price unexpected: {idm['idm_price']}"
    # distance_atr > 0
    assert idm["distance_atr"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: price sweeps the IDM → swept=True
# ─────────────────────────────────────────────────────────────────────────────

def test_minor_swing_idm_swept():
    """
    Same layout as test 1 but after the minor swing low at bar 30,
    we add a bar whose low dips BELOW 103 (sweeping it), then price recovers.
    The IDM must be swept=True.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    rows.append((100.6, 100.8, 99.6, 99.8))   # bar 20 — bearish OB
    rows.append((99.8,  108.2, 99.6, 107.8))  # bar 21 — bull displacement
    rows += flat_bars(8, price=108.0, body=0.5, wick=0.2)  # bars 22-29
    # Minor swing low at bar 30
    rows.append((106.0, 107.0, 103.0, 106.5))  # bar 30
    # Two bars that keep lo > 103 so the fractal is confirmed
    rows += flat_bars(2, price=107.0, body=0.3, wick=0.2)  # bars 31-32
    # Sweep bar: lo dips to 102.5 (below IDM level 103.0)
    rows.append((106.5, 107.0, 102.5, 105.5))  # bar 33 — sweep
    # 1 more quiet bar so the sweep bar is not the live bar
    rows.append((105.5, 106.0, 105.0, 105.8))  # bar 34
    # Live bar
    rows.append((105.8, 106.2, 105.5, 106.0))  # bar 35

    df = make_df(rows)
    obs = detect_order_blocks(df)
    idms = detect_inducement(df, order_blocks=obs)

    bull_idms = [x for x in idms if x["ob_direction"] == "bullish" and x["side"] == "low"]
    assert bull_idms, f"Expected bullish IDM on low side, got: {idms}"
    idm = bull_idms[0]
    assert idm["swept"] is True, f"IDM should be swept, got swept={idm['swept']}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: no fresh OB → no inducement
# ─────────────────────────────────────────────────────────────────────────────

def test_no_ob_no_inducement():
    """
    Only quiet candles — no displacement, hence no OBs.
    detect_inducement must return an empty list.
    """
    rows = flat_bars(40, price=100.0, body=0.5, wick=0.2)
    df = make_df(rows)
    # Explicitly pass empty OB list
    idms = detect_inducement(df, order_blocks=[])
    assert idms == [], f"Expected empty list, got {idms}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: equal-lows cluster detected as 'equal_hl'
# ─────────────────────────────────────────────────────────────────────────────

def test_equal_lows_cluster_detected_as_equal_hl():
    """
    After a bullish OB (zone ≈ 99.6–100.8), price is above at ~108.
    We insert two bars with nearly identical lows (~104) that do NOT form
    local fractal minima — their neighbours have even lower lows, so the
    bars don't qualify as minor swing lows.  Only the equal-hl detector
    should fire.

    Geometry: surround the equal-low bars with bars that have lows of ~102
    (lower than 104), so bar 28 and 29 have lo=104 but are flanked by bars
    with lo=102 — they are NOT local minima, they are just two equal-high-low
    plateaus.  The equal-hl detector looks at rolling window min-clustering,
    not the fractal condition, so it still fires on the 104 cluster.

    NOTE: in real markets equal-lows that are not local fractals are common —
    e.g. two wicks that touch the same support level without being the lowest
    point in their neighbourhood.  We use the ATR tolerance (0.1×ATR) to
    catch them.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    rows.append((100.6, 100.8, 99.6, 99.8))   # bar 20 — bearish OB
    rows.append((99.8,  108.2, 99.6, 107.8))  # bar 21 — bull displacement
    # bars 22-27: some bars with lo ~102 (below the planned equal-low cluster)
    for _ in range(6):
        rows.append((107.0, 108.5, 102.0, 107.5))   # bars 22-27, lo=102
    # Equal-lows cluster: bars 28 and 29 have lo=104.0 and lo=104.05
    # Their neighbours (bars 27 and 30) have lo=102 → they are NOT local minima
    rows.append((107.0, 108.0, 104.00, 107.5))  # bar 28
    rows.append((107.0, 108.0, 104.05, 107.5))  # bar 29
    # bar 30: lo=102 again (below 104) — ensures bars 28/29 are not fractals
    rows.append((107.0, 108.5, 102.0, 107.5))   # bar 30
    # 4 quiet bars at 108 so bar 30 is confirmed
    rows += flat_bars(4, price=107.5, body=0.3, wick=0.15)  # bars 31-34
    # Live bar
    rows.append((107.5, 108.0, 107.0, 107.8))              # bar 35

    df = make_df(rows)
    obs = detect_order_blocks(df)
    idms = detect_inducement(df, order_blocks=obs)

    # The 104 level must appear as equal_hl (no minor_swing at 104 should exist)
    minor_at_104 = [x for x in idms
                    if x["idm_type"] == "minor_swing"
                    and abs(x["idm_price"] - 104.0) < 0.5]
    assert not minor_at_104, f"104 level should NOT be a minor_swing: {minor_at_104}"

    eq_hl_idms = [x for x in idms if x["idm_type"] == "equal_hl" and x["ob_direction"] == "bullish"]
    assert eq_hl_idms, f"Expected equal_hl IDM for bullish OB, got: {idms}"
    idm = eq_hl_idms[0]
    assert idm["side"] == "low"
    # Level should be near 104
    assert 103.5 <= idm["idm_price"] <= 104.6, f"IDM price unexpected: {idm['idm_price']}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: detect_smc_structures includes 'inducement' key
# ─────────────────────────────────────────────────────────────────────────────

def test_smc_structures_has_inducement_key():
    """
    detect_smc_structures() must return a dict with key 'inducement' (a list)
    and must not drop any existing keys.
    """
    from smc_structure import detect_smc_structures

    rows = flat_bars(30, price=100.0, body=0.5, wick=0.3)
    df = make_df(rows)
    result = detect_smc_structures(df)

    assert "inducement" in result, "'inducement' key missing from detect_smc_structures output"
    assert isinstance(result["inducement"], list)

    # All pre-existing keys must still be present
    for key in ("fvg_bullish", "fvg_bearish", "choch_bull", "choch_bear",
                "displacement_bull", "displacement_bear",
                "liquidity_grab_bull", "liquidity_grab_bear",
                "order_blocks"):
        assert key in result, f"Existing key '{key}' dropped from result"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: short df returns empty list
# ─────────────────────────────────────────────────────────────────────────────

def test_short_df_returns_empty():
    rows = flat_bars(15, price=100.0)
    df = make_df(rows)
    idms = detect_inducement(df)
    assert idms == [], f"Expected empty list for short df, got {idms}"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: bearish OB — equal-highs IDM between price and supply zone
# ─────────────────────────────────────────────────────────────────────────────

def test_bearish_ob_equal_highs_idm():
    """
    Build a bearish OB (supply zone above) scenario:
      - 20 quiet bars at price=100
      - Bullish OB candle at bar 20 (zone [99.3, 100.8])
      - Bearish displacement at bar 21 (body=9, close=91.4)
      - Price now below OB, OB direction='bearish'
      - Equal-highs cluster at ~95 that are NOT local fractal maxima
        (neighbours have hi=97 > 95, so bars with hi=95 are not local maxima)
      - The equal_hl detector should fire on the 95 cluster

    We use the same geometry trick as test 4: surround the equal-high bars
    with bars that have even higher highs (97), so the 95 bars are NOT local
    fractals but ARE an equal-highs cluster within 0.1×ATR tolerance.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    rows.append((99.5, 100.8, 99.3, 100.6))   # bar 20 — bullish OB
    rows.append((100.6, 100.9, 91.2, 91.4))   # bar 21 — bearish displacement
    # bars 22-27: bars with hi=97 (above the planned equal-high cluster at 95)
    for _ in range(6):
        rows.append((92.0, 97.0, 91.0, 92.5))   # hi=97 > 95
    # Equal-highs cluster: bars 28 and 29 have hi=95.00 and hi=95.05
    # Their neighbours (bars 27 and 30) have hi=97 → bars 28/29 are NOT fractals
    rows.append((92.0, 95.00, 91.5, 92.5))    # bar 28, hi=95.00
    rows.append((92.0, 95.05, 91.5, 92.5))    # bar 29, hi=95.05
    # bar 30: hi=97 again
    rows.append((92.0, 97.0, 91.0, 92.5))     # bar 30
    # 4 quiet bars at 92 (below 95) so bar 30 is confirmed
    rows += flat_bars(4, price=92.0, body=0.3, wick=0.1)   # bars 31-34
    # Live bar
    rows.append((92.0, 92.5, 91.5, 92.2))                  # bar 35

    df = make_df(rows)
    obs = detect_order_blocks(df)
    idms = detect_inducement(df, order_blocks=obs)

    # No minor_swing at 95 (neighbours are higher)
    minor_at_95 = [x for x in idms
                   if x["idm_type"] == "minor_swing"
                   and abs(x["idm_price"] - 95.0) < 0.5]
    assert not minor_at_95, f"95 level should NOT be a minor_swing: {minor_at_95}"

    bear_idms = [x for x in idms if x["ob_direction"] == "bearish" and x["idm_type"] == "equal_hl"]
    assert bear_idms, f"Expected bearish equal_hl IDM, got: {idms}"
    idm = bear_idms[0]
    assert idm["side"] == "high"
    # Level should be near 95
    assert 94.5 <= idm["idm_price"] <= 95.6, f"IDM price unexpected: {idm['idm_price']}"
