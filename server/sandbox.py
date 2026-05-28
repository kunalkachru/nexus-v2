from __future__ import annotations

import asyncio
import py_compile
import subprocess
import tempfile

from server.models import RunbookScript, SandboxValidationResult


class SandboxExecutor:
    """Deterministic syntax validator used as a lightweight execution boundary."""

    async def validate(self, runbook: RunbookScript) -> SandboxValidationResult:
        return await asyncio.to_thread(self._validate_sync, runbook)

    def _validate_sync(self, runbook: RunbookScript) -> SandboxValidationResult:
        issues: list[str] = []
        syntax_valid = self._syntax_valid(runbook)
        if not syntax_valid:
            issues.append(f"invalid {runbook.language} syntax")

        return SandboxValidationResult(
            syntax_valid=syntax_valid,
            execution_allowed=syntax_valid,
            issues=issues,
        )

    def _syntax_valid(self, runbook: RunbookScript) -> bool:
        if runbook.language in {"bash", "kubectl"}:
            return self._validate_shell(runbook.code)
        if runbook.language == "python":
            return self._validate_python(runbook.code)
        return False

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
