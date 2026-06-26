from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from server.services.support_contract import guidance_for_incident_id


@dataclass(frozen=True)
class AcceptedStratumCase:
    raw_text: str
    expected_incident_id: str
    expected_incident_name: str
    expected_issue_family: str
    expected_severity: str
    expected_classification_type: str


@dataclass(frozen=True)
class RejectedStratumCase:
    raw_text: str
    expected_matched_id: str
    expected_matched_family: str


ACCEPTED_CASES: dict[str, AcceptedStratumCase] = {
    "ST-001": AcceptedStratumCase(
        raw_text="CRITICAL P1: PostgreSQL connection pool exhausted on platform-api. All 200 connections in use. Customer namespaces cannot connect to their databases. Started 08:23 UTC. Coincides with deployment of platform-api v3.1.0 which added new async health-check polling every 100ms per customer namespace (50 customers = 5000 connections/sec). Logs: ERROR: remaining connection slots are reserved for non-replication superuser connections. Revenue impact: all 50 customers affected.",
        expected_incident_id="INC003",
        expected_incident_name="Deploy Regression / 5xx Spike",
        expected_issue_family="Deploy regression / 5xx spike",
        expected_severity="P1",
        expected_classification_type="ambiguous",
    ),
    "ST-002": AcceptedStratumCase(
        raw_text="pipeline-controller service crashing since 11:45 UTC deploy. Goroutine panic on nil pointer in reconcileCustomerPipeline(). Error: panic: runtime error: invalid memory address or nil pointer dereference. Deployed pipeline-controller v2.8.0 at 11:30 UTC adding multi-tenant pipeline isolation. 12 of 50 customers cannot trigger CI/CD pipelines. Other 38 customers unaffected. Cannot rollback — Kubernetes CRD schema migration ran. Error rate: 24% of pipeline trigger requests.",
        expected_incident_id="INC003",
        expected_incident_name="Deploy Regression / 5xx Spike",
        expected_issue_family="Deploy regression / 5xx spike",
        expected_severity="P1",
        expected_classification_type="single",
    ),
    "ST-004": AcceptedStratumCase(
        raw_text="Kafka consumer lag building on platform-events topic. Lag at 4.7M messages, growing at 200k/min. Normal consumer throughput 12000 msg/sec, current 800 msg/sec. Started 14:20 UTC. No consumer pod crashes. CPU and memory normal. Each message now taking 6ms (normal 0.4ms). Traced to enrichment step calling customer-metadata API which slowed from 2ms to 60ms per call after we deployed customer-metadata v1.9.0 at 14:00 UTC. Customers not receiving real-time pipeline status updates.",
        expected_incident_id="INC005",
        expected_incident_name="Queue Backlog Surge",
        expected_issue_family="Queue / worker backlog affecting transaction completion",
        expected_severity="P3",
        expected_classification_type="single",
    ),
    "ST-005": AcceptedStratumCase(
        raw_text="CRITICAL: TLS certificate expired for api.stratum.io at 03:00 UTC. All external API calls from customers failing with SSL handshake errors. Certificate was issued 2024-06-24, expired 2026-06-24, auto-renewal failed silently. cert-manager logs show: failed to renew certificate: ACME challenge failed, DNS propagation timeout. Affects 100% of customer API integrations. Internal services using internal CA working fine.",
        expected_incident_id="INC006",
        expected_incident_name="Expired TLS Certificate On API Gateway",
        expected_issue_family="Expired TLS Certificate On API Gateway",
        expected_severity="P1",
        expected_classification_type="single",
    ),
    "ST-007": AcceptedStratumCase(
        raw_text="Gateway service timeout cascade. Customer-facing API error rate 67%. P99 latency 32 seconds (SLA: 2 seconds). Upstream: terraform-executor service taking 45s per request instead of 800ms. Retries amplifying — each timeout triggers 3 retries with exponential backoff. terraform-executor waiting on AWS API calls which started throttling at 15:00 UTC due to rate limit hit. Customer impact: infrastructure provisioning completely stalled for all 50 tenants.",
        expected_incident_id="INC003",
        expected_incident_name="Deploy Regression / 5xx Spike",
        expected_issue_family="Deploy regression / 5xx spike",
        expected_severity="P1",
        expected_classification_type="ambiguous",
    ),
    "ST-012": AcceptedStratumCase(
        raw_text="Platform degraded across multiple layers since 16:30 UTC. Symptoms: (1) DB connection pool at 95% (180/200), (2) API error rate 18%, (3) Kafka consumer lag at 800k messages, (4) auth token validation p99 at 2400ms. Deployed platform-core v5.0.0 at 16:15 UTC — major refactor touching all four service layers simultaneously. Cannot identify single root cause. All symptoms appeared within 5 minutes of each other.",
        expected_incident_id="INC003",
        expected_incident_name="Deploy Regression / 5xx Spike",
        expected_issue_family="Deploy regression / 5xx spike",
        expected_severity="P2",
        expected_classification_type="ambiguous",
    ),
}


REJECTED_CASES: dict[str, RejectedStratumCase] = {
    "ST-003": RejectedStratumCase(
        raw_text="SSO authentication degraded for enterprise customers since 19:45 UTC. Auth-proxy service showing p99 latency 8400ms (normal 180ms). JWT validation requests to Okta timing out. Customers seeing 504 on /auth/callback. Already-authenticated sessions working. New logins failing. Okta status page green. Our auth-proxy CPU normal. Correlates with Okta configuration change we pushed at 19:30 UTC adding group-claim enrichment to SAML response.",
        expected_matched_id="INC010",
        expected_matched_family="ML Model Degradation",
    ),
    "ST-006": RejectedStratumCase(
        raw_text="Redis memory exhausted on metrics-cache cluster. 47GB used of 48GB limit. Eviction rate spiked to 180k/sec. Metrics API response times degraded from 12ms to 4200ms. Traced to new Prometheus metrics labels introduced in platform v4.0.0 deployed yesterday — added customer_namespace and pipeline_id as label dimensions. With 50 customers x 200 pipelines x 300 metrics = 3M unique time series vs previous 15k. OOM kill imminent.",
        expected_matched_id="INC004",
        expected_matched_family="Cache Cardinality Explosion",
    ),
    "ST-008": RejectedStratumCase(
        raw_text="Multiple customer workload pods OOMKilled in eu-west-1 cluster. 23 pods across 8 customer namespaces killed in last 30 minutes. Node memory pressure: 3 nodes at 94% memory. Kubernetes scheduler cannot reschedule pods — cluster at capacity. No single large deployment triggered this — gradual memory growth over past 6 hours across all namespaces. Vertical pod autoscaler not configured. Customers seeing application restarts and brief outages.",
        expected_matched_id="INC004",
        expected_matched_family="Cache Cardinality Explosion",
    ),
    "ST-009": RejectedStratumCase(
        raw_text="Terraform state locked for 3 customers. State file in S3 showing active lock from 2 hours ago. The process that acquired the lock (terraform-executor pod) crashed due to OOMKill but did not release the lock. Customers cannot run infrastructure changes — all terraform plan and apply commands failing with: Error acquiring the state lock. Lock ID: terraform-20260624-142300. DynamoDB lock table shows stale entry.",
        expected_matched_id="INC004",
        expected_matched_family="Cache Cardinality Explosion",
    ),
    "ST-010": RejectedStratumCase(
        raw_text="customer complaining about slowness. not sure which service. alerts firing in grafana. team is looking.",
        expected_matched_id="INC009",
        expected_matched_family="CDN / Cache Invalidation Failure",
    ),
    "ST-011": RejectedStratumCase(
        raw_text="ALERTNAME=HighErrorRate SEVERITY=critical SERVICE=platform-api NAMESPACE=stratum-prod VALUE=0.34 THRESHOLD=0.05 STARTED=2026-06-24T09:15:00Z LABELS={env=production, team=platform, customer_impact=true} ANNOTATIONS={summary=Error rate above 5% threshold, runbook=https://wiki.internal/runbooks/high-error-rate}",
        expected_matched_id="INC004",
        expected_matched_family="Cache Cardinality Explosion",
    ),
}


GUARDIAN_CASES = {
    "ST-001": ("approve", "investigating", "approved"),
    "ST-002": ("reject", "blocked_by_guardian", "blocked"),
    "ST-005": ("request_modification", "needs_modification", "needs_modification"),
}


def _operator_headers(auth_headers) -> dict[str, str]:
    return auth_headers(user_id="stratum-sre-lead", tenant_id="tenant-a", roles="operator")


def _guardian_headers(auth_headers) -> dict[str, str]:
    return auth_headers(user_id="stratum-sre-lead", tenant_id="tenant-a", roles="guardian")


def _submit_raw_text_case(client: TestClient, headers: dict[str, str], raw_text: str):
    return client.post(
        "/api/v1/incidents/raw-text",
        headers=headers,
        json={"raw_text": raw_text},
    )


def _assert_severity_consistency(context_payload: dict[str, object], expected_severity: str) -> None:
    incident = context_payload["incident"]
    classification = context_payload["classification"]
    assert incident["severity"] == expected_severity
    assert classification["severity"] == expected_severity
    assert classification["severity"] not in {"P99", "P95", "P50"}


@pytest.mark.parametrize("case_id", sorted(ACCEPTED_CASES))
def test_stratum_accepted_case_context_matches_current_contract(
    client: TestClient,
    auth_headers,
    case_id: str,
) -> None:
    case = ACCEPTED_CASES[case_id]

    create_response = _submit_raw_text_case(client, _operator_headers(auth_headers), case.raw_text)
    assert create_response.status_code == 202
    create_payload = create_response.json()
    assert create_payload["severity"] == case.expected_severity

    context_response = client.get(
        f'/api/v1/incidents/{create_payload["nexus_incident_id"]}/context',
        headers=_operator_headers(auth_headers),
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    classification = context_payload["classification"]

    assert classification["incident_id"] == case.expected_incident_id
    assert classification["incident_name"] == case.expected_incident_name
    assert classification["classification_strategy"] == "intake_canonical"
    assert classification["classification_type"] == case.expected_classification_type
    assert isinstance(classification["candidate_families"], list)
    assert context_payload["triage_summary"]["issue_family"] == case.expected_issue_family
    assert context_payload["incident"]["normalized_evidence"]["sentinel_classification"]["incident_id"] == case.expected_incident_id
    _assert_severity_consistency(context_payload, case.expected_severity)


@pytest.mark.parametrize("case_id", sorted(REJECTED_CASES))
def test_stratum_rejected_case_returns_structured_guidance_from_matched_family(
    client: TestClient,
    auth_headers,
    case_id: str,
) -> None:
    case = REJECTED_CASES[case_id]

    response = _submit_raw_text_case(client, _operator_headers(auth_headers), case.raw_text)
    assert response.status_code == 400
    payload = response.json()["detail"]

    assert payload["error"] == "unsupported_incident_type"
    assert payload["matched_id"] == case.expected_matched_id
    assert payload["matched_family"] == case.expected_matched_family
    assert payload["supported"] is False
    assert "6 supported families" in payload["message"]
    assert payload["general_investigation"] == guidance_for_incident_id(case.expected_matched_id)


@pytest.mark.parametrize("case_id", sorted(GUARDIAN_CASES))
def test_stratum_guardian_decisions_persist_across_status_and_context(
    client: TestClient,
    auth_headers,
    case_id: str,
) -> None:
    decision, expected_status, expected_execution_result = GUARDIAN_CASES[case_id]
    case = ACCEPTED_CASES[case_id]

    create_response = _submit_raw_text_case(client, _operator_headers(auth_headers), case.raw_text)
    assert create_response.status_code == 202
    incident_id = create_response.json()["nexus_incident_id"]

    decision_response = client.post(
        f"/api/v1/incidents/{incident_id}/guardian-decision",
        headers=_guardian_headers(auth_headers),
        json={"decision": decision, "notes": "Stratum corpus regression decision"},
    )
    assert decision_response.status_code == 200
    decision_payload = decision_response.json()
    assert decision_payload["guardian_decision"] == decision
    assert decision_payload["status"] == expected_status

    status_response = client.get(
        f"/api/v1/incidents/{incident_id}/status",
        headers=_operator_headers(auth_headers),
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["guardian_decision"] == decision
    assert status_payload["status"] == expected_status

    context_response = client.get(
        f"/api/v1/incidents/{incident_id}/context",
        headers=_operator_headers(auth_headers),
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["guardian"]["decision"] == decision
    assert context_payload["structured_result"]["safety_decision"] == decision
    assert context_payload["execution_result"] == expected_execution_result
    _assert_severity_consistency(context_payload, case.expected_severity)
