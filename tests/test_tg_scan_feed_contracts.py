"""Static contract tests for the Telegram scan feed on the dashboard.

Mirrors test_a5_quickwins_contracts.py pattern: read HTML as text, assert markers.

Checks:
  1. tgScanFeed container element is present in _spAlerts HTML
  2. dvLoadScanAlerts function is defined
  3. /api/scan-alerts fetch is present inside dvLoadScanAlerts
  4. "Telegram Signals" section title is present
  5. Dollar-line markers (risks $, +$ at TP1) are present in the renderer
  6. "every 15 minutes" empty-state message present
  7. dvLoadScanAlerts() is called when alerts tab opens in showSettings
  8. The explainer sub-line ("exact signals") is present
"""
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Container
# ─────────────────────────────────────────────────────────────────────────────

def test_tg_scan_feed_container_present():
    """id='tgScanFeed' container must exist inside _spAlerts."""
    assert 'id="tgScanFeed"' in HTML, "tgScanFeed div must be in the HTML"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Function defined
# ─────────────────────────────────────────────────────────────────────────────

def test_dv_load_scan_alerts_function_defined():
    """dvLoadScanAlerts must be defined as a JS function."""
    assert "function dvLoadScanAlerts(" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# 3. Fetch call inside dvLoadScanAlerts
# ─────────────────────────────────────────────────────────────────────────────

def test_scan_alerts_fetch_present():
    """dvLoadScanAlerts must fetch /api/scan-alerts."""
    start = HTML.index("function dvLoadScanAlerts(")
    # Grab a generous block of the function body
    block = HTML[start: start + 3000]
    assert "/api/scan-alerts" in block, "/api/scan-alerts fetch must be inside dvLoadScanAlerts"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Section title
# ─────────────────────────────────────────────────────────────────────────────

def test_telegram_signals_title_present():
    """'Telegram Signals' section title must appear in the alerts panel."""
    assert "Telegram Signals" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# 5. Dollar-line markers
# ─────────────────────────────────────────────────────────────────────────────

def test_dollar_risk_marker_present():
    """Dollar risk marker ('risks $') must appear in the dvLoadScanAlerts renderer."""
    start = HTML.index("function dvLoadScanAlerts(")
    block = HTML[start: start + 3000]
    assert "risks $" in block, "Dollar risk amount marker must be in the card renderer"


def test_dollar_profit_marker_present():
    """Dollar profit marker ('+$') and 'at TP1' must appear in the renderer."""
    start = HTML.index("function dvLoadScanAlerts(")
    block = HTML[start: start + 3000]
    assert "+$" in block and "at TP1" in block, "+$ / at TP1 markers must be in the card renderer"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Empty-state message
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_state_message_present():
    """Empty-state message mentioning 15 minutes must be present."""
    start = HTML.index("function dvLoadScanAlerts(")
    block = HTML[start: start + 3000]
    assert "15 minutes" in block, "Empty-state '15 minutes' message must be present"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Wired into showSettings
# ─────────────────────────────────────────────────────────────────────────────

def test_dv_load_scan_alerts_called_on_alerts_tab():
    """dvLoadScanAlerts() must be triggered when the alerts tab opens in showSettings."""
    assert "tab==='alerts'" in HTML
    # Find the specific wiring line
    assert "dvLoadScanAlerts" in HTML[HTML.index("tab==='alerts'"):]


# ─────────────────────────────────────────────────────────────────────────────
# 8. Explainer sub-line
# ─────────────────────────────────────────────────────────────────────────────

def test_explainer_sub_line_present():
    """The 'exact signals sent to your Telegram' explainer must appear."""
    assert "exact signals sent to your Telegram" in HTML
