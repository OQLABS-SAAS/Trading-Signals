import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.llm.sentiment import (  # noqa: E402
    build_deepseek_sentiment_prompt,
    extract_negative_sentiment_hits,
    parse_json_array,
)


def test_build_deepseek_sentiment_prompt_numbers_headlines():
    prompt = build_deepseek_sentiment_prompt(["Bad guidance", "Strong revenue"])

    assert "return ONLY a JSON array" in prompt
    assert "1. Bad guidance" in prompt
    assert "2. Strong revenue" in prompt


def test_parse_json_array_handles_markdown_fences():
    parsed = parse_json_array('```json\n[{"score": -0.5, "sentiment": "negative"}]\n```')

    assert parsed == [{"score": -0.5, "sentiment": "negative"}]
    assert parse_json_array('{"not": "array"}') == []


def test_extract_negative_sentiment_hits_validates_score_label_and_index():
    hits = extract_negative_sentiment_hits(
        [
            {"score": -0.6, "sentiment": "negative", "reasoning": "Guidance cut."},
            {"score": -0.2, "sentiment": "negative", "reasoning": "Too mild."},
            {"score": 1.4, "sentiment": "negative", "reasoning": "Out of range."},
            {"score": -0.8, "sentiment": "positive", "reasoning": "Wrong label."},
            {"score": -0.7, "sentiment": "negative", "reasoning": "No matching headline."},
        ],
        ["Headline one", "Headline two", "Headline three", "Headline four"],
    )

    assert hits == [{"score": -0.6, "headline": "Headline one", "reasoning": "Guidance cut."}]
