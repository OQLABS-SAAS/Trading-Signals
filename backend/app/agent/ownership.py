"""Agent ownership and mutation policy helpers."""

from __future__ import annotations

from typing import Any


SHARED_EA_ACCOUNT_ERROR = "Cannot modify shared EA account"


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def agent_account_mutation_error(account: Any, session_user_id: str) -> str | None:
    if account and _get(account, "user_id") == "default" and session_user_id != "default":
        return SHARED_EA_ACCOUNT_ERROR
    return None
