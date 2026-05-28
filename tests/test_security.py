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

    assert response.status_code == 404
