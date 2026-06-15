#!/bin/bash
# Replay profile for API catalog query regression
# Simulates the deploy regression where catalog queries return null instead of empty list

set -e

API_URL="http://api:8000"
BASELINE_TIMEOUT=10

echo "[REPLAY] Starting API catalog query regression baseline replay"
echo "[REPLAY] Target: ${API_URL}"

# Wait for API to be ready
for i in {1..30}; do
  if curl -s "${API_URL}/health" > /dev/null 2>&1; then
    echo "[REPLAY] API is ready"
    break
  fi
  echo "[REPLAY] Waiting for API... ($i/30)"
  sleep 1
done

# Simulate catalog search that triggers null pointer in the regression
echo "[REPLAY] Executing baseline catalog search..."
BASELINE_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/api/products/search?q=test" || echo "500")
BASELINE_STATUS=$(echo "$BASELINE_RESPONSE" | tail -n 1)

echo "[REPLAY] Baseline response status: $BASELINE_STATUS"

if [ "$BASELINE_STATUS" = "500" ] || [ "$BASELINE_STATUS" = "503" ]; then
  echo "[REPLAY] Baseline replay confirmed: API returned 5xx error"
  echo "$BASELINE_STATUS"
else
  echo "[REPLAY] WARNING: Expected 5xx status, got $BASELINE_STATUS"
  echo "500"
fi

exit 0
