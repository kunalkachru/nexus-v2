import asyncio

from incidents.catalogue import load_incident_types
from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent
from server.models import NormalizedAlertEnvelope
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


class FakeObservabilityService:
    def __init__(self, incident) -> None:
        self.incident = incident
        self.envelopes: list[NormalizedAlertEnvelope] = []

    async def fetch_incident_context(self, alert_envelope: NormalizedAlertEnvelope):
        self.envelopes.append(alert_envelope)
        return type(
            "IncidentContextFixture",
            (),
            {
                "incident": self.incident,
                "incident_id": self.incident.id,
                "raw_symptoms": list(self.incident.symptoms),
                "system_context": self.incident.system_context,
                "signals": {
                    "logs": [self.incident.symptoms[0]],
                    "metrics": [self.incident.symptoms[1]],
                    "deployment": [],
                },
            },
        )()


def test_run_episode_routes_through_all_agents() -> None:
    async def scenario() -> None:
        incident = load_incident_types()[0]
        observability = FakeObservabilityService(incident)
        core = NexusCore(
            observability=observability,
            sentinel=SentinelAgent(),
            prism=PrismAgent(),
            forge=ForgeAgent(client=SafeForgeClient()),
            guardian=GuardianAgent(),
        )

        episode = await core.run_episode(
            NormalizedAlertEnvelope(
                source="datadog",
                external_id=incident.id,
                title=incident.name,
                severity="P1",
                service=incident.system_context.service,
                detected_at="2026-05-28T09:14:00Z",
                observed_values={"service": incident.system_context.service},
            )
        )

        assert episode.sentinel_output.incident_id == incident.id
        assert episode.prism_output.root_cause == incident.root_cause
        assert episode.forge_output.syntax_valid is True
        assert episode.guardian_output.decision == "approve"
        assert episode.verification_passed is True
        assert episode.reward is not None
        assert 0.0 <= episode.reward.composite <= 1.0
        assert observability.envelopes[0].external_id == incident.id

    asyncio.run(scenario())


def test_run_episode_blocks_dangerous_runbook() -> None:
    async def scenario() -> None:
        incident = load_incident_types()[0]
        observability = FakeObservabilityService(incident)
        core = NexusCore(
            observability=observability,
            sentinel=SentinelAgent(),
            prism=PrismAgent(),
            forge=ForgeAgent(client=DangerousForgeClient()),
            guardian=GuardianAgent(),
        )

        episode = await core.run_episode(
            NormalizedAlertEnvelope(
                source="datadog",
                external_id=incident.id,
                title=incident.name,
                severity="P1",
                service=incident.system_context.service,
                detected_at="2026-05-28T09:14:00Z",
                observed_values={"service": incident.system_context.service},
            )
        )

        assert episode.guardian_output.decision == "reject"
        assert episode.status == "blocked_by_guardian"
        assert episode.executed is False
        assert episode.verification_passed is False
        assert episode.reward is not None
        assert observability.envelopes[0].external_id == incident.id

    asyncio.run(scenario())
