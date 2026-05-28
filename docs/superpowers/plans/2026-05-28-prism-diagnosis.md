# PRISM Diagnosis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `PrismAgent.diagnose()` so it returns typed root-cause diagnoses with confidence and evidence, and meets the Day 3 75% accuracy target.

**Architecture:** Keep Day 3 deterministic and catalogue-backed like Day 2. `PrismAgent` will use the `SentinelClassification` incident id as its primary lookup key, then score optional signals against the incident root cause and symptoms to produce a typed diagnosis with evidence and queried sources. Shared output types live in `server/models.py`; tests drive the public contract from `tests/test_agents.py`.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest

---

### Task 1: Define The PRISM Contract In Tests

**Files:**
- Modify: `tests/test_agents.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_prism_diagnoses_catalogue_root_causes() -> None:
    ...


def test_prism_accuracy_is_at_least_seventy_five_percent() -> None:
    ...


def test_prism_rejects_unknown_incident_id() -> None:
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agents.py -v`
Expected: FAIL because `PrismAgent.diagnose()` and the typed diagnosis result do not exist yet.

- [ ] **Step 3: Keep expectations on the public API**

```python
assert result.root_cause == incident.root_cause
assert 0.0 <= result.confidence <= 1.0
assert result.evidence
assert result.queried_sources
```

- [ ] **Step 4: Re-run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: Still FAIL, but only because production code is missing.

### Task 2: Add Typed Diagnosis Models

**Files:**
- Modify: `server/models.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Add the minimal diagnosis result type**

```python
class PrismDiagnosis(BaseModel):
    incident_id: str
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    queried_sources: list[str] = Field(default_factory=list)
    reasoning: str
```

- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: FAIL because `PrismAgent.diagnose()` still does not exist.

### Task 3: Implement Deterministic Diagnosis

**Files:**
- Modify: `server/agents/prism.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Implement the public API**

```python
class PrismAgent(BaseAgent):
    def diagnose(
        self,
        sentinel_output: SentinelClassification,
        signals: list[str] | None = None,
    ) -> PrismDiagnosis:
        ...
```

- [ ] **Step 2: Resolve the incident from the catalogue**

```python
incident = self._incident_by_id[sentinel_output.incident_id]
```

- [ ] **Step 3: Build multi-step evidence from signals**

```python
evidence = self._select_evidence(signals, incident)
queried_sources = self._infer_sources(signals)
```

- [ ] **Step 4: Handle invalid input explicitly**

```python
if sentinel_output.incident_id not in self._incident_by_id:
    raise ValueError("unknown incident_id: ...")
```

- [ ] **Step 5: Run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: PASS

### Task 4: Verify The Day 3 Slice

**Files:**
- Modify: `server/agents/prism.py`
- Modify: `server/models.py`
- Modify: `tests/test_agents.py`

- [ ] **Step 1: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 2: Review the diff**

Run: `git diff -- server tests docs/superpowers/plans/2026-05-28-prism-diagnosis.md`
Expected: Only Day 3 PRISM files changed.
