import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.notifications.notification_contracts import (  # noqa: E402
    NotificationValidationError,
    normalize_mark_notifications_read_payload,
    serialize_notification,
    serialize_notifications_response,
)


def test_serialize_notification_parses_data_and_formats_timestamp():
    notification = SimpleNamespace(
        id=3,
        ntype="market",
        title="Price alert",
        body="EURUSD moved",
        data='{"symbol": "EURUSD"}',
        read=False,
        created_at=datetime(2026, 6, 5, 12, 0, 0),
    )

    result = serialize_notification(notification)

    assert result == {
        "id": 3,
        "type": "market",
        "title": "Price alert",
        "body": "EURUSD moved",
        "data": {"symbol": "EURUSD"},
        "read": False,
        "created_at": "2026-06-05 12:00 UTC",
    }


def test_serialize_notifications_response_counts_unread_and_ignores_bad_json():
    rows = [
        SimpleNamespace(id=1, ntype="scan", title="A", body="B", data="{bad", read=False, created_at=None),
        SimpleNamespace(id=2, ntype="level", title="C", body="D", data=None, read=True, created_at=None),
    ]

    result = serialize_notifications_response(rows)

    assert result["unread"] == 1
    assert result["notifications"][0]["data"] is None


def test_normalize_mark_notifications_read_payload_accepts_one_or_all():
    assert normalize_mark_notifications_read_payload({}) is None
    assert normalize_mark_notifications_read_payload({"id": ""}) is None
    assert normalize_mark_notifications_read_payload({"id": "7"}) == 7


def test_normalize_mark_notifications_read_payload_rejects_bad_id():
    try:
        normalize_mark_notifications_read_payload({"id": "latest"})
    except NotificationValidationError as exc:
        assert "id must be an integer" in str(exc)
    else:
        raise AssertionError("invalid notification id should fail")
