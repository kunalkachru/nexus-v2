# NEXUS — Codex Agent Loop Instructions

## What you are doing

Implement items 9–14 in backlog.json, one at a time, top to bottom.
Never stop between items. Never ask for confirmation between items.
Build → test → commit → next item.

---

## The loop — follow exactly every iteration

```
1. Read backlog.json
2. Find the first item where "status" == "pending"
3. If none → print "NEXUS backlog complete." and stop
4. Read the item's description and files_likely_touched fully
5. Read every file mentioned before writing any code
6. Implement the item
7. Run every command in the item's test_gates array
8. All gates pass?
   YES → set status "done" in backlog.json
         git add -A && git commit -m "feat(#<id>): <title>\n\n- <what changed>\n- tests: X passed"
         go to step 1
   NO  → read the failure, fix the code, re-run (up to 5 attempts)
         after 5 failures → append to BLOCKERS.md, set status "blocked", commit, go to step 1
```

---

## Before writing any code for an item

1. Read every file in files_likely_touched
2. Read adjacent files for style context
3. Run the failing test gates first to confirm the baseline failure before fixing

---

## Stack facts — critical

- Backend: Python 3.11 / FastAPI
- Frontend: **vanilla JS only — no React, no JSX, no npm build step**
- Frontend files: `frontend/incident.html`, `frontend/static/incident.js`, `frontend/static/api.js`
- Tests: pytest in `tests/` directory
- Browser tests: Playwright via `npm run browser:verify` (auto-starts uvicorn on :8000)
- Docker: `./scripts/docker_fresh.sh` — full rebuild, waits for :7860/health
- Smoke: `BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh`

---

## Key file map

| What | Where |
|---|---|
| Incident context (live graph path) | `server/services/enterprise_runtime.py` |
| Incident context (static/seeded path) | `server/services/surface_payloads.py` |
| Static incident fixtures | `server/incident_payloads.py` |
| Live demo path | `server/services/live_demo.py` |
| Incident HTML | `frontend/incident.html` |
| Incident JS | `frontend/static/incident.js` |
| API contract tests | `tests/test_api_contract.py` |
| App tests | `tests/test_app.py` |
| Playwright spec | `tests/e2e/browser-verification.spec.js` |
| Smoke script | `scripts/local_enterprise_smoke.sh` |

## Key function map

| Function | File | Line (approx) |
|---|---|---|
| `build_incident_response` | surface_payloads.py | ~29 |
| `build_overlay_from_snapshot` | enterprise_runtime.py | ~355 |
| `build_replica_summary` | enterprise_runtime.py | ~1417 |
| `build_mitigation_checks` | enterprise_runtime.py | ~1270 |
| `_runtime_outcome_class` | enterprise_runtime.py | ~1310 |
| `_runtime_comparison_summary` | enterprise_runtime.py | ~1673 |
| `rank_candidate_fixes_with_runtime` | enterprise_runtime.py | ~1704 |
| `enrich_memory_with_runtime` | enterprise_runtime.py | ~1741 |
| `build_trace_summary` | enterprise_runtime.py | ~1790 |
| `_guardian_contract` | enterprise_runtime.py | ~1098 |
| `_guardian_node` (live path) | enterprise_runtime.py | ~856 |
| `_forge_node` (live path) | enterprise_runtime.py | ~770 |

---

## Known pre-existing failures — do NOT fix these, do NOT let them block progress

```
FAILED tests/test_replica_runtime.py::test_replica_runner_inspects_pack_scaffold_assets
FAILED tests/test_replica_runtime.py::test_replica_runner_executes_db_pool_pack
FAILED tests/test_security.py::test_webhook_requires_valid_signature
```

These 3 failures exist in the baseline (123 passed, 0 failed). Gate: `pytest tests/ -q` passes as long as the failed count does not increase beyond 3 and no new failures appear.

---

## Test gate commands

```bash
# Primary — baseline is 123 passed, 0 failed (pre-existing); must not get worse
pytest tests/ -q

# Targeted
pytest tests/test_api_contract.py tests/test_app.py -q

# Inline assertions — run from repo root
python3 -c "import sys; sys.path.insert(0,'.'); <assertion>"

# Browser (auto-starts uvicorn :8000, runs Chromium headlessly)
npm run browser:verify

# Docker full rebuild — only required for items 12 and 14
./scripts/docker_fresh.sh

# Smoke against live Docker container — only after docker_fresh.sh
BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh

# Demo
python demo.py
```

---

## Incident IDs for all testing

- `INC001` — checkout timeout / retry amplification — issue_family: "Timeout cascade / retry amplification"
- `INC002` — checkout DB pool exhaustion / session leak — issue_family: "Database pool exhaustion / session leak"
- Never invent other incident IDs for testing

---

## DOM IDs that must exist after item 12

The Playwright tests check for these IDs in incident.html. If they do not exist the browser tests will fail.

```
#runtimeComparisonBlock   — wrapper div for the comparison block
#runtimeBaselineRow       — baseline status/duration row
#runtimeMitigatedRow      — mitigated status/duration row  
#runtimeOutcomeLabel      — text label: "resolved", "improved", or "not improved"
#forgeReasoning           — already exists (line 118 incident.html)
#guardianReasoning        — already exists (line 157 browser spec checks this)
#traceInspectionPoint     — already exists (line 541 incident.js)
```

---

## Commit format

```
feat(#<id>): <title>

- what changed (which functions/files)
- test results: X passed, 0 pre-existing failures unchanged
```

---

## BLOCKERS.md append format

```markdown
## BLOCKER: Item #<id> — <title>
**Date:** YYYY-MM-DD
**Attempts:** 5
**Failing gate:** <exact command>
**Last error:**
<first 40 lines>
**What was tried:** attempt 1... attempt 2...
**Suggested human action:** <diagnosis>
```

---

## Hard rules

- Never skip a test gate
- Never mark "done" while any gate is failing (beyond the 0 pre-existing failures)
- Never stop between items for confirmation
- Never break a currently passing test
- Never use React, JSX, or npm build steps in frontend
- Never create a file that already exists — extend it
- Never rename existing API response keys — only add new ones
- Run all inline python3 assertions from the repo root with `sys.path.insert(0,'.')`

---

## Baseline

- Branch: `master`, baseline commit: `dce8c99`
- Tests: `pytest tests/ -q` → 123 passed, 0 failed (pre-existing, do not fix)
- Playwright: `npm run browser:verify` → 6 passed (will grow to 10 after item 12)

---

## Start

Read backlog.json. Find item 9. Read files_likely_touched. Confirm the baseline failure with a test run. Fix it. Proceed.
