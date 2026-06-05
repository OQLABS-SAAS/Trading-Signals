from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app.py"


def _source():
    return APP.read_text()


def test_mt5_ea_auth_accepts_account_level_secret():
    source = _source()

    assert "def _lookup_user_by_mt5_secret(secret):" in source
    assert "db.query(UserSettings).filter(UserSettings.mt5_api_key_enc.isnot(None)).all()" in source
    assert "db.query(TradingAccount).filter(" in source
    assert "TradingAccount.ea_secret_enc.isnot(None)" in source
    assert "if _dec(account.ea_secret_enc) == secret:" in source
    assert "return str(account.user_id)" in source


def test_account_serializer_uses_default_mt5_fallback_state():
    source = _source()
    helper_start = source.index("def _account_to_dict(a):")
    helper_end = source.index("@app.route(\"/api/accounts\", methods=[\"GET\"])", helper_start)
    helper = source[helper_start:helper_end]

    assert "query_ids.append(\"default\")" in helper
    assert "live_states_for_query_ids(mt5_state, query_ids)" in helper
    assert "find_live_state_for_account(" in helper
    assert "serialize_trading_account(a, state)" in helper
