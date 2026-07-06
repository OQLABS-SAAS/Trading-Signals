from pathlib import Path


EA = Path(__file__).resolve().parents[1] / "DotVerse_EA.mq5"


def _source():
    return EA.read_text()


def test_ea_pushes_market_watch_symbols_and_specs():
    source = _source()

    assert "void BuildMarketWatchJson(string &symbolsJson, string &spreadsJson, string &specsJson)" in source
    assert "SymbolsTotal(true)" in source
    assert "SymbolName(i, true)" in source
    assert "SYMBOL_SPREAD" in source
    assert "SYMBOL_VOLUME_MIN" in source
    assert "SYMBOL_VOLUME_STEP" in source
    assert "SYMBOL_TRADE_STOPS_LEVEL" in source
    assert '\\"symbols\\":%s' in source
    assert '\\"tradable_symbols\\":%s' in source
    assert '\\"spreads\\":%s' in source
    assert '\\"symbol_specs\\":%s' in source
    assert "BuildMarketWatchJson(symbolsJson, spreadsJson, specsJson);" in source


def test_ea_escapes_json_strings_in_push_payload():
    source = _source()

    assert "string JsonEscape(string value)" in source
    assert 'StringReplace(value, "\\\\", "\\\\\\\\");' in source
    assert 'StringReplace(value, "\\"", "\\\\\\"");' in source
    assert "JsonEscape(server)" in source
    assert "JsonEscape(company)" in source
    assert "JsonEscape(sym)" in source
    assert "JsonEscape(cmt)" in source
