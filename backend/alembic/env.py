"""Alembic migration environment configuration."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.core.base_model import Base

# Import all models to ensure they're registered with Base.metadata
from app.modules.tenants.models import FeatureFlag, Tenant, TenantSettings  # noqa: F401
from app.modules.auth.models import AdminUser, AuditLog, Permission, Role, RolePermission  # noqa: F401
from app.modules.localization.models import LocaleConfig  # noqa: F401
from app.modules.company.models import (  # noqa: F401
    Service, ServiceLocale, PracticeArea, PracticeAreaLocale,
    Employee, EmployeeLocale, EmployeePracticeArea,
    Advantage, AdvantageLocale, Address, AddressLocale, Contact,
)
from app.modules.content.models import (  # noqa: F401
    Topic, TopicLocale, Article, ArticleLocale, ArticleTopic,
    FAQ, FAQLocale, Case, CaseLocale, CaseServiceLink, Review,
)
from app.modules.leads.models import InquiryForm, Inquiry  # noqa: F401
from app.modules.seo.models import SEORoute, Redirect  # noqa: F401
from app.modules.assets.models import FileAsset  # noqa: F401

# Alembic Config object
config = context.config

# Set database URL from settings
# Escape % characters for ConfigParser (it interprets % as interpolation)
database_url_str = str(settings.database_url).replace("%", "%%")
config.set_main_option("sqlalchemy.url", database_url_str)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # Create engine directly from settings to avoid alembic.ini placeholder
    connectable = create_async_engine(
        str(settings.database_url),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

