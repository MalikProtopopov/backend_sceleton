#!/bin/bash
# =============================================================================
# Zero-Downtime Deployment Script
# =============================================================================
# This script performs a zero-downtime deployment by:
# 1. Pulling latest code changes
# 2. Building new Docker images
# 3. Running database migrations
# 4. Performing rolling restart of services
#
# Usage:
#   ./scripts/deploy.sh [options]
#
# Options:
#   --no-pull         Skip git pull
#   --no-build        Skip Docker build
#   --no-migrate      Skip database migrations
#   --backup          Create backup before deploy
#   -h, --help        Show this help
#
# Example:
#   ./scripts/deploy.sh --backup
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
DO_PULL=true
DO_BUILD=true
DO_MIGRATE=true
DO_BACKUP=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-pull)
            DO_PULL=false
            shift
            ;;
        --no-build)
            DO_BUILD=false
            shift
            ;;
        --no-migrate)
            DO_MIGRATE=false
            shift
            ;;
        --backup)
            DO_BACKUP=true
            shift
            ;;
        --dev)
            COMPOSE_FILE="docker-compose.yml"
            ENV_FILE=".env"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --no-pull         Skip git pull"
            echo "  --no-build        Skip Docker build"
            echo "  --no-migrate      Skip database migrations"
            echo "  --backup          Create backup before deploy"
            echo "  --dev             Use development environment"
            echo "  -h, --help        Show this help"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$PROJECT_DIR"

log_info "=========================================="
log_info "Deployment Script"
log_info "=========================================="
log_info "Project directory: $PROJECT_DIR"
log_info "Compose file: $COMPOSE_FILE"
log_info "Pull: $DO_PULL, Build: $DO_BUILD, Migrate: $DO_MIGRATE, Backup: $DO_BACKUP"
echo ""

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    log_error "$ENV_FILE not found!"
    exit 1
fi

# =============================================================================
# Step 1: Create backup (optional)
# =============================================================================
if [ "$DO_BACKUP" = true ]; then
    log_info "Step 1: Creating backup..."
    if [ -f "$SCRIPT_DIR/backup.sh" ]; then
        "$SCRIPT_DIR/backup.sh" --db-only
    else
        log_warn "backup.sh not found, skipping backup"
    fi
    echo ""
else
    log_info "Step 1: Skipping backup (use --backup to enable)"
    echo ""
fi

# =============================================================================
# Step 2: Pull latest changes
# =============================================================================
if [ "$DO_PULL" = true ]; then
    log_info "Step 2: Pulling latest changes..."
    
    # Check if git repository
    if [ -d ".git" ]; then
        # Stash any local changes
        if ! git diff --quiet; then
            log_warn "Local changes detected, stashing..."
            git stash
        fi
        
        # Pull latest changes
        git pull origin main || git pull origin master
        log_success "Code updated"
    else
        log_warn "Not a git repository, skipping pull"
    fi
    echo ""
else
    log_info "Step 2: Skipping git pull"
    echo ""
fi

# =============================================================================
# Step 3: Build Docker images
# =============================================================================
if [ "$DO_BUILD" = true ]; then
    log_info "Step 3: Building Docker images..."
    
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build backend
    log_success "Docker images built"
    echo ""
else
    log_info "Step 3: Skipping Docker build"
    echo ""
fi

# =============================================================================
# Step 4: Run database migrations
# =============================================================================
if [ "$DO_MIGRATE" = true ]; then
    log_info "Step 4: Running database migrations..."
    
    # Run migrations
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm migrations
    log_success "Migrations completed"
    echo ""
else
    log_info "Step 4: Skipping migrations"
    echo ""
fi

# =============================================================================
# Step 5: Rolling restart of services
# =============================================================================
log_info "Step 5: Performing rolling restart..."

# Start new backend container
log_info "Starting new backend container..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --no-deps backend

# Wait for health check
log_info "Waiting for backend health check..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps backend | grep -q "healthy"; then
        log_success "Backend is healthy!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    log_info "Waiting for backend to be healthy... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "Backend failed to become healthy!"
    log_info "Rolling back..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down backend
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d backend
    exit 1
fi

# Reload nginx to pick up any config changes
log_info "Reloading nginx..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec nginx nginx -s reload 2>/dev/null || true
echo ""

# =============================================================================
# Step 6: Cleanup
# =============================================================================
log_info "Step 6: Cleaning up..."

# Remove dangling images
docker image prune -f
log_success "Cleanup completed"
echo ""

# =============================================================================
# Summary
# =============================================================================
log_info "=========================================="
log_success "Deployment Complete!"
log_info "=========================================="
echo ""
log_info "Service status:"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
echo ""
log_info "Recent logs (last 10 lines):"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=10 backend
echo ""
log_info "Useful commands:"
log_info "  make prod-logs    - View all logs"
log_info "  make prod-status  - Check service status"
log_info "  make db-backup    - Create database backup"
echo ""

