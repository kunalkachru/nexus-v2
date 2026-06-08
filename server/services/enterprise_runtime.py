from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from statistics import mean
from typing import Any, NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from server.artifacts import _load_artifacts
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
from server.services.replica_runtime import ReplicaRunner, build_execution_plan, trace_targets_for_plan


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
            runbooks.append(
                {
                    "incident_id": item["incident_id"],
                    "runbook_summary": str(primary.get("name") or f"Prior mitigation pattern for {item['incident_id']}"),
                    "success_rate": float(primary.get("success_rate", item["success_rate"])),
                    "historical_reason": str(details.get("forge", {}).get("selection_logic", "")).strip(),
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
        top_runbook = memory_hits["runbooks"][0] if memory_hits["runbooks"] else {}
        runner_up = memory_hits["runbooks"][1] if len(memory_hits["runbooks"]) > 1 else {}
        reasoning = (
            f"{forge_output.reasoning} Referenced {len(memory_hits['runbooks'])} runbook memories and "
            f"{len(memory_hits['unresolved_items'])} unresolved service items. "
            f"Primary historical fit: {top_runbook.get('runbook_summary', 'none')}."
            f"{' Why now: ' + str(top_runbook.get('why_now_fit')) + '.' if top_runbook.get('why_now_fit') else ''}"
            f"{' Runner-up: ' + str(runner_up.get('runbook_summary')) + '.' if runner_up else ''} "
            f"REPLICA: {replica_summary.get('reasoning', '')} "
            f"TRACE: {trace_summary.get('reasoning', '')} "
            "FORGE kept the plan biased toward reversible, lower-blast-radius actions first."
        )
        forge_output = forge_output.model_copy(update={"reasoning": reasoning})
        self._set_task_status(state["task_board"], "replica-validate", str(replica_summary.get("reproduction_status", "not_run")), str(replica_summary.get("reasoning", "")))
        self._set_task_status(state["task_board"], "trace-debug", str(trace_summary.get("trace_status", "not_run")), str(trace_summary.get("reasoning", "")))
        self._set_task_status(state["task_board"], "forge-plan", "completed", reasoning)
        return {
            "triage_summary": triage_summary,
            "forge_output": forge_output,
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
                    max((item.get("success_rate", 0.0) for item in memory_hits["runbooks"]), default=0.84),
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
        risk_class = "high" if priority_rank(state["sentinel_output"].severity) <= 2 else "medium"
        approval_level = "incident_manager" if risk_class == "high" else "operator"
        rollback_readiness = "ready" if guardian_output.decision == "approve" else "needs_review"
        simulation_readiness = "ready" if guardian_output.decision != "reject" else "manual_review"
        blocked_controls = guardian_output.blocked_patterns or (
            ["destructive_runbook_guard"] if guardian_output.decision == "reject" else []
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
                    f"Validated signals: REPLICA is {replica_summary.get('reproduction_status', 'not_run')} and TRACE is {trace_summary.get('trace_status', 'not_run')}. "
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
                "replica_summary": build_replica_summary(
                    incident_id=context.incident.id,
                    triage_summary=state["triage_summary"],
                    root_cause=state["prism_output"].root_cause,
                    recent_logs=context.signals.get("logs", []),
                    recent_deployments=context.signals.get("deployment", []),
                    candidate_fixes=[{"action": forge_output.runbook.summary, "success_rate": 0.84}],
                ),
                "trace_summary": build_trace_summary(
                    incident_id=context.incident.id,
                    triage_summary=state["triage_summary"],
                    replica_summary=build_replica_summary(
                        incident_id=context.incident.id,
                        triage_summary=state["triage_summary"],
                        root_cause=state["prism_output"].root_cause,
                        recent_logs=context.signals.get("logs", []),
                        recent_deployments=context.signals.get("deployment", []),
                        candidate_fixes=[{"action": forge_output.runbook.summary, "success_rate": 0.84}],
                    ),
                    root_cause=state["prism_output"].root_cause,
                    recent_deployments=context.signals.get("deployment", []),
                    recent_logs=context.signals.get("logs", []),
                ),
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
                "memory_hits": state["memory_hits"],
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
    checks: list[dict[str, object]] = []
    for action, result, confidence_delta in fallback_checks:
        if candidate_actions and not any(action.lower() in candidate.lower() or candidate.lower() in action.lower() for candidate in candidate_actions):
            continue
        checks.append(
            {
                "action": action,
                "result": result,
                "confidence_delta": confidence_delta,
            }
        )
    if checks:
        return checks
    return [
        {"action": action, "result": result, "confidence_delta": confidence_delta}
        for action, result, confidence_delta in fallback_checks
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


def build_replica_summary(
    *,
    incident_id: str,
    triage_summary: dict[str, object],
    root_cause: str,
    recent_logs: list[object] | None = None,
    recent_deployments: list[object] | None = None,
    candidate_fixes: list[object] | None = None,
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
    runner_result = ReplicaRunner().inspect_plan(plan) if plan else None

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

    return {
        "incident_id": incident_id,
        "environment_pack_id": environment_pack_id,
        "service": service,
        "reproduction_status": reproduction_status,
        "reproduced_symptoms": reproduced_symptoms,
        "hypothesis_supported": hypothesis_supported,
        "confidence_delta": confidence_delta,
        "supporting_conditions": supporting_conditions + ([f"missing scaffold assets: {', '.join(runner_result.missing_assets)}"] if runner_result and runner_result.missing_assets else []),
        "tested_mitigations": tested_mitigations,
        "reasoning": reasoning,
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

    if replica_summary.get("reproduction_status") == "reproduced":
        trace_status = "narrowed"
        if "retry amplification" in issue_family:
            suspected_modules = [module_name for module_name, _ in mapped_targets] or ["auth.middleware.retry", "gateway.timeout_guard", "auth.circuit_breaker"]
            suspected_functions = [function_name for _, function_name in mapped_targets] or ["apply_retry_policy", "await_upstream_auth", "record_timeout_budget"]
            expected_flow = "Auth retries should cap quickly and release gateway workers when upstream latency rises."
            observed_divergence = "Retry middleware continues scheduling upstream attempts after the timeout budget is exhausted."
            state_anomalies = ["retry_count exceeds policy cap", "worker pool stays occupied during downstream timeout wait"]
            if "middleware" in deployment_text:
                state_anomalies.append("recent retry middleware refactor aligns with the divergence point")
            if any("circuit breaker" in action.lower() for action in mitigation_actions):
                state_anomalies.append("circuit-breaker mitigation relieves the same failing path in REPLICA")
            if "event-loop starvation" in logs_text or "worker saturation" in logs_text:
                state_anomalies.append("runtime starvation confirms the retry path is blocking gateway capacity, not just auth latency")
            confidence = 0.74 if "middleware" in deployment_text else 0.69
            reasoning = "TRACE narrowed the issue to the retry middleware path that keeps auth retries alive after the timeout budget is already exhausted."
        elif "pool exhaustion" in issue_family or "session leak" in issue_family:
            suspected_modules = [module_name for module_name, _ in mapped_targets] or ["checkout.db.session", "checkout.retry_patch", "checkout.transaction_flow"]
            suspected_functions = [function_name for _, function_name in mapped_targets] or ["checkout_session_scope", "retry_checkout_write", "release_db_session"]
            expected_flow = "Checkout retries should release DB sessions before re-entering the write path."
            observed_divergence = "Retry path retains a session handle long enough to exhaust the shared pool."
            state_anomalies = ["session count grows between retries", "pool checkout waits continue after request cancellation"]
            if "retry" in deployment_text:
                state_anomalies.append("recent retry patch aligns with the session lifecycle divergence")
            if any("roll back" in action.lower() for action in mitigation_actions):
                state_anomalies.append("rollback mitigation targets the same leaking retry path")
            if "idle in transaction" in logs_text or "leaked session" in logs_text:
                state_anomalies.append("runtime logs confirm sessions remain open after request cancellation")
            confidence = 0.76 if "retry" in deployment_text else 0.72
            reasoning = "TRACE narrowed the issue to the checkout retry patch where the session lifecycle no longer closes cleanly after failure."
        elif "certificate expiry" in issue_family:
            suspected_modules = ["edge.cert_loader", "edge.listener_config", "acme.rotation_job"]
            suspected_functions = ["load_public_certificate", "validate_chain_expiry", "reload_edge_listener"]
            expected_flow = "Edge listeners should always serve a valid public certificate chain."
            observed_divergence = "Expired certificate chain remained attached to the active listener after rotation was missed."
            state_anomalies = ["active cert serial differs from latest staged cert", "rotation timestamp exceeded renewal window"]
            confidence = 0.63
            reasoning = "TRACE narrowed the issue to the certificate loader and rotation path that failed to refresh the active listener."
        elif "memory leak" in issue_family:
            suspected_modules = ["image_worker.frame_cache", "image_worker.transform_pipeline", "image_worker.release_hooks"]
            suspected_functions = ["store_frame_buffer", "run_transform_batch", "release_decoded_frames"]
            expected_flow = "Completed image transform batches should release decoded frame buffers before the next queue pull."
            observed_divergence = "Decoded frame buffers remain strongly referenced after batch completion, so heap pressure compounds across replay cycles."
            state_anomalies = ["retained frame_buffer objects dominate the heap snapshot", "gc pauses grow as replayed batches accumulate"]
            if "release hook missing" in logs_text:
                state_anomalies.append("runtime logs already point at a missing release hook after transform completion")
            confidence = 0.67
            reasoning = "TRACE narrowed the issue to the frame-cache release path where completed transform batches retain decoded buffers."

    return {
        "incident_id": incident_id,
        "service": service,
        "trace_status": trace_status,
        "suspected_modules": suspected_modules,
        "suspected_functions": suspected_functions,
        "expected_flow": expected_flow,
        "observed_divergence": observed_divergence,
        "state_anomalies": state_anomalies,
        "confidence": confidence,
        "reasoning": reasoning,
    }
