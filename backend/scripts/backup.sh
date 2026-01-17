#!/bin/bash
# =============================================================================
# Database and Storage Backup Script
# =============================================================================
# This script creates backups of PostgreSQL database and optionally MinIO data.
#
# Usage:
#   ./scripts/backup.sh [options]
#
# Options:
#   -d, --db-only      Backup only database (default: both)
#   -s, --storage-only Backup only storage
#   -k, --keep N       Keep last N backups (default: 7)
#   -o, --output DIR   Output directory (default: ./backups)
#   -h, --help         Show this help
#
# Example:
#   ./scripts/backup.sh --keep 14 --output /mnt/backups
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default settings
BACKUP_DB=true
BACKUP_STORAGE=true
KEEP_BACKUPS=7
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ENV_FILE=".env.prod"
COMPOSE_FILE="docker-compose.prod.yml"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--db-only)
            BACKUP_DB=true
            BACKUP_STORAGE=false
            shift
            ;;
        -s|--storage-only)
            BACKUP_DB=false
            BACKUP_STORAGE=true
            shift
            ;;
        -k|--keep)
            KEEP_BACKUPS="$2"
            shift 2
            ;;
        -o|--output)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --dev)
            ENV_FILE=".env"
            COMPOSE_FILE="docker-compose.yml"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -d, --db-only      Backup only database"
            echo "  -s, --storage-only Backup only storage"
            echo "  -k, --keep N       Keep last N backups (default: 7)"
            echo "  -o, --output DIR   Output directory (default: ./backups)"
            echo "  --dev              Use development environment"
            echo "  -h, --help         Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$PROJECT_DIR"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Set defaults if not defined
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-cms}

log_info "=========================================="
log_info "Backup Script"
log_info "=========================================="
log_info "Timestamp: $TIMESTAMP"
log_info "Backup directory: $BACKUP_DIR"
log_info "Keep backups: $KEEP_BACKUPS"
log_info "Backup database: $BACKUP_DB"
log_info "Backup storage: $BACKUP_STORAGE"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# =============================================================================
# Database Backup
# =============================================================================
if [ "$BACKUP_DB" = true ]; then
    log_info "Creating database backup..."
    
    DB_BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"
    
    # Check if postgres container is running
    if ! docker compose -f "$COMPOSE_FILE" ps postgres | grep -q "running"; then
        log_error "PostgreSQL container is not running!"
        exit 1
    fi
    
    # Create backup
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl | \
        gzip > "$DB_BACKUP_FILE"
    
    if [ $? -eq 0 ] && [ -s "$DB_BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
        log_success "Database backup created: $DB_BACKUP_FILE ($BACKUP_SIZE)"
    else
        log_error "Database backup failed!"
        rm -f "$DB_BACKUP_FILE"
        exit 1
    fi
fi

# =============================================================================
# Storage Backup (MinIO volumes)
# =============================================================================
if [ "$BACKUP_STORAGE" = true ]; then
    log_info "Creating storage backup..."
    
    STORAGE_BACKUP_FILE="$BACKUP_DIR/storage_backup_$TIMESTAMP.tar.gz"
    
    # Get volume name based on environment
    if [ "$COMPOSE_FILE" = "docker-compose.yml" ]; then
        MINIO_VOLUME="cms_minio_data_dev"
    else
        MINIO_VOLUME="cms_minio_data_prod"
    fi
    
    # Check if volume exists
    if docker volume ls | grep -q "$MINIO_VOLUME"; then
        docker run --rm \
            -v "$MINIO_VOLUME":/data:ro \
            -v "$BACKUP_DIR":/backup \
            alpine tar czf "/backup/storage_backup_$TIMESTAMP.tar.gz" -C /data .
        
        if [ $? -eq 0 ] && [ -s "$STORAGE_BACKUP_FILE" ]; then
            BACKUP_SIZE=$(du -h "$STORAGE_BACKUP_FILE" | cut -f1)
            log_success "Storage backup created: $STORAGE_BACKUP_FILE ($BACKUP_SIZE)"
        else
            log_warn "Storage backup failed or empty"
        fi
    else
        log_warn "MinIO volume not found: $MINIO_VOLUME (skipping storage backup)"
    fi
fi

# =============================================================================
# Cleanup old backups
# =============================================================================
log_info "Cleaning up old backups (keeping last $KEEP_BACKUPS)..."

cleanup_old_backups() {
    local pattern=$1
    local files=($(ls -t "$BACKUP_DIR"/$pattern 2>/dev/null || true))
    local count=${#files[@]}
    
    if [ $count -gt $KEEP_BACKUPS ]; then
        local to_delete=$((count - KEEP_BACKUPS))
        for ((i=KEEP_BACKUPS; i<count; i++)); do
            log_info "Removing old backup: ${files[$i]}"
            rm -f "${files[$i]}"
        done
        log_success "Removed $to_delete old backup(s)"
    else
        log_info "No old backups to remove (found $count, keeping $KEEP_BACKUPS)"
    fi
}

cleanup_old_backups "db_backup_*.sql.gz"
cleanup_old_backups "storage_backup_*.tar.gz"

echo ""

# =============================================================================
# Summary
# =============================================================================
log_info "=========================================="
log_success "Backup Complete!"
log_info "=========================================="
echo ""
log_info "Backup files:"
ls -lh "$BACKUP_DIR"/*_$TIMESTAMP.* 2>/dev/null || log_warn "No backup files found"
echo ""
log_info "Total backups in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/ 2>/dev/null | tail -n +2 || true
echo ""

# =============================================================================
# Restore instructions
# =============================================================================
log_info "To restore database backup:"
log_info "  gunzip -c $DB_BACKUP_FILE | docker compose -f $COMPOSE_FILE exec -T postgres psql -U $POSTGRES_USER -d $POSTGRES_DB"
echo ""
log_info "To restore storage backup:"
log_info "  docker run --rm -v $MINIO_VOLUME:/data -v $BACKUP_DIR:/backup alpine tar xzf /backup/storage_backup_$TIMESTAMP.tar.gz -C /data"
echo ""

