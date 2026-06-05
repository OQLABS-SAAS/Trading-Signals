from pathlib import Path


HTML = Path(__file__).resolve().parents[1] / "static" / "index-v2-prototype.html"


def _source():
    return HTML.read_text()


def test_today_v2_exposes_all_order_automation_flags():
    source = _source()

    assert "['be','Break-even'" in source
    assert "['tp1','TP1 partial'" in source
    assert "['tp2','TP2 alert'" in source
    assert "['trail','Trail runner'" in source
    assert "['macro','News guard'" in source
    assert "['inval','Invalid setup'" in source
    assert "['sent','Sentiment'" in source
    assert "['weekend','Weekend guard'" in source
    assert "tp2_alert:!!(o._autos&&o._autos.tp2)" in source
    assert "weekend:!!(o._autos&&o._autos.weekend)" in source


def test_today_automation_recommendation_uses_ladder_target():
    source = _source()

    assert "function _todayAutomationTarget(o)" in source
    assert "target:_todayAutomationTarget(o)" in source
    assert "rsi:o.rsi||50, target:'tp1'" not in source


def test_today_v2_exposes_multiladder_presets_and_leg_money():
    source = _source()

    assert "function _todayV2SetLadderMode(idx, mode)" in source
    assert "Ladder preset" in source
    assert "function presetBtn(id,label,copy)" in source
    assert "presetBtn('conservative','Conservative'" in source
    assert "presetBtn('beginner','Beginner'" in source
    assert "presetBtn('aggressive','Aggressive'" in source
    assert "Preset controls are inactive" in source
    assert "Every leg below has its own cash in, controlled value, lot size, target, risk, and profit." in source
    assert "controls · '+((l.lots||0).toFixed(4))+' lots" in source


def test_today_v2_downgrades_target_not_covered_to_scout_first():
    source = _source()

    assert "targetNeedsScout" in source
    assert "Scout first" in source
    assert "Review risk anyway" in source
    assert "These setups are technically entry-ready, but the target path is not covered." in source


def test_today_v2_hydrates_account_context_from_live_sources():
    source = _source()

    assert "async function _todayLoadAccountContext()" in source
    assert "function _todayApplyAccountContext(accounts, source)" in source
    assert "typeof _agentLoadAccounts==='function'" in source
    assert "_updateGlobalConnIndicator()" in source
    assert "Live MT5 equity" in source
    assert "Manual override" in source
    assert "todayAcctSource" in source
