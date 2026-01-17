# Corporate CMS Engine - Code Standards

This document defines coding standards and architectural patterns for the Corporate CMS Engine backend.

## Quick Reference

```bash
# Development
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload

# Testing
pytest
pytest --cov=app

# Linting
ruff check .
ruff format .
mypy app/
```

## Project Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/               # Migration files
│   └── env.py                  # Alembic config
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Pydantic settings
│   ├── core/                   # Shared infrastructure
│   │   ├── base_model.py       # SQLAlchemy mixins
│   │   ├── database.py         # DB session management
│   │   ├── dependencies.py     # Common FastAPI deps
│   │   ├── exceptions.py       # Exception hierarchy
│   │   ├── logging.py          # Structured logging
│   │   └── security.py         # JWT, RBAC
│   ├── middleware/             # Custom middleware
│   └── modules/                # Feature modules
│       ├── auth/               # Authentication
│       ├── tenants/            # Multi-tenancy
│       ├── company/            # Services, employees
│       ├── content/            # Articles, FAQ
│       ├── leads/              # Inquiries
│       ├── seo/                # SEO management
│       └── assets/             # File uploads
└── tests/
    ├── conftest.py             # Pytest fixtures
    └── test_*.py               # Test files
```

## Architectural Patterns

### 1. Module Structure

Each module follows a consistent structure:

```
modules/example/
├── __init__.py
├── models.py       # SQLAlchemy models
├── schemas.py      # Pydantic schemas
├── service.py      # Business logic (Service Layer)
├── router.py       # FastAPI routes
└── dependencies.py # Module-specific deps (optional)
```

### 2. Service Layer Pattern

Business logic lives in services, not routes:

```python
# ✅ Good - Service handles logic
class ArticleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    @transactional
    async def create(self, tenant_id: UUID, data: ArticleCreate) -> Article:
        # Validation, business rules, etc.
        article = Article(tenant_id=tenant_id, **data.model_dump())
        self.db.add(article)
        return article

# ✅ Good - Route delegates to service
@router.post("/articles")
async def create_article(
    data: ArticleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    service = ArticleService(db)
    article = await service.create(tenant_id, data)
    return ArticleResponse.model_validate(article)

# ❌ Bad - Business logic in route
@router.post("/articles")
async def create_article(data: ArticleCreate, db: AsyncSession = Depends(get_db)):
    article = Article(**data.model_dump())
    db.add(article)
    await db.commit()
    return article
```

### 3. Dependency Injection

Use FastAPI's `Depends()` for all dependencies:

```python
from app.core.dependencies import DBSession, Pagination, Locale
from app.core.security import PermissionChecker, get_current_tenant_id

@router.get("/articles")
async def list_articles(
    pagination: Pagination,               # Pagination params
    locale: Locale,                       # Locale param
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: DBSession,                        # Database session
) -> ArticleListResponse:
    ...

# Permission checking
@router.post("/articles", dependencies=[Depends(PermissionChecker("articles:create"))])
async def create_article(...):
    ...
```

### 4. Error Handling (RFC 7807)

Always use exception classes from `core/exceptions.py`:

```python
from app.core.exceptions import NotFoundError, AlreadyExistsError, ValidationError

# ✅ Good
if not article:
    raise NotFoundError("Article", article_id)

if existing:
    raise AlreadyExistsError("Article", "slug", slug)

# ❌ Bad - Generic HTTPException
raise HTTPException(status_code=404, detail="Not found")
```

### 5. Database Models

Always use mixins for consistency:

```python
from app.core.base_model import (
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, 
    TenantMixin, VersionMixin, SlugMixin
)

class Article(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, 
              TenantMixin, VersionMixin, SlugMixin):
    """Article model with all standard fields."""
    
    __tablename__ = "articles"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # ...
    
    __table_args__ = (
        Index("ix_articles_tenant_slug", "tenant_id", "slug", unique=True),
        CheckConstraint("char_length(title) >= 1", name="ck_articles_title"),
    )
```

**Required Mixins:**
- `UUIDMixin` - UUID primary key
- `TimestampMixin` - created_at, updated_at
- `SoftDeleteMixin` - deleted_at (CRITICAL for SEO!)
- `TenantMixin` - tenant_id for multi-tenancy
- `VersionMixin` - optimistic locking

### 6. Soft Delete

**CRITICAL: Never hard-delete content!** Use soft delete to preserve URLs:

```python
# ✅ Good - Soft delete
async def delete(self, article_id: UUID) -> None:
    article = await self.get_by_id(article_id)
    article.soft_delete()  # Sets deleted_at = now()
    await self.db.commit()

# ✅ Good - Filter out deleted records
stmt = select(Article).where(Article.deleted_at.is_(None))

# ❌ Bad - Hard delete breaks SEO!
await db.execute(delete(Article).where(Article.id == article_id))
```

### 7. Optimistic Locking

Always require version for updates:

```python
class ArticleUpdate(BaseModel):
    title: str | None = None
    version: int = Field(..., description="Current version for optimistic locking")

async def update(self, article_id: UUID, data: ArticleUpdate) -> Article:
    article = await self.get_by_id(article_id)
    
    if article.version != data.version:
        raise VersionConflictError("Article", article.version, data.version)
    
    # Update fields...
    # version auto-increments via event listener
```

### 8. Localization (Translation Tables)

Use separate locale tables, not JSONB:

```python
# Main entity
class Article(Base, UUIDMixin, ...):
    __tablename__ = "articles"
    tenant_id: Mapped[UUID] = ...
    is_published: Mapped[bool] = ...
    # No title/content here!
    
    locales: Mapped[list["ArticleLocale"]] = relationship(...)

# Locale table
class ArticleLocale(Base, UUIDMixin, TimestampMixin, SlugMixin):
    __tablename__ = "article_locales"
    
    article_id: Mapped[UUID] = mapped_column(ForeignKey("articles.id"))
    locale: Mapped[str] = mapped_column(String(5))  # 'ru', 'en'
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    
    __table_args__ = (
        UniqueConstraint("article_id", "locale", name="uq_article_locales"),
        Index("ix_article_locales_slug", "locale", "slug"),
    )
```

### 9. Logging

Use structured JSON logging:

```python
from app.core.logging import get_logger, bind_context

logger = get_logger(__name__)

# Good - Structured with context
logger.info("article_created", article_id=str(article.id), title=article.title)

# Context binding for request
bind_context(request_id=request_id, tenant_id=str(tenant_id))
logger.info("processing_request")  # Automatically includes request_id, tenant_id
```

### 10. API Versioning

URL-based versioning under `/api/v1/`:

```python
# Public API (no auth)
GET  /api/v1/public/articles
GET  /api/v1/public/articles/{slug}

# Admin API (auth required)
GET  /api/v1/admin/articles
POST /api/v1/admin/articles
```

### 11. Response Schemas

Always use explicit response schemas:

```python
class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    title: str
    slug: str
    # ...

class ArticleListResponse(BaseModel):
    items: list[ArticleResponse]
    total: int
    page: int
    page_size: int
```

### 12. Transactional Operations

Use the `@transactional` decorator:

```python
from app.core.database import transactional

class ArticleService:
    @transactional
    async def create(self, data: ArticleCreate) -> Article:
        article = Article(**data.model_dump())
        self.db.add(article)
        # Auto-commits on success, rollbacks on exception
        return article
```

## Database Conventions

### Naming

- Tables: `snake_case`, plural (`articles`, `admin_users`)
- Columns: `snake_case` (`created_at`, `tenant_id`)
- Indexes: `ix_{table}_{columns}` (`ix_articles_tenant_slug`)
- Constraints: `ck_{table}_{description}` (`ck_articles_title_min`)
- Foreign keys: `fk_{table}_{column}_{ref_table}` (auto-generated)

### Required Indexes

Always add indexes for:
- `tenant_id` (all tenant tables)
- `deleted_at` (partial index where NULL)
- `slug` + `locale` (unique per tenant)
- `is_published` (partial index where true)
- Foreign keys

```python
__table_args__ = (
    Index("ix_articles_tenant", "tenant_id"),
    Index("ix_articles_active", "tenant_id", "is_published", 
          postgresql_where="deleted_at IS NULL AND is_published = true"),
    Index("ix_articles_slug", "tenant_id", "locale", "slug", unique=True),
)
```

### Constraints

Always add check constraints for data integrity:

```python
__table_args__ = (
    CheckConstraint("char_length(title) >= 1", name="ck_articles_title_min"),
    CheckConstraint("char_length(slug) >= 2", name="ck_articles_slug_min"),
    CheckConstraint("email ~* '^[^@]+@[^@]+\\.[^@]+$'", name="ck_users_email"),
)
```

## Testing

### Test Structure

```python
# tests/test_articles.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_article(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/admin/articles",
        json={"title": "Test", "content": "..."},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test"

@pytest.mark.asyncio  
async def test_create_article_unauthorized(client: AsyncClient):
    response = await client.post("/api/v1/admin/articles", json={})
    assert response.status_code == 401
```

### Fixtures

Use fixtures from `conftest.py`:

```python
@pytest.fixture
async def article(db_session, tenant_id):
    article = Article(tenant_id=tenant_id, title="Test")
    db_session.add(article)
    await db_session.commit()
    return article
```

## Code Style

### Type Hints

Always use type hints:

```python
async def get_by_id(self, article_id: UUID) -> Article:
    ...

async def list_articles(
    self,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Article], int]:
    ...
```

### Docstrings

Document public methods:

```python
async def create(self, tenant_id: UUID, data: ArticleCreate) -> Article:
    """Create a new article.
    
    Args:
        tenant_id: Tenant to create article for
        data: Article creation data
        
    Returns:
        Created article instance
        
    Raises:
        AlreadyExistsError: If slug already exists
    """
```

### Import Order

1. Standard library
2. Third-party packages
3. Local modules

```python
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.articles.schemas import ArticleCreate
```

## Environment Variables

Required variables (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cms

# JWT
JWT_SECRET_KEY=your-secret-key-min-32-chars

# Redis  
REDIS_URL=redis://localhost:6379/0

# S3 (Selectel)
S3_ENDPOINT_URL=https://s3.storage.selcloud.ru
S3_ACCESS_KEY=your-key
S3_SECRET_KEY=your-secret
S3_BUCKET_NAME=cms-assets
```

## Performance Guidelines

1. **Use selectinload for relationships** - avoid N+1 queries
2. **Add database indexes** - for all filtered/sorted columns
3. **Use partial indexes** - for soft-deleted and published content
4. **Cache public endpoints** - with Cache-Control headers
5. **Paginate all list endpoints** - max 100 items per page

## Security Checklist

- [ ] JWT tokens with short expiry (30 min access, 7 days refresh)
- [ ] Password hashing with bcrypt
- [ ] RBAC with permission checks on all admin routes
- [ ] Rate limiting on login and public inquiry endpoints
- [ ] Input validation with Pydantic
- [ ] SQL injection prevention (SQLAlchemy ORM)
- [ ] CORS configured for allowed origins only
- [ ] Audit logging for all mutations

