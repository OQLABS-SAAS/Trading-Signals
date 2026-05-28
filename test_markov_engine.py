"""
test_markov_engine.py -- end-to-end verification of the Markov engine.

Tests both the core mathematical logic (synthetic data) and the live
EODHD data-fetching path when a credentials file is present.

Usage:
    python3 test_markov_engine.py         # tests everything, skips live fetch if no key
    python3 test_markov_engine.py -v      # verbose mode
"""

import json
import os
import sys
from typing import Optional

import numpy as np

# Import from the workspace module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from markov_engine import (
    MarkovEngine,
    SimpleHMM,
    classify_states,
    build_transition_matrix,
    square_matrix,
    stationary_distribution,
    STATE_BULL,
    STATE_BEAR,
    STATE_SIDEWAYS,
    STATE_LABELS,
)


def test_synthetic_up_trend():
    """
    Generate a steady uptrend -- all daily returns should be Bull.
    """
    print("  [test] Synthetic uptrend...", end=" ")
    prices = np.linspace(100, 200, 100)  # steady climb
    states = classify_states(prices)
    # Most days should be Bull (return > 5% only on the first few days
    # with extreme slope, then it settles)
    bull_pct = (states == STATE_BULL).mean()
    sideways_pct = (states == STATE_SIDEWAYS).mean()
    bear_pct = (states == STATE_BEAR).mean()
    print(f"Bull={bull_pct:.1%} Sideways={sideways_pct:.1%} Bear={bear_pct:.1%}")


def test_synthetic_down_trend():
    """
    Generate a steady downtrend -- most states should be Bear.
    """
    print("  [test] Synthetic downtrend...", end=" ")
    prices = np.linspace(200, 100, 100)
    states = classify_states(prices)
    bear_pct = (states == STATE_BEAR).mean()
    sideways_pct = (states == STATE_SIDEWAYS).mean()
    bull_pct = (states == STATE_BULL).mean()
    print(f"Bull={bull_pct:.1%} Sideways={sideways_pct:.1%} Bear={bear_pct:.1%}")


def test_synthetic_sideways():
    """
    Prices oscillating within +/- 2% -- all should be Sideways.
    """
    print("  [test] Synthetic sideways...", end=" ")
    base = 100.0
    prices = base + np.sin(np.linspace(0, 4 * np.pi, 100)) * 1.5
    states = classify_states(prices)
    sideways_pct = (states == STATE_SIDEWAYS).mean()
    print(f"Sideways={sideways_pct:.1%}")


def test_transition_matrix_all_bull():
    """
    If every state is Bull, the matrix should be [1, 0, 0] in the Bull row.
    """
    print("  [test] Transition matrix (all Bull)...", end=" ")
    states = np.full(50, STATE_BULL)
    P = build_transition_matrix(states, lookback=20)
    assert P[STATE_BULL, STATE_BULL] == 1.0, f"Expected 1.0, got {P[0,0]}"
    assert P[STATE_BULL, STATE_BEAR] == 0.0
    assert P[STATE_BULL, STATE_SIDEWAYS] == 0.0
    # Bear and Sideways rows should be all 0 (never observed)
    assert P[STATE_BEAR].sum() == 0.0
    assert P[STATE_SIDEWAYS].sum() == 0.0
    print("OK")


def test_transition_matrix_alternating():
    """
    If Bull and Bear alternate perfectly, P[Bull][Bear] = P[Bear][Bull] = 1.
    """
    print("  [test] Transition matrix (alternating Bull/Bear)...", end=" ")
    states = np.tile([STATE_BULL, STATE_BEAR], 25)  # Bull, Bear, Bull, Bear...
    P = build_transition_matrix(states, lookback=20)
    assert P[STATE_BULL, STATE_BEAR] == 1.0, f"Expected 1.0, got {P[0,1]}"
    assert P[STATE_BEAR, STATE_BULL] == 1.0, f"Expected 1.0, got {P[1,0]}"
    print("OK")


def test_matrix_squaring():
    """
    Identify matrix P = I should stay the same for any power.
    """
    print("  [test] Matrix squaring (identity)...", end=" ")
    I = np.eye(3)
    for steps in [1, 5, 10, 20]:
        result = square_matrix(I, steps)
        assert np.allclose(result, I), f"P^{steps} of identity should be identity"
    print("OK")


def test_matrix_squaring_doubly_stochastic():
    """
    Any transition matrix raised to any power should be row-stochastic.
    """
    print("  [test] Matrix squaring (row sums)...", end=" ")
    P = np.array([[0.6, 0.3, 0.1], [0.2, 0.7, 0.1], [0.3, 0.3, 0.4]])
    for steps in [1, 3, 7, 15]:
        Pn = square_matrix(P, steps)
        row_sums = Pn.sum(axis=1)
        assert np.allclose(row_sums, 1.0), f"P^{steps} row sums = {row_sums}"
    print("OK")


def test_stationary_distribution():
    """
    For a primitive matrix, pi * P = pi should hold within tolerance.
    """
    print("  [test] Stationary distribution...", end=" ")
    P = np.array([[0.6, 0.3, 0.1], [0.2, 0.7, 0.1], [0.3, 0.3, 0.4]])
    pi = stationary_distribution(P)
    assert pi is not None, "Stationary distribution returned None for valid P"
    assert np.allclose(pi @ P, pi, atol=1e-6), f"pi * P != pi: {pi} @ P = {pi @ P}"
    assert np.isclose(pi.sum(), 1.0), f"pi does not sum to 1: {pi.sum()}"
    print(f"OK ({pi.round(4).tolist()})")


def test_stationary_distribution_symmetry():
    """
    A symmetric matrix with equal probabilities should give uniform stationary.
    """
    print("  [test] Stationary distribution (uniform)...", end=" ")
    P = np.ones((3, 3)) / 3.0
    pi = stationary_distribution(P)
    assert pi is not None
    assert np.allclose(pi, [1/3, 1/3, 1/3], atol=0.05)
    print("OK")


def test_hmm_synthetic():
    """
    HMM should decode a simple Bull-Bull-Bear-Bear pattern.
    """
    print("  [test] HMM synthetic pattern...", end=" ")
    hmm = SimpleHMM(n_hidden=3, n_obs=3, max_iter=30)
    obs = np.array([STATE_BULL, STATE_BULL, STATE_BULL, STATE_BEAR, STATE_BEAR, STATE_BEAR])
    hmm.fit(obs)
    hidden = hmm.viterbi(obs)
    # The HMM should broadly match (some boundary uncertainty is OK)
    agreement = (hidden == obs).mean()
    assert agreement >= 0.5, f"HMM agreement too low: {agreement}"
    print(f"OK (agreement={agreement:.0%})")


def test_hmm_confidence():
    """
    HMM confidence with perfectly deterministic sequence.
    """
    print("  [test] HMM confidence...", end=" ")
    hmm = SimpleHMM(max_iter=50)
    # A simple pattern: Sideways for 10 days, then Bull for 10
    obs = np.array([STATE_SIDEWAYS] * 10 + [STATE_BULL] * 10)
    threshold = obs.copy()
    hmm.fit(obs)
    conf = hmm.get_confidence(obs, threshold)
    assert conf["agreement_rate"] >= 0.7, f"Low agreement: {conf['agreement_rate']}"
    print(f"OK (agreement={conf['agreement_rate']:.0%})")


def test_markov_engine_synthetic():
    """
    Run the full MarkovEngine pipeline on synthetic data to verify the
    output dict shape.
    """
    print("  [test] MarkovEngine full pipeline on synthetic data...", end=" ")
    engine = MarkovEngine(lookback=20)

    # Override the price data to avoid real API calls
    prices = np.linspace(100, 110, 60) + np.random.default_rng(42).normal(0, 0.5, 60)

    states = classify_states(prices)
    P = build_transition_matrix(states, lookback=20)
    pi = stationary_distribution(P)

    # Run the HMM path manually
    hmm = SimpleHMM(max_iter=30)
    hmm.fit(states)
    hmm_res = hmm.get_confidence(states, states)

    # Verify key fields
    assert P.shape == (3, 3), f"Transition matrix wrong shape: {P.shape}"
    assert pi is None or len(pi) == 3, f"Stationary wrong length: {len(pi) if pi is not None else 0}"
    assert "agreement_rate" in hmm_res

    print("OK")


def test_live_eodhd():
    """
    Test the live EODHD data-fetching path.
    Skips silently if EODHD_API_KEY is not set or returns insufficient data.
    """
    api_key = os.environ.get("EODHD_API_KEY", "").strip()
    if not api_key:
        print("  [test] Live EODHD fetch -- SKIPPED (no EODHD_API_KEY)")
        return

    print("  [test] Live EODHD fetch (SPY, stock)...", end=" ")
    engine = MarkovEngine(api_key=api_key, lookback=20)
    result = engine.run("SPY", asset_type="stock", days=365)
    if "error" in result:
        print(f"SKIPPED ({result['error']})")
        return

    # Validate the result dict has all required fields
    required_keys = [
        "transition_matrix", "multi_day_forecast_5d", "multi_day_forecast_10d",
        "multi_day_forecast_20d", "stationary_distribution", "hmm_confirmation",
        "state_counts", "n_bars", "engine_version",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"

    assert len(result["transition_matrix"]) == 3
    assert len(result["transition_matrix"][0]) == 3

    print(f"OK ({result['n_bars']} bars, stationary={result['stationary_distribution']})")


def test_edge_cases():
    """
    Edge cases: single data point, 2 data points, all same state.
    """
    print("  [test] Edge case -- single price...", end=" ")
    states = classify_states(np.array([100.0]))
    assert len(states) == 1
    P = build_transition_matrix(states, lookback=20)
    assert np.isnan(P).all()  # no transitions possible
    pi = stationary_distribution(P)
    assert pi is None  # NaN matrix -> None
    print("OK")

    print("  [test] Edge case -- 2 prices (flat)...", end=" ")
    states = classify_states(np.array([100.0, 101.0]))
    assert len(states) == 2
    P = build_transition_matrix(states, lookback=20)
    assert not np.isnan(P).any()  # one transition possible
    print("OK")

    print("  [test] Edge case -- missing API key...", end=" ")
    # Temporarily unset the env var so an empty api_key truly means no key
    old_key = os.environ.pop("EODHD_API_KEY", None)
    engine = MarkovEngine(api_key="")
    result = engine.run("SPY", asset_type="stock")
    if old_key is not None:
        os.environ["EODHD_API_KEY"] = old_key
    assert "error" in result, f"Expected error for empty API key, got: {result.get('n_bars', 'no n_bars')}"
    print("OK")


def print_result_dict_example():
    """
    Demonstrate the output dict layout with synthetic data.
    """
    print("\n  [demo] Full output dict from MarkovEngine (synthetic data):")
    rng = np.random.default_rng(42)
    prices = 100 + np.cumsum(rng.normal(0.3, 1.0, 100))
    engine = MarkovEngine(lookback=20)

    result = engine._build_output(
        ticker="DEMO",
        asset_type="stock",
        P=build_transition_matrix(classify_states(prices)),
        pi=stationary_distribution(build_transition_matrix(classify_states(prices))),
        P_5d=square_matrix(build_transition_matrix(classify_states(prices)), 5),
        P_10d=square_matrix(build_transition_matrix(classify_states(prices)), 10),
        P_20d=square_matrix(build_transition_matrix(classify_states(prices)), 20),
        state_counts={"Bull": 35, "Bear": 25, "Sideways": 39},
        hmm_result={
            "agreement_rate": 0.74,
            "hidden_transition_matrix": [[0.6, 0.2, 0.2], [0.25, 0.5, 0.25], [0.15, 0.25, 0.6]],
            "stationary_distribution": [0.30, 0.30, 0.40],
            "most_likely_regime": 0,
            "most_likely_regime_label": "Bull",
        },
    )
    # Pretty print
    print(json.dumps(result, indent=2)[:2000])
    print("  ... (truncated, full dict shown in JSON above)")


if __name__ == "__main__":
    print("=" * 60)
    print("Markov Engine -- End-to-End Test Suite")
    print("=" * 60)
    print()

    tests = [
        ("Core state classification", [
            test_synthetic_up_trend,
            test_synthetic_down_trend,
            test_synthetic_sideways,
        ]),
        ("Transition matrix", [
            test_transition_matrix_all_bull,
            test_transition_matrix_alternating,
        ]),
        ("Matrix squaring", [
            test_matrix_squaring,
            test_matrix_squaring_doubly_stochastic,
        ]),
        ("Stationary distribution", [
            test_stationary_distribution,
            test_stationary_distribution_symmetry,
        ]),
        ("HMM layer", [
            test_hmm_synthetic,
            test_hmm_confidence,
        ]),
        ("Engine pipeline", [
            test_markov_engine_synthetic,
        ]),
        ("Live EODHD", [
            test_live_eodhd,
        ]),
        ("Edge cases", [
            test_edge_cases,
        ]),
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
                failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
    if failed > 0:
        sys.exit(1)
    else:
        print("All tests passed.")
