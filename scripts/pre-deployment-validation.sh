#!/bin/bash

# NEXUS Pre-Deployment Validation Script
#
# Purpose: Validate that all prerequisites and requirements are met
#          before attempting production deployment
#
# Usage: ./scripts/pre-deployment-validation.sh
#
# Exit Codes:
#   0 = All checks passed, ready for deployment
#   1 = Validation failed, do not deploy
#   2 = Warning (non-critical issues)

set -e

# Configuration
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
echo "║  NEXUS Pre-Deployment Validation          ║"
echo "║  $(date +'%Y-%m-%d %H:%M:%S')"                  "║"
echo "╚════════════════════════════════════════════╝"
echo ""

# 1. Directory Structure
echo "1. Checking directory structure..."

REQUIRED_DIRS=(
    "server"
    "frontend"
    "scripts"
    "docs"
    "tests"
    "artifacts"
    "prometheus"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        pass "Directory: $dir"
    else
        fail "Directory missing: $dir"
    fi
done

echo ""

# 2. Required Files
echo "2. Checking required files..."

REQUIRED_FILES=(
    "Dockerfile"
    "docker-compose.yml"
    "requirements.txt"
    "server/app.py"
    "server/db.py"
    "artifacts/incidents.json"
    "scripts/backup_nexus.sh"
    "scripts/restore_nexus.sh"
    "prometheus/alerts.yml"
    "docs/TROUBLESHOOTING_GUIDE.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        pass "File: $file"
    else
        fail "File missing: $file"
    fi
done

echo ""

# 3. Executable Scripts
echo "3. Checking executable scripts..."

SCRIPTS=(
    "scripts/backup_nexus.sh"
    "scripts/restore_nexus.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -x "$script" ]; then
        pass "Executable: $script"
    else
        warn "Script not executable: $script (will chmod +x during deployment)"
    fi
done

echo ""

# 4. Python Environment
echo "4. Checking Python environment..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    pass "Python 3 available: $PYTHON_VERSION"
else
    fail "Python 3 not found"
fi

if command -v pip3 &> /dev/null; then
    pass "pip3 available"
else
    fail "pip3 not found"
fi

echo ""

# 5. Dependencies
echo "5. Checking Python dependencies..."

DEPS=(
    "fastapi"
    "uvicorn"
    "pydantic"
    "pytest"
)

for dep in "${DEPS[@]}"; do
    if pip3 show "$dep" &> /dev/null; then
        pass "Dependency: $dep"
    else
        fail "Dependency missing: $dep (run: pip install -r requirements.txt)"
    fi
done

echo ""

# 6. Docker
echo "6. Checking Docker..."

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    pass "Docker available: $DOCKER_VERSION"
else
    fail "Docker not installed"
fi

if docker ps &> /dev/null; then
    pass "Docker daemon running"
else
    fail "Docker daemon not accessible (requires sudo or docker group)"
fi

echo ""

# 7. Database
echo "7. Checking database..."

DB_FILE="artifacts/incidents.json"

if [ -f "$DB_FILE" ]; then
    DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
    pass "Database file exists: $DB_SIZE"

    if python3 -m json.tool "$DB_FILE" > /dev/null 2>&1; then
        INCIDENT_COUNT=$(python3 -c "import json; f=open('$DB_FILE'); d=json.load(f); print(len(d.get('incidents', [])))")
        pass "Database JSON valid: $INCIDENT_COUNT incidents"
    else
        fail "Database JSON invalid (corrupted)"
    fi
else
    fail "Database file not found: $DB_FILE"
fi

echo ""

# 8. Tests
echo "8. Running test suite..."

if command -v pytest &> /dev/null; then
    # Run quick test count
    TEST_COUNT=$(pytest tests/ --collect-only -q 2>/dev/null | tail -1 | grep -o '^[0-9]*' || echo "0")
    if [ "$TEST_COUNT" -gt 0 ]; then
        pass "Test suite available: $TEST_COUNT tests"

        # Run tests with brief output
        if pytest tests/ -q --tb=no 2>&1 | tail -1 | grep -q "passed"; then
            SUMMARY=$(pytest tests/ -q --tb=no 2>&1 | tail -1)
            pass "Test suite passing: $SUMMARY"
        else
            warn "Some tests failing: review test results before deployment"
        fi
    else
        warn "No tests found"
    fi
else
    warn "pytest not available (cannot run tests)"
fi

echo ""

# 9. Configuration
echo "9. Checking configuration files..."

if [ -f "prometheus/alerts.yml" ]; then
    ALERT_COUNT=$(grep -c "alert:" prometheus/alerts.yml || echo "0")
    pass "Prometheus alerts: $ALERT_COUNT configured"
else
    warn "Prometheus alerts file missing"
fi

if [ -f ".env.example" ]; then
    pass "Environment example provided"
else
    warn "No .env.example provided"
fi

echo ""

# 10. Documentation
echo "10. Checking documentation..."

DOCS=(
    "docs/README.md"
    "docs/TROUBLESHOOTING_GUIDE.md"
    "docs/internal/ops-team-training-guide.md"
    "docs/internal/production-deployment-guide.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        SIZE=$(wc -l < "$doc")
        pass "Documentation: $doc ($SIZE lines)"
    else
        warn "Documentation missing: $doc"
    fi
done

echo ""

# 11. Git Status
echo "11. Checking git status..."

if command -v git &> /dev/null; then
    if git rev-parse --git-dir > /dev/null 2>&1; then
        BRANCH=$(git rev-parse --abbrev-ref HEAD)
        COMMIT=$(git rev-parse --short HEAD)
        pass "Git repository: $BRANCH @ $COMMIT"

        if git status --porcelain | grep -q .; then
            warn "Uncommitted changes in working directory"
        else
            pass "Working directory clean"
        fi
    else
        warn "Not a git repository"
    fi
else
    warn "git not installed (cannot check version control)"
fi

echo ""

# 12. Current Service State
echo "12. Checking current service state..."

if curl -s http://localhost:7860/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:7860/health | jq -r '.status' 2>/dev/null || echo "unknown")
    warn "Service currently running (status: $HEALTH)"
    warn "  → Stop existing service before deploying (docker stop nexus-prod)"
else
    pass "No existing service running on port 7860"
fi

echo ""

# 13. System Resources
echo "13. Checking system resources..."

# Memory
if [ "$(uname)" == "Darwin" ]; then
    AVAILABLE_MEM=$(vm_stat | grep "Pages free" | awk '{print int($3 * 4096 / (1024*1024*1024))}')
    TOTAL_MEM=$(sysctl -n hw.memsize | awk '{print int($1 / (1024*1024*1024))}')
else
    AVAILABLE_MEM=$(free -g | awk '/^Mem:/ {print $7}')
    TOTAL_MEM=$(free -g | awk '/^Mem:/ {print $2}')
fi

if [ "$AVAILABLE_MEM" -gt 1 ]; then
    pass "Memory available: ${AVAILABLE_MEM}GB free (${TOTAL_MEM}GB total)"
else
    warn "Limited memory available: ${AVAILABLE_MEM}GB free (recommend 2GB+)"
fi

# Disk
DISK_FREE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$DISK_FREE" -gt 5 ]; then
    pass "Disk space available: ${DISK_FREE}GB"
else
    fail "Insufficient disk space: ${DISK_FREE}GB (need 5GB+)"
fi

echo ""

# 14. Network
echo "14. Checking network..."

if ping -c 1 8.8.8.8 &> /dev/null; then
    pass "Internet connectivity available"
else
    warn "Cannot reach external network (required for container registry access)"
fi

echo ""

# Summary
echo "╔════════════════════════════════════════════╗"
echo "║  Validation Summary                       ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${RED}Failed:${NC}   $FAILED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

# Decision
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ READY FOR DEPLOYMENT${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review any warnings above"
    echo "  2. Build production image: docker build -t nexus:prod --build-arg APP_ENV=product ."
    echo "  3. Run smoke tests: ./scripts/local_enterprise_smoke.sh"
    echo "  4. Deploy: docker-compose up -d"
    echo ""
    exit 0
else
    echo -e "${RED}✗ NOT READY FOR DEPLOYMENT${NC}"
    echo ""
    echo "Please fix the failures above before attempting deployment."
    echo ""
    exit 1
fi
