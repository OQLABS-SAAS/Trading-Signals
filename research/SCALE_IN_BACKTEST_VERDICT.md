# Smart Entry (scale-in) backtest — VERDICT: DO NOT BUILD (no edge found)

**Date:** 2026-06-10 · **Decision gate for:** `DOTVERSE_SMART_ENTRY_ENGINE_BUILD_PLAN.md`
**Code:** `research/scalein_vs_single_backtest.py` · **Data:** `scalein_vs_single_trades_ALL.csv` · **Stats:** `scalein_vs_single_summary_ALL.json`

## Question
Does splitting the entry into 3 limit legs laddered toward the order block
("scale-in") beat the app's current single full entry at the signal price —
on identical signals, same SL/TP, same total risk?

## Study
1,087 signals · 6 crypto majors (BTC, ETH, SOL, BNB, XRP, LINK) · 1h + 4h ·
~3,000 bars each (Binance, real history). Signals = RSI-14 cross rule (same
family the app's backtester uses), ATR levels (SL 1.5×, TP 2.5×). Order-block
proxy from the repo's own `detect_smc_structures()` (no look-ahead), ATR
fallback when no structure qualified. Walk-forward bar-by-bar fills; same-bar
TP/SL ties counted as loss for BOTH strategies. All results in R of total
intended risk — directly comparable.

## Result
| | A: single entry (today) | B: scale-in at OB |
|---|---|---|
| Win rate | 37.6% | 37.6% |
| Avg R / trade | **−0.0037** | **−0.0139** |
| Total R (1,087 trades) | −4.0 | −15.1 |
| Profit factor | 0.994 | 0.973 |
| Max drawdown (R) | −46.1 | **−53.4 (worse)** |

- Paired per-signal difference (B−A): **−0.0102R**, t = −0.84 → statistically
  indistinguishable; zero evidence of a scale-in edge, slight lean AGAINST it.
- B was worse in 5 of 6 symbols, in both timeframes, and in both directions.
- The "better average fill" DID materialise (legs filled 90.6% of intended
  size on average; 81% of trades filled fully) — and it still didn't help,
  because the trades that never retrace to the OB are the best runners, and
  scale-in systematically under-sizes exactly those.
- Even restricted to the 144 signals where a REAL SMC structure (FVG/liquidity
  grab/CHoCH) supplied the order block: A 0.148R vs B 0.131R. Still no edge.

## Decision
Per the agreed gate ("build only if the data proves an edge"): **the Smart
Entry Engine scale-in feature should NOT be built.** The current single-entry +
scale-OUT ladder is not the weakness the design discussion assumed. This also
retroactively validates keeping the feature gated instead of shipping it on
intuition.

## Honest caveats
- Crypto-only (free, reliable history; forex/stock providers need API keys).
  No reason to expect FX microstructure to rescue the idea, but it's untested.
- Entry rule is the app backtester's RSI-cross family, not the full DotVerse
  confluence engine; the comparison isolates ENTRY PLACEMENT, which is the
  question, but interaction effects with the live engine are untested.
- OB proxy fell back to entry−0.5×ATR in 86.8% of signals (real SMC structures
  near entry are rare on closed bars) — that is itself a finding: the "place
  legs at the order block" premise rarely has an order block to use.
- If revisited, the only variant worth testing: scale-in ONLY on signals where
  a real structure exists AND volatility regime filters — but the n=144 subset
  above already leans against it.
