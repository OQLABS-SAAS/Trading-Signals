from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


def _source():
    return APP.read_text()


def _function_block(source, name, next_marker):
    start = source.index(f"def {name}")
    end = source.index(next_marker, start)
    return source[start:end]


def test_private_app_has_shared_mt5_workspace_switch():
    source = _source()
    block = _function_block(source, "_private_app_shared_mt5_enabled", "def _agent_user_ids")
    assert "DOTVERSE_PRIVATE_APP_SHARED_MT5" in block
    assert '"1"' in block
    assert "false" in block


def test_operator_mt5_state_falls_back_to_single_fresh_shared_connection():
    source = _source()
    helper = _function_block(source, "_mt5_state_for_user", "def _primary_shared_mt5_state_locked")
    shared = _function_block(source, "_primary_shared_mt5_state_locked", "def _mt5_state_for_account")
    state_endpoint = source[source.index("def mt5_get_state") : source.index("@app.route(\"/api/mt5/orders\"", source.index("def mt5_get_state"))]

    assert "_primary_shared_mt5_state_locked()" in helper
    assert "len(connected) == 1" in shared
    assert "If multiple terminals" in shared
    assert "state = _mt5_state_for_user(user_id)" in state_endpoint
    assert "mt5_state.get(user_id) or mt5_state.get(\"default\")" not in state_endpoint


def test_private_app_account_list_includes_shared_mt5_accounts():
    source = _source()
    accounts_list = source[source.index("def accounts_list") : source.index("@app.route(\"/api/accounts\"", source.index("def accounts_list") + 1)]
    summary = source[source.index("def accounts_summary") : source.index("# ═══════════════════════════════════════════════════════════════", source.index("def accounts_summary"))]

    assert "TradingAccount.is_active == True" in accounts_list
    assert "if not _private_app_shared_mt5_enabled()" in accounts_list
    assert "TradingAccount.user_id == user_id" in accounts_list
    assert "if not _private_app_shared_mt5_enabled()" in summary


def test_operator_order_uses_selected_mt5_account_owner_for_ea_polling():
    source = _source()
    resolver = source[source.index("def _resolve_selected_mt5_account") : source.index("def _require_ea", source.index("def _resolve_selected_mt5_account"))]
    submit = source[source.index("def mt5_submit_order") : source.index("@app.route(\"/api/mt5/orders\"", source.index("def mt5_submit_order"))]

    assert "if not _private_app_shared_mt5_enabled()" in resolver
    assert "TradingAccount.id == int(live_state_account_id)" in resolver
    assert "execution_user_id = str(getattr(account, \"user_id\", None) or user_id)" in submit
    assert "_assert_mt5_account_ready_for_order(\n            execution_user_id" in submit
    assert "_find_recent_duplicate_mt5_order(\n            db,\n            execution_user_id" in submit
    assert "user_id          = execution_user_id" in submit
    assert "user_id     = execution_user_id" in submit
