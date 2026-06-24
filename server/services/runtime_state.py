from __future__ import annotations

from typing import NotRequired, TypedDict

from server.models import (
    Episode,
    ForgeRunbookResult,
    GuardianReviewResult,
    IncidentContext,
    NormalizedAlertEnvelope,
    PrismDiagnosis,
    SentinelClassification,
)


class RuntimeState(TypedDict):
    alert_envelope: NormalizedAlertEnvelope
    context: IncidentContext
    task_board: list[dict[str, object]]
    orchestration: dict[str, object]
    memory_hits: dict[str, list[dict[str, object]]]
    fallback_summary: list[dict[str, object]]
    agent_metrics: dict[str, dict[str, object]]
    branch_results: dict[str, dict[str, object]]
    evidence_pack: dict[str, object]
    sentinel_output: SentinelClassification
    prism_output: PrismDiagnosis
    triage_summary: dict[str, object]
    forge_output: ForgeRunbookResult
    guardian_output: GuardianReviewResult
    final_episode: Episode


class RuntimeInput(TypedDict, total=False):
    alert_envelope: NormalizedAlertEnvelope
    context: IncidentContext
    task_board: NotRequired[list[dict[str, object]]]
    orchestration: NotRequired[dict[str, object]]
    memory_hits: NotRequired[dict[str, list[dict[str, object]]]]
    fallback_summary: NotRequired[list[dict[str, object]]]
    agent_metrics: NotRequired[dict[str, dict[str, object]]]
    branch_results: NotRequired[dict[str, dict[str, object]]]
    evidence_pack: NotRequired[dict[str, object]]
    triage_summary: NotRequired[dict[str, object]]


def normalize_pilot_health_status(
    raw_status: str | None,
    *,
    healthy_states: tuple[str, ...],
    partial_states: tuple[str, ...] = (),
    unavailable_states: tuple[str, ...] = (),
) -> str:
    value = str(raw_status or "").strip().lower()
    if value in {item.lower() for item in healthy_states}:
        return "healthy"
    if value in {item.lower() for item in unavailable_states}:
        return "unavailable"
    if value in {item.lower() for item in partial_states}:
        return "partial"
    return "partial" if value else "unavailable"


def build_pilot_safe_subsystem(
    *,
    service: str,
    raw_status: str | None,
    healthy_states: tuple[str, ...],
    partial_states: tuple[str, ...] = (),
    unavailable_states: tuple[str, ...] = (),
    guidance: list[str] | tuple[str, ...] | None = None,
    next_checks: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    posture = normalize_pilot_health_status(
        raw_status,
        healthy_states=healthy_states,
        partial_states=partial_states,
        unavailable_states=unavailable_states,
    )
    label = {
        "healthy": "Healthy for pilot use",
        "partial": "Partially available",
        "unavailable": "Unavailable",
    }[posture]
    guidance_list = [str(item).strip() for item in (guidance or []) if str(item).strip()]
    next_checks_list = [str(item).strip() for item in (next_checks or []) if str(item).strip()]
    summary = {
        "healthy": f"{service.title()} is operating within the current bounded pilot surface.",
        "partial": f"{service.title()} is degraded but still partially usable inside the bounded pilot flow.",
        "unavailable": f"{service.title()} is currently outside supported pilot operation and needs operator attention.",
    }[posture]
    return {
        "service": service,
        "raw_status": str(raw_status or "unknown"),
        "status": posture,
        "posture": posture,
        "label": label,
        "summary": summary,
        "guidance": guidance_list,
        "next_checks": next_checks_list,
    }


def summarize_pilot_surface(subsystems: list[dict[str, object]]) -> dict[str, object]:
    postures = [str(item.get("posture") or item.get("status") or "unavailable") for item in subsystems]
    if any(item == "unavailable" for item in postures):
        overall_posture = "unavailable"
    elif any(item == "partial" for item in postures):
        overall_posture = "partial"
    else:
        overall_posture = "healthy"

    attention_required = overall_posture != "healthy"
    next_checks: list[str] = []
    seen: set[str] = set()
    for subsystem in subsystems:
        if str(subsystem.get("posture") or subsystem.get("status")) == "healthy":
            continue
        for check in subsystem.get("next_checks", []):
            text = str(check).strip()
            if text and text not in seen:
                seen.add(text)
                next_checks.append(text)

    summary = {
        "healthy": "All pilot-critical subsystems are healthy for the bounded workflow.",
        "partial": "Some pilot-critical subsystems are degraded. Operators should use the bounded next checks below before continuing.",
        "unavailable": "One or more pilot-critical subsystems are unavailable. Keep the workflow bounded and follow the next checks before claiming runtime validation.",
    }[overall_posture]

    return {
        "overall_posture": overall_posture,
        "attention_required": attention_required,
        "summary": summary,
        "subsystems": subsystems,
        "next_checks": next_checks,
    }
