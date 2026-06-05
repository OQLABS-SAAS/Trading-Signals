"""Agent analytics projection helpers."""

from __future__ import annotations

from typing import Any, Iterable


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def empty_agent_analytics() -> dict[str, Any]:
    return {
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


def serialize_daily_metric(metric: Any) -> dict[str, Any]:
    return {
        "id": _get(metric, "id"),
        "date": _get(metric, "date").isoformat(),
        "starting_balance": _get(metric, "starting_balance"),
        "ending_balance": _get(metric, "ending_balance"),
        "pnl": _get(metric, "pnl"),
        "trades_count": _get(metric, "trades_count"),
        "wins_count": _get(metric, "wins_count"),
        "losses_count": _get(metric, "losses_count"),
        "max_drawdown": _get(metric, "max_drawdown"),
    }


def build_daily_metrics_response(account_id: int, account_name: str, metrics: Iterable[Any]) -> dict[str, Any]:
    return {
        "account_id": account_id,
        "account_name": account_name,
        "metrics": [serialize_daily_metric(metric) for metric in metrics],
    }


def build_recomputed_daily_metric_rows(trades: Iterable[Any]) -> list[dict[str, Any]]:
    daily: dict[Any, dict[str, Any]] = {}
    for trade in trades:
        timestamp = _get(trade, "exit_time") or _get(trade, "entry_time")
        if not timestamp:
            continue
        date_key = timestamp.date()
        entry = daily.setdefault(date_key, {"trades": 0, "wins": 0, "losses": 0, "pnl": 0.0})
        entry["trades"] += 1
        entry["pnl"] += _to_float(_get(trade, "realized_pnl"), 0.0)
        if _get(trade, "outcome") == "WIN":
            entry["wins"] += 1
        elif _get(trade, "outcome") == "LOSS":
            entry["losses"] += 1

    return [
        {
            "date": date_key,
            "pnl": round(entry["pnl"], 2),
            "trades_count": entry["trades"],
            "wins_count": entry["wins"],
            "losses_count": entry["losses"],
        }
        for date_key, entry in sorted(daily.items())
    ]


def summarize_agent_analytics(trades: Iterable[Any], daily_metrics: Iterable[Any]) -> dict[str, Any]:
    trade_rows = list(trades)
    metric_rows = sorted(list(daily_metrics), key=lambda metric: _get(metric, "date"))
    total = len(trade_rows)
    wins = sum(1 for trade in trade_rows if _get(trade, "outcome") == "WIN")
    losses = sum(1 for trade in trade_rows if _get(trade, "outcome") == "LOSS")
    be = sum(1 for trade in trade_rows if _get(trade, "outcome") == "BE")
    win_rate = round(wins / total * 100, 1) if total > 0 else 0.0

    realized_pnl = [_to_float(_get(trade, "realized_pnl"), 0.0) for trade in trade_rows]
    gross_profit = sum(value for value in realized_pnl if value > 0)
    gross_loss = abs(sum(value for value in realized_pnl if value < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0

    total_pnl = round(sum(realized_pnl), 2)
    valid_rr = [
        _to_float(_get(trade, "rr_ratio"), 0.0)
        for trade in trade_rows
        if _to_float(_get(trade, "rr_ratio"), 0.0) > 0
    ]
    avg_rr = round(sum(valid_rr) / len(valid_rr), 2) if valid_rr else 0.0

    sharpe = 0.0
    if metric_rows:
        daily_pnl = [_to_float(_get(metric, "pnl"), 0.0) for metric in metric_rows]
        mean_pnl = sum(daily_pnl) / len(daily_pnl) if daily_pnl else 0
        variance = sum((value - mean_pnl) ** 2 for value in daily_pnl) / len(daily_pnl) if daily_pnl else 1
        std = variance ** 0.5
        sharpe = round(mean_pnl / std, 2) if std > 0 else 0.0

    equity_curve = []
    running = 100.0
    for metric in metric_rows:
        pnl = _to_float(_get(metric, "pnl"), 0.0)
        starting_balance = _to_float(_get(metric, "starting_balance"), 0.0)
        equity_curve.append({
            "date": _get(metric, "date").isoformat(),
            "value": round(running, 2),
            "pnl": round(pnl, 2),
        })
        if starting_balance > 0:
            running *= (1 + pnl / starting_balance)

    opening_balance = _to_float(_get(metric_rows[0], "starting_balance"), 0.0) if metric_rows else 0
    closing_balance = _to_float(_get(metric_rows[-1], "ending_balance"), 0.0) if metric_rows else 0
    total_return_pct = round(total_pnl / opening_balance * 100, 2) if opening_balance > 0 else 0

    return {
        "total_trades": total,
        "trade_count": total,
        "wins": wins,
        "losses": losses,
        "be": be,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_pnl": total_pnl,
        "avg_rr": avg_rr,
        "sharpe_ratio": sharpe,
        "opening_balance": round(opening_balance, 2),
        "closing_balance": round(closing_balance, 2),
        "total_return": round(total_pnl, 2),
        "total_return_pct": total_return_pct,
        "equity_curve": equity_curve,
    }
