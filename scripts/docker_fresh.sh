#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-7860}"
SERVICE="${SERVICE:-nexus}"
NO_CACHE="${NO_CACHE:-1}"
PULL_BASE="${PULL_BASE:-0}"

cd "${ROOT_DIR}"

echo "Stopping any existing Compose services..."
docker compose down --remove-orphans --volumes >/dev/null 2>&1 || true

BUILD_ARGS=(build)
UP_ARGS=(up --force-recreate --detach --remove-orphans)

if [[ "${PULL_BASE}" == "1" ]]; then
  BUILD_ARGS+=(--pull)
fi

if [[ "${NO_CACHE}" == "1" ]]; then
  BUILD_ARGS+=(--no-cache)
fi

echo "Pruning dangling Docker build cache..."
docker builder prune --force >/dev/null 2>&1 || true

echo "Starting a fresh build on ${HOST}:${PORT}..."
docker compose "${BUILD_ARGS[@]}" "${SERVICE}"
docker compose "${UP_ARGS[@]}" "${SERVICE}"

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
