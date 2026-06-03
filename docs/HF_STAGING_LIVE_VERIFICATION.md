# HF Staging Live Verification

This checklist is for the Hugging Face staging Space only.

Staging Space page:

- [https://huggingface.co/spaces/kunalkachru23/nexus-staging](https://huggingface.co/spaces/kunalkachru23/nexus-staging)

Staging app URL:

- [https://kunalkachru23-nexus-staging.hf.space](https://kunalkachru23-nexus-staging.hf.space)

If the Space is private, sign in to Hugging Face first before testing the app URL.

## What This Verification Covers

- runtime health
- seeded incident behavior
- fresh triage flow
- BYO-key live reasoning behavior
- Guardian approval flow
- training/runtime linkage
- replay scenario wiring

## 1. Confirm The Space Is Healthy

Open:

- [https://kunalkachru23-nexus-staging.hf.space/health](https://kunalkachru23-nexus-staging.hf.space/health)

Expected:

- the response returns `{"status":"ok"}`

## 2. Confirm Command Center Loads

Open:

- [https://kunalkachru23-nexus-staging.hf.space/queue](https://kunalkachru23-nexus-staging.hf.space/queue)

Expected:

- Command Center loads without a blank screen
- the crew strip shows all four agents
- the main navigation shows:
  - `Command Center`
  - `Incident Detail`
  - `Learning & Controls`

## 3. Verify Seeded Incident Behavior

Open:

- [https://kunalkachru23-nexus-staging.hf.space/incident?nexus_incident_id=INC001](https://kunalkachru23-nexus-staging.hf.space/incident?nexus_incident_id=INC001)

Expected:

- the page loads directly into the settled incident state
- refresh does not replay the full orchestration automatically
- `Replay handoff` is visible as an explicit control
- the top state makes it obvious Guardian has already completed its part
- `Enterprise Task Board` is visible
- `Memory-grounded context` is visible
- `Reliability posture` is visible

## 4. Verify BYO-Key Live Reasoning UX

On the same incident page:

Expected before adding a key:

- `Live reasoning` shows `OFF`
- key status shows no user key attached

Steps:

1. Enter your OpenAI key in the BYO-key field
2. Click `Use this key`

Expected after adding a key:

- `Live reasoning` shows `ON`
- the displayed key is masked
- the full raw key is not shown anywhere in the UI

Optional safety check:

1. Click `Clear key`
2. Confirm the UI returns to deterministic mode

## 5. Run A Fresh Triage End To End

Open:

- [https://kunalkachru23-nexus-staging.hf.space/inputs](https://kunalkachru23-nexus-staging.hf.space/inputs)

Steps:

1. Click `Load example logs`
2. Click `Submit raw logs`

Expected:

- the app redirects to a fresh `nxs_...` incident
- the crew relay progresses through:
  - `SENTINEL`
  - `PRISM`
  - `FORGE`
  - `GUARDIAN`
- Guardian becomes the clear control point
- the runbook explanation is visible

## 6. Verify Guardian Approval

On the new `nxs_...` incident:

Steps:

1. Click `Approve runbook`

Expected:

- Guardian remains the visible active decision owner
- the result banner updates to approval
- execution result becomes visible without needing to hunt for it
- the page clearly indicates the incident moved into execution

## 7. Verify Training / Runtime Linkage

Open:

- [https://kunalkachru23-nexus-staging.hf.space/training](https://kunalkachru23-nexus-staging.hf.space/training)

Expected:

- `Last live triage in this browser` references the same `nxs_...` incident
- the card shows:
  - incident id
  - Guardian decision
  - execution outcome
  - live reasoning state
- `Enterprise runtime summary` is visible
- the navigation pills work:
  - `Learning summary`
  - `Governance summary`
  - `Advanced artifacts`

## 8. Verify Replay Scenario Wiring

Open:

- [https://kunalkachru23-nexus-staging.hf.space/replay](https://kunalkachru23-nexus-staging.hf.space/replay)

Steps:

1. Select `Certificate expiry`
2. Launch the incident

Expected:

- the scenario describes a public TLS outage
- it opens `INC006`
- the incident reads like a certificate-expiry event, not a generic timeout issue

## 9. Final Go / No-Go Checks

The staging deploy is good if all of the following are true:

- `/health` is healthy
- `INC001` is stable on refresh
- fresh triage creates a new incident cleanly
- Guardian approval works cleanly
- training maps the last live run back into the page
- replay opens `INC006`
- BYO-key behavior is masked and request-scoped
