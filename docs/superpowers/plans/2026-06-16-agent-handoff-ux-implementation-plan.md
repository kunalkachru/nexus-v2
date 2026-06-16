# Agent Handoff UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make agent-to-agent control transfer legible in the incident workspace through a truthful six-agent handoff ledger, current-owner state, emitted/received packet UI, clearer transfer animations, and a replayable demo mode.

**Architecture:** Add one additive handoff contract that is produced consistently for seeded and live incidents, then render that contract in the incident UI through a baton rail, packet cards, ledger, and replay controller. Promote `REPLICA` and `TRACE` into first-class visible relay participants now, while keeping their execution scope bounded to the currently supported outage families and curated packs.

**Tech Stack:** FastAPI payload services, frontend HTML/CSS/vanilla JS, Playwright browser verification, pytest API/app tests.

---

## File Structure

- `server/services/surface_payloads.py`
  - Seeded incident handoff contract builder across six visible agents.
- `server/services/enterprise_runtime.py`
  - Live incident handoff contract builder so fresh incidents and seeded incidents stay semantically aligned.
- `server/services/incidents.py`
  - Additive persistence and replay-state hooks if replay mode needs stable handoff snapshots.
- `frontend/incident.html`
  - New six-agent handoff rail, current-owner card, packet surfaces, ledger, and replay controls.
- `frontend/static/incident.js`
  - Handoff state model, render functions, replay controller, animation state transitions.
- `frontend/static/dashboard.css`
  - Baton rail, packet cards, ledger, animation, and replay control styling.
- `frontend/static/api.js`
  - Fallback and additive client-side contract support only if required for degraded/fallback incident synthesis.
- `tests/test_api_contract.py`
  - Contract assertions for the additive handoff payload.
- `tests/test_app.py`
  - App-level behavior for seeded and live incidents.
- `tests/e2e/browser-verification.spec.js`
  - UI validation for current owner, packet visibility, transfer clarity, and replay mode.
- `docs/public/MASTER_OPERATOR_DEMO_GUIDE.md`
  - Owner-facing explanation of the new handoff surfaces.
- `docs/public/README.md`
  - Public story alignment if the incident console behavior changes materially.

## Scope Boundary

- In scope:
  - current owner / next owner / previous owner
  - explicit handoff events
  - emitted packet / received packet UI
  - visual baton transfer and replay controls
  - seeded and live incident parity
- Out of scope:
  - VM-based arbitrary reproduction
  - universal debugger
  - new outage families

## Shared Contract To Introduce

Add one additive incident field:

- `handoff_flow`

Suggested shape:

```json
{
  "current_owner": "REPLICA",
  "previous_owner": "PRISM",
  "next_owner": "TRACE",
  "state": "in_progress",
  "transfer_reason": "SENTINEL completed issue framing with likely owner and issue family confidence above threshold.",
  "events": [
    {
      "id": "sentinel-emitted-triage-packet",
      "from": "SENTINEL",
      "to": "PRISM",
      "status": "completed",
      "event_type": "packet_emitted",
      "title": "SENTINEL emitted triage packet",
      "reason": "Initial classification is stable enough for diagnosis branching.",
      "packet": {
        "packet_type": "triage_packet",
        "summary": "Issue family, likely owner, customer path, support coverage.",
        "fields": [
          { "label": "Issue family", "value": "Checkout timeout / retry amplification" },
          { "label": "Likely owner", "value": "Checkout Platform" }
        ]
      }
    }
  ]
}
```

This field must remain additive and must not rename existing response keys.

Canonical visible relay:

- `SENTINEL -> PRISM -> REPLICA -> TRACE -> FORGE -> GUARDIAN`

Canonical packet types:

- `triage_packet`
- `diagnosis_packet`
- `reproduction_packet`
- `debug_packet`
- `runbook_packet`
- `governance_packet`

---

### Task 1: Define the handoff contract and seed/live builders

**Files:**
- Modify: `server/services/surface_payloads.py`
- Modify: `server/services/enterprise_runtime.py`
- Modify: `server/services/incidents.py`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Write failing contract tests for `handoff_flow`**

Add assertions that incident context now includes:
- `handoff_flow.current_owner`
- `handoff_flow.previous_owner`
- `handoff_flow.next_owner`
- `handoff_flow.transfer_reason`
- `handoff_flow.events`
- event packet objects with `packet_type`, `summary`, and `fields`

Run:

```bash
pytest tests/test_api_contract.py -q
```

Expected:
- contract test fails because `handoff_flow` is missing

- [ ] **Step 2: Add seeded handoff contract builder**

Implement a helper in `server/services/surface_payloads.py` that maps the existing seeded incident packet into six canonical handoff stages:
- SENTINEL emits triage packet
- PRISM emits diagnosis packet
- REPLICA emits reproduction packet
- TRACE emits debug packet
- FORGE emits runbook packet
- GUARDIAN receives governance packet

Required event packet content:
- SENTINEL packet: issue family, likely owner, customer path, support coverage
- PRISM packet: diagnosis summary, evidence basis, memory count, branch status
- REPLICA packet: selected pack, runtime posture, reproduced symptom, comparison outcome
- TRACE packet: inspect-here-first target, likely module/function, divergence clue, residual risk
- FORGE packet: recommended action, alternatives, rollback posture, runtime posture
- GUARDIAN packet: approval level, risk class, rationale, execution gate

- [ ] **Step 3: Add live handoff contract builder**

Implement equivalent logic in `server/services/enterprise_runtime.py` so fresh `nxs_...` incidents use the same six-agent event vocabulary and packet labels as seeded incidents.

Guardrails:
- do not fabricate runtime validation
- if a live incident is inference-first or unsupported, packet fields must say so explicitly

- [ ] **Step 4: Thread additive field through the incident context**

Ensure the incident context returned to the frontend includes the new `handoff_flow` field without breaking existing payload consumers.

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/test_api_contract.py tests/test_app.py -q
```

Expected:
- PASS for the new additive handoff contract

- [ ] **Step 6: Commit**

```bash
git add server/services/surface_payloads.py server/services/enterprise_runtime.py server/services/incidents.py tests/test_api_contract.py tests/test_app.py
git commit -m "feat(#125): add incident handoff flow contract"
```

---

### Task 2: Build current-owner state and baton rail UI

**Files:**
- Modify: `frontend/incident.html`
- Modify: `frontend/static/incident.js`
- Modify: `frontend/static/dashboard.css`
- Test: `tests/e2e/browser-verification.spec.js`

- [ ] **Step 1: Add failing browser assertions for current-owner visibility**

Add checks for:
- `Current control` surface showing explicit owner
- visible previous owner and next owner
- baton rail labels showing one active owner and completed prior owners across six agents

Run:

```bash
npm run browser:verify
```

Expected:
- browser verification fails because the new owner-specific UI is missing

- [ ] **Step 2: Add HTML placeholders**

Add a compact handoff control strip near the existing collaboration area with these ids:
- `handoffCurrentOwner`
- `handoffPreviousOwner`
- `handoffNextOwner`
- `handoffTransferReason`
- `handoffCurrentState`

Extend the existing relay strip to include:
- `relayReplica`
- `relayTrace`

Extend the crew stack to include:
- `crew-bot` entries for `REPLICA`
- `crew-bot` entries for `TRACE`

Do not remove the existing relay strip; evolve it into the six-agent rail.

- [ ] **Step 3: Render baton state in `incident.js`**

Add a render function that consumes `handoff_flow` and updates:
- current owner copy
- previous/next owner labels
- baton state classes on `relaySentinel`, `relayPrism`, `relayReplica`, `relayTrace`, `relayForge`, `relayGuardian`

State vocabulary:
- `completed`
- `active`
- `waiting`
- `blocked`

- [ ] **Step 4: Style the baton rail**

Add CSS so the active owner is unmistakable:
- active owner gets strongest contrast and glow
- completed owners read clearly as done, not hidden
- waiting owner reads as next in line

Do not use motion-only cues; the state must remain understandable in a static screenshot.

- [ ] **Step 5: Run browser verification**

Run:

```bash
npm run browser:verify
```

Expected:
- current-owner assertions pass

- [ ] **Step 6: Commit**

```bash
git add frontend/incident.html frontend/static/incident.js frontend/static/dashboard.css tests/e2e/browser-verification.spec.js
git commit -m "feat(#126): add current-owner baton rail"
```

---

### Task 3: Add emitted-packet and received-packet UI plus handoff ledger

**Files:**
- Modify: `frontend/incident.html`
- Modify: `frontend/static/incident.js`
- Modify: `frontend/static/dashboard.css`
- Test: `tests/e2e/browser-verification.spec.js`
- Test: `tests/test_api_contract.py`

- [ ] **Step 1: Add failing assertions for packet and ledger visibility**

Add browser checks for:
- a received-packet card
- an emitted-packet card
- a ledger list with multiple handoff events

Run:

```bash
npm run browser:verify
```

Expected:
- packet and ledger assertions fail

- [ ] **Step 2: Add HTML surfaces**

Add these ids:
- `handoffReceivedPacketTitle`
- `handoffReceivedPacketSummary`
- `handoffReceivedPacketFields`
- `handoffEmittedPacketTitle`
- `handoffEmittedPacketSummary`
- `handoffEmittedPacketFields`
- `handoffLedger`

Place them above the broader technical disclosure, not buried inside it.

When the current owner is `REPLICA` or `TRACE`, the packet cards must read as first-class agent packets, not as side notes under FORGE.

- [ ] **Step 3: Render packets from `handoff_flow.events`**

In `frontend/static/incident.js`, derive:
- the packet most recently received by the current owner
- the packet most recently emitted by the current owner

If an agent has not yet emitted a packet:
- show explicit “No emitted packet yet” wording

- [ ] **Step 4: Render ledger entries**

Render each event with:
- `from -> to`
- event title
- status
- reason
- packet summary

Order:
- chronological top-to-bottom

- [ ] **Step 5: Add CSS for packet cards and ledger**

The packet surfaces should be:
- concise
- readable without expansion
- clearly different from the larger task board and audit ledger

- [ ] **Step 6: Run focused tests**

Run:

```bash
pytest tests/test_api_contract.py -q
npm run browser:verify
```

Expected:
- PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/incident.html frontend/static/incident.js frontend/static/dashboard.css tests/e2e/browser-verification.spec.js tests/test_api_contract.py
git commit -m "feat(#127): add handoff packet cards and ledger"
```

---

### Task 4: Make transfer state and animations clearer

**Files:**
- Modify: `frontend/static/incident.js`
- Modify: `frontend/static/dashboard.css`
- Test: `tests/e2e/browser-verification.spec.js`

- [ ] **Step 1: Add failing assertions for transition clarity**

Add browser checks that:
- the active owner changes during replay mode
- transfer reason text updates when the baton moves

Run:

```bash
npm run browser:verify
```

Expected:
- replay-state assertions fail or remain too generic

- [ ] **Step 2: Refactor relay animation around handoff events**

Update `playAgentRelay(...)` so it no longer only advances a generic index. Instead, it should step through `handoff_flow.events` and update:
- active owner
- completed owner
- current transfer reason
- current packet snapshot

- [ ] **Step 3: Add explicit transfer state copy**

For each stage transition, show one line like:
- `SENTINEL handed triage packet to PRISM`
- `PRISM accepted triage packet and opened diagnosis branches`

This copy must come from the event contract, not from a hardcoded generic string set.

- [ ] **Step 4: Add bounded animation polish**

Add:
- baton pulse on active owner
- subtle ledger highlight on current event
- packet card highlight when received/emitted changes

Keep motion low enough for operator use; this is not a marketing animation.

- [ ] **Step 5: Run browser verification**

Run:

```bash
npm run browser:verify
```

Expected:
- PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/static/incident.js frontend/static/dashboard.css tests/e2e/browser-verification.spec.js
git commit -m "feat(#128): clarify agent transfer states and motion"
```

---

### Task 5: Add demo replay mode for the handoff chain

**Files:**
- Modify: `frontend/incident.html`
- Modify: `frontend/static/incident.js`
- Modify: `frontend/static/dashboard.css`
- Test: `tests/e2e/browser-verification.spec.js`
- Test: `tests/test_app.py`

- [ ] **Step 1: Add failing browser assertions for replay controls**

Add checks for:
- replay start button
- step-forward control
- reset control
- visible replay mode state label

Run:

```bash
npm run browser:verify
```

Expected:
- replay control assertions fail

- [ ] **Step 2: Add replay controls to the incident UI**

Add ids:
- `handoffReplayStart`
- `handoffReplayNext`
- `handoffReplayReset`
- `handoffReplayState`

Keep the existing `Replay handoff` button if it remains useful, but wire the richer replay mode through the new controls.

- [ ] **Step 3: Implement deterministic handoff replay controller**

In `frontend/static/incident.js`, add:
- a replay cursor
- a deterministic render step for each event in `handoff_flow.events`
- reset behavior that returns the incident UI to the fully rendered live state

Rules:
- replay must not mutate server state
- replay must work on both seeded and fresh incidents

- [ ] **Step 4: Add keyboard-safe and click-safe behavior**

Controls should:
- disable `Next` when at the last event
- disable `Start` while replay is already running
- restore the live handoff state when reset completes

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_app.py -q
npm run browser:verify
```

Expected:
- PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/incident.html frontend/static/incident.js frontend/static/dashboard.css tests/e2e/browser-verification.spec.js tests/test_app.py
git commit -m "feat(#129): add handoff chain replay mode"
```

---

### Task 6: Refresh docs and final validation

**Files:**
- Modify: `docs/public/MASTER_OPERATOR_DEMO_GUIDE.md`
- Modify: `docs/public/README.md`
- Modify: `AGENTS.md`
- Modify: `WORKING_STATE.md`
- Modify: `docs/internal/LOOPS_RUNBOOK.md`
- Test: `tests/e2e/browser-verification.spec.js`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Update the master operator walkthrough**

Add owner-facing explanation for:
- current-owner state
- handoff ledger
- packet cards
- replay mode
- six-agent relay with `REPLICA` and `TRACE` as visible participants

- [ ] **Step 2: Update control docs if this backlog is adopted**

Only if this backlog becomes the active frontier:
- point `AGENTS.md`
- point `WORKING_STATE.md`
- point `docs/internal/LOOPS_RUNBOOK.md`

Do claim `REPLICA` and `TRACE` as first-class visible agents only after this slice lands. Keep their bounded execution scope explicit.

- [ ] **Step 3: Run full validation**

Run:

```bash
pytest tests/ -q
npm run browser:verify
python demo.py
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

Expected:
- all gates pass

- [ ] **Step 4: Commit**

```bash
git add docs/public/MASTER_OPERATOR_DEMO_GUIDE.md docs/public/README.md AGENTS.md WORKING_STATE.md docs/internal/LOOPS_RUNBOOK.md
git commit -m "feat(#130): finalize agent handoff UX docs and validation"
```

---

## Self-Review

- Spec coverage:
  - handoff ledger: covered by Tasks 1 and 3
  - current-owner state: covered by Task 2
  - emitted/received packet UI: covered by Task 3
  - clearer transfer animations: covered by Task 4
  - demo replay mode: covered by Task 5
  - `REPLICA` and `TRACE` as visible first-class agents: covered by Tasks 1 and 2
- Placeholder scan:
  - no `TODO`, `TBD`, or undefined task references left
- Scope check:
  - narrow and loop-safe; no platform expansion
- Type consistency:
  - one additive field name used throughout: `handoff_flow`

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-16-agent-handoff-ux-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
