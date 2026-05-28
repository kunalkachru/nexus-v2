from __future__ import annotations

from training.policy import ScalarPolicy, TrainingStepRecord


def extract_trajectory(episode, policies: dict[str, ScalarPolicy]) -> list[TrainingStepRecord]:
    actions = [
        ("sentinel", episode.sentinel_output.incident_id),
        ("prism", episode.prism_output.root_cause),
        ("forge", episode.forge_output.runbook.language),
        ("guardian", episode.guardian_output.decision),
    ]
    contribution = round((episode.reward.composite if episode.reward else 0.0) / len(actions), 6)
    return [
        TrainingStepRecord(
            agent_name=agent_name,
            action=action,
            log_prob=policies[agent_name].log_prob(),
            reward_contribution=contribution,
            observation_digest=_observation_digest(agent_name, episode),
        )
        for agent_name, action in actions
    ]


def compute_group_advantages(trajectory: list[TrainingStepRecord], reward: float) -> dict[str, float]:
    if not trajectory:
        return {}

    baseline = reward / len(trajectory)
    advantages: dict[str, float] = {}
    for step in trajectory:
        advantages[step.agent_name] = round(reward - baseline + step.reward_contribution, 6)
    return advantages


def _observation_digest(agent_name: str, episode) -> str:
    incident = episode.incident
    service = incident.system_context.service
    if agent_name == "sentinel":
        return f"{incident.id}:{service}:{episode.sentinel_output.severity}"
    if agent_name == "prism":
        return f"{incident.id}:{episode.prism_output.root_cause[:48]}"
    if agent_name == "forge":
        return f"{incident.id}:{episode.forge_output.runbook.language}:{service}"
    return f"{incident.id}:{episode.guardian_output.decision}:{episode.status}"
