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
    assert "onclick=\"_todayV2SetLadderMode('+idx+',\\'conservative\\')\"" in source
    assert "onclick=\"_todayV2SetLadderMode('+idx+',\\'beginner\\')\"" in source
    assert "onclick=\"_todayV2SetLadderMode('+idx+',\\'aggressive\\')\"" in source
    assert "Every leg below has its own cash in, controlled value, lot size, target, risk, and profit." in source
    assert "controls · '+((l.lots||0).toFixed(4))+' lots" in source
