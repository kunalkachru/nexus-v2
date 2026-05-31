# NEXUS Verification Pass/Fail Checklist

Use this as a quick yes/no checklist while verifying the UI in a browser.

## What Was Checked In This Pass

- Raw input starts empty and `Load example logs` works.
- Arbitrary priority labels such as `P6` and `critical` are accepted.
- Evidence provenance now shows the fused observability adapter story, not only the static fixtures.
- The incident console shows proposed fix, priority, normalized rank, live reasoning state, and guardian policy metadata.
- The Guardian gate exposes explicit approve, block, and request-modification controls.
- The incident console keeps the top-level summary compact and moves signals, workflow, audit, and agent flow into an `Operational Details` drawer.
- The Inputs page keeps raw logs as the primary demo path and moves Slack, stream anomaly, and batch import into a `More Sources` drawer.
- The main pages include a flow trail and short callout so the UI explains how the screens connect.
- The training lab shows the solution proposal, raw priority, learning-contract count, audit-event count, and Guardian-review count.
- The settings page exposes the learning-contract count, audit-event count, and Guardian-review count.
- Mutating incident routes require an operator role.

## Before You Start

- [ ] The app starts locally without errors.
- [ ] `/health` returns `ok`.
- [ ] The browser opens to `http://127.0.0.1:8000/queue`.
- [ ] The left navigation is visible on every page.

## Queue

- [ ] The queue is the landing page.
- [ ] Active incidents are visible.
- [ ] Severity and source channel are visible.
- [ ] The page shows a trail or callout that makes Queue look like the starting point.
- [ ] Clicking an incident opens the incident console.

## Incident Console

- [ ] The timeline is visible.
- [ ] Intake appears first in the timeline.
- [ ] SENTINEL is shown.
- [ ] PRISM is shown.
- [ ] FORGE is shown.
- [ ] GUARDIAN is shown.
- [ ] Raw incident text is visible for live incidents.
- [ ] Normalized evidence is visible for live incidents.
- [ ] The structured result cards expose proposed fix, priority, normalized rank, and live reasoning state.
- [ ] The structured result cards expose the guardian policy field when a decision has been recorded.
- [ ] Logs, metrics, traces, and deployments are visible.
- [ ] Evidence provenance includes the fused adapter story for logs, metrics, traces, and deployments.
- [ ] A newly created incident opens with backend-assembled live context.
- [ ] A live reasoning toggle is visible and can switch the current incident view without manual URL edits.
- [ ] The screen includes a trail or callout that explains how Incident relates to Queue, Inputs, and the rest of the product.

## Input Channels

- [ ] Raw-log paste intake is visible.
- [ ] The raw input field starts empty.
- [ ] A `Load example logs` button is visible.
- [ ] The `More Sources` drawer keeps the alternate intake paths available without crowding the raw-log path.
- [ ] The page includes a trail or callout that explains Inputs as the raw-entry path.
- [ ] The parsed preview updates when the pasted text changes.
- [ ] Webhook intake is visible.
- [ ] Manual intake is visible.
- [ ] Slack-style intake is visible.
- [ ] Stream intake is visible.
- [ ] Batch import is visible.

## History

- [ ] Past incidents are listed.
- [ ] Closed outcomes are visible.
- [ ] Replay or review actions are visible.
- [ ] The page includes a trail or callout that explains History as the archive between live work and replay.

## Sample Replay

- [ ] Curated replay scenarios are listed.
- [ ] Scenario names are understandable.
- [ ] A replay launch action is visible.
- [ ] The page explains what replay produces.
- [ ] The page includes a trail or callout that explains Replay as the repeatable validation lane.

## RL Training Lab

- [ ] Baseline reward is visible.
- [ ] Trained reward is visible.
- [ ] Reward curve is visible.
- [ ] RL episode contract is visible.
- [ ] Reward evaluation is visible.
- [ ] Reward breakdown is visible.
- [ ] Observation states are visible.
- [ ] The RL episode contract shows the solution proposal, raw priority, priority rank, and live reasoning state.
- [ ] The training page shows audit-event and Guardian-review counts.
- [ ] The page includes a trail or callout that explains Training as the memory layer.

## Settings

- [ ] Demo mode or product mode is visible.
- [ ] Integration posture is visible.
- [ ] Replay readiness or configuration is visible.
- [ ] The learning-contract count is visible.
- [ ] The audit-event and Guardian-review counts are visible.
- [ ] The page includes a trail or callout that explains Settings as the trust and control plane.

## Hardening Check

- [ ] A request with the `viewer` role is rejected from a mutating incident route with HTTP 403.
- [ ] The normal operator browser flow still works for incident creation, Guardian review, and replay launch.

## End-To-End Flow

- [ ] Start on Queue.
- [ ] Open one incident.
- [ ] Walk the timeline from intake to outcome.
- [ ] Open Inputs, keep or replace the sample raw logs, and confirm the parsed preview updates.
- [ ] Open Inputs, confirm the raw field starts empty, and use `Load example logs` only if you want a sample.
- [ ] Paste a severity like `P6` or `critical` and confirm the parser accepts it.
- [ ] Click `Submit raw logs` and confirm a new incident is created.
- [ ] Open the incident console link returned from Inputs.
- [ ] Confirm `Raw Intake` is visible.
- [ ] Confirm `Normalized evidence` is visible and read-only.
- [ ] Confirm the `SENTINEL -> PRISM -> FORGE -> GUARDIAN` rail is visible and read-only.
- [ ] Confirm the live reasoning toggle can switch the incident view on the fly.
- [ ] Confirm the incident summary shows the proposed fix and priority fields.
- [ ] Confirm the incident summary shows the guardian policy field when it is present.
- [ ] Use the `Guardian gate` buttons if they are visible.
- [ ] Confirm the `Request modification` path moves the incident into `NEEDS_MODIFICATION` and leaves execution paused.
- [ ] Confirm the approve path moves the incident into `EXECUTED`.
- [ ] Confirm the block path leaves the incident blocked and does not execute the runbook.
- [ ] Show input channels.
- [ ] Show history.
- [ ] Launch a sample replay.
- [ ] Open the training lab.
- [ ] Confirm the RL episode contract.
- [ ] Confirm the training view shows the solution proposal, raw priority, and learning contract count.
- [ ] Finish in settings.

## Pass Criteria

- [ ] The pages feel like one product.
- [ ] The incident story is easy to follow.
- [ ] The agent contributions are clear.
- [ ] The replay flow is repeatable.
- [ ] The learning story is understandable.
