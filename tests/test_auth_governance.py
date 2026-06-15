from server.auth import AuthenticatedContext, check_governance_capability

def test_guardian_can_approve_runbook():
    """Guardian role should have approve_action capability"""
    auth = AuthenticatedContext(
        user_id="user-alice",
        tenant_id="tenant-a",
        roles=["guardian"],
    )

    # Should not raise
    check_governance_capability(auth, "approve_action")

def test_operator_cannot_approve_runbook():
    """Operator role should not have approve_action capability"""
    auth = AuthenticatedContext(
        user_id="user-bob",
        tenant_id="tenant-a",
        roles=["operator"],
    )

    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc_info:
        check_governance_capability(auth, "approve_action")
    assert exc_info.value.status_code == 403

def test_admin_can_do_anything():
    """Admin role should have all capabilities"""
    auth = AuthenticatedContext(
        user_id="user-admin",
        tenant_id="tenant-a",
        roles=["admin"],
    )

    # All should pass
    check_governance_capability(auth, "approve_action")
    check_governance_capability(auth, "trigger_replay")
    check_governance_capability(auth, "send_handoff")
