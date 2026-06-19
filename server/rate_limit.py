from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections import defaultdict, deque
from time import monotonic
from typing import TYPE_CHECKING

from server.auth import AuthenticatedContext

if TYPE_CHECKING:
    from server.db import SQLiteDatabase

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(
        self,
        *,
        max_requests: int = 60,
        window_seconds: float = 60.0,
        database: SQLiteDatabase | None = None
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests_by_key: dict[str, deque[float]] = defaultdict(deque)
        self._locks: dict[str, asyncio.Lock] = {}
        self._database = database
        self._db_initialized = False

    def _ensure_db_schema(self) -> None:
        """Create rate_limit_events table if it doesn't exist."""
        if not self._database or self._db_initialized:
            return

        try:
            conn = self._database._get_connection()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS rate_limit_events (
                        key TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        CHECK (length(key) > 0)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_key_timestamp ON rate_limit_events(key, timestamp)")
                conn.commit()
                self._db_initialized = True
            finally:
                conn.close()
        except Exception as e:
            logger.warning(f"Failed to initialize rate limit database schema: {e}")

    async def check(self, *, auth: AuthenticatedContext, route_key: str) -> None:
        key = f"{auth.tenant_id}:{auth.user_id}:{route_key}"

        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            now = monotonic()
            requests = self._requests_by_key[key]

            # Clean up old entries from in-memory store
            while requests and now - requests[0] > self._window_seconds:
                requests.popleft()

            # Count valid requests: in-memory + database
            count_from_memory = len(requests)
            count_from_db = 0

            if self._database:
                self._ensure_db_schema()
                count_from_db = await self._get_and_cleanup_db_events(key, now)

            total_count = count_from_memory + count_from_db

            # Add new event to both stores
            requests.append(now)
            if self._database:
                try:
                    await self._add_db_event(key, now)
                except Exception as e:
                    logger.warning(f"Failed to record rate limit event in database: {e}")

            if total_count >= self._max_requests:
                from fastapi import HTTPException

                raise HTTPException(status_code=429, detail="rate limit exceeded")

    async def _get_and_cleanup_db_events(self, key: str, now: float) -> int:
        """Get count of valid events from DB and clean up old ones."""
        def query_and_cleanup():
            try:
                conn = self._database._get_connection()
                try:
                    # Delete events older than window
                    conn.execute(
                        "DELETE FROM rate_limit_events WHERE key = ? AND timestamp < ?",
                        (key, now - self._window_seconds)
                    )

                    # Count remaining events
                    count_result = conn.execute(
                        "SELECT COUNT(*) FROM rate_limit_events WHERE key = ?",
                        (key,)
                    ).fetchone()

                    conn.commit()
                    return count_result[0] if count_result else 0
                finally:
                    conn.close()
            except Exception as e:
                logger.warning(f"Failed to query rate limit events: {e}")
                return 0

        return await asyncio.to_thread(query_and_cleanup)

    async def _add_db_event(self, key: str, timestamp: float) -> None:
        """Add rate limit event to database."""
        def insert():
            conn = self._database._get_connection()
            try:
                conn.execute(
                    "INSERT INTO rate_limit_events (key, timestamp) VALUES (?, ?)",
                    (key, timestamp)
                )
                conn.commit()
            finally:
                conn.close()

        await asyncio.to_thread(insert)
