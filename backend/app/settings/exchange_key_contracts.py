"""Exchange API key request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable


class ExchangeKeyValidationError(ValueError):
    """Raised when an exchange API key request is invalid."""


@dataclass(frozen=True)
class ExchangeKeyCreateRequest:
    exchange: str
    label: str
    api_key: str
    api_secret: str
    api_passphrase: str


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def normalize_exchange_key_create_payload(payload: dict[str, Any] | None) -> ExchangeKeyCreateRequest:
    body = payload if isinstance(payload, dict) else {}
    exchange = str(body.get("exchange") or "").strip().lower()
    api_key = str(body.get("api_key") or "").strip()
    api_secret = str(body.get("api_secret") or "").strip()
    if not exchange or not api_key or not api_secret:
        raise ExchangeKeyValidationError("Exchange, API key, and secret are required")

    return ExchangeKeyCreateRequest(
        exchange=exchange,
        label=str(body.get("label") or "").strip(),
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=str(body.get("api_passphrase") or "").strip(),
    )


def mask_api_key(raw_key: Any) -> str:
    key = str(raw_key or "")
    if len(key) > 8:
        return key[:4] + "••••••••" + key[-4:]
    return "••••••••"


def serialize_exchange_key(row: Any, decrypt: Callable[[Any], str]) -> dict[str, Any]:
    try:
        masked = mask_api_key(decrypt(_get(row, "api_key_enc")))
    except Exception:
        masked = "••••••••"

    created_at = _get(row, "created_at")
    return {
        "id": _get(row, "id"),
        "exchange": _get(row, "exchange"),
        "label": _get(row, "label") or "",
        "key_masked": masked,
        "created_at": created_at.strftime("%Y-%m-%d") if isinstance(created_at, datetime) else "",
    }
