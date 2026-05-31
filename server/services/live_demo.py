from __future__ import annotations

import os
import time

from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent
from server.agents.live_clients import OpenAIForgeClient, OpenAIPrismClient, OpenAISentinelClient
from server.config import AppConfig
from server.incident_payloads import get_incident_definition, get_incident_details
from server.models import NormalizedAlertEnvelope
from server.openai_keys import build_llm_access
from server.orchestrator import NexusCore
from server.integrations.deployments import DeploymentLookupService
from server.services.observability import ObservabilityService
from server.services.result_contracts import build_structured_result
from server.services.surface_payloads import build_incident_response
from server.services.priority import priority_snapshot, shift_priority_label
from training.runner import TrainingForgeClient


def _shift_severity(severity: str) -> str:
    return shift_priority_label(severity)


async def build_demo_payload(
    incident_id: str = "INC001",
    *,
    live_reasoning_override: bool | None = None,
    openai_api_key: str | None = None,
) -> dict[str, object]:
    """Build a demo incident payload, optionally with live LLM-backed agents."""

    config = AppConfig()
    server_key = os.environ.get("OPENAI_API_KEY", "").strip()
    effective_key = openai_api_key or server_key
    use_live_llm = (config.use_live_llm and bool(server_key)) or bool(openai_api_key)
    if live_reasoning_override is not None:
        use_live_llm = live_reasoning_override and bool(effective_key)
    incident = get_incident_definition(incident_id)
    details = get_incident_details(incident_id)
    base = build_incident_response(incident_id)

    sentinel_client = OpenAISentinelClient(api_key=effective_key) if use_live_llm else None
    prism_client = OpenAIPrismClient(api_key=effective_key) if use_live_llm else None
    forge_client = OpenAIForgeClient(api_key=effective_key) if use_live_llm else TrainingForgeClient()

    core = NexusCore(
        observability=ObservabilityService(deployment_lookup=DeploymentLookupService()),
        sentinel=SentinelAgent(client=sentinel_client, model_name=config.forge_model_name),
        prism=PrismAgent(client=prism_client, model_name=config.forge_model_name),
        forge=ForgeAgent(client=forge_client, model_name=config.forge_model_name),
        guardian=GuardianAgent(),
    )

    started_at = time.perf_counter()
    alert_envelope = NormalizedAlertEnvelope(
        source="datadog",
        external_id=incident.id,
        title=incident.name,
        severity=_shift_severity(incident.severity),
        service=incident.system_context.service,
        detected_at=str(details["detected_at"]),
        observed_values={"service": incident.system_context.service},
    )
    priority = priority_snapshot(alert_envelope.severity)
    try:
        episode = await core.run_episode(alert_envelope)
    except Exception:
        if not use_live_llm:
            raise
        use_live_llm = False
        sentinel_client = None
        prism_client = None
        forge_client = TrainingForgeClient()
        core = NexusCore(
            observability=ObservabilityService(deployment_lookup=DeploymentLookupService()),
            sentinel=SentinelAgent(client=sentinel_client, model_name=config.forge_model_name),
            prism=PrismAgent(client=prism_client, model_name=config.forge_model_name),
            forge=ForgeAgent(client=forge_client, model_name=config.forge_model_name),
            guardian=GuardianAgent(),
        )
        episode = await core.run_episode(alert_envelope)
    execution_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

    payload = dict(base)
    payload["incident"] = {
        **base["incident"],
        "summary": details["summary"],
        "detected_at": details["detected_at"],
        "recent_deployments": details["recent_deployments"],
        "similar_past_incidents": details["similar_past_incidents"],
    }
    payload["classification"] = {
        **base["classification"],
        "incident_id": episode.sentinel_output.incident_id,
        "incident_name": episode.sentinel_output.incident_name,
        "severity": episode.sentinel_output.severity,
        "confidence": episode.sentinel_output.confidence,
        "reasoning": episode.sentinel_output.reasoning,
    }
    payload["diagnosis"] = {
        **base["diagnosis"],
        "root_cause": episode.prism_output.root_cause,
        "confidence": episode.prism_output.confidence,
        "supporting_logs": episode.prism_output.evidence or base["diagnosis"]["supporting_logs"],
        "correlation_analysis": episode.prism_output.reasoning,
        "reasoning": episode.prism_output.reasoning,
    }
    payload["runbook"] = {
        **base["runbook"],
        "language": episode.forge_output.runbook.language,
        "summary": episode.forge_output.runbook.summary,
        "proposed_fix": episode.forge_output.runbook.summary,
        "recommended_runbook": episode.forge_output.runbook.summary,
        "reasoning": episode.forge_output.reasoning,
        "cost_usd": round(episode.forge_output.estimated_cost_usd, 2),
    }
    payload["guardian"] = {
        **base["guardian"],
        "decision": episode.guardian_output.decision,
        "confidence": episode.guardian_output.safety_score,
        "safety_checks": base["guardian"]["safety_checks"]
        + [f"LLM-backed {episode.prism_output.root_cause}", f"Model {episode.forge_output.model_name}"],
        "policy_violations": episode.guardian_output.blocked_patterns,
        "reasoning": episode.guardian_output.reasoning,
        "policy_id": episode.guardian_output.policy_id,
        "policy_name": episode.guardian_output.policy_name,
        "policy_basis": episode.guardian_output.policy_basis,
    }
    payload["execution_result"] = "executed" if episode.executed else episode.status
    payload["reward"] = episode.reward.composite if episode.reward else base["reward"]
    payload["execution_time_ms"] = execution_time_ms
    payload["agent_models"] = {
        "sentinel": config.forge_model_name if use_live_llm else "deterministic",
        "prism": config.forge_model_name if use_live_llm else "deterministic",
        "forge": episode.forge_output.model_name,
        "guardian": "deterministic",
    }
    payload["structured_result"] = build_structured_result(
        incident_id=incident.id,
        root_cause=episode.prism_output.root_cause,
        proposed_fix=episode.forge_output.runbook.summary,
        safety_decision=episode.guardian_output.decision,
        confidence=round(episode.guardian_output.safety_score, 2),
        execution_status=payload["execution_result"],
        live_reasoning=use_live_llm,
        raw_priority_label=priority["raw_label"],
        normalized_priority_label=priority["normalized_label"],
        normalized_priority_rank=priority["rank"],
        reward=round(payload["reward"], 2),
        guardian_policy_id=episode.guardian_output.policy_id,
        guardian_policy_name=episode.guardian_output.policy_name,
        guardian_policy_basis=episode.guardian_output.policy_basis,
    )
    payload["live_reasoning"] = use_live_llm
    payload["llm_access"] = build_llm_access(
        live_reasoning_requested=bool(live_reasoning_override),
        user_key_provided=bool(openai_api_key),
        server_key_available=bool(server_key),
        live_reasoning_active=use_live_llm,
    )
    return payload
