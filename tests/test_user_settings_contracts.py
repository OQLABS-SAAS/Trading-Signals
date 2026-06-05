import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.settings.user_settings_contracts import (  # noqa: E402
    normalize_user_settings_update_payload,
    serialize_user_settings,
)


def test_serialize_user_settings_never_returns_plaintext_credentials():
    settings = SimpleNamespace(
        assets_enabled='["forex", "crypto"]',
        risk_tolerance="aggressive",
        chart_theme=None,
        chart_type=None,
        grid_style=None,
        indicator_scheme=None,
        timezone=None,
        alert_confidence=65,
        alert_price_pct=2.0,
        alert_drawdown_pct=10.0,
        alert_loss_pct=5.0,
        perf_target_winrate=55,
        perf_target_rr=2.0,
        perf_target_trades=5,
        perf_target_annual=20.0,
        portfolio_alloc='{"forex": 60}',
        portfolio_preset="balanced",
        portfolio_rebalance="quarterly",
        portfolio_benchmark="spy",
        mt5_api_key_enc="encrypted",
        mt5_account="12345",
        mt5_broker_server="MetaQuotes",
        telegram_bot_token_enc=None,
        telegram_chat_id="",
    )

    result = serialize_user_settings(settings)

    assert result["assets_enabled"] == ["forex", "crypto"]
    assert result["portfolio_alloc"] == {"forex": 60}
    assert result["chart_type"] == "candle"
    assert result["mt5_configured"] is True
    assert result["telegram_configured"] is False
    assert "mt5_api_key" not in result
    assert "telegram_bot_token" not in result


def test_normalize_user_settings_update_payload_extracts_fields_and_credentials():
    req = normalize_user_settings_update_payload(
        {
            "assets_enabled": ["forex"],
            "risk_tolerance": "moderate",
            "chart_theme": "dark-theme-name-that-is-longer-than-thirty-two-characters",
            "chart_type": "area",
            "alert_confidence": "150",
            "alert_price_pct": "1.5",
            "perf_target_winrate": "62",
            "portfolio_alloc": {"forex": 60, "crypto": 40},
            "portfolio_preset": "aggressive",
            "portfolio_rebalance": "monthly",
            "mt5_api_key": "secret",
            "mt5_account": "12345",
            "telegram_bot_token": "telegram-secret",
        }
    )

    assert json.loads(req.updates["assets_enabled"]) == ["forex"]
    assert req.updates["risk_tolerance"] == "moderate"
    assert req.updates["chart_theme"] == "dark-theme-name-that-is-longer-t"
    assert req.updates["alert_confidence"] == 100
    assert req.updates["alert_price_pct"] == 1.5
    assert req.updates["perf_target_winrate"] == 62
    assert json.loads(req.updates["portfolio_alloc"]) == {"forex": 60, "crypto": 40}
    assert req.credentials == {"mt5_api_key": "secret", "telegram_bot_token": "telegram-secret"}


def test_normalize_user_settings_update_payload_ignores_invalid_values():
    req = normalize_user_settings_update_payload(
        {
            "risk_tolerance": "reckless",
            "chart_type": "candles",
            "alert_price_pct": "wide",
            "portfolio_alloc": ["bad"],
            "portfolio_preset": "yolo",
            "telegram_bot_token": "",
        }
    )

    assert req.updates == {}
    assert req.credentials == {}
