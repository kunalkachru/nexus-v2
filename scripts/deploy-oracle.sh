#!/bin/bash
set -e

# For manual deployments, the webhook signing secret should be provided via environment variable
# Usage: NEXUS_WEBHOOK_SIGNING_SECRET=your-secret-here bash scripts/deploy-oracle.sh
# Or retrieve it from GitHub Secrets and pass it in

WEBHOOK_SECRET="${NEXUS_WEBHOOK_SIGNING_SECRET:-}"

if [ -z "$WEBHOOK_SECRET" ]; then
  echo "❌ Error: NEXUS_WEBHOOK_SIGNING_SECRET environment variable not set"
  echo ""
  echo "Usage: NEXUS_WEBHOOK_SIGNING_SECRET=your-secret-here bash scripts/deploy-oracle.sh"
  echo ""
  echo "To retrieve the secret from GitHub Secrets:"
  echo "  1. Go to GitHub repo settings → Secrets and variables → Actions"
  echo "  2. Find ORACLE_WEBHOOK_SECRET and copy its value"
  echo "  3. Run: NEXUS_WEBHOOK_SIGNING_SECRET=<value> bash scripts/deploy-oracle.sh"
  exit 1
fi

echo "=== Deploying NEXUS to Oracle Cloud ==="

# SSH into Oracle Cloud server and update the deployment
ssh -i ~/Downloads/ssh-key-2026-06-19.key -o StrictHostKeyChecking=no ubuntu@92.5.47.239 << ENDSSH
  cd nexus-v2
  git pull origin master
  sudo docker build -t nexus .
  sudo docker stop nexus || true
  sudo docker rm nexus || true
  sudo docker run -d --name nexus --restart always -p 7860:7860 \
    -e NEXUS_DATABASE_PATH=/app/artifacts/incidents.json \
    -e NEXUS_ALLOWED_TENANT_IDS=tenant-a,tenant-system \
    -e NEXUS_FORGE_MODEL_NAME=gpt-4o \
    -e NEXUS_USE_OPENAI=0 \
    -e NEXUS_WEBHOOK_SIGNING_SECRET=$WEBHOOK_SECRET \
    -v nexus-data:/app/artifacts nexus
  echo "=== Deployment complete ==="
  curl -s http://localhost:7860/health
ENDSSH

echo "=== Oracle Cloud deployment successful ==="
echo "URL: https://nexus-triage.duckdns.org/queue"
