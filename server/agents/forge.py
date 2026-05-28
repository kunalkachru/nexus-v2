import json
import os
import py_compile
import subprocess
import tempfile
from typing import Protocol

from server.agents.base import BaseAgent
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

    def __init__(self, client: ForgeClient | None = None) -> None:
        self._client = client or _MissingForgeClient()

    def describe(self) -> AgentStubInfo:
        """Report that FORGE is implemented while GUARDIAN remains a stub."""

        return AgentStubInfo(name=self.name, implemented=True)

    def generate_runbook(
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

        model_name = os.environ.get("LLM_MODEL", "gpt-4o")
        user_prompt = self._build_prompt(prism_output, system_context)
        response_data = self._client.generate_json(
            model=model_name,
            system_prompt=self._SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        runbook = RunbookScript.model_validate(response_data)
        syntax_valid = self._validate_script(runbook.language, runbook.code)
        if not syntax_valid:
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
    ) -> str:
        payload = {
            "incident_id": prism_output.incident_id,
            "root_cause": prism_output.root_cause,
            "evidence": prism_output.evidence,
            "service": system_context.service,
            "language": system_context.language,
            "infra": system_context.infra,
            "dependencies": system_context.dependencies,
        }
        return (
            f"Incident ID: {prism_output.incident_id}\n"
            f"Root Cause: {prism_output.root_cause}\n"
            f"System Context: {json.dumps(payload, sort_keys=True)}\n"
            "Generate one safe remediation runbook."
        )

    def _validate_script(self, language: str, code: str) -> bool:
        if language in {"bash", "kubectl"}:
            return self._validate_shell(code)
        if language == "python":
            return self._validate_python(code)
        raise ValueError(f"unsupported runbook language: {language}")

    def _validate_shell(self, code: str) -> bool:
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=True) as script_file:
            script_file.write(code)
            script_file.flush()
            result = subprocess.run(
                ["bash", "-n", script_file.name],
                capture_output=True,
                text=True,
                check=False,
            )
        return result.returncode == 0

    def _validate_python(self, code: str) -> bool:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=True) as script_file:
            script_file.write(code)
            script_file.flush()
            try:
                py_compile.compile(script_file.name, doraise=True)
            except py_compile.PyCompileError:
                return False
        return True


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
