from datetime import date, datetime
from types import SimpleNamespace

from backend.app.agent.analytics import (
    build_daily_metrics_response,
    build_recomputed_daily_metric_rows,
    empty_agent_analytics,
    summarize_agent_analytics,
)


def test_empty_agent_analytics_matches_route_empty_state_contract():
    assert empty_agent_analytics() == {
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "be": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "total_pnl": 0,
        "avg_rr": 0,
        "sharpe_ratio": 0,
        "equity_curve": [],
    }


def test_summarize_agent_analytics_builds_kpis_and_equity_curve():
    trades = [
        SimpleNamespace(outcome="WIN", realized_pnl=300, rr_ratio=2.0),
        SimpleNamespace(outcome="LOSS", realized_pnl=-100, rr_ratio=1.0),
        SimpleNamespace(outcome="BE", realized_pnl=0, rr_ratio=None),
    ]
    daily_metrics = [
        SimpleNamespace(date=date(2026, 6, 3), pnl=150, starting_balance=10100, ending_balance=10200),
        SimpleNamespace(date=date(2026, 6, 1), pnl=100, starting_balance=10000, ending_balance=10100),
        SimpleNamespace(date=date(2026, 6, 2), pnl=-50, starting_balance=10100, ending_balance=10050),
    ]

    analytics = summarize_agent_analytics(trades, daily_metrics)

    assert analytics["total_trades"] == 3
    assert analytics["trade_count"] == 3
    assert analytics["wins"] == 1
    assert analytics["losses"] == 1
    assert analytics["be"] == 1
    assert analytics["win_rate"] == 33.3
    assert analytics["profit_factor"] == 3.0
    assert analytics["total_pnl"] == 200.0
    assert analytics["avg_rr"] == 1.5
    assert analytics["sharpe_ratio"] == 0.78
    assert analytics["opening_balance"] == 10000.0
    assert analytics["closing_balance"] == 10200.0
    assert analytics["total_return"] == 200.0
    assert analytics["total_return_pct"] == 2.0
    assert analytics["equity_curve"] == [
        {"date": "2026-06-01", "value": 100.0, "pnl": 100.0},
        {"date": "2026-06-02", "value": 101.0, "pnl": -50.0},
        {"date": "2026-06-03", "value": 100.5, "pnl": 150.0},
    ]


def test_build_daily_metrics_response_serializes_metrics():
    metrics = [
        SimpleNamespace(
            id=10,
            date=date(2026, 6, 5),
            starting_balance=10000,
            ending_balance=10100,
            pnl=100,
            trades_count=2,
            wins_count=1,
            losses_count=1,
            max_drawdown=2.5,
        )
    ]

    response = build_daily_metrics_response(7, "Alpha Trading", metrics)

    assert response == {
        "account_id": 7,
        "account_name": "Alpha Trading",
        "metrics": [
            {
                "id": 10,
                "date": "2026-06-05",
                "starting_balance": 10000,
                "ending_balance": 10100,
                "pnl": 100,
                "trades_count": 2,
                "wins_count": 1,
                "losses_count": 1,
                "max_drawdown": 2.5,
            }
        ],
    }


def test_build_recomputed_daily_metric_rows_groups_closed_trades_by_day():
    trades = [
        SimpleNamespace(exit_time=datetime(2026, 6, 5, 10), entry_time=None, realized_pnl=50.125, outcome="WIN"),
        SimpleNamespace(exit_time=None, entry_time=datetime(2026, 6, 5, 12), realized_pnl=-10, outcome="LOSS"),
        SimpleNamespace(exit_time=datetime(2026, 6, 6, 10), entry_time=None, realized_pnl=None, outcome="BE"),
        SimpleNamespace(exit_time=None, entry_time=None, realized_pnl=999, outcome="WIN"),
    ]

    rows = build_recomputed_daily_metric_rows(trades)

    assert rows == [
        {
            "date": date(2026, 6, 5),
            "pnl": 40.12,
            "trades_count": 2,
            "wins_count": 1,
            "losses_count": 1,
        },
        {
            "date": date(2026, 6, 6),
            "pnl": 0.0,
            "trades_count": 1,
            "wins_count": 0,
            "losses_count": 0,
        },
    ]
