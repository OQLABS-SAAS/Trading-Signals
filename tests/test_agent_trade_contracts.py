import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.agent.trade_contracts import (  # noqa: E402
    AgentTradeValidationError,
    build_agent_trade_export_csv,
    calculate_realized_pnl,
    format_agent_position_duration,
    normalize_agent_position_query_params,
    normalize_agent_trade_create_payload,
    normalize_agent_trade_query_params,
    normalize_agent_trade_update_payload,
    project_agent_position,
    project_agent_trade_detail,
    project_agent_trade_history_item,
    serialize_agent_trade,
)


def test_normalize_agent_trade_create_payload_parses_manual_trade():
    now = datetime(2026, 6, 5, 12, 0, 0)
    req = normalize_agent_trade_create_payload(
        {
            "account_id": "7",
            "signal_id": 11,
            "symbol": " eurusd ",
            "side": "sell",
            "quantity": "0.5",
            "entry_price": "1.085",
            "stop_loss": "",
            "take_profit": "1.07",
            "notes": "Manual",
        },
        now=now,
    )

    assert req.account_id == 7
    assert req.symbol == "EURUSD"
    assert req.side == "SELL"
    assert req.quantity == 0.5
    assert req.stop_loss is None
    assert req.take_profit == 1.07
    assert req.entry_time == now


def test_normalize_agent_trade_create_payload_rejects_bad_inputs():
    for payload, expected in [
        ({"symbol": "EURUSD"}, "account_id is required"),
        ({"account_id": 7}, "symbol is required"),
        ({"account_id": 7, "symbol": "EURUSD", "side": "HOLD"}, "side must be BUY or SELL"),
        ({"account_id": 7, "symbol": "EURUSD", "quantity": "lots"}, "quantity must be a number"),
        ({"account_id": 7, "symbol": "EURUSD", "entry_time": "soon"}, "entry_time must be an ISO datetime"),
    ]:
        try:
            normalize_agent_trade_create_payload(payload)
        except AgentTradeValidationError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("invalid Agent trade create payload should fail")


def test_normalize_agent_trade_update_payload_validates_status_and_outcome():
    req = normalize_agent_trade_update_payload(
        {"exit_price": "1.09", "status": "closed", "outcome": "win", "stop_loss": None}
    )

    assert req.updates == {
        "exit_price": 1.09,
        "status": "CLOSED",
        "outcome": "WIN",
        "stop_loss": None,
    }

    for payload, expected in [
        ({"status": "DONE"}, "status must be OPEN or CLOSED"),
        ({"outcome": "SCRATCH"}, "outcome must be WIN, LOSS, or BE"),
        ({"exit_price": "market"}, "exit_price must be a number"),
    ]:
        try:
            normalize_agent_trade_update_payload(payload)
        except AgentTradeValidationError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("invalid Agent trade update payload should fail")


def test_calculate_realized_pnl_handles_buy_and_sell():
    assert calculate_realized_pnl(side="BUY", entry_price=100, exit_price=110, quantity=2) == 20
    assert calculate_realized_pnl(side="SELL", entry_price=100, exit_price=90, quantity=2) == 20
    assert calculate_realized_pnl(side="BUY", entry_price=100, exit_price=None, quantity=2) is None


def test_normalize_agent_trade_query_params_defaults_and_export_status():
    filters = normalize_agent_trade_query_params(
        {
            "account_id": "7",
            "symbol": "eur",
            "outcome": "win",
            "date_from": "2026-06-05T12:00:00",
            "limit": "25",
            "offset": "5",
        }
    )

    assert filters.account_id == 7
    assert filters.status == "CLOSED"
    assert filters.outcome == "WIN"
    assert filters.date_from == datetime(2026, 6, 5, 12, 0, 0)
    assert filters.limit == 25
    assert filters.offset == 5

    export_filters = normalize_agent_trade_query_params({}, default_status=None)
    assert export_filters.status is None


def test_normalize_agent_trade_query_params_rejects_bad_filters():
    for params, expected in [
        ({"limit": "0"}, "limit must be greater than 0"),
        ({"offset": "-1"}, "offset must be 0 or greater"),
        ({"account_id": "main"}, "account_id must be an integer"),
        ({"date_to": "tomorrow"}, "date_to must be an ISO datetime"),
    ]:
        try:
            normalize_agent_trade_query_params(params)
        except AgentTradeValidationError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("invalid Agent trade filters should fail")


def test_normalize_agent_position_query_params_rejects_bad_account_id():
    assert normalize_agent_position_query_params({"account_id": "7"}).account_id == 7

    try:
        normalize_agent_position_query_params({"account_id": "main"})
    except AgentTradeValidationError as exc:
        assert "account_id must be an integer" in str(exc)
    else:
        raise AssertionError("invalid Agent position account_id should fail")


def test_project_agent_position_preserves_frontend_fields():
    entry_time = datetime(2026, 6, 5, 10, 0, 0)
    now = datetime(2026, 6, 5, 12, 35, 0)
    trade = SimpleNamespace(
        id=1,
        uuid="abc",
        account_id=7,
        signal_id=None,
        symbol="EURUSD",
        side="BUY",
        quantity=1.0,
        entry_price=1.08,
        current_price=1.09,
        exit_price=None,
        stop_loss=1.07,
        take_profit=1.1,
        entry_time=entry_time,
        exit_time=None,
        realized_pnl=None,
        unrealized_pnl=12.5,
        rr_ratio=None,
        status="OPEN",
        outcome=None,
        notes="Manual",
        created_at=entry_time,
    )

    result = project_agent_position(trade, "Primary Account", now=now)

    assert result["account_name"] == "Primary Account"
    assert result["client_initials"] == "PA"
    assert result["entry"] == 1.08
    assert result["current"] == 1.09
    assert result["pnl"] == 12.5
    assert result["duration"] == "2h 35m"


def test_project_agent_trade_history_item_adds_account_and_display_date():
    entry_time = datetime(2026, 6, 5, 10, 0, 0)
    exit_time = datetime(2026, 6, 5, 12, 30, 0)
    trade = SimpleNamespace(
        id=1,
        uuid="abc",
        account_id=7,
        signal_id=None,
        symbol="EURUSD",
        side="BUY",
        quantity=1.0,
        entry_price=1.08,
        exit_price=1.09,
        stop_loss=1.07,
        take_profit=1.1,
        entry_time=entry_time,
        exit_time=exit_time,
        realized_pnl=25.0,
        unrealized_pnl=None,
        rr_ratio=2.0,
        status="CLOSED",
        outcome="WIN",
        notes="Manual",
        created_at=entry_time,
    )

    result = project_agent_trade_history_item(trade, "Primary Account")

    assert result["account_name"] == "Primary Account"
    assert result["client_name"] == "Primary Account"
    assert result["date"] == "2026-06-05 12:30"
    assert result["exit_time"] == "2026-06-05T12:30:00"


def test_project_agent_trade_detail_adds_account_name():
    trade = SimpleNamespace(
        id=1,
        uuid="abc",
        account_id=7,
        signal_id=None,
        symbol="EURUSD",
        side="BUY",
        quantity=1.0,
        entry_price=1.08,
        exit_price=None,
        stop_loss=None,
        take_profit=None,
        entry_time=None,
        exit_time=None,
        realized_pnl=None,
        unrealized_pnl=None,
        rr_ratio=None,
        status="OPEN",
        outcome=None,
        notes=None,
        created_at=None,
    )

    assert project_agent_trade_detail(trade, "")["account_name"] == "Unknown"


def test_build_agent_trade_export_csv_uses_stable_header_and_rows():
    entry_time = datetime(2026, 6, 5, 10, 0, 0)
    exit_time = datetime(2026, 6, 5, 12, 30, 0)
    trades = [
        SimpleNamespace(
            account_id=7,
            symbol="EURUSD",
            side="BUY",
            entry_price=1.08,
            exit_price=1.09,
            entry_time=entry_time,
            exit_time=exit_time,
            realized_pnl=25.126,
            rr_ratio=2.345,
            outcome="WIN",
            status="CLOSED",
        ),
        SimpleNamespace(
            account_id=8,
            symbol="XAUUSD",
            side="SELL",
            entry_price=2300,
            exit_price=None,
            entry_time=entry_time,
            exit_time=None,
            realized_pnl=None,
            rr_ratio=None,
            outcome=None,
            status="OPEN",
        ),
    ]

    csv_data = build_agent_trade_export_csv(trades, {7: "Primary Account"})

    assert csv_data.splitlines() == [
        "Date,Account,Symbol,Side,Entry,Exit,P&L,R:R,Outcome,Status",
        "2026-06-05 12:30,Primary Account,EURUSD,BUY,1.08,1.09,25.13,2.35,WIN,CLOSED",
        "2026-06-05 10:00,,XAUUSD,SELL,2300,,0.0,,,OPEN",
    ]


def test_format_agent_position_duration_handles_days_hours_and_minutes():
    start = datetime(2026, 6, 5, 10, 0, 0)

    assert format_agent_position_duration(start, datetime(2026, 6, 5, 10, 7, 0)) == "7m"
    assert format_agent_position_duration(start, datetime(2026, 6, 5, 13, 7, 0)) == "3h 7m"
    assert format_agent_position_duration(start, datetime(2026, 6, 6, 13, 7, 0)) == "1d 3h"


def test_serialize_agent_trade_formats_datetime_fields():
    created = datetime(2026, 6, 5, 12, 0, 0)
    trade = SimpleNamespace(
        id=1,
        uuid="abc",
        account_id=7,
        signal_id=None,
        symbol="EURUSD",
        side="BUY",
        quantity=1.0,
        entry_price=1.08,
        exit_price=None,
        stop_loss=1.07,
        take_profit=1.1,
        entry_time=created,
        exit_time=None,
        realized_pnl=None,
        unrealized_pnl=4.0,
        rr_ratio=None,
        status="OPEN",
        outcome=None,
        notes="Manual",
        created_at=created,
    )

    result = serialize_agent_trade(trade)

    assert result["entry_time"] == "2026-06-05T12:00:00"
    assert result["created_at"] == "2026-06-05T12:00:00"
    assert result["unrealized_pnl"] == 4.0
