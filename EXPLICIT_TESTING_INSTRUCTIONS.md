# Explicit Testing Instructions - Agent Visibility Fix

## What Changed
I added an **Agent Progress** card that shows all 6 agents and their status **in the first viewport** (top of the page). You no longer need to scroll or click to see agent progress.

## How to Test

### Step 1: Refresh the Browser
1. Go to the incident detail page (e.g., http://127.0.0.1:8001/incident?nexus_incident_id=INC001)
2. **Refresh the page** (Ctrl+R or Cmd+R)
3. Wait for page to load completely

### Step 2: Look for "Agent Progress" Card
**Without scrolling**, look for a new card that appears like this:

```
┌──────────────────────────────────┐
│ Agent Progress                   │
├──────────────────────────────────┤
│ SENTINEL   PRISM    REPLICA      │
│ Waiting    Waiting  Waiting      │
│                                  │
│ TRACE      FORGE    GUARDIAN     │
│ Waiting    Waiting  Waiting      │
└──────────────────────────────────┘
```

**Location:** Just below the "Working Memory" card, still in the first viewport (no scrolling needed)

### Step 3: Submit Fresh Incident (Critical Test)
1. Go to `/inputs`
2. Select any demo bundle (e.g., "Checkout timeout / retry amplification")
3. Click **Submit**
4. Wait for new incident to load
5. **Watch the Agent Progress card** and tell me:

**Question 1:** Do you see agent states changing?
- SENTINEL → Completed?
- PRISM → Completed?
- REPLICA → Completed?
- TRACE → Changes to "Working now"?

**Question 2:** Does TRACE ever complete?
- Does TRACE change from "Working now" to "Completed"?
- Or does it stay "Working now" forever?

**Question 3:** Do FORGE and GUARDIAN ever start?
- Does FORGE change from "Waiting" to "Working now"?
- Does GUARDIAN complete?

---

## What Success Looks Like

### ✅ Successful Agent Progression
```
Time 0s:     All agents: Waiting
Time 2s:     SENTINEL: Completed
Time 4s:     PRISM: Completed
Time 6s:     REPLICA: Completed
Time 8s:     TRACE: Working now
Time 11s:    TRACE: Completed ← CRITICAL: This should happen
Time 13s:    FORGE: Completed
Time 15s:    GUARDIAN: Completed (with decision)
```

### ❌ The Current Bug (What You Were Seeing)
```
Time 0s:     All agents: Waiting
Time 2s:     SENTINEL: Completed
Time 4s:     PRISM: Completed
Time 6s:     REPLICA: Completed
Time 8s:     TRACE: Working now
Time 30s:    TRACE: Working now ← STUCK HERE
Time 60s:    TRACE: Working now ← NEVER COMPLETES
Forever:     TRACE: Working now ← HANGS
             FORGE: Waiting (can't start)
             GUARDIAN: Waiting (can't start)
```

---

## Report Back to Me

After testing, tell me:

1. **Agent Progress card visible?**
   - [ ] Yes, I see it without scrolling
   - [ ] No, I don't see it
   - [ ] I see it but I had to scroll

2. **For fresh incident - does TRACE complete?**
   - [ ] Yes - TRACE changes to "Completed" within ~5 seconds
   - [ ] No - TRACE stays "Working now" forever (original bug)
   - [ ] Sometimes - it's inconsistent

3. **Do FORGE and GUARDIAN complete?**
   - [ ] Yes - everything completes and shows Guardian decision
   - [ ] No - they stay "Waiting" because TRACE hangs
   - [ ] Partial - depends on the incident

---

## If Agent Progress Card is Missing

If you don't see the "Agent Progress" card anywhere on the page:

1. **Clear your browser cache:**
   - Chrome: Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
   - Firefox: Ctrl+Shift+Delete
   - Select "All time" → Clear

2. **Do a hard refresh:**
   - Ctrl+F5 (or Cmd+Shift+R on Mac)

3. **Try in incognito/private mode:**
   - Opens with fresh cache

If it STILL doesn't appear, that means the HTML changes didn't deploy properly.

---

## Next Steps Based on Your Feedback

**If UI fix worked (Agent Progress card visible):**
- ✅ The UI issue is solved
- ⏳ Still need to fix TRACE backend hang
- I'll add error handling to the backend TRACE code

**If TRACE still hangs:**
- ⏳ Backend fix needed
- I'll add timeout + error handling to build_trace_summary() function
- Need to test that fix

**If both work:**
- ✅ Both issues are fixed
- 🧪 Need to run full end-to-end test
- 📝 Create final documentation

---

## Example Screenshots to Help You Identify Changes

**First viewport should now look like:**
```
NEXUS header
Command Center | Incident Detail | Learning & Controls
────────────────────────────────────────────────
Incident ID: INC001
Title: API Timeout Cascade
────────────────────────────────────────────────
Stats: Severity | Guardian | Execution | ...
────────────────────────────────────────────────
Working Memory:
  "Detected 2026-05-28T09:14:00Z..."
────────────────────────────────────────────────
Agent Progress: ← NEW CARD (this is what to look for)
  SENTINEL   PRISM    REPLICA
  Completed  Waiting  Waiting
  
  TRACE      FORGE    GUARDIAN
  Working now Waiting Waiting
────────────────────────────────────────────────
[rest of page below]
```

---

## Do Not
- ❌ Don't look for "Agent Relay & Crew Details" in first viewport (that's still collapsed below)
- ❌ Don't expect everything to complete immediately (takes 15-20 seconds normally)
- ❌ Don't worry if states show "Waiting" initially (they start there)

## DO
- ✅ Watch the Agent Progress card for state changes
- ✅ Pay attention to whether TRACE completes or hangs
- ✅ Test with a fresh incident, not a seeded one
- ✅ Report back the three questions above

---

## Summary

**What changed:** Added "Agent Progress" card showing all 6 agents in first viewport  
**What to test:** Look for card + watch if TRACE completes when submitting fresh incident  
**What to report:** Three simple questions about what you observed  
**What's next:** Based on your answers, I'll either confirm the fix works or apply backend corrections

**Please test and report back with your answers to the 3 questions above.**
