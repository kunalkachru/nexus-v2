# Enterprise UI Product Roadmap Implementation Plan

> Historical execution plan. The repo now reflects this plan, and live status is tracked in [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](../../NEXUS_v2_DOC_STATUS_MATRIX.md) and [docs/NEXUS_v2_PRIORITY_BACKLOG.md](../../NEXUS_v2_PRIORITY_BACKLOG.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make NEXUS feel like an enterprise incident response product from the user experience first, then add backend-backed realism behind the same shell.

**Architecture:** Treat the UI as the primary product surface and the backend as a supporting contract. First tighten the app shell, queue, incident console, and supporting pages so the product reads as one coherent enterprise system; then add versioned API seams and data models that can power the same experience with real incident state later.

**Tech Stack:** FastAPI, Pydantic v2, vanilla HTML/CSS/ES modules, file-backed fixtures, pytest, Docker

---

### Task 1: Standardize The Enterprise Shell And Navigation

**Files:**
- Modify: `frontend/dashboard.html`
- Modify: `frontend/queue.html`
- Modify: `frontend/incident.html`
- Modify: `frontend/inputs.html`
- Modify: `frontend/history.html`
- Modify: `frontend/replay.html`
- Modify: `frontend/training.html`
- Modify: `frontend/settings.html`
- Modify: `frontend/static/app-shell.js`
- Modify: `frontend/static/dashboard.css`
- Test: `tests/test_app.py`
- Test: `tests/test_deployment.py`

- [ ] **Step 1: Write failing tests for the shared shell and navigation order**

```python
from fastapi.testclient import TestClient

from server.app import app


def test_enterprise_shell_is_consistent_across_pages() -> None:
    client = TestClient(app)

    pages = [
        client.get("/"),
        client.get("/queue"),
        client.get("/incident"),
        client.get("/inputs"),
        client.get("/history"),
        client.get("/replay"),
        client.get("/training"),
        client.get("/settings"),
    ]

    assert all(response.status_code == 200 for response in pages)
    assert "Queue" in pages[0].text
    assert "Incident Console" in pages[1].text or "Incident" in pages[1].text
    assert "Input Channels" in pages[2].text
    assert "History" in pages[3].text
    assert "Replay" in pages[4].text
    assert "Training" in pages[5].text
    assert "Settings" in pages[6].text
```

- [ ] **Step 2: Run the test to confirm the shell is still inconsistent**

Run: `pytest tests/test_app.py::test_enterprise_shell_is_consistent_across_pages -v`
Expected: FAIL until the queue is the canonical landing page and the shared nav/styling is unified.

- [ ] **Step 3: Implement a single shared app shell and normalize page titles**

```python
# frontend/static/app-shell.js
const THEME_KEY = "nexus.theme";

function setActiveNav() {
  const currentPath = window.location.pathname.replace(/\/$/, "") || "/";
  document.querySelectorAll("[data-shell-nav]").forEach((link) => {
    const href = link.getAttribute("href");
    const targetPath = new URL(href, window.location.origin).pathname.replace(/\/$/, "") || "/";
    const isActive = currentPath === targetPath;
    link.classList.toggle("active", isActive);
    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

window.addEventListener("DOMContentLoaded", () => {
  setActiveNav();
  document.documentElement.dataset.shellReady = "true";
});
```

- [ ] **Step 4: Re-run the shell tests and verify they pass**

Run: `pytest tests/test_app.py::test_enterprise_shell_is_consistent_across_pages -v`
Expected: PASS once all pages share one navigation model and the landing page reads as Queue-first.

- [ ] **Step 5: Commit**

```bash
git add frontend/dashboard.html frontend/queue.html frontend/incident.html frontend/inputs.html frontend/history.html frontend/replay.html frontend/training.html frontend/settings.html frontend/static/app-shell.js frontend/static/dashboard.css tests/test_app.py tests/test_deployment.py
git commit -m "feat: standardize enterprise app shell"
```

### Task 2: Make Queue And Incident Console Feel Like The Core Product

**Files:**
- Modify: `frontend/queue.html`
- Modify: `frontend/incident.html`
- Modify: `frontend/static/queue.js`
- Modify: `frontend/static/incident.js`
- Modify: `frontend/static/dashboard.css`
- Modify: `frontend/static/api.js`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing tests for queue priority and incident narrative**

```python
def test_queue_and_incident_console_read_like_operational_views() -> None:
    client = TestClient(app)

    queue = client.get("/queue")
    incident = client.get("/incident")

    assert queue.status_code == 200
    assert incident.status_code == 200
    assert "SLA at risk" in queue.text
    assert "Current stage" in queue.text
    assert "Workflow Timeline" in incident.text
    assert "SENTINEL" in incident.text
    assert "PRISM" in incident.text
    assert "FORGE" in incident.text
    assert "GUARDIAN" in incident.text
```

- [ ] **Step 2: Run the test to confirm the current pages are not yet strong enough**

Run: `pytest tests/test_app.py::test_queue_and_incident_console_read_like_operational_views -v`
Expected: FAIL until the queue is compact and the incident console has a clear narrative hierarchy.

- [ ] **Step 3: Update the queue to emphasize urgency, stage, and latest agent activity**

```js
// frontend/static/queue.js
import { loadMetrics } from "./api.js";

function renderQueue(data) {
  const snapshot = data.queue_snapshot;
  document.getElementById("queueOpenIncidents").textContent = snapshot.open_incidents;
  document.getElementById("queueSlaAtRisk").textContent = snapshot.sla_at_risk;
  document.getElementById("queuePrimarySource").textContent = snapshot.primary_source;
  document.getElementById("queueCurrentStage").textContent = snapshot.current_stage;
  document.getElementById("queueLatestActivity").textContent = snapshot.latest_agent_activity;
  document.getElementById("queueSlaTimer").textContent = snapshot.sla_timer;
}

window.addEventListener("load", async () => {
  const data = await loadMetrics();
  renderQueue(data);
});
```

- [ ] **Step 4: Update the incident console to present workflow, evidence, and agent contributions as a single story**

```js
// frontend/static/incident.js
import { loadIncident } from "./api.js";

function renderAgentBlock(title, confidence, reasoning, details) {
  return `
    <section class="agent-card">
      <div class="agent-title-row">
        <div class="agent-title">${title}</div>
        <div class="confidence">${Math.round(confidence * 100)}%</div>
      </div>
      <p class="agent-copy">${reasoning}</p>
      <ul class="simple-list">${details.map((item) => `<li>${item}</li>`).join("")}</ul>
    </section>
  `;
}
```

- [ ] **Step 5: Re-run the queue and incident tests**

Run: `pytest tests/test_app.py::test_queue_and_incident_console_read_like_operational_views -v`
Expected: PASS after the queue and incident pages feel like a live operator workflow.

- [ ] **Step 6: Commit**

```bash
git add frontend/queue.html frontend/incident.html frontend/static/queue.js frontend/static/incident.js frontend/static/dashboard.css frontend/static/api.js tests/test_app.py
git commit -m "feat: strengthen queue and incident console"
```

### Task 3: Make Supporting Pages Reinforce The Same Enterprise Narrative

**Files:**
- Modify: `frontend/inputs.html`
- Modify: `frontend/history.html`
- Modify: `frontend/replay.html`
- Modify: `frontend/training.html`
- Modify: `frontend/settings.html`
- Modify: `frontend/static/inputs.js`
- Modify: `frontend/static/history.js`
- Modify: `frontend/static/replay.js`
- Modify: `frontend/static/training.js`
- Modify: `frontend/static/settings.js`
- Modify: `frontend/static/dashboard.css`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing tests for the supporting pages**

```python
def test_supporting_pages_match_the_enterprise_story() -> None:
    client = TestClient(app)

    inputs = client.get("/inputs")
    history = client.get("/history")
    replay = client.get("/replay")
    training = client.get("/training")
    settings = client.get("/settings")

    assert "Input Channels" in inputs.text
    assert "Incident archive" in history.text
    assert "Replay validation" in replay.text
    assert "Learning operations" in training.text
    assert "Operational controls" in settings.text
```

- [ ] **Step 2: Run the test to confirm the supporting pages are still uneven**

Run: `pytest tests/test_app.py::test_supporting_pages_match_the_enterprise_story -v`
Expected: FAIL until every page reinforces the same system instead of feeling like a separate demo.

- [ ] **Step 3: Make Inputs explain the normalized incident envelope**

```js
// frontend/static/inputs.js
const CHANNELS = {
  webhook: {
    label: "Webhook",
    next: "Webhook input lands in the incident queue and opens the same workflow states as every other channel.",
  },
  manual_form: {
    label: "Manual Form",
    next: "Manual input becomes a normalized incident and enters the same queue and console flow.",
  },
};
```

- [ ] **Step 4: Make History, Replay, Training, and Settings feel like evidence of a mature platform**

```js
// frontend/static/history.js
function highlightActiveFilters() {
  document.querySelectorAll("[data-filter]").forEach((node) => {
    node.classList.toggle("is-active", node.value !== "");
  });
}
```

- [ ] **Step 5: Re-run the page coverage tests**

Run: `pytest tests/test_app.py::test_supporting_pages_match_the_enterprise_story -v`
Expected: PASS when the supporting pages clearly reinforce the main product story.

- [ ] **Step 6: Commit**

```bash
git add frontend/inputs.html frontend/history.html frontend/replay.html frontend/training.html frontend/settings.html frontend/static/inputs.js frontend/static/history.js frontend/static/replay.js frontend/static/training.js frontend/static/settings.js frontend/static/dashboard.css tests/test_app.py
git commit -m "feat: align supporting enterprise pages"
```

### Task 4: Apply Shared Visual System, Motion, And States

**Files:**
- Modify: `frontend/static/dashboard.css`
- Modify: `frontend/static/app-shell.js`
- Modify: `frontend/static/queue.js`
- Modify: `frontend/static/incident.js`
- Modify: `frontend/static/inputs.js`
- Modify: `frontend/static/history.js`
- Modify: `frontend/static/replay.js`
- Modify: `frontend/static/training.js`
- Modify: `frontend/static/settings.js`
- Test: `tests/test_app.py`
- Test: `tests/test_deployment.py`

- [ ] **Step 1: Write failing tests for the visual and loading states**

```python
def test_static_assets_and_page_chrome_are_served() -> None:
    client = TestClient(app)

    assert client.get("/static/dashboard.css").status_code == 200
    assert client.get("/static/app-shell.js").status_code == 200
    assert client.get("/static/queue.js").status_code == 200
    assert client.get("/static/incident.js").status_code == 200
```

- [ ] **Step 2: Run the asset test to confirm the shell still needs polish**

Run: `pytest tests/test_app.py::test_static_assets_and_page_chrome_are_served -v`
Expected: FAIL if any shared assets or page scripts are missing.

- [ ] **Step 3: Introduce a single visual language for severity, safety, and status**

```css
/* frontend/static/dashboard.css */
.badge[data-tone="warning"] {
  background: rgba(245, 158, 11, 0.14);
  border-color: rgba(245, 158, 11, 0.24);
}

.badge[data-tone="danger"] {
  background: rgba(239, 68, 68, 0.14);
  border-color: rgba(239, 68, 68, 0.24);
}

.badge[data-tone="success"] {
  background: rgba(34, 197, 94, 0.14);
  border-color: rgba(34, 197, 94, 0.24);
}
```

- [ ] **Step 4: Add restrained motion only where it clarifies state changes**

```css
@media (prefers-reduced-motion: no-preference) {
  .agent-card.active {
    animation: pulse 1.8s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-1px); }
  }
}
```

- [ ] **Step 5: Re-run the asset and deployment tests**

Run: `pytest tests/test_app.py::test_static_assets_and_page_chrome_are_served tests/test_deployment.py -v`
Expected: PASS once the shared visual system is consistently served.

- [ ] **Step 6: Commit**

```bash
git add frontend/static/dashboard.css frontend/static/app-shell.js frontend/static/queue.js frontend/static/incident.js frontend/static/inputs.js frontend/static/history.js frontend/static/replay.js frontend/static/training.js frontend/static/settings.js tests/test_app.py tests/test_deployment.py
git commit -m "feat: unify enterprise visual system"
```

### Task 5: Add Backend-Ready API Seams For Later Realism

**Files:**
- Modify: `server/app.py`
- Modify: `server/models.py`
- Modify: `server/services/incidents.py`
- Modify: `server/integrations/models.py`
- Modify: `server/repositories.py`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_persistence.py`

- [ ] **Step 1: Write failing tests for versioned incident and queue API shapes**

```python
from fastapi.testclient import TestClient

from server.app import app


def test_versioned_queue_contract_is_available(auth_headers) -> None:
    client = TestClient(app)
    response = client.get("/api/v1/incidents/queue", headers=auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert isinstance(payload["items"], list)
```

- [ ] **Step 2: Run the contract test to confirm the current backend shape is not yet sufficient**

Run: `pytest tests/test_api_contract.py::test_versioned_queue_contract_is_available -v`
Expected: FAIL until the UI can rely on a stable versioned API.

- [ ] **Step 3: Add a thin versioned contract layer without changing the UI shell**

```python
from server.app import app


@app.get("/api/v1/incidents/queue")
async def queue_v1() -> dict[str, list[dict[str, object]]]:
    return {"items": []}
```

- [ ] **Step 4: Re-run the contract and persistence tests**

Run: `pytest tests/test_api_contract.py tests/test_persistence.py -v`
Expected: PASS once the UI support contracts are stable enough for real data wiring later.

- [ ] **Step 5: Commit**

```bash
git add server/app.py server/models.py server/services/incidents.py server/integrations/models.py server/repositories.py tests/test_api_contract.py tests/test_persistence.py
git commit -m "feat: add backend-ready api seams"
```

### Task 6: Verify The UI-First Product End To End

**Files:**
- Verify only

- [ ] **Step 1: Run the full app test suite**

Run: `pytest tests/test_app.py tests/test_deployment.py tests/test_api_contract.py -v`
Expected: PASS.

- [ ] **Step 2: Start the app locally and inspect the UI**

Run: `docker compose up --build`
Expected: the app serves on `http://127.0.0.1:7860/`.

- [ ] **Step 3: Verify the core user journey**

Open:
- `http://127.0.0.1:7860/`
- `http://127.0.0.1:7860/queue`
- `http://127.0.0.1:7860/incident?nexus_incident_id=INC001`
- `http://127.0.0.1:7860/inputs`
- `http://127.0.0.1:7860/history`
- `http://127.0.0.1:7860/replay`
- `http://127.0.0.1:7860/training`
- `http://127.0.0.1:7860/settings`

- [ ] **Step 4: Review the diff for product feel, not just correctness**

Check:
- Queue reads as the landing surface.
- Incident Console reads as the core story.
- Supporting pages reinforce the same enterprise narrative.
- Backend readiness does not distract from the UI-first objective.
