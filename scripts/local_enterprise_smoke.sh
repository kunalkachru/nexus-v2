#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:7860}"

echo "=== NEXUS local enterprise smoke ==="

echo "[1] Health check"
curl -fsS "${BASE_URL}/health" >/dev/null
echo "    OK"

echo "[2] INC001 incident HTML markers"
inc001_html="$(curl -fsS "${BASE_URL}/incident?nexus_incident_id=INC001")"
[[ "${inc001_html}" == *"Enterprise Task Board"* ]]
[[ "${inc001_html}" == *"Memory-grounded context"* ]]
[[ "${inc001_html}" == *"Reliability posture"* ]]
[[ "${inc001_html}" == *"Investigation depth"* ]]
echo "    OK"

echo "[3] INC002 incident HTML markers"
inc002_html="$(curl -fsS "${BASE_URL}/incident?nexus_incident_id=INC002")"
[[ "${inc002_html}" == *"Enterprise Task Board"* ]]
[[ "${inc002_html}" == *"Investigation depth"* ]]
echo "    OK"

echo "[4] Training HTML markers"
training_html="$(curl -fsS "${BASE_URL}/training")"
[[ "${training_html}" == *"Enterprise runtime summary"* ]]
echo "    OK"

echo "[5] INC001 context API — core fields, FORGE reasoning, GUARDIAN posture, TRACE"
python3 - "${BASE_URL}" << 'PY'
import json, sys, urllib.request

base_url = sys.argv[1]
headers = {"x-user-id": "user-123", "x-tenant-id": "tenant-a", "x-roles": "operator"}

def get(path):
    req = urllib.request.Request(f"{base_url}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

p = get("/api/v1/incidents/INC001/context")

# Core structure
assert "orchestration" in p, "missing orchestration"
assert "task_board" in p, "missing task_board"
assert "agent_metrics" in p, "missing agent_metrics"
assert "fallback_summary" in p, "missing fallback_summary"
assert p["task_board"]["tasks"], "empty task board"
assert p["guardian"]["required_approval_level"], "missing guardian approval level"

# REPLICA fields
rs = p.get("replica_summary", {})
assert rs.get("reproduction_status"), "missing replica_summary.reproduction_status"
assert rs.get("environment_pack_id"), "missing replica_summary.environment_pack_id"
assert rs.get("best_mitigation_action"), "missing replica_summary.best_mitigation_action"
assert rs.get("best_mitigation_outcome_class"), f"INC001 best_mitigation_outcome_class is empty — item 9 not done"
assert rs.get("runtime_comparison_summary"), f"INC001 runtime_comparison_summary is empty — item 9 not done"

# TRACE fields
ts = p.get("trace_summary", {})
assert ts.get("trace_status") == "narrowed", f"INC001 trace_status should be 'narrowed', got: {ts.get('trace_status')}"
ip = ts.get("inspection_point", "")
assert len(ip) > 80 and "Wait for REPLICA" not in ip, f"INC001 TRACE inspection_point is placeholder or short: {ip}"
assert ts.get("suspected_modules"), "INC001 TRACE must have suspected_modules"

# FORGE/runbook reasoning
runbook = p.get("runbook", {})
forge_reasoning = (runbook.get("reasoning") or "").lower()
assert any(w in forge_reasoning for w in ["resolved","improved","validated","runtime","mitigation"]), \
    f"INC001 FORGE reasoning does not cite runtime outcome: {runbook.get('reasoning')}"

# GUARDIAN reasoning
gd = p.get("guardian", {})
guardian_reasoning = (gd.get("reasoning") or "").lower()
assert any(w in guardian_reasoning for w in ["reproduced","validated","inferred","runtime","resolved","improved"]), \
    f"INC001 GUARDIAN reasoning is generic: {gd.get('reasoning')}"
assert gd.get("confidence", 0) > 0, "INC001 guardian confidence is zero"

print("    INC001 checks passed.")
PY

echo "[6] INC002 context API — FORGE reasoning, GUARDIAN posture, TRACE"
python3 - "${BASE_URL}" << 'PY'
import json, sys, urllib.request

base_url = sys.argv[1]
headers = {"x-user-id": "user-123", "x-tenant-id": "tenant-a", "x-roles": "operator"}

def get(path):
    req = urllib.request.Request(f"{base_url}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

p = get("/api/v1/incidents/INC002/context")

rs = p.get("replica_summary", {})
assert rs.get("reproduction_status") == "reproduced", f"INC002 reproduction_status should be 'reproduced'"
assert rs.get("best_mitigation_outcome_class"), "INC002 best_mitigation_outcome_class is empty — item 9 not done"
assert rs.get("runtime_comparison_summary"), "INC002 runtime_comparison_summary is empty — item 9 not done"

ts = p.get("trace_summary", {})
assert ts.get("suspected_modules"), "INC002 TRACE must have suspected_modules"
assert ts.get("inspection_point") and "Wait for REPLICA" not in ts["inspection_point"], \
    f"INC002 TRACE inspection_point is placeholder"

runbook = p.get("runbook", {})
forge_reasoning = (runbook.get("reasoning") or "").lower()
assert any(w in forge_reasoning for w in ["resolved","improved","validated","runtime","mitigation"]), \
    f"INC002 FORGE reasoning does not cite runtime outcome: {runbook.get('reasoning')}"

gd = p.get("guardian", {})
guardian_reasoning = (gd.get("reasoning") or "").lower()
assert any(w in guardian_reasoning for w in ["reproduced","validated","inferred","runtime","resolved","improved"]), \
    f"INC002 GUARDIAN reasoning is generic: {gd.get('reasoning')}"

print("    INC002 checks passed.")
PY

echo "[7] INC001 memory enrichment check"
python3 - "${BASE_URL}" << 'PY'
import json, sys, urllib.request

base_url = sys.argv[1]
headers = {"x-user-id": "user-123", "x-tenant-id": "tenant-a", "x-roles": "operator"}
req = urllib.request.Request(f"{base_url}/api/v1/incidents/INC001/context", headers=headers)
with urllib.request.urlopen(req, timeout=20) as r:
    p = json.loads(r.read().decode())

memory_hits = p.get("memory_hits", {})
runbooks = memory_hits.get("runbooks", [])
assert runbooks, "INC001 memory_hits.runbooks is empty — item 13 not done"
assert any(rb.get("why_now_fit") for rb in runbooks), \
    f"No runbook has why_now_fit note — item 13 not done. Runbooks: {[rb.get('why_now_fit') for rb in runbooks]}"
print("    Memory enrichment check passed.")
PY

if [[ "${EXPECT_RUNTIME_HOST_RELAY:-0}" == "1" ]]; then
  echo "[8] Relay-backed replay path"
  python3 - "${BASE_URL}" << 'PY'
import json, sys, urllib.request

base_url = sys.argv[1]
headers = {"x-user-id": "user-123", "x-tenant-id": "tenant-a", "x-roles": "operator"}

def request(path, *, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(f"{base_url}{path}", data=body, method=method, headers={
        **headers,
        **({"content-type": "application/json"} if payload is not None else {}),
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

context = request("/api/v1/incidents/INC001/context")
capability = context["replica_summary"]["runtime_capability"]
assert capability["state"] in {"relay_available", "relay_executed"}, capability

replay = request("/api/v1/incidents/INC001/replica-replay", method="POST", payload={})
assert replay["status"] == "relay_executed", replay
assert replay["runtime_capability"]["state"] == "relay_executed", replay["runtime_capability"]
assert replay["replica_summary"]["runtime_mode"] == "relay_runtime_scaffold", replay["replica_summary"]
print("    Relay replay check passed.")
PY

  echo "[9] Fresh nxs incident retains replay evidence and relay provenance after refresh"
  python3 - "${BASE_URL}" << 'PY'
import json, sys, urllib.request

base_url = sys.argv[1]
headers = {"x-user-id": "user-123", "x-tenant-id": "tenant-a", "x-roles": "operator"}

def request(path, *, method="GET", payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(f"{base_url}{path}", data=body, method=method, headers={
        **headers,
        **({"content-type": "application/json"} if payload is not None else {}),
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

created = request(
    "/api/v1/incidents/raw-text",
    method="POST",
    payload={
        "raw_text": "2026-05-30T10:14:22Z auth-svc ERROR timeout waiting for downstream auth\n2026-05-30T10:14:23Z api-gateway WARN retry budget exhausted\nservice=auth-svc severity=P2",
        "source_hint": "smoke",
        "reported_by": "smoke",
        "team": "identity",
        "severity_hint": "P2",
    },
)
incident_id = created["nexus_incident_id"]

replay = request(f"/api/v1/incidents/{incident_id}/replica-replay", method="POST", payload={})
assert replay["status"] == "relay_executed", replay
assert replay["replica_summary"]["runtime_provenance"]["mode"] == "delegated_relay", replay["replica_summary"]
assert replay["trace_summary"]["runtime_provenance"]["mode"] == "delegated_relay", replay["trace_summary"]

context = request(f"/api/v1/incidents/{incident_id}/context")
assert context["replica_summary"]["runtime_executed"] is True, context["replica_summary"]
assert context["replica_summary"]["runtime_provenance"]["mode"] == "delegated_relay", context["replica_summary"]
assert context["trace_summary"]["runtime_provenance"]["mode"] == "delegated_relay", context["trace_summary"]
assert context["incident"]["normalized_evidence"]["latest_replay"]["status"] == "relay_executed", context["incident"]["normalized_evidence"]
assert "runtime host" in context["trace_summary"]["developer_handoff_summary"].lower(), context["trace_summary"]
print("    Fresh incident replay persistence check passed.")
PY
fi

echo ""
echo "=== All smoke checks passed ==="
