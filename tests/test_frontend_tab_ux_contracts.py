from pathlib import Path
import re


HTML = Path("static/index-v2-prototype.html").read_text()


def test_canonical_flow_tracks_today_through_act():
    assert "const steps=['today','market','signals','understand','verdict','size','act'];" in HTML
    for label in [
        "Step 1 of 7 · TODAY",
        "Step 2 of 7 · MARKET",
        "Step 3 of 7",
        "Step 4 of 7 · UNDERSTAND",
        "Step 5 of 7 · VERDICT",
        "Step 6 of 7 · SIZE",
        "Step 7 of 7 · ACT",
    ]:
        assert label in HTML
    assert "DotVerse\\'s 7-step trading flow" in HTML
    assert "6-step trading flow" not in HTML
    assert "Step 0 of 6" not in HTML


def test_mobile_bottom_bar_exposes_core_trading_journey():
    mobile_start = HTML.index('<div class="mobile-tab-bar" id="mobileTabBar">')
    mobile = HTML[mobile_start:]
    for nav in ["today", "market", "signals", "understand", "verdict", "size", "act"]:
        assert f'data-mob-nav="{nav}"' in mobile
    for nav in ["portfolio", "agent", "automations", "settings"]:
        assert f'data-mob-nav="{nav}"' not in mobile


def test_signal_footer_hands_off_to_understand_with_selected_or_top_signal():
    assert "function _sfViewInUnderstand()" in HTML
    assert "loadSignalContext(candidate" in HTML
    assert 'onclick="_sfViewInUnderstand();">View in Understand' in HTML


def test_alert_and_markov_controls_do_not_render_as_dead_buttons():
    assert '<button class="al-dis-btn" onclick="this.closest(' in HTML
    assert '<button class="al-new-btn" onclick="var r=document.querySelector' in HTML
    assert "markov-cell" in HTML
    assert "markov-cell\" data-state=\"bull-to-bull\"" in HTML
    assert "markov-cell\" data-state=\"bear-to-bear\"" in HTML
    assert "markov-cell" in HTML and "cursor:default" in HTML
    assert "markov-cell" not in "\n".join(
        line for line in HTML.splitlines() if "markov-cell" in line and "cursor:pointer" in line
    )
    assert "font-size:122px" not in HTML


def test_verdict_state_is_bound_to_selected_signal():
    assert "function _resetVerdictStateForSignal(reason)" in HTML
    assert "function _verdictOwnsSignal(sig, keyName)" in HTML
    start = HTML.index("function loadSignalContext(o, opts)")
    end = HTML.index("// Load a signal from the", start)
    block = HTML[start:end]

    assert "_resetVerdictStateForSignal('signal-context-change')" in block
    assert "prevSignalKey !== nextSignalKey" in block

    verdict_start = HTML.index("function showVerdict()")
    verdict_end = HTML.index("function _vRunAnalysis()", verdict_start)
    verdict_block = HTML[verdict_start:verdict_end]
    assert "_verdictOwnsSignal(sig, '_verdictPrewarmSignalKey')" in verdict_block
    assert "_verdictOwnsSignal(sig, '_lastVerdictSignalKey')" in verdict_block


def test_signal_cards_review_setup_instead_of_implying_direct_execution():
    assert "Review Setup" in HTML
    assert "Trade This Signal" not in HTML


def test_backtest_gate_matches_visible_30_trade_promise():
    assert "Min 30 trades" in HTML
    assert "min_trades: 30" in HTML
    assert re.search(r"min_trades:\s*3\b", HTML) is None


def test_understand_actions_explain_user_objectives():
    assert "Challenge the setup before sizing." in HTML
    assert "Calculate cash in, lots, risk, and profit." in HTML
    assert "Historical check. Trust only 30+ trades." in HTML
    assert "Copy TradingView research script, not a live order." in HTML
    assert "Watch this setup and notify on movement." in HTML
    assert "und-alert-title" in HTML
    assert "und-alert-sub" in HTML
    refresh_start = HTML.index("async function dvRefreshAlertBtn()")
    refresh_end = HTML.index("// Re-render watchlist", refresh_start)
    refresh = HTML[refresh_start:refresh_end]
    assert "btn.querySelector('.und-alert-title')" in refresh
    assert "btn.querySelector('.und-alert-sub')" in refresh
