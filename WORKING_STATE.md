# Nexus V3 / NEXUS v2 Working State

Use this file as the short handoff for long Codex sessions. Keep it current and compact.

## Goal
- Finish the current Nexus V3 work with minimal token usage.

## Current Phase
- UI-first roadmap: complete
- Thin backend demo layer: complete
- Production hardening / live integrations: next

## App In One Sentence
- NEXUS v2 is an enterprise incident-response product that turns noisy alerts into a queue-first workflow, an explainable incident console, and a controlled path from intake to resolution.

## Current Objective
- Finish the current Nexus V3 project with minimal token usage and keep the working state concise.

## Latest Completed Milestones
- Queue-first shell, incident console, input channels, replay, training, and settings surfaces are in place.
- The docs status matrix now treats the UI-first roadmap as complete and the next phase as only partially complete.
- Full manual walkthrough, speaker notes, and presenter pack are now documented.
- The manual walkthrough now includes explicit functional checks for queue, inputs, incident console, history, replay, training, and settings.
- Browser verification checklist, pass/fail checklist, and automation script are now available from the live docs.
- A 5-slide presenter deck has been created as a `.pptx` for review/judging.
- Live docs now explicitly describe the sequential 4-agent handoff: `SENTINEL -> PRISM -> FORGE -> GUARDIAN`.
- A dedicated agent model matrix now records which agents are deterministic, optional-LLM, or still partially wired.
- `server/config.py` now carries explicit runtime defaults, and `.env.example` documents the local token/model setup.
- The incident console now prefers a backend live-context endpoint for real incidents instead of browser-side synthetic data.

## Open Blockers
- Observability and evidence are still mostly fixture-backed instead of coming from real adapters.
- GUARDIAN policy enforcement is visible, but the approval/block/execute flow is not yet a fully explicit control gate.
- Production persistence is still not durable enough for restart-safe incident, replay, and training state.
- Auth, tenant, and deployment hardening still need stronger production boundaries.
- No blocking issue for the current documentation/presenter-pack task.
- The app-level model/provider story is clearer now, but the enterprise hybrid LLM plan still needs a real PRISM/Forge implementation round.
- The current live-context path is backend-driven, but the underlying observability adapters are still not fully real external integrations.

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
- `server/services/observability.py`
- `server/services/incidents.py`
- `server/app.py`
- `server/models.py`
- `server/agents/forge.py`
- `.env.example`
- `tests/test_observability.py`
- `tests/test_api_contract.py`
- `tests/test_agents.py`
- `frontend/static/api.js`
- `docs/NEXUS_v2_DOC_STATUS_MATRIX.md`
- `docs/AGENT_MODEL_MATRIX.md`
- `docs/NEXUS_v2_PRIORITY_BACKLOG.md`
- `WORKING_STATE.md`

## Next Exact Action
- Use `WORKING_STATE.md` as the short handoff and update it before the next substantive change.

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
- UI-first roadmap: complete
- Thin backend demo layer: complete
- Production hardening / live integrations: next

Current objective:
- Close the biggest credibility gap by implementing live backend incident context and then real observability adapter fusion.

Application state:
- The queue-first shell, incident console, input channels, replay, training, and settings surfaces are already in place.
- The product feels enterprise-grade in the UI, and the incident console now prefers a backend live-context payload for created incidents.
- The next meaningful step is to replace fixture-backed evidence with real adapter-backed observability and provenance.

Open blockers:
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
- Implement real observability ingestion and evidence fusion starting with the service layer and observability tests.

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
