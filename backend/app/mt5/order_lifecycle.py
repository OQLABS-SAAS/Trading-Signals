"""MT5 order lifecycle helpers."""

from __future__ import annotations

from typing import Any


DEFAULT_USER_ID = "default"
TRAILING_ORDER_TYPE = "TRAILING"
PENDING_STATUS = "pending"
EXECUTING_STATUS = "executing"
FILLED_STATUS = "filled"
CANCELLED_STATUS = "cancelled"


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def user_ids_for_mt5_cancel(session_user_id: str) -> list[str]:
    return [str(session_user_id), DEFAULT_USER_ID]


def user_ids_for_pending_poll(ea_user_id: str | None) -> list[str] | None:
    if ea_user_id and ea_user_id != DEFAULT_USER_ID:
        return [str(ea_user_id), DEFAULT_USER_ID]
    return None


def status_after_pending_poll(order_type: Any) -> str:
    return EXECUTING_STATUS


def dotverse_order_comment(order_id: Any) -> str:
    return f"DotVerse #{order_id}"


def project_pending_mt5_order(order: Any) -> dict[str, Any]:
    return {
        "id": _get(order, "id"),
        "account_id": _get(order, "account_id"),
        "symbol": _get(order, "symbol"),
        "order_type": _get(order, "order_type"),
        "volume": _get(order, "volume"),
        "price": _get(order, "price"),
        "sl": _get(order, "sl"),
        "tp": _get(order, "tp"),
        "tp2": _get(order, "tp2"),
        "tp3": _get(order, "tp3"),
        "action": _get(order, "action") or "open",
        "close_ticket": _get(order, "close_ticket"),
        "trailing": bool(_get(order, "trailing")),
        "be": bool(_get(order, "be")),
        "macro": bool(_get(order, "macro")),
        "inval": bool(_get(order, "inval")),
        "sent": bool(_get(order, "sent")),
        "tp1_alert": bool(_get(order, "tp1_alert")),
        "tp2_alert": bool(_get(order, "tp2_alert")),
        "weekend": bool(_get(order, "weekend")),
    }


def mt5_cancel_response() -> dict[str, str]:
    return {"status": CANCELLED_STATUS}
