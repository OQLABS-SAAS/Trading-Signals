"""CR-5 regression tests: SL/TP/sizing must use current Wilder ATR(14), not 100-bar mean.

The old computation was:
    atr_smooth = atr_raw.rolling(100, min_periods=14).mean()
    atr        = float(atr_smooth.iloc[-1])

This produced ATR averaged over ~114 bars.  In a volatility spike the smoothed
value is far below current true range, so stops are placed inside noise (instant
hit).  In calm markets after a spike the smoothed value is elevated, making TPs
unreachable.

CR-5 fix:
    atr = float(atr_raw.iloc[-1])   # current Wilder ATR(14)

Regime detection (_atr50_mean / _regime_ratio) uses atr_raw directly and is
left entirely unchanged.

These tests verify:
  1. On a SPIKE series, calculate_indicators returns an atr > the 100-bar
     smoothed mean — i.e. current volatility, not blurred history.
  2. On the SPIKE series, the returned atr equals the direct Wilder ATR(14)
     last value (within 0.1% tolerance).
  3. Regime detection is unaffected: atr_regime correctly identifies the spike
     series as TRENDING (current ATR >> 50-bar mean).
  4. On a SHORT series (fewer than 100 bars), atr is never NaN or zero.
  5. On a flat 15-bar series (too short for rma to converge on 14 bars), the
     NaN fallback kicks in and still returns a positive float.
"""

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp  # noqa: E402


# ---------------------------------------------------------------------------
# Helper — synthetic OHLCV DataFrame
# ---------------------------------------------------------------------------

def _make_df(closes, spread_pct: float = 0.002, volume: int = 1_000_000) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame from a close price array.

    High = close * (1 + spread_pct), Low = close * (1 - spread_pct).
    Open = previous close (or close for bar 0).
    Volume is constant.
    """
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = closes * (1 + spread_pct)
    lows  = closes * (1 - spread_pct)
    idx   = pd.date_range("2024-01-01", periods=n, freq="1h")
    return pd.DataFrame({
        "Open":   opens,
        "High":   highs,
        "Low":    lows,
        "Close":  closes,
        "Volume": float(volume),
    }, index=idx)


def _spike_series(n_calm: int = 120, spike_mult: float = 8.0) -> np.ndarray:
    """Return a close price array that is calm for n_calm bars then spikes.

    The spike is simulated by dramatically widening High/Low on the last few
    bars — achieved here by giving those bars a much larger spread in the
    DataFrame helper, but for simplicity we embed the spike directly in the
    close series with large up/down swings at the tail.

    Specifically: the last 5 bars have close movements 8× the baseline
    bar-to-bar change so True Range expands significantly.
    """
    rng = np.random.default_rng(42)
    # Baseline: small random walk
    baseline_step = 0.50   # ~0.05% per bar on a ~1000-priced asset
    closes = 1000.0 + np.cumsum(rng.uniform(-baseline_step, baseline_step, n_calm))

    # Spike tail: 5 bars with much larger moves
    spike_step = baseline_step * spike_mult
    tail = closes[-1] + np.cumsum(rng.uniform(-spike_step, spike_step, 5))
    return np.concatenate([closes, tail])


def _spike_df(n_calm: int = 120, spike_mult: float = 8.0) -> pd.DataFrame:
    """Build a DataFrame whose tail bars have dramatically elevated True Range."""
    closes = _spike_series(n_calm, spike_mult)
    n = len(closes)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    highs = closes.copy()
    lows  = closes.copy()
    rng = np.random.default_rng(99)

    # Calm bars: ±0.1% spread
    calm_spread = closes * 0.001
    highs[:n_calm] = closes[:n_calm] + calm_spread[:n_calm]
    lows[:n_calm]  = closes[:n_calm] - calm_spread[:n_calm]

    # Spike bars: ±2% spread so True Range is large
    spike_spread = closes[n_calm:] * 0.02
    highs[n_calm:] = closes[n_calm:] + spike_spread
    lows[n_calm:]  = closes[n_calm:] - spike_spread

    idx = pd.date_range("2024-01-01", periods=n, freq="1h")
    return pd.DataFrame({
        "Open":   opens,
        "High":   highs,
        "Low":    lows,
        "Close":  closes,
        "Volume": 1_000_000.0,
    }, index=idx)


# ---------------------------------------------------------------------------
# Reference helpers — compute values directly to compare against
# ---------------------------------------------------------------------------

def _wilder_atr_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Reproduce dvapp.rma(tr, period) to get the reference ATR series."""
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return dvapp.rma(tr, period)


def _smoothed_atr(df: pd.DataFrame, period: int = 14, window: int = 100) -> float:
    """Old formula: Wilder ATR(14) rolled over `window`-bar mean."""
    atr_raw = _wilder_atr_series(df, period)
    return float(atr_raw.rolling(window, min_periods=period).mean().iloc[-1])


def _current_wilder_atr(df: pd.DataFrame, period: int = 14) -> float:
    """New formula: last value of Wilder ATR(14)."""
    return float(_wilder_atr_series(df, period).iloc[-1])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCR5AtrSpikeTracking:
    """CR-5 contract: atr must equal current Wilder ATR(14), not 100-bar mean."""

    def setup_method(self):
        self.df    = _spike_df()
        self.ind   = dvapp.calculate_indicators(self.df, timeframe="1h", asset_type="stock")
        self.atr_returned   = self.ind["atr"]
        self.atr_smoothed   = _smoothed_atr(self.df)
        self.atr_current    = _current_wilder_atr(self.df)

    def test_current_atr_exceeds_smoothed_on_spike(self):
        """On a spike series current ATR14 must be meaningfully > 100-bar mean.

        This is the core property of the bug: the old formula returned the smoothed
        (blurred) value.  After the fix, returned ATR reflects the elevated recent TR.
        """
        assert self.atr_current > self.atr_smoothed, (
            f"Expected current ATR ({self.atr_current:.6f}) > "
            f"smoothed ATR ({self.atr_smoothed:.6f}) on spike series — "
            "spike must lift current ATR above the long-run mean."
        )

    def test_returned_atr_equals_current_not_smoothed(self):
        """calculate_indicators must return current Wilder ATR(14), not the 100-bar mean.

        Tolerance: 0.1% (floating-point rounding only — both paths read the same series).
        """
        tol = self.atr_current * 0.001
        assert abs(self.atr_returned - self.atr_current) <= tol, (
            f"atr returned by calculate_indicators ({self.atr_returned:.6f}) "
            f"does not match current Wilder ATR14 ({self.atr_current:.6f}). "
            f"diff={abs(self.atr_returned - self.atr_current):.8f}, tol={tol:.8f}"
        )

    def test_returned_atr_is_not_smoothed_value(self):
        """Returned atr must NOT be (or very close to) the old 100-bar smooth mean."""
        if np.isnan(self.atr_smoothed):
            pytest.skip("atr_smooth is NaN on this series — old path was also NaN")
        # If they are equal within 0.1% it means the fix wasn't applied
        old_formula_match = abs(self.atr_returned - self.atr_smoothed) <= self.atr_smoothed * 0.001
        assert not old_formula_match, (
            f"atr returned ({self.atr_returned:.6f}) equals the old 100-bar "
            f"smoothed value ({self.atr_smoothed:.6f}) — CR-5 fix not applied."
        )

    def test_spike_atr_is_at_least_2x_smoothed(self):
        """Sanity: the spike series is designed so current ATR is >> smoothed mean.

        This confirms the test data is actually adversarial enough to catch the bug.
        """
        ratio = self.atr_current / self.atr_smoothed if self.atr_smoothed > 0 else 0
        assert ratio >= 2.0, (
            f"Spike series not adversarial enough: current/smoothed = {ratio:.2f}. "
            "Spike spreads should be much larger than calm spreads."
        )

    def test_returned_atr_is_positive_finite(self):
        """atr must never be NaN, inf, or zero — any of which collapses SL/TP."""
        assert np.isfinite(self.atr_returned), f"atr is not finite: {self.atr_returned}"
        assert self.atr_returned > 0, f"atr is zero or negative: {self.atr_returned}"


class TestCR5RegimeDetectionUnchanged:
    """Regime detection (_atr50_mean / _regime_ratio) uses atr_raw directly.

    CR-5 must not alter this behaviour.  On the spike series the current ATR
    is >> its 50-bar mean so regime should be TRENDING.
    """

    def setup_method(self):
        self.df  = _spike_df()
        self.ind = dvapp.calculate_indicators(self.df, timeframe="1h", asset_type="stock")

    def test_regime_is_trending_on_spike(self):
        """When current ATR >> 50-bar ATR mean, regime must be TRENDING.

        Regime formula: _regime_ratio = atr_raw[-1] / atr_raw.rolling(50).mean()[-1]
        On our spike series current ATR is ~10× the 50-bar mean → ratio > 1.30 → TRENDING.
        """
        regime = self.ind.get("atr_regime")
        assert regime == "TRENDING", (
            f"Expected atr_regime=TRENDING on spike series, got {regime!r}. "
            "Regime detection may have been broken by the CR-5 change."
        )

    def test_regime_key_always_present(self):
        """atr_regime must always be returned — never absent or None."""
        assert "atr_regime" in self.ind
        assert self.ind["atr_regime"] in ("RANGING", "NORMAL", "TRENDING"), (
            f"Unexpected atr_regime value: {self.ind['atr_regime']!r}"
        )

    def test_calm_series_regime_is_normal(self):
        """On a flat-volatility series, regime should be NORMAL (current ~ mean)."""
        # Uniform close prices → TR ≈ constant → ratio ≈ 1.0 → NORMAL
        # Use enough bars so the 50-bar mean has converged.
        closes = np.full(200, 1000.0)
        df_calm = _make_df(closes, spread_pct=0.001)
        ind_calm = dvapp.calculate_indicators(df_calm, timeframe="1h", asset_type="stock")
        # Constant TR → ratio = 1.0 exactly → NORMAL
        assert ind_calm["atr_regime"] == "NORMAL", (
            f"Expected NORMAL on flat series, got {ind_calm['atr_regime']!r}"
        )


class TestCR5NaNGuardShortSeries:
    """atr must never be NaN or zero even on very short price series.

    NOTE: calculate_indicators requires >= ~20 bars to survive the full
    pipeline (vol_avg rolls over 20 bars; fewer bars → NaN → int() crash).
    That is a pre-existing limitation unrelated to ATR.  For sub-20-bar
    cases we test the CR-5 NaN-guard logic directly via rma + the guard
    code rather than routing through the full function.
    """

    def _apply_atr_guard(self, closes, spread_pct=0.005):
        """Replicate the CR-5 guard logic from calculate_indicators in isolation.

        Builds a minimal TR series from the close prices, calls rma(tr,14),
        then applies the same NaN guard as the fixed app.py code.
        Returns the resulting atr float.
        """
        closes = np.asarray(closes, dtype=float)
        n = len(closes)
        opens = np.concatenate([[closes[0]], closes[:-1]])
        highs = closes * (1 + spread_pct)
        lows  = closes * (1 - spread_pct)
        idx   = pd.date_range("2024-01-01", periods=n, freq="1h")
        df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows,
                           "Close": closes, "Volume": 1e6}, index=idx)
        high  = df["High"]
        low   = df["Low"]
        close = df["Close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr_raw = dvapp.rma(tr, 14)
        _last = atr_raw.iloc[-1]
        if pd.isna(_last):
            _fb = tr.dropna()
            _last = float(_fb.mean()) if len(_fb) > 0 else float(close.iloc[-1]) * 0.01
        return float(_last)

    def test_short_series_14_bars_guard_logic(self):
        """14 bars — Wilder ATR just converges (rma seeds at bar 14).
        Guard logic must return a positive finite float, not NaN.
        Tested directly on guard logic because calculate_indicators requires
        >= 20 bars for its vol_avg path.
        """
        closes = np.linspace(100.0, 105.0, 14)
        atr = self._apply_atr_guard(closes, spread_pct=0.005)
        assert not np.isnan(atr), f"atr is NaN on 14-bar guard test: {atr}"
        assert atr > 0, f"atr is zero/negative on 14-bar guard test: {atr}"

    def test_short_series_5_bars_fallback_fires(self):
        """5 bars — below rma(14) convergence threshold (rma returns all-NaN).
        The TR-mean fallback must kick in and return a positive float.
        """
        closes = np.array([100.0, 101.5, 99.0, 102.0, 100.5])
        atr = self._apply_atr_guard(closes, spread_pct=0.005)
        assert not np.isnan(atr), f"atr is NaN on 5-bar fallback test: {atr}"
        assert atr > 0, f"atr is zero/negative on 5-bar fallback test: {atr}"

    def test_5_bar_rma_really_is_nan_confirming_fallback_needed(self):
        """Document that rma(tr, 14) IS all-NaN on 5 bars — confirming the
        guard is load-bearing, not dead code.
        """
        closes = np.array([100.0, 101.5, 99.0, 102.0, 100.5])
        df = _make_df(closes, spread_pct=0.005)
        high, low, close = df["High"], df["Low"], df["Close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low  - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr_raw = dvapp.rma(tr, 14)
        assert atr_raw.isna().all(), (
            "Expected rma(tr,14) to be all-NaN on 5 bars; "
            "if this fails the guard is dead code and the test should be updated."
        )

    def test_short_series_20_bars(self):
        """20 bars — below the 100-bar window.  Old path returned NaN; new path must not."""
        closes = 100.0 + np.arange(20, dtype=float) * 0.1
        df = _make_df(closes, spread_pct=0.003)
        ind = dvapp.calculate_indicators(df, timeframe="1h", asset_type="stock")
        atr = ind["atr"]
        assert atr is not None
        assert not np.isnan(atr), f"atr is NaN on 20-bar series: {atr}"
        assert atr > 0, f"atr non-positive on 20-bar series: {atr}"

    def test_old_path_would_have_produced_nan_on_short_series(self):
        """Confirm the OLD formula really did produce NaN on <100 bars.

        This documents *why* the NaN guard is needed and also guards against
        the old formula being silently re-introduced (it would regress this
        invariant only if the series is >= 100 bars, which could hide the bug).
        """
        closes = 100.0 + np.arange(20, dtype=float) * 0.1
        df = _make_df(closes, spread_pct=0.003)
        # Reproduce old formula manually
        old_atr = _smoothed_atr(df, period=14, window=100)
        assert np.isnan(old_atr), (
            f"Expected old 100-bar smooth ATR to be NaN on 20-bar series "
            f"(min_periods=14, window=100), got {old_atr}. "
            "Test data assumptions have changed."
        )


class TestCR5SLTPUsesCurrentATR:
    """End-to-end: SL/TP levels must scale with current ATR from calculate_indicators.

    Two sub-tests:

    A) atr field comparison: calculate_indicators on calm vs spike series →
       spike atr must be >> calm atr.  This is the exact value that flows into
       SL = price - sl_mult * atr in get_analysis.

    B) get_analysis SL proportionality: inject two synthetic ind dicts that
       differ ONLY in the atr field, force a BUY signal, and assert the SL
       distance is proportional to atr.  This is fully deterministic because
       we bypass calculate_indicators and control every input.
    """

    _VIX_NORMAL = {"vix": 16.0, "zone": "NORMAL", "badge": None,
                   "context_text": "", "is_stale": False}

    # ── Part A: atr from calculate_indicators tracks current vol ─────────────

    def test_atr_field_larger_on_spike_series(self):
        """calculate_indicators["atr"] must be >> for the spike series vs calm.

        The atr field is what get_analysis uses directly for SL = price - sl_mult*atr.
        After the CR-5 fix it tracks current Wilder ATR(14), not the 100-bar mean,
        so it reacts immediately to elevated True Range.
        """
        # Calm: nearly-flat price, tight spread → small TR every bar
        df_calm = _make_df(
            100.0 + np.linspace(0, 5, 150),   # gentle uptrend
            spread_pct=0.001,                   # ±0.1%
        )
        # Spike: same calm history, but last 5 bars have ±2% H-L spread
        df_spike = _spike_df(n_calm=120, spike_mult=8.0)

        ind_calm  = dvapp.calculate_indicators(df_calm,  timeframe="1h", asset_type="stock")
        ind_spike = dvapp.calculate_indicators(df_spike, timeframe="1h", asset_type="stock")

        atr_calm  = ind_calm["atr"]
        atr_spike = ind_spike["atr"]

        assert atr_spike > atr_calm, (
            f"Expected atr_spike ({atr_spike:.6f}) > atr_calm ({atr_calm:.6f}). "
            "After CR-5 fix, calculate_indicators must return current Wilder ATR(14) "
            "which immediately reflects elevated volatility."
        )
        # The spike df is designed so current ATR is >> calm; require at least 3×
        ratio = atr_spike / atr_calm if atr_calm > 0 else 0
        assert ratio >= 3.0, (
            f"Spike ATR should be at least 3× calm ATR, got ratio={ratio:.2f}. "
            "Spike series may not be adversarial enough."
        )

    # ── Part B: get_analysis SL distance proportional to injected atr ────────

    def _make_buy_ind(self, price: float, atr: float) -> dict:
        """Minimal ind dict that reliably produces a BUY signal in get_analysis.

        All fields are deterministic — no dependence on calculate_indicators.
        """
        return {
            "price": price,
            "rsi": 35.0,            # oversold → bullish vote
            "ema_trend": "STRONG BULL",
            "ema20": price * 1.001,
            "ema50": price * 0.999,
            "ema200": price * 0.995,
            "macd_hist": price * 0.002,   # positive → bullish
            "bb_pos": 0.15,         # near lower band → bullish
            "bb_width": 0.03,
            "atr": atr,
            "atr_regime": "NORMAL",
            "vol_ratio": 1.5,
            "supertrend": "BULLISH",
            "support": price * 0.97,
            "resistance": price * 1.03,
            "chg_1d": 0.5,
            "rsi_divergence": {"type": "none", "strength": "none"},
            "adx": {"adx": 28.0, "trend_strength": "STRONG"},
            "ichimoku": {"signal": "BULLISH", "above_cloud": True, "cloud_bullish": True,
                         "tenkan_kijun_bull": True, "tenkan": price, "kijun": price * 0.999},
            "vwap": {"vwap": price * 0.998, "price_vs_vwap": "ABOVE", "signal": "BULLISH"},
            "stochrsi": {"k": 20.0, "d": 22.0, "zone": "OVERSOLD", "signal": "BULLISH"},
            "smc_structures": {"fvg_bullish": True, "fvg_bearish": False,
                                "liquidity_grab_bull": False, "liquidity_grab_bear": False,
                                "displacement_bull": True, "displacement_bear": False},
            "volume_profile": {"vpoc": price, "value_area_high": price * 1.01,
                                "value_area_low": price * 0.99},
            "order_flow": {"delta": 500, "signal": "BULLISH"},
            "chart_prices": [price] * 60,
            "chart_highs":  [price * 1.001] * 60,
            "chart_lows":   [price * 0.999] * 60,
            "chart_rsi":    [35.0] * 60,
        }

    def _get_sl_distance(self, price: float, atr: float) -> float | None:
        """Run get_analysis with a fully-injected ind and return |entry - stop_loss|."""
        from unittest.mock import patch
        ind = self._make_buy_ind(price, atr)
        with patch.object(dvapp, "_get_vix_score", return_value=self._VIX_NORMAL), \
             patch.object(dvapp, "_get_spread", return_value=(0.0, "table", "fair")):
            res = dvapp.get_analysis("AAPL", "stock", ind, "1h")
        sl = res.get("stop_loss")
        entry = res.get("entry")
        if sl is None or entry is None:
            return None
        return abs(entry - sl)

    def test_sl_distance_proportional_to_atr(self):
        """SL = price - sl_mult * atr, so doubling atr must double SL distance.

        Uses two fully-deterministic ind dicts differing only in atr (1.0 vs 2.0).
        This confirms get_analysis correctly uses the atr field for SL placement —
        the field that calculate_indicators now sets to current Wilder ATR(14).
        """
        price = 100.0
        dist_1x = self._get_sl_distance(price, atr=1.0)
        dist_2x = self._get_sl_distance(price, atr=2.0)

        if dist_1x is None or dist_2x is None:
            pytest.fail(
                f"get_analysis did not produce trade levels: "
                f"dist_1x={dist_1x}, dist_2x={dist_2x}. "
                "Signal logic may have changed; update ind dict to force BUY."
            )

        # SL distance must scale with ATR — 2× atr → 2× SL distance (within 1%)
        ratio = dist_2x / dist_1x
        assert abs(ratio - 2.0) < 0.01, (
            f"Expected dist(atr=2.0)/dist(atr=1.0) ≈ 2.0, got {ratio:.4f}. "
            "SL distance must be linearly proportional to atr."
        )

    def test_larger_atr_gives_wider_sl(self):
        """Directional sanity: larger atr → wider SL, regardless of exact multiplier."""
        price = 100.0
        dist_small = self._get_sl_distance(price, atr=0.5)
        dist_large = self._get_sl_distance(price, atr=5.0)

        if dist_small is None or dist_large is None:
            pytest.fail("get_analysis did not produce trade levels.")

        assert dist_large > dist_small, (
            f"Larger ATR (5.0) gave smaller SL distance ({dist_large:.4f}) "
            f"than smaller ATR (0.5, distance={dist_small:.4f}). "
            "SL must widen with ATR."
        )
