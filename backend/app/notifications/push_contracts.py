"""Web push subscription request contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PushSubscriptionValidationError(ValueError):
    """Raised when a web push subscription request is invalid."""


@dataclass(frozen=True)
class PushSubscribeRequest:
    endpoint: str
    p256dh: str
    auth: str


def normalize_push_subscribe_payload(payload: dict[str, Any] | None) -> PushSubscribeRequest:
    body = payload if isinstance(payload, dict) else {}
    keys = body.get("keys") if isinstance(body.get("keys"), dict) else {}
    endpoint = str(body.get("endpoint") or "").strip()
    p256dh = str(keys.get("p256dh") or "").strip()
    auth = str(keys.get("auth") or "").strip()
    if not endpoint or not p256dh or not auth:
        raise PushSubscriptionValidationError("endpoint, keys.p256dh, and keys.auth required")
    return PushSubscribeRequest(endpoint=endpoint, p256dh=p256dh, auth=auth)


def normalize_push_unsubscribe_payload(payload: dict[str, Any] | None) -> str:
    body = payload if isinstance(payload, dict) else {}
    endpoint = str(body.get("endpoint") or "").strip()
    if not endpoint:
        raise PushSubscriptionValidationError("endpoint required")
    return endpoint
