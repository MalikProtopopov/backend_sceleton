#!/bin/bash
# =============================================================================
# SSL Certificate Initialization Script
# =============================================================================
# This script automates the process of obtaining SSL certificates from
# Let's Encrypt using certbot in webroot mode.
#
# Usage:
#   ./scripts/init-ssl.sh <domain> <email>
#
# Example:
#   ./scripts/init-ssl.sh example.com admin@example.com
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - DNS A records pointing to this server for:
#     * api.<domain>
#     * admin.<domain>
#   - Ports 80 and 443 open
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

# Check arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <domain> <email>"
    echo "Example: $0 example.com admin@example.com"
    exit 1
fi

DOMAIN=$1
EMAIL=$2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log_info "=========================================="
log_info "SSL Certificate Initialization"
log_info "=========================================="
log_info "Domain: $DOMAIN"
log_info "Email: $EMAIL"
log_info "Project directory: $PROJECT_DIR"
echo ""

cd "$PROJECT_DIR"

# =============================================================================
# Step 1: Verify DNS records
# =============================================================================
log_info "Step 1: Verifying DNS records..."

check_dns() {
    local subdomain=$1
    local full_domain="${subdomain}.${DOMAIN}"
    
    if [ "$subdomain" = "@" ]; then
        full_domain="$DOMAIN"
    fi
    
    log_info "Checking DNS for $full_domain..."
    
    if command -v dig &> /dev/null; then
        local ip=$(dig +short "$full_domain" | head -1)
        if [ -n "$ip" ]; then
            log_success "$full_domain resolves to $ip"
            return 0
        else
            log_error "$full_domain does not resolve"
            return 1
        fi
    else
        log_warn "dig not found, skipping DNS check for $full_domain"
        return 0
    fi
}

DNS_OK=true
check_dns "api" || DNS_OK=false
check_dns "admin" || DNS_OK=false

if [ "$DNS_OK" = false ]; then
    log_error "DNS records not properly configured!"
    log_info "Please ensure A records point to this server for:"
    log_info "  - api.$DOMAIN"
    log_info "  - admin.$DOMAIN"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# =============================================================================
# Step 2: Create nginx initial configuration
# =============================================================================
log_info "Step 2: Setting up initial nginx configuration..."

if [ ! -f "nginx/nginx-initial.conf" ]; then
    log_error "nginx/nginx-initial.conf not found!"
    exit 1
fi

cp nginx/nginx-initial.conf nginx/nginx.conf
log_success "Initial nginx configuration copied"
echo ""

# =============================================================================
# Step 3: Start services with HTTP only
# =============================================================================
log_info "Step 3: Starting services (HTTP mode)..."

# Make sure .env.prod exists
if [ ! -f ".env.prod" ]; then
    log_error ".env.prod not found!"
    log_info "Please copy env.prod.example to .env.prod and configure it first."
    exit 1
fi

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres redis backend nginx
log_success "Services started"

# Wait for nginx to be ready
log_info "Waiting for nginx to be ready..."
sleep 5

# Test HTTP endpoint
if curl -s -o /dev/null -w "%{http_code}" "http://api.$DOMAIN/health" | grep -q "200\|301\|302"; then
    log_success "HTTP endpoint is accessible"
else
    log_warn "HTTP endpoint may not be accessible yet, continuing..."
fi
echo ""

# =============================================================================
# Step 4: Obtain SSL certificate
# =============================================================================
log_info "Step 4: Obtaining SSL certificate from Let's Encrypt..."

# Request certificate for all subdomains
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "api.$DOMAIN" \
    -d "admin.$DOMAIN"

if [ $? -eq 0 ]; then
    log_success "SSL certificate obtained successfully!"
else
    log_error "Failed to obtain SSL certificate"
    log_info "Check the logs: docker compose -f docker-compose.prod.yml logs certbot"
    exit 1
fi
echo ""

# =============================================================================
# Step 5: Generate SSL nginx configuration
# =============================================================================
log_info "Step 5: Generating SSL nginx configuration..."

if [ ! -f "nginx/nginx.conf.template" ]; then
    log_error "nginx/nginx.conf.template not found!"
    exit 1
fi

export DOMAIN
envsubst '${DOMAIN}' < nginx/nginx.conf.template > nginx/nginx.conf
log_success "SSL nginx configuration generated"
echo ""

# =============================================================================
# Step 6: Reload nginx with SSL
# =============================================================================
log_info "Step 6: Reloading nginx with SSL configuration..."

docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -t
if [ $? -ne 0 ]; then
    log_error "Nginx configuration test failed!"
    exit 1
fi

docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload
log_success "Nginx reloaded with SSL"
echo ""

# =============================================================================
# Step 7: Test HTTPS
# =============================================================================
log_info "Step 7: Testing HTTPS endpoints..."

sleep 3

test_https() {
    local url=$1
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$status" = "200" ] || [ "$status" = "301" ] || [ "$status" = "302" ]; then
        log_success "$url - OK (HTTP $status)"
        return 0
    else
        log_warn "$url - HTTP $status"
        return 1
    fi
}

test_https "https://api.$DOMAIN/health"
test_https "https://admin.$DOMAIN/"
echo ""

# =============================================================================
# Step 8: Start certbot auto-renewal
# =============================================================================
log_info "Step 8: Starting certbot auto-renewal service..."

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d certbot
log_success "Certbot auto-renewal service started"
echo ""

# =============================================================================
# Setup cron for certificate renewal
# =============================================================================
log_info "Step 9: Setting up cron job for certificate renewal..."

CRON_CMD="0 0 * * * cd $PROJECT_DIR && docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm certbot renew --quiet && docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "certbot renew"; then
    log_warn "Certbot renewal cron job already exists"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    log_success "Cron job added for daily certificate renewal check"
fi
echo ""

# =============================================================================
# Summary
# =============================================================================
log_info "=========================================="
log_success "SSL Setup Complete!"
log_info "=========================================="
echo ""
log_info "Your services are now available at:"
log_info "  API:    https://api.$DOMAIN"
log_info "  Admin:  https://admin.$DOMAIN"
echo ""
log_info "Next steps:"
log_info "  1. Create admin user: make init-admin-prod"
log_info "  2. Deploy admin panel static files to /var/www/admin"
log_info "  3. Configure CORS_ORIGINS in .env.prod if needed"
echo ""
log_info "Useful commands:"
log_info "  make prod-logs    - View logs"
log_info "  make prod-status  - Check service status"
log_info "  make db-backup    - Backup database"
echo ""

