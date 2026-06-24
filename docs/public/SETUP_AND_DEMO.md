# NEXUS Setup and Demo Run Path

**Updated:** 2026-06-17  
**Status:** Production Ready

This is the shortest setup path for a truthful local product demo.

**For complete setup instructions and testing checklist, see: [MASTER_GUIDE.md](../MASTER_GUIDE.md)**

## Preferred Local Start

```bash
export OPENAI_API_KEY=sk-proj-your-key-here  # Optional but recommended
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

**Expected:** Fresh container ready in ~30 seconds

## Core Validation

Run these before a serious demo:

```bash
pytest tests/ -q                    # Should pass: 76 passed
npm run browser:verify              # Should pass: 16 passed
python demo.py                      # Should complete
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

## Best Demo Sequence

1. open `/queue` — see focal incident and specialist crew
2. open the flagship seeded incident workspace — review details
3. click `Inspect intake` to reach `/inputs` — show evidence intake
4. submit a guided demo bundle or example logs — demonstrate auto-processing
5. inspect the created `nxs_...` incident from the top incident brief first — show structured output
6. show runtime posture, debugging guidance, and governed approval — demonstrate GUARDIAN gate
7. open `/training` — show pilot scorecard and live triage metrics
8. open `/settings` — demonstrate system readiness and configuration

**The strongest truthful UI path is:**

`/queue → seeded incident → Inspect intake → /inputs → fresh nxs incident → /training → /settings`

## Configuration

See [MASTER_GUIDE.md - Environment Variables](../MASTER_GUIDE.md#part-9--environment-variables) for:
- Environment variables
- Tenant setup
- Database configuration
- OpenAI integration
- Runtime host relay (for demo playback)

## Testing

See [MASTER_GUIDE.md - Running All Tests](../MASTER_GUIDE.md#part-3--running-all-tests) to validate all functionality end-to-end.

## Troubleshooting

See [MASTER_GUIDE.md - Troubleshooting](../MASTER_GUIDE.md#part-8--troubleshooting) for:
- Service startup issues
- Health check failures
- Database problems
- Test failures
- Performance issues
