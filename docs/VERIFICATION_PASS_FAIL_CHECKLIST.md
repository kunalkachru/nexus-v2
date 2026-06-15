# NEXUS Verification Pass/Fail Checklist

Use this as the short manual go/no-go list.

## Startup

- [ ] `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` completes
- [ ] `/health` returns `ok`
- [ ] `/queue` loads
- [ ] the primary nav shows `Command Center`, `Incident Detail`, and `Learning & Controls`

## Fresh Incident Flow

- [ ] `/inputs` loads
- [ ] `Load example logs` works
- [ ] `Submit raw logs` redirects into a populated `nxs_...` incident
- [ ] the new incident shows issue framing, memory, and operator next step

## Incident Console

- [ ] `Investigation Summary & Operator Path` is visible
- [ ] `Enterprise Task Board` is visible
- [ ] replay capability and replay host fields are populated
- [ ] bounded debugger or trace packet is visible for a supported incident
- [ ] Guardian controls are visible

## Approval And Outcome

- [ ] `Approve runbook` changes Guardian state
- [ ] execution outcome becomes visible
- [ ] `/training` reflects the latest live triage and outcome

## Runtime Truth

- [ ] runtime-backed versus inference-first wording is explicit
- [ ] unsupported or bounded behavior is clearly labeled when applicable
- [ ] no screen implies replay executed if it did not

## Final Decision

- [ ] the product feels coherent end to end
- [ ] the demo story matches the actual product boundaries
