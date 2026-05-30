# Enterprise Workflow UI Implementation Plan

> Historical execution plan. The repo now reflects this work, and live status is tracked in [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](../../NEXUS_v2_DOC_STATUS_MATRIX.md) and [docs/NEXUS_v2_PRIORITY_BACKLOG.md](../../NEXUS_v2_PRIORITY_BACKLOG.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-page enterprise NEXUS web app that shows intake, evidence retrieval, agent contributions, sample incident replay, and the RL training story through one consistent incident workflow.

**Architecture:** Keep FastAPI as the application server and retain a build-free frontend, but refactor the current demo into a route-driven product shell. The backend will expose canonical incident, timeline, replay, training, and settings APIs; the frontend will render Queue, Incident Console, Input Channels, History, Sample Replay, RL Training Lab, and Settings pages from those APIs.

**Tech Stack:** FastAPI, Pydantic v2, existing file-backed persistence, deterministic replay fixtures, vanilla HTML/CSS/ES modules, pytest, Docker, docker compose, Kubernetes manifests.

---

## File Structure

### Backend

- Create: `server/routes/__init__.py`
- Create: `server/routes/pages.py`
- Create: `server/routes/incidents.py`
- Create: `server/routes/inputs.py`
- Create: `server/routes/replay.py`
- Create: `server/routes/training.py`
- Create: `server/routes/settings.py`
- Create: `server/services/workflow.py`
- Create: `server/services/replay.py`
- Create: `server/services/training_lab.py`
- Modify: `server/app.py`
- Modify: `server/models.py`
- Modify: `server/repositories.py`
- Modify: `server/services/incidents.py`
- Modify: `server/config.py`

### Incident and replay fixtures

- Create: `incidents/replay_catalog.py`
- Create: `incidents/replay_samples/api-timeout.json`
- Create: `incidents/replay_samples/db-pool.json`
- Create: `incidents/replay_samples/redis-saturation.json`
- Create: `incidents/replay_samples/memory-leak.json`
- Create: `incidents/replay_samples/queue-backlog.json`
- Create: `incidents/replay_samples/bad-deploy.json`
- Create: `incidents/replay_samples/cert-expiry.json`
- Create: `incidents/replay_samples/cache-explosion.json`

### Frontend

- Create: `frontend/queue.html`
- Create: `frontend/incident.html`
- Create: `frontend/inputs.html`
- Create: `frontend/history.html`
- Create: `frontend/replay.html`
- Create: `frontend/training.html`
- Create: `frontend/settings.html`
- Create: `frontend/static/app-shell.css`
- Create: `frontend/static/app-shell.js`
- Create: `frontend/static/client.js`
- Create: `frontend/static/formatters.js`
- Create: `frontend/static/queue.js`
- Create: `frontend/static/incident.js`
- Create: `frontend/static/inputs.js`
- Create: `frontend/static/history.js`
- Create: `frontend/static/replay.js`
- Create: `frontend/static/training.js`
- Create: `frontend/static/settings.js`
- Modify: `frontend/dashboard.html`
- Modify: `frontend/static/api.js`
- Modify: `frontend/static/dashboard.css`
- Modify: `frontend/static/dashboard.js`

### Tests

- Create: `tests/test_page_routes.py`
- Create: `tests/test_workflow_api.py`
- Create: `tests/test_input_channels.py`
- Create: `tests/test_replay.py`
- Create: `tests/test_training_lab.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_app.py`
- Modify: `tests/test_api_contract.py`
- Modify: `tests/test_deployment.py`

### Containerization and docs

- Create: `ops/docker/entrypoint.sh`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `ops/kubernetes/deployment.yaml`
- Modify: `ops/kubernetes/configmap.yaml`
- Modify: `README.md`
- Modify: `docs/OPERATIONS.md`

### References To Read Before Starting

- `docs/superpowers/specs/2026-05-28-enterprise-workflow-ui-design.md`
- `design-docs/NEXUS_v2_Design_Document.md`
- `design-docs/NEXUS_v2_Master_Product_Document.md`
- `/Users/kunalkachru/Downloads/NEXUS_v2_ENTERPRISE_SPECIFICATION.md`

### Task 1: Establish Canonical Workflow Contracts And Route Modules

**Files:**
- Create: `server/routes/__init__.py`
- Create: `server/routes/pages.py`
- Create: `server/routes/incidents.py`
- Modify: `server/app.py`
- Modify: `server/models.py`
- Test: `tests/test_page_routes.py`
- Test: `tests/test_workflow_api.py`

- [ ] **Step 1: Write failing route and model tests**

```python
from fastapi.testclient import TestClient

from server.app import app


def test_queue_and_page_routes_are_served() -> None:
    client = TestClient(app)

    assert client.get("/").status_code == 200
    assert client.get("/queue").status_code == 200
    assert client.get("/incident").status_code == 200
    assert client.get("/inputs").status_code == 200
    assert client.get("/replay").status_code == 200
    assert client.get("/training").status_code == 200


def test_queue_api_returns_stage_aware_incident_records(auth_headers) -> None:
    client = TestClient(app)

    response = client.get("/api/v1/incidents/queue", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `pytest tests/test_page_routes.py tests/test_workflow_api.py -v`
Expected: FAIL with missing routes such as `/queue` or `/api/v1/incidents/queue`.

- [ ] **Step 3: Add workflow enums and shared response models**

```python
from enum import Enum

from pydantic import BaseModel, Field


class IncidentWorkflowStage(str, Enum):
    INCIDENT_RECEIVED = "incident_received"
    VALIDATED_AUTHENTICATED = "validated_authenticated"
    ENRICHED_WITH_SERVICE_CONTEXT = "enriched_with_service_context"
    EVIDENCE_RETRIEVED = "evidence_retrieved"
    SENTINEL_CLASSIFIED = "sentinel_classified"
    PRISM_DIAGNOSED = "prism_diagnosed"
    FORGE_PROPOSED_RUNBOOK = "forge_proposed_runbook"
    GUARDIAN_REVIEWED_SAFETY = "guardian_reviewed_safety"
    EXECUTED_VERIFIED_LEARNED = "executed_verified_learned"


class QueueIncidentSummary(BaseModel):
    nexus_incident_id: str
    title: str
    severity: str
    status: str
    source_channel: str
    current_stage: IncidentWorkflowStage
    updated_at: str


class QueueResponse(BaseModel):
    items: list[QueueIncidentSummary] = Field(default_factory=list)
```

- [ ] **Step 4: Split page and incident routing out of `server/app.py`**

```python
from fastapi import APIRouter
from fastapi.responses import FileResponse

pages_router = APIRouter()


@pages_router.get("/")
async def root() -> FileResponse:
    return FileResponse("frontend/queue.html", media_type="text/html")


@pages_router.get("/queue")
async def queue_page() -> FileResponse:
    return FileResponse("frontend/queue.html", media_type="text/html")


@pages_router.get("/incident")
async def incident_page() -> FileResponse:
    return FileResponse("frontend/incident.html", media_type="text/html")


@pages_router.get("/inputs")
async def inputs_page() -> FileResponse:
    return FileResponse("frontend/inputs.html", media_type="text/html")
```

- [ ] **Step 5: Wire routers in the FastAPI app**

```python
from server.routes.incidents import incidents_router
from server.routes.pages import pages_router

app.include_router(pages_router)
app.include_router(incidents_router)
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_page_routes.py tests/test_workflow_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/routes/__init__.py server/routes/pages.py server/routes/incidents.py server/app.py server/models.py tests/test_page_routes.py tests/test_workflow_api.py
git commit -m "feat: add workflow route foundation"
```

### Task 2: Persist Queue State, Timeline Events, Evidence, And History

**Files:**
- Create: `server/services/workflow.py`
- Modify: `server/repositories.py`
- Modify: `server/services/incidents.py`
- Modify: `server/models.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_workflow_api.py`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_persistence.py`

- [ ] **Step 1: Write failing tests for queue, detail, and timeline APIs**

```python
def test_incident_detail_returns_timeline_and_agent_sections(client, auth_headers, seeded_incident) -> None:
    response = client.get(
        f"/api/v1/incidents/{seeded_incident.nexus_incident_id}",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert "timeline" in payload
    assert "agent_contributions" in payload
    assert "evidence" in payload


def test_history_api_returns_closed_incidents(client, auth_headers) -> None:
    response = client.get("/api/v1/incidents/history", headers=auth_headers())

    assert response.status_code == 200
    assert "items" in response.json()
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run: `pytest tests/test_workflow_api.py tests/test_api_contract.py tests/test_persistence.py -v`
Expected: FAIL with missing repository methods or missing response keys.

- [ ] **Step 3: Extend persisted records to track stage, timestamps, and audit-friendly event history**

```python
class IncidentTimelineEvent(BaseModel):
    stage: IncidentWorkflowStage
    status: str
    title: str
    summary: str
    actor: str
    created_at: str
    detail: dict[str, object] = Field(default_factory=dict)


class IncidentDetailResponse(BaseModel):
    incident: QueueIncidentSummary
    timeline: list[IncidentTimelineEvent]
    evidence: dict[str, object]
    agent_contributions: dict[str, dict[str, object]]
    action_panel: dict[str, object]
    audit_entries: list[dict[str, object]]
```

- [ ] **Step 4: Add repository methods for queue listing, timeline append, detail loading, and history listing**

```python
class IncidentRepository:
    async def list_active_incidents(self, tenant_id: str) -> list[IncidentRecord]:
        ...

    async def list_historical_incidents(self, tenant_id: str) -> list[IncidentRecord]:
        ...

    async def append_timeline_event(
        self,
        nexus_incident_id: str,
        event: IncidentTimelineEvent,
    ) -> None:
        ...
```

- [ ] **Step 5: Add a workflow service that translates stored incidents into queue and detail view models**

```python
class WorkflowService:
    def __init__(self, session) -> None:
        self._session = session

    async def get_queue(self, tenant_id: str) -> QueueResponse:
        ...

    async def get_incident_detail(self, nexus_incident_id: str, tenant_id: str) -> IncidentDetailResponse:
        ...
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_workflow_api.py tests/test_api_contract.py tests/test_persistence.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/services/workflow.py server/repositories.py server/services/incidents.py server/models.py tests/conftest.py tests/test_workflow_api.py tests/test_api_contract.py tests/test_persistence.py
git commit -m "feat: persist workflow timeline and history views"
```

### Task 3: Add Enterprise Intake APIs For Webhook, Manual, Slack-Style, Stream, And Batch Inputs

**Files:**
- Create: `server/routes/inputs.py`
- Modify: `server/integrations/models.py`
- Modify: `server/integrations/alerts.py`
- Modify: `server/services/incidents.py`
- Modify: `server/models.py`
- Test: `tests/test_input_channels.py`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_integrations.py`

- [ ] **Step 1: Write failing tests for all supported intake channels**

```python
def test_manual_report_creates_incident(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/manual-report",
        headers=auth_headers(),
        json={
            "affected_service": "payment-service",
            "symptoms": ["Requests timing out", "High error rate"],
            "severity": "P0",
            "reported_by": "sre@example.com",
            "team": "payments",
        },
    )

    assert response.status_code == 202
    assert response.json()["source_channel"] == "manual_form"


def test_batch_import_accepts_multiple_incidents(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/batch-import",
        headers=auth_headers(),
        json={"batch_id": "batch-001", "source": "recovery", "incidents": []},
    )

    assert response.status_code == 202
```

- [ ] **Step 2: Run the intake tests and verify they fail**

Run: `pytest tests/test_input_channels.py tests/test_api_contract.py tests/test_integrations.py -v`
Expected: FAIL with missing `/api/v1/incidents/manual-report` or `/api/v1/incidents/batch-import`.

- [ ] **Step 3: Add normalized request models for each intake channel**

```python
class ManualIncidentReport(BaseModel):
    affected_service: str
    symptoms: list[str]
    severity: str
    reported_by: str
    team: str
    root_cause_suspected: str | None = None
    additional_context: str | None = None


class BatchIncidentImport(BaseModel):
    batch_id: str
    source: str
    incidents: list[dict[str, object]]
```

- [ ] **Step 4: Expose intake endpoints that all normalize into one workflow creation path**

```python
@inputs_router.post("/api/v1/incidents/manual-report", status_code=202)
async def create_manual_report(...) -> dict[str, object]:
    return await service.create_from_manual_report(payload, auth=auth)


@inputs_router.post("/api/v1/incidents/batch-import", status_code=202)
async def create_batch_import(...) -> dict[str, object]:
    return await service.create_from_batch_import(payload, auth=auth)
```

- [ ] **Step 5: Record intake-specific first-stage timeline events**

```python
await repository.append_timeline_event(
    incident_id,
    IncidentTimelineEvent(
        stage=IncidentWorkflowStage.INCIDENT_RECEIVED,
        status="completed",
        title="Incident received",
        summary="Manual report submitted from Input Channels page.",
        actor=auth.user_id,
        created_at=timestamp,
        detail={"source_channel": "manual_form"},
    ),
)
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_input_channels.py tests/test_api_contract.py tests/test_integrations.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/routes/inputs.py server/integrations/models.py server/integrations/alerts.py server/services/incidents.py server/models.py tests/test_input_channels.py tests/test_api_contract.py tests/test_integrations.py
git commit -m "feat: add enterprise intake channel apis"
```

### Task 4: Add Sample Replay Fixtures And Replay APIs

**Files:**
- Create: `incidents/replay_catalog.py`
- Create: `incidents/replay_samples/api-timeout.json`
- Create: `incidents/replay_samples/db-pool.json`
- Create: `incidents/replay_samples/redis-saturation.json`
- Create: `incidents/replay_samples/memory-leak.json`
- Create: `incidents/replay_samples/queue-backlog.json`
- Create: `incidents/replay_samples/bad-deploy.json`
- Create: `incidents/replay_samples/cert-expiry.json`
- Create: `incidents/replay_samples/cache-explosion.json`
- Create: `server/services/replay.py`
- Create: `server/routes/replay.py`
- Test: `tests/test_replay.py`
- Test: `tests/test_workflow_api.py`

- [ ] **Step 1: Write failing tests for scenario listing and replay launch**

```python
def test_replay_scenarios_are_listed(client, auth_headers) -> None:
    response = client.get("/api/v1/replay/scenarios", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) >= 5


def test_launching_replay_creates_incident(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/incidents/replay/api-timeout",
        headers=auth_headers(),
    )

    assert response.status_code == 202
    assert response.json()["source_channel"] == "replay"
```

- [ ] **Step 2: Run the replay tests and verify they fail**

Run: `pytest tests/test_replay.py tests/test_workflow_api.py -v`
Expected: FAIL with missing replay routes or missing replay fixtures.

- [ ] **Step 3: Add curated replay scenarios as JSON fixtures**

```json
{
  "scenario_id": "api-timeout",
  "title": "API timeout cascade",
  "source_channel": "webhook",
  "service": "payment-service",
  "severity": "P0",
  "workflow": {
    "classification": {"type": "ResourceExhaustion", "confidence": 0.92},
    "diagnosis": {"root_cause": "Redis connection pool exhausted"},
    "runbook": {"language": "bash", "estimated_duration_min": 5},
    "guardian": {"decision": "approve", "safety_score": 0.95}
  }
}
```

- [ ] **Step 4: Build a replay service that converts fixtures into live incident records and timeline events**

```python
class ReplayService:
    async def list_scenarios(self) -> dict[str, object]:
        ...

    async def launch_scenario(self, scenario_id: str, tenant_id: str) -> dict[str, object]:
        ...
```

- [ ] **Step 5: Expose replay endpoints**

```python
@replay_router.get("/api/v1/replay/scenarios")
async def list_replay_scenarios(...) -> dict[str, object]:
    return await service.list_scenarios()


@replay_router.post("/api/v1/incidents/replay/{scenario_id}", status_code=202)
async def launch_replay_scenario(...) -> dict[str, object]:
    return await service.launch_scenario(scenario_id, auth.tenant_id)
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_replay.py tests/test_workflow_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add incidents/replay_catalog.py incidents/replay_samples server/services/replay.py server/routes/replay.py tests/test_replay.py tests/test_workflow_api.py
git commit -m "feat: add sample replay library and api"
```

### Task 5: Build The Multi-Page App Shell And Shared Frontend Assets

**Files:**
- Create: `frontend/queue.html`
- Create: `frontend/incident.html`
- Create: `frontend/inputs.html`
- Create: `frontend/history.html`
- Create: `frontend/replay.html`
- Create: `frontend/training.html`
- Create: `frontend/settings.html`
- Create: `frontend/static/app-shell.css`
- Create: `frontend/static/app-shell.js`
- Create: `frontend/static/client.js`
- Create: `frontend/static/formatters.js`
- Modify: `frontend/dashboard.html`
- Modify: `server/routes/pages.py`
- Test: `tests/test_page_routes.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing page-shell tests**

```python
def test_all_product_pages_render_shell_markup() -> None:
    client = TestClient(app)

    for path in ["/queue", "/inputs", "/history", "/replay", "/training", "/settings"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "app-shell" in response.text
```

- [ ] **Step 2: Run the page tests and verify they fail**

Run: `pytest tests/test_page_routes.py tests/test_app.py -v`
Expected: FAIL because the new HTML files and static shell assets do not exist.

- [ ] **Step 3: Create the shared shell markup and navigation**

```html
<body class="app-shell">
  <div class="shell">
    <aside class="sidebar">
      <a href="/queue">Queue</a>
      <a href="/incident">Incident Console</a>
      <a href="/inputs">Input Channels</a>
      <a href="/history">History</a>
      <a href="/replay">Sample Replay</a>
      <a href="/training">RL Training Lab</a>
      <a href="/settings">Settings</a>
    </aside>
    <main id="pageRoot"></main>
  </div>
  <script type="module" src="/static/app-shell.js"></script>
</body>
```

- [ ] **Step 4: Add shared shell styling and API helpers**

```javascript
export function setActiveNav(pathname) {
  document.querySelectorAll("[data-nav]").forEach((node) => {
    node.classList.toggle("active", node.getAttribute("href") === pathname);
  });
}

export async function apiGet(path) {
  const response = await fetch(path, { headers: { "x-user-id": "demo-user", "x-tenant-id": "tenant-demo" } });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}
```

- [ ] **Step 5: Point `/dashboard` at the new Queue shell for backwards compatibility**

```python
@pages_router.get("/dashboard")
async def dashboard_redirect_shell() -> FileResponse:
    return FileResponse("frontend/queue.html", media_type="text/html")
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_page_routes.py tests/test_app.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/queue.html frontend/incident.html frontend/inputs.html frontend/history.html frontend/replay.html frontend/training.html frontend/settings.html frontend/static/app-shell.css frontend/static/app-shell.js frontend/static/client.js frontend/static/formatters.js frontend/dashboard.html server/routes/pages.py tests/test_page_routes.py tests/test_app.py
git commit -m "feat: add multipage product shell"
```

### Task 6: Implement Queue And Incident Console Pages

**Files:**
- Create: `frontend/static/queue.js`
- Create: `frontend/static/incident.js`
- Modify: `frontend/queue.html`
- Modify: `frontend/incident.html`
- Modify: `frontend/static/client.js`
- Test: `tests/test_workflow_api.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing tests for queue-first and incident-detail rendering**

```python
def test_queue_api_payload_supports_stage_badges(client, auth_headers) -> None:
    response = client.get("/api/v1/incidents/queue", headers=auth_headers())
    assert response.status_code == 200
    assert response.json()["items"] == [] or "current_stage" in response.json()["items"][0]


def test_incident_detail_payload_contains_action_panel(client, auth_headers, replay_incident) -> None:
    response = client.get(
        f"/api/v1/incidents/{replay_incident['nexus_incident_id']}",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert "action_panel" in response.json()
```

- [ ] **Step 2: Run the queue and incident tests and verify they fail**

Run: `pytest tests/test_workflow_api.py tests/test_app.py -v`
Expected: FAIL because the frontend expects queue and incident-console-specific fields not yet populated.

- [ ] **Step 3: Render queue cards from the queue API**

```javascript
import { apiGet } from "/static/client.js";

async function renderQueue() {
  const payload = await apiGet("/api/v1/incidents/queue");
  document.getElementById("queueList").innerHTML = payload.items.map((item) => `
    <a class="queue-card" href="/incident?nexus_incident_id=${item.nexus_incident_id}">
      <div>${item.title}</div>
      <div>${item.severity}</div>
      <div>${item.current_stage}</div>
    </a>
  `).join("");
}
```

- [ ] **Step 4: Render the Incident Console timeline, evidence tabs, agent contributions, and action panel**

```javascript
async function renderIncident() {
  const incidentId = new URLSearchParams(window.location.search).get("nexus_incident_id");
  const payload = await apiGet(`/api/v1/incidents/${incidentId}`);
  renderTimeline(payload.timeline);
  renderEvidenceTabs(payload.evidence);
  renderAgentContributions(payload.agent_contributions);
  renderActionPanel(payload.action_panel);
  renderAuditRail(payload.audit_entries);
}
```

- [ ] **Step 5: Make intake the first visible workflow state in the Incident Console**

```javascript
function renderTimeline(events) {
  return events.map((event) => `
    <article class="timeline-event stage-${event.stage}">
      <div class="timeline-stage">${event.title}</div>
      <div class="timeline-summary">${event.summary}</div>
    </article>
  `).join("");
}
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_workflow_api.py tests/test_app.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/static/queue.js frontend/static/incident.js frontend/queue.html frontend/incident.html frontend/static/client.js tests/test_workflow_api.py tests/test_app.py
git commit -m "feat: add queue and incident console pages"
```

### Task 7: Implement Input Channels, History, And Sample Replay Pages

**Files:**
- Create: `frontend/static/inputs.js`
- Create: `frontend/static/history.js`
- Create: `frontend/static/replay.js`
- Modify: `frontend/inputs.html`
- Modify: `frontend/history.html`
- Modify: `frontend/replay.html`
- Test: `tests/test_input_channels.py`
- Test: `tests/test_replay.py`
- Test: `tests/test_page_routes.py`

- [ ] **Step 1: Write failing tests for input, history, and replay page contracts**

```python
def test_replay_api_lists_curated_scenarios(client, auth_headers) -> None:
    response = client.get("/api/v1/replay/scenarios", headers=auth_headers())
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 5


def test_history_api_is_filterable(client, auth_headers) -> None:
    response = client.get("/api/v1/incidents/history?severity=P0", headers=auth_headers())
    assert response.status_code == 200
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run: `pytest tests/test_input_channels.py tests/test_replay.py tests/test_page_routes.py -v`
Expected: FAIL because the page modules and filters are not implemented yet.

- [ ] **Step 3: Build the Input Channels page with intake cards and a manual incident form**

```javascript
async function submitManualIncident(event) {
  event.preventDefault();
  const payload = {
    affected_service: form.service.value,
    symptoms: form.symptoms.value.split("\n").filter(Boolean),
    severity: form.severity.value,
    reported_by: "demo@example.com",
    team: form.team.value,
  };
  await apiPost("/api/v1/incidents/manual-report", payload);
}
```

- [ ] **Step 4: Build the History page with filterable incident tables and links back to the Incident Console**

```javascript
async function renderHistory() {
  const payload = await apiGet("/api/v1/incidents/history");
  document.getElementById("historyTable").innerHTML = payload.items.map((item) => `
    <tr>
      <td><a href="/incident?nexus_incident_id=${item.nexus_incident_id}">${item.title}</a></td>
      <td>${item.severity}</td>
      <td>${item.status}</td>
    </tr>
  `).join("");
}
```

- [ ] **Step 5: Build the Sample Replay page with launch buttons that create replay incidents**

```javascript
async function launchReplayScenario(scenarioId) {
  const payload = await apiPost(`/api/v1/incidents/replay/${scenarioId}`, {});
  window.location.href = `/incident?nexus_incident_id=${payload.nexus_incident_id}`;
}
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_input_channels.py tests/test_replay.py tests/test_page_routes.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/static/inputs.js frontend/static/history.js frontend/static/replay.js frontend/inputs.html frontend/history.html frontend/replay.html tests/test_input_channels.py tests/test_replay.py tests/test_page_routes.py
git commit -m "feat: add input history and replay pages"
```

### Task 8: Implement RL Training Lab And Settings Pages

**Files:**
- Create: `server/services/training_lab.py`
- Create: `server/routes/training.py`
- Create: `server/routes/settings.py`
- Create: `frontend/static/training.js`
- Create: `frontend/static/settings.js`
- Modify: `frontend/training.html`
- Modify: `frontend/settings.html`
- Modify: `training/reporting.py`
- Test: `tests/test_training_lab.py`
- Test: `tests/test_app.py`
- Test: `tests/test_training.py`

- [ ] **Step 1: Write failing tests for training and settings APIs**

```python
def test_training_summary_api_exposes_reward_and_observation_mapping(client, auth_headers) -> None:
    response = client.get("/api/v1/training/summary", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert "reward_breakdown" in payload
    assert "observation_states" in payload


def test_settings_api_exposes_demo_mode_and_integrations(client, auth_headers) -> None:
    response = client.get("/api/v1/settings", headers=auth_headers())

    assert response.status_code == 200
    assert "integrations" in response.json()
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run: `pytest tests/test_training_lab.py tests/test_app.py tests/test_training.py -v`
Expected: FAIL with missing `/api/v1/training/summary` and `/api/v1/settings`.

- [ ] **Step 3: Add a training lab service that maps the real reward model onto nine observation states**

```python
class TrainingLabService:
    def get_summary(self) -> dict[str, object]:
        metrics = ensure_metrics_payload()
        return {
            "baseline_reward": metrics["summary"]["baseline_reward"],
            "trained_reward": metrics["summary"]["trained_reward"],
            "reward_curve": metrics["reward_curve"],
            "reward_breakdown": ["mttr", "diagnosis", "customer", "coordination", "oversight", "severity_penalty"],
            "observation_states": [
                "incident_received",
                "validated_authenticated",
                "enriched_with_service_context",
                "evidence_retrieved",
                "sentinel_classified",
                "prism_diagnosed",
                "forge_proposed_runbook",
                "guardian_reviewed_safety",
                "executed_verified_learned",
            ],
        }
```

- [ ] **Step 4: Expose training and settings APIs**

```python
@training_router.get("/api/v1/training/summary")
async def training_summary(...) -> dict[str, object]:
    return service.get_summary()


@settings_router.get("/api/v1/settings")
async def settings_summary(request: Request, auth: AuthenticatedContext = Depends(require_auth)) -> dict[str, object]:
    return {
        "app_env": request.app.state.config.app_env,
        "demo_mode": True,
        "integrations": [
            {"name": "Datadog", "status": "demo-ready"},
            {"name": "Prometheus", "status": "demo-ready"},
            {"name": "Replay Library", "status": "ready"},
        ],
    }
```

- [ ] **Step 5: Build the RL Training Lab and Settings pages**

```javascript
async function renderTrainingLab() {
  const payload = await apiGet("/api/v1/training/summary");
  renderRewardCurve(payload.reward_curve);
  renderObservationStates(payload.observation_states);
  renderRewardBreakdown(payload.reward_breakdown);
}

async function renderSettings() {
  const payload = await apiGet("/api/v1/settings");
  renderIntegrationStatus(payload.integrations);
}
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_training_lab.py tests/test_app.py tests/test_training.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/services/training_lab.py server/routes/training.py server/routes/settings.py frontend/static/training.js frontend/static/settings.js frontend/training.html frontend/settings.html training/reporting.py tests/test_training_lab.py tests/test_app.py tests/test_training.py
git commit -m "feat: add rl training lab and settings pages"
```

### Task 9: Update Containerization, Deployment Manifests, Documentation, And Regression Coverage

**Files:**
- Create: `ops/docker/entrypoint.sh`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `ops/kubernetes/deployment.yaml`
- Modify: `ops/kubernetes/configmap.yaml`
- Modify: `README.md`
- Modify: `docs/OPERATIONS.md`
- Modify: `tests/test_deployment.py`
- Modify: `tests/test_app.py`

- [ ] **Step 1: Write failing deployment tests for the multi-page app and seeded demo assets**

```python
from pathlib import Path


def test_multipage_assets_and_entrypoint_exist() -> None:
    assert Path("frontend/queue.html").exists()
    assert Path("frontend/replay.html").exists()
    assert Path("ops/docker/entrypoint.sh").exists()
```

- [ ] **Step 2: Run the deployment tests and verify they fail**

Run: `pytest tests/test_deployment.py tests/test_app.py -v`
Expected: FAIL because the entrypoint and new page assets are not yet wired for containers.

- [ ] **Step 3: Add a container entrypoint that seeds training metrics and replay fixtures before boot**

```sh
#!/bin/sh
set -eu

python -c "from training.reporting import ensure_metrics_payload; ensure_metrics_payload()"
exec uvicorn server.app:app --host 0.0.0.0 --port "${PORT:-7860}"
```

- [ ] **Step 4: Update Docker and deployment manifests for the new pages and demo mode**

```dockerfile
COPY ops/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```yaml
env:
  - name: APP_ENV
    value: product
  - name: PORT
    value: "7860"
```

- [ ] **Step 5: Update operator docs and product README**

```markdown
## Product UI

- `/queue`
- `/inputs`
- `/history`
- `/replay`
- `/training`
- `/settings`

## Demo flow

1. Open Queue
2. Launch replay or submit manual incident
3. Inspect Incident Console
4. Review RL Training Lab
```

- [ ] **Step 6: Run the full regression suite**

Run: `pytest tests/ -v`
Expected: PASS with zero failures

- [ ] **Step 7: Commit**

```bash
git add ops/docker/entrypoint.sh Dockerfile docker-compose.yml ops/kubernetes/deployment.yaml ops/kubernetes/configmap.yaml README.md docs/OPERATIONS.md tests/test_deployment.py tests/test_app.py
git commit -m "feat: ship enterprise workflow ui deployment package"
```

## Self-Review

- Spec coverage:
  - multi-page operator shell: Tasks 1, 5, 6, 7, 8
  - queue-first navigation: Tasks 1 and 6
  - Incident Console with visible intake: Tasks 2 and 6
  - Input Channels as page 3: Tasks 3 and 7
  - sample replay library: Task 4 and Task 7
  - RL Training Lab with 9-state observations and real reward model: Task 8
  - containerization and seeded demo data: Task 9
- Placeholder scan:
  - no placeholder markers remain
  - no deferred-work markers remain
  - no cross-task shortcut references remain
- Type consistency:
  - page routes use `/api/v1/...` consistently
  - workflow stage names match the spec naming
  - replay launches produce real incident IDs consumed by the Incident Console
