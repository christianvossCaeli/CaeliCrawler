#!/bin/bash
# ============================================
# CaeliCrawler Database Restore Script
# ============================================
#
# Usage: ./restore-db.sh <backup_file.sql.gz>
#
# This script restores a PostgreSQL backup created by backup-db.sh
# It includes safety checks and confirmation prompts.
#
# WARNING: This will REPLACE all data in the target database!
#
# ============================================

set -e

# Configuration (can be overridden via environment)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-caelichrawler}"
POSTGRES_USER="${POSTGRES_USER:-caelichrawler}"
PGPASSWORD="${POSTGRES_PASSWORD:-caelichrawler_secret}"
export PGPASSWORD

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Options:"
    echo "  --force    Skip confirmation prompt"
    echo "  --dry-run  Show what would be done without executing"
    echo ""
    echo "Example:"
    echo "  $0 backups/caelichrawler_20231215_143000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
FORCE=false
DRY_RUN=false

# Parse additional arguments
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Verify backup file is readable and valid
if [[ "$BACKUP_FILE" == *.gz ]]; then
    if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
        log_error "Backup file is corrupted or not a valid gzip file"
        exit 1
    fi
    log_info "Backup file verified: valid gzip archive"
fi

# Get backup file info
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
FILE_DATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$BACKUP_FILE" 2>/dev/null || stat --printf="%y" "$BACKUP_FILE" 2>/dev/null | cut -d'.' -f1)

echo ""
echo "=========================================="
echo "         DATABASE RESTORE SCRIPT"
echo "=========================================="
echo ""
echo "Backup file:  $BACKUP_FILE"
echo "File size:    $FILE_SIZE"
echo "File date:    $FILE_DATE"
echo ""
echo "Target database:"
echo "  Host:       $POSTGRES_HOST:$POSTGRES_PORT"
echo "  Database:   $POSTGRES_DB"
echo "  User:       $POSTGRES_USER"
echo ""

# Test database connection
log_info "Testing database connection..."
if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    log_error "Cannot connect to PostgreSQL server"
    log_error "Please check your connection settings and ensure the server is running"
    exit 1
fi
log_info "Database connection successful"

# Check if target database exists
DB_EXISTS=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'")
if [ "$DB_EXISTS" = "1" ]; then
    # Get current database stats
    CURRENT_TABLES=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
    log_warn "Target database '$POSTGRES_DB' exists with $CURRENT_TABLES tables"
    log_warn "ALL DATA WILL BE REPLACED!"
else
    log_info "Target database '$POSTGRES_DB' does not exist, will be created"
fi

# Dry run - just show what would be done
if [ "$DRY_RUN" = true ]; then
    echo ""
    log_info "DRY RUN - The following operations would be performed:"
    echo "  1. Terminate all connections to $POSTGRES_DB"
    echo "  2. Drop database $POSTGRES_DB (if exists)"
    echo "  3. Create empty database $POSTGRES_DB"
    echo "  4. Restore from $BACKUP_FILE"
    echo "  5. Verify restore integrity"
    echo ""
    log_info "No changes were made"
    exit 0
fi

# Confirmation prompt
if [ "$FORCE" = false ]; then
    echo ""
    echo -e "${RED}WARNING: This will PERMANENTLY DELETE all data in '$POSTGRES_DB'${NC}"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
fi

# Create restore log
RESTORE_LOG="/tmp/restore_$(date +%Y%m%d_%H%M%S).log"
log_info "Restore log: $RESTORE_LOG"

# Start restore process
echo ""
log_info "Starting restore process..."
RESTORE_START=$(date +%s)

# Step 1: Terminate existing connections
log_info "Terminating existing connections to $POSTGRES_DB..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();
" > /dev/null 2>&1 || true

# Step 2: Drop and recreate database
log_info "Dropping existing database..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" >> "$RESTORE_LOG" 2>&1

log_info "Creating fresh database..."
psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;" >> "$RESTORE_LOG" 2>&1

# Step 3: Restore backup
log_info "Restoring backup (this may take a while)..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip -c "$BACKUP_FILE" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >> "$RESTORE_LOG" 2>&1
else
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_FILE" >> "$RESTORE_LOG" 2>&1
fi

# Step 4: Verify restore
log_info "Verifying restore..."
RESTORED_TABLES=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
RESTORED_ROWS=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "
SELECT SUM(n_live_tup)
FROM pg_stat_user_tables;
")

RESTORE_END=$(date +%s)
RESTORE_DURATION=$((RESTORE_END - RESTORE_START))

echo ""
echo "=========================================="
echo "         RESTORE COMPLETED"
echo "=========================================="
echo ""
echo "Restored database:"
echo "  Tables:     $RESTORED_TABLES"
echo "  Total rows: ${RESTORED_ROWS:-0}"
echo "  Duration:   ${RESTORE_DURATION}s"
echo ""
log_info "Restore log saved to: $RESTORE_LOG"
echo ""

# Check for errors in log
if grep -qi "error" "$RESTORE_LOG"; then
    log_warn "Some errors were logged during restore. Please review: $RESTORE_LOG"
fi

log_info "Database restore completed successfully!"
