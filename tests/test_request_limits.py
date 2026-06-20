import pytest
from starlette.testclient import TestClient


@pytest.mark.asyncio
async def test_large_request_rejected(client: TestClient) -> None:
    """Test that requests with Content-Length > 1MB are rejected with 413."""
    # Create a payload that is definitely larger than 1MB
    large_data = "x" * (1048576 + 1)  # 1MB + 1 byte

    response = client.post(
        "/api/v1/incidents/raw-text",
        json={"incident_text": large_data},
        headers={
            "Content-Type": "application/json",
            "X-User-ID": "user-123",
            "X-Tenant-ID": "tenant-a",
        },
    )

    assert response.status_code == 413
    assert "too large" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_normal_request_passes(client: TestClient) -> None:
    """Test that normal-sized requests pass through the size check."""
    response = client.post(
        "/api/v1/incidents/raw-text",
        json={
            "incident_text": "This is a normal incident report",
            "severity": "P2",
        },
        headers={
            "Content-Type": "application/json",
            "X-User-ID": "user-123",
            "X-Tenant-ID": "tenant-a",
        },
    )

    # Should either succeed (200-299) or fail with auth/validation error, but not 413
    assert response.status_code != 413


@pytest.mark.asyncio
async def test_request_at_size_limit_passes(client: TestClient) -> None:
    """Test that requests just under 1MB limit pass through."""
    # Create a payload just under 1MB (accounting for JSON encoding overhead)
    large_data = "x" * (1048576 - 100)  # Just under 1MB

    response = client.post(
        "/api/v1/incidents/raw-text",
        json={"incident_text": large_data},
        headers={
            "Content-Type": "application/json",
            "X-User-ID": "user-123",
            "X-Tenant-ID": "tenant-a",
        },
    )

    # Should not be rejected with 413
    assert response.status_code != 413
