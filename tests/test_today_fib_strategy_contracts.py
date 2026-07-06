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
    assert "Fib 23.6 Confirmed Entry" in html
    assert "_todaySetStrategyMode" in html


def test_today_fib_transform_uses_required_levels_and_guardrails():
    html = _html()

    assert "function _todayApplyFib236Preset" in html
    for token in ("fib12", "fib236", "fib382", "fib50", "fib618"):
        assert token in html
    assert "move_stop_at_price_level" in html
    assert "wait_retest" in html
    assert "confirmed_by_signal" in html


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
