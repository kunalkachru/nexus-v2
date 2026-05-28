import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator, Callable

from fastapi import Request
from pydantic import ValidationError

from server.config import AppConfig
from server.models import IncidentRecord
from server.repositories import IncidentRepository

logger = logging.getLogger(__name__)


class _MemoryDatabase:
    def __init__(self, config: AppConfig) -> None:
        self._path = config.database_path
        self.incidents: dict[str, IncidentRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return

        try:
            payload = json.loads(self._path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            logger.exception("invalid persistence payload at %s", self._path)
            self.incidents = {}
            return

        if not isinstance(payload, dict):
            logger.error("persistence payload at %s must be a JSON object", self._path)
            self.incidents = {}
            return

        incidents = payload.get("incidents", {})
        if not isinstance(incidents, dict):
            logger.error("incidents payload at %s must be a JSON object", self._path)
            self.incidents = {}
            return

        loaded_incidents: dict[str, IncidentRecord] = {}
        for incident_id, record in incidents.items():
            try:
                loaded_incidents[incident_id] = IncidentRecord.model_validate(record)
            except ValidationError:
                logger.exception(
                    "invalid persisted incident record %s at %s",
                    incident_id,
                    self._path,
                )
        self.incidents = loaded_incidents

    async def flush(self) -> None:
        await asyncio.to_thread(self._flush_sync)

    def _flush_sync(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "incidents": {
                incident_id: record.model_dump(mode="json")
                for incident_id, record in self.incidents.items()
            }
        }
        temp_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        with temp_path.open("w") as file_handle:
            json.dump(payload, file_handle, indent=2, sort_keys=True)
            file_handle.flush()
            os.fsync(file_handle.fileno())
        temp_path.replace(self._path)

class DatabaseSession:
    def __init__(self, database: _MemoryDatabase) -> None:
        self._database = database
        self.incidents = IncidentRepository(self._database.incidents, self._database.flush)

    async def close(self) -> None:
        return None


def create_session_factory(config: AppConfig) -> Callable[[], DatabaseSession]:
    database = _MemoryDatabase(config)

    def factory() -> DatabaseSession:
        return DatabaseSession(database)

    return factory


async def get_db(request: Request) -> AsyncIterator[DatabaseSession]:
    session = request.app.state.db_session_factory()
    try:
        yield session
    finally:
        await session.close()
