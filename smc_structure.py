"""DotVerse SMC market-structure detection — extracted from app.py (monolith
split, step 2). Pure pandas/numpy: a price DataFrame in, a structure dict out.
Detects FVG, liquidity grabs, displacement candles, CHoCH, and Order Blocks
from CONFIRMED (closed) candles only — the live forming bar is excluded to
prevent repaint.
"""


def detect_order_blocks(df, atr_series=None):
    """
    Detect True Order Blocks from OHLCV price data.

    An Order Block is the last opposite-colour candle immediately before a
    displacement candle (body > 2× ATR).  The OB candle marks where
    institutional orders were placed; price is expected to react if it
    returns to that zone.

    Rules (all on CONFIRMED/closed bars, live bar stripped):
      - Bullish displacement (bull body > 2×ATR) → look back for the last
        BEARISH candle before it → that candle is a BULLISH OB (demand zone).
      - Bearish displacement (bear body > 2×ATR) → last BULLISH candle before
        it → BEARISH OB (supply zone).

    State flags are updated by scanning ALL subsequent bars after formation:
      fresh      : True until price trades back INTO the zone [zone_low, zone_high].
      mitigated  : True once price has traded fully THROUGH the zone
                   (both hi > zone_high AND lo < zone_low seen in the same bar,
                   or successive bars that complete the through-trade).
      times_tested: count of bars that trade into the zone after formation.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV with columns open/high/low/close (case-insensitive).
        Needs at least 20 rows.
    atr_series : pd.Series, optional
        Pre-computed ATR aligned to df.index.  Computed internally (14-period
        EWM) if not supplied.

    Returns
    -------
    list[dict]  — newest OB last.  Each dict:
        index              int positional index in the (confirmed) array
        timestamp          the index value of the OB bar (datetime or int)
        direction          'bullish' | 'bearish'
        zone_high          float
        zone_low           float
        displacement_size_atr  float  (body of the displacement / ATR)
        volume_at_formation    float | None
        fresh              bool
        mitigated          bool
        times_tested       int
    """
    import numpy as np
    import pandas as pd

    result = []
    try:
        if df is None or len(df) < 20:
            return result

        df = df.copy()
        df.columns = [c.lower() if isinstance(c, str) else str(c[0]).lower()
                      for c in df.columns]

        has_vol = "volume" in df.columns or "vol" in df.columns
        vol_col = "volume" if "volume" in df.columns else ("vol" if "vol" in df.columns else None)

        # Drop the live forming bar (anti-repaint, same policy as detect_smc_structures)
        confirmed = df.iloc[:-1] if len(df) >= 21 else df

        hi  = confirmed["high"].values.astype(float)
        lo  = confirmed["low"].values.astype(float)
        cl  = confirmed["close"].values.astype(float)
        op  = confirmed["open"].values.astype(float)
        idx = confirmed.index
        vol = confirmed[vol_col].values.astype(float) if has_vol and vol_col else None
        n   = len(hi)

        # ── ATR (14-period EWM, matches scalein_vs_single_backtest.py) ────────
        if atr_series is not None:
            # Align; fill forward any gaps
            atr_aligned = atr_series.reindex(confirmed.index).ffill().values.astype(float)
        else:
            tr = np.maximum(hi[1:] - lo[1:],
                 np.maximum(np.abs(hi[1:] - cl[:-1]),
                            np.abs(lo[1:] - cl[:-1])))
            # Build a per-bar ATR array (EWM alpha=1/14, same as backtest helper)
            alpha = 1.0 / 14
            atr_arr = np.empty(n)
            atr_arr[0] = np.nan
            atr_arr[1] = tr[0]
            for k in range(2, n):
                atr_arr[k] = alpha * tr[k - 1] + (1 - alpha) * atr_arr[k - 1]
            atr_aligned = atr_arr

        body = np.abs(cl - op)

        # ── Find displacement candles ─────────────────────────────────────────
        for i in range(1, n):
            a = atr_aligned[i]
            if np.isnan(a) or a <= 0:
                continue
            if body[i] <= 2.0 * a:
                continue

            bull_disp = cl[i] > op[i]   # bullish displacement → look for last bearish OB
            bear_disp = cl[i] < op[i]   # bearish displacement → look for last bullish OB

            # ── Step back to find last opposite-colour candle ─────────────────
            ob_idx = None
            for j in range(i - 1, -1, -1):
                if bull_disp and cl[j] < op[j]:   # bearish candle → bullish OB
                    ob_idx = j
                    break
                if bear_disp and cl[j] > op[j]:   # bullish candle → bearish OB
                    ob_idx = j
                    break

            if ob_idx is None:
                continue

            direction = "bullish" if bull_disp else "bearish"
            z_hi = float(hi[ob_idx])
            z_lo = float(lo[ob_idx])
            disp_size_atr = float(body[i] / a)
            vol_at_form = float(vol[ob_idx]) if vol is not None else None

            # ── Scan ALL bars AFTER displacement to compute state ─────────────
            fresh = True
            mitigated = False
            times_tested = 0
            through_hi_seen = False
            through_lo_seen = False

            for k in range(i + 1, n):
                bar_enters_zone = lo[k] <= z_hi and hi[k] >= z_lo
                if bar_enters_zone:
                    if fresh:
                        fresh = False
                    times_tested += 1
                    # Through-trade detection: bar trades past both sides
                    if hi[k] > z_hi:
                        through_hi_seen = True
                    if lo[k] < z_lo:
                        through_lo_seen = True
                    if through_hi_seen and through_lo_seen:
                        mitigated = True

            result.append(dict(
                index=ob_idx,
                timestamp=idx[ob_idx],
                direction=direction,
                zone_high=round(z_hi, 8),
                zone_low=round(z_lo, 8),
                displacement_size_atr=round(disp_size_atr, 4),
                volume_at_formation=vol_at_form,
                fresh=fresh,
                mitigated=mitigated,
                times_tested=times_tested,
            ))

    except Exception as e:
        print(f"[smc] detect_order_blocks error: {e}")

    # Sort by OB index (formation order), newest last
    result.sort(key=lambda x: x["index"])
    return result


def detect_inducement(df, order_blocks=None, atr_series=None):
    """
    Detect Inducement (IDM) zones from OHLCV price data.

    An inducement is a minor opposing liquidity pool — a shallow opposing
    swing point or equal-highs/equal-lows cluster — sitting BETWEEN the
    current price and a true order block zone.  Smart money sweeps these
    minor pools before returning to the OB to fill institutional orders.
    Identifying unswept inducements explains *why* price has not yet reached
    the OB: the minor pool must first be consumed.

    Detection rules (all on confirmed/closed bars, live bar stripped):
      1. Minor swing highs/lows: local fractals with lookback=2 (i.e. the
         bar at position j is higher than the 2 bars on each side).  These
         are "minor" because the lookback is intentionally short; structural
         swings use a larger lookback (3–5).
      2. Equal-highs / equal-lows clusters: ≥2 touches within 0.1×ATR of
         each other in a rolling 20-bar window (conservative: at least 2
         touches before we call it a cluster).
      3. For each FRESH order block, check whether any such minor swing /
         cluster lies BETWEEN the most-recent close and the OB zone:
           - Bullish OB (demand below): look for minor swing LOWS or equal-
             lows between price and the OB zone_high (i.e. above the OB but
             below price).
           - Bearish OB (supply above): look for minor swing HIGHS or equal-
             highs between the OB zone_low and price.
      4. The 'swept' flag is True if price has already traded THROUGH the
         IDM level after its formation bar.

    This is the most subjective SMC concept.  We stay conservative:
      - Only clear fractals (lookback ≥ 2) qualify as minor swings.
      - Equal clusters require ≥ 2 confirmed touches within 0.1×ATR.
      - Only FRESH (unmitigated) OBs are considered.
      - Every emitted item carries enough metadata to explain itself.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV with columns open/high/low/close (case-insensitive).
        Needs at least 20 rows.
    order_blocks : list[dict], optional
        Pre-computed OBs (from detect_order_blocks).  Computed internally
        if not supplied.
    atr_series : pd.Series, optional
        Pre-computed ATR aligned to df.index.

    Returns
    -------
    list[dict]  — formation order, newest last.  Each dict:
        idm_price      float  — the level of the minor swing / cluster
        idm_type       str    — 'minor_swing' | 'equal_hl'
        ob_index       int    — positional index of the guarded OB
        ob_direction   str    — 'bullish' | 'bearish'
        side           str    — 'high' | 'low' (which side the IDM is on)
        formation_bar  int    — positional index in confirmed array where IDM formed
        swept          bool   — True if price has already traded through idm_price
        distance_atr   float  — |last_close - idm_price| / ATR at last bar
    """
    import numpy as np
    import pandas as pd

    result = []
    try:
        if df is None or len(df) < 20:
            return result

        df = df.copy()
        df.columns = [c.lower() if isinstance(c, str) else str(c[0]).lower()
                      for c in df.columns]

        # Drop live forming bar (anti-repaint)
        confirmed = df.iloc[:-1] if len(df) >= 21 else df

        hi  = confirmed["high"].values.astype(float)
        lo  = confirmed["low"].values.astype(float)
        cl  = confirmed["close"].values.astype(float)
        op  = confirmed["open"].values.astype(float)
        idx = confirmed.index
        n   = len(hi)

        # ── ATR ────────────────────────────────────────────────────────────────
        if atr_series is not None:
            atr_aligned = atr_series.reindex(confirmed.index).ffill().values.astype(float)
        else:
            tr = np.maximum(hi[1:] - lo[1:],
                 np.maximum(np.abs(hi[1:] - cl[:-1]),
                            np.abs(lo[1:] - cl[:-1])))
            alpha = 1.0 / 14
            atr_arr = np.empty(n)
            atr_arr[0] = np.nan
            atr_arr[1] = tr[0]
            for k in range(2, n):
                atr_arr[k] = alpha * tr[k - 1] + (1 - alpha) * atr_arr[k - 1]
            atr_aligned = atr_arr

        # Last confirmed ATR (used for distance calculation)
        last_atr = float(atr_aligned[~np.isnan(atr_aligned)][-1]) if not np.all(np.isnan(atr_aligned)) else 1.0
        last_close = float(cl[-1])

        # ── Order Blocks ───────────────────────────────────────────────────────
        if order_blocks is None:
            order_blocks = detect_order_blocks(confirmed)

        fresh_obs = [ob for ob in order_blocks if ob.get("fresh", False) and not ob.get("mitigated", False)]
        if not fresh_obs:
            return result

        # ── 1. Minor swing fractals (lookback=2) ──────────────────────────────
        # A minor swing high at bar j: hi[j] > hi[j-1], hi[j-2] AND hi[j] > hi[j+1], hi[j+2]
        # A minor swing low at bar j:  lo[j] < lo[j-1], lo[j-2] AND lo[j] < lo[j+1], lo[j+2]
        FRAC = 2
        minor_swing_highs = []  # list of (bar_index, price)
        minor_swing_lows  = []  # list of (bar_index, price)
        for j in range(FRAC, n - FRAC):
            is_sh = all(hi[j] > hi[j - k] for k in range(1, FRAC + 1)) and \
                    all(hi[j] > hi[j + k] for k in range(1, FRAC + 1))
            if is_sh:
                minor_swing_highs.append((j, hi[j]))
            is_sl = all(lo[j] < lo[j - k] for k in range(1, FRAC + 1)) and \
                    all(lo[j] < lo[j + k] for k in range(1, FRAC + 1))
            if is_sl:
                minor_swing_lows.append((j, lo[j]))

        # ── 2. Equal-highs / equal-lows clusters (pairwise, any level) ──────────
        # For each pair of bars (i, j) with j > i and j - i <= EQL_WINDOW,
        # check whether their highs (or lows) are within 0.1×ATR.  If so,
        # that shared level is an equal-highs/lows cluster.  Report the last
        # touch bar and the average level as the cluster price.
        # Conservative: only pairs; ≥2 touches suffice (i.e. exactly 2 bars).
        # We skip the dedup pass across all bar pairs for performance; instead
        # we accumulate clusters into a level-keyed dict (rounded to 2×tol grid)
        # and retain the one with the highest last_touch_bar per cell.
        EQL_WINDOW = 20

        def _find_equal_clusters(prices_arr, tol_arr):
            """Return list of (last_touch_bar, level) for repeated prices."""
            m = len(prices_arr)
            clusters = {}  # key = grid cell, value = (last_touch_bar, level)
            for ii in range(m):
                for jj in range(ii + 1, min(ii + EQL_WINDOW + 1, m)):
                    tol_here = max(tol_arr[ii], tol_arr[jj])
                    diff = abs(prices_arr[ii] - prices_arr[jj])
                    if diff <= tol_here:
                        level = (prices_arr[ii] + prices_arr[jj]) / 2.0
                        # Grid key: bucket the level into cells of size tol_here
                        cell = round(level / max(tol_here, 1e-12))
                        if cell not in clusters or clusters[cell][0] < jj:
                            clusters[cell] = (jj, level)
            return sorted(clusters.values(), key=lambda x: x[0])

        eq_tol_arr = np.where(np.isnan(atr_aligned), last_atr, atr_aligned) * 0.1
        equal_highs = _find_equal_clusters(hi, eq_tol_arr)
        equal_lows  = _find_equal_clusters(lo, eq_tol_arr)

        # ── 3. Match IDM candidates to fresh OBs ─────────────────────────────
        # For each fresh OB, gather IDM candidates that sit BETWEEN price and the zone.
        # Then determine 'swept' by checking if subsequent bars traded through the IDM.

        seen_keys = set()   # (ob_index, idm_price_rounded) — prevent duplicates

        for ob in fresh_obs:
            ob_idx   = ob["index"]
            ob_dir   = ob["direction"]
            z_hi     = ob["zone_high"]
            z_lo     = ob["zone_low"]

            candidates = []  # (formation_bar, level, idm_type, side)

            if ob_dir == "bullish":
                # Demand zone BELOW price.  IDM = minor swing lows or equal-lows
                # that sit ABOVE the zone (z_hi) and BELOW the current close.
                # Price must dip to sweep these lows before reaching the OB.
                for (bar_j, price_j) in minor_swing_lows:
                    if bar_j > ob_idx and z_hi <= price_j <= last_close:
                        candidates.append((bar_j, price_j, "minor_swing", "low"))
                for (bar_j, price_j) in equal_lows:
                    if bar_j > ob_idx and z_hi <= price_j <= last_close:
                        candidates.append((bar_j, price_j, "equal_hl", "low"))
            else:
                # Supply zone ABOVE price.  IDM = minor swing highs or equal-highs
                # that sit BELOW the zone (z_lo) and ABOVE the current close.
                for (bar_j, price_j) in minor_swing_highs:
                    if bar_j > ob_idx and last_close <= price_j <= z_lo:
                        candidates.append((bar_j, price_j, "minor_swing", "high"))
                for (bar_j, price_j) in equal_highs:
                    if bar_j > ob_idx and last_close <= price_j <= z_lo:
                        candidates.append((bar_j, price_j, "equal_hl", "high"))

            for (form_bar, idm_price, idm_type, side) in candidates:
                key = (ob_idx, round(idm_price, 6))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                # 'swept' = price has traded THROUGH the IDM level after formation
                swept = False
                for k in range(form_bar + 1, n):
                    if side == "low" and lo[k] < idm_price:
                        swept = True
                        break
                    if side == "high" and hi[k] > idm_price:
                        swept = True
                        break

                dist_atr = abs(last_close - idm_price) / last_atr if last_atr > 0 else 0.0

                result.append(dict(
                    idm_price=round(idm_price, 8),
                    idm_type=idm_type,
                    ob_index=ob_idx,
                    ob_direction=ob_dir,
                    side=side,
                    formation_bar=int(form_bar),
                    swept=swept,
                    distance_atr=round(dist_atr, 4),
                ))

    except Exception as e:
        print(f"[smc] detect_inducement error: {e}")

    # Sort by formation order, newest last
    result.sort(key=lambda x: x["formation_bar"])
    return result


def assess_entry_liquidity_risk(df, entry_price, direction, atr_series=None,
                                proximity_atr=0.5):
    """
    Pre-trade liquidity-trap AVOIDANCE check (D3).

    Scans confirmed (closed) bars for liquidity clusters — equal-highs/equal-lows
    pools and obvious swing-extreme pools (recent fractal highs/lows where stops
    accumulate).  If the proposed entry price sits within proximity_atr × ATR of a
    cluster on the STOP side (below entry for a BUY, above for a SELL), warns the
    caller and suggests waiting for a sweep-and-reclaim.

    Detection rules (all on confirmed bars, live bar stripped):
      Equal-highs/equal-lows clusters: ≥ 2 touches within 0.1 × ATR in a rolling
        20-bar window. The repeated level is where resting stops accumulate.
      Swing-extreme pools: fractal highs/lows with lookback = 3 in the last 60
        bars.  Recent swing extremes reliably attract stop-hunting.

    Proximity check:
      BUY entry: cluster on the LOW side (below entry) within proximity_atr × ATR
        → stops below entry are vulnerable.
      SELL entry: cluster on the HIGH side (above entry) within proximity_atr × ATR
        → stops above entry are vulnerable.
      The NEAREST at-risk cluster is returned (smallest distance_atr).

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV with columns open/high/low/close (case-insensitive).
        Needs at least 20 rows.
    entry_price : float
        Proposed entry price (the level the caller intends to enter at).
    direction : str
        'BUY' or 'SELL' (case-insensitive).
    atr_series : pd.Series, optional
        Pre-computed ATR aligned to df.index.  Computed internally if not supplied.
    proximity_atr : float
        ATR multiples within which a cluster is considered "at risk".
        Default 0.5 — half an ATR.  Conservative: set lower to be more selective.

    Returns
    -------
    dict:
        at_risk : bool
            True if entry sits within proximity_atr × ATR of a stop-side cluster.
        If at_risk is True, also includes:
            cluster_price  : float — the level of the nearest at-risk cluster.
            cluster_type   : 'equal_lows' | 'equal_highs' | 'swing_pool'
            distance_atr   : float — |entry_price - cluster_price| / ATR
            touches        : int   — number of times price has touched this level
            suggestion     : dict
                wait_for        : 'sweep_and_reclaim'
                description     : str — plain-English advisory
                alt_entry_hint  : float — approximate entry after reclaim
    """
    import numpy as np
    import pandas as pd

    try:
        if df is None or len(df) < 20:
            return {"at_risk": False}

        df = df.copy()
        df.columns = [c.lower() if isinstance(c, str) else str(c[0]).lower()
                      for c in df.columns]

        # Drop live forming bar (anti-repaint, same policy as the rest of smc_structure)
        confirmed = df.iloc[:-1] if len(df) >= 21 else df

        hi  = confirmed["high"].values.astype(float)
        lo  = confirmed["low"].values.astype(float)
        cl  = confirmed["close"].values.astype(float)
        n   = len(hi)

        # ── ATR ───────────────────────────────────────────────────────────────
        if atr_series is not None:
            atr_aligned = atr_series.reindex(confirmed.index).ffill().values.astype(float)
        else:
            tr = np.maximum(hi[1:] - lo[1:],
                 np.maximum(np.abs(hi[1:] - cl[:-1]),
                            np.abs(lo[1:] - cl[:-1])))
            alpha = 1.0 / 14
            atr_arr = np.empty(n)
            atr_arr[0] = np.nan
            atr_arr[1] = tr[0]
            for k in range(2, n):
                atr_arr[k] = alpha * tr[k - 1] + (1 - alpha) * atr_arr[k - 1]
            atr_aligned = atr_arr

        # Use the ATR at the last confirmed bar (most recent read)
        valid_atr = atr_aligned[~np.isnan(atr_aligned)]
        if len(valid_atr) == 0:
            return {"at_risk": False}
        current_atr = float(valid_atr[-1])
        if current_atr <= 0:
            return {"at_risk": False}

        eq_tol = 0.1 * current_atr    # tolerance for equal-level clustering
        EQL_WINDOW = 20               # bar window for equal-cluster search
        SWING_LOOKBACK = 3            # fractal order for swing-pool detection
        SWING_SCAN = 60               # how far back to scan for swing pools
        direction_upper = direction.upper()

        clusters = []  # list of (cluster_price, cluster_type, touches, distance_atr)

        # ── 1. Equal-highs clusters (stop-side for SELL) ──────────────────────
        # For a SELL, equal-highs above entry are a danger zone (stops resting above).
        # We also surface equal-lows for awareness, but filter later by direction.
        def _equal_clusters(prices_arr, tol):
            """
            Find groups of ≥ 2 bars whose price is within tol of each other,
            within a rolling EQL_WINDOW-bar window.  Returns list of
            (level, touches) sorted by level.
            """
            found = {}  # level_cell → [price, touch_count, last_bar]
            m = len(prices_arr)
            for ii in range(m):
                for jj in range(ii + 1, min(ii + EQL_WINDOW + 1, m)):
                    diff = abs(prices_arr[ii] - prices_arr[jj])
                    if diff <= tol:
                        level = (prices_arr[ii] + prices_arr[jj]) / 2.0
                        cell = round(level / max(tol, 1e-12))
                        if cell not in found:
                            found[cell] = [level, 2, jj]
                        else:
                            # update to latest touch and average level
                            old_level, old_touches, old_bar = found[cell]
                            found[cell] = [
                                (old_level * old_touches + level) / (old_touches + 1),
                                old_touches + 1,
                                max(old_bar, jj),
                            ]
            return [(v[0], int(v[1])) for v in found.values()]

        eq_highs = _equal_clusters(hi, eq_tol)  # (level, touches)
        eq_lows  = _equal_clusters(lo, eq_tol)

        for (level, touches) in eq_highs:
            dist = abs(entry_price - level) / current_atr
            clusters.append((level, "equal_highs", touches, dist))

        for (level, touches) in eq_lows:
            dist = abs(entry_price - level) / current_atr
            clusters.append((level, "equal_lows", touches, dist))

        # ── 2. Swing-pool (fractal extremes in recent SWING_SCAN bars) ────────
        # Swing highs for SELL, swing lows for BUY — where stops accumulate.
        scan_start = max(SWING_LOOKBACK, n - SWING_SCAN)
        for j in range(scan_start, n - SWING_LOOKBACK):
            # Swing high fractal
            is_sh = all(hi[j] >= hi[j - k] for k in range(1, SWING_LOOKBACK + 1)) and \
                    all(hi[j] >= hi[j + k] for k in range(1, SWING_LOOKBACK + 1))
            if is_sh:
                dist = abs(entry_price - hi[j]) / current_atr
                clusters.append((float(hi[j]), "swing_pool", 1, dist))

            # Swing low fractal
            is_sl = all(lo[j] <= lo[j - k] for k in range(1, SWING_LOOKBACK + 1)) and \
                    all(lo[j] <= lo[j + k] for k in range(1, SWING_LOOKBACK + 1))
            if is_sl:
                dist = abs(entry_price - lo[j]) / current_atr
                clusters.append((float(lo[j]), "swing_pool", 1, dist))

        if not clusters:
            return {"at_risk": False}

        # ── 3. Filter to stop side and within proximity ────────────────────────
        # BUY: stop side = BELOW entry.  Only LOW-side cluster types are relevant:
        #   equal_lows (lows cluster below entry where long stops rest)
        #   swing_pool where level < entry (swing low = stop target for longs)
        # SELL: stop side = ABOVE entry.  Only HIGH-side cluster types:
        #   equal_highs (highs cluster above entry where short stops rest)
        #   swing_pool where level > entry (swing high = stop target for shorts)
        # Equal_highs below entry for a BUY are NOT stop-side risk — they are
        # cleared resistance, irrelevant to stop placement.  Same mirror for SELL.
        at_risk_candidates = []
        for (level, ctype, touches, dist) in clusters:
            if dist > proximity_atr:
                continue
            if direction_upper == "BUY":
                if level >= entry_price:
                    continue   # must be below entry to threaten long stops
                # Only low-side cluster types apply for BUY
                if ctype == "equal_highs":
                    continue   # equal-highs below entry = cleared resistance, not stop risk
            if direction_upper == "SELL":
                if level <= entry_price:
                    continue   # must be above entry to threaten short stops
                # Only high-side cluster types apply for SELL
                if ctype == "equal_lows":
                    continue   # equal-lows above entry = cleared support, not stop risk
            at_risk_candidates.append((level, ctype, touches, dist))

        if not at_risk_candidates:
            return {"at_risk": False}

        # Pick the nearest (smallest distance_atr)
        at_risk_candidates.sort(key=lambda x: x[3])
        cluster_price, cluster_type, touches, distance_atr = at_risk_candidates[0]
        cluster_price = round(float(cluster_price), 8)

        # ── 4. Build suggestion ────────────────────────────────────────────────
        side_word = "below" if direction_upper == "BUY" else "above"
        action_word = "sweep below" if direction_upper == "BUY" else "sweep above"
        reclaim_hint = (cluster_price + 0.25 * current_atr
                        if direction_upper == "BUY"
                        else cluster_price - 0.25 * current_atr)

        description = (
            f"Entry at {entry_price} sits {side_word} a {cluster_type.replace('_', '-')} "
            f"pool at {cluster_price:.5g} ({distance_atr:.2f} ATR away). "
            f"Resting stops likely accumulate here. "
            f"Consider waiting for the {action_word} {cluster_price:.5g} "
            f"followed by a close back through it (reclaim), "
            f"then entering near {reclaim_hint:.5g}."
        )

        return {
            "at_risk": True,
            "cluster_price": cluster_price,
            "cluster_type": cluster_type,
            "distance_atr": round(float(distance_atr), 4),
            "touches": int(touches),
            "suggestion": {
                "wait_for": "sweep_and_reclaim",
                "description": description,
                "alt_entry_hint": round(float(reclaim_hint), 8),
            },
        }

    except Exception as e:
        print(f"[smc] assess_entry_liquidity_risk error: {e}")
        return {"at_risk": False}


def detect_liquidity_clusters(df, atr_series=None):
    """
    Extract all liquidity clusters from confirmed bars, without a specific
    entry price.  Used by detect_smc_structures() to surface the raw cluster
    list under 'liquidity_clusters'.

    Detection mirrors assess_entry_liquidity_risk:
      equal-highs clusters, equal-lows clusters, and swing-pool extremes
      (fractal highs/lows with lookback=3, in the last 60 bars).

    Returns
    -------
    list[dict] — each dict:
        level       float  — cluster price level
        type        str    — 'equal_highs' | 'equal_lows' | 'swing_pool'
        side        str    — 'high' | 'low'
        touches     int    — touch count (equal clusters) or 1 (swing pool)
        bar_index   int    — last-touch bar index in the confirmed array
    """
    import numpy as np
    import pandas as pd

    result = []
    try:
        if df is None or len(df) < 20:
            return result

        df = df.copy()
        df.columns = [c.lower() if isinstance(c, str) else str(c[0]).lower()
                      for c in df.columns]

        confirmed = df.iloc[:-1] if len(df) >= 21 else df

        hi  = confirmed["high"].values.astype(float)
        lo  = confirmed["low"].values.astype(float)
        cl  = confirmed["close"].values.astype(float)
        n   = len(hi)

        # ATR
        if atr_series is not None:
            atr_aligned = atr_series.reindex(confirmed.index).ffill().values.astype(float)
        else:
            tr = np.maximum(hi[1:] - lo[1:],
                 np.maximum(np.abs(hi[1:] - cl[:-1]),
                            np.abs(lo[1:] - cl[:-1])))
            alpha = 1.0 / 14
            atr_arr = np.empty(n)
            atr_arr[0] = np.nan
            atr_arr[1] = tr[0]
            for k in range(2, n):
                atr_arr[k] = alpha * tr[k - 1] + (1 - alpha) * atr_arr[k - 1]
            atr_aligned = atr_arr

        valid_atr = atr_aligned[~np.isnan(atr_aligned)]
        if len(valid_atr) == 0:
            return result
        current_atr = float(valid_atr[-1])
        if current_atr <= 0:
            return result

        eq_tol     = 0.1 * current_atr
        EQL_WINDOW = 20
        SWING_LOOKBACK = 3
        SWING_SCAN     = 60

        def _equal_clusters(prices_arr, tol):
            found = {}  # cell → [level, touches, last_bar]
            m = len(prices_arr)
            for ii in range(m):
                for jj in range(ii + 1, min(ii + EQL_WINDOW + 1, m)):
                    diff = abs(prices_arr[ii] - prices_arr[jj])
                    if diff <= tol:
                        level = (prices_arr[ii] + prices_arr[jj]) / 2.0
                        cell  = round(level / max(tol, 1e-12))
                        if cell not in found:
                            found[cell] = [level, 2, jj]
                        else:
                            old_l, old_t, old_b = found[cell]
                            found[cell] = [
                                (old_l * old_t + level) / (old_t + 1),
                                old_t + 1,
                                max(old_b, jj),
                            ]
            return [(v[0], int(v[1]), int(v[2])) for v in found.values()]  # (level, touches, last_bar)

        for (level, touches, bar_idx) in _equal_clusters(hi, eq_tol):
            result.append(dict(level=round(float(level), 8),
                               type="equal_highs", side="high",
                               touches=touches, bar_index=bar_idx))

        for (level, touches, bar_idx) in _equal_clusters(lo, eq_tol):
            result.append(dict(level=round(float(level), 8),
                               type="equal_lows", side="low",
                               touches=touches, bar_index=bar_idx))

        scan_start = max(SWING_LOOKBACK, n - SWING_SCAN)
        for j in range(scan_start, n - SWING_LOOKBACK):
            is_sh = all(hi[j] >= hi[j - k] for k in range(1, SWING_LOOKBACK + 1)) and \
                    all(hi[j] >= hi[j + k] for k in range(1, SWING_LOOKBACK + 1))
            if is_sh:
                result.append(dict(level=round(float(hi[j]), 8),
                                   type="swing_pool", side="high",
                                   touches=1, bar_index=j))

            is_sl = all(lo[j] <= lo[j - k] for k in range(1, SWING_LOOKBACK + 1)) and \
                    all(lo[j] <= lo[j + k] for k in range(1, SWING_LOOKBACK + 1))
            if is_sl:
                result.append(dict(level=round(float(lo[j]), 8),
                                   type="swing_pool", side="low",
                                   touches=1, bar_index=j))

        result.sort(key=lambda x: x["bar_index"])

    except Exception as e:
        print(f"[smc] detect_liquidity_clusters error: {e}")

    return result


def resample_ohlcv(df, rule):
    """
    Resample an entry-timeframe OHLCV DataFrame to a higher timeframe.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV with a DatetimeIndex and columns open/high/low/close (plus
        optional volume).  Columns are normalised to lowercase internally.
    rule : str
        Pandas offset alias for the target frequency.  Common values:
            '4h'  — 4-hour bars
            '1D'  — daily bars
            '1W'  — weekly bars
        The resample uses label='right', closed='right' so each bucket is
        labelled at its closing timestamp — consistent with how most brokers
        label higher-timeframe bars.

    Returns
    -------
    pd.DataFrame
        Resampled OHLCV with the same column names.  Empty rows are dropped.

    Limitation
    ----------
    Resampled data is NOT equivalent to natively-fetched higher-TF klines.
    The first and last incomplete bucket may be mis-sized, and micro-structure
    gaps in the entry-TF feed propagate silently.  When structure_context()
    uses this helper it tags the source_tf with a '~' prefix (e.g. '~H4') to
    make the synthetic origin explicit everywhere in the output.
    """
    import pandas as pd

    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["open", "high", "low", "close"])

    df = df.copy()
    df.columns = [c.lower() if isinstance(c, str) else str(c[0]).lower()
                  for c in df.columns]

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            "resample_ohlcv requires a DatetimeIndex. "
            "Set a datetime column as the index before calling."
        )

    has_vol = "volume" in df.columns

    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if has_vol:
        agg["volume"] = "sum"

    resampled = (
        df.resample(rule, label="right", closed="right")
        .agg(agg)
        .dropna(how="all")
    )

    # Drop rows where all price columns are NaN (gap periods)
    price_cols = ["open", "high", "low", "close"]
    resampled = resampled.dropna(subset=[c for c in price_cols if c in resampled.columns],
                                 how="all")
    return resampled


def structure_context(df_entry_tf, entry_price, direction,
                      higher_tf_frames=None, atr_series=None):
    """
    Gather and grade all SMC structural context near an entry price.

    This is the D4 entry-point: it replaces the old binary "structure present
    or not" check with a graded, multi-timeframe picture.  The result always
    carries an honest human label — including a plain statement when no
    institutional level is near the entry.

    Parameters
    ----------
    df_entry_tf : pd.DataFrame
        Entry-timeframe OHLCV (open/high/low/close, case-insensitive).
        Must have at least 20 rows.  If the index is a DatetimeIndex and
        higher_tf_frames is not supplied, auto-resampled H4/D1 frames will be
        built from this data (tagged '~H4', '~D1').
    entry_price : float
        The proposed entry price level.
    direction : str
        'BUY' or 'SELL' (case-insensitive).
    higher_tf_frames : dict, optional
        {'H4': df_h4, 'D1': df_d1, ...} — natively-fetched higher-TF frames.
        Each value is an OHLCV DataFrame.  When supplied these are used AS-IS
        and source_tf is set to the dict key (no '~' prefix).
    atr_series : pd.Series, optional
        Pre-computed ATR aligned to df_entry_tf.index.  If not supplied,
        ATR is computed internally from df_entry_tf.

    Returns
    -------
    dict:
        has_structure : bool
            True if any item is graded 'at' (≤0.5 ATR) or 'near' (≤1.5 ATR).
        grade : str | None
            Best grade found across all items:
            'at' → ≤0.5 ATR from entry
            'near' → ≤1.5 ATR
            'context' → ≤4 ATR
            None → nothing within 4 ATR
        items : list[dict]
            Each item:
                type        str   — 'order_block' | 'fvg' | 'liquidity_cluster'
                source_tf   str   — e.g. 'entry', 'H4', 'D1', '~H4', '~D1'
                zone_high   float — upper edge of the zone (or price for point levels)
                zone_low    float — lower edge of the zone
                distance_atr float — |entry_price − nearest zone edge| / entry-TF ATR
                grade       str   — 'at' | 'near' | 'context'
                fresh       bool | None — fresh flag for OBs; None for other types
                direction   str | None — OB direction or None
        label : str
            Human-readable summary.  Always present.
            When has_structure is True: describes the closest structure.
            When has_structure is False: explicitly states this is a
            momentum/indicator signal with no clean institutional level nearby.

    Notes
    -----
    - All detection runs on CONFIRMED (closed) bars only — the live forming
      bar is excluded (anti-repaint policy, same as the rest of smc_structure).
    - Distance is always in entry-TF ATR units, even for higher-TF zones.
      This is intentional: it anchors the grade to the volatility the trader
      experiences at their execution timeframe.
    - Auto-resampling (when higher_tf_frames is None and a DatetimeIndex is
      present) is a convenience.  Resampled ≠ native higher-TF data.  Source
      tags with '~' prefix make this explicit.
    - Minimum history for auto-resampling: ≥96 bars to attempt '~H4' from
      M15; ≥200 bars to attempt '~D1' from H1.  The function documents these
      but does not enforce hard limits — callers see source_tf tags and can
      decide how to weight the results.
    """
    import numpy as np
    import pandas as pd

    GRADE_AT      = 0.5
    GRADE_NEAR    = 1.5
    GRADE_CONTEXT = 4.0

    def _grade(dist_atr):
        if dist_atr <= GRADE_AT:
            return "at"
        if dist_atr <= GRADE_NEAR:
            return "near"
        if dist_atr <= GRADE_CONTEXT:
            return "context"
        return None

    GRADE_RANK = {"at": 0, "near": 1, "context": 2, None: 99}

    items = []

    try:
        if df_entry_tf is None or len(df_entry_tf) < 20:
            return {
                "has_structure": False,
                "grade": None,
                "items": [],
                "label": (
                    "No clean institutional level near this entry — "
                    "this is a momentum/indicator signal, not a structure signal. "
                    "(Insufficient entry-TF data: fewer than 20 bars.)"
                ),
            }

        df_entry_tf = df_entry_tf.copy()
        df_entry_tf.columns = [
            c.lower() if isinstance(c, str) else str(c[0]).lower()
            for c in df_entry_tf.columns
        ]

        # ── Entry-TF ATR ──────────────────────────────────────────────────────
        confirmed_entry = df_entry_tf.iloc[:-1] if len(df_entry_tf) >= 21 else df_entry_tf

        hi_e = confirmed_entry["high"].values.astype(float)
        lo_e = confirmed_entry["low"].values.astype(float)
        cl_e = confirmed_entry["close"].values.astype(float)
        n_e  = len(hi_e)

        if atr_series is not None:
            atr_aligned = atr_series.reindex(confirmed_entry.index).ffill().values.astype(float)
        else:
            tr = np.maximum(hi_e[1:] - lo_e[1:],
                 np.maximum(np.abs(hi_e[1:] - cl_e[:-1]),
                            np.abs(lo_e[1:] - cl_e[:-1])))
            alpha = 1.0 / 14
            atr_arr = np.empty(n_e)
            atr_arr[0] = np.nan
            atr_arr[1] = tr[0] if len(tr) > 0 else np.nan
            for k in range(2, n_e):
                atr_arr[k] = alpha * tr[k - 1] + (1 - alpha) * atr_arr[k - 1]
            atr_aligned = atr_arr

        valid_atr = atr_aligned[~np.isnan(atr_aligned)]
        if len(valid_atr) == 0:
            return {
                "has_structure": False,
                "grade": None,
                "items": [],
                "label": (
                    "No clean institutional level near this entry — "
                    "this is a momentum/indicator signal, not a structure signal. "
                    "(Could not compute ATR from entry-TF data.)"
                ),
            }
        entry_atr = float(valid_atr[-1])
        if entry_atr <= 0:
            entry_atr = 1.0  # guard

        # ── Build higher-TF frames ─────────────────────────────────────────────
        # Priority: caller-supplied > auto-resampled > none
        tf_frames = {}  # tf_label → (df, source_tag)

        if higher_tf_frames:
            for tf_label, tf_df in higher_tf_frames.items():
                if tf_df is not None and len(tf_df) >= 5:
                    tf_frames[tf_label] = (tf_df, tf_label)  # native: no '~'
        else:
            # Auto-resample when entry-TF has a DatetimeIndex
            if isinstance(df_entry_tf.index, pd.DatetimeIndex) and len(df_entry_tf) >= 20:
                # Infer approximate bar duration from the index
                diffs = df_entry_tf.index.to_series().diff().dropna()
                if len(diffs) > 0:
                    median_minutes = diffs.median().total_seconds() / 60.0

                    # Attempt H4 resample if entry-TF bar is shorter than 4h
                    if median_minutes < 240 and len(df_entry_tf) >= 20:
                        try:
                            df_h4 = resample_ohlcv(df_entry_tf, "4h")
                            if len(df_h4) >= 5:
                                tf_frames["~H4"] = (df_h4, "~H4")
                        except Exception:
                            pass

                    # Attempt D1 resample if entry-TF bar is shorter than 1 day
                    if median_minutes < 1440 and len(df_entry_tf) >= 20:
                        try:
                            df_d1 = resample_ohlcv(df_entry_tf, "1D")
                            if len(df_d1) >= 5:
                                tf_frames["~D1"] = (df_d1, "~D1")
                        except Exception:
                            pass

        # ── Collect candidates from all frames ────────────────────────────────
        def _add_ob_candidates(df_tf, source_tag):
            obs = detect_order_blocks(df_tf)
            for ob in obs:
                if ob.get("mitigated"):
                    continue  # mitigated OBs are not actionable
                z_hi = float(ob["zone_high"])
                z_lo = float(ob["zone_low"])
                # Distance from entry to nearest zone edge
                if entry_price >= z_lo and entry_price <= z_hi:
                    dist = 0.0  # entry is inside the zone
                else:
                    dist = min(abs(entry_price - z_hi), abs(entry_price - z_lo))
                dist_atr = dist / entry_atr
                grade = _grade(dist_atr)
                if grade is None:
                    continue
                items.append(dict(
                    type="order_block",
                    source_tf=source_tag,
                    zone_high=round(z_hi, 8),
                    zone_low=round(z_lo, 8),
                    distance_atr=round(dist_atr, 4),
                    grade=grade,
                    fresh=bool(ob.get("fresh", False)),
                    direction=ob.get("direction"),
                ))

        def _add_fvg_candidates(df_tf, source_tag):
            """Detect FVGs within GRADE_CONTEXT ATR of entry."""
            if df_tf is None or len(df_tf) < 5:
                return
            df_c = df_tf.copy()
            df_c.columns = [c.lower() if isinstance(c, str) else str(c[0]).lower()
                             for c in df_c.columns]
            # Anti-repaint
            if len(df_c) >= 6:
                df_c = df_c.iloc[:-1]
            hi_f = df_c["high"].values.astype(float)
            lo_f = df_c["low"].values.astype(float)
            n_f  = len(hi_f)
            for i in range(2, n_f):
                # Bullish FVG: lo[i] > hi[i-2]
                if lo_f[i] > hi_f[i - 2]:
                    mid = (hi_f[i - 2] + lo_f[i]) / 2.0
                    dist_atr = abs(entry_price - mid) / entry_atr
                    grade = _grade(dist_atr)
                    if grade is None:
                        continue
                    items.append(dict(
                        type="fvg",
                        source_tf=source_tag,
                        zone_high=round(float(lo_f[i]), 8),
                        zone_low=round(float(hi_f[i - 2]), 8),
                        distance_atr=round(dist_atr, 4),
                        grade=grade,
                        fresh=None,
                        direction="bullish",
                    ))
                # Bearish FVG: hi[i] < lo[i-2]
                if hi_f[i] < lo_f[i - 2]:
                    mid = (lo_f[i - 2] + hi_f[i]) / 2.0
                    dist_atr = abs(entry_price - mid) / entry_atr
                    grade = _grade(dist_atr)
                    if grade is None:
                        continue
                    items.append(dict(
                        type="fvg",
                        source_tf=source_tag,
                        zone_high=round(float(lo_f[i - 2]), 8),
                        zone_low=round(float(hi_f[i]), 8),
                        distance_atr=round(dist_atr, 4),
                        grade=grade,
                        fresh=None,
                        direction="bearish",
                    ))

        def _add_liq_cluster_candidates(df_tf, source_tag):
            clusters = detect_liquidity_clusters(df_tf)
            for cl in clusters:
                level = float(cl["level"])
                dist_atr = abs(entry_price - level) / entry_atr
                grade = _grade(dist_atr)
                if grade is None:
                    continue
                items.append(dict(
                    type="liquidity_cluster",
                    source_tf=source_tag,
                    zone_high=round(level, 8),
                    zone_low=round(level, 8),
                    distance_atr=round(dist_atr, 4),
                    grade=grade,
                    fresh=None,
                    direction=cl.get("side"),  # 'high' | 'low'
                ))

        # Entry TF
        _add_ob_candidates(df_entry_tf, "entry")
        _add_fvg_candidates(df_entry_tf, "entry")
        _add_liq_cluster_candidates(df_entry_tf, "entry")

        # Higher TFs
        for tf_label, (tf_df, source_tag) in tf_frames.items():
            _add_ob_candidates(tf_df, source_tag)
            _add_fvg_candidates(tf_df, source_tag)
            _add_liq_cluster_candidates(tf_df, source_tag)

    except Exception as e:
        print(f"[smc] structure_context error: {e}")
        items = []

    # ── Determine best grade and has_structure ────────────────────────────────
    if not items:
        best_grade = None
    else:
        best_grade = min(
            (it["grade"] for it in items),
            key=lambda g: GRADE_RANK[g]
        )

    has_structure = best_grade in ("at", "near")

    # ── Build label ───────────────────────────────────────────────────────────
    if has_structure:
        # Find the single closest 'at' or 'near' item to describe
        actionable = [it for it in items if it["grade"] in ("at", "near")]
        actionable.sort(key=lambda it: it["distance_atr"])
        best = actionable[0]

        tf_str  = best["source_tf"]
        typ_str = best["type"].replace("_", " ")
        dist_str = f"{best['distance_atr']:.2f} ATR"

        if best["type"] == "order_block":
            freshness = "fresh " if best.get("fresh") else ""
            dir_str   = (best.get("direction") or "").replace("_", " ")
            label = (
                f"Entry sits at a {freshness}{tf_str} {dir_str} order block "
                f"({dist_str} away)."
            )
        elif best["type"] == "fvg":
            dir_str = (best.get("direction") or "").replace("_", " ")
            label = (
                f"Entry sits within a {tf_str} {dir_str} fair-value gap "
                f"({dist_str} away)."
            )
        else:
            label = (
                f"Entry is near a {tf_str} liquidity cluster "
                f"({dist_str} away)."
            )

        # Append count of additional nearby items
        extra = len(actionable) - 1
        if extra > 0:
            label += f" ({extra} additional structure item{'s' if extra > 1 else ''} also nearby.)"
    else:
        label = (
            "No clean institutional level near this entry — "
            "this is a momentum/indicator signal, not a structure signal."
        )
        if best_grade == "context":
            label += (
                " (Distant structure exists in the 1.5–4 ATR window — "
                "not close enough to be a high-confidence confluence.)"
            )

    return {
        "has_structure": has_structure,
        "grade": best_grade,
        "items": items,
        "label": label,
    }


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
        # Order blocks detected from confirmed bars (list of dicts, newest last)
        "order_blocks": [],
        # Inducement zones (IDM) — minor opposing swings/clusters guarding fresh OBs
        "inducement": [],
        # Raw liquidity clusters (equal-H/L pools + swing-pool extremes) — confirmed bars
        # Use assess_entry_liquidity_risk() at signal-build time for per-entry risk check.
        "liquidity_clusters": [],
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

        # ── 5. Order Blocks ─────────────────────────────────────────────────
        obs = detect_order_blocks(df)
        result["order_blocks"] = obs

        # ── 6. Inducement (IDM) ──────────────────────────────────────────────
        result["inducement"] = detect_inducement(df, order_blocks=obs)

        # ── 7. Liquidity clusters (raw list for app-level risk checks) ────────
        result["liquidity_clusters"] = detect_liquidity_clusters(df)

    except Exception as e:
        print(f"[smc] detect_smc_structures error: {e}")

    return result
