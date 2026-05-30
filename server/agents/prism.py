import json
import asyncio
import os
import re
from collections.abc import Iterable

from server.agents.base import BaseAgent
from server.models import AgentStubInfo, IncidentDefinition, PrismDiagnosis, SentinelClassification
from server.services.observability import ObservabilityService


class PrismAgent(BaseAgent):
    """Deterministic Day 3 diagnosis agent backed by the incident catalogue."""

    name = "prism"

    def __init__(
        self,
        observability: ObservabilityService | None = None,
        client: object | None = None,
        model_name: str | None = None,
    ) -> None:
        self._observability = observability or ObservabilityService()
        self._client = client
        self._model_name = model_name

    def describe(self) -> AgentStubInfo:
        """Report that PRISM is implemented while later agents remain stubs."""

        return AgentStubInfo(name=self.name, implemented=True)

    async def diagnose(
        self,
        sentinel_output: SentinelClassification,
        signals: list[str] | dict[str, list[str]] | None = None,
    ) -> PrismDiagnosis:
        """Return a root-cause diagnosis from a SENTINEL classification and optional signals."""

        incident_id = sentinel_output.incident_id.strip()
        if not incident_id:
            raise ValueError("sentinel_output.incident_id must not be empty")

        incident = await self._observability.resolve_incident_definition(incident_id)

        signal_map = await self._normalize_signals(incident_id, signals)
        signal_list = self._flatten_signals(signal_map)
        evidence = self._select_evidence(signal_list, incident)
        queried_sources = [source for source, values in signal_map.items() if values]
        confidence = self._confidence(signal_list, incident)

        if self._client is not None:
            return self._diagnose_with_live_client(
                incident=incident,
                queried_sources=queried_sources,
                signal_map=signal_map,
                confidence=confidence,
            )

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

    def _diagnose_with_live_client(
        self,
        *,
        incident: IncidentDefinition,
        queried_sources: list[str],
        signal_map: dict[str, list[str]],
        confidence: float,
    ) -> PrismDiagnosis:
        model_name = self._model_name or os.environ.get("LLM_MODEL", "gpt-4o")
        user_prompt = (
            f"Incident ID: {incident.id}\n"
            f"Incident Name: {incident.name}\n"
            f"Symptoms: {json.dumps(incident.symptoms)}\n"
            f"Root Cause Hint: {incident.root_cause}\n"
            f"Signals: {json.dumps(signal_map, sort_keys=True)}\n"
            "Return grounded JSON with root_cause, confidence, evidence, queried_sources, reasoning."
        )
        response_data = self._client.generate_json(
            model=model_name,
            system_prompt=(
                "You are PRISM, an incident diagnosis agent. "
                "Use only the provided signals and incident context. "
                "Return concise JSON that explains the likely root cause."
            ),
            user_prompt=user_prompt,
        )
        payload = {
            "incident_id": incident.id,
            "root_cause": str(response_data.get("root_cause", incident.root_cause)).strip() or incident.root_cause,
            "confidence": float(response_data.get("confidence", confidence)),
            "evidence": [str(item).strip() for item in response_data.get("evidence", []) if str(item).strip()],
            "queried_sources": [
                str(item).strip()
                for item in response_data.get("queried_sources", queried_sources)
                if str(item).strip()
            ]
            or queried_sources,
            "reasoning": str(response_data.get("reasoning", "")).strip()
            or f"Live LLM diagnosis for {incident.id} grounded in {len(queried_sources)} signal source(s)",
        }
        return PrismDiagnosis.model_validate(payload)

    async def _normalize_signals(
        self,
        incident_id: str,
        signals: list[str] | dict[str, list[str]] | None,
    ) -> dict[str, list[str]]:
        if isinstance(signals, dict):
            normalized: dict[str, list[str]] = {}
            for source, values in signals.items():
                if values is None or isinstance(values, str) or not isinstance(values, list):
                    raise ValueError(f"signals[{source!r}] must be a list of strings")
                normalized[source] = []
                for value in values:
                    if not isinstance(value, str):
                        raise ValueError(f"signals[{source!r}] must contain only strings")
                    if value.strip():
                        normalized[source].append(value.strip())
            return normalized
        if signals:
            signal_list = [signal.strip() for signal in signals if signal.strip()]
            return {source: signal_list for source in self._infer_sources(signal_list)}

        requested_sources = ["logs", "metrics", "traces"]
        supporting_signals = await self._observability.fetch_supporting_signals(
            incident_id=incident_id,
            requested_sources=requested_sources,
        )
        return {
            source: [value.strip() for value in values if value.strip()]
            for source, values in supporting_signals.items()
        }

    def _flatten_signals(self, signals: dict[str, list[str]]) -> list[str]:
        flattened: list[str] = []
        for values in signals.values():
            flattened.extend(values)
        return flattened

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
