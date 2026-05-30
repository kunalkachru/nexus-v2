import asyncio
import json
from pathlib import Path

from incidents.catalogue import load_incident_types
from server.integrations.alerts import AlertNormalizer
from server.integrations.deployments import DeploymentLookupService
from server.integrations.models import IncomingIncidentWebhook
from server.models import NormalizedAlertEnvelope
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


def test_deployment_lookup_returns_file_backed_recent_deployments(tmp_path: Path) -> None:
    async def scenario() -> None:
        deployments_path = tmp_path / "deployments.json"
        deployments_path.write_text(
            json.dumps(
                {
                    "deployments": [
                        {
                            "service": "payment-svc",
                            "version": "2026.05.30.1",
                            "change": "Retry middleware patch",
                            "time": "2026-05-30T09:10:00Z",
                        },
                        {
                            "service": "payment-svc",
                            "version": "2026.05.29.9",
                            "change": "Feature flag rollout",
                            "time": "2026-05-29T09:10:00Z",
                        },
                        {
                            "service": "other-svc",
                            "version": "2026.05.28.4",
                            "change": "Ignored",
                            "time": "2026-05-28T09:10:00Z",
                        },
                    ]
                }
            )
        )
        deployments = await DeploymentLookupService(deployments_path=deployments_path).get_recent_deployments("payment-svc")

        assert len(deployments) == 2
        assert deployments[0]["version"] == "2026.05.30.1"
        assert deployments[1]["version"] == "2026.05.29.9"

    asyncio.run(scenario())


def test_observability_service_uses_file_backed_catalog_and_deployments(tmp_path: Path) -> None:
    async def scenario() -> None:
        incident = load_incident_types()[0]
        catalog_path = tmp_path / "observability.json"
        deployments_path = tmp_path / "deployments.json"
        catalog_path.write_text(
            json.dumps(
                {
                    "incidents": {
                        incident.id: {
                            "logs": ["loki: raw log line from file-backed catalog"],
                            "metrics": ["latency 420ms"],
                            "traces": ["service graph: api -> db"],
                            "deployments": [
                                {
                                    "service": incident.system_context.service,
                                    "version": "2026.05.30.2",
                                    "change": "File-backed release feed",
                                }
                            ],
                            "provenance": {
                                "logs": ["loki: file-backed datasource"],
                                "metrics": ["datadog: file-backed datasource"],
                                "deployment": ["release metadata: file-backed datasource"],
                            },
                            "evidence_sources": [
                                {
                                    "source": "loki",
                                    "signal": "logs",
                                    "count": 1,
                                    "summary": "File-backed catalog logs",
                                    "detail": "loki: raw log line from file-backed catalog",
                                }
                            ],
                        }
                    }
                }
            )
        )
        deployments_path.write_text(
            json.dumps(
                {
                    "deployments": [
                        {
                            "service": incident.system_context.service,
                            "version": "2026.05.30.3",
                            "change": "Deployment feed from adapter",
                            "time": "2026-05-30T12:00:00Z",
                        }
                    ]
                }
            )
        )

        deployment_lookup = DeploymentLookupService(deployments_path=deployments_path)
        service = ObservabilityService(
            evidence_catalog_path=catalog_path,
            deployment_lookup=deployment_lookup,
        )

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

        assert any("file-backed" in signal for signal in context.signals["logs"])
        assert any("2026.05.30.3" in signal for signal in context.signals["deployment"])
        assert context.signal_provenance["logs"] == ["loki: file-backed datasource"]
        assert context.evidence_sources[0]["detail"] == "loki: raw log line from file-backed catalog"

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
