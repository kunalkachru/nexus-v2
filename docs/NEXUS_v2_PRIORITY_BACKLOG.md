# NEXUS v2 Priority Backlog

> **Purpose:** This backlog ranks the remaining work after the UI-first roadmap, thin backend seams, and demo-hardening work are complete.
>
> The earlier UI/demo backlog items are now complete. This list is the next-phase enterprise hardening backlog.

## How To Use This List

- Pick item `1` if you want the biggest enterprise-credibility gain.
- Pick item `2` if you want the clearest control story for approval and execution.
- Pick item `3` if you want the strongest durability and recovery story.
- Pick item `4` if you want the best readiness gain for multi-tenant / production mode.
- Pick items `5-6` if you want to reduce operational risk and keep the docs honest.

## Ranked Tasks

### 1. Real Observability Ingestion And Evidence Fusion

**Why this is highest priority:** It closes the biggest credibility gap between the polished product shell and the live enterprise system the docs describe.

**What to do**
- Replace fixture-only joins with real adapters for Prometheus, Datadog, and log sources such as ELK or Loki.
- Carry source provenance all the way into the incident console.
- Make the agent evidence panels show where signals came from and why they matter.

**Done when**
- The incident console can explain evidence provenance without relying on static fixture data.
- The agent story is visibly grounded in live or adapter-backed source data.

### 2. GUARDIAN Execution Policy And Runbook Governance

**Why this is high priority:** A believable enterprise product needs a visible approval gate, not just a button that flips state.

**What to do**
- Make approval, block, execute, and learn states explicit in the UI.
- Add a clearer policy registry or decision record for why an action is allowed or denied.
- Tie runbook selection to a more explicit matching and approval flow.

**Done when**
- Users can see why an execution request was accepted or blocked.
- The approval gate feels like a genuine control point.

### 3. Production Persistence And Durable Artifacts

**Why this is high priority:** Demo-grade file-backed storage is good enough for now, but the next phase needs a real durability story.

**What to do**
- Move incident, audit, replay, and training state onto durable storage.
- Keep the UI unchanged while swapping the backing store.
- Preserve incident history across restarts and deployments.

**Done when**
- The product can survive a restart without losing meaningful state.
- Replay and training artifacts are durably queryable.

### 4. Auth, Tenant, And Deployment Hardening

**Why this is high priority:** The current checks are improved, but true production readiness still needs stronger boundary enforcement.

**What to do**
- Harden ingress verification and tenant separation.
- Tighten deployment-time secrets and operational posture.
- Make the local/demo mode and production mode behavior explicit.

**Done when**
- The trust model is clear and resilient to misuse.
- Production-mode boundaries are easier to reason about.

### 5. Further Backend Service Decomposition And Operational Cleanup

**Why this is medium priority:** The backend is already more modular than before, but the last bits should be cleaned up before the next integration wave.

**What to do**
- Keep extracting route glue and helper logic out of `server/app.py` where it still lingers.
- Make service responsibilities narrower and easier to test.
- Keep the public API contracts stable while changing internals.

**Done when**
- `server/app.py` is mostly orchestration.
- The next feature can land without expanding a monolith again.

### 6. Docs And Source-Of-Truth Maintenance

**Why this is lower priority:** It is important, but it does not block the product itself.

**What to do**
- Keep the README as the canonical product entrypoint.
- Keep the status matrix and backlog in sync with the code.

**Done when**
- A new reader can tell what is current and what is next.

## Recommended Next Pick

- If you want the best product credibility gain: **Task 1**
- If you want the best visible control and safety gain: **Task 2**
- If you want the best engineering-risk reduction: **Task 3**

## Short Version

- `P0`: Tasks 1-3
- `P1`: Tasks 4-5
- `P2`: Task 6
