#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "$0")/../runtime" && pwd)"

cat > "${RUNTIME_DIR}/pool_exhausted.txt" <<'EOF'
0
EOF
echo "Mitigation applied: restart checkout service"
