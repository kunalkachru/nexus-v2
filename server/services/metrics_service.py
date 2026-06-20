from datetime import datetime, timezone
from server.db import SQLiteDatabase


class PilotMetricsService:
    """Service for computing pilot program metrics from incident data."""

    async def compute_pilot_metrics(self, tenant_id: str, database: SQLiteDatabase) -> dict[str, object]:
        """
        Compute pilot metrics for a tenant by querying incident data.

        Args:
            tenant_id: The tenant ID to compute metrics for
            database: The SQLiteDatabase instance

        Returns:
            Dictionary with metrics including:
            - incidents_handled: count of all incidents
            - incidents_runtime_backed: count with evidence_posture='runtime_backed'
            - incidents_inferred: count with evidence_posture='inferred_only'
            - handoff_completion_count: count with handoff_status='sent'
            - total_triage_time_saved_minutes: incidents_handled * 15 (15 min per incident)
            - computed_at: ISO format datetime when metrics were computed
        """
        incidents = await database.list_incidents_for_tenant(tenant_id, limit=10000)

        incidents_handled = len(incidents)
        incidents_runtime_backed = 0
        incidents_inferred = 0
        handoff_completion_count = 0

        for incident in incidents:
            data = incident.get("data", {})
            evidence_posture = data.get("evidence_posture")
            handoff_status = data.get("handoff_status")

            if evidence_posture == "runtime_backed":
                incidents_runtime_backed += 1
            elif evidence_posture == "inferred_only":
                incidents_inferred += 1

            if handoff_status == "sent":
                handoff_completion_count += 1

        # Calculate triage time: 15 minutes per incident handled
        total_triage_time_saved_minutes = incidents_handled * 15

        return {
            "incidents_handled": incidents_handled,
            "incidents_runtime_backed": incidents_runtime_backed,
            "incidents_inferred": incidents_inferred,
            "handoff_completion_count": handoff_completion_count,
            "total_triage_time_saved_minutes": total_triage_time_saved_minutes,
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
