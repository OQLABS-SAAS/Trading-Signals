import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.llm.providers import (  # noqa: E402
    is_provider_configured,
    missing_provider_error,
    parse_json_object,
    provider_config,
)


def test_provider_config_maps_supported_keys():
    deepseek = provider_config("DeepSeek")

    assert deepseek.name == "deepseek"
    assert deepseek.env_key == "DEEPSEEK_API_KEY"
    assert deepseek.base_url == "https://api.deepseek.com"


def test_is_provider_configured_checks_required_env_only():
    assert is_provider_configured("deepseek", {"DEEPSEEK_API_KEY": "sk-test"}) is True
    assert is_provider_configured("deepseek", {"DEEPSEEK_API_KEY": ""}) is False
    assert is_provider_configured("unknown-provider", {}) is True


def test_missing_provider_error_names_process_and_env_key():
    result = missing_provider_error("deepseek", process_name="worker")

    assert result["status"] == "failed"
    assert "DEEPSEEK_API_KEY" in result["error"]
    assert "worker service" in result["error"]


def test_parse_json_object_handles_markdown_and_fallbacks():
    assert parse_json_object('{"ok": true}') == {"ok": True}
    assert parse_json_object('```json\n{"score": 7}\n```') == {"score": 7}
    assert parse_json_object("not json", fallback={"quality_score": 5}) == {"quality_score": 5}
