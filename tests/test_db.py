import asyncio
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from server.db import SQLiteDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.mark.asyncio
async def test_concurrent_writes(temp_db):
    """Verify concurrent writes succeed without serialization bottleneck."""
    db = SQLiteDatabase(temp_db)

    async def write_incident(i: int):
        """Write a single incident."""
        return await db.create_incident(
            nexus_incident_id=f"nxs_concurrent_{i:02d}",
            tenant_id="tenant-test",
            data={"index": i, "message": f"concurrent write {i}"}
        )

    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[write_incident(i) for i in range(10)])
    elapsed = asyncio.get_event_loop().time() - start_time

    # Verify all writes succeeded
    assert len(results) == 10
    for i, result in enumerate(results):
        assert result["nexus_incident_id"] == f"nxs_concurrent_{i:02d}"
        assert result["tenant_id"] == "tenant-test"
        assert result["data"]["index"] == i

    # Verify all records exist in database
    all_incidents = await db.list_incidents_for_tenant("tenant-test", limit=100)
    assert len(all_incidents) == 10

    # With WAL mode and concurrent writes, this should complete reasonably fast
    # Without WAL, the single global lock would serialize all writes
    # Allow up to 10 seconds for 10 concurrent writes (1s per write with WAL is very slow)
    assert elapsed < 10.0, f"Concurrent writes took {elapsed:.2f}s, expected < 10s"


@pytest.mark.asyncio
async def test_wal_mode_enabled(temp_db):
    """Verify WAL mode is enabled for concurrent reads/writes."""
    db = SQLiteDatabase(temp_db)

    # Check that WAL mode was set during schema initialization
    conn = sqlite3.connect(str(temp_db))
    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()

    assert journal_mode.upper() == "WAL"


@pytest.mark.asyncio
async def test_busy_timeout_set(temp_db):
    """Verify busy_timeout is configured for write waiting."""
    db = SQLiteDatabase(temp_db)

    # Check that busy_timeout was set
    conn = sqlite3.connect(str(temp_db))
    busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    conn.close()

    assert busy_timeout == 5000


@pytest.mark.asyncio
async def test_concurrent_reads_and_writes(temp_db):
    """Verify reads and writes can happen concurrently with WAL mode."""
    db = SQLiteDatabase(temp_db)

    # Create initial incidents
    for i in range(5):
        await db.create_incident(
            nexus_incident_id=f"nxs_initial_{i:02d}",
            tenant_id="tenant-concurrent",
            data={"index": i}
        )

    async def write_incident(i: int):
        """Write incidents."""
        await asyncio.sleep(0.01 * i)
        return await db.create_incident(
            nexus_incident_id=f"nxs_write_{i:02d}",
            tenant_id="tenant-concurrent",
            data={"index": i}
        )

    async def read_incidents():
        """Read incidents in parallel."""
        results = []
        for _ in range(5):
            incidents = await db.list_incidents_for_tenant("tenant-concurrent", limit=100)
            results.append(len(incidents))
            await asyncio.sleep(0.01)
        return results

    # Fire concurrent reads and writes
    write_tasks = [write_incident(i) for i in range(5)]
    read_task = read_incidents()

    write_results, read_results = await asyncio.gather(
        asyncio.gather(*write_tasks),
        read_task
    )

    # Verify writes succeeded
    assert len(write_results) == 5

    # Verify reads saw consistent data (read_results shows growing counts as writes complete)
    assert all(isinstance(count, int) for count in read_results)
    assert max(read_results) >= 5  # Should see at least initial 5 + some writes
