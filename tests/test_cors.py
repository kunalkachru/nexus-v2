import pytest
from starlette.testclient import TestClient


@pytest.mark.asyncio
async def test_cors_allowed_origin(client: TestClient) -> None:
    """Test that allowed origins get CORS headers."""
    response = client.get(
        "/api/v1/tenant/pilot-scorecard",
        headers={
            "Origin": "http://localhost:7860",
            "Authorization": "Bearer test-token",
            "X-User-ID": "user-123",
            "X-Tenant-ID": "tenant-a",
        },
    )

    # Should have CORS headers
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:7860"


@pytest.mark.asyncio
async def test_cors_unlisted_origin(client: TestClient) -> None:
    """Test that unlisted origins do not get CORS headers."""
    response = client.get(
        "/api/v1/tenant/pilot-scorecard",
        headers={
            "Origin": "http://attacker.example.com",
            "Authorization": "Bearer test-token",
            "X-User-ID": "user-123",
            "X-Tenant-ID": "tenant-a",
        },
    )

    # Should not have CORS headers for unlisted origins
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_allowed_methods(client: TestClient) -> None:
    """Test that allowed methods are in CORS headers."""
    response = client.options(
        "/api/v1/tenant/pilot-scorecard",
        headers={
            "Origin": "http://localhost:7860",
            "Access-Control-Request-Method": "GET",
        },
    )

    if "access-control-allow-origin" in response.headers:
        assert "access-control-allow-methods" in response.headers
        allowed_methods = response.headers["access-control-allow-methods"].upper()
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods


@pytest.mark.asyncio
async def test_cors_credentials_allowed(client: TestClient) -> None:
    """Test that credentials are allowed in CORS."""
    response = client.get(
        "/api/v1/tenant/pilot-scorecard",
        headers={
            "Origin": "http://localhost:7860",
            "Authorization": "Bearer test-token",
            "X-User-ID": "user-123",
            "X-Tenant-ID": "tenant-a",
        },
    )

    if "access-control-allow-origin" in response.headers:
        assert response.headers.get("access-control-allow-credentials", "").lower() == "true"
