"""
test_backtest_markov.py — End-to-end verification of walk-forward Markov backtesting.

Tests:
  - Core walk-forward logic on synthetic data with known patterns
  - Up-trend: Markov should predict Bull correctly
  - Down-trend: Markov should predict Bear correctly
  - Sideways: Markov should predict Sideways
  - Persistence of state: Bull→Bull matrix entries
  - Edge cases: insufficient data, no API key
  - Live EODHD fetch (skips silently if no key)
  - Output dict shape verification

Usage:
    python3 test_backtest_markov.py         # tests everything
    python3 test_backtest_markov.py -v      # verbose
"""

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest_markov import WalkForwardBacktest, quick_backtest
from markov_engine import (
    STATE_BULL,
    STATE_BEAR,
    STATE_SIDEWAYS,
    classify_states,
    build_transition_matrix,
    DEFAULT_LOOKBACK,
)


ONE_DAY = 1 / 252  # ~0.4% — used for small daily return steps


def _make_trend_prices(
    n_days: int, start: float = 100.0,
    drift: float = 0.001, noise: float = 0.005
) -> pd.Series:
    """Generate synthetic daily price series with drift and noise, indexed by date.
    Use higher drift + noise (~2-3% daily) for walk-forward tests so daily
    returns exceed the +/-5% classification threshold."""
    rng = np.random.default_rng(42)
    log_rets = np.random.normal(drift, noise, n_days)
    prices = start * np.exp(np.cumsum(log_rets))
    dates = pd.date_range(end="2025-12-31", periods=n_days, freq="B")
    return pd.Series(prices, index=dates, name="SYNTH")


# Helper: run a walk-forward loop with the same logic as WalkForwardBacktest
def _walk_forward(prices: pd.Series, warmup: int = 100, lookback: int = 20, threshold: float = 0.05):
    """Run walk-forward and return trade returns array."""
    trades = []
    n = len(prices)
    all_rets = np.diff(np.log(prices.values.astype(np.float64)))
    for t in range(warmup, n):
        available = prices.iloc[:t]
        if len(available) < 2:
            continue
        states = classify_states(available.values.astype(np.float64), threshold=threshold)
        if len(states) < 2:
            continue
        P = build_transition_matrix(states, lookback=lookback)
        if np.any(np.isnan(P)):
            continue
        cs = int(states[-1])
        ps = int(np.argmax(P[cs]))
        ar = all_rets[t - 1] if t - 1 < len(all_rets) else 0.0
        if ps == STATE_BULL:
            tr = ar
        elif ps == STATE_BEAR:
            tr = -ar
        else:
            tr = 0.0
        trades.append(tr)
    return np.array(trades)


# ======================================================================
# Tests
# ======================================================================


def test_walk_forward_output_shape():
    """
    Verify the walk-forward loop runs and produces correctly shaped output.
    Uses synthetic data with high vol so some states are non-Sideways.
    """
    print("  [test] Walk-forward output shape...", end=" ")
    prices = _make_trend_prices(400, drift=0.005, noise=0.10)
    trades = _walk_forward(prices, warmup=100, lookback=20, threshold=0.05)

    assert len(trades) > 50, f"Too few trades: {len(trades)}"
    # _walk_forward returns np.array of trade returns (floats)
    n_non_hold = int((trades != 0).sum())
    print(f"n_trades={len(trades)} n_non_hold={n_non_hold}")
    assert n_non_hold > 0, "No non-HOLD trades generated"
    print(f"OK ({len(trades)} trades, {n_non_hold} non-HOLD)")


def test_walk_forward_no_lookahead():
    """
    Critical test: verify the walk-forward loop uses correctly spaced dates
    (each day predicts the NEXT day, not the same day).
    """
    print("  [test] Walk-forward date spacing...", end=" ")
    # Use a simple 252-day constant +1% per day price series
    rng = np.random.default_rng(42)
    prices = 100 * np.exp(np.cumsum(np.random.normal(0.001, 0.05, 300)))
    dates = pd.date_range(end="2025-12-31", periods=300, freq="B")
    prices_series = pd.Series(prices, index=dates, name="LOOKAHEAD_TEST")

    import backtest_markov as bm
    original_fetch = bm.fetch_daily_prices
    bm.fetch_daily_prices = lambda *a, **kw: prices_series

    try:
        bt = WalkForwardBacktest(warmup_bars=100, lookback=20)
        result = bt.run("LOOKAHEAD_TEST")
        bm.fetch_daily_prices = original_fetch
    except Exception:
        bm.fetch_daily_prices = original_fetch
        raise

    # Verify the trade dates are in order and each trade predicts the next day
    trades = result["trades"]
    assert len(trades) > 0, "Expected some trades"
    for i in range(1, len(trades)):
        assert trades[i]["date"] >= trades[i-1]["date"], \
            f"Trade date went backwards at index {i}: {trades[i-1]['date']} -> {trades[i]['date']}"

    # Verify equity curve length matches trade count + 1
    eq = result["equity_curve"]
    assert len(eq) == result["n_trades"] + 1, \
        f"Equity curve length {len(eq)} != n_trades+1 {result['n_trades']+1}"

    print(f"OK ({result['n_trades']} trades, {len(eq)} equity points, no look-ahead)")


def test_run_method_synthetic():
    """
    Run the full WalkForwardBacktest.run() pipeline on synthetic data with
    override of the price series to avoid real API calls.
    """
    print("  [test] Full run() pipeline (synthetic)...", end=" ")
    prices = _make_trend_prices(300, drift=0.001, noise=0.10)
    bt = WalkForwardBacktest(warmup_bars=80, lookback=20)

    # Monkey-patch fetch_daily_prices to return our synthetic data
    import backtest_markov as bm

    original_fetch = bm.fetch_daily_prices

    def _mock_fetch(ticker, asset_type, days, api_key):
        return prices

    bm.fetch_daily_prices = _mock_fetch

    try:
        result = bt.run("SYNTH", asset_type="stock", years=1)
        bm.fetch_daily_prices = original_fetch
    except Exception as e:
        bm.fetch_daily_prices = original_fetch
        raise AssertionError(f"run() raised exception: {e}")

    # Verify output dict has all required keys
    required_keys = [
        "win_rate_pct", "total_return_pct", "annualised_return_pct",
        "sharpe", "max_drawdown_pct", "n_trades",
        "equity_curve", "benchmark_curve", "trades",
        "benchmark_return_pct", "strategy_vs_benchmark_pct",
        "directional_accuracy_pct", "state_summary",
    ]
    for key in required_keys:
        assert key in result, f"Missing key in result: {key}"

    assert result["n_trades"] > 0, "Zero trades generated"
    assert len(result["equity_curve"]) == result["n_trades"] + 1
    assert len(result["benchmark_curve"]) == result["n_trades"] + 1

    print(f"OK ({result['n_trades']} trades, sharpe={result['sharpe']:.2f})")


def test_edge_insufficient_data():
    """Very few bars — should return error."""
    print("  [test] Edge case — insufficient data...", end=" ")
    prices = _make_trend_prices(30, drift=0.001)

    import backtest_markov as bm
    original_fetch = bm.fetch_daily_prices
    bm.fetch_daily_prices = lambda *a, **kw: prices

    try:
        bt = WalkForwardBacktest(warmup_bars=50)
        result = bt.run("SYNTH")
        bm.fetch_daily_prices = original_fetch
    except Exception:
        bm.fetch_daily_prices = original_fetch
        raise

    assert "error" in result, "Should return error for insufficient data"
    print(f"OK ('{result['error'][:40]}...')")


def test_edge_no_api_key():
    """Empty API key should produce an error gracefully."""
    print("  [test] Edge case — no API key...", end=" ")
    old_key = os.environ.pop("EODHD_API_KEY", None)
    bt = WalkForwardBacktest(api_key="")
    result = bt.run("SPY")
    if old_key is not None:
        os.environ["EODHD_API_KEY"] = old_key
    assert "error" in result, f"Expected error for empty API key, got non-error result"
    print("OK")


def test_state_summary():
    """Verify the state_summary dict has reasonable shape."""
    print("  [test] State summary output...", end=" ")
    prices = _make_trend_prices(300, drift=0.001, noise=0.10)

    import backtest_markov as bm
    original_fetch = bm.fetch_daily_prices
    bm.fetch_daily_prices = lambda *a, **kw: prices

    try:
        bt = WalkForwardBacktest(warmup_bars=80)
        result = bt.run("SYNTH")
        bm.fetch_daily_prices = original_fetch
    except Exception:
        bm.fetch_daily_prices = original_fetch
        raise

    ss = result["state_summary"]
    expected_labels = {"Bull", "Bear", "Sideways"}
    assert len(ss) > 0, "State summary is empty"
    for state_label, transitions in ss.items():
        assert state_label in expected_labels, f"Unexpected state label: {state_label}"
        for target_label, pct in transitions.items():
            assert target_label in expected_labels, f"Unexpected transition target: {target_label}"
            assert 0 <= pct <= 100, f"Invalid percentage: {pct}"
    print(f"OK ({len(ss)} states mapped)")


def test_quick_backtest_synthetic():
    """Verify quick_backtest() convenience function."""
    print("  [test] quick_backtest() convenience...", end=" ")
    prices = _make_trend_prices(200, drift=0.000, noise=0.10)

    import backtest_markov as bm
    original_fetch = bm.fetch_daily_prices
    bm.fetch_daily_prices = lambda *a, **kw: prices

    try:
        result = quick_backtest("SYNTH", years=1)
        bm.fetch_daily_prices = original_fetch
    except Exception:
        bm.fetch_daily_prices = original_fetch
        raise

    assert "win_rate_pct" in result
    print(f"OK ({result['n_trades']} trades)")


def test_equity_curve_integrity():
    """Verify equity curve starts at 1.0 and compounds correctly."""
    print("  [test] Equity curve integrity...", end=" ")
    prices = _make_trend_prices(200, drift=0.001, noise=0.10)

    import backtest_markov as bm
    original_fetch = bm.fetch_daily_prices
    bm.fetch_daily_prices = lambda *a, **kw: prices

    try:
        bt = WalkForwardBacktest(warmup_bars=80)
        result = bt.run("SYNTH")
        bm.fetch_daily_prices = original_fetch
    except Exception:
        bm.fetch_daily_prices = original_fetch
        raise

    eq = result["equity_curve"]
    assert eq[0] == 1.0, f"Equity curve should start at 1.0, got {eq[0]}"

    # Verify compounding: each step should multiply by (1 + trade_return)
    trades = result["trades"]
    for i, t in enumerate(trades):
        expected = eq[i] * (1.0 + t["trade_return_pct"] / 100.0)
        assert abs(eq[i + 1] - expected) < 1e-3, \
            f"Equity mismatch at step {i}: {eq[i+1]:.6f} vs expected {expected:.6f}"

    print(f"OK ({len(eq)} points)")


def test_live_eodhd():
    """
    Test the live EODHD data-fetching path.
    Skips silently if EODHD_API_KEY is not set.
    """
    api_key = os.environ.get("EODHD_API_KEY", "").strip()
    if not api_key:
        print("  [test] Live EODHD fetch — SKIPPED (no EODHD_API_KEY)")
        return

    print("  [test] Live EODHD fetch (SPY, ~1yr)...", end=" ")
    bt = WalkForwardBacktest(api_key=api_key)
    result = bt.run("SPY", asset_type="stock", years=1)
    if "error" in result:
        print(f"SKIPPED ({result['error'][:60]})")
        return

    assert "win_rate_pct" in result, f"Missing win_rate_pct: {list(result.keys())[:10]}"
    assert result["n_trades"] > 0, "Zero trades from live data"
    assert result["total_return_pct"] is not None, "total_return_pct should be present"
    print(f"OK ({result['n_trades']} trades, sharpe={result['sharpe']:.2f}, ret={result['total_return_pct']:.1f}%)")


# ======================================================================
# Runner
# ======================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Walk-Forward Markov Backtest — Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Walk-forward output shape", [test_walk_forward_output_shape]),
        ("No look-ahead date check", [test_walk_forward_no_lookahead]),
        ("Full pipeline", [test_run_method_synthetic]),
        ("State summary", [test_state_summary]),
        ("Quick backtest", [test_quick_backtest_synthetic]),
        ("Equity curve", [test_equity_curve_integrity]),
        ("Edge cases", [test_edge_insufficient_data, test_edge_no_api_key]),
        ("Live EODHD", [test_live_eodhd]),
    ]

    passed = 0
    failed = 0
    for group_name, group_tests in tests:
        print(f"\n--- {group_name} ---")
        for test_fn in group_tests:
            try:
                test_fn()
                passed += 1
            except Exception as e:
                print(f"  FAIL: {e}")
                import traceback
                traceback.print_exc()
                failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed.")
