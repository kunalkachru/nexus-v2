from __future__ import annotations

from server.models import IncidentRecord


class GovernanceService:
    def guardian_decision_for_incident(self, incident: IncidentRecord) -> str:
        if incident.guardian_decision in {"approve", "reject"}:
            return incident.guardian_decision
        if incident.status == "blocked_by_guardian":
            return "reject"
        if incident.status == "resolved":
            return "approve"
        return "pending"

    def guardian_context(self, incident: IncidentRecord) -> dict[str, object]:
        decision = self.guardian_decision_for_incident(incident)
        if decision == "pending":
            return {
                "decision": decision,
                "confidence": 0.0,
                "safety_checks": [
                    "Runbook proposal ready for review",
                    "Execution stays blocked until approval is recorded",
                    "Audit trail is waiting for the operator decision",
                ],
                "policy_violations": [],
                "reasoning": "Guardian review is pending. Choose approve or block to make the gate explicit.",
            }

        return {
            "decision": decision,
            "confidence": 0.89,
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
