# NEXUS Railway Deployment Guide

NEXUS is a support-to-engineering investigation product that pairs AI reasoning with human governance. This guide walks through deploying NEXUS to Railway.

## Prerequisites

- Railway account (free tier available at [railway.app](https://railway.app))
- GitHub account with this repository
- OpenAI API key (optional — required only if you want live LLM reasoning; see [OPENAI_API_KEY](#environment-variables))

## One-Time Setup on Railway

### 1. Connect Your Repository

1. Log in to [railway.app](https://railway.app)
2. Click **"New Project"**
3. Select **"Deploy from GitHub"**
4. Authorize Railway to access your GitHub account
5. Select the `nexus-v2` repository
6. Click **"Deploy"**

Railway will automatically detect the `Dockerfile` and `railway.toml` and begin the first build.

### 2. Configure Environment Variables

Once the project is created:

1. Open the **NEXUS** service in Railway
2. Go to the **"Variables"** tab
3. Add each variable from the template below (copy from `.env.example` in the repo)

**Required variables (copy from `.env.example`):**

```
NEXUS_DATABASE_PATH=/app/artifacts/incidents.json
NEXUS_WEBHOOK_SIGNING_SECRET=(generate with: python -c 'import secrets; print(secrets.token_hex(32))')
NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system
NEXUS_FORGE_MODEL_NAME=gpt-4o
NEXUS_USE_OPENAI=0
OPENAI_API_KEY=(leave blank unless using live reasoning)
```

**Important:** The database path **must** be `/app/artifacts/incidents.json` (absolute path in the container).

### 3. Add Persistent Volume for SQLite Database

1. In Railway, open the NEXUS service
2. Go to the **"Data"** tab
3. Click **"Create Volume"**
4. Set mount path to: `/app/artifacts`
5. Size: 1 GB (free tier allows up to 5 GB)
6. Click **"Create"**

This ensures the SQLite database persists across redeploys and crashes.

### 4. Configure Domain (Optional)

If you want a custom domain:

1. Go to **"Settings"** tab
2. Under **"Networking"**:
   - Copy the auto-generated Railway domain (e.g., `nexus-prod-xyz.up.railway.app`)
   - Or add a custom domain if you own one

## Verify Deployment Worked

### Test the Health Endpoint

After deployment completes (watch the **"Build Logs"** for confirmation):

```bash
curl https://your-railway-domain/health
```

Expected response:
```json
{"status": "ok"}
```

### Test the Queue Page

Open in your browser:
```
https://your-railway-domain/queue
```

You should see the NEXUS Command Center with the five seeded incidents (INC001–INC007) available to review.

### Smoke Test: Full Fresh Incident Flow

1. Go to `/inputs` on your Railway deployment
2. Select a demo bundle or paste raw logs
3. Click **"Submit raw logs"**
4. You should navigate to a fresh incident detail page
5. Verify the six agents (SENTINEL, PRISM, REPLICA, TRACE, FORGE, GUARDIAN) progress through their tasks
6. Click the Guardian approval buttons to test governance flow

## How to Update the Deployment

NEXUS uses **auto-deploy on push**:

1. Make changes locally and test them
2. Commit and push to `master`:
   ```bash
   git push origin master
   ```
3. Railway automatically detects the push
4. New Docker image builds and deploys
5. No manual action needed — watch the **"Build Logs"** in Railway for progress

Rollback: If needed, Railway keeps previous builds. You can redeploy an older build from the **"Deployments"** tab.

## Known Limitations (Free Tier)

### 1. Sleep After Inactivity

Railway free tier suspends services after 7 days of inactivity. To keep NEXUS running:

- Set up a monitoring cronjob to ping `/health` daily, or
- Upgrade to the **Hobby** plan ($5/month) for always-on deployment

### 2. Docker-in-Docker Not Available

NEXUS includes bounded **REPLICA** runtime replay (curated Docker-backed execution). Railway free tier does not support Docker-in-Docker, so:

- Seeded incidents (INC001–INC007) work fully with runtime replay
- Fresh incidents from `/inputs` will show REPLICA as "deterministic fallback" instead of live execution
- Upgrade to a Railway plan with Docker support to enable live REPLICA replay

### 3. Limited Persistent Storage

Railway free tier provides:
- 1 GB persistent storage (more than enough for the SQLite database)
- Up to 100 build minutes/month

## Environment Variables Reference

| Variable | Required? | Default | Purpose |
|----------|-----------|---------|---------|
| `NEXUS_DATABASE_PATH` | Yes | `artifacts/incidents.json` | Where SQLite database is stored (use `/app/artifacts/incidents.json` on Railway) |
| `NEXUS_WEBHOOK_SIGNING_SECRET` | No | demo secret | Random secret for webhook validation; generate a production value |
| `NEXUS_ALLOWED_TENANT_IDS` | No | `tenant-a,tenant-system` | Comma-separated tenant IDs allowed to use the system |
| `NEXUS_FORGE_MODEL_NAME` | No | `gpt-4o` | LLM model name for FORGE agent reasoning |
| `NEXUS_USE_OPENAI` | No | `0` | Set to `1` to enable live OpenAI reasoning (requires `OPENAI_API_KEY`) |
| `OPENAI_API_KEY` | No | (empty) | OpenAI API key (required if `NEXUS_USE_OPENAI=1`) |
| `NEXUS_RUNTIME_HOST_BASE_URL` | No | (empty) | For advanced setups: base URL of external runtime host |
| `NEXUS_RUNTIME_HOST_SHARED_TOKEN` | No | (empty) | For advanced setups: auth token for runtime host |

## Troubleshooting

### Build Fails

1. Check **"Build Logs"** in Railway for error details
2. Verify all required files are in git (Dockerfile, requirements.txt, etc.)
3. Verify no secrets are in `.env` file — that file should only contain placeholders

### Service Keeps Restarting

1. Check **"View Logs"** in the service
2. Common issues:
   - Missing environment variables (especially `OPENAI_API_KEY` if `NEXUS_USE_OPENAI=1`)
   - Persistent volume not mounted — verify in **"Data"** tab that `/app/artifacts` is mounted
   - Database file corrupt — clear the volume and redeploy

### Health Check Failing

1. Ensure `/app/artifacts` volume is mounted
2. Check service logs for permission errors
3. Try restarting the service from the **"Settings"** tab

## Next Steps

- Review the [NEXUS product guide](docs/public/README.md) to understand the six-agent pipeline
- See [docs/internal/production-deployment-guide.md](docs/internal/production-deployment-guide.md) for advanced deployment topics
- Read [docs/internal/monitoring-playbook-24hr.md](docs/internal/monitoring-playbook-24hr.md) for 24-hour production monitoring procedures

---

**Questions?** See [AGENTS.md](AGENTS.md) for internal documentation or [docs/README.md](docs/README.md) for all available guides.
