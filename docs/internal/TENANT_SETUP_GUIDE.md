# NEXUS Tenant Setup Guide

This guide walks through adding a new tenant to the NEXUS pilot program, from initial assessment through operational readiness.

## Supported Bounded Families

Map the tenant’s recurring incidents against:

- `INC001` timeout / retry amplification
- `INC002` DB pool exhaustion / session leak
- `INC003` deploy regression / 5xx spike
- `INC005` queue / worker backlog affecting transaction completion
- `INC007` auth dependency slowdown / token validation failures

Go / no-go rule:

- at least 60% of the tenant’s recurring incidents should map to the supported wedge

## Environment

Recommended pilot app configuration:

```bash
NEXUS_TENANT_ID=tenant-name
ENABLE_RUNTIME_HOST_RELAY=1
```

## Validation

For each tenant, walk at least:

1. one replay-backed family
2. one inference-first or unsupported family
3. one real tenant-flavored log sample through the input flow
