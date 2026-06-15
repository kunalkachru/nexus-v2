# NEXUS Pilot Operations Runbook

This runbook covers tenant onboarding, operational procedures, and governance for running NEXUS across 2–3 pilot tenants.

## Pilot Program Structure

NEXUS pilots run within these bounded incident families:

- `INC001` checkout timeout / retry amplification
- `INC002` checkout DB pool exhaustion / session leak
- `INC003` deploy regression / 5xx spike
- `INC005` queue / worker backlog affecting transaction completion
- `INC007` auth dependency slowdown / token validation failures

Tenant scope:

- 2–3 qualified tenants per wave
- 4–6 week evaluation cycles
- runtime-backed handling should grow while unsupported cases remain explicitly downgraded

## Weekly Pilot Review

Review:

1. incident volume
2. support quality
3. engineering feedback
4. runtime-backed versus inference-first ratio
5. time savings and handoff quality
6. recurring unsupported family patterns
