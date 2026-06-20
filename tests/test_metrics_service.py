import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from server.services.metrics_service import PilotMetricsService
from server.db import SQLiteDatabase


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = SQLiteDatabase(db_path)
        yield db


@pytest.fixture
def tenant_id():
    """Test tenant ID."""
    return "test-tenant-123"


@pytest.mark.asyncio
async def test_compute_pilot_metrics_empty_database(test_db, tenant_id):
    """Test that empty database returns zero counts with computed_at present."""
    service = PilotMetricsService()
    metrics = await service.compute_pilot_metrics(tenant_id, test_db)

    assert metrics["incidents_handled"] == 0
    assert metrics["incidents_runtime_backed"] == 0
    assert metrics["incidents_inferred"] == 0
    assert metrics["handoff_completion_count"] == 0
    assert metrics["total_triage_time_saved_minutes"] == 0
    assert "computed_at" in metrics
    # Verify computed_at is ISO format
    datetime.fromisoformat(metrics["computed_at"])


@pytest.mark.asyncio
async def test_compute_pilot_metrics_counts_incidents(test_db, tenant_id):
    """Test that submitting incidents updates incident count."""
    service = PilotMetricsService()

    # Insert 3 incidents
    for i in range(3):
        incident_data = {
            "incident_title": f"Test Incident {i}",
            "evidence_posture": "runtime_backed" if i < 2 else "inferred_only",
            "handoff_status": "sent" if i < 2 else "not_sent",
        }
        await test_db.create_incident(
            nexus_incident_id=f"incident-{i}",
            tenant_id=tenant_id,
            data=incident_data,
        )

    metrics = await service.compute_pilot_metrics(tenant_id, test_db)

    assert metrics["incidents_handled"] == 3
    assert metrics["incidents_runtime_backed"] == 2
    assert metrics["incidents_inferred"] == 1
    assert metrics["handoff_completion_count"] == 2
    assert "computed_at" in metrics


@pytest.mark.asyncio
async def test_compute_pilot_metrics_calculates_triage_time(test_db, tenant_id):
    """Test that triage time is calculated as incidents_handled * 15 minutes."""
    service = PilotMetricsService()

    # Insert 5 incidents
    for i in range(5):
        incident_data = {
            "incident_title": f"Test Incident {i}",
            "evidence_posture": "runtime_backed",
            "handoff_status": "sent",
        }
        await test_db.create_incident(
            nexus_incident_id=f"incident-{i}",
            tenant_id=tenant_id,
            data=incident_data,
        )

    metrics = await service.compute_pilot_metrics(tenant_id, test_db)

    assert metrics["incidents_handled"] == 5
    assert metrics["total_triage_time_saved_minutes"] == 75  # 5 * 15


@pytest.mark.asyncio
async def test_compute_pilot_metrics_tenant_isolation(test_db):
    """Test that metrics only count incidents for the specified tenant."""
    service = PilotMetricsService()
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    # Insert incidents for tenant A
    for i in range(2):
        incident_data = {
            "incident_title": f"Tenant A Incident {i}",
            "evidence_posture": "runtime_backed",
            "handoff_status": "sent",
        }
        await test_db.create_incident(
            nexus_incident_id=f"a-incident-{i}",
            tenant_id=tenant_a,
            data=incident_data,
        )

    # Insert incidents for tenant B
    for i in range(3):
        incident_data = {
            "incident_title": f"Tenant B Incident {i}",
            "evidence_posture": "runtime_backed",
            "handoff_status": "sent",
        }
        await test_db.create_incident(
            nexus_incident_id=f"b-incident-{i}",
            tenant_id=tenant_b,
            data=incident_data,
        )

    metrics_a = await service.compute_pilot_metrics(tenant_a, test_db)
    metrics_b = await service.compute_pilot_metrics(tenant_b, test_db)

    assert metrics_a["incidents_handled"] == 2
    assert metrics_b["incidents_handled"] == 3


@pytest.mark.asyncio
async def test_compute_pilot_metrics_response_structure(test_db, tenant_id):
    """Test that response has all required fields in correct structure."""
    service = PilotMetricsService()

    # Insert one incident to ensure non-empty response
    incident_data = {
        "incident_title": "Test",
        "evidence_posture": "runtime_backed",
        "handoff_status": "sent",
    }
    await test_db.create_incident(
        nexus_incident_id="test-incident",
        tenant_id=tenant_id,
        data=incident_data,
    )

    metrics = await service.compute_pilot_metrics(tenant_id, test_db)

    # All required fields must be present
    assert "incidents_handled" in metrics
    assert "incidents_runtime_backed" in metrics
    assert "incidents_inferred" in metrics
    assert "handoff_completion_count" in metrics
    assert "total_triage_time_saved_minutes" in metrics
    assert "computed_at" in metrics

    # All counts must be integers
    assert isinstance(metrics["incidents_handled"], int)
    assert isinstance(metrics["incidents_runtime_backed"], int)
    assert isinstance(metrics["incidents_inferred"], int)
    assert isinstance(metrics["handoff_completion_count"], int)
    assert isinstance(metrics["total_triage_time_saved_minutes"], int)
