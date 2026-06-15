# NEXUS Tenant Setup Guide

This guide walks through adding a new tenant to the NEXUS pilot program, from initial assessment through operational readiness.

## Phase 1: Pre-Qualification (2 days)

### Incident Scope Alignment

Collect the tenant's top 10 incidents from the past 3 months. Map them to NEXUS families:

```
Tenant Incident → NEXUS Family → Coverage Status
================================================
API timeout + retries → INC001 (Timeout/Retry) → Runtime-backed
DB connection pool exhaustion → INC002 (Pool Exhaustion) → Runtime-backed
Deploy regression 5xx spike → INC003 (Deploy Regression) → Runtime-backed
Certificate expiry → Unsupported → Downgrade to inference
Memory leak under load → Unsupported → Downgrade to inference
```

**Go/No-go decision**: At least 60% of incidents must map to supported families (INC001, INC002, INC003).

### Stakeholder Confirmation

Get sign-off from:

- [ ] Tenant incident commander (point contact)
- [ ] Tenant engineering leadership (2–3 service owners)
- [ ] NEXUS pilot program owner

Confirm roles and expectations:
- Incident commander attends weekly reviews
- At least one engineering team willing to test NEXUS-guided actions
- 4–6 week evaluation window

## Phase 2: Configuration (1 day)

### Step 1: Collect Ownership Mappings

Get GitHub/Jira ownership info for each service the tenant considers critical:

```
Service          Owner Team         GitHub Contact    Jira Project
==================================================================
checkout-svc     Checkout Platform  @checkout-team    CHECKOUT
auth-svc         Identity Platform  @auth-team        IDENTITY
api-service      Backend Platform   @backend-team     API
payment-gateway  Payment Systems    @payment-team     PAYMENT
```

### Step 2: Add Tenant Configuration

Edit `server/services/enterprise_runtime.py` and add the tenant to `_get_tenant_owner_mappings()`:

```python
def _get_tenant_owner_mappings() -> dict[str, object]:
    tenant_mappings = {
        "tenant-a": { ... },  # existing
        "tenant-b": {  # NEW TENANT
            "checkout-svc": {
                "team": "Checkout Platform",
                "escalation_team": "Platform SRE",
                "repository": "github.com/company/checkout-service",
                "code_owner_slug": "@checkout-team",
                "provenance": "tenant-b-config",
            },
            "auth-svc": {
                "team": "Identity Platform",
                "escalation_team": "Platform SRE",
                "repository": "github.com/company/auth-service",
                "code_owner_slug": "@auth-team",
                "provenance": "tenant-b-config",
            },
        }
    }
    return tenant_mappings
```

### Step 3: Configure App Environment

Set environment variables for the pilot app:

```bash
# .env file or docker-compose override
NEXUS_TENANT_ID=tenant-b
NEXUS_ENABLE_REPLICA_RUNTIME=1
ENABLE_RUNTIME_HOST_RELAY=1  # if using Docker relay
```

### Step 4: Test Ownership Resolution

Verify the tenant's ownership mappings work:

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from server.services.enterprise_runtime import _resolve_owner_for_service

# Test with tenant-b's service
owner = _resolve_owner_for_service('checkout-svc', tenant_id='tenant-b')
print(f'Owner: {owner[\"team\"]}')
print(f'Repo: {owner[\"repository\"]}')
print(f'Slug: {owner[\"code_owner_slug\"]}')
assert owner['is_tenant_mapped'] == True, 'Tenant mapping failed'
print('✓ Ownership resolution OK')
"
```

## Phase 3: Integration Testing (2 days)

### Sample Incident Walkthrough

Create 2–3 test incidents using the tenant's actual logs (sanitized for privacy):

1. **INC001 sample**: Timeout + retry pattern from production
2. **INC002 sample**: Pool exhaustion pattern from production
3. **Out-of-scope sample**: Something intentionally outside bounded wedge

For each, walk through:

```bash
# Start NEXUS server
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Go to http://localhost:7860/inputs
# Paste the sample logs → incident detail
# Verify:
# - Classification matches expected family (or correct downgrade)
# - Owner routing shows correct team + repo
# - TRACE module cites likely services
# - FORGE ranks expected actions first
# - Guardian confidence is appropriate
```

### Integration Test Checklist

- [ ] At least one incident classifies as INC001 correctly
- [ ] At least one incident classifies as INC002 correctly
- [ ] Owner mappings show correct team (not fallback)
- [ ] Out-of-scope incident downgrades clearly (not over-claiming)
- [ ] Triage time is <10 seconds per incident
- [ ] FORGE reasoning mentions memory hits and runtime evidence

### Failure Mode: "Everything classifies as unsupported"

If incidents consistently downgrade:

1. Check tenant's incident logs are similar to benchmark incidents
2. Verify ownership mappings are configured
3. Check PRISM classification with live logs via demo tool
4. May indicate incident family mismatch — escalate to NEXUS owner

## Phase 4: Operations Handoff (1 day)

### Operator Training

Walk the incident commander through:

1. **Inputs page**: How to paste logs and understand intake warnings
2. **Incident detail**: How to read the investigation packet and understand Guardian's role
3. **Training page**: Where to see execution outcomes and broader metrics
4. **Weekly review**: How to assess scorecard and provide feedback

### First Live Incident Checklist

When the tenant encounters their first real incident:

- [ ] Incident commander acknowledges NEXUS triage (email thread or Slack)
- [ ] Engineering team reviews recommended action
- [ ] Action is executed (with or without approval)
- [ ] Outcome is captured (resolved, improved, or no change)
- [ ] Feedback is logged (team confidence, handoff quality, trust signal)

### Feedback Template

Use this for post-incident feedback:

```
Incident: [incident_id]
Date: [when it happened]
Family: [INC001/INC002/INC003/Unsupported]
Action taken: [what NEXUS recommended]
Outcome: [Resolved/Improved/No change/Blocked]
Engineering feedback: [team's assessment]
Trust signal: [confident/cautious/skeptical]
Suggestions: [anything that would improve NEXUS guidance]
```

## Phase 5: Operational Readiness (Ongoing)

### Baseline Metrics

Track these starting week 1:

| Metric | Goal | Check |
|---|---|---|
| Incidents handled | 3–5/week | Weekly review |
| Runtime-backed % | 40%+ by week 2 | Scorecard |
| Triage time | <10 min avg | Training page |
| Handoff completion | 60%+ approved | Guardian audit |
| Engineering trust | Expressed confidence | Weekly sync |

### Escalation Criteria

Pause the pilot immediately if:

- [ ] Engineering team refuses to approve multiple actions (trust broken)
- [ ] Incidents consistently misclassify or downgrade unexpectedly (scope mismatch)
- [ ] Test suite regresses (product stability issue)
- [ ] Operator confusion about Guardian decision (UX issue)

### Graduation Criteria

After 4–6 weeks, recommend graduation if:

- [ ] Runtime-backed handling reaches 60%+
- [ ] Engineering team expresses willingness to use NEXUS for future incidents
- [ ] No critical issues or stability concerns
- [ ] Scorecard metrics are clear and measurable

## Support Contacts During Pilot

- **Immediate issues**: Ping NEXUS pilot owner on Slack
- **Configuration questions**: Reference this guide + docs/PILOT_OPERATIONS_RUNBOOK.md
- **Product feedback**: Log in weekly review, then escalate if blocking
- **Escalation**: NEXUS owner decides whether to fix, work around, or pause

## Rollback Procedure

If the tenant needs to exit the pilot:

1. Inform NEXUS owner 24 hours in advance
2. Archive weekly metrics and feedback for post-mortem
3. Return to manual triage (NEXUS will remain available for reference)
4. Schedule debrief to capture learnings

Rollback should be low-friction — no code changes needed, just redirect future incidents back to standard workflow.

## Next Steps: Scope Expansion

Once a tenant is stable at 60%+ runtime coverage:

1. Review `docs/POST_100_FIELD_PILOT_EXECUTION_AND_PROOF_AT_SCALE_PLAN.md` for next scope phases
2. Propose one additional incident family (e.g., certificate expiry, memory leak)
3. Add that family's reputation patterns to the tenant's config
4. Re-validate with 2–3 test incidents from their production history
5. Gradual rollout starting week 6–7 of pilot

Scope expansion is optional — a tenant's pilot can remain stable within the current three-family wedge indefinitely.
