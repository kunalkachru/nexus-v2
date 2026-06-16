# Post-131 Pilot UX Hardening Plan

Current as of 2026-06-16.

## Objective

Strengthen the shipped five-family NEXUS wedge for self-serve demos, pilot evaluation, and operator clarity without broadening the category.

This phase exists to close the highest-value gap between a technically credible product and a confidently sellable one:

- make incident access and navigation easier
- reduce information overload in the incident workspace
- make six-agent handoff behavior easier to follow
- make fresh-log reasoning more legible and more trustworthy
- align the product UI and the owner-facing walkthrough to the actual best demo path

The product remains:

- a support-to-engineering investigation workflow
- five bounded outage families
- bounded REPLICA and bounded TRACE
- runtime-backed only where explicitly proven
- governed by a human approval gate before action

## Why This Phase Exists

The current baseline is technically strong and truthful, but the remaining friction is mostly operator-facing:

1. the path from landing page to the right incident or intake flow can still be clearer
2. the incident workspace still asks the user to absorb too much at once
3. the six-agent relay is now present, but the transfer story can still be more legible
4. fresh incidents need stronger evidence provenance and clearer explanation of what came from logs versus what the product inferred
5. the docs need one final pass after the UI/flow hardening lands so demos are fully self-serve

## Scope

In scope:

- queue and incident-access usability
- better direct paths to `/inputs` and seeded incidents
- progressive disclosure in the incident workspace
- clearer baton, packet, and relay playback surfaces
- stronger evidence provenance for fresh-log triage
- final browser-truth and operator-doc sync

Out of scope:

- new outage families
- arbitrary VM reproduction
- universal debugging
- platform broadening beyond the current five-family wedge

## Active Backlog

- [backlog-137-plus.json](/Users/kunalkachru/Documents/nexus-v3/backlog-137-plus.json)

## Phase Outcome

This phase is complete only when:

1. a first-time operator can get from queue to the right seeded or fresh incident path without confusion
2. the incident workspace emphasizes the current decision and hides lower-signal detail by default
3. the six-agent relay, current owner, and packet transfers are easy to explain during a live demo
4. fresh-log incidents clearly distinguish extracted evidence from inferred reasoning
5. the owner-facing demo guide matches the shipped UI and can be followed without outside help

## Final Checkpoint

If this phase closes successfully, the next work should stay narrow:

- pilot-specific bug fixes
- tenant-specific onboarding follow-ups
- bounded trust or resilience improvements discovered during real pilot usage

No broader roadmap should be implied from this file.
