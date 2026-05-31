# NEXUS v2 Full Manual Browser Walkthrough

Current as of 2026-05-30.

This is the full step-by-step guide for a new person who has just downloaded the repo.
It explains how to set up the product, start it, open the browser UI, and validate every main screen and workflow by hand.

Use this doc if you want to:

- understand the product from the outside in
- run a live demo
- verify that the current UI and backend behavior are working
- explain the product to a non-technical person

## What This Pass Verified

The latest implementation and browser pass confirmed:

- raw-log intake starts empty and `Load example logs` fills a sample on demand
- arbitrary priority labels such as `P6` and `critical` are accepted
- the observability adapter layer can fuse log, metric, trace, and deployment evidence from a file-backed source when available
- the incident console shows the proposed fix, priority, normalized rank, and live reasoning state
- the `Guardian gate` is the explicit approval, block, and request-modification control surface
- the console shows `APPROVE`, `REJECT`, and `REQUEST_MODIFICATION`, and the execution state can become `needs_modification` when revision is required
- the console also shows guardian policy metadata when a decision has been recorded
- the top of the incident console stays compact, while signals, workflow, audit, and agent-flow data live in a collapsible `Operational Details` drawer
- the Inputs page keeps raw logs as the clearest path and tucks alternate sources into a collapsible `More Sources` drawer
- the training lab shows the solution proposal, learning-contract count, audit-event count, and Guardian-review count
- the settings page shows the learning-contract count, audit-event count, and Guardian-review count
- durable artifact counts now survive restarts through the local artifact store
- mutating incident routes are operator-gated, so the browser demo runs with the same control surface as the hardened backend

## What Each Item Became

If you want the shortest plain-English summary of what was built, use this list:

1. Real observability and evidence fusion: the incident console now blends raw incident context with logs, metrics, traces, and deployment snapshots.
2. GUARDIAN policy and governance: the approve/block/request-modification control is explicit in the UI and the decision is stored as part of the incident record, policy record, and artifact trail.
3. Persistent RL and audit artifacts: the learning loop, audit history, and Guardian reviews are persisted and surfaced in Training and Settings.
4. Auth, tenant, and deployment hardening: state-changing routes require an operator role, and the request path still enforces tenant and signature checks.
5. Backend decomposition and cleanup: the incident service is now split across focused helpers for observability, governance, artifacts, and platform state.
6. Docs and validation: the walkthrough and browser checklists now describe the exact flow the product ships with.

## What This Product Is

NEXUS v2 is a browser-based incident-response product.

It has:

- a raw-log intake path for pasting incident text, logs, or stack traces
- one backend server that serves the pages and API
- one browser UI that acts as the client
- raw-log intake as the primary MVP entrypoint
- queue navigation for operational follow-up
- a detailed incident console
- intake channels for new incidents
- history, replay, training, and settings screens

Important:

- There is no separate frontend build process you need to manage for the current local demo.
- The browser is the client.
- The server serves the HTML pages and the JSON data behind them.

## What You Need Before You Start

You only need a basic local machine with:

- the repository downloaded
- Docker installed, if you want the simplest setup
- or Python installed, if you want to run the server directly
- a web browser

Recommended setup:

- Use Docker if you want the easiest and most repeatable path.
- Use direct Python startup only if you already know the project and want to run it manually.

## Part 1: Download The Repository

If you do not already have the repo on your machine:

1. Clone or download the repository.
2. Open a terminal.
3. Change into the repository directory.

Expected result:

- You are now inside the `nexus-v3` project folder.
- You should see files like `README.md`, `server/`, `frontend/`, and `docs/`.

If you are unsure, run:

```bash
pwd
ls
```

Expected result:

- `pwd` shows the repo path.
- `ls` shows the repository contents.

## Part 2: Check The Required Tools

### Option A: Docker path

Check that Docker works:

```bash
docker --version
docker compose version
```

Expected result:

- Both commands print a version number.
- No error about Docker not being installed.

### Option B: Python path

Check that Python works:

```bash
python3 --version
```

Expected result:

- Python 3 is installed.
- The version is recent enough to run the app.

## Part 3: Start The Product

### Recommended: Docker start

From the repo root, run:

```bash
docker compose up --build
```

What this does:

- builds the container if needed
- starts the backend server
- serves the UI
- keeps the process running in the terminal

Expected result:

- The terminal shows the server starting successfully.
- You do not get immediate error messages.
- The app is available in your browser.

### Direct Python start

If you are not using Docker, run:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Expected result:

- Uvicorn starts without errors.
- The server listens on port `7860`.

## Part 4: Open The Browser UI

Open this URL in your browser:

- `http://127.0.0.1:7860/`

Expected result:

- The app loads.
- You land on the operational shell and can immediately move into raw-log intake or queue review.
- You see the top navigation and the incident queue.

If the page does not load:

- confirm the terminal server is still running
- confirm port `7860` is open
- refresh the page
- check the browser console for errors

## Part 5: Understand The Main Navigation

The main UI surfaces are:

- Queue
- Inputs
- Incident
- History
- Replay
- Training
- Settings

Expected result:

- These pages are visible from the product shell.
- The current page is easy to identify.
- The product feels like a real operational application, not a static demo.

## Part 6: Screen-By-Screen Walkthrough

### 6.1 Queue

Open:

- `http://127.0.0.1:7860/`
- `http://127.0.0.1:7860/queue`

What this screen is for:

- It is the main landing surface.
- It shows what needs attention first.
- It gives operators a quick view of incident priority and status.

What to look for:

- incident cards or rows
- incident ID
- service name
- severity
- source
- stage
- age or timing
- clear ordering

Expected behavior:

- The most urgent incident is near the top.
- Each incident looks actionable.
- The queue does not feel like a placeholder.
- Clicking an incident opens that incident in the console.
- The queue is the follow-up surface after raw intake has been normalized.

How to validate:

1. Read the first item in the queue.
2. Confirm it has a clear priority.
3. Open it.
4. Confirm you land in the Incident Console.

If something is wrong:

- queue cards are empty
- incident links do not open
- the page looks like a static mock

That means the queue flow is not healthy.

### 6.2 Inputs

Open:

- `http://127.0.0.1:7860/inputs`

What this screen is for:

- It lets a person paste raw logs or create or simulate new incidents.
- It shows the supported incident intake paths.

The supported intake paths are:

- Raw log paste
- Webhook
- Manual form
- Slack-style command
- Stream anomaly
- Batch import

What to look for:

- a channel selector or clear channel sections
- a raw log paste box
- fields for service, severity, and summary
- submit or create controls
- a result area that shows what happened after submission

Expected behavior:

- the raw-log path is the clearest and most important path on the page
- The screen explains each intake type in plain language.
- A submission creates a new incident.
- The product tells you the incident ID or gives you a link to open it.
- The new incident appears in the queue.

How to validate each intake path:

#### Raw log paste

1. Keep the raw-log paste path selected.
2. The text box starts empty.
3. If you want a sample, click `Load example logs`. Otherwise paste your own incident text.
4. Confirm the parsed evidence preview updates while you type.
5. Click `Submit raw logs`.

Expected result:

- the browser shows the extracted service, severity, and error signature
- the parser accepts arbitrary priority labels such as `P6` or text like `critical`
- the backend creates a new incident
- the result area gives you a link to the incident console
- click the incident console link that appears in the result area
- the incident opens with the same workflow as the other channels
- if the pasted log contains `P4`, the parsed severity should show `P4`
- the live reasoning toggle on Inputs and the incident console can be used to switch live reasoning on or off before opening the incident
- the incident summary shows the proposed fix, priority, normalized rank, and live reasoning state

#### On The Incident Console

1. Open the incident console link returned from Inputs.
2. Read the `Raw Intake` section.
3. Read the `Normalized evidence` section.
4. Read the `SENTINEL -> PRISM -> FORGE -> GUARDIAN` handoff rail.
5. If you want to switch live reasoning after opening the incident, use the `Live reasoning` toggle and let the page update in place.
6. If you see the `Guardian gate`, use `Approve and execute` once, `Block execution` to stop the runbook, or `Request modification` if the runbook needs revision before execution.

What to remember:

- `Normalized evidence` is read-only. It is not a button.
- The agent handoff rail is also read-only. It is there for inspection.
- The live reasoning toggle is the control that changes how the incident is rendered.
- The incident console now exposes explicit `Approve and execute`, `Block execution`, and `Request modification` controls in the `Guardian gate`.
- The incident console now exposes the guardian policy metadata field when a decision is available.
- The console starts with a concise executive summary, not every signal at once.

Expected result:

- you can tell which raw logs were pasted
- you can see the parsed evidence that the backend derived
- you can read the four-agent sequence in order
- you can switch live reasoning on or off and see the incident content update in place
- if you click `Approve and execute`, the incident state updates and the audit trail records it
- if you block execution, the incident stays under review and the audit trail records the block
- you can open `Operational Details` when you want the longer signal, workflow, and audit trace

#### Webhook

1. Choose the webhook path.
2. Fill in the example service and severity.
3. Submit the incident.

Expected result:

- the app accepts the intake
- the incident is created
- you can open it in the console

#### Manual form

1. Choose the manual form path.
2. Enter a simple example such as a billing or API issue.
3. Submit the form.

Expected result:

- the incident is created in the same system as all other intake types
- the queue updates
- the console link works

#### Slack-style command

1. Choose the Slack-style intake path.
2. Enter a sample command or message if the form allows it.
3. Submit it.

Expected result:

- the app treats it like a real intake path
- the incident is normalized into the same incident model

#### Stream anomaly

1. Choose the stream anomaly path.
2. Use the provided sample data or example text.
3. Submit it.

Expected result:

- the app creates an incident or demo incident from the anomaly signal
- the queue reflects the new item

#### Batch import

1. Choose the batch import path.
2. Use the provided import input or sample file workflow if present.
3. Submit it.

Expected result:

- the product accepts the batch path
- the result is a set of incidents or a batch-created incident record

If something is wrong:

- the form does not submit
- the result does not show an incident link
- the queue does not change

That means intake is not working properly.

### 6.3 Incident Console

Open an incident from the queue or from an intake result.

Example URL:

- `http://127.0.0.1:7860/incident?nexus_incident_id=INC001`

What this screen is for:

- It is the main operational view.
- It explains what happened.
- It shows what the agents found.
- It shows what the system knows and what action is possible.

What to look for on the page:

- incident title and ID
- current status
- service name
- severity
- queue position
- ETA
- raw incident text, when present
- normalized evidence derived from the raw text
- the concise incident summary
- the raw intake and normalized evidence
- the Guardian gate and incident action buttons
- the agent cards for `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN`
- the `Operational Details` drawer for signals, workflow, audit, and provenance

Expected behavior:

- The page loads the incident data.
- The workflow timeline is available in the `Operational Details` drawer.
- The agent flow is available in the `Operational Details` drawer.
- The audit trail is available in the `Operational Details` drawer.
- The raw input and normalized evidence are visible on live incidents.
- The evidence section shows where the information came from.
- The execution state is visible and updates when the incident changes.

The page now prefers a backend live-context payload for newly created incidents.
That means a real intake action can feed the console with:

- backend audit history
- workflow timeline state
- live deployment lookups
- evidence provenance assembled server-side

This is the difference between a static demo payload and the current live incident path.

If you started the app with optional OpenAI mode enabled, this same screen will also show live LLM-backed reasoning for the seeded incident path and the raw-log incident path:

- `SENTINEL` uses a live classification call.
- `PRISM` uses a live diagnosis call.
- `FORGE` uses a live runbook-generation call.
- `GUARDIAN` remains deterministic and keeps the safety gate visible.

The four agents should read as a sequential handoff:

1. `SENTINEL` classifies the incident and establishes priority.
2. `PRISM` correlates logs, metrics, and context to diagnose the likely cause.
3. `FORGE` proposes the remediation path or runbook.
4. `GUARDIAN` reviews the proposal and decides whether it can proceed.

How to validate the important parts:

#### Workflow timeline

1. Read the timeline from left to right or top to bottom.
2. Confirm it has multiple steps.
3. Confirm it shows the incident moving through the system.

Expected result:

- The incident life cycle is easy to follow.

#### Agent flow

1. Find the `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN` sections.
2. Watch for the highlight or flow state.
3. Confirm the data flow across the agents is visible.

Expected result:

- You can tell which agent is doing what.
- The flow looks like a real sequential handoff, not random text.

#### Evidence provenance

1. Find the evidence provenance section.
2. Read the listed sources.

Expected result:

- The system explains where evidence came from.
- The user can see the backend assemble provenance from live incident state.
- The incident is not just browser-synthesized text anymore.

#### Live incident context

1. Create a new incident from `Inputs`.
2. Open the incident from the created result link.
3. Confirm the raw input and normalized evidence appear in the console.
4. Compare it with a seeded demo incident such as `INC001`.

Expected result:

- The new incident opens with backend-generated context.
- Audit trail, status, and evidence all align.
- The console still keeps the same look and feel for the demo, but the data path is now live.
- The raw text you pasted is visible in the console.

#### Audit trail

1. Find the audit trail section.
2. Read the entries.

Expected result:

- You can see the history of actions taken on the incident.
- The timeline of decisions is understandable.

#### Execution state

1. Find the execution or response control.
2. If allowed, trigger the execution action.
3. Observe the state change.

Expected result:

- The incident status changes.
- The audit trail updates.
- The UI still remains stable after the change.

If something is wrong:

- the page stays blank
- the agent sections do not show up
- the audit trail never appears
- execution changes do not update anything

That means the incident console flow needs attention.

### 6.4 History

Open:

- `http://127.0.0.1:7860/history`

What this screen is for:

- It shows previous incidents.
- It lets you look back at older cases.
- It demonstrates that the product remembers what happened.

What to look for:

- historical incident rows or cards
- dates or times
- status labels
- links back to the incident console

Expected behavior:

- Older incidents are visible.
- Clicking one opens the same Incident Console experience.
- History does not dead-end the user.

How to validate:

1. Open the page.
2. Scan the rows.
3. Open one historical item.

Expected result:

- You land back in the incident view.
- The experience feels continuous.

### 6.5 Replay

Open:

- `http://127.0.0.1:7860/replay`

What this screen is for:

- It shows replay scenarios.
- It lets you relive or rerun a case.
- It is useful for demos, testing, and learning.

What to look for:

- replay scenario cards or rows
- a launch action
- a visible result after launch

Expected behavior:

- A replay scenario can be selected.
- A launch action creates or opens an incident record.
- The replay action feels like a real product function.

How to validate:

1. Open the page.
2. Select a replay scenario.
3. Launch the replay.
4. Open the result if the app gives you a new incident link.

Expected result:

- A visible incident or replay record is created.
- You can inspect it using the Incident Console.

### 6.6 Training

Open:

- `http://127.0.0.1:7860/training`

What this screen is for:

- It shows how the system is learning.
- It explains reward or training progress in a product-friendly way.

What to look for:

- baseline reward
- trained reward
- episode count
- RL episode contract
- solution proposal
- raw priority and normalized priority rank
- learning-contract count
- improvement or delta
- reward evaluation
- training snapshots
- live incident artifacts if shown
- reward curve bars
- latest episode details
- the incident link inside the episode table

Expected behavior:

- The training story is understandable.
- The screen does not feel like a raw research dump.
- The product makes the learning loop visible.
- The RL episode contract includes the structured result fields and the solution proposal is visible.

How to validate:

1. Open the page.
2. Read the summary metrics.
3. Review the episodes or snapshots.
4. Open the latest episode incident link if you want to see the learning record in the console.

Expected result:

- You can understand whether the system is improving.
- You can point to the latest episode and explain what the agents did.
- You can see how the learning surface connects back to a real incident.

Optional terminal check:

If you want to confirm the same training contract from the terminal, run:

```bash
curl -s http://127.0.0.1:7860/api/v1/training/summary \
  -H 'x-user-id: user-123' \
  -H 'x-tenant-id: tenant-a' \
  -H 'x-roles: operator' \
| python3 -c "import json,sys; p=json.load(sys.stdin); c=p['rl_episode_contract']; e=p['reward_evaluation']; print('reward_curve_final=', e['reward_curve_final']); print('incident_id=', c['observation']['incident_id']); print('guardian_decision=', c['guardian_decision'])"
```

Expected result:

- The command prints the training reward summary.
- The command prints an incident ID from the RL episode contract.
- The command prints the guardian decision.
- The API also exposes the structured result fields used by the browser training view.

### 6.7 Settings

Open:

- `http://127.0.0.1:7860/settings`

What this screen is for:

- It shows the trust and operating posture.
- It shows whether important platform controls are active.

What to look for:

- signature verification state
- replay launch counts
- training snapshot counts
- learning-contract counts
- integration or platform status
- trust-related settings or indicators

Expected behavior:

- The screen tells you whether the system is in a safe or demo-friendly state.
- It does not hide important operational details.

How to validate:

1. Open the page.
2. Check the trust-related indicators.
3. Confirm the values are shown clearly.

Expected result:

- You can tell whether the platform is ready to operate or still in a demo posture.

## Part 7: The Best Full Demo Flow

If you want the simplest good demo, follow this exact path:

1. Open the queue.
2. Open Inputs.
3. Create a new incident using the manual form.
4. Open the returned incident link.
5. Walk through the Incident Console.
6. Show the `SENTINEL -> PRISM -> FORGE -> GUARDIAN` handoff.
7. Show the audit trail and evidence provenance.
8. Trigger execution if the screen allows it.
9. Open History and show the incident is retained.
10. Open Replay and show a replay scenario.
11. Open Training and explain the learning story.
12. Open Settings and show the trust posture.

Expected result:

- The product feels like a real incident-response system.
- The user can see intake, triage, evidence, audit, replay, training, and governance in one flow.

## Part 8: What Good Looks Like

You are in a healthy state if:

- every main page loads
- the queue is the operational follow-up page after intake is normalized
- intake creates incidents
- incidents open in the console
- the workflow timeline is visible
- the agent flow is visible
- the audit trail is visible
- history opens back into the same console
- replay launches something real
- training shows understandable progress
- settings shows trust posture

## Part 8A: Functional Checks

Use this section to verify the product is working, not just rendering.

### Queue

- Open `/queue`.
- Confirm the top incident is first because it has the highest urgency or oldest age.
- Expected result: each row shows incident ID, source, severity, stage, and time.

### Inputs

- Open `/inputs`.
- Submit one manual report and one webhook-style report.
- Expected result: each submission creates or routes to an incident and shows a usable incident link.

### Incident Console

- Open an incident from the queue or Inputs.
- Confirm the concise summary is visible first.
- Open `Operational Details` and confirm the workflow timeline loads.
- Confirm the agent handoff shows `SENTINEL -> PRISM -> FORGE -> GUARDIAN`.
- Confirm the audit trail and evidence provenance are visible inside `Operational Details`.
- Click the execution action if it is available.
- Expected result: the incident updates state, and the audit trail reflects the action.

### History

- Open `/history`.
- Open a historical incident from the list.
- Expected result: it returns to the same incident console experience.

### Replay

- Open `/replay`.
- Launch a replay scenario.
- Expected result: a new incident is created or opened, and the replay path is visible in the console.

### Training

- Open `/training`.
- Confirm the training summary and reward movement are visible.
- Expected result: the training surface explains the learning loop in plain language.

### Settings

- Open `/settings`.
- Confirm the trust posture and runtime configuration are visible.
- Expected result: you can see the platform readiness story without reading code.

## Part 9: What To Do If Something Fails

If a page does not load:

1. Check the terminal where the server is running.
2. Confirm the server is still alive.
3. Refresh the browser page.
4. Check the browser console for JavaScript errors.
5. Try the main queue page again.

If a form does not submit:

1. Check that the required fields are filled in.
2. Try a different intake type.
3. Look for validation messages.
4. Check the server output for API errors.

If an incident page opens but looks empty:

1. Wait a few seconds.
2. Refresh the page once.
3. Re-open the incident from the queue.
4. Check whether the incident ID in the URL is valid.

If replay or training looks wrong:

1. Open the page again.
2. Check whether the supporting backend state exists.
3. Confirm the demo data is available.

## Part 10: Shutdown

When you are done:

1. Go back to the terminal running the server.
2. Stop the process with `Ctrl+C`.

Expected result:

- The server shuts down cleanly.
- The browser will no longer be able to refresh the app until you start it again.

## Short Version

If you only remember one thing, remember this:

1. Start the server.
2. Open the queue.
3. Create an incident from Inputs.
4. Open the incident console.
5. Show the agent flow, evidence, audit, and execution state.
6. Check History, Replay, Training, and Settings.

## Related Docs

- [README.md](../README.md)
- [docs/OPERATIONS.md](OPERATIONS.md)
- [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](NEXUS_v2_DOC_STATUS_MATRIX.md)
- [docs/NEXUS_v2_PRIORITY_BACKLOG.md](NEXUS_v2_PRIORITY_BACKLOG.md)
