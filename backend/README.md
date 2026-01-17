# Corporate CMS Engine

Reusable backend engine for corporate websites built with FastAPI, PostgreSQL, and Redis.

## Features

- 🏢 **Multi-tenancy** - Database-per-tenant with shared codebase
- 🔐 **Authentication** - JWT-based auth with RBAC
- 🌍 **Localization** - Translation tables for multi-language support
- 🔍 **SEO** - Meta tags, sitemap, redirects management
- 📝 **Content Management** - Articles, services, FAQ, team
- 📊 **Lead Analytics** - UTM tracking, device detection
- 🚀 **Production Ready** - Docker, structured logging, rate limiting

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker (optional)

### Development Setup

1. **Clone and install dependencies:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e ".[dev]"
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Start services (Docker):**

```bash
docker-compose up -d postgres redis
```

4. **Run migrations:**

```bash
alembic upgrade head
```

5. **Start development server:**

```bash
uvicorn app.main:app --reload
```

6. **Open API docs:**

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Using Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## Project Structure

```
backend/
├── alembic/              # Database migrations
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Settings
│   ├── core/             # Shared infrastructure
│   │   ├── base_model.py # SQLAlchemy mixins
│   │   ├── database.py   # DB session management
│   │   ├── exceptions.py # Exception classes
│   │   ├── logging.py    # Structured logging
│   │   └── security.py   # JWT, RBAC
│   ├── middleware/       # Custom middleware
│   └── modules/          # Feature modules
├── tests/                # Test suite
├── Dockerfile
└── docker-compose.yml
```

## API Overview

### Public API (no auth required)

```
GET  /api/v1/public/services          # List services
GET  /api/v1/public/services/{slug}   # Get service by slug
GET  /api/v1/public/articles          # List published articles
GET  /api/v1/public/articles/{slug}   # Get article by slug
GET  /api/v1/public/employees         # List team members
GET  /api/v1/public/faq               # Get FAQ items
POST /api/v1/public/inquiries         # Submit inquiry form
```

### Admin API (auth required)

```
POST /api/v1/auth/login               # Get JWT tokens
POST /api/v1/auth/refresh             # Refresh access token
GET  /api/v1/admin/me                 # Current user info

# CRUD for all resources
GET/POST/PATCH/DELETE /api/v1/admin/articles
GET/POST/PATCH/DELETE /api/v1/admin/services
GET/POST/PATCH/DELETE /api/v1/admin/employees
...
```

## Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_auth.py -v
```

### Code Quality

```bash
# Lint
ruff check .
mypy app/

# Format
ruff format .
```

### Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "add new field"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `JWT_SECRET_KEY` | Secret for JWT signing | Required |
| `S3_ENDPOINT_URL` | S3-compatible storage URL | - |
| `EMAIL_PROVIDER` | Email service (sendgrid/mailgun/console) | console |
| `LOG_FORMAT` | Logging format (json/console) | json |

See `.env.example` for all options.

## Architecture

### Key Patterns

- **Service Layer** - Business logic in services, not routes
- **Soft Delete** - Never hard-delete content (SEO!)
- **Optimistic Locking** - Version field prevents lost updates
- **Translation Tables** - Separate locale tables, not JSONB
- **Feature Flags** - Per-tenant feature toggles

### Multi-tenancy

Each tenant gets isolated data with `tenant_id` in all tables:

```python
class Article(Base, TenantMixin, ...):
    tenant_id: UUID  # From TenantMixin
    ...
```

## License

Proprietary - All rights reserved.

