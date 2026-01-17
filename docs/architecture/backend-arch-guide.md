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

### 1. **Content**
Управление страницами, статьями, темами, блоками контента.

**Сущности:**
- `articles` — статьи/посты
- `topics` — категории статей
- `page_sections` — секции на странице (для page builder)
- `content_blocks` — переиспользуемые блоки (текст, галерея, FAQ)

**Связи:**
- Article → Topics (many-to-many)
- Page → Page_Sections (one-to-many)
- Page_Sections → Content_Blocks (many-to-one)

**Инварианты:**
- Каждая статья может быть только в опубликованном или черновик статусе
- Slug уникален в пределах локали
- Черновики видны только админам

---

### 2. **Company**
Управление услугами, направлениями работы, сотрудниками, преимуществами.

**Сущности:**
- `services` — услуги компании
- `practice_areas` — направления работы / специализации
- `employees` — сотрудники / team members
- `employee_practice_areas` — связь (many-to-many)
- `advantages` — конкурентные преимущества
- `addresses` — адреса офисов (может быть несколько)

**Связи:**
- Practice_Area ← Employees (many-to-many)
- Service — используется в Cases (many-to-many)
- Address — адрес компании

**Инварианты:**
- У сотрудника может быть несколько направлений (упорядочены по sort_order)
- Адрес одной компании может быть несколько (основной + филиалы)
- Сотрудник может быть скрыт (soft delete + status)

---

### 3. **Social Proof**
Кейсы, отзывы, кейсы с услугами.

**Сущности:**
- `cases` — кейсы / case studies
- `reviews` — отзывы клиентов
- `case_services` — какие услуги применены в кейсе (many-to-many)

**Связи:**
- Case → Services (many-to-many)
- Case → Documents (attachments: фото, видео)
- Review — привязана к услуге или в целом к компании

**Инварианты:**
- Только опубликованные кейсы видны на public API
- Рейтинг отзыва 1-5, не может быть пусто
- Каждый кейс имеет slug (уникален в локали)

---

### 4. **Support**
FAQ, контактная информация, справки.

**Сущности:**
- `faq` — frequently asked questions
- `contacts` — контактный блок (телефон, email, форма)
- `addresses` — почтовые адреса (также связаны с Company)

**Связи:**
- FAQ → Topics (optional many-to-one)
- Contacts → Addresses (optional many-to-one)

**Инварианты:**
- FAQ упорядочены по sort_order
- Контакты могут быть скрыты (status)
- Адреса могут быть несколько (основной, филиалы)

---

### 5. **Leads**
Формы заявок, управление лидами.

**Сущности:**
- `inquiries` / `leads` — заявки от посетителей
- `inquiry_forms` — определение форм (какие поля, какая услуга, откуда пришла)

**Связи:**
- Inquiry → Service (optional, если заявка по услуге)
- Inquiry → InquiryForm (many-to-one)

**Инварианты:**
- Inquiry immutable after created (логирование)
- Статусы: new, read, contacted, converted, spam
- Email и phone — обязательные поля

---

### 6. **Assets**
Управление файлами, документами, изображениями.

**Сущности:**
- `documents` / `file_assets` — файлы (PDF, Word, изображения)
- `attachments` — связь между файлами и сущностями (polymorphic)

**Связи:**
- Document ← Article, Case, Employee (polymorphic many-to-one)
- Document хранится в S3-совместимом (MinIO) или локально

**Инварианты:**
- File_url генерируется с подписью (signed URL для приватных)
- Size_bytes и mime_type заполняются при загрузке
- Мягкое удаление (is_deleted flag)

---

### 7. **SEO**
Управление SEO метаданными, перенаправлениями, sitemap.

**Сущности:**
- `seo_routes` — метаданные по path + locale
- `redirects` — старые URL → новые URL
- `seo_settings` — глобальные параметры (robots.txt, default og:image, etc)

**Связи:**
- SEO_Route → Locale (many-to-one)
- Redirect из редиректится в SeoRoute (optional)

**Инварианты:**
- Path + locale = unique constraint
- Canonical может быть self или ссылка на другую локаль
- Robots: index, noindex, follow, nofollow комбинируются
- JSON-LD должно быть валидным JSON (валидируется при сохранении)

---

### 8. **Localization**
Управление языками, переводами.

**Сущности:**
- `locales_config` — доступные языки (en, ru, de, etc)
- `article_locales` — переводы статей
- `service_locales` — переводы услуг
- `employee_locales` — переводы профилей сотрудников
- (и так для каждой translatable сущности)

**Связи:**
- *_Locales → Entity (many-to-one)
- *_Locales → Locale (many-to-one)
- Constraint: Entity + Locale = unique

**Инварианты:**
- Для каждого опубликованного контента нужен перевод на default locale (atau fallback)
- Язык по умолчанию (is_default=true) всегда есть
- Slug в каждой локали unique

---

### 9. **Admin/Auth**
Пользователи, роли, права, аудит.

**Сущности:**
- `admin_users` — пользователи системы
- `roles` — роли (admin, content_manager, marketer, seo_specialist)
- `permissions` — права (view_leads, create_article, edit_seo, etc)
- `role_permissions` — связь (many-to-many)
- `audit_log` — логирование изменений

**Связи:**
- Admin_User → Role (many-to-one)
- Role → Permissions (many-to-many)
- Audit_Log → Admin_User (who changed)

**Инварианты:**
- Email админа уникален
- Пароль хранится как bcrypt hash (никогда plaintext)
- Audit log immutable
- Мягкое удаление пользователей (is_active flag)

---

## Проектирование БД

### Стратегия локализаций: Сравнение вариантов

#### Вариант A: Translation Tables (РЕКОМЕНДУЕТСЯ)

**Структура:**
```
articles (id, slug, status, created_at, updated_at)
article_locales (id, article_id, locale, title, description, content, slug)

Constraints: (article_id, locale) = UNIQUE
```

**Плюсы:**
- ✅ Масштабируемость: добавляем язык без изменения схемы
- ✅ Эффективность памяти: только реальные переводы хранятся
- ✅ Чистые SQL-запросы: JOIN и готово
- ✅ Индексирование: по (article_id, locale), по slug
- ✅ Fallback: легко реализовать (JOIN с default locale, если нет переводов)
- ✅ Уникальность slug: constraint на (locale, slug)

**Минусы:**
- ❌ Сложнее на один запрос (JOIN), но быстро и предсказуемо
- ❌ Нужна осторожность с транзакциями (consistency между article + article_locales)

**Как реализовать уникальность slug:**
```sql
UNIQUE (locale_id, slug)  -- где locale_id это FK на locales_config
```

**Fallback для missing translations:**
```sql
SELECT 
    COALESCE(
        (SELECT content FROM article_locales WHERE article_id = $1 AND locale = $2),
        (SELECT content FROM article_locales WHERE article_id = $1 AND locale = 'en')
    ) as content
```

---

#### Вариант B: JSONB Locales

**Структура:**
```
articles (
    id, slug, 
    locales: JSONB = {
        "en": {"title": "...", "slug": "...", "content": "..."},
        "ru": {"title": "...", "slug": "...", "content": "..."}
    },
    created_at, updated_at
)
```

**Плюсы:**
- ✅ Все в одном месте (привычно для некоторых)
- ✅ Быстрое чтение (нет JOIN)
- ✅ Гибкость: можно сохранить extra fields

**Минусы:**
- ❌ Индексирование сложное: нужны functional indexes → `CREATE INDEX idx_article_slug_en ON articles ((locales->>'en'->>'slug'))`
- ❌ Уникальность slug не гарантирует БД, нужно приложение
- ❌ Сложность запросов: JSONB operators везде
- ❌ Дыры в контенте: не видно, на какой локали не хватает перевода
- ❌ Масштабируемость: сложнее добавлять новые поля

**Рекомендация:** Подходит для 2-3 языков, иначе translation tables лучше.

---

#### Вариант C: Single Table (не рекомендуется)

```
articles (
    id, slug,
    title_en, title_ru, title_de,
    content_en, content_ru, content_de,
    ...
)
```

**Минусы:** Много NULL'ов, нельзя добавить язык без ALTER, дублирование логики.

---

### **ВЫБОР: Translation Tables**

**Причина:** Для перепродаваемого решения, которое должно поддерживать N языков, translation tables — стандарт. Масштабируется, чист, надежен.

---

### Полная схема таблиц PostgreSQL

```sql
-- ============ LOCALIZATION ============
CREATE TABLE locales_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    code VARCHAR(5) UNIQUE NOT NULL, -- 'en', 'ru', 'de'
    name VARCHAR(50) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_locales_tenant_default ON locales_config(tenant_id, is_default);

-- ============ COMPANY ============
CREATE TABLE practice_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(255) NOT NULL,
    icon_url VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'published', -- 'published', 'draft', 'archived'
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_practice_areas_tenant_status ON practice_areas(tenant_id, status);

CREATE TABLE practice_area_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    practice_area_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (practice_area_id, locale_id),
    UNIQUE (locale_id, slug),
    FOREIGN KEY (practice_area_id) REFERENCES practice_areas(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);
CREATE INDEX idx_practice_area_locales_slug ON practice_area_locales(locale_id, slug);

CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(255) NOT NULL,
    icon_url VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_services_tenant_status ON services(tenant_id, status);

CREATE TABLE service_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (service_id, locale_id),
    UNIQUE (locale_id, slug),
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);
CREATE INDEX idx_service_locales_slug ON service_locales(locale_id, slug);

CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(255) NOT NULL,
    photo_url VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_employees_tenant_status ON employees(tenant_id, status);
CREATE INDEX idx_employees_active ON employees(tenant_id, is_active);

CREATE TABLE employee_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    bio TEXT,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (employee_id, locale_id),
    UNIQUE (locale_id, slug),
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);
CREATE INDEX idx_employee_locales_slug ON employee_locales(locale_id, slug);

CREATE TABLE employee_practice_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID NOT NULL,
    practice_area_id UUID NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (employee_id, practice_area_id),
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (practice_area_id) REFERENCES practice_areas(id) ON DELETE CASCADE
);
CREATE INDEX idx_employee_practice_areas_employee ON employee_practice_areas(employee_id);
CREATE INDEX idx_employee_practice_areas_practice_area ON employee_practice_areas(practice_area_id);

CREATE TABLE addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'office', -- 'office', 'branch', 'warehouse'
    street_address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20),
    country_code VARCHAR(2) NOT NULL, -- ISO 3166-1 alpha-2
    phone VARCHAR(20),
    email VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_addresses_tenant_active ON addresses(tenant_id, is_active);

CREATE TABLE advantages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    icon_url VARCHAR(500),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_advantages_tenant ON advantages(tenant_id);

CREATE TABLE advantage_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advantage_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (advantage_id, locale_id),
    FOREIGN KEY (advantage_id) REFERENCES advantages(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);

-- ============ CONTENT ============
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_topics_tenant_status ON topics(tenant_id, status);

CREATE TABLE topic_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (topic_id, locale_id),
    UNIQUE (locale_id, slug),
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);
CREATE INDEX idx_topic_locales_slug ON topic_locales(locale_id, slug);

CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- 'draft', 'published', 'archived'
    published_at TIMESTAMPTZ,
    featured BOOLEAN NOT NULL DEFAULT false,
    featured_image_url VARCHAR(500),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_articles_tenant_status ON articles(tenant_id, status);
CREATE INDEX idx_articles_tenant_published_at ON articles(tenant_id, published_at DESC);
CREATE INDEX idx_articles_featured ON articles(tenant_id, featured, published_at DESC);

CREATE TABLE article_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL, -- SEO description
    content TEXT NOT NULL,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (article_id, locale_id),
    UNIQUE (locale_id, slug),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);
CREATE INDEX idx_article_locales_slug ON article_locales(locale_id, slug);
-- Полнотекстовый поиск для контента
CREATE INDEX idx_article_content_fts ON article_locales USING GIN (
    to_tsvector('english', title || ' ' || content)
);

CREATE TABLE article_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL,
    topic_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (article_id, topic_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);
CREATE INDEX idx_article_topics_topic ON article_topics(topic_id);

-- ============ SOCIAL PROOF ============
CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    slug VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    published_at TIMESTAMPTZ,
    featured BOOLEAN NOT NULL DEFAULT false,
    featured_image_url VARCHAR(500),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_cases_tenant_status ON cases(tenant_id, status);
CREATE INDEX idx_cases_featured ON cases(tenant_id, featured);

CREATE TABLE case_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    content TEXT,
    slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (case_id, locale_id),
    UNIQUE (locale_id, slug),
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);
CREATE INDEX idx_case_locales_slug ON case_locales(locale_id, slug);

CREATE TABLE case_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL,
    service_id UUID NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (case_id, service_id),
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
);
CREATE INDEX idx_case_services_case ON case_services(case_id);
CREATE INDEX idx_case_services_service ON case_services(service_id);

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    author_email VARCHAR(255),
    author_company VARCHAR(255),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    text TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_reviews_tenant_status ON reviews(tenant_id, status);
CREATE INDEX idx_reviews_rating ON reviews(tenant_id, rating DESC);

-- ============ SUPPORT ============
CREATE TABLE faq (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    topic_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL
);
CREATE INDEX idx_faq_tenant_topic ON faq(tenant_id, topic_id);
CREATE INDEX idx_faq_status ON faq(tenant_id, status);

CREATE TABLE faq_locales (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    faq_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (faq_id, locale_id),
    FOREIGN KEY (faq_id) REFERENCES faq(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);

CREATE TABLE contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(255),
    general_email VARCHAR(255),
    support_email VARCHAR(255),
    sales_phone VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE (tenant_id)
);

-- ============ LEADS ============
CREATE TABLE inquiry_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    service_id UUID,
    notification_email VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
);

CREATE TABLE inquiries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    form_id UUID NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    company_name VARCHAR(255),
    message TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'new', -- 'new', 'read', 'contacted', 'converted', 'spam'
    ip_address VARCHAR(45),
    user_agent TEXT,
    source VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (form_id) REFERENCES inquiry_forms(id) ON DELETE CASCADE
);
CREATE INDEX idx_inquiries_tenant_status ON inquiries(tenant_id, status);
CREATE INDEX idx_inquiries_created_at ON inquiries(tenant_id, created_at DESC);
CREATE INDEX idx_inquiries_email ON inquiries(tenant_id, email);

-- ============ ASSETS ============
CREATE TABLE file_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_key VARCHAR(1000) NOT NULL, -- S3 key или локальный path
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    width_px INTEGER,
    height_px INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_file_assets_tenant ON file_assets(tenant_id);

-- ============ SEO ============
CREATE TABLE seo_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    locale_id UUID NOT NULL,
    path VARCHAR(500) NOT NULL, -- /services, /about/team, /articles/seo-tips
    title VARCHAR(255),
    description VARCHAR(500),
    og_title VARCHAR(255),
    og_description VARCHAR(500),
    og_image_url VARCHAR(500),
    canonical_url VARCHAR(500), -- может быть self или другая локаль
    robots_directive VARCHAR(100) DEFAULT 'index, follow', -- 'index, follow', 'noindex, follow' и т.п.
    json_ld JSONB, -- structured data
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, locale_id, path),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (locale_id) REFERENCES locales_config(id) ON DELETE CASCADE
);
CREATE INDEX idx_seo_routes_path ON seo_routes(tenant_id, locale_id, path);

CREATE TABLE redirects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    from_path VARCHAR(500) NOT NULL,
    to_path VARCHAR(500) NOT NULL,
    status_code INTEGER NOT NULL DEFAULT 301, -- 301, 302, 307
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, from_path),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);
CREATE INDEX idx_redirects_from_path ON redirects(tenant_id, from_path);

-- ============ ADMIN / AUTH ============
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(500) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role_id UUID,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL
);
CREATE INDEX idx_admin_users_tenant_email ON admin_users(tenant_id, email);
CREATE INDEX idx_admin_users_active ON admin_users(tenant_id, is_active);

CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system BOOLEAN NOT NULL DEFAULT false, -- system roles: admin, content_manager, etc
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    code VARCHAR(100) NOT NULL, -- 'view_leads', 'edit_article', 'delete_user'
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    action VARCHAR(50) NOT NULL, -- 'CREATE', 'UPDATE', 'DELETE'
    entity_type VARCHAR(100) NOT NULL, -- 'article', 'employee', 'service'
    entity_id UUID NOT NULL,
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES admin_users(id) ON DELETE SET NULL
);
CREATE INDEX idx_audit_log_tenant_entity ON audit_log(tenant_id, entity_type, entity_id);
CREATE INDEX idx_audit_log_user ON audit_log(tenant_id, user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(tenant_id, created_at DESC);

-- ============ MULTI-TENANCY ============
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'starter', -- 'starter', 'pro', 'enterprise'
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Миграции (Alembic порядок)

1. **init** — создать alembic структуру
2. **001_create_tenants** — таблица tenants
3. **002_create_locales** — locales_config
4. **003_create_company_base** — practice_areas, services, employees, addresses, advantages
5. **004_create_company_locales** — *_locales таблицы
6. **005_create_company_relations** — employee_practice_areas
7. **006_create_content** — topics, articles, article_topics
8. **007_create_content_locales** — topic_locales, article_locales
9. **008_create_social_proof** — cases, reviews, case_services
10. **009_create_social_proof_locales** — case_locales
11. **010_create_support** — faq, contacts
12. **011_create_support_locales** — faq_locales
13. **012_create_leads** — inquiry_forms, inquiries
14. **013_create_assets** — file_assets
15. **014_create_seo** — seo_routes, redirects
16. **015_create_auth** — admin_users, roles, permissions, role_permissions
17. **016_create_audit_log** — audit_log
18. **017_create_indexes** — все индексы (если нет в CREATE TABLE)

---

## Проектирование API

### Общие стандарты

#### Версионирование
```
URL Versioning (явно):
  GET /api/v1/public/services
  GET /api/v1/admin/articles
```

#### Структура ответа (единая)

**Success 200/201:**
```json
{
  "data": { /* основной результат */ },
  "meta": { /* метаинформация */ }
}
```

**Success List 200:**
```json
{
  "data": [ /* массив */ ],
  "meta": {
    "total": 150,
    "page": 1,
    "limit": 20,
    "pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

**Error (RFC 7807 Problem Details):**
```json
{
  "type": "https://api.example.com/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Invalid input provided",
  "instance": "/api/v1/articles",
  "errors": [
    {"field": "title", "message": "Title is required"}
  ]
}
```

#### Пагинация
```
Метод: Offset-based (page + limit)
  GET /api/v1/public/articles?page=1&limit=20

Или: Cursor-based для large datasets
  GET /api/v1/public/cases?limit=50&after_cursor=abc123xyz
```

**Рекомендация для этого проекта:** Offset-based для админа (простота), Cursor для public (скорость, защита от data churn).

#### Фильтрация
```
GET /api/v1/articles?
  status=published&
  topic_id=uuid&
  locale=ru&
  search=seo&
  sort=-published_at,title&
  limit=20&page=1
```

**Стандартные фильтры по сущности:**
- `status` — 'published', 'draft', 'archived'
- `locale` — языковой код
- `search` — полнотекстовый поиск по title, description
- `sort` — поле[,поле,...], префикс `-` для DESC
- `limit`, `page` — пагинация

#### Локаль в API
```
Приоритет:
1. Query param: ?locale=ru
2. Header: Accept-Language: ru-RU
3. Default locale из tenant config
```

**Fallback:** Если перевода нет, вернуть default locale или ошибка (определить в бизнес-логике).

---

### Public API (читаемый контент)

#### 1. Services

```
GET /api/v1/public/services
  Params: locale, limit, page, sort, search
  Response: [
    { id, name, description, icon_url, slug }
  ]

GET /api/v1/public/services/{slug}
  Params: locale
  Response: { id, name, description, icon_url, slug, cases }

Example:
  GET /api/v1/public/services?locale=ru&limit=10
  200 OK
  {
    "data": [
      {
        "id": "uuid",
        "name": "Консультирование",
        "description": "...",
        "icon_url": "...",
        "slug": "consulting"
      }
    ],
    "meta": { "total": 5, "page": 1, "limit": 10, "pages": 1 }
  }
```

#### 2. Practice Areas

```
GET /api/v1/public/practice-areas
  Params: locale, limit, page
  Response: [{ id, name, description, icon_url, slug }]
```

#### 3. Employees

```
GET /api/v1/public/employees
  Params: locale, practice_area_id, limit, page, sort
  Response: [{ id, first_name, last_name, title, photo_url, slug, practice_areas }]

GET /api/v1/public/employees/{slug}
  Params: locale
  Response: { id, first_name, last_name, title, bio, photo_url, practice_areas, slug }
```

#### 4. Cases

```
GET /api/v1/public/cases
  Params: locale, service_id, limit, page, sort, search
  Response: [{ id, title, description, thumbnail_url, slug, services }]

GET /api/v1/public/cases/{slug}
  Params: locale
  Response: { id, title, description, content, thumbnail_url, services, slug }
```

#### 5. Articles

```
GET /api/v1/public/articles
  Params: locale, topic_id, limit, page, sort, search
  Response: [{ id, title, description, slug, featured, featured_image_url, published_at }]

GET /api/v1/public/articles/{slug}
  Params: locale
  Response: { id, title, description, content, slug, topic_ids, published_at }
```

#### 6. FAQ

```
GET /api/v1/public/faq
  Params: locale, topic_id, limit, page
  Response: [{ id, question, answer, topic_id }]
```

#### 7. Reviews

```
GET /api/v1/public/reviews
  Params: limit, page, sort
  Response: [{ id, author_name, rating, text, published_at }]
```

#### 8. Contacts

```
GET /api/v1/public/contacts
  Response: { phone, email, addresses }
```

#### 9. Inquiries (форма)

```
POST /api/v1/public/inquiries
  Body: {
    "form_id": "uuid",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+123456789",
    "company_name": "ACME Corp",
    "message": "I'm interested in..."
  }
  Response: 201 { id, created_at }
  
Validations:
  - first_name: required, min 2, max 100
  - email: required, valid email
  - form_id: required, exist in inquiry_forms
  - Rate limit: 5 per IP per hour
```

---

### Admin API (полный CRUD)

#### Структура эндпоинтов

```
GET    /api/v1/admin/{resource}
       Пагинация, фильтры, сортировка

GET    /api/v1/admin/{resource}/{id}
       Одна запись

POST   /api/v1/admin/{resource}
       Создание

PATCH  /api/v1/admin/{resource}/{id}
       Частичное обновление

DELETE /api/v1/admin/{resource}/{id}
       Мягкое удаление (status -> archived)
```

#### Example: Articles CRUD

```
GET /api/v1/admin/articles
  Params: status, topic_id, locale, limit, page, sort, search
  Permissions: view_articles
  Response: [{ id, slug, title, status, locale, published_at, created_by }]

GET /api/v1/admin/articles/{id}
  Permissions: view_articles
  Response: {
    id, slug, status, featured,
    locales: [
      { locale: "en", title: "...", description: "...", content: "...", slug: "..." },
      { locale: "ru", title: "...", description: "...", content: "...", slug: "..." }
    ],
    topic_ids: ["uuid1", "uuid2"],
    created_by: "admin@example.com",
    created_at, updated_at
  }

POST /api/v1/admin/articles
  Permissions: create_articles
  Body: {
    "slug": "my-article",
    "status": "draft",
    "featured": false,
    "locales": {
      "en": { "title": "...", "description": "...", "content": "...", "slug": "..." },
      "ru": { "title": "...", "description": "...", "content": "...", "slug": "..." }
    },
    "topic_ids": ["uuid1"]
  }
  Validations:
    - slug: required, unique, regex ^[a-z0-9-]+$
    - locales: min 1, max N languages in config
    - Для каждого locale: title required, content required
  Response: 201 { id, slug, created_at }

PATCH /api/v1/admin/articles/{id}
  Permissions: edit_articles
  Body: {
    "status": "published",
    "featured": true,
    "locales": {
      "en": { "title": "Updated Title", "slug": "updated-slug" }
    },
    "topic_ids": ["uuid1", "uuid3"]
  }
  Response: 200 { id, updated_at }

DELETE /api/v1/admin/articles/{id}
  Permissions: delete_articles
  Response: 204 No Content
```

#### Example: Employees CRUD

```
GET /api/v1/admin/employees
  Params: status, practice_area_id, locale, limit, page
  Response: [{ id, slug, status, practice_areas, created_at }]

GET /api/v1/admin/employees/{id}
  Response: {
    id, slug, status, photo_url,
    locales: [
      { locale: "en", first_name: "...", last_name: "...", title: "...", bio: "...", slug: "..." }
    ],
    practice_area_ids: ["uuid1", "uuid2"],
    created_at, updated_at
  }

POST /api/v1/admin/employees
  Body: {
    "slug": "john-doe",
    "photo_url": "https://...",
    "status": "draft",
    "locales": {
      "en": { "first_name": "John", "last_name": "Doe", "title": "Senior Developer", "bio": "...", "slug": "john-doe" }
    },
    "practice_area_ids": ["uuid1"]
  }
  Response: 201 { id }

PATCH /api/v1/admin/employees/{id}
  Body: { "status": "published", "practice_area_ids": ["uuid1", "uuid2", "uuid3"] }
  Response: 200 { id }

DELETE /api/v1/admin/employees/{id}
  Response: 204
```

#### Bulk Operations

```
POST /api/v1/admin/articles/bulk
  Body: { "ids": ["id1", "id2", "id3"], "updates": { "status": "published", "featured": false } }
  Response: 200 { updated_count: 3 }

POST /api/v1/admin/seo-routes/bulk-upsert
  Body: [
    { "path": "/services", "locale": "en", "title": "Our Services", "description": "...", "canonical": "self" },
    { "path": "/services", "locale": "ru", "title": "Наши услуги", "description": "...", "canonical": "/services?locale=en" }
  ]
  Response: 200 { created: 0, updated: 2 }
```

---

### SEO API

```
GET /api/v1/admin/seo/routes
  Params: path, locale, limit, page
  Response: [{ path, locale, title, description, og_title, og_description, canonical, robots_directive }]

GET /api/v1/admin/seo/routes?path=/articles&locale=en
  Response: { path: "/articles", locale: "en", title: "Our Articles", ... }

PUT /api/v1/admin/seo/routes
  Body: { "path": "/services", "locale": "en", "title": "Services", "description": "...", "canonical": "self", "robots_directive": "index, follow" }
  Response: 200 { id, created_at }

GET /api/v1/admin/seo/routes/hreflang
  Description: Получить hreflang структуру для пути
  Params: path, exclude_locale (опция)
  Response: [
    { locale: "en", path: "/services", canonical: true },
    { locale: "ru", path: "/services", canonical: false }
  ]

POST /api/v1/admin/seo/redirects
  Body: { "from_path": "/old-service", "to_path": "/services/consulting", "status_code": 301 }
  Response: 201 { id }

GET /api/v1/public/sitemap.xml
  Description: Генерация sitemap на лету (с кешом)
  Query: locale (опция)
  Response: XML

GET /api/v1/public/.well-known/robots.txt
  Response: text/plain
```

---

### Auth API

```
POST /api/v1/auth/login
  Body: { "email": "admin@example.com", "password": "..." }
  Response: 200 {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": { "id", "email", "first_name", "role": { "id", "name", "permissions": [...] } }
  }

POST /api/v1/auth/refresh
  Body: { "refresh_token": "..." }
  Response: 200 { "access_token": "...", "expires_in": 3600 }

POST /api/v1/auth/logout
  Response: 200 {}

GET /api/v1/admin/me
  Requires: JWT auth
  Response: { "id", "email", "first_name", "last_name", "role": {...} }
```

---

### Users & Roles (Admin only)

```
GET /api/v1/admin/users
  Response: [{ id, email, first_name, last_name, role_id, is_active, last_login_at }]

POST /api/v1/admin/users
  Body: { "email": "user@example.com", "password": "...", "first_name": "John", "role_id": "uuid" }
  Response: 201 { id, email }

PATCH /api/v1/admin/users/{id}
  Body: { "first_name": "Jane", "role_id": "uuid", "is_active": true }
  Response: 200 { id }

DELETE /api/v1/admin/users/{id}
  Response: 204

GET /api/v1/admin/roles
  Response: [{ id, name, description, permissions: [{id, code, description}] }]

POST /api/v1/admin/roles
  Body: { "name": "content_editor", "description": "...", "permission_ids": ["uuid1", "uuid2"] }
  Response: 201 { id }
```

---

### Audit Log

```
GET /api/v1/admin/audit-log
  Params: entity_type, entity_id, user_id, action, limit, page, sort
  Response: [{ id, action, entity_type, entity_id, user_id, old_values, new_values, ip_address, created_at }]

Example:
  GET /api/v1/admin/audit-log?entity_type=article&entity_id=uuid&sort=-created_at
  200 {
    "data": [
      { 
        "id": "uuid", 
        "action": "UPDATE",
        "entity_type": "article",
        "entity_id": "article-uuid",
        "user_id": "admin-uuid",
        "old_values": { "status": "draft" },
        "new_values": { "status": "published" },
        "created_at": "2024-01-14T12:00:00Z"
      }
    ],
    "meta": { "total": 5, ... }
  }
```

---

### Health & System

```
GET /health
  Response: 200 { "status": "ok", "version": "1.0.0", "timestamp": "..." }

GET /api/v1/admin/health
  Requires: JWT auth
  Response: 200 {
    "status": "ok",
    "database": "connected",
    "cache": "connected",
    "uptime": 86400,
    "memory_usage_mb": 256
  }
```

---

### Ошибки API (стандартизированные)

| Статус | Type | Title | Пример |
|--------|------|-------|---------|
| 400 | `bad_request` | Bad Request | Неправильный формат JSON |
| 422 | `validation_error` | Validation Error | title обязательное поле |
| 401 | `unauthorized` | Unauthorized | Отсутствует JWT токен |
| 403 | `forbidden` | Forbidden | Недостаточно прав (роль не имеет permission) |
| 404 | `not_found` | Not Found | Ресурс не существует |
| 409 | `conflict` | Conflict | Нарушение UNIQUE constraint (например, slug занят) |
| 429 | `rate_limited` | Too Many Requests | Превышен rate limit |
| 500 | `internal_server_error` | Internal Server Error | Неожиданная ошибка |

**Пример 422:**
```json
{
  "type": "https://api.example.com/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more validation errors occurred",
  "instance": "/api/v1/admin/articles",
  "errors": [
    { "field": "title", "message": "Title is required" },
    { "field": "slug", "message": "Slug must match pattern ^[a-z0-9-]+$" },
    { "field": "locales.en.content", "message": "Content is required for default locale" }
  ]
}
```

---

### OpenAPI (Swagger) Structure

**Tags по доменам:**
- `public:services` — Public API для услуг
- `public:employees` — Public API для сотрудников
- `admin:articles` — Admin API для статей
- `admin:seo` — Admin API для SEO
- `admin:auth` — Аутентификация
- `admin:users` — Управление пользователями

**Schemas в components:**
```yaml
components:
  schemas:
    Service:
      type: object
      properties:
        id: { type: string, format: uuid }
        name: { type: string }
        description: { type: string, nullable: true }
        icon_url: { type: string, format: uri, nullable: true }
        slug: { type: string }
      required: [id, name, slug]
    
    Article:
      type: object
      properties:
        id: { type: string, format: uuid }
        slug: { type: string }
        status: { type: string, enum: [draft, published, archived] }
        locales:
          type: array
          items:
            type: object
            properties:
              locale: { type: string }
              title: { type: string }
              content: { type: string }
      required: [id, slug, status, locales]
    
    PaginatedResponse:
      type: object
      properties:
        data: { type: array }
        meta:
          type: object
          properties:
            total: { type: integer }
            page: { type: integer }
            limit: { type: integer }
            pages: { type: integer }
            has_next: { type: boolean }
            has_prev: { type: boolean }
```

---

## Требования к функционалу

### Must-have (MVP)

- [x] **Auth**: JWT-based аутентификация для админа
- [x] **RBAC**: Роли (admin, content_manager, marketer) + базовые permissions
- [x] **Public API**: Чтение опубликованного контента (services, employees, articles, cases)
- [x] **Admin CRUD**: Создание/редактирование/удаление всех сущностей
- [x] **Локализация**: Поддержка 2+ языков, translation tables
- [x] **Draft/Publish**: Черновики → опубликование
- [x] **SEO метаданные**: title, description, canonical, robots на базовом уровне
- [x] **Аудит**: Логирование who/what/when для всех изменений
- [x] **Rate limit**: Базовый rate limit на public API (например, 100 req/min)
- [x] **Пагинация**: Offset-based (page, limit)
- [x] **Ошибки**: RFC 7807 Problem Details формат

### Should-have (v1)

- [ ] **hreflang**: Автогенерация hreflang для многоязычных страниц
- [ ] **Bulk operations**: Массовое редактирование (status, featured, topic)
- [ ] **Search**: Полнотекстовый поиск по статьям и случаям (FTS)
- [ ] **File upload**: Загрузка фото/документов (S3 или локально)
- [ ] **Page Builder**: Гибкие секции контента (blocks + page_sections)
- [ ] **Email notifications**: Уведомления при новых лидах, комментариях
- [ ] **Cache**: ETag + Cache-Control для public API
- [ ] **Sitemap**: Динамическая генерация sitemap.xml
- [ ] **Import/Export**: Экспорт контента в JSON/CSV для SEO инструментов
- [ ] **Redirects management**: UI для управления 301/302 перенаправлениями
- [ ] **Analytics integration**: Хуки для подключения GA, Yandex.Metrica
- [ ] **Permissions granularity**: Поля/элементы на уровне permissions (view/edit/delete)

### Nice-to-have (v2)

- [ ] **Versioning**: История версий контента (откат на старую версию)
- [ ] **Comments/moderation**: Система комментариев с модерацией
- [ ] **Templates**: Шаблоны для быстрого создания типовых страниц
- [ ] **Webhooks**: Уведомления внешним системам (CRM, Slack)
- [ ] **GraphQL API**: Альтернатива REST для гибких запросов
- [ ] **CLI**: Command-line инструмент для управления (импорт, экспорт, миграция)
- [ ] **Multi-database**: Поддержка несколько БД для разных тенантов
- [ ] **CDN integration**: Кешинг фото/документов на CDN

---

## Архитектура FastAPI

### Структура проекта

```
corporate-cms-backend/
├── alembic/                    # миграции БД
│   ├── versions/
│   │   ├── 001_create_tenants.py
│   │   ├── 002_create_locales.py
│   │   └── ...
│   └── env.py
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── core/
│   │   ├── config.py           # Конфиги (Pydantic Settings)
│   │   ├── security.py         # JWT, hashing, permissions
│   │   ├── logging.py          # Логирование
│   │   └── constants.py        # Enum'ы (roles, status, etc)
│   ├── db/
│   │   ├── session.py          # SessionLocal, get_db dependency
│   │   ├── base.py             # SQLAlchemy Base
│   │   └── models.py           # ORM модели (или models/ папка)
│   ├── modules/                # Доменные модули (по bounded contexts)
│   │   ├── company/
│   │   │   ├── domain/
│   │   │   │   ├── entities.py # Domain objects (не ORM)
│   │   │   │   └── services.py # Domain business logic
│   │   │   ├── application/
│   │   │   │   └── use_cases.py # Application layer (orchestra)
│   │   │   ├── infrastructure/
│   │   │   │   ├── repository.py # Data access
│   │   │   │   └── orm_models.py # SQLAlchemy models (if separated)
│   │   │   ├── api/
│   │   │   │   ├── admin_routes.py
│   │   │   │   ├── public_routes.py
│   │   │   │   └── dependencies.py
│   │   │   └── schemas.py      # Pydantic schemas (request/response)
│   │   ├── content/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   ├── infrastructure/
│   │   │   ├── api/
│   │   │   └── schemas.py
│   │   ├── auth/
│   │   │   ├── application/
│   │   │   ├── infrastructure/
│   │   │   ├── api/
│   │   │   └── schemas.py
│   │   └── ...
│   ├── api/
│   │   ├── v1/
│   │   │   ├── public/
│   │   │   │   └── router.py   # Включает все public routes
│   │   │   ├── admin/
│   │   │   │   └── router.py   # Включает все admin routes
│   │   │   └── router.py       # v1 router (объединяет public + admin)
│   │   └── router.py           # Главный router
│   ├── middleware/
│   │   ├── tenant_context.py   # Tenant ID из URL/domain
│   │   ├── audit_logger.py     # Логирование изменений
│   │   └── error_handler.py    # Глобальная обработка ошибок
│   ├── tasks/                  # Async tasks (Celery, APScheduler)
│   │   ├── email.py
│   │   ├── cache_refresh.py
│   │   └── cleanup.py
│   └── utils/
│       ├── validators.py       # Custom validators (slug regex, etc)
│       ├── exceptions.py       # Custom exceptions
│       ├── cache.py            # Кеширование
│       ├── seo.py              # SEO helpers (hreflang, sitemap)
│       └── file_upload.py      # Работа с файлами
├── tests/
│   ├── conftest.py             # Fixtures (DB, client, user)
│   ├── unit/
│   │   └── test_article_service.py
│   ├── integration/
│   │   └── test_article_api.py
│   └── e2e/
│       └── test_workflow.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml / requirements.txt
└── .env.example
```

---

### Dependency Injection (FastAPI Depends)

**Пример: GetArticleUseCase**

```python
# app/core/security.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthCredential

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthCredential = Depends(security)) -> AdminUser:
    user = verify_jwt_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

def check_permission(permission: str) -> Callable:
    async def _check(user: AdminUser = Depends(get_current_user)):
        if not user.has_permission(permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _check

# app/db/session.py
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# app/modules/content/api/dependencies.py
def get_article_repository(db: Session = Depends(get_db)) -> ArticleRepository:
    return ArticleRepository(db)

def get_article_use_case(
    repo: ArticleRepository = Depends(get_article_repository),
    user: AdminUser = Depends(check_permission("view_articles"))
) -> GetArticleUseCase:
    return GetArticleUseCase(repo, user.tenant_id)

# app/modules/content/api/admin_routes.py
@router.get("/articles/{article_id}")
async def get_article(
    article_id: UUID,
    use_case: GetArticleUseCase = Depends(get_article_use_case)
) -> ArticleDetailResponseSchema:
    article = use_case.execute(article_id)
    return ArticleDetailResponseSchema.from_domain(article)
```

---

### Слои архитектуры (DDD)

#### 1. **API / Delivery Layer** (Routers)
- Обрабатывает HTTP запросы/ответы
- Валидирует input Pydantic schemas
- Преобразует domain objects в response schemas
- **Правило:** Без бизнес-логики, только роутинг

#### 2. **Application Layer** (Use Cases)
- Координирует domain objects
- Управляет транзакциями
- Вызывает domain services
- **Правило:** Не зависит от FastAPI, БД, API деталей

#### 3. **Domain Layer** (Entities, Value Objects, Domain Services)
- Чистая бизнес-логика
- Инварианты (Article должен иметь title)
- Domain Services (нет 1 entity, но нужны правила)
- **Правило:** Полностью независим от фреймворков

#### 4. **Infrastructure Layer** (Repositories, ORM)
- Доступ к данным (DB, кеш, файлы)
- Реализация интерфейсов (Repository pattern)
- **Правило:** Может быть заменен, если интерфейсы одинаковые

**Пример: Create Article Use Case**

```python
# app/modules/content/domain/entities.py
class Article:
    def __init__(self, id: UUID, slug: str, status: str):
        if not slug or len(slug) < 3:
            raise ValueError("Slug must be at least 3 chars")
        self.id = id
        self.slug = slug
        self.status = status
    
    def publish(self):
        if self.status != "draft":
            raise ValueError("Can only publish drafts")
        self.status = "published"

# app/modules/content/domain/services.py
class ArticleService:
    def __init__(self, repo: ArticleRepository):
        self.repo = repo
    
    def check_slug_available(self, slug: str, locale: str, tenant_id: UUID) -> bool:
        existing = self.repo.find_by_slug(slug, locale, tenant_id)
        return not existing

# app/modules/content/application/use_cases.py
class CreateArticleUseCase:
    def __init__(
        self,
        repo: ArticleRepository,
        service: ArticleService,
        audit_log: AuditLogService,
        tenant_id: UUID
    ):
        self.repo = repo
        self.service = service
        self.audit_log = audit_log
        self.tenant_id = tenant_id
    
    def execute(self, cmd: CreateArticleCommand) -> Article:
        # Валидация
        if not self.service.check_slug_available(cmd.slug, cmd.locale, self.tenant_id):
            raise ConflictError("Slug already exists")
        
        # Создание
        article = Article(
            id=uuid4(),
            slug=cmd.slug,
            status="draft"
        )
        
        # Сохранение
        saved = self.repo.save(article)
        
        # Аудит
        self.audit_log.log(
            action="CREATE",
            entity_type="article",
            entity_id=saved.id,
            new_values={"slug": cmd.slug, "status": "draft"},
            tenant_id=self.tenant_id
        )
        
        return saved

# app/modules/content/api/admin_routes.py
@router.post("/articles")
async def create_article(
    body: CreateArticleRequestSchema,
    use_case: CreateArticleUseCase = Depends(get_create_article_use_case),
    user: AdminUser = Depends(check_permission("create_articles"))
) -> ArticleResponseSchema:
    try:
        cmd = CreateArticleCommand.from_request(body)
        article = use_case.execute(cmd)
        return ArticleResponseSchema.from_domain(article)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
```

---

### Обработка ошибок (Global Exception Handler)

```python
# app/utils/exceptions.py
class AppException(Exception):
    status_code = 500
    detail = "Internal Server Error"

class ValidationError(AppException):
    status_code = 422
    detail = "Validation failed"

class NotFoundError(AppException):
    status_code = 404
    detail = "Resource not found"

class ConflictError(AppException):
    status_code = 409
    detail = "Conflict"

class ForbiddenError(AppException):
    status_code = 403
    detail = "Forbidden"

# app/middleware/error_handler.py
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://api.example.com/errors/{exc.__class__.__name__.lower()}",
            "title": exc.__class__.__name__,
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url.path)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(x) for x in err["loc"][1:]),
            "message": err["msg"]
        }
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://api.example.com/errors/validation_error",
            "title": "Validation Error",
            "status": 422,
            "detail": "One or more validation errors occurred",
            "errors": errors
        }
    )
```

---

### Валидация Pydantic Schemas

```python
# app/modules/content/schemas.py
from pydantic import BaseModel, Field, field_validator, EmailStr

class ArticleLocaleSchema(BaseModel):
    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10, max_length=1000)
    content: str = Field(..., min_length=50)
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    
    @field_validator("slug")
    @classmethod
    def slug_not_reserved(cls, v):
        reserved = {"admin", "api", "login", "logout"}
        if v.lower() in reserved:
            raise ValueError("Slug is reserved")
        return v

class CreateArticleRequestSchema(BaseModel):
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    status: str = Field(default="draft", pattern=r"^(draft|published|archived)$")
    featured: bool = False
    locales: dict[str, ArticleLocaleSchema] = Field(..., min_items=1)
    topic_ids: list[UUID] = Field(default_factory=list)
    
    @field_validator("locales")
    @classmethod
    def validate_locales_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("At least one locale is required")
        return v

class ArticleResponseSchema(BaseModel):
    id: UUID
    slug: str
    status: str
    featured: bool
    locales: list[ArticleLocaleSchema]
    topic_ids: list[UUID]
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_domain(cls, article: Article) -> "ArticleResponseSchema":
        # Преобразование domain object в response schema
        return cls(...)

    class Config:
        from_attributes = True  # для sqlalchemy models
```

---

### Тестирование

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine

@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def admin_user(db_session):
    user = AdminUser(email="admin@test.com", role_id=admin_role.id)
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def admin_token(admin_user):
    return create_access_token(data={"sub": str(admin_user.id)})

# tests/integration/test_article_api.py
def test_create_article(client, admin_token, db_session):
    response = client.post(
        "/api/v1/admin/articles",
        json={
            "slug": "test-article",
            "status": "draft",
            "locales": {
                "en": {
                    "title": "Test Article",
                    "description": "A test article",
                    "content": "This is a test article content",
                    "slug": "test-article"
                }
            },
            "topic_ids": []
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 201
    assert response.json()["data"]["slug"] == "test-article"
    
    # Verify in DB
    article = db_session.query(Article).filter_by(slug="test-article").first()
    assert article is not None

def test_create_article_duplicate_slug_conflict(client, admin_token, db_session):
    # Create first
    client.post(
        "/api/v1/admin/articles",
        json={...same slug...},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # Try to create second with same slug
    response = client.post(
        "/api/v1/admin/articles",
        json={...same slug...},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
```

---

## Риски и антипаттерны

### Риски

#### 1. **Data Leakage между тенантами**
- **Проблема**: `tenant_id` забыли в WHERE clause → видны данные другого клиента
- **Решение**:
  - ✅ RLS (Row-Level Security) на БД уровне (PostgreSQL RLS политики)
  - ✅ Middleware, который инжектит tenant_id в каждый запрос
  - ✅ Тесты: каждый тест должен проверить `tenant_id` изоляцию
  - ✅ Audit: все кросс-tenant запросы логировать и мониторить

#### 2. **SEO ломается**
- **Проблема**: Неправильный canonical, hreflang не совпадает, дублирующийся контент
- **Решение**:
  - ✅ Canonical: уникален per locale, по-умолчанию = self
  - ✅ Hreflang: автогенерируется, все локали связаны
  - ✅ Slug: уникален per locale (constraint в БД)
  - ✅ Meta robots: 'noindex' для черновиков + тестовых сайтов
  - ✅ Регулярный аудит через Search Console API

#### 3. **Контент теряется**
- **Проблема**: Hard delete вместо soft delete, дыры в транзакциях
- **Решение**:
  - ✅ Soft delete (is_deleted / status='archived')
  - ✅ Audit log (что менялось, когда, кто)
  - ✅ Backup стратегия (WAL для Postgres, daily snapshots)
  - ✅ Транзакции для multi-table операций

#### 4. **Масштабируемость падает**
- **Проблема**: N+1 queries, неправильные индексы, кеш никогда не валидируется
- **Решение**:
  - ✅ ORM: использовать `eager loading` (select_in_load, joinedload)
  - ✅ Индексы: на всех FK, slug, status, published_at, locale
  - ✅ Кеш: ETag, Cache-Control для public API
  - ✅ Запросы: EXPLAIN ANALYZE каждого

#### 5. **Локализация сломана**
- **Проблема**: Перевод на языке по умолчанию отсутствует, fallback не работает
- **Решение**:
  - ✅ Constraint: (entity_id, default_locale) = обязательны
  - ✅ Fallback: если локали нет → default
  - ✅ UI warning: если переводов не полные

---

### Антипаттерны

#### ❌ Монолитная таблица "entity" с EAV (Entity-Attribute-Value)
```sql
-- ПЛОХО
CREATE TABLE entities (
    id UUID,
    type VARCHAR(50), -- 'article', 'service', etc
    attr_name VARCHAR(100),
    attr_value TEXT
);
```
**Почему плохо:** Невозможно валидировать на уровне БД, медленные запросы, дыры в консистентности.

#### ❌ Все в JSONB без индексов
```sql
-- ПЛОХО
CREATE TABLE articles (
    id UUID,
    data JSONB -- всё в одном JSONB
);
```
**Почему плохо:** Нельзя индексировать, сложные запросы, нет типов, нельзя валидировать.

#### ❌ No Audit Trail
```python
# ПЛОХО
article.title = "New Title"
db.commit()
# Кто менял? Когда? Старое значение куда?
```
**Решение:** Audit log на каждый CREATE/UPDATE/DELETE.

#### ❌ Кеширование без инвалидации
```python
# ПЛОХО
@cache(ttl=3600)
def get_article(id):
    return Article.get(id)

# ...

article.update()  # кеш не инвалидирован, старые данные
```

#### ❌ Локализация через поля language_en, language_ru
```sql
-- ПЛОХО
CREATE TABLE articles (
    id UUID,
    title_en VARCHAR(255),
    title_ru VARCHAR(255),
    title_de VARCHAR(255),
    ...
);
```
**Почему плохо:** Нельзя добавить язык без ALTER, много NULL'ов, нельзя индексировать по языку.

#### ❌ Hard delete
```python
# ПЛОХО
db.delete(article)  # Не знаешь, что было удалено
```
**Решение:** is_deleted флаг + audit log.

#### ❌ Смешивание domain logic с HTTP handlers
```python
# ПЛОХО
@app.post("/articles")
def create_article(request):
    db_article = Article.create(...)  # domain logic в handler
    return {"id": db_article.id}
```
**Решение:** Use cases / Application layer между HTTP и domain.

---

## План реализации

### Фаза 1: Foundation (3-4 недели)

**Результат:** Working MVP с базовым CRUD

- [ ] PostgreSQL migrations (001-010)
- [ ] FastAPI скелет + auth (JWT)
- [ ] Core models (Pydantic schemas)
- [ ] Repository pattern базовый
- [ ] Admin CRUD для Services, Practice Areas, Employees
- [ ] Public API (list/get read-only)
- [ ] Rate limiting базовый
- [ ] Tests (fixtures, conftest)
- [ ] Docker + compose
- [ ] Swagger docs (OpenAPI генерируется автоматически)

**Deliverables:**
- PostgreSQL БД up
- FastAPI app running
- `POST /api/v1/admin/services` работает
- `GET /api/v1/public/services` работает
- Все GET запросы возвращают 200 или 404
- 50+ unit tests

---

### Фаза 2: Content & Localization (2-3 недели)

**Результат:** Полная локализация, статьи, кейсы

- [ ] Articles CRUD + Topics
- [ ] Cases CRUD
- [ ] Translation tables (article_locales, case_locales, etc)
- [ ] Fallback logic для missing translations
- [ ] Slug uniqueness per locale
- [ ] Draft/Publish workflow
- [ ] Audit log implementation
- [ ] Search (FTS) basic
- [ ] Tests (integration 80+)

**Deliverables:**
- `POST /api/v1/admin/articles` с multi-locale support
- `GET /api/v1/public/articles?locale=ru` fallback work
- Audit log для всех сущностей
- Swagger docs обновлены

---

### Фаза 3: SEO & Advanced Features (2 недели)

**Результат:** SEO-ready API, управление метатегами

- [ ] SEO routes CRUD
- [ ] Redirects management
- [ ] hreflang generation
- [ ] robots.txt endpoint
- [ ] sitemap.xml endpoint
- [ ] Bulk update (articles status, featured)
- [ ] Cache headers (ETag, Cache-Control)
- [ ] Permissions granularity (per entity type)
- [ ] Tests (50+ tests)

**Deliverables:**
- `POST /api/v1/admin/seo/routes` bulk upsert
- `GET /api/v1/public/sitemap.xml` works
- `GET /api/v1/public/.well-known/robots.txt` works
- hreflang автогенерируется

---

### Фаза 4: Files & Page Builder (2 недели)

**Результат:** Upload, attachments, page builder blocks

- [ ] File upload (S3-compatible или локально)
- [ ] File assets table + ORM model
- [ ] Polymorphic attachments (article → documents)
- [ ] Page sections + content blocks (page builder)
- [ ] Drag-drop order API (sort_order)
- [ ] Tests (integration, file handling)

**Deliverables:**
- `POST /api/v1/admin/files/upload` работает
- `POST /api/v1/admin/pages/sections` CRUD
- Content blocks reusable

---

### Фаза 5: Advanced Admin & Polish (2 недели)

**Результат:** Production-ready

- [ ] User management (CRUD, roles)
- [ ] Permissions full RBAC
- [ ] Import/Export (CSV, JSON)
- [ ] Email notifications (leads, new content)
- [ ] Health check + monitoring endpoints
- [ ] Rate limiting advanced (per user, per endpoint)
- [ ] Logging + structured logs (JSON)
- [ ] Caching strategy (Redis, invalidation)
- [ ] Tests (100+ total, E2E workflows)
- [ ] Documentation (API docs, setup guide)
- [ ] Docker image optimization
- [ ] Performance tuning (query optimization)

**Deliverables:**
- `GET /health`, `/api/v1/admin/health` работает
- Все permissions фиксированы в коде
- Логи структурированы (JSON)
- Docker image < 500MB

---

### Фаза 6: QA & Deployment (1-2 недели)

**Результат:** Ready for production

- [ ] Load testing (100+ concurrent users)
- [ ] Security audit
- [ ] SQL injection tests
- [ ] CORS / CSRF checks
- [ ] Staging deployment
- [ ] Monitoring setup (Sentry, DataDog)
- [ ] Runbook documentation
- [ ] Disaster recovery plan

---

## Дополнительные решения

### Page Builder без денормализации

**Идея:** Гибкие content blocks без помойки в БД

```sql
CREATE TABLE pages (
    id UUID,
    tenant_id UUID,
    slug VARCHAR(255) UNIQUE,
    status VARCHAR(20),
    created_at, updated_at
);

CREATE TABLE page_sections (
    id UUID,
    page_id UUID,
    sort_order INTEGER,
    content_block_id UUID,
    custom_css TEXT, -- опция для кастомизации
    created_at, updated_at,
    FOREIGN KEY (page_id) REFERENCES pages(id),
    FOREIGN KEY (content_block_id) REFERENCES content_blocks(id)
);

CREATE TABLE content_blocks (
    id UUID,
    tenant_id UUID,
    block_type VARCHAR(50), -- 'text', 'image', 'gallery', 'faq', 'testimonials'
    name VARCHAR(255),
    data JSONB, -- конфиг блока (текст, цвет, размер и т.п.)
    template VARCHAR(50), -- 'default', 'featured', etc
    created_at, updated_at
);
```

**API:**
```
POST /api/v1/admin/pages
  { "slug": "about", "sections": [{ "content_block_id": "uuid1", "sort_order": 1 }] }

POST /api/v1/admin/content-blocks
  { "block_type": "text", "name": "Hero Text", "data": { "text": "...", "color": "#fff" } }

PATCH /api/v1/admin/pages/{id}/sections
  Переупорядочить, добавить, удалить секции
```

---

### Кеширование public API

**Стратегия:**

```python
# app/utils/cache.py
from datetime import timedelta

def cache_response(ttl: timedelta = timedelta(hours=1)):
    def decorator(func):
        async def wrapper(*args, request: Request, **kwargs):
            cache_key = f"{request.method}:{request.url.path}:{request.query_string}"
            
            # Проверить кеш
            cached = cache.get(cache_key)
            if cached:
                return JSONResponse(
                    content=cached,
                    headers={"X-Cache": "HIT"}
                )
            
            # Выполнить функцию
            response = await func(*args, request=request, **kwargs)
            
            # Сохранить в кеш
            cache.set(cache_key, response, ttl)
            
            # ETag
            etag = hashlib.md5(json.dumps(response).encode()).hexdigest()
            return JSONResponse(
                content=response,
                headers={"ETag": f'"{etag}"', "X-Cache": "MISS", "Cache-Control": f"public, max-age={ttl.total_seconds()}"}
            )
        return wrapper
    return decorator

# app/modules/content/api/public_routes.py
@router.get("/articles")
@cache_response(ttl=timedelta(hours=24))
async def list_articles(request: Request, use_case: ListArticlesUseCase = Depends(...)):
    return use_case.execute()
```

---

### Универсальные сущности vs явные таблицы

| Аспект | Универсальные (EAV) | Явные таблицы |
|--------|-------------------|---------------|
| **Гибкость** | ✅ Можно добавить field без миграции | ❌ Нужна миграция |
| **Типизация** | ❌ Всё string, нет валидации | ✅ Типизированно, валидация в БД |
| **Перформанс** | ❌ Медленные запросы (много JOINов) | ✅ Быстрые (direct access) |
| **Индексирование** | ❌ Сложно (functional indexes) | ✅ Просто (B-tree) |
| **Konsistency** | ❌ Нужно приложению | ✅ Constraints в БД |

**Рекомендация:** Явные таблицы для стабильных сущностей (services, employees), translation tables для многоязычности.

---

## Заключение

Этот backend-движок разработан для **масштабируемости, переиспользуемости и SEO-оптимизации**. Ключевые решения:

1. **Multi-tenancy**: Shared schema + `tenant_id` + RLS
2. **Локализация**: Translation tables (лучше, чем JSONB)
3. **Архитектура**: DDD (domain → application → infrastructure → API)
4. **API**: REST v1, offset-based pagination, RFC 7807 errors
5. **SEO**: Управляемые метаданные, hreflang, canonical, robots
6. **Аудит**: Log всех изменений, compliance-ready
7. **Кеш**: ETag + Cache-Control для public, invalidation стратегия
8. **Тесты**: Unit + integration, fixtures, E2E workflows

Реализовать в **3 месяца** (90-дневные спринты) с фазой за фазой delivery.
