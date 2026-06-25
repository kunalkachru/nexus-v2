# Operations

Current as of 2026-06-15.

This document describes how the current NEXUS product operates and what the bounded runtime claims actually mean.

## Runtime Posture

NEXUS is:

- deterministic by default
- public-safe by default
- optionally able to use request-scoped live reasoning when a user supplies a valid OpenAI key
- built around a six-stage support-to-engineering workflow

Visible workflow:

- `SENTINEL`
- `PRISM`
- `REPLICA`
- `TRACE`
- `FORGE`
- `GUARDIAN`

Important boundary:

- `REPLICA` is a bounded replay layer for curated packs
- `TRACE` is a bounded debugging and handoff layer, not a universal live debugger

## Deployment Modes

### Public demo mode

- deterministic by default
- no server-side OpenAI key required
- runtime replay remains bounded and availability-dependent

### Local development mode

Preferred startup:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Direct server path:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Pilot mode

- tenant-aware ownership and repo mappings
- downstream delivery targets
- approval policy and role controls
- runtime-host relay where replay validation is expected

## Oracle Cloud Manual Restart Commands

### With Live Reasoning ON (gpt-4o)

```bash
source /Users/kunalkachru/Documents/nexus-v3/.env && ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239 "sudo docker stop nexus && sudo docker rm nexus && sudo docker run -d --name nexus --restart always -p 7860:7860 -e APP_ENV=production -e NEXUS_USE_OPENAI=1 -e NEXUS_FORGE_MODEL_NAME=gpt-4o -e OPENAI_API_KEY=$OPENAI_API_KEY -e NEXUS_DATABASE_PATH=/app/artifacts/incidents.json -e NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system -e NEXUS_WEBHOOK_SIGNING_SECRET=demo-secret -v nexus-data:/app/artifacts nexus"
```

### With Live Reasoning OFF (Inference Only)

```bash
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239 "sudo docker stop nexus && sudo docker rm nexus && sudo docker run -d --name nexus --restart always -p 7860:7860 -e APP_ENV=production -e NEXUS_USE_OPENAI=0 -e NEXUS_FORGE_MODEL_NAME=gpt-4o -e NEXUS_DATABASE_PATH=/app/artifacts/incidents.json -e NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system -e NEXUS_WEBHOOK_SIGNING_SECRET=demo-secret -v nexus-data:/app/artifacts nexus"
```

### Prerequisites

- `.env` file must exist at `/Users/kunalkachru/Documents/nexus-v3/.env` with `OPENAI_API_KEY=sk-...` (required only for live reasoning ON)
- SSH key must be available at `~/Downloads/ssh-key-2026-06-19.key`

### Verification

After restart, verify the container is healthy:

```bash
curl -s https://nexus-triage.duckdns.org/health
```

Expected response: `{"status":"healthy"}` with HTTP 200

### Important Notes

- **Auto-deploy via GitHub Actions always runs with `NEXUS_USE_OPENAI=0`** — live reasoning must be enabled manually using the "With Live Reasoning ON" command above
- **Public URL:** `https://nexus-triage.duckdns.org`
- **Oracle Cloud IP:** `92.5.47.239`
- The `source .env` in the ON command runs locally on Mac and expands `$OPENAI_API_KEY` before SSH transmission — the variable is not evaluated on the remote server

## Supported Bounded Families

Current baseline support:

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike
4. `INC005` queue / worker backlog affecting transaction completion
5. `INC007` auth dependency slowdown / token validation failures

## Runtime Host And Replay Truth

NEXUS can run bounded replay in two ways:

1. directly on the current host when Docker is available
2. by delegating to the packaged runtime host when `ENABLE_RUNTIME_HOST_RELAY=1` is enabled

Operators should rely on the product’s runtime posture labels:

- runtime-backed
- inference-first
- unsupported

Do not treat inference-first reasoning as replay validation.

## Runtime Queue Durability and Recovery

NEXUS persists the state of all runtime replay jobs so they survive app restarts and connection failures.

### Queue Job States

Each replay job transitions through these states:

- `queued`: The job was requested and is waiting to run.
- `running`: The job is actively executing.
- `completed`: The job finished without errors.
- `recovered`: The job ran successfully (synonym for completed when tracking recovery).
- `retrying`: The job failed and is being retried; check error_message.
- `failed`: The job failed permanently; see error details.
- `abandoned`: The job was abandoned (e.g., due to app restart during execution).

### Recovery Posture

The product reports overall runtime queue recovery status:

- `healthy`: No active jobs; all jobs have completed or been recovered.
- `recovering`: Some jobs were lost during an app restart but were recovered by replaying the request.
- `degraded`: Some jobs remain active or failed and require operator attention.

### Viewing Queue State

Operators can monitor runtime queue state in **Settings > Runtime Queue Recovery**:

- Recovery status shows the overall health of the queue
- Active jobs tracks in-flight work
- Recovered jobs counts successful recoveries from restart boundaries
- Failed jobs tracks permanent failures

When an incident is loaded, its queue state appears in the incident context, showing:

- Whether the incident has queue history
- The latest job state and outcome
- Total attempts and retry count
- Error messages if applicable

### Incident-Specific Queue State

Each incident displays its replay job lifecycle:

- `has_queue_history`: Whether the incident has any recorded jobs
- `current_state`: The most recent job state (queued, running, recovered, failed, etc.)
- `total_attempts`: How many replay jobs have been attempted
- `message`: Operator-friendly summary of the current state

The UI keeps the queue state visible so operators understand whether a replay succeeded, is still running, or needs retry.

## Pilot-Safe Observability Surface

NEXUS exposes a bounded operator-facing observability surface through:

- `GET /api/v1/observability/health`
- the `Learning & Controls` page
- the `Settings` page

This surface is intentionally not a generic monitoring system. It exists to answer four bounded operator questions:

1. Is replay healthy enough for bounded runtime validation?
2. Are downstream delivery targets healthy enough for handoff?
3. Is the runtime queue healthy enough to trust recent replay state?
4. Is memory available enough to claim historical grounding?

### Pilot-Critical Subsystems

The product currently summarizes these pilot-critical subsystems:

- `replay`
- `delivery`
- `runtime queue`
- `memory`

Each subsystem is rendered with:

- `raw_status`
- `posture`
- `label`
- `summary`
- `guidance`
- `next_checks`

### Posture Vocabulary

Operator posture is normalized into exactly three values:

- `healthy` — safe to use inside the current bounded pilot workflow
- `partial` — degraded but still partially usable; operator review required
- `unavailable` — do not treat the subsystem as usable for the claimed workflow

This vocabulary is intentionally stricter than generic “green/yellow/red” monitoring because it maps directly to product truth:

- if replay is unavailable, do not claim runtime-backed validation
- if memory is unavailable, treat reasoning as inference-first
- if delivery is degraded, do not promise downstream handoff completion
- if runtime queue is degraded, review prior job state before rerunning replay

### What To Check Next

The UI exposes bounded next-step guidance directly from the health contract.

Examples:

- restore Docker or runtime-host relay before claiming replay-backed evidence
- review recovered runtime jobs before launching another replay
- confirm degraded delivery targets before promising send completion
- proceed with inference-first triage if memory is unavailable

These are operator checks, not autonomous remediation claims.

## Governance & Multi-Tenant Authorization

### Architecture Overview

NEXUS uses a tenant-scoped, role-based access control model where:
- Each request is authenticated with user ID, tenant ID, and roles
- Each governance-sensitive action is audited with actor context
- Permissions are checked at the API boundary before execution
- Audit logs are queryable per incident for compliance review

### Authentication Headers

The system expects these headers on each request:
- `x-user-id` — Unique user identifier (required)
- `x-tenant-id` — Tenant scope (required, must be in allowed list)
- `x-roles` — Comma-separated roles (e.g., "operator,guardian")

**Note:** In demo/local mode, these are passed by test clients. In production, these should come from your SSO/identity provider middleware.

### Capability Matrix

Capabilities are defined per role in `server/auth.py:ROLE_MATRIX`. The system enforces:

- **read_incidents** — View incident details, status, history
- **create_incident** — Create new incidents from webhooks or manual report
- **trigger_replay** — Launch bounded replay scenarios
- **send_handoff** — Send engineering handoff to downstream systems
- **view_settings** — View tenant bootstrap and governance settings
- **update_bootstrap** — Modify tenant configuration
- **approve_action** — Approve or reject a proposed runbook
- **review_action** — Review runbook proposal and write feedback

Enforcement happens in two ways:
1. **Endpoint-level checks** — Critical endpoints call `check_governance_capability(auth, capability)`
2. **Service-level checks** — Business logic verifies role before taking action

### Audit Logging

Every governance-sensitive action is logged to `.nexus_audit_log.json` with:

```json
{
  "timestamp": "2026-06-16T12:34:56.789Z",
  "event_type": "governance_decision|replay_action|export_action|...",
  "tenant_id": "tenant-a",
  "actor_user_id": "user-alice",
  "actor_roles": ["guardian"],
  "payload": {
    "incident_id": "nexus-123",
    "action": "approve_runbook",
    "decision": "approve",
    "reasoning": "...",
    ...
  }
}
```

Audit events can be queried via `/api/v1/audit-logs/{incident_id}` to see the complete governance trail for an incident.

### Tenant-Aware Bootstrap Configuration

Each tenant has its own bootstrap configuration (`TenantBootstrapConfig`) including:
- `owners` — Contact information
- `repos` — Source code locations
- `delivery_targets` — Where to send handoffs
- `approval_policy` — Approval rules (if custom)
- `enabled_packs` — Which runtime packs are available

Only `admin` role can modify bootstrap configuration. See `/api/v1/tenant/bootstrap-config` for the API.

### Checking Governance Posture

Operators can use the Settings UI to view:
- Current role assignments
- Which roles can perform each critical action
- Full role-to-capability matrix

Or query `/api/v1/governance/visibility` directly to get structured role data.
