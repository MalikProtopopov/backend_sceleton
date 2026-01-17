# =============================================================================
# Corporate CMS Engine - Makefile
# =============================================================================
# Usage:
#   make help          Show all available commands
#   make dev-up        Start development environment
#   make prod-up       Start production environment
# =============================================================================

.PHONY: help install dev run test lint format migrate migration rollback \
        dev-up dev-down dev-logs dev-build dev-restart dev-shell dev-status \
        prod-up prod-down prod-logs prod-build prod-restart prod-status \
        ssl-init ssl-renew db-backup db-restore clean seed init-admin init-admin-prod deploy

# Default target
help:
	@echo "=============================================="
	@echo "Corporate CMS Engine - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development (Local):"
	@echo "  make install       Install production dependencies"
	@echo "  make dev           Install development dependencies"
	@echo "  make run           Run local dev server (no Docker)"
	@echo "  make test          Run tests"
	@echo "  make lint          Run linters"
	@echo "  make format        Format code"
	@echo ""
	@echo "Docker Development:"
	@echo "  make dev-up        Start all dev services"
	@echo "  make dev-down      Stop all dev services"
	@echo "  make dev-logs      View dev logs (follow)"
	@echo "  make dev-build     Rebuild dev images"
	@echo "  make dev-restart   Restart backend container"
	@echo "  make dev-shell     Open shell in backend container"
	@echo "  make dev-status    Show dev service status"
	@echo ""
	@echo "Docker Production:"
	@echo "  make prod-up       Start all prod services"
	@echo "  make prod-down     Stop all prod services"
	@echo "  make prod-logs     View prod logs (follow)"
	@echo "  make prod-build    Rebuild prod images"
	@echo "  make prod-restart  Restart prod backend"
	@echo "  make prod-status   Show prod service status"
	@echo ""
	@echo "SSL:"
	@echo "  make ssl-init DOMAIN=example.com EMAIL=admin@example.com"
	@echo "                     Initialize SSL certificate"
	@echo "  make ssl-renew     Renew SSL certificates"
	@echo ""
	@echo "Database:"
	@echo "  make migrate       Run database migrations"
	@echo "  make migration msg='description'"
	@echo "                     Create new migration"
	@echo "  make rollback      Rollback last migration"
	@echo "  make db-backup     Backup database"
	@echo "  make db-restore FILE=backup.sql.gz"
	@echo "                     Restore database from backup"
	@echo ""
	@echo "Admin:"
	@echo "  make init-admin    Initialize admin (dev)"
	@echo "  make init-admin-prod"
	@echo "                     Initialize admin (prod)"
	@echo "  make seed          Seed database with test data"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy        Deploy with zero downtime"
	@echo "  make deploy-backup Deploy with backup first"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         Clean cache files"

# =============================================================================
# Local Development (without Docker)
# =============================================================================

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# =============================================================================
# Testing & Linting
# =============================================================================

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

lint:
	ruff check .
	mypy app/

format:
	ruff format .
	ruff check --fix .

# =============================================================================
# Database Migrations
# =============================================================================

migrate:
	alembic upgrade head

migration:
	@if [ -z "$(msg)" ]; then \
		echo "Error: Please provide migration message: make migration msg='your message'"; \
		exit 1; \
	fi
	alembic revision --autogenerate -m "$(msg)"

rollback:
	alembic downgrade -1

# =============================================================================
# Docker Development Commands
# =============================================================================

# Copy env.dev to .env if .env doesn't exist
.env:
	@if [ ! -f .env ]; then \
		echo "Creating .env from env.dev..."; \
		cp env.dev .env; \
	fi

dev-up: .env
	docker compose up -d
	@echo ""
	@echo "Development services started!"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
	@echo ""

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f

dev-logs-backend:
	docker compose logs -f backend

dev-build:
	docker compose build --no-cache

dev-restart:
	docker compose restart backend

dev-shell:
	docker compose exec backend bash

dev-status:
	docker compose ps

# =============================================================================
# Docker Production Commands
# =============================================================================

# Check that .env.prod exists
.env.prod-check:
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod not found!"; \
		echo "Please copy env.prod.example to .env.prod and configure it."; \
		exit 1; \
	fi

prod-up: .env.prod-check
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
	@echo ""
	@echo "Production services started!"
	@echo ""

prod-down:
	docker compose -f docker-compose.prod.yml --env-file .env.prod down

prod-logs:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f

prod-logs-backend:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend

prod-logs-nginx:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f nginx

prod-build:
	docker compose -f docker-compose.prod.yml --env-file .env.prod build

prod-restart:
	docker compose -f docker-compose.prod.yml --env-file .env.prod restart backend

prod-restart-nginx:
	docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload

prod-status:
	docker compose -f docker-compose.prod.yml --env-file .env.prod ps

prod-shell:
	docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend bash

# =============================================================================
# SSL Commands
# =============================================================================

ssl-init:
	@if [ -z "$(DOMAIN)" ] || [ -z "$(EMAIL)" ]; then \
		echo "Error: Please provide DOMAIN and EMAIL"; \
		echo "Usage: make ssl-init DOMAIN=example.com EMAIL=admin@example.com"; \
		exit 1; \
	fi
	chmod +x scripts/init-ssl.sh
	./scripts/init-ssl.sh $(DOMAIN) $(EMAIL)

ssl-renew:
	docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm certbot renew
	docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload

# =============================================================================
# Backup Commands
# =============================================================================

db-backup:
	chmod +x scripts/backup.sh
	./scripts/backup.sh --db-only

db-backup-full:
	chmod +x scripts/backup.sh
	./scripts/backup.sh

db-restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: Please provide backup FILE"; \
		echo "Usage: make db-restore FILE=backups/db_backup_20240101_120000.sql.gz"; \
		exit 1; \
	fi
	@echo "Restoring database from $(FILE)..."
	gunzip -c $(FILE) | docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T postgres psql -U cms_user -d cms_db

db-backup-dev:
	chmod +x scripts/backup.sh
	./scripts/backup.sh --db-only --dev

# =============================================================================
# Admin Initialization
# =============================================================================

init-admin: dev-up
	@echo "Waiting for services to be ready..."
	@sleep 5
	docker compose exec backend python -m app.scripts.init_admin

init-admin-prod: .env.prod-check
	docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python -m app.scripts.init_admin

seed:
	docker compose exec backend python -m app.scripts.seed_database

# =============================================================================
# Deployment
# =============================================================================

deploy:
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh

deploy-backup:
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh --backup

deploy-no-migrate:
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh --no-migrate

# =============================================================================
# Utilities
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

docker-clean:
	docker system prune -f

docker-clean-all:
	@echo "WARNING: This will remove all unused Docker resources!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
	docker system prune -a -f --volumes

# =============================================================================
# Health Checks
# =============================================================================

health-dev:
	@curl -s http://localhost:8000/health | python -m json.tool || echo "Service not available"

health-prod:
	@curl -s https://api.$(DOMAIN)/health | python -m json.tool || echo "Service not available"

# =============================================================================
# Logs Analysis
# =============================================================================

logs-errors:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs backend 2>&1 | grep -i error

logs-tail:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail=100 backend
