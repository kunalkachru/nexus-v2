#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "$0")/../runtime" && pwd)"

cat > "${RUNTIME_DIR}/circuit_breaker.txt" <<'EOF'
open
EOF
echo "Mitigation applied: open auth circuit breaker"
