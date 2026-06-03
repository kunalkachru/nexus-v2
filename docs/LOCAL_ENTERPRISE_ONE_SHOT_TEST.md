# Local Enterprise One-Shot Test

This file is for local validation only. It is not intended for the judged GitHub or HF deployment.

## What Changed

The local build now includes a stronger enterprise incident experience across four areas:

- flagship incident UX
- memory-grounded agent reasoning
- training/runtime interpretation
- a harder replayable enterprise scenario

### Core backend changes

- LangGraph-based orchestration runtime in `server/services/enterprise_runtime.py`
- Explicit PRISM sub-problem split:
  - evidence correlation
  - deployment/change analysis
  - historical analog lookup
- Memory layer with:
  - similar incidents
  - prior runbooks
  - unresolved items
  - recent Guardian outcomes
- Guardian policy output now includes:
  - risk class
  - required approval level
  - blocked controls
  - rollback readiness
  - simulation readiness

### UI changes

- Incident Detail now shows:
  - a stable seeded incident state on refresh
  - one-time relay playback for fresh incidents
  - explicit `Replay handoff`
  - `Enterprise Task Board`
  - `Memory-grounded context`
  - `Reliability posture`
  - `Fallback and retries`
  - clearer Guardian gate and next-operator-step wording
- Training now shows:
  - real clickable section navigation
  - `Enterprise runtime summary`
  - latest live triage mapping for this browser
- Replay now includes a harder scenario:
  - `INC006` certificate-expiry / public TLS outage

### Contract changes

Incident context now includes additive enterprise fields:

- `orchestration`
- `task_board`
- `memory_hits`
- `agent_metrics`
- `fallback_summary`
- `enterprise_summary`

## Automated Validation Already Run

These have already been executed locally against the current code:

- `pytest tests/test_app.py tests/test_api_contract.py tests/test_catalogue.py -q`
  - result: `30 passed`
- `npm run browser:verify`
  - result: `6 passed`
- `python demo.py`
  - result: passed

## Recommended One-Shot Local Validation

### Step 1: Rebuild the local Docker app

```bash
./scripts/docker_fresh.sh
```

Wait until the script prints:

```text
Fresh container is ready.
```

### Step 2: Run the fast smoke check

```bash
chmod +x ./scripts/local_enterprise_smoke.sh
./scripts/local_enterprise_smoke.sh
```

Expected result:

- health check passes
- incident page contains enterprise markers
- training page contains enterprise runtime summary
- incident context JSON contains enterprise fields

### Step 3: Run the readable console demo

```bash
python demo.py
```

Expected result:

- incident `INC001` prints
- orchestration story prints
- task board prints all major agent handoffs
- memory-hit counts print
- Guardian policy details print
- execution result prints

## Manual Browser Test Cases

Use these in order. They are designed to explain the change set clearly.

### Test Case 1: Seeded incident stays stable and readable

URL:

```text
http://127.0.0.1:7860/incident?nexus_incident_id=INC001
```

Expected:

- incident header loads for `INC001`
- the page does **not** replay the whole handoff every time you refresh
- the relay banner lands directly on the settled Guardian/execution state
- `Replay handoff` is available if you want to watch the relay again deliberately
- `Agent Handoff Thread` is visible
- `Enterprise Task Board` is visible
- exactly 6 collaboration stages are visible in the task board
- PRISM appears as multiple workstreams, not just one linear note
- `Memory-grounded context` is visible
- at least one similar incident is shown
- at least one prior runbook memory is shown
- `Reliability posture` is visible
- `Fallback and retries` is visible

What this demonstrates:

- stable incident state is separate from live playback
- agents are coordinating on a complex issue
- diagnosis is grounded in memory, not only current logs
- orchestration state is visible to the operator

### Test Case 2: Fresh incident replays once and lands on Guardian

URL:

```text
http://127.0.0.1:7860/inputs
```

Steps:

1. Click `Load example logs`
2. Click `Submit raw logs`

Expected:

- app redirects to a created `nxs_...` incident
- the relay visibly progresses through:
  - `SENTINEL`
  - `PRISM`
  - `FORGE`
  - `GUARDIAN`
- Guardian becomes the obvious control point
- the runbook explainer is populated
- after one load, a manual refresh should show the settled state instead of replaying again

What this demonstrates:

- live incident triage is understandable without narration
- fresh incidents and seeded incidents behave differently in the right way

### Test Case 3: Governance is enterprise-shaped

On the same fresh `nxs_...` incident or on `INC001`:

Expected:

- GUARDIAN section is visible
- GUARDIAN reasoning is populated
- execution gate text mentions approval requirements
- Guardian metadata reflects policy posture such as:
  - approval level
  - rollback readiness
  - simulation readiness

What this demonstrates:

- execution is governed, not blindly automated

### Test Case 4: Training view shows runtime health and latest-run linkage

URL:

```text
http://127.0.0.1:7860/training
```

Expected:

- `Learning summary`, `Governance summary`, and `Advanced artifacts` are clickable pills
- clicking each pill scrolls to the correct section
- clicking `Advanced artifacts` opens the advanced panel
- `Last live triage in this browser` references the same `nxs_...` incident you just created
- `Enterprise runtime summary` is visible
- the following values are visible:
  - orchestration success rate
  - fallback rate
  - branch completion rate
  - guarded execution rate
- `Learning summary` is still visible
- `Governance summary` is still visible

What this demonstrates:

- the product now surfaces runtime quality, not just learning artifacts
- the latest live run is clearly separated from the broader training baseline

### Test Case 5: Harder P0 scenario is wired correctly

URL:

```text
http://127.0.0.1:7860/replay
```

Steps:

1. Select `Certificate expiry`
2. Confirm the scenario text describes a public TLS outage
3. Click the console link or launch action

Expected:

- replay title reflects the certificate expiry scenario
- the scenario opens `INC006`
- the incident story reads like a public trust-boundary outage, not a generic app failure

What this demonstrates:

- the product can showcase more than one incident archetype
- the enterprise story is not limited to the original timeout cascade

## Suggested Demo Script For You

If you want to explain the value in one shot, use this narrative:

1. Open `INC001`
2. Explain that this is no longer a single-agent incident assistant
3. Point at the `Enterprise Task Board`
4. Show that PRISM splits the problem into:
   - evidence
   - deployment changes
   - historical analogs
5. Point at `Memory-grounded context`
6. Explain that FORGE is not acting in a vacuum; it uses runbook history and unresolved items
7. Point at GUARDIAN and explain policy gating
8. Create one fresh `nxs_...` incident from `Inputs`
9. Approve the runbook and show the visible outcome
10. Open `Training`
11. Show latest live triage first, then `Enterprise runtime summary`
12. Open `Replay` and show `INC006` as the harder P0 scenario

## Local-Only Safety Note

Do not push these local validation helpers or further changes while judging is active.
