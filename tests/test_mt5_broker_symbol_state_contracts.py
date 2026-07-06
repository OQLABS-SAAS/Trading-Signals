from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app.py"


def _source():
    return APP.read_text()


def test_mt5_state_preserves_broker_symbol_inventory_for_today_gate():
    source = _source()

    assert "def _mt5_tradable_symbols_from_push(body, spreads, positions):" in source
    assert 'for key in ("tradable_symbols", "symbols", "market_watch", "symbol_specs")' in source
    assert 'for key in ("tradable_symbols", "symbols", "market_watch", "symbol_specs", "spread")' in source
    assert "tradable_symbols = _mt5_tradable_symbols_from_push(body, spreads, positions)" in source
    assert '"tradable_symbols": tradable_symbols' in source
    assert '"tradeable_symbols": tradable_symbols' in source
    assert '"symbol_specs":    body.get("symbol_specs", {})' in source
    assert '"tradable_symbols": sorted(_mt5_state_tradable_symbol_set(state))' in source
    assert '"tradeable_symbols": sorted(_mt5_state_tradable_symbol_set(state))' in source
    assert '"symbol_specs": state.get("symbol_specs", {})' in source
    assert '"execution_universe_ready": bool(_mt5_state_tradable_symbol_set(state))' in source
