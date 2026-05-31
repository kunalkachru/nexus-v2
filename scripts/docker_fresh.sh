#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-7860}"

cd "${ROOT_DIR}"

echo "Stopping any existing Compose services..."
docker compose down --remove-orphans >/dev/null 2>&1 || true

echo "Starting a fresh build on ${HOST}:${PORT}..."
docker compose up --build --force-recreate --detach

echo "Waiting for http://${HOST}:${PORT}/health ..."
for _ in {1..60}; do
  if curl -fsS "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
    echo "Fresh container is ready."
    docker compose ps
    exit 0
  fi
  sleep 1
done

echo "Timed out waiting for the fresh container to become ready." >&2
exit 1
