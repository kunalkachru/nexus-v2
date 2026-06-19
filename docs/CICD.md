# CI/CD Documentation

## SECTION 1 — Overview

NEXUS is deployed to two environments that serve different purposes:

| Environment | URL | Purpose | Persistence |
|---|---|---|---|
| **Render** | https://nexus-uny5.onrender.com | Public demo instance | None (ephemeral) |
| **Oracle Cloud** | http://nexus-triage.duckdns.org:7860 | Production with persistent data | Named volume (nexus-data) |

### How code gets from your laptop to production

1. **Developer** → Commits code and pushes to GitHub (`git push origin master`)
2. **GitHub** → Receives push to `master` branch
3. **Render** → Automatically detects the push, rebuilds the Docker image, and redeploys (no configuration needed — direct connection to repo)
4. **GitHub Actions** → Simultaneously triggers `.github/workflows/deploy.yml`
5. **GitHub Actions** → SSHes into Oracle Cloud server, pulls latest code, rebuilds Docker image, restarts container
6. **Result** → Both environments updated automatically within ~3-5 minutes

---

## SECTION 2 — How auto-deploy works on Render

Render is directly connected to the GitHub repository (`kunalkachru/nexus-v2`). This is a free-tier deployment that automatically redeploys on every push to the master branch.

### Deployment process
1. Render detects a push to the master branch
2. Render clones the latest code
3. Render reads the `Dockerfile` and builds a new Docker image
4. Render starts a new container with the image, replacing the old one
5. Render assigns a public URL: https://nexus-uny5.onrender.com

### Database persistence
The Render free tier uses an ephemeral filesystem, meaning **the SQLite database resets on every restart or redeploy**. This is intentional for a demo environment.

### Checking deployment status
1. Go to https://render.com and log in
2. Navigate to the `nexus-v2` service dashboard
3. View the "Logs" tab to see build and runtime output
4. View the "Deploys" tab to see deployment history

### Deployment time
Render deployments typically take **3-5 minutes** from push to ready.

---

## SECTION 3 — How auto-deploy works on Oracle Cloud

Oracle Cloud deployment is fully automated via GitHub Actions. On every push to the master branch, GitHub Actions:
1. Checks out the latest code
2. Establishes an SSH connection to the Oracle Cloud server
3. Pulls the latest code from GitHub
4. Rebuilds the Docker image
5. Stops the old container and removes it
6. Starts a new container with persistent storage (named volume)

### Workflow file
The workflow is defined in `.github/workflows/deploy.yml` and is triggered on every push to the `master` branch.

### Security: GitHub Secrets
- The SSH private key (`ORACLE_SSH_KEY`) is stored securely in GitHub Secrets, never exposed in code
- The webhook signing secret is stored as `ORACLE_WEBHOOK_SECRET` in GitHub Secrets
- GitHub Actions reads these secrets and uses them only at deploy time

### Server details
- **Host**: Oracle Cloud VM running Ubuntu
- **IP Address**: 92.5.47.239 (internal; accessed via DNS: nexus-triage.duckdns.org)
- **SSH User**: ubuntu
- **Remote repo path**: ~/nexus-v2

### Persistent storage
Unlike Render, Oracle Cloud uses a **named Docker volume** (`nexus-data:/app/artifacts`) to persist the SQLite database across restarts and redeploys. The database survives container stop/start and redeploys.

### Checking deployment status
1. Go to your GitHub repository: https://github.com/kunalkachru/nexus-v2
2. Click the "Actions" tab
3. View the latest workflow run for the `Deploy to Oracle Cloud` workflow
4. Click into the run to see step-by-step logs
5. If the deploy failed, the error details appear in the "Deploy to Oracle Cloud" step logs

### Deployment time
GitHub Actions deployments typically take **3-5 minutes** from push to live.

### Manual verification
After deployment, you can SSH into the server and check the container status:
```bash
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
docker ps  # Verify nexus container is running
docker logs nexus  # View container logs
curl http://localhost:7860/health  # Verify the health endpoint
```

---

## SECTION 4 — Manual deployment commands

If GitHub Actions fails or you need to deploy immediately without waiting for GitHub Actions, you can deploy manually using the deploy script:

```bash
bash scripts/deploy-oracle.sh
```

This script will:
1. SSH into the Oracle Cloud server
2. Pull the latest code from GitHub
3. Rebuild the Docker image
4. Stop and remove the old container
5. Start a new container with all environment variables set

**Prerequisites for manual deployment:**
- SSH key must be present at `~/Downloads/ssh-key-2026-06-19.key` with permissions `600`
- You must have network access to 92.5.47.239
- The oracle host must have Docker installed and the user must have sudo access

**Detailed manual deploy steps** (if you prefer to run commands directly):
```bash
# 1. Connect to the server
ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239

# 2. On the remote server, run:
cd nexus-v2
git pull origin master
sudo docker build -t nexus .

# 3. Stop and remove old container
sudo docker stop nexus || true
sudo docker rm nexus || true

# 4. Start new container with environment variables
# Replace WEBHOOK_SECRET_VALUE with the actual secret from GitHub Secrets
sudo docker run -d --name nexus --restart always -p 7860:7860 \
  -e NEXUS_DATABASE_PATH=/app/artifacts/incidents.json \
  -e NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system \
  -e NEXUS_FORGE_MODEL_NAME=gpt-4o \
  -e NEXUS_USE_OPENAI=0 \
  -e NEXUS_WEBHOOK_SIGNING_SECRET=WEBHOOK_SECRET_VALUE \
  -v nexus-data:/app/artifacts \
  nexus

# 5. Verify the deployment
curl http://localhost:7860/health
```

### Running smoke tests

After deployment, run the smoke test suite to verify the deployment:

```bash
# Test against Oracle Cloud
bash scripts/test-live.sh http://nexus-triage.duckdns.org:7860

# Test against Render
bash scripts/test-live.sh https://nexus-uny5.onrender.com
```

The smoke test runs 5 checks:
1. Health check (`/health`) — verifies the app is responding
2. Queue page (`/queue`) — verifies the web UI is accessible
3. Incident detail (`/incident?nexus_incident_id=INC001`) — verifies incident pages load
4. Training page (`/training`) — verifies the training section is accessible
5. API queue endpoint (`/api/v1/incidents/queue`) — verifies the API is responding

All tests must return HTTP 200 (or 401 for API endpoints without credentials).

---

## SECTION 5 — Environment variables

All environment variables used in production are listed below. The **Storage** column indicates where each variable is stored.

| Variable | Value (Oracle Cloud) | Storage | Sensitive? |
|---|---|---|---|
| `NEXUS_DATABASE_PATH` | `/app/artifacts/incidents.json` | Hardcoded in deploy script | No |
| `NEXUS_ALLOWED_TENANT_IDS` | `tenant-a,tenant-system` | Hardcoded in deploy script | No |
| `NEXUS_FORGE_MODEL_NAME` | `gpt-4o` | Hardcoded in deploy script | No |
| `NEXUS_USE_OPENAI` | `0` | Hardcoded in deploy script | No |
| `NEXUS_WEBHOOK_SIGNING_SECRET` | (32-byte hex string) | GitHub Secrets: `ORACLE_WEBHOOK_SECRET` | **YES — SENSITIVE** |
| `OPENAI_API_KEY` | (if enabled) | Not set in Oracle Cloud deployment | **YES — SENSITIVE** |

### About sensitive variables
- **`NEXUS_WEBHOOK_SIGNING_SECRET`**: Used to validate incoming webhook signatures. This secret is stored in GitHub Secrets and injected at deploy time via GitHub Actions. **Never commit this to code.**
- **`OPENAI_API_KEY`**: Required if `NEXUS_USE_OPENAI=1`. Not configured in the Oracle Cloud production deployment (set to `0`). If you enable OpenAI integration, store the key in GitHub Secrets and inject it at deploy time.

### Local development
For local development, create a `.env.local` file (which is ignored by git) with your real secrets:
```
NEXUS_WEBHOOK_SIGNING_SECRET=your-secret-here
OPENAI_API_KEY=your-key-here
```

---

## SECTION 6 — What to do if something breaks

### Container crashed or won't start

1. **SSH into the server**:
   ```bash
   ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
   ```

2. **Check Docker logs**:
   ```bash
   sudo docker logs nexus | tail -50
   ```

3. **Check container status**:
   ```bash
   sudo docker ps -a  # See all containers (running and stopped)
   ```

4. **Restart the container**:
   ```bash
   sudo docker restart nexus
   ```

### Health check failing (200 OK but broken functionality)

1. **Check the `/health` endpoint**:
   ```bash
   curl http://nexus-triage.duckdns.org:7860/health
   ```

2. **If health check returns an error, check Docker logs**:
   ```bash
   ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
   sudo docker logs nexus | grep -i "error\|exception\|fail" | tail -20
   ```

3. **Check if database is corrupted or locked**:
   ```bash
   # SSH to the server and run:
   sudo docker exec nexus sqlite3 /app/artifacts/incidents.json ".tables"
   ```

### GitHub Actions workflow failing

1. **Go to the GitHub Actions tab**: https://github.com/kunalkachru/nexus-v2/actions

2. **Click the failed workflow run** to see the error

3. **Common failure reasons**:
   - **SSH key is invalid**: Verify `ORACLE_SSH_KEY` secret is correct in GitHub Secrets
   - **Webhook secret is invalid**: Verify `ORACLE_WEBHOOK_SECRET` secret is correct in GitHub Secrets
   - **Network connectivity**: The GitHub Actions runner cannot reach 92.5.47.239 (unlikely, but check Oracle Cloud firewall)
   - **Docker build failed**: Code has a syntax error or missing dependency; check the "Deploy to Oracle Cloud" logs for the actual error

4. **If the SSH connection times out**: The server may be down or unreachable. SSH in manually to check:
   ```bash
   ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
   ```

### Render deployment failing

1. **Go to Render dashboard**: https://render.com (you must be logged in)

2. **Click the `nexus-v2` service**

3. **View the "Logs" tab** for detailed error output

4. **Common failure reasons**:
   - **Dockerfile syntax error**: Fix the Dockerfile and push to GitHub; Render will automatically retry
   - **Build timeout**: Render has a 45-minute build limit; if exceeded, try simplifying dependencies
   - **Port already in use**: Unlikely on Render; check that the Dockerfile exposes port 7860 (`EXPOSE 7860`)

5. **Manual redeploy**: In the Render dashboard, click "Manual Deploy" → "Deploy latest commit" to trigger a rebuild

### Database issues

If you suspect the SQLite database is corrupted:

1. **SSH into the server**:
   ```bash
   ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239
   ```

2. **Back up the database**:
   ```bash
   cp /var/lib/docker/volumes/nexus-data/_data/incidents.json /tmp/incidents.json.backup
   ```

3. **Check database integrity**:
   ```bash
   sudo docker exec nexus sqlite3 /app/artifacts/incidents.json "PRAGMA integrity_check;"
   ```

4. **If corrupt, restore from backup** (you must have a prior backup):
   ```bash
   cp /tmp/incidents.json.backup /var/lib/docker/volumes/nexus-data/_data/incidents.json
   sudo docker restart nexus
   ```

---

## Summary

| Task | How to do it |
|---|---|
| Deploy to both environments | `git push origin master` (automatic via GitHub + Render) |
| Deploy to Oracle Cloud only | `bash scripts/deploy-oracle.sh` (manual) |
| Run smoke tests | `bash scripts/test-live.sh [BASE_URL]` |
| Check Render status | Render dashboard → nexus-v2 service → Logs tab |
| Check Oracle Cloud status | GitHub Actions tab → Deploy to Oracle Cloud workflow |
| SSH into Oracle Cloud | `ssh -i ~/Downloads/ssh-key-2026-06-19.key ubuntu@92.5.47.239` |
| View container logs | `ssh ... && sudo docker logs nexus` |
| Check health | `curl http://nexus-triage.duckdns.org:7860/health` |

---

*Last verified: 2026-06-19 (GitHub Actions deployment with corrected SSH key in secrets)*
