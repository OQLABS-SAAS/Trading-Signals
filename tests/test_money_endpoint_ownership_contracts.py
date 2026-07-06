"""
Security + dedup ownership contracts for money-moving endpoints.

Tests S-7/S-8: /api/mt5/close and /api/mt5/trailing must reject tickets that
don't belong to the requesting user.

Tests B1: duplicate pending CLOSE/TRAILING returns the existing order, no new row.

Tests S-1: _binance_signed_request/_coinbase_signed_request require user_id and
refuse to load a key owned by a different user.

Tests single-user/"default": the owner or "default" can still close their own ticket.

Uses in-memory SQLite so real SQLAlchemy filter expressions are properly evaluated.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ─── In-memory SQLite session factory ────────────────────────────────────────

def _make_sqlite_session_factory():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    dvapp._Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _seed_filled_order(Session, user_id, ticket, order_type="BUY", account_id=None):
    """Insert a filled BUY/SELL order with a known mt5_ticket."""
    db = Session()
    try:
        o = dvapp.MT5Order(
            user_id=user_id,
            account_id=account_id,
            symbol="EURUSD",
            order_type=order_type,
            volume=0.1,
            price=1.1,
            status="filled",
            action="open",
            mt5_ticket=ticket,
        )
        db.add(o)
        db.commit()
        db.refresh(o)
        return o.id
    finally:
        db.close()


def _seed_pending_close(Session, user_id, ticket):
    """Insert a pending CLOSE order for a given ticket."""
    db = Session()
    try:
        o = dvapp.MT5Order(
            user_id=user_id,
            symbol="EURUSD",
            order_type="CLOSE",
            volume=0,
            price=0,
            status="pending",
            action="close",
            close_ticket=ticket,
        )
        db.add(o)
        db.commit()
        db.refresh(o)
        return o.id
    finally:
        db.close()


def _seed_pending_trailing(Session, user_id, ticket):
    """Insert a pending TRAILING order for a given ticket."""
    db = Session()
    try:
        o = dvapp.MT5Order(
            user_id=user_id,
            symbol="AUTO",
            order_type="TRAILING",
            volume=0,
            price=20,
            status="pending",
            action="trailing",
            close_ticket=ticket,
        )
        db.add(o)
        db.commit()
        db.refresh(o)
        return o.id
    finally:
        db.close()


def _count_orders(Session, order_type=None):
    db = Session()
    try:
        q = db.query(dvapp.MT5Order)
        if order_type:
            q = q.filter(dvapp.MT5Order.order_type == order_type)
        return q.count()
    finally:
        db.close()


def _latest_order(Session, order_type):
    db = Session()
    try:
        return (
            db.query(dvapp.MT5Order)
            .filter(dvapp.MT5Order.order_type == order_type)
            .order_by(dvapp.MT5Order.id.desc())
            .first()
        )
    finally:
        db.close()


# ─── Flask test client ────────────────────────────────────────────────────────

def _authed_pro_client(user_id="testuser"):
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return client


# ─── S-7: /api/mt5/close ownership ───────────────────────────────────────────

def test_close_rejects_ticket_owned_by_other_user(monkeypatch):
    """Attacker cannot close a ticket that belongs to victim. Must return 403, no row created."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "victim_user", ticket=12345)
    before = _count_orders(Session, "CLOSE")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("attacker_user")
    resp = client.post("/api/mt5/close", json={"ticket": 12345, "symbol": "EURUSD"})

    assert resp.status_code == 403, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "not yours" in data["error"] or "not found" in data["error"]
    assert _count_orders(Session, "CLOSE") == before, "No CLOSE row must be created"


def test_close_allows_owner_to_close_their_ticket(monkeypatch):
    """The legitimate owner can close their own ticket."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "testuser", ticket=12346)
    before = _count_orders(Session, "CLOSE")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/close", json={"ticket": 12346, "symbol": "EURUSD"})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["status"] == "ok"
    assert _count_orders(Session, "CLOSE") == before + 1


def test_close_accepts_live_position_ticket_from_mt5_state(monkeypatch):
    """MT5 position tickets differ from stored deal tickets; close must use the live position ticket."""
    Session = _make_sqlite_session_factory()
    order_id = _seed_filled_order(Session, "testuser", ticket=400441944)
    before = _count_orders(Session, "CLOSE")

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    with dvapp.mt5_state_lock:
        old_state = dict(dvapp.mt5_state)
        dvapp.mt5_state.clear()
        dvapp.mt5_state["testuser"] = {
            "account_id": None,
            "positions": [
                {
                    "ticket": 496397257,
                    "symbol": "AMD",
                    "comment": f"DotVerse #{order_id}",
                }
            ],
        }

    try:
        client = _authed_pro_client("testuser")
        resp = client.post("/api/mt5/close", json={"ticket": 496397257, "symbol": "AMD"})

        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["status"] == "ok"
        assert _count_orders(Session, "CLOSE") == before + 1
        close_order = _latest_order(Session, "CLOSE")
        assert close_order.close_ticket == 496397257
        assert close_order.comment == f"User close for DotVerse #{order_id}"
    finally:
        with dvapp.mt5_state_lock:
            dvapp.mt5_state.clear()
            dvapp.mt5_state.update(old_state)


def test_close_accepts_selected_account_when_mt5_state_has_no_account_id(monkeypatch):
    """Older EA/state snapshots may omit account_id; DB ownership still scopes the selected account."""
    Session = _make_sqlite_session_factory()
    order_id = _seed_filled_order(Session, "testuser", ticket=400441944, account_id=1)

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    with dvapp.mt5_state_lock:
        old_state = dict(dvapp.mt5_state)
        dvapp.mt5_state.clear()
        dvapp.mt5_state["testuser"] = {
            "positions": [
                {
                    "ticket": 496397257,
                    "symbol": "AMD",
                    "comment": f"DotVerse #{order_id}",
                }
            ],
        }

    try:
        client = _authed_pro_client("testuser")
        resp = client.post(
            "/api/mt5/close",
            json={"ticket": 496397257, "symbol": "AMD", "account_id": 1},
        )

        assert resp.status_code == 200, resp.get_data(as_text=True)
        close_order = _latest_order(Session, "CLOSE")
        assert close_order.account_id == 1
        assert close_order.close_ticket == 496397257
    finally:
        with dvapp.mt5_state_lock:
            dvapp.mt5_state.clear()
            dvapp.mt5_state.update(old_state)


def test_close_translates_stored_deal_ticket_to_live_position_ticket(monkeypatch):
    """If the caller sends the stored deal ticket, send EA the current live position ticket instead."""
    Session = _make_sqlite_session_factory()
    order_id = _seed_filled_order(Session, "testuser", ticket=400441944)

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    with dvapp.mt5_state_lock:
        old_state = dict(dvapp.mt5_state)
        dvapp.mt5_state.clear()
        dvapp.mt5_state["testuser"] = {
            "account_id": None,
            "positions": [
                {
                    "ticket": 496397257,
                    "symbol": "AMD",
                    "comment": f"DotVerse #{order_id}",
                }
            ],
        }

    try:
        client = _authed_pro_client("testuser")
        resp = client.post("/api/mt5/close", json={"ticket": 400441944, "symbol": "AMD"})

        assert resp.status_code == 200, resp.get_data(as_text=True)
        close_order = _latest_order(Session, "CLOSE")
        assert close_order.close_ticket == 496397257
    finally:
        with dvapp.mt5_state_lock:
            dvapp.mt5_state.clear()
            dvapp.mt5_state.update(old_state)


def test_close_allows_default_user_to_close_their_ticket(monkeypatch):
    """Single-user / 'default' path: user_id='default' can close their own ticket."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "default", ticket=99991)
    before = _count_orders(Session, "CLOSE")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("default")
    resp = client.post("/api/mt5/close", json={"ticket": 99991, "symbol": "EURUSD"})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert _count_orders(Session, "CLOSE") == before + 1


def test_close_blocks_ticket_that_does_not_exist(monkeypatch):
    """If no filled BUY/SELL order matches the ticket, return 403."""
    Session = _make_sqlite_session_factory()
    before = _count_orders(Session, "CLOSE")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/close", json={"ticket": 88888, "symbol": "EURUSD"})

    assert resp.status_code == 403
    assert _count_orders(Session, "CLOSE") == before


# ─── S-8: /api/mt5/trailing ownership ────────────────────────────────────────

def test_trailing_rejects_ticket_owned_by_other_user(monkeypatch):
    """Attacker cannot set trailing on a ticket that belongs to victim."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "victim_user", ticket=77777)
    before = _count_orders(Session, "TRAILING")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("attacker_user")
    resp = client.post("/api/mt5/trailing", json={"ticket": 77777, "pips": 15})

    assert resp.status_code == 403, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "not yours" in data["error"] or "not found" in data["error"]
    assert _count_orders(Session, "TRAILING") == before


def test_trailing_allows_owner_to_set_trailing(monkeypatch):
    """The legitimate owner can set trailing on their own ticket."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "testuser", ticket=77778)
    before = _count_orders(Session, "TRAILING")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/trailing", json={"ticket": 77778, "pips": 20})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["status"] == "ok"
    assert _count_orders(Session, "TRAILING") == before + 1


def test_breakeven_accepts_live_position_ticket_from_mt5_state(monkeypatch):
    """Manual BE must target the MT5 live position ticket, not the stored deal ticket."""
    Session = _make_sqlite_session_factory()
    order_id = _seed_filled_order(Session, "testuser", ticket=400441944)

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    with dvapp.mt5_state_lock:
        old_state = dict(dvapp.mt5_state)
        dvapp.mt5_state.clear()
        dvapp.mt5_state["testuser"] = {
            "account_id": None,
            "positions": [
                {
                    "ticket": 496397257,
                    "symbol": "AMD",
                    "comment": f"DotVerse #{order_id}",
                }
            ],
        }

    try:
        client = _authed_pro_client("testuser")
        resp = client.post("/api/mt5/breakeven", json={"ticket": 496397257, "be_price": 562.95})

        assert resp.status_code == 200, resp.get_data(as_text=True)
        modify_order = _latest_order(Session, "MODIFY")
        assert modify_order.close_ticket == 496397257
        assert modify_order.comment == f"Manual BE: move SL to entry 562.95 for DotVerse #{order_id}"
    finally:
        with dvapp.mt5_state_lock:
            dvapp.mt5_state.clear()
            dvapp.mt5_state.update(old_state)


def test_trailing_accepts_live_position_ticket_from_mt5_state(monkeypatch):
    """Trailing stop must target the MT5 live position ticket, not the stored deal ticket."""
    Session = _make_sqlite_session_factory()
    order_id = _seed_filled_order(Session, "testuser", ticket=400441944)

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    with dvapp.mt5_state_lock:
        old_state = dict(dvapp.mt5_state)
        dvapp.mt5_state.clear()
        dvapp.mt5_state["testuser"] = {
            "account_id": None,
            "positions": [
                {
                    "ticket": 496397257,
                    "symbol": "AMD",
                    "comment": f"DotVerse #{order_id}",
                }
            ],
        }

    try:
        client = _authed_pro_client("testuser")
        resp = client.post("/api/mt5/trailing", json={"ticket": 496397257, "pips": 20})

        assert resp.status_code == 200, resp.get_data(as_text=True)
        trailing_order = _latest_order(Session, "TRAILING")
        assert trailing_order.close_ticket == 496397257
        assert trailing_order.comment == f"Trailing stop 20.0 pips for DotVerse #{order_id}"
    finally:
        with dvapp.mt5_state_lock:
            dvapp.mt5_state.clear()
            dvapp.mt5_state.update(old_state)


def test_trailing_allows_default_user_to_set_trailing(monkeypatch):
    """Single-user / 'default' path: user_id='default' can set trailing."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "default", ticket=55555)
    before = _count_orders(Session, "TRAILING")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("default")
    resp = client.post("/api/mt5/trailing", json={"ticket": 55555, "pips": 25})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert _count_orders(Session, "TRAILING") == before + 1


# ─── B1: dedup on /api/mt5/close ────────────────────────────────────────────

def test_close_dedup_returns_existing_pending_close_not_new_row(monkeypatch):
    """Double-tap close: second call returns existing pending CLOSE, no new row."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "testuser", ticket=11111)
    existing_id = _seed_pending_close(Session, "testuser", ticket=11111)
    before = _count_orders(Session, "CLOSE")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/close", json={"ticket": 11111, "symbol": "EURUSD"})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["status"] == "duplicate"
    assert data["id"] == existing_id
    assert _count_orders(Session, "CLOSE") == before, "Must NOT add a new CLOSE row on dedup"


# ─── B1: dedup on /api/mt5/trailing ─────────────────────────────────────────

def test_trailing_dedup_returns_existing_pending_trailing_not_new_row(monkeypatch):
    """Double-tap trailing: second call returns existing pending TRAILING, no new row."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "testuser", ticket=22222)
    existing_id = _seed_pending_trailing(Session, "testuser", ticket=22222)
    before = _count_orders(Session, "TRAILING")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/trailing", json={"ticket": 22222, "pips": 20})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["status"] == "duplicate"
    assert data["order_id"] == existing_id
    assert _count_orders(Session, "TRAILING") == before, "Must NOT add a new TRAILING row on dedup"


# ─── S-1: _binance_signed_request requires user_id ───────────────────────────

def test_binance_signed_request_requires_user_id(monkeypatch):
    """Calling _binance_signed_request without user_id must return an error, no DB opened."""
    calls = {"count": 0}

    def fail_if_called():
        calls["count"] += 1
        raise AssertionError("DB must not be opened when user_id is missing")

    monkeypatch.setattr(dvapp, "_DBSession", fail_if_called)

    data, error = dvapp._binance_signed_request(key_id=1, method="GET", path="/test")
    assert data is None
    assert error is not None
    assert "user_id" in error
    assert calls["count"] == 0


def test_binance_signed_request_rejects_key_owned_by_different_user(monkeypatch):
    """A Binance key owned by user 999 cannot be used by user 1."""
    Session = _make_sqlite_session_factory()

    # Insert a key owned by user 999
    db = Session()
    key = dvapp.ExchangeKey(
        user_id=999,
        exchange="binance",
        label="victim_key",
        api_key_enc="enc_key",
        api_secret_enc="enc_secret",
    )
    db.add(key)
    db.commit()
    key_id = key.id
    db.close()

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    monkeypatch.setattr(dvapp, "_dec", lambda x: "decrypted")

    data, error = dvapp._binance_signed_request(
        key_id=key_id, method="GET", path="/test", user_id="1"
    )
    assert data is None
    assert error is not None
    assert "not found" in error.lower()


def test_binance_signed_request_succeeds_for_correct_owner(monkeypatch):
    """A Binance key owned by the requesting user_id passes ownership; fails only at network."""
    Session = _make_sqlite_session_factory()

    db = Session()
    key = dvapp.ExchangeKey(
        user_id=42,
        exchange="binance",
        label="my_key",
        api_key_enc="enc_key",
        api_secret_enc="enc_secret",
    )
    db.add(key)
    db.commit()
    key_id = key.id
    db.close()

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    monkeypatch.setattr(dvapp, "_dec", lambda x: "my_api_key_value")

    import unittest.mock as mock
    fake_response = mock.Mock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"balances": []}

    with mock.patch("requests.get", return_value=fake_response):
        data, error = dvapp._binance_signed_request(
            key_id=key_id, method="GET", path="/api/v3/account", user_id="42"
        )

    assert error is None, f"Unexpected error: {error}"
    assert data is not None


# ─── S-1: _coinbase_signed_request requires user_id ──────────────────────────

def test_coinbase_signed_request_requires_user_id(monkeypatch):
    """Calling _coinbase_signed_request without user_id must return an error, no DB opened."""
    calls = {"count": 0}

    def fail_if_called():
        calls["count"] += 1
        raise AssertionError("DB must not be opened when user_id is missing")

    monkeypatch.setattr(dvapp, "_DBSession", fail_if_called)

    data, error = dvapp._coinbase_signed_request(key_id=1, method="GET", path="/test")
    assert data is None
    assert error is not None
    assert "user_id" in error
    assert calls["count"] == 0


def test_coinbase_signed_request_rejects_key_owned_by_different_user(monkeypatch):
    """A Coinbase key owned by user 888 cannot be used by user 1."""
    Session = _make_sqlite_session_factory()

    db = Session()
    key = dvapp.ExchangeKey(
        user_id=888,
        exchange="coinbase",
        label="victim_cb_key",
        api_key_enc="enc_key",
        api_secret_enc="enc_secret",
    )
    db.add(key)
    db.commit()
    key_id = key.id
    db.close()

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    monkeypatch.setattr(dvapp, "_dec", lambda x: "decrypted")

    data, error = dvapp._coinbase_signed_request(
        key_id=key_id, method="GET", path="/test", user_id="1"
    )
    assert data is None
    assert error is not None
    assert "not found" in error.lower()


def test_coinbase_signed_request_succeeds_for_correct_owner(monkeypatch):
    """A Coinbase key owned by the requesting user_id passes ownership; fails only at network."""
    Session = _make_sqlite_session_factory()

    db = Session()
    key = dvapp.ExchangeKey(
        user_id=7,
        exchange="coinbase",
        label="my_cb_key",
        api_key_enc="enc_key",
        api_secret_enc="enc_secret",
    )
    db.add(key)
    db.commit()
    key_id = key.id
    db.close()

    monkeypatch.setattr(dvapp, "_DBSession", Session)
    monkeypatch.setattr(dvapp, "_dec", lambda x: "my_cb_key_value")

    import unittest.mock as mock
    fake_response = mock.Mock()
    fake_response.status_code = 200
    fake_response.text = '{"accounts":[]}'
    fake_response.json.return_value = {"accounts": []}

    with mock.patch("requests.get", return_value=fake_response):
        data, error = dvapp._coinbase_signed_request(
            key_id=key_id, method="GET", path="/accounts", user_id="7"
        )

    assert error is None, f"Unexpected error: {error}"
    assert data is not None
