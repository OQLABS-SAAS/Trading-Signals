#!/usr/bin/env python3
"""Demonstrate the MarkovEngine output dict on live SPY data."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from markov_engine import MarkovEngine

engine = MarkovEngine(lookback=20)
result = engine.run("SPY", asset_type="stock", days=365)

# Print a concise summary
print("=" * 60)
print("Markov Engine -- Live SPY Analysis")
print("=" * 60)
print()

print(f"Symbol:      SPY (stock)")
print(f"Bars:        {result['n_bars']}")
print(f"Transitions: {result['n_transitions']}")
print(f"Lookback:    {result['lookback_days']} transitions")
print(f"Threshold:   {result['return_threshold_pct']}%")
print()

print("State counts:")
for label, count in result['state_counts'].items():
    print(f"  {label}: {count}")
print()

print("Transition Matrix (3x3):")
labels = result['state_labels']
matrix = result['transition_matrix']
print(f"           {'  '.join(f'{l:>9s}' for l in labels)}")
for i, label in enumerate(labels):
    row = '  '.join(f'{v:9.4f}' for v in matrix[i])
    print(f"  {label:>8s}  {row}")
print()

print("Multi-day forecasts (from Bull start):")
for n, key in [("5d", "multi_day_forecast_5d"), ("10d", "multi_day_forecast_10d"), ("20d", "multi_day_forecast_20d")]:
    Pn = result[key]
    bull_row = Pn[0]
    print(f"  P^{n:>3s}: Bull={bull_row[0]:.4f} Bear={bull_row[1]:.4f} Sideways={bull_row[2]:.4f}")
print()

print("Stationary Distribution:")
sd = result['stationary_distribution']
if sd:
    for i, label in enumerate(labels):
        print(f"  {label}: {sd[i]:.4f}")
print()

print("HMM Confirmation:")
hmm = result['hmm_confirmation']
print(f"  Agreement rate:       {hmm['agreement_rate']}")
print(f"  Most likely regime:   {hmm['most_likely_regime_label']}")
if hmm['hidden_transition_matrix']:
    print(f"  HMM hidden transition matrix:")
    for i, label in enumerate(labels):
        row = '  '.join(f'{v:9.4f}' for v in hmm['hidden_transition_matrix'][i])
        print(f"    {label:>8s}  {row}")
print()

print("Full JSON output:")
print(json.dumps(result, indent=2))
