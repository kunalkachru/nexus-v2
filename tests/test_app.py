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
    queue = client.get("/queue")
    incident = client.get("/incident")
    history = client.get("/history")
    inputs = client.get("/inputs")
    replay = client.get("/replay")
    training = client.get("/training")
    settings = client.get("/settings")

    assert root.status_code == 200
    assert dashboard.status_code == 200
    assert queue.status_code == 200
    assert incident.status_code == 200
    assert history.status_code == 200
    assert inputs.status_code == 200
    assert replay.status_code == 200
    assert training.status_code == 200
    assert settings.status_code == 200
    assert "NEXUS v2" in root.text
    assert 'static/app-shell.js' in root.text
    assert "Incident Queue" in dashboard.text
    assert "Incident Queue" in queue.text
    assert "SENTINEL" not in queue.text
    assert "Incident Console" in incident.text
    assert "SENTINEL" in incident.text
    assert "Workflow Timeline" in incident.text
    assert "Audit summary" in incident.text
    assert "Evidence Provenance" in incident.text
    assert "Raw Intake" in incident.text
    assert "Normalized evidence" in incident.text
    assert "Evidence details" in incident.text
    assert "Raw input → evidence bundle" in incident.text
    assert "flowing from" in incident.text
    assert "Input Channels" in inputs.text
    assert "Paste Raw Logs" in inputs.text
    assert "Raw Incident Intake Preview" in inputs.text
    assert "Submit raw logs" in inputs.text
    assert "Detected service" in inputs.text
    assert "Webhook" in inputs.text
    assert "Slack Command" in inputs.text
    assert "Open reasoning console" in inputs.text
    assert "Incident archive." in history.text
    assert "Replay validation." in replay.text
    assert "certificate expiry" in replay.text.lower()
    assert "Learning operations." in training.text
    assert "Episode History" in training.text
    assert "RL Episode Contract" in training.text
    assert "Reward evaluation" in training.text
    assert "Observation States" in training.text
    assert "Operational controls." in settings.text
    assert "Signature" in settings.text
    assert "Learning Curves" in training.text
    assert "Back to queue" in incident.text
    assert "Current page:" not in root.text
    assert "Current page:" not in incident.text
    assert "Current page:" not in inputs.text
    assert "Current page:" not in history.text
    assert "Current page:" not in replay.text
    assert "Current page:" not in training.text
    assert "Current page:" not in settings.text
    assert 'href="history"' in root.text
    assert 'href="inputs"' in root.text
    assert 'href="replay"' in root.text
    assert 'href="training"' in root.text
    assert 'href="settings"' in root.text
    assert 'href="queue"' in incident.text


def test_dashboard_serves_static_assets() -> None:
    client = TestClient(app)

    root = client.get("/dashboard")
    queue_js = client.get("/static/queue.js")
    settings_js = client.get("/static/settings.js")
    training_js = client.get("/static/training.js")
    css = client.get("/static/dashboard.css")

    assert root.status_code == 200
    assert queue_js.status_code == 200
    assert settings_js.status_code == 200
    assert training_js.status_code == 200
    assert css.status_code == 200


def test_metrics_api_returns_dashboard_payload() -> None:
    client = TestClient(app)

    response = client.get("/api/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["baseline_reward"] == 0.28
    assert payload["summary"]["trained_reward"] >= 0.65
    assert len(payload["reward_curve"]) == 30
    assert len(payload["workflow_observation_states"]) == 9
    assert payload["latest_episode"]["incident_id"]
    assert payload["queue_snapshot"]["open_incidents"] >= 1
    assert payload["platform_status"]["mode"] == "Product"


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
    assert payload["observability"]["evidence_sources"]
    assert payload["runbook"]["candidate_fixes"][0]["success_rate"] >= 0.9
    assert payload["guardian"]["safety_checks"]
    assert len(payload["workflow"]) == 9
