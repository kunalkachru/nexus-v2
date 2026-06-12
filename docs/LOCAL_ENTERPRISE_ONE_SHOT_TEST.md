# Local Enterprise One-Shot Test

This file is for local validation only. It is not intended for the judged GitHub or HF deployment.

## What Changed

The local build now includes a stronger enterprise incident experience across four areas:

- flagship incident UX
- support-triage packet clarity
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
- Additive triage packet now includes:
  - likely owner team
  - likely owner service
  - issue family
  - impacted customer path
  - responder team
  - support queue
  - blast radius and approval focus

### UI changes

- Incident Detail now shows:
  - a support-triage packet instead of only a workflow view
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
- `triage_summary`
- `replica_summary`
- `trace_summary`

## Automated Validation Already Run

These have already been executed locally against the current code:

- `pytest tests/test_app.py tests/test_api_contract.py tests/test_catalogue.py -q`
  - result: covered by the full suite and targeted contract gates
- `pytest tests/ -q`
  - result: `134 passed`
- `npm run browser:verify`
  - result: `10 passed`
- `python demo.py`
  - result: passed
- `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh`
  - result: passed
- `EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh`
  - result: passed

## Recommended One-Shot Local Validation

### Step 1: Rebuild the local Docker app

Standard packaged path:

```bash
./scripts/docker_fresh.sh
```

Relay-backed packaged path:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
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

If you started the relay-backed packaged path, run:

```bash
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
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

### Optional Step 4: Enable bounded REPLICA runtime execution locally

If you want REPLICA to actually boot the curated pack scaffold, run the demo or app with:

```bash
NEXUS_ENABLE_REPLICA_RUNTIME=1 python demo.py
```

Or start the local app with the same env var before opening the incident page.

For the Docker path, use:

```bash
NEXUS_ENABLE_REPLICA_RUNTIME=1 ./scripts/docker_fresh.sh
```

For the packaged relay path, use:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

What that relay profile does:

- keeps the user-facing app on `:7860`
- starts a private `runtime-host` service that owns Docker-backed replay
- delegates `/api/v1/incidents/{id}/replica-replay` from the packaged app to that relay
- returns `relay_available` or `relay_executed` instead of `host_unavailable` when the relay can run the bounded pack

Expected result:

- REPLICA still uses the same flagged outage pack
- the runtime mode becomes runtime-backed for the local run
- replay and mitigation hook output are available in the `replica_summary` payload
- the incident page exposes a `Run bounded replay` action when the host is capable
- in the relay-backed Docker profile, the same action routes through the runtime host transparently
- fresh `nxs_...` incidents persist the last replay packet into incident state so a refresh keeps the measured REPLICA and TRACE findings
- the runtime comparison becomes explicit:
  - baseline replay status and duration
  - selected mitigation replay status and duration
  - runner-up mitigation replay status and duration when available
  - explicit runtime mode guidance in the incident UI
- for `INC001`, the bounded retry pack should show a 504 baseline and a faster post-mitigation replay
- for `INC002`, the bounded DB pack should show a 503 baseline and a successful post-mitigation replay

## Manual Browser Test Cases

Use these in order. They are designed to explain the change set clearly.

### Test Case 1: Seeded incident stays stable and readable

URL:

```text
http://127.0.0.1:7860/incident?nexus_incident_id=INC001
```

Expected:

- incident header loads for `INC001`
- summary cards show:
  - likely owner
  - issue family
  - customer path
  - approval level
- the page does **not** replay the whole handoff every time you refresh
- the relay banner lands directly on the settled Guardian/execution state
- `Replay handoff` is available if you want to watch the relay again deliberately
- `Agent Handoff Thread` is visible
- `Enterprise Task Board` is visible
- exactly 8 collaboration stages are visible in the task board
- PRISM appears as multiple workstreams, not just one linear note
- `REPLICA` appears as a reproduction stage
- `TRACE` appears as a debugging stage
- `Investigation depth · REPLICA` is visible and shows:
  - reproduction pack
  - reproduction status
  - tested mitigations
  - confidence delta
  - baseline replay versus best mitigation
  - clear runtime outcome such as `improved` or `resolved`
  - if runtime mode is enabled locally, the pack/service footprint and replay comparison should be visible in the payload-backed wording
  - if the relay-backed Docker profile is enabled, runtime capability should read as `relay_available` before replay and `relay_executed` after replay
- `Investigation depth · TRACE` is visible and shows:
  - trace status
  - likely modules/functions
  - observed divergence
  - state anomalies
  - inspect-here-first guidance for engineering
  - code owner/team guidance
  - suspected files to inspect first
  - runtime anomalies should include the bounded replay status/duration when runtime mode is enabled
- `Memory-grounded context` is visible
- at least one similar incident is shown
- at least one prior runbook memory is shown
- the top similar incident explains:
  - why it matched
  - what prior action worked
  - what residual risk remained
- `Reliability posture` is visible
- `Fallback and retries` is visible

What this demonstrates:

- stable incident state is separate from live playback
- the likely owner, issue family, and customer path are obvious without narration
- agents are coordinating on a complex issue
- diagnosis is grounded in memory, not only current logs
- orchestration state is visible to the operator
- reproduction and debugging findings are visible before the final action is approved

### Test Case 1A: Relay-backed replay from the packaged app

Precondition:

- start with `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh`

URL:

```text
http://127.0.0.1:7860/incident?nexus_incident_id=INC001
```

Steps:

1. confirm the REPLICA panel says replay is available through an external runtime host
2. click `Run bounded replay`
3. wait for the incident panel to refresh

Expected:

- replay completes without a page error
- runtime capability changes to `relay_executed`
- runtime mode reads as relay-backed runtime execution
- a refresh keeps the same replay-backed REPLICA and TRACE packet instead of dropping back to scaffold-only inference
- baseline vs mitigated comparison appears in the incident panel
- the same flow also works for `INC002`

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
- the incident summary should make the following obvious:
  - likely owner team
  - issue family
  - customer-facing path
  - why the current approval is the final human step
- the investigation cards should populate with plausible findings, even for a fresh `nxs_...` incident:
  - REPLICA should show whether the failure could be recreated
  - REPLICA should show a capability state even when replay cannot run on the current host
  - REPLICA should still rank a selected mitigation and runner-up mitigation in scaffold-only mode
  - TRACE should show where engineering should inspect first
  - TRACE should include file-level and code-owner cues instead of generic debugging prose
- if replay is triggered in the relay-backed Docker profile, a refresh should keep:
  - the replay-backed runtime comparison
  - the replay provenance (`delegated_relay` or `direct_runtime`)
  - the replay-aware developer handoff packet
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
- Guardian reasoning distinguishes:
  - validated signals
  - inferred signals
- validated signals should explicitly reference:
  - REPLICA reproduction state
  - TRACE narrowing state
- runbook impact text mentions:
  - approval focus
  - blast radius
  - rollback posture
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
9. Open the REPLICA card and point out:
   - replay host capability
   - baseline vs selected mitigation
   - runner-up mitigation when present
10. If runtime is enabled, click `Run bounded replay` and refresh the comparison
11. Approve the runbook and show the visible outcome
12. Open `Training`
13. Show latest live triage first, then `Enterprise runtime summary`
14. Open `Replay` and show `INC006` as the harder P0 scenario

## Local-Only Safety Note

Do not push these local validation helpers or further changes while judging is active.
