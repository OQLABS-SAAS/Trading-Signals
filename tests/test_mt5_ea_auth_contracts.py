from pathlib import Path


APP = Path(__file__).resolve().parents[1] / "app.py"


def _source():
    return APP.read_text()


def test_mt5_ea_auth_accepts_account_level_secret():
    source = _source()

    assert "def _mt5_auth_context(user_id, account=None, scope=\"user\"):" in source
    assert "def _lookup_user_by_mt5_secret(secret):" in source
    assert "db.query(UserSettings).filter(UserSettings.mt5_api_key_enc.isnot(None)).all()" in source
    assert "db.query(TradingAccount).filter(" in source
    assert "TradingAccount.ea_secret_enc.isnot(None)" in source
    assert "if _dec(account.ea_secret_enc) == secret:" in source
    assert "return _mt5_auth_context(account.user_id, account=account)" in source
    assert "request.ea_account_id = auth_ctx.get(\"account_id\")" in source


def test_mt5_account_scoped_ea_routes_filter_pending_confirm_and_push_state():
    source = _source()

    pending_start = source.index("def mt5_get_pending():")
    pending_end = source.index("@app.route(\"/api/mt5/confirm\"", pending_start)
    pending = source[pending_start:pending_end]
    assert "ea_account_id = getattr(request, \"ea_account_id\", None)" in pending
    assert "orders = orders.filter(MT5Order.account_id == int(ea_account_id))" in pending

    confirm_start = source.index("def mt5_confirm_order():")
    confirm_end = source.index("@app.route(\"/api/mt5/alert\"", confirm_start)
    confirm = source[confirm_start:confirm_end]
    assert "ea_account_id = getattr(request, \"ea_account_id\", None)" in confirm
    assert "order_query = order_query.filter(MT5Order.account_id == int(ea_account_id))" in confirm
    assert "return jsonify({\"error\": \"conflicting MT5 confirmation for terminal order\"}), 409" in confirm

    push_start = source.index("def mt5_push_state():")
    push_end = source.index("@app.route(\"/api/mt5/state\"", push_start)
    push = source[push_start:push_end]
    assert "state_key = _mt5_state_key_for_account(ea_account_id) or str(user_id)" in push
    assert "if expected_login and pushed_login and expected_login != pushed_login:" in push
    assert "return jsonify({\"status\": \"stale\", \"ignored\": True}), 200" in push


def test_account_serializer_uses_default_mt5_fallback_state():
    source = _source()
    helper_start = source.index("def _account_to_dict(a):")
    helper_end = source.index("@app.route(\"/api/accounts\", methods=[\"GET\"])", helper_start)
    helper = source[helper_start:helper_end]

    assert "query_ids.append(\"default\")" in helper
    assert "live_states_for_query_ids(mt5_state, query_ids)" in helper
    assert "find_live_state_for_account(" in helper
    assert "serialize_trading_account(a, state)" in helper
