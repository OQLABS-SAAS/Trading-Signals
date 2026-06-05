"""Notification request and response contracts."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any


class NotificationValidationError(ValueError):
    """Raised when a notification request is invalid."""


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _parse_data(raw_data: Any) -> Any:
    if not raw_data:
        return None
    if isinstance(raw_data, (dict, list)):
        return raw_data
    try:
        return json.loads(str(raw_data))
    except Exception:
        return None


def _format_created_at(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M UTC")
    return None


def serialize_notification(notification: Any) -> dict[str, Any]:
    return {
        "id": _get(notification, "id"),
        "type": _get(notification, "ntype"),
        "title": _get(notification, "title"),
        "body": _get(notification, "body"),
        "data": _parse_data(_get(notification, "data")),
        "read": _get(notification, "read"),
        "created_at": _format_created_at(_get(notification, "created_at")),
    }


def serialize_notifications_response(notifications: list[Any]) -> dict[str, Any]:
    rows = [serialize_notification(notification) for notification in notifications]
    return {
        "notifications": rows,
        "unread": sum(1 for row in rows if not row["read"]),
    }


def normalize_mark_notifications_read_payload(payload: dict[str, Any] | None) -> int | None:
    body = payload if isinstance(payload, dict) else {}
    raw_id = body.get("id")
    if raw_id in (None, ""):
        return None
    try:
        return int(raw_id)
    except (TypeError, ValueError) as exc:
        raise NotificationValidationError("id must be an integer") from exc
