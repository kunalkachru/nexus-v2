# NEXUS Pilot Operations Runbook

This runbook covers tenant onboarding, operational procedures, and governance for running NEXUS across 2–3 pilot tenants.

## Pilot Program Structure

NEXUS FR2 pilots run within these boundaries:

**Support scope**: three incident families (INC001, INC002, INC003)
- INC001: Checkout timeout / retry amplification
- INC002: Database pool exhaustion / session leak
- INC003: Deploy regression / 5xx spike

**Tenant scope**: 2–3 qualified tenants per wave
**Duration**: 4–6 week evaluation cycles
**Success metric**: runtime-backed incident handling reaches 60%+ with high engineering trust

## Tenant Setup

### Pre-flight Checklist

Before onboarding a new tenant:

1. **Confirm incident scope alignment**: tenant's top 3 incident families must include at least two from the bounded wedge
2. **Verify ownership mappings**: collect GitHub/Jira slugs and responsible teams for services
3. **Assess environment readiness**: Docker-capable staging environment for optional runtime replay
4. **Confirm point contact**: designate incident commander and weekly review owner

### Tenant Configuration

1. Add tenant to `server/services/enterprise_runtime.py:_get_tenant_owner_mappings()`
2. Configure service-to-team mappings in the tenant block
3. Set `NEXUS_TENANT_ID` in pilot app configuration
4. Test the tenant's incident intake with 2–3 sample logs

### Incident Family Mapping

Link tenant's incident taxonomy to bounded wedge:

| Tenant Pattern | Maps To | Coverage |
|---|---|---|
| Checkout timeout + retries | INC001 | Runtime-backed |
| DB connection exhaustion | INC002 | Runtime-backed |
| API 5xx spike + rollback | INC003 | Runtime-backed |
| Certificate expiry | Unsupported | Downgraded inference |

## Operator Quickstart

### Starting NEXUS Locally

```bash
# Direct server
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Or via Docker (with runtime relay)
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

### Basic Workflow

1. **Inputs** (`http://localhost:7860/inputs`): Paste raw logs
2. **Incident detail** (auto-redirect): Review triage and investigation packet
3. **Guardian gate**: Approve, block, or request modification
4. **Training** (`http://localhost:7860/training`): View execution outcome and broader ROI

### Navigating Ambiguity

**"Why was this action ranked first?"**
- Check the `weighting_summary` field in candidate fixes
- Look for "runtime-backed" vs "inferred-only" language
- If inferred-only, that's a signal to trigger manual validation or defer to engineering

**"Should I approve this action?"**
- Check Guardian's `risk_class`: high risk requires incident manager
- Review the `residual_risk` field in the top-ranked action
- Look for runtime-backed evidence in REPLICA (resolved > improved > unvalidated)

**"What happens if the incident doesn't match any known family?"**
- NEXUS will still triage and offer inference-based guidance
- Check the `evidence_posture` field — it will be "inferred_only"
- Consider referring to engineering for deeper investigation

## Weekly Pilot Review

### Review Checklist

1. **Incident volume**: How many incidents did NEXUS handle this week?
2. **Support quality**: Did actions match issue families? Did approvals go smoothly?
3. **Engineering feedback**: Any complaints about handoff quality or debugging experience?
4. **Runtime coverage**: What fraction of approvals were runtime-backed vs inferred-only?
5. **Time savings**: Approximate hours saved per incident vs. manual escalation?
6. **Blocker signal**: Is any incident family consistently outside the bounded wedge?

### Scorecard Review

Check the pilot scorecard (available on training page):

- **Incidents handled**: growth trajectory week-over-week
- **Runtime-backed ratio**: percentage with measured runtime validation
- **Triage time saved**: estimated minutes per incident
- **Handoff completion**: percentage of cases that reached engineering
- **Prior incident reuse**: how often memory informs current decisions

### Feedback Loop

Weekly sync should surface:

1. Operator observations on incident classification accuracy
2. Engineering trust signals (or trust gaps) from handoff experience
3. Coverage gaps (incident families consistently outside the wedge)
4. UX pain points or confusing surfaces

## Pilot Closeout

### Closeout Template

Use this template when ending a tenant's pilot:

```
NEXUS Pilot Closeout Report
===========================

Tenant: [Name]
Period: [Start date] to [End date]
Incidents handled: [N]
Runtime-backed: [N] ([%])
Average triage time: [X] minutes

Support Quality Summary
- Issue family coverage: [list confidence by family]
- Support downgrade rate: [%] routed outside bounded wedge
- Guardian approval rate: [%] approved vs blocked
- Engineering feedback: [qualitative summary]

Value Summary
- Support escalations reduced: [estimate]
- Triage time saved: [hours]
- Engineering handoff quality: [feedback]

Recommendation
[ ] Ready for broader rollout (met success criteria)
[ ] Continue with improvements (most criteria met)
[ ] Reassess scope (coverage gaps or trust issues)

Next Steps
- [Action 1]
- [Action 2]
```

## Troubleshooting

### "Runtime replay failed"

1. Check Docker availability: `docker ps`
2. Verify compose contract: `pytest tests/test_replica_runtime.py::test_replica_runner_executes_db_pool_pack -xvs`
3. Check runtime-host logs if using relay
4. Fallback to inference-only triage while replay is being debugged

### "Incident keeps downgrading to inference-only"

1. Confirm incident family mapping is correct
2. Check if tenant service ownership is configured
3. Verify incident logs include expected signals (timeouts, pool exhaustion, 5xx errors)
4. If signals are too weak, consider referring to engineering upfront

### "Engineering feedback is skeptical of the handoff"

1. Review the `residual_risk` posture — if "unvalidated", engineering expectations may be misaligned
2. Check TRACE module recommendations — ensure they're concrete, not generic
3. If runtime was available but not executed, proactively trigger replay to validate
4. Share the "why this action won" explanation to demonstrate evidence weighting

## Maintenance

### Weekly Maintenance Tasks

- Monitor test suite health: `pytest tests/ -q`
- Spot-check fresh incidents: load `/inputs`, review classification
- Review AGENTS.md baseline to catch any regressions

### Monthly Maintenance Tasks

- Review scorecard trend across all tenants
- Audit Guardian approval rates for approval-gate creep
- Refresh tenant owner mappings if teams or services change

### Upgrading to Next Scope Phase

Once a tenant's pilot is stable (60%+ runtime coverage, high engineering trust):

1. Review the next phase plan in docs/
2. Confirm scope additions match bounded roadmap
3. Plan gradual rollout to avoid disrupting pilot stability

## Support Contacts

- **NEXUS owner**: [Owner name and contact]
- **Current pilots**: [Tenant names and contacts]
- **Weekly review meeting**: [Day/time]
