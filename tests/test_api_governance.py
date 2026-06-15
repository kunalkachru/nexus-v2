import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from server.app import app

@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as test_client:
        yield test_client

def test_get_governance_packet_requires_read_permission(client):
    """Getting governance packet should work for users with read permission"""
    response = client.get(
        "/api/v1/incidents/nexus-123/governance-packet",
        headers={
            "x-user-id": "user-alice",
            "x-tenant-id": "tenant-a",
            "x-roles": "guardian",
        },
    )
    # Should not get 403 Forbidden for governance read
    assert response.status_code != 403

def test_send_handoff_requires_capability(client):
    """Sending handoff should check send_handoff capability"""
    response = client.post(
        "/api/v1/incidents/nexus-123/handoff-send",
        headers={
            "x-user-id": "user-bob",
            "x-tenant-id": "tenant-a",
            "x-roles": "guardian",
        },
        json={"target": "engineering-team"},
    )
    # Guardian cannot send handoff (only operator, incident_manager, admin can)
    assert response.status_code == 403

def test_send_handoff_works_with_operator_role(client):
    """Operator should be able to send handoff"""
    response = client.post(
        "/api/v1/incidents/nexus-123/handoff-send",
        headers={
            "x-user-id": "user-charlie",
            "x-tenant-id": "tenant-a",
            "x-roles": "operator",
        },
        json={"target": "engineering-team"},
    )
    # Should not get 403 (may be other errors like incident not found, but not 403)
    assert response.status_code != 403
