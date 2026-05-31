# NEXUS v2 Final Submission Guide

Current as of 2026-05-31.

This is the primary submission document for NEXUS v2.
If you only read one file before running, validating, or presenting the project, read this one.

## What NEXUS v2 Is

NEXUS v2 is an autonomous incident response product prototype built around four agents:

1. `SENTINEL` classifies the incident.
2. `PRISM` diagnoses the likely root cause.
3. `FORGE` proposes the runbook or remediation.
4. `GUARDIAN` acts as the safety and approval gate.

The product is designed to show one clear idea:

- incidents can move through a visible multi-agent workflow
- operators can understand the evidence and reasoning
- the system can learn from episodes over time
- deployment can be public and safe by default

## What Is Actually Shipped

The current repo ships a complete, demo-ready product surface with:

- a FastAPI backend
- a multi-page frontend
- a static training metrics dashboard
- a deterministic-by-default incident workflow
- optional request-scoped live reasoning using a user-supplied OpenAI key
- Docker packaging for Hugging Face Spaces
- automated tests and browser validation

## Public URL

- Hugging Face Space: [https://huggingface.co/spaces/kunalkachru23/nexus](https://huggingface.co/spaces/kunalkachru23/nexus)
- Public app URL: [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)

## Default Runtime Posture

The public deployment is intentionally safe by default:

- the app opens in deterministic demo mode
- no server-side `OPENAI_API_KEY` is required
- no public user can spend the project owner's OpenAI credits
- a user may optionally attach their own OpenAI key from the incident detail screen

When a user attaches their own key:

- the key is stored only in browser session storage
- the key is masked in the UI
- the key is sent only on requests that need it
- the app does not persist the key to disk
- the key is not required for the main demo flow

## Core Product Surfaces

### 1. Command Center

Route:
- `/`
- `/queue`

Purpose:
- show one active incident
- show the four agents as active workers
- keep queue context visible but secondary

### 2. Incident Detail

Route:
- `/incident?nexus_incident_id=INC001`

Purpose:
- show the `SENTINEL -> PRISM -> FORGE -> GUARDIAN` handoff
- show incident reasoning and governance clearly
- keep deeper technical evidence behind disclosure

### 3. Learning & Controls

Route:
- `/training`

Purpose:
- show reward improvement
- show episode progress
- show governance posture
- keep dense training artifacts collapsed by default

### Secondary Routes

These remain available directly but are not primary navigation items:

- `/inputs`
- `/history`
- `/replay`
- `/settings`

## Fastest Demo Path

If you need the shortest good demo:

1. Open `/inputs`
2. Click `Load example logs`
3. Click `Submit raw logs`
4. Let the app redirect into the created incident
5. Show the agent crew and handoff thread
6. Show `GUARDIAN` as the safety gate
7. Click `Approve runbook`
8. Show that execution moves to approved/executed
9. Open `/training`
10. Show the reward curve and learning summary

## Expected Demo Outcomes

### Inputs to Incident

Expected:

- a new `nxs_...` incident is created
- the browser redirects into the incident console
- title, reasoning, and Guardian state are populated

### Queue to Incident

Expected:

- clicking a queue incident opens a populated incident detail page
- incident title is visible
- agent reasoning is visible
- the result banner is visible

### Guardian Action

Expected:

- `Approve runbook` changes the Guardian state to approve
- execution changes to executed
- the incident banner updates accordingly

### Training

Expected:

- the reward curve shows 30 episodes
- the baseline is around `0.28`
- the trained curve reaches `0.65+`

## Local Run Instructions

### Fresh Docker Start

```bash
./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

### Direct Server Start

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Judge Demo Script

```bash
python demo.py
```

Expected:

- runs in under 5 seconds
- prints classification, diagnosis, runbook, execution result, and reward

## Verification Commands

### Full Python Test Suite

```bash
pytest tests/ -v
```

### Browser Verification

```bash
npm run browser:verify
```

### Demo Script

```bash
python demo.py
```

### Local Docker Rebuild

```bash
./scripts/docker_fresh.sh
```

## Manual Execution Steps

Use this section as the exact runbook during submission.

### Option A: Public Hugging Face URL

Use this if you want to validate or present the hosted app:

1. Open [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)
2. Wait for the Command Center to load
3. Confirm the primary nav shows:
   - `Command Center`
   - `Incident Detail`
   - `Learning & Controls`
4. Confirm the page shows all 4 agents:
   - `SENTINEL`
   - `PRISM`
   - `FORGE`
   - `GUARDIAN`
5. Click the first incident in the queue
6. Confirm the incident page shows:
   - populated incident title
   - populated SENTINEL reasoning
   - populated GUARDIAN state
   - `Live reasoning: OFF`
7. Confirm `Bring your own OpenAI key` is visible
8. Open `/inputs`
9. Click `Load example logs`
10. Click `Submit raw logs`
11. Wait for redirect to `/incident?nexus_incident_id=nxs_...`
12. Confirm the created incident shows:
   - populated incident title
   - populated agent reasoning
   - populated Guardian state
13. Click `Approve runbook`
14. Confirm:
   - Guardian changes to approved
   - execution changes to executed
15. Open `/training`
16. Confirm the reward curve is visible and shows 30 episodes

### Option B: Local Docker Execution

Use this if you want the most stable local run:

1. From repo root, run:

```bash
./scripts/docker_fresh.sh
```

2. Wait for:

```text
Fresh container is ready.
```

3. Open [http://127.0.0.1:7860](http://127.0.0.1:7860)
4. Open [http://127.0.0.1:7860/queue](http://127.0.0.1:7860/queue)
5. Click the first incident
6. Confirm:
   - incident title is populated
   - result banner is populated
   - agent reasoning is populated
7. Open [http://127.0.0.1:7860/inputs](http://127.0.0.1:7860/inputs)
8. Click `Load example logs`
9. Click `Submit raw logs`
10. Wait for redirect into `/incident?nexus_incident_id=nxs_...`
11. Confirm the new incident is populated
12. Click `Approve runbook`
13. Confirm Guardian and execution update correctly
14. Open [http://127.0.0.1:7860/training](http://127.0.0.1:7860/training)
15. Confirm the reward curve and learning summary are visible

## Browser Execution Steps

This is the exact browser path I recommend following in order.

### 1. Command Center

Open:

- `/queue`

Check:

- page title reads `Command Center`
- one active incident is the focal point
- all 4 agents are visible above the fold
- queue is visible but secondary

Expected result:

- the page immediately reads like autonomous bots are already working

### 2. Incident Detail From Queue

Action:

- click the first queue incident

Check:

- incident title is populated
- `Agent Handoff Thread` is visible
- `SENTINEL handed evidence to PRISM` is visible
- `Governance Bot` is visible
- `Live reasoning: OFF` is visible by default

Expected result:

- the incident console feels populated and active, not empty

### 3. BYO Key Panel

Check:

- `Bring your own OpenAI key` is visible
- no key is shown in plain text by default
- default message indicates deterministic mode

Optional action:

- paste a valid-looking OpenAI key
- click `Use this key`

Expected result:

- the key is masked in the UI
- the full secret is never displayed

### 4. Inputs Flow

Open:

- `/inputs`

Action:

- click `Load example logs`
- click `Submit raw logs`

Check:

- redirect lands on `/incident?nexus_incident_id=nxs_...`
- incident title is populated
- SENTINEL reasoning is populated
- GUARDIAN state is populated

Expected result:

- raw logs become a real incident, not a dead-end input form

### 5. Guardian Approval

Action:

- click `Approve runbook`

Check:

- Guardian changes to approve
- execution changes to executed
- incident banner updates

Expected result:

- the governance gate visibly controls the execution state

### 6. Learning & Controls

Open:

- `/training`

Check:

- page title reads `Learning & Controls`
- reward curve is visible
- 30 episodes are visible
- governance summary is visible
- advanced artifacts are collapsed by default

Expected result:

- the learning story is visible without opening dense detail

## Browser Validation Checklist

Before submission, verify these flows:

1. `/queue` loads and shows the Command Center
2. clicking the first queue incident opens a populated incident page
3. `/inputs` creates a new incident and redirects correctly
4. `Approve runbook` changes Guardian and execution state
5. `/training` shows the reward curve and learning summary
6. `Bring your own OpenAI key` is visible in Incident Detail
7. the default live-reasoning state is `OFF`

Detailed checklists:

- [docs/BROWSER_VERIFICATION_CHECKLIST.md](BROWSER_VERIFICATION_CHECKLIST.md)
- [docs/VERIFICATION_PASS_FAIL_CHECKLIST.md](VERIFICATION_PASS_FAIL_CHECKLIST.md)

## Source Of Truth

Use these files as the current implementation source of truth:

- [README.md](../README.md)
- [docs/FINAL_SUBMISSION_GUIDE.md](FINAL_SUBMISSION_GUIDE.md)
- [docs/DEMO_CHEAT_SHEET.md](DEMO_CHEAT_SHEET.md)
- [docs/OPERATIONS.md](OPERATIONS.md)

## Design Docs Note

The latest branch intentionally removes the older long-form planning and enterprise vision documents from the visible repo surface.

Use:

- [design-docs/README.md](../design-docs/README.md)

for the current note on that cleanup.
