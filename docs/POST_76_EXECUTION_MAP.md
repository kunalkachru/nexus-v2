# NEXUS Post-76 Execution Map

Current as of 2026-06-15.

This document expands [backlog-77-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-77-plus.json) into concrete execution tasks so future loops can move through market-ready v1 hardening without random drift.

Use it together with:

- [backlog-77-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-77-plus.json)
- [docs/POST_76_MARKET_READY_PLAN.md](/Users/kunalkachru/Documents/nexus-v3/docs/POST_76_MARKET_READY_PLAN.md)

## How To Use This Map

For each backlog item:

1. read the JSON item
2. read the matching execution-map section
3. complete backend work first
4. complete UI work second
5. run targeted validation before the full gates
6. update docs before marking the item done

## Item 77: Pilot Deployment And Tenant Onboarding

### Backend tasks

- define the bootstrap fields required for a usable tenant:
  - owners
  - repos
  - delivery targets
  - approval policy
  - enabled packs
- persist bootstrap completeness in a product-readable structure
- add an onboarding-readiness API contract

### UI tasks

- add onboarding or readiness visibility to settings or training surfaces
- show missing prerequisites clearly
- make readiness feel like a product state, not a hidden config issue

### Validation tasks

- test full and partial tenant bootstrap cases
- add browser coverage for onboarding-readiness states

### Documentation tasks

- update `docs/OPERATIONS.md`
- document the bounded onboarding process and required inputs

## Item 78: Auth, Roles, And Approval Controls Hardening

### Backend tasks

- define the role matrix for operator, reviewer, and admin
- gate replay, send, settings, and approval actions by role
- ensure error responses and auth states are stable

### UI tasks

- show disabled or hidden controls based on role
- explain why a control is unavailable
- keep review and approval flows understandable

### Validation tasks

- add role-based backend tests
- add browser checks for role-aware controls

### Documentation tasks

- update `docs/OPERATIONS.md` with the role model

## Item 79: Integration Reliability And Delivery Guarantees

### Backend tasks

- define delivery lifecycle states:
  - queued
  - sent
  - retrying
  - failed
  - terminal_failure
- persist delivery attempts and retry outcomes
- add bounded retry or resend behavior where safe

### UI tasks

- expose delivery lifecycle in incident and history surfaces
- show resend or retry affordances where supported
- keep failure messaging specific and actionable

### Validation tasks

- test success, retry, and terminal-failure states
- verify UI reflects lifecycle state correctly

### Documentation tasks

- update operational notes for downstream delivery recovery

## Item 80: Product Observability And Self-Monitoring

### Backend tasks

- define health metrics for:
  - app responsiveness
  - replay health
  - downstream integration health
  - queue or workflow degradation
- expose concise operational summaries safely

### UI tasks

- surface product health in a training or status area
- distinguish healthy, degraded, and failing states
- keep observability concise and operator-readable

### Validation tasks

- test health endpoints or service summaries
- add browser checks for status rendering

### Documentation tasks

- update `docs/OPERATIONS.md` with observability interpretation

## Item 81: Security And Secrets Handling Hardening

### Backend tasks

- audit credential and secret entry points
- tighten masking and persistence rules
- verify integration payloads do not leak secrets into ordinary evidence surfaces

### UI tasks

- improve masking and safe display behavior for sensitive settings
- ensure unsafe configuration states are visible without exposing secrets

### Validation tasks

- add tests for masking and secret-safe responses
- add browser checks where settings or handoff surfaces render secret-adjacent data

### Documentation tasks

- document the actual security posture and boundaries honestly

## Item 82: Operator Onboarding And Runbooks

### Backend tasks

- usually minimal backend work unless operator help content needs API support

### UI tasks

- refine operator-facing training or help surfaces
- make triage, replay, handoff, approval, and feedback paths clearer

### Validation tasks

- verify onboarding surfaces remain legible in browser tests
- run demo flow to ensure docs and product still match

### Documentation tasks

- update walkthroughs and one-shot test docs
- add operator runbooks for common flows and failure states

## Item 83: Buyer-Facing Proof Package And ROI Story

### Backend tasks

- ensure ROI and case-study inputs are exposed cleanly enough for packaging

### UI tasks

- improve buyer-facing metrics presentation where useful
- ensure proof surfaces stay grounded in measured or honestly estimated values

### Validation tasks

- verify ROI and case-study surfaces remain accurate
- add browser checks if product pages become presentation-critical

### Documentation tasks

- update GTM and presentation docs
- add flagship before/after proof summaries

## Item 84: Market-Facing Wow-Effect UI Revamp And Conversion Polish

### Backend tasks

- usually minimal backend work unless presentation surfaces need small supporting payload additions

### UI tasks

- define a stronger premium visual direction for the core buyer-facing surfaces
- upgrade queue, incident, training, and replay presentation with clearer hierarchy and stronger visual identity
- improve typography, spacing, surface treatment, and motion so the product feels more intentional and differentiated
- ensure the visual pass strengthens comprehension instead of masking evidence posture or bounded behavior

### Validation tasks

- verify the flagship screens remain readable and honest in browser tests
- check mobile and desktop responsiveness for the most visible screens
- run demo flow to ensure the visual changes support the product story rather than distracting from it

### Documentation tasks

- update `docs/PRESENTATION_PACK.md`
- refresh any screenshots or presentation-facing notes that depend on the older visual system

## Item 85: Market-Ready v1 Checkpoint And Release Readiness

### Backend tasks

- no major new feature work unless validation uncovers critical fixes

### UI tasks

- tighten any final wording or visibility issues found during validation

### Validation tasks

- run the full validation stack:
  - `pytest tests/ -q`
  - `npm run browser:verify`
  - `python demo.py`
  - Docker smoke path
- verify the flagship incidents and a fresh live incident remain coherent

### Documentation tasks

- refresh `AGENTS.md`
- refresh `WORKING_STATE.md`
- refresh `docs/LOOPS_RUNBOOK.md`
- update owner-facing readiness docs
- write a concise release-readiness summary

## Recommended Execution Grouping

### Group 1: Deployment and control hardening

- `77`
- `78`
- `79`

### Group 2: Trust and operations hardening

- `80`
- `81`
- `82`

### Group 3: Selling and release checkpoint

- `83`
- `84`
- `85`

## Suggested Future Loop Prompt Add-On

When `77+` becomes active, add this to the loop prompt:

```text
Read docs/POST_76_EXECUTION_MAP.md after reading backlog-77-plus.json.
For each item, complete backend tasks, then UI tasks, then validation tasks, then documentation tasks.
Do not mark the item done until the manual and product-facing readiness implications are reflected in the checkpoint summary.
```
