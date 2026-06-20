import pytest
from starlette.testclient import TestClient


@pytest.mark.asyncio
async def test_health_endpoint_response_structure(client: TestClient, auth_headers) -> None:
    """Test that health endpoint returns required structure."""
    response = client.get("/api/v1/observability/health", headers=auth_headers())

    assert response.status_code == 200
    health = response.json()

    # Top-level fields
    assert "status" in health
    assert "timestamp" in health
    assert "app" in health
    assert "replay" in health
    assert "queue" in health
    assert "memory" in health
    assert "delivery" in health
    assert "runtime_queue" in health
    assert "deployment_readiness" in health
    assert "downstream_integrations" in health
    assert "pilot_surface" in health
    assert "degraded_services" in health

    # App health
    assert "status" in health["app"]

    # Subsystem healths
    assert "status" in health["replay"]
    assert "status" in health["queue"]
    assert "status" in health["memory"]
    assert "status" in health["delivery"]

    # Queue details
    assert "items_pending" in health["queue"]

    # Delivery integrations
    assert "github" in health["downstream_integrations"]
    assert "slack" in health["downstream_integrations"]

    # Degraded services is a list
    assert isinstance(health["degraded_services"], list)


@pytest.mark.asyncio
async def test_health_endpoint_guidance_fields(client: TestClient, auth_headers) -> None:
    """Test that health subsystems include guidance and next_checks."""
    response = client.get("/api/v1/observability/health", headers=auth_headers())

    assert response.status_code == 200
    health = response.json()

    # Each subsystem should have these fields if present
    for subsystem_name in ["replay", "queue", "memory", "delivery"]:
        subsystem = health.get(subsystem_name)
        if subsystem:
            assert isinstance(subsystem.get("guidance", []), list)
            assert isinstance(subsystem.get("next_checks", []), list)


@pytest.mark.asyncio
async def test_health_endpoint_requires_auth(client: TestClient) -> None:
    """Test that health endpoint requires authentication."""
    response = client.get("/api/v1/observability/health")

    assert response.status_code in [401, 403]
