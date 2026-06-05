"""Agent trade request and response contracts."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import io
from typing import Any


class AgentTradeValidationError(ValueError):
    """Raised when an Agent trade request is invalid."""


@dataclass(frozen=True)
class AgentTradeCreateRequest:
    account_id: int
    signal_id: Any
    symbol: str
    side: str
    quantity: float
    entry_price: float
    stop_loss: float | None
    take_profit: float | None
    entry_time: datetime
    notes: Any


@dataclass(frozen=True)
class AgentTradeUpdateRequest:
    updates: dict[str, Any]


@dataclass(frozen=True)
class AgentTradeQueryParams:
    account_id: int | None
    symbol: str | None
    outcome: str | None
    search: str | None
    status: str | None
    date_from: datetime | None
    date_to: datetime | None
    limit: int
    offset: int


@dataclass(frozen=True)
class AgentPositionQueryParams:
    account_id: int | None


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _parse_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AgentTradeValidationError(f"{field_name} must be an integer") from exc


def _parse_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise AgentTradeValidationError(f"{field_name} must be a number") from exc


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_optional_float(value: Any, field_name: str) -> float | None:
    if value in (None, ""):
        return None
    return _parse_float(value, field_name)


def _parse_entry_time(value: Any, now: datetime | None) -> datetime:
    if not value:
        return now or datetime.utcnow()
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise AgentTradeValidationError("entry_time must be an ISO datetime") from exc


def _parse_optional_datetime(value: Any, field_name: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise AgentTradeValidationError(f"{field_name} must be an ISO datetime") from exc


def normalize_agent_trade_create_payload(
    payload: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> AgentTradeCreateRequest:
    body = payload if isinstance(payload, dict) else {}
    if not body.get("account_id"):
        raise AgentTradeValidationError("account_id is required")

    symbol = str(body.get("symbol") or "").upper().strip()
    if not symbol:
        raise AgentTradeValidationError("symbol is required")

    side = str(body.get("side") or "BUY").upper()
    if side not in ("BUY", "SELL"):
        raise AgentTradeValidationError("side must be BUY or SELL")

    return AgentTradeCreateRequest(
        account_id=_parse_int(body.get("account_id"), "account_id"),
        signal_id=body.get("signal_id"),
        symbol=symbol,
        side=side,
        quantity=_parse_float(body.get("quantity", 0.0), "quantity"),
        entry_price=_parse_float(body.get("entry_price", 0.0), "entry_price"),
        stop_loss=_parse_optional_float(body.get("stop_loss"), "stop_loss"),
        take_profit=_parse_optional_float(body.get("take_profit"), "take_profit"),
        entry_time=_parse_entry_time(body.get("entry_time"), now),
        notes=body.get("notes"),
    )


def normalize_agent_trade_update_payload(payload: dict[str, Any] | None) -> AgentTradeUpdateRequest:
    body = payload if isinstance(payload, dict) else {}
    updates: dict[str, Any] = {}

    if "exit_price" in body:
        updates["exit_price"] = _parse_optional_float(body.get("exit_price"), "exit_price")
    if "status" in body:
        status = str(body.get("status") or "").upper()
        if status not in ("OPEN", "CLOSED"):
            raise AgentTradeValidationError("status must be OPEN or CLOSED")
        updates["status"] = status
    if "outcome" in body:
        outcome = str(body.get("outcome") or "").upper()
        if outcome and outcome not in ("WIN", "LOSS", "BE"):
            raise AgentTradeValidationError("outcome must be WIN, LOSS, or BE")
        updates["outcome"] = outcome or None
    if "notes" in body:
        updates["notes"] = body.get("notes")
    if "stop_loss" in body:
        updates["stop_loss"] = _parse_optional_float(body.get("stop_loss"), "stop_loss")
    if "take_profit" in body:
        updates["take_profit"] = _parse_optional_float(body.get("take_profit"), "take_profit")

    return AgentTradeUpdateRequest(updates=updates)


def normalize_agent_trade_query_params(
    params: Any,
    *,
    default_status: str | None = "CLOSED",
) -> AgentTradeQueryParams:
    account_id_raw = params.get("account_id") if params else None
    status_raw = params.get("status", default_status) if params else default_status
    limit_raw = params.get("limit", 200) if params else 200
    offset_raw = params.get("offset", 0) if params else 0

    limit = _parse_int(limit_raw, "limit")
    offset = _parse_int(offset_raw, "offset")
    if limit < 1:
        raise AgentTradeValidationError("limit must be greater than 0")
    if offset < 0:
        raise AgentTradeValidationError("offset must be 0 or greater")

    return AgentTradeQueryParams(
        account_id=_parse_int(account_id_raw, "account_id") if account_id_raw else None,
        symbol=params.get("symbol") if params else None,
        outcome=str(params.get("outcome")).upper() if params and params.get("outcome") else None,
        search=params.get("search") if params else None,
        status=str(status_raw).upper() if status_raw else None,
        date_from=_parse_optional_datetime(params.get("date_from") if params else None, "date_from"),
        date_to=_parse_optional_datetime(params.get("date_to") if params else None, "date_to"),
        limit=limit,
        offset=offset,
    )


def normalize_agent_position_query_params(params: Any) -> AgentPositionQueryParams:
    account_id_raw = params.get("account_id") if params else None
    return AgentPositionQueryParams(
        account_id=_parse_int(account_id_raw, "account_id") if account_id_raw else None,
    )


def format_agent_position_duration(start: datetime | None, end: datetime | None) -> str:
    if not start or not end:
        return ""
    delta = end - start
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    if days > 0:
        return f"{days}d {hours}h"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def project_agent_position(
    trade: Any,
    account_name: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    result = serialize_agent_trade(trade)
    safe_account_name = account_name or "Unknown"
    entry_price = _get(trade, "entry_price")
    current_price = _get(trade, "current_price") or entry_price
    status = _get(trade, "status")
    end_time = (now or datetime.utcnow()) if status == "OPEN" else _get(trade, "exit_time")

    result["account_name"] = safe_account_name
    result["client_name"] = safe_account_name
    result["client_initials"] = "".join([word[0] for word in safe_account_name.split()]).upper()[:2]
    result["entry"] = entry_price
    result["current"] = current_price
    result["pnl"] = _get(trade, "realized_pnl") or _get(trade, "unrealized_pnl") or 0
    result["duration"] = format_agent_position_duration(_get(trade, "entry_time"), end_time)
    return result


def project_agent_trade_history_item(trade: Any, account_name: str) -> dict[str, Any]:
    result = serialize_agent_trade(trade)
    safe_account_name = account_name or "Unknown"
    date_src = _get(trade, "exit_time") or _get(trade, "entry_time")
    result["account_name"] = safe_account_name
    result["client_name"] = safe_account_name
    result["date"] = date_src.strftime("%Y-%m-%d %H:%M") if date_src else None
    return result


def project_agent_trade_detail(trade: Any, account_name: str) -> dict[str, Any]:
    result = serialize_agent_trade(trade)
    result["account_name"] = account_name or "Unknown"
    return result


AGENT_TRADE_EXPORT_HEADER = ["Date", "Account", "Symbol", "Side", "Entry", "Exit", "P&L", "R:R", "Outcome", "Status"]


def agent_trade_export_row(trade: Any, account_name: str) -> list[Any]:
    date_src = _get(trade, "exit_time") or _get(trade, "entry_time")
    rr_ratio = _get(trade, "rr_ratio")
    return [
        date_src.strftime("%Y-%m-%d %H:%M") if date_src else "",
        account_name or "",
        _get(trade, "symbol"),
        _get(trade, "side"),
        _get(trade, "entry_price"),
        _get(trade, "exit_price") or "",
        round(_to_float(_get(trade, "realized_pnl"), 0.0), 2),
        round(_to_float(rr_ratio), 2) if rr_ratio else "",
        _get(trade, "outcome") or "",
        _get(trade, "status"),
    ]


def build_agent_trade_export_csv(trades: list[Any], account_names_by_id: dict[Any, str]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(AGENT_TRADE_EXPORT_HEADER)
    for trade in trades:
        writer.writerow(agent_trade_export_row(trade, account_names_by_id.get(_get(trade, "account_id"), "")))
    csv_data = output.getvalue()
    output.close()
    return csv_data


def calculate_realized_pnl(
    *,
    side: Any,
    entry_price: Any,
    exit_price: Any,
    quantity: Any,
) -> float | None:
    if exit_price in (None, "") or entry_price in (None, "") or quantity in (None, ""):
        return None
    multiplier = 1 if str(side).upper() == "BUY" else -1
    return (_parse_float(exit_price, "exit_price") - _parse_float(entry_price, "entry_price")) * multiplier * _parse_float(quantity, "quantity")


def serialize_agent_trade(trade: Any) -> dict[str, Any]:
    entry_time = _get(trade, "entry_time")
    exit_time = _get(trade, "exit_time")
    created_at = _get(trade, "created_at")
    return {
        "id": _get(trade, "id"),
        "uuid": _get(trade, "uuid"),
        "account_id": _get(trade, "account_id"),
        "signal_id": _get(trade, "signal_id"),
        "symbol": _get(trade, "symbol"),
        "side": _get(trade, "side"),
        "quantity": _get(trade, "quantity"),
        "entry_price": _get(trade, "entry_price"),
        "exit_price": _get(trade, "exit_price"),
        "stop_loss": _get(trade, "stop_loss"),
        "take_profit": _get(trade, "take_profit"),
        "entry_time": entry_time.isoformat() if entry_time else None,
        "exit_time": exit_time.isoformat() if exit_time else None,
        "realized_pnl": _get(trade, "realized_pnl"),
        "unrealized_pnl": _get(trade, "unrealized_pnl"),
        "rr_ratio": _get(trade, "rr_ratio"),
        "status": _get(trade, "status"),
        "outcome": _get(trade, "outcome"),
        "notes": _get(trade, "notes"),
        "created_at": created_at.isoformat() if created_at else None,
    }
