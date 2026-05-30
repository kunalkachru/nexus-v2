# NEXUS v2 Demo Cheat Sheet

Current as of 2026-05-30.

This is the one-page live demo reference. Use the full walkthrough for first-time setup and detailed validation.

## Purpose

- Start the product quickly
- Show the key screens in the right order
- Explain what to expect on each screen
- Keep a live demo moving without losing context

## Start

1. From the repo root, start the app:

```bash
docker compose up --build
```

2. Open the app:

- `http://127.0.0.1:7860/`

Expected:

- The queue loads as the landing page.
- No console errors on first load.

## Demo Order

1. Queue
2. Inputs
3. Incident Console
4. History
5. Replay
6. Training
7. Settings

## Screen Guide

### Queue

- Shows the active incidents.
- Use it to explain priority, severity, source, stage, and age.
- Open the top item.

Expected:

- The queue feels operational.
- Incident links open the console.

### Inputs

- Use this to create a new incident.
- Pick `Manual form` for the simplest story or `Webhook` for the most realistic machine-driven story.
- Submit a sample incident.

Expected:

- A new incident ID or incident link appears.
- The incident shows up in the queue.

### Incident Console

- Main operator view.
- Show the 9-step workflow.
- Highlight the sequential handoff: `SENTINEL -> PRISM -> FORGE -> GUARDIAN`.
- Point out evidence provenance and audit trail.
- Trigger execution if appropriate.

Expected:

- The agent flow is visible.
- The audit trail is readable.
- The status and execution state update when actions happen.

### History

- Shows past incidents.
- Open any row to show that old incidents still land in the same console.

Expected:

- History feels like an archive, not a dead page.

### Replay

- Show a replay scenario.
- Launch it if available.

Expected:

- A visible replay path creates or opens a real incident flow.

### Training

- Show summary metrics, reward movement, and episodes.

Expected:

- The learning story is understandable to a non-engineer.

### Settings

- Show signature verification, replay counts, training snapshots, and trust posture.

Expected:

- The product looks controlled and credible.

## Fast Demo Script

1. Open the queue.
2. Create a manual incident from Inputs.
3. Open the new incident.
4. Show the workflow timeline.
5. Show agent flow and evidence provenance.
6. Show audit trail.
7. Trigger execution if allowed.
8. Jump to History.
9. Jump to Replay.
10. Finish with Training and Settings.

## Quick Checks

- Queue loads first.
- Inputs creates an incident.
- Incident Console renders all main sections.
- History links back into the console.
- Replay is launchable.
- Training shows readable progress.
- Settings shows trust posture.

## If Something Breaks

1. Refresh the page once.
2. Check the browser console.
3. Check the server terminal.
4. Return to the queue and re-open the incident.

## Related Docs

- [Full walkthrough](DEMO_WALKTHROUGH.md)
- [README](../README.md)
- [Operations](OPERATIONS.md)
