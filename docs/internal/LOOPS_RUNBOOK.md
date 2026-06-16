# NEXUS Loops Runbook

This document explains how to run Codex or Claude in a controlled implementation loop against NEXUS.

## Current State

The documentation reset, five-family wedge, and near-production ops maturity pass are done.

The active implementation backlog is:

- none; `backlog-131-plus.json` is complete

The active narrow phase is:

- none

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
4. read the active backlog file for the next narrow phase

Do not start a new loop until that backlog exists and has ordered items, explicit gates, and files-likely-touched lists.

## Current Safety Rules

- never treat scaffold-only evidence as runtime validation
- keep seeded and live incident paths semantically aligned
- verify packaged-app runtime claims through the Docker path on `:7860`
- refresh control docs when a backlog is fully closed
- update the backlog item status immediately after its gates pass

## Post-131 Checkpoint

`backlog-117-plus.json` is complete.

`backlog-125-plus.json` is complete.

`backlog-131-plus.json` is complete.

The five-family product objective remains wrapped for the present strategy. The most recently closed narrow phase added:

- guided stakeholder demo bundles on `/inputs`
- bundle proof surfaces
- fresh-incident demo-origin carryover

Truth boundaries remain:

- do not present `REPLICA` as arbitrary VM reproduction
- do not present `TRACE` as a universal debugger

Future loops should return to:

- bugfixes
- pilot-specific hardening
- narrowly scoped tenant follow-ups
