import json
import os
import time
from pathlib import Path

from incidents.catalogue import load_incident_types
from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent
from server.orchestrator import NexusCore
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


def run_demo(*, print_output: bool = False) -> dict[str, object]:
    metrics = ensure_metrics_payload()
    checkpoint = load_checkpoint()
    incident = load_incident_types()[2]
    core = NexusCore(
        sentinel=SentinelAgent(),
        prism=PrismAgent(),
        forge=ForgeAgent(client=_forge_client()),
        guardian=GuardianAgent(),
    )

    started_at = time.perf_counter()
    episode = core.run_episode(incident)
    execution_time_seconds = round(time.perf_counter() - started_at, 4)

    result = {
        "checkpoint_path": str(CHECKPOINT_PATH),
        "metrics_path": str(METRICS_PATH),
        "checkpoint_final_difficulty": checkpoint["final_difficulty"],
        "trained_reward": checkpoint["reward_curve"][-1],
        "classification": {
            "incident_id": episode.sentinel_output.incident_id,
            "severity": episode.sentinel_output.severity,
            "confidence": round(episode.sentinel_output.confidence, 4),
        },
        "diagnosis": {
            "root_cause": episode.prism_output.root_cause,
            "confidence": round(episode.prism_output.confidence, 4),
        },
        "runbook": {
            "language": episode.forge_output.runbook.language,
            "summary": episode.forge_output.runbook.summary,
            "cost_usd": round(episode.forge_output.estimated_cost_usd, 2),
        },
        "execution_result": "executed" if episode.executed else episode.status,
        "final_reward": round(episode.reward.composite if episode.reward else 0.0, 4),
        "execution_time_seconds": execution_time_seconds,
        "reward_curve_target": metrics["summary"]["trained_reward"],
    }

    if print_output:
        print("NEXUS v2 Judge Demo")
        print(f"Checkpoint: {result['checkpoint_path']}")
        print(f"Classification: {result['classification']}")
        print(f"Diagnosis: {result['diagnosis']}")
        print(f"Runbook: {result['runbook']}")
        print(f"Execution Result: {result['execution_result']}")
        print(f"Final Reward: {result['final_reward']}")
        print(f"Execution Time Seconds: {result['execution_time_seconds']}")

    return result


def main() -> None:
    run_demo(print_output=True)


if __name__ == "__main__":
    main()
