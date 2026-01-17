"""Database configuration and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session

from app.config import settings
from app.core.base_model import Base

# Create async engine
engine = create_async_engine(
    str(settings.database_url),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.database_echo,
    pool_pre_ping=True,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside of FastAPI.

    Usage:
        async with get_db_context() as db:
            result = await db.execute(query)
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Type variables for transactional decorator
P = ParamSpec("P")
R = TypeVar("R")


def transactional(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator for automatic transaction management.

    Commits on success, rolls back on exception.
    Works with both standalone functions (with db arg) and service methods (with self.db).

    Usage:
        # Standalone function
        @transactional
        async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
            user = User(**user_data.model_dump())
            db.add(user)
            return user  # Auto-committed

        # Service method
        class UserService:
            def __init__(self, db: AsyncSession):
                self.db = db

            @transactional
            async def create(self, data: UserCreate) -> User:
                user = User(**data.model_dump())
                self.db.add(user)
                return user  # Auto-committed
    """

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # Find db session in args, kwargs, or self.db
        db: AsyncSession | None = None

        # Check for AsyncSession in args
        for arg in args:
            if isinstance(arg, AsyncSession):
                db = arg
                break

        # Check kwargs
        if db is None:
            db = kwargs.get("db")

        # Check for self.db (service classes)
        if db is None and args:
            first_arg = args[0]
            if hasattr(first_arg, "db") and isinstance(first_arg.db, AsyncSession):
                db = first_arg.db

        if db is None:
            raise ValueError("No AsyncSession found in function arguments")

        try:
            result = await func(*args, **kwargs)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise

    return wrapper  # type: ignore


async def check_db_connection() -> bool:
    """Check database connectivity for health checks."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


async def init_db() -> None:
    """Initialize database (create tables).

    Note: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()

