# Nexus V3 / NEXUS v2 Working State

Use this file as the short handoff for long Codex sessions. Keep it current and compact.

## Goal
- Finish the current Nexus V3 work with minimal token usage.

## Current Phase
- MVP reasoning loop: next
- UI-first roadmap: complete
- Thin backend demo layer: complete
- Production hardening / live integrations: after MVP

## App In One Sentence
- NEXUS v2 is an AI incident-reasoning product that accepts raw incident text or logs, infers likely root cause, proposes solutions, and routes outputs through a safety and learning loop.

## Current Objective
- Build the MVP reasoning loop first: raw logs input, LLM-backed reasoning, solution proposal, safety gate, and RL-ready structured output.
- The consolidated backlog now lives in [docs/NEXUS_v2_PRIORITY_BACKLOG.md](docs/NEXUS_v2_PRIORITY_BACKLOG.md) and is the current ordered task source of truth.

## Latest Completed Milestones
- Raw incident intake now accepts arbitrary priority labels instead of being limited to `P0`-`P4`.
- The raw-log intake field now starts empty, with `Load example logs` as the explicit sample action.
- The incident console and Inputs page now expose a live reasoning toggle so the current incident can switch between live and fallback rendering from the UI.
- Severity handling now accepts `P4` end to end.
- The incident console was refactored into a guided-story layout with lighter cards, collapsible deep-dive panels, and an animated handoff rail between SENTINEL, PRISM, FORGE, and GUARDIAN.
- Queue-first shell, incident console, input channels, replay, training, and settings surfaces are in place.
- The docs status matrix now treats the UI-first roadmap as complete and the next phase as only partially complete.
- Full manual walkthrough, speaker notes, and presenter pack are now documented.
- The manual walkthrough now includes explicit functional checks for queue, inputs, incident console, history, replay, training, and settings.
- Browser verification checklist, pass/fail checklist, and automation script are now available from the live docs.
- The manual walkthrough now explains the live incident context path for newly created incidents versus seeded demo incidents.
- A 5-slide presenter deck has been created as a `.pptx` for review/judging.
- Live docs now explicitly describe the sequential 4-agent handoff: `SENTINEL -> PRISM -> FORGE -> GUARDIAN`.
- A dedicated agent model matrix now records which agents are deterministic, optional-LLM, or still partially wired.
- `server/config.py` now carries explicit runtime defaults, and `.env.example` documents the local token/model setup.
- The incident console now prefers a backend live-context endpoint for real incidents instead of browser-side synthetic data.
- The seeded demo and `/run-incident` path now support optional live OpenAI-backed SENTINEL, PRISM, and FORGE reasoning when `NEXUS_USE_OPENAI=1` and `OPENAI_API_KEY` are set.
- The manual walkthrough now calls out the optional live LLM mode so seeded incident demos can show the reasoning path end to end.
- The full test suite is green after the live reasoning wiring: `99 passed, 1 warning`.
- The Inputs screen now includes a raw-log paste entrypoint and live parse preview for the MVP reasoning loop.
- The Incident Console now shows raw incident text plus normalized evidence for live raw-text incidents.
- The raw-text intake endpoint now creates live incidents with parsed service, severity, signature, and reasoning hints.
- The training surface now exposes an RL-ready episode contract, reward evaluation, and latest-episode observation state.

## Open Blockers
- Observability and evidence are still mostly fixture-backed instead of coming from real adapters.
- GUARDIAN policy enforcement is visible, but the approval/block/execute flow is not yet a fully explicit control gate.
- Production persistence is still not durable enough for restart-safe incident, replay, and training state.
- Auth, tenant, and deployment hardening still need stronger production boundaries.
- No blocking issue for the current documentation/presenter-pack task.
- The product definition is now corrected: the core loop is raw input -> LLM reasoning -> solution -> safety gate -> RL scoring.
- Production persistence still needs to capture the RL episode contract durably across restarts.
- The live reasoning mode still needs a real browser verification pass on a local machine because Chromium is sandbox-blocked in this environment.

## Most Important Source Of Truth
- [README.md](README.md)
- [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](docs/NEXUS_v2_DOC_STATUS_MATRIX.md)
- [docs/NEXUS_v2_PRIORITY_BACKLOG.md](docs/NEXUS_v2_PRIORITY_BACKLOG.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)
- [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md)
- [docs/DEMO_CHEAT_SHEET.md](docs/DEMO_CHEAT_SHEET.md)
- [docs/LIVE_DEMO_SPEAKER_NOTES.md](docs/LIVE_DEMO_SPEAKER_NOTES.md)
- [docs/NEXUS_v2_PHASE2_ROADMAP.md](docs/NEXUS_v2_PHASE2_ROADMAP.md)
- [design-docs/NEXUS_v2_ENTERPRISE_SPECIFICATION.md](design-docs/NEXUS_v2_ENTERPRISE_SPECIFICATION.md)
- [design-docs/NEXUS_v2_Master_Product_Document.md](design-docs/NEXUS_v2_Master_Product_Document.md)
- [design-docs/NEXUS_v2_Design_Document.md](design-docs/NEXUS_v2_Design_Document.md)

## Files Most Likely To Change Next
- `server/services/live_ingest.py`
- `server/services/observability.py`
- `server/services/incidents.py`
- `server/app.py`
- `server/models.py`
- `server/agents/forge.py`
- `server/agents/prism.py`
- `server/agents/sentinel.py`
- `.env.example`
- `frontend/inputs.html`
- `frontend/static/inputs.js`
- `frontend/incident.html`
- `frontend/static/incident.js`
- `tests/test_observability.py`
- `tests/test_api_contract.py`
- `tests/test_agents.py`
- `tests/test_demo.py`
- `frontend/static/api.js`
- `docs/NEXUS_v2_DOC_STATUS_MATRIX.md`
- `docs/AGENT_MODEL_MATRIX.md`
- `docs/NEXUS_v2_PRIORITY_BACKLOG.md`
- `WORKING_STATE.md`

## Next Exact Action
- Make GUARDIAN an explicit approval/block control gate in the incident console and backend flow.

## Current Mode
- Default model: `gpt-5.4-mini`
- Reasoning: `low` or `medium` for routine work
- Reasoning: `high` only for hard blockers

## Working Rules
- Make the smallest useful change.
- Read only the files needed for the next step.
- Run only targeted tests.
- Avoid broad exploration unless a bug actually requires it.
- Prefer concise answers and patch-style edits.

## Session Handoff
Paste this into a new Codex session when you want to restart without reloading the full conversation:

```text
Project: Nexus V3 / NEXUS v2

Goal:
Finish the current Nexus work with minimal token usage.

Current phase:
- MVP reasoning loop: next
- UI-first roadmap: complete
- Thin backend demo layer: complete
- Production hardening / live integrations: after MVP

Current objective:
- Build the MVP reasoning loop first: raw logs input, LLM-backed reasoning, solution proposal, safety gate, and RL-ready structured output.

Application state:
- The queue-first shell, incident console, input channels, replay, training, and settings surfaces are already in place.
- The product feels enterprise-grade in the UI, but the core product now needs a raw-log-to-root-cause reasoning flow.
- The next meaningful step is to make raw incident text the primary input and preserve structured outputs for RL scoring.

Open blockers:
- Raw-log intake and parsing are not yet the primary user entrypoint.
- The MVP still needs a clearer structured output contract for RL scoring.
- Observability and evidence are still mostly fixture-backed.
- GUARDIAN policy enforcement is visible, but not a fully explicit control gate.
- Production persistence is not yet durable enough for restart-safe state.
- Auth, tenant, and deployment hardening still need stronger boundaries.

Most important source of truth:
- `README.md`
- `docs/NEXUS_v2_DOC_STATUS_MATRIX.md`
- `docs/NEXUS_v2_PRIORITY_BACKLOG.md`
- `docs/OPERATIONS.md`
- `docs/DEMO_WALKTHROUGH.md`
- `docs/DEMO_CHEAT_SHEET.md`
- `docs/LIVE_DEMO_SPEAKER_NOTES.md`
- `docs/BROWSER_VERIFICATION_CHECKLIST.md`
- `docs/VERIFICATION_PASS_FAIL_CHECKLIST.md`
- `scripts/browser_verification.sh`
- `docs/DEMO_WALKTHROUGH.md`
- `docs/NEXUS_v2_PHASE2_ROADMAP.md`
- `design-docs/NEXUS_v2_ENTERPRISE_SPECIFICATION.md`
- `design-docs/NEXUS_v2_Master_Product_Document.md`
- `design-docs/NEXUS_v2_Design_Document.md`

Files most likely to change:
- `server/services/observability.py`
- `server/services/incidents.py`
- `server/app.py`
- `server/models.py`
- `tests/test_observability.py`
- `tests/test_api_contract.py`

Next exact action:
- Implement the MVP raw-log intake and reasoning flow first, then wire it into the incident console and RL-ready output contract.

Current operating mode:
- Default to `gpt-5.4-mini`
- Use `low` or `medium` reasoning for routine work
- Use `high` only for genuinely hard blocks
- Prefer concise answers and patch-style changes

Work rules:
- Make the smallest possible change
- Read only the files needed for the next step
- Run only targeted tests
- Avoid broad exploration unless a bug actually demands it
- If the task is unclear, ask one short question before doing extra work

Output format:
- Start with the answer or patch
- Then give a brief note on what changed
- Keep explanations short unless I ask for detail
```
