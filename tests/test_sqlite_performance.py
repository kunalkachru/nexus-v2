"""
Performance tests for SQLite database layer.

Validates:
- Single incident retrieval: < 10ms
- List 100 incidents: < 100ms
- 100 concurrent writes: 0 data loss
- Index effectiveness (no full table scans)
- Memory stability over time
"""

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from server.db import SQLiteDatabase


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "perf_test.db"
        yield SQLiteDatabase(db_path)


@pytest.mark.asyncio
async def test_single_incident_retrieval_latency(temp_db):
    """
    Test: Single incident retrieval must be < 10ms.

    Target: < 10ms (p99)
    Rationale: Single-incident queries are common (get by ID)
    """
    tenant_id = "tenant-a"

    # Create test incident
    await temp_db.create_incident(
        "test-001",
        tenant_id,
        {"title": "Test", "severity": "P1"}
    )

    # Measure retrieval latency (p99 of 100 runs)
    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        await temp_db.get_incident_for_tenant("test-001", tenant_id)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        latencies.append(elapsed)

    latencies.sort()
    p99_latency = latencies[int(len(latencies) * 0.99)]

    print(f"Single retrieval p99: {p99_latency:.2f}ms")
    assert p99_latency < 10, f"Single retrieval p99 {p99_latency}ms exceeds 10ms target"


@pytest.mark.asyncio
async def test_list_100_incidents_latency(temp_db):
    """
    Test: List 100 incidents must be < 100ms.

    Target: < 100ms (p99)
    Rationale: Listing incidents is a common operation
    """
    tenant_id = "tenant-a"

    # Create 150 incidents
    for i in range(150):
        await temp_db.create_incident(
            f"inc-{i:03d}",
            tenant_id,
            {"title": f"Incident {i}", "severity": "P1"}
        )

    # Measure list latency (p99 of 20 runs)
    latencies = []
    for _ in range(20):
        start = time.perf_counter()
        incidents = await temp_db.list_incidents_for_tenant(tenant_id, limit=100, offset=0)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        latencies.append(elapsed)
        assert len(incidents) == 100

    latencies.sort()
    p99_latency = latencies[int(len(latencies) * 0.99)]

    print(f"List 100 p99: {p99_latency:.2f}ms")
    assert p99_latency < 100, f"List p99 {p99_latency}ms exceeds 100ms target"


@pytest.mark.asyncio
async def test_concurrent_writes_no_loss(temp_db):
    """
    Test: 100 concurrent writes must result in 0 data loss.

    Target: All 100 incidents must be present after concurrent writes
    Rationale: Multi-operator concurrency must be safe
    """
    tenant_id = "tenant-a"

    # Create 100 concurrent write tasks
    async def create_incident(idx):
        return await temp_db.create_incident(
            f"concurrent-{idx:03d}",
            tenant_id,
            {"title": f"Concurrent {idx}", "severity": "P1"}
        )

    tasks = [create_incident(i) for i in range(100)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check all succeeded
    assert all(not isinstance(r, Exception) for r in results), \
        f"Some concurrent writes failed: {[r for r in results if isinstance(r, Exception)]}"

    # Verify all 100 incidents exist
    incidents = await temp_db.list_incidents_for_tenant(tenant_id, limit=200, offset=0)
    assert len(incidents) == 100, f"Expected 100 incidents, got {len(incidents)}"


@pytest.mark.asyncio
async def test_memory_stability_over_operations(temp_db):
    """
    Test: Memory usage must remain stable over 1000 operations.

    Target: No unbounded memory growth
    Rationale: Long-running processes must be memory-efficient
    """
    import gc
    import psutil
    import os

    tenant_id = "tenant-a"
    process = psutil.Process(os.getpid())

    # Force garbage collection and measure baseline
    gc.collect()
    baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Perform 1000 operations
    for i in range(1000):
        if i % 100 == 0:
            gc.collect()

        # Create, read, update in sequence
        incident_id = f"mem-test-{i:04d}"
        await temp_db.create_incident(
            incident_id,
            tenant_id,
            {"title": f"Memory test {i}", "value": i}
        )

        await temp_db.get_incident_for_tenant(incident_id, tenant_id)

        await temp_db.update_incident(
            incident_id,
            tenant_id,
            {"title": f"Updated {i}", "value": i * 2}
        )

    # Measure final memory
    gc.collect()
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = final_memory - baseline_memory

    print(f"Memory growth over 1000 ops: {memory_growth:.2f}MB")
    print(f"Baseline: {baseline_memory:.2f}MB, Final: {final_memory:.2f}MB")

    # Allow some growth but not excessive
    # Expect < 50MB growth for 1000 operations
    assert memory_growth < 50, f"Memory growth {memory_growth}MB exceeds 50MB threshold"


@pytest.mark.asyncio
async def test_index_effectiveness(temp_db):
    """
    Test: Queries must use indexes (no full table scans).

    Rationale: Without indexes, performance degrades badly with data growth
    """
    import sqlite3

    tenant_id = "tenant-a"

    # Create 1000 incidents
    for i in range(1000):
        await temp_db.create_incident(
            f"idx-test-{i:04d}",
            tenant_id,
            {"title": f"Index test {i}"}
        )

    # Check query plans use indexes
    conn = sqlite3.connect(temp_db._path)
    conn.execute("PRAGMA query_only = ON")

    # Test 1: Single incident lookup should use PRIMARY KEY or index
    plan = conn.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM incidents WHERE nexus_incident_id = ? AND tenant_id = ?",
        ("idx-test-0000", tenant_id)
    ).fetchall()

    plan_str = str(plan)
    assert "SEARCH" in plan_str, f"Single lookup should use SEARCH (index), got: {plan_str}"

    # Test 2: Tenant listing should use index
    plan = conn.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM incidents WHERE tenant_id = ? ORDER BY created_at DESC LIMIT 100",
        (tenant_id,)
    ).fetchall()

    plan_str = str(plan)
    assert "SEARCH" in plan_str, f"Tenant listing should use SEARCH (index), got: {plan_str}"

    conn.close()


@pytest.mark.asyncio
async def test_large_field_performance(temp_db):
    """
    Test: Large JSONB fields (50KB) must not cause latency issues.

    Target: < 50ms for operations with large fields
    Rationale: Some incidents have verbose raw_input_text
    """
    tenant_id = "tenant-a"
    large_text = "x" * 50000  # 50KB text

    # Create incident with large field
    start = time.perf_counter()
    await temp_db.create_incident(
        "large-001",
        tenant_id,
        {
            "title": "Large field test",
            "raw_input_text": large_text,
            "severity": "P1"
        }
    )
    create_latency = (time.perf_counter() - start) * 1000

    # Retrieve incident with large field
    start = time.perf_counter()
    incident = await temp_db.get_incident_for_tenant("large-001", tenant_id)
    retrieve_latency = (time.perf_counter() - start) * 1000

    print(f"Large field - Create: {create_latency:.2f}ms, Retrieve: {retrieve_latency:.2f}ms")

    assert create_latency < 50, f"Create with large field: {create_latency}ms exceeds 50ms"
    assert retrieve_latency < 50, f"Retrieve with large field: {retrieve_latency}ms exceeds 50ms"
    assert len(incident["data"]["raw_input_text"]) == 50000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
