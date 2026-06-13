"""Unit tests for A4 — EA self-diagnosis flags + trade_permission_issue.

Covers:
  - terminal_trade_allowed == 0  → names "Algo Trading" (first priority)
  - all flags 1                  → None (no issue)
  - flags absent (None)          → None (old EA / unknown, NOT treated as off)
  - priority order when multiple flags are 0 (terminal wins over mql, etc.)
  - each individual flag triggers its own message
  - helper is importable and lives in app module
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as dv


# ── helper shortcut ──────────────────────────────────────────────────────────

def _issue(terminal=None, mql=None, account=None, expert=None):
    """Build a minimal state dict and call the helper."""
    state = {
        "terminal_trade_allowed": terminal,
        "mql_trade_allowed":      mql,
        "account_trade_allowed":  account,
        "account_trade_expert":   expert,
    }
    return dv._mt5_trade_permission_issue(state)


# ── 1. Each flag individually triggers the right message ────────────────────

def test_terminal_off_names_algo_trading():
    issue = _issue(terminal=0, mql=1, account=1, expert=1)
    assert issue is not None
    assert "Algo Trading is OFF" in issue


def test_mql_off_names_ea_permission():
    issue = _issue(terminal=1, mql=0, account=1, expert=1)
    assert issue is not None
    assert "algo-trading permission" in issue


def test_account_trade_off_names_investor_password():
    issue = _issue(terminal=1, mql=1, account=0, expert=1)
    assert issue is not None
    assert "trading disabled" in issue


def test_account_expert_off_names_broker():
    issue = _issue(terminal=1, mql=1, account=1, expert=0)
    assert issue is not None
    assert "Expert Advisor trading" in issue


# ── 2. All flags on → no issue ───────────────────────────────────────────────

def test_all_flags_on_returns_none():
    assert _issue(terminal=1, mql=1, account=1, expert=1) is None


# ── 3. Absent flags (None) → unknown, NOT treated as off ────────────────────

def test_all_flags_absent_returns_none():
    assert _issue() is None


def test_one_flag_absent_rest_on_returns_none():
    # None = old EA didn't send this field; must not fire a false alarm
    assert _issue(terminal=None, mql=1, account=1, expert=1) is None
    assert _issue(terminal=1, mql=None, account=1, expert=1) is None
    assert _issue(terminal=1, mql=1, account=None, expert=1) is None
    assert _issue(terminal=1, mql=1, account=1, expert=None) is None


# ── 4. Priority order when multiple flags are 0 ─────────────────────────────

def test_terminal_wins_over_mql():
    issue = _issue(terminal=0, mql=0, account=1, expert=1)
    assert "Algo Trading is OFF" in issue


def test_terminal_wins_over_account():
    issue = _issue(terminal=0, mql=1, account=0, expert=1)
    assert "Algo Trading is OFF" in issue


def test_terminal_wins_over_expert():
    issue = _issue(terminal=0, mql=1, account=1, expert=0)
    assert "Algo Trading is OFF" in issue


def test_mql_wins_over_account():
    issue = _issue(terminal=1, mql=0, account=0, expert=1)
    assert "algo-trading permission" in issue


def test_mql_wins_over_expert():
    issue = _issue(terminal=1, mql=0, account=1, expert=0)
    assert "algo-trading permission" in issue


def test_account_wins_over_expert():
    issue = _issue(terminal=1, mql=1, account=0, expert=0)
    assert "trading disabled" in issue


def test_all_off_returns_terminal_message():
    issue = _issue(terminal=0, mql=0, account=0, expert=0)
    assert "Algo Trading is OFF" in issue


# ── 5. Edge cases ────────────────────────────────────────────────────────────

def test_non_dict_state_returns_none():
    assert dv._mt5_trade_permission_issue(None) is None
    assert dv._mt5_trade_permission_issue([]) is None
    assert dv._mt5_trade_permission_issue("bad") is None


def test_empty_dict_returns_none():
    # Empty dict → all fields absent → unknown, not off
    assert dv._mt5_trade_permission_issue({}) is None


def test_helper_exists_in_module():
    assert hasattr(dv, "_mt5_trade_permission_issue")
    assert callable(dv._mt5_trade_permission_issue)


def test_permission_messages_table_has_four_entries():
    assert len(dv._TRADE_PERMISSION_MESSAGES) == 4
