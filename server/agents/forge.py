import json
import os
from typing import Protocol

from server.agents.base import BaseAgent
from server.memory_graph import IncidentMemoryGraph
from server.sandbox import SandboxExecutor
from server.models import AgentStubInfo, ForgeRunbookResult, PrismDiagnosis, RunbookScript, SystemContext


class ForgeClient(Protocol):
    """Minimal client contract for runbook generation backends."""

    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, object]:
        """Return a JSON-compatible runbook payload."""


class ForgeAgent(BaseAgent):
    """Day 4 runbook generator with injectable Codex-style client."""

    name = "forge"

    _SYSTEM_PROMPT = (
        "You generate incident remediation runbooks as JSON with keys "
        "language, summary, code, estimated_cost_usd. Prefer concise, "
        "syntactically valid operational scripts."
    )

    def __init__(
        self,
        client: ForgeClient | None = None,
        memory_graph: IncidentMemoryGraph | None = None,
        sandbox: SandboxExecutor | None = None,
        model_name: str | None = None,
    ) -> None:
        self._client = client or _MissingForgeClient()
        self._memory_graph = memory_graph or IncidentMemoryGraph()
        self._sandbox = sandbox or SandboxExecutor()
        self._model_name = model_name

    def describe(self) -> AgentStubInfo:
        """Report that FORGE is implemented while GUARDIAN remains a stub."""

        return AgentStubInfo(name=self.name, implemented=True)

    async def generate_runbook(
        self,
        prism_output: PrismDiagnosis,
        system_context: SystemContext,
    ) -> ForgeRunbookResult:
        """Generate and validate a remediation runbook for a diagnosed incident."""

        incident_id = prism_output.incident_id.strip()
        if not incident_id:
            raise ValueError("prism_output.incident_id must not be empty")
        if not prism_output.root_cause.strip():
            raise ValueError("prism_output.root_cause must not be empty")
        if not system_context.service.strip():
            raise ValueError("system_context.service must not be empty")

        model_name = self._model_name or os.environ.get("LLM_MODEL", "gpt-4o")
        historical_runbooks = await self._memory_graph.find_similar(prism_output.root_cause)
        user_prompt = self._build_prompt(prism_output, system_context, historical_runbooks)
        response_data = self._client.generate_json(
            model=model_name,
            system_prompt=self._SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        if "language" in response_data:
            response_data["language"] = str(response_data["language"]).strip().lower()
        if "summary" in response_data:
            response_data["summary"] = str(response_data["summary"]).strip()
        if "code" in response_data:
            response_data["code"] = str(response_data["code"]).strip()
        runbook = RunbookScript.model_validate(response_data)
        sandbox_validation = await self._sandbox.validate(runbook)
        if not sandbox_validation.syntax_valid:
            raise ValueError("generated runbook failed syntax validation")

        estimated_cost = float(response_data.get("estimated_cost_usd", 0.0))
        return ForgeRunbookResult(
            incident_id=incident_id,
            runbook=runbook,
            syntax_valid=True,
            model_name=model_name,
            estimated_cost_usd=estimated_cost,
            reasoning=(
                f"Generated {runbook.language} runbook for {incident_id} "
                f"using {model_name} with syntax validation passed"
            ),
        )

    def _build_prompt(
        self,
        prism_output: PrismDiagnosis,
        system_context: SystemContext,
        historical_runbooks: list[object],
    ) -> str:
        payload = {
            "incident_id": prism_output.incident_id,
            "root_cause": prism_output.root_cause,
            "evidence": prism_output.evidence,
            "service": system_context.service,
            "language": system_context.language,
            "infra": system_context.infra,
            "dependencies": system_context.dependencies,
            "historical_runbooks": [
                {
                    "summary": getattr(runbook, "runbook_summary", ""),
                    "success_rate": getattr(runbook, "success_rate", 0.0),
                    "similarity_score": getattr(runbook, "similarity_score", 0.0),
                }
                for runbook in historical_runbooks
            ],
        }
        return (
            f"Incident ID: {prism_output.incident_id}\n"
            f"Root Cause: {prism_output.root_cause}\n"
            f"System Context: {json.dumps(payload, sort_keys=True)}\n"
            "Generate one safe remediation runbook."
        )

class _MissingForgeClient:
    """Fallback client that makes missing API wiring explicit."""

    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, object]:
        raise RuntimeError(
            "FORGE client is not configured; inject a client before generating runbooks"
        )
