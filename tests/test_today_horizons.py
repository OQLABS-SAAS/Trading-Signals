"""Static contract tests for the Today multi-horizon (daily/weekly/monthly) feature.

Mirrors test_a5_quickwins_contracts.py pattern: read HTML as text, assert markers.

Checks:
  1. todayHorizon select is present in the HTML (both Today render paths)
  2. select contains Daily, Weekly, Monthly options
  3. _todaySetHorizon function is defined
  4. Label update logic is present inside _todaySetHorizon
  5. Breadcrumb mentions both daily and monthly
  6. goalHorizon is present in _todayCfg default definition
  7. _todayDefaultHorizon helper function is defined
  8. _todaySaveCfg persists goalHorizon
"""
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text()


# ─────────────────────────────────────────────────────────────────────────────
# 1. todayHorizon select present
# ─────────────────────────────────────────────────────────────────────────────

def test_today_horizon_select_present():
    """id='todayHorizon' select must appear in the HTML (at least one render path)."""
    assert 'id="todayHorizon"' in HTML or "id='todayHorizon'" in HTML, \
        "todayHorizon select must be present in the HTML"


def test_today_horizon_select_in_both_render_paths():
    """todayHorizon select must appear in more than one location (both render paths)."""
    count = HTML.count('todayHorizon')
    assert count >= 2, f"todayHorizon must appear in both render paths, found {count} occurrences"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Daily / Weekly / Monthly options
# ─────────────────────────────────────────────────────────────────────────────

def test_today_horizon_daily_option():
    """The horizon select must contain a Daily option."""
    assert ">Daily<" in HTML or '>Daily</option' in HTML, \
        "Daily option must be in todayHorizon select"


def test_today_horizon_weekly_option():
    """The horizon select must contain a Weekly option."""
    assert ">Weekly<" in HTML or '>Weekly</option' in HTML, \
        "Weekly option must be in todayHorizon select"


def test_today_horizon_monthly_option():
    """The horizon select must contain a Monthly option."""
    assert ">Monthly<" in HTML or '>Monthly</option' in HTML, \
        "Monthly option must be in todayHorizon select"


# ─────────────────────────────────────────────────────────────────────────────
# 3. _todaySetHorizon function defined
# ─────────────────────────────────────────────────────────────────────────────

def test_today_set_horizon_function_defined():
    """_todaySetHorizon must be defined as a JS function."""
    assert "function _todaySetHorizon(" in HTML, \
        "_todaySetHorizon function must be defined"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Label update logic inside _todaySetHorizon
# ─────────────────────────────────────────────────────────────────────────────

def test_today_set_horizon_updates_label():
    """_todaySetHorizon must update the todayHorizonLabel element."""
    start = HTML.index("function _todaySetHorizon(")
    block = HTML[start: start + 2000]
    assert "todayHorizonLabel" in block, \
        "_todaySetHorizon must update the todayHorizonLabel DOM element"


def test_today_set_horizon_sets_goalHorizon():
    """_todaySetHorizon must write c.goalHorizon."""
    start = HTML.index("function _todaySetHorizon(")
    block = HTML[start: start + 2000]
    assert "goalHorizon" in block, \
        "_todaySetHorizon must set c.goalHorizon"


def test_today_horizon_label_span_present():
    """todayHorizonLabel span must appear in the render output for label updates to work."""
    assert "todayHorizonLabel" in HTML, \
        "todayHorizonLabel span id must appear in the HTML render"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Breadcrumb mentions daily and monthly
# ─────────────────────────────────────────────────────────────────────────────

def test_today_breadcrumb_mentions_daily():
    """The Today breadcrumb must mention 'daily' profit target."""
    assert "daily" in HTML.lower() and "daily, weekly" in HTML.lower(), \
        "Today breadcrumb must mention 'daily, weekly' profit target"


def test_today_breadcrumb_mentions_monthly():
    """The Today breadcrumb must mention 'monthly' profit target."""
    assert "monthly profit target" in HTML.lower() or \
           ("monthly" in HTML.lower() and "daily, weekly, or monthly" in HTML.lower()), \
        "Today breadcrumb must mention 'monthly' as a profit target option"


# ─────────────────────────────────────────────────────────────────────────────
# 6. goalHorizon in _todayCfg default
# ─────────────────────────────────────────────────────────────────────────────

def test_goalHorizon_in_todayCfg_default():
    """goalHorizon must appear in the _todayCfg default object literal."""
    assert "goalHorizon:'weekly'" in HTML or 'goalHorizon:"weekly"' in HTML, \
        "goalHorizon must have a default value of 'weekly' in _todayCfg"


# ─────────────────────────────────────────────────────────────────────────────
# 7. _todayDefaultHorizon helper
# ─────────────────────────────────────────────────────────────────────────────

def test_today_default_horizon_function_defined():
    """_todayDefaultHorizon helper must be defined."""
    assert "function _todayDefaultHorizon(" in HTML, \
        "_todayDefaultHorizon helper function must be defined"


# ─────────────────────────────────────────────────────────────────────────────
# 8. _todaySaveCfg persists goalHorizon
# ─────────────────────────────────────────────────────────────────────────────

def test_todaySaveCfg_persists_goalHorizon():
    """_todaySaveCfg must include goalHorizon in its persisted JSON."""
    start = HTML.index("function _todaySaveCfg(")
    block = HTML[start: start + 500]
    assert "goalHorizon" in block, \
        "_todaySaveCfg must persist goalHorizon in dv_todayCfg"
