#!/bin/bash
set -e

BASE_URL="${1:-http://nexus-triage.duckdns.org:7860}"

echo "=== Running smoke tests against $BASE_URL ==="

# Test 1: Health check
echo "Test 1: Health check..."
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q "ok"; then
  echo "  ✅ Health check passed"
else
  echo "  ❌ Health check failed: $HEALTH"
  exit 1
fi

# Test 2: Queue loads
echo "Test 2: Queue page loads..."
QUEUE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/queue")
if [ "$QUEUE" = "200" ]; then
  echo "  ✅ Queue page loads (HTTP 200)"
else
  echo "  ❌ Queue page failed (HTTP $QUEUE)"
  exit 1
fi

# Test 3: Incident detail loads
echo "Test 3: Incident detail loads..."
INCIDENT=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/incident?nexus_incident_id=INC001")
if [ "$INCIDENT" = "200" ]; then
  echo "  ✅ Incident detail loads (HTTP 200)"
else
  echo "  ❌ Incident detail failed (HTTP $INCIDENT)"
  exit 1
fi

# Test 4: Training page loads
echo "Test 4: Training page loads..."
TRAINING=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/training")
if [ "$TRAINING" = "200" ]; then
  echo "  ✅ Training page loads (HTTP 200)"
else
  echo "  ❌ Training page failed (HTTP $TRAINING)"
  exit 1
fi

# Test 5: API queue endpoint
echo "Test 5: API queue endpoint..."
API=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/incidents/queue" -H "X-Tenant-ID: tenant-a" -H "X-User-ID: test-user")
if [ "$API" = "200" ] || [ "$API" = "401" ]; then
  echo "  ✅ API queue endpoint responding (HTTP $API)"
else
  echo "  ❌ API queue endpoint failed (HTTP $API)"
  exit 1
fi

echo ""
echo "=== All smoke tests passed ==="
echo "NEXUS is live at: $BASE_URL/queue"
