# NEXUS Demo Cheat Sheet

Current as of 2026-06-15.

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

1. open `/inputs`
2. load example logs
3. submit raw logs
4. open the created `nxs_...` incident
5. show issue framing, memory, replay posture, and debugger path
6. approve the runbook
7. open `/training`
8. show latest triage plus scorecard

## Do Not Overclaim

Do not describe the current product as:

- a universal incident platform
- a universal debugger
- arbitrary environment reproduction

Describe it as:

- a bounded support-triage and investigation product
- with real replay and debugging support for curated outage families
