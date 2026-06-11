"""Backend tests for the P1 Intent model.

Covers:
  - _intent_reconcile: daily-only derivation, weekly-only, monthly-only,
    multi-set consistent, multi-set conflicting (>25% off), all-null.
  - GET /api/intent: default shape when no row exists.
  - PUT then GET round-trip: values persisted and returned.
  - PUT validation: risk pct out-of-range, negative goal, bad markets.
  - Auth required: both GET and PUT return 401 without a session.

Uses in-memory SQLite so no Postgres required.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ─── SQLite session factory ───────────────────────────────────────────────────

def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    dvapp._Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _authed_client(Session):
    """Return a Flask test client with a live in-memory DB and an authenticated session."""
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    # Patch the DB session factory
    dvapp._DBSession = Session
    with client.session_transaction() as sess:
        sess["user_id"] = "intent_test_user"
        sess["logged_in"] = True
    return client


def _anon_client(Session):
    """Return a Flask test client with DB but NO session (unauthenticated)."""
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    dvapp._DBSession = Session
    return dvapp.app.test_client()


# ─── Unit tests: _intent_reconcile ───────────────────────────────────────────

def test_reconcile_all_null():
    result = dvapp._intent_reconcile({"goals": {"daily": None, "weekly": None, "monthly": None}})
    assert result["daily"]   is None
    assert result["weekly"]  is None
    assert result["monthly"] is None
    assert "conflict" not in result


def test_reconcile_daily_only_derives_weekly_and_monthly():
    result = dvapp._intent_reconcile({"goals": {"daily": 100, "weekly": None, "monthly": None}})
    assert result["daily"] == 100
    assert result.get("weekly_derived") is True
    assert result.get("monthly_derived") is True
    assert abs(result["weekly"] - 500) < 1       # 100 × 5
    assert abs(result["monthly"] - 2165) < 1      # 100 × 5 × 4.33


def test_reconcile_weekly_only_derives_daily_and_monthly():
    result = dvapp._intent_reconcile({"goals": {"daily": None, "weekly": 500, "monthly": None}})
    assert result["weekly"] == 500
    assert result.get("daily_derived") is True
    assert result.get("monthly_derived") is True
    assert abs(result["daily"] - 100) < 1         # 500 / 5
    assert abs(result["monthly"] - 2165) < 5      # 500 × 4.33


def test_reconcile_monthly_only_derives_daily_and_weekly():
    result = dvapp._intent_reconcile({"goals": {"daily": None, "weekly": None, "monthly": 2165}})
    assert result["monthly"] == 2165
    assert result.get("weekly_derived") is True
    assert result.get("daily_derived") is True
    assert abs(result["weekly"] - 500) < 2        # 2165 / 4.33
    assert abs(result["daily"] - 100) < 2         # 2165 / (5 × 4.33)


def test_reconcile_consistent_two_no_conflict():
    # daily=100, weekly=500 — exactly consistent (no conflict expected)
    result = dvapp._intent_reconcile({"goals": {"daily": 100, "weekly": 500, "monthly": None}})
    assert "conflict" not in result


def test_reconcile_inconsistent_triggers_conflict():
    # daily=100 implies weekly=500; set weekly=800 → >25% off
    result = dvapp._intent_reconcile({"goals": {"daily": 100, "weekly": 800, "monthly": None}})
    assert "conflict" in result
    assert "weekly" in result["conflict"].lower()


def test_reconcile_conflict_note_is_human_readable():
    result = dvapp._intent_reconcile({"goals": {"daily": 100, "weekly": 800, "monthly": None}})
    note = result["conflict"]
    assert "weekly" in note.lower()
    # Should mention actual and implied values
    assert "800" in note
    assert "500" in note


def test_reconcile_empty_goals_dict():
    result = dvapp._intent_reconcile({})
    assert result["daily"]   is None
    assert result["weekly"]  is None
    assert result["monthly"] is None


def test_reconcile_zero_treated_as_unset():
    result = dvapp._intent_reconcile({"goals": {"daily": 0, "weekly": None, "monthly": None}})
    assert result["daily"]  is None
    assert result["weekly"] is None


def test_reconcile_currency_preserved():
    result = dvapp._intent_reconcile({"goals": {"daily": 100, "currency": "GBP"}})
    assert result["currency"] == "GBP"


# ─── Route tests ─────────────────────────────────────────────────────────────

def test_intent_get_returns_default_shape_when_no_row():
    Session = _make_session()
    client = _authed_client(Session)
    resp = client.get("/api/intent")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "goals"   in data
    assert "risk"    in data
    assert "markets" in data
    assert "hours"   in data
    assert data["risk"]["max_per_trade_pct"] == 1.0
    assert data["risk"]["max_open_risk_pct"] == 3.0
    assert isinstance(data["markets"], list)


def test_intent_put_then_get_roundtrip():
    Session = _make_session()
    client = _authed_client(Session)

    payload = {
        "goals":   {"daily": 100, "weekly": None, "monthly": None},
        "risk":    {"max_per_trade_pct": 1.5, "max_open_risk_pct": 4.0, "daily_loss_stop_pct": 2.0},
        "markets": ["forex", "crypto"],
        "hours":   {"start": "09:30", "end": "16:00", "tz": "America/New_York"},
    }
    put_resp = client.put("/api/intent",
                          json=payload,
                          content_type="application/json")
    assert put_resp.status_code == 200, put_resp.get_data(as_text=True)
    put_data = put_resp.get_json()
    assert put_data["status"] == "ok"
    assert "intent" in put_data

    get_resp = client.get("/api/intent")
    assert get_resp.status_code == 200
    got = get_resp.get_json()

    assert got["risk"]["max_per_trade_pct"] == 1.5
    assert got["risk"]["max_open_risk_pct"] == 4.0
    assert got["risk"]["daily_loss_stop_pct"] == 2.0
    assert "forex" in got["markets"]
    assert "crypto" in got["markets"]
    assert got["hours"]["start"] == "09:30"
    assert got["hours"]["tz"] == "America/New_York"
    # daily=100 should trigger derived weekly and monthly
    assert got["goals"]["daily"] == 100
    assert got["goals"].get("weekly_derived") is True


def test_intent_put_validation_rejects_risk_pct_out_of_range():
    Session = _make_session()
    client = _authed_client(Session)
    payload = {
        "goals":   {},
        "risk":    {"max_per_trade_pct": 99},   # > 10 — must be rejected
        "markets": [],
        "hours":   None,
    }
    resp = client.put("/api/intent", json=payload, content_type="application/json")
    assert resp.status_code == 400, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "error" in data


def test_intent_put_validation_rejects_negative_goal():
    Session = _make_session()
    client = _authed_client(Session)
    payload = {
        "goals":   {"daily": -50},
        "risk":    {},
        "markets": [],
        "hours":   None,
    }
    resp = client.put("/api/intent", json=payload, content_type="application/json")
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_intent_put_validation_rejects_unknown_market():
    Session = _make_session()
    client = _authed_client(Session)
    payload = {
        "goals":   {},
        "risk":    {},
        "markets": ["forex", "unicorn_market"],   # unknown
        "hours":   None,
    }
    resp = client.put("/api/intent", json=payload, content_type="application/json")
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_intent_get_requires_auth():
    Session = _make_session()
    client = _anon_client(Session)
    resp = client.get("/api/intent")
    assert resp.status_code == 401, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data.get("login_required") is True or "Unauthorized" in data.get("error", "")


def test_intent_put_requires_auth():
    Session = _make_session()
    client = _anon_client(Session)
    resp = client.put("/api/intent", json={}, content_type="application/json")
    assert resp.status_code == 401, resp.get_data(as_text=True)


def test_intent_put_valid_risk_boundary_values():
    """Min (0.1) and max (10.0) risk pct values must be accepted."""
    Session = _make_session()
    client = _authed_client(Session)
    for v in [0.1, 10.0]:
        resp = client.put("/api/intent",
                          json={"goals": {}, "risk": {"max_per_trade_pct": v}, "markets": [], "hours": None},
                          content_type="application/json")
        assert resp.status_code == 200, f"v={v} rejected: {resp.get_data(as_text=True)}"


def test_intent_get_goals_reconciled_in_response():
    """GET /api/intent must return reconciled goals (derived flags) not raw stored values."""
    Session = _make_session()
    client = _authed_client(Session)
    # Store daily=200 only
    client.put("/api/intent",
               json={"goals": {"daily": 200}, "risk": {}, "markets": [], "hours": None},
               content_type="application/json")
    resp = client.get("/api/intent")
    data = resp.get_json()
    g = data["goals"]
    assert g["daily"] == 200
    assert g.get("weekly_derived") is True
    assert abs(g["weekly"] - 1000) < 1
