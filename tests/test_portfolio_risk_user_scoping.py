"""Portfolio/Risk endpoints must never mix positions across users."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as dvapp


def _make_session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    dvapp._Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _client(user_id="owner"):
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    c = dvapp.app.test_client()
    with c.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return c


def _seed_position(
    Session,
    user_id,
    ticker="EURUSD=X",
    asset_type="forex",
    signal="BUY",
    size=4.0,
    entry_price=1.1,
    closed=False,
):
    db = Session()
    try:
        p = dvapp.Position(
            user_id=user_id,
            ticker=ticker,
            asset_type=asset_type,
            signal=signal,
            size=size,
            entry_price=entry_price,
            opened_at=datetime.utcnow(),
            closed_at=datetime.utcnow() if closed else None,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return p.id
    finally:
        db.close()


def _count_positions(Session):
    db = Session()
    try:
        return db.query(dvapp.Position).count()
    finally:
        db.close()


def test_positions_get_returns_only_signed_in_users_positions(monkeypatch):
    Session = _make_session_factory()
    _seed_position(Session, "owner", ticker="EURUSD=X")
    _seed_position(Session, "victim", ticker="USDJPY=X")
    monkeypatch.setattr(dvapp, "_DBSession", Session)

    resp = _client("owner").get("/api/positions")

    assert resp.status_code == 200
    rows = resp.get_json()
    assert [r["ticker"] for r in rows] == ["EURUSD=X"]


def test_positions_delete_cannot_delete_other_users_position(monkeypatch):
    Session = _make_session_factory()
    victim_id = _seed_position(Session, "victim", ticker="USDJPY=X")
    monkeypatch.setattr(dvapp, "_DBSession", Session)

    resp = _client("owner").delete(f"/api/positions/{victim_id}")

    assert resp.status_code == 404
    assert _count_positions(Session) == 1


def test_correlation_risk_uses_only_signed_in_users_open_positions(monkeypatch):
    Session = _make_session_factory()
    _seed_position(Session, "owner", ticker="EURUSD=X", asset_type="forex", signal="BUY", size=4.0)
    _seed_position(Session, "victim", ticker="USDJPY=X", asset_type="forex", signal="BUY", size=99.0)
    monkeypatch.setattr(dvapp, "_DBSession", Session)

    resp = _client("owner").get("/api/positions/correlation-risk")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["exposure_map"] == {"EUR": 4.0, "USD": -4.0}
    assert all(w["currency"] != "JPY" for w in data["warnings"])


def test_var_uses_only_signed_in_users_open_positions_and_user_scoped_cache(monkeypatch):
    Session = _make_session_factory()
    _seed_position(Session, "owner", ticker="EURUSD=X", size=4.0)
    _seed_position(Session, "owner", ticker="GBPUSD=X", size=4.0, closed=True)
    _seed_position(Session, "victim", ticker="USDJPY=X", size=99.0)
    monkeypatch.setattr(dvapp, "_DBSession", Session)

    captured_keys = []
    monkeypatch.setattr(dvapp, "_redis_get_ohlcv", lambda key: captured_keys.append(key) or None)
    monkeypatch.setattr(dvapp, "_redis_set_ohlcv", lambda key, data: captured_keys.append(key))

    def fake_download(ticker, period, interval, progress, auto_adjust):
        idx = pd.date_range("2026-01-01", periods=40, freq="D")
        return pd.DataFrame({"Close": [1.0 + i * 0.01 for i in range(40)]}, index=idx)

    monkeypatch.setattr(dvapp.yf, "download", fake_download)

    resp = _client("owner").post("/api/var", json={"portfolio_value": 10000, "confidence": 0.95})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["positions_used"] == 1
    assert any(key.startswith("var:owner:0.95:10000.0:") for key in captured_keys)
    assert not any(key.startswith("var:victim:") for key in captured_keys)


def test_stress_uses_only_signed_in_users_open_positions(monkeypatch):
    Session = _make_session_factory()
    _seed_position(Session, "owner", ticker="AAPL", asset_type="stock", size=10.0, entry_price=150.0)
    _seed_position(Session, "owner", ticker="MSFT", asset_type="stock", size=10.0, entry_price=300.0, closed=True)
    _seed_position(Session, "victim", ticker="BTC-USD", asset_type="crypto", size=99.0, entry_price=60000.0)
    monkeypatch.setattr(dvapp, "_DBSession", Session)

    resp = _client("owner").post("/api/stress", json={"portfolio_value": 10000})

    assert resp.status_code == 200
    data = resp.get_json()
    assert [row["ticker"] for row in data["rows"]] == ["AAPL"]
    assert data["total_pnl_usd"] == -200.0
