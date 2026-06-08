"""Contract tests: real-money risk warning on LIVE trade confirmation surfaces.

Two confirmation modals gate MT5 order placement:
  _todayConfirmAndPlace  — Today tab multi-trade confirm (id=todayCfAcctBanner)
  _szConfirmTrade        — Size/Act tab single-trade confirm (id=szCfAcctBanner)

When the account mode is LIVE, each modal must render a short plain-language risk
warning INSIDE the existing account banner, BEFORE the place/confirm button.

DEMO and UNKNOWN must NOT render the warning:
  - DEMO is practice money — no real risk, no extra alarm needed.
  - UNKNOWN already shows its own amber banner; a second warning would be misleading
    noise (we do not know whether real money is at risk).

Warning text (exact):
  "Real money is at risk. Trading can lose money, and DotVerse signals are not financial advice."
"""
from pathlib import Path
import re

HTML = Path("static/index-v2-prototype.html").read_text()

RISK_WARNING_TEXT = (
    "Real money is at risk. Trading can lose money, "
    "and DotVerse signals are not financial advice."
)

# ── narrow scopes so Today-tab and sz-tab tests are independent ─────────────

_TODAY_FUNC_START = "_cfAccountBannerHtml="
_TODAY_FUNC_END   = "var ov=document.createElement('div'); ov.id='todayConfirmOverlay';"
_today_s = HTML.index(_TODAY_FUNC_START)
_today_e = HTML.index(_TODAY_FUNC_END, _today_s)
TODAY_BANNER_BLOCK = HTML[_today_s:_today_e]

_SZ_FUNC_START = "_szCfAccountBannerHtml ="
_SZ_FUNC_END   = "var ov=document.createElement('div'); ov.id='szConfirmOverlay';"
_sz_s = HTML.index(_SZ_FUNC_START)
_sz_e = HTML.index(_SZ_FUNC_END, _sz_s)
SZ_BANNER_BLOCK = HTML[_sz_s:_sz_e]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Warning text is present in the HTML (whole-file sanity checks)
# ─────────────────────────────────────────────────────────────────────────────

def test_risk_warning_text_present_in_html():
    """The exact warning string must exist at least twice (one per surface)."""
    count = HTML.count(RISK_WARNING_TEXT)
    assert count >= 2, (
        f"Expected warning text at least 2 times (Today + sz), found {count}. "
        f"Expected: {RISK_WARNING_TEXT!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Today confirm (_todayConfirmAndPlace) — LIVE gate
# ─────────────────────────────────────────────────────────────────────────────

def test_today_risk_warning_present_in_banner_block():
    """The risk warning text must appear inside the _cfAccountBannerHtml construction block."""
    assert RISK_WARNING_TEXT in TODAY_BANNER_BLOCK, (
        "Risk warning text not found in _cfAccountBannerHtml block"
    )


def test_today_risk_warning_gated_to_live_only():
    """The risk warning in _todayConfirmAndPlace must be gated by _cfIsLive."""
    assert "_cfIsLive?" in TODAY_BANNER_BLOCK or "_cfIsLive ?" in TODAY_BANNER_BLOCK, (
        "_cfIsLive ternary gate not found — warning may render for non-LIVE modes"
    )
    # Verify the pattern: (_cfIsLive?'<div...warning...</div>':'')
    assert re.search(r'_cfIsLive\s*\?.*' + re.escape(RISK_WARNING_TEXT), TODAY_BANNER_BLOCK), (
        "Risk warning must be inside _cfIsLive ternary in the Today banner block"
    )


def test_today_risk_warning_has_stable_dom_id():
    """The Today risk warning div must carry id='todayCfRiskWarning' for tests and a11y."""
    assert 'id="todayCfRiskWarning"' in TODAY_BANNER_BLOCK


def test_today_risk_warning_uses_red_tint():
    """Today risk warning must use the canonical red colour to match the LIVE banner."""
    # Check any red colour is used — canonical is rgba(232,112,110,...)
    assert "rgba(232,112,110" in TODAY_BANNER_BLOCK


def test_today_risk_warning_not_shown_for_demo():
    """DEMO accounts must NOT trigger the risk warning in _todayConfirmAndPlace.

    The warning lives inside a (_cfIsLive?'<div…warning…>':'') ternary.  The only
    place the warning text appears in the banner block is after '_cfIsLive?', which
    evaluates to false for DEMO.  We verify there is no occurrence of the warning
    text that is NOT immediately preceded by the live gate.
    """
    # Every occurrence of the warning text must be preceded by the _cfIsLive ternary.
    for m in re.finditer(re.escape(RISK_WARNING_TEXT), TODAY_BANNER_BLOCK):
        context = TODAY_BANNER_BLOCK[max(0, m.start() - 200):m.start()]
        assert re.search(r'_cfIsLive\s*\?', context), (
            "Risk warning text found without a preceding _cfIsLive gate — "
            "would render for non-LIVE (DEMO) accounts"
        )


def test_today_risk_warning_not_shown_for_unknown():
    """UNKNOWN accounts must NOT trigger the risk warning in _todayConfirmAndPlace."""
    # Identical gate logic: every occurrence must be preceded by _cfIsLive.
    for m in re.finditer(re.escape(RISK_WARNING_TEXT), TODAY_BANNER_BLOCK):
        context = TODAY_BANNER_BLOCK[max(0, m.start() - 200):m.start()]
        assert re.search(r'_cfIsLive\s*\?', context), (
            "Risk warning text found without a preceding _cfIsLive gate — "
            "would render for UNKNOWN accounts"
        )


def test_today_risk_warning_appears_before_place_button():
    """Risk warning must appear in the HTML before the todayCfGo Place button."""
    warning_pos  = HTML.find('id="todayCfRiskWarning"')
    place_btn_pos = HTML.find('id="todayCfGo"')
    assert warning_pos != -1, "todayCfRiskWarning element not found in HTML"
    assert place_btn_pos != -1, "todayCfGo button not found in HTML"
    assert warning_pos < place_btn_pos, (
        "Risk warning must appear before the Place button in Today confirm modal markup"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Size/Act confirm (_szConfirmTrade) — LIVE gate
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_risk_warning_present_in_banner_block():
    """The risk warning text must appear inside the _szCfAccountBannerHtml construction block."""
    assert RISK_WARNING_TEXT in SZ_BANNER_BLOCK, (
        "Risk warning text not found in _szCfAccountBannerHtml block"
    )


def test_sz_risk_warning_gated_to_live_only():
    """The risk warning in _szConfirmTrade must be gated by _szCfIsLive."""
    assert "_szCfIsLive?" in SZ_BANNER_BLOCK or "_szCfIsLive ?" in SZ_BANNER_BLOCK, (
        "_szCfIsLive ternary gate not found — warning may render for non-LIVE modes"
    )
    assert re.search(r'_szCfIsLive\s*\?.*' + re.escape(RISK_WARNING_TEXT), SZ_BANNER_BLOCK), (
        "Risk warning must be inside _szCfIsLive ternary in the sz banner block"
    )


def test_sz_risk_warning_has_stable_dom_id():
    """The sz risk warning div must carry id='szCfRiskWarning' for tests and a11y."""
    assert 'id="szCfRiskWarning"' in SZ_BANNER_BLOCK


def test_sz_risk_warning_uses_red_tint():
    """sz risk warning must use the canonical red colour to match the LIVE banner."""
    assert "rgba(232,112,110" in SZ_BANNER_BLOCK


def test_sz_risk_warning_not_shown_for_demo():
    """DEMO accounts must NOT trigger the risk warning in _szConfirmTrade."""
    # Every occurrence of the warning text must be preceded by the _szCfIsLive ternary gate.
    for m in re.finditer(re.escape(RISK_WARNING_TEXT), SZ_BANNER_BLOCK):
        context = SZ_BANNER_BLOCK[max(0, m.start() - 200):m.start()]
        assert re.search(r'_szCfIsLive\s*\?', context), (
            "Risk warning text found without a preceding _szCfIsLive gate — "
            "would render for DEMO accounts"
        )


def test_sz_risk_warning_not_shown_for_unknown():
    """UNKNOWN accounts must NOT trigger the risk warning in _szConfirmTrade."""
    for m in re.finditer(re.escape(RISK_WARNING_TEXT), SZ_BANNER_BLOCK):
        context = SZ_BANNER_BLOCK[max(0, m.start() - 200):m.start()]
        assert re.search(r'_szCfIsLive\s*\?', context), (
            "Risk warning text found without a preceding _szCfIsLive gate — "
            "would render for UNKNOWN accounts"
        )


def test_sz_risk_warning_appears_before_place_button():
    """Risk warning must appear in the HTML before the szConfirmGo Place button."""
    warning_pos   = HTML.find('id="szCfRiskWarning"')
    place_btn_pos = HTML.find('id="szConfirmGo"')
    assert warning_pos != -1, "szCfRiskWarning element not found in HTML"
    assert place_btn_pos != -1, "szConfirmGo button not found in HTML"
    assert warning_pos < place_btn_pos, (
        "Risk warning must appear before the Place button in sz confirm modal markup"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. Cross-surface consistency
# ─────────────────────────────────────────────────────────────────────────────

def test_risk_warning_text_identical_on_both_surfaces():
    """Both surfaces must use the exact same warning text for consistency."""
    today_has = RISK_WARNING_TEXT in TODAY_BANNER_BLOCK
    sz_has    = RISK_WARNING_TEXT in SZ_BANNER_BLOCK
    assert today_has and sz_has, (
        f"Warning text mismatch between surfaces — "
        f"Today: {today_has}, sz: {sz_has}. "
        f"Text: {RISK_WARNING_TEXT!r}"
    )


def test_risk_warning_uses_mono_font():
    """Both surfaces must use var(--mono) for the risk warning font."""
    assert "font-family:var(--mono)" in TODAY_BANNER_BLOCK
    assert "font-family:var(--mono)" in SZ_BANNER_BLOCK
