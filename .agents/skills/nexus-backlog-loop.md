---
name: nexus-backlog-loop
description: >
  Drains the NEXUS backlog.json for items 9-14.
  Builds, tests, commits each item and moves to the next without stopping.
  Logs unresolvable blockers to BLOCKERS.md and continues.
---

## What this skill does

Runs the NEXUS build-test-commit loop for items 9–14.
Read AGENTS.md fully before starting — it has the full loop rules, file map, and function map.

## Activation

Read AGENTS.md first. Then read backlog.json. Start from first pending item.

## Stack

- Backend: Python / FastAPI — no ORM migrations needed
- Frontend: vanilla JS — no React, no build step
- Tests: pytest (tests/) + Playwright (npm run browser:verify)
- Docker: ./scripts/docker_fresh.sh → waits for :7860/health
- Smoke: BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh

## Two code paths — understand before editing

1. STATIC/SEEDED path: `server/services/surface_payloads.py:build_incident_response` → reads from `server/incident_payloads.py` fixtures → used by Playwright tests and API contract tests
2. LIVE GRAPH path: `server/services/enterprise_runtime.py` LangGraph nodes → used by live incidents

Items 9-13 fix the STATIC path. The live path is already correct.

## Pre-existing failures (do not fix, do not let worsen)

```
FAILED tests/test_replica_runtime.py::test_replica_runner_inspects_pack_scaffold_assets
FAILED tests/test_replica_runtime.py::test_replica_runner_executes_db_pool_pack
FAILED tests/test_security.py::test_webhook_requires_valid_signature
```

## Loop

```
read backlog.json → first "pending" item
→ read files_likely_touched → run baseline test to confirm failure
→ fix → run all test_gates
→ all pass (beyond 3 pre-existing)? mark "done", commit, loop
→ fail after 5 tries? BLOCKERS.md, mark "blocked", commit, loop
→ no pending left? stop
```
