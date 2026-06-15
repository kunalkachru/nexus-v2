# NEXUS Browser Verification Checklist

Use this checklist to verify the current operator-facing product in a browser.

## Setup

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Wait for the app to be available on:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

Optional automated check:

```bash
npm run browser:verify
```

## Global Checks

- The primary nav shows `Command Center`, `Incident Detail`, and `Learning & Controls`
- Supporting routes still exist for `Inputs`, `History`, `Replay`, and `Settings`
- The product reads like one investigation workflow, not disconnected utilities

## Command Center

Open:

- [http://127.0.0.1:7860/queue](http://127.0.0.1:7860/queue)

Confirm:

- the page reads as a command center
- one live incident is the focal point
- the crew strip is readable above the fold
- Guardian is visible as a governed endpoint, not just another summary card

## Incident Detail

Open:

- [http://127.0.0.1:7860/incident?nexus_incident_id=INC001](http://127.0.0.1:7860/incident?nexus_incident_id=INC001)

Confirm:

- the page title reads `Incident Detail`
- `Bring your own OpenAI key` is visible
- `Investigation Summary & Operator Path` is visible
- `Enterprise Task Board` is visible
- REPLICA replay capability and host fields are visible
- TRACE replay/debugger evidence is visible
- Guardian actions are present and clearly gated

After scrolling, confirm:

- memory-grounded context appears
- reliability posture appears
- fallback and retries appear
- execution outcome appears after approval

## Inputs

Open:

- [http://127.0.0.1:7860/inputs](http://127.0.0.1:7860/inputs)

Confirm:

- example logs load
- raw log submission creates a fresh `nxs_...` incident
- the incident page is populated on redirect

## Training

Open:

- [http://127.0.0.1:7860/training](http://127.0.0.1:7860/training)

Confirm:

- the page title reads `Learning & Controls`
- `Pilot scorecard dashboard` is visible
- runtime host and pack coverage surfaces are visible
- latest live triage is visible after a fresh run
- product health / governance posture is visible

## Final Pass

The verification passes if:

- the UI reads like a premium support investigation workspace
- supported versus unsupported behavior is visible
- runtime-backed versus inference-first posture is clear
- fresh and seeded incident flows both feel coherent
