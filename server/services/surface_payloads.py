from __future__ import annotations

import json
from pathlib import Path

from server.incident_payloads import get_incident_definition, get_incident_details, list_supported_incident_ids
from server.models import IncidentWorkflowStage, QueueIncidentSummary, QueueResponse
from server.artifacts import get_artifact_summary
from server.services.observability import ObservabilityService
from server.services.result_contracts import build_structured_result
from server.services.priority import normalize_priority_label, priority_snapshot
from server.services.enterprise_runtime import build_training_enterprise_summary


METRICS_PATH = Path(__file__).resolve().parents[2] / "frontend" / "metrics.json"
OBSERVABILITY_SERVICE = ObservabilityService()


def _display_severity(severity: str) -> str:
    return normalize_priority_label(severity)


def build_incident_response(incident_id: str) -> dict[str, object]:
    incident = get_incident_definition(incident_id)
    details = get_incident_details(incident_id)
    source_channel = incident_source_channel(incident_id)
    priority = priority_snapshot(incident.severity)

    return {
        "incident": {
            "id": incident.id,
            "name": incident.name,
            "severity": _display_severity(incident.severity),
            "summary": details["summary"],
            "detected_at": details["detected_at"],
            "duration_minutes": details["duration_minutes"],
            "related_services": details["related_services"],
            "recent_deployments": details["recent_deployments"],
            "similar_past_incidents": details["similar_past_incidents"],
            "source_channel": source_channel,
        },
        "observability": {
            "metrics": details["metrics"],
            "recent_logs": details["recent_logs"],
            "alert_timeline": details["alert_timeline"],
            "recommended_runbooks": details["recommended_runbooks"],
            "evidence_sources": OBSERVABILITY_SERVICE.build_evidence_sources(incident_id),
        },
        "classification": {
            "incident_id": incident.id,
            "incident_name": incident.name,
            "severity": _display_severity(incident.severity),
            "confidence": details["sentinel"]["confidence"],
            "confidence_breakdown": details["sentinel"]["confidence_breakdown"],
            "evidence": details["sentinel"]["evidence"],
            "reasoning": details["sentinel"]["reasoning"],
        },
        "diagnosis": {
            "root_cause": incident.root_cause,
            "confidence": details["prism"]["confidence"],
            "supporting_logs": details["prism"]["log_snippets"],
            "correlation_analysis": details["prism"]["correlation_analysis"],
            "reasoning": details["prism"]["reasoning"],
        },
        "runbook": {
            "language": "bash",
            "summary": details["forge"]["recommended_runbook"],
            "proposed_fix": details["forge"]["recommended_runbook"],
            "selection_logic": details["forge"]["selection_logic"],
            "candidate_fixes": details["forge"]["candidate_fixes"],
            "recommended_runbook": details["forge"]["recommended_runbook"],
            "reasoning": details["forge"]["reasoning"],
            "cost_usd": 0.12,
        },
        "guardian": {
            "decision": details["guardian"]["decision"],
            "confidence": details["guardian"]["confidence"],
            "safety_checks": details["guardian"]["safety_checks"],
            "policy_violations": details["guardian"]["policy_violations"],
            "reasoning": details["guardian"]["reasoning"],
        },
        "structured_result": {
            **build_structured_result(
                incident_id=incident.id,
                root_cause=incident.root_cause,
                proposed_fix=details["forge"]["recommended_runbook"],
                safety_decision=details["guardian"]["decision"],
                confidence=details["guardian"]["confidence"],
                execution_status="executed",
                live_reasoning=False,
                raw_priority_label=priority["raw_label"],
                normalized_priority_label=priority["normalized_label"],
                normalized_priority_rank=priority["rank"],
                reward=0.0,
            ),
            "evidence": {
                "log_count": len(details["recent_logs"]),
                "metric_count": len(details["metrics"]),
                "deployment_count": len(details["recent_deployments"]),
            },
        },
        "workflow": build_workflow_timeline(incident_id, source_channel, incident, details),
        "execution_result": "executed",
        "reward": 0.87,
        "execution_time_ms": 8.7,
        "supported_incidents": list_supported_incident_ids(),
    }


def load_metrics_payload() -> dict[str, object]:
    with METRICS_PATH.open() as file_handle:
        payload = json.load(file_handle)
    payload["workflow_observation_states"] = workflow_observation_states()
    episode_records = payload.get("episode_records") or []
    latest_episode = episode_records[-1] if episode_records else None
    payload["latest_episode"] = latest_episode
    payload["reward_evaluation"] = payload.get("reward_evaluation") or payload.get("training_evaluation") or {
        "reward_curve_final": round(payload.get("summary", {}).get("trained_reward", 0.0), 2),
        "reward_curve_peak": round(max(payload.get("reward_curve", [0.0])) if payload.get("reward_curve") else 0.0, 2),
        "reward_curve_delta": round(
            (payload.get("reward_curve", [0.0])[-1] - payload.get("reward_curve", [0.0])[0])
            if len(payload.get("reward_curve", [])) > 1
            else 0.0,
            2,
        ),
        "reward_curve_mean": round(
            sum(payload.get("reward_curve", [])) / len(payload.get("reward_curve", []))
            if payload.get("reward_curve")
            else 0.0,
            2,
        ),
        "policy_drift": payload.get("policy_weights", {}),
    }
    payload["rl_episode_contract"] = payload.get("rl_episode_contract") or _synthesize_rl_episode_contract(latest_episode)
    payload["queue_snapshot"] = build_queue_snapshot(payload)
    payload["platform_status"] = build_platform_status(payload)
    payload["artifact_summary"] = get_artifact_summary()
    return payload


def _synthesize_rl_episode_contract(latest_episode: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(latest_episode, dict):
        return {}
    steps = latest_episode.get("steps") if isinstance(latest_episode.get("steps"), list) else []
    agent_trace = [step for step in steps if isinstance(step, dict)]
    observation = latest_episode.get("observation_state") if isinstance(latest_episode.get("observation_state"), dict) else {}
    forge_step = next(
        (
            str(step.get("action", "")).strip()
            for step in agent_trace
            if str(step.get("agent_name", "")).strip().lower() == "forge" and str(step.get("action", "")).strip()
        ),
        "",
    )
    solution_proposal = str(latest_episode.get("solution_proposal") or forge_step or "Training runbook proposal").strip()
    return {
        "observation": {
            "incident_id": latest_episode.get("incident_id", ""),
            "service": latest_episode.get("incident_id", ""),
            "severity": latest_episode.get("difficulty", ""),
            "difficulty": latest_episode.get("difficulty", ""),
            "source_channel": "datadog",
            "raw_priority_label": observation.get("raw_priority_label", latest_episode.get("difficulty", "")),
            "normalized_priority_label": observation.get("normalized_priority_label", latest_episode.get("difficulty", "")),
            "normalized_priority_rank": int(observation.get("normalized_priority_rank", 0) or 0),
            "live_reasoning": bool(observation.get("live_reasoning", False)),
            "symptom_count": len(agent_trace),
            "evidence_count": len(agent_trace),
            "workflow_state": "resolved",
        },
        "agent_trace": agent_trace,
        "reward_breakdown": {
            "mttr": float(latest_episode.get("reward", 0.0)),
            "diagnosis": float(latest_episode.get("environment_reward", 0.0)),
            "customer": float(latest_episode.get("reward", 0.0)),
            "coordination": float(latest_episode.get("reward", 0.0)),
            "oversight": float(latest_episode.get("reward", 0.0)),
            "severity_penalty": 0.0,
            "composite": float(latest_episode.get("reward", 0.0)),
        },
        "solution_proposal": solution_proposal,
        "raw_priority_label": latest_episode.get("raw_priority_label", latest_episode.get("difficulty", "")),
        "normalized_priority_label": latest_episode.get("normalized_priority_label", latest_episode.get("difficulty", "")),
        "normalized_priority_rank": int(latest_episode.get("normalized_priority_rank", 0) or 0),
        "live_reasoning": bool(latest_episode.get("live_reasoning", False)),
        "guardian_decision": latest_episode.get("guardian_decision", "approve"),
        "execution_result": latest_episode.get("execution_result", "executed"),
        "reward": float(latest_episode.get("reward", 0.0)),
        "advantage": float(latest_episode.get("advantage", 0.0)),
        "cost_usd": float(latest_episode.get("cost_usd", 0.0)),
    }


def build_queue_snapshot(payload: dict[str, object]) -> dict[str, object]:
    episode_records = payload.get("episode_records") or []
    latest_episode = episode_records[-1] if episode_records else {}
    return {
        "open_incidents": len(list_supported_incident_ids()),
        "sla_at_risk": 2,
        "primary_source": "Webhook",
        "last_update": "2 min ago",
        "current_stage": "Evidence retrieved",
        "latest_agent_activity": "FORGE proposed a rollback-safe runbook",
        "sla_timer": "11 min remaining",
        "highest_severity": "P1",
        "current_bottleneck": "API latency",
        "open_console": "INC001",
        "latest_episode": latest_episode,
    }


def build_queue_response() -> QueueResponse:
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

    items: list[QueueIncidentSummary] = []
    for incident_id in list_supported_incident_ids():
        incident = get_incident_definition(incident_id)
        details = get_incident_details(incident_id)
        items.append(
                QueueIncidentSummary(
                    nexus_incident_id=incident.id,
                    title=incident.name,
                    severity=_display_severity(incident.severity),
                status=status_by_incident.get(incident_id, "investigating"),
                source_channel=incident_source_channel(incident_id),
                current_stage=stage_by_incident.get(incident_id, IncidentWorkflowStage.INCIDENT_RECEIVED),
                updated_at=str(details["detected_at"]),
            )
        )
    return QueueResponse(items=items)


def build_history_archive() -> list[dict[str, object]]:
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
                    "severity": _display_severity(incident.severity),
                "outcome": outcome_by_incident.get(incident_id, "resolved"),
                "source_channel": incident_source_channel(incident_id),
                "resolved_at": details["detected_at"],
                "summary": details["summary"],
                "owner_team": details["related_services"][0] if details.get("related_services") else "platform",
                "window": window_by_incident.get(incident_id, "last-30-days"),
            }
        )
    return archive


def build_replay_scenarios() -> list[dict[str, object]]:
    scenarios = []
    replay_map = {
        "api_timeout_cascade": ("INC001", ["webhook", "api-gateway", "P1", "timeout cascade"]),
        "db_connection_pool_exhaustion": ("INC002", ["manual_form", "payments", "P1", "database"]),
        "redis_saturation": ("INC004", ["webhook", "redis", "P2", "cache"]),
        "memory_leak_after_deploy": ("INC003", ["stream_anomaly", "worker-fleet", "P2", "deploy"]),
        "queue_backlog_worker_stall": ("INC005", ["batch_import", "billing", "P1", "queue"]),
        "bad_deployment_regression": ("INC004", ["webhook", "deployment", "P1", "rollback"]),
        "certificate_expiry": ("INC005", ["webhook", "security", "P1", "expiry"]),
        "cache_explosion": ("INC004", ["webhook", "cache", "P2", "eviction"]),
    }
    for scenario_id, (incident_id, pills) in replay_map.items():
        incident = get_incident_definition(incident_id)
        details = get_incident_details(incident_id)
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "title": incident.name,
                "summary": details["summary"],
                "incident_id": incident_id,
                "pills": pills,
                    "payload": [
                        "Source payload",
                        f"Scenario: {scenario_id.replace('_', ' ')}",
                    f"Severity: {_display_severity(incident.severity)}",
                        f"Summary: {details['summary']}",
                    ],
                "evidence": [
                    "Evidence pack",
                    details["sentinel"]["reasoning"],
                    details["prism"]["reasoning"],
                ],
                "agents": [
                    "Agent outputs",
                    f"SENTINEL: {details['sentinel']['reasoning']}",
                    f"PRISM: {details['prism']['reasoning']}",
                    f"FORGE: {details['forge']['reasoning']}",
                    f"GUARDIAN: {details['guardian']['reasoning']}",
                ],
                "outcome": [
                    "Final result",
                    f"Reward: {round(details['guardian']['confidence'] * 100)}% confidence guardrail approval",
                ],
                "launch_label": f"Open {incident.id} console",
            }
        )
    return scenarios


def build_training_summary(payload: dict[str, object]) -> dict[str, object]:
    artifact_summary = get_artifact_summary()
    return {
        "summary": payload.get("summary", {}),
        "episode_records": payload.get("episode_records", []),
        "difficulty_ladder": payload.get("difficulty_ladder", []),
        "reward_curve": payload.get("reward_curve", []),
        "cost_curve": payload.get("cost_curve", []),
        "workflow_observation_states": payload.get("workflow_observation_states", []),
        "agent_accuracy": payload.get("agent_accuracy", {}),
        "final_difficulty": payload.get("final_difficulty"),
        "artifact_summary": artifact_summary,
        "enterprise_summary": build_training_enterprise_summary(payload),
    }


def build_platform_status(payload: dict[str, object]) -> dict[str, object]:
    artifact_summary = get_artifact_summary()
    enterprise_summary = build_training_enterprise_summary(payload)
    return {
        "mode": "Product",
        "webhook_auth": "Configured",
        "webhook_signature_verification": "Active",
        "rate_limiting": "Enabled",
        "policy_status": "Active",
        "audit_logs": "Enabled",
        "integrations": "Healthy",
        "replay_readiness": "Ready",
        "deployment_environment": "Local product shell",
        "validation_profile": "Deterministic",
        "replay_launches": artifact_summary["replay_launches"],
        "training_snapshots": artifact_summary["training_snapshots"],
        "learning_contracts": artifact_summary["learning_contracts"],
        "audit_events": artifact_summary.get("audit_events", 0),
        "guardian_reviews": artifact_summary.get("guardian_reviews", 0),
        "orchestration_success_rate": enterprise_summary["orchestration_success_rate"],
        "fallback_rate": enterprise_summary["fallback_rate"],
        "branch_completion_rate": enterprise_summary["branch_completion_rate"],
        "guarded_execution_rate": enterprise_summary["guarded_execution_rate"],
    }


def incident_source_channel(incident_id: str) -> str:
    source_channels = {
        "INC001": "webhook",
        "INC002": "manual_form",
        "INC003": "stream_anomaly",
        "INC004": "webhook",
        "INC005": "batch_import",
    }
    return source_channels.get(incident_id, "webhook")


def build_workflow_timeline(
    incident_id: str,
    source_channel: str,
    incident,
    details: dict[str, object],
) -> list[dict[str, object]]:
    detected_at = details["detected_at"]
    source_label = {
        "webhook": "Webhook alert ingestion",
        "manual_form": "Manual incident submission",
        "slack_command": "Slack-style report",
        "stream_anomaly": "Stream anomaly detection",
        "batch_import": "Batch import",
    }.get(source_channel, "Enterprise intake")

    return [
        {
            "state": "incident_received",
            "label": "Incident received",
            "actor": source_channel,
            "status": "completed",
            "timestamp": detected_at,
            "summary": f"{incident_id} received via {source_label.lower()}",
            "payload": {
                "source_channel": source_channel,
                "external_id": incident_id,
                "source_label": source_label,
            },
        },
        {
            "state": "validated_authenticated",
            "label": "Validated and authenticated",
            "actor": "api-gateway",
            "status": "completed",
            "timestamp": f"{detected_at} + 1m",
            "summary": "Source channel verified and incident envelope accepted",
            "payload": {
                "source_channel": source_channel,
                "auth_model": "tenant-aware request validation",
            },
        },
        {
            "state": "enriched_with_service_context",
            "label": "Enriched with service context",
            "actor": "workflow-service",
            "status": "completed",
            "timestamp": f"{detected_at} + 2m",
            "summary": "Added service ownership, recent deployment, and environment context",
            "payload": {
                "service": incident.system_context.service,
                "language": incident.system_context.language,
                "infra": incident.system_context.infra,
            },
        },
        {
            "state": "evidence_retrieved",
            "label": "Evidence retrieved",
            "actor": "observability",
            "status": "completed",
            "timestamp": f"{detected_at} + 3m",
            "summary": "Pulled logs, metrics, timeline events, and deployment context",
            "payload": {
                "log_count": len(details["recent_logs"]),
                "metric_count": len(details["metrics"]),
                "deployment_count": len(details["recent_deployments"]),
            },
        },
        {
            "state": "sentinel_classified",
            "label": "SENTINEL classified",
            "actor": "SENTINEL",
            "status": "completed",
            "timestamp": f"{detected_at} + 4m",
            "summary": "Classified severity and blast radius",
            "payload": details["sentinel"],
        },
        {
            "state": "prism_diagnosed",
            "label": "PRISM diagnosed",
            "actor": "PRISM",
            "status": "completed",
            "timestamp": f"{detected_at} + 5m",
            "summary": "Explained the root cause using correlated evidence",
            "payload": details["prism"],
        },
        {
            "state": "forge_proposed_runbook",
            "label": "FORGE proposed runbook",
            "actor": "FORGE",
            "status": "completed",
            "timestamp": f"{detected_at} + 6m",
            "summary": "Selected the best remediation path and rollback shape",
            "payload": details["forge"],
        },
        {
            "state": "guardian_reviewed_safety",
            "label": "GUARDIAN reviewed safety",
            "actor": "GUARDIAN",
            "status": "completed",
            "timestamp": f"{detected_at} + 7m",
            "summary": "Confirmed the action was safe to apply",
            "payload": details["guardian"],
        },
        {
            "state": "executed_verified_learned",
            "label": "Outcome executed, verified, and learned",
            "actor": "workflow-engine",
            "status": "completed",
            "timestamp": f"{detected_at} + 8m",
            "summary": "Outcome recorded and episode added to the learning loop",
            "payload": {
                "execution_result": "executed",
                "reward": 0.87,
                "learning_state": "captured",
            },
        },
    ]


def workflow_observation_states() -> list[dict[str, object]]:
    return [
        {
            "state": "incident_received",
            "label": "Incident received",
            "training_signal": "episode starts with a real operational trigger",
        },
        {
            "state": "validated_authenticated",
            "label": "Validated and authenticated",
            "training_signal": "intake validity and tenant context are confirmed",
        },
        {
            "state": "enriched_with_service_context",
            "label": "Enriched with service context",
            "training_signal": "service ownership and deploy history are attached",
        },
        {
            "state": "evidence_retrieved",
            "label": "Evidence retrieved",
            "training_signal": "logs, metrics, and event trails are available",
        },
        {
            "state": "sentinel_classified",
            "label": "SENTINEL classified",
            "training_signal": "classification confidence and severity are scored",
        },
        {
            "state": "prism_diagnosed",
            "label": "PRISM diagnosed",
            "training_signal": "root-cause reasoning and evidence alignment are scored",
        },
        {
            "state": "forge_proposed_runbook",
            "label": "FORGE proposed runbook",
            "training_signal": "fix quality and rollback safety are scored",
        },
        {
            "state": "guardian_reviewed_safety",
            "label": "GUARDIAN reviewed safety",
            "training_signal": "approval quality and policy compliance are scored",
        },
        {
            "state": "executed_verified_learned",
            "label": "Outcome executed, verified, and learned",
            "training_signal": "execution result and reward become the training target",
        },
    ]
