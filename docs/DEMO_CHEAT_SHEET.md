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

1. Inputs
2. Incident Console
3. Queue
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

- Use this to paste raw logs or create a new incident.
- Start with the raw-log paste path for the MVP story.
- Pick `Manual form` for the simplest alternate story or `Webhook` for the most realistic machine-driven story.
- Submit a sample incident and open the resulting console link.

Expected:

- The raw-log preview updates as you edit text.
- A new incident ID or incident link appears.
- The incident shows up in the queue.

### Incident Console

- Main operator view.
- Show the 9-step workflow.
- Show the raw incident text and normalized evidence for live incidents.
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

- Show summary metrics, reward movement, the RL episode contract, and the latest episode link.
- Point to the reward evaluation and say that the system is turning incidents into a structured learning record.
- Open the latest episode incident if you want to connect training back to the console.

Expected:

- The learning story is understandable to a non-engineer.
- The audience can see how reward and episodes connect to a real incident.

### Settings

- Show signature verification, replay counts, training snapshots, and trust posture.

Expected:

- The product looks controlled and credible.

## Fast Demo Script

1. Open Inputs.
2. Paste raw logs and submit the incident.
3. Open the new incident.
4. Show the workflow timeline.
5. Show raw incident text, normalized evidence, agent flow, and evidence provenance.
6. Show audit trail.
7. Trigger execution if allowed.
8. Jump to Queue.
9. Jump to History.
10. Jump to Replay.
11. Finish with Training and Settings.

## Quick Checks

- Inputs creates an incident and shows the parsed preview.
- Incident Console renders all main sections and raw intake evidence.
- Queue loads and shows the new incident.
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
