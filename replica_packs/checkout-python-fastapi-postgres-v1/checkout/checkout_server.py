from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


RUNTIME = Path("/runtime")


def _read_text(name: str, default: str) -> str:
    path = RUNTIME / name
    if not path.exists():
        return default
    return path.read_text().strip()


class CheckoutHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path.startswith("/checkout-write"):
            leak_enabled = _read_text("session_leak_enabled.txt", "1") != "0"
            pool_exhausted = _read_text("pool_exhausted.txt", "1") != "0"
            if leak_enabled and pool_exhausted:
                time.sleep(1.1)
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps(
                        {
                            "result": "pool_exhausted",
                            "reason": "session_leak_active",
                            "pool_limit": 500,
                        }
                    ).encode("utf-8")
                )
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"result": "write_succeeded"}).encode("utf-8"))
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


if __name__ == "__main__":
    os.makedirs(RUNTIME, exist_ok=True)
    server = HTTPServer(("0.0.0.0", 8000), CheckoutHandler)
    server.serve_forever()
