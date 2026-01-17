# Архитектура Backend-Движка Корпоративного Сайта
## (SaaS-переиспользуемое решение на FastAPI + PostgreSQL)

---

## ОГЛАВЛЕНИЕ
1. [Обзор и принципы](#обзор-и-принципы)
2. [JTBD и роли пользователей](#jtbd-и-роли-пользователей)
3. [Bounded Contexts и домены](#bounded-contexts-и-домены)
4. [Проектирование БД](#проектирование-бд)
5. [Проектирование API](#проектирование-api)
6. [Требования к функционалу](#требования-к-функционалу)
7. [Архитектура FastAPI](#архитектура-fastapi)
8. [Риски и антипаттерны](#риски-и-антипаттерны)
9. [План реализации](#план-реализации)

---

## Обзор и принципы

### Цели системы
- **Переиспользуемость**: Один движок на несколько клиентов с удобной кастомизацией
- **Масштабируемость**: Поддержка сотен клиентов, тысяч контентных элементов
- **Консистентность API**: Единые форматы, ошибки, пагинация, версионирование
- **SEO-готовность**: Управление метатегами, hreflang, canonical, robots, json-ld
- **Локализация**: Легко добавлять языки без изменения схемы БД
- **Удобство администрирования**: Черновики, публикация, аудит, RBAC

### Ключевые принципы

| Принцип | Обоснование |
|---------|-----------|
| **Shared-schema multi-tenancy** | Единая БД на всех клиентов + `tenant_id` в каждой таблице = дешевое масштабирование + RLS для изоляции |
| **REST с версионированием в URL** | `/api/v1/` — явно видно, какую версию использует клиент |
| **Translation tables для локализаций** | Хорошо масштабируется, эффективно по памяти, чистые запросы без JSONB |
| **Separate tables для сущностей** | Лучше, чем универсальный EAV, явная схема + валидация на уровне БД |
| **Page Builder через blocks** | Гибкие секции без денормализации: `page_sections` + `content_blocks` |
| **DDD-слои в коде** | Routers (HTTP) → Application (use cases) → Domain (business logic) → Repositories (data) |
| **Audit log для всех изменений** | Кто что менял и когда — требование для перепродаваемого решения |
| **ETag + Cache-Control для public API** | Скорость и эффективность трафика для фронта |

---

## JTBD и роли пользователей

### 1. Владелец компании / Директор

**Job Statement:** Быстро понять, как компания выглядит онлайн, управлять ключевыми данными (тим, услуги, отзывы).

| Аспект | Детали |
|--------|--------|
| **Успешный результат** | Сайт актуален, контакты и услуги видны, отзывы собраны |
| **Частые задачи** | Просмотр статистики (кол-во лидов, просмотров), обновление услуг, проверка отзывов, публикация новостей |
| **Сущности/поля** | Services, Cases, Reviews, Leads, Articles, Contacts, Advantages |
| **Требования к API** | Дашборд (readonly endpoints), экспорт лидов (CSV), фильтры по статусу и дате |

### 2. Маркетолог

**Job Statement:** Продвигать компанию через контент, кейсы, SEO.

| Аспект | Детали |
|--------|--------|
| **Успешный результат** | Новые кейсы в портфолио, высокие позиции в Google, релевантный контент, трафик растет |
| **Частые задачи** | Загрузить кейс (описание + фото + услуги), написать статью, настроить мета-теги (title, description, og:image), проверить hreflang/canonical |
| **Сущности/поля** | Cases (+ files), Articles, Topics, SEO Routes, Locales |
| **Требования к API** | Bulk upload кейсов, просмотр SEO метаданных по URL, экспорт для аудита (тех SEO инструменты) |

### 3. Контент-менеджер

**Job Statement:** Наполнять и обновлять контент на разных языках, управлять FAQ и блогом.

| Аспект | Детали |
|--------|--------|
| **Успешный результат** | Контент на всех языках, черновики залиты, фактические ошибки исправлены |
| **Частые задачи** | Написать статью на RU, скопировать на EN с переводом, опубликовать, добавить в категорию; создать FAQ; обновить описание услуги |
| **Сущности/поля** | Articles, Topics, FAQ, Services + переводы (article_locales, service_locales) |
| **Требования к API** | Работа с черновиками, preview по URL, bulk update (изменить все переводы сразу), история версий |

### 4. HR / PR

**Job Statement:** Управлять командой, показывать экспертизу, собирать информацию о сотрудниках.

| Аспект | Детали |
|--------|--------|
| **Успешный результат** | Все сотрудники профилированы (имя, должность, специализация), видны на сайте, данные актуальны |
| **Частые задачи** | Добавить сотрудника, выбрать направления работы, загрузить фото, опубликовать; обновить должность; скрыть уволенного |
| **Сущности/поля** | Employees, Practice Areas, Employees_Practice_Areas |
| **Требования к API** | Быстро добавить/удалить сотрудника, множественные направления (many-to-many), сортировка (кто главный эксперт) |

### 5. SEO-специалист

**Job Statement:** Оптимизировать сайт для поиска, настроить многоязычность, отследить метрики.

| Аспект | Детали |
|--------|--------|
| **Успешный результат** | Хорошие рейтинги в Google, правильная структура hreflang, нет 404, правильный canonical |
| **Частые задачи** | Импортировать SEO метаданные (title, description, og-теги) по путям; проверить redirects; настроить robots directives; генерировать sitemap |
| **Сущности/поля** | SEO Routes, Redirects, Locales (для hreflang), SEO настройки (robots.txt, canonical strategy) |
| **Требования к API** | Bulk update SEO по списку путей, экспорт для SEO инструментов, автогенерация hreflang, sitemap endpoint |

### 6. Администратор системы

**Job Statement:** Управлять пользователями, ролями, мониторить здоровье системы, аудит.

| Аспект | Детали |
|--------|--------|
| **Успешный результат** | Система стабильна, нет несанкционированного доступа, логи полные, легко восстановить данные |
| **Частые задачи** | Добавить/удалить юзера, выдать роль, посмотреть кто что менял и когда (audit log), перезагрузить кеш, проверить health |
| **Сущности/поля** | Admin Users, Roles, Permissions, Audit Log, Tenant Config |
| **Требования к API** | Full CRUD on users/roles, audit log с фильтрами, health check, cache invalidation |

### 7. Посетитель сайта / Клиент

**Job Statement:** Найти информацию о компании, её услугах, команде, оставить заявку.

| Аспект | Детали |
|--------|--------|
| **Успешный результат** | Быстрый загрузка, понял услуги, заполнил форму (lead), контакты нашел |
| **Частые задачи** | Просмотр услуг (list), просмотр портфолио (cases), чтение блога, просмотр команды, заполнение формы контакта |
| **Сущности/поля** | Services, Cases, Articles, Employees, FAQ, Contacts, Addresses |
| **Требования к API** | Быстро отвечает (кеш), список (paginated, filtered), поиск (по названию), доступны только опубликованные |

---

## Bounded Contexts и домены

### 1. Content
Управление страницами, статьями, темами, блоками контента.

**Сущности:** articles, topics, page_sections, content_blocks

### 2. Company
Управление услугами, направлениями работы, сотрудниками, преимуществами.

**Сущности:** services, practice_areas, employees, employee_practice_areas, advantages, addresses

### 3. Social Proof
Кейсы, отзывы, кейсы с услугами.

**Сущности:** cases, reviews, case_services

### 4. Support
FAQ, контактная информация, справки.

**Сущности:** faq, contacts, addresses (+ связь с company)

### 5. Leads
Формы заявок, управление лидами.

**Сущности:** inquiries, inquiry_forms

### 6. Assets
Управление файлами, документами, изображениями.

**Сущности:** file_assets, attachments

### 7. SEO
Управление SEO метаданными, перенаправлениями, sitemap.

**Сущности:** seo_routes, redirects, seo_settings

### 8. Localization
Управление языками, переводами.

**Сущности:** locales_config, *_locales (для каждой translatable сущности)

### 9. Admin/Auth
Пользователи, роли, права, аудит.

**Сущности:** admin_users, roles, permissions, role_permissions, audit_log

---

## Проектирование БД

### Стратегия локализаций: Translation Tables (ВЫБРАНА)

**Структура:**
```
articles (id, slug, status, created_at, updated_at)
article_locales (id, article_id, locale, title, description, content, slug)

Constraints: (article_id, locale) = UNIQUE
```

**Плюсы:**
- Масштабируемость: добавляем язык без изменения схемы
- Эффективность памяти: только реальные переводы хранятся
- Чистые SQL-запросы: JOIN и готово
- Индексирование: по (article_id, locale), по slug
- Fallback: легко реализовать (JOIN с default locale)
- Уникальность slug: constraint на (locale, slug)

**Почему выбрана:** Для перепродаваемого решения, поддерживающего N языков, это стандарт.

---

## PostgreSQL Таблицы (выборка ключевых)

### Основные сущности

```sql
-- TENANTS (Multi-tenancy)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'starter',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- LOCALIZATION
CREATE TABLE locales_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    code VARCHAR(5) UNIQUE NOT NULL, -- 'en', 'ru', 'de'
    name VARCHAR(50) NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, code)
);

-- COMPANY: SERVICES
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    slug VARCHAR(255) NOT NULL,
    icon_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'published',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, slug)
);

CREATE TABLE service_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    locale_id UUID NOT NULL REFERENCES locales_config(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(service_id, locale_id),
    UNIQUE(locale_id, slug)
);

-- COMPANY: EMPLOYEES
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    slug VARCHAR(255) NOT NULL,
    photo_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'published',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, slug)
);

CREATE TABLE employee_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    locale_id UUID NOT NULL REFERENCES locales_config(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    bio TEXT,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(employee_id, locale_id),
    UNIQUE(locale_id, slug)
);

-- CONTENT: ARTICLES
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    slug VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'published', 'archived'
    published_at TIMESTAMPTZ,
    featured BOOLEAN DEFAULT false,
    featured_image_url VARCHAR(500),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, slug)
);

CREATE TABLE article_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    locale_id UUID NOT NULL REFERENCES locales_config(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL, -- SEO description
    content TEXT NOT NULL,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(article_id, locale_id),
    UNIQUE(locale_id, slug)
);

-- SEO
CREATE TABLE seo_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    locale_id UUID NOT NULL REFERENCES locales_config(id) ON DELETE CASCADE,
    path VARCHAR(500) NOT NULL, -- /services, /about/team
    title VARCHAR(255),
    description VARCHAR(500),
    og_title VARCHAR(255),
    og_description VARCHAR(500),
    og_image_url VARCHAR(500),
    canonical_url VARCHAR(500),
    robots_directive VARCHAR(100) DEFAULT 'index, follow',
    json_ld JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, locale_id, path)
);

-- LEADS
CREATE TABLE inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    company_name VARCHAR(255),
    message TEXT,
    status VARCHAR(20) DEFAULT 'new', -- 'new', 'read', 'contacted', 'converted', 'spam'
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ADMIN/AUTH
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(500) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role_id UUID REFERENCES roles(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, email)
);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, name)
);

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES admin_users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL, -- 'CREATE', 'UPDATE', 'DELETE'
    entity_type VARCHAR(100) NOT NULL, -- 'article', 'employee', 'service'
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## API Эндпоинты (выборка)

### Public API (read-only)

```
GET  /api/v1/public/services
     Params: locale, limit, page, sort, search
     Response: [{ id, name, description, icon_url, slug }]

GET  /api/v1/public/services/{slug}
     Params: locale
     Response: { id, name, description, icon_url, slug }

GET  /api/v1/public/articles
     Params: locale, topic_id, limit, page, sort, search
     Response: [{ id, title, slug, featured, published_at }]

GET  /api/v1/public/employees
     Params: locale, practice_area_id, limit, page, sort
     Response: [{ id, first_name, last_name, title, slug }]

GET  /api/v1/public/faq
     Params: locale, topic_id, limit, page
     Response: [{ id, question, answer }]

GET  /api/v1/public/sitemap.xml
     Response: XML

POST /api/v1/public/inquiries
     Body: { first_name, last_name, email, phone, message }
     Response: 201 { id, created_at }
```

### Admin API (CRUD + Permissions)

```
GET    /api/v1/admin/articles
       Params: status, topic_id, locale, limit, page
       Permission: view_articles
       Response: [{ id, slug, status, locales: [...] }]

POST   /api/v1/admin/articles
       Permission: create_articles
       Body: { slug, status, locales: {...} }
       Response: 201 { id, slug }

PATCH  /api/v1/admin/articles/{id}
       Permission: edit_articles
       Body: { status, featured, locales: {...} }
       Response: 200 { id }

DELETE /api/v1/admin/articles/{id}
       Permission: delete_articles
       Response: 204

GET    /api/v1/admin/seo/routes
       Permission: view_seo
       Response: [{ path, locale, title, description, canonical }]

PUT    /api/v1/admin/seo/routes
       Permission: edit_seo
       Body: { path, locale, title, description, canonical }
       Response: 200 { id }

GET    /api/v1/admin/audit-log
       Permission: view_audit
       Response: [{ action, entity_type, entity_id, user_id, old_values, new_values }]
```

### Authentication

```
POST /api/v1/auth/login
     Body: { email, password }
     Response: 200 { access_token, token_type, expires_in, user: {...} }

GET  /api/v1/admin/me
     Auth: Required (JWT)
     Response: { id, email, first_name, role: {...} }
```

---

## Ошибки (RFC 7807)

```json
{
  "type": "https://api.example.com/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more validation errors occurred",
  "errors": [
    { "field": "title", "message": "Title is required" },
    { "field": "slug", "message": "Slug must match pattern ^[a-z0-9-]+$" }
  ]
}
```

| Статус | Type | Title |
|--------|------|-------|
| 400 | bad_request | Bad Request |
| 422 | validation_error | Validation Error |
| 401 | unauthorized | Unauthorized |
| 403 | forbidden | Forbidden |
| 404 | not_found | Not Found |
| 409 | conflict | Conflict (unique constraint) |
| 429 | rate_limited | Too Many Requests |
| 500 | internal_server_error | Internal Server Error |

---

## Требования (MoSCoW)

### Must-have (MVP)
- JWT auth + RBAC
- Public API (read-only)
- Admin CRUD (все сущности)
- Localization (2+ языка)
- Draft/publish workflow
- Audit log
- Rate limiting (базовый)
- Пагинация и фильтры
- RFC 7807 ошибки

### Should-have (v1)
- hreflang автогенерация
- Bulk operations
- Full-text search
- File upload (S3)
- Page builder (blocks)
- Email notifications
- Cache headers (ETag)
- sitemap.xml
- Import/Export (CSV/JSON)
- Redirects management

### Nice-to-have (v2)
- Versioning контента
- Comments/moderation
- Templates
- Webhooks
- GraphQL API
- CLI tools

---

## Архитектура FastAPI

### Структура проекта

```
app/
├── main.py                         # Entry point
├── core/
│   ├── config.py                   # Settings
│   ├── security.py                 # JWT, auth
│   └── logging.py
├── db/
│   ├── session.py                  # SessionLocal, get_db
│   ├── base.py                     # Base for ORM
│   └── models.py                   # SQLAlchemy models
├── modules/                        # По доменам
│   ├── company/
│   │   ├── domain/                 # Business logic
│   │   ├── application/            # Use cases
│   │   ├── infrastructure/         # Repository
│   │   ├── api/                    # routes, schemas
│   │   └── schemas.py
│   ├── content/
│   ├── auth/
│   └── leads/
├── api/
│   └── v1/
│       ├── public/
│       └── admin/
├── middleware/
├── utils/
└── tasks/
```

### 4 слоя (DDD)

1. **API Layer (Routers)** — HTTP requests/responses
2. **Application Layer (Use Cases)** — Координация, транзакции
3. **Domain Layer (Entities, Services)** — Бизнес-логика
4. **Infrastructure Layer (Repositories, ORM)** — Доступ к данным

---

## Риски и решения

| Риск | Решение |
|------|---------|
| Data leakage между тенантами | RLS on DB + middleware + isolation tests |
| SEO ломается | DB constraints + hreflang auto-gen + robots meta |
| Контент теряется | Soft delete + audit log + backup (WAL) |
| Медленные запросы | Eager loading + индексы + ETag кеш |
| Дыры в локализации | (entity, default_locale) constraint + fallback |

---

## План реализации (90 дней)

| Фаза | Период | Выход |
|------|--------|-------|
| **1: Foundation** | 3-4 нед | PostgreSQL + FastAPI + basic CRUD + public API |
| **2: Content & Localization** | 2-3 нед | Articles + Topics + translation tables + audit |
| **3: SEO & Advanced** | 2 нед | SEO routes + hreflang + sitemap + bulk ops |
| **4: Files & Page Builder** | 2 нед | File upload + S3 + content blocks |
| **5: Advanced Admin** | 2 нед | User mgmt + full RBAC + import/export + notifications |
| **6: QA & Deployment** | 1-2 нед | Load testing + security audit + production |

---

## Заключение

Этот backend разработан для **масштабируемости, переиспользуемости и SEO-оптимизации**. 

**Ключевые решения:**
- Multi-tenancy: shared schema + tenant_id + RLS
- Локализация: translation tables
- Архитектура: DDD (4 слоя)
- API: REST v1, offset-based, RFC 7807
- SEO: управляемые метаданные, hreflang, canonical
- Аудит: log всех изменений
- Масштабируемость: индексы, eager loading, кеш

**Реализуемо за 3 месяца** (90-дневные спринты) по 6 фазам.
