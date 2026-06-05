"""Market endpoint request contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Collection


class MarketRequestValidationError(ValueError):
    """Raised when a market endpoint request is invalid."""


@dataclass(frozen=True)
class LivePriceRequest:
    ticker: str
    asset_type: str


@dataclass(frozen=True)
class AnalyzeRequest:
    ticker: str
    asset_type: str
    timeframe: str


@dataclass(frozen=True)
class ScreenRequest:
    ticker: str
    asset_type: str
    timeframe: str


@dataclass(frozen=True)
class WatchAutomationFlags:
    be_on: bool = False
    trail_on: bool = False
    macro_on: bool = False
    inval_on: bool = False
    sent_on: bool = False
    tp1_on: bool = False
    tp2_on: bool = False
    weekend_on: bool = False


@dataclass(frozen=True)
class AddWatchRequest:
    ticker: str
    asset_type: str
    timeframe: str
    alert_channels: list[str]
    current_signal: str
    automations: WatchAutomationFlags
    entry_price: float | None
    entry_atr: float | None


@dataclass(frozen=True)
class RemoveWatchRequest:
    ticker: str
    asset_type: str
    timeframe: str


@dataclass(frozen=True)
class ScanListRequest:
    tickers: list[str]
    asset_type: str
    timeframe: str


@dataclass(frozen=True)
class SimulateRequest:
    ticker: str
    asset_type: Any
    signal: Any
    price: Any
    entry: Any
    stop_loss: Any
    tp1: Any
    tp2: Any
    tp3: Any
    narrative: Any
    timeframe: Any


@dataclass(frozen=True)
class PricesRequest:
    tickers: list[str]


@dataclass(frozen=True)
class MarkovRequest:
    ticker: str
    asset_type: str
    days: int
    lookback: int


@dataclass(frozen=True)
class AlertTestRequest:
    channels: Any


def _valid_timeframe(timeframe: str, valid_timeframes: Collection[str], fallback: str) -> str:
    return timeframe if timeframe in valid_timeframes else fallback


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _alert_channels(value: Any) -> list[str]:
    if isinstance(value, list) and value:
        return value
    return ["sms"]


def _automation_flags(value: Any) -> WatchAutomationFlags:
    flags = value if isinstance(value, dict) else {}
    return WatchAutomationFlags(
        be_on=bool(flags.get("be", False)),
        trail_on=bool(flags.get("trail", False)),
        macro_on=bool(flags.get("macro", False)),
        inval_on=bool(flags.get("inval", False)),
        sent_on=bool(flags.get("sent", False)),
        tp1_on=bool(flags.get("tp1", False)),
        tp2_on=bool(flags.get("tp2", False)),
        weekend_on=bool(flags.get("weekend", False)),
    )


def normalize_live_price_query(
    params: Any,
    *,
    normalise_ticker: Callable[[str, str], str],
) -> LivePriceRequest:
    ticker = str(params.get("ticker", "") if params else "").strip().upper()
    asset_type = str(params.get("asset_type", "stock") if params else "stock").strip().lower()
    if not ticker:
        raise MarketRequestValidationError("ticker required")
    return LivePriceRequest(ticker=normalise_ticker(ticker, asset_type), asset_type=asset_type)


def normalize_analyze_payload(
    payload: dict[str, Any] | None,
    *,
    valid_timeframes: Collection[str],
    is_forex_pair: Callable[[str], bool],
    normalise_ticker: Callable[[str, str], str],
) -> AnalyzeRequest:
    body = payload if isinstance(payload, dict) else {}
    ticker = str(body.get("ticker") or "").upper().strip()
    asset_type = body.get("asset_type", "stock")
    timeframe = str(body.get("timeframe", "1d")).lower()

    if not ticker:
        raise MarketRequestValidationError("Ticker symbol is required")
    if timeframe not in valid_timeframes:
        timeframe = "1d"

    forex_probe = ticker.replace("/", "").replace("-", "").replace("=X", "")
    if is_forex_pair(forex_probe) and asset_type != "forex":
        asset_type = "forex"

    return AnalyzeRequest(
        ticker=normalise_ticker(ticker, asset_type),
        asset_type=asset_type,
        timeframe=timeframe,
    )


def normalize_screen_payload(
    payload: dict[str, Any] | None,
    *,
    valid_timeframes: Collection[str],
    normalise_ticker: Callable[[str, str], str],
) -> ScreenRequest:
    body = payload if isinstance(payload, dict) else {}
    ticker = str(body.get("ticker") or "").upper().strip()
    asset_type = body.get("asset_type", "stock")
    timeframe = _valid_timeframe(str(body.get("timeframe", "1d")).lower(), valid_timeframes, "1d")
    if not ticker:
        raise MarketRequestValidationError("Ticker required")
    return ScreenRequest(
        ticker=normalise_ticker(ticker, asset_type),
        asset_type=asset_type,
        timeframe=timeframe,
    )


def normalize_add_watch_payload(
    payload: dict[str, Any] | None,
    *,
    valid_timeframes: Collection[str],
    normalise_ticker: Callable[[str, str], str],
) -> AddWatchRequest:
    body = payload if isinstance(payload, dict) else {}
    ticker = str(body.get("ticker") or "").upper().strip()
    asset_type = body.get("asset_type", "stock")
    timeframe = _valid_timeframe(str(body.get("timeframe", "1d")).lower(), valid_timeframes, "1d")
    if not ticker:
        raise MarketRequestValidationError("Ticker required")
    return AddWatchRequest(
        ticker=normalise_ticker(ticker, asset_type),
        asset_type=asset_type,
        timeframe=timeframe,
        alert_channels=_alert_channels(body.get("alert_channels", ["sms"])),
        current_signal=body.get("current_signal", "HOLD") or "HOLD",
        automations=_automation_flags(body.get("automations") or {}),
        entry_price=_optional_float(body.get("entry_price")),
        entry_atr=_optional_float(body.get("entry_atr")),
    )


def normalize_remove_watch_payload(
    payload: dict[str, Any] | None,
    *,
    normalise_ticker: Callable[[str, str], str],
) -> RemoveWatchRequest:
    body = payload if isinstance(payload, dict) else {}
    ticker = str(body.get("ticker") or "").upper().strip()
    timeframe = str(body.get("timeframe", "1d")).lower()
    asset_type = body.get("asset_type", "stock")
    if not ticker:
        raise MarketRequestValidationError("ticker required")
    return RemoveWatchRequest(
        ticker=normalise_ticker(ticker, asset_type),
        asset_type=asset_type,
        timeframe=timeframe,
    )


def normalize_scan_list_payload(
    payload: dict[str, Any] | None,
    *,
    valid_timeframes: Collection[str],
) -> ScanListRequest:
    body = payload if isinstance(payload, dict) else {}
    return ScanListRequest(
        tickers=[str(t).strip().upper() for t in body.get("tickers", [])[:15]],
        asset_type=body.get("asset_type", "crypto"),
        timeframe=_valid_timeframe(str(body.get("timeframe", "1h")).lower(), valid_timeframes, "1h"),
    )


def normalize_simulate_payload(payload: dict[str, Any] | None) -> SimulateRequest:
    body = payload if isinstance(payload, dict) else {}
    return SimulateRequest(
        ticker=str(body.get("ticker") or "").upper().strip(),
        asset_type=body.get("asset_type", "stock"),
        signal=body.get("signal", "HOLD"),
        price=body.get("price", 0) or 0,
        entry=body.get("entry"),
        stop_loss=body.get("stop_loss"),
        tp1=body.get("tp1"),
        tp2=body.get("tp2"),
        tp3=body.get("tp3"),
        narrative=body.get("narrative", ""),
        timeframe=body.get("timeframe", "1d"),
    )


def normalize_prices_payload(payload: dict[str, Any] | None) -> PricesRequest:
    body = payload if isinstance(payload, dict) else {}
    return PricesRequest(tickers=[str(t).strip() for t in body.get("tickers", [])[:40]])


def normalize_markov_query(params: Any) -> MarkovRequest:
    return MarkovRequest(
        ticker=str(params.get("ticker", "SPY") if params else "SPY").upper().strip(),
        asset_type=str(params.get("asset_type", "stock") if params else "stock").strip().lower(),
        days=int(params.get("days", "365") if params else "365"),
        lookback=int(params.get("lookback", "20") if params else "20"),
    )


def normalize_alert_test_payload(payload: dict[str, Any] | None) -> AlertTestRequest:
    body = payload if isinstance(payload, dict) else {}
    return AlertTestRequest(channels=body.get("channels", ["sms"]))
