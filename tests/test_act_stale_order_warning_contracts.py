"""
Contract tests for Act-tab stale/stuck order warnings.

These tests verify that the frontend JS in static/index-v2-prototype.html:
  1. Declares a 120-second stale threshold (_MT5_STALE_SECS = 120).
  2. Has helper functions _mt5OrderAgeSecs and _mt5FmtAge.
  3. Emits a warning for stale pending/executing rows.
  4. Emits a subtle "Placed X ago" note for non-stale pending/executing rows.
  5. Gracefully omits age display when created_at is absent or unparseable.
  6. Does NOT emit any auto-cancel, auto-retry, or order-mutation logic near the warning.
"""

import re
import pytest

HTML_PATH = "static/index-v2-prototype.html"

@pytest.fixture(scope="module")
def html():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


# ── 1. Stale threshold constant ────────────────────────────────────────────────

def test_stale_threshold_constant_declared(html):
    """_MT5_STALE_SECS must be declared and set to 120."""
    assert "_MT5_STALE_SECS" in html, "_MT5_STALE_SECS constant not found in HTML"
    # Must be assigned 120 (allow spaces around =)
    assert re.search(r"_MT5_STALE_SECS\s*=\s*120\b", html), \
        "_MT5_STALE_SECS is not set to 120"


# ── 2. Helper functions present ────────────────────────────────────────────────

def test_age_helper_function_declared(html):
    """_mt5OrderAgeSecs must be declared as a function."""
    assert "function _mt5OrderAgeSecs" in html, \
        "_mt5OrderAgeSecs function not found in HTML"


def test_fmt_age_helper_function_declared(html):
    """_mt5FmtAge must be declared as a function."""
    assert "function _mt5FmtAge" in html, \
        "_mt5FmtAge function not found in HTML"


# ── 3. Stale warning markup ────────────────────────────────────────────────────

def test_stale_warning_text_present(html):
    """The stale warning message must reference 'may not have reached your broker'."""
    assert "may not have reached your broker" in html, \
        "Stale-order warning text not found in HTML"


def test_stale_warning_check_mt5_text_present(html):
    """The stale warning must advise the user to 'Check MT5'."""
    assert "Check MT5" in html, \
        "'Check MT5' advisory text not found in stale warning"


def test_stale_warning_uses_stale_threshold(html):
    """The render path must compare ageSecs against _MT5_STALE_SECS."""
    assert re.search(r"ageSecs\s*>=\s*_MT5_STALE_SECS", html), \
        "Stale threshold comparison (ageSecs >= _MT5_STALE_SECS) not found"


def test_stale_warning_shows_elapsed_time(html):
    """The stale warning must embed the formatted age string."""
    # The warning block uses ageStr in its text
    assert re.search(r"has been.*for.*ageStr", html, re.DOTALL), \
        "Stale warning does not include the elapsed ageStr in output"


def test_stale_warning_only_for_pending_executing(html):
    """The stale/age block must be gated on pending or executing status."""
    # The if-block must check o.status
    assert re.search(
        r"o\.status\s*===\s*['\"]pending['\"]\s*\|\|\s*o\.status\s*===\s*['\"]executing['\"]",
        html
    ), "Stale check is not gated on pending/executing status"


# ── 4. Subtle "Placed ago" for non-stale rows ─────────────────────────────────

def test_placed_ago_text_present(html):
    """Non-stale pending/executing rows must show 'Placed' + age + 'ago'."""
    assert re.search(r"Placed.*ago", html), \
        "'Placed X ago' text not found in HTML"


def test_placed_ago_uses_age_str(html):
    """The placed-ago note must embed the formatted ageStr."""
    assert re.search(r"Placed.*\+.*ageStr.*\+.*ago", html, re.DOTALL), \
        "'Placed' + ageStr + 'ago' pattern not found"


# ── 5. Graceful handling of missing/unparseable timestamp ─────────────────────

def test_age_helper_returns_null_on_falsy_input(html):
    """_mt5OrderAgeSecs must return null when createdAt is falsy."""
    assert re.search(r"if\s*\(\s*!createdAt", html), \
        "Guard for missing createdAt not found in _mt5OrderAgeSecs"


def test_age_helper_returns_null_on_nan(html):
    """_mt5OrderAgeSecs must check isNaN(t) and return null."""
    assert "isNaN(t)" in html, \
        "isNaN guard not found in _mt5OrderAgeSecs"


def test_age_helper_rejects_negative_age(html):
    """_mt5OrderAgeSecs must return null for negative ages (future timestamps)."""
    assert re.search(r"ageSecs\s*>=\s*0\s*\?", html), \
        "Negative-age guard not found in _mt5OrderAgeSecs"


def test_stale_block_only_rendered_when_age_not_null(html):
    """The stale/placed-ago block must only render when ageSecs !== null."""
    assert re.search(r"ageSecs\s*!==\s*null", html), \
        "Null-check on ageSecs not found before rendering warning"


def test_try_catch_in_age_helper(html):
    """_mt5OrderAgeSecs must be wrapped in try/catch for parse safety."""
    # Locate the function body and confirm try/catch is present within it
    m = re.search(r"function _mt5OrderAgeSecs\(.*?\}\s*\n", html, re.DOTALL)
    if m:
        snippet = m.group(0)
    else:
        snippet = html  # fallback: check whole file
    assert "try {" in snippet or "try{" in snippet, \
        "try/catch not found in _mt5OrderAgeSecs"


# ── 6. No auto-cancel / order-mutation in warning path ─────────────────────────

def test_no_auto_cancel_in_stale_warning(html):
    """The stale warning block must not issue a cancel call automatically."""
    # The warning block (staleWarningHtml) must not call mt5CancelOrder
    # Find the stale warning HTML string in the source and confirm it contains no cancel call
    m = re.search(r"staleWarningHtml\s*=\s*'(.*?)'", html, re.DOTALL)
    if m:
        warning_html = m.group(1)
        assert "mt5CancelOrder" not in warning_html, \
            "staleWarningHtml must not auto-invoke mt5CancelOrder"


def test_no_fetch_in_stale_warning(html):
    """The stale warning rendering must not trigger any dvFetch / fetch call."""
    m = re.search(r"staleWarningHtml\s*=\s*'(.*?)'", html, re.DOTALL)
    if m:
        warning_html = m.group(1)
        assert "dvFetch" not in warning_html and "fetch(" not in warning_html, \
            "staleWarningHtml must not issue any network request"
