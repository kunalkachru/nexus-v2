from __future__ import annotations

import asyncio

from incidents.catalogue import load_incident_types
from server.incident_payloads import INCIDENT_DETAILS
from server.models import IncidentContext, IncidentDefinition, NormalizedAlertEnvelope


class ObservabilityService:
    """Deterministic evidence adapter that resolves alert envelopes into incident context."""

    def __init__(
        self,
        *,
        incidents_by_id: dict[str, IncidentDefinition] | None = None,
        incident_details: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self._incidents_by_id = incidents_by_id or {
            incident.id: incident for incident in load_incident_types()
        }
        self._incident_details = incident_details or INCIDENT_DETAILS

    async def fetch_incident_context(self, alert_envelope: NormalizedAlertEnvelope) -> IncidentContext:
        incident = await self.resolve_incident_definition(alert_envelope.external_id)
        details = self._incident_details.get(incident.id, {})
        signals = {
            "logs": list(details.get("recent_logs", [])),
            "metrics": self._metric_signals(details.get("metrics", [])),
            "traces": self._trace_signals(details),
            "deployment": self._deployment_signals(details.get("recent_deployments", [])),
        }

        return IncidentContext(
            incident=incident,
            incident_id=incident.id,
            raw_symptoms=list(incident.symptoms),
            system_context=incident.system_context,
            signals=signals,
        )

    async def fetch_supporting_signals(
        self,
        *,
        incident_id: str,
        requested_sources: list[str],
    ) -> dict[str, list[str]]:
        await asyncio.sleep(0)
        details = self._incident_details.get(incident_id, {})
        available = {
            "logs": list(details.get("recent_logs", [])),
            "metrics": self._metric_signals(details.get("metrics", [])),
            "traces": self._trace_signals(details),
            "deployment": self._deployment_signals(details.get("recent_deployments", [])),
        }
        return {source: available.get(source, []) for source in requested_sources}

    async def resolve_incident_definition(self, external_id: str) -> IncidentDefinition:
        await asyncio.sleep(0)
        try:
            return self._incidents_by_id[external_id]
        except KeyError as exc:
            raise ValueError(f"unknown incident_id: {external_id}") from exc

    def _metric_signals(self, metrics: object) -> list[str]:
        metric_items = metrics if isinstance(metrics, list) else []
        signals: list[str] = []
        for metric in metric_items:
            if not isinstance(metric, dict):
                continue
            name = str(metric.get("name", "")).strip()
            current = metric.get("current")
            unit = str(metric.get("unit", "")).strip()
            if name:
                signals.append(f"{name} {current}{unit}".strip())
        return signals

    def _trace_signals(self, details: dict[str, object]) -> list[str]:
        related_services = details.get("related_services", [])
        if not isinstance(related_services, list):
            return []
        return [f"service dependency observed: {service}" for service in related_services]

    def _deployment_signals(self, deployments: object) -> list[str]:
        deployment_items = deployments if isinstance(deployments, list) else []
        signals: list[str] = []
        for deployment in deployment_items:
            if not isinstance(deployment, dict):
                continue
            service = str(deployment.get("service", "")).strip()
            version = str(deployment.get("version", "")).strip()
            change = str(deployment.get("change", "")).strip()
            if service:
                signals.append(f"deployment {service} {version} {change}".strip())
        return signals
