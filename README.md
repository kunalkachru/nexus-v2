# NEXUS v2

NEXUS v2 is an autonomous incident response prototype built around four cooperating agents:

- `SENTINEL` classifies the incident.
- `PRISM` diagnoses the likely root cause.
- `FORGE` generates a remediation runbook.
- `GUARDIAN` reviews the runbook for safety before execution.

The repo packages the deterministic Day 6 training loop into a Day 7 production surface for local demos and HuggingFace Spaces deployment.

## Architecture

The orchestration flow is:

1. `SENTINEL` maps live symptoms onto the incident catalogue.
2. `PRISM` produces a structured diagnosis and evidence set.
3. `FORGE` emits a runbook and estimated execution cost.
4. `GUARDIAN` blocks dangerous actions and approves safe ones.
5. `NexusCore` computes a deterministic reward for the full episode.

Training uses a GRPO-style scalar policy simulation over 30 episodes, producing a reward curve that starts at `0.28` and finishes above `0.65`.

## Local Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the judge demo:

```bash
python demo.py
```

Run the app locally:

```bash
uvicorn server.app:app --reload --port 7860
```

Then open `http://localhost:7860/dashboard`.

The dashboard is also available as [`frontend/dashboard.html`](/Users/kunalkachru/Documents/nexus-v3/frontend/dashboard.html) and includes embedded fallback metrics so it can open directly in a browser.

## OPENAI_API_KEY

The default demo path is deterministic so it stays fast and stable for judging. The code also supports an OpenAI-backed FORGE path when `OPENAI_API_KEY` is set and `NEXUS_USE_OPENAI=1`.

```bash
export OPENAI_API_KEY=sk-...
export NEXUS_USE_OPENAI=1
python demo.py
```

## HuggingFace Spaces

Build the container:

```bash
docker build -t nexus-v2 .
```

Run it:

```bash
docker run -p 7860:7860 -e OPENAI_API_KEY=$OPENAI_API_KEY nexus-v2
```

HF Spaces should target port `7860` and launch `uvicorn server.app:app --host 0.0.0.0 --port 7860`.
