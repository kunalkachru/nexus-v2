# NEXUS Pilot Closeout Report

_Use this template at the end of each tenant's evaluation window (typically 4–6 weeks)_

---

## Executive Summary

**Tenant**: [Tenant name]  
**Pilot period**: [Start date] to [End date]  
**Evaluation window**: [4/6/8 weeks]  
**Recommendation**: [ ] Continue → Scope Expansion | [ ] Continue → Same Scope | [ ] Pause & Reassess | [ ] Close

---

## Operational Metrics

### Incident Handling

| Metric | Target | Actual | Status |
|---|---|---|---|
| Incidents handled | 10+ | [N] | [✓/⚠/✗] |
| Runtime-backed ratio | 60%+ | [%] | [✓/⚠/✗] |
| Inference-only ratio | <30% | [%] | [✓/⚠/✗] |
| Unsupported/downgraded | <10% | [%] | [✓/⚠/✗] |

### Quality Metrics

| Metric | Target | Actual | Status |
|---|---|---|---|
| Avg triage time | <10 min | [N] min | [✓/⚠/✗] |
| Handoff approval rate | 70%+ | [%] | [✓/⚠/✗] |
| Engineering feedback | Positive | [Positive/Mixed/Negative] | [✓/⚠/✗] |

### Value Realization

| Metric | Estimate | Confidence |
|---|---|---|
| Support escalations reduced | [N] per week | [High/Medium/Low] |
| Triage time saved | [N] hours/week | [High/Medium/Low] |
| Engineering handoff quality | [Assessment] | [High/Medium/Low] |
| Repeat-incident reuse | [N] cases | [High/Medium/Low] |

---

## Coverage Assessment

### By Incident Family

| Family | Incidents | Supported | Downgraded | Engineering Trust |
|---|---|---|---|---|
| INC001 (Timeout/Retry) | [N] | [N] ([%]) | [N] ([%]) | [High/Med/Low] |
| INC002 (Pool Exhaustion) | [N] | [N] ([%]) | [N] ([%]) | [High/Med/Low] |
| INC003 (Deploy Regression) | [N] | [N] ([%]) | [N] ([%]) | [High/Med/Low] |
| Out-of-scope | [N] | — | [N] ([%]) | N/A |

### Key Observations

- **Strongest family**: [INC001/INC002/INC003] — [confidence level and why]
- **Weakest family**: [INC001/INC002/INC003/Out-of-scope] — [confidence level and why]
- **Surprising insight**: [Any unexpected pattern or learning]

---

## Engineering Trust Feedback

### Structured Feedback

_Collected from 2–3 engineering leaders at the tenant_

**Question 1: Did NEXUS's recommendations feel concrete and actionable?**

Response: [Summary]

Confidence: [High/Medium/Low]

**Question 2: Would you approve a NEXUS action without reading the full packet?**

Response: [Yes/No/Sometimes] — [Explanation]

Confidence: [High/Medium/Low]

**Question 3: Any cases where NEXUS sent you down the wrong path?**

Response: [Case 1: summary and outcome] | [Case 2] | [None]

**Question 4: How is residual-risk framing? Does it feel honest?**

Response: [Assessment]

Confidence: [High/Medium/Low]

**Question 5: What would make you more confident?**

Response: [Suggestions]

### Trust Signal Summary

Based on feedback, engineering teams assess NEXUS as:

- [ ] **Trusted**: "We'd use this for routine incidents without hesitation"
- [ ] **Cautious**: "Helpful, but we verify everything manually still"
- [ ] **Skeptical**: "Too much overhead compared to direct triage"

---

## Operational Posture Assessment

### Evidence Weighting

- **Runtime-backed claims**: [Percentage] of recommendations with measured runtime validation
- **Inference-only clarity**: [Assessment of how clearly inferred-only decisions are labeled]
- **Unsupported downgrade**: [Assessment of whether out-of-scope incidents downgrade cleanly]
- **Honest residual risk**: [Assessment of whether risk posture feels earned, not inflated]

### Product Integrity

- [ ] Product does not overstate capabilities
- [ ] Downgrade behavior feels honest to all stakeholders
- [ ] Runtime evidence weighting is clear and defensible
- [ ] Memory reuse enhances rather than inflates confidence

---

## Success Criteria Evaluation

| Criterion | Status | Evidence |
|---|---|---|
| Runtime-backed handling ≥60% | [Met/Partial/Missed] | [Runtime %: ___] |
| Engineering expresses confidence | [Met/Partial/Missed] | [Trust signal: ___] |
| Triage time visibly shorter | [Met/Partial/Missed] | [Time saved estimate: ___] |
| No critical regressions | [Met/Partial/Missed] | [Incidents/notes: ___] |
| Operational posture is honest | [Met/Partial/Missed] | [Assessment: ___] |

**Overall pass/fail**: [ ] PASSED | [ ] PARTIAL | [ ] FAILED

---

## Recommendation & Next Steps

### If Recommendation is "Continue → Scope Expansion"

Proposed next incident family: [INC or custom]

Rationale:
- [Reason 1]
- [Reason 2]

Timeline: [When to expand]

### If Recommendation is "Continue → Same Scope"

Reasons to maintain current scope:
- [Reason 1]
- [Reason 2]

Focus areas for next cycle:
- [Area 1]
- [Area 2]

### If Recommendation is "Pause & Reassess"

Root causes for pause:
- [Issue 1]
- [Issue 2]

Proposed fixes:
- [Fix 1]
- [Fix 2]

Restart criteria:
- [Criterion 1]
- [Criterion 2]

### If Recommendation is "Close"

Reasons to close:
- [Reason 1]
- [Reason 2]

Learnings for next tenant:
- [Learning 1]
- [Learning 2]

---

## Lessons Learned

### What Worked Well

- [Success 1]
- [Success 2]
- [Success 3]

### What Could Improve

- [Improvement 1]
- [Improvement 2]
- [Improvement 3]

### Surprising Discoveries

- [Discovery 1]
- [Discovery 2]

---

## Appendix: Raw Scorecard Data

_Attach or link the raw scorecard data from the training page for this tenant_

- Start of pilot: [Link or data]
- End of pilot: [Link or data]
- Weekly snapshots: [Link or data]

---

## Sign-Off

**Completed by**: [Name]  
**Date**: [Date]  
**Reviewed by**: [NEXUS owner name]  
**Approved**: [Yes/No]

---

## Distribution

This report should be shared with:

- [ ] Tenant incident commander
- [ ] Tenant engineering leadership
- [ ] NEXUS program owner
- [ ] Product leadership (if scope expansion or rollout being considered)
- [ ] Archive in [shared location]
