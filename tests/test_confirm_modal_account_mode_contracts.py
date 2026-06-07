"""Contract tests: _todayConfirmAndPlace modal must display account mode and identifier.

These tests assert the structural contracts of the pre-trade confirmation surface
introduced to prevent beginners from placing real-money orders while on demo.
"""
from pathlib import Path


HTML = Path("static/index-v2-prototype.html").read_text()


def test_today_confirm_modal_reads_account_from_todayLastMt5State():
    """The modal must read account info from window._todayLastMt5State at confirm-time."""
    assert "window._todayLastMt5State&&window._todayLastMt5State.account" in HTML


def test_today_confirm_modal_uses_mt5_account_mode_helper():
    """The modal must call the shared _mt5AccountMode() helper (not inline its own logic)."""
    assert "_mt5AccountMode(_cfAcct)" in HTML


def test_today_confirm_modal_extracts_login_and_server():
    """The modal must extract login (account number) and server from account state."""
    assert "_cfAcct.login||_cfAcct.account_number" in HTML
    assert "_cfAcct.server" in HTML


def test_today_confirm_modal_shows_live_label_for_live_accounts():
    """LIVE accounts must show a prominent red-tinted label 'LIVE — real money will be used'."""
    assert "LIVE — real money will be used" in HTML


def test_today_confirm_modal_shows_demo_label_for_demo_accounts():
    """DEMO accounts must show a neutral label 'DEMO — practice account, no real money'."""
    assert "DEMO — practice account, no real money" in HTML


def test_today_confirm_modal_shows_unknown_label_when_mode_undetected():
    """When MT5 mode cannot be detected, the modal must surface a warning."""
    assert "MODE UNKNOWN — check MT5 connection" in HTML


def test_today_confirm_modal_account_banner_has_unique_id():
    """The account-mode banner div must have a stable id for tests and a11y."""
    assert 'id="todayCfAcctBanner"' in HTML


def test_today_confirm_modal_account_line_renders_login_and_server():
    """The account identifier line must include both the account number and server."""
    assert "'Account '+_cfLogin" in HTML
    assert "_cfServer" in HTML


def test_today_confirm_modal_live_uses_red_tint():
    """LIVE mode must use a red background tint and red border."""
    assert "rgba(232,112,110,.10)" in HTML
    assert "rgba(232,112,110,.40)" in HTML


def test_today_confirm_modal_demo_uses_green_tint():
    """DEMO mode must use a green (non-alarming) background tint."""
    assert "rgba(93,232,160,.07)" in HTML
    assert "rgba(93,232,160,.25)" in HTML


def test_today_confirm_modal_banner_appears_before_place_button():
    """Account banner must be injected into the HTML before the Place button."""
    banner_pos = HTML.find("_cfAccountBannerHtml")
    place_btn_pos = HTML.find("todayCfGo")
    assert banner_pos != -1, "_cfAccountBannerHtml not found"
    assert place_btn_pos != -1, "todayCfGo not found"
    assert banner_pos < place_btn_pos, (
        "Account mode banner must appear before Place button in modal markup"
    )


# ─────────────────────────────────────────────────────────────────────────────
# EA-only sourcing: _todayConfirmAndPlace must never use _mt5Accounts
# ─────────────────────────────────────────────────────────────────────────────

def test_today_confirm_modal_ea_only_sourcing():
    """_todayConfirmAndPlace banner must derive mode exclusively from EA-reported state.

    The backend routes orders to the EA-connected account (_resolve_selected_mt5_account /
    _mt5_state_account_for_user). The _mt5Accounts list can contain accounts NOT selected
    by the backend. Showing a mode label from _mt5Accounts risks displaying DEMO while the
    order fires on LIVE. The _cfAcct variable must come from _todayLastMt5State.account only.
    """
    # The Today modal already uses EA-only sourcing; verify the pattern is present and
    # that no _mt5Accounts fallback was introduced to the _cfAcct resolution.
    assert "window._todayLastMt5State&&window._todayLastMt5State.account" in HTML
    # No _mt5Accounts-based fallback for _cfAcct should exist.
    assert "_cfAcct = window._mt5Accounts" not in HTML, (
        "_cfAcct must not be sourced from _mt5Accounts — EA-only sourcing required"
    )


def test_mt5Execute_dead_function_gone():
    """The dead mt5Execute() function must not exist anywhere in the file.

    This redundant function posted directly to /api/mt5/order with no confirmation guard
    and was never wired to any UI button (ACT uses actExecute). Confirmed unreferenced
    before removal via grep. Its absence prevents an accidental unguarded real-money path.
    """
    assert "async function mt5Execute()" not in HTML, (
        "mt5Execute() still present — dead unguarded order path must be removed"
    )
