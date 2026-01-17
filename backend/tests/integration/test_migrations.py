"""Integration tests for Alembic migrations."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
class TestMigrations:
    """Tests for database migrations."""

    @pytest.mark.asyncio
    async def test_tenants_table_exists(self, db_session: AsyncSession) -> None:
        """Verify tenants table was created by migrations."""
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tenants')"
            )
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_admin_users_table_exists(self, db_session: AsyncSession) -> None:
        """Verify admin_users table was created."""
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'admin_users')"
            )
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_articles_table_exists(self, db_session: AsyncSession) -> None:
        """Verify articles table was created."""
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'articles')"
            )
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_reviews_table_exists(self, db_session: AsyncSession) -> None:
        """Verify reviews table was created."""
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'reviews')"
            )
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_services_table_exists(self, db_session: AsyncSession) -> None:
        """Verify services table was created."""
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'services')"
            )
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_inquiries_table_exists(self, db_session: AsyncSession) -> None:
        """Verify inquiries table was created."""
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'inquiries')"
            )
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_seo_routes_table_exists(self, db_session: AsyncSession) -> None:
        """Verify seo_routes table was created."""
        result = await db_session.execute(
            text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'seo_routes')"
            )
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_tenants_has_required_columns(
        self, db_session: AsyncSession
    ) -> None:
        """Verify tenants table has required columns."""
        result = await db_session.execute(
            text(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tenants'
                """
            )
        )
        columns = {row[0] for row in result.fetchall()}

        required = {"id", "slug", "name", "domain", "is_active", "created_at"}
        assert required.issubset(columns)

    @pytest.mark.asyncio
    async def test_admin_users_has_required_columns(
        self, db_session: AsyncSession
    ) -> None:
        """Verify admin_users table has required columns."""
        result = await db_session.execute(
            text(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'admin_users'
                """
            )
        )
        columns = {row[0] for row in result.fetchall()}

        required = {
            "id",
            "tenant_id",
            "email",
            "password_hash",
            "is_active",
            "created_at",
        }
        assert required.issubset(columns)

    @pytest.mark.asyncio
    async def test_articles_has_soft_delete_column(
        self, db_session: AsyncSession
    ) -> None:
        """Verify articles table has deleted_at column for soft delete."""
        result = await db_session.execute(
            text(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'articles' AND column_name = 'deleted_at'
                """
            )
        )
        column = result.fetchone()
        assert column is not None

    @pytest.mark.asyncio
    async def test_articles_has_version_column(
        self, db_session: AsyncSession
    ) -> None:
        """Verify articles table has version column for optimistic locking."""
        result = await db_session.execute(
            text(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'articles' AND column_name = 'version'
                """
            )
        )
        column = result.fetchone()
        assert column is not None

    @pytest.mark.asyncio
    async def test_tenant_id_indexes_exist(self, db_session: AsyncSession) -> None:
        """Verify tenant_id columns are indexed."""
        result = await db_session.execute(
            text(
                """
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'articles' 
                AND indexdef LIKE '%tenant_id%'
                """
            )
        )
        indexes = result.fetchall()
        assert len(indexes) > 0

