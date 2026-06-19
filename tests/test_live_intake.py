import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from server.app import app
from server.integrations.models import RawIncidentTextRequest


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as test_client:
        yield test_client


def test_receive_raw_text_rejects_unsupported_incident_type(client, auth_headers):
    """Verify /inputs returns helpful error for unsupported incident types."""
    # Submit an incident that clearly doesn't match any of the 5 supported families
    response = client.post(
        "/api/v1/incidents/raw-text",
        json={
            "raw_text": "The office printer is out of paper and needs to be refilled. Please add toner cartridges.",
            "severity_hint": "P4",
            "source_hint": "manual_form",
            "reported_by": "user@example.com",
            "team": "facilities",
        },
        headers=auth_headers(),
    )

    # Should return 400 Bad Request with helpful message, not 500
    assert response.status_code == 400
    data = response.json()

    # Verify response contains structured error message
    if isinstance(data.get("detail"), dict):
        detail = data["detail"]
        assert detail.get("error") == "unsupported_incident_type"
        assert "5 supported families" in detail.get("message", "")
        assert "Timeout/Retry" in detail.get("message", "")
    else:
        # Fallback: message might be in detail string
        assert "supported" in str(data.get("detail", "")).lower()


def test_receive_raw_text_accepts_supported_incident_type(client, auth_headers):
    """Verify /inputs accepts incidents matching supported families."""
    # Submit an incident that matches the checkout timeout family (INC001)
    response = client.post(
        "/api/v1/incidents/raw-text",
        json={
            "raw_text": (
                "checkout-svc is timing out after 30 seconds. "
                "The service is retrying requests which is amplifying the problem. "
                "This is affecting our payment processing."
            ),
            "severity_hint": "P1",
            "source_hint": "manual_form",
            "reported_by": "oncall@example.com",
            "team": "platform",
        },
        headers=auth_headers(),
    )

    # Should succeed (201 or 200)
    assert response.status_code in [200, 201, 202]
    data = response.json()

    # Should have incident details
    assert "nexus_incident_id" in data or "incident_id" in data


def test_receive_raw_text_accepts_database_pool_exhaustion(client, auth_headers):
    """Verify DB pool exhaustion incidents are accepted."""
    response = client.post(
        "/api/v1/incidents/raw-text",
        json={
            "raw_text": (
                "Database connections exhausted. "
                "The payment-db connection pool is at capacity. "
                "Sessions are not being released properly, causing a pool leak."
            ),
            "severity_hint": "P1",
            "source_hint": "manual_form",
            "reported_by": "db-oncall@example.com",
            "team": "platform",
        },
        headers=auth_headers(),
    )

    assert response.status_code in [200, 201, 202]


def test_receive_raw_text_accepts_deploy_regression(client, auth_headers):
    """Verify deploy regression incidents are accepted."""
    response = client.post(
        "/api/v1/incidents/raw-text",
        json={
            "raw_text": (
                "After deploying version 2.5.1, the API is returning 500 errors. "
                "Error rate jumped from 0.1% to 15% immediately after the deploy. "
                "Need to rollback immediately."
            ),
            "severity_hint": "P1",
            "source_hint": "manual_form",
            "reported_by": "eng@example.com",
            "team": "api",
        },
        headers=auth_headers(),
    )

    assert response.status_code in [200, 201, 202]


def test_receive_raw_text_accepts_valid_docker_compose(client, auth_headers):
    """Verify incidents with valid Docker Compose are accepted."""
    compose = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: testdb
"""
    response = client.post(
        "/api/v1/incidents/raw-text",
        json={
            "raw_text": (
                "checkout-svc is timing out after 30 seconds. "
                "The service is retrying requests which is amplifying the problem."
            ),
            "severity_hint": "P1",
            "source_hint": "manual_form",
            "reported_by": "eng@example.com",
            "team": "platform",
            "docker_compose_content": compose,
        },
        headers=auth_headers(),
    )

    # Should succeed and include Docker Compose in response
    assert response.status_code in [200, 201, 202]
    data = response.json()
    assert "nexus_incident_id" in data or "incident_id" in data


def test_receive_raw_text_rejects_invalid_docker_compose(client, auth_headers):
    """Verify incidents with invalid Docker Compose are rejected."""
    invalid_compose = """
version: '3.8'
services:
  app:
    image: nginx:latest
    privileged: true
"""
    response = client.post(
        "/api/v1/incidents/raw-text",
        json={
            "raw_text": (
                "checkout-svc is timing out after 30 seconds."
            ),
            "severity_hint": "P1",
            "source_hint": "manual_form",
            "reported_by": "eng@example.com",
            "team": "platform",
            "docker_compose_content": invalid_compose,
        },
        headers=auth_headers(),
    )

    # Should reject with 400 error
    assert response.status_code == 400
    data = response.json()

    if isinstance(data.get("detail"), dict):
        detail = data["detail"]
        assert detail.get("error") == "invalid_docker_compose"
        assert "privileged" in detail.get("message", "").lower()
    else:
        assert "invalid" in str(data.get("detail", "")).lower()
