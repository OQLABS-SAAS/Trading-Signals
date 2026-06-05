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
    assert "Every leg below has its own cash in, position value, lot size, target, risk, and profit." in source
    assert "Every leg below has its own cash in, controlled value" not in source
    assert "controls · '+((l.lots||0).toFixed(4))+' lots" in source


def test_today_v2_downgrades_target_not_covered_to_scout_first():
    source = _source()

    assert "targetNeedsScout" in source
    assert "Scout first" in source
    assert "Review risk anyway" in source
    assert "window._todayLastTargetPath" in source
    assert "These setups are technically entry-ready, but the target path is not covered." in source


def test_today_v2_hydrates_account_context_from_live_sources():
    source = _source()

    assert "async function _todayLoadAccountContext()" in source
    assert "function _todayApplyAccountContext(accounts, source)" in source
    assert "typeof _agentLoadAccounts==='function'" in source
    assert "_updateGlobalConnIndicator()" in source
    assert "Live MT5 equity" in source
    assert "Last MT5 balance (offline)" in source
    assert "d.connected===true" in source
    assert "Manual override" in source
    assert "todayAcctSource" in source
    assert "window._todayMt5Online" in source
    assert "function _todayAccountIsConnected(a)" in source
    assert "a.connected===true||a.is_connected===true||a.online===true||s==='connected'||s==='online'" in source
    assert "window._todayMt5Online=list.some(_todayAccountIsConnected)" in source
    assert "window._todayMt5Online=window._todayMt5Online===true || d.connected===true" in source
    assert "function _todayCanPlaceMt5()" in source


def test_today_v2_top_copy_and_modes_do_not_lie_about_state():
    source = _source()

    assert "no open risk is using the weekly budget right now" in source
    assert "open risk is already using part of the weekly budget" in source
    assert '<button disabled title="Use the risk control inside each selected trade.">Per-trade mode</button>' in source
    assert '<button disabled title="Manual allocation is inside each selected trade.">Manual allocation</button>' in source
    assert ".today-v2-mode button:disabled" in source


def test_today_v2_blocks_live_place_actions_when_mt5_is_offline():
    source = _source()

    assert "function _todayV2PlaceCtaText(targetNeedsScout, all)" in source
    assert "MT5 offline - review only" in source
    assert "cta.disabled=!_todayCanPlaceMt5()" in source
    assert "MT5 is offline - Today can review risk, but cannot place live orders yet" in source
    assert "MT5 is offline - connect the account before placing Today orders" in source
    assert "MT5 is offline - no live order was sent" in source
    assert "var bottomOrderNote=protect?'new entries paused':(!mt5CanPlace?'MT5 offline'" in source
    assert ".today-v2-btn:disabled,.today-v2-review:disabled" in source
