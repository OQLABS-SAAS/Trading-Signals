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

    def fake_provider_download(*args, **kwargs):
        out = df.copy()
        out.attrs["dotverse_provider_trace"] = {
            "policy": "provider-first-v1",
            "provider_used": "EODHD",
            "attempted": ["EODHD"],
            "fallback_used": False,
            "last_error": None,
        }
        return out

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
    monkeypatch.setattr(dvapp, "provider_first_download", fake_provider_download)
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
    data = resp.get_json()
    assert data["provider_used"] == "EODHD"
    assert data["fallback_used"] is False
    assert data["provider_trace"]["attempted"] == ["EODHD"]


def test_markov_analysis_returns_ui_projection_fields(monkeypatch):
    class FakeMarkovEngine:
        def __init__(self, lookback=20):
            self.lookback = lookback

        def run(self, ticker, asset_type="stock", days=365, hmm_iterations=50):
            return {
                "ticker": ticker,
                "asset_type": asset_type,
                "state_labels": ["Bull", "Bear", "Sideways"],
                "state_counts": {"Bull": 7, "Bear": 2, "Sideways": 1},
                "transition_matrix": [
                    [0.6, 0.2, 0.2],
                    [0.3, 0.4, 0.3],
                    [0.5, 0.2, 0.3],
                ],
                "multi_day_forecast_5d": [
                    [0.55, 0.25, 0.2],
                    [0.35, 0.35, 0.3],
                    [0.45, 0.25, 0.3],
                ],
                "multi_day_forecast_10d": [
                    [0.52, 0.28, 0.2],
                    [0.38, 0.32, 0.3],
                    [0.42, 0.28, 0.3],
                ],
                "multi_day_forecast_20d": [
                    [0.5, 0.3, 0.2],
                    [0.4, 0.3, 0.3],
                    [0.4, 0.3, 0.3],
                ],
                "hmm_confirmation": {
                    "agreement_rate": 0.71,
                    "most_likely_regime_label": "Bull",
                },
            }

    monkeypatch.setattr(dvapp, "MarkovEngine", FakeMarkovEngine)

    resp = _authed_pro_client().get("/api/analysis/markov?ticker=AAPL&asset_type=stock")

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["bull_pct"] == 0.7
    assert data["bear_pct"] == 0.2
    assert data["current_state"] == "Bull"
    assert data["hmm_aligned"] is True
    assert data["p1_bull_pct"] == 0.6
    assert data["p5_bull_pct"] == 0.55
    assert data["p10_bull_pct"] == 0.52
    assert data["p20_bull_pct"] == 0.5


def test_scan_list_and_prices_routes_use_provider_first_without_external_services(monkeypatch):
    calls = {"provider": []}
    df = _market_df()

    def fake_provider(ticker, *args, **kwargs):
        calls["provider"].append((ticker, kwargs.get("asset_type")))
        out = df.copy()
        out.attrs["dotverse_provider_trace"] = {
            "policy": "provider-first-v1",
            "primary": "EODHD when configured",
            "fallbacks": ["Twelve Data", "Stooq", "FMP", "Yahoo v8", "safe_download"],
            "provider_used": "EODHD",
            "attempted": ["EODHD"],
            "fallback_used": False,
            "last_error": None,
        }
        return out

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


def test_signal_universe_run_projects_canonical_provider_first_contract(monkeypatch):
    calls = {"provider": []}
    df = _market_df()

    def fake_provider(ticker, *args, **kwargs):
        calls["provider"].append((ticker, kwargs.get("asset_type")))
        out = df.copy()
        out.attrs["dotverse_provider_trace"] = {
            "policy": "provider-first-v1",
            "primary": "EODHD when configured",
            "fallbacks": ["Twelve Data", "Stooq", "FMP", "Yahoo v8", "safe_download"],
            "provider_used": "EODHD",
            "attempted": ["EODHD"],
            "fallback_used": False,
            "last_error": None,
        }
        return out

    monkeypatch.setattr(dvapp, "_redis_client", None)
    monkeypatch.setattr(dvapp, "provider_first_download", fake_provider)
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

    resp = _authed_pro_client().post(
        "/api/signal-universe/run",
        json={"groups": [{"tickers": ["eurusd"], "asset_type": "fx", "tfs": ["1h"]}]},
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["ready"] is True
    assert data["run_id"].startswith("sigrun_")
    assert data["provider_policy_version"] == "provider-first-v1"
    assert data["request_count"] == 1
    assert data["scan_scope"] == [{"asset_type": "forex", "timeframe": "1h", "tickers": ["EURUSD"]}]
    assert data["count"] == 1
    assert data["results"] == data["candidates"]
    candidate = data["candidates"][0]
    assert data["provider_health"] == {
        "ready": True,
        "candidate_count": 1,
        "ready_count": 1,
        "failed_count": 0,
        "provider_counts": {"EODHD": 1},
        "fallback_count": 0,
        "latest_data_timestamp_utc": candidate["data_timestamp_utc"],
        "unique_errors": [],
        "provider_policy_version": "provider-first-v1",
    }
    assert candidate["candidate_id"] == "FOREX:EURUSD=X:1H:BUY"
    assert candidate["asset_type"] == "forex"
    assert candidate["signal"] == "BUY"
    assert candidate["provider_trace"]["policy"] == "provider-first-v1"
    assert candidate["provider_used"] == "EODHD"
    assert candidate["fallback_used"] is False
    assert candidate["provider_trace"]["attempted"] == ["EODHD"]
    assert candidate["data_timestamp_utc"]
    assert ("EURUSD=X", "forex") in calls["provider"]


def test_today_signal_universe_reuses_latest_complete_scan_cache(monkeypatch):
    calls = {"provider": 0}
    df = _market_df()

    def fake_provider(*args, **kwargs):
        calls["provider"] += 1
        out = df.copy()
        out.attrs["dotverse_provider_trace"] = {
            "policy": "provider-first-v1",
            "primary": "EODHD when configured",
            "fallbacks": ["Twelve Data", "Stooq", "FMP", "Yahoo v8", "safe_download"],
            "provider_used": "EODHD",
            "attempted": ["EODHD"],
            "fallback_used": False,
            "last_error": None,
        }
        return out

    monkeypatch.setattr(dvapp, "_redis_client", None)
    with dvapp._signal_universe_cache_lock:
        dvapp._signal_universe_cache.clear()
        dvapp._signal_universe_refreshing.clear()
    monkeypatch.setattr(dvapp, "provider_first_download", fake_provider)
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
    payload = {
        "scan_mode": "today",
        "groups": [{"tickers": ["eurusd"], "asset_type": "fx", "tfs": ["1h"]}],
        "force_refresh": True,
    }
    first = client.post("/api/signal-universe/run", json=payload)
    second_payload = {
        "scan_mode": "today",
        "groups": [{"tickers": ["eurusd"], "asset_type": "fx", "tfs": ["1h"]}],
    }
    second = client.post("/api/signal-universe/run", json=second_payload)

    assert first.status_code == 200, first.get_data(as_text=True)
    assert second.status_code == 200, second.get_data(as_text=True)
    first_data = first.get_json()
    second_data = second.get_json()
    assert first_data["ready"] is True
    assert first_data["cache_hit"] is False
    assert second_data["ready"] is True
    assert second_data["cache_hit"] is True
    assert second_data["results"] == first_data["results"]
    assert calls["provider"] == 1


def test_signal_universe_cache_serializes_provider_payloads_with_timestamps(monkeypatch):
    monkeypatch.setattr(dvapp, "_redis_client", None)
    with dvapp._signal_universe_cache_lock:
        dvapp._signal_universe_cache.clear()
        dvapp._signal_universe_refreshing.clear()

    payload = {
        "ready": True,
        "results": [{"symbol": "EURUSD", "data_timestamp_utc": pd.Timestamp("2026-07-07T10:00:00Z")}],
        "candidates": [{"symbol": "EURUSD", "data_timestamp_utc": pd.Timestamp("2026-07-07T10:00:00Z")}],
    }
    dvapp._signal_universe_cache_set("timestamp-test", payload)
    cached, age = dvapp._signal_universe_cache_get("timestamp-test")

    assert age is not None
    assert cached["ready"] is True
    assert isinstance(cached["results"][0]["data_timestamp_utc"], str)


def test_signal_universe_run_keeps_group_timeframe_scans_concurrent():
    source = open(dvapp.__file__).read()
    start = source.index('def signal_universe_run():')
    end = source.index('@app.route("/api/scan-list"', start)
    block = source[start:end]

    helper_start = source.index("def _collect_signal_universe_candidates(")
    helper_end = source.index("def _signal_universe_provider_health", helper_start)
    helper = source[helper_start:helper_end]

    assert "ThreadPoolExecutor(max_workers=max_workers)" in helper
    assert "max_workers = min(6, len(scan_requests))" in helper
    assert "as_completed(futures, timeout=scan_budget_seconds)" in helper
    assert "pool.shutdown(wait=not timed_out, cancel_futures=timed_out)" in helper


def test_today_signal_universe_prioritizes_fast_diverse_requests():
    requests = dvapp._signal_universe_requests({
        "scan_mode": "today",
        "groups": [
            {"asset_type": "crypto", "tickers": ["BTCUSD"], "tfs": ["15m", "30m", "1h"]},
            {"asset_type": "stock", "tickers": ["AMD"], "tfs": ["15m", "30m", "1h"]},
            {"asset_type": "forex", "tickers": ["EURUSD"], "tfs": ["15m", "30m", "1h"]},
        ],
    })

    first = [(r.asset_type, r.timeframe) for r in requests[:6]]
    assert first == [
        ("forex", "15m"),
        ("stock", "15m"),
        ("crypto", "15m"),
        ("forex", "30m"),
        ("stock", "30m"),
        ("crypto", "30m"),
    ]
    assert dvapp._signal_universe_scan_budget({"scan_mode": "standard"}) is None
    assert dvapp._signal_universe_scan_budget({"scan_mode": "today"}) is None
    assert dvapp._signal_universe_scan_budget({"scan_mode": "today", "max_seconds": 90}) == 30.0


def test_provider_first_preserves_monthly_interval_for_mtf_trend(monkeypatch):
    calls = []

    monkeypatch.setattr(dvapp, "cache_get", lambda _key: None)
    monkeypatch.setattr(dvapp, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        dvapp,
        "fetch_chart_direct_with_trace",
        lambda ticker, asset_type, timeframe: (calls.append((ticker, asset_type, timeframe)) or None, dvapp._provider_trace(None, [])),
    )
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
