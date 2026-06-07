from pathlib import Path


HTML = Path("static/index-v2-prototype.html").read_text()


def test_signal_handoff_keeps_browsable_context_across_tabs():
    assert "function _normalizeSignalContext(o, overrides)" in HTML
    assert "function _rememberSignalHandoff(o, opts)" in HTML
    assert "function _signalHandoffMove(delta)" in HTML
    assert "Browse the same opportunity set without rescanning" in HTML
    assert "All Signals" in HTML
    assert "${_signalHandoffBarHtml()}" in HTML


def test_trade_this_signal_routes_to_size_before_act():
    start = HTML.index("function tradeThisSignal(")
    end = HTML.index("function sfSetFilter", start)
    block = HTML[start:end]

    assert "setNav('size')" in block
    assert "showSize()" in block
    assert "setNav('act')" not in block
    assert "showAct()" not in block


def test_market_open_does_not_replace_signals_with_single_card_cache():
    start = HTML.index("function _mktOpenSignalFromEl")
    end = HTML.index("function _mktAnalyseSignalFromEl", start)
    block = HTML[start:end]

    assert "_rememberSignalHandoff(o,{handoffList:list,handoffSource:'market-scan'})" in block
    assert "_mktPrimeSignalCacheFromList(o,list)" in block
    assert "_mktSelectedSignalHtml(o)" not in block
    assert "opps:[o]" not in block


def test_market_signal_cache_renders_browsable_handoff_without_rescan():
    start = HTML.index("function _mktPrimeSignalCacheFromList")
    end = HTML.index("function _mktOpenSignalFromEl", start)
    block = HTML[start:end]

    assert "_signalHandoffListFor(selected, {handoffList:list})" in block
    assert "html: _signalHandoffBarHtml() + '<div class=\"opp-list\">' + cards + '</div>'" in block
    assert "displayOpps: signals" in block
    assert "source: 'market-scan'" in block


def test_market_all_signals_clears_reduced_market_cache():
    start = HTML.index("function _signalHandoffBackToSignals")
    end = HTML.index("function _signalHandoffBarHtml", start)
    block = HTML[start:end]

    assert "window._sfResultCache.source === 'market-scan'" in block
    assert "window._sfResultCache = null" in block
    assert "window._sfFullResultCache = null" in block
    assert "window._signalHandoff = null" in block
    assert "window._sfPreserveStratModeOnce = false" in block


def test_market_mode_handoff_preserves_requested_signal_mode_once():
    show_start = HTML.index("function showSignalFeed()")
    show_end = HTML.index("/* ── Backtest scan cache", show_start)
    show_block = HTML[show_start:show_end]
    market_start = HTML.index("function _mktRenderCockpit()")
    market_end = HTML.index("async function _loadMomentumWindows", market_start)
    market_block = HTML[market_start:market_end]

    assert "window._sfPreserveStratModeOnce === true" in show_block
    assert "if(!_preserveMode) window._stratMode = 'all'" in show_block
    assert "p.id==='sm-'+_activeMode" in show_block
    assert "window._sfPreserveStratModeOnce=true;setNav('signals');showSignalFeed();" in market_block


def test_understand_removes_unsized_skip_to_act_shortcut():
    assert "Skip to Act" not in HTML
    assert "Back to Signals list" in HTML


def test_live_signal_constructors_use_canonical_signal_schema():
    assert "window._activeSignal=_normalizeSignalContext({" in HTML
    assert "window._activeSignal = _normalizeSignalContext({" in HTML
    assert "window._activeSignal = _normalizeSignalContext(d," in HTML
    assert "window._activeSignal={\n" not in HTML


def test_signal_schema_normalizes_backend_and_frontend_aliases():
    start = HTML.index("function _normalizeSignalContext(o, overrides)")
    end = HTML.index("function _signalKey(o)", start)
    block = HTML[start:end]

    assert "src.sym || src.ticker || src.symbol" in block
    assert "src.sig || src.signal || src.dir || src.direction" in block
    assert "src.sl != null ? src.sl : (src.stop_loss != null ? src.stop_loss : src.stop)" in block
    assert "src.tp != null ? src.tp : (src.tp1 != null ? src.tp1" in block
    assert "asset_type: asset" in block


def test_signal_schema_normalizes_fx_to_forex_before_sizing():
    start = HTML.index("function _dvNormalizeAssetType(asset)")
    end = HTML.index("function _normalizeSignalContext(o, overrides)", start)
    block = HTML[start:end]

    assert "a === 'fx'" in block
    assert "return 'forex'" in block
