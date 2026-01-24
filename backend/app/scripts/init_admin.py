"""Initialize first admin user and default roles.

Usage:
    python -m app.scripts.init_admin

In single-tenant mode, this creates:
- A default tenant using settings from config.py
- All default permissions and roles (including platform_owner)
- A platform_owner admin user with superuser privileges
"""

import asyncio
import sys
from uuid import uuid4

from sqlalchemy import select

from app.config import settings
from app.core.database import get_db_context
from app.core.security import hash_password
from app.modules.auth.models import (
    DEFAULT_PERMISSIONS,
    DEFAULT_ROLES,
    AdminUser,
    Permission,
    Role,
    RolePermission,
)
from app.modules.tenants.models import Tenant, TenantSettings


async def init_permissions(db) -> dict[str, Permission]:
    """Create all default permissions if they don't exist."""
    print("📋 Initializing permissions...")
    
    permissions_map = {}
    
    for code, name, resource, action in DEFAULT_PERMISSIONS:
        # Check if permission exists
        result = await db.execute(
            select(Permission).where(Permission.code == code)
        )
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
            print(f"  ✅ Created permission: {code}")
        else:
            print(f"  ⏭️  Permission already exists: {code}")
        
        permissions_map[code] = perm
    
    await db.flush()
    return permissions_map


async def init_roles(db, tenant_id, permissions_map: dict[str, Permission]) -> dict[str, Role]:
    """Create default roles for tenant."""
    print(f"👥 Initializing roles for tenant...")
    
    roles_map = {}
    
    for role_name, role_config in DEFAULT_ROLES.items():
        # Check if role exists
        result = await db.execute(
            select(Role).where(
                Role.tenant_id == tenant_id,
                Role.name == role_name
            )
        )
        role = result.scalar_one_or_none()
        
        if not role:
            role = Role(
                id=uuid4(),
                tenant_id=tenant_id,
                name=role_name,
                description=role_config["description"],
                is_system=True,
            )
            db.add(role)
            await db.flush()
            print(f"  ✅ Created role: {role_name}")
        else:
            print(f"  ⏭️  Role already exists: {role_name}")
        
        # Get existing role permissions
        existing_rp_result = await db.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
        existing_permission_ids = {rp.permission_id for rp in existing_rp_result.scalars().all()}
        
        # Calculate required permissions
        required_permission_ids = set()
        for perm_code in role_config["permissions"]:
            if perm_code == "*":
                # Admin role - assign all permissions
                for perm in permissions_map.values():
                    required_permission_ids.add(perm.id)
            elif perm_code.endswith(":*"):
                # Wildcard permission (e.g., "articles:*")
                resource = perm_code.split(":")[0]
                for code, perm in permissions_map.items():
                    if code.startswith(f"{resource}:"):
                        required_permission_ids.add(perm.id)
            else:
                # Specific permission
                if perm_code in permissions_map:
                    required_permission_ids.add(permissions_map[perm_code].id)
        
        # Find permissions to add and remove
        permissions_to_add = required_permission_ids - existing_permission_ids
        permissions_to_remove = existing_permission_ids - required_permission_ids
        
        # Remove permissions that are no longer needed
        if permissions_to_remove:
            remove_rp_result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id.in_(permissions_to_remove)
                )
        )
            for rp in remove_rp_result.scalars().all():
            await db.delete(rp)
        
        # Add new permissions
        for perm_id in permissions_to_add:
            rp = RolePermission(
                id=uuid4(),
                role_id=role.id,
                permission_id=perm_id,
            )
            db.add(rp)
        
        if permissions_to_add or permissions_to_remove:
        await db.flush()
            if permissions_to_add:
                print(f"  ✅ Added {len(permissions_to_add)} permissions to {role_name}")
            if permissions_to_remove:
                print(f"  ✅ Removed {len(permissions_to_remove)} permissions from {role_name}")
        else:
            print(f"  ⏭️  Role {role_name} already has correct permissions")
        
        roles_map[role_name] = role
    
    return roles_map


async def init_tenant(db) -> Tenant:
    """Create or get default tenant using config settings."""
    print("🏢 Initializing tenant...")
    print(f"  📋 Using slug: {settings.default_tenant_slug}")
    print(f"  📋 Using name: {settings.default_tenant_name}")
    
    # First, try to find tenant by slug
    result = await db.execute(
        select(Tenant).where(
            Tenant.slug == settings.default_tenant_slug,
            Tenant.deleted_at.is_(None)
        )
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        # If not found by slug, check if there's a tenant with domain="localhost"
        # (for migration from old default tenant)
        result = await db.execute(
            select(Tenant).where(
                Tenant.domain == "localhost",
                Tenant.deleted_at.is_(None)
            )
        )
        existing_tenant = result.scalar_one_or_none()
        
        if existing_tenant:
            # Update existing tenant to use new slug and name
            print(f"  🔄 Found existing tenant with domain='localhost', updating...")
            existing_tenant.slug = settings.default_tenant_slug
            existing_tenant.name = settings.default_tenant_name
            existing_tenant.is_active = True
            await db.flush()
            tenant = existing_tenant
            print(f"  ✅ Updated tenant: {tenant.name} (ID: {tenant.id})")
        else:
            # Create new tenant (use None for domain to avoid conflicts)
        tenant = Tenant(
            id=uuid4(),
            name=settings.default_tenant_name,
            slug=settings.default_tenant_slug,
                domain=None,  # Allow None to avoid unique constraint issues
            is_active=True,
        )
        db.add(tenant)
        await db.flush()
        
            # Create tenant settings if they don't exist
            settings_result = await db.execute(
                select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
            )
            if not settings_result.scalar_one_or_none():
        tenant_settings = TenantSettings(
            id=uuid4(),
            tenant_id=tenant.id,
            default_locale="ru",
            timezone="Europe/Moscow",
        )
        db.add(tenant_settings)
        await db.flush()
        
        print(f"  ✅ Created tenant: {tenant.name} (ID: {tenant.id})")
    else:
        # Tenant exists, ensure settings exist
        settings_result = await db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
        )
        if not settings_result.scalar_one_or_none():
            tenant_settings = TenantSettings(
                id=uuid4(),
                tenant_id=tenant.id,
                default_locale="ru",
                timezone="Europe/Moscow",
            )
            db.add(tenant_settings)
            await db.flush()
            print(f"  ✅ Created tenant settings for existing tenant")
        
        print(f"  ⏭️  Tenant already exists: {tenant.name} (ID: {tenant.id})")
    
    return tenant


async def create_admin_user(
    db,
    tenant_id,
    admin_role: Role,
    email: str = "admin@example.com",
    password: str = "admin123",
    first_name: str = "Admin",
    last_name: str = "User",
) -> AdminUser:
    """Create first admin user."""
    print(f"👤 Creating admin user...")
    
    # Check if admin already exists
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.tenant_id == tenant_id,
            AdminUser.email == email,
            AdminUser.deleted_at.is_(None)
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"  ⚠️  Admin user already exists: {email}")
        print(f"  💡 To reset password, use: POST /api/v1/auth/me/password")
        return existing
    
    admin = AdminUser(
        id=uuid4(),
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role_id=admin_role.id,
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    await db.flush()
    
    print(f"  ✅ Created admin user: {email}")
    print(f"  🔑 Password: {password}")
    print(f"  ⚠️  IMPORTANT: Change password after first login!")
    
    return admin


async def main():
    """Main initialization function."""
    print("=" * 60)
    print("🚀 Initializing Admin User and Default Roles")
    print("=" * 60)
    print()
    
    # Show mode
    if settings.single_tenant_mode:
        print("📋 Mode: Single-tenant (X-Tenant-ID header not required)")
    else:
        print("📋 Mode: Multi-tenant (X-Tenant-ID header required)")
    print()
    
    try:
        async with get_db_context() as db:
            # 1. Initialize tenant
            tenant = await init_tenant(db)
            await db.commit()
            
            # 2. Initialize permissions
            permissions_map = await init_permissions(db)
            await db.commit()
            
            # 3. Initialize roles
            roles_map = await init_roles(db, tenant.id, permissions_map)
            await db.commit()
            
            # 4. Create or update admin user with platform_owner role
            # Use platform_owner role if available, otherwise fall back to site_owner or admin
            admin_role = (
                roles_map.get("platform_owner") 
                or roles_map.get("site_owner") 
                or roles_map.get("admin")
            )
            if not admin_role:
                raise RuntimeError("No admin role found. Check DEFAULT_ROLES configuration.")
            
            admin = await create_admin_user(
                db,
                tenant.id,
                admin_role,
                email="admin@example.com",
                password="admin123",
            )
            
            # Update existing admin user to platform_owner role if needed
            if admin.role_id != admin_role.id:
                print(f"  🔄 Updating admin user role to {admin_role.name}...")
                admin.role_id = admin_role.id
                admin.is_superuser = True  # Ensure superuser status
                await db.flush()
                print(f"  ✅ Updated admin user role to {admin_role.name}")
            
            await db.commit()
            
            print()
            print("=" * 60)
            print("✅ Initialization complete!")
            print("=" * 60)
            print()
            print("📝 Login credentials:")
            print(f"   Email:    {admin.email}")
            print(f"   Password: admin123")
            print(f"   Role:     {admin_role.name}")
            print()
            
            if settings.single_tenant_mode:
                print("🔐 Single-tenant mode:")
                print("   No X-Tenant-ID header required for login!")
            else:
                print("🔐 Tenant ID (for login header X-Tenant-ID):")
                print(f"   {tenant.id}")
            print()
            print("⚠️  Security:")
            print("   1. Change password immediately after first login")
            print("   2. Use: POST /api/v1/auth/me/password")
            print()
            print("📚 API Documentation:")
            print("   http://localhost:8000/docs")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

