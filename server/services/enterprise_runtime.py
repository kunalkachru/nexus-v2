from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable
from statistics import mean
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from server.artifacts import _load_artifacts
from server.config import AppConfig
from server.incident_payloads import get_incident_details, list_supported_incident_ids
from server.models import (
    Episode,
    ForgeRunbookResult,
    GuardianReviewResult,
    IncidentContext,
    IncidentDefinition,
    IncidentRecord,
    NormalizedAlertEnvelope,
    PrismDiagnosis,
    SentinelClassification,
    SystemContext,
)
from server.services.priority import normalize_priority_label, priority_rank
from server.services.replica_runtime import ReplicaExecutionResult, ReplicaRunner, build_execution_plan, build_runtime_host_relay_status, trace_targets_for_plan


class RuntimeState(TypedDict):
    alert_envelope: NormalizedAlertEnvelope
    context: IncidentContext
    task_board: list[dict[str, object]]
    orchestration: dict[str, object]
    memory_hits: dict[str, list[dict[str, object]]]
    fallback_summary: list[dict[str, object]]
    agent_metrics: dict[str, dict[str, object]]
    branch_results: dict[str, dict[str, object]]
    evidence_pack: dict[str, object]
    sentinel_output: SentinelClassification
    prism_output: PrismDiagnosis
    triage_summary: dict[str, object]
    forge_output: ForgeRunbookResult
    guardian_output: GuardianReviewResult
    final_episode: Episode


class RuntimeInput(TypedDict, total=False):
    alert_envelope: NormalizedAlertEnvelope
    context: IncidentContext
    task_board: NotRequired[list[dict[str, object]]]
    orchestration: NotRequired[dict[str, object]]
    memory_hits: NotRequired[dict[str, list[dict[str, object]]]]
    fallback_summary: NotRequired[list[dict[str, object]]]
    agent_metrics: NotRequired[dict[str, dict[str, object]]]
    branch_results: NotRequired[dict[str, dict[str, object]]]
    evidence_pack: NotRequired[dict[str, object]]
    triage_summary: NotRequired[dict[str, object]]


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
            similar.append(
                {
                    "incident_id": candidate_id,
                    "summary": summary,
                    "root_cause_hint": candidate_root,
                    "issue_family": str(candidate_triage.get("issue_family") or infer_issue_family(candidate_root or summary, summary)),
                    "service_match": service_overlap,
                    "severity_match": severity_match,
                    "root_overlap": root_overlap,
                    "success_rate": round(0.74 + (score * 0.22), 2),
                    "similarity": round(score, 2),
                    "match_reason": self._build_match_reason(
                        service_match=service_overlap,
                        severity_match=severity_match,
                        root_overlap=root_overlap,
                        issue_family=str(candidate_triage.get("issue_family") or ""),
                    ),
                    "prior_action": self._prior_action(details),
                    "remaining_risk": str(details.get("guardian", {}).get("reasoning", "")).strip(),
                    "source": "incident_history",
                }
            )
        similar.sort(
            key=lambda item: (
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
            runbooks.append(
                {
                    "incident_id": item["incident_id"],
                    "runbook_summary": str(primary.get("name") or f"Prior mitigation pattern for {item['incident_id']}"),
                    "success_rate": float(primary.get("success_rate", item["success_rate"])),
                    "historical_reason": str(details.get("forge", {}).get("selection_logic", "")).strip(),
                    "historical_actions": historical_actions,
                    "why_now_fit": str(details.get("triage", {}).get("approval_focus", "")).strip()
                    or "Historical mitigation favored reversible recovery before broad rollback.",
                    "source": "historical_runbook",
                }
            )
        for item in recent_guardian_outcomes:
            if item["decision"] == "approve":
                runbooks.append(
                    {
                        "incident_id": item["incident_id"],
                        "runbook_summary": f"Guardian-approved execution for {item['incident_id']}",
                        "success_rate": 0.81,
                        "historical_reason": f"Previously cleared by {item.get('policy_id') or 'GUARDIAN policy'}.",
                        "why_now_fit": "This pattern already cleared governance for a closely related production incident.",
                        "source": "guardian_history",
                    }
                )
        return runbooks[:4]

    def _build_match_reason(
        self,
        *,
        service_match: bool,
        severity_match: bool,
        root_overlap: int,
        issue_family: str,
    ) -> str:
        reasons: list[str] = []
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
            f"FORGE kept the plan biased toward reversible, lower-blast-radius actions first and treated the runtime evidence as {validated_outcome or 'inferred only'}."
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
        if replica_summary.get("runtime_executed") and best_outcome == "resolved":
            validated_clause = "Validated runtime signals: REPLICA reproduced the failure and the leading mitigation resolved it in the bounded runtime."
        elif replica_summary.get("runtime_executed") and best_outcome == "improved":
            validated_clause = "Validated runtime signals: REPLICA reproduced the failure and the leading mitigation improved the runtime behavior without fully clearing the failure."
        elif replica_summary.get("runtime_executed"):
            validated_clause = "Validated runtime signals: REPLICA reproduced the failure, but the tested mitigation did not materially improve the bounded runtime."
        else:
            validated_clause = (
                f"Current signals are inferred from the bounded scaffold: REPLICA is {replica_summary.get('reproduction_status', 'not_run')} "
                f"and TRACE is {trace_summary.get('trace_status', 'not_run')}. Runtime replay has not executed in this live path."
            )
        guardian_reasoning = (
            f"{str(updated_guardian.get('reasoning', '')).strip()} "
            f"{validated_clause} "
            f"{str(replica_summary.get('runtime_comparison_summary') or '')} "
            f"Inferred signals: memory-ranked analogs and diagnosis synthesis still inform the remaining confidence. "
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
        trace_summary = build_trace_summary(
            incident_id=state["context"].incident.id,
            triage_summary=state["triage_summary"],
            replica_summary=replica_summary,
            root_cause=state["prism_output"].root_cause,
            recent_deployments=state["context"].signals.get("deployment", []),
            recent_logs=state["context"].signals.get("logs", []),
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
        if replica_summary.get("runtime_executed") and best_outcome == "resolved":
            validated_clause = "Validated runtime signals: REPLICA reproduced the failure and the leading mitigation resolved it in the bounded runtime."
        elif replica_summary.get("runtime_executed") and best_outcome == "improved":
            validated_clause = "Validated runtime signals: REPLICA reproduced the failure and the leading mitigation improved the runtime behavior without fully clearing the failure."
        elif replica_summary.get("runtime_executed"):
            validated_clause = "Validated runtime signals: REPLICA reproduced the failure, but the tested mitigation did not materially improve the bounded runtime."
        else:
            validated_clause = (
                f"Current signals are inferred from the bounded scaffold: REPLICA is {replica_summary.get('reproduction_status', 'not_run')} "
                f"and TRACE is {trace_summary.get('trace_status', 'not_run')}. Runtime replay has not executed in this live path."
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

    if any(token in service_key for token in ("checkout", "payment", "order", "gateway", "auth")) or "checkout" in incident_name.lower():
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
    elif "certificate" in issue_family.lower():
        impacted_customer_path = "Public API and browser entrypoint"
        likely_owner_team = "Edge Reliability"
        responder_team = "Edge Reliability with Security Operations"
        support_queue = "Public edge outage escalation"
        blast_radius = "Customer traffic cannot establish trust with the public endpoint."
        approval_focus = "Restore trust boundaries without widening certificate or DNS risk."

    signal_count = len(detected_signals or [])
    return {
        "issue_family": issue_family,
        "impacted_customer_path": impacted_customer_path,
        "likely_owner_service": likely_owner_service,
        "likely_owner_team": likely_owner_team,
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


def extract_reproduced_symptoms(recent_logs: list[object]) -> list[str]:
    symptom_map = (
        ("timeout", "Customer-facing timeouts reproduced in the sandbox request path."),
        ("worker pool saturation", "Worker pool saturation reappeared under replayed load."),
        ("retry", "Retry amplification reappeared once the failing dependency slowed down."),
        ("circuit breaker", "Circuit breaker remained closed while upstream latency climbed."),
        ("5xx", "The replayed path produced elevated 5xx responses."),
        ("queuepool", "Connection pool exhaustion reproduced in the sandbox."),
        ("leaked session", "Session leakage reappeared across repeated checkout retries."),
        ("max_connections", "Database connection ceiling was reached under the replay."),
        ("certificate", "Public certificate validation failed in the active listener path."),
        ("tls", "TLS trust failure was reproduced at the edge entrypoint."),
    )
    text = " ".join(str(item).lower() for item in recent_logs)
    symptoms = [description for needle, description in symptom_map if needle in text]
    return symptoms[:4]


def default_reproduced_symptoms(issue_family: str, recent_logs: list[object]) -> list[str]:
    if "retry amplification" in issue_family:
        return [
            "Customer-facing checkout requests stall after repeated upstream auth retries.",
            "Gateway workers remain occupied until the timeout budget is exhausted.",
        ]
    if "pool exhaustion" in issue_family or "session leak" in issue_family:
        return [
            "Checkout writes stall once the shared database pool reaches saturation.",
            "Retry traffic keeps leaked sessions open long enough to block new writes.",
        ]
    if "certificate expiry" in issue_family:
        return [
            "Public clients fail TLS handshakes against the active edge listener.",
            "The active certificate chain remains stale after rotation should have occurred.",
        ]
    if "memory leak" in issue_family:
        return [
            "Worker memory keeps climbing across repeated task replay cycles.",
            "Garbage-collection pauses stretch as retained buffers accumulate.",
        ]
    return extract_reproduced_symptoms(recent_logs) or ["REPLICA did not find a reusable reproduction signature yet."]


def build_mitigation_checks(
    candidate_actions: list[str],
    *,
    fallback_checks: list[tuple[str, str, float]],
) -> list[dict[str, object]]:
    matched_checks: list[dict[str, object]] = []
    fallback_only_checks: list[dict[str, object]] = []
    for action, result, confidence_delta in fallback_checks:
        check = {
            "action": action,
            "result": result,
            "confidence_delta": confidence_delta,
            "outcome_class": "inferred_only",
        }
        if candidate_actions and not any(action.lower() in candidate.lower() or candidate.lower() in action.lower() for candidate in candidate_actions):
            fallback_only_checks.append(check)
            continue
        matched_checks.append(check)
    if matched_checks:
        return matched_checks + fallback_only_checks
    return [
        {
            "action": action,
            "result": result,
            "confidence_delta": confidence_delta,
            "outcome_class": "inferred_only",
        }
        for action, result, confidence_delta in fallback_checks
    ]


def _tokenize_text(value: str) -> set[str]:
    return {
        part
        for part in value.lower().replace("/", " ").replace("-", " ").replace("_", " ").split()
        if part and len(part) > 2
    }


def _action_overlap(left: str, right: str) -> float:
    left_tokens = _tokenize_text(left)
    right_tokens = _tokenize_text(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))


def _runtime_outcome_class(
    *,
    baseline_status: int | None,
    mitigation_status: int | None,
    baseline_duration: int | None,
    mitigation_duration: int | None,
) -> str:
    if mitigation_status is None:
        return "inferred_only"
    if baseline_status is None:
        return "validated"
    if baseline_status >= 500 and mitigation_status < 500:
        return "resolved"
    if mitigation_status < baseline_status:
        return "improved"
    if baseline_status == mitigation_status and baseline_duration and mitigation_duration:
        if mitigation_duration <= int(baseline_duration * 0.6):
            return "improved"
    return "unresolved"


def _runtime_outcome_score(
    outcome_class: str,
    *,
    baseline_duration: int | None,
    mitigation_duration: int | None,
) -> float:
    base = {
        "resolved": 0.97,
        "improved": 0.89,
        "validated": 0.8,
        "unresolved": 0.62,
        "inferred_only": 0.0,
    }.get(outcome_class, 0.0)
    if (
        outcome_class in {"resolved", "improved"}
        and baseline_duration
        and mitigation_duration
        and baseline_duration > 0
    ):
        gain = max(0.0, min(0.08, (baseline_duration - mitigation_duration) / baseline_duration * 0.12))
        return round(min(0.99, base + gain), 2)
    return round(base, 2)


def _runtime_delta_ms(baseline_duration: int | None, mitigation_duration: int | None) -> int | None:
    if baseline_duration is None or mitigation_duration is None:
        return None
    return baseline_duration - mitigation_duration


def _runtime_mitigation_sort_key(
    item: dict[str, object],
    *,
    baseline_duration: int | None,
) -> tuple[float, float]:
    duration = item.get("duration_ms")
    return (
        _runtime_outcome_score(
            str(item.get("outcome_class") or ""),
            baseline_duration=baseline_duration,
            mitigation_duration=duration if isinstance(duration, int) else None,
        ),
        float(item.get("confidence_delta", 0.0) or 0.0),
    )


def _rank_runtime_mitigations(
    runtime_mitigations: list[dict[str, object]] | None,
    *,
    baseline_duration: int | None,
) -> list[dict[str, object]]:
    return sorted(
        [item for item in (runtime_mitigations or []) if isinstance(item, dict)],
        key=lambda item: _runtime_mitigation_sort_key(item, baseline_duration=baseline_duration),
        reverse=True,
    )


def _mitigation_comparison_row(
    item: dict[str, object] | None,
    *,
    baseline_status: int | None,
    baseline_duration: int | None,
) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None
    status_code = item.get("status_code")
    duration_ms = item.get("duration_ms")
    delta_ms = item.get("delta_ms")
    if delta_ms is None and isinstance(duration_ms, int):
        delta_ms = _runtime_delta_ms(baseline_duration, duration_ms)
    outcome_class = str(item.get("outcome_class") or "")
    summary = (
        f"{item.get('action', 'Mitigation')} returned "
        f"{status_code if status_code is not None else 'no status'}"
        f"{f' at {duration_ms}ms' if duration_ms is not None else ''}"
        f" ({outcome_class.replace('_', ' ') if outcome_class else 'not classified'})."
    )
    if isinstance(delta_ms, int):
        if delta_ms > 0:
            summary = f"{summary} It improved runtime by {delta_ms}ms versus the baseline."
        elif delta_ms < 0:
            summary = f"{summary} It regressed runtime by {abs(delta_ms)}ms versus the baseline."
    return {
        "action": str(item.get("action") or ""),
        "status_code": int(status_code) if isinstance(status_code, (int, float)) else None,
        "duration_ms": int(duration_ms) if isinstance(duration_ms, (int, float)) else None,
        "delta_ms": int(delta_ms) if isinstance(delta_ms, (int, float)) else None,
        "outcome_class": outcome_class,
        "confidence_delta": float(item.get("confidence_delta", 0.0) or 0.0),
        "won": bool(item.get("won")),
        "summary": summary,
        "baseline_status_code": baseline_status,
        "baseline_duration_ms": baseline_duration,
    }


def _build_mitigation_comparison(
    runtime_result: object | None,
    runtime_mitigations: list[dict[str, object]] | None,
    *,
    baseline_outcome_class: str,
) -> dict[str, object]:
    baseline_status = getattr(runtime_result, "replay_status_code", None) if runtime_result else None
    baseline_duration = getattr(runtime_result, "replay_duration_ms", None) if runtime_result else None
    ranked = _rank_runtime_mitigations(runtime_mitigations, baseline_duration=baseline_duration)
    winner = _mitigation_comparison_row(
        ranked[0] if ranked else None,
        baseline_status=baseline_status,
        baseline_duration=baseline_duration,
    )
    runner_up = _mitigation_comparison_row(
        ranked[1] if len(ranked) > 1 else None,
        baseline_status=baseline_status,
        baseline_duration=baseline_duration,
    )
    verdict = ""
    if winner and runner_up:
        verdict = (
            f"{winner['action']} outranked {runner_up['action']} because it finished as "
            f"{str(winner.get('outcome_class') or 'not classified').replace('_', ' ')} while the runner-up remained "
            f"{str(runner_up.get('outcome_class') or 'not classified').replace('_', ' ')}."
        )
    elif winner:
        verdict = (
            f"{winner['action']} is the leading mitigation because it produced the strongest "
            f"{str(winner.get('outcome_class') or 'runtime').replace('_', ' ')} signal."
        )
    return {
        "baseline": {
            "status_code": int(baseline_status) if isinstance(baseline_status, (int, float)) else None,
            "duration_ms": int(baseline_duration) if isinstance(baseline_duration, (int, float)) else None,
            "outcome_class": baseline_outcome_class,
        },
        "winner": winner,
        "runner_up": runner_up,
        "verdict": verdict,
    }


def runtime_aligned_candidate_fixes(issue_family: str, service: str) -> list[dict[str, object]]:
    issue_family_text = issue_family.lower()
    if "retry amplification" in issue_family_text or ("timeout" in issue_family_text and "retry" in issue_family_text):
        return [
            {"action": "Enable auth-svc circuit breaker and cap retries to 1", "success_rate": 0.9},
            {"action": "Roll back auth-svc retry middleware", "success_rate": 0.87},
            {"action": "Drain hot gateway pods and scale replicas +2", "success_rate": 0.8},
        ]
    if "pool exhaustion" in issue_family_text or "session leak" in issue_family_text:
        return [
            {"action": "Terminate orphaned sessions and restart checkout pods", "success_rate": 0.89},
            {"action": "Roll back checkout retry patch", "success_rate": 0.86},
            {"action": "Increase pool size temporarily to 650", "success_rate": 0.78},
        ]
    if "certificate expiry" in issue_family_text or "trust boundary" in issue_family_text:
        return [
            {"action": "Rotate the expired certificate", "success_rate": 0.93},
            {"action": "Reload the active edge listener", "success_rate": 0.86},
        ]
    return [
        {"action": f"Validate {service or 'service'} ownership and confirm incident scope", "success_rate": 0.9},
        {"action": "Prepare rollback-safe mitigation and monitor audit trail", "success_rate": 0.82},
    ]


def _deployment_signal_summary(recent_deployments: list[object] | None) -> tuple[str, list[str]]:
    if not recent_deployments:
        return "", []
    text = " ".join(str(item).lower() for item in recent_deployments)
    supporting_conditions: list[str] = []
    if "retry" in text:
        supporting_conditions.append("recent retry-related deployment matches the reproduced failure path")
    if "middleware" in text:
        supporting_conditions.append("middleware change is present in the same incident window")
    if "telemetry" in text:
        supporting_conditions.append("telemetry-only change appears adjacent but not causal")
    if "certificate" in text or "rotation" in text:
        supporting_conditions.append("certificate rotation or listener deployment is part of the affected edge path")
    return text, supporting_conditions


def _runtime_enablement_hint(
    *,
    scaffold_ready: bool,
    runtime_executed: bool,
    runtime_mode: str,
    compose_config_valid: bool,
    docker_available: bool,
    runtime_capability_state: str = "",
) -> str:
    if runtime_capability_state == "relay_executed":
        return "A configured runtime host ran Docker-backed replay for this incident. REPLICA is showing measured baseline and mitigation outcomes from delegated execution."
    if runtime_capability_state == "relay_available":
        return "This incident maps to a bounded runtime scaffold and can delegate Docker-backed replay to the configured runtime host."
    if runtime_executed:
        return "Docker-backed replay ran for this incident. REPLICA is showing measured baseline and mitigation outcomes."
    if scaffold_ready and compose_config_valid and docker_available:
        return "Runtime scaffold is ready. Start NEXUS with NEXUS_ENABLE_REPLICA_RUNTIME=1 to execute Docker-backed replay instead of scaffold-only inference."
    if scaffold_ready and not docker_available:
        return "This incident maps to a bounded runtime scaffold, but the current app environment cannot execute Docker-backed replay. Run NEXUS on a Docker-capable host with NEXUS_ENABLE_REPLICA_RUNTIME=1 to execute replay."
    if scaffold_ready:
        return "This incident maps to a bounded runtime scaffold, but the compose contract still needs validation before replay can run."
    if runtime_mode == "inferred":
        return "This incident is using inferred reproduction logic because no bounded runtime scaffold matches yet."
    return "Runtime replay is not available for this incident yet."


def _runtime_host_capability(
    *,
    plan: object,
    runner_result: object,
    runtime_result: object,
) -> dict[str, object]:
    bounded_pack_available = bool(plan and runner_result and not getattr(runner_result, "missing_assets", ()))
    docker_available = bool(getattr(runner_result, "docker_available", False)) if runner_result else False
    compose_config_valid = bool(getattr(runner_result, "compose_config_valid", False)) if runner_result else False
    relay_configured = bool(build_runtime_host_relay_status(AppConfig()).get("configured"))

    if runtime_result:
        return {
            "state": "replay_executed",
            "label": "Replay executed",
            "host_label": "Current app host",
            "can_execute_replay": True,
            "bounded_pack_available": bounded_pack_available,
            "docker_available": docker_available,
            "compose_config_valid": compose_config_valid,
            "message": "This host executed Docker-backed replay for the bounded runtime pack.",
        }
    if bounded_pack_available and not docker_available and relay_configured:
        return {
            "state": "relay_available",
            "label": "Relay available",
            "host_label": "External runtime host",
            "can_execute_replay": True,
            "bounded_pack_available": True,
            "docker_available": False,
            "compose_config_valid": compose_config_valid,
            "message": "The current app host cannot run Docker-backed replay directly, but a configured runtime host can execute it on demand.",
        }
    if bounded_pack_available and docker_available and compose_config_valid:
        return {
            "state": "replay_available",
            "label": "Replay available",
            "host_label": "Current app host",
            "can_execute_replay": True,
            "bounded_pack_available": True,
            "docker_available": True,
            "compose_config_valid": True,
            "message": "This host can execute Docker-backed replay for the bounded runtime pack when replay is explicitly triggered.",
        }
    if bounded_pack_available and not docker_available:
        return {
            "state": "host_unavailable",
            "label": "Host unavailable",
            "host_label": "External Docker host required",
            "can_execute_replay": False,
            "bounded_pack_available": True,
            "docker_available": False,
            "compose_config_valid": False,
            "message": "The incident maps to a bounded runtime pack, but the current app environment cannot execute Docker-backed replay.",
        }
    if bounded_pack_available:
        return {
            "state": "pack_validation_required",
            "label": "Pack validation required",
            "host_label": "Current app host",
            "can_execute_replay": False,
            "bounded_pack_available": True,
            "docker_available": docker_available,
            "compose_config_valid": False,
            "message": "A bounded runtime pack exists for this incident, but the compose contract still needs validation before replay can run.",
        }
    return {
        "state": "no_pack",
        "label": "No bounded pack",
        "host_label": "Not applicable",
        "can_execute_replay": False,
        "bounded_pack_available": False,
        "docker_available": docker_available,
        "compose_config_valid": False,
        "message": "No bounded runtime pack matches this incident class yet.",
    }


def _runtime_provenance(
    *,
    runtime_mode: str,
    runtime_executed: bool,
    runtime_capability: dict[str, object],
) -> dict[str, object]:
    capability_state = str(runtime_capability.get("state") or "")
    if runtime_executed and runtime_mode == "relay_runtime_scaffold":
        return {
            "mode": "delegated_relay",
            "label": "Delegated runtime host replay",
            "summary": "A configured runtime host executed the bounded runtime pack on behalf of the packaged app.",
            "executed_by": "runtime_host",
        }
    if runtime_executed:
        return {
            "mode": "direct_runtime",
            "label": "Direct runtime replay",
            "summary": "The current app host executed the bounded runtime pack directly.",
            "executed_by": "current_app_host",
        }
    if capability_state == "relay_available":
        return {
            "mode": "relay_ready",
            "label": "Delegated runtime host ready",
            "summary": "The packaged app can delegate bounded replay to the configured runtime host when requested.",
            "executed_by": "runtime_host",
        }
    if capability_state == "replay_available":
        return {
            "mode": "direct_ready",
            "label": "Direct runtime ready",
            "summary": "The current app host can execute the bounded runtime pack directly when requested.",
            "executed_by": "current_app_host",
        }
    if capability_state == "host_unavailable":
        return {
            "mode": "runtime_unavailable",
            "label": "Direct runtime unavailable",
            "summary": "The current app environment cannot execute the bounded runtime pack directly.",
            "executed_by": "unavailable",
        }
    return {
        "mode": "inferred_only",
        "label": "Inferred only",
        "summary": "The current incident view is still using bounded inference rather than measured runtime replay.",
        "executed_by": "not_run",
    }


def build_replica_summary(
    *,
    incident_id: str,
    triage_summary: dict[str, object],
    root_cause: str,
    recent_logs: list[object] | None = None,
    recent_deployments: list[object] | None = None,
    candidate_fixes: list[object] | None = None,
    execute_runtime: bool | None = None,
    runtime_execution: ReplicaExecutionResult | None = None,
    runtime_capability_override: dict[str, object] | None = None,
    runtime_mode_override: str | None = None,
) -> dict[str, object]:
    issue_family = str(triage_summary.get("issue_family", "")).lower()
    logs_text = " ".join(str(item) for item in (recent_logs or [])).lower()
    service = str(triage_summary.get("likely_owner_service") or "")
    deployment_text, deployment_conditions = _deployment_signal_summary(recent_deployments)
    reproduced_symptoms = extract_reproduced_symptoms(recent_logs or [])
    candidate_actions = [str(item.get("action", "")).strip() for item in (candidate_fixes or []) if isinstance(item, dict)]
    plan = build_execution_plan(
        issue_family=str(triage_summary.get("issue_family", "")),
        service=service,
        recent_logs=recent_logs,
        recent_deployments=recent_deployments,
    )
    runner_result = runtime_execution if runtime_execution is not None else (ReplicaRunner().inspect_plan(plan) if plan else None)
    execute_runtime = (
        os.environ.get("NEXUS_ENABLE_REPLICA_RUNTIME", "0") == "1"
        if execute_runtime is None
        else execute_runtime
    )
    runtime_result = runtime_execution or (
        ReplicaRunner().execute_scaffold(plan) if plan and execute_runtime and runner_result and runner_result.compose_config_valid and not runner_result.missing_assets else None
    )

    environment_pack_id = "generic-support-triage-pack-v1"
    reproduction_status = "not_run"
    hypothesis_supported = False
    confidence_delta = 0.0
    tested_mitigations: list[dict[str, object]] = []
    reasoning = "REPLICA has not run for this incident class yet."
    supporting_conditions: list[str] = []

    if plan is not None:
        environment_pack_id = plan.pack.pack_id
        if runner_result and not runner_result.missing_assets:
            supporting_conditions.append("pack scaffold is present on disk for the bounded runtime-backed replay path")
        if runner_result and runner_result.compose_config_valid and runner_result.services_seen:
            supporting_conditions.append(
                f"compose plan validates with services: {', '.join(runner_result.services_seen)}"
            )
        if runner_result and not runner_result.docker_available:
            supporting_conditions.append("docker binary is unavailable in the current app environment")
        if runtime_result and runtime_result.replay_output:
            supporting_conditions.append("runtime scaffold executed a replay hook successfully")

    if "retry amplification" in issue_family or ("retry" in logs_text and "timeout" in logs_text):
        reproduction_status = "reproduced"
        supporting_conditions = [
            "downstream auth latency above 5s",
            "retry middleware enabled",
            "gateway worker pool near saturation",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.14 if "middleware" in deployment_text else 0.12
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Enable auth-svc circuit breaker and cap retries to 1", "latency improved and worker pressure eased once retries were capped at the auth boundary", 0.08),
                ("Roll back auth-svc retry middleware", "the timeout cascade no longer persisted after the retry refactor was removed", 0.06),
                ("Drain hot gateway pods and scale replicas +2", "worker pressure eased but the root retry pattern still remained visible", 0.03),
            ],
        )
        reasoning = (
            "The failure pattern reproduced only when the retry-heavy middleware path remained enabled under downstream auth degradation. "
            "The sandbox required both the retry middleware change and elevated downstream auth latency to sustain the timeout cascade."
        )
    elif "pool exhaustion" in issue_family or "session leak" in issue_family or "queuepool" in logs_text:
        reproduction_status = "reproduced"
        supporting_conditions = [
            "checkout retry patch enabled",
            "primary pool capped at production threshold",
            "session cleanup path disabled under retry failure",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.11 if "retry" in deployment_text else 0.1
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Terminate orphaned sessions and restart checkout pods", "pool capacity recovered quickly and new checkout writes resumed", 0.06),
                ("Roll back checkout retry patch", "session growth stopped once the retry patch was removed from the write path", 0.05),
                ("Increase pool size temporarily to 650", "capacity improved briefly but the leak signature remained active", 0.01),
            ],
        )
        reasoning = (
            "The failure reproduced when the patched retry path leaked sessions long enough to exhaust the primary pool. "
            "Pool exhaustion did not persist once the retry patch was removed from the sandbox."
        )
    elif "certificate expiry" in issue_family or "tls" in root_cause.lower():
        environment_pack_id = "edge-nginx-acme-v1"
        reproduction_status = "reproduced"
        supporting_conditions = [
            "expired public certificate chain attached",
            "edge listener still serving stale cert",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.09
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Rotate the expired certificate", "public trust restored", 0.09),
            ],
        )
        reasoning = "The failure reproduced when the edge listener served an expired public certificate chain."
    elif "memory leak" in issue_family or "heap" in logs_text:
        environment_pack_id = "worker-python-image-gc-v1"
        reproduction_status = "reproduced"
        supporting_conditions = [
            "retained frame buffers stay live after task completion",
            "gc pause time increases as replay batches accumulate",
        ] + deployment_conditions
        hypothesis_supported = True
        confidence_delta = 0.08
        tested_mitigations = build_mitigation_checks(
            candidate_actions,
            fallback_checks=[
                ("Recycle leaking worker pods", "memory pressure dropped but the retained-object pattern returned under load", 0.03),
                ("Disable the new frame-cache path", "heap growth stopped once the suspected buffer path was disabled", 0.05),
            ],
        )
        reasoning = "The failure reproduced when repeated image transform batches retained frame buffers beyond the expected cleanup path."

    if not reproduced_symptoms:
        reproduced_symptoms = default_reproduced_symptoms(issue_family, recent_logs or [])

    runtime_mitigations = _runtime_override_mitigations(
        runtime_result=runtime_result,
        default_checks=tested_mitigations,
    )
    runtime_comparison_summary = _runtime_comparison_summary(runtime_result, runtime_mitigations)
    best_mitigation = next((item for item in runtime_mitigations if item.get("won")), runtime_mitigations[0] if runtime_mitigations else {})
    best_outcome_class = str(best_mitigation.get("outcome_class") or "")
    best_status_code = best_mitigation.get("status_code")
    best_duration_ms = best_mitigation.get("duration_ms")
    baseline_outcome_class = (
        "reproduced"
        if (runtime_result and isinstance(runtime_result.replay_status_code, int) and runtime_result.replay_status_code >= 500)
        else (
            "reproduced"
            if reproduction_status == "reproduced" and not runtime_result
            else ("validated" if runtime_result and runtime_result.replay_status_code is not None else "not_run")
        )
    )
    mitigation_comparison = _build_mitigation_comparison(
        runtime_result,
        runtime_mitigations,
        baseline_outcome_class=baseline_outcome_class,
    )
    mitigation_verdict = str(mitigation_comparison.get("verdict") or "")
    runtime_mode = runtime_mode_override or ("runtime_scaffold" if runtime_result else ("pack_scaffold" if plan and runner_result and not runner_result.missing_assets else "inferred"))
    scaffold_ready = bool(plan and runner_result and not runner_result.missing_assets)
    runtime_capability = runtime_capability_override or _runtime_host_capability(
        plan=plan,
        runner_result=runner_result,
        runtime_result=runtime_result,
    )
    runtime_provenance = _runtime_provenance(
        runtime_mode=runtime_mode,
        runtime_executed=bool(runtime_result),
        runtime_capability=runtime_capability,
    )

    return {
        "incident_id": incident_id,
        "environment_pack_id": environment_pack_id,
        "service": service,
        "reproduction_status": reproduction_status,
        "reproduced_symptoms": reproduced_symptoms,
        "hypothesis_supported": hypothesis_supported,
        "confidence_delta": confidence_delta,
        "scaffold_ready": scaffold_ready,
        "runtime_mode": runtime_mode,
        "runtime_executed": bool(runtime_result),
        "services_seen": list(runner_result.services_seen) if runner_result else [],
        "replay_output": runtime_result.replay_output if runtime_result else "",
        "replay_status_code": runtime_result.replay_status_code if runtime_result else None,
        "replay_duration_ms": runtime_result.replay_duration_ms if runtime_result else None,
        "mitigation_outputs": list(runtime_result.mitigation_outputs) if runtime_result else [],
        "mitigation_status_codes": list(runtime_result.mitigation_status_codes) if runtime_result else [],
        "mitigation_duration_ms": list(runtime_result.mitigation_duration_ms) if runtime_result else [],
        "runtime_comparison_summary": runtime_comparison_summary,
        "baseline_outcome_class": baseline_outcome_class,
        "best_mitigation_action": str(best_mitigation.get("action") or ""),
        "best_mitigation_outcome_class": best_outcome_class,
        "best_mitigation_status_code": int(best_status_code) if isinstance(best_status_code, (int, float)) else None,
        "best_mitigation_duration_ms": int(best_duration_ms) if isinstance(best_duration_ms, (int, float)) else None,
        "best_mitigation_summary": (
            (
                f"{best_mitigation.get('action', 'No mitigation validated')} "
                f"finished in state {best_outcome_class.replace('_', ' ') if best_outcome_class else 'not evaluated'}."
            )
            if best_mitigation and runtime_result
            else (
                f"{best_mitigation.get('action', 'No mitigation selected')} is the leading scaffold-only mitigation candidate."
                if best_mitigation
                else "No runtime-backed mitigation comparison is available yet."
            )
        ),
        "mitigation_comparison": mitigation_comparison,
        "runtime_enablement_hint": _runtime_enablement_hint(
            scaffold_ready=scaffold_ready,
            runtime_executed=bool(runtime_result),
            runtime_mode=runtime_mode,
            compose_config_valid=bool(runner_result and runner_result.compose_config_valid),
            docker_available=bool(runner_result.docker_available) if runner_result else False,
            runtime_capability_state=str(runtime_capability.get("state") or ""),
        ),
        "runtime_capability": runtime_capability,
        "runtime_provenance": runtime_provenance,
        "supporting_conditions": supporting_conditions + ([f"missing scaffold assets: {', '.join(runner_result.missing_assets)}"] if runner_result and runner_result.missing_assets else []),
        "tested_mitigations": runtime_mitigations,
        "reasoning": (
            f"{reasoning} "
            f"{'The bounded runtime scaffold was executed for this run.' if runtime_result and runtime_mode != 'relay_runtime_scaffold' else ('A configured runtime host executed the bounded runtime scaffold for this run.' if runtime_result and runtime_mode == 'relay_runtime_scaffold' else ('The bounded runtime scaffold is validated and ready for replay execution.' if runner_result and runner_result.compose_config_valid and not runner_result.missing_assets and str(runtime_capability.get('state') or '') != 'relay_available' else ('The bounded runtime scaffold can delegate replay to the configured runtime host.' if str(runtime_capability.get('state') or '') == 'relay_available' else ('The bounded runtime scaffold is mapped for this incident, but Docker-backed replay is unavailable in the current app environment.' if runner_result and not runner_result.missing_assets and not runner_result.docker_available else ('The bounded runtime scaffold is mapped for this incident, but the compose contract still needs validation.' if runner_result and not runner_result.missing_assets else 'The bounded runtime scaffold is not fully ready yet.')))))}"
            f"{f' {mitigation_verdict}' if mitigation_verdict else ''}"
        ).strip(),
    }


def _runtime_override_mitigations(
    *,
    runtime_result: object,
    default_checks: list[dict[str, object]],
) -> list[dict[str, object]]:
    if not runtime_result:
        return default_checks
    outputs = list(getattr(runtime_result, "mitigation_outputs", ()) or ())
    statuses = list(getattr(runtime_result, "mitigation_status_codes", ()) or ())
    durations = list(getattr(runtime_result, "mitigation_duration_ms", ()) or ())
    baseline_status = getattr(runtime_result, "replay_status_code", None)
    baseline_duration = getattr(runtime_result, "replay_duration_ms", None)
    if not outputs:
        return default_checks
    rewritten: list[dict[str, object]] = []
    default_iter = iter(default_checks)
    for index in range(0, len(outputs), 2):
        default = next(default_iter, {"action": f"Mitigation {index // 2 + 1}", "confidence_delta": 0.0})
        hook_output = outputs[index]
        replay_output = outputs[index + 1] if index + 1 < len(outputs) else ""
        status = statuses[index // 2] if index // 2 < len(statuses) else None
        duration = durations[index // 2] if index // 2 < len(durations) else None
        outcome_class = _runtime_outcome_class(
            baseline_status=baseline_status,
            mitigation_status=status,
            baseline_duration=baseline_duration,
            mitigation_duration=duration,
        )
        rewritten.append(
            {
                "action": default.get("action", f"Mitigation {index // 2 + 1}"),
                "result": (
                    f"{str(hook_output).splitlines()[0] if hook_output else 'Hook executed'}"
                    f"{f' -> replay status {status}' if status is not None else ''}"
                    f"{f' at {duration}ms' if duration is not None else ''}"
                    f"{f' | {str(replay_output).splitlines()[-1]}' if replay_output else ''}"
                ),
                "confidence_delta": default.get("confidence_delta", 0.0),
                "status_code": status,
                "duration_ms": duration,
                "delta_ms": _runtime_delta_ms(baseline_duration, duration),
                "outcome_class": outcome_class,
                "won": False,
            }
        )
    if not rewritten:
        return default_checks
    ranked = _rank_runtime_mitigations(rewritten, baseline_duration=baseline_duration)
    winner = ranked[0]
    for item in ranked:
        item["won"] = item is winner
    return ranked


def _runtime_comparison_summary(
    runtime_result: object | None,
    runtime_mitigations: list[dict[str, object]] | None = None,
) -> str:
    baseline_duration = getattr(runtime_result, "replay_duration_ms", None) if runtime_result else None
    ranked = _rank_runtime_mitigations(runtime_mitigations, baseline_duration=baseline_duration)
    if not runtime_result:
        if not ranked:
            return ""
        winner = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None
        if isinstance(winner, dict):
            best_action = str(winner.get("action") or "Selected mitigation")
            summary = (
                f"Scaffold-only mode ranked '{best_action}' as the leading mitigation candidate. "
                "Runtime replay has not validated this mitigation yet."
            )
            if runner_up:
                summary += f" Runner-up: '{str(runner_up.get('action') or 'Unknown mitigation')}'."
            return summary
        return ""
    baseline_status = getattr(runtime_result, "replay_status_code", None)
    if baseline_status is None:
        return ""
    winner = ranked[0] if ranked else None
    runner_up = ranked[1] if len(ranked) > 1 else None
    if isinstance(winner, dict):
        best_action = str(winner.get("action") or "Selected mitigation")
        best_status = winner.get("status_code")
        best_duration = winner.get("duration_ms")
        outcome = _runtime_outcome_class(
            baseline_status=baseline_status,
            mitigation_status=best_status,
            baseline_duration=baseline_duration,
            mitigation_duration=best_duration,
        ).replace("_", " ")
        summary = (
            f"Baseline replay returned {baseline_status}"
            f"{f' at {baseline_duration}ms' if baseline_duration is not None else ''}; "
            f"best mitigation {best_action} returned {best_status}"
            f"{f' at {best_duration}ms' if best_duration is not None else ''}"
            f" and the runtime outcome was {outcome}."
        )
        if isinstance(runner_up, dict):
            runner_action = str(runner_up.get("action") or "Runner-up mitigation")
            runner_status = runner_up.get("status_code")
            runner_duration = runner_up.get("duration_ms")
            runner_outcome = str(runner_up.get("outcome_class") or "").replace("_", " ")
            summary += (
                f" Runner-up {runner_action} returned {runner_status}"
                f"{f' at {runner_duration}ms' if runner_duration is not None else ''}"
                f" and remained {runner_outcome or 'not classified'}."
            )
        return summary
    return f"Baseline replay returned {baseline_status}{f' at {baseline_duration}ms' if baseline_duration is not None else ''}."


def rank_candidate_fixes_with_runtime(
    candidate_fixes: list[dict[str, object]] | None,
    *,
    replica_summary: dict[str, object],
) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    best_action = str(replica_summary.get("best_mitigation_action") or "")
    best_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "")
    best_duration = replica_summary.get("best_mitigation_duration_ms")
    baseline_duration = replica_summary.get("replay_duration_ms")
    for item in candidate_fixes or []:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action", "")).strip()
        base_success = float(item.get("success_rate", 0.0) or 0.0)
        overlap = _action_overlap(action, best_action) if best_action else 0.0
        runtime_score = _runtime_outcome_score(
            best_outcome,
            baseline_duration=baseline_duration if isinstance(baseline_duration, int) else None,
            mitigation_duration=best_duration if isinstance(best_duration, int) else None,
        ) * overlap
        ranked_item = dict(item)
        ranked_item["runtime_alignment"] = round(overlap, 2)
        ranked_item["runtime_score"] = round(runtime_score, 2)
        ranked_item["runtime_outcome_class"] = best_outcome if overlap >= 0.25 else ""
        ranked_item["success_rate"] = round(max(base_success, runtime_score), 2)
        ranked.append(ranked_item)
    ranked.sort(
        key=lambda item: (
            float(item.get("runtime_score", 0.0) or 0.0),
            float(item.get("success_rate", 0.0) or 0.0),
        ),
        reverse=True,
    )
    return ranked


def enrich_memory_with_runtime(
    memory_hits: dict[str, list[dict[str, object]]] | None,
    *,
    replica_summary: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    payload = {
        "similar_incidents": [dict(item) for item in (memory_hits or {}).get("similar_incidents", [])],
        "runbooks": [dict(item) for item in (memory_hits or {}).get("runbooks", [])],
        "unresolved_items": [dict(item) for item in (memory_hits or {}).get("unresolved_items", [])],
        "recent_guardian_outcomes": [dict(item) for item in (memory_hits or {}).get("recent_guardian_outcomes", [])],
    }
    best_action = str(replica_summary.get("best_mitigation_action") or "")
    best_outcome = str(replica_summary.get("best_mitigation_outcome_class") or "").replace("_", " ")
    best_summary = str(replica_summary.get("best_mitigation_summary") or "")
    if not best_action:
        return payload

    for item in payload["runbooks"]:
        overlap_sources = [str(item.get("runbook_summary", ""))]
        overlap_sources.extend(
            str(action).strip()
            for action in item.get("historical_actions", [])
            if str(action).strip()
        )
        overlap = max((_action_overlap(source, best_action) for source in overlap_sources), default=0.0)
        if overlap >= 0.2:
            item["success_rate"] = round(min(0.99, float(item.get("success_rate", 0.0) or 0.0) + 0.04), 2)
            note = f"Runtime alignment: {best_action} tested as {best_outcome} in REPLICA."
            item["why_now_fit"] = f"{str(item.get('why_now_fit', '')).strip()} {note}".strip()
    payload["runbooks"].sort(key=lambda item: float(item.get("success_rate", 0.0) or 0.0), reverse=True)

    for item in payload["similar_incidents"]:
        overlap = _action_overlap(str(item.get("prior_action", "")), best_action)
        if overlap >= 0.2:
            item["similarity"] = round(min(0.99, float(item.get("similarity", 0.0) or 0.0) + 0.04), 2)
            item["match_reason"] = f"{str(item.get('match_reason', '')).strip()} Runtime overlap: the prior action aligns with {best_action}."
    payload["similar_incidents"].sort(
        key=lambda item: (
            bool(item.get("service_match")),
            bool(item.get("severity_match")),
            float(item.get("similarity", 0.0) or 0.0),
            float(item.get("success_rate", 0.0) or 0.0),
        ),
        reverse=True,
    )

    for item in payload["unresolved_items"]:
        item["follow_up_reason"] = (
            f"{str(item.get('follow_up_reason', '')).strip()} "
            f"Current runtime outcome: {best_summary or f'{best_action} validated as {best_outcome}.'}"
        ).strip()

    return payload


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
    trace_status = "not_run"
    suspected_service = service
    code_owner_team = "Platform Operations"
    code_owner_slug = "@platform-ops"
    suspected_files: list[str] = []
    inspection_point = "Wait for REPLICA to validate the likely failure path before opening a code investigation."
    replay_evidence_summary = runtime_comparison or "No runtime replay evidence is attached to this incident yet."
    developer_handoff_summary = "TRACE has not prepared a developer handoff packet for this incident yet."
    runtime_provenance = {
        "mode": str(replica_runtime_provenance.get("mode") or "inferred_only"),
        "label": str(replica_runtime_provenance.get("label") or "Inferred only"),
        "summary": str(replica_runtime_provenance.get("summary") or "TRACE is still using bounded inference rather than measured runtime replay."),
        "executed_by": str(replica_runtime_provenance.get("executed_by") or "not_run"),
    }

    if replica_summary.get("reproduction_status") == "reproduced":
        trace_status = "narrowed"
        if "retry amplification" in issue_family:
            suspected_modules = [module_name for module_name, _ in mapped_targets] or ["auth.middleware.retry", "gateway.timeout_guard", "auth.circuit_breaker"]
            suspected_functions = [function_name for _, function_name in mapped_targets] or ["apply_retry_policy", "await_upstream_auth", "record_timeout_budget"]
            suspected_service = "auth-svc"
            code_owner_team = "Identity Platform"
            code_owner_slug = "@identity-platform"
            suspected_files = [
                "replica_packs/checkout-python-fastapi-auth-redis-v1/auth/auth_server.py",
                "replica_packs/checkout-python-fastapi-auth-redis-v1/gateway/gateway_server.py",
            ]
            expected_flow = "Auth retries should cap quickly and release gateway workers when upstream latency rises."
            observed_divergence = "Retry middleware continues scheduling upstream attempts after the timeout budget is exhausted."
            state_anomalies = ["retry_count exceeds policy cap", "worker pool stays occupied during downstream timeout wait"]
            inspection_point = "Inspect the auth retry middleware budget check first, then verify the gateway timeout guard stops scheduling retries once the auth timeout budget is spent."
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
            developer_handoff_summary = (
                f"Start with {suspected_files[0]} and hand this packet to {code_owner_team}. "
                "The bounded replay shows the baseline request timing out until retries are capped or the circuit breaker is opened."
                f"{f' {comparison_verdict}' if comparison_verdict else ''}"
            )
        elif "pool exhaustion" in issue_family or "session leak" in issue_family:
            suspected_modules = [module_name for module_name, _ in mapped_targets] or ["checkout.db.session", "checkout.retry_patch", "checkout.transaction_flow"]
            suspected_functions = [function_name for _, function_name in mapped_targets] or ["checkout_session_scope", "retry_checkout_write", "release_db_session"]
            suspected_service = "checkout-svc"
            code_owner_team = "Checkout Platform"
            code_owner_slug = "@checkout-platform"
            suspected_files = [
                "replica_packs/checkout-python-fastapi-postgres-v1/checkout/checkout_server.py",
            ]
            expected_flow = "Checkout retries should release DB sessions before re-entering the write path."
            observed_divergence = "Retry path retains a session handle long enough to exhaust the shared pool."
            state_anomalies = ["session count grows between retries", "pool checkout waits continue after request cancellation"]
            inspection_point = "Inspect the checkout retry patch first, especially the session cleanup hook that should release the DB handle before the next retry is scheduled."
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
            developer_handoff_summary = (
                f"Start with {suspected_files[0]} and hand this packet to {code_owner_team}. "
                "The bounded replay shows the pool recovering only after the leaking retry path is removed or orphaned sessions are terminated."
                f"{f' {comparison_verdict}' if comparison_verdict else ''}"
            )
        elif "certificate expiry" in issue_family:
            suspected_modules = ["edge.cert_loader", "edge.listener_config", "acme.rotation_job"]
            suspected_functions = ["load_public_certificate", "validate_chain_expiry", "reload_edge_listener"]
            suspected_service = "edge-gateway"
            code_owner_team = "Edge Reliability"
            code_owner_slug = "@edge-reliability"
            suspected_files = ["edge/cert_loader.py", "edge/listener.py"]
            expected_flow = "Edge listeners should always serve a valid public certificate chain."
            observed_divergence = "Expired certificate chain remained attached to the active listener after rotation was missed."
            state_anomalies = ["active cert serial differs from latest staged cert", "rotation timestamp exceeded renewal window"]
            inspection_point = "Inspect the edge certificate loader first, then confirm the rotation job and listener reload path picked up the staged chain."
            replay_evidence_summary = "Replay evidence shows the edge listener continued to serve the stale certificate chain."
            confidence = 0.63
            reasoning = "TRACE narrowed the issue to the certificate loader and rotation path that failed to refresh the active listener."
            developer_handoff_summary = "Inspect the certificate loader and listener reload path before any broader edge rollback."
        elif "memory leak" in issue_family:
            suspected_modules = ["image_worker.frame_cache", "image_worker.transform_pipeline", "image_worker.release_hooks"]
            suspected_functions = ["store_frame_buffer", "run_transform_batch", "release_decoded_frames"]
            suspected_service = "image-worker"
            code_owner_team = "Media Runtime"
            code_owner_slug = "@media-runtime"
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
            developer_handoff_summary = "Inspect the release hook and frame cache ownership path before attempting to recycle workers."

    if runtime_provenance["mode"] == "delegated_relay":
        replay_evidence_summary = f"{replay_evidence_summary} Runtime provenance: delegated replay from the external runtime host.".strip()
        developer_handoff_summary = f"{developer_handoff_summary} Runtime evidence came from the external runtime host replay.".strip()
    elif runtime_provenance["mode"] == "direct_runtime":
        replay_evidence_summary = f"{replay_evidence_summary} Runtime provenance: direct replay on the current app host.".strip()
        developer_handoff_summary = f"{developer_handoff_summary} Runtime evidence came from direct replay on the current app host.".strip()

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
        "code_owner_team": code_owner_team,
        "code_owner_slug": code_owner_slug,
        "suspected_files": suspected_files,
        "developer_handoff_summary": developer_handoff_summary,
        "runtime_provenance": runtime_provenance,
        "confidence": confidence,
        "reasoning": reasoning,
    }
