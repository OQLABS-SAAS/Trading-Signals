"""MT5 order request normalization.

This module is framework-free by design. Flask routes should translate HTTP
request bodies into these immutable request objects before touching storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


BUY = "BUY"
SELL = "SELL"
VALID_DIRECTIONS = {BUY, SELL}


class OrderValidationError(ValueError):
    """Raised when an order request cannot be safely queued."""


@dataclass(frozen=True)
class MT5SubmitOrderRequest:
    ticker: str
    asset_type: str
    direction: str
    volume: float
    price: float
    sl: float | None
    tp: float | None
    tp2: float | None
    tp3: float | None
    timeframe: str | None
    entry_confluence: float | None
    entry_atr: float | None
    strategy_mode: str | None
    fib_trigger: float | None
    fib_move_sl_to: float | None
    trailing: bool
    be: bool
    macro: bool
    inval: bool
    sent: bool
    tp1_alert: bool
    tp2_alert: bool
    weekend: bool


@dataclass(frozen=True)
class BrokerOrderRequest:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    stop_loss: float | None
    take_profit: float | None
    timeframe: str | None
    order_type: str
    signal_id: str


def _body(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}


def _upper_text(value: Any) -> str:
    return str(value or "").upper().strip()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _parse_float(raw: Any, field: str, default: float | None = None) -> float | None:
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise OrderValidationError(f"{field} must be numeric") from exc


def _optional_float(payload: dict[str, Any], field: str, default: float | None = None) -> float | None:
    return _parse_float(payload.get(field), field, default)


def _volume_from_aliases(payload: dict[str, Any]) -> float:
    raw_volume = payload.get("volume")
    if raw_volume in (None, ""):
        raw_volume = payload.get("lots")
    try:
        return float(raw_volume)
    except (TypeError, ValueError):
        return 0.0


def normalize_mt5_submit_order(payload: dict[str, Any] | None) -> MT5SubmitOrderRequest:
    payload = _body(payload)
    ticker = _upper_text(payload.get("ticker"))
    asset_type = _text(payload.get("asset_type")) or "forex"
    direction = _upper_text(payload.get("direction"))
    volume = _volume_from_aliases(payload)

    price_raw = payload.get("price")
    if price_raw in (None, ""):
        price_raw = payload.get("entry")
    price = _parse_float(price_raw, "price/entry", 0.0) or 0.0

    sl = _optional_float(payload, "sl")
    tp = _optional_float(payload, "tp")
    if tp is None and payload.get("tp") in (None, ""):
        try:
            tp = _parse_float(payload.get("tp1"), "tp/tp1")
        except OrderValidationError as exc:
            raise OrderValidationError("tp/tp1 must be numeric") from exc
    tp2 = _optional_float(payload, "tp2")
    tp3 = _optional_float(payload, "tp3")
    entry_confluence = _optional_float(payload, "entry_confluence")
    entry_atr = _optional_float(payload, "entry_atr")
    strategy_mode = _text(payload.get("strategy_mode")) or None
    fib_trigger = _optional_float(payload, "fib_trigger")
    fib_move_sl_to = _optional_float(payload, "fib_move_sl_to")

    if not ticker or direction not in VALID_DIRECTIONS or volume <= 0:
        raise OrderValidationError("ticker, direction (BUY/SELL), and volume required")
    if strategy_mode and strategy_mode not in {"standard", "fixed_micro_lot", "fib_236"}:
        raise OrderValidationError("strategy_mode must be standard, fixed_micro_lot, or fib_236")
    if strategy_mode == "fib_236":
        if not (fib_trigger and fib_trigger > 0 and fib_move_sl_to and fib_move_sl_to > 0):
            raise OrderValidationError("fib_236 orders require fib_trigger and fib_move_sl_to")

    timeframe = _text(payload.get("timeframe")) or None
    return MT5SubmitOrderRequest(
        ticker=ticker,
        asset_type=asset_type,
        direction=direction,
        volume=volume,
        price=price,
        sl=sl,
        tp=tp,
        tp2=tp2,
        tp3=tp3,
        timeframe=timeframe,
        entry_confluence=entry_confluence,
        entry_atr=entry_atr,
        strategy_mode=strategy_mode,
        fib_trigger=fib_trigger,
        fib_move_sl_to=fib_move_sl_to,
        trailing=bool(payload.get("trailing", False)),
        be=bool(payload.get("be", False)),
        macro=bool(payload.get("macro", False)),
        inval=bool(payload.get("inval", False)),
        sent=bool(payload.get("sent", False)),
        tp1_alert=bool(payload.get("tp1_alert", False)),
        tp2_alert=bool(payload.get("tp2_alert", False)),
        weekend=bool(payload.get("weekend", False)),
    )


def normalize_broker_order(payload: dict[str, Any] | None) -> BrokerOrderRequest:
    payload = _body(payload)
    symbol = _upper_text(payload.get("symbol"))
    side = _upper_text(payload.get("side"))
    quantity = _parse_float(payload.get("quantity", 0.01), "quantity", 0.01) or 0.0
    entry_price = _parse_float(payload.get("entry_price", 0), "entry_price", 0.0) or 0.0
    stop_loss = _optional_float(payload, "stop_loss")
    take_profit = _optional_float(payload, "take_profit")

    if not symbol or side not in VALID_DIRECTIONS or quantity <= 0:
        raise OrderValidationError("symbol, side (BUY/SELL), and quantity required")

    return BrokerOrderRequest(
        symbol=symbol,
        side=side,
        quantity=quantity,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        timeframe=_text(payload.get("timeframe")) or None,
        order_type=_text(payload.get("order_type")) or "market",
        signal_id=_text(payload.get("signal_id")),
    )
