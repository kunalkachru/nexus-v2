# Guardian, Reward, And Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `GuardianAgent.review()`, deterministic `compute_episode_reward()`, and a minimal end-to-end orchestrator that routes incidents through all four agents and computes a stable reward.

**Architecture:** Keep Day 5 deterministic and fully local. `GuardianAgent` will inspect the typed FORGE runbook for destructive commands and secrets, return a typed review decision, and never depend on external services. Reward computation will live in `server/grader.py` over a typed `Episode` model with five normalized dimensions plus an asymmetric severity penalty. `server/orchestrator.py` will compose SENTINEL, PRISM, FORGE, and GUARDIAN into one synchronous episode runner for end-to-end tests.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest

---

### Task 1: Define The Day 5 Contracts In Tests

**Files:**
- Modify: `tests/test_agents.py`
- Create: `tests/test_grader.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_guardian_approves_safe_runbook() -> None:
    ...


def test_reward_is_deterministic() -> None:
    ...


def test_run_episode_routes_through_all_agents() -> None:
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_agents.py tests/test_grader.py tests/test_orchestrator.py -v`
Expected: FAIL because the GUARDIAN API, reward function, and orchestrator do not exist yet.

- [ ] **Step 3: Keep expectations on the public contract**

```python
assert review.decision == "approve"
assert reward.composite == expected
assert episode.guardian_output.decision == "approve"
```

- [ ] **Step 4: Re-run the focused tests**

Run: `pytest tests/test_agents.py tests/test_grader.py tests/test_orchestrator.py -v`
Expected: Still FAIL, but only because production code is missing.

### Task 2: Add Typed Review, Episode, And Reward Models

**Files:**
- Modify: `server/models.py`
- Test: `tests/test_agents.py`
- Test: `tests/test_grader.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Add the minimal output types**

```python
class GuardianReviewResult(BaseModel):
    ...


class EpisodeReward(BaseModel):
    ...


class Episode(BaseModel):
    ...
```

- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/test_agents.py tests/test_grader.py tests/test_orchestrator.py -v`
Expected: FAIL because the guard logic, reward function, and runner still do not exist.

### Task 3: Implement GUARDIAN Safety Review

**Files:**
- Modify: `server/agents/guardian.py`
- Test: `tests/test_agents.py`

- [ ] **Step 1: Implement the public API**

```python
class GuardianAgent(BaseAgent):
    def review(
        self,
        forge_output: ForgeRunbookResult,
        sentinel_output: SentinelClassification,
        prism_output: PrismDiagnosis,
    ) -> GuardianReviewResult:
        ...
```

- [ ] **Step 2: Score for destructive patterns and secrets**

```python
dangerous = self._contains_dangerous_patterns(...)
secret = self._contains_hardcoded_secret(...)
```

- [ ] **Step 3: Run the focused agent tests**

Run: `pytest tests/test_agents.py -v`
Expected: PASS

### Task 4: Implement Deterministic Reward Computation

**Files:**
- Create: `server/grader.py`
- Test: `tests/test_grader.py`

- [ ] **Step 1: Implement the public function**

```python
def compute_episode_reward(episode: Episode) -> EpisodeReward:
    ...
```

- [ ] **Step 2: Encode five weighted dimensions plus asymmetric severity penalty**

```python
weights = {"mttr": 0.30, "diagnosis": 0.25, "customer": 0.20, "coordination": 0.15, "oversight": 0.05}
```

- [ ] **Step 3: Run the focused grader tests**

Run: `pytest tests/test_grader.py -v`
Expected: PASS

### Task 5: Implement End-To-End Episode Orchestration

**Files:**
- Create: `server/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Implement the public runner**

```python
class NexusCore:
    def run_episode(self, incident: IncidentDefinition) -> Episode:
        ...
```

- [ ] **Step 2: Route the deterministic phases**

```python
sentinel -> prism -> forge -> guardian -> verify -> compute reward
```

- [ ] **Step 3: Run the focused orchestration tests**

Run: `pytest tests/test_orchestrator.py -v`
Expected: PASS

### Task 6: Verify The Day 5 Slice

**Files:**
- Modify: `server/agents/guardian.py`
- Create: `server/grader.py`
- Create: `server/orchestrator.py`
- Modify: `server/models.py`
- Modify: `tests/test_agents.py`
- Create: `tests/test_grader.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 2: Review the diff**

Run: `git diff -- server tests docs/superpowers/plans/2026-05-28-guardian-reward-orchestration.md`
Expected: Only Day 5 files changed.
