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
    assert "Each row below is one MT5 order." in source
    assert "MT5 volume is lots, units, contracts, or shares; cash in is margin; controls is position value." in source
    assert "Every leg below has its own cash in, controlled value" not in source
    assert "MT5 volume for this order." in source
    assert "Position value controlled." in source
    assert "function legSizeText(l)" in source
    assert "esc(legSizeText(l))" in source


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
    assert "if(window._todayMt5Online===true&&window._todayLastMt5State&&window._todayLastMt5State.account) return 'Live MT5 equity'" in source
    assert "todayAcctSource" in source
    assert "window._todayMt5Online" in source
    assert "function _todayAccountIsConnected(a)" in source
    assert "a.connected===true||a.is_connected===true||a.online===true||s==='connected'||s==='online'" in source
    assert "window._todayMt5Online=window._todayMt5Online===true || list.some(_todayAccountIsConnected)" in source
    assert "window._todayMt5Online=window._todayMt5Online===true || d.connected===true" in source
    assert "function _todayBridgeMt5StateToGlobalAccount(d)" in source
    assert "if(window._todayLastMt5State) _todayBridgeMt5StateToGlobalAccount(window._todayLastMt5State)" in source
    assert "if(d&&d.account) window._todayLastMt5State=d" in source
    assert "id:'__mt5_live__'" in source
    # Item 1 (2026-06-10): the bridge must use the shared honest virtual-account
    # builder (LIVE/DEMO/UNKNOWN from /api/mt5/state) - never a hardcoded LIVE label.
    assert "function _dvVirtualEaAccount(st)" in source
    assert "_dvVirtualEaAccount(d)" in source
    assert "if(!window._mt5Accounts.length && d.connected===true)" in source
    assert "if(idx<0 && window._mt5Accounts.length===1) idx=0" in source
    assert "status: connected?'online':(prev.status||'disconnected')" in source
    assert "_todayBridgeMt5StateToGlobalAccount(d)" in source
    assert "function _todayCanPlaceMt5()" in source


def test_mt5_poll_keeps_today_live_state_fresh():
    source = _source()

    assert "function _mt5RememberLiveState(d)" in source
    assert "window._mt5LastState = d" in source
    assert "if (typeof _todayBridgeMt5StateToGlobalAccount === 'function')" in source
    assert "_todayBridgeMt5StateToGlobalAccount(d)" in source
    assert "window._todayLastMt5State = d" in source
    assert "if (d.connected === true) window._todayMt5Online = true" in source

    poll = source[source.index("function mt5Poll()") : source.index("function mt5LoadTab()")]
    load = source[source.index("function mt5LoadTab()") : source.index("function mt5CancelOrder")]
    assert "_mt5RememberLiveState(d)" in poll
    assert "_mt5RememberLiveState(d)" in load
    assert "window._mt5LastState = d" not in poll
    assert "window._mt5LastState = d" not in load


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
    assert "var bottomOrderNote=protect?'new entries paused':(!mt5CanPlace?((window._todayMt5Online!==true)?'MT5 offline':((mt5Perm&&mt5Perm.text)||'MT5 not ready'))" in source
    assert ".today-v2-btn:disabled,.today-v2-review:disabled" in source


def test_today_v2_blocks_mt5_permission_and_broker_symbol_gates():
    source = _source()

    assert "function _todayMt5PermissionStatus()" in source
    assert "trade_permission_issue" in source
    assert "MT5 AutoTrading off" in source
    assert "function _todayMt5SymbolStatus(o)" in source
    assert "function _todayMt5TradableSet()" in source
    assert "function _todayMt5ResolveBrokerSymbol(sym)" in source
    assert "function _todayMt5BrokerExecutableScore(o)" in source
    assert "AMZN:['AMAZON']" in source
    assert "DIS:['DISNEY']" in source
    assert "ticker:_todayMt5SymbolForTrade(o)||o.sym" in source
    assert "_todayMt5BrokerExecutableScore(b)-_todayMt5BrokerExecutableScore(a)" in source
    assert "Not available on this MT5 account" in source
    assert "Trading disabled for this MT5 symbol" in source
    assert "String(spec.trade_mode)==='0'" in source
    assert "function _todayMt5UsesVtMarketsProfile()" in source
    assert "var perm=_todayMt5PermissionStatus();" in source
    assert "var sym=_todayMt5SymbolStatus(o);" in source
    assert "if(sym&&!sym.ok) return {text:sym.text, cls:'wait'};" in source
    assert "return window._todayMt5Online===true && (!perm||perm.ok);" in source


def test_today_v2_allocates_basket_risk_only_to_executable_setups():
    source = _source()

    assert "var candidates=[]" in source
    assert "if(o._minRiskPlace<=cap+1e-9)" in source
    assert "var active=candidates.slice()" in source
    assert "basket risk was reallocated to executable setups" in source
    assert "cap*(weight/activeWeight)" in source
    assert "return Math.max(0, used || 0)" in source
    assert "return Math.max(0, used || 0.6)" not in source


def test_today_v2_fixed_micro_lot_mode_uses_account_rule_and_broker_minimums():
    source = _source()

    assert "function _todayFixedMicroLotForAccount(acct)" in source
    assert "Math.floor(acct/1000)*0.01" in source
    assert "function _todayBrokerLotSpec(o)" in source
    assert "function _todaySizeFixedMicroTrade(o, acct, capPct)" in source
    assert "fixed micro-lot is below broker minimum" in source
    assert "Fixed micro-lot rule: every $1,000 account equity opens 0.01 lot" in source
    assert "if(_todayStrategyMode()==='fixed_micro_lot')" in source
    assert "o._multiEnabled=false" in source
    assert "var unitLabel=lots.toFixed(2)+' lots · fixed micro-lot'" in source
    assert "unitLabel=requestedLots.toFixed(2)+' lot rule · below broker minimum'" in source


def test_today_v2_dedupes_selected_basket_by_broker_symbol():
    source = _source()

    assert "var key=(_todayMt5SymbolForTrade(o)||o.sym||'').toUpperCase();" in source
    assert "if(seen[key]) continue;" in source
    assert "var candidateKey=(_todayMt5SymbolForTrade(candidate)||candidate.sym||'').toUpperCase();" in source
    assert "var planKey=(_todayMt5SymbolForTrade(p)||p.sym||'').toUpperCase();" in source
    assert "same broker symbol already in basket" in source


def test_today_v2_explains_requested_vs_actual_risk_after_lot_rounding():
    source = _source()

    assert "function _todayRiskFitNote(o, s)" in source
    assert "Allocated '+target.toFixed(2)+'%; actual '+actual.toFixed(2)+'% after broker lot step/stop distance." in source
    assert "var riskFitNote=_todayRiskFitNote(o,s)" in source
    assert "riskFitNote||''" in source


def test_today_v2_explains_wait_for_price_in_plain_language():
    source = _source()

    assert "live price is no longer close enough to the planned entry" in source
    assert "Wait for price to return near entry, or rebuild Today for a fresh setup." in source
    assert "Wait for price to come back near entry, or rebuild Today for a fresh setup." in source
    assert "should wait for price instead of chasing" not in source
    assert "entry is slightly chased right now" not in source


def test_today_v2_compresses_multiladder_instead_of_auto_single_when_possible():
    source = _source()

    assert "var execLadder=ladder.slice()" in source
    assert "while(execLadder.length>1)" in source
    assert "lots*((parseFloat(l.share)||0)/sumShares) >= minLot-1e-9" in source
    assert "lots>=minLot*2-1e-9" in source
    assert "compressedSplit:compressed" in source
    assert "var compressedScale=actualScale&&legs.some" in source
    assert "DotVerse compressed the preset so every order clears broker minimum lot size" in source
