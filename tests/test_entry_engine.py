"""Tests for entry_engine.py — D5 Conditional Entry / Decision Engine.

All tests assert:
  - disabled → single plan + analysis present
  - enabled + unproven rules → single plan + 'no proven rules' basis
  - risk invariant: sum(leg fractions) == 1.0, total_risk == account_risk_amount
  - <=3 legs hard limit
  - multi-leg branch (ob_retest monkeypatched to proven) risk invariant holds
  - all current rules load 'unproven' from the real research JSONs
  - calibrated_win_chance returns (None, str) without history

Run:
    python3 -m pytest tests/test_entry_engine.py -q -p no:cacheprovider
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import entry_engine
from entry_engine import (
    propose_entry_plan,
    calibrated_win_chance,
    _load_rule_registry,
    _assert_risk_invariant,
    _apply_proven_rules,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 60, seed: int = 42) -> pd.DataFrame:
    """Generate a deterministic synthetic OHLCV DataFrame."""
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.1, 0.8, n)
    low = close - rng.uniform(0.1, 0.8, n)
    open_ = close - rng.normal(0, 0.3, n)
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    })


@pytest.fixture
def sample_df():
    return _make_ohlcv(n=60)


@pytest.fixture
def sample_params():
    """Typical entry parameters for a BUY trade."""
    return {
        "entry_price": 101.0,
        "direction": "BUY",
        "stop": 99.5,
        "target": 104.0,
        "account_risk_amount": 100.0,
    }


# ---------------------------------------------------------------------------
# Test 1: disabled engine → single plan + analysis present
# ---------------------------------------------------------------------------

class TestDisabledEngine:
    def test_returns_single_mode(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        assert plan["mode"] == "single", (
            f"Expected mode='single' when disabled, got '{plan['mode']}'"
        )

    def test_single_leg_at_entry_price(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        assert len(plan["legs"]) == 1
        assert plan["legs"][0]["price"] == sample_params["entry_price"]

    def test_decision_basis_mentions_disabled(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        assert "engine_disabled" in plan["decision_basis"], (
            f"Expected 'engine_disabled' in decision_basis, got: {plan['decision_basis']!r}"
        )

    def test_analysis_present(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        assert "analysis" in plan, "analysis key must be present"
        analysis = plan["analysis"]
        for key in ("order_blocks", "inducement", "liquidity_risk",
                    "structure_ctx", "hypothetical_mode", "hypothetical_basis"):
            assert key in analysis, f"analysis missing key: {key!r}"

    def test_analysis_has_hypothetical_mode(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        hyp = plan["analysis"]["hypothetical_mode"]
        assert hyp in ("single", "scale_in", "wait"), (
            f"Unexpected hypothetical_mode: {hyp!r}"
        )

    def test_risk_invariant_disabled(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        _assert_risk_invariant(plan, sample_params["account_risk_amount"])

    def test_evidence_list_present(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        assert isinstance(plan.get("evidence"), list)
        assert len(plan["evidence"]) > 0

    def test_rule_statuses_present(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=False, **sample_params
        )
        statuses = plan.get("rule_statuses", {})
        assert len(statuses) > 0
        expected_rules = {"ob_retest", "idm_wait", "trap_avoidance", "structure_context"}
        for rule in expected_rules:
            assert rule in statuses, f"rule_statuses missing rule: {rule!r}"


# ---------------------------------------------------------------------------
# Test 2: enabled + unproven rules → single plan + correct basis
# ---------------------------------------------------------------------------

class TestEnabledNoProvenRules:
    def test_returns_single_when_all_unproven(self, sample_df, sample_params):
        # All rules are unproven from real JSONs today
        plan = propose_entry_plan(
            sample_df, enabled=True, **sample_params
        )
        assert plan["mode"] == "single", (
            f"Expected mode='single' with no proven rules, got '{plan['mode']}'"
        )

    def test_basis_mentions_no_proven_rules(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=True, **sample_params
        )
        assert "no proven rules" in plan["decision_basis"], (
            f"Expected 'no proven rules' in decision_basis, got: {plan['decision_basis']!r}"
        )

    def test_analysis_still_present_when_enabled(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=True, **sample_params
        )
        assert "analysis" in plan

    def test_risk_invariant_enabled_no_proven(self, sample_df, sample_params):
        plan = propose_entry_plan(
            sample_df, enabled=True, **sample_params
        )
        _assert_risk_invariant(plan, sample_params["account_risk_amount"])


# ---------------------------------------------------------------------------
# Test 3: risk invariant across hypothetical multi-leg plans
# (uses monkeypatch to force ob_retest to 'proven')
# ---------------------------------------------------------------------------

class TestRiskInvariantMultiLeg:
    def test_scale_in_fractions_sum_to_one(self):
        """Force ob_retest proven; call _apply_proven_rules directly."""
        # Build a fresh OB sitting below a BUY entry
        fresh_ob = {
            "direction": "bullish",
            "zone_high": 99.0,
            "zone_low": 98.0,
            "fresh": True,
            "mitigated": False,
            "times_tested": 0,
        }
        mode, legs, basis = _apply_proven_rules(
            proven_rules={"ob_retest"},
            direction="BUY",
            entry_price=101.0,
            fresh_obs=[fresh_ob],
            unswept_idm=[],
            liquidity_risk={"at_risk": False},
            account_risk_amount=200.0,
        )
        assert mode == "scale_in"
        frac_sum = sum(leg["fraction"] for leg in legs)
        assert abs(frac_sum - 1.0) < 1e-9, (
            f"Leg fractions sum to {frac_sum}, expected 1.0"
        )

    def test_scale_in_leg_count_le_3(self):
        fresh_ob = {
            "direction": "bullish",
            "zone_high": 99.0,
            "zone_low": 98.0,
            "fresh": True,
            "mitigated": False,
            "times_tested": 0,
        }
        mode, legs, basis = _apply_proven_rules(
            proven_rules={"ob_retest"},
            direction="BUY",
            entry_price=101.0,
            fresh_obs=[fresh_ob],
            unswept_idm=[],
            liquidity_risk={"at_risk": False},
            account_risk_amount=200.0,
        )
        assert len(legs) <= 3, f"Expected <=3 legs, got {len(legs)}"

    def test_scale_in_total_risk_preserved(self):
        fresh_ob = {
            "direction": "bullish",
            "zone_high": 99.0,
            "zone_low": 98.0,
            "fresh": True,
            "mitigated": False,
            "times_tested": 0,
        }
        account_risk = 500.0
        mode, legs, basis = _apply_proven_rules(
            proven_rules={"ob_retest"},
            direction="BUY",
            entry_price=101.0,
            fresh_obs=[fresh_ob],
            unswept_idm=[],
            liquidity_risk={"at_risk": False},
            account_risk_amount=account_risk,
        )
        # Simulate what propose_entry_plan does: total_risk = account_risk_amount
        # Fractions sum to 1.0 means total risk is preserved
        frac_sum = sum(leg["fraction"] for leg in legs)
        implied_risk = frac_sum * account_risk
        assert abs(implied_risk - account_risk) < 1e-9

    def test_propose_with_monkeypatched_proven_rule(self, monkeypatch, sample_params):
        """End-to-end: monkeypatch _load_rule_registry to return ob_retest=proven.
        Build a DataFrame that contains a genuine fresh bullish OB below entry."""
        # Build OHLCV with a displacement that creates a bullish OB near 99
        # Structure: lots of base candles, then a bearish candle (the OB), then
        # a large bullish displacement
        n_base = 30
        base_hi = np.full(n_base, 100.5)
        base_lo = np.full(n_base, 99.5)
        base_cl = np.full(n_base, 100.0)
        base_op = np.full(n_base, 100.0)

        # The bearish OB candle (will become the OB)
        ob_hi = np.array([100.1])
        ob_lo = np.array([98.8])
        ob_op = np.array([100.0])
        ob_cl = np.array([98.9])   # bearish → this is the OB for bull displacement next

        # Large bullish displacement (body >> 2×ATR)
        disp_op = np.array([98.9])
        disp_cl = np.array([103.5])  # large bull body
        disp_hi = np.array([103.6])
        disp_lo = np.array([98.8])

        # A few follow-through candles near entry price (101.0) without retesting OB
        ft_n = 5
        ft_cl = np.full(ft_n, 101.0)
        ft_hi = np.full(ft_n, 101.5)
        ft_lo = np.full(ft_n, 100.5)
        ft_op = np.full(ft_n, 101.0)

        hi = np.concatenate([base_hi, ob_hi, disp_hi, ft_hi, [0]])
        lo = np.concatenate([base_lo, ob_lo, disp_lo, ft_lo, [0]])
        cl = np.concatenate([base_cl, ob_cl, disp_cl, ft_cl, [101.0]])
        op = np.concatenate([base_op, ob_op, disp_op, ft_op, [101.0]])
        # last bar is the live forming bar (will be stripped by detectors)
        hi[-1] = 101.1
        lo[-1] = 100.9
        vol = np.ones(len(hi)) * 500

        df = pd.DataFrame({
            "open": op, "high": hi, "low": lo, "close": cl, "volume": vol
        })

        def _fake_registry():
            reg = _load_rule_registry()
            for r in reg:
                if r["name"] == "ob_retest":
                    r["status"] = "proven"
            return reg

        monkeypatch.setattr(entry_engine, "_load_rule_registry", _fake_registry)

        plan = propose_entry_plan(
            df,
            entry_price=101.0,
            direction="BUY",
            stop=98.0,
            target=105.0,
            account_risk_amount=200.0,
            enabled=True,
        )

        # Regardless of whether scale_in or single fires, invariants must hold
        _assert_risk_invariant(plan, 200.0)
        assert len(plan["legs"]) <= 3
        assert abs(sum(leg["fraction"] for leg in plan["legs"]) - 1.0) < 1e-9

        if plan["mode"] == "scale_in":
            assert len(plan["legs"]) == 2
            assert plan["legs"][0]["kind"] == "market"
            assert plan["legs"][1]["kind"] == "limit_ob_retest"
            assert abs(plan["legs"][0]["fraction"] - 0.60) < 1e-9
            assert abs(plan["legs"][1]["fraction"] - 0.40) < 1e-9

    def test_wait_plan_risk_invariant(self):
        """trap_avoidance proven + at_risk → wait plan with fraction==1.0."""
        mode, legs, basis = _apply_proven_rules(
            proven_rules={"trap_avoidance"},
            direction="BUY",
            entry_price=101.0,
            fresh_obs=[],
            unswept_idm=[],
            liquidity_risk={
                "at_risk": True,
                "cluster_price": 100.3,
                "cluster_type": "equal_lows",
                "distance_atr": 0.3,
            },
            account_risk_amount=300.0,
        )
        assert mode == "wait"
        frac_sum = sum(leg["fraction"] for leg in legs)
        assert abs(frac_sum - 1.0) < 1e-9

    def test_idm_wait_plan_risk_invariant(self):
        """idm_wait proven + unswept IDM → wait plan with fraction==1.0."""
        fake_idm = [{"idm_price": 100.5, "idm_type": "minor_swing",
                     "swept": False, "distance_atr": 0.3}]
        mode, legs, basis = _apply_proven_rules(
            proven_rules={"idm_wait"},
            direction="BUY",
            entry_price=101.0,
            fresh_obs=[],
            unswept_idm=fake_idm,
            liquidity_risk={"at_risk": False},
            account_risk_amount=150.0,
        )
        assert mode == "wait"
        frac_sum = sum(leg["fraction"] for leg in legs)
        assert abs(frac_sum - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Test 4: registry marks all current rules 'unproven' from real JSONs
# ---------------------------------------------------------------------------

class TestRegistryLoadsUnproven:
    def test_all_rules_unproven(self):
        """All rules must load as 'unproven' today — synthetic data only."""
        registry = _load_rule_registry()
        for rule in registry:
            assert rule["status"] != "proven", (
                f"Rule '{rule['name']}' loaded as 'proven' but all research "
                f"JSONs are synthetic-data only. Status={rule['status']!r}, "
                f"verdict={rule.get('verdict')!r}"
            )

    def test_registry_has_all_expected_rules(self):
        registry = _load_rule_registry()
        names = {r["name"] for r in registry}
        expected = {"ob_retest", "idm_wait", "trap_avoidance", "structure_context"}
        assert names == expected, (
            f"Registry rule names mismatch. Expected {expected}, got {names}"
        )

    def test_trap_avoidance_is_failed(self):
        """trap_avoidance has gate_pass=false in its JSON → must be 'failed'."""
        registry = _load_rule_registry()
        trap = next((r for r in registry if r["name"] == "trap_avoidance"), None)
        assert trap is not None
        # gate explicitly failed → status=='failed' (a subtype of unproven)
        assert trap["status"] == "failed", (
            f"Expected trap_avoidance status='failed' (gate_fail + synthetic), "
            f"got '{trap['status']}'"
        )

    def test_ob_retest_synthetic_detected(self):
        """ob_retest has use_fallback=true → synthetic data → unproven."""
        registry = _load_rule_registry()
        ob = next((r for r in registry if r["name"] == "ob_retest"), None)
        assert ob is not None
        assert ob["synthetic_data"] is True, (
            "ob_retest_summary.json uses use_fallback=true (synthetic paths); "
            f"expected synthetic_data=True, got {ob['synthetic_data']}"
        )
        assert ob["status"] == "unproven", (
            f"ob_retest gate_pass=true but data is synthetic → must be 'unproven', "
            f"got '{ob['status']}'"
        )

    def test_idm_wait_caveat_detected(self):
        """idm_summary.json has SYNTHETIC caveat → unproven despite gate_pass."""
        registry = _load_rule_registry()
        idm = next((r for r in registry if r["name"] == "idm_wait"), None)
        assert idm is not None
        assert idm["synthetic_data"] is True
        assert idm["status"] == "unproven", (
            f"idm_wait gate_pass=true but SYNTHETIC caveat present → must be "
            f"'unproven', got '{idm['status']}'"
        )

    def test_structure_context_caveat_detected(self):
        """density_summary.json has synthetic caveat → unproven."""
        registry = _load_rule_registry()
        sc = next((r for r in registry if r["name"] == "structure_context"), None)
        assert sc is not None
        assert sc["synthetic_data"] is True
        assert sc["status"] == "unproven"

    def test_no_rule_can_alter_plan_when_all_unproven(self, sample_df=None):
        """With all rules unproven, enabled=True must still return single entry."""
        if sample_df is None:
            sample_df = _make_ohlcv(60)
        plan = propose_entry_plan(
            sample_df,
            entry_price=101.0,
            direction="BUY",
            stop=99.0,
            target=104.0,
            account_risk_amount=100.0,
            enabled=True,
        )
        assert plan["mode"] == "single"
        assert "no proven rules" in plan["decision_basis"]


# ---------------------------------------------------------------------------
# Test 5: calibrated_win_chance returns None without sufficient history
# ---------------------------------------------------------------------------

class TestCalibratedWinChance:
    def test_returns_none_without_history(self):
        result, explanation = calibrated_win_chance(features={})
        assert result is None, f"Expected None, got {result}"
        assert isinstance(explanation, str) and len(explanation) > 0

    def test_returns_none_with_insufficient_history(self):
        small_df = pd.DataFrame({"outcome": [1, 0, 1] * 10})  # 30 rows < 100
        result, explanation = calibrated_win_chance(features={}, history_df=small_df)
        assert result is None
        assert "insufficient" in explanation.lower() or "30" in explanation

    def test_returns_none_with_none_history(self):
        result, explanation = calibrated_win_chance(features={"grade": "at"}, history_df=None)
        assert result is None

    def test_still_returns_none_with_large_history_no_model(self):
        """Even with >=100 rows, no model is fitted yet → still None."""
        big_df = pd.DataFrame({"outcome": [1, 0] * 60})  # 120 rows >= 100
        result, explanation = calibrated_win_chance(features={}, history_df=big_df)
        assert result is None

    def test_explanation_mentions_journal_anchoring(self):
        result, explanation = calibrated_win_chance(features={})
        # Should mention what the caller needs to do
        assert any(
            word in explanation.lower()
            for word in ("history", "journal", "trades", "real", "history_df")
        ), f"Explanation should mention data requirement. Got: {explanation!r}"


# ---------------------------------------------------------------------------
# Test 6: plan structure invariants (always-present keys)
# ---------------------------------------------------------------------------

class TestPlanStructure:
    @pytest.mark.parametrize("enabled", [True, False])
    def test_required_keys_present(self, sample_df, sample_params, enabled):
        plan = propose_entry_plan(sample_df, enabled=enabled, **sample_params)
        required = {"mode", "legs", "total_risk", "decision_basis",
                    "evidence", "rule_statuses", "analysis"}
        missing = required - set(plan.keys())
        assert not missing, f"Plan missing required keys: {missing}"

    @pytest.mark.parametrize("enabled", [True, False])
    def test_leg_structure(self, sample_df, sample_params, enabled):
        plan = propose_entry_plan(sample_df, enabled=enabled, **sample_params)
        for leg in plan["legs"]:
            assert "price" in leg
            assert "fraction" in leg
            assert "kind" in leg
            assert isinstance(leg["fraction"], (int, float))
            assert 0.0 < leg["fraction"] <= 1.0

    @pytest.mark.parametrize("enabled", [True, False])
    def test_total_risk_equals_account_risk(self, sample_df, sample_params, enabled):
        plan = propose_entry_plan(sample_df, enabled=enabled, **sample_params)
        assert abs(plan["total_risk"] - sample_params["account_risk_amount"]) < 1e-9

    @pytest.mark.parametrize("risk_amount", [50.0, 100.0, 999.99, 0.01])
    def test_risk_invariant_various_amounts(self, sample_df, sample_params, risk_amount):
        params = {**sample_params, "account_risk_amount": risk_amount}
        plan = propose_entry_plan(sample_df, enabled=False, **params)
        _assert_risk_invariant(plan, risk_amount)
