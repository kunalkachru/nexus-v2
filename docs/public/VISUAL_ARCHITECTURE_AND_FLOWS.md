# NEXUS Visual Architecture And Flows

Current as of 2026-06-16.

## Product Screenshots

### Command Center

![Command Center](/Users/kunalkachru/Documents/nexus-v3/docs/public/assets/screenshots/command-center.png)

### Incident Detail

![Incident Detail](/Users/kunalkachru/Documents/nexus-v3/docs/public/assets/screenshots/incident-detail.png)

### Raw Log To Incident Flow

![Raw Log Flow](/Users/kunalkachru/Documents/nexus-v3/docs/public/assets/screenshots/raw-log-incident-flow.png)

### Learning & Controls

![Learning and Controls](/Users/kunalkachru/Documents/nexus-v3/docs/public/assets/screenshots/learning-controls.png)

## What The Product Must Answer

Every major surface should help the operator answer:

1. what is most likely happening?
2. who likely owns it?
3. what prior cases matter?
4. what is supported versus bounded?
5. what should happen next?
6. who approves the action?

## Strongest Review Flow

The strongest truthful UI path is:

`/queue -> seeded incident -> Inspect intake -> /inputs -> fresh nxs incident -> /training -> /settings`

## Current Workflow

```mermaid
flowchart LR
    A["Raw logs or queue incident"] --> B["SENTINEL framing"]
    B --> C["PRISM diagnosis and memory"]
    C --> D["REPLICA bounded replay"]
    D --> E["TRACE bounded debugger and handoff"]
    E --> F["FORGE mitigation ranking"]
    F --> G["GUARDIAN review"]
    G --> H["Execution outcome and memory update"]
```

This is the shipped bounded workflow.

## Bounded Coverage

The current wedge covers five bounded outage families:

- timeout / retry amplification
- DB pool exhaustion / session leak
- deploy regression / 5xx spike
- queue / worker backlog
- auth dependency slowdown / token validation failures

REPLICA and TRACE are real for curated families, but they remain bounded and explicit.

Every stakeholder walkthrough should also keep the support posture explicit:

- `runtime-backed`
- `inference-first`
- `unsupported`
