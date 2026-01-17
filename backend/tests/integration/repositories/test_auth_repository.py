"""Integration tests for auth repository operations."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.modules.auth.models import AdminUser, Role
from app.modules.tenants.models import Tenant


@pytest.mark.integration
class TestAuthRepository:
    """Integration tests for auth database operations."""

    @pytest.fixture
    async def tenant(self, db_session: AsyncSession) -> Tenant:
        """Create test tenant."""
        tenant = Tenant(
            id=uuid4(),
            slug=f"test-auth-tenant-{uuid4().hex[:8]}",
            name="Test Auth Company",
            domain=f"auth-{uuid4().hex[:8]}.example.com",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()
        return tenant

    @pytest.fixture
    async def role(self, db_session: AsyncSession, tenant: Tenant) -> Role:
        """Create test role."""
        role = Role(
            id=uuid4(),
            tenant_id=tenant.id,
            name="admin",
            description="Administrator role",
        )
        db_session.add(role)
        await db_session.flush()
        return role

    @pytest.fixture
    async def user(
        self, db_session: AsyncSession, tenant: Tenant, role: Role
    ) -> AdminUser:
        """Create test user."""
        user = AdminUser(
            id=uuid4(),
            tenant_id=tenant.id,
            email="testuser@example.com",
            password_hash=hash_password("test_password_123"),
            first_name="Test",
            last_name="User",
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        return user

    @pytest.mark.asyncio
    async def test_create_user(
        self, db_session: AsyncSession, tenant: Tenant, role: Role
    ) -> None:
        """Test creating user in database."""
        user = AdminUser(
            tenant_id=tenant.id,
            email="new@example.com",
            password_hash=hash_password("secure_password"),
            first_name="New",
            last_name="User",
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Verify
        result = await db_session.execute(
            select(AdminUser).where(AdminUser.id == user.id)
        )
        saved = result.scalar_one()

        assert saved.email == "new@example.com"
        assert saved.first_name == "New"
        assert saved.is_active is True
        assert saved.version == 1

    @pytest.mark.asyncio
    async def test_user_password_hash(
        self, db_session: AsyncSession, tenant: Tenant, role: Role
    ) -> None:
        """Test password is properly hashed."""
        plain_password = "my_secret_password"
        user = AdminUser(
            tenant_id=tenant.id,
            email="password@example.com",
            password_hash=hash_password(plain_password),
            first_name="Password",
            last_name="Test",
            role_id=role.id,
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        result = await db_session.execute(
            select(AdminUser).where(AdminUser.id == user.id)
        )
        saved = result.scalar_one()

        # Password should not be stored in plain text
        assert saved.password_hash != plain_password
        # But should verify correctly
        assert verify_password(plain_password, saved.password_hash)

    @pytest.mark.asyncio
    async def test_user_soft_delete(
        self, db_session: AsyncSession, user: AdminUser
    ) -> None:
        """Test soft delete sets deleted_at."""
        assert user.deleted_at is None

        user.soft_delete()
        await db_session.flush()

        result = await db_session.execute(
            select(AdminUser).where(AdminUser.id == user.id)
        )
        saved = result.scalar_one()

        assert saved.deleted_at is not None

    @pytest.mark.asyncio
    async def test_query_users_by_tenant(
        self, db_session: AsyncSession, tenant: Tenant, role: Role
    ) -> None:
        """Test querying users by tenant_id."""
        # Create multiple users
        for i in range(3):
            user = AdminUser(
                tenant_id=tenant.id,
                email=f"user{i}@example.com",
                password_hash=hash_password("password"),
                first_name=f"User{i}",
                last_name="Test",
                role_id=role.id,
                is_active=True,
            )
            db_session.add(user)
        await db_session.flush()

        # Query
        result = await db_session.execute(
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant.id)
            .where(AdminUser.deleted_at.is_(None))
        )
        users = result.scalars().all()

        assert len(users) >= 3

    @pytest.mark.asyncio
    async def test_query_users_by_email(
        self, db_session: AsyncSession, user: AdminUser
    ) -> None:
        """Test finding user by email."""
        result = await db_session.execute(
            select(AdminUser)
            .where(AdminUser.tenant_id == user.tenant_id)
            .where(AdminUser.email == user.email)
            .where(AdminUser.deleted_at.is_(None))
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_query_active_users_only(
        self, db_session: AsyncSession, tenant: Tenant, role: Role
    ) -> None:
        """Test querying only active users."""
        # Create active user
        active = AdminUser(
            tenant_id=tenant.id,
            email="active@example.com",
            password_hash=hash_password("password"),
            first_name="Active",
            last_name="User",
            role_id=role.id,
            is_active=True,
        )
        db_session.add(active)

        # Create inactive user
        inactive = AdminUser(
            tenant_id=tenant.id,
            email="inactive@example.com",
            password_hash=hash_password("password"),
            first_name="Inactive",
            last_name="User",
            role_id=role.id,
            is_active=False,
        )
        db_session.add(inactive)
        await db_session.flush()

        # Query active only
        result = await db_session.execute(
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant.id)
            .where(AdminUser.is_active.is_(True))
            .where(AdminUser.deleted_at.is_(None))
        )
        users = result.scalars().all()

        assert all(u.is_active for u in users)

    @pytest.mark.asyncio
    async def test_role_creation(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test creating role in database."""
        role = Role(
            tenant_id=tenant.id,
            name="content_manager",
            description="Content management role",
        )
        db_session.add(role)
        await db_session.flush()

        result = await db_session.execute(
            select(Role).where(Role.id == role.id)
        )
        saved = result.scalar_one()

        assert saved.name == "content_manager"
        assert saved.description == "Content management role"

