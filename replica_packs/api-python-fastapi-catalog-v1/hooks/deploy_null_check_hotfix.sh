#!/bin/bash
# Mitigation: Deploy null-check hotfix to catalog query filter
# Applies a targeted fix without rolling back the entire optimization

set -e

API_URL="http://api:8000"

echo "[MITIGATION] Deploying null-check hotfix to catalog query filter..."

# Simulate hotfix deployment by enabling a safety check
MITIGATION_RESPONSE=$(curl -s -X POST "${API_URL}/api/mitigation/apply-null-check-hotfix" 2>/dev/null || echo "")

echo "[MITIGATION] Executing post-hotfix catalog search..."
RECOVERY_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/products/search?q=test" 2>/dev/null || echo "500")
RECOVERY_STATUS=$(echo "$RECOVERY_RESPONSE" | tail -n 1)

echo "[MITIGATION] Post-mitigation response status: $RECOVERY_STATUS"

if [ "$RECOVERY_STATUS" = "200" ]; then
  echo "[MITIGATION] SUCCESS: API returned 200, hotfix resolved the issue"
  echo "200"
else
  echo "[MITIGATION] PARTIAL: API returned $RECOVERY_STATUS"
  echo "$RECOVERY_STATUS"
fi

exit 0
