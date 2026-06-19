#!/bin/bash
set -e

echo "=== Deploying NEXUS to Oracle Cloud ==="

# SSH into Oracle Cloud server and update the deployment
ssh -i ~/Downloads/ssh-key-2026-06-19.key -o StrictHostKeyChecking=no ubuntu@92.5.47.239 << 'ENDSSH'
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
    -e NEXUS_WEBHOOK_SIGNING_SECRET=f2f2e2cde69e33707da3e368a88f0856705aaf7d54d1dca3d283bb1f7e8cd021 \
    -v nexus-data:/app/artifacts nexus
  echo "=== Deployment complete ==="
  curl -s http://localhost:7860/health
ENDSSH

echo "=== Oracle Cloud deployment successful ==="
echo "URL: http://nexus-triage.duckdns.org:7860/queue"
