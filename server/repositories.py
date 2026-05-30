from collections.abc import Callable
from datetime import datetime, timezone
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
        tenant_id: str = "tenant-system",
        source: str | None = None,
        service: str = "",
    ) -> IncidentRecord:
        timestamp = datetime.now(timezone.utc).isoformat()
        incident = IncidentRecord(
            nexus_incident_id=f"nxs_{uuid4().hex[:12]}",
            external_id=external_id,
            title=title,
            severity=severity,
            status="investigating",
            tenant_id=tenant_id,
            source=source,
            service=service,
            created_at=timestamp,
            updated_at=timestamp,
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

    async def get_incident_for_tenant(
        self,
        nexus_incident_id: str,
        tenant_id: str,
    ) -> IncidentRecord | None:
        incident = self._incident_store.get(nexus_incident_id)
        if incident is None or incident.tenant_id != tenant_id:
            return None
        return incident

    async def list_incidents(self) -> list[IncidentRecord]:
        return list(self._incident_store.values())

    async def list_incidents_for_tenant(self, tenant_id: str) -> list[IncidentRecord]:
        return [incident for incident in self._incident_store.values() if incident.tenant_id == tenant_id]

    async def update_incident_status(
        self,
        nexus_incident_id: str,
        *,
        status: str,
    ) -> IncidentRecord | None:
        incident = self._incident_store.get(nexus_incident_id)
        if incident is None:
            return None

        updated = incident.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self._incident_store[nexus_incident_id] = updated
        try:
            await self._flush_callback()
        except Exception:
            self._incident_store[nexus_incident_id] = incident
            raise
        return updated
