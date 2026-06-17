import asyncio
import json
import logging
import sqlite3
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Request
from pydantic import ValidationError

from server.config import AppConfig
from server.models import IncidentRecord
from server.repositories import IncidentRepository

logger = logging.getLogger(__name__)


class SQLiteDatabase:
    """SQLite-backed database with tenant isolation and async support."""

    def __init__(self, config: AppConfig | str | Path) -> None:
        """
        Initialize database.

        Args:
            config: AppConfig object or Path/string to database file
        """
        if isinstance(config, (str, Path)):
            self._path = Path(config)
        else:
            self._path = config.database_path
        self._lock = asyncio.Lock()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create database and schema if not exists."""
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)

        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")

                # Create incidents table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS incidents (
                        nexus_incident_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        data JSONB NOT NULL,
                        UNIQUE(tenant_id, nexus_incident_id),
                        CHECK (length(nexus_incident_id) > 0),
                        CHECK (length(tenant_id) > 0),
                        CHECK (json_valid(data))
                    )
                """)

                # Create audit_logs table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        event_type TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        user_id TEXT,
                        data JSONB NOT NULL,
                        CHECK (length(event_type) > 0),
                        CHECK (length(tenant_id) > 0),
                        CHECK (json_valid(data))
                    )
                """)

                # Create indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_tenant_id ON incidents(tenant_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_updated_at ON incidents(updated_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_incidents_tenant_created ON incidents(tenant_id, created_at DESC)")

                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_id ON audit_logs(tenant_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_created ON audit_logs(tenant_id, created_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_event ON audit_logs(tenant_id, event_type)")

                conn.commit()
        except sqlite3.DatabaseError:
            if self._path.exists():
                backup_path = self._path.with_suffix(self._path.suffix + ".backup")
                self._path.rename(backup_path)
                logger.info(f"Migrated old database from {self._path} to {backup_path}")
            self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self._path), timeout=5.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    async def get_incident_for_tenant(
        self,
        nexus_incident_id: str,
        tenant_id: str
    ) -> Optional[dict[str, Any]]:
        """Get single incident with tenant isolation."""
        if not tenant_id or not nexus_incident_id:
            raise ValueError("tenant_id and nexus_incident_id required")

        async with self._lock:
            def query():
                conn = self._get_connection()
                try:
                    row = conn.execute(
                        "SELECT * FROM incidents WHERE nexus_incident_id = ? AND tenant_id = ?",
                        (nexus_incident_id, tenant_id)
                    ).fetchone()

                    if not row:
                        return None

                    return {
                        'nexus_incident_id': row['nexus_incident_id'],
                        'tenant_id': row['tenant_id'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'data': json.loads(row['data'])
                    }
                finally:
                    conn.close()

            return await asyncio.to_thread(query)

    async def list_incidents_for_tenant(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """List incidents for tenant, most recent first."""
        if not tenant_id:
            raise ValueError("tenant_id required")

        limit = max(1, min(limit, 1000))
        offset = max(0, offset)

        async with self._lock:
            def query():
                conn = self._get_connection()
                try:
                    rows = conn.execute(
                        """
                        SELECT * FROM incidents
                        WHERE tenant_id = ?
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (tenant_id, limit, offset)
                    ).fetchall()

                    return [
                        {
                            'nexus_incident_id': row['nexus_incident_id'],
                            'tenant_id': row['tenant_id'],
                            'created_at': row['created_at'],
                            'updated_at': row['updated_at'],
                            'data': json.loads(row['data'])
                        }
                        for row in rows
                    ]
                finally:
                    conn.close()

            return await asyncio.to_thread(query)

    async def create_incident(
        self,
        nexus_incident_id: str,
        tenant_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create incident with tenant isolation."""
        if not tenant_id or not nexus_incident_id:
            raise ValueError("tenant_id and nexus_incident_id required")

        async with self._lock:
            def insert():
                conn = self._get_connection()
                try:
                    now = datetime.now(UTC).isoformat()
                    conn.execute(
                        """
                        INSERT INTO incidents
                        (nexus_incident_id, tenant_id, data, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (nexus_incident_id, tenant_id, json.dumps(data), now, now)
                    )
                    conn.commit()

                    return {
                        'nexus_incident_id': nexus_incident_id,
                        'tenant_id': tenant_id,
                        'created_at': now,
                        'updated_at': now,
                        'data': data
                    }
                finally:
                    conn.close()

            return await asyncio.to_thread(insert)

    async def update_incident(
        self,
        nexus_incident_id: str,
        tenant_id: str,
        data: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Update incident with tenant isolation."""
        if not tenant_id or not nexus_incident_id:
            raise ValueError("tenant_id and nexus_incident_id required")

        async with self._lock:
            def update():
                conn = self._get_connection()
                try:
                    # Check if exists (tenant isolation)
                    existing = conn.execute(
                        "SELECT * FROM incidents WHERE nexus_incident_id = ? AND tenant_id = ?",
                        (nexus_incident_id, tenant_id)
                    ).fetchone()

                    if not existing:
                        return None

                    now = datetime.now(UTC).isoformat()
                    conn.execute(
                        """
                        UPDATE incidents
                        SET data = ?, updated_at = ?
                        WHERE nexus_incident_id = ? AND tenant_id = ?
                        """,
                        (json.dumps(data), now, nexus_incident_id, tenant_id)
                    )
                    conn.commit()

                    row = conn.execute(
                        "SELECT * FROM incidents WHERE nexus_incident_id = ? AND tenant_id = ?",
                        (nexus_incident_id, tenant_id)
                    ).fetchone()

                    return {
                        'nexus_incident_id': row['nexus_incident_id'],
                        'tenant_id': row['tenant_id'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'data': json.loads(row['data'])
                    }
                finally:
                    conn.close()

            return await asyncio.to_thread(update)

    async def add_audit_log(
        self,
        event_type: str,
        tenant_id: str,
        user_id: Optional[str],
        data: dict[str, Any]
    ) -> int:
        """Add audit log entry."""
        if not event_type or not tenant_id:
            raise ValueError("event_type and tenant_id required")

        async with self._lock:
            def insert():
                conn = self._get_connection()
                try:
                    now = datetime.now(UTC).isoformat()
                    cursor = conn.execute(
                        """
                        INSERT INTO audit_logs
                        (event_type, tenant_id, user_id, data, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (event_type, tenant_id, user_id, json.dumps(data), now)
                    )
                    conn.commit()
                    return cursor.lastrowid
                finally:
                    conn.close()

            return await asyncio.to_thread(insert)

class DatabaseSession:
    """Database session with repository interface."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self.incidents = IncidentRepository(database)

    async def close(self) -> None:
        """Close session (SQLite handles cleanup)."""
        pass


def create_session_factory(config: AppConfig) -> Callable[[], DatabaseSession]:
    """Create a session factory function."""
    database = SQLiteDatabase(config)

    def factory() -> DatabaseSession:
        return DatabaseSession(database)

    return factory


async def get_db(request: Request) -> AsyncIterator[DatabaseSession]:
    """FastAPI dependency for database session."""
    session = request.app.state.db_session_factory()
    try:
        yield session
    finally:
        await session.close()
