# NEXUS Verification Pass/Fail Checklist

Use this as the short yes/no list for manual verification.

## Startup

- [ ] `./scripts/docker_fresh.sh` completes successfully
- [ ] `/health` returns `ok`
- [ ] `/` loads successfully
- [ ] The top nav shows only `Command Center`, `Incident Detail`, and `Learning & Controls`

## Command Center

- [ ] The landing page reads as a command center, not a dense queue dashboard
- [ ] One live incident is clearly the focal point
- [ ] `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN` are visible above the fold
- [ ] Each bot shows role, task, and handoff
- [ ] The queue is present but secondary
- [ ] Deep queue metadata is hidden behind `Expand queue internals`
- [ ] `History` and `Replay` are linked contextually, not as primary nav items

## Incident Detail

- [ ] The page title reads `Incident Detail`
- [ ] The default live-reasoning state is `OFF`
- [ ] `Bring your own OpenAI key` is visible
- [ ] Saving a key masks it in the UI and does not reveal the full secret
- [ ] `Agent Handoff Thread` is visible
- [ ] `SENTINEL handed evidence to PRISM` is visible
- [ ] `Governance Bot` is visible and clearly refers to `GUARDIAN`
- [ ] Guardian actions are visible but not visually dominant
- [ ] `Working memory` is visible
- [ ] Technical details are hidden behind `Expand technical detail`
- [ ] Source payload, system evidence, workflow internals, and audit ledger become visible only after expansion

## Learning & Controls

- [ ] The page title reads `Learning & Controls`
- [ ] `Learning tab`, `Governance tab`, and `Advanced Artifacts` are visible
- [ ] Reward curve is visible without opening advanced artifacts
- [ ] Agent improvement summary is visible without opening advanced artifacts
- [ ] Governance summary is visible without opening advanced artifacts
- [ ] Deep RL records are hidden behind `Advanced Artifacts`

## Advanced Routes

- [ ] `/inputs` loads directly
- [ ] `/history` loads directly
- [ ] `/replay` loads directly
- [ ] `/settings` loads directly
- [ ] None of those routes reintroduce a 7-item primary nav

## Critical Incident Flows

- [ ] Clicking the first incident from `/queue` opens a populated incident console
- [ ] Submitting logs from `/inputs` redirects into a populated `nxs_...` incident
- [ ] `Approve runbook` changes Guardian to approved and execution to executed
- [ ] No incident screen shows `Incident unavailable`
- [ ] No incident screen shows `Waiting for incident context.`

## Final Pass Criteria

- [ ] The product feels less cluttered than before
- [ ] The UI reads as autonomous AI bots collaborating on incidents
- [ ] Only 3 screens are primary in the default journey
- [ ] Dense data is hidden by default and still reachable when expanded
