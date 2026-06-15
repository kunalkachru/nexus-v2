from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


RUNTIME = Path("/runtime")
AUTH_URL = os.environ.get("AUTH_URL", "http://auth:8001/authorize")


def _read_text(name: str, default: str) -> str:
    path = RUNTIME / name
    if not path.exists():
        return default
    return path.read_text().strip()


def _read_int(name: str, default: int) -> int:
    value = _read_text(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


class GatewayHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path.startswith("/checkout"):
            if _read_text("circuit_breaker.txt", "closed") == "open":
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"result": "degraded", "reason": "circuit_breaker_open"}).encode("utf-8"))
                return

            timeout_ms = _read_int("auth_timeout_ms.txt", 400)
            retries = _read_int("retries.txt", 4)
            retry_enabled = _read_text("retry_middleware_enabled.txt", "1") != "0"
            attempts = retries if retry_enabled else 1
            last_error = "timeout"
            for _ in range(attempts):
                try:
                    with urllib.request.urlopen(AUTH_URL, timeout=timeout_ms / 1000) as response:
                        payload = json.loads(response.read().decode("utf-8"))
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"result": "success", "auth": payload}).encode("utf-8"))
                    return
                except Exception:
                    last_error = "auth_timeout"
            self.send_response(504)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "result": "timeout",
                        "reason": last_error,
                        "attempts": attempts,
                        "timeout_ms": timeout_ms,
                    }
                ).encode("utf-8")
            )
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


if __name__ == "__main__":
    os.makedirs(RUNTIME, exist_ok=True)
    server = HTTPServer(("0.0.0.0", 8000), GatewayHandler)
    server.serve_forever()
