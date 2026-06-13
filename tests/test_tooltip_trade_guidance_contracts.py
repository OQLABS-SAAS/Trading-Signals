"""Tooltip guidance contracts for the P4 beginner-language rewrite.

The handoff called out that many tooltips merely named the UI box instead of
explaining what the trader should do. These tests lock the high-traffic rewrite
batch to action-oriented, trade-aware guidance.
"""
from pathlib import Path
import re


HTML = Path("static/index-v2-prototype.html").read_text(encoding="utf-8")


def _guide_block(key: str) -> str:
    match = re.search(
        rf"'{re.escape(key)}':\s*\{{(?P<body>.*?)\n  \}},",
        HTML,
        flags=re.S,
    )
    assert match, f"Missing guide block for {key}"
    return match.group("body")


def _body_text(key: str) -> str:
    block = _guide_block(key)
    match = re.search(r"body:\s*'(?P<body>(?:\\'|[^'])*)'", block, flags=re.S)
    assert match, f"Missing body text for {key}"
    return match.group("body").replace("\\'", "'")


def test_high_impact_tooltips_tell_trader_what_to_do():
    keys = [
        "order-flow-cvd",
        "order-flow-buy-pressure",
        "order-flow-sell-pressure",
        "order-flow-real-buyer",
        "order-flow-poser-buyer",
        "order-flow-real-seller",
        "order-flow-poser-seller",
        "candle-footprint",
        "fear-greed",
        "market-conditions",
        "scanner-table",
        "scanner-tf-cell",
        "market-top-opportunities",
        "market-latest-news",
        "mtf-cell",
        "journey-step-discover",
        "journey-step-today",
        "journey-step-market",
        "journey-step-understand",
        "journey-step-verdict",
        "verdict-agent-card",
        "auto-sent",
        "auto-recommended",
        "act-exchange-section",
        "act-exchange-selector",
        "act-exchange-place",
        "act-exchange-orders",
        "act-exchange-confirm",
    ]
    action_words = (
        "wait",
        "reduce size",
        "smaller size",
        "skip",
        "confirm",
        "verify",
        "protect",
        "continue",
        "do not",
        "before",
        "after entry",
    )
    for key in keys:
        body = _body_text(key).lower()
        assert len(body) >= 220, f"{key} tooltip is too thin to teach the trade"
        assert any(word in body for word in action_words), (
            f"{key} tooltip must explain a trader action, not only define the UI"
        )


def test_tooltips_do_not_claim_exchange_or_sentiment_automation_is_entry_signal():
    auto_sent = _body_text("auto-sent").lower()
    exchange = _body_text("act-exchange-section").lower()
    place = _body_text("act-exchange-place").lower()
    assert "it is not a reason to enter" in auto_sent
    assert "after entry" in auto_sent
    assert "separate from mt5" in exchange
    assert "omar clicks the final irreversible confirm" in place


def test_scanner_and_market_tooltips_preserve_review_before_execution_flow():
    scanner = _body_text("scanner-table").lower()
    top = _body_text("market-top-opportunities").lower()
    market = _body_text("market-conditions").lower()
    assert "not an instruction to enter immediately" in scanner
    assert "signal/understand/verdict" in scanner
    assert "still needs your execution checks" in top
    assert "capital preservation comes first" in market
