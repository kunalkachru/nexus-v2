# NEXUS Browser Verification Checklist

Use this checklist to verify the new agent-first UI in a browser.

## Goal

Confirm that the product no longer feels like a cluttered dashboard and now reads as an autonomous AI crew coordinating around one live incident.

## Setup

1. Start the fresh Dockerized app:

```bash
./scripts/docker_fresh.sh
```

2. Wait for:

```text
Fresh container is ready.
```

3. Open:

```text
http://127.0.0.1:7860/
```

4. Optional automated browser check:

```bash
npm run browser:verify
```

## Global Checks

- The top navigation shows only 3 primary screens:
  - `Command Center`
  - `Incident Detail`
  - `Learning & Controls`
- `Inputs`, `History`, `Replay`, and `Settings` are not primary nav items.
- The shell feels lighter than before and does not open with large KPI walls or dense tables.

## Command Center

Open:

```text
http://127.0.0.1:7860/queue
```

Confirm:

- The page headline reads as a command center, not a queue-heavy dashboard.
- One live incident is the focal point.
- `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN` are all visible above the fold.
- Each bot shows:
  - identity
  - role
  - current task
  - next handoff
- The compact queue rail is visible but secondary to the active agent crew.
- Deep queue metadata is hidden behind `Expand queue internals`.
- Contextual links to `History` and `Replay` are present.

Pass criteria:

- First impression feels like “AI agents are already working.”

## Incident Detail

Open:

```text
http://127.0.0.1:7860/incident?nexus_incident_id=INC001
```

Confirm:

- The page title and shell say `Incident Detail`.
- The page leads with a bot-first collaboration view, not a dense evidence wall.
- The default live-reasoning state is `OFF`, so the public app opens in deterministic demo mode.
- `Agent Handoff Thread` is visible.
- The thread clearly communicates agent-to-agent collaboration.
- `SENTINEL handed evidence to PRISM` is visible.
- `Governance Bot` is visible and clearly mapped to `GUARDIAN`.
- `Bring your own OpenAI key` is visible near the top of the control rail.
- Adding a valid-looking key masks it in the UI and does not display the full secret.
- Guardian controls are visible but subordinate to the collaboration story.
- `Working memory` is visible near the top.
- Technical details are hidden behind `Expand technical detail`.

After expanding technical detail, confirm:

- source payload is available
- normalized evidence is available
- system evidence is available
- workflow internals are available
- audit ledger is available

Pass criteria:

- The page feels like watching autonomous specialists coordinate on one incident.

## Learning & Controls

Open:

```text
http://127.0.0.1:7860/training
```

Confirm:

- The page title and shell say `Learning & Controls`.
- The top area explains learning progress quickly.
- `Learning tab`, `Governance tab`, and `Advanced Artifacts` are visible.
- The reward curve is visible without opening deep artifacts.
- Agent improvement is visible without opening deep artifacts.
- Governance summary is visible without opening deep artifacts.
- `Settings` content is represented through governance/control posture rather than a separate primary page.
- Deep RL records are hidden behind `Advanced Artifacts`.

Pass criteria:

- The page communicates learning and governance fast, without opening with tables or raw RL structures.

## Advanced Routes

Open directly:

- `/inputs`
- `/history`
- `/replay`
- `/settings`

Confirm:

- Each route still loads.
- The primary nav still shows only the 3 core screens.
- These routes feel secondary and compatible, not like competing top-level destinations.

## Critical Submission Flow

Run this exact flow before submission:

1. Open `/queue`
2. Click the first queue incident
3. Confirm incident title, agent reasoning, and result banner are populated
4. Open `/inputs`
5. Click `Load example logs`
6. Click `Submit raw logs`
7. Confirm the app redirects to `/incident?nexus_incident_id=nxs_...`
8. Confirm the incident title and agent reasoning are populated immediately
9. Click `Approve runbook`
10. Confirm Guardian changes to approved and execution changes to executed

Pass criteria:

- no `Incident unavailable`
- no `Waiting for incident context.`
- no blank incident summary after queue click or raw-log submit

## Final Pass

The redesign passes browser verification if:

- the UI feels less cluttered by default
- the 4 agents read as autonomous bots working together
- one live incident anchors the experience
- only 3 screens are primary
- dense data is hidden behind progressive disclosure
