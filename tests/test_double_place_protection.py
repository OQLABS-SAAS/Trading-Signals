"""Double-place protection — 2026-06-10 hardening of the stale-order requeue.

The dangerous scenario this guards: the EA places a trade but its
/api/mt5/confirm callback is lost (network blip, redeploy). The old code
flipped the order back to 'pending' unconditionally and forever — the EA
would re-execute the same order every 3 minutes: unbounded duplicates.

New contract, verified here:
  1. RECONCILE: if EA telemetry shows a position tagged 'DotVerse #<id>',
     the order is marked filled from telemetry — never requeued.
  2. RETRY ONCE: with no telemetry match, a stale order is requeued exactly
     once (requeue_count 0 -> 1).
  3. FAIL SAFE: a second stall marks it failed with a check-your-terminal
     message — never a third placement attempt.
"""
import importlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app as dv


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *a, **k):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *a, **k):
        return _FakeQuery(self._rows)

    def rollback(self):
        pass


class _Order:
    def __init__(self, oid, user_id="42", requeue_count=0):
        self.id = oid
        self.user_id = user_id
        self.status = "executing"
        self.created_at = datetime.utcnow() - timedelta(seconds=600)
        self.requeue_count = requeue_count
        self.mt5_ticket = None
        self.fill_price = None
        self.comment = "DotVerse EURUSD BUY"
        self.account_id = 1
        self.order_type = "BUY"


def _with_state(positions):
    with dv.mt5_state_lock:
        dv.mt5_state["42"] = {
            "account": {},
            "positions": positions,
            "last_seen": datetime.utcnow().isoformat(),
        }


def _clear_state():
    with dv.mt5_state_lock:
        dv.mt5_state.pop("42", None)


def test_reconciles_filled_order_from_telemetry_instead_of_requeueing():
    order = _Order(901)
    _with_state([{"ticket": 555001, "symbol": "EURUSD", "comment": "DotVerse #901", "open_price": 1.1556}])
    try:
        dv._requeue_stale_executing_mt5_orders(_FakeDB([order]), ea_uid="42")
        assert order.status == "filled"
        assert order.mt5_ticket == 555001
        assert abs(order.fill_price - 1.1556) < 1e-9
        assert "reconciled from EA telemetry" in order.comment
    finally:
        _clear_state()


def test_requeues_exactly_once_when_no_telemetry_match():
    order = _Order(902, requeue_count=0)
    _clear_state()
    n = dv._requeue_stale_executing_mt5_orders(_FakeDB([order]), ea_uid="42")
    assert n == 1
    assert order.status == "pending"
    assert order.requeue_count == 1


def test_second_stall_fails_safe_never_third_attempt():
    order = _Order(903, requeue_count=1)
    _clear_state()
    n = dv._requeue_stale_executing_mt5_orders(_FakeDB([order]), ea_uid="42")
    assert n == 0
    assert order.status == "failed"
    assert "CHECK MT5 MANUALLY" in order.comment


def test_telemetry_lookup_checks_default_bucket_too():
    order = _Order(904, user_id="42")
    with dv.mt5_state_lock:
        dv.mt5_state.pop("42", None)
        dv.mt5_state["default"] = {
            "account": {},
            "positions": [{"ticket": 555002, "comment": "DotVerse #904", "open_price": 2.5}],
            "last_seen": datetime.utcnow().isoformat(),
        }
    try:
        dv._requeue_stale_executing_mt5_orders(_FakeDB([order]), ea_uid="42")
        assert order.status == "filled"
        assert order.mt5_ticket == 555002
    finally:
        with dv.mt5_state_lock:
            dv.mt5_state.pop("default", None)
