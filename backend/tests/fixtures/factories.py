"""Factory Boy factories for test data generation."""

from datetime import datetime, timezone
from uuid import uuid4

import factory
from faker import Faker

from app.modules.auth.models import AdminUser, Role
from app.modules.company.models import Employee, Service
from app.modules.content.models import Article, ArticleLocale, FAQ, Review, Topic
from app.modules.leads.models import Inquiry
from app.modules.tenants.models import Tenant

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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class RoleFactory(factory.Factory):
    """Factory for Role model."""

    class Meta:
        model = Role

    id = factory.LazyFunction(uuid4)
    name = factory.Faker("random_element", elements=["admin", "content_manager", "marketer"])
    description = factory.LazyFunction(lambda: fake.sentence())
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class TopicFactory(factory.Factory):
    """Factory for Topic model."""

    class Meta:
        model = Topic

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    slug = factory.LazyFunction(lambda: fake.slug())
    sort_order = factory.Sequence(lambda n: n)
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class FAQFactory(factory.Factory):
    """Factory for FAQ model."""

    class Meta:
        model = FAQ

    id = factory.LazyFunction(uuid4)
    tenant_id = factory.LazyFunction(uuid4)
    sort_order = factory.Sequence(lambda n: n)
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


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
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))

