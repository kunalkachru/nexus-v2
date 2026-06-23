from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from server.services.classification import validate_supported_raw_text_classification
from server.services.intake import build_fresh_intake_truth, raw_input_quality


def test_raw_input_quality_returns_embedded_quality_dict() -> None:
    normalized_evidence = {
        "service": "checkout-svc",
        "input_quality": {
            "normalization_posture": "partial",
            "evidence_line_count": 4,
        },
    }

    assert raw_input_quality(normalized_evidence) == {
        "normalization_posture": "partial",
        "evidence_line_count": 4,
    }


def test_build_fresh_intake_truth_marks_inference_first_without_runtime_validation() -> None:
    incident = SimpleNamespace(
        raw_input_text="timeout while calling checkout",
        service="checkout-svc",
        severity="P1",
    )

    payload = build_fresh_intake_truth(
        incident=incident,
        normalized_evidence={
            "service": "checkout-svc",
            "severity": "P1",
            "signature": "retry amplification",
        },
        input_quality={
            "service_source": "tenant hint",
            "severity_source": "explicit hint",
            "evidence_line_count": 3,
            "normalization_posture": "partial",
            "missing_signals": ["owner confirmation"],
            "weak_signals": ["Signature is based on only one repeated log line."],
            "tenant_hints_applied": ["checkout-svc"],
        },
        issue_family="INC001",
        triage_summary={"likely_owner_team": "Checkout Platform"},
        support_state="inference-first",
        has_runtime_replay=False,
    )

    assert payload is not None
    assert payload["normalization_posture"] == "partial"
    assert payload["support_state"] == "inference-first"
    assert any(
        "runtime replay has not validated this case yet" in item
        for item in payload["remaining_uncertainty"]
    )
    assert any(
        signal["label"] == "Tenant hint" and signal["value"] == "checkout-svc"
        for signal in payload["extracted_signals"]
    )


def test_validate_supported_raw_text_classification_rejects_unbounded_family() -> None:
    parsed = SimpleNamespace(service="edge-cache", symptoms=["stale content", "cache misses"])

    class StubSentinel:
        def classify(self, *, raw_symptoms, system_context):  # noqa: ANN001 - test stub mirrors runtime call
            return SimpleNamespace(
                incident_id="INC999",
                incident_name="Unsupported cache issue",
                confidence=0.42,
            )

    with pytest.raises(HTTPException) as exc_info:
        validate_supported_raw_text_classification(
            sentinel=StubSentinel(),
            parsed=parsed,
            raw_text="stale content from the CDN edge cache after deploy",
        )

    detail = exc_info.value.detail
    assert exc_info.value.status_code == 400
    assert detail["error"] == "unsupported_incident_type"
    assert detail["matched_id"] == "INC999"
    assert detail["supported"] is False
    assert "8 supported families" in detail["message"]
