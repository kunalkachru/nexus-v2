import json
import os
import time
import asyncio

from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent
from server.config import AppConfig
from server.incident_payloads import get_incident_definition, get_incident_details
from server.models import NormalizedAlertEnvelope
from server.orchestrator import NexusCore
from server.services.observability import ObservabilityService
from training.reporting import CHECKPOINT_PATH, METRICS_PATH, ensure_metrics_payload, load_checkpoint
from training.runner import TrainingForgeClient


class OpenAIForgeClient:
    """Optional live OpenAI backend for FORGE."""

    def generate_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "forge_runbook",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "language": {"type": "string"},
                            "summary": {"type": "string"},
                            "code": {"type": "string"},
                            "estimated_cost_usd": {"type": "number"},
                        },
                        "required": ["language", "summary", "code", "estimated_cost_usd"],
                        "additionalProperties": False,
                    },
                }
            },
        )
        return json.loads(response.output_text)


def _forge_client():
    if os.environ.get("NEXUS_USE_OPENAI") == "1" and os.environ.get("OPENAI_API_KEY"):
        return OpenAIForgeClient()
    return TrainingForgeClient()


def run_demo(*, incident_id: str = "INC001", print_output: bool = False) -> dict[str, object]:
    metrics = ensure_metrics_payload()
    checkpoint = load_checkpoint()
    incident = get_incident_definition(incident_id)
    incident_details = get_incident_details(incident_id)
    config = AppConfig()
    core = NexusCore(
        observability=ObservabilityService(),
        sentinel=SentinelAgent(),
        prism=PrismAgent(),
        forge=ForgeAgent(client=_forge_client(), model_name=config.forge_model_name),
        guardian=GuardianAgent(),
    )

    started_at = time.perf_counter()
    episode = asyncio.run(
        core.run_episode(
            NormalizedAlertEnvelope(
                source="datadog",
                external_id=incident.id,
                title=incident.name,
                severity={"P0": "P1", "P1": "P2", "P2": "P3"}[incident.severity],
                service=incident.system_context.service,
                detected_at=str(incident_details["detected_at"]),
                observed_values={"service": incident.system_context.service},
            )
        )
    )
    execution_time_seconds = round(time.perf_counter() - started_at, 4)

    sentinel_details = incident_details["sentinel"]
    prism_details = incident_details["prism"]
    forge_details = incident_details["forge"]
    guardian_details = incident_details["guardian"]

    result = {
        "checkpoint_path": str(CHECKPOINT_PATH),
        "metrics_path": str(METRICS_PATH),
        "checkpoint_final_difficulty": checkpoint["final_difficulty"],
        "trained_reward": checkpoint["reward_curve"][-1],
        "incident": {
            "id": incident.id,
            "name": incident.name,
            "severity": episode.sentinel_output.severity,
            "summary": incident_details["summary"],
            "detected_at": incident_details["detected_at"],
            "related_services": incident_details["related_services"],
            "recent_deployments": incident_details["recent_deployments"],
            "similar_past_incidents": incident_details["similar_past_incidents"],
        },
        "observability": {
            "metrics": incident_details["metrics"],
            "recent_logs": incident_details["recent_logs"],
            "alert_timeline": incident_details["alert_timeline"],
            "recommended_runbooks": incident_details["recommended_runbooks"],
        },
        "classification": {
            "incident_id": episode.sentinel_output.incident_id,
            "incident_name": episode.sentinel_output.incident_name,
            "severity": episode.sentinel_output.severity,
            "confidence": sentinel_details["confidence"],
            "confidence_breakdown": sentinel_details["confidence_breakdown"],
            "evidence": sentinel_details["evidence"],
            "reasoning": sentinel_details["reasoning"],
        },
        "diagnosis": {
            "root_cause": episode.prism_output.root_cause,
            "confidence": prism_details["confidence"],
            "supporting_logs": prism_details["log_snippets"],
            "correlation_analysis": prism_details["correlation_analysis"],
            "reasoning": prism_details["reasoning"],
        },
        "runbook": {
            "language": episode.forge_output.runbook.language,
            "summary": episode.forge_output.runbook.summary,
            "selection_logic": forge_details["selection_logic"],
            "candidate_fixes": forge_details["candidate_fixes"],
            "recommended_runbook": forge_details["recommended_runbook"],
            "reasoning": forge_details["reasoning"],
            "cost_usd": round(episode.forge_output.estimated_cost_usd, 2),
        },
        "guardian": {
            "decision": guardian_details["decision"],
            "confidence": guardian_details["confidence"],
            "safety_checks": guardian_details["safety_checks"],
            "policy_violations": guardian_details["policy_violations"],
            "reasoning": guardian_details["reasoning"],
        },
        "execution_result": "executed" if episode.executed else episode.status,
        "final_reward": round(episode.reward.composite if episode.reward else 0.0, 4),
        "execution_time_seconds": execution_time_seconds,
        "reward_curve_target": metrics["summary"]["trained_reward"],
    }

    if print_output:
        print("NEXUS v2 Judge Demo")
        print(f"Incident: {result['incident']['id']} - {result['incident']['name']}")
        print(f"Checkpoint: {result['checkpoint_path']}")
        print(f"Classification: {result['classification']}")
        print(f"Diagnosis: {result['diagnosis']}")
        print(f"Runbook: {result['runbook']}")
        print(f"Guardian: {result['guardian']}")
        print(f"Execution Result: {result['execution_result']}")
        print(f"Final Reward: {result['final_reward']}")
        print(f"Execution Time Seconds: {result['execution_time_seconds']}")

    return result


def main() -> None:
    run_demo(print_output=True)


if __name__ == "__main__":
    main()
