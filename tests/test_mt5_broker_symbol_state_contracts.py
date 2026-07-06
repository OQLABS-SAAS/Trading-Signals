from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app.py"


def _source():
    return APP.read_text()


def test_mt5_state_preserves_broker_symbol_inventory_for_today_gate():
    source = _source()

    assert 'broker_symbols = body.get("symbols") or body.get("broker_symbols") or []' in source
    assert 'body.get("tradable_symbols")' in source
    assert 'body.get("tradeable_symbols")' in source
    assert 'symbol_specs = body.get("symbol_specs") or body.get("specs") or {}' in source
    assert '"symbols":        broker_symbols' in source
    assert '"tradable_symbols": tradable_symbols' in source
    assert '"tradeable_symbols": tradable_symbols' in source
    assert '"symbol_specs":   symbol_specs' in source
    assert '"execution_universe_ready": execution_universe_ready' in source
    assert '"symbols":     state.get("symbols", [])' in source
    assert '"symbol_specs": state.get("symbol_specs", {})' in source
