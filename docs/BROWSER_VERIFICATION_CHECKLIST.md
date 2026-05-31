# NEXUS Browser Verification Checklist

Use this document to verify the UI manually in a browser after the implementation is complete.

## Purpose

This checklist confirms that the enterprise workflow UI loads correctly, the main pages are wired, and the demo flow can be followed end to end.

## What Changed In This Pass

Use this list when you want to confirm the exact changes that landed in the latest check-in:

- The raw-input field on `Inputs` starts empty and `Load example logs` fills a sample on demand.
- The raw-log parser accepts arbitrary labels like `P6` and `critical`.
- The observability layer now fuses fixture incident data with file-backed evidence sources and deployment snapshots.
- The incident console shows the structured result fields, including proposed fix, priority, normalized rank, safety decision, and live reasoning state.
- The incident console now shows guardian policy metadata alongside the safety decision when it is available.
- The `Guardian gate` is an explicit approve/block/request-modification control surface and the decision path is persisted.
- The incident console opens with a compact executive summary, while the dense signals, workflow, audit, and agent-flow sections live inside a collapsible `Operational Details` drawer.
- The `Inputs` page centers the raw-log path first and tucks Slack, stream anomaly, and batch import into a `More Sources` drawer.
- The main pages now include a visible journey trail and short flow callout so the screen itself explains how Queue, Inputs, Incident, History, Replay, Training, and Settings connect.
- The console now distinguishes `APPROVE`, `REJECT`, and `REQUEST_MODIFICATION`, and the incident summary can surface a `needs_modification` execution state.
- The training lab shows solution proposal, raw priority, priority rank, live reasoning state, learning-contract count, audit-event count, and Guardian-review count.
- The settings page exposes the learning-contract count, audit-event count, and Guardian-review count alongside replay launches and training snapshots.
- Mutating incident routes are operator-gated, which keeps the browser demo aligned with the hardened backend flow.

## Built Item Map

Use this map when you want to understand what each backlog item now means in the running product:

1. Real observability and evidence fusion: the incident console now reads log, metric, trace, and deployment evidence from a fused adapter layer instead of only static joins.
2. GUARDIAN policy and governance: the approve/block/request-modification gate is visible in the console, and the explicit review is persisted for later review.
3. Persistent RL and audit artifacts: training, audit, replay, learning contracts, and Guardian review counts are stored durably and surfaced in the UI.
4. Auth, tenant, and deployment hardening: the operator role is required for state-changing incident actions, and tenant/signature checks still protect the request path.
5. Backend decomposition and cleanup: the evidence, governance, and artifact responsibilities now live in smaller focused services rather than one oversized incident module.
6. Docs and validation: this checklist, the pass/fail checklist, and the walkthrough are now aligned with the shipped flow.

## Prerequisites

- A local checkout of the repository.
- A Python environment with the project dependencies installed.
- A browser such as Chrome, Safari, or Firefox.

On this machine, the simplest working interpreter is:

- `/opt/anaconda3/bin/python`

## Setup

1. Open a terminal in the repository root.
2. Start the application server:

```bash
uvicorn server.app:app --host 127.0.0.1 --port 8000
```

3. Keep that terminal running.
4. Open a browser and go to:

```text
http://127.0.0.1:8000/queue
```

## Automatic Option

If you want the environment to start, run the tests, and open the verification pages for you, use:

```bash
bash scripts/browser_verification.sh
```

That script:

- runs the test suite
- starts the local server
- waits for `/health`
- opens the verification pages in your browser
- keeps the server running until you stop it

## What To Verify First

Before checking individual pages:

- The app loads without a blank page.
- The main shell renders with the left navigation.
- The browser address bar reflects the page you opened.
- There are no obvious JavaScript or rendering failures.

## Page Verification Order

Verify the pages in this order:

1. `Queue`
2. `Incident Console`
3. `Input Channels`
4. `History`
5. `Sample Replay`
6. `RL Training Lab`
7. `Settings`

This order matches the intended product story.

## Queue Page

Open:

```text
http://127.0.0.1:8000/queue
```

Confirm:

- The queue is the landing page.
- Active incidents are visible.
- Severity, source channel, and stage information are shown.
- The page includes a short trail or callout that explains Queue as the starting point for the rest of the product.
- Clicking an incident opens the incident console.

Pass criteria:

- The page looks like an operator queue, not a static dashboard.

## Incident Console

Open:

```text
http://127.0.0.1:8000/incident
```

Confirm:

- The incident timeline is visible.
- The workflow starts with intake and moves through agent stages when you open `Operational Details`.
- SENTINEL, PRISM, FORGE, and GUARDIAN are each represented in the drawer.
- Raw incident text and normalized evidence are visible for live incidents.
- Evidence sections for logs, metrics, traces, and deployments are present.
- Evidence provenance shows the fused adapter story rather than only the old fixture-only path.
- A newly created incident opens with backend-assembled live context, not just browser-synthesized data.
- `Normalized evidence` is read-only.
- The `SENTINEL -> PRISM -> FORGE -> GUARDIAN` rail is read-only.
- A live reasoning toggle is visible and changes the rendered incident without editing the URL manually.
- The `Guardian gate` buttons are the explicit approval, block, and request-modification controls, if they are visible.
- The incident summary exposes the structured result fields, including proposed fix, priority, normalized rank, safety decision, and live reasoning state.
- The incident summary exposes the guardian policy field when the backend returns one.
- The dense incident sections are tucked into `Operational Details` so the top of the console stays readable.
- The console header shows the page in the product flow, making the handoff from Queue and Inputs obvious.

Pass criteria:

- You can explain the incident from intake to outcome using the page alone.
- You can see the difference between a seeded demo incident and a newly created live incident.

## Input Channels

Open:

```text
http://127.0.0.1:8000/inputs
```

Confirm:

- The raw-log paste path is visible and clearly described.
- The raw input field starts empty.
- A `Load example logs` button is visible for quick demos.
- The `More Sources` drawer keeps the alternate intake methods available without crowding the raw-log flow.
- The page includes a journey trail and flow callout that explain Inputs as the raw-entry path.
- Multiple intake options are visible.
- The page shows more than one input method.
- The intent of the page is to demonstrate how incidents enter the system.
- A live reasoning toggle is visible and can be switched before submission.

Pass criteria:

- Each input method appears to feed the same incident workflow.
- The raw-log preview updates when the pasted text changes.
- The parsed preview reflects the pasted content, including arbitrary labels such as `P6` or `critical`.
- Submitting raw logs creates an incident and updates the console link with the new incident ID.

## History

Open:

```text
http://127.0.0.1:8000/history
```

Confirm:

- Past incidents are listed.
- Closed outcomes are visible.
- Replay or review entry points are available.
- The page includes a trail or callout that explains History as the replayable archive.

Pass criteria:

- The page shows operational memory, not just current-state data.

## Sample Replay

Open:

```text
http://127.0.0.1:8000/replay
```

Confirm:

- Curated replay scenarios are listed.
- Scenario names are understandable to a non-technical audience.
- A replay launch action is available.
- The page explains what replay produces.
- The page includes a trail or callout that explains Replay as the repeatable validation lane.

Pass criteria:

- You can launch a sample incident and use it as a repeatable demo.

## RL Training Lab

Open:

```text
http://127.0.0.1:8000/training
```

Confirm:

- Baseline reward and trained reward are visible.
- A reward curve is visible.
- Reward breakdown information is visible.
- The RL episode contract is visible.
- Reward evaluation is visible.
- The observation-state story is visible.
- The latest episode links back to a real incident.
- The page reads like a learning story, not a research dump.
- The RL episode contract shows the structured result fields, including raw priority, priority rank, solution proposal, and live reasoning.
- The training header shows the audit-event count and Guardian-review count.
- The page includes a trail or callout that explains Training as the memory layer.

Pass criteria:

- The learning layer is understandable without reading code.

## Settings

Open:

```text
http://127.0.0.1:8000/settings
```

Confirm:

- Demo mode or product mode is shown.
- Integration posture is visible.
- Replay readiness or operational configuration is visible.
- The learning-contract count is visible alongside replay launches and training snapshots.
- The audit-event count and Guardian-review count are visible.
- The page includes a trail or callout that explains Settings as the trust and control plane.

Pass criteria:

- The page communicates that the system is deployable, not only demoable.

## End-To-End Demo Check

After the pages are verified individually, do one full walkthrough:

1. Start on `Queue`.
2. Open one incident in `Incident Console`.
3. Walk the timeline from intake to outcome.
4. Switch to `Input Channels` and show the intake options.
5. Paste raw logs, including a label such as `P6` or `critical`, and show the parsed preview update.
6. Submit the raw logs, open the returned incident console, and point to the proposed fix and live reasoning toggle.
7. Open `History` and show a past incident.
8. Open `Sample Replay` and show a curated replay scenario.
9. Open `RL Training Lab` and point to the reward curve, RL episode contract, solution proposal, and observation states.
10. Finish in `Settings`.

## What Good Looks Like

- The navigation is consistent across pages.
- The pages look like one product, not separate prototypes.
- The incident story is easy to follow.
- The agent contributions are clear.
- The replay and training pages support the main product narrative.

## If Something Fails

- Refresh the page once.
- Check the browser console for errors.
- Confirm the server is still running.
- Revisit the relevant page in the order above.
- If a page still fails, capture:
  - the URL
  - what you expected
  - what actually happened
  - any visible console message

## Optional Verification Command

If you want a quick backend sanity check before opening the browser, run:

```bash
curl -s http://127.0.0.1:8000/api/v1/training/summary \
  -H 'x-user-id: user-123' \
  -H 'x-tenant-id: tenant-a' \
  -H 'x-roles: operator' \
| python3 -c "import json,sys; p=json.load(sys.stdin); c=p['rl_episode_contract']; e=p['reward_evaluation']; print('reward_curve_final=', e['reward_curve_final']); print('incident_id=', c['observation']['incident_id']); print('guardian_decision=', c['guardian_decision'])"
```

That does not replace browser verification, but it confirms the backend training contract is healthy and readable from the terminal.
