from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from server.models import IncidentRecord

if TYPE_CHECKING:
    from server.db import SQLiteDatabase


class IncidentRepository:
    """Database repository for incidents with SQLite backing."""

    def __init__(self, database: "SQLiteDatabase") -> None:
        """
        Initialize repository with SQLite database.

        Args:
            database: SQLiteDatabase instance for persistence
        """
        self._database = database
        self._tenant_id = "tenant-system"  # Default tenant (can be overridden)

    async def create_incident(
        self,
        *,
        external_id: str,
        title: str,
        severity: str,
        tenant_id: str = "tenant-system",
        source: str | None = None,
        service: str = "",
        raw_input_text: str = "",
        normalized_evidence: dict[str, object] | None = None,
    ) -> IncidentRecord:
        """Create a new incident in the database."""
        timestamp = datetime.now(timezone.utc).isoformat()
        nexus_incident_id = f"nxs_{uuid4().hex[:12]}"

        # Create Pydantic model
        incident = IncidentRecord(
            nexus_incident_id=nexus_incident_id,
            external_id=external_id,
            title=title,
            severity=severity,
            status="investigating",
            tenant_id=tenant_id,
            source=source,
            service=service,
            raw_input_text=raw_input_text,
            normalized_evidence=normalized_evidence or {},
            guardian_decision="pending",
            guardian_reasoning="",
            guardian_reviewed_at="",
            guardian_policy_id="",
            guardian_policy_name="",
            guardian_policy_basis="",
            created_at=timestamp,
            updated_at=timestamp,
        )

        # Persist to database
        data = incident.model_dump(mode="json")
        await self._database.create_incident(nexus_incident_id, tenant_id, data)

        return incident

    async def get_incident(self, nexus_incident_id: str) -> IncidentRecord | None:
        """Get incident by ID (system tenant)."""
        incident_data = await self._database.get_incident_for_tenant(
            nexus_incident_id, self._tenant_id
        )
        if not incident_data:
            return None
        return IncidentRecord.model_validate(incident_data['data'])

    async def get_incident_for_tenant(
        self,
        nexus_incident_id: str,
        tenant_id: str,
    ) -> IncidentRecord | None:
        """Get incident for specific tenant with isolation."""
        incident_data = await self._database.get_incident_for_tenant(
            nexus_incident_id, tenant_id
        )
        if not incident_data:
            return None
        return IncidentRecord.model_validate(incident_data['data'])

    async def list_incidents(self) -> list[IncidentRecord]:
        """List all incidents (system tenant)."""
        incidents_data = await self._database.list_incidents_for_tenant(self._tenant_id)
        return [
            IncidentRecord.model_validate(incident['data'])
            for incident in incidents_data
        ]

    async def list_incidents_for_tenant(self, tenant_id: str) -> list[IncidentRecord]:
        """List incidents for specific tenant."""
        incidents_data = await self._database.list_incidents_for_tenant(tenant_id)
        return [
            IncidentRecord.model_validate(incident['data'])
            for incident in incidents_data
        ]

    async def update_incident_status(
        self,
        nexus_incident_id: str,
        *,
        status: str,
        tenant_id: str | None = None,
        guardian_decision: str | None = None,
        guardian_reasoning: str | None = None,
        guardian_reviewed_at: str | None = None,
        guardian_policy_id: str | None = None,
        guardian_policy_name: str | None = None,
        guardian_policy_basis: str | None = None,
    ) -> IncidentRecord | None:
        """Update incident status and guardian decision."""
        # Use provided tenant_id or fall back to default
        lookup_tenant_id = tenant_id or self._tenant_id

        # Get existing incident
        incident_data = await self._database.get_incident_for_tenant(
            nexus_incident_id, lookup_tenant_id
        )
        if not incident_data:
            return None

        incident = IncidentRecord.model_validate(incident_data['data'])

        # Build updates
        updates: dict[str, object] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if guardian_decision is not None:
            updates["guardian_decision"] = guardian_decision
        if guardian_reasoning is not None:
            updates["guardian_reasoning"] = guardian_reasoning
        if guardian_reviewed_at is not None:
            updates["guardian_reviewed_at"] = guardian_reviewed_at
        if guardian_policy_id is not None:
            updates["guardian_policy_id"] = guardian_policy_id
        if guardian_policy_name is not None:
            updates["guardian_policy_name"] = guardian_policy_name
        if guardian_policy_basis is not None:
            updates["guardian_policy_basis"] = guardian_policy_basis

        updated = incident.model_copy(update=updates)

        # Persist to database
        data = updated.model_dump(mode="json")
        result = await self._database.update_incident(
            nexus_incident_id, lookup_tenant_id, data
        )

        return updated if result else None

    async def update_incident_normalized_evidence(
        self,
        nexus_incident_id: str,
        *,
        normalized_evidence: dict[str, object],
    ) -> IncidentRecord | None:
        """Update incident normalized evidence."""
        # Get existing incident
        incident_data = await self._database.get_incident_for_tenant(
            nexus_incident_id, self._tenant_id
        )
        if not incident_data:
            return None

        incident = IncidentRecord.model_validate(incident_data['data'])

        updated = incident.model_copy(
            update={
                "normalized_evidence": normalized_evidence,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Persist to database
        data = updated.model_dump(mode="json")
        result = await self._database.update_incident(
            nexus_incident_id, self._tenant_id, data
        )

        return updated if result else None

    async def append_incident_replay_evidence(
        self,
        nexus_incident_id: str,
        *,
        latest_replay: dict[str, object],
        replay_entry: dict[str, object],
        replay_limit: int = 5,
    ) -> IncidentRecord | None:
        """Append replay evidence to incident."""
        # Get existing incident
        incident_data = await self._database.get_incident_for_tenant(
            nexus_incident_id, self._tenant_id
        )
        if not incident_data:
            return None

        incident = IncidentRecord.model_validate(incident_data['data'])

        normalized_evidence = dict(incident.normalized_evidence or {})
        existing_history = normalized_evidence.get("replay_history")
        history = []
        if isinstance(existing_history, list):
            history = [dict(item) for item in existing_history if isinstance(item, dict)]
        history.insert(0, dict(replay_entry))
        normalized_evidence["latest_replay"] = dict(latest_replay)
        normalized_evidence["replay_history"] = history[: max(1, replay_limit)]

        updated = incident.model_copy(
            update={
                "normalized_evidence": normalized_evidence,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Persist to database
        data = updated.model_dump(mode="json")
        result = await self._database.update_incident(
            nexus_incident_id, self._tenant_id, data
        )

        return updated if result else None
