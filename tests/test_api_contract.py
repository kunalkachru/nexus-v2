import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from server.app import app
from server.config import AppConfig
from server.db import create_session_factory
from server.db import DatabaseSession, get_db
from server.models import IncidentRecord


def test_app_startup_wires_persistence_factory() -> None:
    with TestClient(app):
        assert hasattr(app.state, "config")
        assert hasattr(app.state, "db_session_factory")
        session = app.state.db_session_factory()
        assert isinstance(session, DatabaseSession)
        asyncio.run(session.close())


def test_get_db_uses_app_scoped_factory(tmp_path: Path) -> None:
    async def scenario() -> None:
        custom_app = FastAPI()
        custom_app.state.config = AppConfig(database_path=tmp_path / "app-scoped-incidents.json")
        custom_app.state.db_session_factory = create_session_factory(custom_app.state.config)
        scope = {"type": "http", "app": custom_app, "headers": [], "query_string": b""}
        generator = get_db(Request(scope))
        session = await anext(generator)

        assert isinstance(session, DatabaseSession)
        assert hasattr(session, "incidents")

        incident = await session.incidents.create_incident(
            external_id="inc_xyz",
            title="Payment API timeout",
            severity="P1",
        )
        await generator.aclose()

        assert custom_app.state.config.database_path.exists()

        verification_session = custom_app.state.db_session_factory()
        try:
            loaded = await verification_session.incidents.get_incident(incident.nexus_incident_id)
            assert loaded is not None
            assert loaded.external_id == "inc_xyz"
        finally:
            await verification_session.close()

    asyncio.run(scenario())


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
                external_id="inc_seeded",
                title="Seeded incident",
                severity="P2",
                tenant_id="tenant-a",
            )
        finally:
            await session.close()

    return asyncio.run(scenario())


def test_webhook_creates_nexus_incident(client: TestClient) -> None:
    response = client.post(
        "/webhooks/incident",
        json={
            "incident_id": "inc_xyz",
            "title": "Payment API timeout",
            "severity": "P1",
            "detected_at": "2026-05-25T14:32:00Z",
            "monitoring_source": "datadog",
            "metrics": {"service": "payment-svc", "error_rate": 0.45},
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["external_id"] == "inc_xyz"
    assert payload["status"] == "investigating"
    assert payload["source"] == "datadog"
    assert payload["recent_deployments"] == []


def test_incident_status_returns_persisted_lifecycle(
    client: TestClient,
    seeded_incident: IncidentRecord,
    auth_headers,
) -> None:
    response = client.get(
        f"/incidents/{seeded_incident.nexus_incident_id}",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["nexus_incident_id"] == seeded_incident.nexus_incident_id
    assert payload["external_id"] == seeded_incident.external_id
    assert payload["status"] == "investigating"
    assert payload["source"] is None
    assert payload["recent_deployments"] == []


def test_incident_status_returns_404_for_unknown_incident(client: TestClient, auth_headers) -> None:
    response = client.get("/incidents/nxs_missing", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "incident not found"
