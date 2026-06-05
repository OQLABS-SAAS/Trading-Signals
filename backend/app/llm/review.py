"""OpenAI signal-quality review helpers."""

from __future__ import annotations

from typing import Any


def build_signal_quality_review_prompt(signal_ctx: dict[str, Any]) -> str:
    return f"""You are a trading signal quality auditor. Review this signal and rate its quality.

SIGNAL:
- Ticker: {signal_ctx.get('ticker')}
- Direction: {signal_ctx.get('signal')}
- DotVerse Confidence: {signal_ctx.get('confidence', '?')}%
- Timeframe: {signal_ctx.get('timeframe', '?')}
- Trade Type: {signal_ctx.get('trade_type', '?')}
- Entry: {signal_ctx.get('entry', '?')}
- Stop Loss: {signal_ctx.get('stop_loss', '?')}
- Take Profit 1: {signal_ctx.get('tp1', '?')}

Evaluate:
1. Is the R:R ratio reasonable (>1:1)?
2. Does the trade type match the timeframe?
3. Is the confidence score plausible for this setup?
4. Any red flags (e.g., wide spread, news event, overnight gap risk)?

RETURN ONLY this JSON (no markdown):
{{"quality_score": 1-10, "summary": "1 sentence verdict", "strengths": ["bullet1","bullet2"], "weaknesses": ["bullet1","bullet2"], "flags": [], "recommendation": "take"/"review"/"skip"}}"""


def fallback_quality_review(raw_content: str = "") -> dict[str, Any]:
    return {
        "quality_score": 5,
        "summary": str(raw_content or "")[:200],
        "strengths": [],
        "weaknesses": [],
        "flags": [],
        "recommendation": "review",
    }


def normalize_quality_review(result: dict[str, Any], signal_id: Any = None) -> dict[str, Any]:
    normalized = dict(result or {})
    normalized.setdefault("quality_score", 5)
    normalized.setdefault("summary", "")
    normalized.setdefault("strengths", [])
    normalized.setdefault("weaknesses", [])
    normalized.setdefault("flags", [])
    normalized.setdefault("recommendation", "review")
    normalized["signal_id"] = signal_id
    normalized["calibrated_review"] = True
    return normalized
