import inspect
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from server.audit import get_audit_logs
from server.artifacts import record_replay_launch, record_training_snapshot
from server.artifacts import record_learning_contract
from server.artifacts import record_guardian_review
from server.artifacts import get_artifact_summary
from server.agents.forge import ForgeAgent
from server.agents.guardian import GuardianAgent
from server.agents.live_clients import OpenAIForgeClient, OpenAIPrismClient, OpenAISentinelClient
from server.agents.prism import PrismAgent
from server.agents.sentinel import SentinelAgent
from server.config import AppConfig
from server.integrations.alerts import AlertNormalizer
from server.integrations.deployments import DeploymentLookupService
from server.integrations.models import (
    BatchImportRequest,
    GuardianDecisionRequest,
    IncomingIncidentWebhook,
    ManualIncidentReport,
    RawIncidentTextRequest,
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
    SystemContext,
)
from server.openai_keys import build_llm_access
from server.services.live_ingest import RawIncidentParser
from server.services.governance import GovernanceService
from server.services.priority import normalize_priority_label, priority_rank, priority_snapshot, shift_priority_label
from server.services.observability import ObservabilityService
from server.services.result_contracts import build_structured_result
from server.services.enterprise_runtime import (
    EnterpriseNexusRuntime,
    IncidentKnowledgeService,
    build_triage_summary,
    build_training_enterprise_summary,
    runbook_score_from_candidates,
)
from training.runner import TrainingForgeClient

logger = logging.getLogger(__name__)


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
        self._governance = GovernanceService()
        self._raw_parser = RawIncidentParser()
        self._enterprise_runtime = EnterpriseNexusRuntime(
            observability=observability,
            sentinel=SentinelAgent(),
            prism=PrismAgent(observability=observability),
            forge=ForgeAgent(client=TrainingForgeClient()),
            guardian=GuardianAgent(),
            knowledge_service=IncidentKnowledgeService(session=session),
        )

    def _display_severity(self, severity: str) -> str:
        return normalize_priority_label(severity)

    def _guardian_decision_for_incident(self, incident: IncidentRecord) -> str:
        return self._governance.guardian_decision_for_incident(incident)

    def _guardian_context(self, incident: IncidentRecord) -> dict[str, object]:
        return self._governance.guardian_context(incident)

    def _guardian_policy(self, decision: str) -> dict[str, str]:
        return self._governance.guardian_policy_for_decision(decision)

    async def _build_enterprise_overlay(
        self,
        *,
        incident_id: str,
        incident_name: str,
        service: str,
        severity: str,
        source_channel: str,
        classification: dict[str, object],
        diagnosis: dict[str, object],
        runbook: dict[str, object],
        guardian: dict[str, object],
        observability: dict[str, object],
        workflow: list[dict[str, object]],
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        return await self._enterprise_runtime.build_overlay_from_snapshot(
            incident_id=incident_id,
            incident_name=incident_name,
            service=service,
            severity=severity,
            source_channel=source_channel,
            classification=classification,
            diagnosis=diagnosis,
            runbook=runbook,
            guardian=guardian,
            observability=observability,
            workflow=workflow,
            tenant_id=tenant_id,
        )

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
            guardian_decision=incident.guardian_decision,
            guardian_reasoning=incident.guardian_reasoning,
            guardian_reviewed_at=incident.guardian_reviewed_at,
            guardian_policy_id=incident.guardian_policy_id,
            guardian_policy_name=incident.guardian_policy_name,
            guardian_policy_basis=incident.guardian_policy_basis,
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
            guardian_decision=incident.guardian_decision,
            guardian_reasoning=incident.guardian_reasoning,
            guardian_reviewed_at=incident.guardian_reviewed_at,
        )
        return response.model_dump(mode="json")

    async def create_incident_from_manual_report(
        self,
        payload: ManualIncidentReport,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        severity = shift_priority_label(payload.severity)
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
            guardian_decision=incident.guardian_decision,
            guardian_reasoning=incident.guardian_reasoning,
            guardian_reviewed_at=incident.guardian_reviewed_at,
        )
        return response.model_dump(mode="json")

    async def create_incident_from_raw_text(
        self,
        payload: RawIncidentTextRequest,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        parsed = self._raw_parser.parse(payload.raw_text, severity_hint=payload.severity_hint)
        created = await self._session.incidents.create_incident(
            external_id=f"raw_{parsed.service}_{uuid4().hex[:8]}",
            title=parsed.title,
            severity=parsed.severity,
            tenant_id=tenant_id,
            source="raw_text",
            service=parsed.service,
            raw_input_text=payload.raw_text,
            normalized_evidence={
                "service": parsed.service,
                "severity": parsed.severity,
                "signature": parsed.signature,
                "evidence": parsed.evidence,
                "symptoms": parsed.symptoms,
                "source_hint": payload.source_hint,
                "reported_by": payload.reported_by,
                "team": payload.team,
            },
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
            guardian_decision=incident.guardian_decision,
            guardian_reasoning=incident.guardian_reasoning,
            guardian_reviewed_at=incident.guardian_reviewed_at,
        )
        return response.model_dump(mode="json")

    async def create_incident_from_batch_import(
        self,
        payload: BatchImportRequest,
        *,
        tenant_id: str = "tenant-system",
    ) -> dict[str, object]:
        severity = shift_priority_label(payload.severity)
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
            guardian_decision=incident.guardian_decision,
            guardian_reasoning=incident.guardian_reasoning,
            guardian_reviewed_at=incident.guardian_reviewed_at,
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
            guardian_decision=str(lifecycle.get("guardian_decision") or "pending"),
            guardian_reasoning=str(lifecycle.get("guardian_reasoning") or ""),
            guardian_reviewed_at=str(lifecycle.get("guardian_reviewed_at") or ""),
            guardian_policy_id=str(lifecycle.get("guardian_policy_id") or ""),
            guardian_policy_name=str(lifecycle.get("guardian_policy_name") or ""),
            guardian_policy_basis=str(lifecycle.get("guardian_policy_basis") or ""),
        )
        return response.model_dump(mode="json")

    async def get_incident_context_v1(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
        live_reasoning: bool | None = None,
        openai_api_key: str | None = None,
    ) -> dict[str, object]:
        if nexus_incident_id in list_supported_incident_ids():
            from server.services.live_demo import build_demo_payload

            return await build_demo_payload(
                nexus_incident_id,
                live_reasoning_override=live_reasoning,
                openai_api_key=openai_api_key,
            )

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
        priority = priority_snapshot(incident.severity)
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
        if incident.raw_input_text:
            observability["evidence_sources"] = [
                {
                    "source": "raw input",
                    "signal": "paste",
                    "count": len(incident.raw_input_text.splitlines()),
                    "summary": "Operator-pasted logs normalized into the incident evidence bundle.",
                    "detail": incident.raw_input_text.splitlines()[0],
                },
                *observability["evidence_sources"],
            ]
            observability["recent_logs"] = [
                f"Raw input normalized for {incident.service or 'service'}",
                *observability["recent_logs"],
            ]
        normalized_evidence = incident.normalized_evidence or {}
        live_payload = await self._build_raw_live_reasoning_payload(
            incident,
            lifecycle=lifecycle,
            audit_logs=audit_logs,
            recent_deployments=recent_deployments,
            workflow=workflow,
            raw_evidence=normalized_evidence,
            live_reasoning_override=live_reasoning,
            openai_api_key=openai_api_key,
        )
        if live_payload is not None:
            return live_payload
        raw_signature = str(normalized_evidence.get("signature", "")).strip()
        raw_service = str(normalized_evidence.get("service", incident.service or "service")).strip()
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
        if incident.raw_input_text:
            classification["confidence"] = 0.86
            classification["evidence"] = [
                f"Raw text normalized for {raw_service or 'service'}",
                f"Signature: {raw_signature or 'General incident'}",
                f"{len(normalized_evidence.get('evidence', []))} evidence line(s) extracted",
            ]
            classification["reasoning"] = (
                "The pasted logs were normalized into service, severity, and signature before "
                "routing through the agent flow."
            )
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
        if incident.raw_input_text:
            diagnosis["root_cause"] = (
                f"Likely {raw_signature.lower() if raw_signature else 'incident pattern'} affecting {raw_service or 'service'}"
            )
            diagnosis["confidence"] = 0.8
            diagnosis["supporting_logs"] = [
                raw_signature or "Raw input normalized from pasted logs",
                *diagnosis["supporting_logs"],
            ]
            diagnosis["correlation_analysis"] = (
                "The raw logs were normalized into service, severity, and signature before being matched to the incident narrative."
            )
            diagnosis["reasoning"] = (
                "The console is showing the parsed raw incident text, the extracted evidence, and the inferred incident pattern."
            )
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
        if incident.raw_input_text:
            runbook["summary"] = f"Remediation plan for the pasted {raw_service or 'service'} incident"
            runbook["recommended_runbook"] = (
                f"Validate {raw_service or 'service'} ownership, confirm the pasted signature, and prepare rollback-safe mitigation."
            )
            runbook["reasoning"] = (
                "The raw input has been normalized into a service and signature, so the remediation path can refer to the concrete incident evidence."
            )
        guardian = self._guardian_context(incident)
        guardian_decision = guardian["decision"]
        guardian["risk_class"] = "high" if priority["rank"] <= 2 else "medium"
        guardian["required_approval_level"] = "incident_manager" if priority["rank"] <= 2 else "operator"
        guardian["blocked_controls"] = guardian.get("policy_violations", [])
        guardian["rollback_readiness"] = "ready" if guardian_decision != "reject" else "needs_review"
        guardian["simulation_readiness"] = "ready" if guardian_decision != "reject" else "manual_review"
        if incident.status == "resolved":
            execution_result = "executed"
        elif incident.status == "blocked_by_guardian":
            execution_result = "blocked"
        elif incident.status == "needs_modification":
            execution_result = "needs_modification"
        elif guardian_decision == "approve":
            execution_result = "approved"
        elif guardian_decision == "reject":
            execution_result = "blocked"
        elif guardian_decision == "request_modification":
            execution_result = "needs_modification"
        else:
            execution_result = "pending"
        payload = {
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
                "raw_input_text": incident.raw_input_text,
                "normalized_evidence": incident.normalized_evidence,
            },
            "observability": observability,
            "classification": classification,
            "diagnosis": diagnosis,
            "runbook": runbook,
            "guardian": guardian,
            "triage_summary": build_triage_summary(
                incident_name=incident.title,
                service=raw_service or incident.service or incident.nexus_incident_id,
                severity=incident.severity,
                root_cause=diagnosis["root_cause"],
                source_channel=self._queue_source_channel(incident.source),
                detected_signals=observability["recent_logs"],
            ),
            "structured_result": build_structured_result(
                incident_id=incident.nexus_incident_id,
                root_cause=diagnosis["root_cause"],
                proposed_fix=runbook["recommended_runbook"],
                safety_decision=guardian_decision,
                confidence=guardian.get("confidence", 0.0),
                execution_status=execution_result,
                live_reasoning=False,
                raw_priority_label=priority["raw_label"],
                normalized_priority_label=priority["normalized_label"],
                normalized_priority_rank=priority["rank"],
                reward=0.72,
                guardian_policy_id=guardian.get("policy_id", ""),
                guardian_policy_name=guardian.get("policy_name", ""),
                guardian_policy_basis=guardian.get("policy_basis", ""),
            ),
            "workflow": workflow,
            "execution_result": execution_result,
            "reward": 0.72,
            "execution_time_ms": 12.4,
            "supported_incidents": [incident.nexus_incident_id],
            "live_reasoning": False,
            "llm_access": build_llm_access(
                live_reasoning_requested=bool(live_reasoning),
                user_key_provided=bool(openai_api_key),
                server_key_available=bool(os.environ.get("OPENAI_API_KEY", "").strip()),
                live_reasoning_active=False,
            ),
        }
        payload.update(
            await self._build_enterprise_overlay(
                incident_id=incident.nexus_incident_id,
                incident_name=incident.title,
                service=raw_service or incident.service or incident.nexus_incident_id,
                severity=incident.severity,
                source_channel=self._queue_source_channel(incident.source),
                classification=classification,
                diagnosis=diagnosis,
                runbook=runbook,
                guardian=guardian,
                observability=observability,
                workflow=workflow,
                tenant_id=tenant_id or incident.tenant_id,
            )
        )
        payload["enterprise_summary"] = build_training_enterprise_summary(
            {
                "summary": {"trained_reward": payload["reward"]},
                "agent_accuracy": {
                    "sentinel": classification["confidence"],
                    "prism": diagnosis["confidence"],
                    "forge": runbook_score_from_candidates(runbook),
                    "guardian": guardian.get("confidence", 0.0),
                },
            }
        )
        return payload

    async def record_guardian_decision(
        self,
        nexus_incident_id: str,
        *,
        payload: GuardianDecisionRequest,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        if tenant_id is None:
            loaded = await self._session.incidents.get_incident(nexus_incident_id)
        else:
            loaded = await self._session.incidents.get_incident_for_tenant(nexus_incident_id, tenant_id)
        if loaded is None:
            raise HTTPException(status_code=404, detail="incident not found")

        incident = IncidentRecord.model_validate(loaded)
        reviewed_at = datetime.now(timezone.utc).isoformat()
        if incident.status == "resolved":
            next_status = "resolved"
        elif payload.decision == "reject":
            next_status = "blocked_by_guardian"
        elif payload.decision == "request_modification":
            next_status = "needs_modification"
        else:
            next_status = "investigating"
        policy = self._guardian_policy(payload.decision)
        updated = await self._session.incidents.update_incident_status(
            nexus_incident_id,
            status=next_status,
            guardian_decision=payload.decision,
            guardian_reasoning=payload.reasoning or "",
            guardian_reviewed_at=reviewed_at,
            guardian_policy_id=policy["policy_id"],
            guardian_policy_name=policy["policy_name"],
            guardian_policy_basis=policy["policy_basis"],
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="incident not found")
        await record_guardian_review(
            {
                "tenant_id": updated.tenant_id,
                "incident_id": updated.nexus_incident_id,
                "guardian_decision": updated.guardian_decision,
                "guardian_reasoning": updated.guardian_reasoning,
                "guardian_reviewed_at": updated.guardian_reviewed_at,
                "guardian_policy_id": updated.guardian_policy_id,
                "guardian_policy_name": updated.guardian_policy_name,
                "guardian_policy_basis": updated.guardian_policy_basis,
                "status": updated.status,
            }
        )

        recent_deployments = await self._deployment_lookup.get_recent_deployments(updated.service)
        queue_position, eta_sec = await self._queue_position_and_eta(
            updated.nexus_incident_id,
            tenant_id=updated.tenant_id,
        )
        response = IncidentLifecycleResponse(
            nexus_incident_id=updated.nexus_incident_id,
            external_id=updated.external_id,
            title=updated.title,
            severity=updated.severity,
            status=updated.status,
            source=updated.source,
            recent_deployments=recent_deployments,
            queue_position=queue_position,
            eta_sec=eta_sec,
            guardian_decision=updated.guardian_decision,
            guardian_reasoning=updated.guardian_reasoning,
            guardian_reviewed_at=updated.guardian_reviewed_at,
            guardian_policy_id=updated.guardian_policy_id,
            guardian_policy_name=updated.guardian_policy_name,
            guardian_policy_basis=updated.guardian_policy_basis,
        )
        return response.model_dump(mode="json")

    async def _build_raw_live_reasoning_payload(
        self,
        incident: IncidentRecord,
        *,
        lifecycle: dict[str, object],
        audit_logs: list[dict[str, object]],
        recent_deployments: list[dict[str, object]],
        workflow: list[dict[str, object]],
        raw_evidence: dict[str, object],
        live_reasoning_override: bool | None = None,
        openai_api_key: str | None = None,
    ) -> dict[str, object] | None:
        config = AppConfig()
        server_key = os.environ.get("OPENAI_API_KEY", "").strip()
        effective_key = openai_api_key or server_key
        use_live_llm = (config.use_live_llm and bool(server_key)) or bool(openai_api_key)
        if live_reasoning_override is not None:
            use_live_llm = live_reasoning_override and bool(effective_key)
        if not use_live_llm:
            return None

        try:
            raw_lines = [line.strip() for line in incident.raw_input_text.splitlines() if line.strip()]
            raw_service = str(raw_evidence.get("service", incident.service or "service")).strip() or "service"
            priority = priority_snapshot(incident.severity)
            system_context = SystemContext(
                service=raw_service,
                language="unknown",
                infra="production",
                dependencies=[incident.service] if incident.service else [],
            )
            raw_symptoms = list(raw_evidence.get("symptoms", [])) or raw_lines[:5] or [incident.title]
            signal_map = {
                "logs": list(raw_evidence.get("evidence", [])) or raw_lines[:5],
                "metrics": [
                    f"severity={incident.severity}",
                    f"service={raw_service}",
                ],
                "traces": [f"team={raw_evidence.get('team') or 'platform'}"],
            }

            config = AppConfig()
            sentinel = SentinelAgent(client=OpenAISentinelClient(api_key=effective_key), model_name=config.forge_model_name)
            prism = PrismAgent(
                observability=self._observability,
                client=OpenAIPrismClient(api_key=effective_key),
                model_name=config.forge_model_name,
            )
            forge = ForgeAgent(client=OpenAIForgeClient(api_key=effective_key), model_name=config.forge_model_name)
            guardian = GuardianAgent()

            sentinel_output = sentinel.classify(raw_symptoms=raw_symptoms, system_context=system_context)
            prism_output = await prism.diagnose(sentinel_output=sentinel_output, signals=signal_map)
            forge_output = await forge.generate_runbook(prism_output=prism_output, system_context=system_context)
            guardian_output = await guardian.review(
                forge_output=forge_output,
                sentinel_output=sentinel_output,
                prism_output=prism_output,
            )
        except Exception as exc:  # pragma: no cover - provider fallback path
            logger.warning("Raw live reasoning fallback triggered: %s", exc)
            return None

        reward = round(
            (sentinel_output.confidence + prism_output.confidence + guardian_output.safety_score) / 3,
            2,
        )
        if guardian_output.decision == "approve":
            execution_result = "executed"
        elif guardian_output.decision == "request_modification":
            execution_result = "needs_modification"
        else:
            execution_result = "blocked"
        live_observability = {
            "metrics": [
                {
                    "name": "Raw input lines",
                    "current": len(raw_lines),
                    "unit": "",
                    "series": [max(1, len(raw_lines) - 2), max(1, len(raw_lines) - 1), len(raw_lines), len(raw_lines) + 1, len(raw_lines) + 2],
                },
                {
                    "name": "Audit entries",
                    "current": len(audit_logs),
                    "unit": "",
                    "series": [max(1, len(audit_logs) - 2), max(1, len(audit_logs) - 1), len(audit_logs), len(audit_logs) + 1, len(audit_logs) + 2],
                },
            ],
            "recent_logs": [
                f"Raw input normalized for {raw_service}",
                *[f"{entry['timestamp']} · {entry['event_type']} · {entry['payload'].get('status', entry['payload'].get('current_stage', 'recorded'))}" for entry in audit_logs[-5:]],
            ],
            "alert_timeline": [
                {"time": step["timestamp"], "event": step["label"]}
                for step in workflow
            ],
            "recommended_runbooks": [
                f"Validate {raw_service} ownership and confirm the pasted signature",
                "Review audit trail and deployment metadata before execution",
            ],
            "evidence_sources": [
                {
                    "source": "raw input",
                    "signal": "paste",
                    "count": len(raw_lines),
                    "summary": "Operator-pasted incident text normalized into structured evidence.",
                    "detail": raw_lines[0] if raw_lines else "No raw text available.",
                },
                *self._observability.build_live_evidence_sources(
                    incident_id=incident.nexus_incident_id,
                    service=raw_service,
                    source_channel="raw_text",
                    audit_logs=audit_logs,
                    recent_deployments=recent_deployments,
                    timeline=workflow,
                ),
            ],
        }

        payload = {
            "incident": {
                "id": incident.nexus_incident_id,
                "name": incident.title,
                "severity": incident.severity,
                "summary": f"Live incident opened through the raw_text intake path.",
                "detected_at": incident.created_at or incident.updated_at or "now",
                "duration_minutes": 0,
                "related_services": [raw_service] if raw_service else [],
                "recent_deployments": recent_deployments,
                "similar_past_incidents": [],
                "source_channel": "raw_text",
                "raw_input_text": incident.raw_input_text,
                "normalized_evidence": raw_evidence,
            },
            "observability": live_observability,
            "classification": {
                "incident_id": sentinel_output.incident_id,
                "incident_name": sentinel_output.incident_name,
                "severity": sentinel_output.severity,
                "confidence": sentinel_output.confidence,
                "confidence_breakdown": {
                    "intake": 0.34,
                    "audit": 0.18,
                    "evidence": 0.26,
                    "context": 0.22,
                },
                "evidence": sentinel_output.reasoning.split(". ") if sentinel_output.reasoning else raw_symptoms[:3],
                "reasoning": sentinel_output.reasoning,
            },
            "diagnosis": {
                "root_cause": prism_output.root_cause,
                "confidence": prism_output.confidence,
                "supporting_logs": prism_output.evidence or live_observability["recent_logs"],
                "correlation_analysis": prism_output.reasoning,
                "reasoning": prism_output.reasoning,
            },
            "runbook": {
                "language": forge_output.runbook.language,
                "summary": forge_output.runbook.summary,
                "selection_logic": "LLM-generated remediation path grounded in raw incident text and safety review.",
                "candidate_fixes": [
                    {"action": forge_output.runbook.summary, "success_rate": max(0.0, min(0.99, guardian_output.safety_score))},
                ],
                "recommended_runbook": forge_output.runbook.summary,
                "reasoning": forge_output.reasoning,
                "cost_usd": round(forge_output.estimated_cost_usd, 2),
            },
            "guardian": {
                "decision": guardian_output.decision,
                "confidence": guardian_output.safety_score,
                "safety_checks": [
                    "Authenticated live incident read",
                    "Raw input normalized before model reasoning",
                    "Rollback-safe execution path preserved",
                ],
                "policy_violations": guardian_output.blocked_patterns,
                "reasoning": guardian_output.reasoning,
                "policy_id": guardian_output.policy_id,
                "policy_name": guardian_output.policy_name,
                "policy_basis": guardian_output.policy_basis,
                "risk_class": guardian_output.risk_class or ("high" if priority["rank"] <= 2 else "medium"),
                "required_approval_level": guardian_output.required_approval_level or ("incident_manager" if priority["rank"] <= 2 else "operator"),
                "blocked_controls": guardian_output.blocked_controls,
                "rollback_readiness": guardian_output.rollback_readiness or "ready",
                "simulation_readiness": guardian_output.simulation_readiness or "ready",
            },
            "triage_summary": build_triage_summary(
                incident_name=incident.title,
                service=raw_service,
                severity=incident.severity,
                root_cause=prism_output.root_cause,
                source_channel="raw_text",
                detected_signals=live_observability["recent_logs"],
            ),
            "structured_result": build_structured_result(
                incident_id=incident.nexus_incident_id,
                root_cause=prism_output.root_cause,
                proposed_fix=forge_output.runbook.summary,
                safety_decision=guardian_output.decision,
                confidence=guardian_output.safety_score,
                execution_status=execution_result,
                live_reasoning=True,
                raw_priority_label=priority["raw_label"],
                normalized_priority_label=priority["normalized_label"],
                normalized_priority_rank=priority["rank"],
                reward=reward,
                guardian_policy_id=guardian_output.policy_id,
                guardian_policy_name=guardian_output.policy_name,
                guardian_policy_basis=guardian_output.policy_basis,
            ),
            "workflow": workflow,
            "execution_result": execution_result,
            "reward": reward,
            "execution_time_ms": 18.4,
            "supported_incidents": [incident.nexus_incident_id],
            "agent_models": {
                "sentinel": config.forge_model_name,
                "prism": config.forge_model_name,
                "forge": forge_output.model_name,
                "guardian": "deterministic",
            },
            "live_reasoning": True,
            "llm_access": build_llm_access(
                live_reasoning_requested=bool(live_reasoning_override),
                user_key_provided=bool(openai_api_key),
                server_key_available=bool(server_key),
                live_reasoning_active=True,
            ),
            "learning_state": {
                "observation": {
                    "incident_id": incident.nexus_incident_id,
                    "source": "raw_text",
                    "service": raw_service,
                    "evidence_count": len(raw_evidence.get("evidence", [])) if isinstance(raw_evidence.get("evidence"), list) else 0,
                },
                "reward_components": {
                    "classification": round(sentinel_output.confidence, 2),
                    "diagnosis": round(prism_output.confidence, 2),
                    "safety": round(guardian_output.safety_score, 2),
                },
            },
        }
        payload.update(
            await self._build_enterprise_overlay(
                incident_id=incident.nexus_incident_id,
                incident_name=incident.title,
                service=raw_service,
                severity=incident.severity,
                source_channel="raw_text",
                classification=payload["classification"],
                diagnosis=payload["diagnosis"],
                runbook=payload["runbook"],
                guardian=payload["guardian"],
                observability=live_observability,
                workflow=workflow,
                tenant_id=incident.tenant_id,
            )
        )
        payload["enterprise_summary"] = build_training_enterprise_summary(
            {
                "summary": {"trained_reward": reward},
                "agent_accuracy": {
                    "sentinel": sentinel_output.confidence,
                    "prism": prism_output.confidence,
                    "forge": max((item.get("success_rate", 0.0) for item in payload["runbook"]["candidate_fixes"]), default=0.0),
                    "guardian": guardian_output.safety_score,
                },
            }
        )
        return payload

    async def execute_incident(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        lifecycle = await self.get_incident_status(nexus_incident_id, tenant_id=tenant_id)
        guardian_decision = str(lifecycle.get("guardian_decision") or "pending")
        policy = self._guardian_policy(guardian_decision)
        executed = lifecycle.get("status") not in {"blocked_by_guardian", "needs_modification"}
        if guardian_decision == "approve":
            executed = True
        elif guardian_decision in {"reject", "request_modification"}:
            executed = False
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
            "status": "executed" if executed else "needs_modification" if guardian_decision == "request_modification" else "blocked_by_guardian",
            "result": "deterministic_demo_run",
            "queue_position": lifecycle.get("queue_position", 1),
            "eta_sec": lifecycle.get("eta_sec", 30),
            "guardian_decision": guardian_decision,
            "guardian_policy_id": lifecycle.get("guardian_policy_id") or policy["policy_id"],
            "guardian_policy_name": lifecycle.get("guardian_policy_name") or policy["policy_name"],
            "guardian_policy_basis": lifecycle.get("guardian_policy_basis") or policy["policy_basis"],
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
            severity=self._display_severity(incident.severity),
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
        normalized = normalize_priority_label(severity)
        if normalized.startswith("P") and normalized[1:].isdigit():
            return shift_priority_label(normalized)
        return normalized

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
                "guardian_decision": incident.guardian_decision,
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

    def _queue_sort_key(self, item: QueueIncidentSummary) -> tuple[int, int, int, str]:
        updated_at = self._parse_timestamp(item.updated_at)
        active_weight = 1 if item.status == "investigating" else 0
        return active_weight, -priority_rank(item.severity), int(updated_at.timestamp()), item.nexus_incident_id

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
        if source in {"raw_text", "manual_form", "slack_command", "stream_anomaly", "batch_import"}:
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
                    severity=self._display_severity(incident.severity),
                    status=status_by_incident.get(incident_id, "investigating"),
                    source_channel=self._demo_source_channel(incident_id),
                    current_stage=stage_by_incident.get(incident_id, IncidentWorkflowStage.INCIDENT_RECEIVED),
                    updated_at=str(details["detected_at"]),
                )
            )
        return items

    def _derive_current_stage(self, lifecycle: dict[str, object]) -> IncidentWorkflowStage:
        guardian_decision = str(lifecycle.get("guardian_decision") or "pending")
        if lifecycle.get("status") == "resolved":
            return IncidentWorkflowStage.EXECUTED_VERIFIED_LEARNED
        if lifecycle.get("status") in {"blocked_by_guardian", "needs_modification"}:
            return IncidentWorkflowStage.GUARDIAN_REVIEWED_SAFETY
        if guardian_decision in {"approve", "reject", "request_modification"}:
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
            severity=self._display_severity(incident.severity),
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
        summary["enterprise_summary"] = build_training_enterprise_summary(payload)
        await record_training_snapshot(
            {
                "tenant_id": tenant_id,
                "summary": summary.get("summary", {}),
                "episode_records": len(summary.get("episode_records", [])),
                "live_incidents": len(summary.get("live_incidents", [])),
                "enterprise_summary": summary["enterprise_summary"],
            }
        )
        if summary.get("rl_episode_contract"):
            await record_learning_contract(
                {
                    "tenant_id": tenant_id,
                    "contract": summary.get("rl_episode_contract", {}),
                    "reward_evaluation": summary.get("reward_evaluation", {}),
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
                    "severity": self._display_severity(incident.severity),
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
            "certificate_expiry": ("INC006", ["webhook", "edge-gateway", "P0", "expiry"]),
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
                        f"Severity: {self._display_severity(incident.severity)}",
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
            "reward_evaluation": payload.get("reward_evaluation", {}),
            "rl_episode_contract": payload.get("rl_episode_contract", {}),
            "enterprise_summary": build_training_enterprise_summary(payload),
        }
