import os
import sys

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp
import entry_engine


def _authed_client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return client


def _df(rows=80):
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "Open": [100 + i * 0.1 for i in range(rows)],
            "High": [101 + i * 0.1 for i in range(rows)],
            "Low": [99 + i * 0.1 for i in range(rows)],
            "Close": [100.5 + i * 0.1 for i in range(rows)],
            "Volume": [1000 + i for i in range(rows)],
        },
        index=idx,
    )


def _base_payload(**overrides):
    payload = {
        "ticker": "AAPL",
        "asset_type": "stock",
        "timeframe": "1d",
        "signal": "BUY",
        "entry": 100,
        "stop_loss": 95,
        "tp1": 110,
        "tp2": 115,
        "tp3": 120,
        "_btVerified": True,
        "_btPf": 1.4,
        "_btExpectancy": 0.2,
        "_btTrades": 80,
    }
    payload.update(overrides)
    return payload


def test_positive_backtest_can_authorize_existing_scale_out(monkeypatch):
    monkeypatch.setattr(dvapp, "provider_first_download", lambda *args, **kwargs: _df())

    def fake_plan(*args, **kwargs):
        return {
            "mode": "single",
            "legs": [{"price": 100, "fraction": 1.0, "kind": "market"}],
            "total_risk": 100,
            "decision_basis": "engine_disabled - default single entry",
            "rule_statuses": {"ob_retest": "unproven"},
            "evidence": ["No fresh unmitigated OB detected near entry."],
            "analysis": {
                "hypothetical_mode": "single",
                "hypothetical_basis": "No scale-in signal; positive backtest supports scale-out.",
            },
        }

    monkeypatch.setattr(entry_engine, "propose_entry_plan", fake_plan)

    resp = _authed_client().post("/api/entry-plan/advisory", json=_base_payload())

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["ready"] is True
    assert data["recommended_mode"] == "scale_out"
    assert data["execution_authority"] is True
    assert data["live_mode_allowed"] is True
    assert "existing scale-out ladder path" in data["authority_reason"]


def test_unproven_scale_in_is_advisory_only_even_with_positive_backtest(monkeypatch):
    monkeypatch.setattr(dvapp, "provider_first_download", lambda *args, **kwargs: _df())

    def fake_plan(*args, **kwargs):
        return {
            "mode": "single",
            "legs": [{"price": 100, "fraction": 1.0, "kind": "market"}],
            "total_risk": 100,
            "decision_basis": "engine_disabled - default single entry",
            "rule_statuses": {"ob_retest": "unproven", "idm_wait": "unproven"},
            "evidence": ["Fresh OB at [97, 99] (bullish, tested 0x)"],
            "analysis": {
                "hypothetical_mode": "scale_in",
                "hypothetical_basis": "HYPOTHETICAL: engine WOULD propose scale-in.",
            },
        }

    monkeypatch.setattr(entry_engine, "propose_entry_plan", fake_plan)

    resp = _authed_client().post("/api/entry-plan/advisory", json=_base_payload())

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["ready"] is True
    assert data["recommended_mode"] == "scale_in"
    assert data["execution_authority"] is False
    assert data["live_mode_allowed"] is False
    assert "locked until real-kline backtests" in data["authority_reason"]


def test_missing_trade_levels_return_honest_ready_false_without_500():
    resp = _authed_client().post(
        "/api/entry-plan/advisory",
        json={"ticker": "AAPL", "asset_type": "stock", "signal": "BUY"},
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["ready"] is False
    assert data["execution_authority"] is False
    assert "required" in data["reason"]
