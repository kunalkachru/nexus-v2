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
        signal_provenance = self._signal_provenance(details)

        return IncidentContext(
            incident=incident,
            incident_id=incident.id,
            raw_symptoms=list(incident.symptoms),
            system_context=incident.system_context,
            signals=signals,
            signal_provenance=signal_provenance,
            evidence_sources=self._evidence_sources(details),
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

    def build_evidence_sources(self, incident_id: str) -> list[dict[str, object]]:
        details = self._incident_details.get(incident_id, {})
        return self._evidence_sources(details)

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

    def _signal_provenance(self, details: dict[str, object]) -> dict[str, list[str]]:
        recent_logs = list(details.get("recent_logs", []))
        metrics = list(details.get("metrics", []))
        deployments = list(details.get("recent_deployments", []))
        related_services = list(details.get("related_services", []))
        return {
            "logs": [f"loki: {len(recent_logs)} correlated log lines"] if recent_logs else ["loki: no correlated log lines"],
            "metrics": [f"datadog / prometheus: {len(metrics)} aligned metric signals"] if metrics else ["datadog / prometheus: no metrics"],
            "traces": [f"service graph: {len(related_services)} dependent services traced"] if related_services else ["service graph: no dependent services"],
            "deployment": [f"release metadata: {len(deployments)} deployments enriched"] if deployments else ["release metadata: no deployment changes"],
        }

    def _evidence_sources(self, details: dict[str, object]) -> list[dict[str, object]]:
        logs = list(details.get("recent_logs", []))
        metrics = list(details.get("metrics", []))
        deployments = list(details.get("recent_deployments", []))
        related_services = list(details.get("related_services", []))
        return [
            {
                "source": "loki",
                "signal": "logs",
                "count": len(logs),
                "summary": "Correlated log lines from the incident window.",
                "detail": logs[0] if logs else "No log lines available.",
            },
            {
                "source": "datadog",
                "signal": "metrics",
                "count": len(metrics),
                "summary": "Metric series normalized into the incident narrative.",
                "detail": self._metric_signals(metrics)[0] if metrics else "No metric series available.",
            },
            {
                "source": "deployment history",
                "signal": "release",
                "count": len(deployments),
                "summary": "Recent release metadata fused into the operator view.",
                "detail": self._deployment_signals(deployments)[0] if deployments else "No deployment metadata available.",
            },
            {
                "source": "service graph",
                "signal": "traces",
                "count": len(related_services),
                "summary": "Dependency paths used to explain the blast radius.",
                "detail": related_services[0] if related_services else "No dependency graph available.",
            },
        ]
