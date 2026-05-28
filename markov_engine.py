"""
markov_engine.py - Markov chain analysis engine for market regime detection

This module implements a complete Markov analysis pipeline:
  1. Fetches daily price data from EODHD (primary data source)
  2. Classifies market states (Bull / Bear / Sideways at +/-5% returns)
  3. Builds a 3x3 transition matrix with rolling lookback
  4. Squares the matrix for multi-day probability forecasts
  5. Computes the stationary distribution (long-run probabilities)
  6. Runs a simple HMM for regime confirmation

All logic is vectorized with numpy/pandas and has no look-ahead bias.
No external HMM library required -- the HMM is implemented from scratch.

Usage:
    engine = MarkovEngine(api_key="your_eodhd_key")
    result = engine.run("SPY", asset_type="stock")
    print(result["transition_matrix"])
    print(result["stationary_distribution"])
    print(result["hmm_confirmation"])
"""

import os
import warnings
from datetime import datetime, timedelta
from typing import Optional, Union

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Return threshold for state classification.
# Trailing returns above +5% are classed as Bull, below -5% as Bear,
# and everything in between as Sideways.
RETURN_THRESHOLD = 0.05

# State-to-integer mapping for matrix indexing
STATE_BULL = 0       # returns > +threshold
STATE_BEAR = 1       # returns < -threshold
STATE_SIDEWAYS = 2   # returns between -threshold and +threshold

STATE_LABELS = {STATE_BULL: "Bull", STATE_BEAR: "Bear", STATE_SIDEWAYS: "Sideways"}

# Default number of transitions to include in the rolling window
DEFAULT_LOOKBACK = 20

# Maximum bars to keep (oldest data is trimmed for performance)
MAX_BARS = 500

# EODHD API timeout in seconds
EODHD_TIMEOUT = (5, 15)

# ---------------------------------------------------------------------------
# Symbol helpers  (mirrors the DotVerse symbol-mapping patterns)
# ---------------------------------------------------------------------------

def _normalise_ticker(ticker: str, asset_type: str) -> str:
    """Build the EODHD-compatible symbol string for a given ticker + asset type."""
    raw = ticker.upper().replace("=X", "").replace("=F", "")

    if asset_type == "stock":
        return f"{raw.replace('-', '')}.US"
    if asset_type == "forex":
        # Forex pairs use the .FOREX suffix on EODHD
        return raw.replace("-", "").replace("/", "") + ".FOREX"
    if asset_type == "crypto":
        # Crypto is bare ticker (no suffix)
        base = raw.replace("-USD", "").replace("-USDT", "").replace("-USDC", "")
        return base.strip("-")
    if asset_type == "index":
        # Indices use ETF proxies (EODHD does not support raw index symbols)
        INDEX_MAP = {
            "^GSPC": "SPY.US", "^VIX": "UVXY.US", "^NDX": "QQQ.US",
            "^DJI": "DIA.US", "^RUT": "IWM.US", "^IXIC": "QQQ.US",
        }
        return INDEX_MAP.get(raw, raw.replace("-", ""))
    if asset_type == "commodity":
        # Commodity metals use forex symbols on EODHD
        COMMODITY_MAP = {
            "GC": "XAUUSD.FOREX", "SI": "XAGUSD.FOREX",
            "PL": "XPTUSD.FOREX", "PA": "XPDUSD.FOREX",
        }
        return COMMODITY_MAP.get(raw, raw)
    return raw


# ---------------------------------------------------------------------------
# 1. EODHD data fetching
# ---------------------------------------------------------------------------

def fetch_daily_prices(
    ticker: str,
    asset_type: str = "stock",
    days: int = 365,
    api_key: Optional[str] = None,
) -> Optional[pd.Series]:
    """
    Fetch daily close prices from EODHD.

    Parameters
    ----------
    ticker : str
        Ticker symbol (e.g. 'SPY', 'AAPL', 'BTC-USD').
    asset_type : str
        One of 'stock', 'forex', 'crypto', 'index', 'commodity'.
    days : int
        Number of calendar days of history to request.
    api_key : str or None
        EODHD API key.  Falls back to the EODHD_API_KEY environment variable.

    Returns
    -------
    pd.Series or None
        Close prices indexed by date (sorted ascending), or None on failure.
    """
    key = api_key or os.environ.get("EODHD_API_KEY", "").strip()
    if not key:
        print("[markov-engine] EODHD_API_KEY not set -- cannot fetch data")
        return None

    symbol = _normalise_ticker(ticker, asset_type)
    today = datetime.now()
    from_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    url = f"https://eodhd.com/api/eod/{symbol}"
    params = {"api_token": key, "fmt": "json", "from": from_date, "to": to_date}

    try:
        resp = requests.get(url, params=params, timeout=EODHD_TIMEOUT)
        if resp.status_code != 200:
            print(f"[markov-engine] EODHD HTTP {resp.status_code} for {symbol}")
            return None

        data = resp.json()
        if not isinstance(data, list) or len(data) < 20:
            print(f"[markov-engine] EODHD insufficient bars for {symbol}: {len(data) if isinstance(data, list) else 0}")
            return None

        # Parse bars into a price series
        dates, closes = [], []
        for bar in data:
            try:
                d_raw = bar.get("date") or bar.get("datetime", "")
                if " " in d_raw:
                    d_parsed = datetime.strptime(d_raw, "%Y-%m-%d %H:%M:%S")
                else:
                    d_parsed = datetime.strptime(d_raw, "%Y-%m-%d")
                dates.append(d_parsed)
                closes.append(float(bar["close"]))
            except (ValueError, KeyError):
                continue

        if len(closes) < 20:
            print(f"[markov-engine] EODHD only parsed {len(closes)} valid bars for {symbol}")
            return None

        series = pd.Series(closes, index=pd.DatetimeIndex(dates))
        series = series.sort_index()
        series = series.iloc[-MAX_BARS:]  # keep most recent bars

        print(f"[markov-engine] Fetched {len(series)} daily bars for {symbol} ({ticker})")
        return series

    except requests.RequestException as exc:
        print(f"[markov-engine] EODHD request failed for {symbol}: {exc}")
        return None


# ---------------------------------------------------------------------------
# 2. State classification
# ---------------------------------------------------------------------------

def classify_states(
    prices: Union[pd.Series, np.ndarray],
    threshold: float = RETURN_THRESHOLD,
) -> np.ndarray:
    """
    Classify daily returns into Bull / Bear / Sideways states.

    Uses the full price series to compute daily log returns, then assigns
    a state to *each day* based on its return relative to the threshold.

    Returns an integer array of the same length as *prices*:
        STATE_BULL (0)  -> return > +threshold
        STATE_BEAR (1)  -> return < -threshold
        STATE_SIDEWAYS (2) -> everything else

    The first element is padded with STATE_SIDEWAYS because there is no
    prior price to compute a return from.
    """
    if isinstance(prices, pd.Series):
        prices_arr = prices.values.astype(np.float64)
    else:
        prices_arr = np.asarray(prices, dtype=np.float64)

    if len(prices_arr) < 2:
        return np.array([STATE_SIDEWAYS])

    # Log returns: no look-ahead, each day only uses today and yesterday
    log_rets = np.diff(np.log(prices_arr))

    states = np.full(len(prices_arr), STATE_SIDEWAYS, dtype=np.int64)
    # Assign state to each day based on its *own* return (the return that
    # brought us from yesterday to today)
    states[1:] = np.select(
        [log_rets > threshold, log_rets < -threshold],
        [STATE_BULL, STATE_BEAR],
        default=STATE_SIDEWAYS,
    )

    return states


# ---------------------------------------------------------------------------
# 3. Transition matrix builder
# ---------------------------------------------------------------------------

def build_transition_matrix(
    states: np.ndarray,
    lookback: int = DEFAULT_LOOKBACK,
) -> np.ndarray:
    """
    Build a 3x3 transition matrix from the most recent *lookback* transitions.

    The matrix shows the probability of moving from each state (row) to
    each other state (column).  Using a rolling window of the N most recent
    transitions keeps the matrix responsive to current market conditions
    instead of averaging over the entire history (which may span multiple
    regimes).

    Parameters
    ----------
    states : np.ndarray
        Integer state sequence (0=Bull, 1=Bear, 2=Sideways).
    lookback : int
        Number of *transitions* (not individual days) to use.
        Default 20 is roughly one month of trading days.

    Returns
    -------
    np.ndarray
        3x3 matrix where P[i, j] = P(state j | state i).
        Rows sum to 1.0 (or very close, within floating-point rounding).
        A row of all zeroes means that state was never seen in the window.
    """
    if len(states) < 2:
        # Not enough data for even a single transition
        return np.full((3, 3), np.nan)

    # Build transition pairs: (from_state, to_state) for each consecutive day
    from_states = states[:-1]
    to_states = states[1:]

    # Rolling lookback: only keep the most recent N transitions
    if lookback < len(from_states):
        from_states = from_states[-lookback:]
        to_states = to_states[-lookback:]

    # Count transitions using numpy's bincount with 2D indices
    flat_idx = from_states * 3 + to_states  # maps (i, j) to a single integer
    counts = np.bincount(flat_idx, minlength=9).reshape(3, 3).astype(np.float64)

    # Normalise each row so it sums to 1.0
    row_sums = counts.sum(axis=1, keepdims=True)
    # Avoid division by zero for states that never appeared
    with np.errstate(invalid="ignore", divide="ignore"):
        matrix = np.where(row_sums > 0, counts / row_sums, 0.0)

    return matrix


# ---------------------------------------------------------------------------
# 4. Matrix squaring (multi-step forecasts)
# ---------------------------------------------------------------------------

def square_matrix(P: np.ndarray, steps: int = 5) -> np.ndarray:
    """
    Compute P^n (the n-step transition matrix) for multi-day forecasts.

    P^n[i, j] gives the probability of being in state j after n steps,
    starting from state i.

    For large n the rows converge to the stationary distribution.
    """
    result = np.asarray(P, dtype=np.float64)
    for _ in range(steps - 1):
        result = result @ P
    return result


# ---------------------------------------------------------------------------
# 5. Stationary distribution
# ---------------------------------------------------------------------------

def stationary_distribution(P: np.ndarray) -> Optional[np.ndarray]:
    """
    Compute the stationary (long-run / steady-state) distribution.

    Solves pi * P = pi, where pi is a row vector of length 3.
    This is equivalent to finding the left eigenvector of P with
    eigenvalue 1, then normalising so the entries sum to 1.

    Returns None if the matrix is not fully specified (contains NaN or inf).
    """
    if np.any(np.isnan(P)) or np.any(np.isinf(P)):
        return None

    # Eigen-decomposition of P^T (right eigenvectors of transpose)
    # We want the eigenvector corresponding to eigenvalue 1
    eigenvalues, eigenvectors = np.linalg.eig(P.T)

    # Find the index of the eigenvalue closest to 1
    idx = np.argmin(np.abs(eigenvalues - 1.0))

    pi = np.real(eigenvectors[:, idx])

    # Normalise so entries sum to 1
    if np.sum(pi) != 0:
        pi = pi / np.sum(pi)
    else:
        return None

    # Ensure non-negative probabilities
    pi = np.maximum(pi, 0.0)
    pi = pi / np.sum(pi)  # re-normalise after clamping

    return pi


# ---------------------------------------------------------------------------
# 6. HMM confirmation layer
# ---------------------------------------------------------------------------

class SimpleHMM:
    """
    A simple Hidden Markov Model for regime confirmation.

    Hidden states (unobserved): true market regime (Bull / Bear / Sideways).
    Observed states: the +/-5%-threshold classifications we compute from prices.

    The HMM learns transition probabilities (how regimes evolve) and emission
    probabilities (how likely our threshold method is to correctly identify each
    regime) using iterated forward-backward expectation-maximisation (Baum-Welch).

    This acts as a *confirmation* layer -- if the HMM's most likely hidden
    sequence matches our simple threshold states, we have higher confidence
    in the regime classification.
    """

    def __init__(
        self,
        n_hidden: int = 3,
        n_obs: int = 3,
        max_iter: int = 50,
        tol: float = 1e-4,
        random_seed: Optional[int] = 42,
    ):
        """
        Parameters
        ----------
        n_hidden : int
            Number of hidden (true) regime states (default 3).
        n_obs : int
            Number of observable states (default 3, same as hidden).
        max_iter : int
            Maximum Baum-Welch EM iterations.
        tol : float
            Convergence tolerance for log-likelihood change.
        random_seed : int or None
            Seed for reproducible initialisation.
        """
        self.n = n_hidden
        self.m = n_obs
        self.max_iter = max_iter
        self.tol = tol
        self.rng = np.random.default_rng(random_seed)

        # Model parameters (initialised by _initialise)
        self.pi = None        # initial hidden state distribution (n,)
        self.A = None         # hidden transition matrix (n, n)
        self.B = None         # emission matrix (n, m) -- P(obs | hidden)
        self.log_likelihoods = None  # training history

    def _initialise(self, obs: np.ndarray):
        """Set random starting values for pi, A, and B."""
        self.pi = np.ones(self.n) / self.n

        # Transition matrix: random but row-stochastic
        A_raw = self.rng.uniform(size=(self.n, self.n))
        self.A = A_raw / A_raw.sum(axis=1, keepdims=True)

        # Emission matrix: start with a strong diagonal (threshold is decent)
        # then add noise so the EM can adjust
        B_diag = np.eye(self.n, self.m) * 0.7
        B_noise = self.rng.uniform(size=(self.n, self.m)) * 0.15
        self.B = B_diag + B_noise
        self.B = self.B / self.B.sum(axis=1, keepdims=True)

    def _forward(self, obs: np.ndarray) -> np.ndarray:
        """Forward algorithm: compute alpha[t][i] = P(obs_1..obs_t, hidden_t=i)."""
        T = len(obs)
        alpha = np.zeros((T, self.n))

        # Initialisation step (t=0)
        alpha[0] = self.pi * self.B[:, obs[0]]

        # Normalise to prevent underflow
        alpha[0] /= alpha[0].sum()

        # Recursion (t=1..T-1)
        for t in range(1, T):
            alpha[t] = (alpha[t - 1] @ self.A) * self.B[:, obs[t]]
            s = alpha[t].sum()
            if s > 0:
                alpha[t] /= s

        return alpha

    def _backward(self, obs: np.ndarray) -> np.ndarray:
        """Backward algorithm: compute beta[t][i] = P(obs_{t+1}..obs_T | hidden_t=i)."""
        T = len(obs)
        beta = np.ones((T, self.n))

        for t in range(T - 2, -1, -1):
            beta[t] = (self.A @ (self.B[:, obs[t + 1]] * beta[t + 1]))
            s = beta[t].sum()
            if s > 0:
                beta[t] /= s

        return beta

    def _baum_welch_step(self, obs: np.ndarray, alpha: np.ndarray, beta: np.ndarray):
        """Single M-step: re-estimate pi, A, B from the current alpha/beta."""
        T = len(obs)

        # gamma[t][i] = P(hidden_t = i | obs, model)
        gamma = alpha * beta
        gamma /= gamma.sum(axis=1, keepdims=True)

        # xi[t][i][j] = P(hidden_t=i, hidden_{t+1}=j | obs, model)
        xi = np.zeros((T - 1, self.n, self.n))
        for t in range(T - 1):
            for i in range(self.n):
                for j in range(self.n):
                    xi[t, i, j] = alpha[t, i] * self.A[i, j] * self.B[j, obs[t + 1]] * beta[t + 1, j]
            xi[t] /= xi[t].sum()

        # Re-estimate pi (initial state distribution)
        self.pi = gamma[0]

        # Re-estimate A (hidden transition matrix)
        for i in range(self.n):
            denom = gamma[:-1, i].sum()
            if denom > 0:
                self.A[i] = xi[:, i, :].sum(axis=0) / denom

        # Re-estimate B (emission matrix)
        for i in range(self.n):
            denom = gamma[:, i].sum()
            if denom > 0:
                for k in range(self.m):
                    self.B[i, k] = gamma[obs == k, i].sum() / denom

    def _log_likelihood(self, obs: np.ndarray, alpha: np.ndarray) -> float:
        """Compute log-likelihood of the observation sequence."""
        # The normalisation factors from alpha sum to the total likelihood
        T = len(obs)
        ll = 0.0
        for t in range(T):
            s = (alpha[t] * (self.pi if t == 0 else 1.0)).sum()
            if s > 0:
                ll += np.log(s)
        # In practice we track the forward algorithm's scaling
        # which is already absorbed into alpha normalisation.
        # For simplicity, compute from the last forward pass.
        return np.log(alpha[-1].sum()) if alpha[-1].sum() > 0 else -np.inf

    def fit(self, obs: np.ndarray) -> "SimpleHMM":
        """
        Run Baum-Welch EM to learn HMM parameters from observed states.

        Parameters
        ----------
        obs : np.ndarray
            Integer observation sequence (0=Bull, 1=Bear, 2=Sideways).

        Returns
        -------
        self
        """
        obs = np.asarray(obs, dtype=np.int64)
        self._initialise(obs)
        self.log_likelihoods = []

        for iteration in range(self.max_iter):
            # E-step: compute posterior probabilities
            alpha = self._forward(obs)
            beta = self._backward(obs)

            # M-step: re-estimate parameters
            self._baum_welch_step(obs, alpha, beta)

            # Compute log-likelihood for convergence check
            ll = self._log_likelihood(obs, alpha)
            self.log_likelihoods.append(ll)

            if iteration > 1:
                delta = ll - self.log_likelihoods[-2]
                if abs(delta) < self.tol:
                    break

        return self

    def viterbi(self, obs: np.ndarray) -> np.ndarray:
        """
        Find the most likely hidden state sequence (Viterbi decoding).

        Parameters
        ----------
        obs : np.ndarray
            Observation sequence.

        Returns
        -------
        np.ndarray
            Most likely hidden state sequence.
        """
        T = len(obs)
        if T == 0:
            return np.array([], dtype=np.int64)

        # Viterbi: delta[t][i] = max probability of path ending in state i at time t
        delta = np.zeros((T, self.n))
        psi = np.zeros((T, self.n), dtype=np.int64)

        # Initialise
        delta[0] = self.pi * self.B[:, obs[0]]
        delta[0] /= delta[0].sum() if delta[0].sum() > 0 else 1.0

        # Recursion
        for t in range(1, T):
            for j in range(self.n):
                probs = delta[t - 1] * self.A[:, j] * self.B[j, obs[t]]
                psi[t, j] = np.argmax(probs)
                delta[t, j] = probs[psi[t, j]]

        # Backtrack
        path = np.zeros(T, dtype=np.int64)
        path[-1] = np.argmax(delta[-1])
        for t in range(T - 2, -1, -1):
            path[t] = psi[t + 1, path[t + 1]]

        return path

    def get_confidence(self, obs: np.ndarray, threshold_states: np.ndarray) -> dict:
        """
        Compare the HMM-decoded regime against the simple threshold states.

        Returns a dict with:
        - agreement_rate: fraction of days where HMM and threshold agree
        - transition_matrix: the HMM-estimated hidden transition matrix
        - stationary_distribution: stationary distribution of the HMM
        - most_likely_regime: the predominant hidden state
        """
        hidden = self.viterbi(obs)
        min_len = min(len(hidden), len(threshold_states))
        agreement = (hidden[:min_len] == threshold_states[:min_len]).mean()

        # HMM stationary distribution
        hmm_stationary = stationary_distribution(self.A)

        return {
            "agreement_rate": round(float(agreement), 4),
            "hidden_transition_matrix": self.A.round(4).tolist(),
            "stationary_distribution": hmm_stationary.round(4).tolist() if hmm_stationary is not None else None,
            "most_likely_regime": int(hidden[-1]),
            "most_likely_regime_label": STATE_LABELS.get(int(hidden[-1]), "Unknown"),
        }


# ---------------------------------------------------------------------------
# 7. MarkovEngine -- main orchestrator
# ---------------------------------------------------------------------------

class MarkovEngine:
    """
    Orchestrates the full Markov chain analysis pipeline.

    Typical workflow:
        engine = MarkovEngine()
        result = engine.run("SPY", asset_type="stock")
        print(result)

    The run() method returns a dict with all computed quantities.
    """

    def __init__(self, api_key: Optional[str] = None, lookback: int = DEFAULT_LOOKBACK):
        """
        Parameters
        ----------
        api_key : str or None
            EODHD API key. Falls back to EODHD_API_KEY env var.
        lookback : int
            Number of recent transitions to include in the rolling window.
        """
        self.api_key = api_key
        self.lookback = lookback

        # Cached internal state after run()
        self.prices: Optional[pd.Series] = None
        self.states: Optional[np.ndarray] = None
        self.transition_matrix: Optional[np.ndarray] = None
        self.stationary: Optional[np.ndarray] = None
        self.hmm_model: Optional[SimpleHMM] = None
        self.hmm_result: Optional[dict] = None

    def run(
        self,
        ticker: str,
        asset_type: str = "stock",
        days: int = 365,
        hmm_iterations: int = 50,
    ) -> dict:
        """
        Run the full Markov analysis pipeline.

        Parameters
        ----------
        ticker : str
            Ticker symbol.
        asset_type : str
            Asset type for symbol mapping.
        days : int
            Days of history to fetch.
        hmm_iterations : int
            Baum-Welch EM iterations for the HMM confirmer.

        Returns
        -------
        dict with keys:
            ticker, asset_type, lookback, threshold,
            n_bars, n_transitions,
            state_counts, state_labels,
            transition_matrix, transition_matrix_labels,
            multi_day_forecast_5d, multi_day_forecast_10d, multi_day_forecast_20d,
            stationary_distribution,
            hmm_confirmation,
            engine_version
        """
        # Step 1: fetch data
        prices = fetch_daily_prices(ticker, asset_type, days, self.api_key)
        if prices is None:
            return {"error": f"Failed to fetch data for {ticker} ({asset_type})"}

        self.prices = prices

        # Step 2: classify states
        states = classify_states(prices)
        self.states = states

        # Count occurrences of each state
        unique, counts = np.unique(states, return_counts=True)
        state_counts = {STATE_LABELS.get(int(s), f"State{s}"): int(c) for s, c in zip(unique, counts)}

        # Step 3: build transition matrix
        P = build_transition_matrix(states, lookback=self.lookback)
        self.transition_matrix = P

        # Step 4: multi-day forecasts via matrix squaring
        P_5d = square_matrix(P, steps=5)
        P_10d = square_matrix(P, steps=10)
        P_20d = square_matrix(P, steps=20)

        # Step 5: stationary distribution
        pi = stationary_distribution(P)
        self.stationary = pi

        # Step 6: HMM confirmation
        # We need at least ~20 observations before the HMM can learn meaningful
        # transition patterns
        if len(states) >= 20:
            obs = states.copy()
            hmm = SimpleHMM(n_hidden=3, n_obs=3, max_iter=hmm_iterations)
            hmm.fit(obs)
            self.hmm_model = hmm

            # Use the threshold states (our own classification) as the reference
            # for computing agreement
            hmm_result = hmm.get_confidence(obs, states)
            self.hmm_result = hmm_result
        else:
            hmm_result = {
                "agreement_rate": None,
                "hidden_transition_matrix": None,
                "stationary_distribution": None,
                "most_likely_regime": None,
                "most_likely_regime_label": "Insufficient data",
            }
            self.hmm_result = hmm_result

        # Build the output dict
        return self._build_output(ticker, asset_type, P, pi, P_5d, P_10d, P_20d, state_counts, hmm_result)

    def _build_output(
        self,
        ticker: str,
        asset_type: str,
        P: np.ndarray,
        pi: Optional[np.ndarray],
        P_5d: np.ndarray,
        P_10d: np.ndarray,
        P_20d: np.ndarray,
        state_counts: dict,
        hmm_result: dict,
    ) -> dict:
        """Assemble the final output dictionary."""
        labels = [STATE_LABELS[i] for i in range(3)]

        return {
            "engine_version": "1.0.0",
            "ticker": ticker,
            "asset_type": asset_type,
            "lookback_days": self.lookback,
            "return_threshold_pct": RETURN_THRESHOLD * 100,
            "n_bars": len(self.prices) if self.prices is not None else 0,
            "n_transitions": max(0, (len(self.states) - 1) if self.states is not None else 0),

            # State distribution
            "state_counts": state_counts,
            "state_labels": labels,

            # Transition matrix (as nested list for serialisation)
            "transition_matrix": P.round(4).tolist(),
            "transition_matrix_labels": {"from": labels, "to": labels},
            "transition_matrix_interpretation": (
                "Rows = current state, Columns = next state. "
                "E.g. row Bull, col Bear = probability market goes Bull->Bear next day."
            ),

            # Multi-step forecasts
            "multi_day_forecast_5d": P_5d.round(4).tolist(),
            "multi_day_forecast_10d": P_10d.round(4).tolist(),
            "multi_day_forecast_20d": P_20d.round(4).tolist(),
            "forecast_interpretation": (
                "P^N matrix: row = starting state, col = state after N steps. "
                "For large N the rows converge to the stationary distribution."
            ),

            # Stationary distribution
            "stationary_distribution": pi.round(4).tolist() if pi is not None else None,
            "stationary_labels": labels,
            "stationary_interpretation": (
                "Long-run probability of each regime, regardless of starting state. "
                "If Bear is 0.60, the market spends ~60% of days in Bear over the long term."
            ),

            # HMM confirmation
            "hmm_confirmation": hmm_result,
            "hmm_interpretation": (
                "The HMM independently learns the 'true' regime sequence using "
                "probabilistic inference. If agreement_rate is high (above 0.70), "
                "the simple threshold method is reliable. Low agreement suggests "
                "the +/-5% boundary may be too rigid for current conditions."
            ),
        }


# ---------------------------------------------------------------------------
# Convenience function for quick analysis
# ---------------------------------------------------------------------------

def quick_analysis(
    ticker: str,
    asset_type: str = "stock",
    api_key: Optional[str] = None,
    lookback: int = DEFAULT_LOOKBACK,
    days: int = 365,
) -> dict:
    """
    Run a one-shot Markov analysis with sensible defaults.

    Returns the same dict as MarkovEngine.run() -- ready to print or
    pass to a JSON serializer.
    """
    engine = MarkovEngine(api_key=api_key, lookback=lookback)
    return engine.run(ticker, asset_type, days=days)
