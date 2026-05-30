import asyncio

from server.integrations.alerts import AlertNormalizer
from server.integrations.deployments import DeploymentLookupService
from server.integrations.models import IncomingIncidentWebhook
from server.services.incidents import IncidentService
from server.services.observability import ObservabilityService


def test_alert_normalizer_maps_provider_payload_to_phase2_envelope() -> None:
    payload = IncomingIncidentWebhook.model_validate(
        {
            "incident_id": "inc_xyz",
            "title": "Payment API timeout",
            "severity": "P1",
            "detected_at": "2026-05-25T14:32:00Z",
            "monitoring_source": "datadog",
            "metrics": {"service": "payment-svc", "error_rate": 0.45},
        }
    )

    envelope = AlertNormalizer().normalize(payload)

    assert envelope.source == "datadog"
    assert envelope.external_id == "inc_xyz"
    assert envelope.service == "payment-svc"
    assert envelope.observed_values["error_rate"] == 0.45


def test_alert_normalizer_uses_prometheus_job_when_service_missing() -> None:
    payload = IncomingIncidentWebhook.model_validate(
        {
            "incident_id": "inc_prom",
            "title": "Payment API timeout",
            "severity": "P1",
            "detected_at": "2026-05-25T14:32:00Z",
            "monitoring_source": "prometheus",
            "metrics": {"job": "payments-api", "alertname": "HighLatency"},
        }
    )

    envelope = AlertNormalizer().normalize(payload)

    assert envelope.source == "prometheus"
    assert envelope.service == "payments-api"
    assert envelope.observed_values["alertname"] == "HighLatency"


def test_deployment_lookup_returns_placeholder_recent_deployments() -> None:
    async def scenario() -> None:
        deployments = await DeploymentLookupService().get_recent_deployments("payment-svc")

        assert deployments == []

    asyncio.run(scenario())


def test_incident_service_enriches_created_incident_with_recent_deployments() -> None:
    class StubIncidentRepository:
        async def create_incident(
            self,
            *,
            external_id: str,
            title: str,
            severity: str,
            source: str | None = None,
            service: str = "",
        ):
            return {
                "nexus_incident_id": "nxs_123",
                "external_id": external_id,
                "title": title,
                "severity": severity,
                "status": "investigating",
                "source": source,
                "service": service,
            }

    class StubSession:
        def __init__(self) -> None:
            self.incidents = StubIncidentRepository()

    class StubDeploymentLookupService:
        async def get_recent_deployments(self, service_name: str):
            return [
                {
                    "service": service_name,
                    "version": "2026.05.25.1",
                    "environment": "prod",
                }
            ]

    async def scenario() -> None:
        payload = IncomingIncidentWebhook.model_validate(
            {
                "incident_id": "inc_xyz",
                "title": "Payment API timeout",
                "severity": "P1",
                "detected_at": "2026-05-25T14:32:00Z",
                "monitoring_source": "prometheus",
                "metrics": {"service": "payment-svc", "error_rate": 0.45},
            }
        )

        service = IncidentService(
            session=StubSession(),
            alert_normalizer=AlertNormalizer(),
            deployment_lookup=StubDeploymentLookupService(),
            observability=ObservabilityService(),
        )

        created = await service.create_incident_from_webhook(payload)

        assert created["nexus_incident_id"] == "nxs_123"
        assert created["source"] == "prometheus"
        assert created["recent_deployments"] == [
            {
                "service": "payment-svc",
                "version": "2026.05.25.1",
                "environment": "prod",
            }
        ]

    asyncio.run(scenario())


def test_incident_service_enriches_status_response_with_recent_deployments() -> None:
    class StubIncidentRepository:
        async def get_incident(self, nexus_incident_id: str):
            return {
                "nexus_incident_id": nexus_incident_id,
                "external_id": "inc_xyz",
                "title": "Payment API timeout",
                "severity": "P1",
                "status": "investigating",
                "source": "datadog",
                "service": "payment-svc",
            }

    class StubSession:
        def __init__(self) -> None:
            self.incidents = StubIncidentRepository()

    class StubDeploymentLookupService:
        async def get_recent_deployments(self, service_name: str):
            return [{"service": service_name, "version": "2026.05.25.2"}]

    async def scenario() -> None:
        service = IncidentService(
            session=StubSession(),
            alert_normalizer=AlertNormalizer(),
            deployment_lookup=StubDeploymentLookupService(),
            observability=ObservabilityService(),
        )

        payload = await service.get_incident_status("nxs_123")

        assert payload["nexus_incident_id"] == "nxs_123"
        assert payload["source"] == "datadog"
        assert payload["recent_deployments"] == [
            {"service": "payment-svc", "version": "2026.05.25.2"}
        ]

    asyncio.run(scenario())
