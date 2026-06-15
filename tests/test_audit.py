import pytest
import asyncio
from uuid import uuid4
from server.audit import write_audit_log, get_audit_logs

def test_audit_event_includes_actor_context():
    """Audit events should record user_id, role, and tenant for governance traceability"""
    incident_id = f"nexus-test-{uuid4().hex[:8]}"
    event_payload = {
        "incident_id": incident_id,
        "action": "approve_runbook",
    }

    asyncio.run(write_audit_log(
        "governance_decision",
        "tenant-a",
        event_payload,
        actor_user_id="user-alice",
        actor_roles=["guardian"],
    ))

    logs = get_audit_logs(incident_id)
    assert len(logs) >= 1
    latest_log = logs[-1]
    assert latest_log["event_type"] == "governance_decision"
    assert latest_log["actor_user_id"] == "user-alice"
    assert latest_log["actor_roles"] == ["guardian"]
    assert latest_log["tenant_id"] == "tenant-a"
