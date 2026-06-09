from pathlib import Path


HTML = Path("static/index-v2-prototype.html").read_text()


def test_signal_handoff_keeps_browsable_context_across_tabs():
    assert "function _normalizeSignalContext(o, overrides)" in HTML
    assert "function _rememberSignalHandoff(o, opts)" in HTML
    assert "function _signalHandoffMove(delta)" in HTML
    assert "Browse the same opportunity set without rescanning" in HTML
    assert "All Signals" in HTML
    assert "${_signalHandoffBarHtml()}" in HTML


def test_trade_this_signal_routes_to_review_gates_before_size_or_act():
    start = HTML.index("function tradeThisSignal(")
    end = HTML.index("function sfSetFilter", start)
    block = HTML[start:end]

    assert "setNav('understand')" in block
    assert "showUnderstand()" in block
    assert "setNav('size')" not in block
    assert "showSize()" not in block
    assert "setNav('act')" not in block
    assert "showAct()" not in block
    assert "_resetVerdictStateForSignal('trade-intent-change')" in block


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

    assert "_sfOpenFullSignals()" in block
    assert "_sfClearMarketHandoffCache()" not in block
    assert "showSignalFeed({full:true})" not in block


def test_full_signals_and_clear_filter_cannot_restore_filtered_cache():
    full_start = HTML.index("function _sfOpenFullSignals()")
    full_end = HTML.index("function _sfOpenFilteredSignals", full_start)
    full_block = HTML[full_start:full_end]
    render_start = HTML.index("function _sfRender()")
    render_end = HTML.index("/* ── Scanner section", render_start)
    render_block = HTML[render_start:render_end]
    cache_start = HTML.index("function _sfCacheMatchesView(cache)")
    cache_end = HTML.index("function _sfClearMarketHandoffCache", cache_start)
    cache_block = HTML[cache_start:cache_end]

    assert "window._condFilter = null" in full_block
    assert "window._sfResultCache = fullCache && _sfCacheMatchesView(fullCache) ? fullCache : null" in full_block
    assert "_sfOpenFullSignals();" in render_block
    assert "(cache.filterKey || null) === _sfFilterKey()" in cache_block
    assert "!!cache.verifiedOnly === !!window._sfVerifiedOnly" in cache_block
    assert "(cache.mode || 'all') === (window._stratMode || 'all')" in cache_block


def test_normal_signals_entry_does_not_reuse_market_handoff_cache():
    start = HTML.index("function showSignalFeed(opts)")
    end = HTML.index("/* ── Backtest scan cache", start)
    block = HTML[start:end]

    assert "var _marketHandoffEntry = window._sfUseMarketHandoffOnce === true || opts.marketHandoff === true" in block
    assert "window._sfUseMarketHandoffOnce = false" in block
    assert "window._sfResultCache.source === 'market-scan'" in block
    assert "window._sfResultCache = _sfCacheFresh(window._sfFullResultCache) ? window._sfFullResultCache : null" in block
    assert "window._signalHandoff = null" in block


def test_market_handoff_is_one_shot_not_canonical_signals_cache():
    start = HTML.index("function _mktOpenSignalFromEl")
    end = HTML.index("function _mktAnalyseSignalFromEl", start)
    block = HTML[start:end]

    assert "window._sfUseMarketHandoffOnce = true" in block
    assert "showSignalFeed({marketHandoff:true})" in block


def test_market_scan_does_not_poison_full_signals_cache():
    start = HTML.index("async function _mktRunOpportunityScan()")
    end = HTML.index("function showMarket()", start)
    block = HTML[start:end]

    assert "window._mktOpportunityCache={opps:opps,ts:Date.now()}" in block
    assert "window._sfResultCache={html:'',opps:opps,displayOpps:opps,ts:Date.now(),source:'market-scan'}" not in block
    assert "mktScanTfs=['15m','30m','1h','4h','1d','1w']" in block


def test_market_mode_handoff_preserves_requested_signal_mode_once():
    show_start = HTML.index("function showSignalFeed(opts)")
    show_end = HTML.index("/* ── Backtest scan cache", show_start)
    show_block = HTML[show_start:show_end]
    market_start = HTML.index("function _mktRenderCockpit()")
    market_end = HTML.index("async function _loadMomentumWindows", market_start)
    market_block = HTML[market_start:market_end]

    assert "window._sfPreserveStratModeOnce === true" in show_block
    assert "if(!_preserveMode) window._stratMode = 'all'" in show_block
    assert "p.id==='sm-'+_activeMode" in show_block
    assert "_sfOpenModeSignals('${m.id}')" in market_block


def test_market_mode_signal_route_clears_condition_filter():
    start = HTML.index("function _sfOpenModeSignals(mode)")
    end = HTML.index("function showSignalFeed(opts)", start)
    block = HTML[start:end]

    assert "_sfClearMarketHandoffCache()" in block
    assert "window._condFilter = null" in block
    assert "window._stratMode = mode || window._stratMode || 'all'" in block
    assert "window._sfResultCache = null" in block
    assert "window._sfPreserveStratModeOnce = true" in block


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


def test_shared_scan_base_prefers_canonical_signal_universe_with_legacy_fallback():
    start = HTML.index("async function _runScanBase(groups, signal")
    end = HTML.index("async function _sfFetchSignals", start)
    block = HTML[start:end]

    assert "dvFetch('/api/signal-universe/run'" in block
    assert "body:JSON.stringify({ groups: groups })" in block
    assert "window._dvSignalUniverseRun = universe" in block
    assert "if(universe.ready !== false && _universeResults.length > 0)" in block
    assert "signal universe returned no ready candidates" in block
    assert "run_id: universe.run_id" in block
    assert "provider_health: universe.provider_health || null" in block
    assert "url: '/api/scan-list'" in block
    assert "signal universe fetch error" in block


def test_cross_tab_signal_entry_points_use_full_signal_route():
    assert "data-nav=\"signals\" onclick=\"_sfOpenFullSignals();\"" in HTML
    assert "btn-view-sig btn-pipeline\" onclick=\"_sfOpenFullSignals();\"" in HTML
    assert "data-mob-nav=\"signals\" onclick=\"_sfOpenFullSignals();updateMobileTabs('signals');\"" in HTML
    assert "onclick=\"setNav('signals');showSignalFeed();\"" not in HTML
    assert "showSignalFeed&&showSignalFeed();" not in HTML
