from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from incidents.catalogue import load_incident_types
from server.incident_payloads import INCIDENT_DETAILS
from server.integrations.deployments import DeploymentLookupService
from server.models import IncidentContext, IncidentDefinition, NormalizedAlertEnvelope


class ObservabilityService:
    """Evidence adapter that fuses catalog fixtures with file-backed source snapshots."""

    def __init__(
        self,
        *,
        incidents_by_id: dict[str, IncidentDefinition] | None = None,
        incident_details: dict[str, dict[str, object]] | None = None,
        evidence_catalog_path: Path | None = None,
        deployment_lookup: DeploymentLookupService | None = None,
    ) -> None:
        self._incidents_by_id = incidents_by_id or {
            incident.id: incident for incident in load_incident_types()
        }
        self._incident_details = incident_details or INCIDENT_DETAILS
        self._evidence_catalog_path = evidence_catalog_path or Path(
            os.environ.get("NEXUS_OBSERVABILITY_CATALOG_PATH", "artifacts/observability.json")
        )
        self._deployment_lookup = deployment_lookup or DeploymentLookupService()
        self._catalog_cache: dict[str, object] | None = None

    async def fetch_incident_context(self, alert_envelope: NormalizedAlertEnvelope) -> IncidentContext:
        incident = await self.resolve_incident_definition(alert_envelope.external_id)
        details = self._incident_details.get(incident.id, {})
        catalog_entry = self._catalog_entry(incident.id, incident.system_context.service)
        deployments = await self._deployment_lookup.get_recent_deployments(incident.system_context.service)
        signals = {
            "logs": self._merge_signals(details.get("recent_logs", []), catalog_entry.get("logs")),
            "metrics": self._merge_signals(
                self._metric_signals(details.get("metrics", [])),
                catalog_entry.get("metrics"),
            ),
            "traces": self._merge_signals(self._trace_signals(details), catalog_entry.get("traces")),
            "deployment": self._merge_signals(
                self._deployment_signals(details.get("recent_deployments", [])),
                self._deployment_signals(catalog_entry.get("deployments", [])),
                self._deployment_signals(deployments),
            ),
        }
        signal_provenance = self._signal_provenance(details, catalog_entry, deployments)

        return IncidentContext(
            incident=incident,
            incident_id=incident.id,
            raw_symptoms=list(incident.symptoms),
            system_context=incident.system_context,
            signals=signals,
            signal_provenance=signal_provenance,
            evidence_sources=self._evidence_sources(details, catalog_entry, deployments),
        )

    async def fetch_supporting_signals(
        self,
        *,
        incident_id: str,
        requested_sources: list[str],
    ) -> dict[str, list[str]]:
        await asyncio.sleep(0)
        details = self._incident_details.get(incident_id, {})
        catalog_entry = self._catalog_entry(incident_id, str(details.get("service", "")))
        available = {
            "logs": self._merge_signals(details.get("recent_logs", []), catalog_entry.get("logs")),
            "metrics": self._merge_signals(
                self._metric_signals(details.get("metrics", [])),
                catalog_entry.get("metrics"),
            ),
            "traces": self._merge_signals(self._trace_signals(details), catalog_entry.get("traces")),
            "deployment": self._merge_signals(
                self._deployment_signals(details.get("recent_deployments", [])),
                self._deployment_signals(catalog_entry.get("deployments", [])),
            ),
        }
        return {source: available.get(source, []) for source in requested_sources}

    def build_evidence_sources(self, incident_id: str) -> list[dict[str, object]]:
        details = self._incident_details.get(incident_id, {})
        catalog_entry = self._catalog_entry(incident_id, str(details.get("service", "")))
        return self._evidence_sources(details, catalog_entry, [])

    def build_live_evidence_sources(
        self,
        *,
        incident_id: str,
        service: str,
        source_channel: str,
        audit_logs: list[dict[str, object]],
        recent_deployments: list[dict[str, object]],
        timeline: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        latest_audit = audit_logs[-1] if audit_logs else {}
        latest_timeline = timeline[-1] if timeline else {}
        return [
            {
                "source": "incident record",
                "signal": "intake",
                "count": 1,
                "summary": "Authenticated live incident record from the operator console.",
                "detail": f"{incident_id} opened through {source_channel} for {service}.",
            },
            {
                "source": "audit trail",
                "signal": "governance",
                "count": len(audit_logs),
                "summary": "Live audit log entries captured from the backend.",
                "detail": latest_audit.get("event_type", "No audit events available."),
            },
            {
                "source": "workflow timeline",
                "signal": "orchestration",
                "count": len(timeline),
                "summary": "Incident lifecycle states produced by the live status contract.",
                "detail": latest_timeline.get("summary", "No workflow timeline available."),
            },
            {
                "source": "deployment metadata",
                "signal": "release",
                "count": len(recent_deployments),
                "summary": "Recent deployment lookups fused into the incident context.",
                "detail": (
                    f"{recent_deployments[0].get('service', service)} "
                    f"{recent_deployments[0].get('version', 'n/a')}"
                    if recent_deployments
                    else "No deployment metadata available."
                ),
            },
        ]

    async def resolve_incident_definition(self, external_id: str) -> IncidentDefinition:
        await asyncio.sleep(0)
        try:
            return self._incidents_by_id[external_id]
        except KeyError as exc:
            raise ValueError(f"unknown incident_id: {external_id}") from exc

    def _load_catalog(self) -> dict[str, object]:
        if self._catalog_cache is not None:
            return dict(self._catalog_cache)

        path = self._evidence_catalog_path
        if not path.exists():
            self._catalog_cache = {}
            return {}

        try:
            payload = json.loads(path.read_text())
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self._catalog_cache = {}
            return {}

        if isinstance(payload, dict):
            self._catalog_cache = payload
            return dict(payload)

        self._catalog_cache = {}
        return {}

    def _catalog_entry(self, incident_id: str, service: str) -> dict[str, object]:
        catalog = self._load_catalog()
        for section_name in ("incidents", "services"):
            section = catalog.get(section_name, {})
            if not isinstance(section, dict):
                continue
            for key in (incident_id, service):
                entry = section.get(key)
                if isinstance(entry, dict):
                    return dict(entry)
        return {}

    def _merge_signals(self, *signal_groups: object) -> list[str]:
        merged: list[str] = []
        for group in signal_groups:
            if isinstance(group, list):
                for item in group:
                    if isinstance(item, str) and item.strip():
                        merged.append(item.strip())
        seen: set[str] = set()
        unique: list[str] = []
        for signal in merged:
            if signal in seen:
                continue
            seen.add(signal)
            unique.append(signal)
        return unique

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

    def _signal_provenance(
        self,
        details: dict[str, object],
        catalog_entry: dict[str, object],
        deployments: list[dict[str, object]],
    ) -> dict[str, list[str]]:
        recent_logs = list(details.get("recent_logs", []))
        metrics = list(details.get("metrics", []))
        related_services = list(details.get("related_services", []))
        provenance = catalog_entry.get("provenance", {})
        provenance_map = provenance if isinstance(provenance, dict) else {}
        return {
            "logs": self._provenance_line(
                provenance_map.get("logs"),
                f"loki: {len(recent_logs)} correlated log lines" if recent_logs else "loki: no correlated log lines",
            ),
            "metrics": self._provenance_line(
                provenance_map.get("metrics"),
                (
                    f"datadog / prometheus: {len(metrics)} aligned metric signals"
                    if metrics
                    else "datadog / prometheus: no metrics"
                ),
            ),
            "traces": self._provenance_line(
                provenance_map.get("traces"),
                (
                    f"service graph: {len(related_services)} dependent services traced"
                    if related_services
                    else "service graph: no dependent services"
                ),
            ),
            "deployment": self._provenance_line(
                provenance_map.get("deployment"),
                (
                    f"release metadata: {len(deployments)} deployments enriched"
                    if deployments
                    else "release metadata: no deployment changes"
                ),
            ),
        }

    def _provenance_line(self, catalog_value: object, fallback: str) -> list[str]:
        values: list[str] = []
        if isinstance(catalog_value, list):
            values = [str(item).strip() for item in catalog_value if str(item).strip()]
        elif isinstance(catalog_value, str) and catalog_value.strip():
            values = [catalog_value.strip()]
        return values or [fallback]

    def _evidence_sources(
        self,
        details: dict[str, object],
        catalog_entry: dict[str, object],
        deployments: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        logs = self._merge_signals(details.get("recent_logs", []), catalog_entry.get("logs"))
        metrics = self._merge_signals(self._metric_signals(details.get("metrics", [])), catalog_entry.get("metrics"))
        deployment_signals = self._merge_signals(
            self._deployment_signals(details.get("recent_deployments", [])),
            self._deployment_signals(catalog_entry.get("deployments", [])),
            self._deployment_signals(deployments),
        )
        related_services = self._merge_signals(self._trace_signals(details), catalog_entry.get("traces"))
        catalog_sources = catalog_entry.get("evidence_sources", [])
        if isinstance(catalog_sources, list) and catalog_sources:
            normalized_sources = [item for item in catalog_sources if isinstance(item, dict)]
            if normalized_sources:
                return normalized_sources
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
                "detail": metrics[0] if metrics else "No metric series available.",
            },
            {
                "source": "deployment history",
                "signal": "release",
                "count": len(deployment_signals),
                "summary": "Recent release metadata fused into the operator view.",
                "detail": deployment_signals[0] if deployment_signals else "No deployment metadata available.",
            },
            {
                "source": "service graph",
                "signal": "traces",
                "count": len(related_services),
                "summary": "Dependency paths used to explain the blast radius.",
                "detail": related_services[0] if related_services else "No dependency graph available.",
            },
        ]
