#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "$0")/../runtime" && pwd)"

cat > "${RUNTIME_DIR}/session_leak_enabled.txt" <<'EOF'
0
EOF
cat > "${RUNTIME_DIR}/pool_exhausted.txt" <<'EOF'
0
EOF
echo "Mitigation applied: roll back retry patch"
