# Day 1 Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Day 1 FastAPI scaffold with a `/health` endpoint, typed Pydantic models, an 8-incident catalogue, empty agent stubs, and pytest coverage that drives the implementation.

**Architecture:** Keep the scaffold minimal and package-oriented. `server/` contains the web app, data models, and agent stubs; `incidents/` contains seed incident definitions and catalogue loading helpers; `tests/` exercises the HTTP surface, typed contracts, and catalogue shape without pulling in any future RL or database concerns.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest

---

### Task 1: Package Skeleton And Health Endpoint

**Files:**
- Create: `server/__init__.py`
- Create: `server/app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from server.app import app


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py::test_health_returns_ok -v`
Expected: FAIL because `server.app` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import FastAPI

app = FastAPI(title="NEXUS v3")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py::test_health_returns_ok -v`
Expected: PASS

### Task 2: Pydantic Models And Incident Catalogue

**Files:**
- Create: `server/models.py`
- Create: `incidents/__init__.py`
- Create: `incidents/catalogue.py`
- Test: `tests/test_models.py`
- Test: `tests/test_catalogue.py`

- [ ] **Step 1: Write the failing tests**

```python
from incidents.catalogue import load_incident_types
from server.models import IncidentDefinition, SystemContext


def test_system_context_is_typed() -> None:
    context = SystemContext(
        service="payment-svc",
        language="Python/FastAPI",
        infra="AWS ECS Fargate",
        dependencies=["postgres-payments", "stripe-api"],
    )

    assert context.service == "payment-svc"
    assert context.dependencies == ["postgres-payments", "stripe-api"]


def test_load_incident_types_returns_eight_incidents() -> None:
    incidents = load_incident_types()

    assert len(incidents) == 8
    assert all(isinstance(incident, IncidentDefinition) for incident in incidents)
    assert incidents[0].id == "INC001"
    assert incidents[-1].id == "INC008"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py tests/test_catalogue.py -v`
Expected: FAIL because the models and catalogue module do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class SystemContext(BaseModel):
    service: str
    language: str
    infra: str
    dependencies: list[str]


class IncidentDefinition(BaseModel):
    id: str
    name: str
    severity: str
    difficulty: str
    symptoms: list[str]
    system_context: SystemContext
    root_cause: str
    fix: str
```

```python
def load_incident_types() -> list[IncidentDefinition]:
    return [IncidentDefinition(...), ...]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py tests/test_catalogue.py -v`
Expected: PASS

### Task 3: Empty Agent Stubs

**Files:**
- Create: `server/agents/__init__.py`
- Create: `server/agents/base.py`
- Create: `server/agents/sentinel.py`
- Create: `server/agents/prism.py`
- Create: `server/agents/forge.py`
- Create: `server/agents/guardian.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Write the failing test**

```python
from server.agents import ForgeAgent, GuardianAgent, PrismAgent, SentinelAgent


def test_agent_stubs_expose_expected_names() -> None:
    assert SentinelAgent.name == "sentinel"
    assert PrismAgent.name == "prism"
    assert ForgeAgent.name == "forge"
    assert GuardianAgent.name == "guardian"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agents.py::test_agent_stubs_expose_expected_names -v`
Expected: FAIL because the agent modules do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class BaseAgent:
    name: str = "base"


class SentinelAgent(BaseAgent):
    name = "sentinel"
```

Repeat the same pattern for `PrismAgent`, `ForgeAgent`, and `GuardianAgent`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agents.py::test_agent_stubs_expose_expected_names -v`
Expected: PASS

### Task 4: Pytest Wiring And Full Verification

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/test_app.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_catalogue.py`
- Modify: `tests/test_agents.py`

- [ ] **Step 1: Add any shared fixtures only if the tests need them**

```python
# Keep this file minimal for Day 1; add fixtures only when duplication appears.
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest tests/ -v`
Expected: PASS with coverage over the health endpoint, models, catalogue, and stubs.

- [ ] **Step 3: Review the diff before calling the task complete**

Run: `git diff -- server incidents tests docs/superpowers/plans/2026-05-27-day-1-scaffold.md`
Expected: Only the planned scaffold files appear.
