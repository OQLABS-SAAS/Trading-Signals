"""Direction-integrity tests for the signal engine.

Covers two live bugs that could make a SELL fire into an up-move:
  1. Repaint — structure (FVG/displacement/liquidity/CHoCH) was read from the
     live, still-forming candle, so an unconfirmed pattern could spike confidence
     and then vanish. Fix: structure is read only from CONFIRMED (closed) bars.
"""
import pandas as pd
from app import detect_smc_structures


def _flat(n=25, price=100.0):
    return {
        "open":  [price] * n,
        "high":  [price + 0.5] * n,
        "low":   [price - 0.5] * n,
        "close": [price] * n,
    }


def test_repaint_live_candle_structure_excluded():
    """A big displacement candle on the LAST (forming) bar must NOT be reported —
    it isn't confirmed yet and would repaint away on the next tick."""
    d = _flat()
    # spike only on the final, still-forming bar
    d["open"][-1] = 100.0
    d["close"][-1] = 115.0
    d["high"][-1] = 115.5
    d["low"][-1] = 99.9
    r = detect_smc_structures(pd.DataFrame(d))
    assert r["displacement_bull"] is False, "forming-bar structure must be ignored (anti-repaint)"


def test_confirmed_candle_structure_detected():
    """The same displacement on a CONFIRMED (already-closed) bar MUST still be
    reported — the fix excludes only the live bar, not real structure."""
    d = _flat()
    i = len(d["open"]) - 2  # second-to-last: confirmed, survives the live-bar trim
    d["open"][i] = 100.0
    d["close"][i] = 115.0
    d["high"][i] = 115.5
    d["low"][i] = 99.9
    r = detect_smc_structures(pd.DataFrame(d))
    assert r["displacement_bull"] is True, "confirmed-bar structure must still be detected"
