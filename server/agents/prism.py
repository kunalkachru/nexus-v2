import re
from collections.abc import Iterable

from incidents.catalogue import load_incident_types
from server.agents.base import BaseAgent
from server.models import AgentStubInfo, IncidentDefinition, PrismDiagnosis, SentinelClassification


class PrismAgent(BaseAgent):
    """Deterministic Day 3 diagnosis agent backed by the incident catalogue."""

    name = "prism"

    def __init__(self) -> None:
        self._incident_by_id = {
            incident.id: incident for incident in load_incident_types()
        }

    def describe(self) -> AgentStubInfo:
        """Report that PRISM is implemented while later agents remain stubs."""

        return AgentStubInfo(name=self.name, implemented=True)

    def diagnose(
        self,
        sentinel_output: SentinelClassification,
        signals: list[str] | None = None,
    ) -> PrismDiagnosis:
        """Return a root-cause diagnosis from a SENTINEL classification and optional signals."""

        incident_id = sentinel_output.incident_id.strip()
        if not incident_id:
            raise ValueError("sentinel_output.incident_id must not be empty")

        try:
            incident = self._incident_by_id[incident_id]
        except KeyError as exc:
            raise ValueError(f"unknown incident_id: {incident_id}") from exc

        signal_list = [signal.strip() for signal in (signals or []) if signal.strip()]
        evidence = self._select_evidence(signal_list, incident)
        queried_sources = self._infer_sources(signal_list)
        confidence = self._confidence(signal_list, incident)

        return PrismDiagnosis(
            incident_id=incident.id,
            root_cause=incident.root_cause,
            confidence=confidence,
            evidence=evidence,
            queried_sources=queried_sources,
            reasoning=(
                f"Diagnosed {incident.id} from {len(queried_sources)} signal source(s) "
                f"with {confidence:.0%} confidence"
            ),
        )

    def _select_evidence(
        self,
        signals: list[str],
        incident: IncidentDefinition,
    ) -> list[str]:
        if not signals:
            return [incident.symptoms[0]]

        root_tokens = self._tokenize_many([incident.root_cause, *incident.symptoms])
        ranked_signals = sorted(
            signals,
            key=lambda signal: len(self._tokenize_many([signal]) & root_tokens),
            reverse=True,
        )
        evidence = [signal for signal in ranked_signals if self._tokenize_many([signal]) & root_tokens]
        return evidence[:3] or [ranked_signals[0]]

    def _infer_sources(self, signals: list[str]) -> list[str]:
        if not signals:
            return ["catalogue"]

        joined = " ".join(signals).lower()
        sources: list[str] = []
        if any(token in joined for token in ("error", "exception", "fail", "crash", "timeout")):
            sources.append("logs")
        if any(token in joined for token in ("latency", "rate", "memory", "cpu", "lag", "hit", "evicted", "rss")):
            sources.append("metrics")
        if any(token in joined for token in ("downstream", "upstream", "namespace", "service", "queue", "gateway")):
            sources.append("traces")

        return sources or ["signals"]

    def _confidence(self, signals: list[str], incident: IncidentDefinition) -> float:
        if not signals:
            return 0.75

        root_tokens = self._tokenize_many([incident.root_cause, *incident.symptoms])
        matched_tokens = len(self._tokenize_many(signals) & root_tokens)
        max_tokens = max(1, len(root_tokens))
        return min(0.99, 0.75 + (matched_tokens / max_tokens) * 0.24)

    def _tokenize_many(self, parts: Iterable[str]) -> set[str]:
        tokens: set[str] = set()
        for part in parts:
            tokens.update(re.findall(r"[a-z0-9]+", part.lower()))
        return tokens
