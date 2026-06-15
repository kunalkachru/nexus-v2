import pytest
import asyncio
from server.audit import write_audit_log, get_audit_logs

def test_audit_event_includes_actor_context():
    """Audit events should record user_id, role, and tenant for governance traceability"""
    event_payload = {
        "incident_id": "nexus-123",
        "action": "approve_runbook",
    }

    asyncio.run(write_audit_log(
        "governance_decision",
        "tenant-a",
        event_payload,
        actor_user_id="user-alice",
        actor_roles=["guardian"],
    ))

    logs = get_audit_logs("nexus-123")
    assert len(logs) == 1
    assert logs[0]["event_type"] == "governance_decision"
    assert logs[0]["actor_user_id"] == "user-alice"
    assert logs[0]["actor_roles"] == ["guardian"]
    assert logs[0]["tenant_id"] == "tenant-a"
