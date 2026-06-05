import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.llm.narration import (  # noqa: E402
    build_openai_narration_prompt,
    merge_narration_fields,
)


def test_build_openai_narration_prompt_contains_exact_market_values():
    prompt = build_openai_narration_prompt(
        {"signal": "BUY", "confidence": "HIGH", "entry": 1.1, "stop_loss": 1.09, "tp1": 1.12},
        "EURUSD",
        "forex",
        {"price": 1.105, "chg_1d": 0.2, "atr": 0.01, "rsi": 58, "ema20": 1.1, "ema50": 1.09},
        "1h",
    )

    assert "TICKER: EURUSD (forex, 1h timeframe)" in prompt
    assert "SIGNAL: BUY | CONFIDENCE: HIGH" in prompt
    assert "ATR (14): 0.01 (0.9% of price)" in prompt
    assert "Return ONLY valid JSON" in prompt


def test_merge_narration_fields_only_accepts_known_string_keys():
    original = {"signal": "BUY", "summary": "old"}
    merged = merge_narration_fields(
        original,
        {
            "summary": "new",
            "narrative": "plain explanation",
            "unknown": "ignored",
            "rsi_beginner": 123,
        },
    )

    assert original["summary"] == "old"
    assert merged["signal"] == "BUY"
    assert merged["summary"] == "new"
    assert merged["narrative"] == "plain explanation"
    assert "unknown" not in merged
    assert "rsi_beginner" not in merged
