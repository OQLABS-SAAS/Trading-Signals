"""Portfolio VaR unavailable-state frontend contracts.

These are static contracts because the Portfolio tab is still rendered from the
single HTML bundle. They protect against the dangerous false-safety state where
/api/var errors were converted into $0.00 / 0.00% "healthy" risk.
"""
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text(encoding="utf-8")


def _extract_function(name):
    start = HTML.index(f"function {name}(") if f"function {name}(" in HTML else HTML.index(f"async function {name}(")
    depth = 0
    i = start
    while i < len(HTML):
        c = HTML[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return HTML[start : i + 1]
        i += 1
    raise ValueError(f"Could not extract {name}")


def test_show_portfolio_does_not_turn_var_fetch_failure_into_zero_risk():
    block = _extract_function("showPortfolio")

    assert "const varData   = varResp || {var_1d_usd:0,var_1d_pct:0,portfolio_std:0};" not in block
    assert "const varData   = varResp;" in block
    assert "pfVarReady(varData)" in block
    assert "VaR unavailable / not enough data" in block
    assert "not enough data" in block


def test_var_ready_rejects_null_errors_and_missing_var_fields():
    block = _extract_function("pfVarReady")

    assert "if(!varData || varData.error) return false;" in block
    assert "pfVarMetric(varData,'var_1d_usd','var_amount')" in block
    assert "pfVarMetric(varData,'var_1d_pct','var_pct')" in block
    assert "Number.isFinite(varAmt) && Number.isFinite(varPct)" in block


def test_portfolio_health_banner_is_neutral_when_var_unavailable():
    block = _extract_function("pfUpdateHealth")

    assert "const varReady = pfVarReady(varData);" in block
    assert "label = 'VaR unavailable / not enough data'" in block
    assert "Portfolio Healthy" not in block.split("if (varReady) {", 1)[0]
    assert "VaR unavailable" in block


def test_risk_manager_full_check_does_not_mark_unavailable_checks_complete():
    var_block = _extract_function("rmRunVar")
    stress_block = _extract_function("rmRunStress")
    full_block = _extract_function("rmRunFullCheck")

    assert "return false;" in var_block
    assert "return true;" in var_block
    assert "return false;" in stress_block
    assert "return true;" in stress_block
    assert "const ok=results.every(Boolean);" in full_block
    assert "Safety check complete" in full_block
    assert "Safety check incomplete" in full_block
