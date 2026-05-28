# FORGE Runbook Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `ForgeAgent.generate_runbook()` so it builds Codex-style prompts, calls an injectable LLM client, validates generated scripts, and returns typed runbook metadata with cost tracking.

**Architecture:** Keep Day 4 deterministic and budget-safe in tests. `ForgeAgent` will accept an injected client protocol, build a structured prompt from `PrismDiagnosis` and `SystemContext`, parse a JSON response into a typed runbook model, validate script syntax locally, and surface model/cost metadata for review and fallback. Tests will use a fake client to avoid real API calls while still exercising the integration contract.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest

---

### Task 1: Define The FORGE Contract In Tests

**Files:**
- Modify: `tests/test_agents.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_forge_generates_valid_runbooks_for_catalogue_incidents() -> None:
    ...


def test_forge_uses_fallback_model_from_env() -> None:
    ...


def test_forge_rejects_invalid_generated_script() -> None:
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agents.py -v`
Expected: FAIL because `ForgeAgent.generate_runbook()` and the typed runbook output do not exist yet.

- [ ] **Step 3: Keep expectations on the public API**

```python
assert result.runbook.code
assert result.syntax_valid is True
assert result.estimated_cost_usd >= 0.0
```

- [ ] **Step 4: Re-run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: Still FAIL, but only because production code is missing.

### Task 2: Add Typed Runbook Models

**Files:**
- Modify: `server/models.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Add the minimal output types**

```python
class RunbookScript(BaseModel):
    language: Literal["bash", "python", "kubectl"]
    code: str
    summary: str


class ForgeRunbookResult(BaseModel):
    incident_id: str
    runbook: RunbookScript
    syntax_valid: bool
    model_name: str
    estimated_cost_usd: float = Field(ge=0.0)
    reasoning: str
```

- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: FAIL because `ForgeAgent.generate_runbook()` still does not exist.

### Task 3: Implement Deterministic Client-Driven Generation

**Files:**
- Modify: `server/agents/forge.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Implement the public API**

```python
class ForgeAgent(BaseAgent):
    def generate_runbook(
        self,
        prism_output: PrismDiagnosis,
        system_context: SystemContext,
    ) -> ForgeRunbookResult:
        ...
```

- [ ] **Step 2: Build a structured prompt and choose a model**

```python
model_name = os.environ.get("LLM_MODEL", "gpt-4o")
prompt = self._build_prompt(prism_output, system_context)
```

- [ ] **Step 3: Parse JSON and validate syntax locally**

```python
runbook_data = json.loads(response)
syntax_valid = self._validate_script(runbook.language, runbook.code)
```

- [ ] **Step 4: Handle invalid input explicitly**

```python
if not prism_output.root_cause.strip():
    raise ValueError("prism_output.root_cause must not be empty")
if not syntax_valid:
    raise ValueError("generated runbook failed syntax validation")
```

- [ ] **Step 5: Run the focused tests**

Run: `pytest tests/test_agents.py -v`
Expected: PASS

### Task 4: Verify The Day 4 Slice

**Files:**
- Modify: `server/agents/forge.py`
- Modify: `server/models.py`
- Modify: `tests/test_agents.py`

- [ ] **Step 1: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 2: Review the diff**

Run: `git diff -- server tests docs/superpowers/plans/2026-05-28-forge-runbook-generation.md`
Expected: Only Day 4 FORGE files changed.
