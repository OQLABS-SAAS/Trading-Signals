"""Trading account request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


class AccountValidationError(ValueError):
    """Raised when a trading account request is invalid."""


@dataclass(frozen=True)
class TradingAccountCreateRequest:
    name: str
    broker: str
    server: str
    account_number: str
    account_type: str
    currency: str
    color: Any = None
    sort_order: Any = 0


@dataclass(frozen=True)
class TradingAccountUpdateRequest:
    updates: dict[str, Any]
    regenerate_secret: bool = False


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _format_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M UTC")
    return None


def normalize_account_create_payload(
    payload: dict[str, Any] | None,
    *,
    allow_login_alias: bool = False,
) -> TradingAccountCreateRequest:
    body = payload if isinstance(payload, dict) else {}
    name = str(body.get("name") or "").strip()
    if not name:
        raise AccountValidationError("name is required")

    account_number_raw = body.get("account_number")
    if allow_login_alias and account_number_raw in (None, ""):
        account_number_raw = body.get("login")

    account_type = str(body.get("account_type") or "DEMO").upper()
    if account_type not in ("LIVE", "DEMO"):
        raise AccountValidationError("account_type must be LIVE or DEMO")

    return TradingAccountCreateRequest(
        name=name,
        broker=str(body.get("broker") or "").strip(),
        server=str(body.get("server") or "").strip(),
        account_number=str(account_number_raw or "").strip(),
        account_type=account_type,
        currency=str(body.get("currency") or "USD").upper(),
        color=body.get("color"),
        sort_order=body.get("sort_order", 0),
    )


def normalize_account_update_payload(payload: dict[str, Any] | None) -> TradingAccountUpdateRequest:
    body = payload if isinstance(payload, dict) else {}
    updates: dict[str, Any] = {}

    if "name" in body and body["name"]:
        updates["name"] = str(body["name"]).strip()
    if "broker" in body:
        updates["broker"] = str(body.get("broker") or "").strip()
    if "server" in body:
        updates["server"] = str(body.get("server") or "").strip()
    if "account_number" in body:
        updates["account_number"] = str(body.get("account_number") or "").strip()
    if "account_type" in body:
        account_type = str(body.get("account_type") or "").upper()
        if account_type not in ("LIVE", "DEMO"):
            raise AccountValidationError("account_type must be LIVE or DEMO")
        updates["account_type"] = account_type
    if "currency" in body:
        updates["currency"] = str(body.get("currency") or "").upper()[:8]
    if "color" in body:
        updates["color"] = str(body["color"])[:16] if body["color"] else None
    if "sort_order" in body:
        try:
            updates["sort_order"] = int(body["sort_order"])
        except (TypeError, ValueError) as exc:
            raise AccountValidationError("sort_order must be an integer") from exc

    return TradingAccountUpdateRequest(
        updates=updates,
        regenerate_secret=bool(body.get("regenerate_secret")),
    )


def serialize_trading_account(
    account: Any,
    live_state: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    state = live_state if isinstance(live_state, dict) else {}
    acct_info = state.get("account", {}) if isinstance(state.get("account", {}), dict) else {}
    last_seen_str = None
    connected = False
    if state.get("last_seen"):
        try:
            last_seen = datetime.fromisoformat(str(state["last_seen"]))
            connected = ((now or datetime.utcnow()) - last_seen).total_seconds() < 45
            last_seen_str = last_seen.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass

    return {
        "id": _get(account, "id"),
        "name": _get(account, "name"),
        "broker": _get(account, "broker") or "",
        "server": _get(account, "server") or "",
        "account_number": _get(account, "account_number") or "",
        "account_type": _get(account, "account_type"),
        "currency": _get(account, "currency"),
        "platform": _get(account, "platform"),
        "status": _get(account, "status"),
        "connected": connected,
        "last_seen": last_seen_str,
        "error_message": _get(account, "error_message"),
        "color": _get(account, "color"),
        "sort_order": _get(account, "sort_order"),
        "is_active": _get(account, "is_active"),
        "balance": acct_info.get("balance"),
        "equity": acct_info.get("equity"),
        "margin": acct_info.get("margin"),
        "margin_free": acct_info.get("margin_free"),
        "margin_level": acct_info.get("margin_level"),
        "created_at": _format_datetime(_get(account, "created_at")),
        "updated_at": _format_datetime(_get(account, "updated_at")),
    }


def build_account_create_response(account: Any, ea_secret: str | None = None) -> dict[str, Any]:
    result = serialize_trading_account(account)
    if ea_secret is not None:
        result["ea_secret"] = ea_secret
    return result


def build_agent_account_create_response(account: Any, ea_secret: str | None = None) -> dict[str, Any]:
    result = serialize_trading_account(account)
    result["ea_secret"] = ea_secret
    result["success"] = True
    return result


def account_added_audit_description(account_name: str) -> str:
    return f"New account '{account_name}' added via Agent tab"


def account_archived_response(account_name: str) -> dict[str, Any]:
    return {"success": True, "message": f"Account '{account_name}' archived"}


def account_archived_audit_description(account_name: str) -> str:
    return f"Account '{account_name}' archived by user"


def account_sync_response(account_name: str) -> dict[str, Any]:
    return {"success": True, "message": f"Sync triggered for '{account_name}'. Data will refresh shortly."}


def account_sync_audit_description(account_name: str) -> str:
    return f"Manual sync triggered for account '{account_name}'"
