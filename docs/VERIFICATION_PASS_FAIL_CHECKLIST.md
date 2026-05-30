# NEXUS Verification Pass/Fail Checklist

Use this as a quick yes/no checklist while verifying the UI in a browser.

## Before You Start

- [ ] The app starts locally without errors.
- [ ] `/health` returns `ok`.
- [ ] The browser opens to `http://127.0.0.1:8000/queue`.
- [ ] The left navigation is visible on every page.

## Queue

- [ ] The queue is the landing page.
- [ ] Active incidents are visible.
- [ ] Severity and source channel are visible.
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
- [ ] Logs, metrics, traces, and deployments are visible.
- [ ] A newly created incident opens with backend-assembled live context.
- [ ] A live reasoning toggle is visible and can switch the current incident view without manual URL edits.

## Input Channels

- [ ] Raw-log paste intake is visible.
- [ ] The raw input field starts empty.
- [ ] A `Load example logs` button is visible.
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

## Sample Replay

- [ ] Curated replay scenarios are listed.
- [ ] Scenario names are understandable.
- [ ] A replay launch action is visible.
- [ ] The page explains what replay produces.

## RL Training Lab

- [ ] Baseline reward is visible.
- [ ] Trained reward is visible.
- [ ] Reward curve is visible.
- [ ] RL episode contract is visible.
- [ ] Reward evaluation is visible.
- [ ] Reward breakdown is visible.
- [ ] Observation states are visible.
- [ ] The RL episode contract shows the solution proposal, raw priority, priority rank, and live reasoning state.

## Settings

- [ ] Demo mode or product mode is visible.
- [ ] Integration posture is visible.
- [ ] Replay readiness or configuration is visible.
- [ ] The learning-contract count is visible.

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
- [ ] Use the `Guardian gate` buttons if they are visible.
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
