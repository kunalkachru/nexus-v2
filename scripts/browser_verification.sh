#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
LOG_FILE="${LOG_FILE:-/private/tmp/nexus-browser-verification.log}"
UV_CACHE_DIR="${UV_CACHE_DIR:-/private/tmp/uv-cache}"
PYTHON_BIN="${PYTHON_BIN:-}"
SERVER_PID=""

cleanup() {
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

if [[ -z "${PYTHON_BIN}" ]]; then
  for candidate in /opt/anaconda3/bin/python python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "${candidate}")"
      break
    fi
  done
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  echo "No Python interpreter found. Set PYTHON_BIN and try again." >&2
  exit 1
fi

export UV_CACHE_DIR

echo "Running backend verification..."
"${PYTHON_BIN}" -m pytest tests/ -q

echo "Starting local server..."
(cd "${ROOT_DIR}" && "${PYTHON_BIN}" -m uvicorn server.app:app --host "${HOST}" --port "${PORT}" >"${LOG_FILE}" 2>&1) &
SERVER_PID=$!

echo "Waiting for http://${HOST}:${PORT}/health ..."
"${PYTHON_BIN}" - "${HOST}" "${PORT}" <<'PY'
import sys
import time
import urllib.error
import urllib.request

host = sys.argv[1]
port = sys.argv[2]
url = f"http://{host}:{port}/health"
deadline = time.time() + 30

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                print("Server is ready.")
                raise SystemExit(0)
    except Exception:
        time.sleep(0.5)

print(f"Timed out waiting for {url}", file=sys.stderr)
raise SystemExit(1)
PY

PAGES=(
  "/queue"
  "/incident"
  "/inputs"
  "/history"
  "/replay"
  "/training"
  "/settings"
)

if [[ "${NO_BROWSER_OPEN:-0}" != "1" ]]; then
  echo "Opening browser tabs..."
  if command -v open >/dev/null 2>&1; then
    for page in "${PAGES[@]}"; do
      open "http://${HOST}:${PORT}${page}"
    done
  elif command -v xdg-open >/dev/null 2>&1; then
    for page in "${PAGES[@]}"; do
      xdg-open "http://${HOST}:${PORT}${page}" >/dev/null 2>&1 || true
    done
  else
    echo "No browser-open command found. Open these URLs manually:"
    for page in "${PAGES[@]}"; do
      echo "http://${HOST}:${PORT}${page}"
    done
  fi
else
  echo "Browser auto-open disabled. Open these URLs manually:"
  for page in "${PAGES[@]}"; do
    echo "http://${HOST}:${PORT}${page}"
  done
fi

echo
echo "Verification server running at http://${HOST}:${PORT}"
echo "Log file: ${LOG_FILE}"
echo "Press Ctrl+C when you are done reviewing the pages."

wait "${SERVER_PID}"
