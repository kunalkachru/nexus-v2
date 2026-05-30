# NEXUS v2 MVP Priority Backlog

> **Purpose:** This backlog is the same-day execution plan for the corrected product direction.
>
> The product goal is now: raw incident text or logs -> LLM reasoning -> solution proposal -> safety gate -> RL-ready structured output.

## How To Use This List

- Build items in the order listed.
- Keep the UI updated as each task lands.
- Stop after each logical task and validate the screen and the tests.

## Today's Target

Deliver the smallest credible MVP that proves:

- a user can paste raw error logs or incident text,
- the system can reason through the 4-agent flow,
- the system can propose a likely root cause and solution,
- the result is structured enough for scoring and learning later,
- the UI makes the whole flow understandable.

## Consolidated Ordered Backlog

### 1. Raw Log Intake UI

**Goal**
- Give the user a visible place to paste raw incident text, logs, or error output.
- Make this the primary MVP intake surface.

**What to build**
- Add a new top-level intake mode on the Inputs screen for `Paste logs / incident text`.
- Show a large text area for raw text.
- Add a short explanation of what happens next.
- Add sample payloads and examples.
- Add a clear call to action that opens the incident console.

**Done when**
- A non-technical user can understand where to paste logs.
- The UI explains that the system will reason on the pasted text.
- The screen feels like the entrypoint to the product, not a form list.

### 2. Raw Log Normalization

**Goal**
- Convert pasted text into structured evidence before the agents see it.

**What to build**
- Parse obvious fields like service name, severity hints, timestamps, and error signatures.
- Preserve the original raw text.
- Derive a minimal evidence bundle from the paste.
- Make the normalized result visible in the console.

**Done when**
- The incident console can show both raw text and parsed evidence.
- The parsing is deterministic enough to test.

### 3. LLM Reasoning Loop

**Goal**
- Make the four-agent flow reason on the pasted incident input.

**What to build**
- `SENTINEL` classifies the issue from raw text and context.
- `PRISM` explains the likely root cause using evidence.
- `FORGE` proposes solution steps or a runbook.
- Keep the live OpenAI path optional, but make the browser demo able to show reasoning text.
- Make the model/provider path explicit in config so live reasoning can be switched on or off without changing code.
- Keep the reasoning output structured so it can be reused later by RL scoring.

**Done when**
- The console shows human-readable reasoning from each agent.
- The output reads like a real triage pass, not a static demo.

### 4. Safety Gate And Action Decision

**Goal**
- Keep execution controlled and believable.

**What to build**
- Keep `GUARDIAN` as the final check.
- Show why an action is approved, blocked, or needs modification.
- Make the approval state visible in the UI.
- The safety gate must be obvious enough that a non-technical user can understand whether execution is allowed.

**Done when**
- A user can see the final safety decision and the reason for it.
- The product feels governed, not automated blindly.

### 5. RL-Ready Structured Output

**Goal**
- Make the final incident output usable for later scoring and learning.

**What to build**
- Add a structured result contract with fields like:
  - incident id
  - root cause
  - proposed fix
  - safety decision
  - confidence
  - evidence
  - execution status
  - live reasoning on/off
  - raw priority label
  - normalized priority rank
- Keep the payload stable for future reward/evaluation logic.

**Done when**
- The output can be scored without scraping the UI text.
- The shape is good enough for RL later.

### 6. Incident Console Updates

**Goal**
- Make the Incident Console the place where the reasoning is understood.

**What to build**
- Show raw input, parsed evidence, agent reasoning, solution, and safety decision.
- Keep the agent handoff clear: `SENTINEL -> PRISM -> FORGE -> GUARDIAN`.
- Highlight the live reasoning path when OpenAI mode is enabled.
- Make the action buttons obvious and keep the deep-dive panels visually lighter.

**Done when**
- The console tells a full incident story in one view.
- The user can see how the system arrived at the answer.

### 7. Input Channel Coverage

**Goal**
- Show the broader enterprise shape without waiting for the backend.

**What to build**
- Add visible channels for:
  - Slack
  - Stream ingestion
  - Webhook / integrations
  - File upload
  - Manual form
  - Batch import
- Make them look like real future paths with sample inputs and expected behavior.
- Keep raw-log paste as the primary MVP channel, but show the other channels now so the product feels like a real enterprise intake hub.

**Done when**
- The product story includes enterprise integrations without needing them fully built yet.

### 8. Manual Demo And Validation Updates

**Goal**
- Make the product easy to understand and demo end to end.

**What to build**
- Update the walkthrough for the new raw-log MVP flow.
- Update speaker notes and browser checklists.
- Add exact expected results at each step.
- Document the live reasoning toggle, empty raw-input field, and `Load example logs` action clearly enough for a non-technical reviewer.

**Done when**
- A first-time user can follow the docs and understand the whole product.

### 9. Backend Adapter Follow-Up

**Goal**
- Start replacing fixture-backed evidence with real adapters after the MVP flow is visible.

**What to build**
- Add real observability adapters after the raw-log MVP is stable.
- Keep provenance visible.
- Keep the UI unchanged where possible.
- Make the evidence sources richer without breaking the current demo or changing the user flow.

**Done when**
- The backend is no longer depending mostly on demo fixtures for evidence.

### 10. GUARDIAN Explicit Control Gate

**Goal**
- Make GUARDIAN the visible approval / block control point for execution.

**What to build**
- Show approve, reject, and request-modification states clearly in the incident console.
- Tie the state to status and audit history.
- Keep execution blocked until GUARDIAN allows it.

**Done when**
- A user can immediately tell whether the incident is safe to execute.

### 11. Persistent RL And Audit Artifacts

**Goal**
- Persist the structured learning loop so it survives restarts.

**What to build**
- Store RL episode contracts durably.
- Store reward breakdowns durably.
- Store audit history durably.
- Keep replay and training reading from the same persisted state.

**Done when**
- Training and replay still work after a restart.

### 12. Production Hardening

**Goal**
- Make the product credible for a real enterprise rollout.

**What to build**
- Tighten auth and tenant boundaries.
- Harden deployment and ingress verification.
- Decompose remaining backend responsibilities into smaller services.
- Keep provider failures and fallback behavior explicit.

**Done when**
- The product is still understandable, but now looks and behaves like something that could be taken into production.

## Suggested Build Order For Today

1. Raw Log Intake UI
2. Raw Log Normalization
3. LLM Reasoning Loop
4. Safety Gate And Action Decision
5. RL-Ready Structured Output
6. Incident Console Updates
7. Input Channel Coverage
8. Manual Demo And Validation Updates
9. Backend Adapter Follow-Up
10. GUARDIAN Explicit Control Gate
11. Persistent RL And Audit Artifacts
12. Production Hardening

## Practical MVP Boundary

If time runs out today, the minimum shippable MVP is:

- paste logs input
- normalized evidence
- live or live-shaped reasoning output
- safety decision
- structured result
- updated console
- visible input channels
- live reasoning toggle
- empty raw input field with explicit example action
