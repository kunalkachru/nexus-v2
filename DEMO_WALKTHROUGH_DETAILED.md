# NEXUS Demo Walkthrough - Step by Step

**Server Status:** ✅ Running on http://127.0.0.1:7860

---

## Demo Overview

This is the **strongest truthful demo path** through NEXUS. Follow each step in order, and verify the expected result before moving to the next step.

Total time: ~15 minutes

---

## STEP 1: Open Command Center

**Action:** Open in your browser:
```
http://127.0.0.1:7860/queue
```

**Expected Result:**
- ✅ Page loads showing "Command Center" as header
- ✅ Hero section explaining: "Turn support chaos into one focused operating room"
- ✅ You see 2 seeded incidents in the queue (INC001 and INC002)
- ✅ Each incident shows: title, stage (e.g., "Guardian Review"), urgency, response clock
- ✅ Specialist crew strip visible at top: SENTINEL, PRISM, REPLICA, TRACE, FORGE, GUARDIAN

**What This Proves:**
- Product is a focused operating room, not a dashboard zoo
- You're looking at one focal incident (INC001)
- Rest of queue is secondary but visible

---

## STEP 2: Open Flagship Seeded Incident

**Action:** Click on the first incident (INC001) in the queue

**Expected Result:**
- ✅ Incident detail page loads
- ✅ Page title: "Checkout Timeout / Retry Amplification" 
- ✅ Top section shows incident status and six-agent crew
- ✅ Brief summary visible
- ✅ Evidence section shows logs/metrics
- ✅ GUARDIAN section shows approval decision
- ✅ No page errors or loading spinners

**What This Proves:**
- Fresh incident intake works
- All six agents have processed this incident
- Evidence is structured and searchable
- Governance gate (GUARDIAN) made a decision

**Explore This Page:**
- Click on each agent section (SENTINEL, PRISM, REPLICA, TRACE, FORGE, GUARDIAN) to see what each one output
- Note the "Evidence Posture" label (shows if runtime-backed, inference-first, or unsupported)
- Scroll to see engineering handoff packet

---

## STEP 3: Inspect Intake - Fresh Log Path

**Action:** On the incident page, look for a button/link labeled **"Inspect Intake"** and click it

**Expected Result:**
- ✅ Page navigates to `/inputs`
- ✅ Shows 5 demo bundles as cards
- ✅ Each bundle has a title (e.g., "Checkout timeout / retry amplification")
- ✅ Instructions for submitting raw logs
- ✅ "Submit" button visible

**What This Proves:**
- Fresh log intake is available
- Demo bundles are pre-configured for each family
- Users can submit raw evidence

---

## STEP 4: Submit a Demo Bundle

**Action:** 
1. Click on the **first demo bundle** ("Checkout timeout / retry amplification")
2. Scroll down to see the raw logs preview
3. Click **"Submit"** button

**Expected Result:**
- ✅ Page briefly shows "Processing..."
- ✅ After ~5-10 seconds, you're redirected to a new incident
- ✅ New incident ID starts with `nxs_` (showing it's auto-generated)
- ✅ Page shows incident detail similar to Step 2
- ✅ Fresh incident appears at top of `/queue` when you go back

**What This Proves:**
- Fresh incident intake works end-to-end
- Auto-processing happens through all six agents
- Results are immediate and structured
- New incidents appear in queue

---

## STEP 5: Explore the Fresh Incident

**Action:** On the fresh incident detail page (from Step 4):
1. Scroll through the incident brief
2. Click on each agent section to see outputs
3. Look for the "Evidence Posture" label
4. Scroll to the engineering handoff section

**Expected Result:**
- ✅ SENTINEL: Shows normalized evidence
- ✅ PRISM: Shows detected family (should match the bundle you submitted)
- ✅ REPLICA: Shows runtime replay (if available for this family)
- ✅ TRACE: Shows debugging guidance and module/function references
- ✅ FORGE: Shows investigation narrative and mitigation options
- ✅ GUARDIAN: Shows approval decision and reason
- ✅ Evidence posture is clearly labeled (e.g., "runtime-backed" or "inference-first")

**What This Proves:**
- All six agents work end-to-end
- Each agent's output is visible and legible
- Evidence origin is labeled honestly
- Engineering handoff packet is complete

---

## STEP 6: View Training & Metrics

**Action:** Navigate to:
```
http://127.0.0.1:7860/training
```

**Expected Result:**
- ✅ Page shows "Learning & Controls" section
- ✅ Pilot scorecard visible with metrics (incidents processed, approval rate, etc.)
- ✅ Family coverage chart showing all 5 supported families
- ✅ Runtime host status (should show "connected")
- ✅ Live triage metrics visible

**What This Proves:**
- Operator-visible health and ROI metrics
- Product is measurable and bounded
- Pilot readiness is visible

---

## STEP 7: Check System Settings

**Action:** Navigate to:
```
http://127.0.0.1:7860/settings
```

**Expected Result:**
- ✅ Page shows system configuration
- ✅ Tenant information visible
- ✅ Runtime host relay status
- ✅ Database status
- ✅ No warnings or errors

**What This Proves:**
- Product is operationally ready
- All systems configured and healthy
- Deployment is credible

---

## STEP 8: Go Back to Queue - Verify Both Paths

**Action:** Navigate back to:
```
http://127.0.0.1:7860/queue
```

**Expected Result:**
- ✅ Seeded incidents (INC001, INC002) still present
- ✅ Fresh incident from Step 4 appears at top (starts with `nxs_`)
- ✅ Queue shows both seeded and fresh incidents
- ✅ All incidents show consistent format and metadata

**What This Proves:**
- Seeded and fresh incident paths are coherent
- Queue management works
- System is stable

---

## OPTIONAL: View Complete Five-Family Wedge

**Action:** Return to `/queue` and explore the breadth:

1. **INC001** (already visited): Checkout timeout / retry amplification
2. **INC002**: Click to view DB pool exhaustion scenario
3. Go to `/inputs` and submit demo bundle for **"DB pool exhaustion"**
4. Repeat for **INC003** (deploy regression), **INC005** (queue backlog), **INC007** (auth slowdown)

**Expected Result:**
- ✅ Each family has a seeded incident available
- ✅ Each family has a fresh intake bundle
- ✅ All families show complete six-agent processing
- ✅ All show consistent UI and evidence posture

**What This Proves:**
- All 5 supported families are demoable
- Product is feature-complete for stated scope
- No incomplete or broken paths

---

## OPTIONAL: Check Runtime Replay

**Action:** On any incident detail page:
1. Look for a **"Replay"** section or button
2. If present, click to start a bounded replay
3. Watch the runtime execution timeline

**Expected Result:**
- ✅ Replay shows step-by-step execution
- ✅ Errors and state transitions visible
- ✅ Module/function references accurate
- ✅ Timeline shows realistic execution flow

**What This Proves:**
- Runtime replay is bounded and working
- Debugging guidance is concrete
- Evidence is runtime-backed (not just inferred)

---

## OPTIONAL: Check History & Audit

**Action:** Navigate to:
```
http://127.0.0.1:7860/history
```

**Expected Result:**
- ✅ Shows all incidents processed (seeded + fresh)
- ✅ Each incident shows metadata, timestamp, family
- ✅ Can click to re-open any incident

**What This Proves:**
- Audit trail is complete
- Prior incidents are first-class memory
- Operators can review history

---

## Demo Success Checklist

After completing all steps, verify:

- [ ] **Command Center** loaded and showed focal incident pattern
- [ ] **INC001 seeded incident** showed all six agents + governance
- [ ] **Fresh intake** worked: submitted bundle → created incident
- [ ] **Fresh incident** showed complete processing + evidence posture
- [ ] **Training page** showed metrics and runtime status
- [ ] **Settings page** showed operational readiness
- [ ] **Queue** coherently shows both seeded and fresh incidents
- [ ] **Five families** are all present and demoable
- [ ] No errors, timeouts, or broken pages anywhere
- [ ] UI feels clean, professional, and operator-focused

---

## Key Points to Emphasize in Demo

1. **Narrowly Bounded**
   - Only 5 incident families (not trying to be universal)
   - REPLICA replay only for curated packs (not arbitrary VM reproduction)
   - TRACE debugging for these specific families (not universal debugger)

2. **Honest Evidence Posture**
   - Each finding labeled: runtime-backed, inference-first, or unsupported
   - No claims beyond evidence
   - Clear about what's reproduced vs inferred

3. **Governed Before Action**
   - GUARDIAN approval gate required
   - Audit trail complete
   - Human remains in control

4. **Support-to-Engineering Workflow**
   - Raw logs in → structured packet out
   - One operating room, not a dashboard zoo
   - Clear next action for support, triage, and engineering

5. **Demo-Ready**
   - Guided demo bundles for each family
   - Fresh intake for real-world testing
   - Training metrics for buyer conversations

---

## Troubleshooting

**Page doesn't load:**
- Check: http://127.0.0.1:7860/health
- If returns `{"status":"ok"}`, server is running
- Try clearing browser cache or using incognito mode

**Fresh incident processing is slow:**
- Expected: 5-15 seconds for fresh intake
- System is processing through all six agents
- Check console for any JavaScript errors

**Demo bundle submission fails:**
- Check that server is still running: `docker ps`
- Refresh the page and try again
- Check browser console for error messages

**Replay not showing:**
- Replay is only available for curated packs (INC001, INC002)
- Fresh incidents may not have replay depending on family
- This is expected and documented

---

## After Demo

**For Pilot Onboarding:**
- Operator should follow MASTER_SETUP_AND_TESTING_GUIDE.md
- Run all validation checks
- Train on ops procedures
- Set up monitoring and alerts

**For Production Deployment:**
- Run pre-deployment validation: `./scripts/pre-deployment-validation.sh`
- Follow production-deployment-guide.md
- Execute ops team training
- Start 24-hour monitoring playbook

---

**Status:** Ready for demo ✅
**Duration:** 15 minutes for core path, 30 minutes for complete five-family tour
**Next:** Choose your next step: pilot, production, or explore deeper
