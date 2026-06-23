# NEXUS Operations Handoff Procedures

**Document Version:** 1.0  
**Last Updated:** 2026-06-17  
**Audience:** DevOps Lead, Operations Team, Engineering Lead  
**Purpose:** Step-by-step procedures for handing NEXUS operations to the ops team  
**Duration:** 1 day (8 hours)

---

## Overview

After 24-hour production monitoring (Task 8.2) is complete, we transition operational ownership to the operations team. This handoff ensures:

1. **Ops team understands** the entire system
2. **Escalation paths** are confirmed and tested
3. **All documentation** is reviewed and approved
4. **First on-call shift** is successful
5. **Weekly syncs** are scheduled

---

## Pre-Handoff Preparation (Day Before)

### DevOps/Engineering Preparation

- [ ] Schedule handoff meeting (4-8 hours, all team members)
- [ ] Verify 24-hour monitoring completed successfully
- [ ] Collect all documentation into one location
- [ ] Print key runbooks (for reference during handoff)
- [ ] Test all escalation contact numbers
- [ ] Prepare demo/sandbox environment (for hands-on practice)
- [ ] Review any issues from 24-hour monitoring
- [ ] Update contact information (especially phone numbers)

### Ops Team Preparation

- [ ] Attend pre-handoff briefing (30 minutes)
- [ ] Review monitoring playbook (24-hour-playbook.md)
- [ ] Review alert response procedures (alert-response-procedures.md)
- [ ] Ensure access to:
  - [ ] Grafana dashboards (username/password setup)
  - [ ] Prometheus (query access)
  - [ ] Service logs (Docker/systemd access)
  - [ ] Incident documentation system
  - [ ] On-call scheduling tool
- [ ] Prepare notebook for questions

---

## Handoff Day Schedule

### Phase 1: Kickoff & Context (60 minutes)

**Time Allocation:** 1 hour

**Participants:**
- DevOps Lead
- Backend Lead
- Ops Team Lead
- 2-3 Ops Engineers

**Agenda:**

**1. Welcome & Objectives (10 minutes)**
- Explain what handoff means: "Ops now owns the service day-to-day"
- Explain engineering role: "Available for escalations, but not involved in routine operations"
- Set expectations: "We'll train you thoroughly. You'll be ready."

**2. 24-Hour Monitoring Summary (20 minutes)**
- Review what happened during 24-hour monitoring
- Discuss any issues encountered
- Explain how they were resolved
- Key learning: "Here's what to watch for"

**3. System Architecture Overview (20 minutes)**
- Walk through SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN pipeline
- Explain data flow: "Logs come in, analysis happens, recommendations come out"
- Explain what each stage does and why it matters
- Key files: the SQLite incident store at `artifacts/incidents.json`, audit logs, backups

**4. On-Call Expectations (10 minutes)**
- What does "on-call" mean?
  - Respond to alerts within 5-30 minutes (depends on severity)
  - Investigate root cause
  - Fix or escalate
  - Document everything
- Time commitment: "You'll be paged ~1-2 times per week (average)"
- Rest assured: "You're never alone; escalation is always an option"

**Sign-Off:**
- [ ] Ops team understands objectives
- [ ] Questions answered
- [ ] Ready to proceed

---

### Phase 2: Operations Procedures (90 minutes)

**Time Allocation:** 1.5 hours

**Focus:** How to operate the service day-to-day

**Part A: Starting/Stopping Service (20 minutes)**

**Live Demo + Hands-On Practice:**

```bash
# Step 1: Show how service is running
docker ps | grep nexus
systemctl status nexus

# Step 2: Show logs (what to look for)
docker logs -f nexus-prod
# Point out: startup messages, metric collection confirmation

# Step 3: Stop service
docker stop nexus-prod
# Wait 5 seconds
docker ps | grep nexus  # Should be gone

# Step 4: Start service
docker start nexus-prod
docker logs -f nexus-prod  # Show startup sequence

# Step 5: Verify health
sleep 10
curl http://localhost:7860/health | jq .
```

**Have Ops Team Practice (10 minutes):**
- [ ] Ops engineer #1 stops the service
- [ ] Ops engineer #2 starts the service
- [ ] Ops engineer #3 verifies health
- [ ] Repeat until confident

**Part B: Checking Logs (20 minutes)**

**Teach Them to Read Logs:**

```bash
# Daily log check
tail -100 /var/log/nexus.log

# Look for:
# - INFO messages: normal operation
# - WARNING messages: something unusual but handled
# - ERROR messages: something failed (investigate)
# - CRITICAL messages: system-level failure

# Search for specific issues
grep -i "error" /var/log/nexus.log | tail -20
grep -i "database" /var/log/nexus.log
grep -i "timeout" /var/log/nexus.log

# Time-based search
tail -f /var/log/nexus.log  # Watch in real-time
journalctl -u nexus --since "2 hours ago"  # Last 2 hours
```

**Practice Scenario:**
- Inject an error into logs (or use old error log)
- Have ops team find and interpret it
- Verify they understand what each error means

**Part C: Monitoring Dashboards (20 minutes)**

**Grafana Dashboard Tour:**

```
Go to http://localhost:3000

Dashboard 1: Health Dashboard
- Green = healthy
- Yellow = warning
- Red = alert
Show each panel and what it means

Dashboard 2: Performance Dashboard
- Latency metrics
- Throughput metrics
- Resource usage

Dashboard 3: Errors Dashboard
- Error rates
- Error types
- Error trends
```

**Interactive Exercise:**
- [ ] Have ops team member #1 open Grafana
- [ ] Show them where each metric is
- [ ] Have member #2 find specific metric values
- [ ] Practice reading and interpreting panels
- [ ] Zoom/filter exercise: "Show me last 6 hours of latency"

**Part D: Alert Notifications (20 minutes)**

**Alert System Setup:**

```
Verify each notification channel:
- Slack: Does op engineer get @mention when alert fires?
- PagerDuty: Does phone number get correct information?
- Email: Is distribution list correct?

Test each channel:
- Trigger a test alert (if possible)
- Have ops team verify they received notification
- Practice responding (acknowledge alert)
```

**Practice Scenario:**
- Simulate an alert firing
- Have ops team respond to it
- Verify they follow the Alert Response Runbook correctly

**Sign-Off:**
- [ ] Ops team can start/stop service
- [ ] Ops team can read and interpret logs
- [ ] Ops team can navigate Grafana
- [ ] Ops team can receive and respond to alerts

---

### Phase 3: Incident Response Procedures (90 minutes)

**Time Allocation:** 1.5 hours

**Focus:** What to do when something breaks

**Part A: Run Through All 6 Runbooks (60 minutes)**

For each of the 6 incident response runbooks:

**Example: Runbook 1 "Service Not Responding"**

1. **Present the Runbook (5 minutes)**
   - Show the actual runbook document
   - Explain when to use this runbook (trigger: health check fails)
   - Walk through decision tree

2. **Simulate the Incident (5 minutes)**
   - Have someone stop the service
   - "It's 3 AM, you wake up to alert: service down"
   - Hand ops engineer the runbook

3. **Watch Them Execute (5 minutes)**
   - Let them follow runbook steps
   - Don't help (let them figure it out)
   - Intervene only if truly stuck

4. **Debrief (5 minutes)**
   - "Did you follow the runbook?"
   - "What did you find?"
   - "How would you fix it?"
   - "Do we need to escalate?"

**Repeat for all 6 runbooks:**
- Runbook 2: High Error Rate
- Runbook 3: Slow Performance
- Runbook 4: Metrics Not Collecting
- Runbook 5: Database Corrupt
- Runbook 6: Backup Failed

**Sign-Off:**
- [ ] Ops team practiced all 6 runbooks
- [ ] Each member executed at least 2 runbooks
- [ ] They understand escalation criteria
- [ ] Questions answered

**Part B: Postmortem Procedure (10 minutes)**

**Teach Them the Postmortem Process:**

When any incident occurs (during monitoring or after), ops team must document it:

```
For each incident:
1. WHAT HAPPENED? (Symptom)
2. WHY DID IT HAPPEN? (Root cause - investigate)
3. HOW DID WE FIX IT? (Resolution steps)
4. HOW TO PREVENT NEXT TIME? (Improvement)
```

**Show them the postmortem template** (postmortem-template.md)

**Practice Scenario:**
- Simulate an incident
- Have ops team write the postmortem
- Review together for accuracy and completeness

**Part C: When to Escalate (20 minutes)**

**Teach Clear Escalation Criteria:**

```
ESCALATE TO BACKEND LEAD IF:
- Database errors or corruption
- Any logic error in the system
- Performance issue you can't explain
- Data loss suspected

ESCALATE TO DEVOPS LEAD IF:
- Infrastructure issues (CPU, memory, disk)
- Container/Docker issues
- Backup/restore problems
- Monitoring/metrics not working

ESCALATE TO ENGINEERING MANAGER IF:
- Multiple critical issues
- Outage > 1 hour
- Data loss confirmed
- Customer-facing impact
- Any CRITICAL severity alert
```

**Practice Scenarios:**
- Scenario 1: "Database connection failed" → Backend Lead
- Scenario 2: "Server out of memory" → DevOps Lead
- Scenario 3: "Service down for 2 hours" → Engineering Manager

**Sign-Off:**
- [ ] Ops team knows how to write postmortems
- [ ] Ops team knows escalation criteria
- [ ] Ops team knows who to call for each issue type

---

### Phase 4: Escalation Chain & Engineering Contact (60 minutes)

**Time Allocation:** 1 hour

**Part A: Test Escalation Paths (30 minutes)**

**For Each Escalation Level:**

1. **Backend Lead**
   - Name: _________________
   - Email: _________________
   - Phone: _________________
   - Best time to reach: _________________
   - When to contact: database/logic issues
   - [ ] Phone call test completed (actually call them)
   - [ ] Confirmed they're available

2. **DevOps Lead**
   - Name: _________________
   - Email: _________________
   - Phone: _________________
   - Best time to reach: _________________
   - When to contact: infrastructure issues
   - [ ] Phone call test completed
   - [ ] Confirmed they're available

3. **Engineering Manager**
   - Name: _________________
   - Email: _________________
   - Phone: _________________
   - Escalation policy (when to call):
     - Critical issues only
     - Outages > 1 hour
     - Data loss
     - Customer impact
   - [ ] Phone call test completed
   - [ ] Confirmed they're available

**Part B: On-Call Rotation Setup (20 minutes)**

**Confirm:**
- [ ] On-call rotation schedule created
- [ ] Each ops engineer assigned shifts (typically 1 week each)
- [ ] Secondary on-call assigned (for backup)
- [ ] Escalation contacts provided
- [ ] Phone numbers verified
- [ ] Time zones understood (especially if distributed team)

**Schedule First Week:**
```
Primary on-call: _________________ (Mon-Fri)
Backup on-call: _________________ (Mon-Fri)
Primary on-call: _________________ (Sat-Sun)
Backup on-call: _________________ (Sat-Sun)
```

**Part C: Weekly Sync Meetings (10 minutes)**

**Explain Weekly Sync Purpose:**
- Review incidents from past week
- Discuss improvements
- Answer questions from ops team
- Brief on upcoming changes
- Keep engineering and ops aligned

**Schedule First 4 Weeks:**
- [ ] Week 1 sync: _______ (date/time)
- [ ] Week 2 sync: _______ (date/time)
- [ ] Week 3 sync: _______ (date/time)
- [ ] Week 4 sync: _______ (date/time)

**Standing meeting (going forward):**
- [ ] Same day/time each week: _______ @ _______
- [ ] Duration: 60 minutes
- [ ] Attendees: Ops lead + 1-2 engineers, Backend lead, DevOps lead

**Sign-Off:**
- [ ] Escalation chains tested
- [ ] All contacts confirmed reachable
- [ ] On-call rotation setup
- [ ] Weekly syncs scheduled

---

### Phase 5: Documentation Handoff (60 minutes)

**Time Allocation:** 1 hour

**Part A: Documentation Inventory (30 minutes)**

**Verify ops team has received:**

- [ ] **Master Operator Guide** (ops-team-training-guide.md)
  - Location: docs/internal/
  - How to read: Read sections 1-5 in order
  - Reference: Always keep accessible

- [ ] **Runbooks** (docs/runbooks/)
  - 6 incident response runbooks
  - Troubleshooting guide
  - Each runbook reviewed

- [ ] **Monitoring Materials** (docs/internal/)
  - 24-Hour monitoring playbook
  - Alert response procedures
  - Baseline metrics reference

- [ ] **Deployment & Rollback** (docs/internal/)
  - Production deployment guide
  - Rollback procedures (for emergencies)

- [ ] **Disaster Recovery** (docs/internal/)
  - Backup procedures
  - Restore procedures
  - DR drill playbook

- [ ] **Dashboards** (Grafana)
  - Access credentials setup
  - Dashboard guide
  - Metric interpretations

- [ ] **Contact Information**
  - Engineering escalation list
  - Customer contacts
  - On-call rotation

**Part B: Documentation Q&A (20 minutes)**

**For each documentation category:**
- Have ops team member explain what they understand
- Ask them: "If [incident occurs], which doc would you use?"
- Verify they know where to find things
- Make sure they can navigate the documentation

**Example Questions:**
- "The service is slow. Which runbook would you look at?"
- "Backup failed. Where do you find the restore procedure?"
- "Metrics stopped flowing. What's your first diagnostic step?"
- "We need to escalate. Who do you call and for what issue?"

**Part C: Documentation Sign-Off (10 minutes)**

**Each ops team member must sign off:**

```
I have received the following documentation:
- [ ] Master Operator Guide
- [ ] Incident Response Runbooks (6)
- [ ] Monitoring Playbook
- [ ] Alert Response Procedures
- [ ] Deployment & Rollback Procedures
- [ ] Disaster Recovery Procedures
- [ ] Grafana Dashboard Guide
- [ ] Contact Information & Escalation Policy

I understand how to use each document and know where to find them.

Signed: ___________________ Date: __________
```

**Sign-Off:**
- [ ] All documentation provided
- [ ] All ops engineers confirm understanding
- [ ] Copies distributed (print + digital)
- [ ] Access verified (can find docs when needed)

---

### Phase 6: First On-Call Shift (120 minutes)

**Time Allocation:** 2 hours

**Objective:** First ops engineer takes on-call while being observed

**Setup:**

1. **Select Primary Engineer** for first shift (e.g., Ops Engineer #1)
2. **Schedule Observers:**
   - DevOps Lead (to help if stuck)
   - Backend Lead (for escalation practice)
   - Another ops engineer (learns by watching)
3. **Create Safe Test Environment:**
   - Simulate 2-3 alerts firing (or use test scenario)
   - Service is running normally (no real incidents)
   - Use sandbox/staging if available (not production)

**First Shift Schedule:**

**Hour 1: Baseline & Monitoring Setup**
- [ ] Engineer logs in to monitoring systems
- [ ] Verifies health check
- [ ] Checks all 8 metrics are green
- [ ] Sets up alerts/notifications
- [ ] Takes baseline measurements
- [ ] Reads monitoring playbook one more time

**Hour 2: Simulated Incidents**
- Scenario 1: "Alert fires: High Auth Failures"
  - [ ] Engineer gets notification
  - [ ] Finds alert response procedure
  - [ ] Follows steps to diagnosis
  - [ ] Documents findings
  - [ ] Determines: resolve or escalate?

- Scenario 2: "Alert fires: Database Latency High"
  - [ ] Repeats process
  - [ ] May escalate to Backend Lead (if needed)
  - [ ] Documents resolution

- Scenario 3: "Alert fires: Backup Failed"
  - [ ] Follows backup failure runbook
  - [ ] Attempts fix
  - [ ] Documents outcome

**Observers Watch For:**
- Does engineer follow procedures?
- Do they escalate when appropriate?
- Do they document correctly?
- Are they confident?

**Debrief After Hour 2:**

1. **What Went Well:**
   - [ ] Engineer was prepared
   - [ ] Procedures were clear
   - [ ] Escalation worked
   - [ ] Documentation was good

2. **What to Improve:**
   - [ ] Any confusion?
   - [ ] Any missed steps?
   - [ ] Need additional training?

3. **Ready for Real On-Call:**
   - [ ] Yes, engineer is ready
   - [ ] No, needs more practice (schedule additional training)

**Sign-Off:**
- [ ] First on-call shift completed successfully
- [ ] Engineer confident in procedures
- [ ] Observers confirmed readiness
- [ ] Ready for real production on-call

---

## Post-Handoff Checklist

**Immediately After Handoff (End of Day):**

- [ ] All ops team members trained
- [ ] All documentation distributed
- [ ] All escalation paths tested
- [ ] On-call rotation confirmed
- [ ] Weekly syncs scheduled
- [ ] First shift completed successfully

**Follow-Up (48 Hours After):**

- [ ] Debrief meeting with ops team
- [ ] Q&A for questions that arose
- [ ] Any adjustments to procedures?
- [ ] Any additional training needed?

**Follow-Up (1 Week After):**

- [ ] First weekly sync meeting held
- [ ] Review incidents from first week (if any)
- [ ] Ops team confidence level: _______ (1-10)
- [ ] Any operational issues to address?

**Follow-Up (1 Month After):**

- [ ] Ops team running smoothly
- [ ] Incident response time average: _______ minutes
- [ ] No escalations that were avoidable
- [ ] Customer satisfaction confirmed
- [ ] Ready for engineering to step back fully

---

## Handoff Sign-Off Form

**Handoff Completion Confirmation**

| Item | Owner | Sign-Off | Date |
|------|-------|---------|------|
| Phase 1: Context & Objectives | DevOps Lead | ☐ | |
| Phase 2: Operations Procedures | DevOps Lead | ☐ | |
| Phase 3: Incident Response | Backend Lead | ☐ | |
| Phase 4: Escalation & On-Call | DevOps Lead | ☐ | |
| Phase 5: Documentation | DevOps Lead | ☐ | |
| Phase 6: First On-Call Shift | All Observers | ☐ | |

**Ops Team Confirms Understanding**

- [ ] Ops Team Lead confirms team is ready
- [ ] Each engineer has signed off on competency
- [ ] All procedures understood
- [ ] All documentation accessible

**Engineering Confirms Support**

- [ ] Backend Lead available for escalations
- [ ] DevOps Lead available for escalations
- [ ] Engineering Manager on-call for critical

**Handoff Complete:** YES / NO

**Date Completed:** __________________

**Handoff Facilitator:** __________________

**Ops Team Lead:** __________________

**Backend Lead:** __________________

**DevOps Lead:** __________________

---

## Next Steps After Handoff

**Ops Team Owns NEXUS**

Going forward:
- Ops team monitors production 24/7
- Engineering available for escalations
- Weekly syncs to stay aligned
- Monthly reviews of operations

**Engineering Team Transitions**

- Move to new features/improvements
- Respond to escalations from ops
- Monthly review of production issues
- Annual security audit

**Customer Communication**

```
"NEXUS is now in production operations.

Supported by: [Ops Team Names]
Escalation: [Backend Lead], [DevOps Lead]
Status Page: [URL]
Support Email: [Email]

For production issues, please contact [ops-contact].
For feature requests, please contact [product-contact]."
```

---

**Document Owner:** DevOps Lead  
**Last Updated:** 2026-06-17  
**Next Review:** 1 month after handoff
