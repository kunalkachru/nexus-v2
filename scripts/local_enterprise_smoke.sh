#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:7860}"

echo "Checking health at ${BASE_URL}/health"
curl -fsS "${BASE_URL}/health" >/dev/null

echo "Checking incident detail HTML markers"
incident_html="$(curl -fsS "${BASE_URL}/incident?nexus_incident_id=INC001")"
[[ "${incident_html}" == *"Enterprise Task Board"* ]]
[[ "${incident_html}" == *"Memory-grounded context"* ]]
[[ "${incident_html}" == *"Reliability posture"* ]]

echo "Checking training HTML markers"
training_html="$(curl -fsS "${BASE_URL}/training")"
[[ "${training_html}" == *"Enterprise runtime summary"* ]]

echo "Checking incident context enterprise fields"
python - <<'PY' "${BASE_URL}"
import json
import sys
import urllib.request

base_url = sys.argv[1]
request = urllib.request.Request(
    f"{base_url}/api/v1/incidents/INC001/context",
    headers={
        "x-user-id": "user-123",
        "x-tenant-id": "tenant-a",
        "x-roles": "operator",
    },
)
with urllib.request.urlopen(request, timeout=20) as response:
    payload = json.loads(response.read().decode("utf-8"))

assert "orchestration" in payload, "missing orchestration"
assert "task_board" in payload, "missing task_board"
assert "memory_hits" in payload, "missing memory_hits"
assert "agent_metrics" in payload, "missing agent_metrics"
assert "fallback_summary" in payload, "missing fallback_summary"
assert payload["task_board"]["tasks"], "empty task board"
assert payload["guardian"]["required_approval_level"], "missing guardian approval level"
print("Context checks passed.")
PY

echo "Local enterprise smoke passed."
