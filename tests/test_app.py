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
    assert "Command Center" in dashboard.text
    assert "Command Center" in queue.text
    assert "Agent Crew" in queue.text
    assert "SENTINEL" in queue.text
    assert "PRISM" in queue.text
    assert "FORGE" in queue.text
    assert "GUARDIAN" in queue.text
    assert "Incident Detail" in incident.text
    assert "Agent Handoff Thread" in incident.text
    assert "Enterprise Task Board" in incident.text
    assert "Memory-grounded context" in incident.text
    assert "SENTINEL handed evidence to PRISM" in incident.text
    assert "Governance Bot" in incident.text
    assert "Working memory" in incident.text
    assert "Expand technical detail" in incident.text
    assert "Input Channels" in inputs.text
    assert "Paste Raw Logs" in inputs.text
    assert "Incident archive." in history.text
    assert "Replay validation." in replay.text
    assert "certificate expiry" in replay.text.lower()
    assert "Learning & Controls" in training.text
    assert "Enterprise runtime summary" in training.text
    assert "Learning summary" in training.text
    assert "Governance summary" in training.text
    assert "Advanced artifacts" in training.text
    assert "Operational controls." in settings.text
    assert 'href="queue"' in incident.text


def test_primary_navigation_is_reduced_to_three_screens() -> None:
    client = TestClient(app)

    for route in ["/", "/queue", "/incident", "/training", "/inputs", "/history", "/replay", "/settings"]:
        response = client.get(route)

        assert response.status_code == 200
        assert response.text.count('class="nav-link') >= 3
        assert "Command Center" in response.text
        assert "Incident Detail" in response.text
        assert "Learning &amp; Controls" in response.text or "Learning & Controls" in response.text
        assert 'href="inputs"' not in response.text.split("</nav>", maxsplit=1)[0]
        assert 'href="history"' not in response.text.split("</nav>", maxsplit=1)[0]
        assert 'href="replay"' not in response.text.split("</nav>", maxsplit=1)[0]
        assert 'href="settings"' not in response.text.split("</nav>", maxsplit=1)[0]


def test_advanced_routes_are_demoted_but_still_linked_contextually() -> None:
    client = TestClient(app)

    queue = client.get("/queue")
    incident = client.get("/incident")
    training = client.get("/training")

    assert queue.status_code == 200
    assert incident.status_code == 200
    assert training.status_code == 200
    assert 'href="history"' in queue.text
    assert 'href="replay"' in queue.text
    assert 'href="inputs"' in incident.text
    assert 'href="settings"' in training.text


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


def test_primary_screens_hide_dense_details_by_default() -> None:
    client = TestClient(app)

    queue = client.get("/queue")
    incident = client.get("/incident")
    training = client.get("/training")

    assert "Queue Controls" not in queue.text
    assert "Episode History" not in training.text
    assert "RL Episode Contract" not in training.text
    assert "Observation States" not in training.text
    assert "Workflow Timeline" not in incident.text
    assert "Audit summary" not in incident.text
    assert "Raw Intake" not in incident.text


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
    assert payload["orchestration"]["state"] == "completed"
    assert payload["task_board"]["tasks"]
    assert payload["memory_hits"]["similar_incidents"]
    assert payload["agent_metrics"]["prism"]["handoff_to"] == "FORGE"
