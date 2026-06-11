"""Contract + behavioral tests for _dvBasketTotals(legs) — the canonical pure
function that computes combined basket totals for multi-leg ladder trades.

Two layers:
  1. Static contract tests (plain Python) — verify the function is present in
     the HTML and that _todayLadderTotals delegates to it.
  2. Behavioral JS tests — extract the function via node subprocess (same
     brace-balanced extractor pattern as test_sizing_failsafe_behavioral.py)
     and assert exact computed values for 3-leg, empty, and single-leg cases.

All tests run from repo root (pytest cwd); Path is relative to that.
"""
import json
import subprocess
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text()

# ─────────────────────────────────────────────────────────────────────────────
# Narrow scope helpers
# ─────────────────────────────────────────────────────────────────────────────
_BT_START = "function _dvBasketTotals("
_BT_END   = "function _todayLadderTotals("
_bts = HTML.index(_BT_START)
_bte = HTML.index(_BT_END, _bts)
BT_BLOCK = HTML[_bts:_bte]

_TLT_START = "function _todayLadderTotals("
_TLT_END   = "function _todaySetTradeLadder("
_tlts = HTML.index(_TLT_START)
_tlte = HTML.index(_TLT_END, _tlts)
TLT_BLOCK = HTML[_tlts:_tlte]

# _szConfirmTrade block
_CF_START = "function _szConfirmTrade(onConfirm){"
_CF_END   = "// Trade buttons now go through the confirmation card first."
_cfs = HTML.index(_CF_START)
_cfe = HTML.index(_CF_END, _cfs)
CF_BLOCK = HTML[_cfs:_cfe]

# szLadderRender block
_LR_START = "function szLadderRender() {"
_LR_END   = "function szLadderRefresh("
_lrs = HTML.index(_LR_START)
_lre = HTML.index(_LR_END, _lrs)
LR_BLOCK = HTML[_lrs:_lre]


# ─────────────────────────────────────────────────────────────────────────────
# 1. _dvBasketTotals exists and returns the right fields
# ─────────────────────────────────────────────────────────────────────────────

def test_dvBasketTotals_function_exists():
    assert "function _dvBasketTotals(" in HTML


def test_dvBasketTotals_returns_totalCashIn():
    assert "totalCashIn" in BT_BLOCK


def test_dvBasketTotals_returns_totalRisk():
    assert "totalRisk" in BT_BLOCK


def test_dvBasketTotals_returns_totalProfitTarget():
    assert "totalProfitTarget" in BT_BLOCK


def test_dvBasketTotals_returns_totalPositionValue():
    assert "totalPositionValue" in BT_BLOCK


def test_dvBasketTotals_returns_orderCount():
    assert "orderCount" in BT_BLOCK


def test_dvBasketTotals_handles_both_risk_fieldnames():
    """Must handle both l.risk (Today-tab legs) and l.moneyAtRisk (Size-tab legs)."""
    assert "l.risk" in BT_BLOCK
    assert "l.moneyAtRisk" in BT_BLOCK


def test_dvBasketTotals_handles_empty_legs():
    """Empty or null legs must return all-zeros."""
    assert "!legs||!legs.length" in BT_BLOCK or "legs.length" in BT_BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 2. _todayLadderTotals delegates to _dvBasketTotals
# ─────────────────────────────────────────────────────────────────────────────

def test_todayLadderTotals_delegates_to_dvBasketTotals():
    assert "_dvBasketTotals(" in TLT_BLOCK


def test_todayLadderTotals_back_compat_shape_has_margin():
    """Back-compat shape must include margin for Today-tab callers."""
    assert "margin:" in TLT_BLOCK


def test_todayLadderTotals_back_compat_shape_has_orders():
    assert "orders:" in TLT_BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 3. Size-tab confirm modal uses _dvBasketTotals and shows basket totals block
# ─────────────────────────────────────────────────────────────────────────────

def test_confirm_modal_calls_dvBasketTotals():
    assert "_dvBasketTotals(" in CF_BLOCK


def test_confirm_modal_basket_totals_block_id():
    assert 'id="szCfBasketTotals"' in CF_BLOCK


def test_confirm_modal_basket_shows_cash_in():
    idx = CF_BLOCK.index('id="szCfBasketTotals"')
    snippet = CF_BLOCK[idx:idx + 1200]
    assert "totalCashIn" in snippet


def test_confirm_modal_basket_shows_position_value():
    idx = CF_BLOCK.index('id="szCfBasketTotals"')
    snippet = CF_BLOCK[idx:idx + 1600]
    assert "totalPositionValue" in snippet


def test_confirm_modal_basket_shows_total_risk():
    idx = CF_BLOCK.index('id="szCfBasketTotals"')
    snippet = CF_BLOCK[idx:idx + 2000]
    assert "totalRisk" in snippet


def test_confirm_modal_basket_shows_profit_target():
    idx = CF_BLOCK.index('id="szCfBasketTotals"')
    snippet = CF_BLOCK[idx:idx + 2400]
    assert "totalProfitTarget" in snippet


def test_confirm_modal_basket_shows_order_count():
    idx = CF_BLOCK.index('id="szCfBasketTotals"')
    snippet = CF_BLOCK[idx:idx + 800]
    assert "orderCount" in snippet


def test_confirm_modal_basket_totals_before_max_loss_card():
    """The new basket-totals strip must appear before the existing max-loss card."""
    basket_idx   = CF_BLOCK.index('id="szCfBasketTotals"')
    max_loss_idx = CF_BLOCK.index('id="szCfMaxLossCard"')
    assert basket_idx < max_loss_idx


def test_confirm_modal_basket_totals_only_for_multi_leg():
    """The basket-totals strip must be guarded by nT>1."""
    basket_idx = CF_BLOCK.index('id="szCfBasketTotals"')
    # Walk back to find the nearest nT>1 guard
    guard_region = CF_BLOCK[max(0, basket_idx - 200):basket_idx]
    assert "nT>1" in guard_region


# ─────────────────────────────────────────────────────────────────────────────
# 4. Size-tab ladder footer uses _dvBasketTotals for the basket-totals strip
# ─────────────────────────────────────────────────────────────────────────────

def test_ladder_render_calls_dvBasketTotals():
    assert "_dvBasketTotals(" in LR_BLOCK


def test_ladder_render_basket_strip_id():
    assert 'id="szBasketTotalsStrip"' in LR_BLOCK


def test_ladder_render_basket_strip_shows_cash_in():
    idx = LR_BLOCK.index('id="szBasketTotalsStrip"')
    snippet = LR_BLOCK[idx:idx + 600]
    assert "totalCashIn" in snippet


def test_ladder_render_basket_strip_shows_position_value():
    idx = LR_BLOCK.index('id="szBasketTotalsStrip"')
    snippet = LR_BLOCK[idx:idx + 800]
    assert "totalPositionValue" in snippet


def test_ladder_render_basket_strip_shows_profit_target():
    idx = LR_BLOCK.index('id="szBasketTotalsStrip"')
    snippet = LR_BLOCK[idx:idx + 1600]
    assert "totalProfitTarget" in snippet


def test_ladder_render_basket_strip_shows_order_count():
    idx = LR_BLOCK.index('id="szBasketTotalsStrip"')
    snippet = LR_BLOCK[idx:idx + 1600]
    assert "orderCount" in snippet


def test_ladder_render_basket_strip_inside_max_loss_card():
    """The basket-totals strip must be inside szMaxTotalLossCard for consistency."""
    max_loss_idx = LR_BLOCK.index('id="szMaxTotalLossCard"')
    strip_idx    = LR_BLOCK.index('id="szBasketTotalsStrip"')
    assert strip_idx > max_loss_idx


# ─────────────────────────────────────────────────────────────────────────────
# 5. Behavioral JS tests — exact computed values via node subprocess
# ─────────────────────────────────────────────────────────────────────────────

def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _extract_fn(src: str, fn_name: str) -> str:
    """Brace-balanced extractor: returns the full function body for fn_name."""
    marker = "function " + fn_name + "("
    start = src.find(marker)
    if start < 0:
        raise RuntimeError(f"function {fn_name} not found in source")
    depth = 0
    started = False
    j = start
    while j < len(src):
        ch = src[j]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                return src[start:j + 1]
        j += 1
    raise RuntimeError(f"Unbalanced braces for function {fn_name}")


def _build_basket_harness() -> str:
    """Return a JS harness string containing just _dvBasketTotals."""
    src = Path("static/index-v2-prototype.html").read_text()
    fn_js = _extract_fn(src, "_dvBasketTotals")
    return fn_js


def _run_basket_js(script: str) -> object:
    """Inject _dvBasketTotals from HTML and run script; return parsed JSON."""
    harness = _build_basket_harness()
    full = harness + "\n" + script
    r = subprocess.run(
        ["node", "-e", full],
        capture_output=True, text=True, timeout=15,
        cwd=Path(__file__).parent.parent,
    )
    if r.returncode != 0:
        raise RuntimeError(f"node error:\n{r.stderr[:800]}")
    return json.loads(r.stdout.strip())


import pytest


@pytest.mark.skipif(not _node_available(), reason="node not available")
class TestDvBasketTotalsBehavioral:
    """Behavioral tests: extract _dvBasketTotals via brace-balanced extractor,
    run via node, assert exact sums for real-money correctness."""

    def test_three_leg_today_tab_sums(self):
        """3 Today-tab legs: sums must equal exact per-field totals."""
        script = r"""
var legs = [
  {margin: 100, notional: 10000, risk: 50,  profit: 200},
  {margin: 200, notional: 20000, risk: 100, profit: 400},
  {margin: 150, notional: 15000, risk: 75,  profit: 300}
];
var r = _dvBasketTotals(legs);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_basket_js(script)
        assert r["totalCashIn"]        == 450,   f"totalCashIn expected 450, got {r['totalCashIn']}"
        assert r["totalRisk"]          == 225,   f"totalRisk expected 225, got {r['totalRisk']}"
        assert r["totalProfitTarget"]  == 900,   f"totalProfitTarget expected 900, got {r['totalProfitTarget']}"
        assert r["totalPositionValue"] == 45000, f"totalPositionValue expected 45000, got {r['totalPositionValue']}"
        assert r["orderCount"]         == 3,     f"orderCount expected 3, got {r['orderCount']}"

    def test_three_leg_size_tab_moneyAtRisk_field(self):
        """3 Size-tab legs using moneyAtRisk: risk total must use moneyAtRisk."""
        script = r"""
var legs = [
  {margin: 100, notional: 10000, moneyAtRisk: 50,  profit: 200},
  {margin: 200, notional: 20000, moneyAtRisk: 100, profit: 400},
  {margin: 150, notional: 15000, moneyAtRisk: 75,  profit: 300}
];
var r = _dvBasketTotals(legs);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_basket_js(script)
        assert r["totalRisk"]          == 225,   f"moneyAtRisk path: totalRisk expected 225, got {r['totalRisk']}"
        assert r["totalCashIn"]        == 450,   f"totalCashIn expected 450, got {r['totalCashIn']}"
        assert r["totalPositionValue"] == 45000, f"totalPositionValue expected 45000, got {r['totalPositionValue']}"
        assert r["orderCount"]         == 3,     f"orderCount expected 3, got {r['orderCount']}"

    def test_empty_legs_returns_zeros(self):
        """Empty array must return all-zero basket."""
        script = r"""
var r = _dvBasketTotals([]);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_basket_js(script)
        assert r["totalCashIn"]        == 0
        assert r["totalRisk"]          == 0
        assert r["totalProfitTarget"]  == 0
        assert r["totalPositionValue"] == 0
        assert r["orderCount"]         == 0

    def test_null_legs_returns_zeros(self):
        """Null input must return all-zero basket."""
        script = r"""
var r = _dvBasketTotals(null);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_basket_js(script)
        assert r["totalCashIn"]        == 0
        assert r["totalRisk"]          == 0
        assert r["totalProfitTarget"]  == 0
        assert r["totalPositionValue"] == 0
        assert r["orderCount"]         == 0

    def test_single_leg_equals_that_legs_values(self):
        """Single-leg basket must equal exactly that leg's values."""
        script = r"""
var legs = [{margin: 300, notional: 30000, risk: 150, profit: 600}];
var r = _dvBasketTotals(legs);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_basket_js(script)
        assert r["totalCashIn"]        == 300,   f"totalCashIn expected 300, got {r['totalCashIn']}"
        assert r["totalRisk"]          == 150,   f"totalRisk expected 150, got {r['totalRisk']}"
        assert r["totalProfitTarget"]  == 600,   f"totalProfitTarget expected 600, got {r['totalProfitTarget']}"
        assert r["totalPositionValue"] == 30000, f"totalPositionValue expected 30000, got {r['totalPositionValue']}"
        assert r["orderCount"]         == 1,     f"orderCount expected 1, got {r['orderCount']}"

    def test_mixed_risk_risk_and_moneyAtRisk(self):
        """Legs with both risk and moneyAtRisk: risk field should take precedence."""
        script = r"""
var legs = [
  {margin: 100, notional: 5000, risk: 50, moneyAtRisk: 999, profit: 100},
  {margin: 100, notional: 5000, risk: 50, moneyAtRisk: 999, profit: 100}
];
var r = _dvBasketTotals(legs);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_basket_js(script)
        # risk field exists, so l.risk||l.moneyAtRisk = l.risk = 50 for each
        assert r["totalRisk"] == 100, f"Mixed fields: totalRisk expected 100, got {r['totalRisk']}"
        assert r["orderCount"] == 2

    def test_decimal_precision_preserved(self):
        """Decimal leg values must sum correctly (no floating-point truncation)."""
        script = r"""
var legs = [
  {margin: 33.33, notional: 3333.33, risk: 16.67, profit: 66.67},
  {margin: 33.33, notional: 3333.33, risk: 16.67, profit: 66.67},
  {margin: 33.34, notional: 3333.34, risk: 16.66, profit: 66.66}
];
var r = _dvBasketTotals(legs);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_basket_js(script)
        assert abs(r["totalCashIn"]        - 100.00) < 0.01, f"cash-in sum error: {r['totalCashIn']}"
        assert abs(r["totalRisk"]          - 50.00)  < 0.01, f"risk sum error: {r['totalRisk']}"
        assert abs(r["totalProfitTarget"]  - 200.00) < 0.01, f"profit sum error: {r['totalProfitTarget']}"
        assert abs(r["totalPositionValue"] - 10000.0)< 1.0,  f"notional sum error: {r['totalPositionValue']}"
