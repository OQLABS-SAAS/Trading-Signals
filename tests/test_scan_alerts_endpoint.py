"""Tests for the /api/scan-alerts endpoint.

Checks:
  - login_required: unauthenticated request returns 401
  - authenticated request returns {"alerts": [...]} shape
  - each alert item includes risk_usd and profit_usd keys
  - graceful empty response when DB is unavailable
"""
import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _anon_client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    return dvapp.app.test_client()


def _authed_client(db_session_factory=None):
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    if db_session_factory is not None:
        dvapp._DBSession = db_session_factory
    with client.session_transaction() as sess:
        sess["user_id"] = "test_scan_user"
        sess["logged_in"] = True
    return client


class _FakeScanAlertRow:
    """Minimal ScanAlert stand-in."""
    def __init__(self, **kw):
        self.id              = kw.get("id", 1)
        self.ticker          = kw.get("ticker", "EURUSD=X")
        self.signal          = kw.get("signal", "BUY")
        self.timeframe       = kw.get("timeframe", "15m")
        self.trade_type      = kw.get("trade_type", "scalping")
        self.entry           = kw.get("entry", 1.0850)
        self.sl              = kw.get("sl", 1.0800)
        self.tp1             = kw.get("tp1", 1.0950)
        self.tp2             = kw.get("tp2", 1.1050)
        self.tp3             = kw.get("tp3", 1.1150)
        self.lot_size        = kw.get("lot_size", 0.05)
        self.entry_confluence= kw.get("entry_confluence", 0.7)
        self.entry_atr       = kw.get("entry_atr", 0.0010)
        self.sent_at         = kw.get("sent_at", datetime(2026, 6, 11, 10, 0, 0))


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows
        self.closed = False

    def query(self, model):
        return self

    def order_by(self, *a):
        return self

    def limit(self, n):
        return self

    def all(self):
        return self._rows

    def close(self):
        self.closed = True


# ─────────────────────────────────────────────────────────────────────────────
# Auth gate
# ─────────────────────────────────────────────────────────────────────────────

def test_scan_alerts_requires_login():
    """Unauthenticated request must return 401."""
    resp = _anon_client().get("/api/scan-alerts")
    assert resp.status_code == 401, (
        f"Expected 401 without auth, got {resp.status_code}: {resp.get_data(as_text=True)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shape
# ─────────────────────────────────────────────────────────────────────────────

def test_scan_alerts_returns_alerts_key(monkeypatch):
    """Response must contain top-level 'alerts' list."""
    rows = [_FakeScanAlertRow()]
    monkeypatch.setattr(dvapp, "_DBSession", lambda: _FakeDB(rows))
    client = _authed_client()
    resp = client.get("/api/scan-alerts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)


def test_scan_alerts_item_has_required_keys(monkeypatch):
    """Each alert item must include risk_usd and profit_usd keys."""
    rows = [_FakeScanAlertRow(
        ticker="EURUSD=X", signal="BUY", entry=1.0850, sl=1.0800, tp1=1.0950, lot_size=0.1
    )]
    monkeypatch.setattr(dvapp, "_DBSession", lambda: _FakeDB(rows))
    client = _authed_client()
    resp = client.get("/api/scan-alerts")
    data = resp.get_json()
    assert len(data["alerts"]) == 1
    item = data["alerts"][0]
    required_keys = {"id", "ticker", "ticker_raw", "signal", "timeframe", "trade_type",
                     "entry", "sl", "tp1", "tp2", "tp3", "lot", "risk_usd", "profit_usd", "sent_at"}
    missing = required_keys - set(item.keys())
    assert not missing, f"Alert item missing keys: {missing}"


def test_scan_alerts_dollar_amounts_populated(monkeypatch):
    """EURUSD alert with valid entry/sl/tp1 must have non-None risk_usd and profit_usd."""
    rows = [_FakeScanAlertRow(
        ticker="EURUSD=X", signal="BUY", entry=1.0850, sl=1.0800, tp1=1.0950, lot_size=0.1
    )]
    monkeypatch.setattr(dvapp, "_DBSession", lambda: _FakeDB(rows))
    client = _authed_client()
    resp = client.get("/api/scan-alerts")
    item = resp.get_json()["alerts"][0]
    assert item["risk_usd"] is not None, "risk_usd should be populated for EURUSD"
    assert item["profit_usd"] is not None, "profit_usd should be populated for EURUSD"
    assert item["risk_usd"] > 0
    assert item["profit_usd"] > 0


def test_scan_alerts_crypto_dollar_amounts(monkeypatch):
    """BTC-USD alert must also have non-None dollar amounts."""
    rows = [_FakeScanAlertRow(
        ticker="BTC-USD", signal="BUY", entry=65000.0, sl=64000.0, tp1=67000.0, lot_size=0.01
    )]
    monkeypatch.setattr(dvapp, "_DBSession", lambda: _FakeDB(rows))
    client = _authed_client()
    resp = client.get("/api/scan-alerts")
    item = resp.get_json()["alerts"][0]
    assert item["risk_usd"] is not None
    assert item["profit_usd"] is not None


def test_scan_alerts_display_ticker_cleaned(monkeypatch):
    """ticker field must strip Yahoo suffixes for readability."""
    rows = [_FakeScanAlertRow(ticker="EURUSD=X")]
    monkeypatch.setattr(dvapp, "_DBSession", lambda: _FakeDB(rows))
    client = _authed_client()
    resp = client.get("/api/scan-alerts")
    item = resp.get_json()["alerts"][0]
    assert "=X" not in item["ticker"], "Display ticker should not contain =X suffix"
    assert item["ticker_raw"] == "EURUSD=X", "ticker_raw must preserve original"


def test_scan_alerts_empty_when_no_db(monkeypatch):
    """When _DBSession is None, must return {"alerts": []} gracefully."""
    monkeypatch.setattr(dvapp, "_DBSession", None)
    client = _authed_client()
    resp = client.get("/api/scan-alerts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"alerts": []}


def test_scan_alerts_empty_list_when_no_rows(monkeypatch):
    """When DB returns no rows, alerts list must be empty."""
    monkeypatch.setattr(dvapp, "_DBSession", lambda: _FakeDB([]))
    client = _authed_client()
    resp = client.get("/api/scan-alerts")
    data = resp.get_json()
    assert data["alerts"] == []
