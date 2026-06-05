import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.settings.profile_contracts import normalize_profile_update_payload  # noqa: E402


def test_normalize_profile_update_payload_trims_profile_fields():
    req = normalize_profile_update_payload(
        {"name": " Alice ", "old_password": " old-pass ", "new_password": " new-pass "}
    )

    assert req.name == "Alice"
    assert req.old_password == "old-pass"
    assert req.new_password == "new-pass"


def test_normalize_profile_update_payload_handles_missing_body():
    req = normalize_profile_update_payload(None)

    assert req.name == ""
    assert req.old_password == ""
    assert req.new_password == ""
