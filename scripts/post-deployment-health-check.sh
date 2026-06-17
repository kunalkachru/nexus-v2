#!/bin/bash

# NEXUS Post-Deployment Health Check Script
#
# Purpose: Validate that deployed service is healthy and operational
#
# Usage: ./scripts/post-deployment-health-check.sh
#
# Exit Codes:
#   0 = All health checks passed
#   1 = Critical health check failed
#   2 = Warning (non-critical issues)

set -e

# Configuration
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Header
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  NEXUS Post-Deployment Health Check       ║"
echo "║  $(date +'%Y-%m-%d %H:%M:%S')"                  "║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Wait for service to be ready
echo "Waiting for service startup..."
for i in {1..30}; do
    if curl -s http://localhost:7860/health > /dev/null 2>&1; then
        echo "Service is responding"
        break
    fi
    if [ $i -eq 30 ]; then
        fail "Service did not start within 30 seconds"
        exit 1
    fi
    sleep 1
done

echo ""

# 1. Health Endpoint
echo "1. Health endpoint..."

HEALTH_RESPONSE=$(curl -s http://localhost:7860/health)

if [ -z "$HEALTH_RESPONSE" ]; then
    fail "No response from health endpoint"
else
    HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status' 2>/dev/null)

    if [ "$HEALTH_STATUS" == "ok" ]; then
        pass "Health status: ok"
        echo "  Response: $HEALTH_RESPONSE" | jq .
    else
        fail "Health status: $HEALTH_STATUS"
        echo "  Response: $HEALTH_RESPONSE"
    fi
fi

echo ""

# 2. Database Connectivity
echo "2. Database connectivity..."

if [ -f "artifacts/incidents.json" ]; then
    pass "Database file exists"

    if python3 -m json.tool artifacts/incidents.json > /dev/null 2>&1; then
        pass "Database JSON valid"

        INCIDENT_COUNT=$(python3 -c "import json; f=open('artifacts/incidents.json'); d=json.load(f); print(len(d.get('incidents', [])))")
        pass "Incidents in database: $INCIDENT_COUNT"
    else
        fail "Database JSON invalid"
    fi
else
    fail "Database file not found"
fi

echo ""

# 3. Metrics Endpoint
echo "3. Metrics endpoint..."

if curl -s http://localhost:7860/metrics | grep -q "nexus_"; then
    pass "Prometheus metrics available"

    METRIC_COUNT=$(curl -s http://localhost:7860/metrics | grep "^nexus_" | wc -l)
    pass "Metrics exported: $METRIC_COUNT"
else
    warn "Metrics endpoint not responding or metrics not available"
fi

echo ""

# 4. Docker Container (if running in Docker)
echo "4. Docker container status..."

if command -v docker &> /dev/null; then
    if docker ps | grep -q nexus; then
        CONTAINER=$(docker ps | grep nexus | awk '{print $1}')
        pass "Container running: $CONTAINER"

        # Check memory usage
        MEMORY=$(docker stats --no-stream "$CONTAINER" 2>/dev/null | tail -1 | awk '{print $4}')
        pass "Memory usage: $MEMORY"

        # Check restart count
        RESTARTS=$(docker inspect "$CONTAINER" --format='{{.RestartCount}}' 2>/dev/null || echo "unknown")
        if [ "$RESTARTS" == "0" ] || [ "$RESTARTS" == "unknown" ]; then
            pass "Restart count: $RESTARTS (clean start)"
        else
            warn "Container has restarted $RESTARTS times"
        fi
    else
        warn "Container not running (if running locally with docker-compose, this is expected)"
    fi
else
    info "Docker not available (local Python server expected)"
fi

echo ""

# 5. Logs Check
echo "5. Recent logs..."

# Check Docker logs if available
if command -v docker &> /dev/null && docker ps | grep -q nexus; then
    CONTAINER=$(docker ps | grep nexus | awk '{print $1}')
    ERROR_COUNT=$(docker logs "$CONTAINER" 2>&1 | grep -ci ERROR || echo "0")

    if [ "$ERROR_COUNT" -eq 0 ]; then
        pass "No errors in logs"
    else
        warn "Found $ERROR_COUNT errors in container logs"
        info "Recent errors:"
        docker logs "$CONTAINER" 2>&1 | grep ERROR | tail -3
    fi
else
    info "Docker logs not available (check systemctl or application logs if deployed with systemd)"
fi

echo ""

# 6. Performance Baseline
echo "6. Response time..."

START=$(date +%s%N)
curl -s http://localhost:7860/health > /dev/null
END=$(date +%s%N)
RESPONSE_TIME=$((($END - $START) / 1000000))

if [ "$RESPONSE_TIME" -lt 100 ]; then
    pass "Response time: ${RESPONSE_TIME}ms"
else
    warn "Response time: ${RESPONSE_TIME}ms (expect < 100ms)"
fi

echo ""

# 7. Backup Status
echo "7. Backup system..."

if [ -f "scripts/backup_nexus.sh" ] && [ -x "scripts/backup_nexus.sh" ]; then
    pass "Backup script present and executable"

    # Check for recent backups
    BACKUP_DIR=".backup/nexus"
    if [ -d "$BACKUP_DIR" ]; then
        BACKUP_COUNT=$(find "$BACKUP_DIR" -type f -name "*.gz" -mtime -1 2>/dev/null | wc -l)
        if [ "$BACKUP_COUNT" -gt 0 ]; then
            pass "Recent backups found: $BACKUP_COUNT"
        else
            warn "No recent backups found (check backup cron job)"
        fi
    else
        warn "Backup directory not yet created"
    fi
else
    warn "Backup script not available"
fi

echo ""

# 8. System Resources
echo "8. System resources..."

# CPU (approximate)
if [ "$(uname)" == "Darwin" ]; then
    CPU_USAGE=$(ps aux | grep nexus | grep -v grep | awk '{print $3}' | head -1)
else
    CPU_USAGE=$(ps aux | grep nexus | grep -v grep | awk '{print $3}' | head -1)
fi

if [ -n "$CPU_USAGE" ]; then
    pass "CPU usage: $CPU_USAGE%"
else
    info "CPU usage not available"
fi

# Memory
if [ "$(uname)" == "Darwin" ]; then
    MEM_USAGE=$(ps aux | grep nexus | grep -v grep | awk '{print $4}' | head -1)
else
    MEM_USAGE=$(ps aux | grep nexus | grep -v grep | awk '{print $4}' | head -1)
fi

if [ -n "$MEM_USAGE" ]; then
    pass "Memory usage: $MEM_USAGE%"
else
    info "Memory usage not available"
fi

echo ""

# 9. Port Availability
echo "9. Port configuration..."

if netstat -tuln 2>/dev/null | grep -q ":7860" || lsof -i :7860 2>/dev/null | grep -q LISTEN; then
    pass "Port 7860 listening"
else
    fail "Port 7860 not listening"
fi

echo ""

# 10. Integration Check
echo "10. Integration check..."

# Try a basic API call if auth available
if curl -s -H "Authorization: Bearer test" http://localhost:7860/api/incidents > /dev/null 2>&1; then
    pass "API endpoint responding"
else
    warn "API endpoint not responding (might require authentication)"
fi

echo ""

# Summary
echo "╔════════════════════════════════════════════╗"
echo "║  Health Check Summary                     ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${RED}Failed:${NC}   $FAILED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

# Decision
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ DEPLOYMENT HEALTHY${NC}"
    echo ""
    echo "Service is operational and ready for monitoring."
    echo "Proceed to: Task 8.2 (24-hour monitoring)"
    echo ""
    exit 0
else
    echo -e "${RED}✗ DEPLOYMENT HAS ISSUES${NC}"
    echo ""
    echo "Please investigate and resolve the failures above."
    echo "Check logs and troubleshooting guide: docs/TROUBLESHOOTING_GUIDE.md"
    echo ""
    exit 1
fi
