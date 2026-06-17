"""
Tests for SQLite database layer and repository integration.

Validates:
- Database initialization and schema
- Repository operations (create, read, update)
- Tenant isolation
- Async/await patterns
- Error handling
"""

import asyncio
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from server.db import SQLiteDatabase
from server.repositories import IncidentRepository


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield SQLiteDatabase(db_path)


@pytest.mark.asyncio
async def test_database_initialization(temp_db):
    """Test database initializes with correct schema."""
    # Verify database file exists
    assert temp_db._path.exists()

    # Verify tables exist
    conn = sqlite3.connect(temp_db._path)
    cursor = conn.cursor()

    # Check incidents table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'")
    assert cursor.fetchone() is not None

    # Check audit_logs table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
    assert cursor.fetchone() is not None

    # Check indexes
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    index_count = cursor.fetchone()[0]
    assert index_count >= 9  # Expected number of indexes

    conn.close()


@pytest.mark.asyncio
async def test_create_incident(temp_db):
    """Test creating an incident."""
    incident = await temp_db.create_incident(
        nexus_incident_id="test-001",
        tenant_id="tenant-a",
        data={"title": "Test incident", "severity": "P1"}
    )

    assert incident['nexus_incident_id'] == "test-001"
    assert incident['tenant_id'] == "tenant-a"
    assert incident['data']['title'] == "Test incident"


@pytest.mark.asyncio
async def test_get_incident_for_tenant(temp_db):
    """Test retrieving incident with tenant isolation."""
    await temp_db.create_incident(
        nexus_incident_id="test-001",
        tenant_id="tenant-a",
        data={"title": "Test"}
    )

    # Should find with correct tenant
    incident = await temp_db.get_incident_for_tenant("test-001", "tenant-a")
    assert incident is not None
    assert incident['data']['title'] == "Test"

    # Should not find with wrong tenant
    incident = await temp_db.get_incident_for_tenant("test-001", "tenant-b")
    assert incident is None


@pytest.mark.asyncio
async def test_list_incidents_for_tenant(temp_db):
    """Test listing incidents with tenant isolation."""
    # Create incidents for different tenants
    await temp_db.create_incident("inc-001", "tenant-a", {"title": "A1"})
    await temp_db.create_incident("inc-002", "tenant-a", {"title": "A2"})
    await temp_db.create_incident("inc-003", "tenant-b", {"title": "B1"})

    # List for tenant-a
    incidents_a = await temp_db.list_incidents_for_tenant("tenant-a")
    assert len(incidents_a) == 2
    assert all(inc['tenant_id'] == "tenant-a" for inc in incidents_a)

    # List for tenant-b
    incidents_b = await temp_db.list_incidents_for_tenant("tenant-b")
    assert len(incidents_b) == 1
    assert incidents_b[0]['tenant_id'] == "tenant-b"


@pytest.mark.asyncio
async def test_update_incident(temp_db):
    """Test updating an incident."""
    # Create incident
    await temp_db.create_incident(
        "test-001",
        "tenant-a",
        {"title": "Original", "severity": "P1"}
    )

    # Update
    updated = await temp_db.update_incident(
        "test-001",
        "tenant-a",
        {"title": "Updated", "severity": "P2"}
    )

    assert updated is not None
    assert updated['data']['title'] == "Updated"
    assert updated['data']['severity'] == "P2"


@pytest.mark.asyncio
async def test_tenant_isolation(temp_db):
    """Test tenant isolation prevents cross-tenant access."""
    # Create incident for tenant-a
    await temp_db.create_incident(
        "secret-001",
        "tenant-a",
        {"secret": "data"}
    )

    # Tenant-b cannot read
    incident = await temp_db.get_incident_for_tenant("secret-001", "tenant-b")
    assert incident is None

    # Tenant-a can read
    incident = await temp_db.get_incident_for_tenant("secret-001", "tenant-a")
    assert incident is not None


@pytest.mark.asyncio
async def test_concurrent_writes(temp_db):
    """Test concurrent write handling."""
    tasks = [
        temp_db.create_incident(
            f"inc-{i:03d}",
            "tenant-a",
            {"title": f"Incident {i}"}
        )
        for i in range(10)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # All should succeed
    assert all(not isinstance(r, Exception) for r in results)

    # Verify all created
    incidents = await temp_db.list_incidents_for_tenant("tenant-a")
    assert len(incidents) == 10


@pytest.mark.asyncio
async def test_repository_create(temp_db):
    """Test IncidentRepository.create_incident."""
    repo = IncidentRepository(temp_db)

    incident = await repo.create_incident(
        external_id="ext-001",
        title="Test Incident",
        severity="P1",
        tenant_id="tenant-a"
    )

    assert incident.title == "Test Incident"
    assert incident.severity == "P1"
    assert incident.tenant_id == "tenant-a"

    # Verify persisted
    retrieved = await temp_db.get_incident_for_tenant(
        incident.nexus_incident_id,
        "tenant-a"
    )
    assert retrieved is not None


@pytest.mark.asyncio
async def test_repository_get(temp_db):
    """Test IncidentRepository.get_incident_for_tenant."""
    repo = IncidentRepository(temp_db)

    # Create
    incident = await repo.create_incident(
        external_id="ext-002",
        title="Get Test",
        severity="P2",
        tenant_id="tenant-b"
    )

    # Retrieve
    retrieved = await repo.get_incident_for_tenant(
        incident.nexus_incident_id,
        "tenant-b"
    )

    assert retrieved is not None
    assert retrieved.title == "Get Test"


@pytest.mark.asyncio
async def test_repository_update_status(temp_db):
    """Test IncidentRepository.update_incident_status."""
    repo = IncidentRepository(temp_db)

    # Create
    incident = await repo.create_incident(
        external_id="ext-003",
        title="Update Test",
        severity="P1",
        tenant_id="tenant-system"
    )

    # Update
    updated = await repo.update_incident_status(
        incident.nexus_incident_id,
        status="resolved",
        guardian_decision="approve"
    )

    assert updated is not None
    assert updated.status == "resolved"
    assert updated.guardian_decision == "approve"


@pytest.mark.asyncio
async def test_audit_log(temp_db):
    """Test audit logging."""
    log_id = await temp_db.add_audit_log(
        event_type="test_event",
        tenant_id="tenant-a",
        user_id="user-123",
        data={"action": "test"}
    )

    assert isinstance(log_id, int)
    assert log_id > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
