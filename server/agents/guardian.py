import re

from server.agents.base import BaseAgent
from server.models import (
    AgentStubInfo,
    ForgeRunbookResult,
    GuardianReviewResult,
    PrismDiagnosis,
    SentinelClassification,
)


class GuardianAgent(BaseAgent):
    """Deterministic Day 5 safety reviewer for generated runbooks."""

    name = "guardian"

    _DANGEROUS_PATTERNS = (
        "rm -rf /",
        "curl http",
        "curl https",
        "| sh",
        "shutdown -h",
        "mkfs",
        "dd if=",
    )
    _SECRET_PATTERNS = (
        r"aws_secret_access_key\s*=",
        r"openai_api_key\s*=",
        r"sk-[a-z0-9]+",
        r"password\s*=",
        r"token\s*=",
    )

    def describe(self) -> AgentStubInfo:
        """Report that GUARDIAN is implemented."""

        return AgentStubInfo(name=self.name, implemented=True)

    def review(
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

        blocked_patterns = self._blocked_patterns(forge_output.runbook.code)
        safety_score = self._safety_score(blocked_patterns)
        threshold = self._threshold_for_severity(sentinel_output.severity)
        combined_confidence = safety_score * 0.6 + prism_output.confidence * 0.4

        if blocked_patterns:
            decision = "reject"
        elif combined_confidence >= threshold:
            decision = "approve"
        else:
            decision = "request_modification"

        return GuardianReviewResult(
            decision=decision,
            safety_score=safety_score,
            blocked_patterns=blocked_patterns,
            reasoning=(
                f"Safety score {safety_score:.0%}, diagnosis confidence "
                f"{prism_output.confidence:.0%}, threshold {threshold:.0%}"
            ),
        )

    def _blocked_patterns(self, code: str) -> list[str]:
        code_lower = code.lower()
        blocked = [pattern for pattern in self._DANGEROUS_PATTERNS if pattern in code_lower]
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
        thresholds = {
            "P1": 0.95,
            "P2": 0.85,
            "P3": 0.70,
        }
        try:
            return thresholds[severity]
        except KeyError as exc:
            raise ValueError(f"unsupported severity: {severity}") from exc
