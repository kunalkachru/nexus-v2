# NEXUS v2 Live Demo Speaker Notes

Current as of 2026-05-30.

These are presentation notes for the main screens and flows in the product.
Use them when you want to explain the product live, screen by screen, without reading the full walkthrough.

## How To Use These Notes

- Start at the queue.
- Move through the screens in the order below.
- Keep the language simple and outcome-focused.
- Point to what the user can see, not just what the backend is doing.

## 1) Queue

### What to say

- “This is the main operational entry point.”
- “The queue shows what needs attention first.”
- “Priority, source, severity, and stage are visible immediately.”

### What the audience should notice

- The landing page is queue-first.
- Incidents are clearly ordered.
- The page looks like an operations console, not a dashboard mock-up.

### If asked

- Explain that this is where triage begins.
- Explain that the queue is meant to reduce scanning and guesswork.

## 2) Inputs

### What to say

- “This is how incidents enter the system.”
- “We support webhook, manual, chat-style, stream, and batch intake.”
- “Every path lands in the same incident model.”

### What the audience should notice

- The product is not limited to one kind of input.
- The intake screen feels like a real operational front door.

### If asked

- Use manual form for the easiest live demo.
- Use webhook if you want to emphasize machine-driven incident creation.

## 3) Incident Console

### What to say

- “This is the core operator workspace.”
- “It explains what happened, what the agents found, and what action is possible.”
- “The workflow timeline shows the incident moving through the system.”

### What the audience should notice

- The 9-step workflow is visible.
- The agent handoff across `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN` is visible.
- Evidence provenance and audit trail are readable.

### If asked

- Point out queue position and ETA.
- Point out that execution state changes are visible in the console.
- Mention that this is the main place operators spend their time.

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

### What the audience should notice

- Training is understandable without needing to read source code.
- The screen makes progress visible.

### If asked

- Explain that this is where the system gets better from experience.

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
