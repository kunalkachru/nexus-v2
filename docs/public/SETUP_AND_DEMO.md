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

1. open `/queue`
2. open the flagship seeded incident workspace
3. click `Inspect intake` to reach `/inputs`
4. submit a guided demo bundle or example logs
5. inspect the created `nxs_...` incident from the top incident brief first
6. show runtime posture, debugging guidance, and governed approval
7. open `/training`
8. show pilot scorecard and latest live triage

The strongest truthful UI path is:

`/queue -> seeded incident -> Inspect intake -> /inputs -> fresh nxs incident -> /training -> /settings`
