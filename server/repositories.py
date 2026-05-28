from collections.abc import Callable
from typing import Any
from uuid import uuid4

from server.models import IncidentRecord


class IncidentRepository:
    def __init__(
        self,
        incident_store: dict[str, IncidentRecord],
        flush_callback: Callable[[], Any],
    ) -> None:
        self._incident_store = incident_store
        self._flush_callback = flush_callback

    async def create_incident(
        self,
        *,
        external_id: str,
        title: str,
        severity: str,
        source: str | None = None,
        service: str = "",
    ) -> IncidentRecord:
        incident = IncidentRecord(
            nexus_incident_id=f"nxs_{uuid4().hex[:12]}",
            external_id=external_id,
            title=title,
            severity=severity,
            status="investigating",
            source=source,
            service=service,
        )
        self._incident_store[incident.nexus_incident_id] = incident
        try:
            await self._flush_callback()
        except Exception:
            self._incident_store.pop(incident.nexus_incident_id, None)
            raise
        return incident

    async def get_incident(self, nexus_incident_id: str) -> IncidentRecord | None:
        return self._incident_store.get(nexus_incident_id)
