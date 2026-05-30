import re
from collections.abc import Iterable

from incidents.catalogue import load_incident_types
from server.agents.base import BaseAgent
from server.models import AgentStubInfo, IncidentDefinition, SentinelClassification, SystemContext
from server.services.priority import normalize_priority_label


class SentinelAgent(BaseAgent):
    """Deterministic Day 2 classifier for incident type and severity."""

    name = "sentinel"

    def __init__(self, client: object | None = None, model_name: str | None = None) -> None:
        self._incident_catalogue = load_incident_types()
        self._client = client
        self._model_name = model_name

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

        if self._client is not None:
            return self._classify_with_live_client(cleaned_symptoms, system_context)

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

    def _classify_with_live_client(
        self,
        raw_symptoms: list[str],
        system_context: SystemContext,
    ) -> SentinelClassification:
        model_name = self._model_name or "gpt-4o"
        user_prompt = (
            f"Symptoms: {raw_symptoms}\n"
            f"System context: service={system_context.service}, language={system_context.language}, "
            f"infra={system_context.infra}, dependencies={system_context.dependencies}\n"
            "Return grounded JSON with incident_id, incident_name, severity, confidence, reasoning."
        )
        response_data = self._client.generate_json(
            model=model_name,
            system_prompt=(
                "You are SENTINEL, an incident classification agent. "
                "Use only the supplied symptoms and system context. "
                "Return concise JSON that explains the most likely incident pattern."
            ),
            user_prompt=user_prompt,
        )
        incident_id = str(response_data.get("incident_id", "")).strip() or self._incident_catalogue[0].id
        incident_name = str(response_data.get("incident_name", "")).strip() or self._incident_catalogue[0].name
        severity = str(response_data.get("severity", "")).strip() or self._normalize_severity(self._incident_catalogue[0].severity)
        confidence = float(response_data.get("confidence", 0.8))
        reasoning = str(response_data.get("reasoning", "")).strip() or (
            f"Live LLM classification for {incident_id} grounded in {len(raw_symptoms)} symptom(s)"
        )
        return SentinelClassification(
            incident_id=incident_id,
            incident_name=incident_name,
            severity=normalize_priority_label(severity),
            confidence=confidence,
            reasoning=reasoning,
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
        normalized = normalize_priority_label(severity)
        if normalized == "P0":
            return "P1"
        if normalized.startswith("P") and normalized[1:].isdigit():
            return f"P{int(normalized[1:]) + 1}"
        return normalized

    def _tokenize_many(self, parts: Iterable[str]) -> set[str]:
        tokens: set[str] = set()
        for part in parts:
            tokens.update(re.findall(r"[a-z0-9]+", part.lower()))
        return tokens
