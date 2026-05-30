# NEXUS v2 Priority Backlog

> **Purpose:** This backlog ranks the remaining work after the UI-first roadmap and thin demo backend are complete. It is ordered so you can choose the next task based on product value, trust, and dependency.

## How To Use This List

- Pick item `1` if you want the biggest visible product credibility gain.
- Pick item `2` if you want the strongest enterprise narrative and the best bridge to real backend integrations.
- Pick item `3` if you want the safest technical foundation before doing more feature work.
- Pick items `4-6` if you want to turn the demo-grade shell into a more production-shaped system.
- Pick items `7-8` if you want to close out polish, realism, and documentation drift.

## Ranked Tasks

### 1. Visible Audit UI And Incident History

**Why this is high priority:** Users should be able to inspect what happened without leaving the product shell. This is the clearest trust and enterprise-feel upgrade.

**What to do**
- Add a visible audit trail section to the incident console.
- Add a dedicated audit drawer or panel for incident history.
- Surface who changed state, when, and why.
- Make the audit trail readable without opening raw JSON or logs.

**Done when**
- The incident page shows an obvious audit trail.
- The audit data is readable in the UI, not just available via API.
- The manual demo flow can be validated visually from intake through audit review.

### 2. Observability Adapters And Evidence Fusion

**Why this is high priority:** This is the main bridge from a polished demo to a believable enterprise system. It is also the clearest way to justify the SENTINEL/PRISM/FORGE/GUARDIAN narrative.

**What to do**
- Add adapters for Prometheus and Datadog signals.
- Add log correlation inputs from ELK/Loki style sources.
- Add deployment and service metadata enrichment.
- Make the incident evidence view show where each signal came from.

**Done when**
- The backend no longer relies only on fixture joins for evidence.
- The agent cards visibly reference distinct input sources.
- The incident timeline and signal sections show real source provenance.

### 3. Split The Remaining Backend Monolith

**Why this is high priority:** The current backend is already functional, but the remaining logic in `server/app.py` is too dense for the next stage. Splitting it reduces risk before adding more integrations.

**What to do**
- Move incident lifecycle helpers into dedicated service modules.
- Move page route glue into route modules if it still lives in `server/app.py`.
- Keep API contracts stable while changing internals.

**Done when**
- `server/app.py` is mostly composition and wiring.
- Incident logic lives in focused modules.
- Tests continue to pass without changing the external UI flow.

### 4. Strengthen GUARDIAN Execution Policy

**Why this is high priority:** The product needs a clearer story for approval, rejection, and safe execution boundaries.

**What to do**
- Make execution outcomes explicit in the UI.
- Show approval, blocked, executed, and learned states clearly.
- Add more visible decision provenance for why an action is allowed or denied.

**Done when**
- Users can see why GUARDIAN approved or blocked an action.
- The execute flow feels like a real control point, not a button that only changes state.

### 5. Auth, Tenant, And Signature Hardening

**Why this is high priority:** This is the minimum production-readiness layer once the product story is convincing.

**What to do**
- Tighten request verification for ingress paths.
- Clarify tenant boundaries.
- Add stronger auth posture for enterprise mode.

**Done when**
- Ingress and API actions are harder to spoof.
- The product can explain its trust model clearly.

### 6. Persistent Production Storage

**Why this is high priority:** Demo-grade in-memory state is fine for a demo, but the next step is durable incident, replay, and training storage.

**What to do**
- Persist incident events durably.
- Persist replay launches and training artifacts.
- Keep the UI behavior the same while swapping the backing store.

**Done when**
- Restarting the app does not lose the important product history.
- Replay and training pages can be backed by durable state rather than only fixture overlays.

### 7. Replay And Training Realism

**Why this is medium priority:** The surfaces already exist and work, but they can be made more persuasive and more connected to the backend.

**What to do**
- Make replay create clearer incident-state transitions.
- Make training summaries derive from real incident history where possible.
- Keep the current UI but deepen the data model behind it.

**Done when**
- Replay feels like a real product feature, not just a scenario launcher.
- Training shows a credible learning loop tied to incident history.

### 8. Doc Cleanup And Source-Of-Truth Refresh

**Why this is lower priority:** The stale docs are confusing, but they do not block product progress.

**What to do**
- Refresh hackathon-era docs that still describe the old sprint as authoritative.
- Point readers at the current matrix and backlog.
- Keep the repo documentation consistent with the code.

**Done when**
- New readers can find the current status quickly.
- Old sprint docs are clearly labeled historical.

## Recommended Next Pick

- If you want the best visible enterprise-feel gain: **Task 1**
- If you want the best backend credibility gain: **Task 2**
- If you want the best engineering-risk reduction: **Task 3**

## Short Version

- `P0`: Tasks 1-3
- `P1`: Tasks 4-6
- `P2`: Tasks 7-8
