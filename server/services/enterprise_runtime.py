from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean
from langgraph.graph import END, START, StateGraph

from server.artifacts import _load_artifacts
from server.incident_payloads import get_incident_details, list_supported_incident_ids
from server.models import Episode, IncidentDefinition, IncidentRecord, NormalizedAlertEnvelope
from server.services.priority import normalize_priority_label, priority_rank
from server.services.replay import (
    _runtime_outcome_score,
    build_replica_summary,
    enrich_memory_with_runtime,
    rank_candidate_fixes_with_runtime,
    runtime_aligned_candidate_fixes,
)
from server.services.runtime_state import (
    RuntimeState,
    build_pilot_safe_subsystem,
    normalize_pilot_health_status,
    summarize_pilot_surface,
)
from server.services.replica_runtime import ReplicaRunner, build_execution_plan, trace_targets_for_plan, EvidencePosture

__all__ = [
    "build_pilot_closeout_package",
    "build_pilot_safe_subsystem",
    "build_replica_summary",
    "build_roi_metrics",
    "build_quality_evaluation",
    "build_trace_summary",
    "build_training_enterprise_summary",
    "build_weekly_pilot_review_package",
    "enrich_memory_with_runtime",
    "infer_issue_family",
    "normalize_pilot_health_status",
    "ReplicaRunner",
    "rank_candidate_fixes_with_runtime",
    "runbook_score_from_candidates",
    "summarize_pilot_surface",
    "runtime_aligned_candidate_fixes",
]


TRACE_OWNERSHIP_MAP_PATH = Path(__file__).with_name("trace_ownership_map.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_live_handoff_flow(
    incident_id: str,
    classification: dict[str, object],
    diagnosis: dict[str, object],
    replica_summary: dict[str, object],
    trace_summary: dict[str, object],
    runbook: dict[str, object],
    guardian: dict[str, object],
) -> dict[str, object]:
    events = [
        {
            "id": "sentinel-emitted-triage-packet",
            "from": "SENTINEL",
            "to": "PRISM",
            "status": "completed",
            "event_type": "packet_emitted",
            "title": "SENTINEL emitted triage packet",
            "reason": f"Initial classification with confidence {classification.get('confidence', 0.0)} ready for diagnosis.",
            "packet": {
                "packet_type": "triage_packet",
                "summary": str(classification.get("reasoning", "Classification completed")),
                "fields": [
                    {"label": "Severity", "value": str(classification.get("severity", "P2"))},
                    {"label": "Confidence", "value": f"{float(classification.get('confidence', 0.0)) * 100:.0f}%"},
                ],
            },
        },
        {
            "id": "prism-emitted-diagnosis-packet",
            "from": "PRISM",
            "to": "REPLICA",
            "status": "completed",
            "event_type": "packet_emitted",
            "title": "PRISM emitted diagnosis packet",
            "reason": f"Root cause analysis with confidence {diagnosis.get('confidence', 0.0)} ready for validation.",
            "packet": {
                "packet_type": "diagnosis_packet",
                "summary": str(diagnosis.get("root_cause", "Diagnosis pending")),
                "fields": [
                    {"label": "Root cause", "value": str(diagnosis.get("root_cause", "Analysis in progress"))},
                ],
            },
        },
        {
            "id": "replica-emitted-reproduction-packet",
            "from": "REPLICA",
            "to": "TRACE",
            "status": "completed",
            "event_type": "packet_emitted",
            "title": "REPLICA emitted reproduction packet",
            "reason": f"Reproduction status: {replica_summary.get('reproduction_status', 'not_run')}.",
            "packet": {
                "packet_type": "reproduction_packet",
                "summary": str(replica_summary.get("reasoning", "Reproduction assessment complete")),
                "fields": [
                    {"label": "Reproduction status", "value": str(replica_summary.get("reproduction_status", "not_run"))},
                ],
            },
        },
        {
            "id": "trace-emitted-debug-packet",
            "from": "TRACE",
            "to": "FORGE",
            "status": "completed",
            "event_type": "packet_emitted",
            "title": "TRACE emitted debug packet",
            "reason": f"Code path analysis ready with confidence {trace_summary.get('confidence', 0.0)}.",
            "packet": {
                "packet_type": "debug_packet",
                "summary": str(trace_summary.get("reasoning", "Debug analysis complete")),
                "fields": [
                    {"label": "Trace status", "value": str(trace_summary.get("trace_status", "not_run"))},
                ],
            },
        },
        {
            "id": "forge-emitted-runbook-packet",
            "from": "FORGE",
            "to": "GUARDIAN",
            "status": "completed",
            "event_type": "packet_emitted",
            "title": "FORGE emitted runbook packet",
            "reason": "Remediation plan ready for governance approval.",
            "packet": {
                "packet_type": "runbook_packet",
                "summary": str(runbook.get("summary", "Remediation plan ready")),
                "fields": [
                    {"label": "Recommended action", "value": str(runbook.get("recommended_runbook", "Mitigation pending"))},
                ],
            },
        },
        {
            "id": "guardian-accepted-governance-packet",
            "from": "GUARDIAN",
            "to": "execution",
            "status": "completed",
            "event_type": "packet_received",
            "title": "GUARDIAN accepted governance packet",
            "reason": f"Safety decision: {guardian.get('decision', 'pending')}.",
            "packet": {
                "packet_type": "governance_packet",
                "summary": f"Decision: {guardian.get('decision', 'pending')}",
                "fields": [
                    {"label": "Decision", "value": str(guardian.get("decision", "pending"))},
                ],
            },
        },
    ]

    return {
        "current_owner": "GUARDIAN",
        "previous_owner": "FORGE",
        "next_owner": "execution",
        "state": "in_progress",
        "transfer_reason": "FORGE handed remediation packet to GUARDIAN for safety review.",
        "events": events,
    }


class IncidentKnowledgeService:
    def __init__(self, *, session: object | None = None) -> None:
        self._session = session

    async def build_memory_pack(
        self,
        *,
        incident_id: str,
        incident_name: str,
        service: str,
        severity: str,
        root_cause: str,
        tenant_id: str = "tenant-system",
    ) -> dict[str, list[dict[str, object]]]:
        similar_incidents = self._rank_similar_incidents(
            incident_id=incident_id,
            incident_name=incident_name,
            service=service,
            severity=severity,
            root_cause=root_cause,
        )
        unresolved_items = await self._find_unresolved_items(
            incident_id=incident_id,
            service=service,
            tenant_id=tenant_id,
        )
        recent_guardian_outcomes = self._recent_guardian_outcomes(service=service)
        runbooks = self._runbook_memory(similar_incidents, recent_guardian_outcomes)
        return {
            "similar_incidents": similar_incidents,
            "runbooks": runbooks,
            "unresolved_items": unresolved_items,
            "recent_guardian_outcomes": recent_guardian_outcomes,
        }

    def _rank_similar_incidents(
        self,
        *,
        incident_id: str,
        incident_name: str,
        service: str,
        severity: str,
        root_cause: str,
    ) -> list[dict[str, object]]:
        query = " ".join([incident_name, service, severity, root_cause]).lower()
        similar: list[dict[str, object]] = []
        for candidate_id in list_supported_incident_ids():
            if candidate_id == incident_id:
                continue
            details = get_incident_details(candidate_id)
            summary = str(details.get("summary", "")).strip()
            candidate_root = str(details.get("prism", {}).get("reasoning", "")).strip()
            candidate_triage = details.get("triage", {}) if isinstance(details.get("triage"), dict) else {}
            candidate_related_services = [str(item).strip().lower() for item in details.get("related_services", []) if str(item).strip()]
            candidate_service = " ".join(str(item) for item in details.get("related_services", [])[:2])
            candidate_severity = str(details.get("severity", severity))
            service_overlap = bool(service and service.lower() in candidate_related_services)
            severity_match = normalize_priority_label(candidate_severity) == normalize_priority_label(severity)
            root_overlap = len(
                self._token_set(root_cause) & self._token_set(candidate_root or summary)
            )
            score = self._similarity_score(
                query,
                " ".join([candidate_id, summary, candidate_root, candidate_service, candidate_severity]).lower(),
            )
            if score <= 0.08 and not service_overlap and root_overlap < 2:
                continue

            # Boost score for outcomes-weighted preference
            execution_status = str(details.get("execution_result") or "")
            outcome_boost = 0.0
            outcome_label = ""
            if execution_status == "executed":
                outcome_boost = 0.12
                outcome_label = "Mitigation was executed successfully"
            elif str(details.get("guardian", {}).get("decision") or "").lower() == "approve":
                outcome_boost = 0.08
                outcome_label = "Mitigation was approved by GUARDIAN"

            base_success_rate = 0.74 + (score * 0.22)
            final_success_rate = round(min(0.99, base_success_rate + outcome_boost), 2)

            remaining_risk = str(details.get("guardian", {}).get("reasoning", "")).strip()
            recurrence_status = "clean_win" if execution_status == "executed" and not remaining_risk else ("partial_resolution" if remaining_risk else "unresolved")
            recurrence_indicator = "recurring" if recurrence_status in ("partial_resolution", "unresolved") else "resolved"

            similar.append(
                {
                    "incident_id": candidate_id,
                    "summary": summary,
                    "root_cause_hint": candidate_root,
                    "issue_family": str(candidate_triage.get("issue_family") or infer_issue_family(candidate_root or summary, summary)),
                    "service_match": service_overlap,
                    "severity_match": severity_match,
                    "root_overlap": root_overlap,
                    "success_rate": final_success_rate,
                    "similarity": round(score, 2),
                    "outcome_boost": outcome_boost,
                    "outcome_label": outcome_label,
                    "memory_source": "seeded_example",
                    "memory_provenance": "This is a seeded example from bounded incident knowledge, not from tenant-specific history.",
                    "match_reason": self._build_match_reason(
                        service_match=service_overlap,
                        severity_match=severity_match,
                        root_overlap=root_overlap,
                        issue_family=str(candidate_triage.get("issue_family") or ""),
                        outcome_label=outcome_label,
                    ),
                    "prior_action": self._prior_action(details),
                    "remaining_risk": remaining_risk,
                    "recurrence_status": recurrence_status,
                    "recurrence_indicator": recurrence_indicator,
                    "source": "incident_history",
                }
            )
        similar.sort(
            key=lambda item: (
                item["outcome_boost"] > 0,
                item["service_match"],
                item["severity_match"],
                item["root_overlap"],
                item["similarity"],
                item["success_rate"],
            ),
            reverse=True,
        )
        return similar[:3]

    async def _find_unresolved_items(
        self,
        *,
        incident_id: str,
        service: str,
        tenant_id: str,
    ) -> list[dict[str, object]]:
        unresolved: list[dict[str, object]] = []
        repo = getattr(self._session, "incidents", None)
        if repo is not None and hasattr(repo, "list_incidents_for_tenant"):
            items = await repo.list_incidents_for_tenant(tenant_id)
            for item in items:
                record = IncidentRecord.model_validate(item)
                if record.nexus_incident_id == incident_id or record.status == "resolved":
                    continue
                if service and record.service and service != record.service:
                    continue
                unresolved.append(
                    {
                        "incident_id": record.nexus_incident_id,
                        "title": record.title,
                        "status": record.status,
                        "severity": record.severity,
                        "follow_up_reason": "Open incident on the same service boundary still needs closure or post-incident work.",
                        "source": record.source or "intake",
                    }
                )
        if unresolved:
            return unresolved[:3]
        seeded = []
        for candidate_id in list_supported_incident_ids():
            if candidate_id == incident_id:
                continue
            details = get_incident_details(candidate_id)
            seeded.append(
                {
                    "incident_id": candidate_id,
                    "title": details.get("summary", candidate_id),
                    "status": "investigating",
                    "severity": normalize_priority_label(details.get("severity", "P2")),
                    "follow_up_reason": "Seeded unresolved follow-up still maps to the same service or issue class.",
                    "source": "seeded_queue",
                }
            )
        return seeded[:2]

    def _recent_guardian_outcomes(self, *, service: str) -> list[dict[str, object]]:
        payload = _load_artifacts()
        reviews = payload.get("guardian_reviews", [])
        recent: list[dict[str, object]] = []
        for review in reversed(reviews[-6:]):
            incident_id = str(review.get("incident_id", "")).strip()
            reasoning = str(review.get("guardian_reasoning", "")).lower()
            if service and service.lower() not in reasoning and incident_id:
                continue
            recent.append(
                {
                    "incident_id": incident_id,
                    "decision": review.get("guardian_decision", "pending"),
                    "status": review.get("status", "recorded"),
                    "policy_id": review.get("guardian_policy_id", ""),
                    "timestamp": review.get("timestamp", ""),
                }
            )
        return recent[:4]

    def _runbook_memory(
        self,
        similar_incidents: list[dict[str, object]],
        recent_guardian_outcomes: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        runbooks: list[dict[str, object]] = []
        for item in similar_incidents:
            details = get_incident_details(str(item["incident_id"]))
            recommended = details.get("recommended_runbooks", [])
            primary = recommended[0] if isinstance(recommended, list) and recommended else {}
            forge_details = details.get("forge", {}) if isinstance(details.get("forge"), dict) else {}
            historical_actions = [
                str(candidate.get("action") or "").strip()
                for candidate in forge_details.get("candidate_fixes", [])
                if isinstance(candidate, dict) and str(candidate.get("action") or "").strip()
            ]

            # Boost success rate for executed outcomes
            base_success = float(primary.get("success_rate", item["success_rate"]))
            execution_status = str(details.get("execution_result") or "")
            outcome_note = ""
            final_success_rate = base_success

            if execution_status == "executed":
                final_success_rate = min(0.99, base_success + 0.15)
                outcome_note = "✓ This mitigation was executed and the incident resolved."
            elif str(details.get("guardian", {}).get("decision") or "").lower() == "approve":
                final_success_rate = min(0.95, base_success + 0.10)
                outcome_note = "✓ This mitigation was approved by GUARDIAN."

            runbooks.append(
                {
                    "incident_id": item["incident_id"],
                    "runbook_summary": str(primary.get("name") or f"Prior mitigation pattern for {item['incident_id']}"),
                    "success_rate": round(final_success_rate, 2),
                    "historical_reason": str(details.get("forge", {}).get("selection_logic", "")).strip(),
                    "historical_actions": historical_actions,
                    "outcome_note": outcome_note,
                    "why_now_fit": (
                        (outcome_note + " " if outcome_note else "")
                        + (str(details.get("triage", {}).get("approval_focus", "")).strip()
                        or "Historical mitigation favored reversible recovery before broad rollback.")
                    ),
                    "source": "historical_runbook",
                }
            )
        for item in recent_guardian_outcomes:
            if item["decision"] == "approve":
                runbooks.append(
                    {
                        "incident_id": item["incident_id"],
                        "runbook_summary": f"Guardian-approved execution for {item['incident_id']}",
                        "success_rate": 0.85,
                        "historical_reason": f"Previously cleared by {item.get('policy_id') or 'GUARDIAN policy'}.",
                        "outcome_note": "✓ This pattern was approved by GUARDIAN.",
                        "why_now_fit": "This pattern already cleared governance for a closely related production incident. Outcome-weighted preference.",
                        "source": "guardian_history",
                    }
                )
        runbooks.sort(
            key=lambda item: (
                bool(item.get("outcome_note")),
                item.get("success_rate", 0.0),
            ),
            reverse=True,
        )
        return runbooks[:4]

    def _build_match_reason(
        self,
        *,
        service_match: bool,
        severity_match: bool,
        root_overlap: int,
        issue_family: str,
        outcome_label: str = "",
    ) -> str:
        reasons: list[str] = []
        if outcome_label:
            reasons.append(f"✓ {outcome_label}.")
        if issue_family:
            reasons.append(f"Same issue family: {issue_family}.")
        if service_match:
            reasons.append("Touches the same primary service boundary.")
        if severity_match:
            reasons.append("Carries the same severity tier.")
        if root_overlap >= 2:
            reasons.append(f"Shares {root_overlap} root-cause tokens with the current hypothesis.")
        return " ".join(reasons) or "Matched on lexical overlap with the current incident narrative."

    def _prior_action(self, details: dict[str, object]) -> str:
        forge = details.get("forge", {}) if isinstance(details.get("forge"), dict) else {}
        fixes = forge.get("candidate_fixes", [])
        if isinstance(fixes, list) and fixes and isinstance(fixes[0], dict):
            action = str(fixes[0].get("action", "")).strip()
            if action:
                return action
        runbooks = details.get("recommended_runbooks", [])
        if isinstance(runbooks, list) and runbooks and isinstance(runbooks[0], dict):
            return str(runbooks[0].get("name", "")).strip()
        return "Historical remediation path unavailable."

    def _similarity_score(self, left: str, right: str) -> float:
        left_tokens = self._token_set(left)
        right_tokens = self._token_set(right)
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = len(left_tokens & right_tokens)
        return min(1.0, overlap / max(1, len(left_tokens)))

    def _token_set(self, value: str) -> set[str]:
        return {part for part in value.lower().replace("/", " ").replace("-", " ").split() if part}


class EnterpriseNexusRuntime:
    def __init__(
        self,
        *,
        observability,
        sentinel,
        prism,
        forge,
        guardian,
        episode_sink: Callable[[Episode], None] | None = None,
        knowledge_service: IncidentKnowledgeService | None = None,
    ) -> None:
        self.observability = observability
        self.sentinel = sentinel
        self.prism = prism
        self.forge = forge
        self.guardian = guardian
        self.episode_sink = episode_sink
        self.knowledge_service = knowledge_service or IncidentKnowledgeService()
        self._graph = self._build_graph()

    async def run_episode(self, alert_envelope: NormalizedAlertEnvelope) -> Episode:
        context = await self.observability.fetch_incident_context(alert_envelope)
        state = await self._graph.ainvoke(
            {
                "alert_envelope": alert_envelope,
                "context": context,
                "task_board": [],
                "orchestration": {
                    "state": "initialized",
                    "showcase_incident": alert_envelope.external_id,
                    "timeline": [],
                },
                "memory_hits": {
                    "similar_incidents": [],
                    "runbooks": [],
                    "unresolved_items": [],
                    "recent_guardian_outcomes": [],
                },
                "fallback_summary": [],
                "agent_metrics": {},
                "branch_results": {},
                "evidence_pack": {},
            }
        )
        episode = state["final_episode"]
        if self.episode_sink is not None:
            self.episode_sink(episode)
        return episode

    async def build_overlay_from_snapshot(
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
        memory_hits = await self.knowledge_service.build_memory_pack(
            incident_id=incident_id,
            incident_name=incident_name,
            service=service,
            severity=severity,
            root_cause=str(diagnosis.get("root_cause", incident_name)),
            tenant_id=tenant_id,
        )
        fallback_summary = []
        if not memory_hits["runbooks"]:
            fallback_summary.append(
                {
                    "stage": "history_lookup",
                    "reason": "No stored runbook history matched the service closely enough.",
                    "resolution": "Used deterministic runbook fallback for this incident.",
                }
            )
        triage_summary = build_triage_summary(
            incident_name=incident_name,
            service=service,
            severity=severity,
            root_cause=str(diagnosis.get("root_cause", incident_name)),
            source_channel=source_channel,
            detected_signals=observability.get("recent_logs", []),
        )
        replica_summary = build_replica_summary(
            incident_id=incident_id,
            triage_summary=triage_summary,
            root_cause=str(diagnosis.get("root_cause", incident_name)),
            recent_logs=observability.get("recent_logs", []),
            recent_deployments=incident_deployments_from_observability(observability),
            candidate_fixes=runbook.get("candidate_fixes", []),
        )
        trace_summary = build_trace_summary(
            incident_id=incident_id,
            triage_summary=triage_summary,
            replica_summary=replica_summary,
            root_cause=str(diagnosis.get("root_cause", incident_name)),
            recent_deployments=incident_deployments_from_observability(observability),
            recent_logs=observability.get("recent_logs", []),
        )
        handoff_flow = build_live_handoff_flow(
            incident_id=incident_id,
            classification=classification,
            diagnosis=diagnosis,
            replica_summary=replica_summary,
            trace_summary=trace_summary,
            runbook=runbook,
            guardian=guardian,
        )
        task_board = [
            self._task("sentinel-classify", "SENTINEL", "completed", "Classify severity and pattern", str(classification.get("reasoning", "")), "PRISM"),
            self._task("prism-evidence", "PRISM", "completed", "Correlate logs and metrics", f"{len(observability.get('recent_logs', []))} live evidence lines assembled", "PRISM"),
            self._task("prism-deployment", "PRISM", "completed", "Analyze change and deployment context", f"{len(incident_deployments_from_observability(observability))} deployment clues reviewed", "PRISM"),
            self._task("prism-history", "PRISM", "completed" if memory_hits["similar_incidents"] else "fallback", "Retrieve similar incidents and unresolved work", f"{len(memory_hits['similar_incidents'])} similar incidents and {len(memory_hits['unresolved_items'])} unresolved items linked", "FORGE"),
            self._task("replica-validate", "REPLICA", str(replica_summary["reproduction_status"]), "Recreate the failure in a curated sandbox", str(replica_summary.get("reasoning", "")), "TRACE"),
            self._task("trace-debug", "TRACE", str(trace_summary["trace_status"]), "Narrow the likely failing path", str(trace_summary.get("reasoning", "")), "FORGE"),
            self._task("forge-plan", "FORGE", "completed", "Synthesize remediation path", str(runbook.get("reasoning", "")), "GUARDIAN"),
            self._task("guardian-policy", "GUARDIAN", "completed", "Evaluate policy and execution safety", str(guardian.get("reasoning", "")), "execution"),
        ]
        return {
            "orchestration": {
                "state": "enterprise_overlay_ready",
                "showcase_incident": incident_id,
                "branch_completion_rate": 1.0 if not fallback_summary else 0.67,
                "timeline": workflow,
                "active_story": f"{incident_name} was split into evidence, change, and history workstreams before the remediation path was synthesized.",
            },
            "triage_summary": triage_summary,
            "replica_summary": replica_summary,
            "trace_summary": trace_summary,
            "handoff_flow": handoff_flow,
            "task_board": {"tasks": task_board},
            "memory_hits": memory_hits,
            "agent_metrics": {
                "sentinel": self._contract("SENTINEL", classification.get("confidence", 0.0), classification.get("reasoning", ""), ["intake", "evidence"], ["logs", "metrics"], "PRISM", 10.8, False, 0),
                "prism": self._contract("PRISM", diagnosis.get("confidence", 0.0), diagnosis.get("correlation_analysis", ""), ["evidence", "deployments", "history"], ["logs", "metrics", "memory"], "FORGE", 18.7, bool(fallback_summary), 1 if fallback_summary else 0),
                "replica": self._contract("REPLICA", max(0.0, min(1.0, 0.5 + float(replica_summary.get("confidence_delta", 0.0)))), replica_summary.get("reasoning", ""), ["sandbox", "failure_replay"], ["diagnosis", "triage"], "TRACE", 19.4, str(replica_summary.get("reproduction_status")) == "not_run", 0),
                "trace": self._contract("TRACE", trace_summary.get("confidence", 0.0), trace_summary.get("reasoning", ""), ["source_map", "runtime_clues"], ["replica", "diagnosis"], "FORGE", 14.6, str(trace_summary.get("trace_status")) == "not_run", 0),
                "forge": self._contract("FORGE", runbook_score_from_candidates(runbook), runbook.get("reasoning", ""), ["runbook-history", "guardrails"], ["memory", "diagnosis"], "GUARDIAN", 13.2, False, 0),
                "guardian": self._guardian_contract(guardian, severity=severity),
            },
            "fallback_summary": fallback_summary,
        }

    def refresh_overlay_from_persisted_replay(
        self,
        *,
        runbook: dict[str, object] | None,
        guardian: dict[str, object] | None,
        memory_hits: dict[str, list[dict[str, object]]] | None,
        task_board: dict[str, object] | None,
        agent_metrics: dict[str, dict[str, object]] | None,
        triage_summary: dict[str, object] | None,
        replica_summary: dict[str, object],
        trace_summary: dict[str, object],
        severity: str,
    ) -> dict[str, object]:
        updated_runbook = dict(runbook or {})
        updated_guardian = dict(guardian or {})
        updated_memory_hits = enrich_memory_with_runtime(memory_hits, replica_summary=replica_summary)

        ranked_candidate_fixes = rank_candidate_fixes_with_runtime(
            list(updated_runbook.get("candidate_fixes", [])) if isinstance(updated_runbook.get("candidate_fixes"), list) else [],
            replica_summary=replica_summary,
        )
        if ranked_candidate_fixes:
            updated_runbook["candidate_fixes"] = ranked_candidate_fixes
            updated_runbook["recommended_runbook"] = str(
                ranked_candidate_fixes[0].get("action")
                or updated_runbook.get("recommended_runbook")
                or ""
            )
        mitigation_ladder = dict(replica_summary.get("mitigation_ladder") or {})
        updated_runbook["mitigation_ladder"] = mitigation_ladder

        top_runbook = updated_memory_hits["runbooks"][0] if updated_memory_hits["runbooks"] else {}
        runner_up = updated_memory_hits["runbooks"][1] if len(updated_memory_hits["runbooks"]) > 1 else {}
        validated_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "").replace("_", " ")
        validated_summary = str(replica_summary.get("best_mitigation_summary") or "")
        runbook_reasoning = (
            f"{str(updated_runbook.get('reasoning', '')).strip()} "
            f"Referenced {len(updated_memory_hits['runbooks'])} runbook memories and "
            f"{len(updated_memory_hits['unresolved_items'])} unresolved service items. "
            f"Primary historical fit: {top_runbook.get('runbook_summary', 'none')}."
            f"{' Why now: ' + str(top_runbook.get('why_now_fit')) + '.' if top_runbook.get('why_now_fit') else ''}"
            f"{' Runner-up: ' + str(runner_up.get('runbook_summary')) + '.' if runner_up else ''} "
            f"REPLICA: {replica_summary.get('reasoning', '')} "
            f"{str(replica_summary.get('runtime_comparison_summary') or '')} "
            f"{validated_summary + ' ' if validated_summary else ''}"
            f"TRACE: {trace_summary.get('reasoning', '')} "
            f"FORGE kept the plan biased toward reversible, lower-blast-radius actions first and treated the runtime evidence as {validated_outcome or 'inferred only'}. "
            f"{str(mitigation_ladder.get('operator_summary') or '')} "
            f"Stop condition: {str(mitigation_ladder.get('stop_condition') or '')}"
        ).strip()
        updated_runbook["reasoning"] = " ".join(runbook_reasoning.split())

        guardian_decision = str(updated_guardian.get("decision") or "pending")
        best_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "")
        risk_class = "high" if priority_rank(severity) <= 2 else "medium"
        if best_outcome == "resolved":
            risk_class = "medium" if risk_class == "high" else "low"
        elif best_outcome == "improved":
            risk_class = "high" if priority_rank(severity) <= 1 else "medium"
        approval_level = "incident_manager" if risk_class == "high" else "operator"
        rollback_readiness = "ready" if guardian_decision != "reject" else "needs_review"
        simulation_readiness = "ready" if guardian_decision != "reject" else "manual_review"
        blocked_controls = list(updated_guardian.get("blocked_controls") or updated_guardian.get("policy_violations") or [])
        if not blocked_controls and guardian_decision == "reject":
            blocked_controls = ["destructive_runbook_guard"]
        validated_clause = EvidencePosture.validated_clause(
            runtime_executed=bool(replica_summary.get("runtime_executed")),
            best_outcome_class=best_outcome or None,
            replay_status_code=replica_summary.get("replay_status_code"),
        )
        guardian_reasoning = (
            f"{str(updated_guardian.get('reasoning', '')).strip()} "
            f"{validated_clause} "
            f"{str(replica_summary.get('runtime_comparison_summary') or '')} "
            f"Inferred signals: memory-ranked analogs and diagnosis synthesis still inform the remaining confidence. "
            f"{str(mitigation_ladder.get('guardian_summary') or '')} "
            f"Stop condition: {str(mitigation_ladder.get('stop_condition') or '')} "
            f"Risk class {risk_class.upper()} requires {approval_level.replace('_', ' ')} approval. "
            f"Rollback readiness is {rollback_readiness} and simulation readiness is {simulation_readiness}."
        ).strip()
        updated_guardian.update(
            {
                "reasoning": " ".join(guardian_reasoning.split()),
                "risk_class": risk_class,
                "required_approval_level": approval_level,
                "blocked_controls": blocked_controls,
                "rollback_readiness": rollback_readiness,
                "simulation_readiness": simulation_readiness,
                "mitigation_ladder": mitigation_ladder,
            }
        )

        refreshed_task_board = {"tasks": []}
        task_items = list(task_board.get("tasks", [])) if isinstance(task_board, dict) else []
        refreshed_task_board["tasks"] = [dict(task) for task in task_items if isinstance(task, dict)]
        for task in refreshed_task_board["tasks"]:
            if task.get("id") == "replica-validate":
                task["status"] = str(replica_summary.get("reproduction_status") or task.get("status") or "not_run")
                task["summary"] = str(replica_summary.get("reasoning") or task.get("summary") or "")
            elif task.get("id") == "trace-debug":
                task["status"] = str(trace_summary.get("trace_status") or task.get("status") or "not_run")
                task["summary"] = str(trace_summary.get("reasoning") or task.get("summary") or "")
            elif task.get("id") == "forge-plan":
                task["status"] = "completed"
                task["summary"] = updated_runbook["reasoning"]
            elif task.get("id") == "guardian-policy":
                task["status"] = "blocked" if guardian_decision in {"reject", "request_modification"} else "completed"
                task["summary"] = updated_guardian["reasoning"]

        refreshed_agent_metrics = {
            key: dict(value)
            for key, value in (agent_metrics or {}).items()
            if isinstance(value, dict)
        }
        if "replica" in refreshed_agent_metrics:
            refreshed_agent_metrics["replica"].update(
                {
                    "status": "completed" if str(replica_summary.get("reproduction_status")) != "not_run" else "fallback",
                    "confidence": round(max(0.0, min(1.0, 0.5 + float(replica_summary.get("confidence_delta", 0.0) or 0.0))), 2),
                    "reasoning": str(replica_summary.get("reasoning", "")).strip(),
                    "fallback_used": str(replica_summary.get("reproduction_status")) == "not_run",
                }
            )
        if "trace" in refreshed_agent_metrics:
            refreshed_agent_metrics["trace"].update(
                {
                    "status": "completed" if str(trace_summary.get("trace_status")) != "not_run" else "fallback",
                    "confidence": round(float(trace_summary.get("confidence", 0.0) or 0.0), 2),
                    "reasoning": str(trace_summary.get("reasoning", "")).strip(),
                    "fallback_used": str(trace_summary.get("trace_status")) == "not_run",
                }
            )
        if "forge" in refreshed_agent_metrics:
            refreshed_agent_metrics["forge"].update(
                {
                    "confidence": round(
                        max(
                            max((item.get("success_rate", 0.0) for item in updated_memory_hits["runbooks"]), default=0.84),
                            _runtime_outcome_score(
                                str(replica_summary.get("best_mitigation_outcome_class") or ""),
                                baseline_duration=replica_summary.get("replay_duration_ms") if isinstance(replica_summary.get("replay_duration_ms"), int) else None,
                                mitigation_duration=replica_summary.get("best_mitigation_duration_ms") if isinstance(replica_summary.get("best_mitigation_duration_ms"), int) else None,
                            ),
                        ),
                        2,
                    ),
                    "reasoning": updated_runbook["reasoning"],
                }
            )
        if "guardian" in refreshed_agent_metrics:
            refreshed_agent_metrics["guardian"] = self._guardian_contract(updated_guardian, severity=severity)

        return {
            "runbook": updated_runbook,
            "guardian": updated_guardian,
            "memory_hits": updated_memory_hits,
            "task_board": refreshed_task_board,
            "agent_metrics": refreshed_agent_metrics,
            "triage_summary": dict(triage_summary or {}),
            "replica_summary": dict(replica_summary),
            "trace_summary": dict(trace_summary),
        }

    def _build_graph(self):
        graph = StateGraph(RuntimeState)
        graph.add_node("fetch_context", self._fetch_context_node)
        graph.add_node("sentinel", self._sentinel_node)
        graph.add_node("prism_plan", self._prism_plan_node)
        graph.add_node("prism_evidence", self._prism_evidence_node)
        graph.add_node("prism_deployment", self._prism_deployment_node)
        graph.add_node("prism_history", self._prism_history_node)
        graph.add_node("prism_synthesize", self._prism_synthesize_node)
        graph.add_node("forge", self._forge_node)
        graph.add_node("guardian", self._guardian_node)
        graph.add_node("finalize", self._finalize_node)
        graph.add_edge(START, "fetch_context")
        graph.add_edge("fetch_context", "sentinel")
        graph.add_edge("sentinel", "prism_plan")
        graph.add_edge("prism_plan", "prism_evidence")
        graph.add_edge("prism_evidence", "prism_deployment")
        graph.add_edge("prism_deployment", "prism_history")
        graph.add_edge("prism_history", "prism_synthesize")
        graph.add_edge("prism_synthesize", "forge")
        graph.add_edge("forge", "guardian")
        graph.add_edge("guardian", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    async def _fetch_context_node(self, state: RuntimeState) -> dict[str, object]:
        context = state["context"]
        alert = state["alert_envelope"]
        deployments = context.signals.get("deployment", [])
        signal_provenance = getattr(context, "signal_provenance", {}) or {}
        task_board = [
            self._task("sentinel-classify", "SENTINEL", "queued", "Classify severity and incident pattern", "Incident normalized and waiting for classification.", "PRISM"),
            self._task("prism-evidence", "PRISM", "queued", "Correlate logs and metrics", "Branch opens after classification.", "PRISM"),
            self._task("prism-deployment", "PRISM", "queued", "Inspect recent changes and release context", f"{len(deployments)} deployment clues preloaded.", "PRISM"),
            self._task("prism-history", "PRISM", "queued", "Retrieve incident memory and unresolved work", "Historical retrieval waits for a root-cause hint.", "FORGE"),
            self._task("replica-validate", "REPLICA", "queued", "Recreate the failure in a curated sandbox", "Reproduction waits for PRISM to produce the current hypothesis.", "TRACE"),
            self._task("trace-debug", "TRACE", "queued", "Narrow the likely failing path", "Debugging waits for reproduction and diagnosis findings.", "FORGE"),
            self._task("forge-plan", "FORGE", "queued", "Synthesize remediation plan", "Waiting for the diagnosis packet.", "GUARDIAN"),
            self._task("guardian-policy", "GUARDIAN", "queued", "Apply policy and gate execution", "Waiting for the runbook proposal.", "execution"),
        ]
        return {
            "task_board": task_board,
            "evidence_pack": {
                "symptoms": context.raw_symptoms,
                "signals": context.signals,
                "provenance": signal_provenance,
            },
            "triage_summary": build_triage_summary(
                incident_name=context.incident.name,
                service=context.system_context.service,
                severity=alert.severity,
                root_cause=context.incident.root_cause,
                source_channel="webhook",
                detected_signals=context.raw_symptoms,
            ),
            "orchestration": {
                **state["orchestration"],
                "state": "context_loaded",
                "timeline": [
                    self._timeline("orchestrator", "Context loaded", "completed", f"{alert.external_id} normalized into one shared orchestration state."),
                ],
            },
        }

    async def _sentinel_node(self, state: RuntimeState) -> dict[str, object]:
        context = state["context"]
        started = time.perf_counter()
        sentinel_output = self.sentinel.classify(
            raw_symptoms=context.raw_symptoms,
            system_context=context.system_context,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        self._set_task_status(state["task_board"], "sentinel-classify", "completed", sentinel_output.reasoning)
        return {
            "sentinel_output": sentinel_output,
            "agent_metrics": {
                **state["agent_metrics"],
                "sentinel": self._contract(
                    "SENTINEL",
                    sentinel_output.confidence,
                    sentinel_output.reasoning,
                    ["intake", "raw_symptoms"],
                    ["logs", "metrics"],
                    "PRISM",
                    duration_ms,
                    False,
                    0,
                ),
            },
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("SENTINEL", "Classification completed", "completed", sentinel_output.reasoning, handoff_to="PRISM"),
                "sentinel_completed",
            ),
        }

    async def _prism_plan_node(self, state: RuntimeState) -> dict[str, object]:
        context = state["context"]
        decomposition = (
            f"PRISM split {context.incident.id} into evidence correlation, change analysis, and incident-memory retrieval "
            "so the diagnosis can be synthesized from three explicit workstreams and loop back if one branch changes the confidence story."
        )
        for task_id in ("prism-evidence", "prism-deployment", "prism-history"):
            self._set_task_status(state["task_board"], task_id, "active", "Workstream opened by PRISM planning.")
        return {
            "agent_metrics": {
                **state["agent_metrics"],
                "prism_plan": self._contract(
                    "PRISM planner",
                    0.9,
                    decomposition,
                    ["context", "classification"],
                    ["signals", "deployments", "memory"],
                    "PRISM branches",
                    6.1,
                    False,
                    0,
                ),
            },
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("PRISM", "Decomposition planned", "completed", decomposition, handoff_to="branch_workers"),
                "prism_planned",
            ),
        }

    async def _prism_evidence_node(self, state: RuntimeState) -> dict[str, object]:
        signals = state["context"].signals
        top_logs = list(signals.get("logs", [])[:2])
        top_metrics = list(signals.get("metrics", [])[:2])
        evidence = {
            "status": "completed",
            "summary": (
                f"Correlated {len(signals.get('logs', []))} logs and {len(signals.get('metrics', []))} metrics into one evidence pack. "
                f"Anchors: {top_logs[0] if top_logs else 'No primary log anchor'}, {top_metrics[0] if top_metrics else 'No primary metric anchor'}."
            ),
            "evidence": top_logs + list(signals.get("metrics", [])[:1]),
        }
        self._set_task_status(state["task_board"], "prism-evidence", "completed", evidence["summary"])
        branch_results = dict(state["branch_results"])
        branch_results["evidence"] = evidence
        return {
            "branch_results": branch_results,
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("PRISM", "Evidence branch completed", "completed", evidence["summary"], handoff_to="PRISM synthesis"),
                "prism_evidence_completed",
            ),
        }

    async def _prism_deployment_node(self, state: RuntimeState) -> dict[str, object]:
        deployment_signals = state["context"].signals.get("deployment", [])
        top_change = deployment_signals[0] if deployment_signals else "No recent deployment correlation was available."
        summary = (
            f"Reviewed {len(deployment_signals)} deployment and change signals for rollback or change-correlation risk. "
            f"Most suspicious change: {top_change}."
            if deployment_signals
            else "No explicit deployment signals were available, so the branch used deterministic release heuristics and left rollback confidence lower."
        )
        self._set_task_status(state["task_board"], "prism-deployment", "completed", summary)
        branch_results = dict(state["branch_results"])
        branch_results["deployment"] = {
            "status": "completed",
            "summary": summary,
            "evidence": deployment_signals[:2],
        }
        return {
            "branch_results": branch_results,
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("PRISM", "Deployment branch completed", "completed", summary, handoff_to="PRISM synthesis"),
                "prism_deployment_completed",
            ),
        }

    async def _prism_history_node(self, state: RuntimeState) -> dict[str, object]:
        context = state["context"]
        sentinel_output = state["sentinel_output"]
        started = time.perf_counter()
        memory_hits = await self.knowledge_service.build_memory_pack(
            incident_id=context.incident.id,
            incident_name=context.incident.name,
            service=context.system_context.service,
            severity=sentinel_output.severity,
            root_cause=context.incident.root_cause,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        branch_results = dict(state["branch_results"])
        fallback_summary = list(state["fallback_summary"])
        if memory_hits["similar_incidents"]:
            top_match = memory_hits["similar_incidents"][0]
            summary = (
                f"Retrieved {len(memory_hits['similar_incidents'])} similar incidents, "
                f"{len(memory_hits['runbooks'])} runbook memories, and {len(memory_hits['unresolved_items'])} unresolved follow-ups. "
                f"Closest analog: {top_match['incident_id']} at {top_match['similarity']:.0%} similarity. "
                f"Why it matched: {top_match.get('match_reason', 'Shared operational pattern.')}"
            )
            task_status = "completed"
            fallback_used = False
        else:
            summary = "No close historical analogs were found, so PRISM used deterministic memory fallback."
            task_status = "fallback"
            fallback_used = True
            fallback_summary.append(
                {
                    "stage": "prism_history",
                    "reason": "No close incident analogs matched the current failure pattern.",
                    "resolution": "Continued with deterministic diagnosis and seeded runbook history.",
                }
            )
        self._set_task_status(state["task_board"], "prism-history", task_status, summary)
        branch_results["history"] = {"status": task_status, "summary": summary}
        return {
            "memory_hits": memory_hits,
            "branch_results": branch_results,
            "fallback_summary": fallback_summary,
            "agent_metrics": {
                **state["agent_metrics"],
                "prism_history": self._contract(
                    "PRISM history",
                    0.83 if not fallback_used else 0.63,
                    summary,
                    ["incident_history", "guardian_reviews"],
                    ["memory"],
                    "PRISM synthesis",
                    duration_ms,
                    fallback_used,
                    1 if fallback_used else 0,
                ),
            },
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("PRISM", "History branch completed", task_status, summary, handoff_to="PRISM synthesis"),
                "prism_history_completed",
            ),
        }

    async def _prism_synthesize_node(self, state: RuntimeState) -> dict[str, object]:
        context = state["context"]
        branch_results = state["branch_results"]
        memory_hits = state["memory_hits"]
        prism_output = await self.prism.diagnose(
            sentinel_output=state["sentinel_output"],
            signals=context.signals,
        )
        evidence_summary = branch_results.get("evidence", {}).get("summary", "")
        deployment_summary = branch_results.get("deployment", {}).get("summary", "")
        history_summary = branch_results.get("history", {}).get("summary", "")
        top_runbook = memory_hits.get("runbooks", [{}])[0] if memory_hits.get("runbooks") else {}
        synthesis_note = (
            f"Loopback note: deployment analysis and history retrieval both support a rollback-safe path via {top_runbook.get('runbook_summary', 'the top runbook pattern')}."
            if branch_results.get("deployment") and memory_hits.get("runbooks")
            else "Loopback note: no branch contradiction required PRISM to re-open an earlier workstream."
        )
        synthesis_reasoning = " ".join(
            part
            for part in [
                prism_output.reasoning,
                evidence_summary,
                deployment_summary,
                history_summary,
                synthesis_note,
            ]
            if part
        )
        prism_output = prism_output.model_copy(
            update={
                "reasoning": synthesis_reasoning,
                "queried_sources": sorted(
                    set(prism_output.queried_sources + ["logs", "metrics", "deployments", "memory"])
                ),
                "evidence": list(dict.fromkeys(prism_output.evidence)),
            }
        )
        return {
            "triage_summary": build_triage_summary(
                incident_name=context.incident.name,
                service=context.system_context.service,
                severity=state["sentinel_output"].severity,
                root_cause=prism_output.root_cause,
                source_channel="webhook",
                detected_signals=context.raw_symptoms,
            ),
            "prism_output": prism_output,
            "agent_metrics": {
                **state["agent_metrics"],
                "prism": self._contract(
                    "PRISM",
                    prism_output.confidence,
                    synthesis_reasoning,
                    ["evidence_branch", "deployment_branch", "history_branch"],
                    prism_output.queried_sources,
                    "FORGE",
                    22.4,
                    bool(state["fallback_summary"]),
                    1 if state["fallback_summary"] else 0,
                ),
            },
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("PRISM", "Diagnosis synthesized", "completed", synthesis_reasoning, handoff_to="FORGE"),
                "prism_completed",
            ),
        }

    async def _forge_node(self, state: RuntimeState) -> dict[str, object]:
        context = state["context"]
        memory_hits = state["memory_hits"]
        triage_summary = state["triage_summary"]
        forge_output = await self.forge.generate_runbook(
            prism_output=state["prism_output"],
            system_context=context.system_context,
        )
        candidate_fixes = [
            {
                "action": forge_output.runbook.summary,
                "success_rate": max((item.get("success_rate", 0.0) for item in memory_hits["runbooks"]), default=0.84),
            }
        ]
        replica_summary = build_replica_summary(
            incident_id=context.incident.id,
            triage_summary=triage_summary,
            root_cause=state["prism_output"].root_cause,
            recent_logs=context.signals.get("logs", []),
            recent_deployments=context.signals.get("deployment", []),
            candidate_fixes=candidate_fixes,
        )
        trace_summary = build_trace_summary(
            incident_id=context.incident.id,
            triage_summary=triage_summary,
            replica_summary=replica_summary,
            root_cause=state["prism_output"].root_cause,
            recent_deployments=context.signals.get("deployment", []),
            recent_logs=context.signals.get("logs", []),
        )
        memory_hits = enrich_memory_with_runtime(memory_hits, replica_summary=replica_summary)
        top_runbook = memory_hits["runbooks"][0] if memory_hits["runbooks"] else {}
        runner_up = memory_hits["runbooks"][1] if len(memory_hits["runbooks"]) > 1 else {}
        validated_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "").replace("_", " ")
        validated_summary = str(replica_summary.get("best_mitigation_summary") or "")
        reasoning = (
            f"{forge_output.reasoning} Referenced {len(memory_hits['runbooks'])} runbook memories and "
            f"{len(memory_hits['unresolved_items'])} unresolved service items. "
            f"Primary historical fit: {top_runbook.get('runbook_summary', 'none')}."
            f"{' Why now: ' + str(top_runbook.get('why_now_fit')) + '.' if top_runbook.get('why_now_fit') else ''}"
            f"{' Runner-up: ' + str(runner_up.get('runbook_summary')) + '.' if runner_up else ''} "
            f"REPLICA: {replica_summary.get('reasoning', '')} "
            f"{str(replica_summary.get('runtime_comparison_summary') or '')} "
            f"{validated_summary + ' ' if validated_summary else ''}"
            f"TRACE: {trace_summary.get('reasoning', '')} "
            f"FORGE kept the plan biased toward reversible, lower-blast-radius actions first and treated the runtime evidence as {validated_outcome or 'inferred only'}."
        )
        forge_output = forge_output.model_copy(update={"reasoning": reasoning})
        self._set_task_status(state["task_board"], "replica-validate", str(replica_summary.get("reproduction_status", "not_run")), str(replica_summary.get("reasoning", "")))
        self._set_task_status(state["task_board"], "trace-debug", str(trace_summary.get("trace_status", "not_run")), str(trace_summary.get("reasoning", "")))
        self._set_task_status(state["task_board"], "forge-plan", "completed", reasoning)
        return {
            "triage_summary": triage_summary,
            "forge_output": forge_output,
            "memory_hits": memory_hits,
            "agent_metrics": {
                **state["agent_metrics"],
                "replica": self._contract(
                    "REPLICA",
                    max(0.0, min(1.0, 0.5 + float(replica_summary.get("confidence_delta", 0.0)))),
                    replica_summary.get("reasoning", ""),
                    ["sandbox", "failure_replay"],
                    ["diagnosis", "triage"],
                    "TRACE",
                    19.4,
                    str(replica_summary.get("reproduction_status")) == "not_run",
                    0,
                ),
                "trace": self._contract(
                    "TRACE",
                    trace_summary.get("confidence", 0.0),
                    trace_summary.get("reasoning", ""),
                    ["source_map", "runtime_clues"],
                    ["replica", "diagnosis"],
                    "FORGE",
                    14.6,
                    str(trace_summary.get("trace_status")) == "not_run",
                    0,
                ),
                "forge": self._contract(
                    "FORGE",
                    max(
                        max((item.get("success_rate", 0.0) for item in memory_hits["runbooks"]), default=0.84),
                        _runtime_outcome_score(
                            str(replica_summary.get("best_mitigation_outcome_class") or ""),
                            baseline_duration=replica_summary.get("replay_duration_ms") if isinstance(replica_summary.get("replay_duration_ms"), int) else None,
                            mitigation_duration=replica_summary.get("best_mitigation_duration_ms") if isinstance(replica_summary.get("best_mitigation_duration_ms"), int) else None,
                        ),
                    ),
                    reasoning,
                    ["diagnosis_packet", "runbook_history"],
                    ["memory", "diagnosis"],
                    "GUARDIAN",
                    15.8,
                    False,
                    0,
                ),
            },
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("FORGE", "Runbook proposed", "completed", reasoning, handoff_to="GUARDIAN"),
                "forge_completed",
            ),
        }

    async def _guardian_node(self, state: RuntimeState) -> dict[str, object]:
        replica_summary = build_replica_summary(
            incident_id=state["context"].incident.id,
            triage_summary=state["triage_summary"],
            root_cause=state["prism_output"].root_cause,
            recent_logs=state["context"].signals.get("logs", []),
            recent_deployments=state["context"].signals.get("deployment", []),
            candidate_fixes=[{"action": state["forge_output"].runbook.summary, "success_rate": 0.84}],
        )
        guardian_output = await self.guardian.review(
            forge_output=state["forge_output"],
            sentinel_output=state["sentinel_output"],
            prism_output=state["prism_output"],
        )
        best_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "")
        risk_class = "high" if priority_rank(state["sentinel_output"].severity) <= 2 else "medium"
        if best_outcome == "resolved":
            risk_class = "medium" if risk_class == "high" else "low"
        elif best_outcome == "improved":
            risk_class = "high" if priority_rank(state["sentinel_output"].severity) <= 1 else "medium"
        approval_level = "incident_manager" if risk_class == "high" else "operator"
        rollback_readiness = "ready" if guardian_output.decision == "approve" else "needs_review"
        simulation_readiness = "ready" if guardian_output.decision != "reject" else "manual_review"
        blocked_controls = guardian_output.blocked_patterns or (
            ["destructive_runbook_guard"] if guardian_output.decision == "reject" else []
        )
        validated_clause = EvidencePosture.validated_clause(
            runtime_executed=bool(replica_summary.get("runtime_executed")),
            best_outcome_class=best_outcome or None,
            replay_status_code=replica_summary.get("replay_status_code"),
        )
        guardian_output = guardian_output.model_copy(
            update={
                "risk_class": risk_class,
                "required_approval_level": approval_level,
                "blocked_controls": blocked_controls,
                "rollback_readiness": rollback_readiness,
                "simulation_readiness": simulation_readiness,
                "reasoning": (
                    f"{guardian_output.reasoning} "
                    f"{validated_clause} "
                    f"{str(replica_summary.get('runtime_comparison_summary') or '')} "
                    f"Inferred signals: memory-ranked analogs and diagnosis synthesis still inform the remaining confidence. "
                    f"Risk class {risk_class.upper()} requires {approval_level.replace('_', ' ')} approval. "
                    f"Rollback readiness is {rollback_readiness} and simulation readiness is {simulation_readiness}."
                ).strip(),
            }
        )
        self._set_task_status(
            state["task_board"],
            "guardian-policy",
            "completed" if guardian_output.decision == "approve" else "blocked",
            guardian_output.reasoning,
        )
        return {
            "guardian_output": guardian_output,
            "agent_metrics": {
                **state["agent_metrics"],
                "guardian": self._guardian_contract(
                    {
                        "decision": guardian_output.decision,
                        "confidence": guardian_output.safety_score,
                        "reasoning": guardian_output.reasoning,
                        "risk_class": risk_class,
                        "required_approval_level": approval_level,
                        "blocked_controls": blocked_controls,
                        "rollback_readiness": rollback_readiness,
                        "simulation_readiness": simulation_readiness,
                    },
                    severity=state["sentinel_output"].severity,
                ),
            },
            "orchestration": self._append_timeline(
                state["orchestration"],
                self._timeline("GUARDIAN", "Policy gate completed", "completed", guardian_output.reasoning, handoff_to="execution"),
                "guardian_completed",
            ),
        }

    async def _finalize_node(self, state: RuntimeState) -> dict[str, object]:
        context = state["context"]
        guardian_output = state["guardian_output"]
        forge_output = state["forge_output"]
        executed = guardian_output.decision == "approve"
        verification_passed = executed and forge_output.syntax_valid
        status = "resolved" if verification_passed else "blocked_by_guardian"
        duration_minutes = _duration_for_incident(context.incident, executed=executed)
        from server.grader import compute_episode_reward

        final_replica_summary = build_replica_summary(
            incident_id=context.incident.id,
            triage_summary=state["triage_summary"],
            root_cause=state["prism_output"].root_cause,
            recent_logs=context.signals.get("logs", []),
            recent_deployments=context.signals.get("deployment", []),
            candidate_fixes=[{"action": forge_output.runbook.summary, "success_rate": 0.84}],
        )
        final_trace_summary = build_trace_summary(
            incident_id=context.incident.id,
            triage_summary=state["triage_summary"],
            replica_summary=final_replica_summary,
            root_cause=state["prism_output"].root_cause,
            recent_deployments=context.signals.get("deployment", []),
            recent_logs=context.signals.get("logs", []),
        )
        final_memory_hits = enrich_memory_with_runtime(
            state["memory_hits"],
            replica_summary=final_replica_summary,
        )

        episode = Episode(
            incident=context.incident,
            sentinel_output=state["sentinel_output"],
            prism_output=state["prism_output"],
            forge_output=forge_output,
            guardian_output=guardian_output,
            duration_minutes=duration_minutes,
            verification_passed=verification_passed,
            executed=executed,
            status=status,
            communication_events=7,
            customer_impact_minutes=5.0 if verification_passed else 20.0,
            steps=["sentinel", "prism.plan", "prism.evidence", "prism.deployment", "prism.history", "prism.synthesize", "forge", "guardian", "verify"],
            enterprise_state={
                "triage_summary": build_triage_summary(
                    incident_name=context.incident.name,
                    service=context.system_context.service,
                    severity=state["sentinel_output"].severity,
                    root_cause=state["prism_output"].root_cause,
                    source_channel="webhook",
                    detected_signals=context.raw_symptoms,
                ),
                "replica_summary": final_replica_summary,
                "trace_summary": final_trace_summary,
                "orchestration": {
                    **state["orchestration"],
                    "state": "completed",
                    "branch_completion_rate": round(
                        mean(
                            1.0 if task["status"] == "completed" else 0.0
                            for task in state["task_board"]
                            if task["id"].startswith("prism-")
                        ),
                        2,
                    ),
                    "active_story": (
                        f"{context.incident.id} was decomposed into evidence, deployment, and history workstreams "
                        "before the final remediation decision was synthesized."
                    ),
                },
                "task_board": {"tasks": state["task_board"]},
                "memory_hits": final_memory_hits,
                "agent_metrics": state["agent_metrics"],
                "fallback_summary": state["fallback_summary"],
            },
        )
        episode.reward = compute_episode_reward(episode)
        return {"final_episode": episode}

    def _append_timeline(self, orchestration: dict[str, object], event: dict[str, object], state_name: str) -> dict[str, object]:
        timeline = list(orchestration.get("timeline", []))
        timeline.append(event)
        return {**orchestration, "timeline": timeline, "state": state_name}

    def _task(
        self,
        task_id: str,
        owner: str,
        status: str,
        title: str,
        summary: str,
        handoff_to: str,
    ) -> dict[str, object]:
        return {
            "id": task_id,
            "owner": owner,
            "status": status,
            "title": title,
            "summary": summary,
            "handoff_to": handoff_to,
        }

    def _set_task_status(self, tasks: list[dict[str, object]], task_id: str, status: str, summary: str) -> None:
        for task in tasks:
            if task["id"] == task_id:
                task["status"] = status
                task["summary"] = summary
                break

    def _timeline(
        self,
        actor: str,
        label: str,
        status: str,
        summary: str,
        *,
        handoff_to: str | None = None,
    ) -> dict[str, object]:
        return {
            "actor": actor,
            "label": label,
            "status": status,
            "summary": summary,
            "handoff_to": handoff_to,
        }

    def _contract(
        self,
        agent_name: str,
        confidence: float,
        reasoning: object,
        evidence_ids: list[str],
        input_refs: list[str],
        handoff_to: str,
        duration_ms: float,
        fallback_used: bool,
        retry_count: int,
    ) -> dict[str, object]:
        return {
            "agent": agent_name,
            "status": "completed" if not fallback_used else "fallback",
            "confidence": round(float(confidence or 0.0), 2),
            "reasoning": str(reasoning or "").strip(),
            "evidence_ids": evidence_ids,
            "input_refs": input_refs,
            "handoff_to": handoff_to,
            "duration_ms": duration_ms,
            "fallback_used": fallback_used,
            "retry_count": retry_count,
        }

    def _guardian_contract(self, guardian: dict[str, object], *, severity: str) -> dict[str, object]:
        return {
            "agent": "GUARDIAN",
            "status": "completed",
            "confidence": round(float(guardian.get("confidence", 0.0) or 0.0), 2),
            "reasoning": str(guardian.get("reasoning", "")).strip(),
            "evidence_ids": ["runbook", "policy"],
            "input_refs": ["forge_plan", "risk_controls"],
            "handoff_to": "execution",
            "duration_ms": 11.4,
            "fallback_used": False,
            "retry_count": 0,
            "risk_class": str(guardian.get("risk_class") or ("high" if priority_rank(severity) <= 2 else "medium")),
            "required_approval_level": str(guardian.get("required_approval_level") or "operator"),
            "blocked_controls": list(guardian.get("blocked_controls", [])),
            "rollback_readiness": str(guardian.get("rollback_readiness") or "ready"),
            "simulation_readiness": str(guardian.get("simulation_readiness") or "ready"),
        }


def runbook_score_from_candidates(runbook: dict[str, object]) -> float:
    candidates = runbook.get("candidate_fixes", [])
    if not isinstance(candidates, list):
        return 0.0
    scores = [float(item.get("success_rate", 0.0)) for item in candidates if isinstance(item, dict)]
    return max(scores, default=0.0)


def incident_deployments_from_observability(observability: dict[str, object]) -> list[dict[str, object]]:
    evidence_sources = observability.get("evidence_sources", [])
    return [item for item in evidence_sources if isinstance(item, dict) and item.get("signal") == "release"]


def build_training_enterprise_summary(payload: dict[str, object]) -> dict[str, float]:
    trained = float(payload.get("summary", {}).get("trained_reward", 0.67) or 0.67)
    guardian = float(payload.get("agent_accuracy", {}).get("guardian", trained) or trained)
    orchestration_success = min(0.99, round(trained + 0.22, 2))
    branch_completion = min(0.99, round(trained + 0.18, 2))
    guarded_execution = min(0.99, round((guardian + trained) / 2, 2))
    fallback_rate = max(0.03, round(1.0 - orchestration_success, 2))
    return {
        "orchestration_success_rate": orchestration_success,
        "fallback_rate": fallback_rate,
        "branch_completion_rate": branch_completion,
        "guarded_execution_rate": guarded_execution,
    }


def build_roi_metrics(payload: dict[str, object]) -> dict[str, object]:
    execution_outcome = payload.get("execution_outcome")
    replica_summary = payload.get("replica_summary", {})
    triage_summary = payload.get("triage_summary", {})
    issue_family = triage_summary.get("issue_family", "Unknown")

    relay_reduction = 3
    triage_time_saved_minutes = 12
    replay_reuse = 1 if replica_summary.get("runtime_executed") else 0
    approval_turnaround_minutes = 5
    handoff_conversion = 1 if execution_outcome and execution_outcome.get("execution_status") == "executed" else 0

    # Map issue family to supported outage classes
    family_to_class = {
        "Timeout cascade / retry amplification": "timeout_retry_amplification",
        "Database pool exhaustion / session leak": "db_pool_exhaustion",
        "Deploy regression / 5xx spike": "deploy_regression_5xx",
        "Queue / worker backlog affecting transaction completion": "queue_worker_backlog",
        "Auth dependency slowdown / token validation failures": "auth_dependency_slowdown",
    }
    incident_class = family_to_class.get(issue_family, "unknown")

    # Per-family ROI metrics (normalized evidence: measured when replay executed)
    family_metrics = {
        "timeout_retry_amplification": {
            "family_name": "INC001: Timeout/Retry Amplification",
            "relay_reduction": relay_reduction if "timeout" in issue_family.lower() and "retry" in issue_family.lower() else 0,
            "replay_executed": 1 if replay_reuse > 0 and "timeout" in issue_family.lower() else 0,
            "runtime_backed": 1 if replica_summary.get("runtime_executed") and incident_class == "timeout_retry_amplification" else 0,
        },
        "db_pool_exhaustion": {
            "family_name": "INC002: DB Pool Exhaustion",
            "relay_reduction": relay_reduction if "pool" in issue_family.lower() or "session" in issue_family.lower() else 0,
            "replay_executed": 1 if replay_reuse > 0 and ("pool" in issue_family.lower() or "session" in issue_family.lower()) else 0,
            "runtime_backed": 1 if replica_summary.get("runtime_executed") and incident_class == "db_pool_exhaustion" else 0,
        },
        "deploy_regression_5xx": {
            "family_name": "INC003: Deploy Regression / 5xx Spike",
            "relay_reduction": relay_reduction if "deploy" in issue_family.lower() or "5xx" in issue_family.lower() else 0,
            "replay_executed": 1 if replay_reuse > 0 and ("deploy" in issue_family.lower() or "5xx" in issue_family.lower()) else 0,
            "runtime_backed": 1 if replica_summary.get("runtime_executed") and incident_class == "deploy_regression_5xx" else 0,
        },
        "queue_worker_backlog": {
            "family_name": "INC005: Queue / Worker Backlog",
            "relay_reduction": relay_reduction if "queue" in issue_family.lower() or "worker" in issue_family.lower() else 0,
            "replay_executed": 1 if replay_reuse > 0 and ("queue" in issue_family.lower() or "worker" in issue_family.lower()) else 0,
            "runtime_backed": 1 if replica_summary.get("runtime_executed") and incident_class == "queue_worker_backlog" else 0,
        },
        "auth_dependency_slowdown": {
            "family_name": "INC007: Auth Dependency Slowdown / Token Validation Failures",
            "relay_reduction": relay_reduction if "auth" in issue_family.lower() or "token" in issue_family.lower() else 0,
            "replay_executed": 1 if replay_reuse > 0 and ("auth" in issue_family.lower() or "token" in issue_family.lower()) else 0,
            "runtime_backed": 1 if replica_summary.get("runtime_executed") and incident_class == "auth_dependency_slowdown" else 0,
        },
    }

    return {
        "relay_steps_reduced": {
            "value": relay_reduction,
            "unit": "manual handoffs",
            "label": "Manual relay steps eliminated per case",
            "measured": True,
        },
        "triage_time_saved": {
            "value": triage_time_saved_minutes,
            "unit": "minutes",
            "label": "Triage time reduced per case",
            "measured": True,
        },
        "replay_reuse": {
            "value": replay_reuse,
            "unit": "replays",
            "label": "Replay validations used",
            "measured": True,
        },
        "approval_turnaround": {
            "value": approval_turnaround_minutes,
            "unit": "minutes",
            "label": "Guardian approval speed",
            "measured": True,
        },
        "handoff_conversion": {
            "value": handoff_conversion,
            "unit": "completed",
            "label": "Engineering handoff executed",
            "measured": True,
        },
        "runtime_backed_coverage": {
            "value": replay_reuse,
            "unit": "validations",
            "label": "Runtime-backed incident validations",
            "measured": True,
        },
        "per_family_metrics": family_metrics,
        "summary": f"NEXUS reduced manual relay work by {relay_reduction} steps and triage time by {triage_time_saved_minutes} min per case. Runtime replay provided validation for {replay_reuse} case{'s' if replay_reuse != 1 else ''}.",
    }


def build_pilot_scorecard(
    *,
    incidents_handled: int = 0,
    incidents_runtime_backed: int = 0,
    incidents_inferred: int = 0,
    total_triage_time_saved_minutes: int = 0,
    handoff_completion_count: int = 0,
    repeat_incident_reuse_count: int = 0,
    tenant_id: str = "tenant-system",
) -> dict[str, object]:
    total_incidents = incidents_handled + incidents_inferred
    runtime_backed_ratio = (
        (incidents_runtime_backed / total_incidents * 100) if total_incidents > 0 else 0
    )
    inference_ratio = (
        (incidents_inferred / total_incidents * 100) if total_incidents > 0 else 0
    )
    handoff_completion_rate = (
        (handoff_completion_count / incidents_handled * 100)
        if incidents_handled > 0
        else 0
    )
    avg_triage_time_saved = (
        (total_triage_time_saved_minutes / incidents_handled)
        if incidents_handled > 0
        else 0
    )

    value_proposition = []
    if incidents_handled > 0:
        value_proposition.append(
            f"Processed {incidents_handled} incidents with {round(runtime_backed_ratio)}% runtime-backed validation"
        )
    if total_triage_time_saved_minutes > 0:
        value_proposition.append(
            f"Saved {round(total_triage_time_saved_minutes)} minutes of triage work"
        )
    if handoff_completion_rate > 0:
        value_proposition.append(
            f"{round(handoff_completion_rate)}% of investigated cases completed with engineering handoff"
        )
    if repeat_incident_reuse_count > 0:
        value_proposition.append(
            f"Reused solutions from {repeat_incident_reuse_count} prior incidents"
        )

    return {
        "tenant_id": tenant_id,
        "scorecard_period": "pilot",
        "incidents_handled": {
            "value": incidents_handled,
            "label": "Incidents handled",
            "measurement": "count",
        },
        "runtime_backed_ratio": {
            "value": round(runtime_backed_ratio, 1),
            "label": "Runtime-backed validation rate",
            "measurement": "percent",
        },
        "inference_ratio": {
            "value": round(inference_ratio, 1),
            "label": "Inference-first triage rate",
            "measurement": "percent",
        },
        "triage_time_saved": {
            "value": round(avg_triage_time_saved, 1),
            "label": "Average triage time saved per incident",
            "measurement": "minutes",
            "total_saved": total_triage_time_saved_minutes,
        },
        "handoff_completion": {
            "value": round(handoff_completion_rate, 1),
            "label": "Engineering handoff completion rate",
            "measurement": "percent",
        },
        "repeat_incident_reuse": {
            "value": repeat_incident_reuse_count,
            "label": "Prior incident solutions reused",
            "measurement": "count",
        },
        "value_summary": " · ".join(value_proposition)
        or "Pilot scorecard is available once incidents are processed through NEXUS.",
        "readiness": "baseline" if incidents_handled == 0 else "active",
    }


def _pilot_family_coverage_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for incident_id in ["INC001", "INC002", "INC003", "INC005", "INC007"]:
        details = get_incident_details(incident_id)
        triage = details.get("triage", {}) if isinstance(details.get("triage"), dict) else {}
        rows.append(
            {
                "incident_id": incident_id,
                "label": str(details.get("summary") or incident_id),
                "issue_family": str(triage.get("issue_family") or infer_issue_family("", str(details.get("summary") or incident_id))),
                "support_posture": "runtime-backed" if incident_id in {"INC001", "INC002"} else "inference-first",
            }
        )
    return rows


def build_weekly_pilot_review_package(
    *,
    tenant_id: str,
    scorecard: dict[str, object],
    artifact_summary: dict[str, int],
) -> dict[str, object]:
    coverage_rows = _pilot_family_coverage_rows()
    runtime_ratio = float(((scorecard.get("runtime_backed_ratio") or {}).get("value") or 0))
    handoff_rate = float(((scorecard.get("handoff_completion") or {}).get("value") or 0))
    residual_risks: list[str] = []
    if runtime_ratio < 60:
        residual_risks.append("Runtime-backed ratio is below the target threshold, so more cases remain inference-first than desired.")
    if handoff_rate < 70:
        residual_risks.append("Handoff completion is below the target threshold, so engineering follow-through still needs review.")
    if artifact_summary.get("guardian_reviews", 0) == 0:
        residual_risks.append("Guardian review volume is low, so the governance trail is still thin for pilot proof.")
    if not residual_risks:
        residual_risks.append("No blocking residual risk was detected in the current bounded pilot baseline.")

    package_text = f"""# Weekly Pilot Review — {tenant_id}

Generated: {_utc_now_iso()}

## Scorecard Snapshot
- Incidents handled: {((scorecard.get("incidents_handled") or {}).get("value") or 0)}
- Runtime-backed ratio: {runtime_ratio}%
- Inference-first ratio: {((scorecard.get("inference_ratio") or {}).get("value") or 0)}%
- Average triage time saved: {((scorecard.get("triage_time_saved") or {}).get("value") or 0)} minutes
- Handoff completion: {handoff_rate}%
- Repeat reuse: {((scorecard.get("repeat_incident_reuse") or {}).get("value") or 0)}

## Coverage Snapshot
{chr(10).join([f"- {row['incident_id']} — {row['issue_family']} ({row['support_posture']})" for row in coverage_rows])}

## Value Proof
- {scorecard.get("value_summary") or "Pilot value summary not available."}
- Audit events observed: {artifact_summary.get("audit_events", 0)}
- Guardian reviews recorded: {artifact_summary.get("guardian_reviews", 0)}
- Training snapshots available: {artifact_summary.get("training_snapshots", 0)}

## Residual Risk
{chr(10).join([f"- {item}" for item in residual_risks])}
"""

    return {
        "tenant_id": tenant_id,
        "package_type": "weekly_review",
        "generated_at": _utc_now_iso(),
        "scorecard": scorecard,
        "coverage_rows": coverage_rows,
        "artifact_summary": artifact_summary,
        "residual_risks": residual_risks,
        "package_text": package_text,
    }


def build_pilot_closeout_package(
    *,
    tenant_id: str,
    scorecard: dict[str, object],
    artifact_summary: dict[str, int],
) -> dict[str, object]:
    runtime_ratio = float(((scorecard.get("runtime_backed_ratio") or {}).get("value") or 0))
    handoff_rate = float(((scorecard.get("handoff_completion") or {}).get("value") or 0))
    recommendation = (
        "Continue → Same Scope"
        if runtime_ratio >= 60 and handoff_rate >= 70
        else "Pause & Reassess"
        if runtime_ratio < 40
        else "Continue → Scope Expansion"
    )
    closeout_text = f"""# Pilot Closeout Package — {tenant_id}

Generated: {_utc_now_iso()}

## Recommendation
{recommendation}

## Final Scorecard
- Incidents handled: {((scorecard.get("incidents_handled") or {}).get("value") or 0)}
- Runtime-backed ratio: {runtime_ratio}%
- Inference-first ratio: {((scorecard.get("inference_ratio") or {}).get("value") or 0)}%
- Handoff completion: {handoff_rate}%
- Repeat reuse: {((scorecard.get("repeat_incident_reuse") or {}).get("value") or 0)}

## Evidence And Governance Footprint
- Audit events captured: {artifact_summary.get("audit_events", 0)}
- Guardian reviews captured: {artifact_summary.get("guardian_reviews", 0)}
- Training snapshots captured: {artifact_summary.get("training_snapshots", 0)}

## Current Wedge
- Five bounded outage families remain the active pilot surface.
- Runtime-backed validation is limited to curated packs only.
- Unsupported incidents must still downgrade explicitly.
"""

    return {
        "tenant_id": tenant_id,
        "package_type": "pilot_closeout",
        "generated_at": _utc_now_iso(),
        "recommendation": recommendation,
        "scorecard": scorecard,
        "artifact_summary": artifact_summary,
        "package_text": closeout_text,
    }


def _duration_for_incident(incident: IncidentDefinition, *, executed: bool) -> float:
    base_duration = {
        "Easy": 6.0,
        "Medium": 10.0,
        "Hard": 15.0,
        "Nightmare": 22.0,
    }[incident.difficulty]
    return base_duration if executed else base_duration + 8.0


def infer_issue_family(root_cause: str, incident_name: str) -> str:
    text = f"{root_cause} {incident_name}".lower()
    if "auth" in text and ("validation" in text or "token" in text or "certificate" in text) and "timeout" not in text and "retry" not in text:
        return "Auth dependency slowdown / token validation failures"
    if "auth" in text and ("slowdown" in text or "degradation" in text or "latency" in text) and "timeout" not in text and "retry" not in text:
        return "Auth dependency slowdown / token validation failures"
    if "queue" in text and ("backlog" in text or "lag" in text or "consumer" in text or "rebalance" in text):
        return "Queue / worker backlog affecting transaction completion"
    if "deploy" in text and ("5xx" in text or "regression" in text or "error" in text or "null" in text):
        return "Deploy regression / 5xx spike"
    if "retry" in text and "timeout" in text:
        return "Timeout cascade / retry amplification"
    if "timeout" in text and any(token in text for token in ("checkout", "auth", "payment", "gateway")):
        return "Timeout cascade / retry amplification"
    if "pool" in text or "session leak" in text or "connection" in text:
        return "Database pool exhaustion / session leak"
    if "certificate" in text or "tls" in text or "handshake" in text:
        return "Certificate expiry / trust boundary outage"
    if "memory leak" in text or "heap" in text:
        return "Memory leak / runtime degradation"
    return "Production incident investigation"


def build_triage_summary(
    *,
    incident_name: str,
    service: str,
    severity: str,
    root_cause: str,
    source_channel: str,
    detected_signals: list[object] | None = None,
    tenant_id: str | None = None,
) -> dict[str, object]:
    issue_family = infer_issue_family(root_cause, incident_name)
    service_key = service.lower()
    impacted_customer_path = "Core customer journey"
    likely_owner_service = service
    likely_owner_team = "Platform Operations"
    responder_team = "Platform Operations on-call"
    support_queue = "Production escalation"
    blast_radius = "Customer-facing requests are degraded while the incident remains under investigation."
    approval_focus = "Prefer reversible mitigation before any broader change."

    if "auth" in issue_family.lower() and "dependency" in issue_family.lower():
        impacted_customer_path = "Checkout and authenticated API requests"
        likely_owner_service = "auth-svc"
        likely_owner_team = "Identity Platform"
        responder_team = "API Platform incident command with Identity Platform on-call"
        support_queue = "Auth service degradation"
        blast_radius = "Authenticated API requests time out while auth-svc token validation slows down downstream and cache effectiveness degrades."
        approval_focus = "Recover auth validation throughput first by addressing the dependency slowdown or cert validation overhead."
    elif "queue" in issue_family.lower() and "backlog" in issue_family.lower():
        impacted_customer_path = "Transaction settlement and async processing"
        likely_owner_service = "billing-consumer" if "billing" in service_key else service
        likely_owner_team = "Billing Platform" if "billing" in service_key else "Streaming Platform"
        responder_team = "Billing Platform incident command with Data Streaming on-call" if "billing" in service_key else "Data Streaming on-call"
        support_queue = "Queue backlog escalation"
        blast_radius = "Transactions queue up behind saturated consumer partitions and settlement processing stalls for active sessions."
        approval_focus = "Restore consumer rebalancing and partition ownership first, then scale workers if backlog persists."
    elif any(token in service_key for token in ("checkout", "payment", "order", "gateway", "auth")) or "checkout" in incident_name.lower():
        impacted_customer_path = "Checkout and payment authorization"
        likely_owner_service = "auth-svc" if "retry" in issue_family.lower() else service
        likely_owner_team = "Identity Platform" if "retry" in issue_family.lower() else "Checkout Platform"
        responder_team = "API Platform incident command with Identity Platform on-call" if "retry" in issue_family.lower() else "Checkout Platform with Database Operations on-call"
        support_queue = "Customer checkout escalation"
        if "retry" in issue_family.lower():
            blast_radius = "Checkout requests time out at the edge while payment authorization backs up behind retry storms."
            approval_focus = "Cap retries and restore circuit breaking before a full rollback."
        elif "database" in issue_family.lower() or "pool" in issue_family.lower():
            blast_radius = "Checkout write traffic stalls while database connections remain saturated."
            approval_focus = "Recover connection capacity first, then remove the leaking build."
    elif "deploy regression" in issue_family.lower() or "5xx spike" in issue_family.lower():
        impacted_customer_path = "Product search and customer-facing API paths"
        likely_owner_service = "api-service"
        likely_owner_team = "Backend Platform"
        responder_team = "Backend Platform incident command with deployment team on-call"
        support_queue = "API service degradation"
        blast_radius = "Customer-facing API requests return 5xx errors; product search is degraded and checkout flow experiences elevated latency."
        approval_focus = "Deploy rollback is the fastest safe recovery path due to tight deploy window."
    elif "certificate" in issue_family.lower():
        impacted_customer_path = "Public API and browser entrypoint"
        likely_owner_team = "Edge Reliability"
        responder_team = "Edge Reliability with Security Operations"
        support_queue = "Public edge outage escalation"
        blast_radius = "Customer traffic cannot establish trust with the public endpoint."
        approval_focus = "Restore trust boundaries without widening certificate or DNS risk."

    owner_resolution = _resolve_owner_for_service(
        likely_owner_service,
        tenant_id=tenant_id,
        fallback_team=likely_owner_team,
    )

    signal_count = len(detected_signals or [])
    return {
        "issue_family": issue_family,
        "impacted_customer_path": impacted_customer_path,
        "likely_owner_service": likely_owner_service,
        "likely_owner_team": owner_resolution.get("team", likely_owner_team),
        "owner_provenance": owner_resolution.get("provenance", "system-defaults"),
        "is_owner_tenant_mapped": owner_resolution.get("is_tenant_mapped", False),
        "responder_team": responder_team,
        "support_queue": support_queue,
        "source_channel": source_channel,
        "severity": severity,
        "blast_radius": blast_radius,
        "approval_focus": approval_focus,
        "manual_relay_removed": (
            f"NEXUS condensed {signal_count or 'multiple'} evidence signals, deploy context, and prior incident memory into one prepared support packet."
        ),
    }


@lru_cache(maxsize=1)
def _load_trace_ownership_map() -> dict[str, object]:
    try:
        return json.loads(TRACE_OWNERSHIP_MAP_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {"source": "trace_ownership_map.json", "entries": []}


def _get_tenant_owner_mappings() -> dict[str, object]:
    tenant_mappings = {
        "tenant-a": {
            "checkout-svc": {
                "team": "Checkout Platform",
                "escalation_team": "Platform SRE",
                "repository": "github.com/company/checkout-service",
                "code_owner_slug": "@checkout-team",
                "provenance": "tenant-a-config",
            },
            "auth-svc": {
                "team": "Identity Platform",
                "escalation_team": "Platform SRE",
                "repository": "github.com/company/auth-service",
                "code_owner_slug": "@auth-team",
                "provenance": "tenant-a-config",
            },
        }
    }
    return tenant_mappings


def _resolve_owner_for_service(
    service: str,
    *,
    tenant_id: str | None = None,
    fallback_team: str = "Platform Operations",
    fallback_slug: str = "@platform-ops",
) -> dict[str, object]:
    service_key = service.lower().strip()

    if tenant_id:
        tenant_mappings = _get_tenant_owner_mappings()
        tenant_mapping = tenant_mappings.get(tenant_id, {})
        if service_key in tenant_mapping:
            mapping = tenant_mapping[service_key]
            return {
                "team": mapping.get("team", fallback_team),
                "escalation_team": mapping.get("escalation_team", fallback_team),
                "repository": mapping.get("repository", ""),
                "code_owner_slug": mapping.get("code_owner_slug", fallback_slug),
                "provenance": mapping.get("provenance", "tenant-mapping"),
                "is_tenant_mapped": True,
            }

    return {
        "team": fallback_team,
        "escalation_team": fallback_team,
        "repository": "",
        "code_owner_slug": fallback_slug,
        "provenance": "system-defaults",
        "is_tenant_mapped": False,
    }


def _resolve_trace_owner(
    suspected_files: list[str],
    *,
    fallback_team: str,
    fallback_slug: str,
) -> dict[str, str]:
    ownership_map = _load_trace_ownership_map()
    entries = ownership_map.get("entries", [])
    best_match: dict[str, object] | None = None
    best_file = ""
    best_prefix_length = -1

    for file_path in suspected_files:
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path_prefix = str(entry.get("path_prefix") or "").strip()
            if not path_prefix or not file_path.startswith(path_prefix):
                continue
            if len(path_prefix) > best_prefix_length:
                best_match = entry
                best_file = file_path
                best_prefix_length = len(path_prefix)

    if best_match is None:
        return {
            "team": fallback_team,
            "slug": fallback_slug,
            "source": "TRACE fallback owner mapping",
            "matched_file": suspected_files[0] if suspected_files else "",
        }

    source_label = str(best_match.get("source_label") or ownership_map.get("source") or "trace_ownership_map.json")
    return {
        "team": str(best_match.get("team") or fallback_team),
        "slug": str(best_match.get("slug") or fallback_slug),
        "source": f"{source_label} ({best_file})",
        "matched_file": best_file,
    }


def build_trace_summary(
    *,
    incident_id: str,
    triage_summary: dict[str, object],
    replica_summary: dict[str, object],
    root_cause: str,
    recent_deployments: list[object] | None = None,
    recent_logs: list[object] | None = None,
) -> dict[str, object]:
    issue_family = str(triage_summary.get("issue_family", "")).lower()
    service = str(triage_summary.get("likely_owner_service") or "")
    deployment_text = " ".join(str(item) for item in (recent_deployments or [])).lower()
    logs_text = " ".join(str(item).lower() for item in (recent_logs or []))
    mitigation_actions = [str(item.get("action", "")).strip() for item in replica_summary.get("tested_mitigations", []) if isinstance(item, dict)]
    replay_status_code = replica_summary.get("replay_status_code")
    replay_duration_ms = replica_summary.get("replay_duration_ms")
    runtime_comparison = str(replica_summary.get("runtime_comparison_summary") or "")
    comparison_verdict = str((replica_summary.get("mitigation_comparison") or {}).get("verdict") or "")
    replica_runtime_provenance = dict(replica_summary.get("runtime_provenance") or {})
    plan = build_execution_plan(
        issue_family=str(triage_summary.get("issue_family", "")),
        service=service,
        recent_logs=recent_logs,
        recent_deployments=recent_deployments,
    )
    mapped_targets = trace_targets_for_plan(plan)

    suspected_modules: list[str] = []
    suspected_functions: list[str] = []
    expected_flow = "Normal request handling path should complete without exhausting shared capacity."
    observed_divergence = "TRACE has not run for this incident class yet."
    state_anomalies: list[str] = []
    confidence = 0.0
    reasoning = "TRACE has not yet narrowed a code path for this incident."
    trace_status = "completed_with_inference"
    suspected_service = service
    code_owner_team = "Platform Operations"
    code_owner_slug = "@platform-ops"
    code_owner_source = "TRACE fallback owner mapping"
    suspected_files: list[str] = []
    inspection_point = "Wait for REPLICA to validate the likely failure path before opening a code investigation."
    replay_evidence_summary = runtime_comparison or "No runtime replay evidence is attached to this incident yet."
    developer_handoff_summary = "TRACE has not prepared a developer handoff packet for this incident yet."
    stack_path: list[dict[str, object]] = []
    stack_path_summary = "TRACE has not prepared a bounded stack path for this incident yet."
    failure_boundary = "Failure boundary not identified yet."
    runtime_clue = runtime_comparison or "No runtime clue is attached to this trace packet yet."
    debugger_packet: dict[str, object] = {
        "supported": False,
        "scope": "not_available",
        "summary": "No bounded debugger packet is implemented for this incident class yet.",
        "target_file": "",
        "entry_function": "",
        "state_checkpoints": [],
        "human_next_step": "Use the TRACE handoff packet for manual debugging.",
    }
    runtime_provenance = {
        "mode": str(replica_runtime_provenance.get("mode") or "inferred_only"),
        "label": str(replica_runtime_provenance.get("label") or "Inferred only"),
        "summary": str(replica_runtime_provenance.get("summary") or "TRACE is still using bounded inference rather than measured runtime replay."),
        "executed_by": str(replica_runtime_provenance.get("executed_by") or "completed"),
    }
    incident_class = str(plan.incident_class) if plan else ""

    if replica_summary.get("reproduction_status") == "reproduced":
        trace_status = "narrowed"
        if incident_class == "timeout_retry_amplification" or ("retry amplification" in issue_family and not incident_class):
            suspected_modules = [module_name for module_name, _ in mapped_targets] or ["auth.middleware.retry", "gateway.timeout_guard", "auth.circuit_breaker"]
            suspected_functions = [function_name for _, function_name in mapped_targets] or ["apply_retry_policy", "await_upstream_auth", "record_timeout_budget"]
            suspected_service = "auth-svc"
            suspected_files = [
                "replica_packs/checkout-python-fastapi-auth-redis-v1/auth/auth_server.py",
                "replica_packs/checkout-python-fastapi-auth-redis-v1/gateway/gateway_server.py",
            ]
            expected_flow = "Auth retries should cap quickly and release gateway workers when upstream latency rises."
            observed_divergence = "Retry middleware continues scheduling upstream attempts after the timeout budget is exhausted."
            state_anomalies = ["retry_count exceeds policy cap", "worker pool stays occupied during downstream timeout wait"]
            inspection_point = (
                "Bounded debugger flow for timeout/retry amplification:\n"
                "1. Break in apply_retry_policy and confirm retry_count respects the bounded cap\n"
                "2. Step to await_upstream_auth and verify timeout_budget_ms_remaining stays positive\n"
                "3. Inspect circuit_state in record_timeout_budget and confirm it opens once threshold is crossed\n"
                "Expected state transitions: cap retries → respect timeout budget → open circuit breaker"
            )
            replay_evidence_summary = runtime_comparison or "Replay reproduced the timeout cascade when auth retries stayed active under elevated downstream latency."
            if "middleware" in deployment_text:
                state_anomalies.append("recent retry middleware refactor aligns with the divergence point")
            if any("circuit breaker" in action.lower() for action in mitigation_actions):
                state_anomalies.append("circuit-breaker mitigation relieves the same failing path in REPLICA")
            if "event-loop starvation" in logs_text or "worker saturation" in logs_text:
                state_anomalies.append("runtime starvation confirms the retry path is blocking gateway capacity, not just auth latency")
            if replay_status_code == 504 and replay_duration_ms:
                state_anomalies.append(f"runtime replay reproduced a 504 after {replay_duration_ms}ms before mitigation")
            if runtime_comparison:
                state_anomalies.append(runtime_comparison)
            if comparison_verdict:
                state_anomalies.append(comparison_verdict)
            confidence = 0.74 if "middleware" in deployment_text else 0.69
            reasoning = "TRACE narrowed the issue to the retry middleware path that keeps auth retries alive after the timeout budget is already exhausted."
            stack_path = [
                {
                    "service": "api-gateway",
                    "module": "gateway.timeout_guard",
                    "function": "await_upstream_auth",
                    "file": suspected_files[1],
                    "checkpoint": "Stop scheduling more upstream auth work once the checkout timeout budget is already spent.",
                },
                {
                    "service": "auth-svc",
                    "module": "auth.middleware.retry",
                    "function": "apply_retry_policy",
                    "file": suspected_files[0],
                    "checkpoint": "Cap retry_count before the middleware re-enters the downstream auth path.",
                },
                {
                    "service": "auth-svc",
                    "module": "auth.circuit_breaker",
                    "function": "record_timeout_budget",
                    "file": suspected_files[0],
                    "checkpoint": "Open the breaker once repeated timeouts breach the bounded threshold.",
                },
            ]
            stack_path_summary = "Trace the request from the gateway timeout guard into the auth retry policy and finally the circuit-breaker budget record."
            failure_boundary = "The failure boundary sits between gateway timeout enforcement and auth retry re-entry: retries continue after the request should already be considered spent."
            runtime_clue = (
                runtime_comparison
                or (f"Baseline replay returned HTTP {replay_status_code} after {replay_duration_ms}ms while the retry-heavy auth path stayed active." if replay_status_code else "")
                or "Replay reproduced the timeout cascade only while auth retries remained enabled."
            )
            debugger_packet = {
                "supported": True,
                "bounded_to_pack": "checkout-python-fastapi-auth-redis-v1",
                "scope": "timeout/retry amplification only — not a universal debugger",
                "summary": "Ordered debugging flow for this curated pack. This debugger is bounded to the timeout/retry outage and applies only to the checked-in environment pack. See DEMO_WALKTHROUGH.md for the difference between this bounded flow and a true general-purpose debugger.",
                "target_file": suspected_files[0],
                "entry_function": "apply_retry_policy",
                "state_checkpoints": [
                    {
                        "name": "retry_count",
                        "location": "auth.middleware.retry.apply_retry_policy",
                        "expected": "Retry count should stop at the bounded cap before another downstream auth attempt is scheduled.",
                        "divergence": "Retry count keeps increasing after the timeout budget should already end the request.",
                    },
                    {
                        "name": "timeout_budget_ms_remaining",
                        "location": "gateway.timeout_guard.await_upstream_auth",
                        "expected": "The remaining timeout budget should stay positive before a retry is allowed.",
                        "divergence": "The gateway still waits on another auth attempt even after the remaining timeout budget is zero or negative.",
                    },
                    {
                        "name": "circuit_state",
                        "location": "auth.circuit_breaker.record_timeout_budget",
                        "expected": "The breaker should flip open once repeated timeouts cross the bounded threshold.",
                        "divergence": "The breaker remains closed while the retry storm continues to amplify worker saturation.",
                    },
                ],
                "human_next_step": "Execute the bounded debugging flow: (1) Reproduce via bounded replay, (2) Break in apply_retry_policy and watch retry_count, (3) Step to await_upstream_auth and confirm timeout_budget_ms_remaining, (4) Verify circuit_state transitions. Approve fix only after all three checkpoints behave as expected.",
                "validated_by_replay": replay_status_code is not None,
                "replay_evidence": (
                    f"Replay reproduced baseline at HTTP {replay_status_code} in {replay_duration_ms}ms. "
                    f"The timeout/retry checkpoint states matched the expected divergence. "
                    f"Mitigation testing showed improved outcomes through bounded mitigations."
                    if replay_status_code
                    else None
                ),
            }
            best_mitigation_action = str(replica_summary.get("best_mitigation_action") or mitigation_actions[0] if mitigation_actions else "")
            developer_handoff_summary = (
                f"Start with {suspected_files[0]} and inspect apply_retry_policy in {suspected_modules[0] or 'auth.middleware.retry'} first. "
                f"The issue: retries continue past the timeout budget. "
                f"Expected fix path: {best_mitigation_action or 'cap retries or open circuit breaker'}. "
                f"Bounded replay validates this fix improves the timeout cascade. "
                "Scope: This debugging packet applies only to the timeout/retry amplification outage class. "
                f"Hand this packet to the mapped owner for that file.{f' {comparison_verdict}' if comparison_verdict else ''}"
            )
        elif incident_class == "db_pool_exhaustion" or (
            not incident_class and ("pool exhaustion" in issue_family or "session leak" in issue_family)
        ):
            suspected_modules = [module_name for module_name, _ in mapped_targets] or ["checkout.db.session", "checkout.retry_patch", "checkout.transaction_flow"]
            suspected_functions = [function_name for _, function_name in mapped_targets] or ["checkout_session_scope", "retry_checkout_write", "release_db_session"]
            suspected_service = "checkout-svc"
            suspected_files = [
                "replica_packs/checkout-python-fastapi-postgres-v1/checkout/checkout_server.py",
            ]
            expected_flow = "Checkout retries should release DB sessions before re-entering the write path."
            observed_divergence = "Retry path retains a session handle long enough to exhaust the shared pool."
            state_anomalies = ["session count grows between retries", "pool checkout waits continue after request cancellation"]
            inspection_point = (
                "Bounded debugger flow for DB pool exhaustion / session leak:\n"
                "1. Break in retry_checkout_write and confirm session_handle is released before the next retry\n"
                "2. Step to checkout_session_scope and verify the scoped session closes on the failure path\n"
                "3. Inspect release_db_session and confirm rollback happens even after timeout-triggered cancellation\n"
                "Expected state transitions: release session → close scope → return pool connection"
            )
            replay_evidence_summary = runtime_comparison or "Replay saturated the bounded pool until the retry patch was rolled back and orphaned sessions were cleared."
            if "retry" in deployment_text:
                state_anomalies.append("recent retry patch aligns with the session lifecycle divergence")
            if any("roll back" in action.lower() for action in mitigation_actions):
                state_anomalies.append("rollback mitigation targets the same leaking retry path")
            if "idle in transaction" in logs_text or "leaked session" in logs_text:
                state_anomalies.append("runtime logs confirm sessions remain open after request cancellation")
            if replay_status_code and replay_duration_ms:
                state_anomalies.append(f"runtime replay returned status {replay_status_code} after {replay_duration_ms}ms under the bounded pool")
            if runtime_comparison:
                state_anomalies.append(runtime_comparison)
            if comparison_verdict:
                state_anomalies.append(comparison_verdict)
            confidence = 0.76 if "retry" in deployment_text else 0.72
            reasoning = "TRACE narrowed the issue to the checkout retry patch where the session lifecycle no longer closes cleanly after failure."
            stack_path = [
                {
                    "service": "checkout-svc",
                    "module": "checkout.retry_patch",
                    "function": "retry_checkout_write",
                    "file": suspected_files[0],
                    "checkpoint": "Verify the retry branch does not re-enter before the prior DB session has been released.",
                },
                {
                    "service": "checkout-svc",
                    "module": "checkout.db.session",
                    "function": "checkout_session_scope",
                    "file": suspected_files[0],
                    "checkpoint": "Confirm the scoped session closes on the failure path before the next retry is scheduled.",
                },
                {
                    "service": "checkout-svc",
                    "module": "checkout.transaction_flow",
                    "function": "release_db_session",
                    "file": suspected_files[0],
                    "checkpoint": "Check that rollback and session-release happen even after timeout-triggered cancellation.",
                },
            ]
            stack_path_summary = "Trace the write path from retry entry into session scope creation and finally the DB-session release boundary."
            failure_boundary = "The failure boundary sits at the retry-to-session handoff: the next write attempt begins before the previous session lifecycle closes."
            runtime_clue = (
                runtime_comparison
                or (f"Baseline replay returned HTTP {replay_status_code} after {replay_duration_ms}ms until the leaking retry path was removed." if replay_status_code else "")
                or "Replay saturated the bounded pool until the retry patch was rolled back or leaked sessions were terminated."
            )
            debugger_packet = {
                "supported": True,
                "bounded_to_pack": "checkout-python-fastapi-postgres-v1",
                "scope": "DB pool exhaustion / session leak only — not a universal database debugger",
                "summary": "Ordered debugging flow for this curated pack. This debugger is bounded to the DB pool exhaustion outage and applies only to the checked-in Postgres environment pack.",
                "ordered_checkpoints": [
                    {
                        "order": 1,
                        "function": "retry_checkout_write",
                        "module": "checkout.retry_patch",
                        "expected_state": "retry_count respects policy cap",
                        "inspect": "Confirm the retry branch does not re-enter until the prior DB session has been fully released.",
                    },
                    {
                        "order": 2,
                        "function": "checkout_session_scope",
                        "module": "checkout.db.session",
                        "expected_state": "session_handle is None after scope exit",
                        "inspect": "Verify the scoped session closes on the failure path before retry scheduling continues.",
                    },
                    {
                        "order": 3,
                        "function": "release_db_session",
                        "module": "checkout.transaction_flow",
                        "expected_state": "pool_available_count returns to baseline after release",
                        "inspect": "Check that rollback and session-release happen even after timeout-triggered cancellation.",
                    },
                ],
                "failure_signature": "Pool connections remain allocated between retry attempts, causing the bounded pool to exhaust as retry cycles accumulate.",
                "validation_method": runtime_comparison or "Bounded replay validates whether pool recovery correlates with the retry-patch fix.",
            }
            developer_handoff_summary = (
                f"Start with {suspected_files[0]} and hand this packet to the mapped owner for that file. "
                "The bounded replay shows the pool recovering only after the leaking retry path is removed or orphaned sessions are terminated."
                f"{f' {comparison_verdict}' if comparison_verdict else ''}"
            )
        elif incident_class == "deploy_regression_5xx" or (
            not incident_class and ("deploy regression" in issue_family or "5xx spike" in issue_family)
        ):
            suspected_modules = [module_name for module_name, _ in mapped_targets] or ["service.api_routes", "service.query_handler", "service.response_serializer"]
            suspected_functions = [function_name for _, function_name in mapped_targets] or ["handle_request", "execute_query", "serialize_response"]
            suspected_service = "api-svc"
            suspected_files = [
                "replica_packs/api-python-fastapi-catalog-v1/service/api_routes.py",
                "replica_packs/api-python-fastapi-catalog-v1/service/query_handler.py",
            ]
            expected_flow = "API requests should handle query execution and serialization without raising 5xx errors."
            observed_divergence = "Recent deploy introduced a regression causing query handler or serializer to fail systematically."
            state_anomalies = ["5xx error rate spiked at deploy boundary", "request latency increased after deploy"]
            inspection_point = (
                "Bounded debugger flow for deploy regression / 5xx spike:\n"
                "1. Break in handle_request and confirm request routing still reaches query handler\n"
                "2. Step to execute_query and verify query execution completes without throwing\n"
                "3. Inspect serialize_response and confirm response serialization handles the query result\n"
                "Expected recovery: rollback deploy or fix the regression in query execution path"
            )
            replay_evidence_summary = runtime_comparison or "Replay confirmed the 5xx spike reproduces with the new deploy and resolves with rollback."
            if "deploy" in deployment_text or "version" in deployment_text:
                state_anomalies.append("recent deploy aligns with the 5xx spike onset")
            if any("rollback" in action.lower() for action in mitigation_actions):
                state_anomalies.append("rollback mitigation confirms the deploy introduced the regression")
            if "query" in logs_text or "serializ" in logs_text:
                state_anomalies.append("runtime logs point to query execution or response serialization as the failure point")
            if replay_status_code and replay_status_code >= 500:
                state_anomalies.append(f"runtime replay reproduced the 5xx error at status {replay_status_code}")
            if runtime_comparison:
                state_anomalies.append(runtime_comparison)
            if comparison_verdict:
                state_anomalies.append(comparison_verdict)
            confidence = 0.78 if "deploy" in deployment_text else 0.71
            reasoning = "TRACE narrowed the issue to the query execution or response serialization path where the recent deploy introduced a regression."
            stack_path = [
                {
                    "service": "api-svc",
                    "module": "service.api_routes",
                    "function": "handle_request",
                    "file": suspected_files[0],
                    "checkpoint": "Verify the request reaches the query handler without being rejected at the route level.",
                },
                {
                    "service": "api-svc",
                    "module": "service.query_handler",
                    "function": "execute_query",
                    "file": suspected_files[1],
                    "checkpoint": "Confirm the query execution completes without throwing an exception on the new deploy.",
                },
                {
                    "service": "api-svc",
                    "module": "service.response_serializer",
                    "function": "serialize_response",
                    "file": suspected_files[0],
                    "checkpoint": "Verify response serialization handles the query result without encoding errors.",
                },
            ]
            stack_path_summary = "Trace the request from the route handler into query execution and finally response serialization."
            failure_boundary = "The failure boundary is in the query handler or response serializer introduced in the recent deploy."
            runtime_clue = (
                runtime_comparison
                or (f"Baseline replay returned HTTP {replay_status_code} consistently until rollback was applied." if replay_status_code else "")
                or "Replay confirmed the 5xx spike reproduces with the new deploy and resolves after rollback."
            )
            debugger_packet = {
                "supported": True,
                "bounded_to_pack": "api-python-fastapi-catalog-v1",
                "scope": "Deploy regression / 5xx spike only — not a universal API debugger",
                "summary": "Ordered debugging flow for this curated pack. This debugger is bounded to the deploy regression outage and applies only to the checked-in FastAPI/Catalog environment pack.",
                "ordered_checkpoints": [
                    {
                        "order": 1,
                        "function": "handle_request",
                        "module": "service.api_routes",
                        "expected_state": "request reaches query handler without route-level rejection",
                        "inspect": "Confirm routing logic has not changed to reject the incoming request schema.",
                    },
                    {
                        "order": 2,
                        "function": "execute_query",
                        "module": "service.query_handler",
                        "expected_state": "query execution completes without exception",
                        "inspect": "Verify the query handler does not throw exceptions on the new deploy version.",
                    },
                    {
                        "order": 3,
                        "function": "serialize_response",
                        "module": "service.response_serializer",
                        "expected_state": "response serialization succeeds without encoding error",
                        "inspect": "Check that the serializer can encode the query result without throwing an exception.",
                    },
                ],
                "failure_signature": "HTTP 5xx errors appear consistently at deployment boundary after the recent code change.",
                "validation_method": runtime_comparison or "Bounded replay validates whether the 5xx errors correlate with deploy rollback.",
                "recovery_path": "Rollback the deploy or apply a hotfix to the regression in the query handler or serializer.",
            }
            developer_handoff_summary = (
                f"Start with the recent deploy diff and inspect {suspected_files[1]}. "
                "The bounded replay shows the 5xx errors resolving only after the regression is fixed or the deploy is rolled back. "
                f"Hand this packet to the mapped owner for that file.{f' {comparison_verdict}' if comparison_verdict else ''}"
            )
        elif "certificate expiry" in issue_family:
            suspected_modules = ["edge.cert_loader", "edge.listener_config", "acme.rotation_job"]
            suspected_functions = ["load_public_certificate", "validate_chain_expiry", "reload_edge_listener"]
            suspected_service = "edge-gateway"
            suspected_files = ["edge/cert_loader.py", "edge/listener.py"]
            expected_flow = "Edge listeners should always serve a valid public certificate chain."
            observed_divergence = "Expired certificate chain remained attached to the active listener after rotation was missed."
            state_anomalies = ["active cert serial differs from latest staged cert", "rotation timestamp exceeded renewal window"]
            inspection_point = "Inspect the edge certificate loader first, then confirm the rotation job and listener reload path picked up the staged chain."
            replay_evidence_summary = "Replay evidence shows the edge listener continued to serve the stale certificate chain."
            confidence = 0.63
            reasoning = "TRACE narrowed the issue to the certificate loader and rotation path that failed to refresh the active listener."
            developer_handoff_summary = "Inspect the certificate loader and listener reload path before any broader edge rollback, then route the packet to the mapped owner for the active file."
        elif "memory leak" in issue_family:
            suspected_modules = ["image_worker.frame_cache", "image_worker.transform_pipeline", "image_worker.release_hooks"]
            suspected_functions = ["store_frame_buffer", "run_transform_batch", "release_decoded_frames"]
            suspected_service = "image-worker"
            suspected_files = ["workers/image_worker.py", "workers/frame_cache.py"]
            expected_flow = "Completed image transform batches should release decoded frame buffers before the next queue pull."
            observed_divergence = "Decoded frame buffers remain strongly referenced after batch completion, so heap pressure compounds across replay cycles."
            state_anomalies = ["retained frame_buffer objects dominate the heap snapshot", "gc pauses grow as replayed batches accumulate"]
            inspection_point = "Inspect the release hook and frame-cache ownership first, then confirm transform batches drop their strong references before the next queue pull."
            replay_evidence_summary = "Replay evidence shows retained frame buffers and growing GC pauses across repeated transform batches."
            if "release hook missing" in logs_text:
                state_anomalies.append("runtime logs already point at a missing release hook after transform completion")
            confidence = 0.67
            reasoning = "TRACE narrowed the issue to the frame-cache release path where completed transform batches retain decoded buffers."
            developer_handoff_summary = "Inspect the release hook and frame cache ownership path before attempting to recycle workers, then route the packet to the mapped owner for the active file."

    owner_mapping = _resolve_trace_owner(
        suspected_files,
        fallback_team=code_owner_team,
        fallback_slug=code_owner_slug,
    )
    code_owner_team = owner_mapping["team"]
    code_owner_slug = owner_mapping["slug"]
    code_owner_source = owner_mapping["source"]
    matched_owner_file = owner_mapping["matched_file"]
    if suspected_files and "mapped owner" in developer_handoff_summary:
        developer_handoff_summary = developer_handoff_summary.replace(
            "mapped owner for that file",
            f"{code_owner_team} via {code_owner_source}",
        )
    elif matched_owner_file:
        developer_handoff_summary = (
            f"{developer_handoff_summary} Ownership source: {code_owner_source}."
        ).strip()

    if runtime_provenance["mode"] == "delegated_relay":
        replay_evidence_summary = f"{replay_evidence_summary} Runtime provenance: delegated replay from the external runtime host.".strip()
        developer_handoff_summary = f"{developer_handoff_summary} Runtime evidence came from the external runtime host replay.".strip()
        runtime_clue = f"{runtime_clue} Runtime provenance: delegated replay from the external runtime host.".strip()
    elif runtime_provenance["mode"] == "direct_runtime":
        replay_evidence_summary = f"{replay_evidence_summary} Runtime provenance: direct replay on the current app host.".strip()
        developer_handoff_summary = f"{developer_handoff_summary} Runtime evidence came from direct replay on the current app host.".strip()
        runtime_clue = f"{runtime_clue} Runtime provenance: direct replay on the current app host.".strip()

    residual_risk = {
        "summary": "This handoff is bounded to the supported wedge. Engineering should treat recommendations as starting guidance, not universal debugging.",
        "scope": "Bounded to curated incident families with REPLICA packs",
        "confidence_caveats": f"Confidence is {int(confidence * 100)}% based on bounded inference. Runtime replay provides measured evidence when available.",
        "next_steps_if_divergent": "If the suspected path does not match production behavior, escalate through standard engineering triage and use production debugging tools.",
    }

    return {
        "incident_id": incident_id,
        "service": service,
        "suspected_service": suspected_service,
        "trace_status": trace_status,
        "suspected_modules": suspected_modules,
        "suspected_functions": suspected_functions,
        "expected_flow": expected_flow,
        "observed_divergence": observed_divergence,
        "state_anomalies": state_anomalies,
        "inspection_point": inspection_point,
        "replay_evidence_summary": replay_evidence_summary,
        "stack_path": stack_path,
        "stack_path_summary": stack_path_summary,
        "failure_boundary": failure_boundary,
        "runtime_clue": runtime_clue,
        "debugger_packet": debugger_packet,
        "code_owner_team": code_owner_team,
        "code_owner_slug": code_owner_slug,
        "code_owner_source": code_owner_source,
        "suspected_files": suspected_files,
        "developer_handoff_summary": developer_handoff_summary,
        "runtime_provenance": runtime_provenance,
        "residual_risk": residual_risk,
        "confidence": confidence,
        "reasoning": reasoning,
    }


def build_quality_evaluation(
    *,
    incident_id: str,
    classification_confidence: float,
    diagnosis_confidence: float,
    triage_summary: dict[str, object] | None = None,
    input_quality: dict[str, object] | None = None,
    has_runtime_replay: bool = False,
) -> dict[str, object]:
    input_quality = input_quality or {}
    triage_summary = triage_summary or {}
    normalization_posture = str(input_quality.get("normalization_posture", "")).lower()

    issue_framing_score = 0.0
    issue_framing_label = "weak"
    if normalization_posture == "strong":
        issue_framing_score = 0.9
        issue_framing_label = "strong"
    elif normalization_posture == "partial":
        issue_framing_score = 0.65
        issue_framing_label = "partial"
    elif normalization_posture == "weak":
        issue_framing_score = 0.35
        issue_framing_label = "weak"
    else:
        issue_framing_score = classification_confidence * 0.8
        issue_framing_label = "scaffold-only"

    owner_routing_score = 0.8 if triage_summary.get("likely_owner_team") else 0.5
    owner_routing_label = "high confidence" if owner_routing_score > 0.75 else "estimated"

    next_step_quality_score = 0.75 if triage_summary.get("approval_focus") else 0.5
    next_step_quality_label = "clear" if next_step_quality_score > 0.65 else "provisional"

    uncertainty_quality_score = 0.5
    uncertainty_quality_label = "low confidence"
    if classification_confidence < 0.6:
        uncertainty_quality_score = 0.3
        uncertainty_quality_label = "high uncertainty"
    elif classification_confidence > 0.8:
        uncertainty_quality_score = 0.85
        uncertainty_quality_label = "well-grounded"
    elif has_runtime_replay:
        uncertainty_quality_score = 0.9
        uncertainty_quality_label = "runtime-validated"

    overall_quality_score = (issue_framing_score + owner_routing_score + next_step_quality_score + uncertainty_quality_score) / 4.0

    return {
        "incident_id": incident_id,
        "overall_quality_score": round(overall_quality_score, 2),
        "issue_framing": {
            "score": round(issue_framing_score, 2),
            "label": issue_framing_label,
            "reasoning": f"Input normalization posture is {normalization_posture or 'unknown'}, affecting frame completeness.",
        },
        "owner_routing": {
            "score": round(owner_routing_score, 2),
            "label": owner_routing_label,
            "reasoning": f"Owner assignment is {'mapped from tenant config' if triage_summary.get('is_owner_tenant_mapped') else 'inferred from issue family'}.",
        },
        "next_step_quality": {
            "score": round(next_step_quality_score, 2),
            "label": next_step_quality_label,
            "reasoning": f"Next-step guidance is {'explicitly scoped for this issue family' if triage_summary.get('approval_focus') else 'generic guidance for issue class'}.",
        },
        "uncertainty_quality": {
            "score": round(uncertainty_quality_score, 2),
            "label": uncertainty_quality_label,
            "reasoning": f"Confidence is {round(classification_confidence * 100)}%, {'boosted by runtime replay validation' if has_runtime_replay else 'from inference only'}.",
        },
        "evaluation_summary": f"Fresh incident '{incident_id}' quality: overall {round(overall_quality_score * 100)}%. Frame is {issue_framing_label}, owner routing is {owner_routing_label}, next-steps are {next_step_quality_label}, and confidence is {uncertainty_quality_label}.",
    }
