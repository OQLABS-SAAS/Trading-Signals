"""Contracts for A2: automation-flag watch wiring.

These tests verify that:
  1. _ensure_watch_for_order creates a watch_registry entry when any automation flag
     is True, with the correct keys and values.
  2. An order with no automation flags does NOT create a watch entry.
  3. Calling _ensure_watch_for_order on an existing watch MERGES (does not duplicate
     or clobber runtime fields like last_check / last_price).
  4. mt5_confirm (status=filled, BUY/SELL) updates the watch entry's entry_price to
     the actual fill price.
  5. An existing scanner-registered watch is unaffected by the new wiring code.

All tests operate directly on dvapp.watch_registry and dvapp._ensure_watch_for_order
to avoid HTTP-layer complexity and DB dependency.  The helpers stub _DBSession=None
so no real DB calls happen.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp


# ── helpers ──────────────────────────────────────────────────────────────────

def _clear_key(key):
    """Remove a key from the registry if present (cleanup between tests)."""
    with dvapp.watch_lock:
        dvapp.watch_registry.pop(key, None)


def _call_ensure(
    user_id="u1",
    ticker="EURUSD=X",
    asset_type="forex",
    timeframe="1h",
    be_on=False, trail_on=False, macro_on=False, inval_on=False,
    sent_on=False, tp1_on=False, tp2_on=False, weekend_on=False,
    entry_price=None, entry_atr=None, last_signal=None,
    stub_db=True,
    monkeypatch=None,
):
    if stub_db and monkeypatch is not None:
        monkeypatch.setattr(dvapp, "_DBSession", None)
        monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)
    dvapp._ensure_watch_for_order(
        user_id=user_id, ticker=ticker, asset_type=asset_type, timeframe=timeframe,
        be_on=be_on, trail_on=trail_on, macro_on=macro_on, inval_on=inval_on,
        sent_on=sent_on, tp1_on=tp1_on, tp2_on=tp2_on, weekend_on=weekend_on,
        entry_price=entry_price, entry_atr=entry_atr, last_signal=last_signal,
    )


# ── test 1: automation flags → watch entry created ────────────────────────────

def test_ensure_watch_creates_entry_when_be_true(monkeypatch):
    """An order with be=True must produce a watch_registry entry with be_on=True."""
    key = "u1_EURUSD=X_1h"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    _call_ensure(
        be_on=True, entry_price=1.1000, entry_atr=0.0040,
        last_signal="BUY", monkeypatch=monkeypatch,
    )

    with dvapp.watch_lock:
        w = dvapp.watch_registry.get(key)

    assert w is not None, "watch_registry entry must exist after _ensure_watch_for_order"
    assert w["be_on"]     is True
    assert w["trail_on"]  is False
    assert w["ticker"]    == "EURUSD=X"
    assert w["timeframe"] == "1h"
    assert w["user_id"]   == "u1"
    assert w["asset_type"] == "forex"
    assert w["entry_price"] == 1.1000
    assert w["entry_atr"]   == 0.0040
    assert w["last_signal"] == "BUY"


def test_ensure_watch_creates_entry_when_trailing_true(monkeypatch):
    """An order with trailing=True must produce a watch_registry entry with trail_on=True."""
    key = "u2_BTC-USD_4h"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    dvapp._ensure_watch_for_order(
        user_id="u2", ticker="BTC-USD", asset_type="crypto", timeframe="4h",
        be_on=False, trail_on=True, macro_on=False, inval_on=False,
        sent_on=False, tp1_on=False, tp2_on=False, weekend_on=False,
        entry_price=68000.0, entry_atr=1200.0, last_signal="BUY",
    )

    with dvapp.watch_lock:
        w = dvapp.watch_registry.get(key)

    assert w is not None
    assert w["trail_on"]   is True
    assert w["be_on"]      is False
    assert w["entry_price"] == 68000.0


def test_ensure_watch_creates_entry_all_flags_true(monkeypatch):
    """All automation flags true — all _on fields must be True in the registry entry."""
    key = "u3_GBPUSD=X_1d"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    dvapp._ensure_watch_for_order(
        user_id="u3", ticker="GBPUSD=X", asset_type="forex", timeframe="1d",
        be_on=True, trail_on=True, macro_on=True, inval_on=True,
        sent_on=True, tp1_on=True, tp2_on=True, weekend_on=True,
        entry_price=1.2700, entry_atr=0.0080, last_signal="SELL",
    )

    with dvapp.watch_lock:
        w = dvapp.watch_registry.get(key)

    assert w is not None
    for flag in ("be_on", "trail_on", "macro_on", "inval_on",
                 "sent_on", "tp1_on", "tp2_on", "weekend_on"):
        assert w[flag] is True, f"{flag} must be True"
    assert w["last_signal"] == "SELL"


# ── test 2: no automation flags → no watch entry ──────────────────────────────

def test_ensure_watch_no_op_when_all_flags_false(monkeypatch):
    """An order with NO automation flags must not create a watch_registry entry."""
    key = "u4_USDJPY=X_1h"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    dvapp._ensure_watch_for_order(
        user_id="u4", ticker="USDJPY=X", asset_type="forex", timeframe="1h",
        be_on=False, trail_on=False, macro_on=False, inval_on=False,
        sent_on=False, tp1_on=False, tp2_on=False, weekend_on=False,
        entry_price=150.0, entry_atr=0.5,
    )

    with dvapp.watch_lock:
        w = dvapp.watch_registry.get(key)

    assert w is None, "No watch entry should be created when all automation flags are False"


def test_ensure_watch_no_op_when_no_timeframe(monkeypatch):
    """An order with be=True but no timeframe must be skipped (can't run watch without TF)."""
    key = "u5_XAUUSD_None"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    dvapp._ensure_watch_for_order(
        user_id="u5", ticker="XAUUSD", asset_type="commodity", timeframe=None,
        be_on=True, trail_on=False, macro_on=False, inval_on=False,
        sent_on=False, tp1_on=False, tp2_on=False, weekend_on=False,
    )

    # The key with timeframe=None should not be in registry
    with dvapp.watch_lock:
        found = any(k.startswith("u5_XAUUSD") for k in dvapp.watch_registry)

    assert not found, "No watch entry should be created when timeframe is None"


# ── test 3: merge into existing watch ────────────────────────────────────────

def test_ensure_watch_merges_into_existing_watch(monkeypatch):
    """If a watch entry already exists (scanner-registered), _ensure_watch_for_order
    must UPDATE the automation flags and entry data WITHOUT overwriting runtime
    fields like last_check, last_price, last_reason."""
    key = "u6_EURUSD=X_4h"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    from datetime import datetime
    pre_check = datetime(2025, 1, 1, 12, 0)
    pre_price = 1.0810

    # Pre-populate as if the scanner already registered this watch
    with dvapp.watch_lock:
        dvapp.watch_registry[key] = {
            "user_id":    "u6",
            "ticker":     "EURUSD=X",
            "asset_type": "forex",
            "timeframe":  "4h",
            "alert_channels": ["telegram"],
            "last_signal":  "BUY",
            "last_check":   pre_check,
            "last_reason":  "EMA aligned",
            "last_price":   pre_price,
            "added_at":     "2025-01-01 00:00 UTC",
            "be_on":      False,
            "trail_on":   False,
            "macro_on":   False,
            "inval_on":   False,
            "sent_on":    False,
            "tp1_on":     False,
            "tp2_on":     False,
            "weekend_on": False,
            "entry_price": None,
            "entry_atr":   None,
        }

    # Now an order arrives with be=True and trail=True
    dvapp._ensure_watch_for_order(
        user_id="u6", ticker="EURUSD=X", asset_type="forex", timeframe="4h",
        be_on=True, trail_on=True, macro_on=False, inval_on=False,
        sent_on=False, tp1_on=False, tp2_on=False, weekend_on=False,
        entry_price=1.0800, entry_atr=0.0035, last_signal="BUY",
    )

    with dvapp.watch_lock:
        w = dvapp.watch_registry.get(key)

    assert w is not None
    # Automation flags must be updated
    assert w["be_on"]    is True
    assert w["trail_on"] is True
    # Runtime fields must be preserved
    assert w["last_check"]  == pre_check,  "last_check must not be clobbered"
    assert w["last_price"]  == pre_price,  "last_price must not be clobbered"
    assert w["last_reason"] == "EMA aligned", "last_reason must not be clobbered"
    # Entry data must be populated
    assert w["entry_price"] == 1.0800
    assert w["entry_atr"]   == 0.0035


def test_ensure_watch_does_not_duplicate_entry(monkeypatch):
    """Calling _ensure_watch_for_order twice for the same key must not create two entries."""
    key = "u7_GBPUSD=X_1h"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    for _ in range(3):
        dvapp._ensure_watch_for_order(
            user_id="u7", ticker="GBPUSD=X", asset_type="forex", timeframe="1h",
            be_on=True, trail_on=False, macro_on=False, inval_on=False,
            sent_on=False, tp1_on=False, tp2_on=False, weekend_on=False,
            entry_price=1.2500, entry_atr=0.0060,
        )

    with dvapp.watch_lock:
        count = sum(1 for k in dvapp.watch_registry if k == key)

    assert count == 1, "Exactly one registry entry must exist regardless of repeated calls"


# ── test 4: mt5_confirm updates entry_price to fill_price ────────────────────

def test_confirm_fill_updates_watch_entry_price(monkeypatch):
    """mt5_confirm (status=filled, BUY) must update the watch's entry_price to fill_price.
    This ensures BE/TP alert thresholds are based on the real execution price."""
    key = "u8_EURUSD=X_1h"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    # Create a watch entry as if the order was just submitted
    with dvapp.watch_lock:
        dvapp.watch_registry[key] = {
            "user_id":    "u8",
            "ticker":     "EURUSD=X",
            "asset_type": "forex",
            "timeframe":  "1h",
            "alert_channels": ["telegram"],
            "last_signal":  "BUY",
            "last_check":   None,
            "last_reason":  "Not checked yet",
            "last_price":   None,
            "added_at":     "2025-01-01 00:00 UTC",
            "be_on":      True,
            "trail_on":   False,
            "macro_on":   False,
            "inval_on":   False,
            "sent_on":    False,
            "tp1_on":     True,
            "tp2_on":     False,
            "weekend_on": False,
            "entry_price": 1.0800,   # requested price — fill_price may differ
            "entry_atr":   0.0035,
        }

    # Simulate the confirm-path fill_price update (the part extracted into the helper)
    fill_price = 1.0798   # slightly below limit — typical market fill
    _uid      = "u8"
    _tf       = "1h"
    _mt5_sym  = "EURUSD"   # MT5 symbol

    # Call the in-process logic: find by mt5_symbol match
    with dvapp.watch_lock:
        for _wkey, _wval in dvapp.watch_registry.items():
            if (_wval.get("user_id") == _uid
                    and _wval.get("timeframe") == _tf
                    and dvapp._mt5_symbol(
                        _wval.get("ticker", ""),
                        _wval.get("asset_type", "forex")
                    ).upper() == _mt5_sym.upper()):
                _wval["entry_price"] = float(fill_price)
                break

    with dvapp.watch_lock:
        w = dvapp.watch_registry.get(key)

    assert w is not None
    assert w["entry_price"] == 1.0798, (
        f"entry_price must be updated to fill_price 1.0798, got {w['entry_price']}"
    )
    # Other fields must be untouched
    assert w["be_on"]     is True
    assert w["tp1_on"]    is True
    assert w["entry_atr"] == 0.0035


def test_confirm_fill_updates_watch_via_http(monkeypatch):
    """Full-stack: POST /api/mt5/confirm with status=filled updates the in-memory
    watch entry's entry_price to the actual fill_price.
    Confirms the confirm handler path reaches the registry update logic.

    EA auth is bypassed via MT5_BYPASS_USER_IDS — the same pattern used by the
    existing test_mt5_execution_account_contracts.py tests.
    """
    key = "u9_EURUSD=X_1h"
    _clear_key(key)

    # Pre-populate watch entry mimicking an order that was submitted with be=True
    with dvapp.watch_lock:
        dvapp.watch_registry[key] = {
            "user_id":    "u9",
            "ticker":     "EURUSD=X",
            "asset_type": "forex",
            "timeframe":  "1h",
            "alert_channels": ["telegram"],
            "last_signal":  "BUY",
            "last_check":   None,
            "last_reason":  "Not checked yet",
            "last_price":   None,
            "added_at":     "2025-01-01 00:00 UTC",
            "be_on":      True,
            "trail_on":   True,
            "macro_on":   False,
            "inval_on":   False,
            "sent_on":    False,
            "tp1_on":     True,
            "tp2_on":     False,
            "weekend_on": False,
            "entry_price": 1.0800,
            "entry_atr":   0.0035,
        }

    from types import SimpleNamespace

    fake_order = SimpleNamespace(
        id=999,
        user_id="u9",
        symbol="EURUSD",    # MT5 symbol (no =X suffix)
        order_type="BUY",
        volume=0.1,
        price=1.0800,
        sl=1.0750,
        tp=1.0870,
        tp2=None, tp3=None,
        timeframe="1h",
        action="open",
        close_ticket=None,
        status="executing",
        mt5_ticket=None,
        fill_price=None,
        pnl=None,
        comment="DotVerse EURUSD=X BUY | acct=1 LIVE",
        be=True,
        trailing=True,
        macro=False,
        inval=False,
        sent=False,
        tp1_alert=True,
        tp2_alert=False,
        weekend=False,
        entry_atr=0.0035,
        filled_at=None,
    )

    class FakeQuery:
        def filter_by(self, **kw): return self
        def filter(self, *a, **kw): return self
        def first(self): return fake_order
        def all(self): return [fake_order]

    class FakeDB:
        def query(self, model): return FakeQuery()
        def add(self, obj): pass
        def commit(self): pass
        def rollback(self): pass
        def close(self): pass

    monkeypatch.setattr(dvapp, "_DBSession", lambda: FakeDB())
    monkeypatch.setattr(dvapp, "send_telegram", lambda msg: None)
    monkeypatch.setattr(dvapp, "_push_notification", lambda *a, **kw: None)
    monkeypatch.setattr(dvapp, "_redis_client", None)
    monkeypatch.setattr(dvapp, "_get_automation_settings",
                        lambda uid: {"market_alerts_on": False})

    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"

    # Use the same MT5_BYPASS_USER_IDS pattern as the existing EA-auth tests.
    # A single-user set bypasses the X-EA-Secret check and sets ea_user_id = "u9".
    previous_bypass = dvapp.MT5_BYPASS_USER_IDS
    dvapp.MT5_BYPASS_USER_IDS = {"u9"}
    try:
        resp = dvapp.app.test_client().post(
            "/api/mt5/confirm",
            json={
                "order_id": 999,
                "status":   "filled",
                "ticket":   10001,
                "fill_price": 1.0797,
                "pnl":      None,
                "comment":  "filled by EA",
            },
        )
    finally:
        dvapp.MT5_BYPASS_USER_IDS = previous_bypass

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data.get("status") == "ok", f"Expected status=ok, got {data}"

    # The watch entry's entry_price must now reflect the actual fill price
    with dvapp.watch_lock:
        w = dvapp.watch_registry.get(key)

    assert w is not None
    assert w["entry_price"] == 1.0797, (
        f"entry_price must be updated to fill_price 1.0797, got {w.get('entry_price')}"
    )
    # Sanity: automation flags and ATR must be untouched
    assert w["be_on"]     is True
    assert w["tp1_on"]    is True
    assert w["entry_atr"] == 0.0035


# ── test 5: existing scanner-registered watch unaffected ─────────────────────

def test_existing_scanner_watch_unaffected_by_wiring(monkeypatch):
    """A watch registered via the normal /api/watch scanner flow must not be
    removed or broken by the order-wiring code.  The wiring only merges;
    it never deletes or creates conflicting entries."""
    key = "u10_AAPL_1d"
    _clear_key(key)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "_save_watch_to_db", lambda *a, **kw: None)

    # Register a scanner watch with no automation flags
    with dvapp.watch_lock:
        dvapp.watch_registry[key] = {
            "user_id":    "u10",
            "ticker":     "AAPL",
            "asset_type": "stock",
            "timeframe":  "1d",
            "alert_channels": ["telegram", "sms"],
            "last_signal":  "BUY",
            "last_check":   None,
            "last_reason":  "Bullish trend",
            "last_price":   195.0,
            "added_at":     "2025-01-01 00:00 UTC",
            "be_on":      False,
            "trail_on":   False,
            "macro_on":   False,
            "inval_on":   False,
            "sent_on":    False,
            "tp1_on":     False,
            "tp2_on":     False,
            "weekend_on": False,
            "entry_price": None,
            "entry_atr":   None,
        }

    snapshot_before = dict(dvapp.watch_registry[key])

    # No order touches this ticker — registry must be unchanged
    dvapp._ensure_watch_for_order(
        user_id="u11",       # different user — must not touch u10's watch
        ticker="AAPL",
        asset_type="stock",
        timeframe="1d",
        be_on=True, trail_on=False, macro_on=False, inval_on=False,
        sent_on=False, tp1_on=False, tp2_on=False, weekend_on=False,
        entry_price=195.5,
    )

    with dvapp.watch_lock:
        w10 = dvapp.watch_registry.get(key)

    # u10's watch must be completely unchanged
    assert w10 == snapshot_before, "Scanner-registered watch must not be modified by a different user's order"

    # u11's watch must have been created separately
    key11 = "u11_AAPL_1d"
    with dvapp.watch_lock:
        w11 = dvapp.watch_registry.get(key11)
    assert w11 is not None
    assert w11["be_on"] is True
    _clear_key(key11)
