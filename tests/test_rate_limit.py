import asyncio
import sqlite3
import tempfile
from pathlib import Path
from time import monotonic
from unittest.mock import Mock

import pytest

from server.auth import AuthenticatedContext
from server.db import SQLiteDatabase
from server.rate_limit import RateLimiter


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.mark.asyncio
async def test_rate_limiter_without_database(temp_db):
    """Verify rate limiter works without database (in-memory only)."""
    limiter = RateLimiter(max_requests=3, window_seconds=60.0)

    auth = Mock(spec=AuthenticatedContext)
    auth.tenant_id = "tenant-test"
    auth.user_id = "user-1"

    # First 3 requests should succeed
    for i in range(3):
        await limiter.check(auth=auth, route_key="test_route")

    # 4th request should fail
    with pytest.raises(Exception, match="rate limit exceeded"):
        await limiter.check(auth=auth, route_key="test_route")


@pytest.mark.asyncio
async def test_rate_limiter_with_database_persistence(temp_db):
    """Verify rate limiter persists state to database."""
    db = SQLiteDatabase(temp_db)
    limiter = RateLimiter(max_requests=3, window_seconds=60.0, database=db)

    auth = Mock(spec=AuthenticatedContext)
    auth.tenant_id = "tenant-test"
    auth.user_id = "user-1"

    # Record some requests
    for i in range(2):
        await limiter.check(auth=auth, route_key="test_route")

    # Verify requests are stored in database
    conn = db._get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_limit_events WHERE key LIKE ?"
            , ("%user-1%",)
        ).fetchone()[0]
        assert count == 2
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_rate_limiter_recovers_from_database_restart(temp_db):
    """Verify rate limiter recovers state after restart from database."""
    # Create first limiter and add requests
    db1 = SQLiteDatabase(temp_db)
    limiter1 = RateLimiter(max_requests=3, window_seconds=60.0, database=db1)

    auth = Mock(spec=AuthenticatedContext)
    auth.tenant_id = "tenant-test"
    auth.user_id = "user-1"

    for i in range(2):
        await limiter1.check(auth=auth, route_key="test_route")

    # Simulate restart - create new limiter with same database
    db2 = SQLiteDatabase(temp_db)
    limiter2 = RateLimiter(max_requests=3, window_seconds=60.0, database=db2)

    # Should still count the 2 events from before the restart
    # Adding 1 more should succeed
    await limiter2.check(auth=auth, route_key="test_route")

    # Adding a 4th should fail (3 + 1 from new limiter = 4, which exceeds limit)
    with pytest.raises(Exception, match="rate limit exceeded"):
        await limiter2.check(auth=auth, route_key="test_route")


@pytest.mark.asyncio
async def test_rate_limiter_cleans_old_events(temp_db):
    """Verify rate limiter cleans up expired events from database."""
    db = SQLiteDatabase(temp_db)
    limiter = RateLimiter(max_requests=3, window_seconds=0.1, database=db)

    auth = Mock(spec=AuthenticatedContext)
    auth.tenant_id = "tenant-test"
    auth.user_id = "user-1"

    # Add request
    await limiter.check(auth=auth, route_key="test_route")

    # Wait for window to expire
    await asyncio.sleep(0.2)

    # Add another request - should trigger cleanup of old event
    await limiter.check(auth=auth, route_key="test_route")

    # Verify only 1 event in database (old one was cleaned)
    conn = db._get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_limit_events WHERE key LIKE ?",
            ("%user-1%",)
        ).fetchone()[0]
        # Should be just the one we added after cleanup
        assert count == 1
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_rate_limiter_graceful_fallback_if_db_unavailable(temp_db):
    """Verify rate limiter falls back to in-memory if database fails."""
    db = SQLiteDatabase(temp_db)
    limiter = RateLimiter(max_requests=3, window_seconds=60.0, database=db)

    auth = Mock(spec=AuthenticatedContext)
    auth.tenant_id = "tenant-test"
    auth.user_id = "user-1"

    # Mock the database methods to raise exceptions
    original_get = db._get_connection

    def failing_get_connection():
        raise RuntimeError("Database unavailable")

    db._get_connection = failing_get_connection

    # Should still work with in-memory store even if DB fails
    for i in range(3):
        await limiter.check(auth=auth, route_key="test_route")

    # 4th should fail from in-memory limit
    with pytest.raises(Exception, match="rate limit exceeded"):
        await limiter.check(auth=auth, route_key="test_route")

    # Restore the original method
    db._get_connection = original_get
