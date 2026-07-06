import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(ROOT, "static", "index-v2-prototype.html")


def _html():
    with open(HTML_PATH, encoding="utf-8") as f:
        return f.read()


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
    order_pos = html.index("dvOrderFetch('/api/mt5/order'")
    payload = html[order_pos : order_pos + 1800]

    assert "strategy_mode" in payload
    assert "fib_trigger" in payload
    assert "fib_move_sl_to" in payload
    assert re.search(r"tp2:\s*o\.tp2", payload)
