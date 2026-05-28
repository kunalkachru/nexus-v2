from incidents.catalogue import load_incident_types
from server.grader import compute_episode_reward
from server.models import (
    Episode,
    ForgeRunbookResult,
    GuardianReviewResult,
    PrismDiagnosis,
    RunbookScript,
    SentinelClassification,
)


SEVERITY_MAP = {"P0": "P1", "P1": "P2", "P2": "P3"}


def _build_episode(*, predicted_severity: str, duration_minutes: float = 8.0, incident_index: int = 0) -> Episode:
    incident = load_incident_types()[incident_index]
    return Episode(
        incident=incident,
        sentinel_output=SentinelClassification(
            incident_id=incident.id,
            incident_name=incident.name,
            severity=predicted_severity,
            confidence=0.95,
            reasoning="fixture",
        ),
        prism_output=PrismDiagnosis(
            incident_id=incident.id,
            root_cause=incident.root_cause,
            confidence=0.91,
            evidence=incident.symptoms[:2],
            queried_sources=["logs", "metrics"],
            reasoning="fixture",
        ),
        forge_output=ForgeRunbookResult(
            incident_id=incident.id,
            runbook=RunbookScript(
                language="bash",
                summary="fixture",
                code="set -e\nprintf 'ok\\n'\n",
            ),
            syntax_valid=True,
            model_name="gpt-4o",
            estimated_cost_usd=0.12,
            reasoning="fixture",
        ),
        guardian_output=GuardianReviewResult(
            decision="approve",
            safety_score=0.95,
            blocked_patterns=[],
            reasoning="fixture",
        ),
        duration_minutes=duration_minutes,
        verification_passed=True,
        executed=True,
        status="resolved",
        communication_events=4,
        customer_impact_minutes=5.0,
        steps=["sentinel", "prism", "forge", "guardian", "verify"],
    )


def test_reward_is_deterministic() -> None:
    episode = _build_episode(predicted_severity=SEVERITY_MAP[load_incident_types()[0].severity])

    first = compute_episode_reward(episode)
    second = compute_episode_reward(episode)

    assert first == second


def test_reward_is_asymmetric() -> None:
    incident = load_incident_types()[1]
    exact = compute_episode_reward(
        _build_episode(predicted_severity=SEVERITY_MAP[incident.severity], incident_index=1)
    )
    over = compute_episode_reward(_build_episode(predicted_severity="P1", incident_index=1))
    under = compute_episode_reward(_build_episode(predicted_severity="P3", incident_index=1))

    assert exact.composite > over.composite
    assert over.composite > under.composite
    assert under.severity_penalty > over.severity_penalty


def test_reward_dimensions_are_bounded() -> None:
    incident = load_incident_types()[0]
    reward = compute_episode_reward(_build_episode(predicted_severity=SEVERITY_MAP[incident.severity]))

    assert 0.0 <= reward.mttr <= 1.0
    assert 0.0 <= reward.diagnosis <= 1.0
    assert 0.0 <= reward.customer <= 1.0
    assert 0.0 <= reward.coordination <= 1.0
    assert 0.0 <= reward.oversight <= 1.0
    assert 0.0 <= reward.composite <= 1.0
