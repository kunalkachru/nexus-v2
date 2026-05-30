# NEXUS v2 Live Demo Speaker Notes

Current as of 2026-05-30.

These are presentation notes for the main screens and flows in the product.
Use them when you want to explain the product live, screen by screen, without reading the full walkthrough.

## How To Use These Notes

- Start with raw-log intake in Inputs.
- Move through the screens in the order below.
- Keep the language simple and outcome-focused.
- Point to what the user can see, not just what the backend is doing.

## 1) Inputs

### What to say

- “This is where a real incident begins.”
- “A user can paste raw logs, an error message, or a stack trace.”
- “The product normalizes that input before the agents reason about it.”

### What the audience should notice

- The raw-log preview updates as text changes.
- The page makes the intake path obvious.
- The product feels like a real incident front door.

### If asked

- Explain that this is the MVP entrypoint.
- Explain that the system will later apply the same flow to Slack, webhooks, and streams.

## 2) Incident Console

### What to say

- “This is the core operator workspace.”
- “It explains what happened, what the agents found, and what action is possible.”
- “The workflow timeline shows the incident moving through the system.”
- “The agents run in sequence: SENTINEL classifies, PRISM diagnoses, FORGE proposes, and GUARDIAN decides whether execution can proceed.”
- “If live OpenAI mode is enabled, the raw-log path and the seeded demo path both show live reasoning from the same agent chain.”

### What the audience should notice

- The 9-step workflow is visible.
- The sequential agent handoff across `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN` is visible.
- Raw incident text and normalized evidence are visible for live incidents.
- Evidence provenance and audit trail are readable.

### If asked

- Point out queue position and ETA.
- Point out that execution state changes are visible in the console.
- Mention that this is the main place operators spend their time.

## 3) Queue

### What to say

- “This is the operational backlog.”
- “It shows what needs attention first.”
- “Priority, source, severity, and stage are visible immediately.”

### What the audience should notice

- Incidents are clearly ordered.
- The page looks like an operations console, not a dashboard mock-up.

### If asked

- Explain that this is where triage starts after intake.
- Explain that the queue is meant to reduce scanning and guesswork.

## 4) History

### What to say

- “This gives us continuity across incidents.”
- “Older cases still open in the same console experience.”

### What the audience should notice

- History is not a dead archive.
- Past incidents remain inspectable and useful.

### If asked

- Explain that history is for review, audit, and operational memory.

## 5) Replay

### What to say

- “This is how we replay scenarios for validation and learning.”
- “Replay is a product surface, not just a backend test tool.”

### What the audience should notice

- Scenarios are visible and understandable.
- There is a direct action path into a replay run.

### If asked

- Explain that replay helps with demoing, learning, and repeatability.

## 6) Training

### What to say

- “This is the learning loop.”
- “We show reward movement, episode history, and training snapshots.”
- “The page also exposes the RL episode contract so the learning story is visible, not hidden.”
- “There is nothing to click here unless I want to open the latest episode in the incident console.”

### What the audience should notice

- Training is understandable without needing to read source code.
- The screen makes progress visible.
- The latest episode links learning back to a real incident.

### If asked

- Explain that this is where the system gets better from experience.
- Explain that reward evaluation and the episode contract are the parts that later feed the RL loop.

## 7) Settings

### What to say

- “This is the trust and operating posture screen.”
- “It shows signature verification, replay counts, and training snapshots.”

### What the audience should notice

- The product makes its controls visible.
- It does not hide the operational posture.

### If asked

- Explain that settings are there to show readiness and control, not just configuration.

## Closing Message

If you want a short closing line for the whole demo:

- “NEXUS turns incident intake into a visible queue, a traceable console, and a controlled path to action, learning, and review.”

## Related Docs

- [Full walkthrough](DEMO_WALKTHROUGH.md)
- [Quick demo reference](DEMO_CHEAT_SHEET.md)
- [README](../README.md)
- [Operations](OPERATIONS.md)
