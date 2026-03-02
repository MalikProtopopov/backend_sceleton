"""Billing system: modules, plans, bundles, tenant_modules, upgrade_requests.

Revision ID: 038
Revises: 037
Create Date: 2026-03-01
"""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_MODULES = [
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

_PLANS = [
    {
        "slug": "starter",
        "name": "Starter",
        "name_ru": "Стартовый",
        "description_ru": "Для небольших компаний и визиток",
        "price_monthly": 199000,
        "price_yearly": 190800,  # -20%
        "setup_fee": 999000,
        "is_default": True,
        "sort": 0,
        "limits": {
            "max_users": 2, "max_storage_mb": 5120, "max_leads_per_month": 500,
            "max_products": 0, "max_variants": 0, "max_domains": 1,
            "max_articles": 100, "max_rbac_roles": 2,
        },
        "modules": ["core", "content", "company", "crm_basic"],
    },
    {
        "slug": "business",
        "name": "Business",
        "name_ru": "Бизнес",
        "description_ru": "Для растущего бизнеса с SEO и аналитикой",
        "price_monthly": 499000,
        "price_yearly": 479000,
        "setup_fee": 1999000,
        "is_default": False,
        "sort": 1,
        "limits": {
            "max_users": 5, "max_storage_mb": 20480, "max_leads_per_month": 2000,
            "max_products": 0, "max_variants": 0, "max_domains": 3,
            "max_articles": 500, "max_rbac_roles": 5,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "documents"],
    },
    {
        "slug": "commerce",
        "name": "Commerce",
        "name_ru": "Коммерция",
        "description_ru": "Полный набор с каталогом товаров",
        "price_monthly": 999000,
        "price_yearly": 959000,
        "setup_fee": 4999000,
        "is_default": False,
        "sort": 2,
        "limits": {
            "max_users": 10, "max_storage_mb": 51200, "max_leads_per_month": 5000,
            "max_products": 5000, "max_variants": 10000, "max_domains": 5,
            "max_articles": -1, "max_rbac_roles": 10,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "catalog_basic", "catalog_pro", "documents"],
    },
    {
        "slug": "enterprise",
        "name": "Enterprise",
        "name_ru": "Корпоративный",
        "description_ru": "Индивидуальные условия для крупных клиентов",
        "price_monthly": 0,
        "price_yearly": 0,
        "setup_fee": 0,
        "is_default": False,
        "sort": 3,
        "limits": {
            "max_users": -1, "max_storage_mb": -1, "max_leads_per_month": -1,
            "max_products": -1, "max_variants": -1, "max_domains": -1,
            "max_articles": -1, "max_rbac_roles": -1,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "catalog_basic", "catalog_pro", "documents"],
    },
    {
        "slug": "agency",
        "name": "Agency",
        "name_ru": "Агентский",
        "description_ru": "Для агентств и реселлеров с дегрессивной шкалой",
        "price_monthly": 99000,
        "price_yearly": 95000,
        "setup_fee": 0,
        "is_default": False,
        "sort": 4,
        "limits": {
            "max_users": 3, "max_storage_mb": 10240, "max_leads_per_month": 1000,
            "max_products": 500, "max_variants": 1000, "max_domains": 2,
            "max_articles": 200, "max_rbac_roles": 3,
        },
        "modules": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced", "multilang", "catalog_basic", "catalog_pro", "documents"],
    },
]

_FLAG_TO_MODULE = {
    "blog_module": "content",
    "cases_module": "content",
    "reviews_module": "content",
    "faq_module": "content",
    "team_module": "company",
    "services_module": "company",
    "analytics_advanced": "crm_pro",
    "seo_advanced": "seo_advanced",
    "multilang": "multilang",
    "catalog_module": "catalog_basic",
    "variants_module": "catalog_pro",
}


def upgrade() -> None:
    # ── billing_modules ──
    op.create_table(
        "billing_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_ru", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("description_ru", sa.Text, nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("price_monthly_kopecks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_base", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price_monthly_kopecks >= 0", name="ck_billing_modules_price_positive"),
    )

    # ── billing_plans ──
    op.create_table(
        "billing_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_ru", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("description_ru", sa.Text, nullable=True),
        sa.Column("price_monthly_kopecks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("price_yearly_kopecks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("setup_fee_kopecks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("limits", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price_monthly_kopecks >= 0", name="ck_billing_plans_price_positive"),
        sa.CheckConstraint("setup_fee_kopecks >= 0", name="ck_billing_plans_setup_fee_positive"),
    )

    # ── billing_plan_modules (M:M) ──
    op.create_table(
        "billing_plan_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_modules.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("plan_id", "module_id", name="uq_plan_module"),
    )

    # ── billing_bundles ──
    op.create_table(
        "billing_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_ru", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("description_ru", sa.Text, nullable=True),
        sa.Column("price_monthly_kopecks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price_monthly_kopecks >= 0", name="ck_billing_bundles_price_positive"),
        sa.CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="ck_billing_bundles_discount_range"),
    )

    # ── billing_bundle_modules (M:M) ──
    op.create_table(
        "billing_bundle_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_bundles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_modules.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("bundle_id", "module_id", name="uq_bundle_module"),
    )

    # ── tenant_modules ──
    op.create_table(
        "tenant_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_modules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="plan"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("activated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "module_id", "source", name="uq_tenant_module_source"),
        sa.CheckConstraint("source IN ('plan', 'addon', 'bundle', 'manual')", name="ck_tenant_modules_source"),
    )
    op.create_index("ix_tenant_modules_lookup", "tenant_modules", ["tenant_id", "enabled"])

    # ── upgrade_requests ──
    op.create_table(
        "upgrade_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("request_type", sa.String(30), nullable=False),
        sa.Column("target_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_modules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_bundle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_bundles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("request_type IN ('plan_upgrade', 'module_addon', 'bundle_addon')", name="ck_upgrade_requests_type"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_upgrade_requests_status"),
    )
    op.create_index("ix_upgrade_requests_status", "upgrade_requests", ["tenant_id", "status"])

    # ── Add plan_id to tenants ──
    op.add_column(
        "tenants",
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("billing_plans.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_tenants_plan_id", "tenants", ["plan_id"])

    # ── Seed modules ──
    conn = op.get_bind()
    module_ids = {}
    for m in _MODULES:
        mid = uuid.uuid4()
        module_ids[m["slug"]] = mid
        conn.execute(
            sa.text(
                "INSERT INTO billing_modules (id, slug, name, name_ru, description, description_ru, "
                "category, price_monthly_kopecks, is_base, sort_order) "
                "VALUES (:id, :slug, :name, :name_ru, :description, :description_ru, "
                ":category, :price, :is_base, :sort)"
            ),
            {
                "id": mid, "slug": m["slug"], "name": m["name"], "name_ru": m["name_ru"],
                "description": m.get("description"), "description_ru": m.get("description_ru"),
                "category": m["category"], "price": m["price"],
                "is_base": m["is_base"], "sort": m["sort"],
            },
        )

    # ── Seed plans + plan_modules ──
    import json as _json

    plan_ids = {}
    for p in _PLANS:
        pid = uuid.uuid4()
        plan_ids[p["slug"]] = pid
        conn.execute(
            sa.text(
                "INSERT INTO billing_plans (id, slug, name, name_ru, description_ru, "
                "price_monthly_kopecks, price_yearly_kopecks, setup_fee_kopecks, "
                "is_default, is_active, sort_order, limits) "
                "VALUES (:id, :slug, :name, :name_ru, :description_ru, "
                ":pm, :py, :sf, :is_default, true, :sort, CAST(:limits AS jsonb))"
            ),
            {
                "id": pid, "slug": p["slug"], "name": p["name"], "name_ru": p["name_ru"],
                "description_ru": p.get("description_ru"),
                "pm": p["price_monthly"], "py": p["price_yearly"], "sf": p["setup_fee"],
                "is_default": p["is_default"], "sort": p["sort"],
                "limits": _json.dumps(p["limits"]),
            },
        )
        for mod_slug in p["modules"]:
            conn.execute(
                sa.text(
                    "INSERT INTO billing_plan_modules (id, plan_id, module_id) VALUES (:id, :pid, :mid)"
                ),
                {"id": uuid.uuid4(), "pid": pid, "mid": module_ids[mod_slug]},
            )

    # ── Migrate feature_flags to tenant_modules ──
    rows = conn.execute(sa.text("SELECT tenant_id, feature_name, enabled FROM feature_flags")).fetchall()
    seen = set()
    for row in rows:
        tenant_id, flag_name, enabled = row[0], row[1], row[2]
        mod_slug = _FLAG_TO_MODULE.get(flag_name)
        if not mod_slug or mod_slug not in module_ids:
            continue
        key = (str(tenant_id), mod_slug)
        if key in seen:
            continue
        seen.add(key)
        if enabled:
            conn.execute(
                sa.text(
                    "INSERT INTO tenant_modules (id, tenant_id, module_id, source, enabled) "
                    "VALUES (:id, :tid, :mid, 'manual', :enabled) "
                    "ON CONFLICT (tenant_id, module_id, source) DO NOTHING"
                ),
                {"id": uuid.uuid4(), "tid": tenant_id, "mid": module_ids[mod_slug], "enabled": enabled},
            )

    # Ensure every tenant has the 'core' module
    tenants = conn.execute(sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")).fetchall()
    for t in tenants:
        conn.execute(
            sa.text(
                "INSERT INTO tenant_modules (id, tenant_id, module_id, source, enabled) "
                "VALUES (:id, :tid, :mid, 'manual', true) "
                "ON CONFLICT (tenant_id, module_id, source) DO NOTHING"
            ),
            {"id": uuid.uuid4(), "tid": t[0], "mid": module_ids["core"]},
        )


def downgrade() -> None:
    op.drop_index("ix_tenants_plan_id", table_name="tenants")
    op.drop_column("tenants", "plan_id")
    op.drop_index("ix_upgrade_requests_status", table_name="upgrade_requests")
    op.drop_table("upgrade_requests")
    op.drop_index("ix_tenant_modules_lookup", table_name="tenant_modules")
    op.drop_table("tenant_modules")
    op.drop_table("billing_bundle_modules")
    op.drop_table("billing_bundles")
    op.drop_table("billing_plan_modules")
    op.drop_table("billing_plans")
    op.drop_table("billing_modules")
