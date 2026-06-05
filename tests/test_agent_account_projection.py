from datetime import datetime, timedelta
from types import SimpleNamespace

from backend.app.agent.account_projection import (
    find_live_state_for_account,
    is_live_state_connected,
    live_states_for_query_ids,
    normalize_leverage,
    project_agent_account,
    project_agent_portfolio,
    project_pending_mt5_account,
    summarize_agent_dashboard_accounts,
    summarize_agent_dashboard_trades,
)


def _account(**overrides):
    base = {
        "id": 1,
        "name": "Alpha Trading",
        "account_number": "123456",
        "account_type": "LIVE",
        "broker": "MetaTrader 5",
        "server": "Broker-Live",
        "currency": "USD",
        "status": "disconnected",
        "last_seen": None,
        "error_message": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_live_states_for_query_ids_keeps_only_states_with_account():
    state = {
        "user-a": {"account": {"login": "111"}},
        "user-b": {"positions": []},
        "user-c": {"account": None},
    }

    assert live_states_for_query_ids(state, ["user-a", "user-b", "missing", "user-c"]) == [
        {"account": {"login": "111"}}
    ]


def test_project_agent_account_overlays_live_mt5_state_by_account_number():
    now = datetime(2026, 6, 5, 12, 0, 0)
    live_state = {
        "account": {"login": "123456", "balance": 10000.25, "equity": 10020.5, "leverage": 500},
        "last_seen": (now - timedelta(seconds=10)).isoformat(),
    }

    projected = project_agent_account(_account(), [live_state], 2, now=now, today_pnl=25.5)

    assert projected["login"] == "123456"
    assert projected["account_number"] == "123456"
    assert projected["balance"] == 10000.25
    assert projected["equity"] == 10020.5
    assert projected["leverage"] == "1:500"
    assert projected["status"] == "online"
    assert projected["problem"] is None
    assert projected["today_pnl"] == 25.5


def test_project_agent_account_uses_single_live_state_fallback_for_one_account():
    now = datetime(2026, 6, 5, 12, 0, 0)
    live_state = {
        "account": {"login": "different-login", "balance": 5000, "equity": 4990, "leverage": "1:200"},
        "last_seen": (now - timedelta(seconds=5)).isoformat(),
    }

    projected = project_agent_account(_account(account_number="123456"), [live_state], 1, now=now)

    assert projected["balance"] == 5000
    assert projected["equity"] == 4990
    assert projected["status"] == "online"
    assert projected["leverage"] == "1:200"


def test_project_agent_account_prefers_fresh_single_account_state_over_stale_match():
    now = datetime(2026, 6, 5, 12, 0, 0)
    stale_matching_state = {
        "account": {"login": "123456", "balance": 100, "equity": 100},
        "last_seen": (now - timedelta(minutes=5)).isoformat(),
    }
    fresh_default_state = {
        "account": {"login": "different-login", "balance": 5000, "equity": 4990},
        "last_seen": (now - timedelta(seconds=5)).isoformat(),
    }

    projected = project_agent_account(
        _account(account_number="123456"),
        [stale_matching_state, fresh_default_state],
        1,
        now=now,
    )

    assert projected["balance"] == 5000
    assert projected["equity"] == 4990
    assert projected["status"] == "online"


def test_project_agent_account_does_not_cross_wire_multi_account_live_state():
    now = datetime(2026, 6, 5, 12, 0, 0)
    live_state = {
        "account": {"login": "999999", "balance": 5000, "equity": 4990},
        "last_seen": (now - timedelta(seconds=5)).isoformat(),
    }

    projected = project_agent_account(_account(status="warning"), [live_state], 2, now=now)

    assert projected["balance"] == 0.0
    assert projected["equity"] == 0.0
    assert projected["status"] == "warning"
    assert projected["problem"] == "Margin warning"


def test_project_pending_mt5_account_keeps_live_login_and_metrics():
    live_state = {
        "account": {
            "login": "777888",
            "balance": "2500.5",
            "equity": "2510.75",
            "server": "Broker-Demo",
            "currency": "EUR",
        },
        "positions": [{"ticket": 1}, {"ticket": 2}],
        "last_seen": datetime(2026, 6, 5, 12, 0, 0),
    }

    projected = project_pending_mt5_account(live_state)

    assert projected["id"] == "__pending__"
    assert projected["login"] == "777888"
    assert projected["account_number"] == "777888"
    assert projected["balance"] == 2500.5
    assert projected["equity"] == 2510.75
    assert projected["server"] == "Broker-Demo"
    assert projected["currency"] == "EUR"
    assert projected["open_positions"] == 2


def test_connection_and_leverage_helpers_are_stable():
    now = datetime(2026, 6, 5, 12, 0, 0)
    fresh = {"account": {"login": "1"}, "last_seen": (now - timedelta(seconds=44)).isoformat()}
    stale = {"account": {"login": "1"}, "last_seen": (now - timedelta(seconds=46)).isoformat()}

    assert is_live_state_connected(fresh, now=now) is True
    assert is_live_state_connected(stale, now=now) is False
    assert find_live_state_for_account("1", [fresh], 2) == fresh
    assert normalize_leverage(500) == "1:500"
    assert normalize_leverage("1:1000") == "1:1000"
    assert normalize_leverage(None) == "1:100"


def test_summarize_agent_dashboard_trades_counts_open_pnl_and_win_rate():
    open_trades = [
        SimpleNamespace(unrealized_pnl=10.125),
        SimpleNamespace(unrealized_pnl="-2.12"),
        SimpleNamespace(unrealized_pnl=None),
    ]
    closed_trades = [
        SimpleNamespace(outcome="WIN"),
        SimpleNamespace(outcome="LOSS"),
        SimpleNamespace(outcome="WIN"),
    ]

    summary = summarize_agent_dashboard_trades(open_trades, closed_trades)

    assert summary["total_open_positions"] == 3
    assert summary["unrealized_pnl"] == 8.0
    assert summary["total_closed_trades_90d"] == 3
    assert summary["win_rate_90d"] == 66.7


def test_summarize_agent_dashboard_accounts_splits_attention_and_totals():
    online = {"status": "online", "balance": 100, "equity": 105, "today_pnl": 5}
    warning = {"status": "warning", "balance": 50, "equity": 45, "today_pnl": -2}
    disconnected = {"status": "disconnected", "balance": None, "equity": "", "today_pnl": None}

    summary = summarize_agent_dashboard_accounts([online, warning, disconnected])

    assert summary["online_accounts"] == 1
    assert summary["total_balance"] == 150.0
    assert summary["total_equity"] == 150.0
    assert summary["today_pnl"] == 3.0
    assert summary["healthy"] == [online]
    assert summary["attention"] == [warning, disconnected]


def test_project_agent_portfolio_summarizes_accounts_and_open_trades():
    accounts = [
        SimpleNamespace(id=1, name="Alpha Trading", status="online"),
        SimpleNamespace(id=2, name="Beta", status="warning"),
    ]
    open_trades = [
        SimpleNamespace(account_id=1, symbol="EURUSD", unrealized_pnl="10.125"),
        SimpleNamespace(account_id=1, symbol="XAUUSD", unrealized_pnl=-2.12),
        SimpleNamespace(account_id=2, symbol="EURUSD", unrealized_pnl=None),
    ]

    portfolio = project_agent_portfolio(accounts, open_trades)

    assert portfolio["total_accounts"] == 2
    assert portfolio["total_open_positions"] == 3
    assert portfolio["total_unrealized_pnl"] == 8.0
    assert set(portfolio["unique_symbols"]) == {"EURUSD", "XAUUSD"}
    assert portfolio["accounts"] == [
        {
            "id": 1,
            "name": "Alpha Trading",
            "initials": "AT",
            "status": "online",
            "open_positions": 2,
            "unrealized_pnl": 8.0,
        },
        {
            "id": 2,
            "name": "Beta",
            "initials": "B",
            "status": "warning",
            "open_positions": 1,
            "unrealized_pnl": 0.0,
        },
    ]
