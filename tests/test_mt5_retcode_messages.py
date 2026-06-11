"""Unit tests for _mt5_retcode_message (A1 — broker-error translator).

Covers:
  - Known retcode 10017 extracted from a comment → returns actionable message
  - Unknown retcode → returns None
  - Comment with no retcode at all → returns None
  - Non-failed status → returns None regardless of comment
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as dv


def test_10017_returns_actionable_message():
    msg = dv._mt5_retcode_message("retcode=10017", "failed")
    assert msg is not None
    assert "Algo Trading is OFF" in msg
    assert "10017" in msg


def test_10017_colon_separator():
    msg = dv._mt5_retcode_message("retcode:10017", "failed")
    assert msg is not None
    assert "Algo Trading is OFF" in msg


def test_10017_bare_number_in_comment():
    msg = dv._mt5_retcode_message("EA error 10017 see MT5", "failed")
    assert msg is not None
    assert "Algo Trading is OFF" in msg


def test_unknown_retcode_returns_none():
    msg = dv._mt5_retcode_message("retcode=99999", "failed")
    assert msg is None


def test_comment_without_code_returns_none():
    msg = dv._mt5_retcode_message("DotVerse EURUSD BUY 1.08250", "failed")
    assert msg is None


def test_non_failed_status_returns_none():
    # Even if the comment has a valid retcode, non-failure statuses should not get a message
    assert dv._mt5_retcode_message("retcode=10017", "filled") is None
    assert dv._mt5_retcode_message("retcode=10017", "pending") is None
    assert dv._mt5_retcode_message("retcode=10017", "cancelled") is None
    assert dv._mt5_retcode_message("retcode=10017", "executing") is None


def test_rejected_status_returns_message():
    msg = dv._mt5_retcode_message("retcode=10019", "rejected")
    assert msg is not None
    assert "margin" in msg.lower()


def test_none_comment_returns_none():
    assert dv._mt5_retcode_message(None, "failed") is None


def test_empty_comment_returns_none():
    assert dv._mt5_retcode_message("", "failed") is None


def test_all_mapped_codes_have_messages():
    """Verify every code in the dict produces a non-None result."""
    for code in dv._MT5_RETCODE_MESSAGES:
        msg = dv._mt5_retcode_message("retcode={}".format(code), "failed")
        assert msg is not None, "code {} unexpectedly returned None".format(code)
        assert str(code) in msg
