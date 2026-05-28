from fastapi import HTTPException

from server.integrations.alerts import AlertNormalizer
from server.integrations.deployments import DeploymentLookupService
from server.integrations.models import IncomingIncidentWebhook
from server.models import IncidentLifecycleResponse, IncidentRecord


class IncidentService:
    def __init__(
        self,
        *,
        session,
        alert_normalizer: AlertNormalizer,
        deployment_lookup: DeploymentLookupService,
    ) -> None:
        self._session = session
        self._alert_normalizer = alert_normalizer
        self._deployment_lookup = deployment_lookup

    async def create_incident_from_webhook(
        self,
        payload: IncomingIncidentWebhook,
    ) -> dict[str, object]:
        envelope = self._alert_normalizer.normalize(payload)
        created = await self._session.incidents.create_incident(
            external_id=envelope.external_id,
            title=envelope.title,
            severity=envelope.severity,
            source=envelope.source,
            service=envelope.service,
        )
        incident = IncidentRecord.model_validate(created)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(
            envelope.service
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=incident.nexus_incident_id,
            external_id=incident.external_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source=envelope.source,
            recent_deployments=recent_deployments,
        )
        return response.model_dump(mode="json")

    async def get_incident_status(self, nexus_incident_id: str) -> dict[str, object]:
        loaded = await self._session.incidents.get_incident(nexus_incident_id)
        if loaded is None:
            raise HTTPException(status_code=404, detail="incident not found")

        incident = IncidentRecord.model_validate(loaded)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(
            incident.service
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=incident.nexus_incident_id,
            external_id=incident.external_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source=incident.source,
            recent_deployments=recent_deployments,
        )
        return response.model_dump(mode="json")
