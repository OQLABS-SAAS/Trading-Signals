import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.llm.review import (  # noqa: E402
    build_signal_quality_review_prompt,
    fallback_quality_review,
    normalize_quality_review,
)


def test_build_signal_quality_review_prompt_contains_signal_contract():
    prompt = build_signal_quality_review_prompt(
        {"ticker": "EURUSD", "signal": "BUY", "confidence": 82, "timeframe": "4h", "entry": 1.1, "stop_loss": 1.09}
    )

    assert "trading signal quality auditor" in prompt
    assert "- Ticker: EURUSD" in prompt
    assert "- Direction: BUY" in prompt
    assert '"quality_score": 1-10' in prompt


def test_fallback_quality_review_uses_raw_summary_prefix():
    fallback = fallback_quality_review("not json response")

    assert fallback["quality_score"] == 5
    assert fallback["summary"] == "not json response"
    assert fallback["recommendation"] == "review"


def test_normalize_quality_review_adds_required_defaults_and_signal_id():
    normalized = normalize_quality_review({"summary": "Looks fine"}, signal_id=42)

    assert normalized["summary"] == "Looks fine"
    assert normalized["quality_score"] == 5
    assert normalized["strengths"] == []
    assert normalized["signal_id"] == 42
    assert normalized["calibrated_review"] is True
