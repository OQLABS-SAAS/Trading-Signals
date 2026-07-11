from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_require_tier_no_longer_blocks_private_app_users():
    source = APP.read_text()
    start = source.index("def require_tier(minimum):")
    end = source.index("# ─── AGENT TAB SESSION RATE LIMITER", start)
    block = source[start:end]

    assert "Private-app compatibility decorator" in block
    assert "subscription paywalls" in block
    assert "return f(*args, **kwargs)" in block
    assert "Upgrade required" not in block
    assert "required_tier" not in block
    assert "current_tier" not in block
    assert "return jsonify" not in block
    assert "), 402" not in block


def test_tier_removal_keeps_broker_safety_language():
    source = APP.read_text()
    start = source.index("def require_tier(minimum):")
    end = source.index("# ─── AGENT TAB SESSION RATE LIMITER", start)
    block = source[start:end]

    for phrase in [
        "login_required",
        "account ownership",
        "per-account EA secrets",
        "fresh MT5 state",
        "DEMO/LIVE mode checks",
        "tradeability",
        "duplicate-order protection",
    ]:
        assert phrase in block
