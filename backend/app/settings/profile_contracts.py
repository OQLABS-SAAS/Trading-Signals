"""Profile settings request contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfileUpdateRequest:
    name: str
    old_password: str
    new_password: str


def normalize_profile_update_payload(payload: dict[str, Any] | None) -> ProfileUpdateRequest:
    body = payload if isinstance(payload, dict) else {}
    return ProfileUpdateRequest(
        name=str(body.get("name") or "").strip(),
        old_password=str(body.get("old_password") or "").strip(),
        new_password=str(body.get("new_password") or "").strip(),
    )
