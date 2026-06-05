"""LLM provider helpers.

This is intentionally provider-agnostic and framework-free. Flask routes and
jobs can use it to check API-key readiness and parse structured responses
without duplicating brittle code.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


PROVIDER_ENV_KEYS = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
}

PROVIDER_BASE_URLS = {
    "deepseek": "https://api.deepseek.com",
}

@dataclass(frozen=True)
class LLMProvider:
    name: str
    env_key: str | None
    base_url: str | None = None


def provider_config(provider: str | None) -> LLMProvider:
    name = str(provider or "").strip().lower()
    return LLMProvider(
        name=name,
        env_key=PROVIDER_ENV_KEYS.get(name),
        base_url=PROVIDER_BASE_URLS.get(name),
    )


def is_provider_configured(provider: str | None, environ: dict[str, str]) -> bool:
    config = provider_config(provider)
    if not config.env_key:
        return True
    return bool(str(environ.get(config.env_key, "")).strip())


def missing_provider_error(provider: str | None, process_name: str = "worker") -> dict[str, str]:
    config = provider_config(provider)
    env_key = config.env_key or "LLM_API_KEY"
    return {
        "error": (
            f"{env_key} is not set in this {process_name}'s environment. "
            f"Open Railway -> your {process_name} service -> Variables and add {env_key}. "
            f"The web service may have the key while the process running this job does not."
        ),
        "status": "failed",
    }


def parse_json_object(raw_content: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    text = str(raw_content or "").strip()
    fallback_value = dict(fallback or {})
    if not text:
        return fallback_value
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else fallback_value
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            parsed = json.loads(fence.group(1))
            return parsed if isinstance(parsed, dict) else fallback_value
        except json.JSONDecodeError:
            pass

    obj = re.search(r"\{.*\}", text, re.DOTALL)
    if obj:
        try:
            parsed = json.loads(obj.group(0))
            return parsed if isinstance(parsed, dict) else fallback_value
        except json.JSONDecodeError:
            pass

    return fallback_value
