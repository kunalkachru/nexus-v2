import asyncio

from incidents.catalogue import load_incident_types
from server.models import NormalizedAlertEnvelope
from server.services.observability import ObservabilityService


def test_observability_service_builds_incident_context_from_alert_envelope() -> None:
    async def scenario() -> None:
        incident = load_incident_types()[1]
        service = ObservabilityService()

        context = await service.fetch_incident_context(
            NormalizedAlertEnvelope(
                source="datadog",
                external_id=incident.id,
                title=incident.name,
                severity="P1",
                service=incident.system_context.service,
                detected_at="2026-05-28T10:22:00Z",
                observed_values={"service": incident.system_context.service},
            )
        )

        assert context.incident_id == incident.id
        assert context.system_context.service == incident.system_context.service
        assert context.raw_symptoms
        assert context.signals["logs"]
        assert context.signals["metrics"]
        assert "deployment" in context.signals

    asyncio.run(scenario())
