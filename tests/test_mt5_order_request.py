import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.mt5.order_request import (  # noqa: E402
    OrderValidationError,
    normalize_broker_order,
    normalize_mt5_submit_order,
)


def test_normalize_mt5_submit_order_accepts_frontend_aliases():
    order = normalize_mt5_submit_order(
        {
            "ticker": " eurusd ",
            "asset_type": "forex",
            "direction": "buy",
            "lots": "0.10",
            "entry": "1.1000",
            "sl": "1.0900",
            "tp1": "1.1200",
            "tp2": "1.1300",
            "timeframe": "1H",
            "entry_confluence": "0.77",
            "entry_atr": "0.004",
            "strategy_mode": "fib_236",
            "fib_trigger": "1.1150",
            "fib_move_sl_to": "1.1080",
            "trailing": True,
        }
    )

    assert order.ticker == "EURUSD"
    assert order.direction == "BUY"
    assert order.volume == 0.10
    assert order.price == 1.1000
    assert order.tp == 1.1200
    assert order.tp2 == 1.1300
    assert order.timeframe == "1H"
    assert order.entry_confluence == 0.77
    assert order.entry_atr == 0.004
    assert order.strategy_mode == "fib_236"
    assert order.fib_trigger == 1.1150
    assert order.fib_move_sl_to == 1.1080
    assert order.trailing is True


def test_normalize_mt5_submit_order_rejects_bad_numeric_aliases():
    try:
        normalize_mt5_submit_order({"ticker": "EURUSD", "direction": "BUY", "lots": 0.1, "tp1": "bad"})
    except OrderValidationError as exc:
        assert "tp/tp1 must be numeric" in str(exc)
    else:
        raise AssertionError("invalid tp1 should fail")


def test_normalize_broker_order_rejects_bad_or_zero_quantity():
    for quantity in ("bad", 0):
        try:
            normalize_broker_order({"symbol": "EURUSD", "side": "BUY", "quantity": quantity})
        except OrderValidationError as exc:
            assert "quantity" in str(exc)
        else:
            raise AssertionError("invalid quantity should fail")


def test_normalize_broker_order_parses_optional_prices():
    order = normalize_broker_order(
        {
            "symbol": " btc-usd ",
            "side": "sell",
            "quantity": "0.25",
            "entry_price": "68000",
            "stop_loss": "69000",
            "take_profit": "65000",
            "order_type": "limit",
            "signal_id": "sig-1",
        }
    )

    assert order.symbol == "BTC-USD"
    assert order.side == "SELL"
    assert order.quantity == 0.25
    assert order.entry_price == 68000
    assert order.stop_loss == 69000
    assert order.take_profit == 65000
    assert order.order_type == "limit"
    assert order.signal_id == "sig-1"
