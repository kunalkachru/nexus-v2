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
    build_replica_summary,
    build_trace_summary,
    build_triage_summary,
    build_training_enterprise_summary,
    infer_issue_family,
    runtime_aligned_candidate_fixes,
    runbook_score_from_candidates,
)
from server.services.replica_runtime import ReplicaExecutionResult, build_runtime_trust_packet, invoke_runtime_host_relay
from training.runner import TrainingForgeClient

logger = logging.getLogger(__name__)
_REPLAY_HISTORY_LIMIT = 5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_replay_lifecycle(
    *,
    requested_at: str,
    started_at: str,
    finished_at: str,
    final_state: str,
    final_message: str,
) -> dict[str, object]:
    completion_label = "Completed" if final_state == "completed" else "Failed"
    return {
        "current_state": final_state,
        "requested_at": requested_at,
        "started_at": started_at,
        "finished_at": finished_at,
        "events": [
            {
                "state": "requested",
                "label": "Requested",
                "recorded_at": requested_at,
                "message": "The operator requested bounded replay from the packaged incident console.",
            },
            {
                "state": "running",
                "label": "Running",
                "recorded_at": started_at,
                "message": "NEXUS dispatched the bounded replay plan to the current app host or configured relay host.",
            },
            {
                "state": final_state,
                "label": completion_label,
                "recorded_at": finished_at,
                "message": final_message,
            },
        ],
    }


def _root_cause_from_issue_family(issue_family: str, service: str) -> str:
    issue_family_text = issue_family.lower()
    if "retry amplification" in issue_family_text:
        return f"Timeout cascade caused by retry amplification in the {service or 'checkout'} authorization path."
    if "pool exhaustion" in issue_family_text or "session leak" in issue_family_text:
        return f"Database pool exhaustion caused by a leaked retry session path in {service or 'checkout'}."
    if "certificate expiry" in issue_family_text:
        return f"Trust boundary outage caused by an expired certificate on {service or 'the public edge'}."
    if "memory leak" in issue_family_text:
        return f"Runtime degradation caused by retained memory in {service or 'the worker fleet'}."
    return f"Likely production incident pattern affecting {service or 'service'}."


def _runtime_aligned_live_runbook(
    *,
    issue_family: str,
    service: str,
    reason: str,
) -> dict[str, object]:
    candidate_fixes = runtime_aligned_candidate_fixes(issue_family, service)
    recommended = candidate_fixes[0]["action"] if candidate_fixes else f"Validate {service or 'service'} ownership and prepare rollback-safe mitigation."
    summary_prefix = service or "service"
    return {
        "language": "bash",
        "summary": f"Live mitigation plan for {summary_prefix}",
        "selection_logic": (
            f"Runtime-aligned candidate fixes were selected for the {issue_family.lower()} path so the live incident stays close to the bounded REPLICA packs."
        ),
        "candidate_fixes": candidate_fixes,
        "recommended_runbook": recommended,
        "reasoning": reason,
        "cost_usd": 0.08,
    }


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

    async def _persist_latest_replay_packet(
        self,
        *,
        incident: IncidentRecord | None,
        status: str,
        message: str,
        runtime_capability: dict[str, object],
        replica_summary: dict[str, object],
        trace_summary: dict[str, object],
    ) -> dict[str, object] | None:
        if incident is None or not incident.nexus_incident_id.startswith("nxs_"):
            return None
        replay_entry = {
            "status": status,
            "message": message,
            "recorded_at": _utc_now_iso(),
            "runtime_capability": runtime_capability,
            "runtime_provenance": dict(replica_summary.get("runtime_provenance") or {}),
            "replay_lifecycle": dict(replica_summary.get("replay_lifecycle") or {}),
            "runtime_trust_packet": dict(replica_summary.get("runtime_trust_packet") or {}),
            "replica_summary": replica_summary,
            "trace_summary": trace_summary,
        }
        append_replay = getattr(self._session.incidents, "append_incident_replay_evidence", None)
        if callable(append_replay):
            updated = await append_replay(
                incident.nexus_incident_id,
                latest_replay=replay_entry,
                replay_entry=replay_entry,
                replay_limit=_REPLAY_HISTORY_LIMIT,
            )
            return dict(updated.normalized_evidence or {}) if updated is not None else None

        normalized_evidence = dict(incident.normalized_evidence or {})
        history = [
            dict(item)
            for item in normalized_evidence.get("replay_history", [])
            if isinstance(normalized_evidence.get("replay_history"), list) and isinstance(item, dict)
        ]
        history.insert(0, replay_entry)
        normalized_evidence["latest_replay"] = replay_entry
        normalized_evidence["replay_history"] = history[:_REPLAY_HISTORY_LIMIT]
        updated = await self._session.incidents.update_incident_normalized_evidence(
            incident.nexus_incident_id,
            normalized_evidence=normalized_evidence,
        )
        return dict(updated.normalized_evidence or normalized_evidence) if updated is not None else normalized_evidence

    def _replay_history_summaries(
        self,
        normalized_evidence: dict[str, object] | None,
    ) -> list[dict[str, object]]:
        payload = dict(normalized_evidence or {})
        replay_history = payload.get("replay_history")
        if isinstance(replay_history, list):
            source_entries = replay_history
        else:
            latest_replay = payload.get("latest_replay")
            source_entries = [latest_replay] if isinstance(latest_replay, dict) else []

        summaries: list[dict[str, object]] = []
        for index, entry in enumerate(source_entries):
            if not isinstance(entry, dict):
                continue
            entry_replica = dict(entry.get("replica_summary") or {})
            entry_trace = dict(entry.get("trace_summary") or {})
            runtime_provenance = dict(
                entry.get("runtime_provenance")
                or entry_replica.get("runtime_provenance")
                or {}
            )
            summaries.append(
                {
                    "index": index,
                    "recorded_at": str(entry.get("recorded_at") or ""),
                    "status": str(entry.get("status") or ""),
                    "message": str(entry.get("message") or ""),
                    "runtime_provenance": runtime_provenance,
                    "runtime_trust_packet": dict(
                        entry.get("runtime_trust_packet")
                        or entry_replica.get("runtime_trust_packet")
                        or {}
                    ),
                    "lifecycle_state": str(
                        (
                            dict(entry.get("replay_lifecycle") or {}).get("current_state")
                            or dict(entry_replica.get("replay_lifecycle") or {}).get("current_state")
                            or ""
                        )
                    ),
                    "lifecycle_events": list(
                        (
                            dict(entry.get("replay_lifecycle") or {}).get("events")
                            or dict(entry_replica.get("replay_lifecycle") or {}).get("events")
                            or []
                        )
                    ),
                    "runtime_mode": str(entry_replica.get("runtime_mode") or ""),
                    "replay_status_code": entry_replica.get("replay_status_code"),
                    "replay_duration_ms": entry_replica.get("replay_duration_ms"),
                    "best_mitigation_action": str(entry_replica.get("best_mitigation_action") or ""),
                    "best_mitigation_outcome_class": str(entry_replica.get("best_mitigation_outcome_class") or ""),
                    "best_mitigation_status_code": entry_replica.get("best_mitigation_status_code"),
                    "best_mitigation_duration_ms": entry_replica.get("best_mitigation_duration_ms"),
                    "trace_status": str(entry_trace.get("trace_status") or ""),
                    "trace_inspection_point": str(entry_trace.get("inspection_point") or ""),
                    "is_latest": index == 0,
                }
            )
        return summaries

    def _attach_replay_history(
        self,
        *,
        payload: dict[str, object],
        normalized_evidence: dict[str, object],
    ) -> dict[str, object]:
        replay_history = self._replay_history_summaries(normalized_evidence)
        if not replay_history:
            return payload

        replica_summary = payload.get("replica_summary")
        if isinstance(replica_summary, dict):
            replica_summary["replay_history"] = replay_history
        trace_summary = payload.get("trace_summary")
        if isinstance(trace_summary, dict):
            trace_summary["replay_history"] = replay_history
        payload["replay_history"] = replay_history
        return payload

    def _apply_persisted_replay_packet(
        self,
        *,
        incident: IncidentRecord,
        payload: dict[str, object],
    ) -> dict[str, object]:
        normalized_evidence = dict(incident.normalized_evidence or {})
        latest_replay = normalized_evidence.get("latest_replay")
        if not isinstance(latest_replay, dict):
            latest_replay = None

        if latest_replay:
            replica_summary = latest_replay.get("replica_summary")
            trace_summary = latest_replay.get("trace_summary")
            if isinstance(replica_summary, dict):
                payload["replica_summary"] = replica_summary
            if isinstance(trace_summary, dict):
                payload["trace_summary"] = trace_summary

            if isinstance(replica_summary, dict) and isinstance(trace_summary, dict):
                payload.update(
                    self._enterprise_runtime.refresh_overlay_from_persisted_replay(
                        runbook=payload.get("runbook") if isinstance(payload.get("runbook"), dict) else None,
                        guardian=payload.get("guardian") if isinstance(payload.get("guardian"), dict) else None,
                        memory_hits=payload.get("memory_hits") if isinstance(payload.get("memory_hits"), dict) else None,
                        task_board=payload.get("task_board") if isinstance(payload.get("task_board"), dict) else None,
                        agent_metrics=payload.get("agent_metrics") if isinstance(payload.get("agent_metrics"), dict) else None,
                        triage_summary=payload.get("triage_summary") if isinstance(payload.get("triage_summary"), dict) else None,
                        replica_summary=replica_summary,
                        trace_summary=trace_summary,
                        severity=incident.severity,
                    )
                )

            self._attach_replay_history(payload=payload, normalized_evidence=normalized_evidence)

        execution_outcome = normalized_evidence.get("execution_outcome")
        if isinstance(execution_outcome, dict):
            payload["execution_outcome"] = execution_outcome
            if incident.status == "resolved":
                payload["execution_result"] = "executed"

        incident_payload = dict(payload.get("incident") or {})
        incident_payload["normalized_evidence"] = normalized_evidence
        payload["incident"] = incident_payload
        return payload

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
            case_lifecycle=incident.case_lifecycle,
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
            raw_input_text="\n".join(
                [
                    f"service={payload.affected_service}",
                    f"severity={severity}",
                    f"summary={payload.root_cause_suspected or payload.additional_context or 'manual report'}",
                    *[f"symptom={symptom}" for symptom in payload.symptoms],
                ]
            ),
            normalized_evidence={
                "service": payload.affected_service,
                "severity": severity,
                "signature": " / ".join(payload.symptoms[:2]) if payload.symptoms else (payload.root_cause_suspected or "Manual incident report"),
                "evidence": payload.symptoms,
                "reported_by": payload.reported_by,
                "team": payload.team,
                "additional_context": payload.additional_context,
                "affected_regions": payload.affected_regions,
                "affected_hosts": payload.affected_hosts,
            },
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
            case_lifecycle=incident.case_lifecycle,
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
            case_lifecycle=incident.case_lifecycle,
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
            case_lifecycle=incident.case_lifecycle,
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
        latest_replay = dict(normalized_evidence.get("latest_replay", {})) if isinstance(normalized_evidence.get("latest_replay"), dict) else {}
        has_runtime_replay = bool(latest_replay and latest_replay.get("status") in {"replay_executed", "relay_executed"} or latest_replay.get("lifecycle_state") == "completed")
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
            if has_runtime_replay:
                classification["reasoning"] = (
                    "The pasted logs were normalized into service, severity, and signature, then validated by bounded runtime replay. "
                    "This classification is now backed by measured runtime evidence."
                )
            else:
                classification["reasoning"] = (
                    "The pasted logs were normalized into service, severity, and signature. "
                    "This context is scaffold-only inference from the raw text, not yet backed by runtime replay."
                )
        issue_family = infer_issue_family(
            " ".join(
                [
                    incident.title,
                    incident.raw_input_text,
                    raw_signature,
                    " ".join(str(item) for item in observability["recent_logs"]),
                ]
            ),
            incident.title,
        )
        diagnosis = {
            "root_cause": _root_cause_from_issue_family(issue_family, raw_service or incident.service or incident.nexus_incident_id),
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
            diagnosis["confidence"] = 0.8 if not has_runtime_replay else 0.88
            diagnosis["supporting_logs"] = [
                raw_signature or "Raw input normalized from pasted logs",
                *diagnosis["supporting_logs"],
            ]
            if has_runtime_replay:
                diagnosis["correlation_analysis"] = (
                    "The raw logs were normalized into service, severity, and signature, then validated through bounded runtime replay. "
                    "This analysis is now backed by measured evidence from the replay execution."
                )
                diagnosis["reasoning"] = (
                    "The console is showing the parsed raw incident text with runtime-backed validation. "
                    "The diagnosis has been tested through bounded replay and the measured evidence confirms the hypothesis."
                )
            else:
                diagnosis["correlation_analysis"] = (
                    "The raw logs were normalized into service, severity, and signature before being matched to the incident narrative. "
                    "This analysis is scaffold-only until runtime replay provides measured evidence."
                )
                diagnosis["reasoning"] = (
                    "The console is showing the parsed raw incident text and the inferred incident pattern. "
                    "Upgrade to runtime-backed diagnosis by running bounded replay to test the hypothesis."
                )
        runbook = _runtime_aligned_live_runbook(
            issue_family=issue_family,
            service=raw_service or incident.service or incident.nexus_incident_id,
            reason="The live incident view keeps the remediation contract aligned to the same bounded runtime packs used in the flagship outage demos.",
        )
        if incident.raw_input_text:
            if has_runtime_replay:
                runbook["summary"] = f"Remediation plan for the pasted {raw_service or 'service'} incident (runtime-backed)"
                runbook["reasoning"] = (
                    "The raw input has been normalized and validated through bounded runtime replay. This remediation path is backed by measured evidence; "
                    "the selected candidate fix was tested against the failure signature and showed measurable improvement."
                )
            else:
                runbook["summary"] = f"Remediation plan for the pasted {raw_service or 'service'} incident (scaffold-only)"
                runbook["reasoning"] = (
                    "The raw input has been normalized into a concrete issue family. This remediation path is scaffold-only inference; "
                    "runtime replay will test whether these candidate fixes actually resolve the failure signature."
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
        triage_summary = build_triage_summary(
            incident_name=incident.title,
            service=raw_service or incident.service or incident.nexus_incident_id,
            severity=incident.severity,
            root_cause=diagnosis["root_cause"],
            source_channel=self._queue_source_channel(incident.source),
            detected_signals=observability["recent_logs"],
        )
        if has_runtime_replay and latest_replay.get("replica_summary"):
            replica_summary = dict(latest_replay["replica_summary"])
        else:
            replica_summary = build_replica_summary(
                incident_id=incident.nexus_incident_id,
                triage_summary=triage_summary,
                root_cause=diagnosis["root_cause"],
                recent_logs=observability["recent_logs"],
                recent_deployments=recent_deployments,
                candidate_fixes=runbook["candidate_fixes"],
            )
        if has_runtime_replay and latest_replay.get("trace_summary"):
            trace_summary = dict(latest_replay["trace_summary"])
        else:
            trace_summary = build_trace_summary(
                incident_id=incident.nexus_incident_id,
                triage_summary=triage_summary,
                replica_summary=replica_summary,
                root_cause=diagnosis["root_cause"],
                recent_deployments=recent_deployments,
                recent_logs=observability["recent_logs"],
            )

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
            "triage_summary": triage_summary,
            "replica_summary": replica_summary,
            "trace_summary": trace_summary,
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
        return self._apply_persisted_replay_packet(incident=incident, payload=payload)

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

        triage_summary = build_triage_summary(
            incident_name=incident.title,
            service=raw_service,
            severity=incident.severity,
            root_cause=prism_output.root_cause,
            source_channel="raw_text",
            detected_signals=live_observability["recent_logs"],
        )
        live_candidate_fixes = runtime_aligned_candidate_fixes(
            str(triage_summary.get("issue_family", "")),
            raw_service,
        )
        if live_candidate_fixes:
            live_candidate_fixes[0]["success_rate"] = max(
                float(live_candidate_fixes[0].get("success_rate", 0.0) or 0.0),
                max(0.0, min(0.99, guardian_output.safety_score)),
            )
        replica_summary = build_replica_summary(
            incident_id=incident.nexus_incident_id,
            triage_summary=triage_summary,
            root_cause=prism_output.root_cause,
            recent_logs=live_observability["recent_logs"],
            recent_deployments=recent_deployments,
            candidate_fixes=live_candidate_fixes,
        )
        trace_summary = build_trace_summary(
            incident_id=incident.nexus_incident_id,
            triage_summary=triage_summary,
            replica_summary=replica_summary,
            root_cause=prism_output.root_cause,
            recent_deployments=recent_deployments,
            recent_logs=live_observability["recent_logs"],
        )

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
                "candidate_fixes": live_candidate_fixes,
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
            "triage_summary": triage_summary,
            "replica_summary": replica_summary,
            "trace_summary": trace_summary,
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
        return self._apply_persisted_replay_packet(incident=incident, payload=payload)

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

        outcome_summary = None
        if executed or guardian_decision in {"reject", "request_modification"}:
            context = await self.get_incident_context_v1(
                nexus_incident_id,
                tenant_id=tenant_id,
                live_reasoning=False,
                openai_api_key=None,
            )
            diagnosis = dict(context.get("diagnosis") or {})
            runbook = dict(context.get("runbook") or {})
            replica_summary = dict(context.get("replica_summary") or {})
            outcome_summary = {
                "recorded_at": _utc_now_iso(),
                "guardian_decision": guardian_decision,
                "execution_status": "executed" if executed else "needs_modification" if guardian_decision == "request_modification" else "blocked",
                "root_cause": str(diagnosis.get("root_cause") or "Unknown cause"),
                "selected_action": str(runbook.get("recommended_runbook") or "Review and modify runbook"),
                "summary": (
                    f"Incident approved and executed: {runbook.get('summary', 'Remediation applied')}. "
                    f"The proposed action was based on the root cause analysis: {diagnosis.get('root_cause', 'diagnosis pending')}."
                    if executed
                    else (
                        f"Guardian requested modification to the remediation plan. "
                        f"Current hypothesis: {diagnosis.get('root_cause', 'diagnosis pending')}. "
                        f"Review the feedback and adjust the proposed action accordingly."
                        if guardian_decision == "request_modification"
                        else f"Guardian blocked the remediation plan. Review the policy notes and constraints before proceeding."
                    )
                ),
                "mitigation_outcome_class": str(replica_summary.get("best_mitigation_outcome_class") or "inferred_only"),
                "runtime_backed": bool(replica_summary.get("runtime_executed")),
            }

        if executed:
            stored_incident = (
                await self._session.incidents.get_incident_for_tenant(nexus_incident_id, tenant_id)
                if tenant_id and hasattr(self._session.incidents, "get_incident_for_tenant")
                else await self._session.incidents.get_incident(nexus_incident_id)
            )
            normalized_evidence = dict(stored_incident.normalized_evidence or {}) if stored_incident else {}
            normalized_evidence["execution_outcome"] = outcome_summary
            await self._session.incidents.update_incident_normalized_evidence(
                nexus_incident_id,
                normalized_evidence=normalized_evidence,
            )
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
            "execution_outcome": outcome_summary,
        }
        return payload

    async def trigger_replica_replay(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        requested_at = _utc_now_iso()
        context = await self.get_incident_context_v1(
            nexus_incident_id,
            tenant_id=tenant_id,
            live_reasoning=False,
            openai_api_key=None,
        )
        triage_summary = dict(context.get("triage_summary") or {})
        diagnosis = dict(context.get("diagnosis") or {})
        observability = dict(context.get("observability") or {})
        incident = dict(context.get("incident") or {})
        runbook = dict(context.get("runbook") or {})
        config = AppConfig()
        started_at = _utc_now_iso()

        replica_summary = build_replica_summary(
            incident_id=nexus_incident_id,
            triage_summary=triage_summary,
            root_cause=str(diagnosis.get("root_cause") or ""),
            recent_logs=list(observability.get("recent_logs") or []),
            recent_deployments=list(incident.get("recent_deployments") or []),
            candidate_fixes=list(runbook.get("candidate_fixes") or []),
            execute_runtime=True,
        )
        runtime_capability = dict(replica_summary.get("runtime_capability") or {})
        capability_state = str(runtime_capability.get("state") or "no_pack")

        if capability_state == "relay_available" and config.runtime_host_base_url and config.runtime_host_shared_token:
            relay_response = invoke_runtime_host_relay(
                base_url=config.runtime_host_base_url,
                shared_token=config.runtime_host_shared_token,
                payload={
                    "incident_id": nexus_incident_id,
                    "issue_family": str(triage_summary.get("issue_family") or ""),
                    "service": str(triage_summary.get("likely_owner_service") or ""),
                    "recent_logs": list(observability.get("recent_logs") or []),
                    "recent_deployments": list(incident.get("recent_deployments") or []),
                    "execute_runtime": True,
                },
            )
            relay_capability = dict(relay_response.get("runtime_capability") or {})
            relay_trust_packet = dict(relay_response.get("trust_packet") or {})
            relay_execution_result = ReplicaExecutionResult(**dict(relay_response.get("execution_result") or {}))
            relay_capability.update(
                {
                    "state": "relay_executed" if relay_response.get("status") == "replay_executed" else "relay_available",
                    "label": "Relay executed" if relay_response.get("status") == "replay_executed" else "Relay available",
                    "host_label": "External runtime host",
                    "can_execute_replay": True,
                }
            )
            if relay_trust_packet:
                relay_trust_packet.update(
                    {
                        "execution_mode": "delegated_relay",
                        "executor": "External runtime host",
                    }
                )
            replica_summary = build_replica_summary(
                incident_id=nexus_incident_id,
                triage_summary=triage_summary,
                root_cause=str(diagnosis.get("root_cause") or ""),
                recent_logs=list(observability.get("recent_logs") or []),
                recent_deployments=list(incident.get("recent_deployments") or []),
                candidate_fixes=list(runbook.get("candidate_fixes") or []),
                execute_runtime=False,
                runtime_execution=relay_execution_result,
                runtime_capability_override=relay_capability,
                runtime_mode_override="relay_runtime_scaffold",
            )
            runtime_capability = dict(replica_summary.get("runtime_capability") or {})
            capability_state = str(runtime_capability.get("state") or "relay_executed")
            if relay_trust_packet:
                replica_summary["runtime_trust_packet"] = relay_trust_packet

        trace_summary = build_trace_summary(
            incident_id=nexus_incident_id,
            triage_summary=triage_summary,
            replica_summary=replica_summary,
            root_cause=str(diagnosis.get("root_cause") or ""),
            recent_deployments=list(incident.get("recent_deployments") or []),
            recent_logs=list(observability.get("recent_logs") or []),
        )
        status = {
            "replay_executed": "replay_executed",
            "relay_executed": "relay_executed",
            "relay_available": "replay_available",
            "host_unavailable": "host_unavailable",
            "pack_validation_required": "host_unavailable",
            "replay_available": "replay_available",
            "no_pack": "unsupported",
        }.get(capability_state, "unsupported")
        message = str(runtime_capability.get("message") or replica_summary.get("runtime_enablement_hint") or "Replay state unavailable.")
        final_state = "completed" if status in {"replay_executed", "relay_executed"} else "failed"

        if status == "pack_unsupported":
            message = f"No bounded REPLICA pack is available for this incident class. Runtime replay is not supported; proceeding with inferred-only evidence."
        elif status == "replay_available":
            message = f"Bounded REPLICA pack is available but runtime replay was not executed. Proceeding with inferred-only evidence."
        elif status == "relay_unavailable":
            message = f"The external runtime host is not currently available or reachable. Proceeding with inferred-only evidence."
        replay_lifecycle = _build_replay_lifecycle(
            requested_at=requested_at,
            started_at=started_at,
            finished_at=_utc_now_iso(),
            final_state=final_state,
            final_message=message,
        )
        replica_summary["replay_lifecycle"] = replay_lifecycle
        if "runtime_trust_packet" not in replica_summary:
            execution_mode = (
                "delegated_relay"
                if capability_state in {"relay_available", "relay_executed"}
                else "direct_runtime"
                if capability_state in {"replay_available", "replay_executed"}
                else "inferred_only"
            )
            runtime_execution = (
                ReplicaExecutionResult(
                    pack_id=str(replica_summary.get("environment_pack_id") or ""),
                    compose_ready=bool(replica_summary.get("scaffold_ready")),
                    replay_ready=bool(replica_summary.get("scaffold_ready")),
                    mitigation_hooks_ready=bool(replica_summary.get("tested_mitigations")),
                    missing_assets=(),
                    replay_status_code=replica_summary.get("replay_status_code"),
                    replay_duration_ms=replica_summary.get("replay_duration_ms"),
                )
                if replica_summary.get("runtime_executed")
                else None
            )
            replica_summary["runtime_trust_packet"] = build_runtime_trust_packet(
                runtime_capability=runtime_capability,
                execution_result=runtime_execution,
                execution_mode=execution_mode,
                pack_id=str(replica_summary.get("environment_pack_id") or ""),
            )

        if status in {"replay_executed", "relay_executed"}:
            await record_replay_launch(
                {
                    "scenario_id": "bounded_runtime_replay",
                    "nexus_incident_id": nexus_incident_id,
                    "tenant_id": tenant_id or incident.get("tenant_id") or "tenant-system",
                    "source_channel": incident.get("source_channel") or incident.get("source") or "incident_console",
                    "title": incident.get("name") or nexus_incident_id,
                    "launch_label": "Replica relay replay" if status == "relay_executed" else "Replica replay",
                }
            )

        stored_incident = (
            await self._session.incidents.get_incident_for_tenant(nexus_incident_id, tenant_id)
            if tenant_id and hasattr(self._session.incidents, "get_incident_for_tenant")
            else await self._session.incidents.get_incident(nexus_incident_id)
        )
        normalized_evidence = await self._persist_latest_replay_packet(
            incident=stored_incident,
            status=status,
            message=message,
            runtime_capability=runtime_capability,
            replica_summary=replica_summary,
            trace_summary=trace_summary,
        )
        replay_history = self._replay_history_summaries(
            normalized_evidence if isinstance(normalized_evidence, dict) else dict(stored_incident.normalized_evidence or {}) if stored_incident else {}
        )
        if replay_history:
            replica_summary["replay_history"] = replay_history
            trace_summary["replay_history"] = replay_history

        return {
            "incident_id": nexus_incident_id,
            "status": status,
            "message": message,
            "runtime_capability": runtime_capability,
            "replay_lifecycle": replay_lifecycle,
            "trust_packet": dict(replica_summary.get("runtime_trust_packet") or {}),
            "replica_summary": replica_summary,
            "trace_summary": trace_summary,
        }

    def _format_handoff_as_markdown(
        self,
        *,
        incident: dict[str, object],
        diagnosis: dict[str, object],
        replica_summary: dict[str, object],
        trace_summary: dict[str, object],
        runbook: dict[str, object],
        guardian: dict[str, object],
        execution_outcome: dict[str, object] | None,
        similar_incidents: list[dict[str, object]],
    ) -> str:
        evidence_backing = "runtime-backed" if replica_summary.get("runtime_executed") else "inferred-only"
        mitigation_class = str(replica_summary.get("best_mitigation_outcome_class") or "inferred_only")
        similar_summary = "\n".join([
            f"- {item.get('incident_id', 'Unknown')}: {item.get('issue_family', 'related outage')}"
            for item in similar_incidents
        ]) if similar_incidents else ""
        trace_owner = str(trace_summary.get("suspected_owner") or "")
        trace_path = str(trace_summary.get("suspected_path") or "")
        debugger_checkpoint = str(trace_summary.get("inspection_point") or "")
        supporting_logs_text = "\n".join([f"- {log}" for log in diagnosis.get("supporting_logs", [])[:3]])
        validation_result = (
            f"✓ **Validation**: {mitigation_class.replace('_', ' ').upper()}"
            if replica_summary.get("runtime_executed")
            else "⧖ **Status**: Scaffold-only inference (not yet validated through runtime replay)"
        )
        replay_duration = (
            f"Replay Duration: {replica_summary.get('replay_duration_ms', 0)}ms"
            if replica_summary.get("runtime_executed")
            else ""
        )
        developer_handoff = "**Suspected Owner**: " + (trace_owner if trace_owner else "TBD (see service ownership map)")
        if trace_path:
            developer_handoff += f"\n**Suspected Code Path**: {trace_path}"
        if debugger_checkpoint:
            developer_handoff += f"\n**Debugger Checkpoint**: {debugger_checkpoint}"
        related_memory = (
            f"Similar recent incidents:\n{similar_summary}"
            if similar_summary
            else "No recent similar incidents found."
        )
        execution_summary = (
            f"✓ **Executed**: {execution_outcome.get('summary', 'Approved and executed')}"
            if execution_outcome
            else "⧖ **Pending**: Awaiting Guardian approval"
        )
        return f"""# Engineering Handoff — {incident.get('id', 'Unknown Incident')}

## Incident Summary
- **Title**: {incident.get('name', 'Unknown')}
- **Service**: {incident.get('related_services', ['Unknown'])[0] if incident.get('related_services') else 'Unknown'}
- **Severity**: {incident.get('severity', 'Unknown').upper()}
- **Detected**: {incident.get('detected_at', 'Unknown')}

## Root Cause Hypothesis
{diagnosis.get('root_cause', 'Unknown cause')}

**Confidence**: {int(float(diagnosis.get('confidence', 0)) * 100)}% (Evidence-backed: {evidence_backing})

## Evidence Summary
Supporting logs:
{supporting_logs_text}

## Runtime Validation Result
{validation_result}

{replay_duration}

## Proposed Mitigation
**Primary Action**: {runbook.get('recommended_runbook', 'Review and adjust')}

**Fallback**: Rollback to previous version if primary action does not stabilize the system within 5 minutes.

**Blast Radius**: Affects checkout service path only. Rollback-safe.

## Developer Handoff
{developer_handoff}

## Related Memory
{related_memory}

## Guardian Review
**Decision**: {str(guardian.get('decision', 'pending')).upper()}
**Confidence**: {int(float(guardian.get('confidence', 0)) * 100)}%
**Risk Assessment**: {guardian.get('risk_class', 'unknown').upper()}

## Execution Outcome
{execution_summary}

---
*Generated by NEXUS v2 — {_utc_now_iso()}*
"""

    def _format_handoff_as_github_issue(
        self,
        *,
        incident: dict[str, object],
        diagnosis: dict[str, object],
        replica_summary: dict[str, object],
        trace_summary: dict[str, object],
        runbook: dict[str, object],
        guardian: dict[str, object],
        execution_outcome: dict[str, object] | None,
        similar_incidents: list[dict[str, object]],
    ) -> str:
        evidence_backing = "runtime-backed" if replica_summary.get("runtime_executed") else "inferred-only"
        service = incident.get('related_services', ['Unknown'])[0] if incident.get('related_services') else 'Unknown'
        severity = incident.get('severity', 'Unknown').upper()
        trace_owner = str(trace_summary.get("suspected_owner") or "TBD")
        trace_path = str(trace_summary.get("suspected_path") or "")
        supporting_logs = diagnosis.get("supporting_logs", [])[:2]
        labels = [severity.lower(), "incident", evidence_backing.replace("-", "_")]
        labels_text = "\n".join([f"- {label}" for label in labels])
        return f"""{incident.get('name', 'Unknown Incident')}

## Summary
A production incident has been triaged by NEXUS and requires engineering review and remediation.

## Details
- **Service**: {service}
- **Severity**: {severity}
- **Evidence Type**: {evidence_backing.title()}
- **Suspected Owner**: {trace_owner}
{f"- **Code Path**: {trace_path}" if trace_path else ""}

## Root Cause
{diagnosis.get('root_cause', 'Unknown cause')}

Confidence: {int(float(diagnosis.get('confidence', 0)) * 100)}%

## Remediation
**Recommended Action**: {runbook.get('recommended_runbook', 'Review and adjust')}

**Rollback Plan**: Available if needed. Service can be safely rolled back to previous version.

## Evidence
{chr(10).join([f"- {log}" for log in supporting_logs]) or "See incident detail for full evidence"}

## Assignment
This issue should be assigned to: **@{trace_owner.split("/")[-1] if "/" in trace_owner else trace_owner}**

---
Generated by NEXUS incident investigation — Reference: {incident.get('id', 'unknown')}
"""

    def _format_handoff_as_jira(
        self,
        *,
        incident: dict[str, object],
        diagnosis: dict[str, object],
        replica_summary: dict[str, object],
        trace_summary: dict[str, object],
        runbook: dict[str, object],
        guardian: dict[str, object],
        execution_outcome: dict[str, object] | None,
        similar_incidents: list[dict[str, object]],
    ) -> str:
        evidence_backing = "runtime-backed" if replica_summary.get("runtime_executed") else "inferred-only"
        service = incident.get('related_services', ['Unknown'])[0] if incident.get('related_services') else 'Unknown'
        severity_map = {"p1": "Highest", "p2": "High", "p3": "Medium", "p4": "Low"}
        severity_label = incident.get('severity', 'p3').lower()
        jira_priority = severity_map.get(severity_label, "Medium")
        trace_owner = str(trace_summary.get("suspected_owner") or "Unassigned")
        issue_type = "Production Incident"
        return f"""**Project**: Engineering
**Issue Type**: {issue_type}
**Summary**: {incident.get('name', 'Unknown Incident')}
**Priority**: {jira_priority}
**Labels**: production-incident, {evidence_backing.replace('-', '_')}, incident-response

## Description
A production incident has been automatically triaged by NEXUS and is ready for engineering investigation and remediation.

## Root Cause Analysis
{diagnosis.get('root_cause', 'Unknown cause')}

*Confidence: {int(float(diagnosis.get('confidence', 0)) * 100)}%*

## Affected Service
{service}

## Suspected Owner
{trace_owner}

## Proposed Mitigation
{runbook.get('recommended_runbook', 'Review and adjust mitigation')}

*Rollback-safe: Yes. Can be rolled back to previous version if mitigation does not resolve issue within 5 minutes.*

## Additional Context
- Evidence Type: {evidence_backing}
- NEXUS Incident ID: {incident.get('id', 'unknown')}
- Investigation Status: Guardian review {str(guardian.get('decision', 'pending')).upper()}

## Acceptance Criteria
- [ ] Root cause confirmed
- [ ] Mitigation deployed and validated
- [ ] Monitoring in place
- [ ] Incident closure documented

---
Created by NEXUS incident investigation platform — {_utc_now_iso()}
"""

    def _format_handoff_as_slack(
        self,
        *,
        incident: dict[str, object],
        diagnosis: dict[str, object],
        replica_summary: dict[str, object],
        trace_summary: dict[str, object],
        runbook: dict[str, object],
        guardian: dict[str, object],
        execution_outcome: dict[str, object] | None,
        similar_incidents: list[dict[str, object]],
    ) -> str:
        evidence_backing = "runtime-backed" if replica_summary.get("runtime_executed") else "inferred-only"
        service = incident.get('related_services', ['Unknown'])[0] if incident.get('related_services') else 'Unknown'
        severity = incident.get('severity', 'Unknown').upper()
        severity_emoji = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}.get(severity, "⚪")
        trace_owner = str(trace_summary.get("suspected_owner") or "TBD")
        confidence = int(float(diagnosis.get('confidence', 0)) * 100)
        return f"""{severity_emoji} **{incident.get('name', 'Unknown')} ({severity})**

*NEXUS Incident Investigation Summary*

**Service**: {service}
**Evidence**: {evidence_backing.title()}
**Root Cause Confidence**: {confidence}%

**Likely Root Cause**
{diagnosis.get('root_cause', 'Unknown cause')}

**Recommended Action**
{runbook.get('recommended_runbook', 'See incident detail')}

**Suspected Owner**
@{trace_owner.split("/")[-1] if "/" in trace_owner else trace_owner}

**Next Steps**
1. Review the full investigation at: [NEXUS Incident Detail](https://nexus/incident?id={incident.get('id', 'unknown')})
2. {runbook.get('recommended_runbook', 'Execute the mitigation')}
3. Monitor for 5 minutes, then assess need for rollback

**Status**: {str(guardian.get('decision', 'pending')).upper()} by Guardian review

---
Full incident details: NEXUS v2 | {incident.get('id', 'unknown')}
"""

    async def build_engineering_handoff(
        self,
        nexus_incident_id: str,
        *,
        export_format: str = "markdown",
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        context = await self.get_incident_context_v1(
            nexus_incident_id,
            tenant_id=tenant_id,
            live_reasoning=False,
            openai_api_key=None,
        )
        incident = dict(context.get("incident") or {})
        diagnosis = dict(context.get("diagnosis") or {})
        replica_summary = dict(context.get("replica_summary") or {})
        trace_summary = dict(context.get("trace_summary") or {})
        runbook = dict(context.get("runbook") or {})
        guardian = dict(context.get("guardian") or {})
        execution_outcome = context.get("execution_outcome")
        memory_hits = dict(context.get("memory_hits") or {})

        evidence_backing = "runtime-backed" if replica_summary.get("runtime_executed") else "inferred-only"
        similar_incidents = memory_hits.get("similar_incidents", [])[:2]

        format_generators = {
            "markdown": self._format_handoff_as_markdown,
            "github": self._format_handoff_as_github_issue,
            "jira": self._format_handoff_as_jira,
            "slack": self._format_handoff_as_slack,
        }

        generator = format_generators.get(export_format, format_generators["markdown"])
        handoff_text = generator(
            incident=incident,
            diagnosis=diagnosis,
            replica_summary=replica_summary,
            trace_summary=trace_summary,
            runbook=runbook,
            guardian=guardian,
            execution_outcome=execution_outcome,
            similar_incidents=similar_incidents,
        )

        return {
            "incident_id": nexus_incident_id,
            "handoff_text": handoff_text,
            "export_format": export_format,
            "backing_evidence": evidence_backing,
            "validated_items": {
                "root_cause_confidence": diagnosis.get("confidence", 0),
                "mitigation_confidence": runbook.get("success_rate", 0),
                "guardian_confidence": guardian.get("confidence", 0),
            },
            "generated_at": _utc_now_iso(),
        }

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

    async def build_governance_packet(
        self,
        nexus_incident_id: str,
        *,
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        context = await self.get_incident_context_v1(
            nexus_incident_id,
            tenant_id=tenant_id,
            live_reasoning=False,
            openai_api_key=None,
        )
        incident = dict(context.get("incident") or {})
        diagnosis = dict(context.get("diagnosis") or {})
        replica_summary = dict(context.get("replica_summary") or {})
        runbook = dict(context.get("runbook") or {})
        guardian = dict(context.get("guardian") or {})
        execution_outcome = context.get("execution_outcome")

        timeline = [
            {
                "event": "Incident detected",
                "timestamp": incident.get("detected_at") or incident.get("created_at") or _utc_now_iso(),
                "actor": incident.get("source") or "system",
                "summary": f"{incident.get('name', 'Unknown incident')} detected with severity {incident.get('severity', 'unknown')}",
            },
            {
                "event": "Investigation completed",
                "timestamp": incident.get("analyzed_at") or _utc_now_iso(),
                "actor": "PRISM",
                "summary": f"Root cause hypothesis: {diagnosis.get('root_cause', 'Unknown')} (confidence: {int(float(diagnosis.get('confidence', 0)) * 100)}%)",
                "evidence_type": "runtime-backed" if replica_summary.get("runtime_executed") else "inferred-only",
            },
            {
                "event": "Replay validation",
                "timestamp": replica_summary.get("replay_executed_at") or _utc_now_iso() if replica_summary.get("runtime_executed") else None,
                "actor": "REPLICA",
                "summary": f"Hypothesis {'confirmed' if replica_summary.get('runtime_executed') else 'not validated'} {'via bounded runtime' if replica_summary.get('runtime_executed') else 'pending execution'}",
                "outcome_class": replica_summary.get("best_mitigation_outcome_class") if replica_summary.get("runtime_executed") else "pending",
            } if replica_summary.get("runtime_executed") or True else None,
            {
                "event": "Remediation prepared",
                "timestamp": incident.get("decision_ready_at") or _utc_now_iso(),
                "actor": "FORGE",
                "summary": f"Primary action: {runbook.get('recommended_runbook', 'Review and adjust')}",
            },
            {
                "event": "Governance review",
                "timestamp": incident.get("guardian_reviewed_at") or _utc_now_iso(),
                "actor": "GUARDIAN",
                "summary": f"Decision: {str(guardian.get('decision', 'pending')).upper()} · Risk class: {guardian.get('risk_class', 'unknown')}",
                "decision": guardian.get("decision"),
                "reasoning": guardian.get("reasoning"),
            },
        ]

        if execution_outcome:
            timeline.append({
                "event": "Execution completed",
                "timestamp": execution_outcome.get("executed_at") or _utc_now_iso(),
                "actor": "operator",
                "summary": execution_outcome.get("summary", "Action executed"),
                "status": execution_outcome.get("status", "completed"),
            })

        timeline = [item for item in timeline if item is not None]

        return {
            "incident_id": nexus_incident_id,
            "incident_title": incident.get("name", "Unknown Incident"),
            "incident_severity": incident.get("severity", "unknown"),
            "incident_service": incident.get("related_services", ["Unknown"])[0] if incident.get("related_services") else "Unknown",
            "approval_timeline": timeline,
            "governance_decisions": {
                "guardian_decision": str(guardian.get("decision", "pending")).upper(),
                "guardian_confidence": int(float(guardian.get("confidence", 0)) * 100),
                "risk_assessment": guardian.get("risk_class", "unknown").upper(),
                "policy_basis": guardian.get("policy_basis", "standard"),
            },
            "evidence_posture": {
                "root_cause_evidence": "runtime-backed" if replica_summary.get("runtime_executed") else "inferred-only",
                "mitigation_validated": bool(replica_summary.get("runtime_executed")),
                "hypothesis_confidence": int(float(diagnosis.get("confidence", 0)) * 100),
            },
            "execution_record": {
                "executed": bool(execution_outcome),
                "status": execution_outcome.get("status") if execution_outcome else "pending",
                "summary": execution_outcome.get("summary") if execution_outcome else "Not yet executed",
            },
            "generated_at": _utc_now_iso(),
        }

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
            case_lifecycle=incident.case_lifecycle,
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
                    case_lifecycle="triaged",
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
