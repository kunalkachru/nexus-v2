# NEXUS v2 Demo And Manual Browser Walkthrough

Current as of 2026-05-30.

This is the step-by-step walkthrough for manually validating the product in a browser and for running a credible live demo. It is the practical companion to the README, operations guide, and docs matrix.

## What this walkthrough covers

- Landing and queue experience
- Incident creation from the supported intake surfaces
- Incident Console behavior, evidence, audit, and execution state
- History, replay, training, and settings screens
- Basic validation checks for demo readiness

## Prerequisites

- The app is running locally, usually with `docker compose up --build`.
- You can open `http://127.0.0.1:7860/` in a browser.
- For the full flow, keep the browser console open so you can spot UI errors quickly.

## Suggested Demo Order

Use this order if you want the shortest path to a convincing product demo:

1. Queue
2. Inputs
3. Incident Console
4. History
5. Replay
6. Training
7. Settings

## Full Manual Browser Validation

### 1) Queue

Open:

- `http://127.0.0.1:7860/`
- `http://127.0.0.1:7860/queue`

Check:

- The landing surface is queue-first.
- Incidents show priority, source, severity, stage, and age.
- The top incident is clearly the one that should be handled next.
- Clicking an incident opens the Incident Console.

### 2) Inputs

Open:

- `http://127.0.0.1:7860/inputs`

Validate each intake surface:

- Webhook
- Manual form
- Slack-style command
- Stream anomaly
- Batch import

For each channel:

- Confirm the screen explains what the channel is for.
- Submit a sample incident.
- Confirm the product returns a usable incident link or incident ID.
- Confirm the new incident appears in the queue.

Recommended demo choice:

- Use `Manual form` if you want the clearest operator story.
- Use `Webhook` if you want the most realistic machine-driven intake story.

### 3) Incident Console

Open an incident from the queue or from the intake result.

Example:

- `http://127.0.0.1:7860/incident?nexus_incident_id=INC001`

Check:

- The 9-step workflow timeline renders.
- The agent narrative is visible across `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN`.
- The agent data flow highlights across the stages.
- The evidence provenance section is populated.
- The audit trail is visible and readable.
- Queue position, ETA, and execution state are shown.
- The incident can be opened and refreshed without breaking the state.

For demo purposes, also verify:

- The execution control is visible.
- The audit trail updates after execution or state changes.
- The console feels like a real operator workspace, not a mock screen.

### 4) History

Open:

- `http://127.0.0.1:7860/history`

Check:

- The archive reads as a real operational history.
- Entries open back into the same Incident Console.
- The page communicates that older incidents are still inspectable, not dead-ended.

### 5) Replay

Open:

- `http://127.0.0.1:7860/replay`

Check:

- Replay scenarios are visible and understandable.
- A replay launch action is available.
- The launch path returns or opens a real incident record.
- The replay surface feels like a product feature, not a static catalogue.

### 6) Training

Open:

- `http://127.0.0.1:7860/training`

Check:

- Training summary metrics are visible.
- Reward movement is understandable.
- Episode history is visible.
- The page makes the learning loop legible to product and engineering stakeholders.

### 7) Settings

Open:

- `http://127.0.0.1:7860/settings`

Check:

- Trust posture is visible.
- Signature verification state is visible.
- Replay and training counts are visible.
- The product presents a credible operating posture instead of hiding behind config.

## Quick Validation Checklist

Use this as a final go/no-go checklist before a demo:

- Queue loads without UI errors.
- Inputs can create a new incident.
- The new incident appears in the queue.
- The incident opens in the Incident Console.
- The workflow timeline and agent flow render.
- Audit and evidence sections are present.
- History opens archived incidents back into the console.
- Replay launches a visible scenario.
- Training renders summary and episode state.
- Settings shows trust and platform posture.

## Recommended Manual Demo Script

1. Start on the queue.
2. Create an incident from Inputs.
3. Open the incident and walk the workflow timeline.
4. Highlight evidence provenance and audit trail.
5. Show how execution state is visible.
6. Jump to History to show archived cases.
7. Jump to Replay to show how scenarios can be re-run.
8. End on Training and Settings to show learning and trust posture.

## Notes

- This walkthrough is meant for both product understanding and live demo execution.
- If a screen looks wrong, check the browser console first, then the relevant API response, then the local app logs.
- Keep this doc paired with the README and the operations guide; together they describe the current product, how to run it, and how to validate it manually.
