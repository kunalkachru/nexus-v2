from incidents.catalogue import load_incident_types
from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent
from server.orchestrator import NexusCore


class SafeForgeClient:
    def generate_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        incident_id = user_prompt.split("Incident ID:", maxsplit=1)[1].splitlines()[0].strip()
        return {
            "language": "bash",
            "summary": f"Runbook for {incident_id}",
            "code": "set -e\nprintf 'verify service\\n'\n",
            "estimated_cost_usd": 0.12,
        }


class DangerousForgeClient:
    def generate_json(self, *, model: str, system_prompt: str, user_prompt: str) -> dict[str, object]:
        incident_id = user_prompt.split("Incident ID:", maxsplit=1)[1].splitlines()[0].strip()
        return {
            "language": "bash",
            "summary": f"Dangerous runbook for {incident_id}",
            "code": "rm -rf /\n",
            "estimated_cost_usd": 0.12,
        }


def test_run_episode_routes_through_all_agents() -> None:
    incident = load_incident_types()[0]
    core = NexusCore(
        sentinel=SentinelAgent(),
        prism=PrismAgent(),
        forge=ForgeAgent(client=SafeForgeClient()),
        guardian=GuardianAgent(),
    )

    episode = core.run_episode(incident)

    assert episode.sentinel_output.incident_id == incident.id
    assert episode.prism_output.root_cause == incident.root_cause
    assert episode.forge_output.syntax_valid is True
    assert episode.guardian_output.decision == "approve"
    assert episode.verification_passed is True
    assert episode.reward is not None
    assert 0.0 <= episode.reward.composite <= 1.0


def test_run_episode_blocks_dangerous_runbook() -> None:
    incident = load_incident_types()[0]
    core = NexusCore(
        sentinel=SentinelAgent(),
        prism=PrismAgent(),
        forge=ForgeAgent(client=DangerousForgeClient()),
        guardian=GuardianAgent(),
    )

    episode = core.run_episode(incident)

    assert episode.guardian_output.decision == "reject"
    assert episode.status == "blocked_by_guardian"
    assert episode.executed is False
    assert episode.verification_passed is False
    assert episode.reward is not None
