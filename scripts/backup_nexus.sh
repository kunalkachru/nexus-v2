#!/bin/bash

# NEXUS Backup Automation Script
#
# Purpose: Create automated backups of NEXUS database with:
#  - Gzip compression
#  - S3 upload
#  - Local retention cleanup (7-day max)
#  - Backup verification
#
# Usage: ./scripts/backup_nexus.sh
#
# Expected cron entry (every 6 hours):
#  0 */6 * * * /nexus/scripts/backup_nexus.sh >> /var/log/nexus-backup.log 2>&1

set -e  # Exit on any error

# Configuration
BACKUP_DIR="${BACKUP_DIR:-.backup/nexus}"
DATABASE_PATH="${DATABASE_PATH:-.artifacts/incidents.json}"
S3_BUCKET="${S3_BUCKET:-s3://nexus-backups}"
LOCAL_RETENTION_DAYS=7
LOG_FILE="/var/log/nexus-backup.log"

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="nexus_backup_${TIMESTAMP}.json.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Pre-flight checks
log "Starting NEXUS backup process..."

if [ ! -f "$DATABASE_PATH" ]; then
    error "Database file not found: $DATABASE_PATH"
fi

mkdir -p "$BACKUP_DIR"

# Check if database is locked
if lsof "$DATABASE_PATH" 2>/dev/null | grep -q .; then
    log "Database is in use by processes. Proceeding with snapshot..."
fi

# Create backup
log "Creating backup: $BACKUP_FILENAME"

# If SQLite database
if [[ "$DATABASE_PATH" == *.db ]] || [[ "$DATABASE_PATH" == *.sqlite ]]; then
    # Use sqlite3 dump for consistency
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DATABASE_PATH" ".dump" | gzip > "$BACKUP_PATH"
        log "SQLite dump created and compressed"
    else
        # Fallback to file copy
        cp "$DATABASE_PATH" - | gzip > "$BACKUP_PATH"
        log "Database file copied and compressed (sqlite3 not available)"
    fi
else
    # JSON file backup
    if [ -f "$DATABASE_PATH" ]; then
        gzip < "$DATABASE_PATH" > "$BACKUP_PATH"
        log "JSON backup created and compressed"
    else
        error "Database file not accessible: $DATABASE_PATH"
    fi
fi

# Verify backup was created
if [ ! -f "$BACKUP_PATH" ]; then
    error "Backup file was not created: $BACKUP_PATH"
fi

BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
log "Backup size: $BACKUP_SIZE"

# Verify backup is not empty
if [ ! -s "$BACKUP_PATH" ]; then
    error "Backup file is empty: $BACKUP_PATH"
fi

# Verify backup is valid gzip
if ! gzip -t "$BACKUP_PATH" 2>/dev/null; then
    error "Backup file is corrupted or not valid gzip: $BACKUP_PATH"
fi

success "Backup created: $BACKUP_PATH"

# Upload to S3
log "Uploading to S3: $S3_BUCKET/$BACKUP_FILENAME"

if command -v aws &> /dev/null; then
    if aws s3 cp "$BACKUP_PATH" "$S3_BUCKET/$BACKUP_FILENAME" --sse AES256; then
        success "Backup uploaded to S3"
    else
        error "S3 upload failed"
    fi
else
    warning "AWS CLI not available. Skipping S3 upload. Install with: pip install awscli"
fi

# Verify S3 upload
if command -v aws &> /dev/null; then
    log "Verifying S3 upload..."
    if aws s3 ls "$S3_BUCKET/$BACKUP_FILENAME"; then
        success "S3 upload verified"
    else
        error "S3 verification failed"
    fi
fi

# Local retention cleanup
log "Cleaning up local backups older than $LOCAL_RETENTION_DAYS days..."

CLEANUP_COUNT=0
if [ -d "$BACKUP_DIR" ]; then
    # Find and delete backups older than retention period
    while IFS= read -r old_backup; do
        log "Deleting old backup: $(basename $old_backup)"
        rm -f "$old_backup"
        ((CLEANUP_COUNT++))
    done < <(find "$BACKUP_DIR" -name "nexus_backup_*.json.gz" -mtime +$LOCAL_RETENTION_DAYS)
fi

if [ $CLEANUP_COUNT -gt 0 ]; then
    success "Cleaned up $CLEANUP_COUNT old backup(s)"
else
    log "No old backups to clean up"
fi

# Final summary
log "====================================="
log "Backup Summary:"
log "  Filename: $BACKUP_FILENAME"
log "  Size: $BACKUP_SIZE"
log "  Location: $BACKUP_PATH"
log "  S3: $S3_BUCKET/$BACKUP_FILENAME"
log "====================================="

success "NEXUS backup completed successfully"

exit 0
