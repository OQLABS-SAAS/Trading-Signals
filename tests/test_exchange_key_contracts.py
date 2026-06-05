import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.settings.exchange_key_contracts import (  # noqa: E402
    ExchangeKeyValidationError,
    mask_api_key,
    normalize_exchange_key_create_payload,
    serialize_exchange_key,
)


def test_normalize_exchange_key_create_payload_extracts_required_fields():
    req = normalize_exchange_key_create_payload(
        {
            "exchange": " Binance ",
            "label": " Main ",
            "api_key": " key ",
            "api_secret": " secret ",
            "api_passphrase": " pass ",
        }
    )

    assert req.exchange == "binance"
    assert req.label == "Main"
    assert req.api_key == "key"
    assert req.api_secret == "secret"
    assert req.api_passphrase == "pass"


def test_normalize_exchange_key_create_payload_rejects_missing_required_fields():
    for payload in [
        {},
        {"exchange": "binance", "api_key": "key"},
        {"exchange": "binance", "api_secret": "secret"},
    ]:
        try:
            normalize_exchange_key_create_payload(payload)
        except ExchangeKeyValidationError as exc:
            assert "Exchange, API key, and secret are required" in str(exc)
        else:
            raise AssertionError("invalid exchange key payload should fail")


def test_mask_api_key_preserves_existing_mask_shape():
    assert mask_api_key("abcd12345678wxyz") == "abcd••••••••wxyz"
    assert mask_api_key("short") == "••••••••"


def test_serialize_exchange_key_masks_key_and_formats_date():
    row = SimpleNamespace(
        id=2,
        exchange="binance",
        label=None,
        api_key_enc="encrypted",
        created_at=datetime(2026, 6, 5, 12, 0, 0),
    )

    result = serialize_exchange_key(row, lambda encrypted: "abcd12345678wxyz")

    assert result == {
        "id": 2,
        "exchange": "binance",
        "label": "",
        "key_masked": "abcd••••••••wxyz",
        "created_at": "2026-06-05",
    }
