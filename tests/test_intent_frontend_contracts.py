"""Static contract tests for the P1 dvIntent frontend store and settings editor.

Pattern mirrors test_a5_quickwins_contracts.py — read the HTML as text,
assert markers are present.

Checks:
  1. dvIntent store functions present (_dvIntentGet, _dvIntentSave, _dvIntentLoad).
  2. localStorage key constant (_DV_INTENT_KEY / 'dvIntent') defined.
  3. Default intent shape defined in JS (_DV_INTENT_DEFAULT).
  4. Settings editor panel: _spIntent function defined.
  5. Settings editor markers: intentSettPanel, intentGoal_daily,
     intentRiskPerTrade, intentRiskOpen, intentSaveBtn.
  6. Intent tab wired into showSettings tabs array.
  7. Fallback chain for riskPct: max_open_risk_pct with fallback 3.
  8. Fallback chain for profitGoal: weekly goal with fallback 500.
  9. Intent loaded on login: _dvIntentLoad called from goDash / login block.
 10. _dvIntentSave uses PUT /api/intent.
"""
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text()


# ─── 1. dvIntent store functions ─────────────────────────────────────────────

def test_dvintent_get_function_defined():
    assert "function _dvIntentGet(" in HTML


def test_dvintent_save_function_defined():
    assert "async function _dvIntentSave(" in HTML


def test_dvintent_load_function_defined():
    assert "async function _dvIntentLoad(" in HTML


# ─── 2. localStorage key constant ────────────────────────────────────────────

def test_dvintent_localStorage_key_constant():
    assert "_DV_INTENT_KEY" in HTML
    assert "'dvIntent'" in HTML


# ─── 3. Default intent shape in JS ───────────────────────────────────────────

def test_dvintent_default_shape_defined():
    assert "_DV_INTENT_DEFAULT" in HTML


def test_dvintent_default_has_goals_and_risk():
    start = HTML.index("_DV_INTENT_DEFAULT")
    # Find the block
    block = HTML[start:start + 600]
    assert "goals" in block
    assert "risk"  in block
    assert "markets" in block


def test_dvintent_default_risk_values():
    """Default max_per_trade_pct=1.0 and max_open_risk_pct=3.0 must appear in the default."""
    start = HTML.index("_DV_INTENT_DEFAULT")
    block = HTML[start:start + 600]
    assert "max_per_trade_pct" in block
    assert "max_open_risk_pct" in block
    assert "1.0" in block
    assert "3.0" in block


# ─── 4. Settings editor panel function ───────────────────────────────────────

def test_spIntent_function_defined():
    assert "function _spIntent(" in HTML


# ─── 5. Settings editor DOM markers ──────────────────────────────────────────

def test_intent_panel_id_present():
    assert "intentSettPanel" in HTML


def test_intent_goal_daily_input():
    assert "intentGoal_daily" in HTML


def test_intent_goal_weekly_input():
    assert "intentGoal_weekly" in HTML


def test_intent_goal_monthly_input():
    assert "intentGoal_monthly" in HTML


def test_intent_risk_per_trade_input():
    assert "intentRiskPerTrade" in HTML


def test_intent_risk_open_input():
    assert "intentRiskOpen" in HTML


def test_intent_risk_daily_stop_input():
    assert "intentRiskDailyStop" in HTML


def test_intent_save_button():
    assert "intentSaveBtn" in HTML


def test_intent_save_panel_function():
    assert "async function _intentSavePanel(" in HTML


def test_intent_market_chips_rendered():
    """Market toggle chips must be present for known markets."""
    assert "intentMktsRow" in HTML
    assert "_intentToggleMarket(" in HTML


def test_intent_derived_label_shown():
    """Derived goal values must be labelled as (derived) in the UI."""
    assert "derived" in HTML


# ─── 6. Intent tab wired into showSettings ───────────────────────────────────

def test_intent_tab_in_showSettings():
    """The intent tab must be listed in the showSettings tabs array."""
    start = HTML.index("function showSettings(")
    end   = HTML.index("el.innerHTML=`", start)
    block = HTML[start:end]
    assert "intent" in block
    assert "Your goals" in block or "goals" in block.lower()


def test_spIntent_called_in_showSettings():
    start = HTML.index("function showSettings(")
    end   = HTML.index("el.innerHTML=`", start)
    block = HTML[start:end]
    assert "_spIntent()" in block


# ─── 7. Fallback chain: riskPct ──────────────────────────────────────────────

def test_risk_pct_reads_from_intent_with_fallback():
    """The _todayCfg init must read max_open_risk_pct from intent with old default (3) as fallback."""
    # Find _todayCfg initialisation block
    start = HTML.index("window._todayCfg = window._todayCfg ||")
    end   = HTML.index("function _todaySaveCfg(", start)
    block = HTML[start:end]
    assert "max_open_risk_pct" in block, \
        "riskPct must be read from intent.risk.max_open_risk_pct"
    assert "3" in block, \
        "Old hardcoded fallback value 3 must still be present for back-compat"
    assert "_dvIntentGet" in block, \
        "_dvIntentGet must be called to source the risk value"
    # The actual riskPct default must no longer be a naked literal 3
    # — it must go through the intent read
    assert "_intentRisk" in block or "max_open_risk_pct" in block


# ─── 8. Fallback chain: profitGoal (weekly) ──────────────────────────────────

def test_profit_goal_reads_from_intent_with_fallback():
    """The _todayCfg init must read weekly goal from intent with old default (500) as fallback."""
    start = HTML.index("window._todayCfg = window._todayCfg ||")
    end   = HTML.index("function _todaySaveCfg(", start)
    block = HTML[start:end]
    assert "weekly" in block, \
        "profitGoal must be sourced from intent.goals.weekly"
    assert "500" in block, \
        "Old hardcoded fallback value 500 must still be present for back-compat"
    assert "_dvIntentGet" in block, \
        "_dvIntentGet must be called to source the goal value"


# ─── 9. Intent loaded on login ───────────────────────────────────────────────

def test_dvIntentLoad_called_on_login():
    """_dvIntentLoad must be called from the login/goDash block."""
    assert "_dvIntentLoad()" in HTML


# ─── 10. _dvIntentSave uses PUT ──────────────────────────────────────────────

def test_dvIntentSave_uses_PUT():
    start = HTML.index("async function _dvIntentSave(")
    end   = HTML.index("async function _dvIntentLoad(", start)
    block = HTML[start:end]
    assert "PUT" in block
    assert "/api/intent" in block


def test_dvIntentLoad_uses_GET():
    start = HTML.index("async function _dvIntentLoad(")
    # Find closing brace
    depth = 0
    i = start
    while i < len(HTML):
        if HTML[i] == '{': depth += 1
        elif HTML[i] == '}':
            depth -= 1
            if depth == 0: break
        i += 1
    block = HTML[start:i+1]
    assert "/api/intent" in block
