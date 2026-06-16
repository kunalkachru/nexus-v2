# NEXUS Loops Runbook

This document explains how to run Codex or Claude in a controlled implementation loop against NEXUS.

## Current State

The documentation reset, five-family wedge, near-production ops maturity pass, and pilot UX hardening pass are done.

There is no active implementation backlog right now.

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

## Post-137 Checkpoint

`backlog-117-plus.json` is complete.

`backlog-125-plus.json` is complete.

`backlog-131-plus.json` is complete.

`backlog-137-plus.json` is complete.

`backlog-145-plus.json` is complete.

The five-family product objective remains wrapped for the present strategy. The most recently closed narrow phase added:

- easier seeded and fresh incident access from `/queue`
- progressive disclosure across the incident workspace
- stronger six-agent relay ownership and packet visibility
- clearer extracted-versus-inferred fresh-incident truth
- a smoother `/inputs -> fresh incident` landing path
- stronger browser-truth and smoke coverage across the core demo routes

Truth boundaries remain:

- do not present `REPLICA` as arbitrary VM reproduction
- do not present `TRACE` as a universal debugger

The most recently closed narrow phase added:

- public validation baseline sync across the main owner-facing entrypoints
- queue-first route guidance consistency across the public demo docs
- explicit public evidence-posture wording across GTM, buyer, and presenter material
- internal control-surface sync so the repo no longer implies an unstarted backlog

Do not start another loop until a new narrow backlog exists with ordered items, explicit test gates, and files-likely-touched lists.
