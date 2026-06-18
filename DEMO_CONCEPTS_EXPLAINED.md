# NEXUS Concepts Explained - Understanding the Demo

---

## The Problem NEXUS Solves

**Before NEXUS:** When a customer-facing outage happens:
1. Support team receives raw logs from monitoring
2. Someone guesses which team owns it
3. Manual relay through 5+ people
4. Engineering receives a weak escalation
5. Case gets re-investigated from scratch
6. **Result: 2-4 hours of manual work for each incident**

**With NEXUS:** 
1. Support submits raw logs to one place
2. AI processes through six-agent relay
3. Engineering gets a structured investigation packet
4. All analysis visible in one workspace
5. **Result: 15 minutes, one human approval gate**

---

## The Six-Agent Relay: SENTINEL → PRISM → REPLICA → TRACE → FORGE → GUARDIAN

Think of this like a relay race. Each agent passes the baton forward.

### Agent 1: SENTINEL (The Intake Officer)
**What it does:** Takes raw, noisy logs and normalizes them
- Extracts timestamps, error messages, metrics
- Removes duplicates and noise
- Creates structured evidence from chaos

**What you see in demo:**
- SENTINEL section shows cleaned-up version of raw logs
- Same evidence as input, but organized and searchable

**Example:**
- Input: 1000 log lines with duplicate error spikes
- Output: "Database connection timeout occurred 147 times between 10:15-10:47 UTC"

---

### Agent 2: PRISM (The Classifier)
**What it does:** Identifies which outage family this is
- Matches evidence to known patterns
- Routes to the right debugging playbook
- Checks if this matches prior incidents

**What you see in demo:**
- PRISM section shows detected family: "Checkout timeout / retry amplification"
- Shows confidence score
- Shows prior similar incidents if memory found them

**Why this matters:**
- Each incident family has specific debugging steps
- Skipping classification = generic investigation (slower)
- Correct classification = targeted investigation (much faster)

---

### Agent 3: REPLICA (The Reproducer)
**What it does:** Tries to replay the failure in a bounded runtime environment
- Spins up demo version of the system
- Replays the same logs/traffic
- Captures stack traces, state transitions, breakpoints

**What you see in demo:**
- REPLICA section shows execution timeline
- Exact line of code where failure happened
- Full stack trace and local variable state

**Important:** REPLICA is **BOUNDED**
- Only works for 5 specific incident families
- Only on curated demo packs (not arbitrary code)
- Not a universal debugger or VM reproduction system
- This is intentional - better to be honest and good at 5 things than fake it on 50

---

### Agent 4: TRACE (The Debugger)
**What it does:** Generates engineering debugging guidance
- Based on REPLICA output (if available) or PRISM analysis
- Shows "check this module", "look at this function"
- Explains WHY the failure happened

**What you see in demo:**
- TRACE section lists debugging checkpoints
- Module and function names that need review
- Concrete state transitions to look for
- Expected vs actual values

**Example:**
"Check: `checkout.py:validate_token()` - expected return 200, got 403. Token validation is rejecting valid tokens. Look for recent auth service changes."

---

### Agent 5: FORGE (The Analyst)
**What it does:** Creates the investigation narrative and mitigation options
- Synthesizes all evidence into readable story
- Ranks mitigation options by risk/effort
- Creates handoff packet for engineering

**What you see in demo:**
- FORGE section shows investigation summary
- Root cause explanation
- 3-5 ranked mitigation options
- Confidence level for each option

**Example:**
1. **Increase retry backoff** (low risk, 5 min) - Quick fix
2. **Upgrade token cache** (medium risk, 30 min) - More robust
3. **Refactor auth validation** (high effort, 4 hrs) - Long-term fix

---

### Agent 6: GUARDIAN (The Approval Gate)
**What it does:** Makes approval/rejection decision before any action
- Reviews full investigation
- Confirms evidence quality
- Enforces governance

**What you see in demo:**
- GUARDIAN section shows: Approved or Rejected
- Clear reason for decision
- Audit trail of who made decision and when

**Why this matters:**
- Prevents bad recommendations from reaching engineering
- Enforces quality bar
- Creates audit trail for compliance
- **Humans stay in control** - this is not autonomous remediation

---

## Evidence Posture: Runtime-Backed vs Inference-First

**This is NEXUS being honest about what it knows.**

### Runtime-Backed ✅
"This is actually reproduced in our runtime environment"

**Example:** REPLICA shows exact line of code failing with stack trace
- Most credible (you have the evidence)
- Takes 30 seconds per incident
- Only available for 5 specific families

### Inference-First ⚠️
"This is our best guess based on patterns and logs"

**Example:** PRISM detected the family, TRACE made recommendations, but REPLICA couldn't reproduce it
- Less credible (but still useful)
- Fast (5 seconds)
- Works for any incident family

### Unsupported ❌
"This incident doesn't match our 5 families"

**Example:** Customer reports "widgets are slow" - not in our 5 families
- NEXUS shows what it CAN'T do
- Honest about bounds
- Better than fake universal solution

---

## The Five Incident Families

These five families cause **80% of recurring customer outages**. NEXUS intentionally focuses here.

### INC001: Checkout Timeout / Retry Amplification
**Pattern:** Client keeps retrying failed requests, server gets overwhelmed

**Root cause:** Downstream service slow → client retries → more load → more slowness → cascade

**Runtime evidence:** Sees exact retry counts, timing, failure rates

**Demo shows:** How to detect pattern, what to check in code, mitigation options

---

### INC002: DB Pool Exhaustion / Session Leak
**Pattern:** Database connections aren't being released, new requests starve

**Root cause:** Code doesn't close connections properly, or pool size too small

**Runtime evidence:** Connection pool metrics, stuck connection timestamps, query backlog

**Demo shows:** Connection state, query queue, which code holds connections

---

### INC003: Deploy Regression / 5xx Spike
**Pattern:** New deploy caused sudden spike in errors

**Root cause:** Code change, config change, or infrastructure issue at deploy time

**Runtime evidence:** Before/after metrics, which service changed, error types

**Demo shows:** Exact changes deployed, error distribution, affected endpoints

---

### INC005: Queue / Worker Backlog
**Pattern:** Job queue fills up, workers can't keep pace

**Root cause:** Worker is slow or crashed, or job producer too fast

**Runtime evidence:** Queue depth over time, worker health, job processing times

**Demo shows:** Queue metrics, worker status, processing backlog

---

### INC007: Auth Dependency Slowdown
**Pattern:** Auth service is slow, blocking all requests

**Root cause:** Auth service overloaded, network latency, or auth cache missed

**Runtime evidence:** Auth call latencies, cache hit rates, upstream dependency health

**Demo shows:** Timing breakdown, cache effectiveness, dependency status

---

## How This Differs From Generic Solutions

### NOT a Universal Incident Platform
- NEXUS doesn't try to handle all 500 types of outages
- It's excellent at 5 families, honest about scope
- Generic platforms are mediocre at everything

### NOT a Universal Debugger
- REPLICA doesn't reproduce arbitrary code
- Only 5 specific incident families
- Can't reproduce customer's code in their environment
- But it's really good at those 5

### NOT Autonomous Remediation
- GUARDIAN always requires human approval
- This is intentional - safety and governance
- No automatic production changes

### Instead: Honest Scope + Deep Capability
- Excellent REPLICA runtime replay for 5 families
- Honest about inference vs runtime evidence
- Clear handoff to engineering
- Governed approval gate
- Fast (minutes, not hours)

---

## The Demo Path Explained

### Why Start at `/queue` (Command Center)?
- Shows NEXUS is a focused operating room
- One focal incident in focus, rest secondary
- Not a dashboard zoo with 100 metrics
- Demonstrates operator UX clarity

### Why Show Both Seeded and Fresh Incidents?
**Seeded (INC001, INC002):**
- Pre-built to show exactly what good output looks like
- Consistent every time (good for demos)
- Show all features working

**Fresh (you submit logs):**
- Prove it really works on new data
- More credible than seeded alone
- Show end-to-end workflow

Together: "It works on demos AND on real new data"

### Why Click Through Each Agent?
- Proves all six agents ran
- Shows packet flow is visible
- Demonstrates evidence posture is labeled
- Shows no hidden black box

### Why Show Training & Settings?
- Training: Proves it's operationally measurable
- Settings: Proves all systems configured and healthy
- Together: "This is deployable and credible"

---

## What Success Looks Like in the Demo

✅ **Seeded incident** - All six agents visible, complete handoff packet  
✅ **Fresh intake** - Submitted logs → processed automatically → incident created in seconds  
✅ **Evidence posture** - Clearly labeled if runtime-backed or inference-first  
✅ **Engineering handoff** - Structured packet with checkpoints and mitigation options  
✅ **Governance** - GUARDIAN made an approval decision, reason visible  
✅ **Metrics** - Training page shows this is measurable and bounded  
✅ **All 5 families** - You can walk through all 5 incident types  
✅ **No errors** - Pages load cleanly, no JavaScript errors, professional UI  

---

## What NEXUS is NOT (Stay Honest in Demo)

❌ "This debugs all types of code" → No, 5 families only  
❌ "This automatically fixes problems" → No, GUARDIAN approval required  
❌ "This reproduces any environment" → No, curated packs only  
❌ "This replaces your incident system" → No, it's a specialist tool  
❌ "This needs no human review" → No, humans stay in control  

**Instead say:**
"This is really good at 5 specific families. We're honest about the bounds. For these 5, it's excellent - you go from raw logs to investigation packet in minutes instead of hours."

---

## Key Takeaways

1. **NEXUS is bounded and honest**
   - 5 families, not infinite
   - Runtime-backed where proven, inference where not
   - Bounded REPLICA, bounded TRACE

2. **Each agent adds value**
   - SENTINEL: Normalizes chaos
   - PRISM: Identifies pattern
   - REPLICA: Reproduces failure
   - TRACE: Generates debugging guidance
   - FORGE: Creates narrative
   - GUARDIAN: Approves action

3. **Workflow is visible**
   - You see what each agent output
   - No hidden black box
   - Evidence origin is clear

4. **Support-to-Engineering Journey**
   - Raw logs in → structured packet out
   - One operating room, clear next action
   - Engineering gets what they need

5. **Ready for Pilots**
   - Stable, tested, documented
   - Demo path is repeatable
   - Metrics are operator-visible
   - Bounded scope is honest strength

---

**Now go demo it - watch for how naturally these concepts show up in the UI!**
