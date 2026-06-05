import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp


def _authed_pro_client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return client


def test_mt5_order_rejects_missing_invalid_or_zero_volume(monkeypatch):
    calls = {"db": 0}

    def fail_if_called():
        calls["db"] += 1
        raise AssertionError("DB session should not open for invalid order size")

    monkeypatch.setattr(dvapp, "_DBSession", fail_if_called)
    client = _authed_pro_client()

    base = {"ticker": "EURUSD", "asset_type": "forex", "direction": "BUY", "entry": 1.1, "sl": 1.09, "tp1": 1.12}
    payloads = [
        base,
        {**base, "lots": "abc"},
        {**base, "lots": 0},
    ]

    for payload in payloads:
        resp = client.post("/api/mt5/order", json=payload)
        assert resp.status_code == 400
        assert "volume required" in resp.get_json()["error"]

    assert calls["db"] == 0


def test_mt5_order_rejects_invalid_numeric_fields_before_db(monkeypatch):
    calls = {"db": 0}

    def fail_if_called():
        calls["db"] += 1
        raise AssertionError("DB session should not open for invalid numeric input")

    monkeypatch.setattr(dvapp, "_DBSession", fail_if_called)
    client = _authed_pro_client()

    base = {"ticker": "EURUSD", "asset_type": "forex", "direction": "BUY", "lots": 0.1, "entry": 1.1}
    cases = [
        ({**base, "entry": "abc"}, "price/entry"),
        ({**base, "sl": "bad"}, "sl"),
        ({**base, "tp1": "bad"}, "tp/tp1"),
        ({**base, "entry_confluence": "bad"}, "entry_confluence"),
    ]

    for payload, field in cases:
        resp = client.post("/api/mt5/order", json=payload)
        assert resp.status_code == 400
        assert field in resp.get_json()["error"]

    assert calls["db"] == 0


def test_execution_order_rejects_invalid_numeric_fields_before_db(monkeypatch):
    calls = {"db": 0}

    def fail_if_called():
        calls["db"] += 1
        raise AssertionError("DB session should not open for invalid execution order")

    monkeypatch.setattr(dvapp, "_DBSession", fail_if_called)
    client = _authed_pro_client()

    base = {"symbol": "EURUSD", "side": "BUY", "quantity": 0.1, "entry_price": 1.1}
    cases = [
        ({**base, "quantity": "bad"}, "quantity"),
        ({**base, "quantity": 0}, "quantity"),
        ({**base, "entry_price": "bad"}, "entry_price"),
        ({**base, "stop_loss": "bad"}, "stop_loss"),
        ({**base, "take_profit": "bad"}, "take_profit"),
    ]

    for payload, field in cases:
        resp = client.post("/api/orders", json=payload)
        assert resp.status_code == 400
        assert field in resp.get_json()["error"]

    assert calls["db"] == 0
