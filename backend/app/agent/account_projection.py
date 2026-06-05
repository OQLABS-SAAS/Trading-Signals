"""Agent account projection helpers.

This module is deliberately framework-free. It owns the contract between saved
TradingAccount rows, live MT5 state, and the Agent tab account view.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable


MT5_ONLINE_TTL_SECONDS = 45


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        return parsed.replace(tzinfo=None)
    return parsed


def _iso_or_none(value: Any) -> str | None:
    parsed = _parse_datetime(value)
    if parsed:
        return parsed.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def initials_for_name(name: str | None) -> str:
    words = [w for w in str(name or "").split() if w]
    if not words:
        return "MT"
    return "".join(w[0] for w in words).upper()[:2]


def normalize_leverage(raw: Any) -> str:
    if raw is None or raw == "":
        return "1:100"
    raw_str = str(raw)
    if isinstance(raw, (int, float)) or raw_str.isdigit():
        return f"1:{raw_str}"
    return raw_str


def live_states_for_query_ids(mt5_state_by_user: dict[str, Any], query_ids: Iterable[str]) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for uid in query_ids:
        candidate = mt5_state_by_user.get(uid, {})
        if isinstance(candidate, dict) and isinstance(candidate.get("account"), dict):
            states.append(candidate)
    return states


def mt5_login_from_state(live_state: dict[str, Any] | None) -> str:
    account = live_state.get("account", {}) if isinstance(live_state, dict) else {}
    return str(account.get("login") or account.get("account_number") or "")


def find_live_state_for_account(
    account_number: Any,
    live_states: list[dict[str, Any]],
    account_count: int,
) -> dict[str, Any] | None:
    account_login = str(account_number or "")
    for candidate in live_states:
        if account_login and mt5_login_from_state(candidate) == account_login:
            return candidate
    if account_count == 1 and len(live_states) == 1:
        return live_states[0]
    return None


def is_live_state_connected(
    live_state: dict[str, Any] | None,
    now: datetime | None = None,
    ttl_seconds: int = MT5_ONLINE_TTL_SECONDS,
) -> bool:
    if not live_state:
        return False
    last_seen = _parse_datetime(live_state.get("last_seen"))
    if not last_seen:
        return False
    now = now or datetime.utcnow()
    return (now - last_seen).total_seconds() < ttl_seconds


def problem_for_status(status: str, drawdown: float, error_message: str | None = None) -> str | None:
    if status == "warning":
        return "Margin warning"
    if drawdown > 20:
        return "Drawdown threshold exceeded"
    if status == "error":
        return error_message or "Account error"
    if status == "disconnected":
        return "Account disconnected"
    return None


def project_agent_account(
    account: Any,
    live_states: list[dict[str, Any]],
    account_count: int,
    *,
    now: datetime | None = None,
    today_pnl: float | None = None,
) -> dict[str, Any]:
    login = _get(account, "account_number") or ""
    live_state = find_live_state_for_account(login, live_states, account_count)
    live_account = live_state.get("account", {}) if live_state else {}
    balance = _to_float(live_account.get("balance"), _to_float(_get(account, "balance"), 0.0))
    equity = _to_float(live_account.get("equity"), _to_float(_get(account, "equity"), balance))
    drawdown = _to_float(_get(account, "drawdown"), 0.0)
    status = "online" if is_live_state_connected(live_state, now=now) else (_get(account, "status") or "disconnected")
    name = _get(account, "name") or "MT5 Account"
    problem = problem_for_status(status, drawdown, _get(account, "error_message"))
    last_seen = _iso_or_none(live_state.get("last_seen")) if live_state else _iso_or_none(_get(account, "last_seen"))

    return {
        "id": _get(account, "id"),
        "name": name,
        "initials": initials_for_name(name),
        "balance": balance,
        "equity": equity,
        "drawdown": drawdown,
        "leverage": normalize_leverage(live_account.get("leverage") or _get(account, "leverage")),
        "login": login,
        "broker": _get(account, "broker"),
        "server": _get(account, "server"),
        "account_number": _get(account, "account_number"),
        "account_type": _get(account, "account_type"),
        "currency": _get(account, "currency"),
        "status": status,
        "problem": problem,
        "today_pnl": today_pnl,
        "last_seen": last_seen,
    }


def project_pending_mt5_account(live_state: dict[str, Any]) -> dict[str, Any]:
    account = live_state.get("account", {}) if isinstance(live_state, dict) else {}
    positions = live_state.get("positions", []) if isinstance(live_state, dict) else []
    balance = _to_float(account.get("balance"), 0.0)
    equity = _to_float(account.get("equity"), balance)
    login = str(account.get("login") or account.get("account_number") or "")
    last_seen = _iso_or_none(live_state.get("last_seen")) if isinstance(live_state, dict) else None
    return {
        "id": "__pending__",
        "name": "MT5 (Pending Setup)",
        "initials": "MT",
        "needs_onboarding": True,
        "balance": balance,
        "equity": equity,
        "drawdown": None,
        "leverage": normalize_leverage(account.get("leverage")) if account.get("leverage") else None,
        "login": login,
        "broker": "MetaTrader 5",
        "server": str(account.get("server", "") or ""),
        "account_number": login,
        "account_type": str(account.get("account_type", "live") or "live"),
        "currency": str(account.get("currency", "USD") or "USD"),
        "status": "pending",
        "problem": None,
        "today_pnl": None,
        "last_seen": last_seen,
        "open_positions": len(positions),
    }


def summarize_agent_dashboard_trades(open_trades: Iterable[Any], closed_trades: Iterable[Any]) -> dict[str, Any]:
    open_rows = list(open_trades)
    closed_rows = list(closed_trades)
    total_closed = len(closed_rows)
    wins = sum(1 for trade in closed_rows if _get(trade, "outcome") == "WIN")
    return {
        "total_open_positions": len(open_rows),
        "unrealized_pnl": round(sum(_to_float(_get(trade, "unrealized_pnl"), 0.0) for trade in open_rows), 2),
        "total_closed_trades_90d": total_closed,
        "win_rate_90d": round(wins / total_closed * 100, 1) if total_closed > 0 else 0.0,
    }


def summarize_agent_dashboard_accounts(projected_accounts: Iterable[dict[str, Any]]) -> dict[str, Any]:
    attention: list[dict[str, Any]] = []
    healthy: list[dict[str, Any]] = []
    online = 0
    total_balance = 0.0
    total_equity = 0.0
    today_pnl = 0.0

    for entry in projected_accounts:
        total_balance += _to_float(entry.get("balance"), 0.0)
        total_equity += _to_float(entry.get("equity"), 0.0)
        today_pnl += _to_float(entry.get("today_pnl"), 0.0)
        status = entry.get("status")
        if status in ("connected", "online"):
            online += 1
        if status in ("warning", "error", "disconnected"):
            attention.append(entry)
        else:
            healthy.append(entry)

    return {
        "online_accounts": online,
        "total_balance": round(total_balance, 2),
        "total_equity": round(total_equity, 2),
        "today_pnl": round(today_pnl, 2),
        "attention": attention,
        "healthy": healthy,
    }


def project_agent_portfolio(accounts: Iterable[Any], open_trades: Iterable[Any]) -> dict[str, Any]:
    account_rows = list(accounts)
    trade_rows = list(open_trades)
    total_unrealized = sum(_to_float(_get(trade, "unrealized_pnl"), 0.0) for trade in trade_rows)
    symbols = list(set(_get(trade, "symbol") for trade in trade_rows))

    projected_accounts = []
    for account in account_rows:
        account_id = _get(account, "id")
        account_name = _get(account, "name") or ""
        account_open_trades = [trade for trade in trade_rows if _get(trade, "account_id") == account_id]
        projected_accounts.append({
            "id": account_id,
            "name": account_name,
            "initials": initials_for_name(account_name),
            "status": _get(account, "status"),
            "open_positions": len(account_open_trades),
            "unrealized_pnl": round(
                sum(_to_float(_get(trade, "unrealized_pnl"), 0.0) for trade in account_open_trades),
                2,
            ),
        })

    return {
        "total_accounts": len(projected_accounts),
        "total_open_positions": len(trade_rows),
        "total_unrealized_pnl": round(total_unrealized, 2),
        "unique_symbols": symbols,
        "accounts": projected_accounts,
    }
