"""Cleanup duplicates across all database tables.

Usage:
    python -m app.scripts.cleanup_all_duplicates [--dry-run] [--tenant-id UUID] [--table TABLE]

This script finds and removes duplicates in all tables based on their uniqueness constraints.
"""

import asyncio
import sys
from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.database import get_db_context

# Import all models
from app.modules.auth.models import AdminUser, Permission, Role
from app.modules.company.models import (
    AdvantageLocale,
    AddressLocale,
    EmployeeLocale,
    PracticeAreaLocale,
    ServiceLocale,
)
from app.modules.content.models import (
    ArticleLocale,
    CaseLocale,
    FAQLocale,
    TopicLocale,
)
from app.modules.documents.models import DocumentLocale
from app.modules.leads.models import InquiryForm
from app.modules.seo.models import Redirect, SEORoute
from app.modules.tenants.models import Tenant
from app.modules.assets.models import FileAsset


# Define duplicate detection rules for each table
DUPLICATE_RULES = {
    # Locale tables with slug - duplicates by (tenant_id, locale, slug)
    "topic_locales": {
        "model": TopicLocale,
        "key_fields": ["topic.tenant_id", "locale", "slug"],
        "join": "topic",
        "keep_strategy": "oldest",  # Keep oldest created_at
    },
    "article_locales": {
        "model": ArticleLocale,
        "key_fields": ["article.tenant_id", "locale", "slug"],
        "join": "article",
        "keep_strategy": "oldest",
    },
    "service_locales": {
        "model": ServiceLocale,
        "key_fields": ["service.tenant_id", "locale", "slug"],
        "join": "service",
        "keep_strategy": "oldest",
    },
    "employee_locales": {
        "model": EmployeeLocale,
        "key_fields": ["employee.tenant_id", "locale", "slug"],
        "join": "employee",
        "keep_strategy": "oldest",
    },
    "case_locales": {
        "model": CaseLocale,
        "key_fields": ["case.tenant_id", "locale", "slug"],
        "join": "case",
        "keep_strategy": "oldest",
    },
    "document_locales": {
        "model": DocumentLocale,
        "key_fields": ["document.tenant_id", "locale", "slug"],
        "join": "document",
        "keep_strategy": "oldest",
    },
    "practice_area_locales": {
        "model": PracticeAreaLocale,
        "key_fields": ["practice_area.tenant_id", "locale", "slug"],
        "join": "practice_area",
        "keep_strategy": "oldest",
    },
    "advantage_locales": {
        "model": AdvantageLocale,
        "key_fields": ["advantage.tenant_id", "locale", "slug"],
        "join": "advantage",
        "keep_strategy": "oldest",
    },
    "address_locales": {
        "model": AddressLocale,
        "key_fields": ["address.tenant_id", "locale", "slug"],
        "join": "address",
        "keep_strategy": "oldest",
    },
    "faq_locales": {
        "model": FAQLocale,
        "key_fields": ["faq.tenant_id", "locale", "slug"],
        "join": "faq",
        "keep_strategy": "oldest",
    },
    # Admin users - duplicates by (tenant_id, email)
    "admin_users": {
        "model": AdminUser,
        "key_fields": ["tenant_id", "email"],
        "join": None,
        "keep_strategy": "oldest",
    },
    # SEO routes - duplicates by (tenant_id, path, locale)
    "seo_routes": {
        "model": SEORoute,
        "key_fields": ["tenant_id", "path", "locale"],
        "join": None,
        "keep_strategy": "oldest",
    },
    # Redirects - duplicates by (tenant_id, source_path)
    "redirects": {
        "model": Redirect,
        "key_fields": ["tenant_id", "source_path"],
        "join": None,
        "keep_strategy": "oldest",
    },
    # Inquiry forms - duplicates by (tenant_id, slug)
    "inquiry_forms": {
        "model": InquiryForm,
        "key_fields": ["tenant_id", "slug"],
        "join": None,
        "keep_strategy": "oldest",
    },
    # Roles - duplicates by (tenant_id, name)
    "roles": {
        "model": Role,
        "key_fields": ["tenant_id", "name"],
        "join": None,
        "keep_strategy": "oldest",
    },
    # Tenants - duplicates by slug or domain
    "tenants": {
        "model": Tenant,
        "key_fields": ["slug"],  # slug is unique globally
        "join": None,
        "keep_strategy": "oldest",
    },
    # File assets - duplicates by s3_key
    "file_assets": {
        "model": FileAsset,
        "key_fields": ["s3_key"],
        "join": None,
        "keep_strategy": "oldest",
    },
}


def get_key_value(obj, key_field, join_attr=None):
    """Extract key value from object based on field path."""
    if "." in key_field:
        # Handle nested attributes like "topic.tenant_id"
        parts = key_field.split(".")
        value = obj
        for part in parts:
            if join_attr and part == join_attr:
                # Load relationship if needed
                if not hasattr(value, part) or getattr(value, part) is None:
                    return None
                value = getattr(value, part)
            else:
                value = getattr(value, part, None)
                if value is None:
                    return None
        return value
    else:
        return getattr(obj, key_field, None)


async def find_duplicates(db, table_name: str, rule: dict, tenant_id: UUID | None = None):
    """Find duplicates for a specific table."""
    model = rule["model"]
    key_fields = rule["key_fields"]
    join_attr = rule.get("join")
    
    # Build query - only filter by deleted_at if model has it
    stmt = select(model)
    if hasattr(model, "deleted_at"):
        stmt = stmt.where(model.deleted_at.is_(None))
    
    # Add join if needed
    if join_attr:
        join_model = getattr(model, join_attr).property.mapper.class_
        stmt = stmt.join(join_model)
        if tenant_id:
            stmt = stmt.where(join_model.tenant_id == tenant_id)
    elif tenant_id and hasattr(model, "tenant_id"):
        stmt = stmt.where(model.tenant_id == tenant_id)
    
    # Load relationships if needed
    if join_attr:
        stmt = stmt.options(selectinload(getattr(model, join_attr)))
    
    result = await db.execute(stmt)
    records = result.scalars().all()
    
    # Group by key fields
    groups = defaultdict(list)
    for record in records:
        key_parts = []
        for key_field in key_fields:
            value = get_key_value(record, key_field, join_attr)
            if value is None:
                # Skip records with None values in key fields
                break
            key_parts.append(value)
        else:
            # All key fields have values
            key = tuple(key_parts)
            groups[key].append(record)
    
    # Find duplicates (groups with more than 1 record)
    duplicates = {}
    for key, records_list in groups.items():
        if len(records_list) > 1:
            duplicates[key] = records_list
    
    return duplicates


async def choose_record_to_keep(records: list, strategy: str = "oldest"):
    """Choose which record to keep based on strategy."""
    if strategy == "oldest":
        # Keep the one with earliest created_at
        return min(records, key=lambda r: r.created_at)
    elif strategy == "newest":
        # Keep the one with latest created_at
        return max(records, key=lambda r: r.created_at)
    else:
        # Default: keep first one
        return records[0]


async def cleanup_table_duplicates(
    db, table_name: str, rule: dict, tenant_id: UUID | None = None, dry_run: bool = True
):
    """Cleanup duplicates for a specific table."""
    print(f"\n{'=' * 60}")
    print(f"🔍 Checking table: {table_name}")
    print("=" * 60)
    
    try:
        duplicates = await find_duplicates(db, table_name, rule, tenant_id)
        
        if not duplicates:
            print(f"✅ No duplicates found in {table_name}")
            return 0
        
        print(f"⚠️  Found {len(duplicates)} groups of duplicates:")
        
        total_to_delete = 0
        records_to_delete = []
        
        for key, records_list in duplicates.items():
            key_str = " | ".join(str(k) for k in key)
            print(f"\n📋 Key: {key_str}")
            print(f"   Found {len(records_list)} records")
            
            # Choose which to keep
            record_to_keep = await choose_record_to_keep(records_list, rule.get("keep_strategy", "oldest"))
            print(f"   ✅ Keeping: {record_to_keep.id} (created: {record_to_keep.created_at})")
            
            # Mark others for deletion
            for record in records_list:
                if record.id != record_to_keep.id:
                    records_to_delete.append(record)
                    print(f"   ❌ Will delete: {record.id} (created: {record.created_at})")
            
            total_to_delete += len(records_list) - 1
        
        print(f"\n📊 Summary for {table_name}:")
        print(f"   - Duplicate groups: {len(duplicates)}")
        print(f"   - Records to delete: {total_to_delete}")
        
        if dry_run:
            print(f"🔍 DRY RUN - No changes made to {table_name}")
        else:
            if records_to_delete:
                print(f"🗑️  Deleting {len(records_to_delete)} duplicate records...")
                for record in records_to_delete:
                    if hasattr(record, "soft_delete"):
                        record.soft_delete()
                    else:
                        # Hard delete if no soft_delete method
                        await db.delete(record)
                        await db.flush()
                    print(f"   ✅ Deleted: {record.id}")
                
                await db.flush()
                print(f"✅ Cleanup completed for {table_name}")
        
        return total_to_delete
        
    except Exception as e:
        print(f"❌ Error processing {table_name}: {e}")
        import traceback
        traceback.print_exc()
        return 0


async def cleanup_all_duplicates(
    db, tenant_id: UUID | None = None, dry_run: bool = True, table_filter: str | None = None
):
    """Cleanup duplicates in all tables."""
    print("=" * 60)
    print("🧹 CLEANUP ALL DUPLICATES")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE DELETE'}")
    if tenant_id:
        print(f"Tenant filter: {tenant_id}")
    if table_filter:
        print(f"Table filter: {table_filter}")
    print()
    
    tables_to_process = (
        [table_filter] if table_filter else list(DUPLICATE_RULES.keys())
    )
    
    total_deleted = 0
    results = {}
    
    for table_name in tables_to_process:
        if table_name not in DUPLICATE_RULES:
            print(f"⚠️  Unknown table: {table_name}")
            continue
        
        rule = DUPLICATE_RULES[table_name]
        deleted_count = await cleanup_table_duplicates(
            db, table_name, rule, tenant_id, dry_run
        )
        results[table_name] = deleted_count
        total_deleted += deleted_count
    
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"Total records to delete: {total_deleted}")
    print("\nBy table:")
    for table_name, count in results.items():
        if count > 0:
            print(f"  - {table_name}: {count}")
    
    if not dry_run and total_deleted > 0:
        await db.commit()
        print("\n✅ All duplicates have been removed!")
    elif dry_run:
        print("\n🔍 DRY RUN MODE - No changes made")
        print("   Run without --dry-run to actually delete duplicates")


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup duplicates in all database tables")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        help="Filter by specific tenant ID (UUID)",
    )
    parser.add_argument(
        "--table",
        type=str,
        help="Process only specific table (e.g., 'topic_locales', 'admin_users')",
    )
    args = parser.parse_args()
    
    tenant_id = None
    if args.tenant_id:
        try:
            tenant_id = UUID(args.tenant_id)
        except ValueError:
            print(f"❌ Error: Invalid tenant_id format: {args.tenant_id}")
            sys.exit(1)
    
    # List available tables
    if args.table and args.table not in DUPLICATE_RULES:
        print(f"❌ Error: Unknown table '{args.table}'")
        print(f"Available tables: {', '.join(DUPLICATE_RULES.keys())}")
        sys.exit(1)
    
    try:
        async with get_db_context() as db:
            await cleanup_all_duplicates(
                db,
                tenant_id=tenant_id,
                dry_run=args.dry_run,
                table_filter=args.table,
            )
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

