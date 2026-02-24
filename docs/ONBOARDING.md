# Developer Onboarding Guide

## 1. Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- `make` (optional, for convenience commands)

### Start the Stack

```bash
cd backend

# Copy environment template and adjust if needed
cp .env.example .env

# Start all services (Postgres, Redis, MinIO, backend)
docker compose up -d

# Migrations run automatically via the `migrations` service.
# To run manually:
docker compose exec backend alembic upgrade head

# Seed initial data (creates default tenant, roles, permissions)
docker compose exec backend python -m app.scripts.seed
```

The API is available at **http://localhost:8000**. OpenAPI docs live at `/docs`.

### Running Locally (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Make sure Postgres and Redis are running (e.g. via docker compose up postgres redis)
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Running Tests

```bash
cd backend
pytest                         # all tests
pytest tests/unit              # unit only
pytest tests/api               # API / integration
pytest -x -q                   # stop on first failure
```

---

## 2. Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app factory, router mounting
│   ├── config.py                  # Pydantic Settings (env vars)
│   ├── core/                      # Shared infrastructure
│   │   ├── base_model.py          # Base, UUIDMixin, TenantMixin, SoftDeleteMixin, VersionMixin, …
│   │   ├── base_service.py        # BaseService[ModelT] with _get_by_id, _paginate, _soft_delete
│   │   ├── database.py            # AsyncSession factory, get_db, @transactional decorator
│   │   ├── security.py            # JWT, password hashing, PermissionChecker, get_current_user
│   │   ├── exceptions.py          # Domain exceptions → HTTP error mapping
│   │   ├── dependencies.py        # Shared FastAPI dependencies (get_public_tenant_id, …)
│   │   ├── pagination.py          # PaginatedResponse schema
│   │   ├── audit.py               # AuditService helper
│   │   ├── redis.py               # Redis client
│   │   ├── encryption.py          # Fernet encryption for secrets (SMTP passwords, API keys)
│   │   ├── image_upload.py        # S3/MinIO upload helpers
│   │   ├── locale_helpers.py      # Locale resolution utilities
│   │   └── url_utils.py           # Slug generation, URL helpers
│   ├── middleware/
│   │   └── feature_check.py       # require_feature / require_feature_public dependencies
│   ├── modules/                   # Domain modules (see §3)
│   │   ├── auth/
│   │   ├── tenants/
│   │   ├── content/
│   │   ├── company/
│   │   ├── catalog/
│   │   ├── parameters/
│   │   ├── leads/
│   │   ├── seo/
│   │   ├── assets/
│   │   ├── documents/
│   │   ├── notifications/
│   │   ├── telegram/
│   │   ├── dashboard/
│   │   ├── platform_dashboard/
│   │   ├── audit/
│   │   ├── export/
│   │   └── health/
│   └── services/                  # Cross-module application services
│       └── domain_provisioning.py
├── alembic/                       # Database migrations
│   ├── env.py
│   └── versions/
├── tests/
│   ├── unit/
│   ├── api/
│   ├── integration/
│   ├── security/
│   └── fixtures/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
└── requirements.txt
```

---

## 3. Module Anatomy

Each module follows a consistent layout:

```
modules/<name>/
├── __init__.py
├── models.py          # SQLAlchemy ORM models (tables, relationships, constraints)
├── schemas.py         # Pydantic v2 schemas (Create, Update, Response, List)
├── services/          # Business logic (or service.py for smaller modules)
│   ├── article_service.py
│   └── topic_service.py
├── routers/           # FastAPI routers (or router.py for smaller modules)
│   ├── article_router.py
│   └── topic_router.py
└── mappers.py         # Optional: model ↔ schema conversion helpers
```

**Models** use mixins from `app/core/base_model.py` — `UUIDMixin`, `TimestampMixin`,
`TenantMixin`, `SoftDeleteMixin`, `VersionMixin`, `SlugMixin`, `SEOMixin`,
`SortOrderMixin`, `PublishableMixin`.

**Services** extend `BaseService[ModelT]` from `app/core/base_service.py` and use the
`@transactional` decorator from `app/core/database.py`.

**Routers** use `PermissionChecker` from `app/core/security.py` for RBAC and
`require_feature` from `app/middleware/feature_check.py` for feature gating.

---

## 4. Key Patterns

### BaseService

```python
from app.core.base_service import BaseService

class ArticleService(BaseService[Article]):
    model = Article

    def _get_default_options(self) -> list:
        return [selectinload(Article.locales), selectinload(Article.topics)]

    async def get_by_id(self, article_id: UUID, tenant_id: UUID) -> Article:
        return await self._get_by_id(article_id, tenant_id)
```

Provides `_get_by_id`, `_soft_delete`, `_paginate`, `_list_all`, `_build_base_query` —
all with automatic tenant isolation and soft-delete filtering.

### TenantMixin & Multi-Tenancy

Every tenant-scoped model inherits `TenantMixin`, which adds a `tenant_id` column.
`BaseService` automatically filters by `tenant_id` in all queries.

### SoftDeleteMixin

Adds `deleted_at` column. Records are never hard-deleted — `BaseService._soft_delete`
sets `deleted_at = now()`. All default queries exclude soft-deleted rows.

### VersionMixin (Optimistic Locking)

Adds a `version` integer column. Call `entity.check_version(data.version)` before
updating — it raises `VersionConflictError` if stale, and auto-increments on success.

### @transactional

```python
from app.core.database import transactional

class MyService(BaseService[MyModel]):
    @transactional
    async def create(self, tenant_id: UUID, data: CreateSchema) -> MyModel:
        entity = MyModel(tenant_id=tenant_id, **data.model_dump())
        self.db.add(entity)
        await self.db.flush()
        return entity  # auto-committed
```

Commits on success, rolls back on exception. Works on both service methods (`self.db`)
and standalone functions with a `db` parameter.

### PermissionChecker (RBAC)

```python
from app.core.security import PermissionChecker

@router.post("/articles")
async def create_article(
    user: AdminUser = Depends(PermissionChecker("articles:create")),
):
    ...
```

Resolves the current user, verifies the JWT, and checks that the user's role grants
the required `resource:action` permission. Superusers bypass all checks.

### require_feature (Feature Gating)

```python
from app.middleware.feature_check import require_blog, require_blog_public

# Admin route — requires auth + feature flag
@router.get("/admin/articles", dependencies=[require_blog])
async def list_articles(...): ...

# Public route — no auth, uses tenant_id query param
@router.get("/public/articles", dependencies=[require_blog_public])
async def list_articles_public(...): ...
```

---

## 5. How to Add a New Module

1. **Create the directory** — `app/modules/<name>/`
2. **Define models** — `models.py` with appropriate mixins. Register the import in
   `alembic/env.py` so Alembic sees the new tables.
3. **Create a migration** — see §6.
4. **Add Pydantic schemas** — `schemas.py` with `Create`, `Update`, `Response`, `List`
   schemas.
5. **Implement services** — `services/<name>_service.py` extending `BaseService[Model]`.
   Decorate mutating methods with `@transactional`.
6. **Build routers** — `routers/<name>_router.py` (admin) and optionally a public
   router. Wire permissions with `PermissionChecker` and feature gates with
   `require_feature`.
7. **Mount routers** — add `app.include_router(...)` calls in `app/main.py`.
8. **Add permissions** — see §8.
9. **Add feature flag** — see §7 (if the module should be toggleable).
10. **Write tests** — `tests/unit/services/test_<name>_service.py` and
    `tests/api/test_<name>_api.py`.

---

## 6. How to Add a Migration

```bash
cd backend

# Auto-generate from model changes
alembic revision --autogenerate -m "short_description"

# Or create an empty migration for manual SQL
alembic revision -m "short_description"

# Apply
alembic upgrade head

# Rollback one step
alembic downgrade -1

# Check current version
alembic current
```

**Naming convention:** migrations are numbered sequentially — `001_`, `002_`, etc.
Check existing files in `alembic/versions/` for the next number.

After creating a migration, always:
- Verify the generated `upgrade()` and `downgrade()` functions.
- Run `alembic upgrade head` to confirm it applies cleanly.
- Run `alembic downgrade -1 && alembic upgrade head` to verify reversibility.

---

## 7. How to Add a Feature Flag

Feature flags control per-tenant access to entire modules.

1. **Add a migration** that inserts the new flag for all existing tenants:

```python
from alembic import op

def upgrade():
    op.execute("""
        INSERT INTO feature_flags (id, tenant_id, feature_name, enabled, created_at, updated_at)
        SELECT gen_random_uuid(), id, 'my_new_module', false, now(), now()
        FROM tenants
        WHERE NOT EXISTS (
            SELECT 1 FROM feature_flags
            WHERE feature_flags.tenant_id = tenants.id
              AND feature_flags.feature_name = 'my_new_module'
        )
    """)
```

2. **Register the feature** in `app/modules/tenants/models.py` →
   `AVAILABLE_FEATURES` dict:

```python
"my_new_module": {
    "title": "My New Module",
    "title_ru": "Мой новый модуль",
    "description": "Description of the module",
    "description_ru": "Описание модуля",
    "category": "content",  # content | company | platform | commerce
},
```

3. **Add dependency shortcuts** in `app/middleware/feature_check.py`:

```python
require_my_module = require_feature("my_new_module")
require_my_module_public = require_feature_public("my_new_module")
```

4. **Use in routers** via `dependencies=[require_my_module]` on admin routes and
   `dependencies=[require_my_module_public]` on public routes.

---

## 8. How to Add Permissions

Permissions follow the `resource:action` pattern (e.g., `articles:create`).

1. **Add entries to `DEFAULT_PERMISSIONS`** in `app/modules/auth/models.py`:

```python
DEFAULT_PERMISSIONS = [
    ...
    ("myresource:create", "Create My Resource", "myresource", "create"),
    ("myresource:read",   "Read My Resource",   "myresource", "read"),
    ("myresource:update", "Update My Resource",  "myresource", "update"),
    ("myresource:delete", "Delete My Resource",  "myresource", "delete"),
]
```

2. **Add entries to `DEFAULT_ROLES`** in the same file — assign the new permissions to
   relevant roles (`platform_owner`, `site_owner`, `content_manager`, etc.).

3. **Create a migration** that inserts the new permissions and assigns them to existing
   roles:

```python
from alembic import op

def upgrade():
    # Insert new permissions
    op.execute("""
        INSERT INTO permissions (id, code, name, resource, action, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'myresource:create', 'Create My Resource', 'myresource', 'create', now(), now()),
            (gen_random_uuid(), 'myresource:read',   'Read My Resource',   'myresource', 'read',   now(), now()),
            (gen_random_uuid(), 'myresource:update', 'Update My Resource', 'myresource', 'update', now(), now()),
            (gen_random_uuid(), 'myresource:delete', 'Delete My Resource', 'myresource', 'delete', now(), now())
        ON CONFLICT (code) DO NOTHING
    """)

    # Grant to platform_owner and site_owner roles
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('platform_owner', 'site_owner')
          AND p.resource = 'myresource'
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)
```

4. **Use in routers** with `PermissionChecker`:

```python
@router.post("/my-resource")
async def create_my_resource(
    user: AdminUser = Depends(PermissionChecker("myresource:create")),
):
    ...
```
