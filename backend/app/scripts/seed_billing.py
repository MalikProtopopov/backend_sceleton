"""Seed billing modules, plans, and bundles.

Idempotent: creates if not exist, updates if changed.
Can be run repeatedly without side effects.

Usage:
    python -m app.scripts.seed_billing
"""

import asyncio
import json
import sys
from uuid import uuid4

from sqlalchemy import delete, select

from app.core.database import get_db_context
from app.modules.billing.models import (
    BillingModule,
    Bundle,
    BundleModule,
    Plan,
    PlanModule,
)

MODULES = [
    {"slug": "core", "name": "Core", "name_ru": "Базовый", "category": "platform", "price": 0, "is_base": True, "sort": 0,
     "description": "Auth, RBAC, SSL, media, sitemap, robots.txt, dashboard, basic audit",
     "description_ru": "Авторизация, RBAC, SSL, медиа, карта сайта, robots.txt, дашборд, базовый аудит"},
    {"slug": "content", "name": "Content", "name_ru": "Контент", "category": "content", "price": 99000, "is_base": False, "sort": 1,
     "description": "Blog, cases, reviews, FAQ, content blocks, bulk operations",
     "description_ru": "Блог, кейсы, отзывы, FAQ, блоки контента, массовые операции"},
    {"slug": "company", "name": "Company", "name_ru": "Компания", "category": "company", "price": 99000, "is_base": False, "sort": 2,
     "description": "Services, team, advantages, addresses, contacts, practice areas",
     "description_ru": "Услуги, команда, преимущества, адреса, контакты, направления"},
    {"slug": "crm_basic", "name": "CRM Basic", "name_ru": "CRM Базовый", "category": "crm", "price": 69000, "is_base": False, "sort": 3,
     "description": "Leads, email/telegram notifications, inquiry forms",
     "description_ru": "Лиды, уведомления email/telegram, формы заявок"},
    {"slug": "crm_pro", "name": "CRM Pro", "name_ru": "CRM Про", "category": "crm", "price": 149000, "is_base": False, "sort": 4,
     "description": "UTM analytics, device/geo analytics, export",
     "description_ru": "UTM-аналитика, аналитика устройств/гео, экспорт"},
    {"slug": "seo_advanced", "name": "SEO Advanced", "name_ru": "SEO Расширенный", "category": "platform", "price": 149000, "is_base": False, "sort": 5,
     "description": "Redirects, IndexNow, llms.txt, OG meta, structured data",
     "description_ru": "Редиректы, IndexNow, llms.txt, OG-метатеги, структурированные данные"},
    {"slug": "multilang", "name": "Multilang", "name_ru": "Мультиязычность", "category": "platform", "price": 149000, "is_base": False, "sort": 6,
     "description": "Locale configuration, all locale tables",
     "description_ru": "Настройка локалей, все таблицы локализации"},
    {"slug": "catalog_basic", "name": "Catalog Basic", "name_ru": "Каталог Базовый", "category": "commerce", "price": 299000, "is_base": False, "sort": 7,
     "description": "Products, categories, prices, images, search",
     "description_ru": "Товары, категории, цены, изображения, поиск"},
    {"slug": "catalog_pro", "name": "Catalog Pro", "name_ru": "Каталог Про", "category": "commerce", "price": 249000, "is_base": False, "sort": 8,
     "description": "Variants, parameters, faceted filtering, SEO filter pages",
     "description_ru": "Вариации, параметры, фасетная фильтрация, SEO-страницы фильтров"},
    {"slug": "documents", "name": "Documents", "name_ru": "Документы", "category": "content", "price": 69000, "is_base": False, "sort": 9,
     "description": "Document management (admin CRUD, localization, publish/draft). Public read is Core.",
     "description_ru": "Управление документами (CRUD, локализация, публикация). Публичное чтение — Core."},
]

PLANS = [
    {
        "slug": "starter", "name": "Starter", "name_ru": "Стартовый",
        "description_ru": "Для небольших компаний и визиток",
        "price_monthly": 199000, "price_yearly": 190800, "setup_fee": 999000,
        "is_default": True, "sort": 0,
        "limits": {
            "max_users": 2, "max_storage_mb": 5120, "max_leads_per_month": 500,
            "max_products": 0, "max_variants": 0, "max_domains": 1,
            "max_articles": 100, "max_rbac_roles": 2,
        },
        "modules": ["core", "content", "company", "crm_basic"],
    },
    {
        "slug": "business", "name": "Business", "name_ru": "Бизнес",
        "description_ru": "Для растущего бизнеса с SEO и аналитикой",
        "price_monthly": 499000, "price_yearly": 479000, "setup_fee": 1999000,
        "is_default": False, "sort": 1,
        "limits": {
            "max_users": 5, "max_storage_mb": 20480, "max_leads_per_month": 2000,
            "max_products": 0, "max_variants": 0, "max_domains": 3,
            "max_articles": 500, "max_rbac_roles": 5,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "documents"],
    },
    {
        "slug": "commerce", "name": "Commerce", "name_ru": "Коммерция",
        "description_ru": "Полный набор с каталогом товаров",
        "price_monthly": 999000, "price_yearly": 959000, "setup_fee": 4999000,
        "is_default": False, "sort": 2,
        "limits": {
            "max_users": 10, "max_storage_mb": 51200, "max_leads_per_month": 5000,
            "max_products": 5000, "max_variants": 10000, "max_domains": 5,
            "max_articles": -1, "max_rbac_roles": 10,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "catalog_basic", "catalog_pro", "documents"],
    },
    {
        "slug": "enterprise", "name": "Enterprise", "name_ru": "Корпоративный",
        "description_ru": "Индивидуальные условия для крупных клиентов",
        "price_monthly": 0, "price_yearly": 0, "setup_fee": 0,
        "is_default": False, "sort": 3,
        "limits": {
            "max_users": -1, "max_storage_mb": -1, "max_leads_per_month": -1,
            "max_products": -1, "max_variants": -1, "max_domains": -1,
            "max_articles": -1, "max_rbac_roles": -1,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "catalog_basic", "catalog_pro", "documents"],
    },
    {
        "slug": "agency", "name": "Agency", "name_ru": "Агентский",
        "description_ru": "Для агентств и реселлеров с дегрессивной шкалой",
        "price_monthly": 99000, "price_yearly": 95000, "setup_fee": 0,
        "is_default": False, "sort": 4,
        "limits": {
            "max_users": 3, "max_storage_mb": 10240, "max_leads_per_month": 1000,
            "max_products": 500, "max_variants": 1000, "max_domains": 2,
            "max_articles": 200, "max_rbac_roles": 3,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "catalog_basic", "catalog_pro", "documents"],
    },
]

BUNDLES = [
    {
        "slug": "seo_pack", "name": "SEO Pack", "name_ru": "SEO-пакет",
        "description": "SEO Advanced + Multilang", "description_ru": "SEO Расширенный + Мультиязычность",
        "price": 199000, "discount": 33, "sort": 0,
        "modules": ["seo_advanced", "multilang"],
    },
    {
        "slug": "catalog_pack", "name": "Catalog Pack", "name_ru": "Каталог-пакет",
        "description": "Catalog Basic + Catalog Pro", "description_ru": "Каталог Базовый + Каталог Про",
        "price": 499000, "discount": 9, "sort": 1,
        "modules": ["catalog_basic", "catalog_pro"],
    },
    {
        "slug": "analytics_pack", "name": "Analytics Pack", "name_ru": "Аналитика-пакет",
        "description": "CRM Pro (analytics + export)", "description_ru": "CRM Про (аналитика + экспорт)",
        "price": 149000, "discount": 0, "sort": 2,
        "modules": ["crm_pro"],
    },
]


async def seed_billing():
    """Create or update billing modules, plans, and bundles."""
    print("=" * 60)
    print("💰 Seeding billing data")
    print("=" * 60)

    async with get_db_context() as db:
        module_map: dict[str, BillingModule] = {}

        # ── Modules ──
        for m in MODULES:
            result = await db.execute(select(BillingModule).where(BillingModule.slug == m["slug"]))
            existing = result.scalar_one_or_none()

            if existing:
                existing.name = m["name"]
                existing.name_ru = m["name_ru"]
                existing.description = m.get("description")
                existing.description_ru = m.get("description_ru")
                existing.category = m["category"]
                existing.price_monthly_kopecks = m["price"]
                existing.is_base = m["is_base"]
                existing.sort_order = m["sort"]
                module_map[m["slug"]] = existing
                print(f"  ⏭️  Module exists: {m['slug']}")
            else:
                mod = BillingModule(
                    id=uuid4(), slug=m["slug"], name=m["name"], name_ru=m["name_ru"],
                    description=m.get("description"), description_ru=m.get("description_ru"),
                    category=m["category"], price_monthly_kopecks=m["price"],
                    is_base=m["is_base"], sort_order=m["sort"],
                )
                db.add(mod)
                module_map[m["slug"]] = mod
                print(f"  ✅ Created module: {m['slug']}")

        await db.flush()

        # ── Plans ──
        for p in PLANS:
            result = await db.execute(select(Plan).where(Plan.slug == p["slug"]))
            existing = result.scalar_one_or_none()

            if existing:
                existing.name = p["name"]
                existing.name_ru = p["name_ru"]
                existing.description_ru = p.get("description_ru")
                existing.price_monthly_kopecks = p["price_monthly"]
                existing.price_yearly_kopecks = p["price_yearly"]
                existing.setup_fee_kopecks = p["setup_fee"]
                existing.is_default = p["is_default"]
                existing.sort_order = p["sort"]
                existing.limits = p["limits"]
                plan = existing
                print(f"  ⏭️  Plan exists: {p['slug']}")
            else:
                plan = Plan(
                    id=uuid4(), slug=p["slug"], name=p["name"], name_ru=p["name_ru"],
                    description_ru=p.get("description_ru"),
                    price_monthly_kopecks=p["price_monthly"],
                    price_yearly_kopecks=p["price_yearly"],
                    setup_fee_kopecks=p["setup_fee"],
                    is_default=p["is_default"], sort_order=p["sort"],
                    limits=p["limits"],
                )
                db.add(plan)
                print(f"  ✅ Created plan: {p['slug']}")

            await db.flush()

            # Sync plan-module links
            result = await db.execute(
                select(PlanModule).where(PlanModule.plan_id == plan.id)
            )
            existing_links = {pm.module_id for pm in result.scalars().all()}
            desired_ids = {module_map[slug].id for slug in p["modules"] if slug in module_map}

            for mid in desired_ids - existing_links:
                db.add(PlanModule(id=uuid4(), plan_id=plan.id, module_id=mid))
            for mid in existing_links - desired_ids:
                await db.execute(
                    delete(PlanModule).where(PlanModule.plan_id == plan.id, PlanModule.module_id == mid)
                )

            await db.flush()

        # ── Bundles ──
        for b in BUNDLES:
            result = await db.execute(select(Bundle).where(Bundle.slug == b["slug"]))
            existing = result.scalar_one_or_none()

            if existing:
                existing.name = b["name"]
                existing.name_ru = b["name_ru"]
                existing.description = b.get("description")
                existing.description_ru = b.get("description_ru")
                existing.price_monthly_kopecks = b["price"]
                existing.discount_percent = b["discount"]
                existing.sort_order = b["sort"]
                bundle = existing
                print(f"  ⏭️  Bundle exists: {b['slug']}")
            else:
                bundle = Bundle(
                    id=uuid4(), slug=b["slug"], name=b["name"], name_ru=b["name_ru"],
                    description=b.get("description"), description_ru=b.get("description_ru"),
                    price_monthly_kopecks=b["price"],
                    discount_percent=b["discount"], sort_order=b["sort"],
                )
                db.add(bundle)
                print(f"  ✅ Created bundle: {b['slug']}")

            await db.flush()

            # Sync bundle-module links
            result = await db.execute(
                select(BundleModule).where(BundleModule.bundle_id == bundle.id)
            )
            existing_links = {bm.module_id for bm in result.scalars().all()}
            desired_ids = {module_map[slug].id for slug in b["modules"] if slug in module_map}

            for mid in desired_ids - existing_links:
                db.add(BundleModule(id=uuid4(), bundle_id=bundle.id, module_id=mid))

            await db.flush()

        await db.commit()

    print()
    print("✅ Billing seed complete!")
    print()


if __name__ == "__main__":
    asyncio.run(seed_billing())
