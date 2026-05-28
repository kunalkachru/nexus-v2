# Sentinel Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `SentinelAgent.classify()` so it classifies all 8 incident types, returns normalized severity and confidence scores, and fails safely on invalid input.

**Architecture:** Keep Day 2 deterministic and local. `SentinelAgent` will score incoming symptoms against the 8-entry incident catalogue using normalized keyword overlap, then return a typed classification model with a normalized `P1`/`P2`/`P3` severity and bounded confidence. Shared output types live in `server/models.py`; tests drive the public contract from `tests/test_agents.py`.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest

---

### Task 1: Define The SENTINEL Contract In Tests

**Files:**
- Modify: `tests/test_agents.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_sentinel_classifies_catalogue_incidents() -> None:
    ...


def test_sentinel_accuracy_is_at_least_ninety_percent() -> None:
    ...


def test_sentinel_rejects_empty_symptoms() -> None:
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agents.py -v`
Expected: FAIL because `SentinelAgent.classify()` and the typed classification result do not exist yet.

- [ ] **Step 3: Keep expectations minimal and public**

```python
assert result.incident_id == incident.id
assert result.severity in {"P1", "P2", "P3"}
assert 0.0 <= result.confidence <= 1.0
```

- [ ] **Step 4: Re-run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: Still FAIL, but only because production code is missing.

### Task 2: Add Typed Classification Models

**Files:**
- Modify: `server/models.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Add the failing assertion coverage first**

```python
assert result.reasoning
```

- [ ] **Step 2: Add the minimal output type**

```python
class SentinelClassification(BaseModel):
    incident_id: str
    incident_name: str
    severity: Literal["P1", "P2", "P3"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
```

- [ ] **Step 3: Run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: FAIL because `SentinelAgent.classify()` still does not exist.

### Task 3: Implement Deterministic Classification

**Files:**
- Modify: `server/agents/base.py`
- Modify: `server/agents/sentinel.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Implement the smallest public API that satisfies the tests**

```python
class SentinelAgent(BaseAgent):
    def classify(
        self,
        raw_symptoms: list[str],
        system_context: SystemContext,
    ) -> SentinelClassification:
        ...
```

- [ ] **Step 2: Score against all 8 incidents**

```python
score = keyword_overlap(raw_symptoms, incident.symptoms, system_context, incident.system_context)
```

- [ ] **Step 3: Normalize severity into the Day 2 contract**

```python
mapping = {"P0": "P1", "P1": "P2", "P2": "P3"}
```

- [ ] **Step 4: Handle invalid input explicitly**

```python
if not raw_symptoms:
    raise ValueError("raw_symptoms must not be empty")
```

- [ ] **Step 5: Run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: PASS

### Task 4: Verify The Day 2 Slice

**Files:**
- Modify: `server/agents/sentinel.py`
- Modify: `server/models.py`
- Modify: `tests/test_agents.py`

- [ ] **Step 1: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 2: Review the diff**

Run: `git diff -- server tests docs/superpowers/plans/2026-05-28-sentinel-classification.md`
Expected: Only Day 2 SENTINEL files changed.
