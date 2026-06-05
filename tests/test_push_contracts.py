import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.notifications.push_contracts import (  # noqa: E402
    PushSubscriptionValidationError,
    normalize_push_subscribe_payload,
    normalize_push_unsubscribe_payload,
)


def test_normalize_push_subscribe_payload_extracts_endpoint_and_keys():
    req = normalize_push_subscribe_payload(
        {"endpoint": " https://push.example/sub ", "keys": {"p256dh": " key ", "auth": " auth "}}
    )

    assert req.endpoint == "https://push.example/sub"
    assert req.p256dh == "key"
    assert req.auth == "auth"


def test_normalize_push_subscribe_payload_rejects_missing_fields():
    for payload in [
        {},
        {"endpoint": "https://push.example/sub"},
        {"endpoint": "https://push.example/sub", "keys": {"p256dh": "key"}},
    ]:
        try:
            normalize_push_subscribe_payload(payload)
        except PushSubscriptionValidationError as exc:
            assert "endpoint, keys.p256dh, and keys.auth required" in str(exc)
        else:
            raise AssertionError("invalid push subscribe payload should fail")


def test_normalize_push_unsubscribe_payload_requires_endpoint():
    assert normalize_push_unsubscribe_payload({"endpoint": " https://push.example/sub "}) == "https://push.example/sub"

    try:
        normalize_push_unsubscribe_payload({})
    except PushSubscriptionValidationError as exc:
        assert "endpoint required" in str(exc)
    else:
        raise AssertionError("invalid push unsubscribe payload should fail")
