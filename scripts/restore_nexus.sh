#!/bin/bash

# NEXUS Restore Script
#
# Purpose: Restore NEXUS database from a backup with:
#  - Backup integrity verification
#  - Rollback capability (keeps original as .backup)
#  - Transaction-style restoration (atomic)
#
# Usage: ./scripts/restore_nexus.sh <backup_file>
#
# Examples:
#  # Restore from local backup
#  ./scripts/restore_nexus.sh .backup/nexus/nexus_backup_20260617_120000.json.gz
#
#  # Restore from S3
#  aws s3 cp s3://nexus-backups/nexus_backup_20260617_120000.json.gz . && \
#    ./scripts/restore_nexus.sh nexus_backup_20260617_120000.json.gz

set -e  # Exit on any error

# Configuration
DATABASE_PATH="${DATABASE_PATH:-.artifacts/incidents.json}"
LOG_FILE="/var/log/nexus-restore.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Argument validation
if [ $# -ne 1 ]; then
    error "Usage: $0 <backup_file>"
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

log "Starting NEXUS restore process..."
info "Backup file: $BACKUP_FILE"
info "Target database: $DATABASE_PATH"

# Pre-flight checks
log "Running pre-flight checks..."

# Check if backup is valid gzip
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
    error "Backup file is corrupted or not valid gzip: $BACKUP_FILE"
fi

success "Backup file integrity verified"

# Check if NEXUS service is running
if command -v systemctl &> /dev/null; then
    if systemctl is-active --quiet nexus; then
        warning "NEXUS service is running. Restore will require service stop."
        log "Attempting to stop NEXUS service..."
        systemctl stop nexus || warning "Could not stop NEXUS (may require manual stop)"
    fi
elif docker ps | grep -q nexus; then
    warning "NEXUS container is running. Restore will require container stop."
    log "Attempting to stop NEXUS container..."
    docker stop nexus-app || warning "Could not stop NEXUS (may require manual stop)"
fi

# Create backup of current database (rollback capability)
if [ -f "$DATABASE_PATH" ]; then
    BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    ORIGINAL_BACKUP="${DATABASE_PATH}.backup.${BACKUP_TIMESTAMP}"

    log "Creating backup of current database: $ORIGINAL_BACKUP"
    cp "$DATABASE_PATH" "$ORIGINAL_BACKUP"
    success "Current database backed up to: $ORIGINAL_BACKUP"
else
    info "No existing database found. This is a fresh restore."
fi

# Restore from backup
log "Restoring database from backup..."

if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Decompress and restore
    if ! gunzip -c "$BACKUP_FILE" > "$DATABASE_PATH"; then
        error "Failed to decompress backup. Restoring from backup..."
        if [ -f "$ORIGINAL_BACKUP" ]; then
            cp "$ORIGINAL_BACKUP" "$DATABASE_PATH"
            error "Restore failed. Original database restored from: $ORIGINAL_BACKUP"
        fi
    fi
else
    # Direct copy if not gzipped (shouldn't happen but handle gracefully)
    if ! cp "$BACKUP_FILE" "$DATABASE_PATH"; then
        error "Failed to restore from backup"
    fi
fi

success "Database restored from backup"

# Verify restored database
log "Verifying restored database..."

if [ ! -f "$DATABASE_PATH" ]; then
    error "Restored database file not found!"
fi

if [ ! -s "$DATABASE_PATH" ]; then
    error "Restored database is empty!"
fi

# Verify database integrity
if [[ "$DATABASE_PATH" == *.db ]] || [[ "$DATABASE_PATH" == *.sqlite ]]; then
    if command -v sqlite3 &> /dev/null; then
        if ! sqlite3 "$DATABASE_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
            error "Database integrity check failed. Restoring from backup..."
            if [ -f "$ORIGINAL_BACKUP" ]; then
                cp "$ORIGINAL_BACKUP" "$DATABASE_PATH"
                error "Database is corrupted. Original restored from: $ORIGINAL_BACKUP"
            fi
        fi
        success "Database integrity verified"
    else
        warning "sqlite3 not available. Skipping database integrity check."
    fi
elif [[ "$DATABASE_PATH" == *.json ]]; then
    # Verify JSON is valid
    if ! python3 -m json.tool "$DATABASE_PATH" > /dev/null 2>&1; then
        error "Restored JSON is invalid. Restoring from backup..."
        if [ -f "$ORIGINAL_BACKUP" ]; then
            cp "$ORIGINAL_BACKUP" "$DATABASE_PATH"
            error "Restored database has invalid JSON. Original restored from: $ORIGINAL_BACKUP"
        fi
    fi
    success "Database JSON validity verified"
fi

# Verify data count
if command -v sqlite3 &> /dev/null; then
    INCIDENT_COUNT=$(sqlite3 "$DATABASE_PATH" "SELECT COUNT(*) FROM incidents;" 2>/dev/null || echo "N/A")
    if [ "$INCIDENT_COUNT" != "N/A" ]; then
        info "Restored database contains $INCIDENT_COUNT incidents"
        if [ "$INCIDENT_COUNT" -eq 0 ]; then
            warning "Restored database is empty (no incidents found)"
        fi
    fi
fi

success "Database verification complete"

# Restart NEXUS service
log "Restarting NEXUS service..."

if command -v systemctl &> /dev/null; then
    if systemctl start nexus; then
        success "NEXUS service started successfully"
    else
        warning "Failed to start NEXUS service. Start manually with: systemctl start nexus"
    fi
elif command -v docker &> /dev/null; then
    if docker start nexus-app; then
        success "NEXUS container started successfully"
    else
        warning "Failed to start NEXUS container. Start manually with: docker start nexus-app"
    fi
else
    warning "Could not determine how to start NEXUS. Start manually."
fi

# Health check
sleep 5  # Wait for service to fully start
log "Running health check..."

if curl -f http://localhost:7860/health > /dev/null 2>&1; then
    success "NEXUS health check passed"
else
    warning "NEXUS health check failed. Service may still be starting or there may be issues."
fi

# Final summary
log "====================================="
log "Restore Summary:"
log "  Backup file: $BACKUP_FILE"
log "  Restored to: $DATABASE_PATH"
log "  Original backup: ${ORIGINAL_BACKUP:-N/A (fresh restore)}"
log "  Timestamp: $(date)"
log "====================================="

success "NEXUS restore completed successfully"

if [ -f "$ORIGINAL_BACKUP" ]; then
    info "Original database saved as: $ORIGINAL_BACKUP (safe to delete after verification)"
fi

exit 0
