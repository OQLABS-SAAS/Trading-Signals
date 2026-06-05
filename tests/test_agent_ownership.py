from types import SimpleNamespace

from backend.app.agent.ownership import SHARED_EA_ACCOUNT_ERROR, agent_account_mutation_error


def test_agent_account_mutation_error_blocks_shared_default_account_for_regular_user():
    account = SimpleNamespace(user_id="default")

    assert agent_account_mutation_error(account, "user-123") == SHARED_EA_ACCOUNT_ERROR


def test_agent_account_mutation_error_allows_owner_default_and_regular_accounts():
    assert agent_account_mutation_error(SimpleNamespace(user_id="default"), "default") is None
    assert agent_account_mutation_error(SimpleNamespace(user_id="user-123"), "user-123") is None
    assert agent_account_mutation_error(None, "user-123") is None
