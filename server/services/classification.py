from typing import Any, Protocol

from fastapi import HTTPException

from server.models import SystemContext
from server.services.support_contract import (
    RAW_TEXT_SUPPORTED_FAMILIES,
    guidance_for_incident_id,
    supported_family_names,
    supported_family_message,
)


class SupportsSentinel(Protocol):
    def classify(self, *, raw_symptoms: list[str], system_context: SystemContext) -> Any: ...


class SupportsParsedRawText(Protocol):
    service: str
    symptoms: list[str]
    signature: str
    input_quality: dict[str, object]


def investigation_guidance_for_incident_id(incident_id: str) -> dict[str, object]:
    return guidance_for_incident_id(incident_id)


def validate_supported_raw_text_classification(
    *,
    sentinel: SupportsSentinel,
    parsed: SupportsParsedRawText,
    raw_text: str,
) -> Any:
    system_context = SystemContext(
        service=parsed.service,
        language="Unknown",
        infra="Unknown",
        dependencies=[],
    )
    classification = sentinel.classify(
        raw_symptoms=parsed.symptoms,
        system_context=system_context,
    )
    input_quality = dict(getattr(parsed, "input_quality", {}) or {})
    normalization_posture = str(input_quality.get("normalization_posture") or "weak")
    signature = str(getattr(parsed, "signature", "") or "General incident")
    top_candidate_score = 0.0
    if getattr(classification, "candidate_families", None):
        first_candidate = classification.candidate_families[0]
        if isinstance(first_candidate, dict):
            top_candidate_score = float(first_candidate.get("score") or 0.0)
    weak_general_intake = (
        normalization_posture == "weak"
        and signature == "General incident"
        and getattr(classification, "classification_type", "single") == "ambiguous"
        and top_candidate_score < 8.0
    )

    if classification.incident_id in RAW_TEXT_SUPPORTED_FAMILIES and not weak_general_intake:
        return classification

    raise HTTPException(
        status_code=400,
        detail={
            "error": "unsupported_incident_type",
            "message": supported_family_message(),
            "confidence": float(classification.confidence),
            "matched_family": classification.incident_name,
            "matched_id": classification.incident_id,
            "supported": False,
            "general_investigation": investigation_guidance_for_incident_id(classification.incident_id),
            "supported_families": supported_family_names(),
        },
    )
