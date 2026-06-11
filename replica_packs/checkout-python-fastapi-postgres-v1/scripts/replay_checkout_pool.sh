#!/usr/bin/env bash
set -euo pipefail

python <<'PY'
import json
import os
import time
import urllib.error
import urllib.request

runtime_host = os.environ.get("NEXUS_RUNTIME_HTTP_HOST", "127.0.0.1")
start = time.time()
try:
    response = urllib.request.urlopen(f"http://{runtime_host}:19080/checkout-write", timeout=8)
    body = response.read().decode("utf-8")
    status_code = response.getcode()
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8")
    status_code = exc.code
except urllib.error.URLError as exc:
    body = json.dumps({"result": "unreachable", "reason": str(exc.reason)})
    status_code = 599
duration_ms = int((time.time() - start) * 1000)

print("Replay: checkout DB pool exhaustion / session leak")
print(json.dumps({"status_code": status_code, "duration_ms": duration_ms, "body": body}))
PY
