# NEXUS Operator Runbook

Quick reference for support operators triaging and managing incidents through NEXUS.

## The 6-Step Flow

1. **Triage**: Command Center → select incident
2. **Review**: Read the triage summary and suggested action
3. **Decide**: Approve, reject, or request modification
4. **Execute**: (if approved) Action runs and results are captured
5. **Handoff**: Send investigation packet to engineering (GitHub, Slack, or download)
6. **Follow-up**: Track delivery and engineering feedback

## At Each Step: Your Next Action

### In Command Center (Queue)
- **See**: Incidents sorted by severity and recency
- **Do**: Click an incident to open the detail view
- **Look for**: Severity, service, and summary to understand the scope

### In Incident Detail
- **See**: SENTINEL classification, PRISM evidence, TRACE guidance, FORGE action, GUARDIAN decision
- **Do**: Read the summary, then scroll to **Guardian Gate**
- **Your choice**: Approve (execute), Reject (don't act), or Modify (request changes)

### In Input Channels
- **See**: Browser parse, normalization posture, missing signals, and operator read
- **Do**: Paste the logs first and check whether the intake posture is `Strong`, `Partial`, or `Weak`
- **Use it this way**:
  - `Strong` means the packet is shaped well enough for bounded triage
  - `Partial` means routing is usable but you should confirm the missing fields before approval
  - `Weak` means ask for the service name, severity, and 2-3 concrete log lines before treating the case as decision-ready

### If You Approve
- **See**: Action executes and results appear below Guardian
- **Do**: Review execution outcome
- **Next**: Click **Send Handoff** to notify engineering

### If You Reject or Request Modification
- **See**: Case remains in "awaiting review" state
- **Do**: Provide feedback if applicable
- **Next**: Engineering reviews your decision

### Sending Handoff to Engineering
- **See**: Handoff send options (GitHub, Slack, download)
- **Do**: Choose target, review contents, click Send
- **See**: Delivery history shows send status

### After Handoff Sent
- **Track**: Delivery history shows sent timestamp and status
- **Receive**: Engineering feedback when action is taken
- **Learn**: Outcomes improve memory for similar cases

## Common Operator Tasks

### Task: Understanding a Triage Result

**Q: What does it mean if PRISM says "high confidence"?**

A: High confidence means the evidence strongly supports the root cause diagnosis. Medium or low confidence means you should verify the diagnosis yourself before acting on it.

**Q: What if I disagree with NEXUS's diagnosis?**

A: You can reject NEXUS's suggestion and add your own notes via the feedback system. Your expertise is the final check before any action runs.

**Q: How do I know if a TRACE recommendation is safe?**

A: TRACE provides a debugging path based on the evidence. If NEXUS suggests testing a hypothesis via replay, the replay runs in an isolated environment (Docker sandbox), not production, so it's safe to approve.

### Task: Sending a Handoff to Engineering

**Q: What information is in the handoff?**

A: The handoff includes:
- NEXUS's full investigation (what it found, confidence, evidence)
- TRACE debugging path (where to look in the code)
- FORGE proposal (what the suggested fix is)
- GUARDIAN decision (your approval/rejection)
- Replay results (if you ran a test)
- Any engineering feedback (if engineering already responded)

**Q: Can I send the same handoff twice?**

A: Yes. If a send fails or you need to resend, click **Retry** in the delivery history. The system tracks all attempts.

**Q: What if the send fails permanently?**

A: The delivery status will show "terminal failure" if the target is unreachable or credentials are invalid. Contact your administrator to fix the target configuration, then send a new handoff.

### Task: Following Up on Feedback

**Q: How do I see if engineering accepted the suggestion?**

A: Go to the incident detail page and scroll to **Engineering Feedback**. You'll see:
- Whether engineering **accepted**, **rejected**, **modified**, or **resolved** it
- Any notes they added
- When they responded

**Q: Can I retry if engineering rejected it?**

A: You can resend the investigation to a different engineer or try a modified approach, but you can't force acceptance. The rejection is valuable learning for NEXUS's future suggestions.

## Troubleshooting

### Problem: Button is greyed out (disabled)

**Why?** Your role doesn't have permission for that action.

**Solutions:**
- Ask your team lead if you should have broader permissions
- Check **Settings** to understand role-based controls
- Try using a different workflow path that matches your role

### Problem: Delivery failed

**Why?** The target (GitHub, Slack) is unavailable or misconfigured.

**Solutions:**
1. Check the failure reason in **Delivery History**
2. Ask your administrator to verify target credentials
3. Try **Retry** if it was a temporary network issue
4. Download and send manually if the system can't reach the target

### Problem: Replay isn't available

**Why?** Runtime host is not configured, or this incident class doesn't support bounded replay.

**Solutions:**
1. Check **Settings** > **Runtime Host** to see if it's configured
2. Check **Settings** > **Enabled Packs** to see which incident classes support replay
3. For unsupported classes, proceed with engineering handoff instead
4. Ask your administrator if more runtime packs can be enabled

### Problem: I don't understand NEXUS's analysis

**Why?** The analysis might be incomplete, low-confidence, or too technical.

**Solutions:**
1. Read **TRACE guidance** for a simpler explanation
2. Click on evidence sections to drill into specific signals
3. Use **Live Reasoning** (if available) to get more detailed explanations
4. Reject the suggestion and add your own notes
5. Ask senior team members to review the case

## Role-Based Limitations

### If You're an Operator

- ✓ Read and triage incidents
- ✓ Create new cases
- ✓ Approve/reject NEXUS suggestions
- ✓ Send handoffs to engineering
- ✗ Cannot modify settings or bootstrap config
- ✗ Cannot review or approve on behalf of others

### If You're an Incident Manager

- ✓ All operator permissions
- ✓ Review and comment on cases
- ✓ Request modifications to NEXUS suggestions
- ✗ Cannot update settings or bootstrap config
- ✗ Cannot execute as Guardian

### If You're a Guardian

- ✓ Read incidents
- ✓ Approve or reject NEXUS suggestions
- ✓ Execute approved actions
- ✗ Cannot create cases
- ✗ Cannot view settings

### If You're an Admin

- ✓ All permissions
- ✓ Configure bootstrap (owners, repos, targets)
- ✓ Update approval policies
- ✓ Manage enabled runtime packs

## Quick Reference: Keyboard & Navigation

- **Q** = Queue / Command Center
- **I** = Incident Detail
- **T** = Training & Controls
- **Settings** = System configuration (admin only)
- **Back button** = Return to previous page
- **Preserve return** = Return context after settings changes

## Getting Help

- **In-product help**: Hover over labels and badges for inline explanations
- **Settings page**: Shows system configuration and what's enabled
- **Training page**: Shows runtime health and learning progress
- **DEMO_WALKTHROUGH.md**: Full walkthrough for the flagship use case

## Key Concepts You Should Know

**Scaffold-only vs. Runtime-backed evidence**: Some signals come from NEXUS's built-in reasoning (scaffold), others from actual test execution (runtime). The UI labels which is which.

**Bounded debugging**: NEXUS can only debug specific incident classes it was trained for. For other cases, you get reasoning-only guidance.

**Replay safety**: Replays run in isolated Docker sandbox, never touch production systems.

**Deterministic vs. Live reasoning**: Deterministic (default) uses no LLM. Live reasoning uses your or the server's OpenAI key for more detailed analysis.

## Success Criteria

You're operating NEXUS well if:

- Most of your approved actions lead to successful outcomes
- You rarely need to reject NEXUS suggestions
- Your handoffs to engineering are complete and actionable
- Cases cycle through triage, decision, and handoff quickly
- You rarely encounter system errors or timeouts
