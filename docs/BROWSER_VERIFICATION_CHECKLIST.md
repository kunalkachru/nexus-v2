# NEXUS Browser Verification Checklist

Use this document to verify the UI manually in a browser after the implementation is complete.

## Purpose

This checklist confirms that the enterprise workflow UI loads correctly, the main pages are wired, and the demo flow can be followed end to end.

## Prerequisites

- A local checkout of the repository.
- A Python environment with the project dependencies installed.
- A browser such as Chrome, Safari, or Firefox.

On this machine, the simplest working interpreter is:

- `/opt/anaconda3/bin/python`

## Setup

1. Open a terminal in the repository root.
2. Start the application server:

```bash
uvicorn server.app:app --host 127.0.0.1 --port 8000
```

3. Keep that terminal running.
4. Open a browser and go to:

```text
http://127.0.0.1:8000/queue
```

## Automatic Option

If you want the environment to start, run the tests, and open the verification pages for you, use:

```bash
bash scripts/browser_verification.sh
```

That script:

- runs the test suite
- starts the local server
- waits for `/health`
- opens the verification pages in your browser
- keeps the server running until you stop it

## What To Verify First

Before checking individual pages:

- The app loads without a blank page.
- The main shell renders with the left navigation.
- The browser address bar reflects the page you opened.
- There are no obvious JavaScript or rendering failures.

## Page Verification Order

Verify the pages in this order:

1. `Queue`
2. `Incident Console`
3. `Input Channels`
4. `History`
5. `Sample Replay`
6. `RL Training Lab`
7. `Settings`

This order matches the intended product story.

## Queue Page

Open:

```text
http://127.0.0.1:8000/queue
```

Confirm:

- The queue is the landing page.
- Active incidents are visible.
- Severity, source channel, and stage information are shown.
- Clicking an incident opens the incident console.

Pass criteria:

- The page looks like an operator queue, not a static dashboard.

## Incident Console

Open:

```text
http://127.0.0.1:8000/incident
```

Confirm:

- The incident timeline is visible.
- The workflow starts with intake and moves through agent stages.
- SENTINEL, PRISM, FORGE, and GUARDIAN are each represented.
- Evidence sections for logs, metrics, traces, and deployments are present.

Pass criteria:

- You can explain the incident from intake to outcome using the page alone.

## Input Channels

Open:

```text
http://127.0.0.1:8000/inputs
```

Confirm:

- Multiple intake options are visible.
- The page shows more than one input method.
- The intent of the page is to demonstrate how incidents enter the system.

Pass criteria:

- Each input method appears to feed the same incident workflow.

## History

Open:

```text
http://127.0.0.1:8000/history
```

Confirm:

- Past incidents are listed.
- Closed outcomes are visible.
- Replay or review entry points are available.

Pass criteria:

- The page shows operational memory, not just current-state data.

## Sample Replay

Open:

```text
http://127.0.0.1:8000/replay
```

Confirm:

- Curated replay scenarios are listed.
- Scenario names are understandable to a non-technical audience.
- A replay launch action is available.
- The page explains what replay produces.

Pass criteria:

- You can launch a sample incident and use it as a repeatable demo.

## RL Training Lab

Open:

```text
http://127.0.0.1:8000/training
```

Confirm:

- Baseline reward and trained reward are visible.
- A reward curve is visible.
- Reward breakdown information is visible.
- The observation-state story is visible.

Pass criteria:

- The learning layer is understandable without reading code.

## Settings

Open:

```text
http://127.0.0.1:8000/settings
```

Confirm:

- Demo mode or product mode is shown.
- Integration posture is visible.
- Replay readiness or operational configuration is visible.

Pass criteria:

- The page communicates that the system is deployable, not only demoable.

## End-To-End Demo Check

After the pages are verified individually, do one full walkthrough:

1. Start on `Queue`.
2. Open one incident in `Incident Console`.
3. Walk the timeline from intake to outcome.
4. Switch to `Input Channels` and show the intake options.
5. Open `History` and show a past incident.
6. Open `Sample Replay` and show a curated replay scenario.
7. Open `RL Training Lab` and point to the reward curve and observation states.
8. Finish in `Settings`.

## What Good Looks Like

- The navigation is consistent across pages.
- The pages look like one product, not separate prototypes.
- The incident story is easy to follow.
- The agent contributions are clear.
- The replay and training pages support the main product narrative.

## If Something Fails

- Refresh the page once.
- Check the browser console for errors.
- Confirm the server is still running.
- Revisit the relevant page in the order above.
- If a page still fails, capture:
  - the URL
  - what you expected
  - what actually happened
  - any visible console message

## Optional Verification Command

If you want a quick backend sanity check before opening the browser, run:

```bash
pytest tests/ -q
```

That does not replace browser verification, but it confirms the backend and page routes are healthy.
