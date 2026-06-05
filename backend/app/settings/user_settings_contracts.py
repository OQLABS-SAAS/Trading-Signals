"""User settings request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


RISK_TOLERANCES = {"conservative", "moderate", "aggressive"}
CHART_TYPES = {"candle", "bar", "line", "area", "hollow"}
PORTFOLIO_PRESETS = {"conservative", "balanced", "aggressive"}
REBALANCE_INTERVALS = {"monthly", "quarterly", "yearly"}


@dataclass(frozen=True)
class UserSettingsUpdateRequest:
    updates: dict[str, Any]
    credentials: dict[str, str]


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _json_loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _json_dumps_list(value: Any) -> str | None:
    try:
        return json.dumps(list(value))
    except Exception:
        return None


def _json_dumps_dict(value: Any) -> str | None:
    try:
        return json.dumps(dict(value))
    except Exception:
        return None


def _bounded_int(value: Any, *, minimum: int | None = None, maximum: int | None = None) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def serialize_user_settings(settings: Any) -> dict[str, Any]:
    if not settings:
        return {}

    return {
        "assets_enabled": _json_loads(_get(settings, "assets_enabled"), []),
        "risk_tolerance": _get(settings, "risk_tolerance"),
        "chart_theme": _get(settings, "chart_theme") or "",
        "chart_type": _get(settings, "chart_type") or "candle",
        "grid_style": _get(settings, "grid_style") or "",
        "indicator_scheme": _get(settings, "indicator_scheme") or "",
        "timezone": _get(settings, "timezone") or "UTC",
        "alert_confidence": _get(settings, "alert_confidence"),
        "alert_price_pct": _get(settings, "alert_price_pct"),
        "alert_drawdown_pct": _get(settings, "alert_drawdown_pct"),
        "alert_loss_pct": _get(settings, "alert_loss_pct"),
        "perf_target_winrate": _get(settings, "perf_target_winrate"),
        "perf_target_rr": _get(settings, "perf_target_rr"),
        "perf_target_trades": _get(settings, "perf_target_trades"),
        "perf_target_annual": _get(settings, "perf_target_annual"),
        "portfolio_alloc": _json_loads(_get(settings, "portfolio_alloc"), {}),
        "portfolio_preset": _get(settings, "portfolio_preset"),
        "portfolio_rebalance": _get(settings, "portfolio_rebalance"),
        "portfolio_benchmark": _get(settings, "portfolio_benchmark"),
        "mt5_configured": bool(_get(settings, "mt5_api_key_enc")),
        "mt5_account": _get(settings, "mt5_account") or "",
        "mt5_broker_server": _get(settings, "mt5_broker_server") or "",
        "telegram_configured": bool(_get(settings, "telegram_bot_token_enc")),
        "telegram_chat_id": _get(settings, "telegram_chat_id") or "",
    }


def normalize_user_settings_update_payload(payload: dict[str, Any] | None) -> UserSettingsUpdateRequest:
    body = payload if isinstance(payload, dict) else {}
    updates: dict[str, Any] = {}
    credentials: dict[str, str] = {}

    if "assets_enabled" in body:
        serialized = _json_dumps_list(body.get("assets_enabled"))
        if serialized is not None:
            updates["assets_enabled"] = serialized
    if body.get("risk_tolerance") in RISK_TOLERANCES:
        updates["risk_tolerance"] = body["risk_tolerance"]

    if "chart_theme" in body:
        updates["chart_theme"] = str(body.get("chart_theme"))[:32]
    if body.get("chart_type") in CHART_TYPES:
        updates["chart_type"] = body["chart_type"]
    if "grid_style" in body:
        updates["grid_style"] = str(body.get("grid_style"))[:16]
    if "indicator_scheme" in body:
        updates["indicator_scheme"] = str(body.get("indicator_scheme"))[:16]
    if "timezone" in body:
        updates["timezone"] = str(body.get("timezone"))[:64]

    if "alert_confidence" in body:
        value = _bounded_int(body.get("alert_confidence"), minimum=0, maximum=100)
        if value is not None:
            updates["alert_confidence"] = value
    for field_name in ("alert_price_pct", "alert_drawdown_pct", "alert_loss_pct", "perf_target_rr", "perf_target_annual"):
        if field_name in body:
            value = _float_or_none(body.get(field_name))
            if value is not None:
                updates[field_name] = value
    for field_name in ("perf_target_winrate", "perf_target_trades"):
        if field_name in body:
            value = _bounded_int(body.get(field_name))
            if value is not None:
                updates[field_name] = value

    if "portfolio_alloc" in body:
        serialized = _json_dumps_dict(body.get("portfolio_alloc"))
        if serialized is not None:
            updates["portfolio_alloc"] = serialized
    if body.get("portfolio_preset") in PORTFOLIO_PRESETS:
        updates["portfolio_preset"] = body["portfolio_preset"]
    if body.get("portfolio_rebalance") in REBALANCE_INTERVALS:
        updates["portfolio_rebalance"] = body["portfolio_rebalance"]
    if "portfolio_benchmark" in body:
        updates["portfolio_benchmark"] = str(body.get("portfolio_benchmark"))[:16]

    if body.get("mt5_api_key"):
        credentials["mt5_api_key"] = str(body["mt5_api_key"])
    if "mt5_account" in body:
        updates["mt5_account"] = str(body.get("mt5_account"))[:64]
    if "mt5_broker_server" in body:
        updates["mt5_broker_server"] = str(body.get("mt5_broker_server"))[:128]
    if body.get("telegram_bot_token"):
        credentials["telegram_bot_token"] = str(body["telegram_bot_token"])
    if "telegram_chat_id" in body:
        updates["telegram_chat_id"] = str(body.get("telegram_chat_id"))[:64]

    return UserSettingsUpdateRequest(updates=updates, credentials=credentials)
