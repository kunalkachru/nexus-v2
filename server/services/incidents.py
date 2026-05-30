import inspect
from datetime import datetime, timezone

from fastapi import HTTPException

from server.audit import get_audit_logs
from server.artifacts import record_replay_launch, record_training_snapshot
from server.artifacts import get_artifact_summary
from server.integrations.alerts import AlertNormalizer
from server.integrations.deployments import DeploymentLookupService
from server.integrations.models import (
    BatchImportRequest,
    IncomingIncidentWebhook,
    ManualIncidentReport,
    SlackIncidentCommand,
    StreamAnomalyReport,
)
from server.incident_payloads import get_incident_definition, get_incident_details, list_supported_incident_ids
from server.models import (
    IncidentLifecycleResponse,
    IncidentRecord,
    IncidentStatusResponse,
    IncidentWorkflowStage,
    QueueIncidentSummary,
    QueueResponse,
)
from server.services.observability import ObservabilityService


class IncidentService:
    def __init__(
        self,
        *,
        session,
        alert_normalizer: AlertNormalizer,
        deployment_lookup: DeploymentLookupService,
        observability: ObservabilityService,
    ) -> None:
        self._session = session
        self._alert_normalizer = alert_normalizer
        self._deployment_lookup = deployment_lookup
        self._observability = observability

    async def create_incident_from_webhook(
        self,
        payload: IncomingIncidentWebhook,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        envelope = self._alert_normalizer.normalize(payload)
        created = await self._create_normalized_incident(
            external_id=envelope.external_id,
            title=envelope.title,
            severity=envelope.severity,
            source=envelope.source,
            service=envelope.service,
            tenant_id=tenant_id,
        )
        incident = IncidentRecord.model_validate(created)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(
            envelope.service
        )
        queue_position, eta_sec = await self._queue_position_and_eta(
            incident.nexus_incident_id,
            tenant_id=tenant_id,
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=incident.nexus_incident_id,
            external_id=incident.external_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source=envelope.source,
            recent_deployments=recent_deployments,
            queue_position=queue_position,
            eta_sec=eta_sec,
        )
        return response.model_dump(mode="json")

    async def create_incident_from_slack_command(
        self,
        payload: SlackIncidentCommand,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        created = await self._create_normalized_incident(
            external_id=payload.command_id,
            title=payload.text,
            severity=self._normalize_severity(payload.severity),
            source="slack_command",
            service=payload.service,
            tenant_id=tenant_id,
        )
        incident = IncidentRecord.model_validate(created)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(incident.service)
        queue_position, eta_sec = await self._queue_position_and_eta(
            incident.nexus_incident_id,
            tenant_id=tenant_id,
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=incident.nexus_incident_id,
            external_id=incident.external_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source=incident.source,
            recent_deployments=recent_deployments,
            queue_position=queue_position,
            eta_sec=eta_sec,
        )
        return response.model_dump(mode="json")

    async def create_incident_from_stream_anomaly(
        self,
        payload: StreamAnomalyReport,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        created = await self._create_normalized_incident(
            external_id=payload.detector_id,
            title=f"{payload.service} stream anomaly",
            severity=self._normalize_severity(payload.severity),
            source="stream_anomaly",
            service=payload.service,
            tenant_id=tenant_id,
        )
        incident = IncidentRecord.model_validate(created)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(incident.service)
        queue_position, eta_sec = await self._queue_position_and_eta(
            incident.nexus_incident_id,
            tenant_id=tenant_id,
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=incident.nexus_incident_id,
            external_id=incident.external_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source=incident.source,
            recent_deployments=recent_deployments,
            queue_position=queue_position,
            eta_sec=eta_sec,
        )
        return response.model_dump(mode="json")

    async def create_incident_from_manual_report(
        self,
        payload: ManualIncidentReport,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        severity = "P1" if payload.severity == "P0" else payload.severity
        created = await self._session.incidents.create_incident(
            external_id=f"manual_{payload.affected_service}",
            title=f"{payload.affected_service} manual report",
            severity=severity,
            tenant_id=tenant_id,
            source="manual_form",
            service=payload.affected_service,
        )
        incident = IncidentRecord.model_validate(created)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(
            incident.service
        )
        queue_position, eta_sec = await self._queue_position_and_eta(
            incident.nexus_incident_id,
            tenant_id=tenant_id,
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=incident.nexus_incident_id,
            external_id=incident.external_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source=incident.source,
            recent_deployments=recent_deployments,
            queue_position=queue_position,
            eta_sec=eta_sec,
        )
        return response.model_dump(mode="json")

    async def create_incident_from_batch_import(
        self,
        payload: BatchImportRequest,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        severity = "P1" if payload.severity == "P0" else payload.severity
        created = await self._session.incidents.create_incident(
            external_id=f"batch_{payload.batch_name}",
            title=f"Batch import {payload.batch_name}",
            severity=severity,
            tenant_id=tenant_id,
            source="batch_import",
            service=payload.batch_name,
        )
        incident = IncidentRecord.model_validate(created)
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
            queue_position=1,
            eta_sec=30,
        )
        return response.model_dump(mode="json")

    async def get_incident_status(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        if tenant_id is None:
            loaded = await self._session.incidents.get_incident(nexus_incident_id)
        else:
            loaded = await self._session.incidents.get_incident_for_tenant(nexus_incident_id, tenant_id)
        if loaded is None and nexus_incident_id in list_supported_incident_ids():
            loaded = self._demo_incident_record(nexus_incident_id)
        if loaded is None:
            raise HTTPException(status_code=404, detail="incident not found")

        incident = IncidentRecord.model_validate(loaded)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(
            incident.service
        )
        queue_position, eta_sec = await self._queue_position_and_eta(
            incident.nexus_incident_id,
            tenant_id=incident.tenant_id,
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=incident.nexus_incident_id,
            external_id=incident.external_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source=incident.source,
            recent_deployments=recent_deployments,
            queue_position=queue_position,
            eta_sec=eta_sec,
        )
        return response.model_dump(mode="json")

    async def get_incident_status_v1(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        lifecycle = await self.get_incident_status(nexus_incident_id, tenant_id=tenant_id)
        stage = self._derive_current_stage(lifecycle)
        response = IncidentStatusResponse(
            nexus_incident_id=lifecycle["nexus_incident_id"],
            external_id=lifecycle["external_id"],
            title=lifecycle["title"],
            severity=lifecycle["severity"],
            status=lifecycle["status"],
            source=lifecycle.get("source"),
            current_stage=stage,
            queue_position=int(lifecycle.get("queue_position") or 1),
            eta_sec=int(lifecycle.get("eta_sec") or 30),
            timeline=self._build_status_timeline(lifecycle),
            audit_logs=get_audit_logs(nexus_incident_id),
        )
        return response.model_dump(mode="json")

    async def get_incident_context_v1(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        if nexus_incident_id in list_supported_incident_ids():
            from server.services.live_demo import build_demo_payload

            return await build_demo_payload(nexus_incident_id)

        if tenant_id is None:
            loaded = await self._session.incidents.get_incident(nexus_incident_id)
        else:
            loaded = await self._session.incidents.get_incident_for_tenant(nexus_incident_id, tenant_id)
        if loaded is None:
            raise HTTPException(status_code=404, detail="incident not found")

        incident = IncidentRecord.model_validate(loaded)
        lifecycle = await self.get_incident_status_v1(nexus_incident_id, tenant_id=tenant_id)
        audit_logs = get_audit_logs(nexus_incident_id)
        recent_deployments = await self._deployment_lookup.get_recent_deployments(incident.service)
        workflow = lifecycle.get("timeline", [])
        observability = {
            "metrics": [
                {
                    "name": "Live incident state",
                    "current": 1,
                    "unit": "",
                    "series": [1, 2, 3, 4, 5],
                },
                {
                    "name": "Audit entries",
                    "current": len(audit_logs),
                    "unit": "",
                    "series": [max(1, len(audit_logs) - 2), max(1, len(audit_logs) - 1), len(audit_logs), len(audit_logs) + 1, len(audit_logs) + 2],
                },
            ],
            "recent_logs": [
                f"{entry['timestamp']} · {entry['event_type']} · {entry['payload'].get('status', entry['payload'].get('current_stage', 'recorded'))}"
                for entry in audit_logs[-5:]
            ]
            or [f"Live incident {incident.nexus_incident_id} awaiting evidence"],
            "alert_timeline": [
                {"time": step["timestamp"], "event": step["label"]}
                for step in workflow
            ],
            "recommended_runbooks": [
                f"Validate {incident.service or 'service'} ownership and confirm rollback safety",
                "Review audit trail and deployment metadata before execution",
            ],
            "evidence_sources": self._observability.build_live_evidence_sources(
                incident_id=incident.nexus_incident_id,
                service=incident.service,
                source_channel=self._queue_source_channel(incident.source),
                audit_logs=audit_logs,
                recent_deployments=recent_deployments,
                timeline=workflow,
            ),
        }
        classification = {
            "incident_id": incident.nexus_incident_id,
            "incident_name": incident.title,
            "severity": incident.severity,
            "confidence": 0.84 if incident.source in {"manual_form", "webhook"} else 0.77,
            "confidence_breakdown": {
                "intake": 0.32,
                "audit": 0.22,
                "evidence": 0.26,
                "context": 0.20,
            },
            "evidence": [
                f"{incident.source or 'webhook'} intake for {incident.service or 'service'}",
                f"{len(audit_logs)} audit events captured",
                f"{len(recent_deployments)} deployment records correlated",
            ],
            "reasoning": (
                "Live incident context assembled from authenticated intake, audit trail, "
                "and deployment metadata."
            ),
        }
        diagnosis = {
            "root_cause": (
                f"Live incident for {incident.service or 'service'} awaiting deeper observability enrichment"
            ),
            "confidence": 0.75,
            "supporting_logs": observability["recent_logs"],
            "correlation_analysis": (
                "The backend fused the live incident record, workflow timeline, audit trail, and deployment lookups."
            ),
            "reasoning": (
                "This context comes from the live incident contract rather than the static demo fixture."
            ),
        }
        runbook = {
            "language": "bash",
            "summary": f"Live mitigation plan for {incident.service or 'service'}",
            "selection_logic": "Prefer the safest rollback-ready response while the production observability adapters are expanded.",
            "candidate_fixes": [
                {"action": "Validate ownership and confirm incident scope", "success_rate": 0.92},
                {"action": "Prepare rollback-safe mitigation and monitor audit trail", "success_rate": 0.86},
            ],
            "recommended_runbook": f"Validate {incident.service or 'service'} ownership and prepare rollback-safe mitigation.",
            "reasoning": "The live incident view keeps the same remediation contract while using backend state instead of client synthesis.",
            "cost_usd": 0.08,
        }
        guardian = {
            "decision": "approve" if incident.status != "blocked_by_guardian" else "reject",
            "confidence": 0.89,
            "safety_checks": [
                "Authenticated live incident read",
                "Audit trail available from backend state",
                "Rollback-safe execution path preserved",
            ],
            "policy_violations": [],
            "reasoning": "The live context path is read-only and keeps execution behind the existing control gate.",
        }
        execution_result = "blocked" if incident.status == "blocked_by_guardian" else "executed"
        return {
            "incident": {
                "id": incident.nexus_incident_id,
                "name": incident.title,
                "severity": incident.severity,
                "summary": f"Live incident opened through the {self._queue_source_channel(incident.source)} intake path.",
                "detected_at": incident.created_at or incident.updated_at or "now",
                "duration_minutes": 0,
                "related_services": [incident.service] if incident.service else [],
                "recent_deployments": recent_deployments,
                "similar_past_incidents": [],
                "source_channel": self._queue_source_channel(incident.source),
            },
            "observability": observability,
            "classification": classification,
            "diagnosis": diagnosis,
            "runbook": runbook,
            "guardian": guardian,
            "workflow": workflow,
            "execution_result": execution_result,
            "reward": 0.72,
            "execution_time_ms": 12.4,
            "supported_incidents": [incident.nexus_incident_id],
        }

    async def execute_incident(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        lifecycle = await self.get_incident_status(nexus_incident_id, tenant_id=tenant_id)
        executed = lifecycle.get("status") != "blocked_by_guardian"
        if executed:
            updated = await self._session.incidents.update_incident_status(
                nexus_incident_id,
                status="resolved",
            )
            if updated is not None:
                lifecycle["status"] = updated.status
                lifecycle["queue_position"], lifecycle["eta_sec"] = await self._queue_position_and_eta(
                    nexus_incident_id,
                    tenant_id=tenant_id or "tenant-system",
                )
        payload = {
            "incident_id": nexus_incident_id,
            "status": "executed" if executed else "blocked_by_guardian",
            "result": "deterministic_demo_run",
            "queue_position": lifecycle.get("queue_position", 1),
            "eta_sec": lifecycle.get("eta_sec", 30),
        }
        return payload

    async def get_audit_logs(
        self,
        nexus_incident_id: str,
    ) -> list[dict[str, object]]:
        return get_audit_logs(nexus_incident_id)

    async def list_queue_items(self, *, tenant_id: str) -> QueueResponse:
        repo = self._session.incidents
        if not hasattr(repo, "list_incidents_for_tenant"):
            return QueueResponse(items=self._demo_queue_items())
        stored_records = await repo.list_incidents_for_tenant(tenant_id)
        items: list[QueueIncidentSummary] = [
            self._incident_to_queue_item(incident) for incident in stored_records
        ]
        if not items:
            items = self._demo_queue_items()
        items.sort(key=self._queue_sort_key, reverse=True)
        return QueueResponse(items=items)

    def _demo_incident_record(self, nexus_incident_id: str) -> IncidentRecord:
        incident = get_incident_definition(nexus_incident_id)
        details = get_incident_details(nexus_incident_id)
        return IncidentRecord(
            nexus_incident_id=incident.id,
            external_id=incident.id,
            title=incident.name,
            severity="P1" if incident.severity == "P1" else "P2" if incident.severity == "P2" else "P3",
            status="investigating",
            source=self._demo_source_channel(nexus_incident_id),
            service=details["related_services"][0] if details.get("related_services") else "",
        )

    def _demo_source_channel(self, nexus_incident_id: str) -> str:
        source_channels = {
            "INC001": "webhook",
            "INC002": "manual_form",
            "INC003": "stream_anomaly",
            "INC004": "webhook",
            "INC005": "batch_import",
        }
        return source_channels.get(nexus_incident_id, "webhook")

    def _normalize_severity(self, severity: str) -> str:
        return "P1" if severity == "P0" else severity

    async def _queue_position_and_eta(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str,
    ) -> tuple[int, int]:
        if not hasattr(self._session.incidents, "list_incidents_for_tenant"):
            return 1, self._eta_for_position(1)
        queue = await self.list_queue_items(tenant_id=tenant_id)
        for position, item in enumerate(queue.items, start=1):
            if item.nexus_incident_id == nexus_incident_id:
                return position, self._eta_for_position(position)
        return 1, self._eta_for_position(1)

    async def _create_normalized_incident(
        self,
        *,
        external_id: str,
        title: str,
        severity: str,
        source: str,
        service: str,
        tenant_id: str,
    ) -> IncidentRecord:
        create_incident = self._session.incidents.create_incident
        create_kwargs = {
            "external_id": external_id,
            "title": title,
            "severity": severity,
            "source": source,
            "service": service,
        }
        if "tenant_id" in inspect.signature(create_incident).parameters:
            create_kwargs["tenant_id"] = tenant_id
        created = await create_incident(**create_kwargs)
        return IncidentRecord.model_validate(created)

    def _incident_to_queue_item(self, incident: IncidentRecord) -> QueueIncidentSummary:
        current_stage = self._derive_current_stage(
            {
                "source": incident.source,
                "status": incident.status,
            }
        )
        return QueueIncidentSummary(
            nexus_incident_id=incident.nexus_incident_id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            source_channel=self._queue_source_channel(incident.source),
            current_stage=current_stage,
            updated_at=incident.updated_at or incident.created_at or "now",
        )

    def _queue_sort_key(self, item: QueueIncidentSummary) -> tuple[int, int, str]:
        updated_at = self._parse_timestamp(item.updated_at)
        active_weight = 1 if item.status == "investigating" else 0
        return active_weight, int(updated_at.timestamp()), item.nexus_incident_id

    def _parse_timestamp(self, value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _eta_for_position(self, position: int) -> int:
        return max(30, 30 + (position - 1) * 20)

    def _queue_source_channel(self, source: str | None) -> str:
        if source in {"manual_form", "slack_command", "stream_anomaly", "batch_import"}:
            return source
        return "webhook"

    def _demo_queue_items(self) -> list[QueueIncidentSummary]:
        items: list[QueueIncidentSummary] = []
        stage_by_incident = {
            "INC001": IncidentWorkflowStage.EVIDENCE_RETRIEVED,
            "INC002": IncidentWorkflowStage.SENTINEL_CLASSIFIED,
            "INC003": IncidentWorkflowStage.PRISM_DIAGNOSED,
            "INC004": IncidentWorkflowStage.FORGE_PROPOSED_RUNBOOK,
            "INC005": IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY,
        }
        status_by_incident = {
            "INC001": "investigating",
            "INC002": "investigating",
            "INC003": "investigating",
            "INC004": "investigating",
            "INC005": "investigating",
        }
        for incident_id in list_supported_incident_ids():
            incident = get_incident_definition(incident_id)
            details = get_incident_details(incident_id)
            items.append(
                QueueIncidentSummary(
                    nexus_incident_id=incident.id,
                    title=incident.name,
                    severity="P1" if incident.severity == "P1" else "P2" if incident.severity == "P2" else "P3",
                    status=status_by_incident.get(incident_id, "investigating"),
                    source_channel=self._demo_source_channel(incident_id),
                    current_stage=stage_by_incident.get(incident_id, IncidentWorkflowStage.INCIDENT_RECEIVED),
                    updated_at=str(details["detected_at"]),
                )
            )
        return items

    def _derive_current_stage(self, lifecycle: dict[str, object]) -> IncidentWorkflowStage:
        if lifecycle.get("status") == "resolved":
            return IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED
        if lifecycle.get("status") == "blocked_by_guardian":
            return IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY
        source = lifecycle.get("source")
        if source == "manual_form":
            return IncidentWorkflowStage.VALIDATED_AUTHENTICATED
        if source == "batch_import":
            return IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED
        if source == "slack_command":
            return IncidentWorkflowStage.ENRICHED_WITH_SERVICE_CONTEXT
        if source == "stream_anomaly":
            return IncidentWorkflowStage.EVIDENCE_RETRIEVED
        return IncidentWorkflowStage.EVIDENCE_RETRIEVED

    def _build_status_timeline(self, lifecycle: dict[str, object]) -> list[dict[str, object]]:
        source = lifecycle.get("source") or "webhook"
        current_stage = self._derive_current_stage(lifecycle)
        stages: list[tuple[IncidentWorkflowStage, str, str, str]] = [
            (
                IncidentWorkflowStage.INCIDENT_RECEIVED,
                "Incident received",
                "intake",
                "completed",
            ),
            (
                IncidentWorkflowStage.VALIDATED_AUTHENTICATED,
                "Validated and authenticated",
                "platform",
                "completed" if current_stage != IncidentWorkflowStage.INCIDENT_RECEIVED else "pending",
            ),
            (
                IncidentWorkflowStage.ENRICHED_WITH_SERVICE_CONTEXT,
                "Enriched with service context",
                "enrichment",
                "completed"
                if current_stage
                in {
                    IncidentWorkflowStage.ENRICHED_WITH_SERVICE_CONTEXT,
                    IncidentWorkflowStage.EVIDENCE_RETRIEVED,
                    IncidentWorkflowStage.SENTINEL_CLASSIFIED,
                    IncidentWorkflowStage.PRISM_DIAGNOSED,
                    IncidentWorkflowStage.FORGE_PROPOSED_RUNBOOK,
                    IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY,
                    IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED,
                }
                else "pending",
            ),
            (
                IncidentWorkflowStage.EVIDENCE_RETRIEVED,
                "Evidence retrieved",
                "observability",
                "completed"
                if current_stage
                in {
                    IncidentWorkflowStage.EVIDENCE_RETRIEVED,
                    IncidentWorkflowStage.SENTINEL_CLASSIFIED,
                    IncidentWorkflowStage.PRISM_DIAGNOSED,
                    IncidentWorkflowStage.FORGE_PROPOSED_RUNBOOK,
                    IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY,
                    IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED,
                }
                else "pending",
            ),
            (
                IncidentWorkflowStage.SENTINEL_CLASSIFIED,
                "SENTINEL classified the incident",
                "sentinel",
                "completed"
                if current_stage
                in {
                    IncidentWorkflowStage.SENTINEL_CLASSIFIED,
                    IncidentWorkflowStage.PRISM_DIAGNOSED,
                    IncidentWorkflowStage.FORGE_PROPOSED_RUNBOOK,
                    IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY,
                    IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED,
                }
                else "pending",
            ),
            (
                IncidentWorkflowStage.PRISM_DIAGNOSED,
                "PRISM correlated the evidence",
                "prism",
                "completed"
                if current_stage
                in {
                    IncidentWorkflowStage.PRISM_DIAGNOSED,
                    IncidentWorkflowStage.FORGE_PROPOSED_RUNBOOK,
                    IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY,
                    IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED,
                }
                else "pending",
            ),
            (
                IncidentWorkflowStage.FORGE_PROPOSED_RUNBOOK,
                "FORGE proposed a runbook",
                "forge",
                "completed"
                if current_stage
                in {
                    IncidentWorkflowStage.FORGE_PROPOSED_RUNBOOK,
                    IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY,
                    IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED,
                }
                else "pending",
            ),
            (
                IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY,
                "GUARDIAN reviewed safety",
                "guardian",
                "completed"
                if current_stage in {IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY, IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED}
                else "pending",
            ),
            (
                IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED,
                "Executed, verified, and learned",
                "execution",
                "completed"
                if current_stage == IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED
                else "pending",
            ),
        ]

        timeline: list[dict[str, object]] = []
        for index, (stage, label, actor, status) in enumerate(stages):
            timeline.append(
                {
                    "state": stage.value,
                    "label": label,
                    "actor": actor,
                    "status": status,
                    "timestamp": f"stage-{index + 1}",
                    "summary": f"{label} via {source}",
                }
            )
        return timeline

    async def list_history_archive(self, *, tenant_id: str) -> list[dict[str, object]]:
        repo = self._session.incidents
        if not hasattr(repo, "list_incidents_for_tenant"):
            return self._demo_history_archive()

        records = await repo.list_incidents_for_tenant(tenant_id)
        completed = [
            IncidentRecord.model_validate(record)
            for record in records
            if getattr(record, "status", None) in {"resolved", "blocked_by_guardian"}
        ]
        if not completed:
            return self._demo_history_archive()

        completed.sort(
            key=lambda incident: self._parse_timestamp(incident.updated_at or incident.created_at or ""),
            reverse=True,
        )

        archive: list[dict[str, object]] = []
        for incident in completed:
            archive.append(
                {
                    "incident_id": incident.nexus_incident_id,
                    "title": incident.title,
                    "severity": incident.severity,
                    "outcome": "blocked" if incident.status == "blocked_by_guardian" else "resolved",
                    "source_channel": self._queue_source_channel(incident.source),
                    "resolved_at": incident.updated_at or incident.created_at or datetime.now(timezone.utc).isoformat(),
                    "summary": f"{incident.title} resolved through the live operator console",
                    "owner_team": incident.service or "platform",
                    "window": self._history_window_for_timestamp(incident.updated_at or incident.created_at or ""),
                }
            )
        return archive

    async def list_replay_scenarios(self) -> list[dict[str, object]]:
        return self._replay_scenario_catalog()

    async def launch_replay_scenario(
        self,
        scenario_id: str,
        *,
        tenant_id: str,
    ) -> dict[str, object]:
        catalog = {scenario["scenario_id"]: scenario for scenario in self._replay_scenario_catalog()}
        scenario = catalog.get(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="replay scenario not found")

        incident_id = scenario["incident_id"]
        incident = get_incident_definition(incident_id)
        details = get_incident_details(incident_id)
        created = await self._session.incidents.create_incident(
            external_id=f"replay_{scenario_id}",
            title=scenario["title"],
            severity="P1" if incident.severity == "P1" else "P2" if incident.severity == "P2" else "P3",
            tenant_id=tenant_id,
            source=scenario["source_channel"],
            service=details["related_services"][0] if details.get("related_services") else incident.system_context.service,
        )
        created_record = IncidentRecord.model_validate(created)
        await record_replay_launch(
            {
                "scenario_id": scenario_id,
                "nexus_incident_id": created_record.nexus_incident_id,
                "tenant_id": tenant_id,
                "source_channel": created_record.source,
                "title": created_record.title,
            }
        )
        return {
            "scenario_id": scenario_id,
            "nexus_incident_id": created_record.nexus_incident_id,
            "incident_id": created_record.nexus_incident_id,
            "source_channel": created_record.source,
            "title": created_record.title,
            "launch_label": scenario["launch_label"],
        }

    async def build_training_summary(self, payload: dict[str, object], *, tenant_id: str) -> dict[str, object]:
        summary = self._build_training_summary(payload)
        repo = self._session.incidents
        live_records = []
        if hasattr(repo, "list_incidents_for_tenant"):
            live_records = await repo.list_incidents_for_tenant(tenant_id)

        live_incidents = [IncidentRecord.model_validate(record) for record in live_records]
        summary_block = dict(summary.get("summary", {}))
        summary_block["live_incidents"] = len(live_incidents)
        summary_block["live_resolved_incidents"] = sum(1 for incident in live_incidents if incident.status == "resolved")
        summary_block["live_audit_events"] = len(get_audit_logs())
        summary["summary"] = summary_block
        summary["live_incidents"] = [
            {
                "incident_id": incident.nexus_incident_id,
                "title": incident.title,
                "status": incident.status,
                "severity": incident.severity,
                "source_channel": self._queue_source_channel(incident.source),
                "updated_at": incident.updated_at or incident.created_at,
            }
            for incident in sorted(
                live_incidents,
                key=lambda record: self._parse_timestamp(record.updated_at or record.created_at or ""),
                reverse=True,
            )
        ]
        summary["replay_readiness"] = "Ready"
        summary["training_signal"] = "Derived from live incidents and persisted audit events"
        await record_training_snapshot(
            {
                "tenant_id": tenant_id,
                "summary": summary.get("summary", {}),
                "episode_records": len(summary.get("episode_records", [])),
                "live_incidents": len(summary.get("live_incidents", [])),
            }
        )
        summary["artifact_summary"] = get_artifact_summary()
        return summary

    def _demo_history_archive(self) -> list[dict[str, object]]:
        archive: list[dict[str, object]] = []
        outcome_by_incident = {
            "INC001": "resolved",
            "INC002": "resolved",
            "INC003": "resolved",
            "INC004": "resolved",
            "INC005": "resolved",
        }
        window_by_incident = {
            "INC001": "last-24-hours",
            "INC002": "last-7-days",
            "INC003": "last-30-days",
            "INC004": "last-7-days",
            "INC005": "last-24-hours",
        }
        for incident_id in list_supported_incident_ids():
            incident = get_incident_definition(incident_id)
            details = get_incident_details(incident_id)
            archive.append(
                {
                    "incident_id": incident.id,
                    "title": incident.name,
                    "severity": "P1" if incident.severity == "P1" else "P2" if incident.severity == "P2" else "P3",
                    "outcome": outcome_by_incident.get(incident_id, "resolved"),
                    "source_channel": self._demo_source_channel(incident_id),
                    "resolved_at": details["detected_at"],
                    "summary": details["summary"],
                    "owner_team": details["related_services"][0] if details.get("related_services") else "platform",
                    "window": window_by_incident.get(incident_id, "last-30-days"),
                }
            )
        return archive

    def _replay_scenario_catalog(self) -> list[dict[str, object]]:
        replay_map = {
            "api_timeout_cascade": ("INC001", ["webhook", "api-gateway", "P1", "timeout cascade"]),
            "db_connection_pool_exhaustion": ("INC002", ["manual_form", "payments", "P1", "database"]),
            "redis_saturation": ("INC004", ["webhook", "redis", "P2", "cache"]),
            "memory_leak_after_deploy": ("INC003", ["stream_anomaly", "worker-fleet", "P2", "deploy"]),
            "queue_backlog_worker_stall": ("INC005", ["batch_import", "billing", "P1", "queue"]),
            "bad_deployment_regression": ("INC004", ["webhook", "api-gateway", "P1", "rollback"]),
            "certificate_expiry": ("INC005", ["webhook", "edge-gateway", "P1", "expiry"]),
            "cache_explosion": ("INC004", ["webhook", "redis", "P2", "eviction"]),
        }
        scenarios: list[dict[str, object]] = []
        for scenario_id, (incident_id, pills) in replay_map.items():
            incident = get_incident_definition(incident_id)
            details = get_incident_details(incident_id)
            scenarios.append(
                {
                    "scenario_id": scenario_id,
                    "title": incident.name,
                    "summary": details["summary"],
                    "pills": pills,
                    "payload": [
                        "Source payload",
                        f"Scenario: {scenario_id.replace('_', ' ')}",
                        f"Severity: {incident.severity}",
                        f"Service: {incident.system_context.service}",
                    ],
                    "evidence": [
                        "Evidence pack",
                        f"{len(details['recent_logs'])} logs, {len(details['metrics'])} metrics, {len(details['recent_deployments'])} deployments",
                        details["summary"],
                    ],
                    "agents": [
                        "Agent outputs",
                        "SENTINEL classified the incident",
                        "PRISM correlated the evidence",
                        "FORGE proposed a runbook",
                        "GUARDIAN reviewed the action for safety",
                    ],
                    "outcome": [
                        "Final result",
                        "Open the live console to inspect the replayed flow",
                    ],
                    "incident_id": incident.id,
                    "launch_label": f"Open {incident.id} console",
                    "source_channel": pills[0],
                }
            )
        return scenarios

    def _history_window_for_timestamp(self, value: str) -> str:
        timestamp = self._parse_timestamp(value)
        age_hours = (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600
        if age_hours <= 24:
            return "last-24-hours"
        if age_hours <= 24 * 7:
            return "last-7-days"
        return "last-30-days"

    def _build_training_summary(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "summary": payload.get("summary", {}),
            "episode_records": payload.get("episode_records", []),
            "difficulty_ladder": payload.get("difficulty_ladder", []),
            "reward_curve": payload.get("reward_curve", []),
            "cost_curve": payload.get("cost_curve", []),
            "workflow_observation_states": payload.get("workflow_observation_states", []),
            "agent_accuracy": payload.get("agent_accuracy", {}),
            "final_difficulty": payload.get("final_difficulty"),
        }
