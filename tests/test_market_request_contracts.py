import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.market.request_contracts import (  # noqa: E402
    MarketRequestValidationError,
    normalize_add_watch_payload,
    normalize_alert_test_payload,
    normalize_analyze_payload,
    normalize_live_price_query,
    normalize_markov_query,
    normalize_prices_payload,
    normalize_remove_watch_payload,
    normalize_scan_list_payload,
    normalize_screen_payload,
    normalize_simulate_payload,
)


def _normalise_ticker(ticker, asset_type):
    return f"{asset_type}:{ticker}"


def _is_forex_pair(ticker):
    return ticker == "GBPUSD"


def test_normalize_live_price_query_requires_and_normalizes_ticker():
    req = normalize_live_price_query(
        {"ticker": " eurusd ", "asset_type": " Forex "},
        normalise_ticker=_normalise_ticker,
    )

    assert req.ticker == "forex:EURUSD"
    assert req.asset_type == "forex"

    try:
        normalize_live_price_query({}, normalise_ticker=_normalise_ticker)
    except MarketRequestValidationError as exc:
        assert "ticker required" in str(exc)
    else:
        raise AssertionError("missing live-price ticker should fail")


def test_normalize_analyze_payload_defaults_timeframe_and_normalizes_ticker():
    req = normalize_analyze_payload(
        {"ticker": " aapl ", "asset_type": "stock", "timeframe": "9d"},
        valid_timeframes={"1d", "1h"},
        is_forex_pair=_is_forex_pair,
        normalise_ticker=_normalise_ticker,
    )

    assert req.ticker == "stock:AAPL"
    assert req.asset_type == "stock"
    assert req.timeframe == "1d"


def test_normalize_analyze_payload_upgrades_forex_pair():
    req = normalize_analyze_payload(
        {"ticker": "gbpusd", "asset_type": "crypto", "timeframe": "1h"},
        valid_timeframes={"1d", "1h"},
        is_forex_pair=_is_forex_pair,
        normalise_ticker=_normalise_ticker,
    )

    assert req.ticker == "forex:GBPUSD"
    assert req.asset_type == "forex"
    assert req.timeframe == "1h"


def test_normalize_analyze_payload_requires_ticker():
    try:
        normalize_analyze_payload(
            {},
            valid_timeframes={"1d"},
            is_forex_pair=_is_forex_pair,
            normalise_ticker=_normalise_ticker,
        )
    except MarketRequestValidationError as exc:
        assert "Ticker symbol is required" in str(exc)
    else:
        raise AssertionError("missing analyze ticker should fail")


def test_normalize_screen_payload_defaults_timeframe_and_requires_ticker():
    req = normalize_screen_payload(
        {"ticker": " msft ", "asset_type": "stock", "timeframe": "bad"},
        valid_timeframes={"1d", "1h"},
        normalise_ticker=_normalise_ticker,
    )

    assert req.ticker == "stock:MSFT"
    assert req.timeframe == "1d"

    try:
        normalize_screen_payload({}, valid_timeframes={"1d"}, normalise_ticker=_normalise_ticker)
    except MarketRequestValidationError as exc:
        assert "Ticker required" in str(exc)
    else:
        raise AssertionError("missing screen ticker should fail")


def test_normalize_add_watch_payload_extracts_channels_automation_and_levels():
    req = normalize_add_watch_payload(
        {
            "ticker": "btc-usd",
            "asset_type": "crypto",
            "timeframe": "4h",
            "alert_channels": ["telegram"],
            "current_signal": "",
            "automations": {"be": True, "trail": True, "tp1": True},
            "entry_price": "100.5",
            "entry_atr": "2.5",
        },
        valid_timeframes={"1d", "1h"},
        normalise_ticker=_normalise_ticker,
    )

    assert req.ticker == "crypto:BTC-USD"
    assert req.timeframe == "1d"
    assert req.alert_channels == ["telegram"]
    assert req.current_signal == "HOLD"
    assert req.automations.be_on is True
    assert req.automations.trail_on is True
    assert req.automations.tp1_on is True
    assert req.automations.tp2_on is False
    assert req.entry_price == 100.5
    assert req.entry_atr == 2.5


def test_normalize_add_watch_payload_defaults_bad_channels_and_levels():
    req = normalize_add_watch_payload(
        {"ticker": "aapl", "alert_channels": "sms", "entry_price": "market"},
        valid_timeframes={"1d"},
        normalise_ticker=_normalise_ticker,
    )

    assert req.alert_channels == ["sms"]
    assert req.entry_price is None
    assert req.entry_atr is None


def test_normalize_remove_watch_payload_uses_existing_error_text():
    req = normalize_remove_watch_payload(
        {"ticker": " aapl ", "asset_type": "stock", "timeframe": "1h"},
        normalise_ticker=_normalise_ticker,
    )

    assert req.ticker == "stock:AAPL"
    assert req.timeframe == "1h"

    try:
        normalize_remove_watch_payload({}, normalise_ticker=_normalise_ticker)
    except MarketRequestValidationError as exc:
        assert "ticker required" in str(exc)
    else:
        raise AssertionError("missing remove-watch ticker should fail")


def test_normalize_scan_list_payload_caps_tickers_and_defaults_timeframe():
    req = normalize_scan_list_payload(
        {"tickers": [f"t{i}" for i in range(20)], "asset_type": "forex", "timeframe": "bad"},
        valid_timeframes={"1h"},
    )

    assert req.tickers == [f"T{i}" for i in range(15)]
    assert req.asset_type == "forex"
    assert req.timeframe == "1h"


def test_normalize_simulate_payload_preserves_existing_defaults_and_fields():
    req = normalize_simulate_payload(
        {
            "ticker": " aapl ",
            "asset_type": "stock",
            "signal": "BUY",
            "price": None,
            "entry": 100,
            "stop_loss": 95,
            "tp1": 105,
            "tp2": 110,
            "tp3": 115,
            "narrative": "Setup",
            "timeframe": "1h",
        }
    )

    assert req.ticker == "AAPL"
    assert req.signal == "BUY"
    assert req.price == 0
    assert req.entry == 100
    assert req.timeframe == "1h"

    default_req = normalize_simulate_payload(None)
    assert default_req.ticker == ""
    assert default_req.asset_type == "stock"
    assert default_req.signal == "HOLD"
    assert default_req.timeframe == "1d"


def test_normalize_prices_payload_caps_tickers():
    req = normalize_prices_payload({"tickers": [f" T{i} " for i in range(45)]})

    assert req.tickers == [f"T{i}" for i in range(40)]
    assert normalize_prices_payload(None).tickers == []


def test_normalize_markov_query_defaults_and_parses_ints():
    req = normalize_markov_query({"ticker": " spy ", "asset_type": " Stock ", "days": "90", "lookback": "15"})

    assert req.ticker == "SPY"
    assert req.asset_type == "stock"
    assert req.days == 90
    assert req.lookback == 15

    default_req = normalize_markov_query(None)
    assert default_req.ticker == "SPY"
    assert default_req.asset_type == "stock"
    assert default_req.days == 365
    assert default_req.lookback == 20


def test_normalize_alert_test_payload_preserves_channels_default():
    assert normalize_alert_test_payload(None).channels == ["sms"]
    assert normalize_alert_test_payload({"channels": ["telegram", "sms"]}).channels == ["telegram", "sms"]
