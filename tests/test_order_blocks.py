"""Unit tests for detect_order_blocks() — D1 True Order Block detection.

Synthetic OHLC frames are used so behaviour is fully deterministic.
ATR is deliberately set via candle geometry to make displacement thresholds
predictable without relying on floating-point EWM accumulation details.

Run:
    python3 -m pytest tests/test_order_blocks.py -q -p no:cacheprovider
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from smc_structure import detect_order_blocks


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_df(bars, has_volume=False):
    """
    bars = list of (open, high, low, close) or (open, high, low, close, vol).
    Returns a DataFrame with a simple integer index.
    """
    if has_volume:
        cols = ["open", "high", "low", "close", "volume"]
    else:
        cols = ["open", "high", "low", "close"]
    return pd.DataFrame(bars, columns=cols)


def flat_bars(n, price=100.0, body=0.5, wick=0.1):
    """Generate n quiet (small body) candles alternating bull/bear."""
    rows = []
    for i in range(n):
        if i % 2 == 0:  # bullish
            o, c = price - body / 2, price + body / 2
        else:            # bearish
            o, c = price + body / 2, price - body / 2
        rows.append((o, c + wick, c - wick, c))
    return rows


# ── Test 1: Bullish OB detected before upward displacement ────────────────────

def test_bullish_ob_detected():
    """
    Build:  20 quiet bars at price=100 (body~0.5, ATR~1.0)
    Then:   1 bearish candle (the OB candidate)
    Then:   1 bullish displacement candle (body = 8 > 2×ATR)
    Expect: exactly one OB with direction='bullish', zone spans the OB candle.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    # OB candle: bearish at bar 20
    ob_o, ob_c = 100.6, 99.8
    ob_h, ob_l = 100.8, 99.6
    rows.append((ob_o, ob_h, ob_l, ob_c))      # index 20, bearish
    # Displacement candle: bullish, body = 8 (>> 2×ATR ~1)
    rows.append((99.8, 108.2, 99.6, 107.8))    # index 21
    # Add 2 more quiet bars so displacement is not the live bar
    rows += flat_bars(3, price=108.0, body=0.5, wick=0.2)

    df = make_df(rows)
    obs = detect_order_blocks(df)

    assert len(obs) >= 1, "Expected at least one OB"
    bull_obs = [o for o in obs if o["direction"] == "bullish"]
    assert bull_obs, "Expected a bullish OB"

    ob = bull_obs[-1]   # most recently formed
    assert ob["zone_high"] == pytest.approx(ob_h, abs=1e-6)
    assert ob["zone_low"]  == pytest.approx(ob_l, abs=1e-6)
    assert ob["displacement_size_atr"] > 2.0


# ── Test 2: Bearish OB detected before downward displacement ─────────────────

def test_bearish_ob_detected():
    """
    20 quiet bars, then bullish OB candle, then bearish displacement.
    Expect: one OB with direction='bearish'.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    # OB candle: bullish at bar 20
    rows.append((99.5, 100.8, 99.3, 100.6))    # index 20, bullish
    # Bearish displacement: body = 9
    rows.append((100.6, 100.9, 91.2, 91.4))    # index 21, bearish
    rows += flat_bars(3, price=91.0, body=0.5, wick=0.2)

    df = make_df(rows)
    obs = detect_order_blocks(df)

    bear_obs = [o for o in obs if o["direction"] == "bearish"]
    assert bear_obs, "Expected a bearish OB"
    ob = bear_obs[-1]
    assert ob["zone_high"] == pytest.approx(100.8, abs=1e-6)
    assert ob["zone_low"]  == pytest.approx(99.3,  abs=1e-6)


# ── Test 3: fresh flips to False after price re-enters the zone ──────────────

def test_freshness_flips_after_reentry():
    """
    Same setup as test_bullish_ob_detected but add bars where price
    trades back into the OB zone.  fresh must be False.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    ob_o, ob_c = 100.6, 99.8
    ob_h, ob_l = 100.8, 99.6
    rows.append((ob_o, ob_h, ob_l, ob_c))      # bearish OB
    rows.append((99.8, 108.2, 99.6, 107.8))    # bull displacement
    rows += flat_bars(3, price=108.0, body=0.5, wick=0.2)
    # Bar that trades INTO the OB zone: lo touches below ob_h
    rows.append((105.0, 105.5, 99.7, 100.0))   # lo=99.7, zone [99.6, 100.8]
    rows += flat_bars(2, price=100.0, body=0.3, wick=0.1)

    df = make_df(rows)
    obs = detect_order_blocks(df)

    bull_obs = [o for o in obs if o["direction"] == "bullish"]
    assert bull_obs, "Expected bullish OB"
    ob = bull_obs[-1]
    assert ob["fresh"] is False, "OB should not be fresh after price re-enters zone"
    assert ob["times_tested"] >= 1


# ── Test 4: mitigated flag after full trade-through ──────────────────────────

def test_mitigated_after_full_tradethrough():
    """
    After the OB zone is established, add a bar whose high > zone_high AND
    low < zone_low — a full through-trade.  mitigated must be True.
    """
    rows = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    ob_h, ob_l = 100.8, 99.6
    rows.append((100.6, ob_h, ob_l, 99.8))     # bearish OB (index 20)
    rows.append((99.8, 108.2, 99.6, 107.8))    # bull displacement (index 21)
    rows += flat_bars(2, price=108.0, body=0.5, wick=0.2)
    # Through-trade bar: high > ob_h AND low < ob_l
    rows.append((100.5, 101.2, 99.2, 100.0))   # hi=101.2>100.8, lo=99.2<99.6
    rows += flat_bars(2, price=100.0, body=0.3, wick=0.1)

    df = make_df(rows)
    obs = detect_order_blocks(df)

    bull_obs = [o for o in obs if o["direction"] == "bullish"]
    assert bull_obs, "Expected bullish OB"
    ob = bull_obs[-1]
    assert ob["mitigated"] is True, "OB should be mitigated after full through-trade"


# ── Test 5: no OB when no displacement ───────────────────────────────────────

def test_no_ob_when_no_displacement():
    """
    Only quiet candles — no displacement.  Result must be empty list.
    """
    rows = flat_bars(40, price=100.0, body=0.5, wick=0.2)
    df = make_df(rows)
    obs = detect_order_blocks(df)
    assert obs == [], f"Expected empty list, got {obs}"


# ── Test 6: volume_at_formation present when vol column exists ────────────────

def test_volume_at_formation_populated():
    """
    Same as test 1 but with a volume column.
    volume_at_formation must be a float matching the OB candle's volume.
    """
    rows_base = flat_bars(20, price=100.0, body=0.5, wick=0.3)
    rows = [(o, h, l, c, 1000.0) for o, h, l, c in rows_base]
    ob_vol = 5500.0
    rows.append((100.6, 100.8, 99.6, 99.8, ob_vol))   # bearish OB
    rows.append((99.8, 108.2, 99.6, 107.8, 3000.0))   # bull displacement
    for o, h, l, c in flat_bars(3, price=108.0, body=0.5, wick=0.2):
        rows.append((o, h, l, c, 2000.0))

    df = make_df(rows, has_volume=True)
    obs = detect_order_blocks(df)

    bull_obs = [o for o in obs if o["direction"] == "bullish"]
    assert bull_obs, "Expected bullish OB"
    ob = bull_obs[-1]
    assert ob["volume_at_formation"] == pytest.approx(ob_vol, abs=0.01)


# ── Test 7: detect_smc_structures includes order_blocks key ──────────────────

def test_smc_structures_has_order_blocks_key():
    """
    detect_smc_structures() must return a dict containing key 'order_blocks'
    (a list) without raising and without removing any pre-existing key.
    """
    from smc_structure import detect_smc_structures

    rows = flat_bars(30, price=100.0, body=0.5, wick=0.3)
    df = make_df(rows)
    result = detect_smc_structures(df)

    assert "order_blocks" in result, "'order_blocks' key missing from detect_smc_structures output"
    assert isinstance(result["order_blocks"], list)
    # Existing keys must still be present
    for key in ("fvg_bullish", "fvg_bearish", "choch_bull", "choch_bear",
                "displacement_bull", "displacement_bear",
                "liquidity_grab_bull", "liquidity_grab_bear"):
        assert key in result, f"Existing key '{key}' dropped from result"


# ── Test 8: too-short df returns empty list ───────────────────────────────────

def test_short_df_returns_empty():
    rows = flat_bars(10, price=100.0)
    df = make_df(rows)
    obs = detect_order_blocks(df)
    assert obs == []
