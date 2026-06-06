import re
from pathlib import Path


HTML = Path(__file__).resolve().parents[1] / "static" / "index-v2-prototype.html"


def _source():
    return HTML.read_text()


def test_market_recomputes_verdict_from_live_prices():
    source = _source()

    assert "function _mktLiveCondition(data, map)" in source
    assert "VIX is '+_mktPctText(vixChg)" in source
    assert "_mktUpdateConditionChip(liveState)" in source
    assert "id=\"mktCondLabel\"" in source
    assert "id=\"mktCondDesc\"" in source
    assert "id=\"mktCondFilter\"" in source
    assert "id=\"mktCondCta\"" in source


def test_market_group_badges_are_live_not_hardcoded_positive():
    source = _source()

    assert "id=\"mktBadgeIndices\"" in source
    assert "id=\"mktBadgeCrypto\"" in source
    assert "_mktSetGroupBadge('mktBadgeIndices', _mktAvgChange(data, TM, ['SPY','QQQ','DIA','IWM']))" in source
    assert "_mktSetGroupBadge('mktBadgeCrypto', _mktAvgChange(data, TM, ['BTC','ETH','SOL','BNB']))" in source
    assert '<span class="mkt-sc-badge">+0.82% avg</span>' not in source
    assert '<span class="mkt-sc-badge">+1.9% avg</span>' not in source


def test_market_expanded_rows_sync_change_and_trend():
    source = _source()

    assert 'id="mkexchg-${m.sym}"' in source
    assert 'id="mktrend-${m.sym}"' in source
    assert "const exChgEl=document.getElementById('mkexchg-'+disp)" in source
    assert "const trendEl=document.getElementById('mktrend-'+disp)" in source
    assert "const barEl=document.getElementById('mkbar-'+disp)" in source


def test_market_analysis_click_sets_correct_asset_context():
    source = _source()

    assert "function _mktAssetForSymbol(sym)" in source
    assert "function _mktSyncQuickAsset(sym, asset)" in source
    assert "if(asset==='equity') asset='stock'" in source
    assert "_mktSyncQuickAsset(sym, asset)" in source
    assert "'SPY':'equity'" in source
    assert "'AAPL':'stock'" in source
    assert "assetSel.value=asset" in source


def test_market_has_first_class_opportunity_desk_with_signal_badges():
    source = _source()

    assert "mkt-opp-hero" in source
    assert "Opportunity Map" in source
    assert "mkt-lane" in source
    assert "asset-class lanes" in source
    assert "guided trade badges" in source
    assert "review a badge in Signal before sizing" in source
    assert "mktOppDesk" in source
    assert "mktOppCount" in source
    assert "mktOppAvgConf" in source
    assert "Market → Signal" in source
    assert "opp-badge" in source
    assert "sc-badge" in source
    assert "Today motion" in source


def test_market_runs_own_opportunity_scan_not_today_redirect():
    source = _source()

    assert "async function _mktRunOpportunityScan()" in source
    assert "_runScanBase(groups)" in source
    assert "Scanning Market for live trade badges" in source
    assert "_mktRunOpportunityScan();" in source
    assert "Open SIGNAL tab to run a live scan" not in source
    assert "go scout on Today" not in source


def test_market_trade_cards_route_into_signal_journey():
    source = _source()
    open_body = re.search(
        r"function _mktOpenSignalFromEl\(el\)\{(?P<body>.*?)\n\}",
        source,
        re.S,
    ).group("body")

    assert "function _mktOpenSignalFromEl(el)" in source
    assert "setNav('signals')" in source
    assert "showSignalFeed()" in source
    assert "window._sfResultCache={html:_mktSelectedSignalHtml(o),opps:[o],displayOpps:[o],ts:Date.now(),source:'market-selected'}" in source
    assert "loadSignalContext" not in open_body
    assert "function _mktAnalyseSignalFromEl(el)" in source
    assert "loadSignalContext(o)" in source


def test_market_primary_cta_targets_rendered_lane_chips():
    source = _source()

    assert "function _mktOpenTopSignal()" in source
    assert "document.querySelector('.mkt-lane-chip, .mkt-opp-card')" in source
    assert 'onclick="_mktOpenTopSignal();">Review top Signal' in source
    assert "Review top setup" in source
    assert "Open strongest" not in source
    assert "document.querySelector('.mkt-opp-card'); if(c) _mktOpenSignalFromEl(c); else _mktRunOpportunityScan();" not in source


def test_market_scan_uses_full_ticker_map_and_refreshes_market_payload():
    source = _source()

    assert "function _mktTickerMap()" in source
    assert "const TM=_mktTickerMap()" in source
    assert "var state=_mktLiveCondition(window._mktLastLiveData||{}, _mktTickerMap())" in source
    assert "window._sfResultCache={html:'',opps:opps,displayOpps:opps,ts:Date.now(),source:'market-scan'}" in source
    assert "window._sfResultCache=window._sfResultCache&&window._sfResultCache.html?window._sfResultCache" not in source
