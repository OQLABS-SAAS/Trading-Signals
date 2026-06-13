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


def _seed_filled_order(Session, user_id, ticket, order_type="BUY", account_id=7):
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


def _seed_pending_close(Session, user_id, ticket, account_id=7):
    """Insert a pending CLOSE order for a given ticket."""
    db = Session()
    try:
        o = dvapp.MT5Order(
            user_id=user_id,
            account_id=account_id,
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


def _seed_pending_trailing(Session, user_id, ticket, account_id=7):
    """Insert a pending TRAILING order for a given ticket."""
    db = Session()
    try:
        o = dvapp.MT5Order(
            user_id=user_id,
            account_id=account_id,
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


def _seed_pending_modify_sl(Session, user_id, ticket, account_id=7):
    """Insert a pending MODIFY / modify_sl order for a given ticket."""
    db = Session()
    try:
        o = dvapp.MT5Order(
            user_id=user_id,
            account_id=account_id,
            symbol="EURUSD",
            order_type="MODIFY",
            volume=0,
            price=0,
            sl=1.081,
            status="pending",
            action="modify_sl",
            close_ticket=ticket,
        )
        db.add(o)
        db.commit()
        db.refresh(o)
        return o.id
    finally:
        db.close()


def _seed_unfilled_open_order(Session, user_id, ticket, status="executing", account_id=8):
    db = Session()
    try:
        o = dvapp.MT5Order(
            user_id=user_id,
            account_id=account_id,
            symbol="WRONG",
            order_type="BUY",
            volume=0.1,
            price=1.1,
            status=status,
            action="open",
            mt5_ticket=ticket,
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


def _seed_account(Session, user_id="testuser", account_id=7, account_number="123456", account_type="LIVE"):
    db = Session()
    try:
        acct = dvapp.TradingAccount(
            id=account_id,
            user_id=user_id,
            name="Primary",
            broker="TestBroker",
            account_number=account_number,
            account_type=account_type,
            currency="USD",
            platform="MT5",
            is_active=True,
        )
        db.add(acct)
        db.commit()
        return acct.id
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
    queued = _latest_order(Session, "CLOSE")
    assert queued.account_id == 7
    assert queued.symbol == "EURUSD"


def test_close_ignores_unfilled_same_ticket_when_selecting_owned_position(monkeypatch):
    """Close must derive account/symbol from a filled parent order, not stale executing rows."""
    Session = _make_sqlite_session_factory()
    _seed_unfilled_open_order(Session, "testuser", ticket=12347, account_id=8)
    _seed_filled_order(Session, "testuser", ticket=12347, account_id=7)

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/close", json={"ticket": 12347, "symbol": "EURUSD", "account_id": 7})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    queued = _latest_order(Session, "CLOSE")
    assert queued.account_id == 7
    assert queued.symbol == "EURUSD"


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
    queued = _latest_order(Session, "TRAILING")
    assert queued.account_id == 7
    assert queued.symbol == "EURUSD"
    assert queued.price == 20.0


def test_trailing_ignores_unfilled_same_ticket_when_selecting_owned_position(monkeypatch):
    """Trailing must derive account/symbol from a filled parent order."""
    Session = _make_sqlite_session_factory()
    _seed_unfilled_open_order(Session, "testuser", ticket=77780, account_id=8)
    _seed_filled_order(Session, "testuser", ticket=77780, account_id=7)

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/trailing", json={"ticket": 77780, "pips": 20, "account_id": 7})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    queued = _latest_order(Session, "TRAILING")
    assert queued.account_id == 7
    assert queued.symbol == "EURUSD"


def test_trailing_rejects_invalid_pip_distance(monkeypatch):
    """Trailing distance must be positive before a broker-facing row is queued."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "testuser", ticket=77779)
    before = _count_orders(Session, "TRAILING")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/trailing", json={"ticket": 77779, "pips": -5})

    assert resp.status_code == 400, resp.get_data(as_text=True)
    assert "valid trailing stop distance required" in resp.get_json()["error"]
    assert _count_orders(Session, "TRAILING") == before


# ─── S-9: /api/mt5/breakeven ownership ───────────────────────────────────────

def test_breakeven_rejects_ticket_owned_by_other_user(monkeypatch):
    """Attacker cannot move stop to entry on a victim's position."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "victim_user", ticket=44444)
    before = _count_orders(Session, "MODIFY")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("attacker_user")
    resp = client.post("/api/mt5/breakeven", json={"ticket": 44444, "be_price": 1.081, "account_id": 7})

    assert resp.status_code == 403, resp.get_data(as_text=True)
    data = resp.get_json()
    assert "not yours" in data["error"] or "not found" in data["error"]
    assert _count_orders(Session, "MODIFY") == before


def test_breakeven_allows_owner_to_queue_modify_sl(monkeypatch):
    """The legitimate owner can queue a modify_sl row for their filled ticket."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "testuser", ticket=44445, account_id=7)
    before = _count_orders(Session, "MODIFY")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/breakeven", json={"ticket": 44445, "be_price": 1.081, "account_id": 7})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "ok"
    assert _count_orders(Session, "MODIFY") == before + 1
    queued = _latest_order(Session, "MODIFY")
    assert queued.account_id == 7
    assert queued.symbol == "EURUSD"
    assert queued.action == "modify_sl"
    assert queued.close_ticket == 44445
    assert queued.sl == 1.081


def test_breakeven_ignores_unfilled_same_ticket_when_selecting_owned_position(monkeypatch):
    """Break-even must derive account/symbol from a filled parent order."""
    Session = _make_sqlite_session_factory()
    _seed_unfilled_open_order(Session, "testuser", ticket=44446, account_id=8)
    _seed_filled_order(Session, "testuser", ticket=44446, account_id=7)

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/breakeven", json={"ticket": 44446, "be_price": 1.081, "account_id": 7})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    queued = _latest_order(Session, "MODIFY")
    assert queued.account_id == 7
    assert queued.symbol == "EURUSD"
    assert queued.action == "modify_sl"


def test_breakeven_dedup_returns_existing_pending_modify_not_new_row(monkeypatch):
    """Double-tap breakeven: second call returns existing pending MODIFY, no new row."""
    Session = _make_sqlite_session_factory()
    _seed_filled_order(Session, "testuser", ticket=44447, account_id=7)
    existing_id = _seed_pending_modify_sl(Session, "testuser", ticket=44447, account_id=7)
    before = _count_orders(Session, "MODIFY")

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.post("/api/mt5/breakeven", json={"ticket": 44447, "be_price": 1.081, "account_id": 7})

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["status"] == "duplicate"
    assert data["id"] == existing_id
    assert _count_orders(Session, "MODIFY") == before, "Must NOT add a new MODIFY row on dedup"


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


def test_mt5_orders_return_account_metadata_for_history_badges(monkeypatch):
    """Order history must expose account context so Act rows are not ambiguous."""
    Session = _make_sqlite_session_factory()
    _seed_account(Session, account_id=7, account_number="123456", account_type="LIVE")
    _seed_filled_order(Session, "testuser", ticket=33333, account_id=7)

    monkeypatch.setattr(dvapp, "_DBSession", Session)

    client = _authed_pro_client("testuser")
    resp = client.get("/api/mt5/orders")

    assert resp.status_code == 200, resp.get_data(as_text=True)
    order = resp.get_json()["orders"][0]
    assert order["account_id"] == 7
    assert order["account_number"] == "123456"
    assert order["account_type"] == "LIVE"


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
