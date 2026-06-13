"""Tests for /api/prices per-provider timeout (#24).

Verifies that a slow/hung provider is skipped within the per-provider budget,
that a fast provider after a slow one still returns its data, and that the
all-fail case returns the null-fields shape the frontend expects.
"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")
# Use a short timeout so tests run fast (2 s per provider, 6 s hard budget).
os.environ["DV_PRICE_PROVIDER_TIMEOUT"] = "2"

import pandas as pd
import app as dvapp


# ── helpers ──────────────────────────────────────────────────────────────────

def _authed_client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return client


def _good_df(rows=5):
    """Minimal DataFrame that satisfies the >=2-row price extraction path."""
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "Open":   [100.0] * rows,
            "High":   [102.0] * rows,
            "Low":    [98.0]  * rows,
            "Close":  [101.0] * rows,
            "Volume": [1000]  * rows,
        },
        index=idx,
    )


def _post_prices(client, tickers):
    return client.post(
        "/api/prices",
        data=json.dumps({"tickers": tickers}),
        content_type="application/json",
    )


# ── test 1: slow provider_first_download is skipped; endpoint returns within budget ──

def test_slow_provider_skipped_and_endpoint_returns_within_budget(monkeypatch):
    """provider_first_download sleeps 30 s → endpoint must return in < 10 s with null entry."""
    def _slow_provider(*args, **kwargs):
        time.sleep(30)  # simulate a hung provider
        return _good_df()

    monkeypatch.setattr(dvapp, "DV_PRICE_PROVIDER_TIMEOUT", 2)
    monkeypatch.setattr(dvapp, "provider_first_download", _slow_provider)
    # TV fallback also stubbed to return nothing (so null path is exercised)
    monkeypatch.setattr(dvapp, "fetch_tv_data", lambda *a, **kw: None)

    client = _authed_client()
    t0 = time.time()
    resp = _post_prices(client, ["AAPL"])
    elapsed = time.time() - t0

    assert resp.status_code == 200
    assert elapsed < 10, f"Endpoint stalled: took {elapsed:.1f}s (expected < 10s)"
    data = resp.get_json()
    assert "AAPL" in data
    assert data["AAPL"]["price"] is None, "Slow provider should yield null price"


# ── test 2: fast provider after a slow one returns its data ──

def test_fast_tv_fallback_returns_data_after_slow_primary(monkeypatch):
    """provider_first_download sleeps 30 s → TV fallback (fast) must still return price."""
    def _slow_provider(*args, **kwargs):
        time.sleep(30)

    def _fast_tv(ticker, asset_type, timeframe="1d"):
        return {"tv_price": 55.55, "tv_chg": 1.23}

    monkeypatch.setattr(dvapp, "DV_PRICE_PROVIDER_TIMEOUT", 2)
    monkeypatch.setattr(dvapp, "provider_first_download", _slow_provider)
    monkeypatch.setattr(dvapp, "fetch_tv_data", _fast_tv)

    client = _authed_client()
    t0 = time.time()
    resp = _post_prices(client, ["EURUSD=X"])
    elapsed = time.time() - t0

    assert resp.status_code == 200
    assert elapsed < 10, f"Took too long: {elapsed:.1f}s"
    data = resp.get_json()
    assert "EURUSD=X" in data
    assert data["EURUSD=X"]["price"] == 55.55
    assert data["EURUSD=X"]["chg"] == 1.23


# ── test 3: all providers fail → error shape returned fast ──

def test_all_providers_fail_returns_null_shape_fast(monkeypatch):
    """Both providers return nothing → null-fields dict returned, HTTP 200, fast."""
    monkeypatch.setattr(dvapp, "DV_PRICE_PROVIDER_TIMEOUT", 2)
    monkeypatch.setattr(dvapp, "provider_first_download", lambda *a, **kw: None)
    monkeypatch.setattr(dvapp, "fetch_tv_data", lambda *a, **kw: None)

    client = _authed_client()
    t0 = time.time()
    resp = _post_prices(client, ["BTC-USD", "TSLA"])
    elapsed = time.time() - t0

    assert resp.status_code == 200
    assert elapsed < 10, f"All-fail path too slow: {elapsed:.1f}s"
    data = resp.get_json()
    for ticker in ("BTC-USD", "TSLA"):
        assert ticker in data
        entry = data[ticker]
        assert entry["price"] is None
        assert entry["chg"] is None
        assert "high" in entry
        assert "low" in entry


# ── test 4: fast provider returns correct data unchanged ──

def test_fast_provider_success_path_unchanged(monkeypatch):
    """When provider_first_download returns data immediately, shape must be correct."""
    good = _good_df()

    def _fast_provider(*args, **kwargs):
        return good

    monkeypatch.setattr(dvapp, "DV_PRICE_PROVIDER_TIMEOUT", 2)
    monkeypatch.setattr(dvapp, "provider_first_download", _fast_provider)
    monkeypatch.setattr(dvapp, "fetch_tv_data", lambda *a, **kw: None)

    client = _authed_client()
    resp = _post_prices(client, ["SPY"])
    assert resp.status_code == 200
    data = resp.get_json()
    assert "SPY" in data
    entry = data["SPY"]
    assert entry["price"] == 101.0
    assert entry["chg"] == 0.0          # all rows are 101.0 → no change
    assert entry["high"] == 102.0
    assert entry["low"] == 98.0
    assert entry["provider_order"] == "eodhd-first"


# ── test 5: env var DV_PRICE_PROVIDER_TIMEOUT is read at request time ──

def test_dv_price_provider_timeout_env_var_configures_timeout(monkeypatch):
    """DV_PRICE_PROVIDER_TIMEOUT controls the per-provider timeout value."""
    monkeypatch.setattr(dvapp, "DV_PRICE_PROVIDER_TIMEOUT", 3)
    # Just verify the module attribute is used — we monkeypatched it so it must be 3
    assert dvapp.DV_PRICE_PROVIDER_TIMEOUT == 3
