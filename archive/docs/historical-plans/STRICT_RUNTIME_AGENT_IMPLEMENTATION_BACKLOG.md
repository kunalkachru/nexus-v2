# Strict Runtime Agent Implementation Backlog

Current as of 2026-06-08.

This is the strict implementation backlog for turning the current support-triage product into a narrowly real, end-to-end demonstration of:

- support triage
- memory-backed investigation
- runtime-backed reproduction
- bounded debugging handoff
- governed remediation

The scope is intentionally narrow so we can make it real rather than broad and aspirational.

## Narrowed Product Scope

### Supported flagship outages

1. Checkout timeout / retry amplification
2. Checkout DB pool exhaustion / session leak

### Supported environment packs

1. `checkout-python-fastapi-auth-redis-v1`
2. `checkout-python-fastapi-postgres-v1`

### Supported stack

- Python / FastAPI
- Redis
- Postgres
- Docker Compose as the first execution substrate

### Demo promise

At the end of this backlog, one operator should be able to show:

1. logs arrive
2. NEXUS triages the case
3. memory links prior incidents and runbooks
4. REPLICA launches a bounded pack and reports whether the failure reproduced
5. REPLICA evaluates 1-2 mitigations
6. TRACE narrows the likely code path and debugging packet
7. FORGE cites validated evidence
8. GUARDIAN approves or blocks with explicit validated vs inferred signals

## Phase Mapping

This backlog stays aligned with the earlier phased plan.

### Phase A

Design the next product layer.

Status:

- complete for product contract and orchestration shape

This backlog starts where Phase A ends.

### Phase B

Build `REPLICA` V1.

Status:

- partially complete today at the inference/UI layer
- incomplete at the true runtime-backed layer

This backlog turns Phase B into a hard implementation path.

### Phase C

Build `TRACE` V1.

Status:

- partially complete today at the inference/UI layer
- incomplete at the true debugging-packet layer

This backlog turns Phase C into a hard implementation path.

### Phase D

Strengthen the flagship outage use case.

Status:

- strong today at the demo/payload level
- still missing true runtime reproduction and debugging evidence

### Phase E

Memory/RAG second pass.

Status:

- partially complete today
- needs tighter linkage to reproduction and debugging outcomes

### Phase F

Validation and docs.

Status:

- strong today for the current prototype
- needs new runtime-agent validation steps as implementation lands

### Phase G

End-to-end runtime-backed demo closure.

This is the phase where the product can honestly demonstrate a real reproduced outage class instead of only an inferred one.

## Implementation Order

1. Build the REPLICA runtime substrate
2. Build the first real environment pack
3. Wire REPLICA output into the incident flow
4. Build the bounded TRACE source-map and debugging packet
5. Wire TRACE output into FORGE and GUARDIAN
6. Add the second environment pack
7. Re-run full validation and refresh the demo flow

## Epic B1: REPLICA Pack Registry

### Goal

Create a concrete registry of curated reproduction environments.

### Deliverables

- `server/services/replica_runtime.py`
- pack definitions for:
  - `checkout-python-fastapi-auth-redis-v1`
  - `checkout-python-fastapi-postgres-v1`
- compose path metadata
- replay profile metadata
- mitigation hook metadata
- source-map pointer metadata for TRACE

### Acceptance criteria

- the codebase has a concrete pack registry module
- flagship outage classes can select a deterministic real pack id
- tests verify pack selection rules

## Epic B2: REPLICA Runner Contract

### Goal

Define the actual execution contract for a bounded reproduction run.

### Deliverables

- `ReplicaExecutionPlan`
- `ReplicaExecutionResult`
- runner contract methods for:
  - boot
  - wait for readiness
  - replay
  - collect logs
  - apply mitigation
  - rerun
  - teardown

### Acceptance criteria

- REPLICA no longer depends only on summary inference
- the runtime contract can express a real replay cycle

## Epic B3: Retry-Amplification Pack

### Goal

Make one real reproduction environment work for the timeout / retry flagship outage.

### Pack contents

- FastAPI gateway/service shell
- downstream auth dependency shell
- Redis or queue/cache component
- replay script for checkout requests
- fault injection profile for downstream latency
- mitigation hooks:
  - cap retries
  - open circuit breaker
  - disable retry middleware flag

### Acceptance criteria

- the pack can be launched locally with Docker Compose
- a replay can trigger the target failure mode
- at least one mitigation measurably reduces the failure condition

## Epic B4: DB-Pool Pack

### Goal

Add the second real reproduction environment for pool exhaustion / session leak.

### Pack contents

- FastAPI checkout service shell
- Postgres
- bounded leak or stuck-session profile
- replay script for write-heavy checkout flow
- mitigation hooks:
  - terminate orphaned sessions
  - rollback retry patch flag
  - restart checkout service

### Acceptance criteria

- the pack can be launched locally with Docker Compose
- replay reproduces saturation or session leakage
- at least one mitigation measurably reduces the failure condition

## Epic C1: TRACE Source Map

### Goal

Create a bounded mapping from environment pack to likely code paths.

### Deliverables

- source-map structure for each supported pack
- mapping from:
  - issue family
  - service
  - mitigation outcome
to:
  - suspected modules
  - suspected functions
  - expected flow

### Acceptance criteria

- TRACE uses pack-aware source maps
- TRACE is no longer only issue-family templating

## Epic C2: TRACE Debugging Packet

### Goal

Produce a developer-facing packet grounded in replay output.

### Packet fields

- suspected service
- suspected modules
- suspected functions
- observed divergence
- state anomalies
- replay evidence summary
- recommended engineering inspection point

### Acceptance criteria

- incident UI shows a bounded debugging packet
- packet language reflects replay findings rather than only static heuristics

## Epic D1: Runtime-backed FORGE and GUARDIAN

### Goal

Make remediation and governance explicitly react to validated runtime evidence.

### Deliverables

- FORGE cites:
  - reproduced failure
  - mitigation comparison
  - narrowed code path
- GUARDIAN cites:
  - validated signals
  - inferred signals
  - residual risk after mitigation

### Acceptance criteria

- FORGE and GUARDIAN both visibly distinguish validated vs inferred reasoning
- the decision path changes if no reproduction was possible

## Epic E1: Memory/RAG linkage to runtime

### Goal

Make memory explicitly support REPLICA and TRACE, not just PRISM.

### Deliverables

- memory ranking that factors:
  - issue family overlap
  - service overlap
  - deployment overlap
  - successful mitigation overlap
- memory notes that explain:
  - which prior mitigation matches the reproduced case
  - which unresolved risk still remains

### Acceptance criteria

- memory hits influence both reproduction and remediation explanations

## Epic F1: Validation and manual demo refresh

### Goal

Keep the runtime-backed phase demoable and testable.

### Deliverables

- backend tests for pack selection and execution-plan generation
- browser checks for the new runtime-backed surfaces
- updated local one-shot guide
- updated demo script/walkthrough references

### Acceptance criteria

- fresh local run can verify the runtime-backed flagship flow without guesswork

## Epic G1: End-to-end runtime-backed demo closure

### Goal

Reach the first honest production-style demo.

### Definition of done

We can demo the following sequence on one flagship outage:

1. raw incident evidence enters NEXUS
2. NEXUS identifies likely owner and issue family
3. NEXUS links memory and prior runbooks
4. REPLICA selects a real curated pack
5. REPLICA runs replay and reproduces the failure
6. REPLICA applies a mitigation and measures the result
7. TRACE produces a bounded debugging packet grounded in replay output
8. FORGE proposes the safer action based on validated evidence
9. GUARDIAN approves or blocks with explicit validated/inferred separation

## Immediate next implementation slices

These should be done next, in order:

1. `B1` REPLICA pack registry
2. `B2` REPLICA runner contract
3. `B3` retry-amplification pack scaffold
4. `C1` TRACE source map

Only after those should we wire deeper runtime execution into the incident path.
