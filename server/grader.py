from server.models import Episode, EpisodeReward
from server.services.priority import priority_rank

def compute_episode_reward(episode: Episode) -> EpisodeReward:
    """Compute a deterministic 5-dimensional reward for a completed episode."""

    expected_severity = _expected_severity(episode.incident.severity)
    mttr = _bounded(1.0 - (episode.duration_minutes / 30.0))
    diagnosis = 1.0 if episode.prism_output.root_cause == episode.incident.root_cause else 0.0
    customer = _bounded(
        (1.0 if episode.verification_passed else 0.2)
        - min(episode.customer_impact_minutes, 30.0) / 60.0
    )
    coordination = _bounded(min(episode.communication_events, 5) / 5.0)
    oversight = episode.guardian_output.safety_score if episode.guardian_output.decision == "approve" else 0.5
    severity_penalty = _severity_penalty(
        predicted=episode.sentinel_output.severity,
        expected=expected_severity,
    )

    weighted = (
        mttr * 0.30
        + diagnosis * 0.25
        + customer * 0.20
        + coordination * 0.15
        + oversight * 0.05
    )
    composite = _bounded(weighted - severity_penalty)

    return EpisodeReward(
        mttr=mttr,
        diagnosis=diagnosis,
        customer=customer,
        coordination=coordination,
        oversight=oversight,
        severity_penalty=severity_penalty,
        composite=composite,
    )


def _severity_penalty(*, predicted: str, expected: str) -> float:
    predicted_value = priority_rank(predicted)
    expected_value = priority_rank(expected)

    if predicted_value == expected_value:
        return 0.0
    if predicted_value < expected_value:
        return 0.10 * (expected_value - predicted_value)
    return 0.20 * (predicted_value - expected_value)


def _expected_severity(severity: str) -> str:
    normalized = str(severity).strip().upper()
    if normalized == "P0":
        return "P1"
    if normalized.startswith("P") and normalized[1:].isdigit():
        return f"P{int(normalized[1:]) + 1}"
    return normalized


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, round(value, 6)))
