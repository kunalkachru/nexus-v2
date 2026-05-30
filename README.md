---
title: NEXUS v2
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_file: server/app.py
pinned: false
---

# NEXUS v2

NEXUS v2 is an enterprise incident-response product that turns noisy alerts into a queue-first operator workflow, an explainable incident console, and a controlled path from intake to resolution.

Current phase:
- UI-first roadmap: complete
- Thin backend demo layer: complete
- Production hardening / live integrations: next

The current source of truth for scope and status is:
- [Documentation status matrix](docs/NEXUS_v2_DOC_STATUS_MATRIX.md)
- [Priority backlog](docs/NEXUS_v2_PRIORITY_BACKLOG.md)
- [Operations guide](docs/OPERATIONS.md)

## Who this is for

- Business and leadership: see the market problem, product thesis, and operating model.
- Product: see the user journeys, product surfaces, and phased roadmap.
- Engineering: see the current architecture, contracts, and test strategy.
- Triage and ops: see the queue, incident console, audit trail, and recovery posture.
- Customers: see how incidents are handled, explained, and reviewed.
- Tier-1 / Tier-2 / Tier-3 support: see how intake, diagnosis, and policy gates map to responsibility.

## What problem it solves

Teams lose time when incident intake is fragmented across webhooks, forms, chat commands, log streams, and spreadsheets. The result is slower triage, unclear ownership, weak auditability, and a poor story for business stakeholders who need to understand impact.

NEXUS v2 solves that by making the queue the primary surface, normalizing every intake path into the same incident object, and showing the evidence, decisions, and actions in one place.

## Our solution

The product combines:
- A queue-first landing page for active incidents.
- An incident console with workflow stages, evidence provenance, audit history, and execution state.
- Multiple intake channels that normalize into the same backend contract.
- Replay and training surfaces that explain how incidents are replayed, learned from, and measured.
- A settings and trust surface that makes the system posture visible instead of hiding it in config.

## Product

The main user journeys are:

1. Intake an incident from webhook, manual form, Slack-style command, stream anomaly, or batch import.
2. Land it in the queue with visible priority, stage, and age.
3. Open the incident console to inspect timeline, evidence, agent analysis, audit trail, and execution status.
4. Replay a scenario or inspect training output to understand how the system learns.
5. Review settings and trust posture before expanding into production usage.

The current UI is intentionally enterprise-shaped so it feels credible in front of users, operators, and reviewers even before every backend integration is fully live.

## Business angle

| Stakeholder | Why it matters |
|---|---|
| Business / leadership | Shows a believable enterprise product story, auditability, and visible control over incident handling. |
| Product | Provides a coherent shell, clear user journeys, and a roadmap that can be shipped in phases. |
| Development | Gives stable contracts, defined surfaces, and testable features instead of an amorphous prototype. |
| Engineering | Reduces integration risk by keeping the UX, API seams, and persistence story explicit. |
| Triage / ops | Makes the queue, incident state, audit trail, and execution gate easy to inspect during real incident work. |
| Customers | Improves confidence by making status, evidence, and resolution paths visible. |
| Tier-1 / Tier-2 / Tier-3 support | Tier-1 gets intake and prioritization, Tier-2 gets diagnosis and evidence, Tier-3 gets policy and execution context. |

## Functional design

### Queue

- Default landing page.
- Shows incident priority, source, severity, stage, and timing.
- Makes it obvious why the next incident is first.

### Incident console

- Shows the 9-step workflow.
- Surfaces SENTINEL, PRISM, FORGE, and GUARDIAN contributions.
- Includes audit trail, evidence provenance, queue position, ETA, and execution state.

### Input channels

- Webhook
- Manual form
- Slack-style command
- Stream anomaly
- Batch import

Every intake path lands in the same incident model so the downstream queue and console stay consistent.

### History

- Presents a historical archive.
- Links historical incidents back into the same console experience.

### Replay

- Launches replay scenarios into the same incident workflow.
- Keeps replay visible as a product surface rather than a hidden backend operation.

### Training

- Shows training summaries, episode history, and reward movement.
- Connects the training story to live incident artifacts where possible.

### Settings

- Surfaces trust posture, contract surface, replay/training counts, and signature verification state.

## Technical design

The application is a FastAPI-backed product shell with a static frontend and explicit API seams.

Key implementation layers:
- `server/app.py` wires the routes.
- `server/services/` holds incident, observability, surface-payload, and tenancy logic.
- `server/models.py` defines the current request/response schema.
- `server/repositories.py`, `server/db.py`, `server/audit.py`, and `server/artifacts.py` handle persisted state.
- `frontend/` contains the product pages.
- `frontend/static/` contains the shell, page controllers, and shared styles.

Data flow at a high level:
1. Intake arrives through a supported channel.
2. The backend normalizes the payload into an incident envelope.
3. Incident state, audit entries, and artifacts are persisted.
4. The queue and console read the same incident record.
5. Replay and training surfaces read the same artifact history.

## Architecture

Current architecture, in practical terms:
- FastAPI app serving both HTML pages and JSON contracts.
- Queue-first UI with a shared shell and page-specific controllers.
- File-backed local persistence for incidents, audit logs, and artifacts.
- Versioned API contracts for the most visible product actions.
- Security and tenancy checks on authenticated paths.
- Signature verification for webhook intake.

The broader production hardening target, which is still only partially complete, is tracked in the docs matrix and backlog.

## Setup

### Local product mode

```bash
docker compose up --build
```

Open:
- `http://127.0.0.1:7860/`
- `http://127.0.0.1:7860/queue`
- `http://127.0.0.1:7860/incident?nexus_incident_id=INC001`

### Direct server mode

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Useful runtime settings

The current demo-friendly defaults live in `server/config.py`:
- `database_path`
- `webhook_signing_secret`
- `allowed_tenant_ids`

## Testing and automation

Run the full automated suite:

```bash
pytest -q
```

Recommended focused checks:

```bash
pytest -q tests/test_api_contract.py tests/test_app.py tests/test_security.py tests/test_observability.py tests/test_deployment.py
```

Browser validation targets:
- `/`
- `/queue`
- `/incident?nexus_incident_id=INC001`
- `/inputs`
- `/history`
- `/replay`
- `/training`
- `/settings`

The current repo is considered ready when the suite is green and the browser pages load without console errors in the main demo flow.

For a full screen-by-screen manual validation and demo script, see [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md).
For a quick live demo reference, see [docs/DEMO_CHEAT_SHEET.md](docs/DEMO_CHEAT_SHEET.md).
For live presentation notes by screen, see [docs/LIVE_DEMO_SPEAKER_NOTES.md](docs/LIVE_DEMO_SPEAKER_NOTES.md).

## Roadmap

Current roadmap alignment:
- [UI-first roadmap](docs/superpowers/specs/2026-05-29-enterprise-ui-product-roadmap.md)
- [Phase 2 roadmap](docs/NEXUS_v2_PHASE2_ROADMAP.md)
- [Enterprise specification](design-docs/NEXUS_v2_ENTERPRISE_SPECIFICATION.md)

If you want the shortest path to the next phase of product hardening, start with the [priority backlog](docs/NEXUS_v2_PRIORITY_BACKLOG.md).

## Documentation map

### Current source of truth

- [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](docs/NEXUS_v2_DOC_STATUS_MATRIX.md)
- [docs/NEXUS_v2_PRIORITY_BACKLOG.md](docs/NEXUS_v2_PRIORITY_BACKLOG.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)
- [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md)
- [docs/DEMO_CHEAT_SHEET.md](docs/DEMO_CHEAT_SHEET.md)
- [docs/LIVE_DEMO_SPEAKER_NOTES.md](docs/LIVE_DEMO_SPEAKER_NOTES.md)
