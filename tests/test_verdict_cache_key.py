"""V-1: the verdict cache key must include direction + date so one user's BUY
verdict is never served to another user's SELL request on the same ticker/TF."""
from app import _verdict_dir_token, _verdict_cache_key


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
