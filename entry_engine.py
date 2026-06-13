"""DotVerse D5 — Conditional Entry / Decision Engine.

Purpose
-------
Proposes an entry plan (single vs scale-in vs delay) for a given trade setup by
assembling SMC structural evidence and applying gated trading rules.

CRITICAL CONSTRAINT — GATED OFF BY DEFAULT
-------------------------------------------
This engine ships with ``enabled=False`` and has NO authority over live entries
until EVERY rule that alters a plan has:
  1. A real-kline (not synthetic) per-class backtest that clears the gate.
  2. The 'proven' flag set in RULE_REGISTRY (manual step by Omar).
  3. A staging environment verified before production.

Today ALL rules load as 'unproven' — the research JSONs carry synthetic-data
caveats.  See RULE_REGISTRY for details and promotion criteria.

A fixed 3-leg scale-out failed at −0.014R in the 1,087-trade study
(research/scalein_vs_single_summary_ALL.json). Fixed rules are FORBIDDEN.
All multi-leg decisions must be per-trade and evidence-based.
"""

import json
import os
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_RESEARCH = _HERE / "research"

# ---------------------------------------------------------------------------
# RULE_REGISTRY
# ---------------------------------------------------------------------------
# Each entry describes one SMC decision rule.  Status is loaded from the
# corresponding backtest JSON at call time (see _load_rule_registry()).
#
# Promotion path to 'proven':
#   1. Run the backtest against REAL OHLCV klines (not Monte Carlo / synthetic).
#   2. Gate criteria: strategy B beats strategy A on avg_R AND does not worsen
#      max drawdown, across >=500 real trades, per-class (TF+direction+symbol).
#   3. Omar reviews and manually sets status='proven' here.
#   4. Deploy to staging; verify UI shows updated plan annotation.
#   5. Merge to main and deploy to production.
#
# A rule with status=='failed' or status=='unproven' has zero influence on the
# returned plan, even when enabled=True.

_RULE_DEFINITIONS = [
    {
        "name": "ob_retest",
        "description": (
            "Delay/split entry toward a fresh order-block zone when one sits "
            "below (BUY) or above (SELL) the current entry price."
        ),
        "backtest_file": str(_RESEARCH / "ob_retest_summary.json"),
        "promotion_criteria": (
            "B avg_R > A avg_R on >=500 real-kline trades; "
            "B max_dd_R <= A max_dd_R; gate_pass=true on real data."
        ),
    },
    {
        "name": "idm_wait",
        "description": (
            "Wait for an unswept inducement (IDM) to be cleared before entering; "
            "enter only after the IDM sweep is confirmed."
        ),
        "backtest_file": str(_RESEARCH / "idm_summary.json"),
        "promotion_criteria": (
            "B avg_R > A avg_R on >=500 real-kline trades; "
            "B max_dd_R <= A max_dd_R; gate_pass=true on real data."
        ),
    },
    {
        "name": "trap_avoidance",
        "description": (
            "Delay entry when a liquidity cluster is within 0.5 ATR of the "
            "stop side; wait for a sweep-and-reclaim before entering."
        ),
        "backtest_file": str(_RESEARCH / "trap_avoidance_summary.json"),
        "promotion_criteria": (
            "B avg_R > A avg_R on >=500 real-kline trades; "
            "B max_dd_R <= A max_dd_R; B avg_mae <= A avg_mae; "
            "gate_pass=true on real data.  "
            "NOTE: synthetic backtest was a GATE FAIL — this rule must NOT be "
            "promoted until a real-data run shows a positive edge."
        ),
    },
    {
        "name": "structure_context",
        "description": (
            "Grade the structural confluence of the entry (at/near/context) "
            "across multiple timeframes and use it to size legs or defer."
        ),
        "backtest_file": str(_RESEARCH / "density_summary.json"),
        "promotion_criteria": (
            "Per-grade outcome study on >=500 real-kline trades showing that "
            "'at'-grade entries outperform 'near' and 'context' by a "
            "statistically meaningful margin; then per-class gate."
        ),
    },
]


def _load_rule_registry() -> list[dict]:
    """Load RULE_REGISTRY, populating status from research JSONs at call time.

    Status assignment logic
    -----------------------
    A rule is 'proven' ONLY when ALL of the following are true:
      - The backtest JSON exists.
      - The JSON's gate.gate_pass == True.
      - The JSON contains NO synthetic-data caveat flag.

    A synthetic-data caveat is detected by checking:
      - Top-level key 'caveat' containing the substring 'SYNTHETIC'
        (present in idm_summary.json, trap_avoidance_summary.json,
         density_summary.json).
      - gate.verdict containing 'SYNTHETIC'
        (idm_summary.json and trap_avoidance_summary.json carry this).
      - ob_retest_summary.json has gate_pass=True but no caveat key —
        however the file was generated on synthetic OHLCV paths
        (Monte Carlo, see ob_retest_backtest.py).  The absence of a caveat
        does NOT make it real data; we encode the synthetic origin by
        checking for 'use_fallback': true (the backtest used random
        forward paths when no real OB fill was available).

    Any rule that does not pass this triple check loads as 'unproven'.
    A rule whose JSON is missing or malformed loads as 'unproven'.
    A rule whose gate explicitly failed loads as 'failed'.
    """
    registry = []
    for defn in _RULE_DEFINITIONS:
        entry = {
            "name": defn["name"],
            "description": defn["description"],
            "backtest_file": defn["backtest_file"],
            "promotion_criteria": defn["promotion_criteria"],
            "status": "unproven",   # safe default
            "gate_pass": None,
            "synthetic_data": None,
            "verdict": None,
        }

        path = Path(defn["backtest_file"])
        if not path.exists():
            entry["status"] = "unproven"
            entry["verdict"] = "backtest file not found — rule is unproven"
            registry.append(entry)
            continue

        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            entry["status"] = "unproven"
            entry["verdict"] = f"could not parse backtest JSON: {exc}"
            registry.append(entry)
            continue

        gate = data.get("gate", None)   # None means no gate section at all
        gate_exists = gate is not None
        gate = gate or {}
        gate_pass = bool(gate.get("gate_pass", False))
        gate_verdict = gate.get("verdict", "")
        entry["gate_pass"] = gate_pass if gate_exists else None
        entry["verdict"] = gate_verdict

        # Detect synthetic-data markers
        synthetic = False

        # Marker 1: explicit 'caveat' key at top level containing 'SYNTHETIC'
        # Note: density_summary.json caveat starts with "Synthetic" — .upper() catches it.
        caveat_text = data.get("caveat", "")
        if isinstance(caveat_text, str) and "SYNTHETIC" in caveat_text.upper():
            synthetic = True

        # Marker 2: gate.verdict contains 'SYNTHETIC'
        if "SYNTHETIC" in gate_verdict.upper():
            synthetic = True

        # Marker 3: use_fallback = True signals synthetic forward-path methodology
        # (ob_retest and idm_summary use this; it means OB fill was simulated, not real)
        if data.get("use_fallback") is True:
            synthetic = True

        entry["synthetic_data"] = synthetic

        if not gate_exists:
            # No gate section → not yet evaluated → unproven (not failed)
            entry["status"] = "unproven"
        elif not gate_pass:
            # Gate section exists and explicitly failed
            entry["status"] = "failed"
        elif gate_pass and synthetic:
            # Gate technically passed but on synthetic data — still unproven
            entry["status"] = "unproven"
        else:
            # gate_pass=True AND no synthetic markers → proven
            entry["status"] = "proven"

        registry.append(entry)

    return registry


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_entry_plan(
    df,
    entry_price: float,
    direction: str,
    stop: float,
    target: float,
    account_risk_amount: float,
    enabled: bool = False,
) -> dict:
    """Propose an entry plan (single vs multi-leg) for a trade setup.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV DataFrame with at least 20 confirmed bars (open/high/low/close).
        Anti-repaint: the live forming bar should be the last row (it will be
        stripped internally by the SMC detectors).
    entry_price : float
        Proposed entry price.
    direction : str
        'BUY' or 'SELL' (case-insensitive).
    stop : float
        Stop-loss price level.
    target : float
        Take-profit price level.
    account_risk_amount : float
        Maximum risk in account currency units for this trade.
        The sum of all leg risks MUST equal this value (risk invariant).
    enabled : bool, optional
        When False (default): the engine returns a single-entry plan and
        populates ``analysis`` with what the engine WOULD consider, so the
        UI can show a transparent "here's what the engine sees" panel
        without any plan being affected.
        When True: only 'proven' rules may alter the plan.  With zero proven
        rules (today's reality) the engine still returns a single-entry plan
        but decision_basis reflects that rather than 'engine_disabled'.

    Returns
    -------
    dict with keys:
        mode : str
            'single' | 'scale_in' | 'wait'
        legs : list[dict]
            Each leg: {price: float, fraction: float, kind: str}
            ``fraction`` is the share of account_risk_amount for that leg.
            sum(leg['fraction']) == 1.0  (risk invariant).
        total_risk : float
            Always equal to account_risk_amount (asserted internally).
        decision_basis : str
            Human sentence naming the evidence or reason for this plan.
        evidence : list[str]
            Plain-English list of structural observations.
        rule_statuses : dict
            {rule_name: status_string} for every rule in the registry.
        analysis : dict
            Always present.  Contains:
                order_blocks      : list[dict] — OBs detected
                inducement        : list[dict] — IDM zones detected
                liquidity_risk    : dict — assess_entry_liquidity_risk output
                structure_ctx     : dict — structure_context output
                hypothetical_mode : str — what mode WOULD be chosen if all
                                    rules were proven (illustrative only)
                hypothetical_basis: str — explanation of hypothetical
    """
    from smc_structure import (
        detect_order_blocks,
        detect_inducement,
        assess_entry_liquidity_risk,
        structure_context,
    )

    direction_upper = direction.upper()

    # ── 1. Load registry ────────────────────────────────────────────────────
    registry = _load_rule_registry()
    rule_statuses = {r["name"]: r["status"] for r in registry}

    # ── 2. Run detectors ────────────────────────────────────────────────────
    order_blocks = []
    inducement = []
    liquidity_risk = {"at_risk": False}
    struct_ctx = {"has_structure": False, "grade": None, "items": [], "label": ""}

    try:
        order_blocks = detect_order_blocks(df)
        inducement = detect_inducement(df, order_blocks=order_blocks)
        liquidity_risk = assess_entry_liquidity_risk(df, entry_price, direction_upper)
        struct_ctx = structure_context(df, entry_price, direction_upper)
    except Exception as exc:
        pass   # detectors are best-effort; plan defaults to single

    # ── 3. Assemble evidence list ──────────────────────────────────────────
    evidence = []

    fresh_obs = [ob for ob in order_blocks
                 if ob.get("fresh") and not ob.get("mitigated")]
    if fresh_obs:
        # Find the OB closest to entry price on the correct side
        def _ob_distance(ob):
            mid = (ob["zone_high"] + ob["zone_low"]) / 2.0
            return abs(entry_price - mid)

        closest_ob = min(fresh_obs, key=_ob_distance)
        evidence.append(
            f"Fresh OB at [{closest_ob['zone_low']:.5g}, "
            f"{closest_ob['zone_high']:.5g}] "
            f"({closest_ob['direction']}, "
            f"tested {closest_ob['times_tested']}x)"
        )
    else:
        evidence.append("No fresh unmitigated OB detected near entry.")

    unswept_idm = [idm for idm in inducement if not idm.get("swept")]
    if unswept_idm:
        evidence.append(
            f"Unswept IDM at {unswept_idm[0]['idm_price']:.5g} "
            f"(type={unswept_idm[0]['idm_type']}, "
            f"dist={unswept_idm[0]['distance_atr']:.2f} ATR)"
        )
    else:
        evidence.append("No unswept inducement (IDM) between price and OB zone.")

    if liquidity_risk.get("at_risk"):
        evidence.append(
            f"Liquidity trap risk: {liquidity_risk['cluster_type']} at "
            f"{liquidity_risk['cluster_price']:.5g} "
            f"({liquidity_risk['distance_atr']:.2f} ATR from entry on stop side)."
        )
    else:
        evidence.append("No stop-side liquidity cluster within 0.5 ATR.")

    if struct_ctx.get("has_structure"):
        evidence.append(f"Structure: {struct_ctx['label']}")
    else:
        evidence.append(f"Structure: {struct_ctx.get('label', 'No structure context computed.')}")

    # ── 4. Hypothetical logic (illustrative, never live today) ────────────
    hypothetical_mode, hypothetical_basis = _compute_hypothetical(
        direction_upper, entry_price, fresh_obs, unswept_idm, liquidity_risk
    )

    analysis = {
        "order_blocks": order_blocks,
        "inducement": inducement,
        "liquidity_risk": liquidity_risk,
        "structure_ctx": struct_ctx,
        "hypothetical_mode": hypothetical_mode,
        "hypothetical_basis": hypothetical_basis,
    }

    # ── 5. Build plan ──────────────────────────────────────────────────────
    if not enabled:
        # Engine is disabled — always return single, show analysis
        plan = _single_plan(
            entry_price, account_risk_amount,
            decision_basis="engine_disabled — default single entry",
        )
        plan["evidence"] = evidence
        plan["rule_statuses"] = rule_statuses
        plan["analysis"] = analysis
        _assert_risk_invariant(plan, account_risk_amount)
        return plan

    # Engine is enabled — only proven rules may act
    proven_rules = {r["name"] for r in registry if r["status"] == "proven"}

    if not proven_rules:
        plan = _single_plan(
            entry_price, account_risk_amount,
            decision_basis="no proven rules — single entry",
        )
        plan["evidence"] = evidence
        plan["rule_statuses"] = rule_statuses
        plan["analysis"] = analysis
        _assert_risk_invariant(plan, account_risk_amount)
        return plan

    # --- Proven-rule logic (future: not reachable today) ---
    mode, legs, decision_basis = _apply_proven_rules(
        proven_rules,
        direction_upper,
        entry_price,
        fresh_obs,
        unswept_idm,
        liquidity_risk,
        account_risk_amount,
    )

    plan = {
        "mode": mode,
        "legs": legs,
        "total_risk": account_risk_amount,
        "decision_basis": decision_basis,
        "evidence": evidence,
        "rule_statuses": rule_statuses,
        "analysis": analysis,
    }
    _assert_risk_invariant(plan, account_risk_amount)
    return plan


def calibrated_win_chance(features: dict, history_df=None) -> tuple:
    """Estimate the calibrated win probability for a trade.

    This function is intentionally a STUB until sufficient real outcome history
    is available.  It returns (None, explanation) to make it crystal-clear that
    no probability estimate is being produced.

    Parameters
    ----------
    features : dict
        Feature dict describing the trade setup (e.g. structure grade, OB
        freshness, IDM state).  Reserved for future use when anchoring to
        journal outcomes.
    history_df : pd.DataFrame, optional
        Closed-trade journal with at least one outcome column.  Must contain
        >= 100 rows of real closed trades before any estimate can be made.

    Returns
    -------
    (None, explanation : str)
        Always returns None as the probability.  The explanation string
        describes the data requirement and how this function will be
        populated once real outcome history exists.

    Notes
    -----
    The intention is to anchor estimates to the user's own journal via:
      1. Collect >=100 closed real trades with entry features + outcome.
      2. Fit a Platt-scaled logistic regression (or isotonic regression) on
         the feature vector.
      3. Cross-validate to confirm calibration (reliability diagram).
      4. Replace this stub with the trained estimator.
    Invented probabilities are explicitly forbidden — they mislead sizing.
    """
    n_real_trades = 0
    if history_df is not None:
        try:
            n_real_trades = len(history_df)
        except Exception:
            pass

    if n_real_trades < 100:
        explanation = (
            f"calibrated_win_chance: insufficient real outcome history "
            f"({n_real_trades} closed trades, need >=100). "
            "Returning None to prevent invented probability estimates. "
            "Populate history_df with real closed-trade journal data "
            "(>=100 rows) and re-run; then a Platt-scaled calibration "
            "model will be fitted and this stub replaced."
        )
        return None, explanation

    # If we ever reach here (future), we'd fit and return a real estimate.
    # For now, even with enough rows, refuse until a fitted model is present.
    explanation = (
        f"calibrated_win_chance: {n_real_trades} closed trades available but "
        "no calibrated model has been fitted yet. "
        "Run the calibration harness (to be built) and replace this stub."
    )
    return None, explanation


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _single_plan(entry_price: float, account_risk_amount: float,
                 decision_basis: str) -> dict:
    """Return a conservative single-entry plan."""
    return {
        "mode": "single",
        "legs": [{"price": entry_price, "fraction": 1.0, "kind": "market"}],
        "total_risk": account_risk_amount,
        "decision_basis": decision_basis,
    }


def _compute_hypothetical(direction, entry_price, fresh_obs,
                           unswept_idm, liquidity_risk) -> tuple:
    """Illustrative hypothetical: what the engine WOULD do if rules were proven.

    This is for UI transparency only — it must never affect the live plan.

    Returns (mode, basis) strings.
    """
    # Mirror the proven-rule logic to show what *would* happen
    would_scale_in = False
    would_wait = False
    basis_parts = []

    # ob_retest: fresh OB on the right side near entry → would scale in
    ob_below_buy = any(
        ob["direction"] == "bullish" and ob["zone_high"] < entry_price
        for ob in fresh_obs
    ) if direction == "BUY" else False

    ob_above_sell = any(
        ob["direction"] == "bearish" and ob["zone_low"] > entry_price
        for ob in fresh_obs
    ) if direction == "SELL" else False

    if ob_below_buy or ob_above_sell:
        would_scale_in = True
        basis_parts.append("fresh OB on correct side (ob_retest rule)")

    # trap_avoidance: at-risk liquidity near stop → would wait
    if liquidity_risk.get("at_risk"):
        would_wait = True
        basis_parts.append("stop-side liquidity trap (trap_avoidance rule)")

    # idm_wait: unswept IDM → would wait
    if unswept_idm:
        would_wait = True
        basis_parts.append(f"unswept IDM at {unswept_idm[0]['idm_price']:.5g} (idm_wait rule)")

    if would_wait:
        mode = "wait"
        basis = (
            "HYPOTHETICAL (illustrative only — rules unproven): "
            "engine WOULD annotate 'wait' based on: "
            + "; ".join(basis_parts) + "."
        )
    elif would_scale_in:
        mode = "scale_in"
        basis = (
            "HYPOTHETICAL (illustrative only — rules unproven): "
            "engine WOULD propose scale-in based on: "
            + "; ".join(basis_parts) + "."
        )
    else:
        mode = "single"
        basis = (
            "HYPOTHETICAL (illustrative only — rules unproven): "
            "engine would default to single entry — no strong scale-in signal."
        )

    return mode, basis


def _apply_proven_rules(proven_rules, direction, entry_price,
                        fresh_obs, unswept_idm, liquidity_risk,
                        account_risk_amount) -> tuple:
    """Build a plan using only the rules whose status is 'proven'.

    Hard constraints (always enforced regardless of rules):
      - Never more than 3 legs.
      - sum(leg fraction) == 1.0 exactly.
      - Conservative default: single entry if no clear signal.

    Returns (mode, legs, decision_basis).
    """
    # --- trap_avoidance (proven) + at_risk → delay ---
    if "trap_avoidance" in proven_rules and liquidity_risk.get("at_risk"):
        return (
            "wait",
            [{"price": entry_price, "fraction": 1.0, "kind": "wait_sweep_reclaim"}],
            (
                "trap_avoidance rule (proven): stop-side liquidity cluster at "
                f"{liquidity_risk.get('cluster_price', '?'):.5g} within "
                f"{liquidity_risk.get('distance_atr', '?'):.2f} ATR. "
                "Waiting for sweep-and-reclaim before entry."
            ),
        )

    # --- idm_wait (proven) + unswept IDM → delay ---
    if "idm_wait" in proven_rules and unswept_idm:
        nearest_idm = unswept_idm[0]
        return (
            "wait",
            [{"price": entry_price, "fraction": 1.0, "kind": "wait_idm_sweep"}],
            (
                "idm_wait rule (proven): unswept IDM at "
                f"{nearest_idm['idm_price']:.5g} must be cleared first."
            ),
        )

    # --- ob_retest (proven) + fresh OB on correct side → scale-in (2 legs) ---
    if "ob_retest" in proven_rules:
        ob_match = None
        for ob in fresh_obs:
            if direction == "BUY" and ob["direction"] == "bullish" and ob["zone_high"] < entry_price:
                ob_match = ob
                break
            if direction == "SELL" and ob["direction"] == "bearish" and ob["zone_low"] > entry_price:
                ob_match = ob
                break

        if ob_match is not None:
            zone_mid = (ob_match["zone_high"] + ob_match["zone_low"]) / 2.0
            # 2-leg split: 60% at market, 40% at OB zone mid
            # Fractions must sum to 1.0; total risk == account_risk_amount
            legs = [
                {"price": entry_price, "fraction": 0.60, "kind": "market"},
                {"price": round(zone_mid, 8), "fraction": 0.40, "kind": "limit_ob_retest"},
            ]
            # Validate <= 3 legs
            assert len(legs) <= 3, "scale-in plan must not exceed 3 legs"
            return (
                "scale_in",
                legs,
                (
                    "ob_retest rule (proven): fresh "
                    f"{ob_match['direction']} OB at "
                    f"[{ob_match['zone_low']:.5g}, {ob_match['zone_high']:.5g}]. "
                    "60% at market, 40% limit at OB zone mid. "
                    "Total risk preserved == account_risk_amount."
                ),
            )

    # --- Conservative default: single ---
    return (
        "single",
        [{"price": entry_price, "fraction": 1.0, "kind": "market"}],
        "proven rules present but no triggering condition met — single entry.",
    )


def _assert_risk_invariant(plan: dict, account_risk_amount: float):
    """Assert that the sum of leg fractions == 1.0 and total_risk is correct.

    Raises AssertionError (caught in tests) if violated.
    """
    legs = plan.get("legs", [])
    frac_sum = sum(leg.get("fraction", 0.0) for leg in legs)
    # Allow floating-point tolerance
    assert abs(frac_sum - 1.0) < 1e-9, (
        f"Risk invariant violated: leg fractions sum to {frac_sum}, expected 1.0"
    )
    assert abs(plan.get("total_risk", 0) - account_risk_amount) < 1e-9, (
        f"Risk invariant violated: total_risk {plan.get('total_risk')} "
        f"!= account_risk_amount {account_risk_amount}"
    )
    assert len(legs) <= 3, (
        f"Plan exceeds 3-leg hard limit: {len(legs)} legs found."
    )
