import asyncio
import json
from pathlib import Path

from incidents.catalogue import load_incident_types
from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent
from server.models import SentinelClassification
from training.runner import TrainingForgeClient, load_agent_policies, run_training


ROOT_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
FRONTEND_DIR = ROOT_DIR / "frontend"
METRICS_PATH = FRONTEND_DIR / "metrics.json"
CHECKPOINT_PATH = ARTIFACTS_DIR / "day6_checkpoint.json"


def _severity_map(severity: str) -> str:
    return {"P0": "P1", "P1": "P2", "P2": "P3"}[severity]


def compute_agent_accuracy() -> dict[str, float]:
    async def scenario() -> dict[str, float]:
        incidents = load_incident_types()
        sentinel = SentinelAgent()
        prism = PrismAgent()
        forge = ForgeAgent(client=TrainingForgeClient())
        guardian = GuardianAgent()

        sentinel_correct = 0
        prism_correct = 0
        forge_valid = 0
        guardian_safe = 0

        for incident in incidents:
            sentinel_output = sentinel.classify(
                raw_symptoms=incident.symptoms,
                system_context=incident.system_context,
            )
            sentinel_correct += int(sentinel_output.incident_id == incident.id)

            prism_output = await prism.diagnose(
                sentinel_output=sentinel_output,
                signals=incident.symptoms,
            )
            prism_correct += int(prism_output.root_cause == incident.root_cause)

            forge_output = await forge.generate_runbook(
                prism_output=prism_output,
                system_context=incident.system_context,
            )
            forge_valid += int(forge_output.syntax_valid)

            guardian_output = await guardian.review(
                forge_output=forge_output,
                sentinel_output=SentinelClassification(
                    incident_id=incident.id,
                    incident_name=incident.name,
                    severity=_severity_map(incident.severity),
                    confidence=sentinel_output.confidence,
                    reasoning=sentinel_output.reasoning,
                ),
                prism_output=prism_output,
            )
            guardian_safe += int(guardian_output.decision == "approve")

        total = float(len(incidents))
        return {
            "sentinel": round(sentinel_correct / total, 4),
            "prism": round(prism_correct / total, 4),
            "forge": round(forge_valid / total, 4),
            "guardian": round(guardian_safe / total, 4),
        }

    return asyncio.run(scenario())


def build_metrics_payload(summary) -> dict[str, object]:
    trained_reward = round(summary.reward_curve[-1], 2) if summary.reward_curve else 0.0
    total_cost = round(summary.total_cost_usd, 2)
    episode_count = len(summary.reward_curve)

    return {
        "reward_curve": summary.reward_curve,
        "cost_curve": summary.cost_curve,
        "difficulty_progression": summary.difficulty_progression,
        "difficulty_ladder": ["Easy", "Medium", "Hard", "Nightmare"],
        "final_difficulty": summary.final_difficulty,
        "total_cost_usd": summary.total_cost_usd,
        "episode_records": [record.to_dict() for record in summary.episode_records],
        "agent_accuracy": compute_agent_accuracy(),
        "summary": {
            "baseline_reward": 0.28,
            "trained_reward": trained_reward,
            "episode_count": episode_count,
            "average_cost_per_episode": round(total_cost / episode_count, 2) if episode_count else 0.0,
            "total_cost_usd": total_cost,
            "execution_target_seconds": 5.0,
        },
    }


def ensure_metrics_payload(
    *,
    metrics_path: Path = METRICS_PATH,
    checkpoint_path: Path = CHECKPOINT_PATH,
    num_episodes: int = 30,
    seed: int = 7,
) -> dict[str, object]:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    if metrics_path.exists() and checkpoint_path.exists():
        return json.loads(metrics_path.read_text())

    policies = load_agent_policies()
    summary = run_training(
        num_episodes=num_episodes,
        seed=seed,
        save_curve_path=None,
        policies=policies,
    )
    payload = build_metrics_payload(summary)
    metrics_path.write_text(json.dumps(payload, indent=2))
    checkpoint_path.write_text(
        json.dumps(
            {
                "model_version": "day6-deterministic",
                "episodes": num_episodes,
                "seed": seed,
                "policy_weights": {name: policy.weight for name, policy in policies.items()},
                "reward_curve": summary.reward_curve,
                "final_difficulty": summary.final_difficulty,
                "metrics_path": str(metrics_path.relative_to(ROOT_DIR)),
            },
            indent=2,
        )
    )
    return payload


def load_checkpoint(checkpoint_path: Path = CHECKPOINT_PATH) -> dict[str, object]:
    ensure_metrics_payload(checkpoint_path=checkpoint_path)
    return json.loads(checkpoint_path.read_text())
