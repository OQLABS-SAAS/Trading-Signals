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
