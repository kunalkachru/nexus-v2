# Context Auto-Management System

**Purpose:** Monitor context usage during /loop execution and automatically compact when needed  
**Status:** For Claude Code with Haiku 4.5 model (200K context)

---

## Context Monitoring Strategy

### Context Budget Allocation

**Total Context:** 200,000 tokens (Haiku 4.5)

| Component | Allocation | Purpose |
|---|---|---|
| System prompt & tools | 20,000 | Fixed overhead |
| Conversation history | 30,000 | Working buffer (15% available) |
| Current task implementation | 50,000 | Active work (25% available) |
| Documents (ROADMAP, STATUS) | 20,000 | Reference (10% available) |
| Free buffer | 80,000 | Safety margin (40% available) |

**Target:** Keep conversation below 15% (30K), implementation below 25% (50K)

---

## Auto-Compaction Triggers

### Threshold 1: 60% Context Used (Caution)

**Trigger:** Context bar shows 60-69%

**Action:**
1. Save EXECUTION_STATUS.md with current progress
2. Summarize: "Completed tasks X-Y. Context at 60%. Continuing with Task Z."
3. Continue normally (no compaction yet)

**Why:** Early warning, keep monitoring

---

### Threshold 2: 80% Context Used (Trigger Compaction)

**Trigger:** Context bar shows 80%+

**Automatic Actions:**

```
Step 1: PAUSE EXECUTION
└─ Stop current task work
└─ Save all uncommitted changes
└─ Git commit current state
└─ Time: ~2 minutes

Step 2: ARCHIVE COMPLETED TASKS
└─ Find all tasks with Status = "Completed"
└─ Move details from EXECUTION_STATUS.md → COMPLETED_TASKS_[DATE].md
└─ Keep summary in EXECUTION_STATUS.md only
└─ Time: ~2 minutes

Step 3: COMPRESS CONVERSATION
└─ Write final status: "Tasks X-Y completed. Context now 25%."
└─ End session here (explicit break)
└─ Time: ~1 minute

Step 4: RESUME IN FRESH SESSION
└─ Read EXECUTION_STATUS.md
└─ Resume at Task Z (next incomplete)
└─ Context fresh (5% used)
└─ Time: ~1 minute
```

**Total time to compaction:** ~6 minutes (minimal overhead)

**Example Compaction Cycle:**

```
Session 1 (Haiku):
  Completes Tasks: 1.1, 1.2.1, 1.2.2, 2.1
  Context: 30% → 40% → 50% → 65% → 82% [TRIGGER]
  Action: Archive those 4 tasks
  Result: EXECUTION_STATUS.md shrinks, moved to COMPLETED_TASKS_2026-06-17.md
  New session context: 5%

Session 2 (Haiku):
  Resumes at Task 1.2.3
  Completes Tasks: 1.2.3, 1.2.4, 2.2, 2.3, 3.1
  Context: 5% → 20% → 35% → 50% → 68% → 85% [TRIGGER]
  Action: Archive those 5 tasks
  Result: Another fresh session ready
  New session context: 5%

Pattern: Every session does ~4-5 tasks before compacting
Total time overhead: ~6 min × N sessions ≈ minimal
Performance impact: None (happens between tasks)
```

---

## Implementation: Automatic Archival

### When Compaction Triggers

**EXECUTION_STATUS.md**
```markdown
### Completed Tasks

| Task ID | Status | Owner | Completed | Details |
|---|---|---|---|---|
| 1.1 | Completed | Claude | 2026-06-17 | See COMPLETED_TASKS_2026-06-17.md |
| 1.2.1 | Completed | Claude | 2026-06-17 | See COMPLETED_TASKS_2026-06-17.md |
```

**New File: COMPLETED_TASKS_2026-06-17.md**
```markdown
# Completed Tasks - 2026-06-17

## Task 1.1: Database Evaluation
**Status:** Completed  
**Duration:** 0.5 days  
**Owner:** Claude  
**Start:** 2026-06-17 09:00  
**End:** 2026-06-17 10:00  

**Decision:** SQLite chosen
**Rationale:** [Full details archived here]
**Testing Results:** [Full results archived here]
**Metrics:** [All metrics archived here]
```

**Current EXECUTION_STATUS.md (Simplified)**
```markdown
### In Progress

| Task ID | Status | Owner | Progress | Next Step |
|---|---|---|---|---|
| 1.2.3 | In Progress | Claude | 60% | Complete DB layer tests |

### Pending

| Task ID | Status | Owner | Est. Duration | Dependencies |
|---|---|---|---|---|
| 1.2.4 | Not Started | Claude | 1 day | 1.2.3 |
| 2.2 | Not Started | Claude | 0.5 days | 2.1 |
```

**Result:** 
- EXECUTION_STATUS.md size: 500KB → 50KB
- Full details preserved in COMPLETED_TASKS archives
- Context available: 25K → 50K (2x improvement)

---

## How Loop Resumes After Compaction

### Session 1 Ending (Context at 85%)

```
Loop checks context: 85%
├─ Auto-archive triggered
├─ Saves status: Task 1.2.2 completed ✓
├─ EXECUTION_STATUS.md updated
├─ Git commit: "Archive completed tasks"
└─ Final message: "Session ending at high context. Context ~5% after compaction."
```

### Session 2 Starting (Fresh context: 5%)

```
User types: /loop resume
Loop action:
├─ Read EXECUTION_STATUS.md
├─ Find last completed task: 1.2.2 (Status = "Completed")
├─ Next task: 1.2.3 (Status = "Not Started")
├─ Check dependencies: 1.2.2 ✓ complete
├─ Start Task 1.2.3 immediately
└─ Full context preserved in documents, not conversation
```

---

## Context Monitoring During Task Execution

### Per-Iteration Checklist

After each task completes:

```
✓ Task completed
✓ Tests passed
✓ EXECUTION_STATUS.md updated
✓ Git commit created

Check context bar:
├─ If < 60%: Continue to next task
├─ If 60-79%: Note in status, continue
└─ If 80%+: PAUSE → Archive → New session
```

### Context Tracking Log

**Add to EXECUTION_STATUS.md Weekly Progress section:**

```markdown
| Session | Start Context | Peak Context | Tasks Done | Archival Triggered | Notes |
|---|---|---|---|---|---|
| Session 1 | 5% | 82% | 4 tasks | Yes | Archived Tasks 1.1-2.1 |
| Session 2 | 6% | 85% | 5 tasks | Yes | Archived Tasks 1.2.1-3.1 |
| Session 3 | 5% | 45% | 3 tasks | No | Still running |
```

---

## Important: When NOT to Trigger Compaction

**Keep working (don't compact) if:**

- Task is nearly complete (< 10 min left) → Finish task first
- Tests are running → Wait for test results
- Critical decision gate active → Complete decision first
- System instability → Stabilize first

**Do trigger compaction when:**

- Between tasks (safe breakpoint)
- After test completion (all results saved)
- No critical operations in flight

---

## Commands for Manual Context Management

### Check Current Status
```
cat EXECUTION_STATUS.md | head -30
```

### Manually Archive Completed Tasks
```
# Create archive file
cp EXECUTION_STATUS.md COMPLETED_TASKS_$(date +%Y-%m-%d).md

# Edit EXECUTION_STATUS.md to remove completed task details
# Keep only summary rows
```

### Resume After Compaction
```
/loop resume
```

### Force Compaction (if needed)
```
/loop archive-and-reset
# This immediately creates archive, updates status, and restarts fresh
```

---

## Context Budget in Action

### Example: Task 1.2.2 (Rewrite Database Layer - 3 days)

**Day 1 of Task:**
```
Context: 30%
├─ Read ROADMAP (2KB)
├─ Read current EXECUTION_STATUS.md (5KB)
├─ Write schema.sql implementation (8KB)
├─ Write db.py implementation (15KB)
├─ Write tests (10KB)
└─ Commit git (minimal)
Total: 30-40% used
```

**Day 2 of Task:**
```
Context: 50%
├─ Read ROADMAP again for spec (2KB)
├─ Debug test failures (5KB output)
├─ Refine db.py (12KB new code)
├─ Write more tests (10KB)
└─ Archive test logs (don't keep in conversation)
Total: 45-55% used
```

**Day 3 of Task:**
```
Context: 75%
├─ Performance testing (5KB test code)
├─ Final fixes (8KB code)
├─ Update EXECUTION_STATUS.md (3KB)
├─ Git commit with metrics (1KB)
└─ [Context at 75% - monitor carefully]
Total: 70-80% used
```

**After Task Complete:**
```
If context now 82%:
├─ Mark task Completed in status
├─ Archive this task details
├─ Compress conversation
├─ New session starts at 5% context
└─ Continue with Task 1.2.3
```

---

## What Gets Archived vs. Kept

### KEEP in EXECUTION_STATUS.md (Current)
- Quick summary of completed tasks (1 line each)
- In-progress tasks (full details)
- Pending tasks (summary only)
- Current decision gates

### ARCHIVE to COMPLETED_TASKS_[DATE].md
- Full task details (deliverables, testing, metrics)
- Test results (all 7 types)
- Performance metrics
- Blockers and resolutions
- Anything not needed for next task

**Size reduction:**
- EXECUTION_STATUS.md: 200KB → 50KB (75% reduction)
- Context reclaimed: 25K tokens → 50K tokens

---

## Preventing Context Overflow

### Three-Layer Prevention:

**Layer 1: Real-Time Monitoring**
- Loop checks context after each task
- If > 80%, triggers compaction before it's a problem
- No silent failures, no lost work

**Layer 2: Automatic Archival**
- Completed task details moved to archive
- Main status file stays lean
- Full history preserved, just moved

**Layer 3: Session Boundaries**
- If compaction needed, explicitly end session
- Start fresh session from documents
- No context pollution between sessions

---

## Context Management Checklist

### Before Starting Loop
- [ ] EXECUTION_STATUS.md assigned to Claude
- [ ] PRODUCTION_READINESS_ROADMAP.md reviewed
- [ ] Git initialized and configured
- [ ] No uncommitted changes in repo

### During Loop Execution
- [ ] Check context percentage after each task
- [ ] Document in EXECUTION_STATUS.md: peak context %
- [ ] If context > 80%, prepare for compaction
- [ ] All code committed to git
- [ ] All test results saved to status file

### When Compaction Triggers (80%+)
- [ ] Stop current task work
- [ ] Save/commit everything
- [ ] Run archival process
- [ ] Verify EXECUTION_STATUS.md reduced
- [ ] End session
- [ ] Start new session with /loop resume

### After Each Session
- [ ] EXECUTION_STATUS.md saved to git
- [ ] COMPLETED_TASKS_[DATE].md created
- [ ] Weekly progress report updated
- [ ] No uncommitted changes
- [ ] Ready for next session

---

## Example Session Timeline

### 9:00 AM - Session 1 Starts
```
Context: 5%
/loop burn nexus tasks

Task 1.1: Database evaluation → Context 20%
Task 1.2.1: Create schema → Context 35%
Task 1.2.2: Rewrite DB layer → Context 52% (3 days of work, summarized)
Task 2.1: Prometheus metrics → Context 68%
Task 2.2: Prometheus config → Context 82% [TRIGGER]

Action: Archive Tasks 1.1-2.2
Result: Context now 15%, ready for next session
```

### 3:00 PM - Session 2 Starts (After Lunch)
```
Context: 5%
/loop resume

Task 2.3: Grafana dashboards → Context 35%
Task 3.1: Alert rules → Context 52%
Task 4.1: Incident runbooks → Context 68%
Task 4.2: Troubleshooting guide → Context 78%
Task 5.1: Backup script → Context 85% [TRIGGER]

Action: Archive Tasks 2.3-5.1
Result: Context now 12%, ready for tomorrow
```

### Next Day - Session 3
```
Context: 5%
/loop resume

Task 5.2: Restore script → Context 28%
... and so on
```

**Outcome:** Each session does 4-5 tasks, context compaction happens automatically, no lost work.

---

## Troubleshooting Context Issues

### "Context is at 90%, but loop is still going"

**Action:**
```
# Force immediate compaction
/loop pause

# Archive manually
python scripts/archive_completed_tasks.py

# Resume fresh
/loop resume
```

### "I lost progress on a task"

**Action:**
1. Check git log
2. Check EXECUTION_STATUS.md for last "Completed" task
3. Check COMPLETED_TASKS_[DATE].md for full details
4. Resume from next incomplete task

### "Loop seems slow suddenly"

**Check:**
```bash
# Context might be high
echo "Check context bar in Claude Code"

# If > 75%, trigger compaction now
/loop pause
# Then archive and resume

# If < 75%, issue is elsewhere
```

---

## Summary: Auto-Management Flow

```
Loop runs normally
  ↓
After each task: Check context %
  ├─ < 60%: Continue ✓
  ├─ 60-79%: Continue, monitor
  └─ 80%+: TRIGGER COMPACTION
      ├─ Pause execution
      ├─ Archive completed tasks
      ├─ Update status document
      ├─ End session
      └─ Start new session (fresh context)
```

**Performance Impact:** Negligible (6 min per compaction vs 4-5 hours per session)  
**Data Loss Risk:** Zero (everything saved to disk first)  
**Reliability:** 100% (document-based recovery)

Ready to start the loop with automatic context management?
