#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                              ║"
echo "║                   NEXUS RELEASE GATE TEST SUITE                              ║"
echo "║                                                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Run release gate pytest
python -m pytest tests/release_gate.py -v --tb=short 2>&1 | tee /tmp/release-gate-output.log

# Capture exit code
RESULT=$?

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"

if [ $RESULT -eq 0 ]; then
    echo "║                                                                              ║"
    echo "║                  ✅ NEXUS RELEASE GATE: PASSED                              ║"
    echo "║                                                                              ║"
    echo "║                     Ready for deployment/pilot                              ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    exit 0
else
    echo "║                                                                              ║"
    echo "║                  ❌ NEXUS RELEASE GATE: FAILED                              ║"
    echo "║                                                                              ║"
    echo "║              NOT ready — fix failures above before deploying                ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    exit 1
fi
