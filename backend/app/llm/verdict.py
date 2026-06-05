"""Verdict structuring helpers for DeepSeek/TradingAgents output."""

from __future__ import annotations

from typing import Any


def _snip(text: Any, limit: int = 600) -> str:
    value = str(text or "").strip()
    if not value or value.lower() in ("none", ""):
        return "Report not available for this analysis run."
    return value[:limit] + "..." if len(value) > limit else value


def derive_verdict_action(decision: Any) -> str:
    text = str(decision or "").lower()
    bull_words = sum(1 for word in ["buy", "bullish", "long", "upside", "positive", "strong"] if word in text)
    bear_words = sum(1 for word in ["sell", "bearish", "short", "downside", "negative", "weak"] if word in text)
    if bull_words > bear_words:
        return "BUY"
    if bear_words > bull_words:
        return "SELL"
    return "HOLD"


def build_fallback_structured(state: dict[str, Any] | None, decision: Any) -> dict[str, Any]:
    state = state or {}
    debate = state.get("investment_debate_state", {}) if isinstance(state, dict) else {}
    action = derive_verdict_action(decision)
    agents = [
        {"name": "Market Analyst", "vote": action, "argument": _snip(state.get("market_report", ""))},
        {"name": "Sentiment Analyst", "vote": action, "argument": _snip(state.get("sentiment_report", ""))},
        {"name": "News Researcher", "vote": "HOLD", "argument": _snip(state.get("news_report", ""))},
        {"name": "Fundamentals Researcher", "vote": action, "argument": _snip(state.get("fundamentals_report", ""))},
        {"name": "Bull Researcher", "vote": "BUY", "argument": _snip(debate.get("bull_history", ""))},
        {"name": "Bear Researcher", "vote": "SELL", "argument": _snip(debate.get("bear_history", ""))},
        {"name": "Research Manager", "vote": action, "argument": _snip(state.get("investment_plan", ""))},
        {"name": "Risk Team", "vote": action, "argument": _snip(state.get("final_trade_decision", ""))},
    ]
    return {
        "action": action,
        "confidence": "MEDIUM",
        "summary": _snip(str(decision or ""), 500),
        "risk_team_notes": _snip(state.get("final_trade_decision", ""), 300),
        "positions": 3,
        "risk_ladder": [0.5, 1.0, 1.5],
        "tp_r_multiples": [1.5, 2.5, 3.5],
        "trailing": ["0.5x ATR after +1.5R", "0.5x ATR after +1.5R", "0.75x ATR after +2R"],
        "agents": agents,
    }


def build_verdict_structure_messages(
    ticker: str,
    verdict_text: Any,
    state: dict[str, Any] | None,
    signal_ctx: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    raw = str(verdict_text)[:3000]
    state = state or {}
    debate = state.get("investment_debate_state", {}) if isinstance(state, dict) else {}
    agent_ctx = (
        f"[Market Analyst] {_snip(state.get('market_report', ''), 300)}\n"
        f"[Sentiment Analyst] {_snip(state.get('sentiment_report', ''), 300)}\n"
        f"[News Researcher] {_snip(state.get('news_report', ''), 300)}\n"
        f"[Fundamentals Researcher] {_snip(state.get('fundamentals_report', ''), 300)}\n"
        f"[Bull Researcher] {_snip(debate.get('bull_history', ''), 300)}\n"
        f"[Bear Researcher] {_snip(debate.get('bear_history', ''), 300)}\n"
        f"[Research Manager] {_snip(state.get('investment_plan', ''), 300)}\n"
        f"[Risk Team] {_snip(state.get('final_trade_decision', ''), 300)}\n"
    )
    signal_block = build_signal_context_block(signal_ctx)
    return [{
        "role": "user",
        "content": (
            f"Extract a structured trade plan from this analysis of {ticker}. "
            "Return ONLY valid JSON with these exact keys:\n"
            '{"action":"BUY|SELL|HOLD",'
            '"confidence":"HIGH|MEDIUM|LOW",'
            '"summary":"2-3 sentences plain English for a beginner",'
            '"risk_team_notes":"1-2 sentences about stop loss management and risk controls",'
            '"dotverse_signal_review":"2-3 sentences: evaluate the DotVerse technical signal separately. Write N/A if no signal provided.",'
            '"positions":3,'
            '"risk_ladder":[0.5,1.0,1.5],'
            '"tp_r_multiples":[1.5,2.5,3.5],'
            '"trailing":["0.5x ATR after +1.5R","0.5x ATR after +1.5R","0.75x ATR after +2R"],'
            '"agents":['
            '{"name":"Market Analyst","vote":"BUY","argument":"4-6 sentences with their specific findings, data points, and reasoning"},'
            '{"name":"Sentiment Analyst","vote":"BUY","argument":"..."},'
            '{"name":"News Researcher","vote":"HOLD","argument":"..."},'
            '{"name":"Fundamentals Researcher","vote":"BUY","argument":"..."},'
            '{"name":"Bull Researcher","vote":"BUY","argument":"..."},'
            '{"name":"Bear Researcher","vote":"SELL","argument":"..."},'
            '{"name":"Research Manager","vote":"BUY","argument":"..."},'
            '{"name":"Risk Team","vote":"BUY","argument":"..."}'
            ']}\n\n'
            "Rules: positions=3-5 (HIGH=5, MEDIUM=4, LOW=3). "
            "risk_ladder must sum <=8%. Start small (0.5-1%), scale up. "
            "tp_r_multiples: TP as multiples of initial R. TP1 min 1.5R. "
            "If DotVerse signal is provided, calibrate tp_r_multiples against actual SL distance. "
            "HOLD: positions=1, risk_ladder=[0.5], trailing=['manual'], tp_r_multiples=[1.5].\n"
            "For agents: vote must match each agent's actual stance from their report. "
            "argument must be 4-6 sentences of detailed analysis from their specific report.\n\n"
            f"FINAL VERDICT:\n{raw}\n\n"
            f"AGENT REPORTS:\n{agent_ctx}"
            f"{signal_block}"
        ),
    }]


def build_signal_context_block(signal_ctx: dict[str, Any] | None) -> str:
    if not isinstance(signal_ctx, dict):
        return ""
    sig_dir = signal_ctx.get("sig", signal_ctx.get("signal", ""))
    sig_entry = signal_ctx.get("entry", "")
    sig_sl = signal_ctx.get("sl", "")
    sig_tp1 = signal_ctx.get("tp", signal_ctx.get("tp1", ""))
    sig_tp2 = signal_ctx.get("tp2", "")
    sig_tp3 = signal_ctx.get("tp3", "")
    sig_rr = signal_ctx.get("rr", "")
    sig_conf = signal_ctx.get("conf", signal_ctx.get("confLbl", ""))
    sig_tf = signal_ctx.get("tf", "")
    parts = [f"Direction: {sig_dir}", f"Timeframe: {sig_tf}"]
    if sig_entry:
        parts.append(f"Entry: {sig_entry}")
    if sig_sl:
        parts.append(f"Stop loss: {sig_sl}")
    if sig_tp1:
        parts.append(f"TP1: {sig_tp1}")
    if sig_tp2:
        parts.append(f"TP2: {sig_tp2}")
    if sig_tp3:
        parts.append(f"TP3: {sig_tp3}")
    if sig_rr:
        parts.append(f"R:R 1:{sig_rr}")
    if sig_conf:
        parts.append(f"DotVerse confidence: {sig_conf}")
    return "\n\nDOTVERSE SIGNAL (the app's own technical analysis - treat as separate context):\n" + " | ".join(parts)
