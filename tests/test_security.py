import hashlib
import hmac
import json
import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.models import IncidentRecord


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_incident(client: TestClient) -> IncidentRecord:
    async def scenario() -> IncidentRecord:
        session = app.state.db_session_factory()
        try:
            return await session.incidents.create_incident(
                external_id="inc_secure",
                title="Secure incident",
                severity="P1",
                tenant_id="tenant-a",
            )
        finally:
            await session.close()

    return asyncio.run(scenario())


def test_incident_status_requires_authenticated_user(client: TestClient) -> None:
    response = client.get("/incidents/nxs_abc")

    assert response.status_code == 401


def test_tenant_cannot_read_other_tenant_incident(client: TestClient, auth_headers, seeded_incident: IncidentRecord) -> None:
    response = client.get(
        f"/incidents/{seeded_incident.nexus_incident_id}",
        headers=auth_headers(tenant_id="tenant-b"),
    )

    assert response.status_code == 403


def test_webhook_requires_valid_signature(client: TestClient) -> None:
    body = {
        "incident_id": "inc_xyz",
        "title": "Payment API timeout",
        "severity": "P1",
        "detected_at": "2026-05-25T14:32:00Z",
        "monitoring_source": "datadog",
        "metrics": {"service": "payment-svc", "error_rate": 0.45},
    }
    payload = json.dumps(body, separators=(",", ":"))

    missing_signature = client.post(
        "/webhooks/incident",
        headers={
            "x-tenant-id": "tenant-system",
            "content-type": "application/json",
        },
        content=payload,
    )
    # Missing signature header should return 401 (unauthorized)
    assert missing_signature.status_code == 401

    secret = app.state.config.webhook_signing_secret
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    missing_tenant = client.post(
        "/webhooks/incident",
        headers={
            "x-signature": f"sha256={digest}",
            "content-type": "application/json",
        },
        content=payload,
    )
    # Missing tenant header should return 403 (forbidden)
    assert missing_tenant.status_code == 403

    bad_signature = client.post(
        "/webhooks/incident",
        headers={
            "x-tenant-id": "tenant-system",
            "x-signature": "sha256=deadbeef",
            "content-type": "application/json",
        },
        content=payload,
    )
    # Invalid/mismatched signature should return 401 (unauthorized)
    assert bad_signature.status_code == 401

    valid_signature = client.post(
        "/webhooks/incident",
        headers={
            "x-tenant-id": "tenant-system",
            "x-signature": f"sha256={digest}",
            "content-type": "application/json",
        },
        content=payload,
    )
    assert valid_signature.status_code == 202


def test_mutating_routes_require_operator_role(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/manual-report",
        headers=auth_headers(roles="viewer"),
        json={
            "affected_service": "billing-api",
            "symptoms": ["checkout latency", "timeout spikes"],
            "severity": "P1",
            "reported_by": "operator",
            "team": "platform",
            "additional_context": "Role gate should block this request.",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "role not allowed"
