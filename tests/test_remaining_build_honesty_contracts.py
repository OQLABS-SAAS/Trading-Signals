"""Contracts for late build-readiness fixes across Signal/Scanner/Market/Calibration."""

import re
from pathlib import Path

from backend.app.intelligence.calibration import CALIBRATION_GATE, build_not_ready_response


HTML = Path("static/index-v2-prototype.html").read_text(encoding="utf-8")
APP = Path("app.py").read_text(encoding="utf-8")


def _extract_function(name: str) -> str:
    markers = (f"function {name}(", f"async function {name}(")
    starts = [HTML.rfind(m) for m in markers if m in HTML]
    start = max(starts) if starts else None
    assert start is not None, f"{name} not found"
    depth = 0
    for idx in range(start, len(HTML)):
        if HTML[idx] == "{":
            depth += 1
        elif HTML[idx] == "}":
            depth -= 1
            if depth == 0:
                return HTML[start : idx + 1]
    raise AssertionError(f"{name} body not closed")


def _html_const_int(name: str) -> int:
    match = re.search(rf"const {re.escape(name)} = (\d+);", HTML)
    assert match, f"{name} const not found"
    return int(match.group(1))


def test_calibration_gate_is_100_and_copy_is_observational():
    assert CALIBRATION_GATE == 100
    assert "CALIBRATION_GATE, fit_isotonic_calibration" in APP
    assert "GATE = CALIBRATION_GATE" in APP
    assert "total >= gate" in APP
    assert "gate = CALIBRATION_GATE" in APP
    assert "GATE = 100" not in APP
    assert "gate = 100" not in APP
    assert "{total}/{gate} labels" in APP

    result = build_not_ready_response(17)
    assert result["ready"] is False
    assert "Need 83 more labeled trades" in result["message"]

    assert "100 labeled trade outcomes" in HTML
    assert "observational only and does not change live signal confidence, ranking, sizing, or execution" in HTML
    assert "does not yet feed back into live signal ranking, sizing, or execution" in HTML
    assert "80% truly means 80%" not in HTML
    assert "50 labeled trades" not in HTML


def test_today_does_not_claim_global_calibration_model():
    assert "global model" not in HTML
    assert "similar historical trades" not in HTML
    assert "Pattern check:" in HTML
    assert "not a calibrated win probability" in HTML


def test_scanner_auto_entry_copy_matches_alert_and_confirm_flow():
    assert "places the trade in MT5 automatically" not in HTML
    assert "places the trade in MT5 without you needing to click" not in HTML
    assert "fully automated entry engine" not in HTML
    assert "auto-entry fires" not in HTML
    assert "alert-and-confirm, not unattended MT5 order placement" in HTML
    assert "you confirm before any MT5 order is queued" in HTML


def test_load_signal_context_syncs_analyze_asset_and_timeframe_after_render():
    block = _extract_function("loadSignalContext")
    assert "window._activeSignal = Object.assign({}, signal);" in block
    assert "_dvSyncAnalyzeControls(signal);" in block
    assert "showUnderstand();_dvSyncAnalyzeControls(window._activeSignal);" in block

    sync = _extract_function("_dvSyncAnalyzeControls")
    assert "window._dvAsset = asset;" in sync
    assert "window._dvTF = tf;" in sync
    assert "dvTickerInput" in sync
    assert "qpTickerInput" in sync
    assert ".dv-tf-pill" in sync


def test_scanner_rows_do_not_duplicate_one_signal_across_all_timeframes():
    block = _extract_function("_scRenderLive")
    assert "grouped[key].tfs[tfk]=r" in block
    assert "tfCell('15m')" in block
    assert "tfCell('1h')" in block
    assert "tfCell('4h')" in block
    assert "tfCell('1d')" in block
    assert 'data-s15="${c15.data}"' in block
    assert 'data-s1h="${c1h.data}"' in block
    assert 'data-s4h="${c4h.data}"' in block
    assert 'data-s1d="${c1d.data}"' in block
    assert 'data-s15="${sig}"' not in block
    assert "4H scout view" not in HTML


def test_scanner_run_uses_shared_signal_universe_for_all_timeframes():
    block = _extract_function("scRunScan")
    assert "_runScanBase(groups" in block
    assert "['15m','1h','4h','1d']" in block
    assert "await _todayAutoBacktestCandidates(scOpps)" in block
    assert "_btVerified:o._btVerified" in block
    assert "'/api/scan-list'" not in block
    assert "real timeframe candidates" in block


def test_today_build_plan_scans_all_timeframes_before_goal_selection():
    block = _extract_function("_todayBuildPlan")
    assert "_runScanBase(groups" in block
    assert "['15m','30m','1h','4h','1d','1w']" in block
    assert "asset_type:g.asset_type" in block
    assert "window._todayOpps = ranked" in block
    assert "window._todayDeferredOpps" in block
    assert "dvFetch('/api/scan-list'" not in block


def test_shared_scan_engine_cannot_leave_today_spinner_waiting_forever():
    block = _extract_function("_runScanBase")
    assert "_DV_SIGNAL_UNIVERSE_TIMEOUT_MS = 12000" in HTML
    assert "_DV_TODAY_SIGNAL_UNIVERSE_TIMEOUT_MS = 180000" in HTML
    assert "_DV_SCAN_BATCH_TIMEOUT_MS = 18000" in HTML
    assert _html_const_int("_DV_TODAY_SIGNAL_UNIVERSE_TIMEOUT_MS") > _html_const_int("_DV_SIGNAL_UNIVERSE_TIMEOUT_MS")
    assert "function dvFetchAbortableT" in HTML
    assert "ctrl.abort()" in HTML
    assert "onProgress(0, _expectedTotal, 0)" in block
    assert "scan_mode: scanMode || 'standard'" in block
    assert "max_seconds" not in block
    assert "scanMode === 'today' ? _DV_TODAY_SIGNAL_UNIVERSE_TIMEOUT_MS : _DV_SIGNAL_UNIVERSE_TIMEOUT_MS" in block
    assert "cache_hit: !!universe.cache_hit" in block
    assert "refresh_pending: !!universe.refresh_pending" in block
    assert "dvFetchAbortableT('/api/signal-universe/run'" in block
    assert "_DV_SIGNAL_UNIVERSE_TIMEOUT_MS" in block
    assert ": _DV_SIGNAL_UNIVERSE_TIMEOUT_MS" in block
    assert "signal universe scan timed out; falling back to batched scanner" in block
    assert "dvFetchAbortableT(req.url, req.opts, _DV_SCAN_BATCH_TIMEOUT_MS)" in block
    assert "scan request timed out" in block


def test_today_build_plan_cannot_leave_scan_spinner_waiting_forever():
    block = _extract_function("_todayBuildPlan")
    render = _extract_function("_todayRenderPlan")
    assert "_DV_TODAY_BUILD_TIMEOUT_MS = 270000" in HTML
    assert _html_const_int("_DV_TODAY_BUILD_TIMEOUT_MS") - _html_const_int("_DV_TODAY_SIGNAL_UNIVERSE_TIMEOUT_MS") >= 90000
    assert "window._todayBuildRunSeq=(window._todayBuildRunSeq||0)+1" in block
    assert "window._todayBuildAbortCtrl" in block
    assert "return window._todayBuildRunSeq===_todayRunSeq;" in block
    assert "window._todayBuildRunSeq===_todayRunSeq &&" not in block
    assert "function _todayRenderNoPlanDirect" in block
    assert "Try scan again" in block
    assert "var _todayBuildTimedOut=false" in block
    assert "var _todayBuildWatchdog=setTimeout(function(){" in block
    assert "_todayAbortCtrl.abort()" in block
    assert "Today full scan timed out before it could finish" in block
    assert "Scanning the full market map for the best setups" in block
    assert "Latest full scan" in block
    assert "refreshing in background" in block
    assert "Full scan complete" in block
    assert "clearTimeout(_todayBuildWatchdog)" in block
    assert "if(!opps.length){" in block
    assert "Today scanned your markets but found no usable BUY/SELL setups" in block
    assert "No executable Today basket" in block
    assert "_runScanBase(groups, _todayAbortCtrl?_todayAbortCtrl.signal:null" in block
    assert "}, 'today')" in block
    assert "var noTitle=window._todayNoPlanTitle||''" in render


def test_today_goal_pace_uses_horizon_as_pacing_not_scan_filter():
    pace = _extract_function("_todayGoalPace")
    select = _extract_function("_todaySelectPlan")
    target = _extract_function("_todayV2TargetPath")
    assert "todayTarget=horizon==='daily'?remaining:Math.max(0,remaining/daysLeft)" in pace
    assert "periodGoal:goalVal" in pace
    assert "var plan=[], seen={}, goal=parseFloat(pace.todayTarget)" in select
    assert "today\\'s pace" in target
    assert "The rest of the '+_tpHorizonLow+' plan stays in Scout" in target


def test_today_auto_backtests_candidates_before_basket_actions():
    block = _extract_function("_todayAutoBacktestCandidates")
    build = _extract_function("_todayBuildPlan")
    classify = _extract_function("_todayClassifyBasketCandidate")
    assert "dvFetch('/api/backtest'" in block
    assert "_todayBtCache" in block
    assert "min_trades:30" in block
    assert "_btVerified:passes" in block
    assert "await _todayAutoBacktestCandidates(ranked)" in build
    assert "b._btVerified?1:0" in build
    assert "candidate._btVerified!==true" in classify
    assert "automatic backtest has not verified" in classify


def test_today_auto_backtest_preserves_insufficient_data_reason():
    block = _extract_function("_todayAutoBacktestCandidates")
    assert "_btValidityTier:bt?bt.validity_tier:null" in block
    assert "_btReason:passes?'automatic backtest verified':(bt&&bt.error?bt.error:'automatic backtest did not clear the gate')" in block


def test_today_v2_render_defines_horizon_label_before_target_copy_uses_it():
    block = _extract_function("_todayRenderPlan")
    definition = block.index("var _horizonLbl =")
    target_copy = block.index("_horizonLbl.toLowerCase()")
    assert definition < target_copy


def test_today_v2_explains_hidden_multi_timeframe_candidates():
    audit = _extract_function("_todayV2TimeframeAuditPanel")
    render = _extract_function("_todayRenderPlan")
    assert "Other timeframes checked" in audit
    assert "multi-timeframe scan" in audit
    assert "live-entry rule says skip now" in audit
    assert "basket risk was reallocated" in audit
    assert "_todayReadiness(o)" in audit
    assert "o._size.skipReason" in audit
    assert "_todayV2TimeframeAuditPanel(plan, usableIdx, esc)" in render
    assert render.index("today-v2-priorityTotals") < render.index("_todayV2TimeframeAuditPanel(plan, usableIdx, esc)")
    assert render.index("_todayV2TimeframeAuditPanel(plan, usableIdx, esc)") < render.index("today-v2-main")


def test_today_v2_surfaces_basket_totals_before_review_table():
    render = _extract_function("_todayRenderPlan")
    priority_idx = render.index("today-v2-priorityTotals")
    table_idx = render.index("Review trades")
    assert priority_idx < table_idx
    assert "New basket risk" in render[priority_idx:table_idx]
    assert "Total after placing" in render[priority_idx:table_idx]
    assert "Remaining buffer" in render[priority_idx:table_idx]
    assert "Cash in total" in render[priority_idx:table_idx]
    assert "Position value" in render[priority_idx:table_idx]


def test_today_v2_shows_lot_cash_and_position_value_per_trade_and_leg():
    render = _extract_function("_todayRenderPlan")
    assert "MT5 volume / cash / controls" in render
    assert "esc(s.unitLabel||'--')" in render
    assert "cash in '+money2(s.marginReq||0)" in render
    assert "controls '+money(s.notional||0)" in render
    assert "MT5 volume for this order" in render
    assert "Cash in: margin you put up" in render
    assert "Position value controlled" in render
    assert "Scale-out means DotVerse sends smaller orders from the same entry" in render


def test_shared_signal_mapper_carries_automatic_backtest_evidence():
    block = _extract_function("_dvSignalFromScanRow")
    assert "_btVerified: r._btVerified === true" in block
    assert "_btWr: r._btWr" in block
    assert "_btReason: r._btReason || null" in block


def test_quick_analyse_all_tf_uses_shared_scan_engine_and_mapper():
    block = _extract_function("qpAnalyse")
    assert "_runScanBase([{tickers:tickerList, asset_type:assetType, tfs:allTfs}]" in block
    assert "_dvSignalFromScanRow(r, r.timeframe || r.tf || '1d', assetType)" in block
    assert "await _todayAutoBacktestCandidates(rawOpps)" in block
    assert "dvFetch('/api/scan-list'" not in block


def test_quick_scan_all_markets_uses_shared_signal_mapper():
    block = _extract_function("qpScanAll")
    assert "_runScanBase(ALL_SCAN_GROUPS" in block
    assert "_dvSignalFromScanRow(r, r.timeframe || r.tf || '1d', r.asset_type || 'stock')" in block
    assert "await _todayAutoBacktestCandidates(rawOpps)" in block
    assert "return {" not in block[block.index("const rawOpps") : block.index("if (rawOpps.length")]


def test_signal_cards_use_fixed_micro_lot_rule_per_account_equity():
    helper = _extract_function("_dvSignalCardLotSize")
    quick_one = _extract_function("qpAnalyse")
    quick_all = _extract_function("qpScanAll")
    signals = _extract_function("_sfFetchSignals")
    normalize = _extract_function("_normalizeSignalContext")

    assert "Math.floor(acct/1000)" in helper
    assert "0.01" in helper
    assert "Every $1,000 account equity = 0.01 lot" in helper

    assert "_dvSignalCardLotLabel(o)" in quick_one
    assert "_dvSignalCardLotLabel(o)" in quick_all
    assert "_dvSignalCardLotLabel(o)" in signals
    assert "var signalLot = _dvSignalCardLotSize();" in normalize
    assert "volume:signalLot>0?signalLot:(src.volume!=null?src.volume:src.lot)" in normalize
    assert "lots:signalLot>0?signalLot:(src.lots!=null?src.lots:(src.volume!=null?src.volume:src.lot))" in normalize


def test_market_opportunity_scan_auto_backtests_before_cache():
    block = _extract_function("_mktRunOpportunityScan")
    assert "_runScanBase(groups)" in block
    assert "_dvSignalFromScanRow(r, r.timeframe || r.tf || '4H', r.asset_type || r.asset || 'stock')" in block
    assert "await _todayAutoBacktestCandidates(opps)" in block
    assert "b._btVerified?1:0" in block
    assert "window._mktOpportunityCache={opps:opps,ts:Date.now()}" in block


def test_today_entry_brain_recommends_without_unproven_live_scale_in_authority():
    load = _extract_function("_todayV2LoadEntryBrain")
    apply = _extract_function("_todayV2ApplyEntryBrainDecision")
    build = _extract_function("_todayBuildPlan")
    readiness = _extract_function("_todayV2EffectiveReadiness")
    scale_state = _extract_function("_todayV2ScaleState")
    place_one = _extract_function("_todayPlaceTrade")
    place_all = _extract_function("_todayPlaceAll")
    confirm = _extract_function("_todayConfirmAndPlace")
    can_execute = _extract_function("_todayCanExecuteNow")
    card = _extract_function("_todayV2EntryBrainCard")
    set_scale = _extract_function("_todayV2SetScale")
    set_mode = _extract_function("_todayV2SetLadderMode")
    assert "dvFetch('/api/entry-plan/advisory'" in load
    assert "_btVerified:o._btVerified===true" in load
    assert "_todayV2ApplyEntryBrainDecision(o, data)" in load
    assert "return o._entryBrainPromise" in load
    assert "data.execution_authority===true" in apply
    assert "data.recommended_mode==='scale_out'" in apply
    assert "data.recommended_mode==='single'" in apply
    authorized_block = apply[
        apply.index("if(data.execution_authority===true") : apply.index("}else if")
    ]
    assert "data.recommended_mode==='scale_in'" not in authorized_block
    assert "data.recommended_mode==='scale_in' || data.recommended_mode==='wait'" in apply
    assert "o._multiEnabled=false" in apply
    assert "o._multiEnabled=false" in build
    assert "await _todayV2LoadEntryBrain(o)" in build
    assert "Brain says wait" in readiness
    assert "Scale-in advisory" in readiness
    assert "legs.length>1" in scale_state
    assert "orders: active?legs.length:1" in scale_state
    assert "_todayExecutionReadiness(o)" in can_execute
    assert "rd.cls==='wait'" in can_execute
    assert "_todayCanExecuteNow(o)" in place_one
    assert "_todayCanExecuteNow(o)" in place_all
    assert "_todayCanExecuteNow(o)" in confirm
    assert "o._entryBrainUserOverride=true" in set_scale
    assert "o._entryBrainUserOverride=true" in set_mode
    assert "Advisory only - live execution authority is locked" in card
    assert "scale-in" in card


def test_today_live_price_monitor_cannot_overwrite_brain_wait_gate():
    live = _extract_function("_todayStartLivePrices")
    render = _extract_function("_todayRenderPlan")

    assert "var gate=(typeof _todayExecutionReadiness==='function')?_todayExecutionReadiness(o):null" in live
    assert "var blockedByGate=gate&&(gate.cls==='wait'||gate.cls==='invalid')" in live
    assert "label=gate.text+(label?' · live: '+label:'')" in live
    assert "else if(!_todayCanExecuteNow(o))" in live
    assert "cta.innerHTML=(gate&&gate.text?gate.text:'Not executable yet')" in live
    assert "cta.disabled=true" in live

    assert "var canExecuteNow=(typeof _todayCanExecuteNow==='function')?_todayCanExecuteNow(o):true" in render
    assert "var placeDisabled=!_todayCanPlaceMt5() || !canExecuteNow" in render
    assert "var placeLabel=!canExecuteNow?(rd&&rd.text?rd.text:'Not executable yet'):_todayV2PlaceCtaText(targetNeedsScout,false)" in render
    assert "readyNow<1?'No executable orders'" in render
    assert "readyNow<1?'wait for brain/price/broker gate'" in render


def test_recommendation_badge_requires_backtest_verified_signal():
    block = _extract_function("showUnderstand")
    assert "&& o._btVerified === true" in HTML
    assert "sig._btVerified === true || sig.btVerified === true" in block
    assert "var _hard = _notHold&&_conf&&_btOk" in block
    assert "DOTVERSE RECOMMENDS THIS TRADE" in block
    assert "HIGH AGREEMENT — BACKTEST NOT VERIFIED" in HTML


def test_dynamic_mobile_signal_and_scanner_taps_are_delegated():
    dom_block = HTML[HTML.index("document.addEventListener('DOMContentLoaded'") :]
    assert "e.target.closest && e.target.closest('.qual-ring')" in dom_block
    assert "closest('.qual-ring')) return" in dom_block
    assert "e.target.closest && e.target.closest('.sc-row')" in dom_block
    assert "document.querySelectorAll('.qual-ring').forEach(function(ring)" not in dom_block
    assert "document.querySelectorAll('.sc-row').forEach(function(row)" not in dom_block


def test_market_risk_off_language_uses_confirmed_only_consistently():
    live_condition = _extract_function("_mktLiveCondition")
    desk = _extract_function("_mktRenderOpportunityDesk")
    status = _extract_function("_mktStatusForSignal")
    assert "Filter: CONFIRMED signals only" in live_condition
    assert "'CONFIRMED only'" in desk
    assert "'75%+'" not in desk
    assert status.index("if(riskOff)") < status.index("if(lbl==='CONFIRMED'||conf>=80)")
    assert "if(lbl==='CONFIRMED') return {cls:'green',text:'confirmed'" in status
