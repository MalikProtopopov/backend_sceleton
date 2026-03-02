"""Sync DEFAULT_PERMISSIONS and DEFAULT_ROLES to all tenants.

Idempotent — safe to run multiple times. Creates missing permissions
and adds missing role→permission links for every tenant.

Usage:
    python -m app.scripts.sync_permissions
"""

import asyncio
from uuid import uuid4

from sqlalchemy import select

import app.modules.billing.models  # noqa: F401  — resolve Tenant.plan
from app.core.database import get_db_context
from app.modules.auth.models import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    Permission,
    Role,
    RolePermission,
)
from app.modules.tenants.models import Tenant


async def main() -> None:
    print("=" * 60)
    print("Syncing permissions and roles for all tenants")
    print("=" * 60)

    async with get_db_context() as db:
        # 1. Ensure every entry in DEFAULT_PERMISSIONS exists in the DB
        perm_map: dict[str, Permission] = {}
        result = await db.execute(select(Permission))
        for p in result.scalars().all():
            perm_map[p.code] = p

        created_perms = 0
        for code, name, resource, action in DEFAULT_PERMISSIONS:
            if code not in perm_map:
                perm = Permission(
                    id=uuid4(), code=code, name=name,
                    resource=resource, action=action,
                )
                db.add(perm)
                perm_map[code] = perm
                created_perms += 1
                print(f"  + Permission: {code}")

        if created_perms:
            await db.flush()
        print(f"  Permissions: {created_perms} created, "
              f"{len(DEFAULT_PERMISSIONS) - created_perms} already exist\n")

        # 2. Expand wildcard permission lists for each role
        all_codes = {code for code, *_ in DEFAULT_PERMISSIONS}
        role_perms_expanded: dict[str, set[str]] = {}
        for role_name, cfg in DEFAULT_ROLES.items():
            expanded: set[str] = set()
            for pat in cfg["permissions"]:
                if pat == "*":
                    expanded = all_codes.copy()
                    break
                if pat.endswith(":*"):
                    resource = pat.split(":")[0]
                    expanded.update(c for c in all_codes if c.startswith(f"{resource}:"))
                else:
                    if pat in all_codes:
                        expanded.add(pat)
            role_perms_expanded[role_name] = expanded

        # 3. For every tenant, sync role→permission links
        tenants_result = await db.execute(
            select(Tenant).where(Tenant.deleted_at.is_(None))
        )
        tenants = list(tenants_result.scalars().all())
        print(f"  Tenants to process: {len(tenants)}\n")

        total_added = 0
        for tenant in tenants:
            tenant_label = tenant.slug or str(tenant.id)[:8]
            added_for_tenant = 0

            for role_name, desired_codes in role_perms_expanded.items():
                role_result = await db.execute(
                    select(Role).where(
                        Role.tenant_id == tenant.id,
                        Role.name == role_name,
                    )
                )
                role = role_result.scalar_one_or_none()
                if not role:
                    continue

                existing_result = await db.execute(
                    select(RolePermission.permission_id).where(
                        RolePermission.role_id == role.id,
                    )
                )
                existing_perm_ids = {row[0] for row in existing_result.all()}

                for code in desired_codes:
                    perm = perm_map.get(code)
                    if not perm:
                        continue
                    if perm.id in existing_perm_ids:
                        continue
                    db.add(RolePermission(
                        id=uuid4(), role_id=role.id, permission_id=perm.id,
                    ))
                    added_for_tenant += 1

            if added_for_tenant:
                print(f"  {tenant_label}: +{added_for_tenant} role-permission links")
                total_added += added_for_tenant

        await db.commit()
        print(f"\nDone. Added {total_added} role-permission link(s) total.")


if __name__ == "__main__":
    asyncio.run(main())
