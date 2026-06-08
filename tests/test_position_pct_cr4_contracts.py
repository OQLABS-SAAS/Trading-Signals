"""CR-4 regression tests: position_pct must NOT be entry / stop_distance.

The old computation was:
    risk = abs(entry - stop_loss)                        # stop distance, price units
    position_pct = round(min(entry / risk, 100.0), 1)   # dimensionally wrong

entry / risk is a leverage-style ratio (price / stop-distance), not a portfolio
percentage. get_analysis() has no account balance so it cannot compute a real
risk-based position size. The field is tombstoned to None (CR-4 fix).

These tests:
  1. Assert position_pct is always None in the get_analysis return value.
  2. Assert it is never equal to round(entry / abs(entry-stop_loss), 1) for
     concrete BUY and SELL cases — the specific wrong formula must never reappear.
  3. Assert the key is present in the response dict (tombstone, not absent) so
     callers receive a graceful null rather than a KeyError.
  4. Assert the frontend HTML no longer assigns positionPct from data.position_pct.
"""

import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp  # noqa: E402

HTML = Path("static/index-v2-prototype.html").read_text()

# ---------------------------------------------------------------------------
# VIX stub — NORMAL zone, no network call
# ---------------------------------------------------------------------------
_VIX_NORMAL = {"vix": 16.0, "zone": "NORMAL", "badge": None,
               "context_text": "", "is_stale": False}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ind(price: float = 1.0850, atr: float = 0.0020, **overrides) -> dict:
    """Minimal indicator dict accepted by get_analysis."""
    base = {
        "price": price,
        "rsi": 45.0,
        "ema_fast": price * 0.999,
        "ema_slow": price * 0.998,
        "ema_200": price * 0.995,
        "ema_trend": "BULLISH",
        "macd": 0.0001,
        "macd_signal": 0.00005,
        "macd_hist": 0.00005,
        "bb_pos": 0.5,
        "bb_width": 0.01,
        "atr": atr,
        "vol_ratio": 1.1,
        "supertrend": "BULLISH",
        "adx": {"trend_strength": "STRONG", "adx": 28.0},
        "price_change_pct": 0.1,
        "rsi_divergence": {"type": "none"},
        "chart_prices": [price] * 60,
        "chart_highs":  [price * 1.001] * 60,
        "chart_lows":   [price * 0.999] * 60,
        "chart_rsi":    [45.0] * 60,
    }
    base.update(overrides)
    return base


def _run(ticker="EURUSD", asset_type="forex", timeframe="1h", **ind_overrides) -> dict:
    """Call get_analysis with VIX and spread mocked to avoid network I/O."""
    ind = _make_ind(**ind_overrides)
    with patch.object(dvapp, "_get_vix_score", return_value=_VIX_NORMAL), \
         patch.object(dvapp, "_get_spread", return_value=(0.0001, "table", "fair")):
        # Signature: get_analysis(ticker, asset_type, ind, timeframe, ...)
        return dvapp.get_analysis(ticker, asset_type, ind, timeframe)


# ---------------------------------------------------------------------------
# Core: position_pct is always None
# ---------------------------------------------------------------------------

class TestPositionPctIsAlwaysNone:

    def test_buy_signal_position_pct_is_none(self):
        """BUY path: position_pct must be None after CR-4 fix."""
        result = _run(rsi=40.0, ema_trend="BULLISH", macd_hist=0.0002,
                      supertrend="BULLISH")
        assert "position_pct" in result, "position_pct key must exist (tombstone)"
        assert result["position_pct"] is None, (
            f"position_pct should be None, got {result['position_pct']!r}"
        )

    def test_sell_signal_position_pct_is_none(self):
        """SELL path: position_pct must be None after CR-4 fix."""
        result = _run(
            rsi=74.0,
            ema_trend="BEARISH",
            macd_hist=-0.0002,
            supertrend="BEARISH",
        )
        assert "position_pct" in result
        assert result["position_pct"] is None, (
            f"position_pct should be None, got {result['position_pct']!r}"
        )

    def test_hold_signal_position_pct_is_none(self):
        """HOLD path: position_pct must be None."""
        result = _run(rsi=52.0, ema_trend="MIXED")
        assert "position_pct" in result
        assert result["position_pct"] is None

    def test_zero_atr_position_pct_is_none(self):
        """Zero ATR skips trade-level block entirely — position_pct still None."""
        result = _run(atr=0.0)
        assert result["position_pct"] is None

    def test_key_always_present_on_hold(self):
        """position_pct key must be present even on HOLD (no KeyError for callers)."""
        result = _run(rsi=52.0, ema_trend="MIXED")
        assert "position_pct" in result  # tombstone, not absent


# ---------------------------------------------------------------------------
# Anti-regression: the forbidden formula must never reappear
# ---------------------------------------------------------------------------

class TestForbiddenFormulaNeverReturned:
    """position_pct must not equal round(min(entry/risk, 100), 1) for any signal."""

    def _assert_not_old_formula(self, result: dict, label: str):
        """If trade levels are present, confirm position_pct != old wrong value."""
        entry = result.get("entry")
        sl    = result.get("stop_loss")
        if entry is None or sl is None:
            return  # no trade levels — can't compute old formula; skip
        risk = abs(entry - sl)
        if risk == 0:
            return
        old_wrong_value = round(min(entry / risk, 100.0), 1)
        assert result["position_pct"] != old_wrong_value, (
            f"[{label}] position_pct={result['position_pct']!r} equals the "
            f"banned entry/stop_distance formula ({entry}/{risk:.6f} = "
            f"{old_wrong_value!r}). CR-4 regression."
        )

    def test_forex_buy_not_entry_over_risk(self):
        """
        EURUSD BUY — concrete numbers:
          price=1.0850, atr=0.0020, sl_mult≈4 (1H day-trade profile)
          stop_loss ≈ 1.0850 - 4*0.002 = 1.077
          risk = 0.008 → old_formula = min(1.085/0.008, 100) = 100.0
        """
        result = _run(price=1.0850, atr=0.0020,
                      rsi=40.0, ema_trend="BULLISH",
                      macd_hist=0.0002, supertrend="BULLISH")
        self._assert_not_old_formula(result, "EURUSD-BUY")

    def test_stock_sell_not_entry_over_risk(self):
        """
        AAPL SELL — concrete numbers:
          price=150.25, atr=0.80, sl_mult≈4
          stop_loss ≈ 153.45  →  risk = 3.20
          old_formula = round(min(150.25/3.20, 100), 1) = 46.9
        """
        result = _run(
            ticker="AAPL", asset_type="stock", timeframe="1h",
            price=150.25, atr=0.80,
            rsi=74.0, ema_trend="BEARISH",
            macd_hist=-0.05, supertrend="BEARISH",
        )
        self._assert_not_old_formula(result, "AAPL-SELL")

    def test_crypto_buy_not_entry_over_risk(self):
        """
        BTC-like BUY — high price amplifies the ratio even more:
          price=68000, atr=800
          risk ≈ 4*800 = 3200
          old_formula = min(68000/3200, 100) = 21.25
        """
        result = _run(
            ticker="BTC-USD", asset_type="crypto", timeframe="4h",
            price=68000.0, atr=800.0,
            rsi=40.0, ema_trend="BULLISH",
            macd_hist=50.0, supertrend="BULLISH",
        )
        self._assert_not_old_formula(result, "BTC-BUY")


# ---------------------------------------------------------------------------
# Frontend contracts
# ---------------------------------------------------------------------------

class TestPositionPctFrontend:

    def test_positionPct_assignment_removed_from_state_object(self):
        """The frontend state object must not propagate the misleading field."""
        assert "positionPct:data.position_pct" not in HTML, (
            "Frontend still assigns positionPct from data.position_pct — "
            "CR-4 fix requires this assignment to be removed."
        )

    def test_positionPct_not_in_live_js_code(self):
        """positionPct must not appear in live JS (comments are OK)."""
        non_comment_lines = [
            line.strip()
            for line in HTML.splitlines()
            if "positionPct" in line and not line.strip().startswith("//")
        ]
        assert non_comment_lines == [], (
            f"positionPct still referenced outside a comment: {non_comment_lines}"
        )
