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
    if classification.incident_id in RAW_TEXT_SUPPORTED_FAMILIES:
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
