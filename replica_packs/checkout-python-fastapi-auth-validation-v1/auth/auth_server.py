from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


RUNTIME = Path("/runtime")


def _read_int(name: str, default: int) -> int:
    path = RUNTIME / name
    if not path.exists():
        return default
    try:
        return int(path.read_text().strip())
    except ValueError:
        return default


class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path.startswith("/authorize"):
            delay_ms = _read_int("auth_delay_ms.txt", 1200)
            time.sleep(delay_ms / 1000)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"authorized": True, "delay_ms": delay_ms}).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


if __name__ == "__main__":
    os.makedirs(RUNTIME, exist_ok=True)
    server = HTTPServer(("0.0.0.0", 8001), AuthHandler)
    server.serve_forever()
