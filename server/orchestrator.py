from collections.abc import Callable

from server.agents.forge import ForgeAgent
from server.agents.guardian import GuardianAgent
from server.agents.prism import PrismAgent
from server.agents.sentinel import SentinelAgent
from server.grader import compute_episode_reward
from server.models import Episode, IncidentDefinition, NormalizedAlertEnvelope
from server.services.observability import ObservabilityService


class NexusCore:
    """Deterministic Day 5 orchestrator for a full incident response episode."""

    def __init__(
        self,
        *,
        observability: ObservabilityService,
        sentinel: SentinelAgent,
        prism: PrismAgent,
        forge: ForgeAgent,
        guardian: GuardianAgent,
        episode_sink: Callable[[Episode], None] | None = None,
    ) -> None:
        self.observability = observability
        self.sentinel = sentinel
        self.prism = prism
        self.forge = forge
        self.guardian = guardian
        self.episode_sink = episode_sink

    async def run_episode(self, alert_envelope: NormalizedAlertEnvelope) -> Episode:
        """Run the four-agent flow from an alert envelope and fetched evidence context."""

        context = await self.observability.fetch_incident_context(alert_envelope)
        incident = context.incident
        sentinel_output = self.sentinel.classify(
            raw_symptoms=context.raw_symptoms,
            system_context=context.system_context,
        )
        prism_output = await self.prism.diagnose(
            sentinel_output=sentinel_output,
            signals=context.signals,
        )
        forge_output = await self.forge.generate_runbook(
            prism_output=prism_output,
            system_context=context.system_context,
        )
        guardian_output = await self.guardian.review(
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
        if self.episode_sink is not None:
            self.episode_sink(episode)
        return episode


def _duration_for_incident(incident: IncidentDefinition, *, executed: bool) -> float:
    base_duration = {
        "Easy": 6.0,
        "Medium": 10.0,
        "Hard": 15.0,
        "Nightmare": 22.0,
    }[incident.difficulty]
    return base_duration if executed else base_duration + 8.0
