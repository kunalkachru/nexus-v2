# NEXUS Verification Pass/Fail Checklist

## Startup

- [ ] `ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh` completes
- [ ] `/health` returns `ok`
- [ ] `/queue` loads

## Product Truth

- [ ] public docs describe five bounded families
- [ ] public demo docs reflect the queue-first operator path
- [ ] UI no longer says `NEXUS v2`
- [ ] runtime-backed versus inference-first wording is explicit
- [ ] no screen implies replay executed if it did not
