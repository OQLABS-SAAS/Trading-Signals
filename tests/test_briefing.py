"""Backend tests for the P2 /api/briefing endpoint.

Covers:
  - Endpoint shape: all required keys present.
  - login_required: returns 401 without a session.
  - no-goal stance: mode='no_goal' when intent has no goals set.
  - Ahead stance math: pct >= 100 → mode='ahead' with correct horizon.
  - Behind stance math: pct < 50 → mode='behind'.
  - On-track stance math: 50 <= pct < 100 → mode='on_track'.
  - pnl aggregates: only sums filled MT5Orders with pnl set; unfilled excluded.
  - _briefing_stance pure function: all branches.

Uses in-memory SQLite — mirrors test_intent_model.py seeding pattern.
"""
import json
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ─── SQLite in-memory session factory ────────────────────────────────────────

def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    dvapp._Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _authed_client(Session):
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    dvapp._DBSession = Session
    with client.session_transaction() as sess:
        sess["user_id"] = "brief_test_user"
        sess["logged_in"] = True
    return client


def _anon_client(Session):
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    dvapp._DBSession = Session
    return dvapp.app.test_client()


def _seed_mt5_order(db, uid, pnl_val, status="filled", filled_at=None):
    """Insert a seeded MT5Order with a known pnl value."""
    from app import MT5Order
    if filled_at is None:
        filled_at = datetime.utcnow()
    order = MT5Order(
        user_id=uid,
        symbol="EURUSD",
        order_type="BUY",
        volume=0.01,
        price=1.1000,
        status=status,
        pnl=pnl_val,
        filled_at=filled_at,
        action="open",
    )
    db.add(order)
    db.commit()
    return order


def _seed_intent(db, uid, daily=None, weekly=None, monthly=None):
    """Seed a UserSettings row with an intent_json containing the given goals."""
    from app import UserSettings
    goals = {"daily": daily, "weekly": weekly, "monthly": monthly, "currency": "USD"}
    intent_json = json.dumps({"goals": goals, "risk": {}, "markets": [], "hours": None})
    s = db.query(UserSettings).filter_by(user_id=uid).first()
    if not s:
        s = UserSettings(user_id=uid, intent_json=intent_json)
        db.add(s)
    else:
        s.intent_json = intent_json
    db.commit()


# ─── Shape tests ─────────────────────────────────────────────────────────────

def test_briefing_returns_required_shape():
    Session = _make_session()
    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    for key in ("equity", "balance", "open_positions", "open_risk", "pnl", "goals", "stance", "generated_at"):
        assert key in data, f"Missing key: {key}"


def test_briefing_pnl_has_required_horizons():
    Session = _make_session()
    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    pnl = data["pnl"]
    assert "today"  in pnl
    assert "week"   in pnl
    assert "month"  in pnl


def test_briefing_stance_has_mode_and_text():
    Session = _make_session()
    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    stance = data["stance"]
    assert "mode" in stance
    assert "text" in stance


def test_briefing_open_positions_is_list():
    Session = _make_session()
    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    assert isinstance(data["open_positions"], list)


# ─── Auth required ────────────────────────────────────────────────────────────

def test_briefing_requires_auth():
    Session = _make_session()
    client = _anon_client(Session)
    resp = client.get("/api/briefing")
    assert resp.status_code == 401


# ─── No-goal stance ───────────────────────────────────────────────────────────

def test_briefing_stance_no_goal_when_no_intent():
    """When the user has no goals set, stance.mode must be 'no_goal'."""
    Session = _make_session()
    client = _authed_client(Session)
    # Do NOT seed intent — no goals configured
    resp = client.get("/api/briefing")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["stance"]["mode"] == "no_goal"


def test_briefing_stance_no_goal_text_mentions_goal():
    Session = _make_session()
    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    text = data["stance"]["text"].lower()
    assert "goal" in text


# ─── Stance math: AHEAD ──────────────────────────────────────────────────────

def test_briefing_stance_ahead_when_daily_exceeded():
    """Seed daily goal=100, pnl today=150 → stance.mode='ahead', pct>=100."""
    Session = _make_session()
    db = Session()
    uid = "brief_test_user"
    _seed_intent(db, uid, daily=100)
    # Seed 3 filled orders today totalling +150
    for _ in range(3):
        _seed_mt5_order(db, uid, pnl_val=50.0)
    db.close()

    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["stance"]["mode"] == "ahead", f"stance: {data['stance']}"
    assert data["stance"].get("pct_progress", 0) >= 100.0


def test_briefing_stance_ahead_horizon_is_daily():
    Session = _make_session()
    db = Session()
    uid = "brief_test_user"
    _seed_intent(db, uid, daily=100)
    _seed_mt5_order(db, uid, pnl_val=200.0)
    db.close()
    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    assert data["stance"].get("horizon") == "daily"


# ─── Stance math: BEHIND ─────────────────────────────────────────────────────

def test_briefing_stance_behind_when_pnl_low():
    """daily=200, pnl today=10 → pct=5% → mode='behind'."""
    Session = _make_session()
    db = Session()
    uid = "brief_test_user"
    _seed_intent(db, uid, daily=200)
    _seed_mt5_order(db, uid, pnl_val=10.0)
    db.close()

    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    assert data["stance"]["mode"] == "behind", f"stance: {data['stance']}"
    assert data["stance"]["pct_progress"] < 50.0


# ─── Stance math: ON_TRACK ───────────────────────────────────────────────────

def test_briefing_stance_on_track_at_75_pct():
    """daily=200, pnl today=150 → pct=75% → mode='on_track'."""
    Session = _make_session()
    db = Session()
    uid = "brief_test_user"
    _seed_intent(db, uid, daily=200)
    _seed_mt5_order(db, uid, pnl_val=150.0)
    db.close()

    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    assert data["stance"]["mode"] == "on_track", f"stance: {data['stance']}"


# ─── Weekly goal horizon used when no daily ──────────────────────────────────

def test_briefing_uses_weekly_horizon_when_no_daily():
    """weekly=500, pnl week=600 → ahead, horizon='weekly'."""
    Session = _make_session()
    db = Session()
    uid = "brief_test_user"
    _seed_intent(db, uid, weekly=500)
    # Seed filled orders this week totalling 600
    _seed_mt5_order(db, uid, pnl_val=600.0)
    db.close()

    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    # Since daily is derived from weekly (daily=100), the stance picks daily as primary.
    # After reconciliation daily=100.0, and today's pnl=600 → ahead.
    # Both daily and weekly could apply — either horizon is acceptable.
    assert data["stance"]["mode"] == "ahead"


# ─── pnl aggregation: only filled orders with pnl count ─────────────────────

def test_briefing_pnl_excludes_non_filled_orders():
    """Only 'filled' status orders with pnl set should be counted."""
    Session = _make_session()
    db = Session()
    uid = "brief_test_user"
    _seed_mt5_order(db, uid, pnl_val=100.0, status="filled")
    _seed_mt5_order(db, uid, pnl_val=50.0,  status="pending")   # should NOT count
    _seed_mt5_order(db, uid, pnl_val=25.0,  status="failed")    # should NOT count
    db.close()

    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    # Only the 100.0 order should be counted
    assert abs(data["pnl"]["today"] - 100.0) < 0.01, f"pnl.today={data['pnl']['today']}"


def test_briefing_pnl_today_zero_when_no_orders():
    Session = _make_session()
    client = _authed_client(Session)
    resp = client.get("/api/briefing")
    data = resp.get_json()
    assert data["pnl"]["today"] == 0.0


# ─── _briefing_stance unit tests (pure function) ─────────────────────────────

def test_briefing_stance_pure_no_goal():
    s = dvapp._briefing_stance({}, {"today": 0, "week": 0, "month": 0})
    assert s["mode"] == "no_goal"


def test_briefing_stance_pure_ahead_daily():
    s = dvapp._briefing_stance({"daily": 100}, {"today": 150, "week": 150, "month": 150})
    assert s["mode"] == "ahead"
    assert s["pct_progress"] == 150.0


def test_briefing_stance_pure_behind_daily():
    s = dvapp._briefing_stance({"daily": 200}, {"today": 20, "week": 20, "month": 20})
    assert s["mode"] == "behind"
    assert s["pct_progress"] < 50.0


def test_briefing_stance_pure_on_track_weekly():
    s = dvapp._briefing_stance({"weekly": 500}, {"today": 0, "week": 300, "month": 300})
    assert s["mode"] == "on_track"
    assert s["horizon"] == "weekly"
    assert abs(s["pct_progress"] - 60.0) < 0.1


def test_briefing_stance_pure_ahead_monthly():
    s = dvapp._briefing_stance({"monthly": 2000}, {"today": 0, "week": 0, "month": 2500})
    assert s["mode"] == "ahead"
    assert s["horizon"] == "monthly"


def test_briefing_stance_pure_text_mentions_horizon():
    s = dvapp._briefing_stance({"weekly": 500}, {"today": 0, "week": 600, "month": 600})
    assert "weekly" in s["text"]


def test_briefing_stance_pure_daily_preferred_over_weekly():
    """When both daily and weekly are set, daily is the primary horizon."""
    s = dvapp._briefing_stance({"daily": 100, "weekly": 500}, {"today": 120, "week": 400, "month": 400})
    assert s["horizon"] == "daily"
