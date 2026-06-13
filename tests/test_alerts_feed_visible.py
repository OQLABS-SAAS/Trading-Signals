"""Static contract tests confirming the Telegram signal feed is visible in the main Alerts tab.

The owner must see the feed when they click the Alerts nav item (which calls showAlerts),
NOT only when they navigate to Settings → Alerts.

Checks:
  1. showAlerts() output contains id='tgScanFeed'
  2. showAlerts() output contains "Telegram Signals" section heading
  3. showAlerts() calls dvLoadScanAlerts (i.e. it's wired in the setTimeout at the end)
  4. The feed container appears BEFORE the al-toolbar (top of page, not buried at bottom)
  5. dvLoadScanAlerts is also still present in the _spAlerts (Settings) path (both kept)
  6. The showAlerts Telegram section includes the "exact signals" sub-line
"""
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text()


def _show_alerts_block():
    """Return the text of the showAlerts function body."""
    start = HTML.index("async function showAlerts(")
    # Grab 12000 chars — the full function is ~10k chars
    return HTML[start: start + 12000]


# ─────────────────────────────────────────────────────────────────────────────
# 1. tgScanFeed in showAlerts output
# ─────────────────────────────────────────────────────────────────────────────

def test_show_alerts_contains_tg_scan_feed():
    """showAlerts() must include the tgScanFeed container in its HTML output."""
    block = _show_alerts_block()
    assert "tgScanFeed" in block, \
        "tgScanFeed must be injected by showAlerts(), not only by _spAlerts()"


# ─────────────────────────────────────────────────────────────────────────────
# 2. "Telegram Signals" heading in showAlerts
# ─────────────────────────────────────────────────────────────────────────────

def test_show_alerts_contains_telegram_signals_heading():
    """showAlerts() must include the 'Telegram Signals' section heading."""
    block = _show_alerts_block()
    assert "Telegram Signals" in block, \
        "'Telegram Signals' heading must appear in the showAlerts() HTML output"


# ─────────────────────────────────────────────────────────────────────────────
# 3. dvLoadScanAlerts called from showAlerts
# ─────────────────────────────────────────────────────────────────────────────

def test_show_alerts_calls_dv_load_scan_alerts():
    """showAlerts() must call dvLoadScanAlerts() in its post-render callback."""
    block = _show_alerts_block()
    assert "dvLoadScanAlerts" in block, \
        "dvLoadScanAlerts must be called from showAlerts() (in the setTimeout at the end)"


def test_show_alerts_dv_load_scan_alerts_in_settimeout():
    """dvLoadScanAlerts must be in the setTimeout block at the end of showAlerts."""
    block = _show_alerts_block()
    # Find the last setTimeout in the function block
    last_timeout_pos = block.rfind("setTimeout")
    assert last_timeout_pos >= 0, "setTimeout must be present in showAlerts"
    tail = block[last_timeout_pos:]
    assert "dvLoadScanAlerts" in tail, \
        "dvLoadScanAlerts must be called inside the showAlerts setTimeout"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Feed appears before al-toolbar (top of page)
# ─────────────────────────────────────────────────────────────────────────────

def test_tg_scan_feed_appears_before_al_toolbar_in_show_alerts():
    """The tgScanFeed section must appear BEFORE the al-toolbar in showAlerts output."""
    block = _show_alerts_block()
    feed_pos = block.find("tgScanFeed")
    toolbar_pos = block.find("al-toolbar")
    assert feed_pos >= 0, "tgScanFeed must be in showAlerts block"
    assert toolbar_pos >= 0, "al-toolbar must be in showAlerts block"
    assert feed_pos < toolbar_pos, \
        "tgScanFeed section must come BEFORE al-toolbar (should be at the top of the page)"


# ─────────────────────────────────────────────────────────────────────────────
# 5. _spAlerts still has feed too (Settings path preserved)
# ─────────────────────────────────────────────────────────────────────────────

def test_sp_alerts_still_has_tg_scan_feed():
    """_spAlerts (Settings panel) must still contain tgScanFeed (both paths preserved)."""
    start = HTML.index("function _spAlerts(")
    block = HTML[start: start + 3000]
    assert "tgScanFeed" in block, \
        "_spAlerts Settings panel must still include tgScanFeed"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Sub-line in showAlerts Telegram section
# ─────────────────────────────────────────────────────────────────────────────

def test_show_alerts_telegram_sub_line():
    """The Telegram section in showAlerts must include the 'dollar amounts' sub-line."""
    block = _show_alerts_block()
    assert "dollar amounts" in block, \
        "The Telegram feed section in showAlerts must include the 'dollar amounts' sub-line"
