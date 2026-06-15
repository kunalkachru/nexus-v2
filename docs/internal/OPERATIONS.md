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
