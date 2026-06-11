---
name: nexus-backlog-loop
description: >
  Drains the active NEXUS backlog file in a build-test-commit loop.
  Builds, tests, commits each item and moves to the next without stopping.
  Logs blockers and keeps backlog state explicit.
---

## What this skill does

Runs the NEXUS build-test-commit loop against the active backlog file.
Read AGENTS.md fully before starting.

## Activation

Read AGENTS.md first. Then read WORKING_STATE.md. Then read the active backlog file. Start from the first pending item.

## Stack

- Backend: Python / FastAPI — no ORM migrations needed
- Frontend: vanilla JS — no React, no build step
- Tests: pytest (tests/) + Playwright (npm run browser:verify)
- Docker: ./scripts/docker_fresh.sh → waits for :7860/health
- Smoke: BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh

## Two code paths — understand before editing

1. STATIC/SEEDED path: `server/services/surface_payloads.py:build_incident_response` → reads from `server/incident_payloads.py` fixtures → used by Playwright tests and API contract tests
2. LIVE GRAPH path: `server/services/enterprise_runtime.py` LangGraph nodes → used by live incidents

Keep these two paths semantically aligned. Do not let one overclaim compared with the other.

## Current validated baseline

- `pytest tests/ -q` -> `124 passed`
- `npm run browser:verify` -> `10 passed`
- `python demo.py` -> passes
- `./scripts/docker_fresh.sh` -> passes
- `BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh` -> passes

## Loop

```
read active backlog file → first "pending" item
→ read files_likely_touched → run baseline test to confirm failure
→ fix → run all test_gates
→ all pass? mark "done", commit, loop
→ fail after repeated debugging? mark "blocked", document blocker, commit backlog state
→ no pending left? stop and report completion
```
