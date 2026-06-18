# Ideal Agent Progression Behavior

## What SHOULD Happen (Expected Timeline)

```
Time 0s:   Incident submitted to /inputs
           ↓ All agents initialize to "Waiting"
           
Time 2-3s: SENTINEL completes
           Status: COMPLETED ✓
           Handoff: "Here's the incident classification"
           Next: PRISM starts
           
Time 4-5s: PRISM completes
           Status: COMPLETED ✓
           Handoff: "Here's the diagnosis and evidence correlation"
           Next: REPLICA starts (in parallel with orchestration)
           
Time 6-8s: REPLICA completes
           Status: COMPLETED ✓
           Handoff: "Here's the reproduction results"
           Next: TRACE can now start (needs REPLICA output)
           
Time 8-10s: TRACE processes and completes
           Status: COMPLETED ✓
           Handoff: "Here's the code path analysis"
           Next: FORGE starts
           
Time 10-12s: FORGE completes
           Status: COMPLETED ✓
           Handoff: "Here's the remediation plan"
           Next: GUARDIAN starts
           
Time 12-14s: GUARDIAN completes
           Status: COMPLETED ✓
           Final: Shows approval decision with safety score
           
Total time: ~14 seconds from submission to final decision
```

## What IS Happening (Current Bug)

```
Time 0s:   Incident submitted
Time 2s:   SENTINEL: Completed ✓
Time 4s:   PRISM: Completed ✓
Time 6s:   REPLICA: Completed ✓
Time 8s:   TRACE: Working now ⚙️
Time 10s:  TRACE: Working now ⚙️ (stuck)
Time 15s:  TRACE: Working now ⚙️ (stuck)
Time 20s:  TRACE: Working now ⚙️ (stuck, never completes)
           
           FORGE: Waiting (can't start - waiting for TRACE)
           GUARDIAN: Waiting (can't start - waiting for FORGE)
```

## Root Cause of TRACE Hang

### The Issue
The TRACE agent displays "Working now" but never transitions to "Completed". This blocks FORGE and GUARDIAN from ever starting.

### Why This Happens
TRACE is built in the `_forge_node` function (enterprise_runtime.py:1241), which means:
- FORGE is technically completing (since it calls build_trace_summary successfully)
- But the **frontend shows TRACE as "Working now"** instead of "Completed"
- This is because `trace_summary.get("trace_status")` defaults to "not_run" (line 3352)
- It only changes to "narrowed" if REPLICA was successfully reproduced (line 3382)

### The Display Logic
The frontend UI shows agent state based on `trace_status` values:
- `"not_run"` → Displays as "Waiting"
- `"narrowed"` → Should display as "Completed"
- But the orchest ration rail shows "Working now" instead

This suggests a **state mismatch between the backend and frontend display logic**.

## The Fix Needed

### Backend Change Required
In `enterprise_runtime.py`, ensure TRACE always completes and returns a meaningful status:

```python
def build_trace_summary(...) -> dict[str, object]:
    try:
        # ... existing function logic ...
        # Always set a completion status
        if trace_status == "not_run":
            trace_status = "completed_with_fallback"
        return {...}
    except Exception as e:
        logger.error(f"TRACE processing failed: {e}")
        return {
            "trace_status": "error_fallback",
            "confidence": 0.0,
            "reasoning": "TRACE encountered an error. Manual code review recommended.",
            # ... minimal fallback fields ...
        }
```

### Frontend Change Required
Ensure the agent progress display correctly maps TRACE status to display state:
- `trace_status` of "narrowed", "completed_with_fallback", "error_fallback" → should show "Completed"
- Only "not_run" or "not_executed" → should show "Waiting"

### State Update Requirement
After FORGE completes and builds TRACE summary, explicitly broadcast the updated TRACE state to the frontend via WebSocket:
```
TRACE state update → "Completed" 
FORGE state update → "Completed"
GUARDIAN state update → "Working now"
```

## Verification Steps

### Step 1: Submit Fresh Incident
1. Go to `/inputs`
2. Select a demo bundle
3. Click Submit
4. Monitor the incident detail page

### Step 2: Watch Agent Timeline
- Observe agent states update in real-time
- Each agent should move: Waiting → Working now → Completed
- Total time should be ~14 seconds

### Step 3: Verify Completion Criteria
✅ **Success** - All agents complete within 15 seconds
- SENTINEL: Completed
- PRISM: Completed
- REPLICA: Completed
- TRACE: Completed ← **This is the critical one currently failing**
- FORGE: Completed
- GUARDIAN: Completed with decision shown

✗ **Failure** - TRACE stays "Working now" after 20+ seconds
- Blocks FORGE from completing
- Blocks GUARDIAN from showing decision
- Incident workflow incomplete

## Why This Matters

**TRACE completion is critical because:**
1. **Unblocks FORGE** - Which needs TRACE output to generate remediation plan
2. **Unblocks GUARDIAN** - Which needs FORGE plan to make safety decision
3. **Shows users progress** - "TRACE is done, FORGE is next" is clear progress
4. **Enables end-to-end completion** - Without it, incidents appear stuck

## Summary

| State | Expected | Actual | Issue |
|-------|----------|--------|-------|
| TRACE at 8s | Working now | Working now | ✓ OK |
| TRACE at 12s | Completed | Working now | ✗ STUCK |
| FORGE at 12s | Waiting/Working | Shows Completed | ⚠️ Mismatch |
| GUARDIAN at 14s | Completed | Waiting | ✗ Never starts |

**Fix required:** Ensure TRACE transitions to "Completed" within 2-3 seconds and explicitly update frontend state.
