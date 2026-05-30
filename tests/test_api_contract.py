import json
import hashlib
import hmac
import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from pathlib import Path

from server.app import app
from server.config import AppConfig
from server.db import create_session_factory
from server.db import DatabaseSession, get_db
from server.models import IncidentRecord


def _webhook_signature(body: str) -> str:
    secret = app.state.config.webhook_signing_secret
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_app_startup_wires_persistence_factory() -> None:
    with TestClient(app):
        assert hasattr(app.state, "config")
        assert hasattr(app.state, "db_session_factory")
        session = app.state.db_session_factory()
        assert isinstance(session, DatabaseSession)
        asyncio.run(session.close())


def test_get_db_uses_app_scoped_factory(tmp_path: Path) -> None:
    async def scenario() -> None:
        custom_app = FastAPI()
        custom_app.state.config = AppConfig(database_path=tmp_path / "app-scoped-incidents.json")
        custom_app.state.db_session_factory = create_session_factory(custom_app.state.config)
        scope = {"type": "http", "app": custom_app, "headers": [], "query_string": b""}
        generator = get_db(Request(scope))
        session = await anext(generator)

        assert isinstance(session, DatabaseSession)
        assert hasattr(session, "incidents")

        incident = await session.incidents.create_incident(
            external_id="inc_xyz",
            title="Payment API timeout",
            severity="P1",
        )
        await generator.aclose()

        assert custom_app.state.config.database_path.exists()

        verification_session = custom_app.state.db_session_factory()
        try:
            loaded = await verification_session.incidents.get_incident(incident.nexus_incident_id)
            assert loaded is not None
            assert loaded.external_id == "inc_xyz"
        finally:
            await verification_session.close()

    asyncio.run(scenario())


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seeded_incident(client: TestClient) -> IncidentRecord:
    async def scenario() -> IncidentRecord:
        session = app.state.db_session_factory()
        try:
            return await session.incidents.create_incident(
                external_id="inc_seeded",
                title="Seeded incident",
                severity="P2",
                tenant_id="tenant-a",
            )
        finally:
            await session.close()

    return asyncio.run(scenario())


def test_webhook_creates_nexus_incident(client: TestClient) -> None:
    body = {
        "incident_id": "inc_xyz",
        "title": "Payment API timeout",
        "severity": "P1",
        "detected_at": "2026-05-25T14:32:00Z",
        "monitoring_source": "datadog",
        "metrics": {"service": "payment-svc", "error_rate": 0.45},
    }
    payload = json.dumps(body, separators=(",", ":"))
    response = client.post(
        "/webhooks/incident",
        headers={
            "x-tenant-id": "tenant-system",
            "x-signature": _webhook_signature(payload),
            "content-type": "application/json",
        },
        content=payload,
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["external_id"] == "inc_xyz"
    assert payload["status"] == "investigating"
    assert payload["source"] == "datadog"
    assert payload["recent_deployments"] == []


def test_incident_status_returns_persisted_lifecycle(
    client: TestClient,
    seeded_incident: IncidentRecord,
    auth_headers,
) -> None:
    response = client.get(
        f"/incidents/{seeded_incident.nexus_incident_id}",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["nexus_incident_id"] == seeded_incident.nexus_incident_id
    assert payload["external_id"] == seeded_incident.external_id
    assert payload["status"] == "investigating"
    assert payload["source"] is None
    assert payload["recent_deployments"] == []


def test_incident_status_returns_404_for_unknown_incident(client: TestClient, auth_headers) -> None:
    response = client.get("/incidents/nxs_missing", headers=auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "incident not found"


def test_versioned_queue_contract_returns_current_incidents(client: TestClient, auth_headers) -> None:
    response = client.get("/api/v1/incidents/queue", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) >= 1
    first = payload["items"][0]
    assert first["nexus_incident_id"]
    assert first["title"]
    assert first["severity"] in {"P1", "P2", "P3", "P4"}
    assert first["status"] == "investigating"
    assert first["source_channel"] in {"webhook", "raw_text", "manual_form", "slack_command", "stream_anomaly", "batch_import"}
    assert first["current_stage"]
    assert first["updated_at"]


def test_manual_report_contract_creates_incident_and_status(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/manual-report",
        headers=auth_headers(),
        json={
            "affected_service": "billing-api",
            "symptoms": ["checkout latency", "timeout spikes"],
            "severity": "P0",
            "reported_by": "operator",
            "team": "platform",
            "additional_context": "Live checkout path is degraded.",
            "affected_regions": ["us-east-1"],
            "affected_hosts": ["billing-api-1"],
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "investigating"
    assert payload["source"] == "manual_form"
    assert payload["severity"] == "P1"
    assert payload["queue_position"] == 1
    assert payload["eta_sec"] == 30

    status_response = client.get(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/status',
        headers=auth_headers(),
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["current_stage"] == "validated_authenticated"
    assert len(status_payload["timeline"]) >= 1
    assert status_payload["audit_logs"]

    queue_response = client.get("/api/v1/incidents/queue", headers=auth_headers())
    assert queue_response.status_code == 200
    queue_items = queue_response.json()["items"]
    assert any(item["nexus_incident_id"] == payload["nexus_incident_id"] for item in queue_items)

    audit_log_path = Path.cwd() / ".nexus_audit_log.json"
    assert audit_log_path.exists()
    assert "incident.manual_report.accepted" in audit_log_path.read_text()


def test_guardian_review_contract_records_gate_and_execute(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/manual-report",
        headers=auth_headers(),
        json={
            "affected_service": "checkout-api",
            "symptoms": ["timeout spikes", "retry budget exhausted"],
            "severity": "P1",
            "reported_by": "operator",
            "team": "platform",
            "additional_context": "Need to validate the safety gate.",
        },
    )

    assert response.status_code == 202
    payload = response.json()

    review_response = client.post(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/guardian-review',
        headers=auth_headers(),
        json={
            "decision": "approve",
            "reasoning": "The proposed rollback path is safe to execute.",
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["guardian_decision"] == "approve"
    assert review_payload["guardian_reasoning"] == "The proposed rollback path is safe to execute."
    assert review_payload["status"] == "investigating"

    execute_response = client.post(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/execute',
        headers=auth_headers(),
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["status"] == "executed"
    assert execute_payload["guardian_decision"] == "approve"

    status_response = client.get(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/status',
        headers=auth_headers(),
    )
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["guardian_decision"] == "approve"
    assert status_payload["current_stage"] == "executed_verified_learned"

    platform_response = client.get("/api/v1/platform/status", headers=auth_headers())
    assert platform_response.status_code == 200
    platform_payload = platform_response.json()
    assert platform_payload["audit_events"] >= 1
    assert platform_payload["guardian_reviews"] >= 1


def test_guardian_block_contract_blocks_execution(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/manual-report",
        headers=auth_headers(),
        json={
            "affected_service": "billing-api",
            "symptoms": ["sudden error spike", "unknown side effects"],
            "severity": "P1",
            "reported_by": "operator",
            "team": "platform",
        },
    )

    assert response.status_code == 202
    payload = response.json()

    review_response = client.post(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/guardian-review',
        headers=auth_headers(),
        json={
            "decision": "reject",
            "reasoning": "The change is too risky to run during the incident.",
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["guardian_decision"] == "reject"
    assert review_payload["status"] == "blocked_by_guardian"

    execute_response = client.post(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/execute',
        headers=auth_headers(),
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["status"] == "blocked_by_guardian"
    assert execute_payload["guardian_decision"] == "reject"


def test_guardian_request_modification_contract_pauses_execution(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/manual-report",
        headers=auth_headers(),
        json={
            "affected_service": "billing-api",
            "symptoms": ["runbook needs revision", "safety review requested"],
            "severity": "P1",
            "reported_by": "operator",
            "team": "platform",
        },
    )

    assert response.status_code == 202
    payload = response.json()

    review_response = client.post(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/guardian-review',
        headers=auth_headers(),
        json={
            "decision": "request_modification",
            "reasoning": "The runbook needs a safer rollback sequence.",
        },
    )
    assert review_response.status_code == 200
    review_payload = review_response.json()
    assert review_payload["guardian_decision"] == "request_modification"
    assert review_payload["status"] == "needs_modification"
    assert review_payload["guardian_policy_id"].endswith(":request_modification")
    assert review_payload["guardian_policy_name"]
    assert review_payload["guardian_policy_basis"]

    execute_response = client.post(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/execute',
        headers=auth_headers(),
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["status"] == "needs_modification"
    assert execute_payload["guardian_decision"] == "request_modification"
    assert execute_payload["guardian_policy_id"].endswith(":request_modification")


def test_raw_text_contract_creates_incident_and_context(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/raw-text",
        headers=auth_headers(),
        json={
            "raw_text": "2026-05-30T10:14:22Z checkout-api ERROR timeout waiting for payment service\n2026-05-30T10:14:23Z checkout-api WARN retry budget exhausted\nservice=checkout-api severity=P4",
            "source_hint": "paste",
            "reported_by": "operator",
            "team": "platform",
            "severity_hint": "P4",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "investigating"
    assert payload["source"] == "raw_text"
    assert payload["severity"] == "P4"
    assert payload["queue_position"] == 1
    assert payload["eta_sec"] == 30

    context_response = client.get(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/context',
        headers=auth_headers(),
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["incident"]["source_channel"] == "raw_text"
    assert context_payload["incident"]["severity"] == "P4"
    assert context_payload["incident"]["raw_input_text"]
    assert context_payload["incident"]["normalized_evidence"]
    assert context_payload["observability"]["evidence_sources"][0]["source"] == "raw input"
    assert context_payload["observability"]["recent_logs"][0].startswith("Raw input normalized")
    assert context_payload["guardian"]["policy_id"]
    assert context_payload["structured_result"]["proposed_fix"]
    assert context_payload["structured_result"]["raw_priority_label"] == "P4"
    assert context_payload["structured_result"]["normalized_priority_rank"] == 4
    assert context_payload["structured_result"]["guardian_policy_id"]

    audit_log_path = Path.cwd() / ".nexus_audit_log.json"
    assert audit_log_path.exists()
    assert "incident.raw_text.accepted" in audit_log_path.read_text()


def test_raw_text_contract_accepts_arbitrary_priority_labels(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/raw-text",
        headers=auth_headers(),
        json={
            "raw_text": "2026-05-30T10:14:22Z checkout-api ERROR timeout waiting for payment service\nseverity=P6\npriority=critical",
            "source_hint": "paste",
            "reported_by": "operator",
            "team": "platform",
            "severity_hint": "P6",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["severity"] == "P6"

    context_response = client.get(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/context',
        headers=auth_headers(),
    )
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["incident"]["severity"] == "P6"
    assert context_payload["classification"]["severity"] == "P6"


def test_live_incident_context_contract_returns_backend_evidence(client: TestClient, auth_headers) -> None:
    create_response = client.post(
        "/api/v1/incidents/manual-report",
        headers=auth_headers(),
        json={
            "affected_service": "billing-api",
            "symptoms": ["checkout latency", "timeout spikes"],
            "severity": "P0",
            "reported_by": "operator",
            "team": "platform",
            "additional_context": "Live checkout path is degraded.",
            "affected_regions": ["us-east-1"],
            "affected_hosts": ["billing-api-1"],
        },
    )

    assert create_response.status_code == 202
    incident_id = create_response.json()["nexus_incident_id"]

    response = client.get(
        f"/api/v1/incidents/{incident_id}/context",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident"]["id"] == incident_id
    assert payload["incident"]["source_channel"] == "manual_form"
    assert payload["observability"]["evidence_sources"]
    assert payload["observability"]["recent_logs"]
    assert payload["observability"]["alert_timeline"]
    assert payload["classification"]["reasoning"]
    assert payload["diagnosis"]["correlation_analysis"]
    assert payload["runbook"]["candidate_fixes"]
    assert payload["guardian"]["safety_checks"]
    assert len(payload["workflow"]) >= 1
    assert payload["execution_result"] in {"executed", "blocked", "approved", "pending", "needs_modification"}


def test_batch_import_and_execute_contracts(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/batch-import",
        headers=auth_headers(),
        json={
            "batch_name": "replay_bundle",
            "source_uri": "s3://nexus/demo/replay_bundle.csv",
            "record_count": 128,
            "severity": "P1",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["source"] == "batch_import"

    audit_response = client.get(
        f'/api/v1/audit-logs/{payload["nexus_incident_id"]}',
        headers=auth_headers(),
    )
    assert audit_response.status_code == 200
    audit_payload = audit_response.json()
    assert audit_payload

    execute_response = client.post(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/execute',
        headers=auth_headers(),
    )
    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["incident_id"] == payload["nexus_incident_id"]
    assert execute_payload["status"] in {"executed", "blocked_by_guardian"}

    status_response = client.get(
        f'/api/v1/incidents/{payload["nexus_incident_id"]}/status',
        headers=auth_headers(),
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "resolved"


def test_slack_and_stream_intake_contracts(client: TestClient, auth_headers) -> None:
    slack_response = client.post(
        "/api/v1/incidents/slack-command",
        headers=auth_headers(),
        json={
            "command_id": "slack-123",
            "workspace": "nexus-ops",
            "channel": "#incidents",
            "user_id": "user-123",
            "service": "search-api",
            "severity": "P1",
            "text": "Slack intake: search API latency spike",
            "detected_at": "2026-05-29T14:00:00Z",
            "symptoms": ["indexing delay", "timeout spike"],
        },
    )
    stream_response = client.post(
        "/api/v1/incidents/stream-anomaly",
        headers=auth_headers(),
        json={
            "detector_id": "stream-456",
            "service": "worker-fleet",
            "severity": "P2",
            "detected_at": "2026-05-29T14:05:00Z",
            "signal_name": "rss-growth",
            "signal_value": "92%",
            "symptoms": ["RSS growth", "CPU pressure"],
            "observed_values": {"rss": 92, "cpu": 67},
        },
    )

    assert slack_response.status_code == 202
    assert stream_response.status_code == 202

    slack_payload = slack_response.json()
    stream_payload = stream_response.json()
    assert slack_payload["source"] == "slack_command"
    assert stream_payload["source"] == "stream_anomaly"

    queue_response = client.get("/api/v1/incidents/queue", headers=auth_headers())
    queue_items = queue_response.json()["items"]
    queue_ids = {item["nexus_incident_id"] for item in queue_items}
    assert slack_payload["nexus_incident_id"] in queue_ids
    assert stream_payload["nexus_incident_id"] in queue_ids


def test_history_replay_training_and_platform_contracts(client: TestClient, auth_headers) -> None:
    history_response = client.get("/api/v1/incidents/history", headers=auth_headers())
    replay_response = client.get("/api/v1/replay/scenarios", headers=auth_headers())
    training_response = client.get("/api/v1/training/summary", headers=auth_headers())
    platform_response = client.get("/api/v1/platform/status", headers=auth_headers())

    assert history_response.status_code == 200
    assert replay_response.status_code == 200
    assert training_response.status_code == 200
    assert platform_response.status_code == 200

    history_payload = history_response.json()
    replay_payload = replay_response.json()
    training_payload = training_response.json()
    platform_payload = platform_response.json()

    assert history_payload["items"]
    assert replay_payload["items"]
    assert training_payload["episode_records"]
    assert training_payload["summary"]
    assert training_payload["artifact_summary"]["training_snapshots"] >= 1
    assert training_payload["artifact_summary"]["learning_contracts"] >= 1
    assert training_payload["reward_evaluation"]["reward_curve_final"] >= 0.65
    assert training_payload["rl_episode_contract"]["observation"]["incident_id"]
    assert training_payload["rl_episode_contract"]["agent_trace"]
    assert training_payload["rl_episode_contract"]["raw_priority_label"]
    assert training_payload["rl_episode_contract"]["solution_proposal"]
    assert training_payload["rl_episode_contract"]["live_reasoning"] is False
    assert platform_payload["webhook_signature_verification"] == "Active"
    assert platform_payload["replay_launches"] >= 0
    assert platform_payload["training_snapshots"] >= 1
    assert platform_payload["contract_surface"]


def test_replay_launch_creates_live_incident(client: TestClient, auth_headers) -> None:
    scenarios_response = client.get("/api/v1/replay/scenarios", headers=auth_headers())
    assert scenarios_response.status_code == 200
    scenario_id = scenarios_response.json()["items"][0]["scenario_id"]

    launch_response = client.post(
        f"/api/v1/replay/scenarios/{scenario_id}/launch",
        headers=auth_headers(),
    )
    assert launch_response.status_code == 202
    launch_payload = launch_response.json()
    assert launch_payload["scenario_id"] == scenario_id
    assert launch_payload["nexus_incident_id"]
    artifact_path = Path.cwd() / "artifacts" / "platform_artifacts.json"
    assert artifact_path.exists()
    assert scenario_id in artifact_path.read_text()

    status_response = client.get(
        f'/api/v1/incidents/{launch_payload["nexus_incident_id"]}/status',
        headers=auth_headers(),
    )
    assert status_response.status_code == 200
    assert status_response.json()["source"] in {"webhook", "manual_form", "slack_command", "stream_anomaly", "batch_import"}
