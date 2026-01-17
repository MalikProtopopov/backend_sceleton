"""Seed database with test data and export to SQL.

Usage:
    python -m app.scripts.seed_database
"""

import asyncio
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from faker import Faker
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

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
from app.modules.company.models import (
    Address,
    AddressLocale,
    Advantage,
    AdvantageLocale,
    Contact,
    Employee,
    EmployeeLocale,
    EmployeePracticeArea,
    PracticeArea,
    PracticeAreaLocale,
    Service,
    ServiceLocale,
)
from app.modules.content.models import (
    Article,
    ArticleLocale,
    ArticleTopic,
    ArticleStatus,
    Case,
    CaseLocale,
    CaseServiceLink,
    FAQ,
    FAQLocale,
    Review,
    ReviewStatus,
    Topic,
    TopicLocale,
)
from app.modules.documents.models import Document, DocumentLocale, DocumentStatus
from app.modules.leads.models import Inquiry, InquiryForm, InquiryStatus
from app.modules.seo.models import Redirect, SEORoute
from app.modules.tenants.models import FeatureFlag, Tenant, TenantSettings

fake = Faker(["ru_RU", "en_US"])

# Fixed UUIDs for consistency
TENANT_ID = uuid4()
TENANT_SETTINGS_ID = uuid4()
ADMIN_USER_ID = uuid4()
ADMIN_ROLE_ID = uuid4()


async def create_tenant(db) -> Tenant:
    """Create or get test tenant."""
    print("🏢 Creating tenant...")
    
    from sqlalchemy import select
    
    # Check if tenant already exists
    result = await db.execute(
        select(Tenant).where(Tenant.slug == "test-company")
    )
    existing_tenant = result.scalar_one_or_none()
    
    if existing_tenant:
        print(f"  ⏭️  Tenant already exists: {existing_tenant.name}")
        # Update tenant settings if needed
        result = await db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == existing_tenant.id)
        )
        settings = result.scalar_one_or_none()
        if not settings:
            settings = TenantSettings(
                id=TENANT_SETTINGS_ID,
                tenant_id=existing_tenant.id,
                default_locale="ru",
                timezone="Europe/Moscow",
                date_format="DD.MM.YYYY",
                time_format="HH:mm",
                notify_on_inquiry=True,
                inquiry_email="leads@test.example.com",
            )
            db.add(settings)
            await db.flush()
        return existing_tenant
    
    tenant = Tenant(
        id=TENANT_ID,
        name="Test Company",
        slug="test-company",
        domain=f"test-{uuid4().hex[:8]}.example.com",  # Unique domain
        is_active=True,
        contact_email="info@test.example.com",
        contact_phone="+7 (999) 123-45-67",
        logo_url="/media/logo.png",
        primary_color="#00A3FF",
        extra_data={"founded": 2020, "team_size": "10-15"},
    )
    db.add(tenant)
    
    settings = TenantSettings(
        id=TENANT_SETTINGS_ID,
        tenant_id=tenant.id,
        default_locale="ru",
        timezone="Europe/Moscow",
        date_format="DD.MM.YYYY",
        time_format="HH:mm",
        notify_on_inquiry=True,
        inquiry_email="leads@test.example.com",
    )
    db.add(settings)
    
    await db.flush()
    print(f"  ✅ Created tenant: {tenant.name}")
    return tenant


async def create_permissions_and_roles(db, tenant_id: UUID) -> tuple[dict[str, Permission], dict[str, Role]]:
    """Create permissions and roles."""
    print("📋 Creating permissions and roles...")
    
    from sqlalchemy import select
    
    permissions_map = {}
    for code, name, resource, action in DEFAULT_PERMISSIONS:
        # Check if permission exists
        result = await db.execute(select(Permission).where(Permission.code == code))
        existing = result.scalar_one_or_none()
        if existing:
            permissions_map[code] = existing
        else:
            perm = Permission(
                id=uuid4(),
                code=code,
                name=name,
                resource=resource,
                action=action,
            )
            db.add(perm)
            permissions_map[code] = perm
    
    await db.flush()
    print(f"  ✅ Created/found {len(permissions_map)} permissions")
    
    roles_map = {}
    # Check if admin role exists
    result = await db.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.name == "admin")
    )
    admin_role = result.scalar_one_or_none()
    
    if not admin_role:
        admin_role = Role(
            id=ADMIN_ROLE_ID,
            tenant_id=tenant_id,
            name="admin",
            description="Full access",
            is_system=True,
        )
        db.add(admin_role)
        await db.flush()
        
        # Assign all permissions to admin
        for perm in permissions_map.values():
            rp = RolePermission(
                id=uuid4(),
                role_id=admin_role.id,
                permission_id=perm.id,
            )
            db.add(rp)
        await db.flush()
    
    roles_map["admin"] = admin_role
    print(f"  ✅ Created/found admin role")
    
    return permissions_map, roles_map


async def create_admin_user(db, admin_role: Role, tenant_id: UUID) -> AdminUser:
    """Create admin user."""
    print("👤 Creating admin user...")
    
    from sqlalchemy import select
    
    # Check if admin exists
    result = await db.execute(
        select(AdminUser).where(
            AdminUser.tenant_id == tenant_id,
            AdminUser.email == "admin@test.example.com"
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"  ⏭️  Admin user already exists: {existing.email}")
        return existing
    
    admin = AdminUser(
        id=ADMIN_USER_ID,
        tenant_id=tenant_id,
        email="admin@test.example.com",
        password_hash=hash_password("admin123"),
        first_name="Admin",
        last_name="User",
        role_id=admin_role.id,
        is_active=True,
        is_superuser=True,
    )
    db.add(admin)
    await db.flush()
    print(f"  ✅ Created admin: {admin.email} (password: admin123)")
    return admin


async def create_topics(db, tenant_id: UUID, count: int = 5) -> list[Topic]:
    """Create topics."""
    print(f"📂 Creating {count} topics...")
    
    topics = []
    topic_names = [
        ("Технологии", "technologies"),
        ("Бизнес", "business"),
        ("Дизайн", "design"),
        ("Маркетинг", "marketing"),
        ("Разработка", "development"),
    ]
    
    for i, (name_ru, slug) in enumerate(topic_names[:count]):
        topic = Topic(
            id=uuid4(),
            tenant_id=tenant_id,
            icon=f"icon-{i+1}",
            color=fake.hex_color(),
            sort_order=i,
        )
        db.add(topic)
        await db.flush()
        
        # Russian locale
        ru_locale = TopicLocale(
            id=uuid4(),
            topic_id=topic.id,
            locale="ru",
            title=name_ru,
            slug=slug,
            description=fake.text(max_nb_chars=200),
            meta_title=f"{name_ru} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = TopicLocale(
            id=uuid4(),
            topic_id=topic.id,
            locale="en",
            title=name_ru.title(),
            slug=f"{slug}-en",
            description=fake.text(max_nb_chars=200),
            meta_title=f"{name_ru.title()} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(en_locale)
        
        topics.append(topic)
    
    await db.flush()
    print(f"  ✅ Created {len(topics)} topics")
    return topics


async def create_articles(db, tenant_id: UUID, topics: list[Topic], author_id: UUID, count: int = 10) -> list[Article]:
    """Create articles."""
    print(f"📝 Creating {count} articles...")
    
    articles = []
    for i in range(count):
        status = ArticleStatus.PUBLISHED if i < 7 else ArticleStatus.DRAFT
        article = Article(
            id=uuid4(),
            tenant_id=tenant_id,
            status=status.value,
            published_at=datetime.now(UTC) - timedelta(days=i) if status == ArticleStatus.PUBLISHED else None,
            cover_image_url=f"/media/articles/article-{i+1}.jpg",
            reading_time_minutes=fake.random_int(min=3, max=15),
            view_count=fake.random_int(min=0, max=1000),
            author_id=author_id,
            sort_order=i,
        )
        db.add(article)
        await db.flush()
        
        # Russian locale
        ru_locale = ArticleLocale(
            id=uuid4(),
            article_id=article.id,
            locale="ru",
            title=fake.sentence(nb_words=6),
            slug=f"article-{i+1}-ru",
            excerpt=fake.text(max_nb_chars=200),
            content=f"<h2>{fake.sentence()}</h2><p>{fake.text(max_nb_chars=500)}</p>",
            meta_title=fake.sentence(nb_words=5)[:70],
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = ArticleLocale(
            id=uuid4(),
            article_id=article.id,
            locale="en",
            title=fake.sentence(nb_words=6),
            slug=f"article-{i+1}-en",
            excerpt=fake.text(max_nb_chars=200),
            content=f"<h2>{fake.sentence()}</h2><p>{fake.text(max_nb_chars=500)}</p>",
            meta_title=fake.sentence(nb_words=5)[:70],
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(en_locale)
        
        # Assign random topics
        if topics:
            selected_topics = fake.random_elements(elements=topics, length=fake.random_int(min=1, max=3), unique=True)
            for topic in selected_topics:
                article_topic = ArticleTopic(
                    id=uuid4(),
                    article_id=article.id,
                    topic_id=topic.id,
                )
                db.add(article_topic)
        
        articles.append(article)
    
    await db.flush()
    print(f"  ✅ Created {len(articles)} articles")
    return articles


async def create_services(db, tenant_id: UUID, count: int = 6) -> list[Service]:
    """Create services."""
    print(f"🛠️  Creating {count} services...")
    
    services = []
    service_names = [
        ("Веб-разработка", "web-development"),
        ("Мобильная разработка", "mobile-development"),
        ("E-Commerce", "ecommerce"),
        ("CRM системы", "crm"),
        ("ERP системы", "erp"),
        ("Консалтинг", "consulting"),
    ]
    
    for i, (name_ru, slug) in enumerate(service_names[:count]):
        service = Service(
            id=uuid4(),
            tenant_id=tenant_id,
            icon=f"icon-{i+1}",
            image_url=f"/media/services/service-{i+1}.jpg",
            price_from=fake.random_int(min=100000, max=2000000, step=50000),
            price_currency="RUB",
            is_published=True,
            sort_order=i,
        )
        db.add(service)
        await db.flush()
        
        # Russian locale
        ru_locale = ServiceLocale(
            id=uuid4(),
            service_id=service.id,
            locale="ru",
            title=name_ru,
            slug=slug,
            short_description=fake.text(max_nb_chars=200),
            description=f"<h3>Описание</h3><p>{fake.text(max_nb_chars=500)}</p>",
            meta_title=f"{name_ru} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = ServiceLocale(
            id=uuid4(),
            service_id=service.id,
            locale="en",
            title=name_ru.title(),
            slug=f"{slug}-en",
            short_description=fake.text(max_nb_chars=200),
            description=f"<h3>Description</h3><p>{fake.text(max_nb_chars=500)}</p>",
            meta_title=f"{name_ru.title()} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(en_locale)
        
        services.append(service)
    
    await db.flush()
    print(f"  ✅ Created {len(services)} services")
    return services


async def create_cases(db, tenant_id: UUID, services: list[Service], count: int = 5) -> list[Case]:
    """Create cases."""
    print(f"💼 Creating {count} cases...")
    
    cases = []
    for i in range(count):
        case = Case(
            id=uuid4(),
            tenant_id=tenant_id,
            status="published",
            published_at=datetime.now(UTC) - timedelta(days=i*10),
            cover_image_url=f"/media/cases/case-{i+1}.jpg",
            client_name=fake.company(),
            project_year=fake.random_int(min=2022, max=2024),
            project_duration=f"{fake.random_int(min=2, max=12)} months",
            is_featured=i < 3,
            sort_order=i,
        )
        db.add(case)
        await db.flush()
        
        # Russian locale
        ru_locale = CaseLocale(
            id=uuid4(),
            case_id=case.id,
            locale="ru",
            title=fake.sentence(nb_words=8),
            slug=f"case-{i+1}-ru",
            excerpt=fake.text(max_nb_chars=200),
            description=f"<h3>Задача</h3><p>{fake.text(max_nb_chars=300)}</p><h3>Решение</h3><p>{fake.text(max_nb_chars=300)}</p>",
            results=f"<ul><li>{fake.sentence()}</li><li>{fake.sentence()}</li></ul>",
            meta_title=fake.sentence(nb_words=5)[:70],
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = CaseLocale(
            id=uuid4(),
            case_id=case.id,
            locale="en",
            title=fake.sentence(nb_words=8),
            slug=f"case-{i+1}-en",
            excerpt=fake.text(max_nb_chars=200),
            description=f"<h3>Challenge</h3><p>{fake.text(max_nb_chars=300)}</p><h3>Solution</h3><p>{fake.text(max_nb_chars=300)}</p>",
            results=f"<ul><li>{fake.sentence()}</li><li>{fake.sentence()}</li></ul>",
            meta_title=fake.sentence(nb_words=5)[:70],
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(en_locale)
        
        # Link to random services
        if services:
            selected_services = fake.random_elements(elements=services, length=fake.random_int(min=1, max=3), unique=True)
            for service in selected_services:
                link = CaseServiceLink(
                    id=uuid4(),
                    case_id=case.id,
                    service_id=service.id,
                )
                db.add(link)
        
        cases.append(case)
    
    await db.flush()
    print(f"  ✅ Created {len(cases)} cases")
    return cases


async def create_reviews(db, tenant_id: UUID, cases: list[Case], count: int = 8) -> list[Review]:
    """Create reviews."""
    print(f"⭐ Creating {count} reviews...")
    
    reviews = []
    for i in range(count):
        status = ReviewStatus.APPROVED if i < 6 else ReviewStatus.PENDING
        review = Review(
            id=uuid4(),
            tenant_id=tenant_id,
            status=status.value,
            rating=fake.random_int(min=4, max=5),
            author_name=fake.name(),
            author_company=fake.company() if fake.boolean() else None,
            author_position=fake.job() if fake.boolean() else None,
            author_photo_url=f"/media/reviews/review-{i+1}.jpg" if fake.boolean() else None,
            content=fake.text(max_nb_chars=500),
            case_id=cases[i % len(cases)].id if cases and fake.boolean() else None,
            is_featured=i < 3,
            source=fake.random_element(elements=("google", "clutch", "yandex", None)),
            review_date=datetime.now(UTC) - timedelta(days=fake.random_int(min=1, max=180)),
            sort_order=i,
        )
        db.add(review)
        reviews.append(review)
    
    await db.flush()
    print(f"  ✅ Created {len(reviews)} reviews")
    return reviews


async def create_faqs(db, tenant_id: UUID, count: int = 6) -> list[FAQ]:
    """Create FAQs."""
    print(f"❓ Creating {count} FAQs...")
    
    faqs = []
    categories = ["General", "Process", "Pricing", "Technical"]
    
    for i in range(count):
        faq = FAQ(
            id=uuid4(),
            tenant_id=tenant_id,
            category=fake.random_element(elements=categories),
            is_published=True,
            sort_order=i,
        )
        db.add(faq)
        await db.flush()
        
        # Russian locale
        ru_locale = FAQLocale(
            id=uuid4(),
            faq_id=faq.id,
            locale="ru",
            question=fake.sentence(nb_words=8),
            answer=f"<p>{fake.text(max_nb_chars=300)}</p>",
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = FAQLocale(
            id=uuid4(),
            faq_id=faq.id,
            locale="en",
            question=fake.sentence(nb_words=8),
            answer=f"<p>{fake.text(max_nb_chars=300)}</p>",
        )
        db.add(en_locale)
        
        faqs.append(faq)
    
    await db.flush()
    print(f"  ✅ Created {len(faqs)} FAQs")
    return faqs


async def create_employees(db, tenant_id: UUID, count: int = 6) -> list[Employee]:
    """Create employees."""
    print(f"👥 Creating {count} employees...")
    
    employees = []
    positions = [
        "CEO",
        "CTO",
        "Lead Developer",
        "Senior Developer",
        "Designer",
        "Project Manager",
    ]
    
    for i, position in enumerate(positions[:count]):
        employee = Employee(
            id=uuid4(),
            tenant_id=tenant_id,
            photo_url=f"/media/employees/employee-{i+1}.jpg",
            email=fake.email(),
            phone=fake.phone_number(),
            linkedin_url=f"https://linkedin.com/in/{fake.user_name()}" if fake.boolean() else None,
            telegram_url=f"https://t.me/{fake.user_name()}" if fake.boolean() else None,
            is_published=True,
            sort_order=i,
        )
        db.add(employee)
        await db.flush()
        
        # Russian locale
        ru_locale = EmployeeLocale(
            id=uuid4(),
            employee_id=employee.id,
            locale="ru",
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            position=position,
            slug=f"employee-{i+1}-ru",
            bio=f"<p>{fake.text(max_nb_chars=300)}</p>",
            meta_title=f"{position} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = EmployeeLocale(
            id=uuid4(),
            employee_id=employee.id,
            locale="en",
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            position=position,
            slug=f"employee-{i+1}-en",
            bio=f"<p>{fake.text(max_nb_chars=300)}</p>",
            meta_title=f"{position} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(en_locale)
        
        employees.append(employee)
    
    await db.flush()
    print(f"  ✅ Created {len(employees)} employees")
    return employees


async def create_advantages(db, tenant_id: UUID, count: int = 5) -> list[Advantage]:
    """Create advantages."""
    print(f"✨ Creating {count} advantages...")
    
    advantages = []
    advantage_titles = [
        "Вовремя и в бюджет",
        "Полная прозрачность",
        "Результат, который продает",
        "Гарантия качества",
        "Опытная команда",
    ]
    
    for i, title in enumerate(advantage_titles[:count]):
        advantage = Advantage(
            id=uuid4(),
            tenant_id=tenant_id,
            icon=f"icon-{i+1}",
            is_published=True,
            sort_order=i,
        )
        db.add(advantage)
        await db.flush()
        
        # Russian locale
        ru_locale = AdvantageLocale(
            id=uuid4(),
            advantage_id=advantage.id,
            locale="ru",
            title=title,
            description=fake.text(max_nb_chars=200),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = AdvantageLocale(
            id=uuid4(),
            advantage_id=advantage.id,
            locale="en",
            title=title.title(),
            description=fake.text(max_nb_chars=200),
        )
        db.add(en_locale)
        
        advantages.append(advantage)
    
    await db.flush()
    print(f"  ✅ Created {len(advantages)} advantages")
    return advantages


async def create_practice_areas(db, tenant_id: UUID, count: int = 4) -> list[PracticeArea]:
    """Create practice areas."""
    print(f"🎯 Creating {count} practice areas...")
    
    practice_areas = []
    area_names = [
        ("E-Commerce", "ecommerce"),
        ("SaaS & Startups", "saas-startups"),
        ("Enterprise", "enterprise"),
        ("FinTech", "fintech"),
    ]
    
    for i, (name, slug) in enumerate(area_names[:count]):
        area = PracticeArea(
            id=uuid4(),
            tenant_id=tenant_id,
            icon=f"icon-{i+1}",
            is_published=True,
            sort_order=i,
        )
        db.add(area)
        await db.flush()
        
        # Russian locale
        ru_locale = PracticeAreaLocale(
            id=uuid4(),
            practice_area_id=area.id,
            locale="ru",
            title=name,
            slug=slug,
            description=fake.text(max_nb_chars=200),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = PracticeAreaLocale(
            id=uuid4(),
            practice_area_id=area.id,
            locale="en",
            title=name,
            slug=f"{slug}-en",
            description=fake.text(max_nb_chars=200),
        )
        db.add(en_locale)
        
        practice_areas.append(area)
    
    await db.flush()
    print(f"  ✅ Created {len(practice_areas)} practice areas")
    return practice_areas


async def create_addresses(db, tenant_id: UUID) -> list[Address]:
    """Create addresses."""
    print("📍 Creating addresses...")
    
    address = Address(
        id=uuid4(),
        tenant_id=tenant_id,
        address_type="office",
        latitude=55.7558,
        longitude=37.6173,
        working_hours="9:00-18:00 пн-пт",
        phone="+7 (999) 123-45-67",
        email="office@test.example.com",
        is_primary=True,
        sort_order=0,
    )
    db.add(address)
    await db.flush()
    
    # Russian locale
    ru_locale = AddressLocale(
        id=uuid4(),
        address_id=address.id,
        locale="ru",
        name="Главный офис",
        country="Россия",
        city="Москва",
        street="ул. Примерная",
        building="10",
        postal_code="123456",
    )
    db.add(ru_locale)
    
    # English locale
    en_locale = AddressLocale(
        id=uuid4(),
        address_id=address.id,
        locale="en",
        name="Main Office",
        country="Russia",
        city="Moscow",
        street="Example Street",
        building="10",
        postal_code="123456",
    )
    db.add(en_locale)
    
    await db.flush()
    print("  ✅ Created 1 address")
    return [address]


async def create_contacts(db, tenant_id: UUID) -> list[Contact]:
    """Create contacts."""
    print("📞 Creating contacts...")
    
    contacts_data = [
        ("email", "info@test.example.com", "Email", "mail", True),
        ("phone", "+7 (999) 123-45-67", "Phone", "phone", True),
        ("telegram", "https://t.me/test", "Telegram", "send", False),
        ("linkedin", "https://linkedin.com/company/test", "LinkedIn", "linkedin", False),
    ]
    
    contacts = []
    for i, (contact_type, value, label, icon, is_primary) in enumerate(contacts_data):
        contact = Contact(
            id=uuid4(),
            tenant_id=tenant_id,
            contact_type=contact_type,
            value=value,
            label=label,
            icon=icon,
            is_primary=is_primary,
            sort_order=i,
        )
        db.add(contact)
        contacts.append(contact)
    
    await db.flush()
    print(f"  ✅ Created {len(contacts)} contacts")
    return contacts


async def create_documents(db, tenant_id: UUID, count: int = 5) -> list[Document]:
    """Create documents."""
    print(f"📄 Creating {count} documents...")
    
    documents = []
    doc_types = [
        ("Политика конфиденциальности", "privacy-policy"),
        ("Условия использования", "terms-of-service"),
        ("Пользовательское соглашение", "user-agreement"),
        ("Политика возврата", "refund-policy"),
        ("Лицензионное соглашение", "license-agreement"),
    ]
    
    for i, (name_ru, slug) in enumerate(doc_types[:count]):
        doc = Document(
            id=uuid4(),
            tenant_id=tenant_id,
            status="published",
            document_version=f"1.{i}",
            document_date=date.today() - timedelta(days=i*30),
            published_at=datetime.now(UTC) - timedelta(days=i*30),
            file_url=f"/media/documents/{slug}.pdf" if fake.boolean() else None,
            sort_order=i,
        )
        db.add(doc)
        await db.flush()
        
        # Russian locale
        ru_locale = DocumentLocale(
            id=uuid4(),
            document_id=doc.id,
            locale="ru",
            title=name_ru,
            slug=slug,
            excerpt=fake.text(max_nb_chars=200),
            full_description=f"<h2>Введение</h2><p>{fake.text(max_nb_chars=500)}</p>",
            meta_title=f"{name_ru} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(ru_locale)
        
        # English locale
        en_locale = DocumentLocale(
            id=uuid4(),
            document_id=doc.id,
            locale="en",
            title=name_ru.title(),
            slug=f"{slug}-en",
            excerpt=fake.text(max_nb_chars=200),
            full_description=f"<h2>Introduction</h2><p>{fake.text(max_nb_chars=500)}</p>",
            meta_title=f"{name_ru.title()} | Test Company",
            meta_description=fake.text(max_nb_chars=160),
        )
        db.add(en_locale)
        
        documents.append(doc)
    
    await db.flush()
    print(f"  ✅ Created {len(documents)} documents")
    return documents


async def create_inquiries(db, tenant_id: UUID, services: list[Service], count: int = 10) -> list[Inquiry]:
    """Create inquiries."""
    print(f"📧 Creating {count} inquiries...")
    
    inquiries = []
    statuses = ["new", "in_progress", "contacted", "completed", "spam"]
    
    for i in range(count):
        inquiry = Inquiry(
            id=uuid4(),
            tenant_id=tenant_id,
            status=fake.random_element(elements=statuses),
            name=fake.name(),
            email=fake.email(),
            phone=fake.phone_number(),
            company=fake.company() if fake.boolean() else None,
            message=fake.text(max_nb_chars=300),
            service_id=services[i % len(services)].id if services else None,
            utm_source=fake.random_element(elements=("google", "yandex", "direct", None)),
            utm_medium=fake.random_element(elements=("cpc", "organic", "referral", None)),
            utm_campaign=fake.word() if fake.boolean() else None,
            device_type=fake.random_element(elements=("desktop", "mobile", "tablet")),
            ip_address=fake.ipv4(),
            country=fake.country(),
            city=fake.city(),
        )
        db.add(inquiry)
        inquiries.append(inquiry)
    
    await db.flush()
    print(f"  ✅ Created {len(inquiries)} inquiries")
    return inquiries


async def create_feature_flags(db, tenant_id: UUID) -> list[FeatureFlag]:
    """Create feature flags."""
    print("🚩 Creating feature flags...")
    
    from sqlalchemy import select
    
    features = [
        "blog_module",
        "cases_module",
        "reviews_module",
        "team_module",
        "faq_module",
        "seo_advanced",
        "analytics_advanced",
        "multilang",
    ]
    
    flags = []
    for feature in features:
        # Check if flag exists
        result = await db.execute(
            select(FeatureFlag).where(
                FeatureFlag.tenant_id == tenant_id,
                FeatureFlag.feature_name == feature
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            flags.append(existing)
        else:
            flag = FeatureFlag(
                id=uuid4(),
                tenant_id=tenant_id,
                feature_name=feature,
                enabled=True,
                description=f"Enable {feature}",
            )
            db.add(flag)
            flags.append(flag)
    
    await db.flush()
    print(f"  ✅ Created/found {len(flags)} feature flags")
    return flags


async def export_to_sql(db, output_file: str, tenant_id: UUID | None = None):
    """Export database to SQL file."""
    print(f"💾 Exporting to SQL file: {output_file}")
    sql_content = []
    sql_content.append("-- Test Database Seed SQL")
    sql_content.append("-- Generated automatically")
    sql_content.append("-- Use: psql -U postgres -d cms_db -f mediann_seed.sql")
    sql_content.append("")
    sql_content.append("BEGIN;")
    sql_content.append("")
    
    # Get all tables in order
    tables = [
        ("tenants", "tenant_id"),
        ("tenant_settings", "tenant_id"),
        ("feature_flags", "tenant_id"),
        ("permissions", None),
        ("roles", "tenant_id"),
        ("role_permissions", "role_id"),
        ("admin_users", "tenant_id"),
        ("topics", "tenant_id"),
        ("topic_locales", "topic_id"),
        ("articles", "tenant_id"),
        ("article_locales", "article_id"),
        ("article_topics", "article_id"),
        ("services", "tenant_id"),
        ("service_locales", "service_id"),
        ("cases", "tenant_id"),
        ("case_locales", "case_id"),
        ("case_service_links", "case_id"),
        ("reviews", "tenant_id"),
        ("faqs", "tenant_id"),
        ("faq_locales", "faq_id"),
        ("employees", "tenant_id"),
        ("employee_locales", "employee_id"),
        ("employee_practice_areas", "employee_id"),
        ("advantages", "tenant_id"),
        ("advantage_locales", "advantage_id"),
        ("practice_areas", "tenant_id"),
        ("practice_area_locales", "practice_area_id"),
        ("addresses", "tenant_id"),
        ("address_locales", "address_id"),
        ("contacts", "tenant_id"),
        ("documents", "tenant_id"),
        ("document_locales", "document_id"),
        ("inquiry_forms", "tenant_id"),
        ("inquiries", "tenant_id"),
    ]
    
    for table_name, filter_col, filter_by_tenant in tables:
        try:
            # Use SAVEPOINT to isolate errors
            savepoint = await db.begin_nested()
            try:
                # Try to get table columns first
                result = await db.execute(
                    text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position")
                )
                column_names = [row[0] for row in result.fetchall()]
                
                if not column_names:
                    await savepoint.rollback()
                    continue
                
                # Build SELECT query with tenant filter if needed
                columns_str = ", ".join(column_names)
                order_by = "created_at" if "created_at" in column_names else column_names[0]
                
                where_clause = ""
                if tenant_id and filter_by_tenant and filter_col:
                    where_clause = f"WHERE {filter_col} = '{tenant_id}'"
                elif tenant_id and not filter_by_tenant and filter_col:
                    # For tables without direct tenant_id, filter through parent
                    # This is simplified - in practice might need joins
                    where_clause = ""
                
                query = f"SELECT {columns_str} FROM {table_name} {where_clause} ORDER BY {order_by}"
                result = await db.execute(text(query))
                rows = result.fetchall()
                
                if not rows:
                    await savepoint.rollback()
                    continue
                
                sql_content.append(f"-- ============================================================================")
                sql_content.append(f"-- {table_name.upper()}")
                sql_content.append(f"-- ============================================================================")
                sql_content.append("")
                
                for row in rows:
                    values = []
                    row_dict = dict(row._mapping)
                    for col in column_names:
                        val = row_dict.get(col)
                        if val is None:
                            values.append("NULL")
                        elif isinstance(val, datetime):
                            values.append(f"'{val.isoformat()}'::timestamptz")
                        elif isinstance(val, date):
                            values.append(f"'{val.isoformat()}'::date")
                        elif isinstance(val, str):
                            # Escape single quotes
                            escaped = val.replace("'", "''")
                            values.append(f"'{escaped}'")
                        elif isinstance(val, bool):
                            values.append("true" if val else "false")
                        elif isinstance(val, UUID):
                            values.append(f"'{str(val)}'::uuid")
                        elif isinstance(val, (dict, list)):
                            json_str = json.dumps(val, ensure_ascii=False, default=str)
                            escaped = json_str.replace("'", "''")
                            values.append(f"'{escaped}'::jsonb")
                        elif isinstance(val, (int, float)):
                            values.append(str(val))
                        else:
                            # Fallback: convert to string
                            escaped = str(val).replace("'", "''")
                            values.append(f"'{escaped}'")
                    
                    sql_content.append(f"INSERT INTO {table_name} ({', '.join(column_names)})")
                    sql_content.append(f"VALUES ({', '.join(values)});")
                    sql_content.append("")
                
                await savepoint.commit()
            except Exception as e:
                await savepoint.rollback()
                print(f"  ⚠️  Warning: Could not export {table_name}: {e}")
                continue
        except Exception as e:
            # Outer exception handler
            print(f"  ⚠️  Warning: Could not export {table_name}: {e}")
            continue
    
    sql_content.append("COMMIT;")
    sql_content.append("")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_content))
    
    print(f"  ✅ Exported to {output_file}")


async def main():
    """Main seeding function."""
    print("=" * 60)
    print("🌱 Seeding Database with Test Data")
    print("=" * 60)
    print()
    
    try:
        async with get_db_context() as db:
            # 1. Create or get tenant
            tenant = await create_tenant(db)
            await db.commit()
            
            # Use tenant ID from existing or new tenant
            global TENANT_ID
            TENANT_ID = tenant.id
            
            # 2. Create permissions and roles
            permissions_map, roles_map = await create_permissions_and_roles(db, tenant.id)
            await db.commit()
            
            # 3. Create admin user
            admin = await create_admin_user(db, roles_map["admin"], tenant.id)
            await db.commit()
            
            # 4. Create content
            topics = await create_topics(db, tenant.id, count=5)
            await db.commit()
            
            articles = await create_articles(db, tenant.id, topics, admin.id, count=10)
            await db.commit()
            
            services = await create_services(db, tenant.id, count=6)
            await db.commit()
            
            cases = await create_cases(db, tenant.id, services, count=5)
            await db.commit()
            
            reviews = await create_reviews(db, tenant.id, cases, count=8)
            await db.commit()
            
            faqs = await create_faqs(db, tenant.id, count=6)
            await db.commit()
            
            # 5. Create company info
            employees = await create_employees(db, tenant.id, count=6)
            await db.commit()
            
            advantages = await create_advantages(db, tenant.id, count=5)
            await db.commit()
            
            practice_areas = await create_practice_areas(db, tenant.id, count=4)
            await db.commit()
            
            addresses = await create_addresses(db, tenant.id)
            await db.commit()
            
            contacts = await create_contacts(db, tenant.id)
            await db.commit()
            
            # 6. Create documents
            documents = await create_documents(db, tenant.id, count=5)
            await db.commit()
            
            # 7. Create inquiries
            inquiries = await create_inquiries(db, tenant.id, services, count=10)
            await db.commit()
            
            # 8. Create feature flags
            flags = await create_feature_flags(db, tenant.id)
            await db.commit()
            
            # 9. Export to SQL (use separate connection for reading)
            output_file = "/Users/mak/mediannback/docs/test_db/mediann_seed.sql"
            # Create a fresh connection for export to avoid transaction issues
            from app.core.database import async_session_factory
            async with async_session_factory() as export_db:
                await export_db.rollback()  # Ensure clean state
                await export_to_sql(export_db, output_file, tenant.id)
            
            print()
            print("=" * 60)
            print("✅ Database seeding complete!")
            print("=" * 60)
            print()
            print("📊 Summary:")
            print(f"   - Tenant: 1")
            print(f"   - Topics: {len(topics)}")
            print(f"   - Articles: {len(articles)}")
            print(f"   - Services: {len(services)}")
            print(f"   - Cases: {len(cases)}")
            print(f"   - Reviews: {len(reviews)}")
            print(f"   - FAQs: {len(faqs)}")
            print(f"   - Employees: {len(employees)}")
            print(f"   - Documents: {len(documents)}")
            print(f"   - Inquiries: {len(inquiries)}")
            print()
            print("🔐 Login credentials:")
            print(f"   Email: admin@test.example.com")
            print(f"   Password: admin123")
            print(f"   Tenant ID: {tenant.id}")
            print()
            print(f"💾 SQL file: {output_file}")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

