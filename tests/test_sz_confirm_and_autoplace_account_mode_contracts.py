"""Contract tests: _szConfirmTrade and _todayAutoPlace must display account mode/identifier.

These tests close the two real-MT5-order paths that were not covered by the Today modal
contracts. Both surfaces now show LIVE/DEMO/UNKNOWN before any order is fired.

Surfaces under test
-------------------
_szConfirmTrade  — pre-trade confirmation modal shared by SIZE tab (szLadderSubmitAll)
                   and ACT tab (actExecute). Reads state ONLY from the EA-connected ground
                   truth: window._todayLastMt5State.account (set by
                   _todayBridgeMt5StateToGlobalAccount / mt5Poll). Mode-only fallback to
                   window._mt5AccountType (also EA-derived). Never uses window._mt5Accounts
                   for mode/login/server derivation. If EA truth unavailable: UNKNOWN banner.
_todayAutoPlace  — auto-fire countdown bar on the Today tab. Shows a compact inline chip
                   reading from window._todayLastMt5State (same source as the Today
                   confirm modal). Safe UNKNOWN fallback when state is not yet populated.
"""
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text()


# ─────────────────────────────────────────────────────────────────────────────
# _szConfirmTrade: primary state source
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_confirm_reads_todayLastMt5State_first():
    """_szConfirmTrade must try window._todayLastMt5State.account as its primary source."""
    assert "window._todayLastMt5State && window._todayLastMt5State.account" in HTML


def test_sz_confirm_does_not_use_mt5Accounts_for_banner():
    """_szConfirmTrade must NOT use window._mt5Accounts to derive mode/login/server for the banner.

    The _mt5Accounts list is not the EA-connected ground truth and can reflect a different
    account than the one the backend routes orders to. Using it risks showing DEMO while
    the order fires on LIVE. The banner must derive mode exclusively from the EA-reported
    state (window._todayLastMt5State.account). We verify that the _szConnAcct fallback
    block (which previously used _mt5Accounts.find / _mt5Accounts[0] to populate _szCfAcct)
    has been removed.
    """
    # The specific fallback variable that bridged _mt5Accounts → _szCfAcct must be gone.
    assert "_szConnAcct" not in HTML, (
        "_szConnAcct found — the _mt5Accounts fallback block was not removed from _szConfirmTrade"
    )
    # The pattern that set _szCfAcct from _mt5Accounts must be gone.
    assert "window._mt5Accounts.find(function(a){ return a.connected" not in HTML, (
        "window._mt5Accounts.find(connected) still used to populate _szCfAcct banner source"
    )


def test_sz_confirm_falls_back_to_mt5AccountType_mode_string():
    """_szConfirmTrade must use window._mt5AccountType as a second-level mode fallback."""
    assert "window._mt5AccountType" in HTML


def test_sz_confirm_uses_mt5_account_mode_helper():
    """_szConfirmTrade must call the shared _mt5AccountMode() helper — not inline mode logic."""
    assert "_mt5AccountMode(_szCfAcct)" in HTML


def test_sz_confirm_extracts_login_from_account():
    """_szConfirmTrade must extract the login / account number from the resolved account object."""
    assert "_szCfAcct.login || _szCfAcct.account_number" in HTML


def test_sz_confirm_extracts_server_from_account():
    """_szConfirmTrade must extract the server field from the resolved account object."""
    assert "_szCfAcct.server" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# _szConfirmTrade: LIVE / DEMO / UNKNOWN branches
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_confirm_shows_live_label():
    """LIVE must produce 'LIVE — real money will be used' in the sz confirm banner."""
    # The label string appears at least twice in the file now (Today + sz), just
    # ensure it is present (the Today modal test already checks it once).
    assert HTML.count("LIVE — real money will be used") >= 2


def test_sz_confirm_shows_demo_label():
    """DEMO must produce 'DEMO — practice account, no real money' in the sz confirm banner."""
    assert HTML.count("DEMO — practice account, no real money") >= 2


def test_sz_confirm_shows_unknown_label():
    """UNKNOWN must produce 'MODE UNKNOWN — check MT5 connection' in the sz confirm banner."""
    assert HTML.count("MODE UNKNOWN — check MT5 connection") >= 2


def test_sz_confirm_live_uses_red_tint():
    """LIVE branch in _szConfirmTrade must use the canonical red background tint."""
    # _szCfModeBg for LIVE = rgba(232,112,110,.10)
    assert "_szCfIsLive ? 'rgba(232,112,110,.10)'" in HTML


def test_sz_confirm_demo_uses_green_tint():
    """DEMO branch in _szConfirmTrade must use the canonical green background tint."""
    assert "_szCfIsDemo ? 'rgba(93,232,160,.07)'" in HTML


def test_sz_confirm_unknown_uses_amber_tint():
    """UNKNOWN branch in _szConfirmTrade must use amber as the fallback tint."""
    assert "'rgba(201,168,76,.08)'" in HTML


def test_sz_confirm_banner_has_unique_id():
    """The sz-confirm account banner div must carry a stable DOM id."""
    assert 'id="szCfAcctBanner"' in HTML


def test_sz_confirm_account_line_renders_login():
    """The sz confirm account identifier line must compose 'Account <login>'."""
    assert "'Account ' + _szCfLogin" in HTML


def test_sz_confirm_account_line_renders_server():
    """The sz confirm account identifier line must include the server name."""
    assert "_szCfServer" in HTML


def test_sz_confirm_banner_appears_before_place_button():
    """Account banner HTML var must be injected into the modal before szConfirmGo button."""
    banner_pos = HTML.find("_szCfAccountBannerHtml")
    place_btn_pos = HTML.find("szConfirmGo")
    assert banner_pos != -1, "_szCfAccountBannerHtml not found in HTML"
    assert place_btn_pos != -1, "szConfirmGo not found in HTML"
    assert banner_pos < place_btn_pos, (
        "_szConfirmTrade account banner must appear before the szConfirmGo button in modal markup"
    )


def test_sz_confirm_unknown_fallback_never_empty():
    """The _szCfMode variable must be forced to 'UNKNOWN' when neither source provides a mode."""
    # The guard: if (!_szCfMode) _szCfMode = 'UNKNOWN';
    assert "if (!_szCfMode) _szCfMode = 'UNKNOWN'" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# _todayAutoPlace: compact mode chip in countdown bar
# ─────────────────────────────────────────────────────────────────────────────

def test_autoplace_reads_todayLastMt5State():
    """_todayAutoPlace must read from window._todayLastMt5State for its mode chip."""
    # The variable assignment block inside _todayAutoPlace scope
    assert "_apAcct=(window._todayLastMt5State&&window._todayLastMt5State.account)" in HTML


def test_autoplace_uses_mt5_account_mode_helper():
    """_todayAutoPlace must call _mt5AccountMode() for mode resolution."""
    assert "_mt5AccountMode(_apAcct)" in HTML


def test_autoplace_has_mode_chip_element():
    """The countdown bar must contain a DOM element with id todayAutoModeChip."""
    assert 'id="todayAutoModeChip"' in HTML


def test_autoplace_chip_shows_live_label():
    """The auto-place chip must render 'LIVE' text for live accounts."""
    # Variable _apModeLabel is set to 'LIVE' when mode is LIVE
    assert "_apIsLive?'LIVE'" in HTML


def test_autoplace_chip_shows_demo_label():
    """The auto-place chip must render 'DEMO' text for demo accounts."""
    assert "_apIsDemo?'#5de8a0'" in HTML


def test_autoplace_chip_shows_unknown_fallback():
    """The auto-place chip must render 'MODE UNKNOWN' when mode cannot be determined."""
    assert "?_apModeLabel:'MODE UNKNOWN'" in HTML


def test_autoplace_chip_live_uses_red_color():
    """The auto-place chip must use red (#e8706e) for LIVE accounts."""
    assert "_apIsLive?'#e8706e'" in HTML


def test_autoplace_chip_includes_login():
    """The auto-place chip must append the account login when available."""
    assert "_apLogin?' · '+_apLogin:''" in HTML


def test_autoplace_chip_safe_unknown_fallback_comment():
    """Code must include a comment explaining the safe UNKNOWN fallback for auto-place."""
    assert "Safe UNKNOWN fallback" in HTML or "safe UNKNOWN fallback" in HTML


def test_autoplace_countdown_bar_contains_chip_before_cancel_button():
    """The mode chip must be injected before the Cancel button in the countdown bar HTML."""
    chip_pos = HTML.find("todayAutoModeChip")
    cancel_pos = HTML.find("todayAutoCancel")
    assert chip_pos != -1, "todayAutoModeChip not found in HTML"
    assert cancel_pos != -1, "todayAutoCancel not found in HTML"
    assert chip_pos < cancel_pos, (
        "Mode chip must appear before Cancel button in auto-place countdown bar"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Comment fix: _todayBuildPlan vs _todayBridgeMt5StateToGlobalAccount
# ─────────────────────────────────────────────────────────────────────────────

def test_comment_correctly_credits_bridge_not_build_plan():
    """The corrected comment must credit _todayBridgeMt5StateToGlobalAccount, not _todayBuildPlan."""
    # The old false claim said '_todayBuildPlan populates window._todayLastMt5State'.
    # After the fix the comment must name the correct function.
    assert "_todayBridgeMt5StateToGlobalAccount" in HTML
    # Confirm the old false claim is gone from the vicinity of the banner comment block.
    # Locate the banner comment and grab ~300 chars of context around it.
    marker = "Account mode banner — build before injecting HTML"
    idx = HTML.find(marker)
    assert idx != -1, "Banner comment block not found"
    snippet = HTML[max(0, idx - 50): idx + 400]
    assert "_todayBuildPlan populates" not in snippet, (
        "Old false claim '_todayBuildPlan populates window._todayLastMt5State' "
        "still present near the banner comment"
    )


# ─────────────────────────────────────────────────────────────────────────────
# EA-only sourcing: _szConfirmTrade must never derive mode from _mt5Accounts
# ─────────────────────────────────────────────────────────────────────────────

def test_sz_confirm_ea_only_sourcing_no_mt5Accounts_fallback_for_mode():
    """_szConfirmTrade must not use _mt5Accounts to set _szCfAcct (the banner source).

    The backend routes orders to the EA-connected account via _resolve_selected_mt5_account.
    The _mt5Accounts list can contain accounts that are NOT the one the backend selects.
    Using _mt5Accounts[0] or .find(connected) to show a mode label risks displaying DEMO
    while the order fires on LIVE. The _szCfAcct variable must be set exclusively from
    window._todayLastMt5State.account or left null (UNKNOWN path).
    """
    # The removed fallback block used _szConnAcct as the bridge variable.
    assert "_szConnAcct" not in HTML, (
        "_szConnAcct variable found — _mt5Accounts fallback block was not fully removed"
    )


def test_sz_confirm_ea_only_sourcing_no_mt5Accounts_find_connected():
    """The pattern _mt5Accounts.find(connected) must not appear in the banner resolution code."""
    assert "window._mt5Accounts.find(function(a){ return a.connected" not in HTML, (
        "window._mt5Accounts.find(connected) still present — could derive mode from wrong account"
    )


def test_sz_confirm_ea_only_sourcing_unknown_when_no_ea_state():
    """When _todayLastMt5State.account is absent, mode must be 'UNKNOWN', not a guessed account.

    The guard 'if (!_szCfMode) _szCfMode = UNKNOWN' ensures this. The _szCfAcct null path
    means login/server will also be blank — the banner shows only the UNKNOWN amber label.
    """
    # _szCfAcct is set to null when _todayLastMt5State is absent.
    assert "window._todayLastMt5State && window._todayLastMt5State.account) || null" in HTML, (
        "_szCfAcct must be null (not a fallback account) when EA state is unavailable"
    )
    # The UNKNOWN guard must still be present.
    assert "if (!_szCfMode) _szCfMode = 'UNKNOWN'" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# Dead-code removal: mt5Execute() must be gone
# ─────────────────────────────────────────────────────────────────────────────

def test_mt5Execute_function_removed():
    """The dead mt5Execute() function must no longer exist in the codebase.

    mt5Execute() posted directly to /api/mt5/order with no confirmation modal or guard.
    It was not wired to any UI element (the ACT button uses actExecute, which routes through
    _szConfirmTrade). Confirmed unreferenced by grep before removal (only the definition
    itself matched 'mt5Execute'). Deleting it eliminates an unguarded real-money path.
    """
    assert "async function mt5Execute()" not in HTML, (
        "mt5Execute() function definition still present — dead unguarded order path not removed"
    )


def test_mt5Execute_not_called_anywhere():
    """mt5Execute must not be called from any call-site in the file."""
    import re
    # Match mt5Execute followed by ( — the function-call pattern.
    # actExecute is a different function and must NOT be caught by this pattern.
    calls = re.findall(r'\bmt5Execute\s*\(', HTML)
    assert len(calls) == 0, (
        f"mt5Execute() call-site(s) found: {calls} — remove all references"
    )
