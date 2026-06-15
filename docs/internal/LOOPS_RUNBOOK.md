# NEXUS Loops Runbook

This document explains how to run Codex or Claude in a controlled implementation loop against NEXUS.

## Current State

The documentation reset and five-family wedge completion are done.

The active backlog is:

- `backlog-117-plus.json`

This backlog covers near-production ops maturity for the current five-family product.

## Loop Rule

Use a loop only when:

1. the next work is broken into ordered backlog items
2. each item has concrete completion criteria
3. each item has explicit test gates

## Required Control Docs

Before any future loop:

1. read [AGENTS.md](/Users/kunalkachru/Documents/nexus-v3/AGENTS.md)
2. read [WORKING_STATE.md](/Users/kunalkachru/Documents/nexus-v3/WORKING_STATE.md)
3. read [LOOP_MEMORY.md](/Users/kunalkachru/Documents/nexus-v3/docs/internal/LOOP_MEMORY.md)
4. read [backlog-117-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-117-plus.json)

## Current Safety Rules

- never treat scaffold-only evidence as runtime validation
- keep seeded and live incident paths semantically aligned
- verify packaged-app runtime claims through the Docker path on `:7860`
- refresh control docs when a backlog is fully closed
- update the backlog item status immediately after its gates pass
