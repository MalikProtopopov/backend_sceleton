# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **AI Avatar Platform** - a modular monolith SaaS application for creating RAG-powered AI consultants. Built with FastAPI, it uses PostgreSQL with pgvector for vector storage, Redis for caching and task queues, and MinIO (S3-compatible) for document storage. The platform supports multi-tenant project management, Telegram bot integration, and token-based billing.

## Architecture

**Modular Monolith** with clear domain boundaries. Each module is self-contained but shares the same database and process.

```
backend/
   app/
      api/                  # Shared API components (health, schemas)
      core/                 # Shared infrastructure (database, redis, events, security)
      modules/              # Domain modules (auth, projects, avatars, chat, etc.)
      config.py             # Pydantic Settings
      main.py               # FastAPI application factory
   alembic/                 # Database migrations
   tests/
      unit/                 # Unit tests
      integration/          # Integration tests with API client
```

### Module Structure

Each domain module follows this pattern:

```
modules/{module}/
   __init__.py
   service.py              # Business logic (NOT versioned)
   api/
      __init__.py
      v1/                   # API version 1
         __init__.py        # Router aggregation
         routes/            # HTTP endpoints
            __init__.py
            public.py       # Public endpoints (no auth)
            admin.py        # Admin-only endpoints
            {feature}.py    # Feature-specific endpoints
         schemas/           # Pydantic request/response schemas
            __init__.py
            requests.py
            responses.py
   domain/
      __init__.py
      models.py             # SQLAlchemy models
      events.py             # Domain events (dataclasses)
      exceptions.py         # Module-specific exceptions
```

### Core Modules

1. **auth** - User authentication, JWT tokens, roles (SAAS_ADMIN, OWNER, MANAGER, etc.)
2. **projects** - Multi-tenant projects with team members and secrets
3. **avatars** - AI avatar configuration (prompts, LLM settings, RAG params)
4. **documents** - Document upload, parsing, chunking, embedding generation
5. **chat** - RAG-based chat with avatars, conversation history
6. **billing** - Token usage tracking and limits
7. **analytics** - Usage statistics and audit logs
8. **integrations/telegram** - Telegram bot integration per project
9. **notifications** - Telegram notifications for platform events
10. **end_users** - B2C end-user management (chat users)
11. **plan_requests** - Tariff upgrade requests
12. **platform_config** - Global platform settings (API keys, etc.)

## Development Commands

All commands from project root:

```bash
# === Installation ===
make install              # Install dependencies via Poetry

# === Development (Local) ===
make dev                  # Start FastAPI with hot reload (port 8000)
make worker               # Start TaskIQ worker for background tasks

# === Docker (Development) ===
make up                   # Start all services (postgres, redis, minio, backend, worker)
make down                 # Stop all services
make logs                 # View all logs
make logs-backend         # View backend logs only

# === Docker (Production) ===
make up-prod              # Start production stack (requires .env.prod)
make down-prod            # Stop production services

# === Database ===
make migrate              # Run Alembic migrations (local)
make migrate-docker       # Run migrations in Docker
make makemigrations MSG="description"  # Create new migration

# === Testing ===
make test                 # Run all tests
make test-unit            # Run unit tests only
make test-int             # Run integration tests only
make test-cov             # Run with coverage report

# === Code Quality ===
make lint                 # Run ruff + mypy
make format               # Run black + ruff --fix
make clean                # Remove __pycache__, .pytest_cache, etc.
```

### Running Individual Tests

```bash
cd backend
poetry run pytest tests/unit/test_auth.py -v
poetry run pytest tests/integration/test_chat_api.py::test_send_message -v
```

## Key Architectural Patterns

### 1. Dependency Injection (Standard FastAPI)

No DI framework - uses standard FastAPI `Depends()`:

```python
# In routes
def get_auth_service(session: AsyncSession = Depends(get_async_session)) -> AuthService:
    return AuthService(session)

@router.post("/login")
async def login(
    data: UserLogin,
    service: AuthService = Depends(get_auth_service),
):
    return await service.authenticate(...)
```

Type aliases for common dependencies in `core/dependencies.py`:
```python
DbSession = Annotated[AsyncSession, Depends(get_async_session)]
CurrentToken = Annotated[TokenPayload, Depends(get_current_token)]
```

### 2. Service Layer Pattern

Business logic lives in `service.py` (not versioned):

```python
class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def register_user(self, data: UserCreate) -> User:
        # Business logic, validation, event publishing
        await EventBus.publish(UserCreated(...))
        return user
```

Services:
- Accept `AsyncSession` in constructor
- Handle transactions (commit/rollback)
- Publish domain events
- Raise domain exceptions

### 3. Event-Driven Communication

In-process event bus for module decoupling (`core/events.py`):

```python
# Define event in module's domain/events.py
@dataclass
class UserCreated(DomainEvent):
    user_id: str
    email: str
    role: UserRole

# Publish event from service
await EventBus.publish(UserCreated(user_id=user.id, email=user.email, role=user.role))

# Subscribe in another module's handlers.py
@event_handler("UserCreated")
async def on_user_created(event: UserCreated):
    # Initialize token budget, send notification, etc.
```

Register handlers in `main.py`:
```python
def _register_event_handlers():
    from app.modules.billing import handlers
    handlers.register_handlers()
```

### 4. Background Tasks with TaskIQ

Async task queue for long-running operations:

```python
# Define task in module's tasks.py
@broker.task(retry_on_error=True, max_retries=3)
async def process_document(document_id: str) -> dict:
    async with get_session_context() as session:
        # Processing logic
        pass

# Enqueue task
await process_document.kiq(document_id)
```

Tasks are registered in `core/taskiq_broker.py` via imports.

### 5. SQLAlchemy Models

Base classes in `core/base_model.py`:

```python
class User(SoftDeleteModel):  # UUID + timestamps + soft delete
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
```

Mixins available:
- `UUIDMixin` - UUID primary key
- `TimestampMixin` - created_at, updated_at
- `SoftDeleteMixin` - deleted_at, is_deleted, soft_delete()
- `BaseModel` = Base + UUID + Timestamps
- `SoftDeleteModel` = BaseModel + SoftDelete

### 6. Error Handling

Standardized error responses via `AppException` hierarchy:

```python
# Raise in service
from app.modules.auth.domain.exceptions import UserNotFoundError
raise UserNotFoundError(user_id=user_id)

# Automatic JSON response
{
    "error": {
        "code": "NOT_FOUND",
        "message": "User not found",
        "field": null,
        "details": {"user_id": "..."}
    }
}
```

Exception classes in `core/exceptions.py`:
- `NotFoundError` (404)
- `ValidationError` (422)
- `AuthenticationError` (401)
- `AuthorizationError` (403)
- `ConflictError` (409)
- `RateLimitError` (429)
- `ExternalServiceError` (502)

### 7. RAG Pipeline

Document processing flow:

```
Upload → S3 Storage → TaskIQ Task → Parse → Chunk → Embed → pgvector
```

Components in `modules/documents/`:
- `processor.py` - DocumentParser, TextChunker, EmbeddingService
- `tasks.py` - Background processing tasks

Retrieval in `modules/chat/rag/`:
- `retriever.py` - VectorRetriever with pgvector similarity search
- `agent.py` - LangChain/LangGraph agent for RAG
- `prompts.py` - System prompts for avatars

### 8. Configuration

Pydantic Settings in `config.py`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    
    database_url: str = "postgresql+asyncpg://..."
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
```

Access via `from app.config import settings`.

## Testing Patterns

### Unit Tests

```python
# tests/unit/test_auth.py
import pytest
from app.modules.auth.service import AuthService

@pytest.fixture
def auth_service(session):
    return AuthService(session)

async def test_register_user(auth_service):
    user = await auth_service.register_user(UserCreate(...))
    assert user.email == "test@example.com"
```

### Integration Tests

```python
# tests/integration/test_auth_api.py
from httpx import AsyncClient

async def test_login(client: AsyncClient):
    response = await client.post("/api/v1/auth/login", json={
        "email": "user@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## Common Gotchas & Refactoring Targets

### 1. Database Session Management

**Problem**: Not using context manager, session leaks
```python
# Bad
session = AsyncSessionLocal()
user = await session.get(User, id)
# Missing close!

# Good
async with get_session_context() as session:
    user = await session.get(User, id)
```

### 2. Circular Imports

**Problem**: Modules importing each other directly
```python
# Bad - in auth/service.py
from app.modules.billing.service import TokenService

# Good - import at function level or use events
async def register_user(self, data):
    await EventBus.publish(UserCreated(...))  # Billing handles event
```

### 3. Transaction Boundaries

**Problem**: Committing multiple times or forgetting commit
```python
# Bad
await session.commit()  # First commit
# ... more operations
await session.commit()  # Second commit - might leave partial state

# Good - single commit at end
user = User(...)
session.add(user)
token = RefreshToken(user_id=user.id, ...)
session.add(token)
await session.commit()  # Single atomic commit
```

### 4. Event Handler Registration

**Problem**: Handlers not registered on startup
```python
# handlers.py must have register_handlers() function
def register_handlers():
    """Register all event handlers for this module."""
    pass  # @event_handler decorators run on import
```

### 5. Missing Soft Delete Filters

**Problem**: Queries returning deleted records
```python
# Bad
stmt = select(User).where(User.id == user_id)

# Good
stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
```

### 6. N+1 Query Problem

**Problem**: Loading related objects in loops
```python
# Bad
users = await session.execute(select(User))
for user in users:
    projects = user.projects  # N+1!

# Good - use joinedload
from sqlalchemy.orm import joinedload
stmt = select(User).options(joinedload(User.projects))
```

### 7. Blocking Operations in Async Code

**Problem**: Using sync libraries in async context
```python
# Bad
model = CrossEncoder("model")
scores = model.predict(pairs)  # Blocking!

# Good
import asyncio
loop = asyncio.get_event_loop()
scores = await loop.run_in_executor(None, lambda: model.predict(pairs))
```

### 8. Missing Error Codes

**Problem**: Generic HTTPException without error codes
```python
# Bad
raise HTTPException(status_code=404, detail="Not found")

# Good
raise HTTPException(
    status_code=404,
    detail=create_error_response(
        code=ErrorCode.USER_NOT_FOUND,
        message="User not found",
    )
)
```

### 9. Hardcoded Configuration

**Problem**: Magic numbers and strings in code
```python
# Bad
if len(chunks) > 100:
    ...

# Good - use settings
if len(chunks) > settings.rag_top_k:
    ...
```

### 10. Missing Type Hints

**Problem**: Functions without type annotations
```python
# Bad
async def get_user(user_id):
    ...

# Good
async def get_user(user_id: str) -> User | None:
    ...
```

## Docker Services

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| PostgreSQL | avatar_postgres | 5432 | Database with pgvector |
| Redis | avatar_redis | 6379 | Cache + TaskIQ broker |
| MinIO | avatar_minio | 9000/9001 | S3-compatible storage |
| Backend | avatar_backend | 8000 | FastAPI application |
| Worker | avatar_worker | - | TaskIQ background worker |

## Environment Variables

Key variables in `.env.dev` / `.env.prod`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://avatar_user:avatar_pass@postgres:5432/avatar_db

# Redis
REDIS_URL=redis://redis:6379/0
TASKIQ_BROKER_URL=redis://redis:6379/1

# S3/MinIO
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=avatar-documents

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# JWT
JWT_SECRET_KEY=change-me-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# App
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]
```

## Adding a New Module

1. Create module structure:
```bash
mkdir -p app/modules/newmodule/{api/v1/{routes,schemas},domain}
touch app/modules/newmodule/__init__.py
touch app/modules/newmodule/service.py
touch app/modules/newmodule/domain/{__init__,models,events,exceptions}.py
touch app/modules/newmodule/api/__init__.py
touch app/modules/newmodule/api/v1/{__init__,routes/__init__,schemas/__init__}.py
```

2. Define models in `domain/models.py`
3. Create migration: `make makemigrations MSG="add newmodule tables"`
4. Implement service in `service.py`
5. Create routes in `api/v1/routes/`
6. Register router in `main.py`:
```python
from app.modules.newmodule.api.v1 import router as newmodule_router
app.include_router(newmodule_router, prefix=f"{settings.api_v1_prefix}/newmodule")
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

All endpoints use Russian descriptions for client-facing documentation.

## Naming Conventions

### Files
- Models: `models.py` in `domain/` directory
- Schemas: `requests.py`, `responses.py` (separated by direction)
- Routes: `public.py` (no auth), `admin.py` (admin only), `{feature}.py`
- Tests: `test_{module}.py` for unit, `test_{module}_api.py` for integration

### Variables and Fields
- **Metadata fields**: Use consistent suffix `_metadata` (e.g., `session_metadata`, `chunk_metadata`)
- **Config fields**: Use suffix `_config` or `_settings` (e.g., `extra_config`, `extra_settings`)
- **Timestamp fields**: Use suffixes `_at` (e.g., `created_at`, `last_seen_at`, `blocked_at`)
- **Count fields**: Use suffix `_count` (e.g., `messages_count`, `documents_count`)
- **ID fields**: Use suffix `_id` (e.g., `user_id`, `project_id`)

### Types
- **Enums**: PascalCase with descriptive names (e.g., `UserRole`, `DocumentStatus`)
- **TypedDict**: PascalCase matching field purpose (e.g., `SessionMetadata`, `AvatarExtraConfig`)
- **Exception classes**: PascalCase with `Error` suffix (e.g., `UserNotFoundError`)

### JSONB Field Naming
Preferred patterns for JSONB columns:
- `{entity}_metadata` - Entity-specific metadata (e.g., `doc_metadata`, `chunk_metadata`)
- `extra_config` / `extra_settings` - Additional configuration
- `consent_flags` - Boolean flags collection
- `raw_profile` - Raw external data

### API Endpoints
- Use kebab-case for URL paths (e.g., `/api/v1/plan-requests`)
- Use snake_case for query parameters
- Use camelCase for JSON response fields (optional, currently using snake_case)

## API Versioning Strategy

### Current Versioning

The API uses URL path versioning: `/api/v1/...`

All routers are registered with version prefix in `main.py`:
```python
app.include_router(auth_router, prefix=f"{settings.api_v1_prefix}/auth")
```

### When to Create a New Version

Create `/api/v2/` when making **breaking changes**:
- Removing or renaming endpoints
- Changing request/response schema structure
- Modifying authentication requirements
- Changing HTTP methods for existing endpoints

**Non-breaking changes** (keep in v1):
- Adding new optional fields
- Adding new endpoints
- Adding new query parameters
- Relaxing validation rules

### Deprecation Process

1. **Mark deprecated** - Add `Deprecated` header and update docstring:
```python
@router.get("/old-endpoint", deprecated=True)
async def old_endpoint():
    """DEPRECATED: Use /new-endpoint instead. Will be removed in v2."""
```

2. **Add deprecation warning** - Log usage:
```python
logger.warning("Deprecated endpoint called", extra={"endpoint": "/old-endpoint"})
```

3. **Document timeline** - Update CHANGELOG with removal date

4. **Remove in next major version** - After sufficient deprecation period (3+ months)

### Version Coexistence

When v2 is created:
```python
# main.py
from app.modules.auth.api.v1 import router as auth_v1_router
from app.modules.auth.api.v2 import router as auth_v2_router

app.include_router(auth_v1_router, prefix="/api/v1/auth")
app.include_router(auth_v2_router, prefix="/api/v2/auth")
```

Services remain unversioned - only API layer is versioned.

## Code Style

- **Line length**: 100 characters
- **Formatter**: Black
- **Linter**: Ruff
- **Type checker**: MyPy
- **Async mode**: Always use async/await for DB and HTTP operations
- **Docstrings**: Google style with Russian descriptions for API endpoints
