"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.modules.auth.models import AdminUser, Role
from app.modules.tenants.models import Tenant


# ============================================================================
# Test Settings
# ============================================================================


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing.

    Uses the same Docker PostgreSQL database (port 5433).
    """
    return Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5433/cms",
        jwt_secret_key="test-secret-key-for-testing-only",
        environment="development",
        debug=True,
        log_format="console",
    )


# ============================================================================
# Event Loop
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def db_engine(test_settings: Settings) -> AsyncGenerator[Any, None]:
    """Create test database engine.

    Uses existing database tables (created by migrations).
    Wraps tests in transactions that are rolled back.
    """
    engine = create_async_engine(
        str(test_settings.database_url),
        echo=False,
    )

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine: Any) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with automatic rollback."""
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


# ============================================================================
# Application Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def app(db_session: AsyncSession) -> FastAPI:
    """Create test FastAPI application."""
    application = create_app()

    # Override database dependency
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    application.dependency_overrides[get_db] = override_get_db

    return application


@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ============================================================================
# Test Data Constants
# ============================================================================

TEST_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000002")
TEST_ROLE_ID = UUID("00000000-0000-0000-0000-000000000003")
TEST_USER_EMAIL = "testuser@example.com"
TEST_USER_PASSWORD = "testpass123"


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    # Use unique identifiers per test to avoid conflicts
    unique_id = uuid4()
    tenant = Tenant(
        id=unique_id,
        slug=f"test-tenant-{unique_id.hex[:8]}",
        name="Test Company",
        domain=f"test-{unique_id.hex[:8]}.example.com",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture(scope="function")
async def test_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """Create a test admin role."""
    role = Role(
        id=uuid4(),  # Use random UUID to avoid conflicts
        tenant_id=test_tenant.id,
        name=f"admin-{uuid4().hex[:8]}",  # Unique name per test
        description="Administrator with full access",
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture(scope="function")
async def test_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_role: Role,
) -> AdminUser:
    """Create a test admin user."""
    unique_id = uuid4()
    user = AdminUser(
        id=unique_id,
        tenant_id=test_tenant.id,
        email=f"testuser-{unique_id.hex[:8]}@example.com",  # Unique email
        password_hash=hash_password(TEST_USER_PASSWORD),
        first_name="Test",
        last_name="User",
        role_id=test_role.id,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(scope="function")
async def test_superuser(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_role: Role,
) -> AdminUser:
    """Create a test superuser."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="superuser@example.com",
        password_hash=hash_password(TEST_USER_PASSWORD),
        first_name="Super",
        last_name="User",
        role_id=test_role.id,
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def auth_token(test_user: AdminUser, test_tenant: Tenant) -> str:
    """Generate a valid JWT token for test user."""
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_tenant.id),
        "email": test_user.email,
        "role": "admin",
        "permissions": ["*"],
        "is_superuser": test_user.is_superuser,
    }
    return create_access_token(token_data, expires_delta=timedelta(hours=1))


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Generate test authentication headers with valid JWT."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(
    app: FastAPI,
    auth_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated test HTTP client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=auth_headers,
    ) as ac:
        yield ac


# ============================================================================
# Superuser Authentication Fixtures
# ============================================================================


@pytest.fixture
def superuser_token(test_superuser: AdminUser, test_tenant: Tenant) -> str:
    """Generate a valid JWT token for test superuser."""
    token_data = {
        "sub": str(test_superuser.id),
        "tenant_id": str(test_tenant.id),
        "email": test_superuser.email,
        "role": "admin",
        "permissions": ["*"],
        "is_superuser": test_superuser.is_superuser,
    }
    return create_access_token(token_data, expires_delta=timedelta(hours=1))


@pytest.fixture
def superuser_headers(superuser_token: str) -> dict[str, str]:
    """Generate test authentication headers for superuser."""
    return {"Authorization": f"Bearer {superuser_token}"}


@pytest_asyncio.fixture(scope="function")
async def superuser_client(
    app: FastAPI,
    superuser_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated HTTP client for superuser."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=superuser_headers,
    ) as ac:
        yield ac


# ============================================================================
# Content Manager Role Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def content_manager_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """Create a content manager role."""
    role = Role(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="content_manager",
        description="Content manager with limited access",
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture(scope="function")
async def content_manager_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    content_manager_role: Role,
) -> AdminUser:
    """Create a test content manager user."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="content_manager@example.com",
        password_hash=hash_password(TEST_USER_PASSWORD),
        first_name="Content",
        last_name="Manager",
        role_id=content_manager_role.id,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
def content_manager_token(
    content_manager_user: AdminUser,
    test_tenant: Tenant,
) -> str:
    """Generate JWT token for content manager."""
    token_data = {
        "sub": str(content_manager_user.id),
        "tenant_id": str(test_tenant.id),
        "email": content_manager_user.email,
        "role": "content_manager",
        "permissions": ["articles:read", "articles:create", "articles:update"],
        "is_superuser": False,
    }
    return create_access_token(token_data, expires_delta=timedelta(hours=1))


@pytest_asyncio.fixture(scope="function")
async def content_manager_client(
    app: FastAPI,
    content_manager_token: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Create authenticated client for content manager."""
    headers = {"Authorization": f"Bearer {content_manager_token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers=headers,
    ) as ac:
        yield ac


# ============================================================================
# Simple Fixtures (No DB)
# ============================================================================


@pytest.fixture
def tenant_id() -> UUID:
    """Generate test tenant ID."""
    return TEST_TENANT_ID


@pytest.fixture
def random_tenant_id() -> UUID:
    """Generate random tenant ID."""
    return uuid4()


@pytest.fixture
def random_uuid() -> UUID:
    """Generate random UUID."""
    return uuid4()
