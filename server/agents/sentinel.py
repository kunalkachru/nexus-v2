import re
from collections.abc import Iterable

from incidents.catalogue import load_incident_types
from server.agents.base import BaseAgent
from server.models import AgentStubInfo, IncidentDefinition, SentinelClassification, SystemContext


class SentinelAgent(BaseAgent):
    """Deterministic Day 2 classifier for incident type and severity."""

    name = "sentinel"

    def __init__(self) -> None:
        self._incident_catalogue = load_incident_types()

    def describe(self) -> AgentStubInfo:
        """Report that SENTINEL is implemented while other agents remain stubs."""

        return AgentStubInfo(name=self.name, implemented=True)

    def classify(
        self,
        raw_symptoms: list[str],
        system_context: SystemContext,
    ) -> SentinelClassification:
        """Classify an incident by matching symptoms and context to the catalogue."""

        cleaned_symptoms = [symptom.strip() for symptom in raw_symptoms if symptom.strip()]
        if not cleaned_symptoms:
            raise ValueError("raw_symptoms must not be empty")
        if not system_context.service.strip():
            raise ValueError("system_context.service must not be empty")
        if not self._incident_catalogue:
            raise RuntimeError("incident catalogue is empty")

        scored_incidents = [
            (incident, self._score_incident(cleaned_symptoms, system_context, incident))
            for incident in self._incident_catalogue
        ]
        scored_incidents.sort(key=lambda item: item[1], reverse=True)

        best_incident, best_score = scored_incidents[0]
        runner_up_score = scored_incidents[1][1] if len(scored_incidents) > 1 else 0.0
        confidence = self._confidence(best_score, runner_up_score)

        return SentinelClassification(
            incident_id=best_incident.id,
            incident_name=best_incident.name,
            severity=self._normalize_severity(best_incident.severity),
            confidence=confidence,
            reasoning=(
                f"Matched {best_incident.id} using symptom and context overlap "
                f"with {confidence:.0%} confidence"
            ),
        )

    def _score_incident(
        self,
        raw_symptoms: list[str],
        system_context: SystemContext,
        incident: IncidentDefinition,
    ) -> float:
        query_tokens = self._tokenize_many(raw_symptoms)
        incident_tokens = self._tokenize_many(incident.symptoms)

        score = float(len(query_tokens & incident_tokens) * 4)
        if system_context.service == incident.system_context.service:
            score += 8.0
        if system_context.language == incident.system_context.language:
            score += 2.0

        score += float(
            len(
                set(system_context.dependencies)
                & set(incident.system_context.dependencies)
            )
            * 2
        )

        query_context_tokens = self._tokenize_many(
            [
                system_context.service,
                system_context.language,
                system_context.infra,
                *system_context.dependencies,
            ]
        )
        incident_context_tokens = self._tokenize_many(
            [
                incident.name,
                incident.system_context.service,
                incident.system_context.language,
                incident.system_context.infra,
                *incident.system_context.dependencies,
            ]
        )
        score += float(len(query_context_tokens & incident_context_tokens))

        return score

    def _confidence(self, best_score: float, runner_up_score: float) -> float:
        if best_score <= 0:
            return 0.0
        return min(0.99, 0.6 + (best_score / (best_score + runner_up_score + 1.0)) * 0.4)

    def _normalize_severity(self, severity: str) -> str:
        severity_map = {"P0": "P1", "P1": "P2", "P2": "P3"}
        try:
            return severity_map[severity]
        except KeyError as exc:
            raise ValueError(f"unsupported severity: {severity}") from exc

    def _tokenize_many(self, parts: Iterable[str]) -> set[str]:
        tokens: set[str] = set()
        for part in parts:
            tokens.update(re.findall(r"[a-z0-9]+", part.lower()))
        return tokens
