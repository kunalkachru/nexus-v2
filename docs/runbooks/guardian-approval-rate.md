# Runbook: GUARDIAN Approval Rate Below Baseline

**Alert:** `GuardianApprovalRateLow`  
**Severity:** MEDIUM  
**On-Call Owner:** GUARDIAN Team + Backend Team  
**Estimated Resolution Time:** 15-30 minutes

---

## Symptoms

- GUARDIAN approval rate dropped to <50% (threshold)
- Prometheus metric: `(rate(nexus_guardian_decisions_total{decision="approve"}[1h]) / rate(nexus_guardian_decisions_total[1h])) < 0.5`
- Sustained for >30 minutes
- Possible causes:
  - New validation rule too strict
  - GUARDIAN model degradation or bias
  - Policy change
  - Quality of incident submissions decreased

---

## Immediate Actions (< 5 min)

1. **Verify this is a real issue, not noise**
   ```bash
   # Check approval rate trend
   sqlite3 /path/to/nexus.db "SELECT decision, COUNT(*) as count FROM 
     (SELECT decision FROM incidents WHERE created_at > datetime('now','-1 hour'))
     GROUP BY decision;"
   
   # Calculate approval % manually
   # approved / (approved + rejected + other)
   ```

2. **Check if there was a recent GUARDIAN rule change**
   ```bash
   git log --oneline -20 -- server/guardian.py
   git log --oneline -20 -- docs/guardian-rules.md
   ```
   - Did a new validation rule get added?
   - Did decision logic change?

3. **Sample recent GUARDIAN decisions to understand the rejections**
   ```bash
   sqlite3 /path/to/nexus.db "SELECT incident_id, decision, decision_reason FROM incidents 
     WHERE created_at > datetime('now','-30 minutes') AND decision IS NOT NULL 
     ORDER BY created_at DESC LIMIT 20;"
   ```
   - Look for patterns: same rejection reason repeated?
   - Or varied reasons (suggests quality drop)?

4. **Check if incident quality changed**
   ```bash
   # Sample incidents submitted in last hour
   sqlite3 /path/to/nexus.db "SELECT incident_id, severity, family, raw_text_length FROM incidents 
     WHERE created_at > datetime('now','-1 hour') ORDER BY created_at DESC LIMIT 50;"
   
   # Did submissions become shorter, less detailed, or have lower severity?
   ```

---

## If Immediate Actions Don't Work (5-15 min)

1. **Check GUARDIAN model/service health**
   ```bash
   # If GUARDIAN is an external service
   curl -s https://guardian-api.company.com/health
   
   # Check response time
   time curl -s https://guardian-api.company.com/decision -X POST -d '{"test": true}'
   
   # Check error rate in logs
   grep "GUARDIAN.*error\|GUARDIAN.*timeout" /var/log/nexus/app.log | wc -l
   ```

2. **Check if GUARDIAN was redeployed or rules changed**
   ```bash
   # Check deployment log
   git log --oneline -20 | grep -i guardian
   
   # If code changed, review the diff
   git show <commit-hash>:server/guardian.py | head -100
   ```

3. **Manually test GUARDIAN decision logic**
   - Take a recent rejected incident
   - Trace through the decision logic manually
   - Try modifying one field and see if it would be approved

4. **Check for side effects from other changes**
   ```bash
   # Recent deployments in general
   git log --oneline -10
   
   # Did validation rules change in Input Validation layer?
   git log -p --follow -S "severity\|guardian_decision" | head -50
   ```

---

## If Still Below Baseline (15+ min)

1. **Assess business impact**
   - How many incidents are being rejected inappropriately?
   - Are users frustrated by rejections?
   - Is the system safer with stricter rules, even if baseline drops?

2. **Options**

   **Option A: Revert to previous behavior**
   ```bash
   git revert <commit-hash>  # Revert the change that broke it
   docker restart nexus-app
   # Monitor approval rate for 30 min
   ```

   **Option B: Adjust threshold**
   - If new baseline is acceptable (>40%, >30%), adjust alert threshold
   - Update alert rule in `deployment/prometheus/alerts.yml`

   **Option C: Investigate root cause and fix**
   - If it's the incident quality, work with users to improve submissions
   - If it's GUARDIAN rules, refine the rules to be less strict

3. **Escalation**
   - Slack: `@guardian-team`
   - If user impact: `@product`
   - Discuss: is the lower approval rate acceptable or do we need to roll back?

---

## Post-Incident

- [ ] Determine if the change was intentional or accidental
- [ ] Document the new baseline (if intentional)
- [ ] Update alert threshold if new baseline is stable
- [ ] Review GUARDIAN rules for any overly-strict conditions
- [ ] Create feedback loop: collect user reactions to increased rejections
- [ ] If GUARDIAN improvement needed: create ticket for model/rule refinement

---

## Prevention

- Test rule changes in staging with historical data first
- Monitor approval rate baseline continuously
- Set alerts for both "too low" AND "unexpectedly high" (quality regression)
- Require approval from product/legal before significant rule changes
- Maintain clear documentation of what triggers rejection

---

## GUARDIAN Baseline (Production Target)

- Approval rate: 70-80% (rejection of ~20-30% of incidents is normal)
- If <50%: alert and investigate
- If >90%: may be too permissive, missing quality issues

---

## Contact & Escalation

- **GUARDIAN Team:** See wiki
- **Product/Policy Owner:** If threshold needs adjustment
- **Backend Team Lead:** Implementation questions
