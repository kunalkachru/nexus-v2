# Weekly NEXUS Pilot Review Checklist

Use this checklist in your weekly pilot sync to stay aligned on progress, blockers, and team trust.

The current product can now generate a bounded weekly review packet directly from `Learning & Controls`. Use the generated packet as the meeting pre-read, then use this checklist to discuss the result.

## Before the Meeting (15 min)

### Incident Review

- [ ] Check scorecard on training page for this week's metrics
- [ ] Note incidents handled and runtime-backed ratio
- [ ] Flag any incidents that were downgraded (inference-only or unsupported)
- [ ] Look for patterns: are failures clustered by issue family or by tenant?

### Test Baseline

- [ ] Run `pytest tests/ -q` locally — baseline should be stable
- [ ] Run `npm run browser:verify` — should see 11 passing
- [ ] Spot-check one fresh incident via `/inputs` to confirm classification feels right

### Engineering Feedback Prep

- [ ] Did any engineering teams comment on recent handoffs?
- [ ] Any GitHub/Slack threads about NEXUS guidance quality?
- [ ] Notable trust wins or trust gaps?
- [ ] Any retryable failures, terminal failures, or partial follow-up states that need explanation in the review?

## During the Meeting (30 min)

### Scorecard Review (10 min)

Discuss this week's metrics:

- **Incidents handled**: Growing or stable?
- **Runtime-backed %**: Tracking toward 60%+ goal?
- **Triage time saved**: Realistic estimate? Measurable?
- **Handoff completion rate**: Engineering teams actually executing the recommendations?
- **Prior incident reuse**: Is memory helping or just adding noise?

**Key question**: _Are we delivering measurable value, or does it feel like extra overhead?_

### Coverage Assessment (10 min)

For each incident family:

| Family | This Week | Status | Notes |
|---|---|---|---|
| INC001 (Timeout/Retry) | [N] | [Supported/Degraded/Unsupported] | [Feedback] |
| INC002 (Pool Exhaustion) | [N] | [Supported/Degraded/Unsupported] | [Feedback] |
| INC003 (Deploy Regression) | [N] | [Supported/Degraded/Unsupported] | [Feedback] |
| INC005 (Queue/Worker Backlog) | [N] | [Supported/Degraded/Unsupported] | [Feedback] |
| INC007 (Auth Dependency) | [N] | [Supported/Degraded/Unsupported] | [Feedback] |
| Out-of-scope | [N] | Downgraded | [Feedback] |

**Key question**: _Are we staying inside the bounded wedge, or are cases leaking out as unsupported?_

### Engineering Trust Signal (10 min)

Ask each engineering team:

1. Did NEXUS's recommendations feel concrete and debuggable?
2. Was the "why this action won" explanation clear?
3. Any cases where NEXUS sent you down the wrong path?
4. Would you approve the action without reading the full packet?
5. Any residual risk concerns or unhandled edge cases?

**Key question**: _Do engineering teams feel confident in the handoff, or skeptical?_

## Action Items

### If scorecard is strong (60%+ runtime-backed, high trust):

- [ ] Decide whether the current five-family wedge is strong enough for the next pilot wave
- [ ] Document reusable patterns for ops/engineering handoff
- [ ] Consider pilot readiness for broader rollout

### If scorecard is mixed (30–60% runtime-backed, medium trust):

- [ ] Identify which issue families have weak runtime support
- [ ] Plan targeted improvements to handoff clarity or evidence weighting
- [ ] Schedule deeper dive into low-trust incident families

### If scorecard is weak (<30% runtime-backed, low trust):

- [ ] Pause new scope additions
- [ ] Root-cause coverage gaps: are incidents genuinely outside the wedge, or is NEXUS failing to classify?
- [ ] Assess if pilot should continue or reset
- [ ] Consider referring back to manual triage until coverage improves

## Blockage Signals

Escalate immediately if you see:

- **Engineering refuses to approve**: handoff trust is broken — pause pilot until root-caused
- **Consistent downgrade to unsupported**: incident families are leaking outside bounded scope — reassess coverage
- **Test suite degradation**: baseline regressions indicate product stability issue — fix before continuing
- **Runtime replay failures**: Docker path or compose contracts are broken — needs triage before rollout
- **Repeated duplicate sends**: operators are resending packets without explicit downstream need — clarify duplicate semantics and control usage

## Notes Section

Use this space for week-specific observations:

```
Week of [DATE]:

Scorecard:
- Incidents: [N]
- Runtime-backed: [N] ([%])
- Triage time: [estimate]

Highlights:
- [Notable success or insight]
- [Team feedback]

Blockers:
- [Any issues]

Next steps:
- [Action 1]
- [Action 2]
```

## Recurring Metrics to Track

Keep a running tally across weeks:

| Week | Incidents | Runtime % | Time Saved | Engineering Trust | Notes |
|---|---|---|---|---|---|
| Week 1 | [N] | [%] | [est hrs] | [rating] | |
| Week 2 | [N] | [%] | [est hrs] | [rating] | |
| Week 3 | [N] | [%] | [est hrs] | [rating] | |
| Week 4 | [N] | [%] | [est hrs] | [rating] | |

## Success Criteria Reminder

By end of pilot (4–6 weeks):

- [ ] Runtime-backed incident handling reaches 60%+
- [ ] Engineering team expresses confidence in NEXUS-guided actions
- [ ] Support handoff time is visibly shorter than manual escalation
- [ ] No critical product regressions or stability issues
- [ ] Operational posture (downgrade, unsupported handling) feels honest to all stakeholders

If these are met, recommend progression to next scope phase. If not, document learnings and reset scope.
