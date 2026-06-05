import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.accounts.account_contracts import (  # noqa: E402
    AccountValidationError,
    account_added_audit_description,
    account_archived_audit_description,
    account_archived_response,
    account_sync_audit_description,
    account_sync_response,
    build_account_create_response,
    build_agent_account_create_response,
    normalize_account_create_payload,
    normalize_account_update_payload,
    serialize_trading_account,
)


def test_normalize_account_create_payload_accepts_agent_login_alias():
    req = normalize_account_create_payload(
        {"name": "Primary", "login": "12345", "account_type": "live", "currency": "usd"},
        allow_login_alias=True,
    )

    assert req.name == "Primary"
    assert req.account_number == "12345"
    assert req.account_type == "LIVE"
    assert req.currency == "USD"


def test_normalize_account_create_payload_rejects_missing_name_and_bad_type():
    for payload, expected in [
        ({"account_type": "LIVE"}, "name is required"),
        ({"name": "Primary", "account_type": "FUNDED"}, "account_type must be LIVE or DEMO"),
    ]:
        try:
            normalize_account_create_payload(payload)
        except AccountValidationError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("invalid account payload should fail")


def test_normalize_account_update_payload_extracts_editable_fields():
    req = normalize_account_update_payload(
        {
            "name": " Primary ",
            "broker": None,
            "account_type": "demo",
            "currency": "usdt-extra",
            "color": "#123456789abcdef",
            "sort_order": "4",
            "regenerate_secret": True,
        }
    )

    assert req.updates == {
        "name": "Primary",
        "broker": "",
        "account_type": "DEMO",
        "currency": "USDT-EXT",
        "color": "#123456789abcdef",
        "sort_order": 4,
    }
    assert req.regenerate_secret is True


def test_normalize_account_update_payload_rejects_bad_type_and_sort_order():
    for payload, expected in [
        ({"account_type": "FUNDED"}, "account_type must be LIVE or DEMO"),
        ({"sort_order": "last"}, "sort_order must be an integer"),
    ]:
        try:
            normalize_account_update_payload(payload)
        except AccountValidationError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("invalid account update payload should fail")


def test_serialize_trading_account_overlays_live_state():
    now = datetime(2026, 6, 5, 12, 0, 0)
    account = SimpleNamespace(
        id=7,
        name="Primary",
        broker=None,
        server="MetaQuotes",
        account_number="12345",
        account_type="LIVE",
        currency="USD",
        platform="MT5",
        status="online",
        error_message=None,
        color="#fff",
        sort_order=2,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    live_state = {
        "last_seen": (now - timedelta(seconds=10)).isoformat(),
        "account": {"balance": 1000, "equity": 1005, "margin": 20, "margin_free": 980, "margin_level": 500},
    }

    result = serialize_trading_account(account, live_state, now=now)

    assert result["connected"] is True
    assert result["broker"] == ""
    assert result["balance"] == 1000
    assert result["created_at"] == "2026-06-05 12:00 UTC"


def test_account_create_responses_include_secrets_only_when_requested():
    now = datetime(2026, 6, 5, 12, 0, 0)
    account = SimpleNamespace(
        id=7,
        name="Primary",
        broker="MetaTrader",
        server="Broker-Live",
        account_number="12345",
        account_type="LIVE",
        currency="USD",
        platform="MT5",
        status="online",
        error_message=None,
        color="#fff",
        sort_order=2,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    regular = build_account_create_response(account, "secret-once")
    agent = build_agent_account_create_response(account, None)

    assert regular["ea_secret"] == "secret-once"
    assert "success" not in regular
    assert agent["success"] is True
    assert agent["ea_secret"] is None


def test_account_action_responses_and_audit_descriptions_are_stable():
    assert account_archived_response("Primary") == {"success": True, "message": "Account 'Primary' archived"}
    assert account_sync_response("Primary") == {
        "success": True,
        "message": "Sync triggered for 'Primary'. Data will refresh shortly.",
    }
    assert account_added_audit_description("Primary") == "New account 'Primary' added via Agent tab"
    assert account_archived_audit_description("Primary") == "Account 'Primary' archived by user"
    assert account_sync_audit_description("Primary") == "Manual sync triggered for account 'Primary'"
