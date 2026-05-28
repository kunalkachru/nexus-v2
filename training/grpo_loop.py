import random
import asyncio
from dataclasses import asdict, dataclass
from statistics import mean

from incidents.catalogue import load_incident_types
from server.models import NormalizedAlertEnvelope
from server.orchestrator import NexusCore
from training.curriculum import CurriculumAdapter
from training.policy import AdamScalarOptimizer, ScalarPolicy, TrainingStepRecord


@dataclass
class TrainingEpisodeRecord:
    """One deterministic training episode result."""

    episode_index: int
    incident_id: str
    difficulty: str
    reward: float
    environment_reward: float
    advantage: float
    cost_usd: float
    steps: list[TrainingStepRecord]

    def to_dict(self) -> dict[str, object]:
        """Serialize the record for JSON metrics output."""

        return {
            "episode_index": self.episode_index,
            "incident_id": self.incident_id,
            "difficulty": self.difficulty,
            "reward": self.reward,
            "environment_reward": self.environment_reward,
            "advantage": self.advantage,
            "cost_usd": self.cost_usd,
            "steps": [asdict(step) for step in self.steps],
        }


@dataclass
class TrainingSummary:
    """Aggregate output from a deterministic Day 6 training run."""

    reward_curve: list[float]
    cost_curve: list[float]
    episode_records: list[TrainingEpisodeRecord]
    difficulty_progression: list[str]
    final_difficulty: str
    total_cost_usd: float

    def to_dict(self) -> dict[str, object]:
        """Serialize the summary for reward-curve persistence."""

        return {
            "reward_curve": self.reward_curve,
            "cost_curve": self.cost_curve,
            "difficulty_progression": self.difficulty_progression,
            "final_difficulty": self.final_difficulty,
            "total_cost_usd": self.total_cost_usd,
            "episode_records": [record.to_dict() for record in self.episode_records],
        }


class GRPOTrainer:
    """Deterministic GRPO-style trainer over the Day 5 orchestrator."""

    def __init__(
        self,
        *,
        nexus_core: NexusCore,
        policies: dict[str, ScalarPolicy],
        curriculum: CurriculumAdapter,
        seed: int = 0,
        max_steps_per_episode: int = 20,
    ) -> None:
        self.nexus_core = nexus_core
        self.policies = policies
        self.curriculum = curriculum
        self.max_steps_per_episode = max_steps_per_episode
        self.rng = random.Random(seed)
        self.optimizers = {
            name: AdamScalarOptimizer(lr=1e-4) for name in policies
        }
        self.reward_curve: list[float] = []
        self.cost_curve: list[float] = []
        self.episode_records: list[TrainingEpisodeRecord] = []
        self._incidents = load_incident_types()

    def train(self, num_episodes: int = 30) -> TrainingSummary:
        """Run the deterministic training loop for the requested episode count."""

        for episode_index in range(num_episodes):
            incident = self._sample_incident()
            episode = asyncio.run(self.nexus_core.run_episode(self._alert_envelope_for_incident(incident)))
            environment_reward = episode.reward.composite if episode.reward is not None else 0.0
            policy_quality = mean(policy.probability() for policy in self.policies.values())
            reward = round(environment_reward * policy_quality, 6)
            baseline = mean(self.reward_curve[-5:]) if self.reward_curve else 0.2
            advantage = round(reward - baseline, 6)

            steps = self._build_step_records(episode, reward)
            self._update_policies(steps, advantage)

            cost_usd = round(episode.forge_output.estimated_cost_usd, 6)
            self.reward_curve.append(reward)
            self.cost_curve.append(cost_usd)
            self.curriculum.observe_reward(reward)
            self.episode_records.append(
                TrainingEpisodeRecord(
                    episode_index=episode_index,
                    incident_id=incident.id,
                    difficulty=self.curriculum.current_difficulty,
                    reward=reward,
                    environment_reward=round(environment_reward, 6),
                    advantage=advantage,
                    cost_usd=cost_usd,
                    steps=steps,
                )
            )

        return TrainingSummary(
            reward_curve=self.reward_curve,
            cost_curve=self.cost_curve,
            episode_records=self.episode_records,
            difficulty_progression=self.curriculum.progression,
            final_difficulty=self.curriculum.current_difficulty,
            total_cost_usd=round(sum(self.cost_curve), 6),
        )

    def _sample_incident(self):
        allowed = {
            "Easy": {"Easy"},
            "Medium": {"Easy", "Medium"},
            "Hard": {"Easy", "Medium", "Hard"},
            "Nightmare": {"Easy", "Medium", "Hard", "Nightmare"},
            "Impossible": {"Hard", "Nightmare"},
        }[self.curriculum.current_difficulty]
        pool = [incident for incident in self._incidents if incident.difficulty in allowed]
        return self.rng.choice(pool)

    def _alert_envelope_for_incident(self, incident) -> NormalizedAlertEnvelope:
        return NormalizedAlertEnvelope(
            source="datadog",
            external_id=incident.id,
            title=incident.name,
            severity={"P0": "P1", "P1": "P2", "P2": "P3"}[incident.severity],
            service=incident.system_context.service,
            detected_at="2026-05-28T09:14:00Z",
            observed_values={"service": incident.system_context.service},
        )

    def _build_step_records(self, episode, reward: float) -> list[TrainingStepRecord]:
        actions = [
            ("sentinel", episode.sentinel_output.incident_id),
            ("prism", episode.prism_output.root_cause),
            ("forge", episode.forge_output.runbook.language),
            ("guardian", episode.guardian_output.decision),
        ]
        contribution = round(reward / len(actions), 6)
        records = [
            TrainingStepRecord(
                agent_name=agent_name,
                action=action,
                log_prob=self.policies[agent_name].log_prob(),
                reward_contribution=contribution,
            )
            for agent_name, action in actions
        ]
        return records[: self.max_steps_per_episode]

    def _update_policies(self, steps: list[TrainingStepRecord], advantage: float) -> None:
        for step in steps:
            policy = self.policies[step.agent_name]
            optimizer = self.optimizers[step.agent_name]
            probability = policy.probability()
            gradient = -advantage * max(0.05, 1.0 - probability)
            optimizer.step(policy, gradient)
