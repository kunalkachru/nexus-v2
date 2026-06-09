#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "$0")/../runtime" && pwd)"

cat > "${RUNTIME_DIR}/retry_middleware_enabled.txt" <<'EOF'
0
EOF
echo "Mitigation applied: disable retry middleware path"
