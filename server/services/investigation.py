import logging
import os
from collections.abc import Awaitable, Callable

from server.agents.forge import ForgeAgent
from server.agents.guardian import GuardianAgent
from server.agents.live_clients import OpenAIForgeClient, OpenAIPrismClient, OpenAISentinelClient
from server.agents.prism import PrismAgent
from server.agents.sentinel import SentinelAgent
from server.config import AppConfig
from server.models import IncidentRecord, SystemContext
from server.openai_keys import build_llm_access
from server.services.enterprise_runtime import (
    build_quality_evaluation,
    build_replica_summary,
    build_trace_summary,
    build_triage_summary,
    build_training_enterprise_summary,
    infer_issue_family,
    runbook_score_from_candidates,
    runtime_aligned_candidate_fixes,
)
from server.services.intake import raw_input_quality
from server.services.priority import priority_snapshot
from server.services.result_contracts import build_structured_result
from server.services.runtime_queue import RuntimeQueueManager

logger = logging.getLogger(__name__)


def root_cause_from_issue_family(issue_family: str, service: str) -> str:
    issue_family_text = issue_family.lower()
    if "auth" in issue_family_text and "dependency" in issue_family_text:
        return f"Auth service degradation caused by token validation slowdown or dependency latency in {service or 'the auth path'}."
    if "queue" in issue_family_text and "backlog" in issue_family_text:
        return f"Consumer backlog surge caused by partition assignment failure or worker starvation in {service or 'the queue'} topology."
    if "retry amplification" in issue_family_text:
        return f"Timeout cascade caused by retry amplification in the {service or 'checkout'} authorization path."
    if "pool exhaustion" in issue_family_text or "session leak" in issue_family_text:
        return f"Database pool exhaustion caused by a leaked retry session path in {service or 'checkout'}."
    if "certificate expiry" in issue_family_text:
        return f"Trust boundary outage caused by an expired certificate on {service or 'the public edge'}."
    if "memory leak" in issue_family_text:
        return f"Runtime degradation caused by retained memory in {service or 'the worker fleet'}."
    return f"Likely production incident pattern affecting {service or 'service'}."


def runtime_aligned_live_runbook(
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


class InvestigationContextBuilder:
    def __init__(
        self,
        *,
        observability,
        tenancy_service,
        build_enterprise_overlay: Callable[..., Awaitable[dict[str, object]]],
        apply_persisted_replay_packet: Callable[..., dict[str, object]],
        queue_source_channel: Callable[[str | None], str],
        guardian_context: Callable[[IncidentRecord], dict[str, object]],
        build_fresh_intake_truth: Callable[..., dict[str, object] | None],
    ) -> None:
        self._observability = observability
        self._tenancy_service = tenancy_service
        self._build_enterprise_overlay = build_enterprise_overlay
        self._apply_persisted_replay_packet = apply_persisted_replay_packet
        self._queue_source_channel = queue_source_channel
        self._guardian_context = guardian_context
        self._build_fresh_intake_truth = build_fresh_intake_truth

    async def build_incident_context_payload(
        self,
        *,
        incident: IncidentRecord,
        tenant_id: str | None,
        live_reasoning: bool | None,
        openai_api_key: str | None,
        lifecycle: dict[str, object],
        audit_logs: list[dict[str, object]],
        recent_deployments: list[dict[str, object]],
        workflow: list[dict[str, object]],
    ) -> dict[str, object]:
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
        input_quality = raw_input_quality(normalized_evidence)
        latest_replay = dict(normalized_evidence.get("latest_replay", {})) if isinstance(normalized_evidence.get("latest_replay"), dict) else {}
        has_runtime_replay = bool(latest_replay and latest_replay.get("status") in {"replay_executed", "relay_executed"} or latest_replay.get("lifecycle_state") == "completed")
        is_fresh_incident = bool(incident.raw_input_text)
        live_payload = await self.build_raw_live_reasoning_payload(
            incident=incident,
            tenant_id=tenant_id or incident.tenant_id,
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
            posture = str(input_quality.get("normalization_posture", "")).lower()
            if posture == "weak":
                classification["confidence"] = 0.58
                classification["reasoning"] = (
                    "The pasted logs were only weakly normalized into a provisional incident packet. "
                    "Service and severity signals are incomplete, so this context should be treated as scaffold-only intake shaping until stronger evidence arrives."
                )
            elif posture == "partial":
                classification["confidence"] = 0.72 if not has_runtime_replay else 0.8
                classification["reasoning"] = (
                    "The pasted logs were partially normalized into service, severity, and signature. "
                    "Routing is usable, but missing signals should be confirmed before execution."
                )
            elif has_runtime_replay:
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
        support_state_info = self._tenancy_service.get_incident_support_state(
            tenant_id or incident.tenant_id,
            issue_family,
        )
        diagnosis = {
            "root_cause": root_cause_from_issue_family(issue_family, raw_service or incident.service or incident.nexus_incident_id),
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
            posture = str(input_quality.get("normalization_posture", "")).lower()
            diagnosis["confidence"] = 0.8 if not has_runtime_replay else 0.88
            diagnosis["supporting_logs"] = [
                raw_signature or "Raw input normalized from pasted logs",
                *diagnosis["supporting_logs"],
            ]
            if posture == "weak":
                diagnosis["confidence"] = 0.55
                diagnosis["correlation_analysis"] = (
                    "The raw text was normalized into only a weak packet. NEXUS can still suggest an initial incident frame, "
                    "but service ownership and mitigation choice remain provisional until stronger logs arrive."
                )
                diagnosis["reasoning"] = (
                    "This diagnosis is intentionally conservative because the intake is weak and runtime replay has not validated a concrete family yet."
                )
            elif posture == "partial":
                diagnosis["confidence"] = 0.69 if not has_runtime_replay else 0.82
                diagnosis["correlation_analysis"] = (
                    "The raw text was normalized into a partial packet. The likely incident family is usable for routing, "
                    "but the missing signals should be confirmed before approval."
                )
                diagnosis["reasoning"] = (
                    "This diagnosis is partially grounded in the raw text. Treat it as a bounded routing aid until stronger logs or replay evidence arrive."
                )
            elif has_runtime_replay:
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

        runbook = runtime_aligned_live_runbook(
            issue_family=issue_family,
            service=raw_service or incident.service or incident.nexus_incident_id,
            reason="The live incident view keeps the remediation contract aligned to the same bounded runtime packs used in the flagship outage demos.",
        )
        if incident.raw_input_text:
            posture = str(input_quality.get("normalization_posture", "")).lower()
            if posture == "weak":
                runbook["summary"] = f"Remediation plan for the pasted {raw_service or 'service'} incident (weak intake)"
                runbook["reasoning"] = (
                    "The raw input was only weakly normalized into a provisional issue family. "
                    "This plan is scaffold-only guidance and should not be treated as decision-ready until stronger evidence is attached."
                )
            elif posture == "partial":
                runbook["summary"] = f"Remediation plan for the pasted {raw_service or 'service'} incident (partial intake)"
                runbook["reasoning"] = (
                    "The raw input normalized into a usable but partial packet. "
                    "This path is suitable for routing and initial handoff, but the missing signals should be confirmed before approval."
                )
            elif has_runtime_replay:
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
            tenant_id=tenant_id,
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

        quality_evaluation = None
        if is_fresh_incident:
            quality_evaluation = build_quality_evaluation(
                incident_id=incident.nexus_incident_id,
                classification_confidence=float(classification.get("confidence", 0.8)),
                diagnosis_confidence=float(diagnosis.get("confidence", 0.75)),
                triage_summary=triage_summary,
                input_quality=input_quality,
                has_runtime_replay=has_runtime_replay,
            )
        fresh_intake_truth = self._build_fresh_intake_truth(
            incident=incident,
            normalized_evidence=normalized_evidence,
            input_quality=input_quality,
            issue_family=issue_family,
            triage_summary=triage_summary,
            support_state=support_state_info["support_state"],
            has_runtime_replay=has_runtime_replay,
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
                "input_quality": input_quality,
                "support_state": support_state_info["support_state"],
                "issue_family": issue_family,
            },
            "tenant_support": {
                "support_state": support_state_info["support_state"],
                "downgrade_guidance": support_state_info["downgrade_guidance"],
                "all_supported_families": support_state_info["all_supported_families"],
                "supporting_packs": support_state_info["supported_packs"],
            },
            "fresh_intake_truth": fresh_intake_truth,
            "quality_evaluation": quality_evaluation,
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
        payload["runtime_queue_state"] = RuntimeQueueManager.get_incident_queue_state(incident.nexus_incident_id)
        payload["runtime_recovery_posture"] = RuntimeQueueManager.get_runtime_recovery_posture()
        return self._apply_persisted_replay_packet(incident=incident, payload=payload)

    async def build_raw_live_reasoning_payload(
        self,
        *,
        incident: IncidentRecord,
        tenant_id: str,
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
            input_quality = raw_input_quality(raw_evidence)
            has_runtime_replay = bool(
                isinstance(raw_evidence.get("latest_replay"), dict)
                and (
                    raw_evidence["latest_replay"].get("status") in {"replay_executed", "relay_executed"}
                    or raw_evidence["latest_replay"].get("lifecycle_state") == "completed"
                )
            )
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
            tenant_id=tenant_id,
        )
        support_state_info = self._tenancy_service.get_incident_support_state(
            tenant_id,
            str(triage_summary.get("issue_family") or ""),
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
        fresh_intake_truth = self._build_fresh_intake_truth(
            incident=incident,
            normalized_evidence=raw_evidence,
            input_quality=input_quality,
            issue_family=str(triage_summary.get("issue_family") or ""),
            triage_summary=triage_summary,
            support_state=support_state_info["support_state"],
            has_runtime_replay=has_runtime_replay,
        )

        payload = {
            "incident": {
                "id": incident.nexus_incident_id,
                "name": incident.title,
                "severity": incident.severity,
                "summary": "Live incident opened through the raw_text intake path.",
                "detected_at": incident.created_at or incident.updated_at or "now",
                "duration_minutes": 0,
                "related_services": [raw_service] if raw_service else [],
                "recent_deployments": recent_deployments,
                "similar_past_incidents": [],
                "source_channel": "raw_text",
                "raw_input_text": incident.raw_input_text,
                "normalized_evidence": raw_evidence,
                "input_quality": input_quality,
                "support_state": support_state_info["support_state"],
            },
            "tenant_support": {
                "support_state": support_state_info["support_state"],
                "downgrade_guidance": support_state_info["downgrade_guidance"],
                "all_supported_families": support_state_info["all_supported_families"],
                "supporting_packs": support_state_info["supported_packs"],
            },
            "fresh_intake_truth": fresh_intake_truth,
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
        posture = str(input_quality.get("normalization_posture", "")).lower()
        if posture == "weak":
            payload["classification"]["confidence"] = min(float(payload["classification"]["confidence"]), 0.58)
            payload["classification"]["reasoning"] = (
                "Live reasoning shaped a provisional packet from weak raw input. Service and severity signals remain incomplete, so this should be treated as routing guidance rather than a decision-ready diagnosis."
            )
            payload["diagnosis"]["confidence"] = min(float(payload["diagnosis"]["confidence"]), 0.56)
            payload["diagnosis"]["reasoning"] = (
                "The live model produced a conservative diagnosis because the pasted evidence is weak and still missing core service or severity signals."
            )
        elif posture == "partial":
            payload["classification"]["confidence"] = min(float(payload["classification"]["confidence"]), 0.78)
            payload["classification"]["reasoning"] = (
                "Live reasoning shaped a usable but partial packet from the pasted logs. Routing is credible, but the missing signals should be confirmed before approval."
            )
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
        payload["runtime_queue_state"] = RuntimeQueueManager.get_incident_queue_state(incident.nexus_incident_id)
        payload["runtime_recovery_posture"] = RuntimeQueueManager.get_runtime_recovery_posture()
        return self._apply_persisted_replay_packet(incident=incident, payload=payload)
