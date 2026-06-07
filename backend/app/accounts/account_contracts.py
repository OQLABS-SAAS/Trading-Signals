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


def _normalize_account_mode_text(value: Any) -> str | None:
    raw = str(value or "").strip().upper()
    if not raw:
        return None
    if raw == "2":
        return "LIVE"
    if raw in {"0", "1"}:
        return "DEMO"
    if any(token in raw for token in ("REAL", "LIVE")):
        return "LIVE"
    if any(token in raw for token in ("DEMO", "PRACTICE", "PAPER", "CONTEST")):
        return "DEMO"
    return None


def normalize_mt5_account_type(account_info: Any, fallback: Any = None) -> str:
    """Derive DEMO/LIVE from the MT5 account payload, then fallback safely."""
    info = account_info if isinstance(account_info, dict) else {}

    for key, mode in (
        ("is_live", "LIVE"),
        ("live", "LIVE"),
        ("real", "LIVE"),
        ("is_real", "LIVE"),
        ("is_demo", "DEMO"),
        ("demo", "DEMO"),
        ("paper", "DEMO"),
    ):
        if isinstance(info.get(key), bool) and info.get(key):
            return mode

    for key in (
        "account_type",
        "type",
        "mode",
        "trade_mode",
        "trade_mode_label",
        "trade_mode_name",
        "account_trade_mode",
    ):
        mode = _normalize_account_mode_text(info.get(key))
        if mode:
            return mode

    for key in ("trade_mode", "account_trade_mode", "trade_mode_value", "trade_mode_id"):
        try:
            value = int(info.get(key))
        except (TypeError, ValueError):
            continue
        if value == 2:
            return "LIVE"
        if value in (0, 1):
            return "DEMO"

    server_text = " ".join(
        str(info.get(key) or "") for key in ("server", "name", "company", "broker")
    )
    mode = _normalize_account_mode_text(server_text)
    if mode:
        return mode

    return _normalize_account_mode_text(fallback) or "UNKNOWN"


def annotate_mt5_account_mode(account_info: Any, fallback: Any = None) -> dict[str, Any]:
    result = dict(account_info) if isinstance(account_info, dict) else {}
    mt5_mode = normalize_mt5_account_type(result)
    mode = normalize_mt5_account_type(result, fallback=fallback)
    result["account_type"] = mode
    result["is_demo"] = mode == "DEMO"
    result["is_live"] = mode == "LIVE"
    if mt5_mode in ("DEMO", "LIVE"):
        result["account_mode_source"] = "mt5"
    elif _normalize_account_mode_text(fallback):
        result["account_mode_source"] = "fallback"
    else:
        result["account_mode_source"] = "unknown"
    return result


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
    acct_fallback = None if acct_info else _get(account, "account_type")
    acct_info = annotate_mt5_account_mode(acct_info, fallback=acct_fallback)
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
        "account_type": acct_info.get("account_type"),
        "is_demo": acct_info.get("is_demo"),
        "is_live": acct_info.get("is_live"),
        "account_mode_source": acct_info.get("account_mode_source"),
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
