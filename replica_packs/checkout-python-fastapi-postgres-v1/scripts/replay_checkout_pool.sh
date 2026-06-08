#!/usr/bin/env bash
set -euo pipefail

echo "Replay scaffold: checkout DB pool exhaustion / session leak"
echo "Target: replay write-heavy checkout traffic against a bounded pool"
