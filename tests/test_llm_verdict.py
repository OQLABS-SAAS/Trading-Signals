import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.llm.verdict import (  # noqa: E402
    build_fallback_structured,
    build_signal_context_block,
    build_verdict_structure_messages,
    derive_verdict_action,
)


def test_derive_verdict_action_from_keyword_balance():
    assert derive_verdict_action("bullish upside and strong buy case") == "BUY"
    assert derive_verdict_action("bearish downside and weak sell case") == "SELL"
    assert derive_verdict_action("mixed evidence") == "HOLD"


def test_build_fallback_structured_always_has_agent_cards():
    fallback = build_fallback_structured(
        {
            "market_report": "Bullish structure",
            "investment_debate_state": {"bear_history": "Valuation concern"},
        },
        "Buy with controlled risk",
    )

    assert fallback["action"] == "BUY"
    assert fallback["confidence"] == "MEDIUM"
    assert len(fallback["agents"]) == 8
    assert fallback["agents"][0]["name"] == "Market Analyst"


def test_build_signal_context_block_uses_dotverse_signal_fields():
    block = build_signal_context_block(
        {"sig": "BUY", "tf": "4h", "entry": "1.10", "sl": "1.09", "tp": "1.12", "rr": "2.0", "confLbl": "CONFIRMED"}
    )

    assert "DOTVERSE SIGNAL" in block
    assert "Direction: BUY" in block
    assert "R:R 1:2.0" in block
    assert "DotVerse confidence: CONFIRMED" in block


def test_build_verdict_structure_messages_contains_agent_context_and_json_contract():
    messages = build_verdict_structure_messages(
        "EURUSD",
        "Final verdict text",
        {"market_report": "Market report details"},
        {"signal": "SELL", "tf": "1h"},
    )

    assert messages[0]["role"] == "user"
    assert "Extract a structured trade plan" in messages[0]["content"]
    assert "[Market Analyst] Market report details" in messages[0]["content"]
    assert '"action":"BUY|SELL|HOLD"' in messages[0]["content"]
