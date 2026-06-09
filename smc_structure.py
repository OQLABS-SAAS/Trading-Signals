"""DotVerse SMC market-structure detection — extracted from app.py (monolith
split, step 2). Pure pandas/numpy: a price DataFrame in, a structure dict out.
Detects FVG, liquidity grabs, displacement candles and CHoCH from CONFIRMED
(closed) candles only — the live forming bar is excluded to prevent repaint.
"""

def detect_smc_structures(df):
    """
    Detect Smart Money Concept structures from OHLCV data.
    Returns a dict with four boolean flags and context for each:
      fvg_bullish   : bullish Fair Value Gap in the last 10 bars
      fvg_bearish   : bearish Fair Value Gap in the last 10 bars
      liquidity_grab_bull : swing-high sweep + rejection (bullish)
      liquidity_grab_bear : swing-low sweep + rejection (bearish)
      displacement_bull   : bullish displacement candle (body > 2× ATR)
      displacement_bear   : bearish displacement candle
      choch_bull          : Change of Character bullish (first swing-high break after downtrend)
      choch_bear          : Change of Character bearish (first swing-low break after uptrend)
    All detection is purely mechanical on OHLCV — no LLMs, no pattern-matching heuristics.
    Returns empty dict (all False) if df has fewer than 20 bars.
    """
    result = {
        "fvg_bullish": False, "fvg_bearish": False,
        "liquidity_grab_bull": False, "liquidity_grab_bear": False,
        "displacement_bull": False, "displacement_bear": False,
        "choch_bull": False, "choch_bear": False,
        # Price levels — set to actual price when pattern fires, None otherwise
        "fvg_bullish_level": None, "fvg_bearish_level": None,
        "liquidity_grab_bull_level": None, "liquidity_grab_bear_level": None,
        "displacement_bull_level": None, "displacement_bear_level": None,
        "choch_bull_level": None, "choch_bear_level": None,
    }
    try:
        import pandas as pd, numpy as np
        if df is None or len(df) < 20:
            return result

        # Normalise column names — yfinance returns lowercase after auto_adjust
        df = df.copy()
        df.columns = [c.lower() if isinstance(c, str) else str(c[0]).lower() for c in df.columns]

        hi  = df["high"].values
        lo  = df["low"].values
        cl  = df["close"].values
        op  = df["open"].values
        # ── Anti-repaint: drop the live, still-forming candle so structure is read
        # ONLY from confirmed (closed) bars. Without this, an unconfirmed FVG/
        # displacement/liquidity/CHoCH on the current bar can spike confidence and
        # then vanish on the next tick — making a SELL look valid into an up-move.
        if len(cl) >= 21:
            hi, lo, cl, op = hi[:-1], lo[:-1], cl[:-1], op[:-1]
        n   = len(hi)

        # ── ATR for displacement threshold ─────────────────────────────────
        tr = np.maximum(hi[1:] - lo[1:],
             np.maximum(np.abs(hi[1:] - cl[:-1]),
                        np.abs(lo[1:] - cl[:-1])))
        atr = float(np.mean(tr[-14:])) if len(tr) >= 14 else float(np.mean(tr))

        # ── 1. Fair Value Gap (FVG) ─────────────────────────────────────────
        # Bullish FVG: candle[i-2] high < candle[i] low — gap not filled by candle[i-1]
        # Bearish FVG: candle[i-2] low  > candle[i] high — gap not filled by candle[i-1]
        # Check last 10 complete bars for a recent unfilled FVG.
        for i in range(max(2, n-10), n):
            if lo[i] > hi[i-2]:           # gap between c[i-2] top and c[i] bottom
                result["fvg_bullish"] = True
                result["fvg_bullish_level"] = round(float((hi[i-2] + lo[i]) / 2), 6)
            if hi[i] < lo[i-2]:           # gap between c[i-2] bottom and c[i] top
                result["fvg_bearish"] = True
                result["fvg_bearish_level"] = round(float((lo[i-2] + hi[i]) / 2), 6)

        # ── 2. Liquidity Grab ───────────────────────────────────────────────
        # Find equal highs/lows in recent 20 bars (within 0.1% tolerance).
        # Bullish grab: equal lows swept (lo pierces below) then candle closes ABOVE them.
        # Bearish grab: equal highs swept (hi pierces above) then candle closes BELOW them.
        tol = 0.001  # 0.1%
        for i in range(5, n):
            # equal lows in [i-5 .. i-1]
            ref_lo = lo[i-5:i]
            eq_lo  = ref_lo[np.abs(ref_lo - ref_lo.min()) / max(ref_lo.min(), 1e-9) < tol]
            if len(eq_lo) >= 2:
                sweep_level = eq_lo.min()
                if lo[i] < sweep_level and cl[i] > sweep_level:
                    result["liquidity_grab_bull"] = True
                    result["liquidity_grab_bull_level"] = round(float(sweep_level), 6)
            # equal highs in [i-5 .. i-1]
            ref_hi = hi[i-5:i]
            eq_hi  = ref_hi[np.abs(ref_hi - ref_hi.max()) / max(ref_hi.max(), 1e-9) < tol]
            if len(eq_hi) >= 2:
                sweep_level = eq_hi.max()
                if hi[i] > sweep_level and cl[i] < sweep_level:
                    result["liquidity_grab_bear"] = True
                    result["liquidity_grab_bear_level"] = round(float(sweep_level), 6)

        # ── 3. Displacement candle ──────────────────────────────────────────
        # Body > 2× ATR in the last 5 bars = institutional order flow entering.
        for i in range(max(0, n-5), n):
            body = abs(cl[i] - op[i])
            if body > 2 * atr:
                if cl[i] > op[i]:
                    result["displacement_bull"] = True
                    result["displacement_bull_level"] = round(float(cl[i]), 6)
                else:
                    result["displacement_bear"] = True
                    result["displacement_bear_level"] = round(float(cl[i]), 6)

        # ── 4. Change of Character (CHOCH) ──────────────────────────────────
        # Detect the FIRST break of a swing high after a series of lower-highs
        # (downtrend), or FIRST break of swing low after series of higher-lows.
        # Use last 20 bars. Minimum 3 swings needed.
        def _swings(prices, order=3):
            """Return indices of local pivot highs or lows."""
            pivots = []
            for j in range(order, len(prices) - order):
                if all(prices[j] >= prices[j-k] for k in range(1, order+1)) and \
                   all(prices[j] >= prices[j+k] for k in range(1, order+1)):
                    pivots.append(j)
            return pivots

        window = min(n, 30)
        hi_w   = hi[-window:]
        lo_w   = lo[-window:]
        cl_w   = cl[-window:]

        swing_highs = _swings(hi_w, order=2)
        swing_lows  = _swings(lo_w, order=2)

        # CHOCH bullish: after 2+ lower-highs, last bar closes above the last swing high
        if len(swing_highs) >= 2:
            sh_vals = [hi_w[j] for j in swing_highs]
            if sh_vals[-1] < sh_vals[-2]:           # lower-high pattern confirmed
                last_sh = hi_w[swing_highs[-1]]
                if cl_w[-1] > last_sh:              # price now breaks above it → CHOCH bull
                    result["choch_bull"] = True
                    result["choch_bull_level"] = round(float(last_sh), 6)

        # CHOCH bearish: after 2+ higher-lows, last bar closes below the last swing low
        if len(swing_lows) >= 2:
            sl_vals = [lo_w[j] for j in swing_lows]
            if sl_vals[-1] > sl_vals[-2]:           # higher-low pattern confirmed
                last_sl = lo_w[swing_lows[-1]]
                if cl_w[-1] < last_sl:              # price now breaks below it → CHOCH bear
                    result["choch_bear"] = True
                    result["choch_bear_level"] = round(float(last_sl), 6)

    except Exception as e:
        print(f"[smc] detect_smc_structures error: {e}")

    return result
