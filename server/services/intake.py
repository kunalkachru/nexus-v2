from typing import Any, Protocol

from fastapi import HTTPException

from server.integrations.models import RawIncidentTextRequest
from server.services.compose_validator import ComposeValidationError, ComposeValidator


class SupportsFreshIncidentContext(Protocol):
    raw_input_text: str | None
    service: str | None
    severity: str | None


def raw_input_quality(normalized_evidence: dict[str, object]) -> dict[str, object]:
    quality = normalized_evidence.get("input_quality", {})
    return dict(quality) if isinstance(quality, dict) else {}


def build_fresh_intake_truth(
    *,
    incident: SupportsFreshIncidentContext,
    normalized_evidence: dict[str, object],
    input_quality: dict[str, object],
    issue_family: str,
    triage_summary: dict[str, object],
    support_state: str,
    has_runtime_replay: bool,
) -> dict[str, object] | None:
    if not incident.raw_input_text:
        return None

    service = str(normalized_evidence.get("service") or incident.service or "unknown-service")
    severity = str(normalized_evidence.get("severity") or incident.severity or "P2")
    signature = str(normalized_evidence.get("signature") or "General incident")
    service_source = str(input_quality.get("service_source") or "defaulted")
    severity_source = str(input_quality.get("severity_source") or "default")
    evidence_line_count = int(input_quality.get("evidence_line_count") or 0)
    posture = str(input_quality.get("normalization_posture") or "weak")
    likely_owner = str(
        triage_summary.get("likely_owner_team")
        or triage_summary.get("likely_owner_service")
        or "Platform Operations"
    )

    extracted_signals: list[dict[str, str]] = [
        {
            "label": "Service token",
            "value": service,
            "source": service_source,
        },
        {
            "label": "Severity hint",
            "value": severity,
            "source": severity_source,
        },
    ]
    if signature and signature != "General incident":
        extracted_signals.append({
            "label": "Signature",
            "value": signature,
            "source": "log pattern",
        })
    extracted_signals.append({
        "label": "Evidence lines",
        "value": str(evidence_line_count),
        "source": "raw input",
    })
    for match in input_quality.get("tenant_hints_applied", []) or []:
        extracted_signals.append({
            "label": "Tenant hint",
            "value": str(match),
            "source": "tenant bootstrap",
        })

    inferred_conclusions = [
        {
            "label": "Issue family",
            "value": issue_family or "Unclassified live incident",
        },
        {
            "label": "Likely owner",
            "value": likely_owner,
        },
        {
            "label": "Support posture",
            "value": support_state,
        },
        {
            "label": "Next bounded path",
            "value": "REPLICA → TRACE → FORGE → GUARDIAN"
            if support_state != "unsupported"
            else "FORGE → GUARDIAN with inferred evidence only",
        },
    ]

    remaining_uncertainty: list[str] = []
    for signal in input_quality.get("missing_signals", []) or []:
        remaining_uncertainty.append(f"Missing {signal} confirmation from the pasted evidence.")
    for warning in input_quality.get("weak_signals", []) or []:
        remaining_uncertainty.append(str(warning))
    if support_state == "unsupported":
        remaining_uncertainty.append(
            "This incident family is outside the bounded runtime packs, so runtime validation is not available."
        )
    elif support_state == "inference-first" and not has_runtime_replay:
        remaining_uncertainty.append(
            "The current path is still inference-first because bounded runtime replay has not validated this case yet."
        )
    elif support_state == "runtime-backed" and not has_runtime_replay:
        remaining_uncertainty.append(
            "Pack coverage exists, but this fresh incident has not yet been validated through bounded replay in this page view."
        )

    summary = (
        f"Fresh intake posture is {posture}. "
        f"NEXUS extracted {len(extracted_signals)} concrete signal(s) from the logs, inferred {len(inferred_conclusions)} routing and action clue(s), "
        f"and is tracking {len(remaining_uncertainty)} remaining uncertainty item(s)."
    )

    return {
        "is_fresh_incident": True,
        "normalization_posture": posture,
        "support_state": support_state,
        "summary": summary,
        "operator_guidance": str(
            input_quality.get("operator_guidance")
            or "Review the extracted versus inferred split before treating this packet as decision-ready."
        ),
        "extracted_signals": extracted_signals,
        "inferred_conclusions": inferred_conclusions,
        "remaining_uncertainty": remaining_uncertainty,
    }


def validate_docker_compose_content(docker_compose_content: str | None) -> str | None:
    if not docker_compose_content:
        return None

    try:
        ComposeValidator.validate_compose_content(docker_compose_content)
    except ComposeValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_docker_compose",
                "message": f"Docker Compose validation failed: {exc}",
            },
        ) from exc

    return docker_compose_content


def build_raw_text_normalized_evidence(
    *,
    parsed: Any,
    payload: RawIncidentTextRequest,
    docker_compose_content: str | None,
) -> dict[str, object]:
    normalized_evidence = {
        "service": parsed.service,
        "severity": parsed.severity,
        "signature": parsed.signature,
        "evidence": parsed.evidence,
        "symptoms": parsed.symptoms,
        "input_quality": parsed.input_quality,
        "source_hint": payload.source_hint,
        "reported_by": payload.reported_by,
        "team": payload.team,
    }
    if docker_compose_content:
        normalized_evidence["docker_compose"] = docker_compose_content
    return normalized_evidence
