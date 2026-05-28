# GRPO, Curriculum, And Training Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a deterministic Day 6 training package with a GRPO-style policy update loop, 5-level curriculum adapter, and reproducible training runner that records reward curves and episode costs.

**Architecture:** Keep Day 6 fully local and test-first. `training/policy.py` will hold lightweight scalar policies plus a pure-Python Adam optimizer and step records. `training/curriculum.py` will manage the 5 difficulty levels and 55% advancement rule. `training/grpo_loop.py` will sample incidents, run deterministic episodes through `NexusCore`, compute a relative advantage, update policies on-policy, and record metrics. `training/runner.py` will wire default agents, default policies, and JSON reward-curve saving for reproducible runs.

**Tech Stack:** Python 3.11+, pytest, standard library JSON/random/math

---

### Task 1: Define The Training Contracts In Tests

**Files:**
- Create: `tests/test_training.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_grpo_update_increases_policy_likelihood_of_good_actions() -> None:
    ...


def test_curriculum_advances_after_fifty_five_percent_threshold() -> None:
    ...


def test_thirty_episode_training_shows_reward_improvement() -> None:
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_training.py -v`
Expected: FAIL because the `training/` package does not exist yet.

- [ ] **Step 3: Keep expectations on the public API**

```python
assert summary.reward_curve[0] < summary.reward_curve[-1]
assert summary.final_difficulty in {"Medium", "Hard", "Nightmare", "Impossible"}
assert summary.total_cost_usd >= 0.0
```

- [ ] **Step 4: Re-run the focused tests**

Run: `pytest tests/test_training.py -v`
Expected: Still FAIL, but only because production code is missing.

### Task 2: Add Typed Training Models And Policies

**Files:**
- Create: `training/__init__.py`
- Create: `training/policy.py`
- Test: `tests/test_training.py`

- [ ] **Step 1: Add the minimal policy and optimizer types**

```python
class ScalarPolicy:
    ...


class AdamScalarOptimizer:
    ...


class TrainingStepRecord:
    ...
```

- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/test_training.py -v`
Expected: FAIL because the curriculum and trainer still do not exist.

### Task 3: Implement Curriculum Learning

**Files:**
- Create: `training/curriculum.py`
- Test: `tests/test_training.py`

- [ ] **Step 1: Implement the public adapter**

```python
class CurriculumAdapter:
    ...
```

- [ ] **Step 2: Encode the 5 levels and 55% advancement rule**

```python
levels = ["Easy", "Medium", "Hard", "Nightmare", "Impossible"]
```

- [ ] **Step 3: Run the focused tests**

Run: `pytest tests/test_training.py -v`
Expected: Partial PASS for curriculum coverage, trainer tests still FAIL.

### Task 4: Implement GRPO-Style Training Loop

**Files:**
- Create: `training/grpo_loop.py`
- Test: `tests/test_training.py`

- [ ] **Step 1: Implement the public trainer**

```python
class GRPOTrainer:
    def train(self, num_episodes: int = 30) -> TrainingSummary:
        ...
```

- [ ] **Step 2: Sample incidents, compute advantages, and apply Adam updates**

```python
advantage = reward - baseline
optimizer.step(policy, gradient)
```

- [ ] **Step 3: Cap step records per episode at 20**

```python
steps = steps[:20]
```

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/test_training.py -v`
Expected: PASS

### Task 5: Implement Training Runner

**Files:**
- Create: `training/runner.py`
- Test: `tests/test_training.py`

- [ ] **Step 1: Implement the default runner entrypoint**

```python
def run_training(...):
    ...
```

- [ ] **Step 2: Save reward curves and track costs**

```python
json.dump(summary.model_dump(), fp)
```

- [ ] **Step 3: Run the focused tests**

Run: `pytest tests/test_training.py -v`
Expected: PASS

### Task 6: Verify The Day 6 Slice

**Files:**
- Create: `training/__init__.py`
- Create: `training/policy.py`
- Create: `training/curriculum.py`
- Create: `training/grpo_loop.py`
- Create: `training/runner.py`
- Create: `tests/test_training.py`

- [ ] **Step 1: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 2: Review the diff**

Run: `git diff -- training tests docs/superpowers/plans/2026-05-28-grpo-curriculum-training.md`
Expected: Only Day 6 files changed.
