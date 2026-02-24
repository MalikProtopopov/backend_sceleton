"""Factory Boy factories for test data generation."""

from datetime import UTC, datetime
from uuid import uuid4

import factory
from faker import Faker

from app.modules.auth.models import AdminUser, AuditLog, Permission, Role, RolePermission
from app.modules.catalog.models import Category, Product, ProductImage, UOM
from app.modules.company.models import Employee, Service
from app.modules.content.models import FAQ, Article, ArticleLocale, Review, Topic
from app.modules.leads.models import Inquiry
from app.modules.tenants.models import FeatureFlag, Tenant

fake = Faker("ru_RU")


class TenantFactory(factory.Factory):
    """Factory for Tenant model."""

    class Meta:
        model = Tenant

    id = factory.LazyFunction(uuid4)
    slug = factory.LazyFunction(lambda: fake.slug())
    name = factory.LazyFunction(lambda: fake.company())
    domain = factory.LazyFunction(lambda: fake.domain_name())
    plan = factory.Faker("random_element", elements=["starter", "pro", "enterprise"])
    is_active = True
    extra_data = factory.LazyFunction(dict)
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class RoleFactory(factory.Factory):
    """Factory for Role model."""

    class Meta:
        model = Role

    id = factory.LazyFunction(uuid4)
    name = factory.Faker("random_element", elements=["admin", "content_manager", "marketer"])
    description = factory.LazyFunction(lambda: fake.sentence())
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))


class AdminUserFactory(factory.Factory):
    """Factory for AdminUser model."""

    class Meta:
        model = AdminUser

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    email = factory.LazyFunction(lambda: fake.email())
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4TxK6VE9EnOjKvTq"  # "testpass123"
    first_name = factory.LazyFunction(lambda: fake.first_name())
    last_name = factory.LazyFunction(lambda: fake.last_name())
    role_id = factory.LazyFunction(uuid4)
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class ServiceFactory(factory.Factory):
    """Factory for Service model."""

    class Meta:
        model = Service

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    slug = factory.LazyFunction(lambda: fake.slug())
    icon_url = factory.LazyFunction(lambda: fake.image_url())
    is_featured = factory.Faker("boolean")
    sort_order = factory.Sequence(lambda n: n)
    status = "published"
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class EmployeeFactory(factory.Factory):
    """Factory for Employee model."""

    class Meta:
        model = Employee

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    slug = factory.LazyFunction(lambda: fake.slug())
    email = factory.LazyFunction(lambda: fake.email())
    phone = factory.LazyFunction(lambda: fake.phone_number())
    photo_url = factory.LazyFunction(lambda: fake.image_url())
    sort_order = factory.Sequence(lambda n: n)
    status = "published"
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class TopicFactory(factory.Factory):
    """Factory for Topic model."""

    class Meta:
        model = Topic

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    slug = factory.LazyFunction(lambda: fake.slug())
    sort_order = factory.Sequence(lambda n: n)
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class ArticleFactory(factory.Factory):
    """Factory for Article model."""

    class Meta:
        model = Article

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    slug = factory.LazyFunction(lambda: fake.slug())
    topic_id = None
    cover_image_url = factory.LazyFunction(lambda: fake.image_url())
    is_featured = factory.Faker("boolean")
    status = factory.Faker("random_element", elements=["draft", "published", "archived"])
    published_at = None
    view_count = factory.Faker("random_int", min=0, max=1000)
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class ArticleLocaleFactory(factory.Factory):
    """Factory for ArticleLocale model."""

    class Meta:
        model = ArticleLocale

    id = factory.LazyFunction(uuid4)
    article_id = factory.LazyFunction(uuid4)
    locale = factory.Faker("random_element", elements=["ru", "en", "kz"])
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=6))
    excerpt = factory.LazyFunction(lambda: fake.paragraph(nb_sentences=2))
    content = factory.LazyFunction(lambda: fake.text(max_nb_chars=500))
    meta_title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    meta_description = factory.LazyFunction(lambda: fake.paragraph(nb_sentences=1))
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class FAQFactory(factory.Factory):
    """Factory for FAQ model."""

    class Meta:
        model = FAQ

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    sort_order = factory.Sequence(lambda n: n)
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class InquiryFactory(factory.Factory):
    """Factory for Inquiry model."""

    class Meta:
        model = Inquiry

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    form_id = None
    name = factory.LazyFunction(lambda: fake.name())
    email = factory.LazyFunction(lambda: fake.email())
    phone = factory.LazyFunction(lambda: fake.phone_number())
    company = factory.LazyFunction(lambda: fake.company())
    message = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    status = "new"
    # Analytics
    source_url = factory.LazyFunction(lambda: fake.url())
    referrer = factory.LazyFunction(lambda: fake.url())
    utm_source = factory.Faker("random_element", elements=["google", "yandex", "direct", None])
    utm_medium = factory.Faker("random_element", elements=["cpc", "organic", "referral", None])
    utm_campaign = factory.LazyFunction(lambda: fake.word())
    ip_address = factory.LazyFunction(lambda: fake.ipv4())
    user_agent = factory.LazyFunction(lambda: fake.user_agent())
    device_type = factory.Faker("random_element", elements=["desktop", "mobile", "tablet"])
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class ReviewFactory(factory.Factory):
    """Factory for Review model."""

    class Meta:
        model = Review

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    author_name = factory.LazyFunction(lambda: fake.name())
    author_company = factory.LazyFunction(lambda: fake.company())
    author_position = factory.LazyFunction(lambda: fake.job())
    author_photo_url = factory.LazyFunction(lambda: fake.image_url())
    content = factory.LazyFunction(lambda: fake.text(max_nb_chars=300))
    rating = factory.Faker("random_int", min=1, max=5)
    status = factory.Faker("random_element", elements=["pending", "approved", "rejected"])
    case_id = None
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class FeatureFlagFactory(factory.Factory):
    """Factory for FeatureFlag model."""

    class Meta:
        model = FeatureFlag

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    feature_name = factory.Faker(
        "random_element",
        elements=[
            "blog_module", "cases_module", "reviews_module", "faq_module",
            "team_module", "services_module", "seo_advanced", "multilang",
            "analytics_advanced", "catalog_module",
        ],
    )
    enabled = True
    description = factory.LazyFunction(lambda: fake.sentence())
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class AuditLogFactory(factory.Factory):
    """Factory for AuditLog model."""

    class Meta:
        model = AuditLog

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    user_id = factory.LazyFunction(uuid4)
    resource_type = factory.Faker(
        "random_element", elements=["user", "tenant", "role", "feature_flag", "auth"]
    )
    resource_id = factory.LazyFunction(uuid4)
    action = factory.Faker(
        "random_element", elements=["create", "update", "delete", "login", "logout"]
    )
    changes = factory.LazyFunction(dict)
    ip_address = factory.LazyFunction(lambda: fake.ipv4())
    user_agent = factory.LazyFunction(lambda: fake.user_agent())
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))


class PermissionFactory(factory.Factory):
    """Factory for Permission model."""

    class Meta:
        model = Permission

    id = factory.LazyFunction(uuid4)
    code = factory.LazyFunction(lambda: f"{fake.word()}:{fake.word()}")
    name = factory.LazyFunction(lambda: fake.sentence(nb_words=3))
    description = factory.LazyFunction(lambda: fake.sentence())
    resource = factory.LazyFunction(lambda: fake.word())
    action = factory.Faker("random_element", elements=["read", "create", "update", "delete"])
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class RolePermissionFactory(factory.Factory):
    """Factory for RolePermission model."""

    class Meta:
        model = RolePermission

    id = factory.LazyFunction(uuid4)
    role_id = factory.LazyFunction(uuid4)
    permission_id = factory.LazyFunction(uuid4)


class UOMFactory(factory.Factory):
    class Meta:
        model = UOM

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    name = factory.Faker("random_element", elements=["Kilogram", "Piece", "Meter", "Liter"])
    code = factory.LazyFunction(lambda: fake.lexify(text="???").upper())
    symbol = factory.Faker("random_element", elements=["kg", "pcs", "m", "L"])
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class CategoryFactory(factory.Factory):
    class Meta:
        model = Category

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    title = factory.LazyFunction(lambda: fake.word().capitalize())
    slug = factory.LazyFunction(lambda: fake.slug())
    parent_id = None
    description = factory.LazyFunction(lambda: fake.sentence())
    is_active = True
    sort_order = factory.Sequence(lambda n: n)
    version = 1
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class ProductFactory(factory.Factory):
    class Meta:
        model = Product

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    sku = factory.LazyFunction(lambda: fake.bothify(text="SKU-####-??").upper())
    slug = factory.LazyFunction(lambda: fake.slug())
    title = factory.LazyFunction(lambda: fake.catch_phrase())
    brand = factory.LazyFunction(lambda: fake.company())
    model = factory.LazyFunction(lambda: fake.bothify(text="Model-??##"))
    description = factory.LazyFunction(lambda: fake.text(max_nb_chars=200))
    is_active = True
    version = 1
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class ProductImageFactory(factory.Factory):
    class Meta:
        model = ProductImage

    id = factory.LazyFunction(uuid4)
    product_id = factory.LazyFunction(uuid4)
    storage_key = factory.LazyFunction(lambda: f"products/{uuid4()}.jpg")
    url = factory.LazyFunction(lambda: fake.image_url())
    alt = factory.LazyFunction(lambda: fake.sentence(nb_words=3))
    sort_order = factory.Sequence(lambda n: n)
    is_cover = False
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))

