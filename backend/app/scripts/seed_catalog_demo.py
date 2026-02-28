"""Seed 5 demo products with 3 variants each into a specific tenant.

Usage (inside Docker or locally):
    python -m app.scripts.seed_catalog_demo

Finds the first active tenant (or mediann.dev by slug) and populates
products, categories, option groups, variants, prices, and inclusions.
Idempotent: skips if products with the same SKUs already exist.
"""

import asyncio
import sys
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.core.database import get_db_context
from app.modules.catalog.models import (
    Category,
    Product,
    ProductCategory,
    ProductPrice,
)
from app.modules.tenants.models import FeatureFlag, Tenant
from app.modules.variants.models import (
    ProductOptionGroup,
    ProductOptionValue,
    ProductVariant,
    VariantInclusion,
    VariantOptionLink,
    VariantPrice,
)

PRODUCTS = [
    {
        "sku": "DEMO-LAPTOP-001",
        "slug": "gaming-laptop-pro",
        "title": "Игровой ноутбук ProMax",
        "brand": "TechBrand",
        "product_type": "physical",
        "description": "Мощный игровой ноутбук для работы и игр",
        "base_price": Decimal("89990.00"),
        "option_group": {
            "title": "Конфигурация",
            "slug": "configuration",
            "display_type": "cards",
        },
        "variants": [
            {
                "sku": "DEMO-LAPTOP-8GB",
                "slug": "8gb-256ssd",
                "title": "8 ГБ / 256 ГБ SSD",
                "price": Decimal("89990.00"),
                "stock": 15,
                "weight": Decimal("2.100"),
                "is_default": True,
                "option_value": {"title": "8 ГБ / 256 SSD", "slug": "8gb-256ssd"},
                "inclusions": [
                    {"title": "8 ГБ DDR5 RAM", "is_included": True},
                    {"title": "256 ГБ NVMe SSD", "is_included": True},
                    {"title": "RTX 4060", "is_included": True},
                    {"title": "Расширенная гарантия 3 года", "is_included": False},
                ],
            },
            {
                "sku": "DEMO-LAPTOP-16GB",
                "slug": "16gb-512ssd",
                "title": "16 ГБ / 512 ГБ SSD",
                "price": Decimal("119990.00"),
                "stock": 8,
                "weight": Decimal("2.100"),
                "option_value": {"title": "16 ГБ / 512 SSD", "slug": "16gb-512ssd"},
                "inclusions": [
                    {"title": "16 ГБ DDR5 RAM", "is_included": True},
                    {"title": "512 ГБ NVMe SSD", "is_included": True},
                    {"title": "RTX 4070", "is_included": True},
                    {"title": "Расширенная гарантия 3 года", "is_included": True},
                ],
            },
            {
                "sku": "DEMO-LAPTOP-32GB",
                "slug": "32gb-1tb",
                "title": "32 ГБ / 1 ТБ SSD",
                "price": Decimal("159990.00"),
                "sale_price": Decimal("149990.00"),
                "stock": 3,
                "weight": Decimal("2.200"),
                "option_value": {"title": "32 ГБ / 1 ТБ SSD", "slug": "32gb-1tb"},
                "inclusions": [
                    {"title": "32 ГБ DDR5 RAM", "is_included": True},
                    {"title": "1 ТБ NVMe SSD", "is_included": True},
                    {"title": "RTX 4080", "is_included": True},
                    {"title": "Расширенная гарантия 3 года", "is_included": True},
                ],
            },
        ],
    },
    {
        "sku": "DEMO-COURSE-001",
        "slug": "python-course",
        "title": "Курс «Python с нуля до PRO»",
        "brand": None,
        "product_type": "course",
        "description": "Онлайн-курс по Python для начинающих и продвинутых",
        "base_price": Decimal("4990.00"),
        "option_group": {
            "title": "Тариф",
            "slug": "tariff",
            "display_type": "cards",
        },
        "variants": [
            {
                "sku": "DEMO-COURSE-BASIC",
                "slug": "basic",
                "title": "Базовый",
                "price": Decimal("4990.00"),
                "is_default": True,
                "option_value": {"title": "Базовый", "slug": "basic"},
                "inclusions": [
                    {"title": "Видеоуроки (50 часов)", "is_included": True},
                    {"title": "Домашние задания", "is_included": True},
                    {"title": "Проверка ментором", "is_included": False},
                    {"title": "Сертификат", "is_included": False},
                    {"title": "Помощь с трудоустройством", "is_included": False},
                ],
            },
            {
                "sku": "DEMO-COURSE-PRO",
                "slug": "pro",
                "title": "Продвинутый",
                "price": Decimal("14990.00"),
                "option_value": {"title": "Продвинутый", "slug": "pro"},
                "inclusions": [
                    {"title": "Видеоуроки (50 часов)", "is_included": True},
                    {"title": "Домашние задания", "is_included": True},
                    {"title": "Проверка ментором", "is_included": True},
                    {"title": "Сертификат", "is_included": True},
                    {"title": "Помощь с трудоустройством", "is_included": False},
                ],
            },
            {
                "sku": "DEMO-COURSE-VIP",
                "slug": "vip",
                "title": "VIP",
                "price": Decimal("29990.00"),
                "sale_price": Decimal("24990.00"),
                "option_value": {"title": "VIP", "slug": "vip"},
                "inclusions": [
                    {"title": "Видеоуроки (50 часов)", "is_included": True},
                    {"title": "Домашние задания", "is_included": True},
                    {"title": "Проверка ментором", "is_included": True},
                    {"title": "Сертификат", "is_included": True},
                    {"title": "Помощь с трудоустройством", "is_included": True},
                ],
            },
        ],
    },
    {
        "sku": "DEMO-SAAS-001",
        "slug": "crm-subscription",
        "title": "CRM-система «Контакт»",
        "brand": "Контакт",
        "product_type": "subscription",
        "description": "Облачная CRM для малого и среднего бизнеса",
        "base_price": Decimal("990.00"),
        "option_group": {
            "title": "Тарифный план",
            "slug": "plan",
            "display_type": "cards",
        },
        "variants": [
            {
                "sku": "DEMO-SAAS-STARTER",
                "slug": "starter",
                "title": "Стартовый",
                "price": Decimal("990.00"),
                "is_default": True,
                "option_value": {"title": "Стартовый", "slug": "starter"},
                "inclusions": [
                    {"title": "До 3 пользователей", "is_included": True, "group": "Лимиты"},
                    {"title": "1 000 контактов", "is_included": True, "group": "Лимиты"},
                    {"title": "Email-рассылки", "is_included": False, "group": "Функции"},
                    {"title": "Воронка продаж", "is_included": True, "group": "Функции"},
                    {"title": "API-доступ", "is_included": False, "group": "Интеграции"},
                    {"title": "Приоритетная поддержка", "is_included": False, "group": "Поддержка"},
                ],
            },
            {
                "sku": "DEMO-SAAS-BUSINESS",
                "slug": "business",
                "title": "Бизнес",
                "price": Decimal("2990.00"),
                "option_value": {"title": "Бизнес", "slug": "business"},
                "inclusions": [
                    {"title": "До 15 пользователей", "is_included": True, "group": "Лимиты"},
                    {"title": "10 000 контактов", "is_included": True, "group": "Лимиты"},
                    {"title": "Email-рассылки", "is_included": True, "group": "Функции"},
                    {"title": "Воронка продаж", "is_included": True, "group": "Функции"},
                    {"title": "API-доступ", "is_included": True, "group": "Интеграции"},
                    {"title": "Приоритетная поддержка", "is_included": False, "group": "Поддержка"},
                ],
            },
            {
                "sku": "DEMO-SAAS-ENTERPRISE",
                "slug": "enterprise",
                "title": "Корпоративный",
                "price": Decimal("9990.00"),
                "option_value": {"title": "Корпоративный", "slug": "enterprise"},
                "inclusions": [
                    {"title": "Неограниченно пользователей", "is_included": True, "group": "Лимиты"},
                    {"title": "Неограниченно контактов", "is_included": True, "group": "Лимиты"},
                    {"title": "Email-рассылки", "is_included": True, "group": "Функции"},
                    {"title": "Воронка продаж", "is_included": True, "group": "Функции"},
                    {"title": "API-доступ", "is_included": True, "group": "Интеграции"},
                    {"title": "Приоритетная поддержка", "is_included": True, "group": "Поддержка"},
                ],
            },
        ],
    },
    {
        "sku": "DEMO-EBOOK-001",
        "slug": "design-patterns-book",
        "title": "Паттерны проектирования: практическое руководство",
        "brand": None,
        "product_type": "digital",
        "description": "Электронная книга о паттернах проектирования с примерами на Python и Go",
        "base_price": Decimal("790.00"),
        "option_group": {
            "title": "Формат",
            "slug": "format",
            "display_type": "buttons",
        },
        "variants": [
            {
                "sku": "DEMO-EBOOK-PDF",
                "slug": "pdf",
                "title": "PDF",
                "price": Decimal("790.00"),
                "is_default": True,
                "option_value": {"title": "PDF", "slug": "pdf"},
                "inclusions": [
                    {"title": "PDF-файл", "is_included": True},
                    {"title": "Обновления 1 год", "is_included": True},
                    {"title": "Исходный код примеров", "is_included": False},
                ],
            },
            {
                "sku": "DEMO-EBOOK-EPUB",
                "slug": "epub",
                "title": "ePub + PDF",
                "price": Decimal("990.00"),
                "option_value": {"title": "ePub + PDF", "slug": "epub"},
                "inclusions": [
                    {"title": "PDF + ePub файлы", "is_included": True},
                    {"title": "Обновления 1 год", "is_included": True},
                    {"title": "Исходный код примеров", "is_included": True},
                ],
            },
            {
                "sku": "DEMO-EBOOK-BUNDLE",
                "slug": "bundle",
                "title": "Полный комплект",
                "price": Decimal("1490.00"),
                "sale_price": Decimal("1190.00"),
                "option_value": {"title": "Полный комплект", "slug": "bundle"},
                "inclusions": [
                    {"title": "PDF + ePub + MOBI", "is_included": True},
                    {"title": "Пожизненные обновления", "is_included": True},
                    {"title": "Исходный код примеров", "is_included": True},
                ],
            },
        ],
    },
    {
        "sku": "DEMO-CONSULT-001",
        "slug": "it-consulting",
        "title": "IT-консалтинг: аудит инфраструктуры",
        "brand": None,
        "product_type": "service",
        "description": "Профессиональный аудит IT-инфраструктуры с рекомендациями по оптимизации",
        "base_price": Decimal("25000.00"),
        "option_group": {
            "title": "Пакет",
            "slug": "package",
            "display_type": "cards",
        },
        "variants": [
            {
                "sku": "DEMO-CONSULT-EXPRESS",
                "slug": "express",
                "title": "Экспресс-аудит",
                "price": Decimal("25000.00"),
                "is_default": True,
                "option_value": {"title": "Экспресс", "slug": "express"},
                "inclusions": [
                    {"title": "Анализ текущей инфраструктуры", "is_included": True},
                    {"title": "Отчёт с рекомендациями", "is_included": True},
                    {"title": "Внедрение решений", "is_included": False},
                    {"title": "Сопровождение 30 дней", "is_included": False},
                ],
            },
            {
                "sku": "DEMO-CONSULT-STANDARD",
                "slug": "standard",
                "title": "Стандартный аудит",
                "price": Decimal("75000.00"),
                "option_value": {"title": "Стандартный", "slug": "standard"},
                "inclusions": [
                    {"title": "Анализ текущей инфраструктуры", "is_included": True},
                    {"title": "Отчёт с рекомендациями", "is_included": True},
                    {"title": "Внедрение решений", "is_included": True},
                    {"title": "Сопровождение 30 дней", "is_included": False},
                ],
            },
            {
                "sku": "DEMO-CONSULT-PREMIUM",
                "slug": "premium",
                "title": "Премиум + сопровождение",
                "price": Decimal("150000.00"),
                "option_value": {"title": "Премиум", "slug": "premium"},
                "inclusions": [
                    {"title": "Анализ текущей инфраструктуры", "is_included": True},
                    {"title": "Отчёт с рекомендациями", "is_included": True},
                    {"title": "Внедрение решений", "is_included": True},
                    {"title": "Сопровождение 90 дней", "is_included": True},
                ],
            },
        ],
    },
]


async def find_tenant(db) -> Tenant:
    result = await db.execute(
        select(Tenant).where(
            Tenant.is_active == True,
            Tenant.deleted_at.is_(None),
        ).order_by(Tenant.created_at)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        print("ERROR: No active tenant found")
        sys.exit(1)
    return tenant


async def ensure_feature_flags(db, tenant_id):
    for flag_name in ("catalog_module", "variants_module"):
        existing = await db.execute(
            select(FeatureFlag).where(
                FeatureFlag.tenant_id == tenant_id,
                FeatureFlag.feature_name == flag_name,
            )
        )
        flag = existing.scalar_one_or_none()
        if flag:
            if not flag.enabled:
                flag.enabled = True
                print(f"  Enabled {flag_name}")
        else:
            db.add(FeatureFlag(
                id=uuid4(),
                tenant_id=tenant_id,
                feature_name=flag_name,
                enabled=True,
                description=f"Auto-enabled by seed script",
            ))
            print(f"  Created + enabled {flag_name}")


async def ensure_category(db, tenant_id) -> Category:
    result = await db.execute(
        select(Category).where(
            Category.tenant_id == tenant_id,
            Category.slug == "demo-catalog",
            Category.deleted_at.is_(None),
        )
    )
    cat = result.scalar_one_or_none()
    if cat:
        return cat

    cat = Category(
        tenant_id=tenant_id,
        title="Демо-каталог",
        slug="demo-catalog",
        description="Категория для тестовых товаров",
        is_active=True,
    )
    db.add(cat)
    await db.flush()
    print(f"  Created category: {cat.title}")
    return cat


async def product_exists(db, tenant_id, sku: str) -> bool:
    result = await db.execute(
        select(Product.id).where(
            Product.tenant_id == tenant_id,
            Product.sku == sku,
            Product.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none() is not None


async def create_product(db, tenant_id, category_id, data: dict):
    if await product_exists(db, tenant_id, data["sku"]):
        print(f"  SKIP: {data['sku']} already exists")
        return

    variant_prices = [v["price"] for v in data["variants"]]

    product = Product(
        tenant_id=tenant_id,
        sku=data["sku"],
        slug=data["slug"],
        title=data["title"],
        brand=data.get("brand"),
        product_type=data["product_type"],
        description=data.get("description"),
        is_active=True,
        has_variants=True,
        price_from=min(variant_prices),
        price_to=max(variant_prices),
    )
    db.add(product)
    await db.flush()

    db.add(ProductPrice(
        product_id=product.id,
        price_type="regular",
        amount=data["base_price"],
        currency="RUB",
    ))

    db.add(ProductCategory(
        product_id=product.id,
        category_id=category_id,
        is_primary=True,
    ))

    og_data = data["option_group"]
    option_group = ProductOptionGroup(
        product_id=product.id,
        tenant_id=tenant_id,
        title=og_data["title"],
        slug=og_data["slug"],
        display_type=og_data["display_type"],
        sort_order=0,
        is_required=True,
    )
    db.add(option_group)
    await db.flush()

    for i, v_data in enumerate(data["variants"]):
        ov = ProductOptionValue(
            option_group_id=option_group.id,
            title=v_data["option_value"]["title"],
            slug=v_data["option_value"]["slug"],
            sort_order=i,
        )
        db.add(ov)
        await db.flush()

        variant = ProductVariant(
            product_id=product.id,
            tenant_id=tenant_id,
            sku=v_data["sku"],
            slug=v_data["slug"],
            title=v_data["title"],
            is_default=v_data.get("is_default", False),
            is_active=True,
            sort_order=i,
            stock_quantity=v_data.get("stock"),
            weight=v_data.get("weight"),
        )
        db.add(variant)
        await db.flush()

        db.add(VariantPrice(
            variant_id=variant.id,
            price_type="regular",
            amount=v_data["price"],
            currency="RUB",
        ))

        if v_data.get("sale_price"):
            db.add(VariantPrice(
                variant_id=variant.id,
                price_type="sale",
                amount=v_data["sale_price"],
                currency="RUB",
            ))

        db.add(VariantOptionLink(
            variant_id=variant.id,
            option_value_id=ov.id,
        ))

        for j, inc in enumerate(v_data.get("inclusions", [])):
            db.add(VariantInclusion(
                variant_id=variant.id,
                title=inc["title"],
                is_included=inc["is_included"],
                sort_order=j,
                group=inc.get("group"),
            ))

    await db.flush()
    print(f"  Created: {data['title']} ({data['product_type']}) — {len(data['variants'])} variants")


async def main():
    print("=" * 60)
    print("Seed Catalog Demo: 5 products × 3 variants")
    print("=" * 60)

    async with get_db_context() as db:
        tenant = await find_tenant(db)
        print(f"\nTenant: {tenant.name} (id={tenant.id})")

        print("\n1. Feature flags:")
        await ensure_feature_flags(db, tenant.id)

        print("\n2. Category:")
        category = await ensure_category(db, tenant.id)

        print("\n3. Products:")
        for product_data in PRODUCTS:
            await create_product(db, tenant.id, category.id, product_data)

        await db.commit()
        print("\n" + "=" * 60)
        print("Done! All data committed.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
