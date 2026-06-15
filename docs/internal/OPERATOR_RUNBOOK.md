# NEXUS Operator Runbook

Quick reference for support operators triaging and managing incidents through NEXUS.

## The 6-Step Flow

1. Triage: Command Center → select incident
2. Review: read the investigation summary and suggested action
3. Decide: approve, reject, or request modification
4. Execute: if approved, action runs and results are captured
5. Handoff: send investigation packet to engineering
6. Follow-up: track delivery and engineering feedback

## Key Concepts

- `runtime-backed`: replay really ran for this incident family
- `inference-first`: NEXUS can frame and guide the case, but replay did not validate it
- `unsupported`: NEXUS can still triage, but the incident is outside the current bounded wedge

## Current Supported Bounded Families

- `INC001` timeout / retry amplification
- `INC002` DB pool exhaustion / session leak
- `INC003` deploy regression / 5xx spike
- `INC005` queue / worker backlog
- `INC007` auth dependency slowdown / token validation failures

## If Replay Is Not Available

1. confirm whether the issue family is supported
2. check runtime-host status in Settings or Training
3. proceed with inference-first handoff if replay is unavailable
4. do not describe the incident as validated unless replay actually ran
