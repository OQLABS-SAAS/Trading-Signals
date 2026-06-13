"""V-1: verdict context keys must include direction/date/user where needed."""
import json

import app as dvapp
from app import _verdict_dir_token, _verdict_cache_key, _verdict_cached_payload, _signal_ctx_cache_key


def test_direction_token_from_dict_and_str():
    assert _verdict_dir_token({"signal": "BUY"}) == "BUY"
    assert _verdict_dir_token({"signal": "SELL"}) == "SELL"
    assert _verdict_dir_token({"direction": "long"}) == "BUY"
    assert _verdict_dir_token({"action": "short"}) == "SELL"
    assert _verdict_dir_token("BUY") == "BUY"
    assert _verdict_dir_token(None) == "NA"
    assert _verdict_dir_token({}) == "NA"


def test_buy_and_sell_keys_differ_same_ticker_tf_date():
    k_buy = _verdict_cache_key("EURUSD", "4H", _verdict_dir_token({"signal": "BUY"}), "2026-06-09")
    k_sell = _verdict_cache_key("EURUSD", "4H", _verdict_dir_token({"signal": "SELL"}), "2026-06-09")
    assert k_buy != k_sell, "BUY and SELL must not collide on the same ticker/TF/date"
    assert "BUY" in k_buy and "SELL" in k_sell


def test_date_is_part_of_key():
    k_today = _verdict_cache_key("BTCUSD", "1d", "BUY", "2026-06-09")
    k_yest = _verdict_cache_key("BTCUSD", "1d", "BUY", "2026-06-08")
    assert k_today != k_yest, "a stale-date verdict must not be reused for a new date"


def test_tf_normalized_lowercase():
    assert _verdict_cache_key("AAPL", "4H", "BUY", "2026-06-09") == _verdict_cache_key("AAPL", "4h", "BUY", "2026-06-09")


class _FakeRedis:
    def __init__(self, values):
        self.values = values
        self.get_keys = []

    def get(self, key):
        self.get_keys.append(key)
        return self.values.get(key)


def test_verdict_cached_payload_does_not_fallback_to_opposite_direction(monkeypatch):
    sell_key = _verdict_cache_key("EURUSD", "1h", "SELL", "2026-06-13")
    fake = _FakeRedis({sell_key: json.dumps({"verdict": "SELL verdict"}).encode()})
    monkeypatch.setattr(dvapp, "_redis_client", fake)

    assert _verdict_cached_payload("EURUSD", "1h", "BUY", "2026-06-13") is None
    assert fake.get_keys == [_verdict_cache_key("EURUSD", "1h", "BUY", "2026-06-13")]


def test_verdict_cached_payload_does_not_fallback_to_stale_date(monkeypatch):
    stale_key = _verdict_cache_key("EURUSD", "1h", "BUY", "2026-06-13")
    fake = _FakeRedis({stale_key: json.dumps({"verdict": "old verdict"}).encode()})
    monkeypatch.setattr(dvapp, "_redis_client", fake)

    assert _verdict_cached_payload("EURUSD", "1h", "BUY", "2026-06-14") is None
    assert fake.get_keys == [_verdict_cache_key("EURUSD", "1h", "BUY", "2026-06-14")]


def test_signal_context_key_scopes_user_direction_and_date():
    key_a = _signal_ctx_cache_key("user-a", "EURUSD", "1H", "BUY", "2026-06-13")
    key_b = _signal_ctx_cache_key("user-b", "EURUSD", "1H", "BUY", "2026-06-13")
    key_sell = _signal_ctx_cache_key("user-a", "EURUSD", "1H", "SELL", "2026-06-13")
    key_next_day = _signal_ctx_cache_key("user-a", "EURUSD", "1H", "BUY", "2026-06-14")

    assert key_a != key_b
    assert key_a != key_sell
    assert key_a != key_next_day
