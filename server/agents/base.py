from typing import Protocol

from server.models import AgentStubInfo, SentinelClassification, SystemContext


class ClassificationAgent(Protocol):
    """Protocol for agents that classify incidents from symptoms and context."""

    def classify(
        self,
        raw_symptoms: list[str],
        system_context: SystemContext,
    ) -> SentinelClassification:
        """Return a structured classification for an incident."""


class BaseAgent:
    name: str = "base"

    def describe(self) -> AgentStubInfo:
        return AgentStubInfo(name=self.name)
