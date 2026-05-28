from server.agents.forge import ForgeAgent
from server.agents.guardian import GuardianAgent
from server.agents.prism import PrismAgent
from server.agents.sentinel import SentinelAgent
from server.grader import compute_episode_reward
from server.models import Episode, IncidentDefinition


class NexusCore:
    """Deterministic Day 5 orchestrator for a full incident response episode."""

    def __init__(
        self,
        *,
        sentinel: SentinelAgent,
        prism: PrismAgent,
        forge: ForgeAgent,
        guardian: GuardianAgent,
    ) -> None:
        self.sentinel = sentinel
        self.prism = prism
        self.forge = forge
        self.guardian = guardian

    def run_episode(self, incident: IncidentDefinition) -> Episode:
        """Run the four-agent flow and compute a deterministic reward."""

        sentinel_output = self.sentinel.classify(
            raw_symptoms=incident.symptoms,
            system_context=incident.system_context,
        )
        prism_output = self.prism.diagnose(
            sentinel_output=sentinel_output,
            signals=incident.symptoms,
        )
        forge_output = self.forge.generate_runbook(
            prism_output=prism_output,
            system_context=incident.system_context,
        )
        guardian_output = self.guardian.review(
            forge_output=forge_output,
            sentinel_output=sentinel_output,
            prism_output=prism_output,
        )

        executed = guardian_output.decision == "approve"
        verification_passed = executed and forge_output.syntax_valid
        status = "resolved" if verification_passed else "blocked_by_guardian"
        duration_minutes = _duration_for_incident(incident, executed=executed)

        episode = Episode(
            incident=incident,
            sentinel_output=sentinel_output,
            prism_output=prism_output,
            forge_output=forge_output,
            guardian_output=guardian_output,
            duration_minutes=duration_minutes,
            verification_passed=verification_passed,
            executed=executed,
            status=status,
            communication_events=4 if verification_passed else 2,
            customer_impact_minutes=5.0 if verification_passed else 20.0,
            steps=["sentinel", "prism", "forge", "guardian", "verify"],
        )
        episode.reward = compute_episode_reward(episode)
        return episode


def _duration_for_incident(incident: IncidentDefinition, *, executed: bool) -> float:
    base_duration = {
        "Easy": 6.0,
        "Medium": 10.0,
        "Hard": 15.0,
        "Nightmare": 22.0,
    }[incident.difficulty]
    return base_duration if executed else base_duration + 8.0
