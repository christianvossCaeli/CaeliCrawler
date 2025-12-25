#!/bin/bash
# ============================================
# CaeliCrawler Database Backup Script
# ============================================
# Usage: ./backup-db.sh [backup_dir]
#
# Environment variables:
#   POSTGRES_HOST     - Database host (default: localhost)
#   POSTGRES_PORT     - Database port (default: 5432)
#   POSTGRES_USER     - Database user (default: caelichrawler)
#   POSTGRES_DB       - Database name (default: caelichrawler)
#   POSTGRES_PASSWORD - Database password (required)
#   BACKUP_RETENTION  - Days to keep backups (default: 30)
# ============================================

set -euo pipefail

# Configuration
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-caelichrawler}"
POSTGRES_DB="${POSTGRES_DB:-caelichrawler}"
BACKUP_RETENTION="${BACKUP_RETENTION:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check for required password
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    log_error "POSTGRES_PASSWORD environment variable is required"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup filename
BACKUP_FILE="${BACKUP_DIR}/caelichrawler_${TIMESTAMP}.sql.gz"
BACKUP_FILE_LATEST="${BACKUP_DIR}/caelichrawler_latest.sql.gz"

log_info "Starting backup of database '$POSTGRES_DB'"
log_info "Backup file: $BACKUP_FILE"

# Check if running in Docker
if [ -f /.dockerenv ]; then
    # Running inside Docker - use docker exec
    log_info "Running inside Docker container"
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        --format=custom \
        --compress=9 \
        -f "$BACKUP_FILE"
else
    # Running on host - use docker-compose exec
    if command -v docker-compose &> /dev/null; then
        log_info "Using docker-compose to create backup"
        docker-compose exec -T postgres pg_dump \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            --format=custom \
            --compress=9 | gzip > "$BACKUP_FILE"
    elif command -v docker &> /dev/null; then
        log_info "Using docker exec to create backup"
        docker exec caelichrawler-postgres pg_dump \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            --format=custom \
            --compress=9 | gzip > "$BACKUP_FILE"
    else
        log_error "Neither docker-compose nor docker found"
        exit 1
    fi
fi

# Check if backup was successful
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"

    # Create symlink to latest backup
    ln -sf "$(basename "$BACKUP_FILE")" "$BACKUP_FILE_LATEST"
    log_info "Updated latest backup symlink"
else
    log_error "Backup failed - file not created"
    exit 1
fi

# Cleanup old backups
log_info "Cleaning up backups older than $BACKUP_RETENTION days"
find "$BACKUP_DIR" -name "caelichrawler_*.sql.gz" -type f -mtime +$BACKUP_RETENTION -delete
REMAINING=$(find "$BACKUP_DIR" -name "caelichrawler_*.sql.gz" -type f | wc -l)
log_info "Remaining backups: $REMAINING"

log_info "Backup completed successfully"
