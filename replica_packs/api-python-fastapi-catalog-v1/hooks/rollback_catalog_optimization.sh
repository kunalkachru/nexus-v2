#!/bin/bash
# Mitigation: Rollback the catalog query optimization
# Disables the query optimization feature flag and verifies recovery

set -e

API_URL="http://api:8000"

echo "[MITIGATION] Rolling back catalog query optimization..."

# Disable the optimization feature flag by setting environment variable
# In a real scenario, this would restart the service with the flag disabled
MITIGATION_RESPONSE=$(curl -s -X POST "${API_URL}/api/mitigation/disable-query-optimization" 2>/dev/null || echo "")

echo "[MITIGATION] Executing post-rollback catalog search..."
RECOVERY_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/products/search?q=test" 2>/dev/null || echo "500")
RECOVERY_STATUS=$(echo "$RECOVERY_RESPONSE" | tail -n 1)

echo "[MITIGATION] Post-mitigation response status: $RECOVERY_STATUS"

if [ "$RECOVERY_STATUS" = "200" ]; then
  echo "[MITIGATION] SUCCESS: API returned 200, mitigation resolved the issue"
  echo "200"
else
  echo "[MITIGATION] PARTIAL: API returned $RECOVERY_STATUS"
  echo "$RECOVERY_STATUS"
fi

exit 0
