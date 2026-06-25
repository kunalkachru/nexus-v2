from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from server.services.live_ingest import RawIncidentParser
from server.services.classification import validate_supported_raw_text_classification
from server.services.intake import build_fresh_intake_truth, raw_input_quality
from server.services.investigation import root_cause_from_issue_family, runtime_aligned_live_runbook
from server.services.priority import normalize_priority_label


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
    assert "6 supported families" in detail["message"]


def test_validate_supported_raw_text_classification_rejects_noisy_cdn_family() -> None:
    parsed = SimpleNamespace(
        service="unknown-service",
        symptoms=["General incident", "customer complaining about slowness", "service=unknown-service", "severity=P3"],
    )

    class StubSentinel:
        def classify(self, *, raw_symptoms, system_context):  # noqa: ANN001 - test stub mirrors runtime call
            return SimpleNamespace(
                incident_id="INC009",
                incident_name="CDN / Cache Invalidation Failure",
                confidence=0.58,
            )

    with pytest.raises(HTTPException) as exc_info:
        validate_supported_raw_text_classification(
            sentinel=StubSentinel(),
            parsed=parsed,
            raw_text="customer complaining about slowness. not sure which service. alerts firing in grafana.",
        )

    detail = exc_info.value.detail
    assert exc_info.value.status_code == 400
    assert detail["matched_id"] == "INC009"
    assert detail["supported"] is False


def test_root_cause_from_issue_family_keeps_auth_dependency_language() -> None:
    root_cause = root_cause_from_issue_family("Auth Dependency Slowdown", "auth-api")

    assert "token validation slowdown" in root_cause
    assert "auth-api" in root_cause


def test_runtime_aligned_live_runbook_uses_runtime_candidate_fixes() -> None:
    runbook = runtime_aligned_live_runbook(
        issue_family="INC001",
        service="checkout-svc",
        reason="Keep live investigations aligned with bounded replay packs.",
    )

    assert runbook["summary"] == "Live mitigation plan for checkout-svc"
    assert runbook["candidate_fixes"]
    assert runbook["recommended_runbook"] == runbook["candidate_fixes"][0]["action"]


def test_normalize_priority_label_rejects_multi_digit_priority_tokens() -> None:
    assert normalize_priority_label("P99") == "P3"
    assert normalize_priority_label("P95") == "P3"


def test_raw_incident_parser_does_not_treat_p99_latency_as_priority() -> None:
    parser = RawIncidentParser()

    parsed = parser.parse(
        "service=auth-proxy p99 latency 8400ms while token validation requests time out",
    )

    assert parsed.severity == "P2"
    assert parsed.input_quality["severity_source"] == "default"
