# NEXUS Operator Runbook

Quick reference guide for operators using NEXUS to triage and manage support cases.

## Getting Started as an Operator

### What You'll Do

1. **Triage** incoming incidents from the queue
2. **Review** NEXUS analysis and suggestions
3. **Decide** whether to approve, modify, or reject the suggested action
4. **Execute** approved actions (if permitted by your role)
5. **Handoff** to engineering with all the investigation details
6. **Follow up** on outcomes

### First Steps

1. Navigate to **Command Center** (Queue)
2. Select an incident from the list
3. Read the incident detail page to understand what NEXUS found
4. Review the suggested Guardian decision
5. Apply your judgment and approve or reject

## The Core Workflow

### Step 1: Triage in the Queue

- **Command Center** shows your incident queue
- Items are sorted by severity and recency
- Click an incident to open the detail view
- Look at the **triage summary** to understand what happened

### Step 2: Review NEXUS Analysis

The incident detail page shows:

- **SENTINEL classification**: What kind of problem is this?
- **PRISM evidence**: What specific evidence points to the root cause?
- **TRACE guidance**: Where in your codebase should you look?
- **FORGE proposal**: What's the suggested fix or investigation?
- **GUARDIAN gate**: Is it safe to execute this suggestion?

### Step 3: Make a Decision

For each incident, you choose:

- **Approve**: Execute the suggested action
- **Modify**: Request changes before execution
- **Reject**: Don't execute (but keep the investigation for reference)

### Step 4: Execute or Handoff

- **If approved**: The action executes (replay testing or otherwise), and results are captured
- **If rejected**: The case moves to learning without execution
- **Either way**: You can handoff the full investigation packet to engineering

### Step 5: Send to Engineering

Click **Send Handoff** to export the complete investigation:

1. Choose target: GitHub, Slack, or download
2. Review what's being sent (debugging path, evidence, Guardian decision)
3. Click Send

The handoff includes everything engineering needs to understand the issue without re-running your triage.

### Step 6: Track Outcomes

After sending to engineering:

- View **delivery history** to see if the send succeeded
- Check **engineering feedback** section once they respond
- Use outcomes to improve NEXUS memory for similar future cases

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
