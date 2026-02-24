"""Auth module - user service."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, InvalidCredentialsError, NotFoundError
from app.core.pagination import paginate_query
from app.core.security import hash_password, verify_password
from app.modules.auth.models import AdminUser
from app.modules.auth.schemas import PasswordChange, UserCreate, UserUpdate


class UserService(BaseService[AdminUser]):
    """Service for user management operations."""

    model = AdminUser

    def __init__(self, db: AsyncSession, actor_id: UUID | None = None) -> None:
        super().__init__(db)
        self._actor_id = actor_id
        self._audit: "AuditService | None" = None

    @property
    def audit(self) -> "AuditService":
        if self._audit is None:
            from app.core.audit import AuditService
            self._audit = AuditService(self.db)
        return self._audit

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(AdminUser.role)]

    async def get_by_id(self, user_id: UUID, tenant_id: UUID) -> AdminUser:
        """Get user by ID within tenant."""
        return await self._get_by_id(user_id, tenant_id)

    async def get_by_id_global(self, user_id: UUID) -> AdminUser:
        """Get user by ID without tenant restriction.

        Used by superuser / platform_owner when the user's tenant
        is unknown (e.g. navigating from the global user list).
        """
        stmt = (
            select(AdminUser)
            .where(AdminUser.id == user_id)
            .where(AdminUser.deleted_at.is_(None))
            .options(*self._get_default_options())
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("AdminUser", user_id)

        return user

    async def list_users(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[AdminUser], int]:
        """List users in tenant with pagination."""
        filters = []
        if is_active is not None:
            filters.append(AdminUser.is_active == is_active)

        base_query = self._build_base_query(tenant_id, filters=filters)

        # Add search filter separately (complex OR condition)
        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(
                (AdminUser.email.ilike(search_pattern)) |
                (AdminUser.full_name.ilike(search_pattern))
            )

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=self._get_default_options(),
            order_by=[AdminUser.created_at.desc()],
        )

    @transactional
    async def create(self, tenant_id: UUID, data: UserCreate) -> AdminUser:
        """Create a new user.
        
        Sets force_password_change=True for new users.
        Sends welcome email when send_credentials=True.
        """
        existing = await self.db.execute(
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.email == data.email)
            .where(AdminUser.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsError("User", "email", data.email)

        # Create user with force_password_change=True
        user = AdminUser(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role_id=data.role_id,
            is_active=data.is_active,
            force_password_change=True,
        )
        self.db.add(user)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            if "uq_admin_users_tenant_email" in str(exc):
                raise AlreadyExistsError("User", "email", data.email) from exc
            raise
        await self.db.refresh(user)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(user, ["role"])

        # Audit log: user created
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id,
            resource_type="user",
            resource_id=user.id,
            action="create",
            changes={"email": user.email, "first_name": user.first_name, "last_name": user.last_name},
        )

        # Send welcome email if requested
        if data.send_credentials:
            try:
                from app.modules.notifications.service import EmailService
                from app.modules.tenants.models import Tenant

                # Get tenant name for the email
                tenant_stmt = select(Tenant.name).where(Tenant.id == tenant_id)
                tenant_result = await self.db.execute(tenant_stmt)
                tenant_name = tenant_result.scalar_one_or_none() or "Platform"

                email_service = EmailService(db=self.db)
                await email_service.send_welcome_email(
                    to_email=data.email,
                    first_name=data.first_name,
                    tenant_name=tenant_name,
                    tenant_id=tenant_id,
                )
            except Exception:
                # Don't fail user creation if email sending fails
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to send welcome email to %s", data.email
                )

        return user

    @transactional
    async def update(
        self, user_id: UUID, tenant_id: UUID, data: UserUpdate
    ) -> AdminUser:
        """Update user with optimistic locking."""
        user = await self.get_by_id(user_id, tenant_id)
        user.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        # Track changes for audit log
        changes: dict = {}
        for field, value in update_data.items():
            old_value = getattr(user, field, None)
            if old_value != value:
                changes[field] = {"old": str(old_value) if old_value is not None else None, "new": str(value)}
            setattr(user, field, value)

        await self.db.flush()

        # Audit log: user updated
        if changes:
            await self.audit.log(
                tenant_id=tenant_id,
                user_id=self._actor_id,
                resource_type="user",
                resource_id=user_id,
                action="update",
                changes=changes,
            )

        await self.db.refresh(user)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(user, ["role"])

        return user

    @transactional
    async def change_password(
        self, user_id: UUID, tenant_id: UUID, data: PasswordChange
    ) -> None:
        """Change user password. Clears force_password_change flag.

        The new hash is also synced to every other ``AdminUser`` row
        with the same email so the user keeps a single password across
        all tenants.
        """
        user = await self.get_by_id(user_id, tenant_id)

        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        new_hash = hash_password(data.new_password)
        user.password_hash = new_hash
        user.force_password_change = False
        await self.db.flush()

        # Sync password to all other tenant records with the same email
        sync_stmt = (
            update(AdminUser)
            .where(
                AdminUser.email == user.email,
                AdminUser.id != user.id,
                AdminUser.deleted_at.is_(None),
            )
            .values(password_hash=new_hash)
        )
        await self.db.execute(sync_stmt)

        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id or user_id,
            resource_type="user",
            resource_id=user_id,
            action="update",
            changes={"password": {"old": "***", "new": "***"}, "force_password_change": {"old": "True", "new": "False"}},
        )

    @transactional
    async def update_avatar_url(
        self, user_id: UUID, tenant_id: UUID, url: str | None
    ) -> AdminUser:
        """Update or clear the user avatar URL."""
        user = await self.get_by_id(user_id, tenant_id)
        user.avatar_url = url
        await self.db.flush()
        await self.db.refresh(user)
        await self.db.refresh(user, ["role"])
        return user

    @transactional
    async def soft_delete(self, user_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a user."""
        await self._soft_delete(user_id, tenant_id)

        # Audit log: user deleted
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id,
            resource_type="user",
            resource_id=user_id,
            action="delete",
        )
