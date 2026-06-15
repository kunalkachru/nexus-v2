# Curated Runtime Pack Contract

Current as of 2026-06-15.

This document defines how a new outage class becomes a curated runtime and debugger pack in NEXUS.

## Current Curated Packs

1. `checkout-python-fastapi-auth-redis-v1`
2. `checkout-python-fastapi-postgres-v1`
3. `api-python-fastapi-catalog-v1`
4. `checkout-python-fastapi-auth-validation-v1`
5. `worker-backlog-kafka-v1`

## Current Supported Bounded Families

- timeout / retry amplification
- DB pool exhaustion / session leak
- deploy regression / 5xx spike
- auth dependency slowdown / token validation failures
- queue / worker backlog affecting transaction completion

Each pack must remain:

- bounded, not generic
- reproducible, not heuristic
- measurable, not subjective
- honest about runtime support
