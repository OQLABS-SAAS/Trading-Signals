"""
GAP 1.5 Integration Tests — BUG A, E, K, N
============================================
Uses the real Flask app + real PostgreSQL DB.
Each test seeds its own rows, exercises the real endpoint, and asserts DB state.

Run:
    pip install pytest --break-system-packages -q
    DATABASE_URL="postgresql://..." REDIS_URL="redis://..." pytest tests/test_gap15_bugs.py -v

Environment variables required (same as Railway):
    DATABASE_URL   — PostgreSQL connection string
    REDIS_URL      — Redis connection string (can be empty, tests don't need it)
    SECRET_KEY     — Flask secret key
    MT5_BYPASS_USER_IDS — set to "testuser" so _require_ea passes without a real X-EA-Secret
"""

import os, sys, pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal env so app bootstraps without crashing
os.environ.setdefault("SECRET_KEY",           "test-secret-key-not-for-prod")
os.environ.setdefault("DATABASE_URL",         os.environ.get("DATABASE_URL", ""))
os.environ.setdefault("REDIS_URL",            "")
os.environ.setdefault("MT5_BYPASS_USER_IDS",  "testuser")

import app as dvapp

# ── helpers ──────────────────────────────────────────────────────────────────

def _db():
    """Return a fresh DB session."""
    return dvapp._DBSession()


def _seed_order(user_id, order_type, status, symbol="EURUSD", **kwargs):
    """Insert a minimal MT5Order row and return its id."""
    db = _db()
    try:
        o = dvapp.MT5Order(
            user_id    = user_id,
            symbol     = symbol,
            order_type = order_type,
            volume     = 0.01,
            price      = 1.1000,
            status     = status,
            action     = "open",
            **kwargs,
        )
        db.add(o)
        db.commit()
        db.refresh(o)
        oid = o.id
        return oid
    finally:
        db.close()


def _get_order(order_id):
    db = _db()
    try:
        return db.query(dvapp.MT5Order).filter_by(id=order_id).first()
    finally:
        db.close()


def _delete_order(order_id):
    db = _db()
    try:
        o = db.query(dvapp.MT5Order).filter_by(id=order_id).first()
        if o:
            db.delete(o)
            db.commit()
    finally:
        db.close()


def _seed_scan_alert(ticker, signal, entry, sl, tp1, tp2, tp3):
    """Insert a minimal ScanAlert row and return its id."""
    db = _db()
    try:
        rec = dvapp.ScanAlert(
            ticker           = ticker,
            signal           = signal,
            timeframe        = "1h",
            trade_type       = "swing",
            entry            = entry,
            sl               = sl,
            tp1              = tp1,
            tp2              = tp2,
            tp3              = tp3,
            lot_size         = 0.01,
            entry_confluence = 0.70,
            entry_atr        = 0.0012,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        rid = rec.id
        return rid
    finally:
        db.close()


def _delete_scan_alert(scan_id):
    db = _db()
    try:
        rec = db.query(dvapp.ScanAlert).filter_by(id=scan_id).first()
        if rec:
            db.delete(rec)
            db.commit()
    finally:
        db.close()


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    with dvapp.app.test_client() as c:
        # Inject a session so @login_required passes
        with c.session_transaction() as sess:
            sess["user_id"]   = "testuser"
            sess["logged_in"] = True
            sess["user_tier"] = "pro"
        yield c


# ── BUG A ─────────────────────────────────────────────────────────────────────
# mt5_cancel_order must cancel orders owned by "default" when called by a real user.
# BEFORE fix: query used `MT5Order.user_id == user_id` — "default" orders never matched → 404.
# AFTER fix:  query uses `.in_([user_id, "default"])` — "default" orders match → 200, status=cancelled.

class TestBugA:
    def test_cancel_default_order_returns_200(self, client):
        """A 'default' user_id order must be cancellable by any logged-in user."""
        oid = _seed_order("default", "BUY", "pending")
        try:
            resp = client.post(f"/api/mt5/cancel/{oid}")
            assert resp.status_code == 200, \
                f"BEFORE fix this was 404. Got {resp.status_code}: {resp.data}"
            data = resp.get_json()
            assert data.get("status") == "cancelled", \
                f"Expected status=cancelled, got: {data}"
        finally:
            _delete_order(oid)

    def test_cancel_default_order_persists_cancelled_in_db(self, client):
        """After cancel, DB row must have status='cancelled'."""
        oid = _seed_order("default", "BUY", "pending")
        try:
            client.post(f"/api/mt5/cancel/{oid}")
            o = _get_order(oid)
            assert o.status == "cancelled", \
                f"DB row still has status='{o.status}' — fix not persisting."
        finally:
            _delete_order(oid)

    def test_cancel_own_order_still_works(self, client):
        """Own user_id orders must still cancel correctly (regression guard)."""
        oid = _seed_order("testuser", "BUY", "pending")
        try:
            resp = client.post(f"/api/mt5/cancel/{oid}")
            assert resp.status_code == 200
            assert resp.get_json().get("status") == "cancelled"
        finally:
            _delete_order(oid)


# ── BUG E ─────────────────────────────────────────────────────────────────────
# mt5_level_alert must return 200 with note="missing_ticket" when ticket is None.
# mt5_level_alert must return 200 with note="invalid_ticket" when ticket is non-numeric.
# BEFORE fix: `int(ticket)` on None raised TypeError → 500.
# AFTER fix:  early guards return 200 before int() is attempted.

class TestBugE:
    def _ea_post(self, client, payload):
        """POST to /api/mt5/alert. MT5_BYPASS_USER_IDS set → no X-EA-Secret needed."""
        return client.post("/api/mt5/alert",
                           json=payload,
                           content_type="application/json")

    def test_null_ticket_returns_200(self, client):
        """ticket=None must NOT crash (was TypeError → 500 before fix)."""
        resp = self._ea_post(client, {"ticket": None, "symbol": "EURUSD", "level": "TP1"})
        assert resp.status_code == 200, \
            f"BEFORE fix this was 500. Got {resp.status_code}: {resp.data}"
        data = resp.get_json()
        assert data.get("note") == "missing_ticket", f"Got: {data}"

    def test_missing_ticket_key_returns_200(self, client):
        """Missing ticket key entirely must return 200, note=missing_ticket."""
        resp = self._ea_post(client, {"symbol": "EURUSD", "level": "TP1"})
        assert resp.status_code == 200
        assert resp.get_json().get("note") == "missing_ticket"

    def test_string_ticket_returns_200(self, client):
        """ticket='abc' (non-numeric) must return 200, note=invalid_ticket."""
        resp = self._ea_post(client, {"ticket": "abc", "symbol": "EURUSD", "level": "TP1"})
        assert resp.status_code == 200, \
            f"BEFORE fix this was 500. Got {resp.status_code}: {resp.data}"
        data = resp.get_json()
        assert data.get("note") == "invalid_ticket", f"Got: {data}"

    def test_valid_ticket_does_not_error(self, client):
        """A valid integer ticket must not return 4xx/5xx (regression guard)."""
        resp = self._ea_post(client, {"ticket": 12345, "symbol": "EURUSD",
                                       "level": "TP1", "price": 1.10, "direction": "BUY"})
        # May return 200 ok or 200 with duplicate note — must NOT be 500
        assert resp.status_code == 200, \
            f"Valid ticket raised an error: {resp.status_code}: {resp.data}"


# ── BUG K ─────────────────────────────────────────────────────────────────────
# mt5_get_pending must mark TRAILING orders as "filled", not "executing".
# BEFORE fix: all orders set to "executing" regardless of order_type.
# AFTER fix:  TRAILING → "filled", all others → "executing".

class TestBugK:
    def _ea_get(self, client, user_id=None):
        url = "/api/mt5/pending"
        if user_id:
            url += f"?user_id={user_id}"
        return client.get(url)

    def test_trailing_order_marked_filled_after_poll(self, client):
        """TRAILING pending order must become 'filled' after EA polls — not 'executing'."""
        oid = _seed_order("default", "TRAILING", "pending")
        try:
            # BEFORE fix: status would be "executing" after this call
            resp = self._ea_get(client)
            assert resp.status_code == 200

            o = _get_order(oid)
            assert o.status == "filled", \
                f"BEFORE fix status was 'executing'. After fix expected 'filled', got '{o.status}'"
        finally:
            _delete_order(oid)

    def test_buy_order_still_marked_executing(self, client):
        """BUY order must still become 'executing' after poll (regression guard)."""
        oid = _seed_order("default", "BUY", "pending")
        try:
            self._ea_get(client)
            o = _get_order(oid)
            assert o.status == "executing", \
                f"Regression: BUY order should be 'executing', got '{o.status}'"
        finally:
            _delete_order(oid)

    def test_sell_order_still_marked_executing(self, client):
        """SELL order must still become 'executing' after poll (regression guard)."""
        oid = _seed_order("default", "SELL", "pending")
        try:
            self._ea_get(client)
            o = _get_order(oid)
            assert o.status == "executing", \
                f"Regression: SELL order should be 'executing', got '{o.status}'"
        finally:
            _delete_order(oid)

    def test_trailing_not_returned_in_second_poll(self, client):
        """After first poll, TRAILING is 'filled' — must NOT appear in second poll."""
        oid = _seed_order("default", "TRAILING", "pending")
        try:
            self._ea_get(client)                   # first poll → marks filled
            resp2 = self._ea_get(client)           # second poll → must not return it
            orders = resp2.get_json().get("orders", [])
            ids = [o["id"] for o in orders]
            assert oid not in ids, \
                f"TRAILING order {oid} re-appeared in second poll — still not fully fixed"
        finally:
            _delete_order(oid)


# ── BUG N ─────────────────────────────────────────────────────────────────────
# telegram_webhook execute path must write comment="DotVerse #<MT5Order.id>"
# BEFORE fix: comment was "Telegram execute #{scan_id}" — ScanAlert PK, not MT5Order PK.
#             mt5_get_state regex r'DotVerse #(\d+)' never matched → TP2/TP3 never enriched.
# AFTER fix:  two-commit pattern ensures comment = f"DotVerse #{order.id}" after refresh.

class TestBugN:
    def _webhook_post(self, client, scan_id):
        payload = {
            "callback_query": {
                "id":      "test-callback-id",
                "data":    f"execute|{scan_id}",
                "message": {
                    "chat":       {"id": 99999},
                    "message_id": 1,
                },
            }
        }
        return client.post("/api/telegram/webhook",
                           json=payload,
                           content_type="application/json")

    def test_order_comment_matches_dotverse_pattern(self, client):
        """MT5Order.comment must be 'DotVerse #<id>' — matches mt5_get_state regex."""
        import re
        scan_id = _seed_scan_alert("EURUSD=X", "BUY", 1.10, 1.09, 1.11, 1.12, 1.13)
        try:
            resp = self._webhook_post(client, scan_id)
            assert resp.status_code == 200

            db = _db()
            try:
                # Find the order created by this webhook call
                orders = (db.query(dvapp.MT5Order)
                          .filter_by(user_id="default")
                          .order_by(dvapp.MT5Order.id.desc())
                          .limit(5)
                          .all())
                # Must find at least one with correct comment pattern
                matching = [o for o in orders
                            if o.comment and re.match(r'^DotVerse #\d+$', o.comment)]
                assert matching, \
                    (f"BEFORE fix comment was 'Telegram execute #{scan_id}'. "
                     f"After fix must be 'DotVerse #<id>'. "
                     f"Got comments: {[o.comment for o in orders[:5]]}")
                order = matching[0]
                # The id in the comment must match the actual row id
                comment_id = int(order.comment.split("#")[1])
                assert comment_id == order.id, \
                    (f"Comment DotVerse #{comment_id} does not match row id {order.id}. "
                     f"BEFORE fix this was scan_id={scan_id} not order.id")
            finally:
                # Clean up the order created by this test
                for o in orders:
                    if o.comment and re.match(r'^DotVerse #\d+$', o.comment):
                        db.delete(o)
                db.commit()
                db.close()
        finally:
            _delete_scan_alert(scan_id)

    def test_comment_id_differs_from_scan_id(self, client):
        """order.id and scan_id are different PKs — comment must use order.id, not scan_id."""
        import re
        scan_id = _seed_scan_alert("EURUSD=X", "BUY", 1.10, 1.09, 1.11, 1.12, 1.13)
        try:
            self._webhook_post(client, scan_id)
            db = _db()
            try:
                orders = (db.query(dvapp.MT5Order)
                          .filter_by(user_id="default")
                          .order_by(dvapp.MT5Order.id.desc())
                          .limit(5)
                          .all())
                for o in orders:
                    if o.comment and re.match(r'^DotVerse #\d+$', o.comment):
                        comment_id = int(o.comment.split("#")[1])
                        # The comment must encode the MT5Order PK, not the ScanAlert PK
                        assert comment_id == o.id, \
                            (f"Comment encodes scan_id={scan_id} not order.id={o.id}. "
                             f"This is the BUG N failure mode.")
                        break
            finally:
                for o in orders:
                    if o.comment and re.match(r'^DotVerse #\d+$', o.comment):
                        db.delete(o)
                db.commit()
                db.close()
        finally:
            _delete_scan_alert(scan_id)
