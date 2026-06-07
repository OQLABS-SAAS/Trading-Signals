import os
import sys
from types import SimpleNamespace

import pandas as pd


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp


def _market_df(rows=60):
    dates = pd.date_range("2026-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(rows)],
            "High": [101.0 + i for i in range(rows)],
            "Low": [99.0 + i for i in range(rows)],
            "Close": [100.5 + i for i in range(rows)],
            "Volume": [1000 + i for i in range(rows)],
        },
        index=dates,
    )


def _authed_pro_client():
    dvapp.app.config["TESTING"] = True
    dvapp.app.config["SECRET_KEY"] = "test-secret-key-not-for-prod"
    client = dvapp.app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "testuser"
        sess["logged_in"] = True
        sess["user_tier"] = "pro"
    return client


def test_analyze_accepts_markov_payload_without_body_name_error(monkeypatch):
    calls = {}
    df = _market_df()

    def fake_get_analysis(*args, **kwargs):
        calls["use_markov"] = kwargs.get("use_markov")
        calls["markov_weight"] = kwargs.get("markov_weight")
        return {
            "signal": "HOLD",
            "confidence": "LOW",
            "confidence_label": "HYPOTHESIS",
            "summary": "Test analysis",
        }

    monkeypatch.setattr(dvapp, "_redis_client", None)
    monkeypatch.setattr(dvapp, "_DBSession", None)
    monkeypatch.setattr(dvapp, "fetch_tv_data", lambda *args, **kwargs: {"tv_price": 100.5, "tv_rsi": 55, "tv_mtf": {}})
    monkeypatch.setattr(dvapp, "provider_first_download", lambda *args, **kwargs: df)
    monkeypatch.setattr(dvapp, "_fill_date_grid", lambda frame, *args, **kwargs: frame)
    monkeypatch.setattr(
        dvapp,
        "calculate_indicators",
        lambda *args, **kwargs: {
            "price": 100.5,
            "rsi": 55,
            "ema_trend": "MIXED",
            "chart_prices": [100.0 + i for i in range(60)],
            "chart_highs": [101.0 + i for i in range(60)],
            "chart_lows": [99.0 + i for i in range(60)],
            "chart_rsi": [55.0 for _ in range(60)],
            "rsi_divergence": {"type": "none"},
        },
    )
    monkeypatch.setattr(dvapp, "calculate_win_rate", lambda *args, **kwargs: {"win_rate": None, "sample_size": 0})
    monkeypatch.setattr(dvapp, "get_analysis", fake_get_analysis)
    monkeypatch.setattr(dvapp, "detect_counter_trade", lambda *args, **kwargs: {})
    monkeypatch.setattr(dvapp, "_get_macro_context_inline", lambda *args, **kwargs: {"events": [], "warning": "", "has_high_impact": False})
    monkeypatch.setattr(dvapp, "_fetch_news_sentiment", lambda *args, **kwargs: None)

    resp = _authed_pro_client().post(
        "/api/analyze",
        json={
            "ticker": "AAPL",
            "asset_type": "stock",
            "timeframe": "1h",
            "use_markov": True,
            "markov_weight": 0.42,
        },
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert calls == {"use_markov": True, "markov_weight": 0.42}


def test_scan_list_and_prices_routes_use_provider_first_without_external_services(monkeypatch):
    calls = {"provider": []}
    df = _market_df()

    def fake_provider(ticker, *args, **kwargs):
        calls["provider"].append((ticker, kwargs.get("asset_type")))
        return df.copy()

    monkeypatch.setattr(dvapp, "_redis_client", None)
    monkeypatch.setattr(dvapp, "provider_first_download", fake_provider)
    monkeypatch.setattr(dvapp, "fetch_tv_data", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dvapp,
        "calculate_indicators",
        lambda *args, **kwargs: {
            "price": 100.5,
            "chg_1d": 1.2,
            "rsi": 55,
            "vol_ratio": 1.1,
            "ema_trend": "MIXED",
            "supertrend": "NEUTRAL",
        },
    )
    monkeypatch.setattr(
        dvapp,
        "get_analysis",
        lambda *args, **kwargs: {
            "signal": "BUY",
            "entry": 100,
            "stop_loss": 95,
            "tp1": 110,
            "summary": "Test setup",
            "confidence": "MEDIUM",
            "confidence_label": "LIKELY",
        },
    )
    monkeypatch.setattr(dvapp, "detect_counter_trade", lambda *args, **kwargs: {"counter_trade": False})
    monkeypatch.setattr(dvapp, "calculate_win_rate", lambda *args, **kwargs: {"win_rate": 60, "sample_size": 40})

    client = _authed_pro_client()
    scan = client.post("/api/scan-list", json={"tickers": ["eurusd"], "asset_type": "fx", "timeframe": "1h"})
    prices = client.post("/api/prices", json={"tickers": ["AAPL"]})

    assert scan.status_code == 200, scan.get_data(as_text=True)
    scan_data = scan.get_json()
    assert scan_data["count"] == 1
    assert scan_data["results"][0]["asset_type"] == "forex"
    assert scan_data["results"][0]["signal"] == "BUY"
    assert prices.status_code == 200, prices.get_data(as_text=True)
    price_data = prices.get_json()
    assert price_data.get("AAPL", {}).get("provider_order") == "eodhd-first", (price_data, calls)
    assert ("EURUSD=X", "forex") in calls["provider"]
    assert ("AAPL", "stock") in calls["provider"]


def test_provider_first_preserves_monthly_interval_for_mtf_trend(monkeypatch):
    calls = []

    monkeypatch.setattr(dvapp, "cache_get", lambda _key: None)
    monkeypatch.setattr(dvapp, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dvapp, "fetch_chart_direct", lambda ticker, asset_type, timeframe: calls.append((ticker, asset_type, timeframe)) or None)
    monkeypatch.setattr(dvapp, "safe_download", lambda *args, **kwargs: pd.DataFrame())

    dvapp.provider_first_download("AAPL", period="10y", interval="1mo", asset_type="stock")

    assert calls == [("AAPL", "stock", "1mo")]


def test_mt5_state_route_projects_demo_live_mode_from_ea_state():
    user_id = "testuser"
    with dvapp.mt5_state_lock:
        previous = dvapp.mt5_state.get(user_id)
        dvapp.mt5_state[user_id] = {
            "account": {"login": "123456", "trade_mode": 2, "server": "Broker-Live"},
            "positions": [],
            "last_seen": dvapp.datetime.utcnow().isoformat(),
            "level_hits": {},
        }
    try:
        resp = _authed_pro_client().get("/api/mt5/state")
        assert resp.status_code == 200, resp.get_data(as_text=True)
        data = resp.get_json()
        assert data["connected"] is True
        assert data["account_type"] == "LIVE"
        assert data["is_live"] is True
        assert data["is_demo"] is False
        assert data["account"]["account_mode_source"] == "mt5"
    finally:
        with dvapp.mt5_state_lock:
            if previous is None:
                dvapp.mt5_state.pop(user_id, None)
            else:
                dvapp.mt5_state[user_id] = previous


class _FakeRedis:
    def __init__(self):
        self.get_keys = []
        self.values = {
            "verdict:EURUSD:1h": b'{"verdict":"1H verdict text","ticker":"EURUSD","timeframe":"1h"}',
        }

    def get(self, key):
        self.get_keys.append(key)
        return self.values.get(key)


def test_verdict_chat_uses_requested_timeframe_cache(monkeypatch):
    fake_redis = _FakeRedis()
    captured = {}

    class _FakeCompletions:
        def create(self, **kwargs):
            captured["messages"] = kwargs["messages"]
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Use the 1H verdict."))]
            )

    class _FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(dvapp, "_redis_client", fake_redis)
    monkeypatch.setattr(dvapp, "_rq_queue", None)
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))

    resp = _authed_pro_client().post(
        "/api/verdict/chat",
        json={"ticker": "EURUSD", "timeframe": "1h", "question": "What should I do?"},
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["answer"] == "Use the 1H verdict."
    assert fake_redis.get_keys[0] == "verdict:EURUSD:1h"
    assert "verdict:EURUSD:4h" not in fake_redis.get_keys
    assert "1H verdict text" in captured["messages"][1]["content"]
