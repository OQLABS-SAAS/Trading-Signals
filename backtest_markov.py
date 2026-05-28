"""
backtest_markov.py — Walk-forward backtesting for Markov chain trading signals.

Algorithm (no look-ahead bias):
  1. Fetch daily close prices from EODHD.
  2. Reserve the first N bars as a warmup window (initial transition matrix).
  3. For each subsequent day t:
       a. Classify states using ALL data up to day t-1.
       b. Build a 3x3 transition matrix from the most recent `lookback` transitions.
       c. Read the row for the current state (day t-1) — highest column = predicted state.
       d. If predicted state is Bull → go LONG (return = actual day-t return).
         If predicted state is Bear → go SHORT (return = -actual day-t return).
         If predicted state is Sideways → HOLD (return = 0).
       e. Record the trade PnL.
  4. Compute aggregate metrics: win rate, avg return, Sharpe, max drawdown,
     equity curve, and comparison vs buy-and-hold.

All vectorised with numpy/pandas. No external backtesting libraries required.

Usage:
    bt = WalkForwardBacktest()
    result = bt.run("SPY", years=3)
    print(result["win_rate"], result["sharpe"])
"""

import math
import os
import sys
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from markov_engine import (
    classify_states,
    build_transition_matrix,
    fetch_daily_prices,
    STATE_BULL,
    STATE_BEAR,
    STATE_SIDEWAYS,
    STATE_LABELS,
    DEFAULT_LOOKBACK,
)

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

DEFAULT_WARMUP_BARS = 50       # Minimum bars before walk-forward starts
DEFAULT_YEARS       = 3        # Default history length
ANNUAL_TRADING_DAYS = 252      # For annualising returns


# ---------------------------------------------------------------------------
# Walk-forward backtest engine
# ---------------------------------------------------------------------------

class WalkForwardBacktest:
    """Walk-forward backtesting for Markov regime-prediction trading signals."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        lookback: int = DEFAULT_LOOKBACK,
        warmup_bars: int = DEFAULT_WARMUP_BARS,
        threshold: float = 0.05,
    ):
        """
        Parameters
        ----------
        api_key : str or None
            EODHD API key. Falls back to EODHD_API_KEY env var.
        lookback : int
            Number of recent transitions to include in the rolling matrix.
        warmup_bars : int
            Minimum number of price bars before the walk-forward loop begins.
        threshold : float
            Return threshold for Bull/Bear/Sideways classification.
        """
        self.api_key = api_key
        self.lookback = lookback
        self.warmup_bars = warmup_bars
        self.threshold = threshold

        # Cached results after run()
        self.prices: Optional[pd.Series] = None
        self.trades: Optional[list] = None
        self.equity_curve: Optional[list] = None
        self.benchmark_curve: Optional[list] = None

    # ------------------------------------------------------------------
    # Core walk-forward loop
    # ------------------------------------------------------------------

    def run(
        self,
        ticker: str,
        asset_type: str = "stock",
        years: int = DEFAULT_YEARS,
    ) -> dict:
        """
        Run the walk-forward backtest on daily data.

        Parameters
        ----------
        ticker : str
            Ticker symbol (e.g. 'SPY', 'AAPL', 'BTC-USD').
        asset_type : str
            Asset type for symbol mapping.
        years : int
            Years of history to fetch (min 1, max 10).

        Returns
        -------
        dict with keys:
            ticker, asset_type, years, n_bars, warmup_bars, lookback,
            n_out_of_sample_days, n_trades,
            win_rate, avg_return_per_trade,
            total_return_pct, annualised_return_pct,
            sharpe, max_drawdown_pct,
            benchmark_return_pct, benchmark_annualised_return_pct,
            strategy_vs_benchmark_pct,
            equity_curve, benchmark_curve,
            trade_summary, state_summary,
        """
        days = max(int(years * 365), 365)
        days = min(days, 3650)  # cap at 10 years

        # Step 1: fetch prices
        prices = fetch_daily_prices(ticker, asset_type, days, self.api_key)
        if prices is None:
            return {"error": f"Failed to fetch data for {ticker} ({asset_type})"}
        if len(prices) < self.warmup_bars + 10:
            return {
                "error": (
                    f"Only {len(prices)} bars available for {ticker}; "
                    f"need at least {self.warmup_bars + 10} for walk-forward"
                )
            }

        self.prices = prices
        n = len(prices)
        warmup = self.warmup_bars

        # Step 2: run walk-forward loop
        trades = []
        # We start at warmup (index warmup) and predict the return at warmup+1
        # by using only data up to index warmup.
        # Actually, let's think carefully:
        # - At day t (0-indexed), we need to predict the return from t-1 to t.
        # - We have prices[0:t] available (up to but not including day t).
        # - We classify states from prices[0:t], get states[0:t].
        # - We build transition matrix from states[0:t] (the last lookback transitions).
        # - The current state is states[t-1] (the state of day t-1, which reflects returns up to t-1).
        # - The predicted next state is argmax of transition_matrix[current_state].
        # - The actual return is prices[t] / prices[t-1] - 1.
        # - We need at least warmup data before we start.

        # First day we can predict is index warmup (since we need warmup bars of history).
        # For that, we use data up to index warmup-1, classify, build matrix,
        # and predict state at warmup-1 -> return at warmup.

        all_log_returns = np.diff(np.log(prices.values.astype(np.float64)))
        all_simple_returns = all_log_returns

        for t in range(warmup, n):
            # Data available: prices[0:t] (t elements)
            available = prices.iloc[:t]

            if len(available) < 2:
                continue

            # Classify states using only available data (no look-ahead)
            states = classify_states(
                available.values.astype(np.float64),
                threshold=self.threshold,
            )

            if len(states) < 2:
                continue

            # Build transition matrix from most recent lookback transitions
            P = build_transition_matrix(states, lookback=self.lookback)

            if np.any(np.isnan(P)):
                continue

            # Current state (the state for day t-1, i.e., the last available day)
            current_state = int(states[-1])

            # Predicted next state: the column with highest probability in current row
            predicted_state = int(np.argmax(P[current_state]))
            predicted_prob = float(P[current_state, predicted_state])

            # Actual simple return from day t-1 to day t
            actual_return = all_simple_returns[t - 1] if t - 1 < len(all_simple_returns) else 0.0

            # Trading decision:
            #   Bull prediction → LONG (earn actual return)
            #   Bear prediction → SHORT (earn negative of actual return)
            #   Sideways → HOLD (0 return)
            if predicted_state == STATE_BULL:
                trade_return = actual_return
                direction = "LONG"
            elif predicted_state == STATE_BEAR:
                trade_return = -actual_return
                direction = "SHORT"
            else:
                trade_return = 0.0
                direction = "HOLD"

            # Record trade
            date_str = str(pd.Timestamp(prices.index[t]).date())
            trades.append({
                "date": date_str,
                "current_state": int(current_state),
                "current_state_label": STATE_LABELS.get(current_state, "?"),
                "predicted_state": int(predicted_state),
                "predicted_state_label": STATE_LABELS.get(predicted_state, "?"),
                "predicted_prob": round(predicted_prob, 4),
                "actual_return_pct": round(actual_return * 100, 4),
                "trade_return_pct": round(trade_return * 100, 4),
                "direction": direction,
            })

        if len(trades) < 5:
            return {"error": f"Only {len(trades)} out-of-sample trades generated — insufficient for meaningful stats"}

        self.trades = trades

        # Step 3: compute aggregate metrics
        return self._compute_metrics(trades, prices, warmup)

    def _compute_metrics(self, trades: list, prices: pd.Series, warmup: int) -> dict:
        """Compute all aggregate metrics from the trade log."""

        # Extract trade returns as decimals
        trade_rets = np.array([t["trade_return_pct"] for t in trades], dtype=np.float64) / 100.0

        # --- Basic stats ---
        n_trades = len(trades)
        n_wins = int((trade_rets > 0).sum())
        n_losses = int((trade_rets < 0).sum())
        n_holds = int((trade_rets == 0).sum())
        win_rate = n_wins / n_trades if n_trades > 0 else 0.0
        avg_ret = float(np.mean(trade_rets))
        std_ret = float(np.std(trade_rets, ddof=1)) if n_trades > 1 else 0.0

        # --- Equity curve (starting at 1.0, compounding) ---
        equity = np.ones(n_trades + 1)
        for i, r in enumerate(trade_rets):
            equity[i + 1] = equity[i] * (1.0 + r)
        self.equity_curve = equity.tolist()

        total_return = equity[-1] - 1.0

        # --- Annualised return ---
        # Out-of-sample days
        oos_days = len(trades)
        years = oos_days / ANNUAL_TRADING_DAYS
        annualised_ret = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0

        # --- Sharpe ratio (annualised, risk-free = 0) ---
        sharpe = 0.0
        if std_ret > 0:
            sharpe = (avg_ret / std_ret) * math.sqrt(ANNUAL_TRADING_DAYS)

        # --- Max drawdown ---
        peak = equity[0]
        max_dd = 0.0
        for val in equity[1:]:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd

        # --- Benchmark: buy-and-hold from warmup start ---
        # The benchmark starts at the same point as our walk-forward
        benchmark_start = prices.iloc[warmup - 1] if warmup - 1 < len(prices) else prices.iloc[0]
        benchmark_end = prices.iloc[-1]
        benchmark_return = (benchmark_end / benchmark_start) - 1.0
        benchmark_annualised = (1.0 + benchmark_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0

        # Benchmark equity curve
        bm_equity_start = float(benchmark_start)
        bm_equity = prices.iloc[warmup - 1:].values.astype(np.float64)
        bm_curve = (bm_equity / bm_equity_start).tolist()
        self.benchmark_curve = bm_curve

        # --- Trade summary ---
        wins = trade_rets[trade_rets > 0]
        losses = trade_rets[trade_rets < 0]
        avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
        avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
        profit_factor = abs(sum(wins) / sum(losses)) if sum(losses) != 0 else float("inf")
        expectancy = float(np.mean(trade_rets))

        # --- State prediction accuracy ---
        correct = 0
        for t in trades:
            cs = t["current_state"]
            ps = t["predicted_state"]
            ar = t["actual_return_pct"]
            # Correct directional prediction:
            # Bull predicted and actual return > 0 → correct
            # Bear predicted and actual return < 0 → correct
            # Sideways predicted and actual |return| < threshold → correct (neutral zone)
            if ps == STATE_BULL and ar > 0:
                correct += 1
            elif ps == STATE_BEAR and ar < 0:
                correct += 1
            elif ps == STATE_SIDEWAYS and abs(ar) < self.threshold * 100:
                correct += 1
        directional_accuracy = correct / n_trades if n_trades > 0 else 0.0

        return {
            "ticker": str(prices.name) if hasattr(prices, "name") and prices.name else "?",
            "engine_version": "1.0.0",
            "method": "walk-forward",
            "warmup_bars": warmup,
            "lookback": self.lookback,
            "threshold_pct": self.threshold * 100,
            "n_out_of_sample_days": n_trades,
            "n_trades": n_trades,
            "n_wins": n_wins,
            "n_losses": n_losses,
            "n_holds": n_holds,

            # Performance
            "win_rate_pct": round(win_rate * 100, 2),
            "avg_return_per_trade_pct": round(avg_ret * 100, 4),
            "total_return_pct": round(total_return * 100, 2),
            "annualised_return_pct": round(annualised_ret * 100, 2),
            "sharpe": round(sharpe, 4),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "profit_factor": round(profit_factor, 4) if math.isfinite(profit_factor) else None,
            "expectancy_pct": round(expectancy * 100, 4),

            # Directional prediction accuracy
            "directional_accuracy_pct": round(directional_accuracy * 100, 2),

            # Benchmark comparison
            "benchmark_return_pct": round(benchmark_return * 100, 2),
            "benchmark_annualised_return_pct": round(benchmark_annualised * 100, 2),
            "strategy_vs_benchmark_pct": round((total_return - benchmark_return) * 100, 2),

            # State summary
            "state_summary": self._state_summary(trades),

            # Curves
            "equity_curve": [round(v, 4) for v in equity.tolist()],
            "benchmark_curve": [round(v, 4) for v in bm_curve],

            # Full trade log
            "trades": trades,
        }

    def _state_summary(self, trades: list) -> dict:
        """Summarise how often each current state leads to each predicted state."""
        from collections import defaultdict, Counter

        counts: dict = defaultdict(Counter)
        for t in trades:
            cs = t["current_state_label"]
            ps = t["predicted_state_label"]
            counts[cs][ps] += 1

        summary = {}
        for cs, ps_counter in counts.items():
            total = sum(ps_counter.values())
            summary[cs] = {
                label: round(cnt / total * 100, 1)
                for label, cnt in sorted(ps_counter.items(), key=lambda x: -x[1])
            }
        return summary


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def quick_backtest(
    ticker: str,
    asset_type: str = "stock",
    years: int = 3,
    api_key: Optional[str] = None,
    lookback: int = DEFAULT_LOOKBACK,
) -> dict:
    """Run a one-shot walk-forward backtest with sensible defaults."""
    bt = WalkForwardBacktest(api_key=api_key, lookback=lookback)
    return bt.run(ticker, asset_type, years=years)
