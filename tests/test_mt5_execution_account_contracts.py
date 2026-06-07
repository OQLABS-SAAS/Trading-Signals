from pathlib import Path
import os
import sys
from types import SimpleNamespace


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp


APP = Path("app.py").read_text()


def test_mt5_submit_routes_stamp_selected_account_context():
    assert "def _resolve_selected_mt5_account" in APP
    assert "account = _resolve_selected_mt5_account(db, user_id, body)" in APP
    assert "account_id       = account.id" in APP
    assert "account_id = account.id" in APP
    assert '"account_type": account_type' in APP


def test_mt5_pending_poll_uses_authenticated_ea_identity_and_projects_account():
    assert "ea_uid = getattr(request, 'ea_user_id', None)" in APP
    assert "projected = project_pending_mt5_order(o)" in APP
    assert '"account_number": account.account_number' in APP
    assert '"is_live": account_type == "LIVE"' in APP


class _FakeQuery:
    def __init__(self, accounts):
        self.accounts = list(accounts)

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        self.accounts = [
            item
            for item in self.accounts
            if all(getattr(item, key, None) == value for key, value in kwargs.items())
        ]
        return self

    def first(self):
        return self.accounts[0] if self.accounts else None

    def all(self):
        return self.accounts


class _FakeDB:
    def __init__(self, accounts):
        self.accounts = list(accounts)
        self.added = []
        self.committed = False
        self.closed = False
        self.rolled_back = False

    def query(self, model):
        return _FakeQuery(self.accounts)

    def add(self, obj):
        obj.id = 101
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class _FakePendingDB:
    def __init__(self, orders, accounts):
        self.orders = list(orders)
        self.accounts = list(accounts)
        self.committed = False
        self.closed = False
        self.rolled_back = False

    def query(self, model):
        if model is dvapp.MT5Order:
            return _FakeQuery(self.orders)
        if model is dvapp.TradingAccount:
            return _FakeQuery(self.accounts)
        return _FakeQuery([])

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class _FakeConfirmDB:
    def __init__(self, orders):
        self.orders = list(orders)
        self.committed = False
        self.closed = False
        self.rolled_back = False

    def query(self, model):
        if model is dvapp.MT5Order:
            return _FakeQuery(self.orders)
        return _FakeQuery([])

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class _FakeSyncDB:
    def __init__(self, accounts):
        self.accounts = list(accounts)
        self.committed = False
        self.closed = False
        self.rolled_back = False

    def query(self, model):
        if model is dvapp.TradingAccount:
            return _FakeQuery(self.accounts)
        return _FakeQuery([])

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _authed_pro_client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return client


def test_mt5_submit_order_functionally_stamps_selected_account(monkeypatch):
    account = SimpleNamespace(
        id=7,
        user_id="testuser",
        account_number="123456",
        account_type="LIVE",
        is_active=True,
        updated_at=None,
    )
    fake_db = _FakeDB([account])

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)

    resp = _authed_pro_client().post(
        "/api/mt5/order",
        json={
            "account_id": 7,
            "ticker": "EURUSD",
            "asset_type": "forex",
            "direction": "BUY",
            "lots": 0.2,
            "entry": 1.08,
            "sl": 1.075,
            "tp1": 1.09,
            "timeframe": "1h",
        },
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["order_id"] == 101
    assert data["account_id"] == 7
    assert data["account_type"] == "LIVE"
    assert data["is_live"] is True
    assert data["is_demo"] is False
    assert fake_db.committed is True
    assert fake_db.closed is True
    order = fake_db.added[0]
    assert order.account_id == 7
    assert order.volume == 0.2
    assert order.symbol == "EURUSD"
    assert "acct=7 LIVE" in order.comment


def test_mt5_submit_order_requires_account_selection_when_ambiguous(monkeypatch):
    fake_db = _FakeDB(
        [
            SimpleNamespace(id=7, user_id="testuser", account_number="123456", account_type="LIVE", is_active=True),
            SimpleNamespace(id=8, user_id="testuser", account_number="789000", account_type="DEMO", is_active=True),
        ]
    )
    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)

    resp = _authed_pro_client().post(
        "/api/mt5/order",
        json={
            "ticker": "EURUSD",
            "asset_type": "forex",
            "direction": "BUY",
            "lots": 0.2,
            "entry": 1.08,
        },
    )

    assert resp.status_code == 400, resp.get_data(as_text=True)
    assert "select a connected MT5 account" in resp.get_json()["error"]
    assert fake_db.added == []
    assert fake_db.rolled_back is True


def test_mt5_submit_order_does_not_downgrade_saved_mode_from_partial_mt5_state(monkeypatch):
    account = SimpleNamespace(
        id=7,
        user_id="testuser",
        account_number="123456",
        account_type="LIVE",
        is_active=True,
        updated_at=None,
    )
    fake_db = _FakeDB([account])

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)
    with dvapp.mt5_state_lock:
        previous_state = dict(dvapp.mt5_state)
        dvapp.mt5_state.clear()
        dvapp.mt5_state["testuser"] = {"account": {"login": "123456", "balance": 1000}}
    try:
        resp = _authed_pro_client().post(
            "/api/mt5/order",
            json={
                "ticker": "EURUSD",
                "asset_type": "forex",
                "direction": "BUY",
                "lots": 0.2,
                "entry": 1.08,
            },
        )
    finally:
        with dvapp.mt5_state_lock:
            dvapp.mt5_state.clear()
            dvapp.mt5_state.update(previous_state)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["account_type"] == "LIVE"
    assert data["is_live"] is True
    assert account.account_type == "LIVE"
    assert account.updated_at is None
    assert "acct=7 LIVE" in fake_db.added[0].comment


def test_mt5_pending_poll_returns_account_context_and_marks_executing(monkeypatch):
    order = SimpleNamespace(
        id=101,
        user_id="testuser",
        account_id=7,
        symbol="EURUSD",
        order_type="BUY",
        volume=0.2,
        price=1.08,
        sl=1.075,
        tp=1.09,
        tp2=None,
        tp3=None,
        action="open",
        close_ticket=None,
        trailing=False,
        be=True,
        macro=False,
        inval=False,
        sent=False,
        tp1_alert=True,
        tp2_alert=False,
        weekend=False,
        status="pending",
    )
    account = SimpleNamespace(
        id=7,
        account_number="123456",
        account_type="LIVE",
    )
    fake_db = _FakePendingDB([order], [account])
    previous_bypass = dvapp.MT5_BYPASS_USER_IDS
    settings_users = []

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)
    monkeypatch.setattr(
        dvapp,
        "_get_automation_settings",
        lambda user_id: settings_users.append(user_id) or {"trailing_on": True, "trailing_pips": 33, "trailing_atr_mult": 2},
    )
    dvapp.MT5_BYPASS_USER_IDS = {"testuser"}
    try:
        resp = dvapp.app.test_client().get("/api/mt5/pending")
    finally:
        dvapp.MT5_BYPASS_USER_IDS = previous_bypass

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert len(data["orders"]) == 1
    projected = data["orders"][0]
    assert projected["id"] == 101
    assert projected["account_id"] == 7
    assert projected["account_number"] == "123456"
    assert projected["account_type"] == "LIVE"
    assert projected["is_live"] is True
    assert projected["is_demo"] is False
    assert projected["volume"] == 0.2
    assert projected["be"] is True
    assert data["settings"]["trailing_on"] is True
    assert data["settings"]["trailing_pips"] == 33.0
    assert data["settings"]["trailing_atr_mult"] == 2.0
    assert settings_users == ["testuser", "testuser"]
    assert projected["settings"]["trailing_on"] is True
    assert projected["settings"]["trailing_pips"] == 33.0
    assert order.status == "executing"
    assert fake_db.committed is True
    assert fake_db.closed is True


def test_mt5_pending_poll_includes_per_order_settings_for_mixed_default_queue(monkeypatch):
    user_order = SimpleNamespace(
        id=101,
        user_id="testuser",
        account_id=None,
        symbol="EURUSD",
        order_type="BUY",
        volume=0.2,
        price=1.08,
        sl=1.075,
        tp=1.09,
        tp2=None,
        tp3=None,
        action="open",
        close_ticket=None,
        trailing=False,
        be=False,
        macro=False,
        inval=False,
        sent=False,
        tp1_alert=False,
        tp2_alert=False,
        weekend=False,
        status="pending",
    )
    default_order = SimpleNamespace(**{**user_order.__dict__, "id": 102, "user_id": "default", "symbol": "XAUUSD"})
    fake_db = _FakePendingDB([user_order, default_order], [])
    previous_bypass = dvapp.MT5_BYPASS_USER_IDS
    settings_users = []

    def fake_settings(user_id):
        settings_users.append(user_id)
        return {
            "trailing_on": user_id == "testuser",
            "trailing_pips": 33 if user_id == "testuser" else 77,
            "trailing_atr_mult": 2 if user_id == "testuser" else 5,
        }

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)
    monkeypatch.setattr(dvapp, "_get_automation_settings", fake_settings)
    dvapp.MT5_BYPASS_USER_IDS = {"testuser"}
    try:
        resp = dvapp.app.test_client().get("/api/mt5/pending")
    finally:
        dvapp.MT5_BYPASS_USER_IDS = previous_bypass

    assert resp.status_code == 200, resp.get_data(as_text=True)
    orders = resp.get_json()["orders"]
    by_id = {o["id"]: o for o in orders}
    assert by_id[101]["settings"]["trailing_pips"] == 33.0
    assert by_id[101]["settings"]["trailing_atr_mult"] == 2.0
    assert by_id[102]["settings"]["trailing_pips"] == 77.0
    assert by_id[102]["settings"]["trailing_atr_mult"] == 5.0
    assert settings_users[:2] == ["testuser", "default"]


def test_mt5_legacy_bypass_rejects_ambiguous_multi_user_configuration(monkeypatch):
    previous_bypass = dvapp.MT5_BYPASS_USER_IDS
    fake_db = _FakePendingDB([], [])

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)
    dvapp.MT5_BYPASS_USER_IDS = {"user-a", "user-b"}
    try:
        resp = dvapp.app.test_client().get("/api/mt5/pending")
    finally:
        dvapp.MT5_BYPASS_USER_IDS = previous_bypass

    assert resp.status_code == 401, resp.get_data(as_text=True)
    assert "Ambiguous MT5 legacy bypass" in resp.get_json()["message"]
    assert fake_db.closed is False


def _mt5_order(**overrides):
    base = {
        "id": 101,
        "user_id": "testuser",
        "account_id": 7,
        "symbol": "EURUSD",
        "order_type": "BUY",
        "volume": 0.2,
        "price": 1.08,
        "sl": 1.075,
        "tp": 1.09,
        "tp2": 1.095,
        "tp3": 1.1,
        "timeframe": "1h",
        "action": "open",
        "close_ticket": None,
        "status": "executing",
        "mt5_ticket": None,
        "fill_price": None,
        "pnl": None,
        "comment": "DotVerse #101 acct=7 LIVE",
        "filled_at": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_mt5_confirm_scopes_to_ea_user_and_preserves_existing_comment(monkeypatch):
    order = _mt5_order()
    other_user_order = _mt5_order(id=102, user_id="otheruser", comment="DotVerse #102 acct=9 LIVE")
    fake_db = _FakeConfirmDB([order, other_user_order])
    previous_bypass = dvapp.MT5_BYPASS_USER_IDS
    settings_users = []

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)
    monkeypatch.setattr(dvapp, "_get_automation_settings", lambda user_id: settings_users.append(user_id) or {"market_alerts_on": False})
    dvapp.MT5_BYPASS_USER_IDS = {"testuser"}
    try:
        resp = dvapp.app.test_client().post(
            "/api/mt5/confirm",
            json={"order_id": 101, "status": "filled", "ticket": 555, "fill_price": 1.081},
        )
    finally:
        dvapp.MT5_BYPASS_USER_IDS = previous_bypass

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["status"] == "ok"
    assert order.status == "filled"
    assert order.mt5_ticket == 555
    assert order.fill_price == 1.081
    assert order.comment == "DotVerse #101 acct=7 LIVE"
    assert other_user_order.status == "executing"
    assert settings_users == ["testuser"]
    assert fake_db.committed is True
    assert fake_db.closed is True


def test_mt5_confirm_rejects_unknown_or_invalid_results(monkeypatch):
    fake_db = _FakeConfirmDB([_mt5_order(id=101)])
    previous_bypass = dvapp.MT5_BYPASS_USER_IDS

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)
    dvapp.MT5_BYPASS_USER_IDS = {"testuser"}
    try:
        missing_resp = dvapp.app.test_client().post(
            "/api/mt5/confirm",
            json={"order_id": 999, "status": "filled", "ticket": 555, "fill_price": 1.081},
        )
        invalid_resp = dvapp.app.test_client().post(
            "/api/mt5/confirm",
            json={"order_id": 101, "status": "mystery", "ticket": 555, "fill_price": 1.081},
        )
    finally:
        dvapp.MT5_BYPASS_USER_IDS = previous_bypass

    assert missing_resp.status_code == 404, missing_resp.get_data(as_text=True)
    assert missing_resp.get_json()["error"] == "MT5 order not found"
    assert invalid_resp.status_code == 400, invalid_resp.get_data(as_text=True)
    assert "valid MT5 confirmation status" in invalid_resp.get_json()["error"]
    assert fake_db.committed is False
    assert fake_db.closed is True


def test_mt5_push_sync_does_not_persist_unknown_mode_as_demo(monkeypatch):
    account = SimpleNamespace(
        id=7,
        user_id="testuser",
        account_number="123456",
        account_type="LIVE",
        is_active=True,
        updated_at=None,
    )
    fake_db = _FakeSyncDB([account])

    monkeypatch.setattr(dvapp, "_DBSession", lambda: fake_db)

    dvapp._sync_mt5_account_mode_from_state(
        "testuser",
        {"login": "123456", "balance": 1000},
    )

    assert account.account_type == "LIVE"
    assert fake_db.committed is False
    assert fake_db.rolled_back is False
    assert fake_db.closed is False
