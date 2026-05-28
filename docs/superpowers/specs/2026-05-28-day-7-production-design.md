# Day 7 Production Design

## Goal

Ship a production-ready NEXUS v2 package for HuggingFace Spaces with a judge-facing demo path, a static metrics dashboard, and containerized FastAPI serving.

## Scope

- Add a static responsive dashboard at `frontend/dashboard.html`.
- Add a judge-facing `demo.py` that runs one incident through the full four-agent flow.
- Add production packaging files for HF Spaces: `Dockerfile`, `requirements.txt`, `.gitignore`, `README.md`.
- Extend the FastAPI app to serve the dashboard and expose runtime metadata endpoints.

## Architecture

### Metrics

Use the existing deterministic Day 6 training pipeline as the source of truth. A small reporting layer will convert `TrainingSummary` into:

- reward curve
- per-episode cost curve
- difficulty progression
- aggregate agent accuracy metrics
- total and average training cost

The metrics payload will be written to JSON so both `demo.py` and the dashboard can consume the same data.

### Dashboard

Keep the frontend build-free. `frontend/dashboard.html` will:

- fetch a local JSON metrics document
- render charts with lightweight inline SVG
- show summary cards and a 30-episode progression table
- degrade gracefully when opened directly from disk

The page will be styled with hand-written responsive CSS and no asset pipeline.

### Demo

`demo.py` will:

- load or generate the Day 6 metrics/checkpoint artifact
- build the deterministic four-agent pipeline
- select one incident from the catalogue
- time the end-to-end execution
- print the exact judge-facing outputs in a stable order

FORGE will use a deterministic offline client by default so the demo remains fast and reliable. If `OPENAI_API_KEY` is present, the codebase will remain compatible with a live OpenAI-backed client path without making it mandatory for local smoke tests.

### Deployment

FastAPI will serve:

- `/health`
- `/api/metrics`
- `/`
- `/dashboard`
- static frontend files from `frontend/`

Docker will run `uvicorn` on port `7860`, matching HF Spaces defaults.

## Error Handling

- Missing metrics file triggers deterministic regeneration from the training runner.
- Demo failures surface explicit errors for missing dependencies or malformed artifacts.
- Dashboard fetch failures fall back to embedded starter metrics so local file opening still works.

## Testing

- App tests cover dashboard/static serving and metrics API.
- Demo tests cover artifact generation and required output fields.
- Training tests continue to enforce the 30-episode reward target and cost tracking.

