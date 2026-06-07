from pathlib import Path


HTML = Path("static/index-v2-prototype.html").read_text()


def _block(start_marker: str, end_marker: str) -> str:
    start = HTML.index(start_marker)
    end = HTML.index(end_marker, start)
    return HTML[start:end]


def test_size_has_shared_contract_size_helpers_for_execution_quantities():
    assert "function _szNormalizeAssetType(assetType)" in HTML
    assert "function _szContractSize(assetType, sym, forexContractSize)" in HTML
    assert "function _szBrokerLotUnits(assetType, sym)" in HTML
    assert "function _szNativeLotsFromUnits(units, assetType, sym)" in HTML
    assert "if(a === 'fx' || a === 'forex'" in HTML
    assert "if(/XAG/.test(s)) return 5000" in HTML
    assert "if(/XAU/.test(s)) return 100" in HTML
    assert "if(/(WTI|USOIL|UKOIL|BRENT|CL)/.test(s)) return 1000" in HTML


def test_size_summary_uses_broker_lots_not_raw_commodity_units():
    block = _block("function szCalc(){", "function szRRToggle(key)")

    assert "lots=_szNativeLotsFromUnits(posSize, assetType, ticker)" in block
    assert "lotsDisplay=_szFormatNativeSize(posSize, assetType, ticker)" in block
    assert "lots=null" not in block
    assert "posSize.toFixed(2)+(assetType==='index'?' contracts':' shares')" not in block


def test_size_ladder_and_mt5_payload_use_native_lot_conversion():
    ladder = _block("function szLadderRender() {", "function szLadderRefresh(opts)")
    legs = _block("function _szBuildExecutionLegs(){", "// ── Pre-trade confirmation card")

    assert "return _szFormatNativeSize(units, assetType, ticker)" in ladder
    assert "return _szNativeLotsFromUnits(units, assetType, ticker)" in ladder
    assert "var lots = _szNativeLotsFromUnits(units, assetType, sig.sym || '')" in legs
    assert "lots: parseFloat(calc.lots) || _szNativeLotsFromUnits(units0, assetType, sig.sym || '')" in legs
    assert "assetType === 'forex' ? units / contractSize : units" not in legs


def test_act_executes_every_size_ladder_leg_not_only_first_one():
    block = _block("function _actExecuteGo(){", "function actLogToPortfolio()")

    assert "const executionLegs=hasSizeCalc && typeof _szBuildExecutionLegs === 'function' ? _szBuildExecutionLegs() : []" in block
    assert "if(typedQty>0 && executionLegs.length === 1)" in block
    assert "if(typedQty>0 && executionLegs.length){" not in block
    assert "const orderRequests = executionLegs.map(function(leg)" in block
    assert "Promise.all(orderRequests)" in block
    assert "catch(function(err)" in block
    assert "finally(function()" in block
    assert "_szBuildExecutionLegs()[0]" not in block
    assert 'data-multi-leg="true"' in HTML
    assert "Multi-ladder sizing is locked here so Act sends the exact SIZE plan" in HTML
    assert "Exact MT5 orders" in HTML
    assert "Orders DotVerse will send to MT5" in HTML
    assert "TP ${target} · risk $" in HTML
    assert "' lots</span>'" in HTML
    assert "Place MT5 order${_actMultiLeg?'s':''}" in HTML
    assert "Place '+nT+' MT5 order" in HTML
