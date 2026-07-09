import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, "static", "index-v2-prototype.html")


def _html():
    with open(HTML_PATH, encoding="utf-8") as f:
        return f.read()


def _extract_last_function(name):
    markers = (f"function {name}(", f"async function {name}(")
    start = max(_html().rfind(marker) for marker in markers)
    if start < 0:
        raise ValueError(f"Could not extract {name}")
    html = _html()
    depth = 0
    i = start
    while i < len(html):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[start : i + 1]
        i += 1
    raise ValueError(f"Could not extract {name}")


def test_today_strategy_mode_selector_contains_all_modes():
    html = _html()

    assert "todayStrategyMode" in html
    assert "Standard DotVerse" in html
    assert "Fixed Micro-Lot Signal" in html
    assert "Fib 23.6 Setup" in html
    assert "Fib 23.6 Confirmed Entry" not in html
    assert "_todaySetStrategyMode" in html


def test_today_fib_transform_uses_required_levels_and_guardrails():
    html = _html()

    assert "function _todayApplyFib236Preset" in html
    for token in ("fib12", "fib236", "fib382", "fib50", "fib618"):
        assert token in html
    assert "move_stop_at_price_level" in html
    assert "wait_retest" in html
    assert "confirmed_by_signal" in html


def test_today_fib_copy_separates_preset_status_and_action():
    html = _html()

    assert "function _todayFibStatusLabel" in html
    assert "function _todayFibActionLine" in html
    assert "This setup looks for entry on a shallow retracement inside the current trend." in html
    assert "Entry at Fib 23.6, stop at Fib 12, targets at Fib 38.2 and 61.8." in html
    assert "Waiting for 23.6 confirmation" in html
    assert "23.6 confirmed" in html
    assert "Confirmed by signal engine" in html
    assert "Do not chase - wait for retest" in html
    assert "Setup invalid" in html
    assert "Confirmation source" in html
    assert "Selected timeframe" in html
    assert "Entry rule" in html
    assert "Protection rule" in html
    assert "Current Fib status" not in html
    assert "Wait 23.6 close" not in html


def test_today_build_plan_applies_strategy_before_selection():
    html = _html()
    build_start = html.index("async function _todayBuildPlan")
    select_pos = html.index("var plan=_todaySelectPlan", build_start)
    apply_pos = html.index("_todayApplyStrategyModeToOpps", build_start)

    assert apply_pos < select_pos


def test_today_order_payload_sends_fib_metadata_to_mt5_order():
    html = _html()
    payload_start = html.index("function _todayLegOrderPayload")
    payload = html[payload_start : payload_start + 2200]

    assert "strategy_mode" in payload
    assert "fib_trigger" in payload
    assert "fib_move_sl_to" in payload
    assert "tp1:assignedTp" in payload
    assert "tp2:null" in payload
    assert "tp3:null" in payload
    assert "trailing:!!leg.trailing" in payload


def test_today_fib_preset_is_entry_authority_over_generic_entry_brain_wait():
    html = _html()

    assert "function _todayFibOwnsExecutionGate" in html

    readiness_start = html.index("function _todayV2EffectiveReadiness")
    readiness = html[readiness_start : readiness_start + 1200]

    assert "var fibGate=_todayFibOwnsExecutionGate(o)" in readiness
    assert "if(fibGate && (mode==='wait'||mode==='scale_in')) return rd" in readiness
    assert "if(mode==='wait') return {text:'Brain says wait', cls:'wait'}" in readiness

    card_start = html.index("function _todayV2EntryBrainCard")
    card = html[card_start : card_start + 2600]

    assert "Fib 23.6 preset controls entry" in card
    assert "Structure note" in card


def test_today_strategy_preset_verdict_layer_judges_found_trades_not_scan_discovery():
    html = _html()

    assert "function _todayStrategyPresetEvidence" in html
    assert "function _todayStrategyPresetVerdictCard" in html
    assert "function _todaySignalQualityCriteriaPanel" in html
    assert "function _todayQualityCriterion" in html

    evidence_start = html.index("function _todayStrategyPresetEvidence")
    evidence = html[evidence_start : evidence_start + 9000]
    assert "mode=_todayStrategyMode()" in evidence
    assert "label=_todayStrategyModeLabel(mode)" in evidence
    assert "scanCount:window._todayScanCount||plan.length" in evidence
    assert "horizonLabel:horizonLabel" in evidence
    assert "actions=window._todayCandidateActionCounts||{}" in evidence
    assert "brokerFiltered=parseInt(window._todayBrokerFilteredCount||0)||0" in evidence
    assert "leftOut=parseInt(window._todayLeftOut||0)||0" in evidence
    assert "quality={directional:0,confirmed:0,likely:0,hypothesis:0,good:0,excellent:0,rrOk:0,spreadOk:0,btVerified:0}" in evidence
    assert "qualityCriteria={" in evidence
    assert "gate: WR 50%+, PF 1.0+, 30 trades, expectancy 0.10+" in evidence
    assert "blockers={brainWait:0,scaleIn:0,liveWait:0,invalid:0,broker:brokerFiltered,sizing:0,other:0}" in evidence
    assert "blockerSummary:blockerBits.join(' · ')" in evidence
    assert "Good enough for today\\'s pace" in evidence
    assert "Too small for target" in evidence
    assert "Waiting for Fib retest" in evidence
    assert "scaleOut" in evidence
    assert "scaleInAdvisory" in evidence
    assert "fib.confirmed" in evidence
    assert "fib.waiting" in evidence
    assert "fib.invalid" in evidence

    card_start = html.index("function _todayStrategyPresetVerdictCard")
    card = html[card_start : card_start + 4200]
    assert "Strategy preset verdict" in card
    assert "Scan finds trades first" in card
    assert "selected strategy preset turns those found trades" in card
    assert "selected" in card
    assert "deferred" in card
    assert "on watch" in card
    assert "add/replace candidate" in card
    assert "broker filtered" in card
    assert "Why not stronger yet" in card
    assert "scale-out" in card
    assert "scale-in watch" in card
    assert "Fib:" in card

    panel_start = html.index("function _todaySignalQualityCriteriaPanel")
    panel = html[panel_start : panel_start + 2600]
    assert "Signal quality criteria" in panel
    assert "Direction" in panel
    assert "Confluence" in panel
    assert "R:R + cost" in panel
    assert "Backtest edge" in panel
    assert "Execution" in panel
    assert "Target fit" in panel
    assert "not just BUY or SELL" in panel
    assert "clean reward/risk" in panel

    render = _extract_last_function("_todayRenderPlan")
    assert "strategyEvidence=_todayStrategyPresetEvidence(plan, usable, c, targetPath)" in render
    assert "window._todayLastStrategyEvidence=strategyEvidence" in render
    assert "_todayStrategyPresetVerdictCard(strategyEvidence,money2)" in render
    assert render.index("_todayV2ScoutPanel(targetPath,c,money2)") < render.index("_todayStrategyPresetVerdictCard(strategyEvidence,money2)")
