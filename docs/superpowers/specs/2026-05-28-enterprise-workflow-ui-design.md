# Enterprise Workflow UI Design

> Design reference for the UI-first phase. Current implementation status and remaining gaps are tracked in [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](../../NEXUS_v2_DOC_STATUS_MATRIX.md) and [docs/NEXUS_v2_PRIORITY_BACKLOG.md](../../NEXUS_v2_PRIORITY_BACKLOG.md).

## Goal

Turn the current single-page deterministic dashboard into a multi-page enterprise web app that shows how incidents enter NEXUS, how each agent contributes to diagnosis and remediation, and how the RL system learns from each episode.

## Source Context

This design consolidates the current Phase 2 implementation with:

- `design-docs/NEXUS_v2_Design_Document.md`
- `design-docs/NEXUS_v2_Master_Product_Document.md`
- `/Users/kunalkachru/Downloads/NEXUS_v2_ENTERPRISE_SPECIFICATION.md`

## Product Positioning

The app should look and behave like an enterprise operator console, not a hackathon dashboard. The opening experience should emphasize operational value first, then system flexibility, then RL depth.

The web app navigation order is:

1. `Queue`
2. `Incident Console`
3. `Input Channels`
4. `History`
5. `Sample Replay`
6. `RL Training Lab`
7. `Settings`

The system workflow still begins with incident intake. The distinction is intentional:

- `System workflow`: intake -> validation -> enrichment -> evidence -> agents -> safety -> outcome -> learning
- `User workflow`: open queue -> inspect incident -> drill into source and evidence -> review solution -> understand learning

## Primary User Experience

### Queue

This is the default landing page. It shows all active incidents, severity, source channel, current workflow stage, SLA timer, and the latest agent activity.

### Incident Console

This is the main product page. It shows one incident progressing through a visible pipeline, with evidence, agent contributions, proposed actions, and audit history.

### Input Channels

This is the third page, not the landing page. It explains and simulates all supported intake modes:

- alert webhooks
- manual incident reports
- Slack-style reporting
- continuous stream anomaly detection
- batch import

### History

This page shows closed incidents, filterable by service, severity, outcome, source channel, and time window. It also supports drilling into the same incident console for past incidents.

### Sample Replay

This page exposes curated incidents that can be replayed end to end through the same APIs and UI as live incidents.

### RL Training Lab

This page explains how the agents learn. It shows the reward curve, episode history, trajectory records, observation states, and per-agent contribution to reward.

### Settings

This page contains integration health, environment configuration, policy status, and demo-mode settings.

## Workflow Model

The app should use one canonical incident workflow with nine visible states:

1. `incident_received`
2. `validated_authenticated`
3. `enriched_with_service_context`
4. `evidence_retrieved`
5. `sentinel_classified`
6. `prism_diagnosed`
7. `forge_proposed_runbook`
8. `guardian_reviewed_safety`
9. `executed_verified_learned`

Each state should have:

- timestamp
- actor or system owner
- summary label
- detailed payload
- status (`pending`, `in_progress`, `completed`, `blocked`, `failed`)
- linked evidence

This model drives the timeline in the Incident Console, the queue stage badges, the replay progress view, and the RL episode mapping.

## Agent Contribution Model

Each agent must render as a contribution block instead of a generic card.

### SENTINEL contribution

- what is broken
- severity
- blast radius
- confidence
- alternatives considered
- immediate risks

### PRISM contribution

- why it is broken
- evidence used
- rejected hypotheses
- diagnostic confidence
- query budget used

### FORGE contribution

- proposed remediation
- candidate fixes
- selected runbook
- prerequisites
- rollback
- validation check

### GUARDIAN contribution

- approval or rejection
- safety score
- approval type
- risk flags
- rollback readiness
- reasoning

## Input Channel Model

All intake modes must map into one normalized incident trigger so the rest of the system behaves consistently.

Supported channels for the first full revamp:

- `webhook`
- `manual_form`
- `slack_command`
- `stream_anomaly`
- `batch_import`

The UI should present the differences in source payload and auth model, but the backend should emit a single incident envelope with:

- incident ID
- source channel
- external source metadata
- affected service
- severity
- initial symptoms
- evidence lookup hints

## Sample Replay Model

Sample incidents are first-class incidents, not mock-only screens. They should be loaded through the same incident APIs and render inside the same Incident Console.

Initial replay set:

- API timeout cascade
- DB connection pool exhaustion
- Redis saturation
- memory leak after deploy
- queue backlog and worker stall
- bad deployment regression
- certificate expiry
- cache explosion

Each replay scenario must include:

- source payload
- enriched service metadata
- metrics
- logs
- traces or trace summaries
- deployment events
- similar historical incidents
- agent outputs
- guardian outcome
- execution or blocked result
- reward breakdown for the learned episode

## RL Training Lab Model

The current trainer already uses a deterministic five-dimensional reward:

- `mttr`
- `diagnosis`
- `customer`
- `coordination`
- `oversight`
- plus `severity_penalty`

The UI should keep that reward model as the source of truth. The new visibility layer should map it onto the nine workflow observation states so users can understand how an operational episode becomes a training trajectory.

The RL Training Lab should show:

- baseline reward vs trained reward
- reward curve over episodes
- cost curve
- difficulty progression
- episode table
- per-agent trajectory steps
- observation digest per step
- reward component breakdown
- mapping from workflow state to training signal

## Frontend Architecture

Keep the frontend build-free for this phase, but make it feel like a real product. Use static HTML pages with shared JavaScript modules and shared CSS tokens served by FastAPI.

Recommended page files:

- `frontend/queue.html`
- `frontend/incident.html`
- `frontend/inputs.html`
- `frontend/history.html`
- `frontend/replay.html`
- `frontend/training.html`
- `frontend/settings.html`

Recommended shared assets:

- `frontend/static/app-shell.css`
- `frontend/static/app-shell.js`
- `frontend/static/client.js`
- `frontend/static/formatters.js`
- page-specific modules for each page

## Backend Architecture

The backend should move away from a single `server/app.py` page-plus-payload assembly model and split into route modules and service modules.

Recommended route groups:

- pages
- incidents
- inputs
- replay
- training
- settings

Recommended service responsibilities:

- workflow service for incident state transitions
- replay service for curated scenarios
- training lab service for metrics and trajectories
- incident service for queue, detail, and history APIs

## Containerization And Ops

The container should boot with deterministic demo assets available by default:

- training metrics payload
- sample replay incidents
- static pages

The app should support:

- local demo mode
- docker compose product-demo mode
- Kubernetes manifests for the same surface area

## Success Criteria

- landing page is the incident queue, not the old dashboard
- Incident Console clearly shows intake as the first workflow step
- Input Channels is the third page and can launch or simulate incidents
- Sample Replay can run curated incidents end to end through the same UI
- RL Training Lab explains learning without contradicting the real reward model
- all pages are served by FastAPI and covered by route and API tests
- the container boots with replay data and training data available
