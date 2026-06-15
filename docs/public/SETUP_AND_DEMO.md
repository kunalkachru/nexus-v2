# NEXUS Setup And Demo Run Path

This is the shortest setup path for a truthful local product demo.

## Preferred Local Start

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

Then open:

- [http://127.0.0.1:7860](http://127.0.0.1:7860)

## Core Validation

Run these before a serious demo:

```bash
pytest tests/ -q
npm run browser:verify
python demo.py
EXPECT_RUNTIME_HOST_RELAY=1 BASE_URL=http://127.0.0.1:7860 ./scripts/local_enterprise_smoke.sh
```

## Best Demo Sequence

1. open `/inputs`
2. submit example logs
3. inspect the created `nxs_...` incident
4. show runtime posture and debugger guidance
5. approve the runbook
6. open `/training`
7. show pilot scorecard and latest live triage
