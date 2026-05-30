import argparse
import asyncio
import json
from pathlib import Path

from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent
from server.orchestrator import NexusCore
from server.artifacts import record_learning_contract, record_training_snapshot
from server.services.observability import ObservabilityService
from training.curriculum import CurriculumAdapter
from training.grpo_loop import GRPOTrainer, TrainingSummary
from training.policy import ScalarPolicy


class TrainingForgeClient:
    """Deterministic Forge client used for Day 6 offline training."""

    def generate_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        incident_id = user_prompt.split("Incident ID:", maxsplit=1)[1].splitlines()[0].strip()
        return {
            "language": "bash",
            "summary": f"Training runbook for {incident_id}",
            "code": "set -e\nprintf 'stabilize service\\n'\n",
            "estimated_cost_usd": 0.12,
        }


def load_agent_policies() -> dict[str, ScalarPolicy]:
    """Load the default Day 6 scalar policies for each agent."""

    return {
        "sentinel": ScalarPolicy(name="sentinel", weight=-0.0007),
        "prism": ScalarPolicy(name="prism", weight=-0.0007),
        "forge": ScalarPolicy(name="forge", weight=-0.0007),
        "guardian": ScalarPolicy(name="guardian", weight=-0.0007),
    }


def run_training(
    *,
    num_episodes: int = 30,
    seed: int = 0,
    save_curve_path: Path | None = None,
    policies: dict[str, ScalarPolicy] | None = None,
) -> TrainingSummary:
    """Run deterministic Day 6 training and optionally persist the reward curve."""

    policies = policies or load_agent_policies()
    core = NexusCore(
        observability=ObservabilityService(),
        sentinel=SentinelAgent(),
        prism=PrismAgent(),
        forge=ForgeAgent(client=TrainingForgeClient()),
        guardian=GuardianAgent(),
    )
    trainer = GRPOTrainer(
        nexus_core=core,
        policies=policies,
        curriculum=CurriculumAdapter(),
        seed=seed,
        max_steps_per_episode=20,
    )
    summary = trainer.train(num_episodes=num_episodes)

    asyncio.run(record_training_snapshot(summary.to_dict()))
    if summary.rl_episode_contract:
        asyncio.run(record_learning_contract(summary.rl_episode_contract))

    if save_curve_path is not None:
        from training.reporting import build_metrics_payload

        save_curve_path = Path(save_curve_path)
        save_curve_path.write_text(json.dumps(build_metrics_payload(summary), indent=2))

    return summary


def main() -> None:
    """CLI entrypoint for deterministic Day 6 training runs."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--save-curve", type=Path, default=None)
    args = parser.parse_args()

    summary = run_training(
        num_episodes=args.episodes,
        seed=args.seed,
        save_curve_path=args.save_curve,
    )
    print(json.dumps(summary.to_dict(), indent=2))


if __name__ == "__main__":
    main()
