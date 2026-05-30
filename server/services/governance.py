from __future__ import annotations

from server.models import IncidentRecord


class GovernanceService:
    _POLICY_ID = "guardian-runbook-policy-v2"
    _POLICY_NAME = "GUARDIAN runbook review policy"

    def guardian_decision_for_incident(self, incident: IncidentRecord) -> str:
        if incident.guardian_decision in {"approve", "reject", "request_modification"}:
            return incident.guardian_decision
        if incident.status == "blocked_by_guardian":
            return "reject"
        if incident.status == "needs_modification":
            return "request_modification"
        if incident.status == "resolved":
            return "approve"
        return "pending"

    def guardian_context(self, incident: IncidentRecord) -> dict[str, object]:
        decision = self.guardian_decision_for_incident(incident)
        policy = self.guardian_policy_for_decision(decision)
        if decision == "pending":
            return {
                "decision": decision,
                "confidence": 0.0,
                **policy,
                "safety_checks": [
                    "Runbook proposal ready for review",
                    "Execution stays blocked until approval is recorded",
                    "Audit trail is waiting for the operator decision",
                ],
                "policy_violations": [],
                "reasoning": "Guardian review is pending. Choose approve or block to make the gate explicit.",
            }

        if decision == "request_modification":
            return {
                "decision": decision,
                "confidence": 0.67,
                **policy,
                "safety_checks": [
                    "Authenticated live incident read",
                    "Runbook proposal needs revision before execution",
                    "Audit trail is waiting for the operator decision",
                ],
                "policy_violations": ["Runbook requires modification before execution"],
                "reasoning": incident.guardian_reasoning
                or "GUARDIAN requested changes before allowing the runbook to proceed.",
            }

        return {
            "decision": decision,
            "confidence": 0.89,
            **policy,
            "safety_checks": [
                "Authenticated live incident read",
                "Audit trail available from backend state",
                "Rollback-safe execution path preserved",
            ],
            "policy_violations": [] if decision == "approve" else ["Execution blocked by Guardian"],
            "reasoning": incident.guardian_reasoning
            or (
                "GUARDIAN approved the runbook and the incident can proceed."
                if decision == "approve"
                else "GUARDIAN blocked the runbook and kept the incident out of execution."
            ),
        }

    def guardian_policy_for_decision(self, decision: str) -> dict[str, str]:
        if decision == "approve":
            return {
                "policy_id": f"{self._POLICY_ID}:approve",
                "policy_name": self._POLICY_NAME,
                "policy_basis": "The runbook is safe enough to proceed after the final operator review.",
            }
        if decision == "reject":
            return {
                "policy_id": f"{self._POLICY_ID}:reject",
                "policy_name": self._POLICY_NAME,
                "policy_basis": "The runbook was rejected and kept out of execution.",
            }
        if decision == "request_modification":
            return {
                "policy_id": f"{self._POLICY_ID}:request_modification",
                "policy_name": self._POLICY_NAME,
                "policy_basis": "The runbook needs revision before it can be executed safely.",
            }
        return {
            "policy_id": f"{self._POLICY_ID}:pending",
            "policy_name": self._POLICY_NAME,
            "policy_basis": "Runbook proposal ready, but operator approval is still required before execution.",
        }
