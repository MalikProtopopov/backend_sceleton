"""Cleanup duplicate topics by slug and locale.

Usage:
    python -m app.scripts.cleanup_duplicate_topics [--dry-run] [--tenant-id UUID]

This script finds topics with duplicate slugs in the same locale and tenant,
keeps the one with the most articles (or oldest if equal), and soft-deletes the rest.
"""

import asyncio
import sys
from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.database import get_db_context
from app.modules.content.models import ArticleTopic, Topic, TopicLocale


async def find_duplicate_topics(db, tenant_id: UUID | None = None):
    """Find topics with duplicate slugs in the same locale and tenant."""
    # Build base query
    stmt = (
        select(TopicLocale)
        .join(Topic)
        .where(Topic.deleted_at.is_(None))
        .options(selectinload(TopicLocale.topic))
    )
    
    if tenant_id:
        stmt = stmt.where(Topic.tenant_id == tenant_id)
    
    result = await db.execute(stmt)
    topic_locales = result.scalars().all()
    
    # Group by (tenant_id, locale, slug)
    groups = defaultdict(list)
    for tl in topic_locales:
        key = (tl.topic.tenant_id, tl.locale, tl.slug)
        groups[key].append(tl)
    
    # Find duplicates (groups with more than 1 topic)
    duplicates = {}
    for key, topic_locales_list in groups.items():
        if len(topic_locales_list) > 1:
            duplicates[key] = topic_locales_list
    
    return duplicates


async def count_articles_for_topic(db, topic_id: UUID) -> int:
    """Count published articles for a topic."""
    stmt = (
        select(func.count(ArticleTopic.article_id))
        .where(ArticleTopic.topic_id == topic_id)
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def choose_topic_to_keep(db, topic_locales_list: list[TopicLocale]) -> Topic:
    """Choose which topic to keep based on article count and creation date."""
    topic_scores = []
    
    for tl in topic_locales_list:
        topic = tl.topic
        article_count = await count_articles_for_topic(db, topic.id)
        topic_scores.append((topic, article_count, topic.created_at))
    
    # Sort by: 1) article count (desc), 2) created_at (asc - oldest first)
    topic_scores.sort(key=lambda x: (-x[1], x[2]))
    
    return topic_scores[0][0]  # Return topic with highest score


async def cleanup_duplicates(db, tenant_id: UUID | None = None, dry_run: bool = True):
    """Find and remove duplicate topics."""
    print("=" * 60)
    print("🔍 Searching for duplicate topics...")
    print("=" * 60)
    print()
    
    duplicates = await find_duplicate_topics(db, tenant_id)
    
    if not duplicates:
        print("✅ No duplicate topics found!")
        return
    
    print(f"⚠️  Found {len(duplicates)} groups of duplicate topics:")
    print()
    
    total_to_delete = 0
    topics_to_delete = []
    
    for (t_tenant_id, locale, slug), topic_locales_list in duplicates.items():
        print(f"📋 Slug: '{slug}' (locale: {locale}, tenant: {t_tenant_id})")
        print(f"   Found {len(topic_locales_list)} topics with this slug")
        
        # Choose which to keep
        topic_to_keep = await choose_topic_to_keep(db, topic_locales_list)
        article_count = await count_articles_for_topic(db, topic_to_keep.id)
        
        print(f"   ✅ Keeping: {topic_to_keep.id} (created: {topic_to_keep.created_at}, articles: {article_count})")
        
        # Mark others for deletion
        for tl in topic_locales_list:
            if tl.topic.id != topic_to_keep.id:
                topics_to_delete.append(tl.topic)
                print(f"   ❌ Will delete: {tl.topic.id} (created: {tl.topic.created_at})")
        
        print()
        total_to_delete += len(topic_locales_list) - 1
    
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   - Duplicate groups: {len(duplicates)}")
    print(f"   - Topics to delete: {total_to_delete}")
    print("=" * 60)
    print()
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes made")
        print("   Run without --dry-run to actually delete duplicates")
    else:
        if topics_to_delete:
            print("🗑️  Deleting duplicate topics...")
            for topic in topics_to_delete:
                topic.soft_delete()
                print(f"   ✅ Deleted: {topic.id}")
            
            await db.commit()
            print()
            print("✅ Cleanup completed!")
        else:
            print("ℹ️  No topics to delete")


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cleanup duplicate topics")
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
    args = parser.parse_args()
    
    tenant_id = None
    if args.tenant_id:
        try:
            tenant_id = UUID(args.tenant_id)
        except ValueError:
            print(f"❌ Error: Invalid tenant_id format: {args.tenant_id}")
            sys.exit(1)
    
    try:
        async with get_db_context() as db:
            await cleanup_duplicates(db, tenant_id=tenant_id, dry_run=args.dry_run)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

