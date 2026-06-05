"""OpenAI narration prompt and merge helpers."""

from __future__ import annotations

from typing import Any


ALLOWED_NARRATION_KEYS = {
    "summary",
    "narrative",
    "rsi_assessment",
    "trend_assessment",
    "macd_assessment",
    "volume_assessment",
    "supertrend_assessment",
    "rsi_beginner",
    "macd_beginner",
    "ema_beginner",
    "volume_beginner",
    "atr_beginner",
    "bb_beginner",
    "overall_beginner",
}


def _safe_atr_pct(indicators: dict[str, Any]) -> float:
    try:
        atr = float(indicators.get("atr") or 0)
        price = max(float(indicators.get("price") or 1), 0.01)
        return round((atr / price) * 100, 2)
    except (TypeError, ValueError):
        return 0.0


def build_openai_narration_prompt(
    result: dict[str, Any],
    ticker: str,
    asset_type: str,
    indicators: dict[str, Any],
    timeframe: str,
) -> str:
    return f"""You are a data narrator for traders. Your ONLY job is to describe what the numbers below mean in plain English.

STRICT RULES:
- ONLY reference the exact numbers provided below. Do not invent or estimate any data.
- Do not predict future price movement. Do not say "price will" or "expect to."
- Do not add information not present in the data.
- Your audience is BEGINNER traders. Explain every trading term in simple everyday language.
- Avoid jargon. If you must use a term (RSI, MACD, etc.), immediately explain what it means.
- Be concise. Use the actual numbers. Make it feel like a smart friend explaining the chart.

TICKER: {ticker} ({asset_type}, {timeframe} timeframe)
SIGNAL: {result.get('signal')} | CONFIDENCE: {result.get('confidence')}
PRICE: {indicators.get('price')} | CHANGE: {indicators.get('chg_1d')}%
RSI (14): {indicators.get('rsi')}
MACD HISTOGRAM: {indicators.get('macd_hist')}
EMA TREND: {indicators.get('ema_trend')} | EMA20: {indicators.get('ema20')} | EMA50: {indicators.get('ema50')}
ATR (14): {indicators.get('atr')} ({_safe_atr_pct(indicators)}% of price)
VOLUME RATIO: {indicators.get('vol_ratio')}x vs 30d avg
BOLLINGER POSITION: {indicators.get('bb_pos')} | BB WIDTH: {indicators.get('bb_width')}
SUPERTREND: {indicators.get('supertrend')}
SUPPORT: {indicators.get('support')} | RESISTANCE: {indicators.get('resistance')}
ENTRY: {result.get('entry') or 'N/A (HOLD - no trade setup)'} | STOP LOSS: {result.get('stop_loss') or 'N/A'}
TP1: {result.get('tp1') or 'N/A'} | TP2: {result.get('tp2') or 'N/A'} | TP3: {result.get('tp3') or 'N/A'}

Return JSON with these keys ONLY:
- "summary": 2 sentences for a beginner - what is happening with this asset right now, using the numbers above
- "narrative": 3 sentences explaining the trade setup in simple language, referencing specific values
- "rsi_assessment": 1 sentence explaining RSI {indicators.get('rsi')} in plain English
- "trend_assessment": 1 sentence explaining the EMA trend simply
- "macd_assessment": 1 sentence explaining MACD in beginner terms
- "volume_assessment": 1 sentence explaining volume ratio simply
- "supertrend_assessment": 1 sentence explaining supertrend simply
- "rsi_beginner": 1 sentence - what RSI means for someone who has never traded
- "macd_beginner": 1 sentence - what MACD means for a complete beginner
- "ema_beginner": 1 sentence - what the EMA trend means for a complete beginner
- "volume_beginner": 1 sentence - what the volume ratio means for a complete beginner
- "atr_beginner": 1 sentence - explain ATR as "how much the price typically moves" for a beginner
- "bb_beginner": 1 sentence - explain Bollinger Bands position in the simplest possible way
- "overall_beginner": 2 sentences - the big picture in the simplest terms a non-trader would understand

Return ONLY valid JSON. No markdown."""


def merge_narration_fields(result: dict[str, Any], narration: dict[str, Any]) -> dict[str, Any]:
    merged = dict(result)
    for key in ALLOWED_NARRATION_KEYS:
        value = narration.get(key)
        if isinstance(value, str):
            merged[key] = value
    return merged
