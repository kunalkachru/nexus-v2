# NEXUS Enterprise Grade Phase 2 Implementation Plan

> Target-state Phase 2 implementation plan. Current implementation alignment and remaining gaps are tracked in [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](../../NEXUS_v2_DOC_STATUS_MATRIX.md) and [docs/NEXUS_v2_PRIORITY_BACKLOG.md](../../NEXUS_v2_PRIORITY_BACKLOG.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current deterministic demo into an enterprise-grade Phase 2 product with real alert ingestion, evidence correlation, runbook retrieval, policy enforcement, persistence, authenticated APIs, and a maintainable operator dashboard.

**Architecture:** Keep the four-agent model and deterministic orchestrator boundary, but replace static payload assembly with an async service layer. Introduce typed ingestion models, persistence, integration adapters, execution-policy services, and a real incident lifecycle API so the UI and agents operate on stored incident state instead of hardcoded demo envelopes.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy or aiosqlite/asyncpg, PostgreSQL, Redis, pytest, OpenAI SDK, Docker, Hugging Face Spaces for demo mode, Kubernetes-compatible runtime for product mode.

---

### Task 1: Establish Enterprise Data Contracts And Persistence

**Files:**
- Create: `server/config.py`
- Create: `server/db.py`
- Create: `server/repositories.py`
- Create: `server/integrations/models.py`
- Modify: `server/models.py`
- Modify: `server/app.py`
- Test: `tests/test_persistence.py`
- Test: `tests/test_api_contract.py`

- [ ] **Step 1: Write the failing persistence and contract tests**

```python
from server.integrations.models import IncomingIncidentWebhook


def test_incoming_webhook_model_normalizes_provider_payload() -> None:
    payload = IncomingIncidentWebhook.model_validate(
        {
            "incident_id": "inc_xyz",
            "title": "Payment API timeout",
            "severity": "P1",
            "detected_at": "2026-05-25T14:32:00Z",
            "monitoring_source": "datadog",
            "metrics": {"service": "payment-svc", "error_rate": 0.45},
        }
    )

    assert payload.monitoring_source == "datadog"
    assert payload.metrics["service"] == "payment-svc"


async def test_incident_repository_persists_and_reads_status(async_session) -> None:
    incident = await async_session.incidents.create_incident(
        external_id="inc_xyz",
        title="Payment API timeout",
        severity="P1",
    )

    loaded = await async_session.incidents.get_incident(incident.nexus_incident_id)

    assert loaded.status == "investigating"
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pytest tests/test_persistence.py tests/test_api_contract.py -v`
Expected: FAIL with import errors for `server.integrations.models`, `server.db`, or missing repository/session fixtures.

- [ ] **Step 3: Implement the configuration, database, and repository layer**

```python
from pydantic import BaseModel, Field


class IncomingIncidentWebhook(BaseModel):
    incident_id: str
    title: str
    severity: str
    detected_at: str
    monitoring_source: str
    metrics: dict[str, object] = Field(default_factory=dict)


class IncidentRecord(BaseModel):
    nexus_incident_id: str
    external_id: str
    title: str
    severity: str
    status: str
```

- [ ] **Step 4: Add a database session factory and startup wiring**

```python
from collections.abc import AsyncIterator


async def get_db() -> AsyncIterator[DatabaseSession]:
    session = DatabaseSession(...)
    try:
        yield session
    finally:
        await session.close()
```

- [ ] **Step 5: Run the targeted tests again**

Run: `pytest tests/test_persistence.py tests/test_api_contract.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/config.py server/db.py server/repositories.py server/integrations/models.py server/models.py server/app.py tests/test_persistence.py tests/test_api_contract.py
git commit -m "feat: add incident persistence foundation"
```

### Task 2: Implement Real Incident Ingestion And Status APIs

**Files:**
- Create: `server/integrations/alerts.py`
- Create: `server/integrations/deployments.py`
- Create: `server/services/incidents.py`
- Modify: `server/app.py`
- Modify: `server/models.py`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_integrations.py`

- [ ] **Step 1: Write the failing webhook and status endpoint tests**

```python
def test_webhook_creates_nexus_incident(client) -> None:
    response = client.post(
        "/webhooks/incident",
        json={
            "incident_id": "inc_xyz",
            "title": "Payment API timeout",
            "severity": "P1",
            "detected_at": "2026-05-25T14:32:00Z",
            "monitoring_source": "datadog",
            "metrics": {"service": "payment-svc", "error_rate": 0.45},
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "investigating"


def test_incident_status_returns_persisted_lifecycle(client, seeded_incident) -> None:
    response = client.get(f"/incidents/{seeded_incident.nexus_incident_id}")

    assert response.status_code == 200
    assert response.json()["nexus_incident_id"] == seeded_incident.nexus_incident_id
```

- [ ] **Step 2: Run the endpoint tests to verify they fail**

Run: `pytest tests/test_api_contract.py::test_webhook_creates_nexus_incident tests/test_api_contract.py::test_incident_status_returns_persisted_lifecycle -v`
Expected: FAIL with `404 Not Found` for `/webhooks/incident` or `/incidents/{id}`.

- [ ] **Step 3: Add provider-normalization services for Prometheus and Datadog**

```python
class AlertNormalizer:
    def normalize(self, payload: IncomingIncidentWebhook) -> NormalizedAlertEnvelope:
        return NormalizedAlertEnvelope(
            source=payload.monitoring_source,
            external_id=payload.incident_id,
            title=payload.title,
            severity=payload.severity,
            service=str(payload.metrics.get("service", "")),
            observed_values=payload.metrics,
        )
```

- [ ] **Step 4: Expose the Phase 2 API contract in FastAPI**

```python
@app.post("/webhooks/incident", status_code=202)
async def receive_incident_webhook(
    payload: IncomingIncidentWebhook,
    service: IncidentService = Depends(get_incident_service),
) -> dict[str, object]:
    return await service.create_incident_from_webhook(payload)


@app.get("/incidents/{nexus_incident_id}")
async def get_incident_status(
    nexus_incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> dict[str, object]:
    return await service.get_incident_status(nexus_incident_id)
```

- [ ] **Step 5: Add deployment metadata enrichment**

```python
class DeploymentLookupService:
    async def get_recent_deployments(self, service_name: str) -> list[dict[str, object]]:
        return []
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_api_contract.py tests/test_integrations.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/integrations/alerts.py server/integrations/deployments.py server/services/incidents.py server/app.py server/models.py tests/test_api_contract.py tests/test_integrations.py
git commit -m "feat: add incident webhook and status apis"
```

### Task 3: Replace Static Agent Inputs With Real Evidence Services

**Files:**
- Create: `server/services/observability.py`
- Create: `server/memory_graph.py`
- Create: `server/sandbox.py`
- Modify: `server/agents/sentinel.py`
- Modify: `server/agents/prism.py`
- Modify: `server/agents/forge.py`
- Modify: `server/agents/guardian.py`
- Modify: `server/orchestrator.py`
- Modify: `server/models.py`
- Test: `tests/test_agents.py`
- Test: `tests/test_orchestrator.py`
- Test: `tests/test_observability.py`

- [ ] **Step 1: Write the failing evidence-service tests**

```python
def test_prism_uses_observability_service_for_logs_and_metrics(fake_observability) -> None:
    prism = PrismAgent(observability=fake_observability)

    result = prism.diagnose(
        sentinel_output=sentinel_output_fixture(),
        signals=None,
    )

    assert "logs" in result.queried_sources
    assert result.evidence


def test_forge_uses_memory_graph_before_llm_call(fake_memory_graph, fake_forge_client) -> None:
    forge = ForgeAgent(client=fake_forge_client, memory_graph=fake_memory_graph)

    forge.generate_runbook(prism_output=diagnosis_fixture(), system_context=system_context_fixture())

    assert fake_memory_graph.queries == ["Leaked SQLAlchemy sessions after a checkout retry patch exhausted the primary Postgres pool"]
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `pytest tests/test_agents.py::test_prism_uses_observability_service_for_logs_and_metrics tests/test_agents.py::test_forge_uses_memory_graph_before_llm_call tests/test_orchestrator.py -v`
Expected: FAIL with constructor signature mismatches or missing modules `server.services.observability`, `server.memory_graph`, `server.sandbox`.

- [ ] **Step 3: Add observability, memory-graph, and sandbox interfaces**

```python
class ObservabilityService:
    async def fetch_incident_context(self, envelope: NormalizedAlertEnvelope) -> IncidentContext:
        ...


class IncidentMemoryGraph:
    async def find_similar(self, root_cause: str, top_k: int = 3) -> list[HistoricalRunbook]:
        ...


class SandboxExecutor:
    async def validate(self, runbook: RunbookScript) -> SandboxValidationResult:
        ...
```

- [ ] **Step 4: Refactor the agents to consume services instead of static payload maps**

```python
class PrismAgent(BaseAgent):
    def __init__(self, observability: ObservabilityService) -> None:
        self._observability = observability


class ForgeAgent(BaseAgent):
    def __init__(self, client: ForgeClient, memory_graph: IncidentMemoryGraph) -> None:
        self._client = client
        self._memory_graph = memory_graph
```

- [ ] **Step 5: Update the orchestrator to fetch context, persist state, and validate execution**

```python
context = await self.observability.fetch_incident_context(alert_envelope)
sentinel_output = await self.sentinel.classify(context.raw_symptoms, context.system_context)
prism_output = await self.prism.diagnose(sentinel_output=sentinel_output, signals=context.signals)
forge_output = await self.forge.generate_runbook(prism_output=prism_output, system_context=context.system_context)
guardian_output = await self.guardian.review(...)
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_agents.py tests/test_orchestrator.py tests/test_observability.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/services/observability.py server/memory_graph.py server/sandbox.py server/agents/sentinel.py server/agents/prism.py server/agents/forge.py server/agents/guardian.py server/orchestrator.py server/models.py tests/test_agents.py tests/test_orchestrator.py tests/test_observability.py
git commit -m "feat: connect agents to observability and memory services"
```

### Task 4: Replace Demo-Style Training With Verifiable RL Infrastructure

**Files:**
- Create: `training/trajectory.py`
- Create: `training/evaluation.py`
- Modify: `training/policy.py`
- Modify: `training/grpo_loop.py`
- Modify: `training/runner.py`
- Modify: `training/reporting.py`
- Test: `tests/test_training.py`
- Test: `tests/test_grader.py`

- [ ] **Step 1: Write the failing RL-behavior tests**

```python
def test_training_records_agent_trajectories_with_log_probs() -> None:
    summary = run_training(num_episodes=3, seed=7)

    assert summary.episode_records[0].steps[0].log_prob < 0.0
    assert summary.episode_records[0].steps[0].agent_name == "sentinel"


def test_training_updates_policy_parameters_after_positive_advantage() -> None:
    policies = load_agent_policies()
    baseline = policies["sentinel"].weight

    run_training(num_episodes=5, seed=7, policies=policies)

    assert policies["sentinel"].weight != baseline
```

- [ ] **Step 2: Run the training tests to verify the current simplifications fail the stronger assertions**

Run: `pytest tests/test_training.py -v`
Expected: FAIL on new trajectory structure, richer policy outputs, or unsupported policy fields.

- [ ] **Step 3: Refactor policy and trajectory objects to carry meaningful training state**

```python
@dataclass
class TrainingStepRecord:
    agent_name: str
    action: str
    log_prob: float
    reward_contribution: float
    observation_digest: str
```

- [ ] **Step 4: Upgrade the trainer to extract trajectories from real episode steps**

```python
trajectory = extract_trajectory(episode)
advantages = compute_group_advantages(trajectory, episode.reward.composite)
for step in trajectory:
    self.optimizers[step.agent_name].step(self.policies[step.agent_name], advantages[step.agent_name])
```

- [ ] **Step 5: Add evaluation output for enterprise reporting**

```python
def evaluate_training(summary: TrainingSummary) -> dict[str, object]:
    return {
        "reward_curve_final": summary.reward_curve[-1],
        "policy_drift": {name: policy.weight for name, policy in policies.items()},
    }
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_training.py tests/test_grader.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add training/trajectory.py training/evaluation.py training/policy.py training/grpo_loop.py training/runner.py training/reporting.py tests/test_training.py tests/test_grader.py
git commit -m "feat: strengthen rl training infrastructure"
```

### Task 5: Add Enterprise Controls, Auth, And Multi-Tenant APIs

**Files:**
- Create: `server/auth.py`
- Create: `server/rate_limit.py`
- Create: `server/audit.py`
- Create: `server/services/tenancy.py`
- Modify: `server/app.py`
- Modify: `server/repositories.py`
- Test: `tests/test_security.py`
- Test: `tests/test_api_contract.py`

- [ ] **Step 1: Write the failing security and tenancy tests**

```python
def test_incident_status_requires_authenticated_user(client) -> None:
    response = client.get("/incidents/nexus_abc")
    assert response.status_code == 401


def test_tenant_cannot_read_other_tenant_incident(client, auth_headers, seeded_incident) -> None:
    response = client.get(
        f"/incidents/{seeded_incident.nexus_incident_id}",
        headers=auth_headers(tenant_id="tenant-b"),
    )

    assert response.status_code == 404
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pytest tests/test_security.py tests/test_api_contract.py -v`
Expected: FAIL because the current app has no auth dependency, tenant scoping, or rate limiting.

- [ ] **Step 3: Add auth and tenant dependencies**

```python
class AuthenticatedContext(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str]


async def require_auth(...) -> AuthenticatedContext:
    ...
```

- [ ] **Step 4: Add audit logging and rate limiting**

```python
async def write_audit_log(event_type: str, tenant_id: str, payload: dict[str, object]) -> None:
    ...
```

- [ ] **Step 5: Apply tenant scoping to incident reads and writes**

```python
incident = await repository.get_incident_for_tenant(nexus_incident_id, auth.tenant_id)
if incident is None:
    raise HTTPException(status_code=404)
```

- [ ] **Step 6: Run the targeted tests again**

Run: `pytest tests/test_security.py tests/test_api_contract.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add server/auth.py server/rate_limit.py server/audit.py server/services/tenancy.py server/app.py server/repositories.py tests/test_security.py tests/test_api_contract.py
git commit -m "feat: add auth tenancy and audit controls"
```

### Task 6: Refactor The Dashboard Into A Maintainable Operator UI

**Files:**
- Create: `frontend/static/dashboard.js`
- Create: `frontend/static/dashboard.css`
- Create: `frontend/static/api.js`
- Modify: `frontend/dashboard.html`
- Test: `tests/test_app.py`
- Test: `tests/test_deployment.py`

- [ ] **Step 1: Write the failing UI-contract tests**

```python
def test_dashboard_serves_static_assets() -> None:
    root = client.get("/dashboard")
    js = client.get("/static/dashboard.js")
    css = client.get("/static/dashboard.css")

    assert root.status_code == 200
    assert js.status_code == 200
    assert css.status_code == 200
```

- [ ] **Step 2: Run the UI tests to verify they fail**

Run: `pytest tests/test_app.py::test_dashboard_serves_static_assets tests/test_deployment.py -v`
Expected: FAIL because the JavaScript and CSS assets do not exist yet.

- [ ] **Step 3: Move the inline dashboard logic into dedicated assets**

```javascript
export async function loadIncident(incidentId) {
  const response = await fetch(`/incidents/${incidentId}`);
  return response.json();
}
```

- [ ] **Step 4: Keep the HTML shell thin and API-driven**

```html
<link rel="stylesheet" href="/static/dashboard.css">
<script type="module" src="/static/dashboard.js"></script>
```

- [ ] **Step 5: Run the targeted tests again**

Run: `pytest tests/test_app.py tests/test_deployment.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/dashboard.html frontend/static/dashboard.js frontend/static/dashboard.css frontend/static/api.js tests/test_app.py tests/test_deployment.py
git commit -m "feat: split dashboard into maintainable assets"
```

### Task 7: Ship Product-Grade Deployment, Observability, And Operations

**Files:**
- Create: `docker-compose.yml`
- Create: `ops/kubernetes/deployment.yaml`
- Create: `ops/kubernetes/configmap.yaml`
- Create: `ops/runbooks/README.md`
- Create: `docs/OPERATIONS.md`
- Modify: `Dockerfile`
- Modify: `README.md`
- Test: `tests/test_deployment.py`

- [ ] **Step 1: Write the failing deployment tests**

```python
from pathlib import Path


def test_product_deployment_manifests_exist() -> None:
    assert Path("ops/kubernetes/deployment.yaml").exists()
    assert Path("docs/OPERATIONS.md").exists()
```

- [ ] **Step 2: Run the deployment tests to verify they fail**

Run: `pytest tests/test_deployment.py -v`
Expected: FAIL because the product deployment manifests and operations docs do not exist yet.

- [ ] **Step 3: Add dual-mode deployment support for demo and product**

```dockerfile
ARG APP_ENV=demo
ENV APP_ENV=${APP_ENV}
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

- [ ] **Step 4: Add product operations documentation**

```markdown
# Operations

- Required secrets
- Database migrations
- Redis and rate limiting
- Auth provider configuration
- Incident replay and rollback procedures
```

- [ ] **Step 5: Run the targeted tests again**

Run: `pytest tests/test_deployment.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml ops/kubernetes/deployment.yaml ops/kubernetes/configmap.yaml ops/runbooks/README.md docs/OPERATIONS.md Dockerfile README.md tests/test_deployment.py
git commit -m "feat: add enterprise deployment artifacts"
```

### Task 8: Full Regression Verification

**Files:**
- Modify: `tests/conftest.py`
- Test: `tests/test_agents.py`
- Test: `tests/test_app.py`
- Test: `tests/test_training.py`
- Test: `tests/test_deployment.py`

- [ ] **Step 1: Run the focused suites for each subsystem**

Run: `pytest tests/test_agents.py tests/test_orchestrator.py tests/test_training.py -v`
Expected: PASS

- [ ] **Step 2: Run the API, persistence, and security suites**

Run: `pytest tests/test_api_contract.py tests/test_persistence.py tests/test_security.py tests/test_integrations.py -v`
Expected: PASS

- [ ] **Step 3: Run the full regression suite**

Run: `pytest tests/ -v`
Expected: PASS with zero failures

- [ ] **Step 4: Commit the final verification pass**

```bash
git add tests/conftest.py
git commit -m "test: finalize enterprise grade regression coverage"
```
