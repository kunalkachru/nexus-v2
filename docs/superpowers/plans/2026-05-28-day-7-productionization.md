# Day 7 Productionization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the final dashboard, demo, and HuggingFace Spaces deployment package for NEXUS v2.

**Architecture:** Reuse the deterministic Day 6 trainer as the source of truth for production metrics, add a static dashboard served by FastAPI, and package the service with a small Docker image for HF Spaces. Keep runtime behavior deterministic by default so tests and the judge demo remain reliable and fast.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Pydantic v2, pytest, static HTML/CSS/JS

---

### Task 1: Metrics Reporting Surface

**Files:**
- Create: `server/reporting.py`
- Modify: `training/runner.py`
- Test: `tests/test_training.py`

- [ ] **Step 1: Write failing tests for persisted metrics payload expectations**
- [ ] **Step 2: Run targeted training tests to confirm failure**
- [ ] **Step 3: Implement metrics shaping helpers and persistence hooks**
- [ ] **Step 4: Re-run targeted training tests to confirm pass**

### Task 2: Dashboard And App Serving

**Files:**
- Create: `frontend/dashboard.html`
- Modify: `server/app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing tests for dashboard routes and metrics API**
- [ ] **Step 2: Run targeted app tests to confirm failure**
- [ ] **Step 3: Implement static serving and responsive dashboard**
- [ ] **Step 4: Re-run targeted app tests to confirm pass**

### Task 3: Judge Demo

**Files:**
- Create: `demo.py`
- Test: `tests/test_demo.py`

- [ ] **Step 1: Write failing tests for demo output contract**
- [ ] **Step 2: Run targeted demo tests to confirm failure**
- [ ] **Step 3: Implement deterministic end-to-end demo runner**
- [ ] **Step 4: Re-run targeted demo tests to confirm pass**

### Task 4: Deployment Package

**Files:**
- Create: `Dockerfile`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `README.md`
- Test: `tests/test_deployment.py`

- [ ] **Step 1: Write failing tests for deployment artifact presence and key contents**
- [ ] **Step 2: Run targeted deployment tests to confirm failure**
- [ ] **Step 3: Implement production packaging artifacts**
- [ ] **Step 4: Re-run targeted deployment tests to confirm pass**

### Task 5: Verification

**Files:**
- Verify only

- [ ] **Step 1: Run `pytest tests/ -v`**
- [ ] **Step 2: Run `python demo.py`**
- [ ] **Step 3: Run `docker build -t nexus-v2 .`**
- [ ] **Step 4: Run `docker run -e OPENAI_API_KEY=$OPENAI_API_KEY nexus-v2` if Docker is available**
- [ ] **Step 5: Review diff for production readiness**
