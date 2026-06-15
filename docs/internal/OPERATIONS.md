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
