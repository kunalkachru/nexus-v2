import json
import logging
import re
from collections.abc import Iterable

from incidents.catalogue import load_incident_types
from server.agents.base import BaseAgent
from server.models import AgentStubInfo, IncidentDefinition, SentinelClassification, SystemContext
from server.services.priority import normalize_priority_label

logger = logging.getLogger(__name__)


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
        """Classify an incident using hybrid strategy: deterministic-first with live escalation."""

        cleaned_symptoms = [symptom.strip() for symptom in raw_symptoms if symptom.strip()]
        if not cleaned_symptoms:
            raise ValueError("raw_symptoms must not be empty")
        if not system_context.service.strip():
            raise ValueError("system_context.service must not be empty")
        if not self._incident_catalogue:
            raise RuntimeError("incident catalogue is empty")

        # PHASE 2: Always run deterministic first
        deterministic_result = self._classify_deterministic(cleaned_symptoms, system_context)

        # High confidence or no live client — use deterministic result
        if deterministic_result.confidence >= 0.75 or self._client is None:
            deterministic_result.classification_strategy = "deterministic"
            return deterministic_result

        # Low confidence + live client available — escalate to constrained GPT-4o
        try:
            live_result = self._classify_with_live_client(cleaned_symptoms, system_context)
            valid_ids = {inc.id for inc in self._incident_catalogue}

            # Verify live result is valid
            if live_result.incident_id in valid_ids:
                live_result.classification_strategy = "hybrid_escalated"
                live_result.reasoning = (
                    f"[Hybrid: deterministic confidence {deterministic_result.confidence:.0%}, "
                    f"escalated to live reasoning] " + live_result.reasoning
                )
                return live_result
        except Exception as exc:
            logger.warning(f"Live SENTINEL failed during hybrid escalation: {exc} — using deterministic fallback")

        # Fallback to deterministic
        deterministic_result.classification_strategy = "deterministic_fallback"
        return deterministic_result

    def _classify_deterministic(
        self,
        cleaned_symptoms: list[str],
        system_context: SystemContext,
    ) -> SentinelClassification:
        """Deterministic token-based classification using catalogue."""

        scored_incidents = [
            (incident, self._score_incident(cleaned_symptoms, system_context, incident))
            for incident in self._incident_catalogue
        ]
        scored_incidents.sort(key=lambda item: item[1], reverse=True)

        best_incident, best_score = scored_incidents[0]
        runner_up_incident, runner_up_score = (scored_incidents[1] if len(scored_incidents) > 1 else (None, 0.0))
        confidence = self._confidence(best_score, runner_up_score)

        # Detect ambiguity: if top 2 scores are within 20% of each other
        is_ambiguous = False
        candidate_families = []
        if runner_up_incident and best_score > 0:
            score_ratio = runner_up_score / best_score
            if 0.8 <= score_ratio:  # Within 20%
                is_ambiguous = True
                # Include top 2-3 candidates
                candidate_families = [
                    {
                        "incident_id": scored_incidents[i][0].id,
                        "incident_name": scored_incidents[i][0].name,
                        "score": scored_incidents[i][1],
                    }
                    for i in range(min(3, len(scored_incidents)))
                ]

        return SentinelClassification(
            incident_id=best_incident.id,
            incident_name=best_incident.name,
            severity=self._normalize_severity(best_incident.severity),
            confidence=confidence,
            reasoning=(
                f"Matched {best_incident.id} using symptom and context overlap "
                f"with {confidence:.0%} confidence"
                + (" (but top candidates are close—consider ambiguous)" if is_ambiguous else "")
            ),
            classification_type="ambiguous" if is_ambiguous else "single",
            candidate_families=candidate_families,
            classification_strategy="deterministic",
        )

    def _classify_with_live_client(
        self,
        raw_symptoms: list[str],
        system_context: SystemContext,
    ) -> SentinelClassification:
        # Build catalogue summary for constrained classification
        catalogue_summary = json.dumps([
            {
                "incident_id": inc.id,
                "incident_name": inc.name,
                "key_symptoms": inc.symptoms[:3]  # first 3 symptoms as hints
            }
            for inc in self._incident_catalogue
        ], indent=2)

        model_name = self._model_name or "gpt-4o"
        user_prompt = (
            f"Symptoms: {raw_symptoms}\n"
            f"System context: service={system_context.service}, language={system_context.language}, "
            f"infra={system_context.infra}, dependencies={system_context.dependencies}\n"
            "Return grounded JSON with incident_id, incident_name, severity, confidence, reasoning."
        )

        # PHASE 1: Constrain GPT-4o to pick from valid incident families
        system_prompt = (
            "You are SENTINEL, an incident classifier for NEXUS.\n"
            "You MUST classify this incident into EXACTLY ONE of these supported families:\n\n"
            f"{catalogue_summary}\n\n"
            "Rules:\n"
            "- Return ONLY an incident_id from the list above — never invent a new one\n"
            "- Pick the family whose symptoms best match the incident\n"
            "- If unsure between two families, pick the closer match\n"
            "- Do not return generic responses\n"
            "Return JSON: {incident_id, incident_name, severity, confidence, reasoning}"
        )

        response_data = self._client.generate_json(
            model=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        incident_id = str(response_data.get("incident_id", "")).strip()
        incident_name = str(response_data.get("incident_name", "")).strip()
        severity = str(response_data.get("severity", "")).strip()
        confidence = float(response_data.get("confidence", 0.8))
        reasoning = str(response_data.get("reasoning", "")).strip()

        # Validate that incident_id is in the catalogue
        valid_ids = {inc.id for inc in self._incident_catalogue}
        if not incident_id or incident_id not in valid_ids:
            logger.warning(
                f"GPT-4o returned invalid incident_id '{incident_id}' — falling back to deterministic classification"
            )
            # Fall back to deterministic classification (Phase 1 inline fallback)
            return self._classify_deterministic(raw_symptoms, system_context)

        # Find the incident in catalogue to get proper name and defaults
        matched_incident = next((inc for inc in self._incident_catalogue if inc.id == incident_id), None)
        if not matched_incident:
            logger.warning(f"Could not find incident {incident_id} in catalogue — falling back to deterministic")
            return self._classify_deterministic(raw_symptoms, system_context)

        # Use provided name or fall back to catalogue name
        if not incident_name:
            incident_name = matched_incident.name

        # Use provided severity or fall back to catalogue default
        if not severity:
            severity = self._normalize_severity(matched_incident.severity)
        else:
            severity = normalize_priority_label(severity)

        # Use provided reasoning or generate default
        if not reasoning:
            reasoning = f"Live LLM classification for {incident_id} grounded in {len(raw_symptoms)} symptom(s)"

        return SentinelClassification(
            incident_id=incident_id,
            incident_name=incident_name,
            severity=severity,
            confidence=confidence,
            reasoning=reasoning,
            classification_type="single",
            candidate_families=[],
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
