# NEXUS Demo Cheat Sheet

Current as of 2026-06-16.

## One-Line Pitch

NEXUS compresses the support-to-engineering relay for recurring customer-facing outages by turning noisy evidence into a runtime-aware, debugging-guided, engineering-ready case before one final human review point.

## Product Flow

`SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

## Current Bounded Families

- `INC001` timeout / retry amplification
- `INC002` DB pool exhaustion / session leak
- `INC003` deploy regression / 5xx spike
- `INC005` queue / worker backlog
- `INC007` auth dependency slowdown / token validation failures

## Fastest Demo Flow

1. open `/queue`
2. open the flagship seeded incident
3. click `Inspect intake`
4. on `/inputs`, load a guided demo bundle or example logs
5. submit raw logs
6. open the created `nxs_...` incident from the top brief
7. show issue framing, memory, replay posture, and debugger path
8. approve the runbook
9. open `/training`
10. show latest triage plus scorecard

## Do Not Overclaim

Do not describe the current product as:

- a universal incident platform
- a universal debugger
- arbitrary environment reproduction

Describe it as:

- a bounded support-triage and investigation product
- with real replay and debugging support for curated outage families
