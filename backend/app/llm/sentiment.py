"""DeepSeek sentiment prompt and validation helpers."""

from __future__ import annotations

import json
import re
from typing import Any


def build_deepseek_sentiment_prompt(headlines: list[str], limit: int = 10) -> str:
    headline_block = "\n".join(f"{i + 1}. {headline}" for i, headline in enumerate(headlines[:limit]))
    return (
        "You are a financial news sentiment classifier. "
        "For each numbered headline below, return ONLY a JSON array "
        "where each element is an object with exactly three keys: "
        "\"score\" (float from -1.0 to +1.0), "
        "\"sentiment\" (one of: positive, neutral, negative), "
        "\"reasoning\" (one plain-English sentence explaining why, max 15 words). "
        "Do not add any text outside the JSON array. "
        "Headlines:\n" + headline_block
    )


def parse_json_array(raw_content: str) -> list[Any]:
    text = str(raw_content or "").strip()
    if not text:
        return []
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def extract_negative_sentiment_hits(
    llm_items: list[Any],
    headlines: list[str],
    *,
    threshold: float = -0.3,
) -> list[dict[str, Any]]:
    negatives: list[dict[str, Any]] = []
    for index, item in enumerate(llm_items):
        if not isinstance(item, dict):
            continue
        try:
            score = float(item.get("score", 0))
            sentiment = str(item.get("sentiment", "")).lower().strip()
            reasoning = str(item.get("reasoning", "")).strip()
        except (TypeError, ValueError):
            continue
        if not (-1.0 <= score <= 1.0):
            continue
        if sentiment != "negative" or score >= threshold:
            continue
        if index >= len(headlines):
            continue
        negatives.append({
            "score": score,
            "headline": headlines[index],
            "reasoning": reasoning,
        })
    return negatives
