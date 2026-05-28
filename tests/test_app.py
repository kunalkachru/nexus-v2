from fastapi.testclient import TestClient

from server.app import app


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_routes_are_served() -> None:
    client = TestClient(app)

    root = client.get("/")
    dashboard = client.get("/dashboard")

    assert root.status_code == 200
    assert dashboard.status_code == 200
    assert "NEXUS v2" in root.text
    assert "Reward Curve" in dashboard.text


def test_dashboard_serves_static_assets() -> None:
    client = TestClient(app)

    root = client.get("/dashboard")
    js = client.get("/static/dashboard.js")
    css = client.get("/static/dashboard.css")

    assert root.status_code == 200
    assert js.status_code == 200
    assert css.status_code == 200


def test_metrics_api_returns_dashboard_payload() -> None:
    client = TestClient(app)

    response = client.get("/api/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["baseline_reward"] == 0.28
    assert payload["summary"]["trained_reward"] >= 0.65
    assert len(payload["reward_curve"]) == 30


def test_run_incident_returns_realistic_incident_context() -> None:
    client = TestClient(app)

    response = client.get("/run-incident", params={"incident_id": "INC002"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["incident"]["id"] == "INC002"
    assert payload["classification"]["confidence"] >= 0.9
    assert payload["diagnosis"]["correlation_analysis"]
    assert len(payload["observability"]["recent_logs"]) == 20
    assert len(payload["observability"]["metrics"]) == 4
    assert payload["runbook"]["candidate_fixes"][0]["success_rate"] >= 0.9
    assert payload["guardian"]["safety_checks"]
