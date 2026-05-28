from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable

from incidents.catalogue import load_incident_types
from server.incident_payloads import INCIDENT_DETAILS
from server.models import HistoricalRunbook, IncidentDefinition


class IncidentMemoryGraph:
    """Deterministic historical-retrieval adapter for prior runbook outcomes."""

    def __init__(
        self,
        *,
        incidents: list[IncidentDefinition] | None = None,
        incident_details: dict[str, dict[str, object]] | None = None,
        similarity_threshold: float = 0.1,
    ) -> None:
        self._incidents = incidents or load_incident_types()
        self._incident_details = incident_details or INCIDENT_DETAILS
        self._similarity_threshold = similarity_threshold

    async def find_similar(self, root_cause: str, top_k: int = 3) -> list[HistoricalRunbook]:
        await asyncio.sleep(0)
        if not root_cause.strip():
            return []

        ranked_incidents = []
        for incident in self._incidents:
            similarity = self._similarity(root_cause, incident)
            if similarity >= self._similarity_threshold:
                ranked_incidents.append((incident, similarity))

        ranked_incidents.sort(key=lambda item: item[1], reverse=True)

        results: list[HistoricalRunbook] = []
        for incident, similarity in ranked_incidents:
            details = self._incident_details.get(incident.id, {})
            recommended = details.get("recommended_runbooks", [])
            if not isinstance(recommended, list):
                continue
            for runbook in recommended:
                if not isinstance(runbook, dict):
                    continue
                results.append(
                    HistoricalRunbook(
                        incident_id=incident.id,
                        root_cause=incident.root_cause,
                        runbook_summary=str(runbook.get("name", "")),
                        success_rate=float(runbook.get("success_rate", 0.0)),
                        similarity_score=similarity,
                    )
                )
                if len(results) >= top_k:
                    return results
        return results

    def _similarity(self, root_cause: str, incident: IncidentDefinition) -> float:
        query_tokens = self._tokenize([root_cause])
        incident_tokens = self._tokenize([incident.root_cause, *incident.symptoms])
        if not query_tokens or not incident_tokens:
            return 0.0
        overlap = len(query_tokens & incident_tokens)
        return min(1.0, overlap / max(1, len(query_tokens)))

    def _tokenize(self, parts: Iterable[str]) -> set[str]:
        tokens: set[str] = set()
        for part in parts:
            tokens.update(re.findall(r"[a-z0-9]+", part.lower()))
        return tokens
