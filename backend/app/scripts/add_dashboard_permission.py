"""Add dashboard:read permission to site_owner, content_manager, marketer, editor roles.

Run once after deploying the dashboard:read permission fix:
    python -m app.scripts.add_dashboard_permission

Updates ALL tenants' roles (unlike init_admin which only updates the default tenant).
"""

import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.core.database import get_db_context
from app.modules.auth.models import (
    DEFAULT_PERMISSIONS,
    Permission,
    Role,
    RolePermission,
)
from app.modules.tenants.models import Tenant

ROLES_TO_UPDATE = ("site_owner", "content_manager", "marketer", "editor")
PERMISSION_CODE = "dashboard:read"


async def main() -> None:
    print("Adding dashboard:read permission to tenant roles...")

    # Find dashboard:read in DEFAULT_PERMISSIONS
    perm_tuple = next((p for p in DEFAULT_PERMISSIONS if p[0] == PERMISSION_CODE), None)
    if not perm_tuple:
        print(f"  ❌ {PERMISSION_CODE} not found in DEFAULT_PERMISSIONS")
        return

    code, name, resource, action = perm_tuple

    async with get_db_context() as db:
        # Get or create permission
        result = await db.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()
        if not perm:
            perm = Permission(
                id=uuid4(),
                code=code,
                name=name,
                resource=resource,
                action=action,
            )
            db.add(perm)
            await db.flush()
            print(f"  ✅ Created permission: {code}")
        else:
            print(f"  ⏭️  Permission exists: {code}")

        # Get all tenants
        tenants_result = await db.execute(
            select(Tenant).where(Tenant.deleted_at.is_(None))
        )
        tenants = list(tenants_result.scalars().all())

        updated = 0
        for tenant in tenants:
            for role_name in ROLES_TO_UPDATE:
                role_result = await db.execute(
                    select(Role).where(
                        Role.tenant_id == tenant.id,
                        Role.name == role_name,
                    )
                )
                role = role_result.scalar_one_or_none()
                if not role:
                    continue

                # Check if role already has this permission
                rp_result = await db.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm.id,
                    )
                )
                if rp_result.scalar_one_or_none():
                    continue

                rp = RolePermission(
                    id=uuid4(),
                    role_id=role.id,
                    permission_id=perm.id,
                )
                db.add(rp)
                updated += 1
                print(f"  ✅ {tenant.slug or tenant.id}: {role_name}")

        await db.commit()
        print(f"\nDone. Updated {updated} role(s).")


if __name__ == "__main__":
    asyncio.run(main())
