from types import SimpleNamespace

from backend.app.mt5.order_lifecycle import (
    dotverse_order_comment,
    mt5_cancel_response,
    project_pending_mt5_order,
    status_after_pending_poll,
    user_ids_for_mt5_cancel,
    user_ids_for_pending_poll,
)


def test_user_ids_for_mt5_cancel_includes_session_user_and_default():
    assert user_ids_for_mt5_cancel("user-123") == ["user-123", "default"]


def test_user_ids_for_pending_poll_scopes_when_ea_identifies_user():
    assert user_ids_for_pending_poll("user-123") == ["user-123", "default"]
    assert user_ids_for_pending_poll("default") is None
    assert user_ids_for_pending_poll(None) is None


def test_status_after_pending_poll_marks_trailing_filled_and_others_executing():
    assert status_after_pending_poll("TRAILING") == "filled"
    assert status_after_pending_poll("trailing") == "filled"
    assert status_after_pending_poll("BUY") == "executing"
    assert status_after_pending_poll("SELL") == "executing"


def test_dotverse_order_comment_uses_mt5_order_id():
    assert dotverse_order_comment(42) == "DotVerse #42"


def test_project_pending_mt5_order_preserves_ea_contract_fields():
    order = SimpleNamespace(
        id=7,
        symbol="EURUSD",
        order_type="BUY",
        volume=0.01,
        price=1.1,
        sl=1.09,
        tp=1.11,
        tp2=1.12,
        tp3=1.13,
        action=None,
        close_ticket=None,
        trailing=True,
        be=False,
        macro=True,
        inval=False,
        sent=True,
        tp1_alert=False,
        tp2_alert=True,
        weekend=False,
    )

    assert project_pending_mt5_order(order) == {
        "id": 7,
        "symbol": "EURUSD",
        "order_type": "BUY",
        "volume": 0.01,
        "price": 1.1,
        "sl": 1.09,
        "tp": 1.11,
        "tp2": 1.12,
        "tp3": 1.13,
        "action": "open",
        "close_ticket": None,
        "trailing": True,
        "be": False,
        "macro": True,
        "inval": False,
        "sent": True,
        "tp1_alert": False,
        "tp2_alert": True,
        "weekend": False,
    }


def test_mt5_cancel_response_is_stable():
    assert mt5_cancel_response() == {"status": "cancelled"}
