# Operations

Current as of 2026-06-15.

This document describes how the current NEXUS product operates, how to run it safely, and what the bounded runtime claims actually mean.

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

### 1. Public demo mode

Used for:

- product review
- demos
- public walkthroughs

Characteristics:

- deterministic by default
- no server-side OpenAI key required
- runtime replay remains bounded and availability-dependent
- safe for public use

### 2. Local development mode

Used for:

- feature work
- browser validation
- end-to-end walkthroughs
- runtime-pack testing

Preferred startup:

```bash
./scripts/docker_fresh.sh
```

Relay-backed packaged path:

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Direct server path:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### 3. Pilot mode

Used for:

- bounded tenant pilots
- delivery and handoff testing
- weekly value reviews

Characteristics:

- tenant-aware ownership and repo mappings
- downstream delivery targets
- approval policy and role controls
- runtime-host relay where replay validation is expected

## Runtime Host And Replay Truth

NEXUS can run bounded replay in two ways:

1. directly on the current host when Docker is available
2. by delegating to the packaged runtime host when `ENABLE_RUNTIME_HOST_RELAY=1` is enabled

Operators should rely on the product’s runtime posture labels:

- runtime-backed
- inference-first
- unsupported

Do not treat inference-first reasoning as replay validation.

## Supported Incident Scope

Current baseline support:

1. `INC001` checkout timeout / retry amplification
2. `INC002` checkout DB pool exhaustion / session leak
3. `INC003` deploy regression / 5xx spike

The active expansion frontier is tracked in:

- [POST_108_SELECTIVE_EXPANSION_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_108_SELECTIVE_EXPANSION_PLAN.md)
- [POST_108_EXECUTION_MAP.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_108_EXECUTION_MAP.md)

## Pilot Setup

A pilot tenant is ready when these are configured:

1. supported outage families mapped to the tenant’s problem space
2. owner mappings for likely escalation targets
3. repository mappings for TRACE handoff
4. delivery targets for GitHub / Slack / export workflows
5. approval policy for Guardian decisions
6. enabled curated runtime packs

Example bootstrap shape:

```json
{
  "tenant_id": "acme-pilot",
  "owners": {
    "timeout_retry_amplification": "checkout-team@acme.com",
    "db_pool_exhaustion": "infra-team@acme.com"
  },
  "repos": {
    "checkout-service": "https://github.com/acme/checkout"
  },
  "delivery_targets": {
    "github": {
      "org": "acme",
      "repo": "incidents",
      "token_env": "GITHUB_INCIDENTS_TOKEN"
    }
  },
  "approval_policy": {
    "P0": "incident_manager",
    "P1": "incident_manager",
    "P2": "operator",
    "P3": "operator"
  },
  "enabled_packs": [
    "checkout-python-fastapi-auth-redis-v1",
    "checkout-python-fastapi-postgres-v1"
  ]
}
```

## Health And Observability

Basic health:

- `GET /health`

Product health summary:

- `GET /api/v1/observability/health`

This surface should answer:

- is the app healthy?
- what is replay doing?
- is the queue healthy?
- are downstream integrations reachable?

The training page exposes the operator-facing health summary so maintainers can inspect product posture without diving into logs first.

## Role Model

Current bounded roles:

- `operator`
- `incident_manager`
- `guardian`
- `admin`

Roles govern:

- incident creation
- replay triggering
- approval actions
- delivery actions
- settings and bootstrap access

Requests pass roles through the `x-roles` header.

## Operational Boundaries

NEXUS is production-shaped but still bounded.

It is not:

- a general job orchestrator for arbitrary runtime work
- a universal debugger
- an autonomous production remediation engine

For unsupported incidents, the expected product behavior is:

- still frame the incident
- clearly downgrade the evidence posture
- recommend escalation rather than pretend replay or debugging happened

## Related Docs

- [OPERATOR_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/OPERATOR_RUNBOOK.md)
- [PILOT_OPERATIONS_RUNBOOK.md](/Users/kunalkachru/Documents/nexus-v3/docs/PILOT_OPERATIONS_RUNBOOK.md)
- [TENANT_SETUP_GUIDE.md](/Users/kunalkachru/Documents/nexus-v3/docs/TENANT_SETUP_GUIDE.md)
- [WORKING_STATE.md](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md)
