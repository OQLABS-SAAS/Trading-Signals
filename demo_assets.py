#!/usr/bin/env python3
"""Demonstrate MarkovEngine on BTC (volatile) and SPY with tighter threshold."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from markov_engine import (
    MarkovEngine, quick_analysis,
    classify_states, build_transition_matrix, stationary_distribution, square_matrix,
    STATE_BULL, STATE_BEAR, STATE_SIDEWAYS, STATE_LABELS,
)

print("=" * 60)
print("BTC-USD at 5% threshold (from EODHD)")
print("=" * 60)
engine = MarkovEngine(lookback=20)
result = engine.run("BTC-USD", asset_type="crypto", days=365)
print(f"Bars: {result['n_bars']}  |  States: {result['state_counts']}")
P = result['transition_matrix']
print(f"Transition matrix (3x3):")
for i, label in enumerate(result['state_labels']):
    row = '  '.join(f'{v:9.4f}' for v in P[i])
    print(f"  {label:>8s}  {row}")
print(f"Stationary: {[round(v,4) for v in result['stationary_distribution']]}" if result['stationary_distribution'] else "Stationary: None")
hmm = result['hmm_confirmation']
print(f"HMM agreement: {hmm['agreement_rate']}")
print()

print("=" * 60)
print("SPY at 1% threshold (better for ETFs)")
print("=" * 60)
prices_result = engine.run("SPY", asset_type="stock", days=365)
states = classify_states(engine.prices, threshold=0.01)
counts = {STATE_LABELS[i]: int((states == i).sum()) for i in [0,1,2]}
print(f"State counts at 1%: {counts}")
P = build_transition_matrix(states, lookback=20)
print(f"Transition matrix:")
for i, label in enumerate([STATE_LABELS[i] for i in [0,1,2]]):
    row = '  '.join(f'{v:9.4f}' for v in P[i])
    print(f"  {label:>8s}  {row}")
pi = stationary_distribution(P)
print(f"Stationary: {pi.round(4).tolist() if pi is not None else None}")
print(f"P^5 from Bull: {square_matrix(P, 5)[0].round(4).tolist()}")
print(f"P^10 from Bull: {square_matrix(P, 10)[0].round(4).tolist()}")
print()

print("=" * 60)
print("quick_analysis() one-liner on AAPL")
print("=" * 60)
try:
    result = quick_analysis("AAPL", asset_type="stock")
    print(f"Bars: {result['n_bars']}  |  States: {result['state_counts']}")
    P = result['transition_matrix']
    for i, label in enumerate(result['state_labels']):
        row = '  '.join(f'{v:9.4f}' for v in P[i])
        print(f"  {label:>8s}  {row}")
except Exception as e:
    print(f"Error: {e}")
