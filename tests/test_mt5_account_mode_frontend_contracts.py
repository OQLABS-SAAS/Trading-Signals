from pathlib import Path


HTML = Path("static/index-v2-prototype.html").read_text()


def test_mt5_frontend_surfaces_demo_live_account_mode():
    assert "function _mt5AccountMode(dataOrMode)" in HTML
    assert "function _mt5ModeLabel(dataOrMode)" in HTML
    assert "MT5 ' + mode" in HTML
    assert "demo account detected" in HTML
    assert "live account detected" in HTML
    # A5 fix 3: "account mode unknown" replaced with human-readable syncing phrase
    assert "account details syncing" in HTML
    # A5 fix 3: literal "MT5 UNKNOWN" removed from all render paths
    assert "MT5 UNKNOWN" not in HTML
    assert "mode === 'DEMO' ? '#5de8a0' : '#c9a84c'" in HTML
    assert "_mt5SetStatus(d.connected, lastSeenStr, accountType)" in HTML
