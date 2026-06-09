#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "$0")/../runtime" && pwd)"

cat > "${RUNTIME_DIR}/retries.txt" <<'EOF'
1
EOF
echo "Mitigation applied: cap retries to 1"
