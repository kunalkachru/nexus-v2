#!/usr/bin/env bash
set -euo pipefail

python <<'PY'
import json
import time
import urllib.error
import urllib.request

start = time.time()
try:
    response = urllib.request.urlopen("http://127.0.0.1:18080/checkout", timeout=8)
    body = response.read().decode("utf-8")
    status_code = response.getcode()
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8")
    status_code = exc.code
except urllib.error.URLError as exc:
    body = json.dumps({"result": "unreachable", "reason": str(exc.reason)})
    status_code = 599
duration_ms = int((time.time() - start) * 1000)

print("Replay: checkout timeout / retry amplification")
print(json.dumps({"status_code": status_code, "duration_ms": duration_ms, "body": body}))
PY
