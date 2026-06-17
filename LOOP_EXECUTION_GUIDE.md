# NEXUS Loop Execution Guide

**Purpose:** Continuous task automation with persistent state across sessions and agents

---

## Quick Start: Running the Loop

### One-Time Setup

1. **Review the Documents:**
   - `PRODUCTION_READINESS_ROADMAP.md` - What needs to be done
   - `EXECUTION_STATUS.md` - Current progress and testing requirements

2. **Assign Task Owners** in EXECUTION_STATUS.md:
   - Update [TBD] fields with actual team member names
   - Or start with just yourself to test the loop

3. **Create a Loop Start Script** (optional):
   ```bash
   # ~/.claude/nexus-loop-start.sh
   #!/bin/bash
   cd /Users/kunalkachru/Documents/nexus-v3
   echo "Starting NEXUS production readiness loop..."
   echo "Reference documents:"
   echo "  - PRODUCTION_READINESS_ROADMAP.md (what to build)"
   echo "  - EXECUTION_STATUS.md (current progress)"
   echo ""
   ```

### Starting the Loop in Claude Code

**In Claude Code terminal, type:**

```
/loop burn nexus production readiness tasks following PRODUCTION_READINESS_ROADMAP.md and EXECUTION_STATUS.md, updating status with testing metrics after each task
```

**What this does:**
- Starts a self-paced loop (no fixed interval)
- Each iteration:
  1. Reads EXECUTION_STATUS.md
  2. Finds next "Not Started" task
  3. Checks dependencies
  4. Executes task
  5. Runs all testing (unit, integration, E2E, browser)
  6. Updates EXECUTION_STATUS.md with results
  7. Moves to next task

---

## Loop Iteration Workflow

### Per-Task Execution (15-30 min typical)

```
START ITERATION
│
├─ 1. READ STATUS
│  └─ Load EXECUTION_STATUS.md from disk
│     Get current progress
│     Identify next task
│
├─ 2. CHECK DEPENDENCIES
│  └─ Verify all "Depends On" tasks marked "Completed"
│     If blocked: wait or escalate (don't proceed)
│
├─ 3. EXECUTE TASK
│  ├─ Read task details from EXECUTION_STATUS.md
│  ├─ Read implementation details from PRODUCTION_READINESS_ROADMAP.md
│  ├─ Write/edit code files
│  ├─ Create tests
│  └─ Commit changes (git)
│
├─ 4. RUN TESTS (All 7 types)
│  ├─ Unit tests (pytest / unittest)
│  ├─ Integration tests (full setup)
│  ├─ Performance tests (latency, throughput)
│  ├─ Regression tests (existing features)
│  ├─ E2E tests (full workflow)
│  ├─ Browser/UI tests (Playwright manual or automated)
│  └─ Code review (peer or AI review)
│
├─ 5. UPDATE DOCUMENTATION
│  ├─ Code comments
│  ├─ Docstrings
│  ├─ Architecture docs
│  └─ User guides
│
├─ 6. UPDATE STATUS DOCUMENT
│  ├─ Task Status: "Not Started" → "Completed"
│  ├─ Fill all [TBD] fields with actual metrics
│  ├─ Document any blockers
│  ├─ Record test results
│  ├─ Record effort spent
│  └─ Save file
│
└─ END ITERATION
   Wait for next iteration signal (event or timeout)
```

---

## Context Management Strategy

**Problem:** Context hits 100% and session freezes  
**Solution:** Keep conversation context small, let documents grow

### Strategy 1: Use Documents as State, Not Conversation

❌ **Wrong Way:**
```
User: How's the loop going?
Agent: [Repeats last 50 tasks completed, metrics, errors, everything]
Context: 80% and growing
```

✅ **Right Way:**
```
User: How's the loop going?
Agent: Task 1.2.2 completed, 4 tests passed. Next: Task 1.2.3.
       Full status in EXECUTION_STATUS.md (line 142-200).
Context: 5% used
```

### Strategy 2: Use Agent Forks for Long Tasks

For any task > 2 hours of implementation:

```python
# In main loop agent:

# Task is long, fork a worker
Agent({
    subagent_type: "fork",
    name: "task-1.2.2-worker",
    description: "Execute Task 1.2.2: Rewrite Database Layer",
    prompt: """
    Execute Task 1.2.2 from PRODUCTION_READINESS_ROADMAP.md.
    Update EXECUTION_STATUS.md with results when done.
    Run all 7 test types before completion.
    """
})

# Fork completes in background
# Main agent continues with coordination
# Context stays clean
```

**Why this works:**
- Fork inherits full context (knows about task)
- Fork runs in background (you can keep chatting)
- Fork updates status document directly
- Main conversation doesn't accumulate implementation details
- When fork finishes, you get a summary, not a dump

### Strategy 3: Archive Completed Tasks

**Weekly, move completed tasks to archive:**

```bash
# Create COMPLETED_TASKS_WEEK1.md
# Move Task 1.1 details there
# Keep EXECUTION_STATUS.md summary-only
```

Current EXECUTION_STATUS.md size: ~50KB (manageable)
After 50 tasks completed: Could grow to 250KB (still manageable)

### Strategy 4: Minimal Context Reads

❌ **Wrong:**
```
# Every iteration
READ ENTIRE EXECUTION_STATUS.md
READ ENTIRE ROADMAP
[This adds 50KB to context each iteration]
```

✅ **Right:**
```
# Every iteration
READ ONLY next 3 tasks from EXECUTION_STATUS.md (3KB)
[Minimal context impact]

# Store working directory state in task status file, not conversation
```

### Strategy 5: Use Session Boundaries

**Session 1 (2 hours):**
- Completes Tasks 1.1, 2.1, 2.2
- Saves full progress to EXECUTION_STATUS.md
- Session ends

**Session 2 (2 hours):**
- Reads EXECUTION_STATUS.md
- Resumes at Task 2.3
- No loss of progress
- Context fresh

**Between sessions:**
- EXECUTION_STATUS.md is authoritative
- No need to reference conversation history
- Agent picks up exactly where it left off

---

## Loop Variants

### Variant 1: Single Agent Loop (Default)

```
Agent executes:
- Task 1.1 → Task 1.2.1 → Task 1.2.2 → ... → Task 8.3
- All sequential
- Takes ~9-15 weeks in real time
- Best for: Small team, serial execution
```

**Start with:**
```
/loop burn nexus production readiness tasks following PRODUCTION_READINESS_ROADMAP.md and EXECUTION_STATUS.md
```

### Variant 2: Parallel Tasks (Faster)

```
Main agent coordinates:
- Fork 1: Track 1 (Database) - 5-7 days
- Fork 2: Track 2 (Monitoring) - 3 days
- Fork 3: Track 5 (Backups) - 3 days
- Fork 4: Track 6 (Secrets) - 1 day
[Tracks 3, 4, 7, 8 sequential]

Reduces total time: 9-15 weeks → 6-8 weeks
Best for: Full team, parallel capability
```

**Start with:**
```
/loop burn nexus production readiness in parallel: Track 1, 2, 5, 6 concurrent; then Track 3, 4, 7, 8 sequential
```

### Variant 3: Parallel with Checkpoints

```
Milestone 1 (Week 1-2):
  - Parallel: Tracks 1, 2, 5, 6
  - Gate: Task 1.1 (database decision)

Milestone 2 (Week 3):
  - Parallel: Tracks 3, 4
  - Gate: Tasks 2.3, 3.1 complete

Milestone 3 (Week 4-5):
  - Sequential: Tracks 7, 8

Reduces time with controlled risk
Best for: Balanced team and risk tolerance
```

---

## Handling Blockers in Loop

### If Task Blocked (Dependency Not Complete)

```
LOOP detects: Task X depends on Task Y (not completed)

Options:
1. Wait - Pause loop until Task Y done
   /loop pause-until Task Y completes

2. Skip - Move to independent task
   /loop skip-to Task Z (which has no dependencies)

3. Escalate - Task owner must fix blocking task
   /loop escalate Task Y to [owner]
```

### If Test Fails

```
Loop detects: Test failure on Task X

Workflow:
1. Stop task execution
2. Document error in EXECUTION_STATUS.md
3. Create diagnostic bundle (logs, traces)
4. Escalate to task owner

Owner action:
1. Review error
2. Fix root cause
3. Run test again
4. Resume loop
```

### If Regression Detected

```
Loop detects: Existing feature broken by Task X

Immediate action:
1. ROLLBACK code changes for Task X
2. Mark in EXECUTION_STATUS.md: "Regression detected, rolled back"
3. Create issue: Document what broke
4. Skip to next task (or retry after fix)

Investigation (parallel):
- Analyze root cause
- Fix architecture or test
- Re-attempt task
```

---

## Monitoring Loop Progress

### During Execution

**Check current status any time:**
```bash
# Terminal
cat EXECUTION_STATUS.md | grep "Task ID\|Status\|Progress"

# Output:
# Task 1.1: Status = Completed
# Task 1.2.1: Status = In Progress (50%)
# Task 1.2.2: Status = Not Started
```

**Check detailed metrics:**
```bash
# See test results of last task
cat EXECUTION_STATUS.md | grep -A 20 "Task 1.2.1" | grep "Test\|Metrics"
```

### Weekly Report

Every Friday, loop runs:
```
generate-weekly-report.py
→ WEEKLY_REPORT.md

Shows:
- Tasks completed
- Tasks blocked
- On schedule? (Yes/No)
- Risks identified
```

---

## Resume from Crash

### If System Crashes Mid-Task

**Automatic recovery:**

```
Session 1: Executes Task 1.2.2
- Task 1.2.2 partially done (40% complete)
- Session crashes

Session 2: Read EXECUTION_STATUS.md
- Sees Task 1.2.2 status = "In Progress (40%)"
- Sees notes: "Schema created, DB layer at line XXX"
- Continues from line XXX
- Completes Task 1.2.2
- Updates status to "Completed"
```

**How EXECUTION_STATUS.md enables recovery:**

1. Every completed test → documented in status file
2. Every completed code section → saved in git + documented in status
3. Every blocker → escalated + noted in status
4. Can always resume from "last completed milestone"

### If Agent Changes

**Handoff to different agent:**

```
Agent A: Completes Tasks 1.1-1.2.3
- Updates EXECUTION_STATUS.md
- Leaves full context in that document
- Session ends

Agent B (Codex, or different Claude model): 
- Reads EXECUTION_STATUS.md
- Sees Tasks 1.1-1.2.3 completed
- Sees Task 1.2.4 next
- Starts Task 1.2.4
- Full context from document, not conversation
```

---

## Integration with CI/CD

### Automatic Testing Gate

After each task completion, loop can trigger:

```bash
# In loop script
task_complete() {
  local task_id=$1
  
  # 1. Run local tests
  pytest tests/ -v
  
  # 2. Push to branch
  git push origin feature/$task_id
  
  # 3. Trigger CI
  gh pr create --title "Task $task_id: ..." --auto-review
  
  # 4. Wait for CI
  while ! ci_passed; do
    sleep 60
  done
  
  # 5. Merge when CI green
  gh pr merge --auto
  
  # 6. Update status
  update_status $task_id "Completed" "CI passed"
}
```

---

## Context Budget Breakdown

**Per iteration (per task):**

| Component | Context Size | Notes |
|---|---|---|
| Status doc read (next 3 tasks) | 3 KB | Minimal |
| Roadmap details (1 task) | 2 KB | Minimal |
| Implementation code (write/edit) | 10 KB | Working buffer |
| Test code | 5 KB | Test implementation |
| Test output | 2 KB | Summarized results |
| Documentation | 3 KB | Docstrings + comments |
| Task completion summary | 1 KB | Status update |
| **Total per iteration** | **26 KB** | Low overhead |

**Over 23 tasks:**
- Naive approach: 26 KB × 23 = 600 KB (triggers compression)
- Smart approach: 26 KB per iteration, archive completed (50 KB), stay under 100 KB (never triggers compression)

---

## Loop Interruption & Resume

### Pausing the Loop

```
User: "pause loop"
Loop: "Pausing after Task 1.2.2 completes. Status saved to EXECUTION_STATUS.md."

Later...

User: "resume loop"
Loop: "Resuming at Task 1.2.3. [reads EXECUTION_STATUS.md]"
```

### Skipping Tasks

```
User: "skip tasks 2.1-2.3, jump to task 3.1"
Loop: "Skipping to Task 3.1. Prerequisites (2.3) verified. Starting..."
```

### Changing Task Owner

```
User: "assign task 1.2.2 to alice@company.com"
Loop: Updates EXECUTION_STATUS.md, notifies Alice
Alice: Can pick up task from status document
```

---

## Example Loop Execution Session

### Hour 1: Setup & Task 1.1

```
User: /loop burn nexus production readiness tasks

Loop: Reading EXECUTION_STATUS.md...
      Task 1.1: Database Evaluation (0.5 days)
      No blockers. Starting.

      [Executes Task 1.1]
      - Reads pilot feedback
      - Compares options (JSON vs SQLite vs PostgreSQL)
      - Documents decision: SQLite chosen
      - Updates timeline: 5-7 days for Task 1.2

      [Testing & Validation]
      - Decision reviewed: [✓ passed]
      - Team alignment confirmed: [✓ passed]
      - Roadmap updated: [✓ passed]

Loop: Task 1.1 COMPLETED
      Updating EXECUTION_STATUS.md...
      Next task: 1.2.1 (Create Schema)
      Total context used: 5%
```

### Hour 2: Task 2.1 (Parallel, no dependencies)

```
Loop: Task 1.2.1 depends on 1.1 (✓ done)
      Task 2.1 has no dependencies
      Executing Task 2.1 in parallel fork

Fork (background):
  [Executes Task 2.1]
  - Implements Prometheus metrics
  - Creates /metrics endpoint
  - Writes 10 tests
  - All tests pass
  - Updates docs
  - Updates EXECUTION_STATUS.md

Main Loop:
  [Starts Task 1.2.1]
  - Creates schema.sql
  - Runs 8 tests
  - All pass
  - Commits to git

Loop: Hour 2 summary
      Task 1.2.1 COMPLETED ✓
      Task 2.1 COMPLETED ✓ (fork)
      Context used: 8%
      Next: Task 1.2.2, Task 2.2
```

### Hour 3+: Continue

```
Loop: Context at 8%, proceeding
      Task 1.2.2 (3 days) → Forked (background)
      Task 2.2 (0.5 day) → Main thread
      
      ... continues until all tasks complete
```

---

## Best Practices

### ✅ DO:
- Keep EXECUTION_STATUS.md as source of truth
- Use forks for tasks > 2 hours
- Update status after EACH test
- Commit code after completing each task
- Archive completed tasks weekly
- Document blockers immediately
- Use minimal context reads

### ❌ DON'T:
- Store task details in conversation (use documents)
- Repeat full status report each iteration (summarize)
- Keep all test output in context (archive results)
- Wait for all tasks at conversation level (use doc persistence)
- Assume context will stay under 50% (monitor actively)

---

## Troubleshooting

### "Loop seems to be running in circles"

Check:
```bash
# Has EXECUTION_STATUS.md been updated?
git log -p EXECUTION_STATUS.md | head -20

# Has git commits been created?
git log --oneline | head -10

# Compare Task status before/after
grep "Task 1.1" EXECUTION_STATUS.md
```

**Fix:** Manually update EXECUTION_STATUS.md, set task to "Completed", loop resumes.

### "Context keeps hitting 100%"

Check:
```bash
# What's using context?
git diff --stat

# Are we storing full output?
tail -100 [conversation log]
```

**Fix:** 
1. Archive completed tasks
2. Use forks for long implementations
3. Summarize test results instead of showing full output

### "Agent doesn't know previous task status"

Check:
```bash
# Is EXECUTION_STATUS.md saved to disk?
ls -lh EXECUTION_STATUS.md

# Has it been updated?
tail -50 EXECUTION_STATUS.md | grep -i "task\|completed"
```

**Fix:** Make sure loop agent calls `git add EXECUTION_STATUS.md && git commit` after each task.

---

## Ready to Start?

1. **Review PRODUCTION_READINESS_ROADMAP.md** (what to build)
2. **Review EXECUTION_STATUS.md** (tracking sheet)
3. **Run:** `/loop burn nexus production readiness tasks`
4. **Monitor:** Check EXECUTION_STATUS.md weekly
5. **Pause if needed:** `/loop pause` (resume later)

All progress is saved to EXECUTION_STATUS.md. No conversation context needed to resume.
