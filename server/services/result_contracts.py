from __future__ import annotations


def build_structured_result(
    *,
    incident_id: str,
    root_cause: str,
    proposed_fix: str,
    safety_decision: str,
    confidence: float,
    execution_status: str,
    live_reasoning: bool,
    raw_priority_label: str,
    normalized_priority_label: str,
    normalized_priority_rank: int,
    reward: float,
    guardian_policy_id: str = "",
    guardian_policy_name: str = "",
    guardian_policy_basis: str = "",
) -> dict[str, object]:
    return {
        "incident_id": incident_id,
        "root_cause": root_cause,
        "proposed_fix": proposed_fix,
        "safety_decision": safety_decision,
        "confidence": confidence,
        "execution_status": execution_status,
        "live_reasoning": live_reasoning,
        "raw_priority_label": raw_priority_label,
        "normalized_priority_label": normalized_priority_label,
        "normalized_priority_rank": normalized_priority_rank,
        "reward": reward,
        "guardian_policy_id": guardian_policy_id,
        "guardian_policy_name": guardian_policy_name,
        "guardian_policy_basis": guardian_policy_basis,
    }
