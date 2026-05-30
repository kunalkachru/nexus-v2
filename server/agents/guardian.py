import re

from server.agents.base import BaseAgent
from server.models import (
    AgentStubInfo,
    ForgeRunbookResult,
    GuardianReviewResult,
    PrismDiagnosis,
    SentinelClassification,
)
from server.services.priority import priority_rank
from server.sandbox import SandboxExecutor


class GuardianAgent(BaseAgent):
    """Deterministic Day 5 safety reviewer for generated runbooks."""

    name = "guardian"

    _DANGEROUS_PATTERNS = (
        r"(^|\s)rm\s+-rf\s+/(?:\s|$)",
        r"\|\s*sh(?:\s|$)",
        r"(^|\s)shutdown\s+-h(?:\s|$)",
        r"(^|\s)mkfs(?:\s|$)",
        r"(^|\s)dd\s+if=",
    )
    _SECRET_PATTERNS = (
        r"aws_secret_access_key\s*=",
        r"openai_api_key\s*=",
        r"sk-[a-z0-9]+",
        r"password\s*=",
    )

    def __init__(self, sandbox: SandboxExecutor | None = None) -> None:
        self._sandbox = sandbox or SandboxExecutor()

    def describe(self) -> AgentStubInfo:
        """Report that GUARDIAN is implemented."""

        return AgentStubInfo(name=self.name, implemented=True)

    async def review(
        self,
        forge_output: ForgeRunbookResult,
        sentinel_output: SentinelClassification,
        prism_output: PrismDiagnosis,
    ) -> GuardianReviewResult:
        """Review a generated runbook for safety before execution."""

        if not forge_output.runbook.code.strip():
            raise ValueError("forge_output.runbook.code must not be empty")
        if not prism_output.root_cause.strip():
            raise ValueError("prism_output.root_cause must not be empty")

        sandbox_validation = await self._sandbox.validate(forge_output.runbook)
        blocked_patterns = self._blocked_patterns(forge_output.runbook.code)
        safety_score = self._safety_score(blocked_patterns)
        threshold = self._threshold_for_severity(sentinel_output.severity)
        combined_confidence = safety_score * 0.6 + prism_output.confidence * 0.4

        if not sandbox_validation.execution_allowed:
            decision = "reject"
        elif blocked_patterns:
            decision = "reject"
        elif combined_confidence >= threshold:
            decision = "approve"
        else:
            decision = "request_modification"

        return GuardianReviewResult(
            decision=decision,
            safety_score=safety_score,
            blocked_patterns=blocked_patterns + sandbox_validation.issues,
            reasoning=(
                f"Safety score {safety_score:.0%}, diagnosis confidence "
                f"{prism_output.confidence:.0%}, threshold {threshold:.0%}"
            ),
            policy_id="guardian-safety-threshold-v1",
            policy_name="GUARDIAN safety threshold policy",
            policy_basis=(
                "Approve when sandbox validation passes and the combined safety score clears the severity threshold."
                if decision == "approve"
                else "Reject blocked runbooks or request revision when the combined score stays below the threshold."
            ),
        )

    def _blocked_patterns(self, code: str) -> list[str]:
        code_lower = code.lower()
        blocked = [pattern for pattern in self._DANGEROUS_PATTERNS if re.search(pattern, code_lower)]
        for pattern in self._SECRET_PATTERNS:
            if re.search(pattern, code_lower):
                blocked.append(pattern)
        return blocked

    def _safety_score(self, blocked_patterns: list[str]) -> float:
        if not blocked_patterns:
            return 1.0
        penalty = min(1.0, 0.35 * len(blocked_patterns))
        return max(0.0, 1.0 - penalty)

    def _threshold_for_severity(self, severity: str) -> float:
        rank = max(1, priority_rank(severity))
        return max(0.55, 1.05 - (0.1 * rank))
