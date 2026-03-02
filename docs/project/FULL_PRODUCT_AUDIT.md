# Полный продуктовый и технический аудит SaaS-платформы

> Дата аудита: 2026-03-01  
> Источник: анализ исходного кода Backend (Python/FastAPI), Admin Panel (Next.js), Client Site (Next.js)

---

## БЛОК 1 — ФУНКЦИОНАЛЬНАЯ КАРТА

---

### 1.1 Управление организациями (Tenants) — ✅ Готов

**Цель:** Мультитенантное управление клиентами платформы. Для platform owner.

**Сущности и ключевые поля:**

| Модель | Ключевые поля | Назначение |
|--------|---------------|------------|
| `Tenant` | name, slug (unique), domain, is_active, logo_url, primary_color, extra_data | Организация-клиент |
| `TenantDomain` | domain (unique), ssl_status (pending→verifying→active→error), dns_verified_at, ssl_provisioned_at | Кастомный домен админки |
| `TenantSettings` | default_locale, timezone, site_url, email_*, smtp_*, ga_tracking_id, ym_counter_id, indexnow_*, llms_txt_*, sitemap_static_pages, robots_txt_custom_rules | Настройки организации |
| `FeatureFlag` | feature_name, enabled, per tenant | Включение/выключение модулей |

**CRUD-операции:**
- **Admin:** Полный CRUD тенантов, доменов, настроек, feature flags. Только platform_owner.
- **Public:** `GET /public/tenants/by-domain/{domain}` — резолв домена → tenant_id (используется SPA при загрузке). `GET /public/tenants/{tenant_id}` — публичная инфо. `GET /public/tenants/{tenant_id}/analytics` — GA/YM ID.

**Как создаётся новый тенант:**
1. Platform owner вызывает `POST /tenants` с name, slug, contact_email.
2. Автоматически создаются `TenantSettings` (дефолтные) и все `FeatureFlag` (все включены по умолчанию).
3. Добавляется кастомный домен через `POST /tenants/{id}/domains`.
4. DNS-верификация: `POST /tenants/{id}/domains/{id}/verify` → проверка CNAME → `provision_domain_task` (TaskIQ) → Caddy выписывает SSL.
5. Polling SSL статуса: `GET /tenants/{id}/domains/{id}/ssl-status`.

**Настройки тенанта:**
- Локализация: default_locale, timezone, date/time format
- Email: provider (smtp/sendgrid/mailgun/console), from address, SMTP credentials (encrypted)
- SEO: site_url, static pages для sitemap, robots.txt, IndexNow, llms.txt
- Аналитика: GA tracking ID, Yandex Metrika counter ID
- Верификация: Yandex.Webmaster, Google Search Console

**Ограничения и валидации:**
- slug ≥ 2 символов, уникальный глобально
- domain ≥ 4 символов, уникальный глобально
- ssl_status ∈ {pending, verifying, active, error}
- email_provider ∈ {smtp, sendgrid, mailgun, console}
- locale формат: `^[a-z]{2}(-[A-Z]{2})?$`
- Optimistic locking (version) на Tenant

**Что НЕ реализовано:**
- ❌ Биллинг и лимиты per-tenant (кол-во пользователей, объём хранилища)
- ❌ Валидация timezone как IANA timezone
- ❌ Валидация hostname при добавлении домена
- ❌ `TenantDomain.get_domain` не привязан к tenant (любой домен можно получить по ID)
- ❌ `Tenant.domain` (legacy поле) дублирует `TenantDomain`

---

### 1.2 Аутентификация и авторизация (Auth + RBAC) — ✅ Готов

**Цель:** Управление пользователями, ролями, разрешениями. Multi-tenant login.

**Сущности:**

| Модель | Ключевые поля |
|--------|---------------|
| `AdminUser` | email, password_hash (bcrypt), first_name, last_name, is_superuser, force_password_change, last_login_at, role_id, tenant_id |
| `Role` | name, description, is_system, tenant-scoped |
| `Permission` | code (`resource:action`), name, resource, action |
| `AuditLog` | resource_type, resource_id, action, changes (JSONB), ip_address, user_agent |

**Дефолтные роли и разрешения (40+ permissions):**

| Роль | Доступ |
|------|--------|
| `platform_owner` | `*` — всё |
| `site_owner` | Весь контент + пользователи + SEO + настройки + аудит (read) |
| `content_manager` | Статьи + сервисы (read/update) + каталог + FAQ |
| `marketer` | Кейсы + отзывы + SEO + заявки (read) |
| `editor` | Статьи (без delete) + каталог (read) + FAQ (без delete) |

**Multi-tenant login flow:**
1. `POST /auth/login` — smart login: ищет пользователя по email во всех тенантах.
2. Если 1 тенант → авторизация.
3. Если 2+ тенантов → возвращает `selection_token` и список тенантов.
4. `POST /auth/select-tenant` — выбор тенанта по `selection_token`.
5. `POST /auth/switch-tenant` — переключение между тенантами (если пользователь есть в обоих).
6. `GET /auth/me/tenants` — список тенантов пользователя.

**Токены:**
- Access token: JWT, configurable expiry
- Refresh token: JWT
- Password reset token: 1 час
- Tenant selection token: 15 минут
- Token blacklist через Redis

**Что НЕ реализовано:**
- ❌ Invite-flow (нет invite-токенов, expiry, acceptance). Только создание + welcome email.
- ❌ 2FA / MFA
- ❌ OAuth (Google, GitHub)
- ❌ Password strength validation в сервисе
- ❌ `switch_tenant` записывает в AuditLog action="switch_tenant", но constraint `ck_audit_logs_action` не содержит этого значения → **баг, crash при switch-tenant**
- ❌ `role_id` не валидируется на принадлежность к тому же тенанту
- ❌ Refresh token не отзывается при logout

---

### 1.3 Каталог товаров (Catalog) — ✅ Готов

**Цель:** Товарный каталог с категориями, ценами, изображениями, фильтрацией. Для e-commerce и service-oriented сайтов.

**Сущности:**

| Модель | Ключевые поля |
|--------|---------------|
| `Category` | title, slug, parent_id (иерархия), description, image_url, sort_order, is_active |
| `Product` | sku, slug, title, brand, model, description, product_type, has_variants, price_from, price_to |
| `ProductImage` | url, alt, width/height, sort_order, is_cover |
| `ProductPrice` | price_type (regular/sale/wholesale/cost), amount, currency, valid_from/to |
| `ProductAlias` | alias (альтернативные артикулы) |
| `ProductAnalog` | analog_product_id, relation (equivalent/better/worse) |
| `ProductCategory` | product_id, category_id, is_primary (мультикатегорийность) |
| `UOM` | name, code, symbol (единицы измерения) |

**Типы товаров:** physical, digital, service, course, subscription

**Admin CRUD:**
- Категории: CRUD + tree view + сортировка
- Продукты: CRUD + поиск (title/sku/brand/model) + фильтр по brand/category/active
- Изображения: загрузка, удаление, reorder, set cover
- Цены: CRUD с типами и валидностью
- Алиасы: bulk create, delete
- Аналоги: add/remove с типом связи
- Привязка к категориям: `PUT /admin/products/{id}/categories`

**Public API:**
- `GET /public/categories` — дерево категорий
- `GET /public/categories/{slug}` — категория с продуктами
- `GET /public/products` — фильтрованный список
- `GET /public/products/{slug}` — детальная карточка
- `GET /public/filters` — фасетные фильтры с количествами
- `GET /public/seo/filter-pages` — SEO-страницы фильтров

**Фасетная фильтрация (`CatalogFilterService`):**
- Поиск по title, description
- Фильтр по категориям (slugs)
- Фильтр по параметрам (AND между параметрами, OR внутри параметра)
- Фильтр по цене (price_from/price_to)
- Фильтр по бренду
- Сортировка: newest, price_asc, price_desc, title_asc, title_desc
- Возврат facets: enum значения с count, number min/max, price range
- SEO filter pages: генерация URL-комбинаций для фильтров, кэш в Redis

**Ограничения:**
- SKU уникален per tenant
- Slug уникален per tenant (partial index, deleted_at IS NULL)
- Цена ≥ 0
- product_type строго из enum
- Аналог не может ссылаться на самого себя

**Что НЕ реализовано:**
- ❌ Локализация товаров (нет `ProductLocale` таблицы)
- ❌ Остатки/склад на уровне Product (только на Variant)
- ❌ Импорт/экспорт товаров (CSV, Excel)
- ❌ Дублирование товара
- ❌ Массовое обновление цен
- ❌ `ProductAlias` — нет unique constraint на (product_id, alias)

---

### 1.4 Параметры и характеристики (Parameters) — ✅ Готов

**Цель:** Динамические характеристики товаров для фильтрации и сравнения.

**Сущности:**

| Модель | Ключевые поля |
|--------|---------------|
| `Parameter` | name, slug, value_type (string/number/enum/bool/range), scope (global/category), is_filterable, is_required, constraints (JSONB) |
| `ParameterValue` | label, slug, code, sort_order (для enum-параметров) |
| `ParameterCategory` | parameter_id, category_id (привязка к категориям) |
| `ProductCharacteristic` | product_id, parameter_id, parameter_value_id, value_text/value_number/value_bool, source_type (manual/import/system), is_locked |

**CRUD (admin only):**
- Параметры: CRUD + search + filter by type/scope
- Значения: CRUD (только для enum)
- Привязка к категориям: `PUT /admin/parameters/{id}/categories`
- Характеристики: set/delete + **bulk set** (`PUT /admin/products/{id}/characteristics/bulk`)

**Ключевая логика:**
- Auto-create enum values: если label не найден при set_characteristic — создаётся автоматически
- Bulk set: замена характеристик per parameter (удаление старых + создание новых)
- Unique constraints: enum — (product, parameter, value), scalar — (product, parameter)

**Что НЕ реализовано:**
- ❌ Public API для параметров (фильтрация реализована через `CatalogFilterService`)
- ❌ Валидация constraints (JSONB) — поле есть, но не применяется
- ❌ Наследование параметров по иерархии категорий

---

### 1.5 Варианты и тарифы (Variants) — ✅ Готов

**Цель:** Модификации товара (размер, цвет, тариф) с собственными ценами, изображениями, комплектациями.

**Сущности:**

| Модель | Ключевые поля |
|--------|---------------|
| `ProductOptionGroup` | title, slug, display_type (dropdown/buttons/color/radio), is_required, parameter_id (связь с параметром) |
| `ProductOptionValue` | title, slug, color_hex, image_url, sort_order |
| `ProductVariant` | sku, slug, title, description, is_default, is_active, stock_quantity, weight |
| `VariantPrice` | price_type, amount, currency, valid_from/to |
| `VariantOptionLink` | variant_id, option_value_id (связь варианта с выбранными опциями) |
| `VariantInclusion` | title, description, is_included, icon, group (что входит/не входит в тариф) |
| `VariantImage` | url, alt, sort_order, is_cover |

**CRUD (admin only):**
- Option groups: CRUD per product
- Option values: CRUD per group
- Variants: CRUD + `POST /admin/products/{id}/variants/generate` — генерация матрицы
- Variant prices: CRUD
- Inclusions: CRUD (состав тарифа)
- Variant images: upload/delete

**Генерация матрицы вариантов:**
- Декартово произведение всех option values
- Автоматический SKU: `{product_sku}-{slugs}`
- Пропуск существующих SKU
- Опциональная базовая цена

**Price range refresh:**
- При изменении цен вариантов автоматически обновляются `Product.price_from/price_to`
- Для продуктов без вариантов — из `ProductPrice`

**Что НЕ реализовано:**
- ❌ Public API для вариантов отдельно (данные вложены в product detail)
- ❌ `ProductOptionGroup.tenant_id` не имеет FK constraint
- ❌ Управление остатками (stock_quantity есть в модели, но нет инвентарной логики)
- ❌ Автосоздание вариантов при добавлении нового option value

---

### 1.6 Контент-модули (Content) — ✅ Готов

**Цель:** Блог, портфолио, отзывы, FAQ — контент для клиентского сайта.

**Сущности:**

| Модель | Статус-машина | Ключевые поля |
|--------|---------------|---------------|
| `Article` | draft → published → archived | cover_image, reading_time, view_count, author_id |
| `Case` | draft → published → archived | client_name, project_year, project_duration, is_featured |
| `Review` | pending → approved / rejected | rating (1-5), author_name/company/position/photo, case_id, is_featured, source |
| `FAQ` | published/unpublished (bool) | category |
| `Topic` | — | icon, color (#RRGGBB) |
| `ContentBlock` | — | entity_type, block_type (text/image/video/gallery/link/result), media_url, device_type |

**Локализация:**
- Article, Case, FAQ, Topic — имеют `*Locale` таблицы с title, slug, description, SEO meta
- Review — НЕ локализован (одноязычный)

**Public API:**
- Articles: list published (filter by topic), get by slug, view count increment
- Cases: list published, get by slug
- Reviews: list approved, filter by case
- FAQ: list published
- Topics: list, get by slug

**Admin API:**
- Полный CRUD для каждой сущности
- Publish/Unpublish для articles и cases
- Approve/Reject для reviews
- Cover image upload для articles и cases
- Content blocks: CRUD + reorder (для articles, cases, services, employees, products)
- Locale management: add/update/delete переводов
- **Bulk operations:** publish, unpublish, archive, delete для articles/cases/faq/reviews

**ContentBlock система:**
- Полиморфная: entity_type (article/case/service/employee/product) + entity_id
- Типы блоков: text, image, video, gallery, link, result
- Device targeting: mobile, desktop, both
- Metadata: JSONB для дополнительных данных
- Порядок: reorder endpoint

**Что НЕ реализовано:**
- ❌ Автоматический расчёт reading_time
- ❌ Проверка наличия хотя бы одного locale перед публикацией
- ❌ Archive endpoint для отдельной статьи (есть только model method и bulk)
- ❌ Валидация case_id в Review (не проверяется принадлежность к тенанту)
- ❌ Поиск по отзывам (автор, текст)
- ❌ ContentBlock: нет FK на entity (polymorphic через entity_type+entity_id)

---

### 1.7 Компания (Company) — ✅ Готов

**Цель:** Информация о компании: услуги, команда, преимущества, адреса, контакты.

**Сущности:**

| Модель | Ключевые поля |
|--------|---------------|
| `Service` | icon, image_url, price_from, price_currency + ServiceLocale (slug, title, description) |
| `ServicePrice` | price, currency, locale |
| `ServiceTag` | tag, locale |
| `Employee` | photo_url, email, phone, linkedin, telegram + EmployeeLocale |
| `PracticeArea` | icon + PracticeAreaLocale (slug, title, description) |
| `Advantage` | icon + AdvantageLocale (slug, title, description) |
| `Address` | address_type (office/warehouse/showroom), latitude/longitude, working_hours, is_primary |
| `Contact` | contact_type (phone/email/whatsapp/telegram/...), value, is_primary |

**Связи:**
- Employee ↔ PracticeArea (M:N через EmployeePracticeArea)
- Case ↔ Service (M:N через CaseServiceLink)
- Content blocks для Service и Employee

**Public/Admin API:**
- Полный CRUD + locale management для каждой сущности
- Service: CRUD + prices + tags + content blocks + image upload
- Employee: CRUD + photo + content blocks + locale

**Что НЕ реализовано:**
- ❌ Service не имеет back-reference на CaseServiceLink (нельзя получить кейсы по услуге из модели)
- ❌ Нет фильтрации услуг по тегам в public API

---

### 1.8 Документы (Documents) — ✅ Готов

**Цель:** Публикация документов (правовые, регулярные, инструкции) с файлами.

**Сущности:** `Document` (status: draft/published/archived, file_url, document_version, document_date) + `DocumentLocale` (slug, title, excerpt, full_description)

**Admin:** CRUD + publish/unpublish + file upload/delete  
**Public:** list published, get by slug

**Что НЕ реализовано:**
- ❌ Нет типизации документов (legal, manual, policy)
- ❌ Нет версионирования файлов (document_version — строка, не связана с историей)

---

### 1.9 Лиды и заявки (Leads) — ✅ Готов

**Цель:** Приём заявок с сайта, CRM-like управление.

**Сущности:**

| Модель | Ключевые поля |
|--------|---------------|
| `InquiryForm` | slug, name, fields_config (JSONB), notification_email, success_message |
| `Inquiry` | status (new→in_progress→contacted→completed→spam→cancelled), name, email, phone, company, message, service_id, product_id, custom_fields (JSONB), assigned_to, notes |

**Аналитика заявки (автоматический сбор):**
- UTM: source, medium, campaign, term, content
- Referrer, source_url, page_path, page_title
- Device: user_agent, device_type, browser, os, screen_resolution
- Geo: ip_address, country, city, region
- Поведение: session_id, session_page_views, time_on_page

**Public API:**
- `POST /public/inquiries` — отправка заявки (+ form slug для custom forms)
- `POST /public/inquiries/upload` — FormData с файлами
- Rate limit: 3 req/min per IP

**Admin API:**
- Inquiry forms: CRUD
- Inquiries: list (filter by status, form_id, date, search), get, update (status, assigned_to, notes), delete
- Analytics: `GET /admin/inquiries/analytics` — total, by_status, by_utm_source, by_device_type

**Уведомления:** Telegram при создании заявки (автоматически через `TelegramNotifier`)

**Что НЕ реализовано:**
- ❌ `notification_email` на InquiryForm не используется (email не отправляется)
- ❌ Daily/weekly аналитика (только aggregate)
- ❌ Фильтр по service_id в list_inquiries
- ❌ Relationship Inquiry→Service отсутствует (есть FK, но нет ORM relationship)
- ❌ Экспорт заявок в CRM

---

### 1.10 SEO — ✅ Готов

**Цель:** Полный SEO-стек: мета-теги, sitemap, robots, IndexNow, редиректы, llms.txt.

**Сущности:**
- `SEORoute`: path, locale, title, description, keywords, og_image, robots, canonical_url, structured_data (JSONB), sitemap_priority/changefreq
- `Redirect`: from_path, to_path, status_code (301/302/307/308), hit_count, is_active

**Public API:**
- `GET /public/seo/meta?path=...&locale=...` — мета-теги для страницы
- `GET /public/sitemap.xml` — основной sitemap
- `GET /public/sitemap-index.xml` — sitemap index (pages, articles, cases, services)
- `GET /public/sitemap-{segment}-{locale}.xml` — сегментные sitemaps
- `GET /public/robots.txt` — robots.txt (кастомные правила из TenantSettings)
- `GET /public/seo/redirects` — список активных редиректов
- `GET /public/indexnow/{key}.txt` — IndexNow key file
- `GET /public/llms.txt` — AI-friendly описание компании

**Admin API:**
- SEO routes: list, create_or_update, update, delete
- Redirects: CRUD
- Revalidate: `POST /admin/seo/revalidate` — IndexNow push

**IndexNow:**
- Поддержка 4 движков: Bing, Yandex, Seznam, Naver
- Batch до 10 000 URL
- Rate limiting: 60 секунд между запросами
- Дедупликация URL

**llms.txt:**
- Автоматическая генерация: компания, топ-5 услуг, топ-3 кейса, контакты
- Кастомный контент из TenantSettings

**Что НЕ реализовано:**
- ❌ Автоматический IndexNow при publish/update контента (есть helper, но не вызывается)
- ❌ Sitemap index не включает segments: team, documents
- ❌ Нет structured data templates (JSON-LD)
- ❌ Нет Open Graph image generation

---

### 1.11 Медиа и файлы (Assets) — ✅ Готов

**Цель:** Файловое хранилище на S3/MinIO с presigned URLs.

**Сущности:** `FileAsset` (storage_key, url, cdn_url, original_filename, mime_type, size_bytes, width/height, alt_text, folder, uploaded_by)

**Admin API:**
- `POST /admin/files/upload-url` — получение presigned upload URL
- `POST /admin/files` — регистрация загруженного файла
- `GET /admin/files` — список файлов (пагинация)
- `PATCH/DELETE /admin/files/{id}` — обновление/удаление

**Что НЕ реализовано:**
- ❌ Image processing (resize, thumbnails, WebP)
- ❌ Virus scanning
- ❌ Очистка orphan-файлов в S3
- ❌ Валидация MIME type vs расширение

---

### 1.12 Telegram-интеграция — ✅ Готов

**Цель:** Per-tenant Telegram-бот для уведомлений о заявках.

**Сущности:** `TelegramIntegration` (tenant_id, bot_token_encrypted, owner_chat_id, webhook_secret, welcome_message, is_active)

**Admin API:**
- CRUD интеграции
- Webhook setup/remove
- Test message
- `POST /webhook/{webhook_secret}` — incoming webhook

**Логика:**
- Encrypted bot token (Fernet AES)
- Token validation через Telegram getMe API
- Auto webhook при наличии PUBLIC_API_URL
- HTML-formatted inquiry notifications с custom fields и UTM
- Message splitting при > 4096 символов

**Что НЕ реализовано:**
- ❌ Дублирование уведомлений: legacy `TelegramService` (глобальный бот из config) + per-tenant `TelegramNotifier` могут сработать одновременно
- ❌ Нет retry при ошибке отправки
- ❌ Только `message` updates (нет callback_query, inline)

---

### 1.13 Email-уведомления (Notifications) — ⚠️ Частично

**Цель:** Отправка email уведомлений через различных провайдеров.

**Провайдеры:** SMTP, SendGrid, Mailgun, Console (лог в stdout)

**Типы писем:**
- Welcome (при создании пользователя)
- Password reset
- Inquiry notification
- Test email

**Per-tenant конфигурация:** email_provider, smtp_*, email_api_key — из TenantSettings, fallback на глобальные из config

**Логирование:** `EmailLog` (tenant, to, subject, type, provider, status, error)

**Что НЕ реализовано:**
- ❌ HTML-шаблоны (только plain text)
- ❌ Retry при ошибке отправки
- ❌ Email notification при новой заявке (только Telegram, `notification_email` не используется)
- ❌ Логирование пропускается при tenant_id=None

---

### 1.14 Локализация (Localization) — ✅ Готов

**Цель:** Мультиязычность контента.

**Локализованные сущности:**
Article, Topic, FAQ, Case, Service, Employee, PracticeArea, Advantage, Address, Document — каждая имеет `*Locale` таблицу с полями title, slug, description + SEO meta.

**Модель:** `LocaleConfig` (tenant, locale, name, native_name, is_enabled, is_default, is_rtl)  
**Дефолтные:** ru, en

**Как работает:**
- Каждый запрос принимает `?locale=ru` параметр
- Публичные API фильтруют по locale
- Админские API управляют отдельными locale записями (CRUD)

**Что НЕ реализовано:**
- ❌ Каталог (Product, Category) НЕ локализован
- ❌ Review НЕ локализован
- ❌ Нет fallback-цепочки локалей
- ❌ Нет сервисного слоя для LocaleConfig
- ❌ Нет форматов валют/дат per locale

---

### 1.15 Дашборды — ✅ Готов

**Tenant Dashboard (`GET /admin/dashboard`):**
- Контент: количество articles, cases, employees, services, FAQs, reviews
- Заявки: total, pending, in_progress, done, this_month
- Контент по статусам: published/draft/archived для articles и cases

**Platform Dashboard (platform_owner only):**
- Overview: кол-во тенантов, пользователей, заявок, неактивных тенантов (30 дней)
- Tenant table: search, sort, pagination, content counts, inquiries, features, last login
- Tenant detail: content breakdown, inquiry analytics (UTM, device, country, top pages), features, users, audit
- Trends: новые тенанты/пользователи по месяцам, заявки по дням, логины по дням
- Health alerts: неактивные тенанты, зависшие заявки, пустые тенанты, низкое adoption фич, высокий spam ratio, снижение заявок

**Что НЕ реализовано:**
- ❌ `recent_activity` в tenant dashboard всегда пустой
- ❌ Нет date range фильтров
- ❌ Нет кэширования тяжёлых platform-запросов

---

### 1.16 Экспорт и аудит — ⚠️ Частично

**Экспорт (`GET /admin/export`):**
- Ресурсы: inquiries, employees, seo_routes, audit_logs
- Форматы: CSV, JSON
- Фильтры: status, date_from/date_to
- Лимит: 10 000 строк

**Аудит:**
- Логирование: create, update, delete, login, logout
- Фильтры: user_id, resource_type, resource_id, action, date range
- Пагинация

**Что НЕ реализовано:**
- ❌ Экспорт articles, cases, services, documents, products
- ❌ XLSX формат
- ❌ Streaming для больших экспортов (всё в памяти)
- ❌ Retention policy для audit logs
- ❌ `resource_name` всегда None, `status` всегда "success"

---

## БЛОК 2 — ИНФРАСТРУКТУРА И АРХИТЕКТУРНЫЕ РЕШЕНИЯ

---

### 2.1 Стек технологий

| Компонент | Технология | Версия |
|-----------|------------|--------|
| **Backend** | Python + FastAPI | 3.11 |
| **ORM** | SQLAlchemy (async) | 2.x |
| **Валидация** | Pydantic | v2 |
| **БД** | PostgreSQL | 16 |
| **Кэш/Брокер** | Redis | 7 |
| **Объектное хранилище** | MinIO / AWS S3 | — |
| **Background jobs** | TaskIQ + Redis broker | — |
| **Reverse proxy** | Caddy | v2 |
| **Миграции** | Alembic | — |
| **Тесты** | pytest (unit + integration + API) | — |
| **CI/CD** | GitHub Actions | — |
| **Контейнеризация** | Docker + Docker Compose | — |
| **Admin Panel** | Next.js + TypeScript + Tailwind + Zustand + React Query | — |
| **Client Site** | Next.js + TypeScript + Tailwind + Zustand | — |

### 2.2 Мультитенантность

**Модель:** Shared database, row-level isolation через `tenant_id` в каждой таблице.

**Реализация:**
- `TenantMixin` — базовый mixin с `tenant_id` FK
- Все сервисы фильтруют по `tenant_id`
- Public API: `tenant_id` из query parameter (`?tenant_id=...`)
- Admin API: `tenant_id` из JWT токена + `X-Tenant-ID` header
- `single_tenant_mode`: упрощённый режим для single-client деплоя (дефолтный тенант, headers не нужны)

**Изоляция данных:**
- Unique constraints включают `tenant_id` (slug, sku, email)
- Partial indexes с `deleted_at IS NULL`
- Soft delete через `SoftDeleteMixin`
- Optimistic locking через `VersionMixin`

### 2.3 Кэширование и производительность

| Механизм | Реализация | TTL |
|----------|------------|-----|
| CORS origins | Redis + in-memory | 5 мин |
| Tenant status | Redis | 30 сек |
| Domain→Tenant resolve | Redis | 5 мин |
| SEO filter pages | Redis | настраивается |
| HTTP Cache-Control | Middleware | public 5 мин, sitemap 1 час |
| ETag | MD5 от response body | — |
| Rate limiting | Redis + in-memory fallback | — |

**Rate limits:**

| Endpoint | Лимит |
|----------|-------|
| Login | 5 req/5 мин (prod), 50 req/мин (dev) |
| Inquiry submit | 3 req/мин |
| Public API | 100 req/мин |
| Admin API | Без лимита |

### 2.4 Security

- **Encryption:** Fernet (AES-128-CBC) для bot tokens, SMTP passwords, API keys
- **Passwords:** bcrypt
- **CORS:** Dynamic middleware — origins из DB (tenant_domains + site_url) + env
- **Headers:** X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS, X-XSS-Protection
- **RBAC:** Granular permissions (40+), wildcard support, role-based + permission-based checks
- **Token blacklist:** Redis

### 2.5 Background Jobs

**Broker:** TaskIQ с Redis (ListQueueBroker)

**Задачи:**
- `provision_domain_task` — DNS-верификация + SSL через Caddy
- `poll_ssl_status_task` — polling статуса сертификата (до 10 попыток, 30 сек интервал)

### 2.6 Деплой

- **Docker Compose:** prod файл с services: backend, worker, postgres, redis, minio, caddy, migrations
- **Caddy:** on-demand TLS для кастомных доменов, `ask` endpoint на бэкенде (`/internal/domains/check`)
- **CI/CD:** GitHub Actions — lint (ruff), unit tests, integration tests (postgres + redis), API tests, coverage
- **Deploy script:** `make deploy` → `deploy.sh` → git pull, build, migrate, up

---

## БЛОК 3 — FEATURE FLAGS И МОДУЛЬНОСТЬ

---

### Feature Flags (per-tenant, 11 штук)

| Flag | Категория | Что контролирует |
|------|-----------|------------------|
| `blog_module` | content | Статьи, топики |
| `cases_module` | content | Кейсы, портфолио |
| `reviews_module` | content | Отзывы |
| `faq_module` | content | FAQ |
| `team_module` | company | Команда, сотрудники |
| `services_module` | company | Услуги |
| `seo_advanced` | platform | SEO мета, редиректы |
| `multilang` | platform | Мультиязычность |
| `analytics_advanced` | platform | Аналитика заявок (UTM, device, geo) |
| `catalog_module` | commerce | Товарный каталог |
| `variants_module` | commerce | Варианты и тарифы |

**Как работают:**
- Admin API: `require_feature("blog_module")` — dependency, блокирует endpoint если фича выключена
- Public API: `require_feature_public("blog_module")` — аналогично
- Superuser и platform_owner bypass все проверки
- При создании тенанта — **все фичи включены по умолчанию**

**Модульность:**
- Платформа — конструктор: можно включить только каталог, или только блог, или комбинацию
- Feature flags контролируют и API, и UI (admin panel проверяет `GET /auth/me/features`)

**Маппинг на тарифные планы (рекомендация):**

| Тариф | Модули | Примерная цена |
|-------|--------|----------------|
| **Starter** | blog, faq, services, team | Базовый |
| **Business** | + cases, reviews, seo_advanced, multilang, analytics_advanced | Средний |
| **Commerce** | + catalog, variants | Премиум |
| **Enterprise** | Всё + кастомизация | Индивидуально |

---

## БЛОК 4 — БИЗНЕС-АУДИТ

---

### 4.1 Целевая аудитория

**Основные сегменты:**

| Сегмент | Use case | Ключевые модули |
|---------|----------|-----------------|
| **Сервисные компании** (юридические, консалтинг, медицина) | Сайт-визитка + блог + кейсы + заявки | services, team, cases, articles, leads |
| **E-commerce** (каталожные сайты, оптовые витрины) | Каталог + варианты + фильтрация + цены | catalog, variants, parameters, leads |
| **Агентства и продакшны** | Портфолио + команда + отзывы | cases, team, reviews, services |
| **Образовательные платформы** | Курсы (product_type=course) + тарифы (variants) | catalog, variants |
| **SaaS для web-студий** | White-label CMS для своих клиентов | вся платформа + мультитенантность |

**Лучшие индустрии:** юридические фирмы, медицинские клиники, консалтинговые агентства, B2B каталожные компании, web-студии (reseller модель).

### 4.2 Конкурентное позиционирование

| Критерий | Mediann CMS | Tilda | WordPress | Webflow | Strapi |
|----------|-------------|-------|-----------|---------|--------|
| Мультитенантность | ✅ Нативная | ❌ | ❌ | ❌ | ❌ Plugin |
| Программный каталог | ✅ API-first | ⚠️ Ограничен | ⚠️ WooCommerce | ⚠️ CMS fields | ✅ Custom |
| Feature flags | ✅ Per-tenant | ❌ | ❌ | ❌ | ❌ |
| Custom domains + auto SSL | ✅ Caddy on-demand | ❌ | ❌ | ✅ Enterprise | ❌ |
| Per-tenant email config | ✅ | ❌ | ❌ | ❌ | ❌ |
| SEO (sitemap, IndexNow, llms.txt) | ✅ Полный | ⚠️ Базовый | ⚠️ Plugins | ⚠️ Базовый | ❌ |
| RBAC | ✅ Granular (40+ perms) | ❌ | ⚠️ Plugins | ⚠️ Базовый | ✅ |
| Telegram integration | ✅ Per-tenant | ❌ | ❌ | ❌ | ❌ |
| Фасетная фильтрация | ✅ | ❌ | ⚠️ Plugins | ❌ | ❌ Custom |
| Self-hosted | ✅ | ❌ | ✅ | ❌ | ✅ |

**Killer Features:**
1. **Нативная мультитенантность** — единый бэкенд для сотен клиентов
2. **Feature flags как тарифные планы** — модульная продажа
3. **Auto SSL для кастомных доменов** — белый лейбл из коробки
4. **Фасетная фильтрация с SEO-страницами** — каталожный e-commerce
5. **Per-tenant Telegram + Email** — персонализированные уведомления

### 4.3 Готовность к рынку (Product Readiness)

| Аспект | Оценка | Комментарий |
|--------|--------|-------------|
| **Функциональная полнота** | 8/10 | 20 модулей, 250+ endpoints. Покрывает MVP для сервисных и каталожных сайтов. Не хватает: биллинг, импорт/экспорт товаров, HTML-шаблоны email. |
| **Стабильность** | 7/10 | Optimistic locking, soft delete, валидации Pydantic v2. Есть баги: switch_tenant audit crash, дублирование Telegram-уведомлений. |
| **Масштабируемость** | 8/10 | Shared DB + row-level isolation. Redis кэширование. TaskIQ workers. Потолок — одна БД (нет sharding / database-per-tenant). |
| **Безопасность** | 8/10 | RBAC с wildcards, rate limiting, bcrypt, Fernet encryption, dynamic CORS, security headers. Не хватает: 2FA, key rotation, audit для всех actions. |
| **Developer Experience** | 9/10 | 100+ документов в /docs, OpenAPI auto-docs, Alembic migrations, CI/CD, Docker Compose, Makefile. Образцовый DX. |
| **User Experience** | 7/10 | Функциональная админка. Не хватает: onboarding wizard, bulk import, drag-and-drop content builder. |

**Средняя оценка: 7.8/10**

### 4.4 Ограничения и технический долг

**Критические для production:**

| # | Проблема | Приоритет | Сложность |
|---|----------|-----------|-----------|
| 1 | `switch_tenant` crash: audit action не в constraint | 🔴 Critical | Низкая (ALTER TABLE) |
| 2 | Дублирование Telegram-уведомлений (legacy + per-tenant) | 🔴 Critical | Средняя |
| 3 | Email notification при заявке не работает (только Telegram) | 🟡 High | Средняя |
| 4 | Нет биллинга / лимитов per-tenant | 🟡 High | Высокая |
| 5 | Каталог не локализован | 🟡 High | Высокая |
| 6 | Нет импорта товаров (CSV/Excel) | 🟡 High | Средняя |
| 7 | Нет key rotation для encryption | 🟠 Medium | Средняя |
| 8 | `TenantDomainService.get_domain` не tenant-scoped | 🟠 Medium | Низкая |
| 9 | IndexNow rate limiting per-process, не shared | 🟠 Medium | Средняя |
| 10 | ETag из MD5 body → всё равно генерирует полный response | 🟢 Low | Средняя |

**Архитектурные ограничения:**
- Shared database — потолок ~1000 тенантов (зависит от объёма данных)
- Нет database-per-tenant mode (подготовка есть в коде, но не реализована)
- TaskIQ worker — один тип задач (domains). Нет scheduled tasks, no retries with backoff
- Нет WebSocket (real-time updates)
- Нет CDN-интеграции (только S3 presigned)

### 4.5 Монетизация

**Рекомендуемая модель: SaaS подписка + модульное ценообразование**

| Тариф | Модули | Пользователи | Домены | Цена/мес |
|-------|--------|--------------|--------|----------|
| **Starter** | blog, faq, services, team, leads | 2 | 1 (*.mediann.dev) | $29 |
| **Business** | + cases, reviews, seo, multilang, analytics | 5 | 1 custom domain | $79 |
| **Commerce** | + catalog, variants | 10 | 2 custom domains | $149 |
| **Agency** (reseller) | Все модули × N тенантов | Unlimited | Unlimited | $49/тенант |

**Unit-economics (оценка стоимости 1 тенанта):**
- Compute: ~$0.05/мес (shared backend, proportional CPU)
- Storage: ~$0.10/мес (PostgreSQL rows, S3 images)
- SSL: $0 (Caddy + Let's Encrypt)
- Email: ~$0.01/email (SendGrid/Mailgun)
- **Итого: ~$1-5/мес per tenant** → маржа 85-95%

---

## БЛОК 5 — ФУНКЦИОНАЛЬНЫЕ ТРЕБОВАНИЯ (PRD)

---

### 5.1 Реализованные функциональные требования (FR)

| ID | Требование | Модуль | Статус |
|----|------------|--------|--------|
| FR-01 | Мультитенантная архитектура с изоляцией данных | Core | ✅ |
| FR-02 | CRUD организаций с настройками и feature flags | Tenants | ✅ |
| FR-03 | Кастомные домены с автоматическим SSL | Tenants + Caddy | ✅ |
| FR-04 | Аутентификация с JWT (access + refresh tokens) | Auth | ✅ |
| FR-05 | Multi-tenant login (smart login, select, switch) | Auth | ✅ |
| FR-06 | RBAC: 5 ролей, 40+ разрешений, wildcard support | Auth | ✅ |
| FR-07 | Password reset через email | Auth | ✅ |
| FR-08 | Товарный каталог с категориями и иерархией | Catalog | ✅ |
| FR-09 | Мультикатегорийность товаров | Catalog | ✅ |
| FR-10 | Система ценообразования (regular/sale/wholesale/cost) | Catalog | ✅ |
| FR-11 | Фасетная фильтрация с подсчётом количеств | Catalog | ✅ |
| FR-12 | SEO filter pages (комбинации фильтров) | Catalog | ✅ |
| FR-13 | Динамические параметры товаров (string/number/enum/bool/range) | Parameters | ✅ |
| FR-14 | Bulk-операции с характеристиками | Parameters | ✅ |
| FR-15 | Варианты товаров с генерацией матрицы | Variants | ✅ |
| FR-16 | Inclusions (состав тарифа/комплектации) | Variants | ✅ |
| FR-17 | Изображения вариантов | Variants | ✅ |
| FR-18 | Блог с топиками и статусами публикации | Content | ✅ |
| FR-19 | Портфолио (кейсы) с связью с услугами | Content | ✅ |
| FR-20 | Отзывы с модерацией (pending→approved/rejected) | Content | ✅ |
| FR-21 | FAQ с категориями | Content | ✅ |
| FR-22 | Полиморфные контент-блоки (text/image/video/gallery/link/result) | Content | ✅ |
| FR-23 | Bulk-операции (publish/unpublish/archive/delete) | Content | ✅ |
| FR-24 | Услуги с прайсами и тегами | Company | ✅ |
| FR-25 | Команда с компетенциями | Company | ✅ |
| FR-26 | Преимущества, адреса, контакты | Company | ✅ |
| FR-27 | Документы с файлами и статусами | Documents | ✅ |
| FR-28 | Приём заявок с кастомными формами | Leads | ✅ |
| FR-29 | Аналитика заявок (UTM, device, geo) | Leads | ✅ |
| FR-30 | SEO: sitemap, robots.txt, мета-теги, редиректы | SEO | ✅ |
| FR-31 | IndexNow (push уведомление поисковикам) | SEO | ✅ |
| FR-32 | llms.txt для AI-ботов | SEO | ✅ |
| FR-33 | Файловое хранилище (S3/MinIO, presigned URLs) | Assets | ✅ |
| FR-34 | Telegram-бот per-tenant | Telegram | ✅ |
| FR-35 | Email через SMTP/SendGrid/Mailgun per-tenant | Notifications | ✅ |
| FR-36 | Мультиязычность контента | Localization | ✅ |
| FR-37 | Tenant dashboard (метрики) | Dashboard | ✅ |
| FR-38 | Platform dashboard (здоровье платформы, алерты) | Platform | ✅ |
| FR-39 | Экспорт (inquiries, employees, seo, audit → CSV/JSON) | Export | ✅ |
| FR-40 | Аудит-лог действий | Audit | ✅ |
| FR-41 | Google/Yandex webmaster verification | Tenants | ✅ |
| FR-42 | 5 типов товаров (physical/digital/service/course/subscription) | Catalog | ✅ |

### 5.2 Нефункциональные требования (NFR)

| ID | Требование | Реализация |
|----|------------|------------|
| NFR-01 | Response time < 200ms для публичных endpoints | Redis caching, partial indexes, connection pooling |
| NFR-02 | Rate limiting для критичных endpoints | Redis-based middleware + in-memory fallback |
| NFR-03 | Data encryption at rest для secrets | Fernet AES-128-CBC |
| NFR-04 | Security headers (HSTS, X-Frame-Options и др.) | SecurityHeadersMiddleware |
| NFR-05 | Dynamic CORS | DynamicCORSMiddleware с Redis cache |
| NFR-06 | HTTP caching (Cache-Control, ETag, 304) | CacheHeadersMiddleware |
| NFR-07 | Soft delete для всех основных сущностей | SoftDeleteMixin |
| NFR-08 | Optimistic locking | VersionMixin |
| NFR-09 | Structured logging | JSON logs, request_id |
| NFR-10 | Health checks (liveness + readiness) | /health/live, /health/ready |
| NFR-11 | CI/CD pipeline | GitHub Actions: lint, test, coverage |
| NFR-12 | Containerized deployment | Docker Compose prod |
| NFR-13 | Auto TLS for custom domains | Caddy on-demand TLS |
| NFR-14 | Database migrations | Alembic |

### 5.3 Gap Analysis — НЕ реализовано

| ID | Требование | Приоритет | Категория |
|----|------------|-----------|-----------|
| GAP-01 | Биллинг и подписки (Stripe/Paddle) | 🔴 Must Have (для SaaS) | Монетизация |
| GAP-02 | Лимиты per-tenant (пользователи, хранилище, API calls) | 🔴 Must Have | Монетизация |
| GAP-03 | Invite-flow для пользователей (токен, expiry, accept) | 🔴 Must Have | Auth |
| GAP-04 | 2FA / MFA | 🟡 Must Have | Security |
| GAP-05 | Локализация каталога (ProductLocale, CategoryLocale) | 🟡 Must Have | Catalog |
| GAP-06 | Импорт товаров (CSV/Excel) | 🟡 Must Have | Catalog |
| GAP-07 | HTML email-шаблоны | 🟡 Must Have | Notifications |
| GAP-08 | Email notification при заявке | 🟡 Must Have | Leads |
| GAP-09 | OAuth login (Google, GitHub) | 🟠 Nice to Have | Auth |
| GAP-10 | Drag-and-drop page builder (вместо content blocks API) | 🟠 Nice to Have | Content |
| GAP-11 | Webhooks для внешних интеграций | 🟠 Nice to Have | Platform |
| GAP-12 | REST API → GraphQL (или дополнительно) | 🟠 Nice to Have | DX |
| GAP-13 | Image processing (resize, thumbnails, WebP) | 🟠 Nice to Have | Assets |
| GAP-14 | Scheduled tasks (publish в будущем, отчёты) | 🟠 Nice to Have | Platform |
| GAP-15 | WebSocket для real-time updates | 🟠 Nice to Have | DX |
| GAP-16 | A/B тестирование контента | 🔵 Future | Content |
| GAP-17 | AI-генерация контента (GPT integration) | 🔵 Future | Content |
| GAP-18 | Database-per-tenant mode | 🔵 Future | Architecture |
| GAP-19 | Marketplace шаблонов/тем | 🔵 Future | Platform |
| GAP-20 | White-label admin panel (кастомный брендинг) | 🔵 Future | Platform |
| GAP-21 | Mobile app (React Native) | 🔵 Future | Frontend |
| GAP-22 | Inventory management (остатки, складской учёт) | 🔵 Future | Catalog |
| GAP-23 | Payment gateway (приём платежей) | 🔵 Future | Commerce |

### 5.4 Приоритизация gap'ов для MVP → Product-Market Fit

**Phase 1 — Critical Path (1-2 месяца):**
- GAP-01 + GAP-02: Биллинг + лимиты (без этого нет SaaS)
- GAP-03: Invite-flow (без этого нельзя нормально добавлять пользователей)
- GAP-08: Email при заявке (базовое ожидание клиентов)
- Bugfix: switch_tenant audit, дублирование Telegram

**Phase 2 — Growth (2-4 месяца):**
- GAP-04: 2FA
- GAP-05 + GAP-06: Локализация + импорт каталога
- GAP-07: HTML email templates
- GAP-10: Улучшенный content builder

**Phase 3 — Scale (4-6 месяцев):**
- GAP-09: OAuth
- GAP-11: Webhooks
- GAP-13: Image processing
- GAP-14: Scheduled tasks
- GAP-20: White-label branding

---

## Заключение

**Mediann CMS** — зрелая SaaS-платформа уровня **late MVP / early Product-Market Fit** с сильной технической базой:

- **20 модулей**, **250+ API endpoints**, **60+ моделей** — широкий функционал
- **Нативная мультитенантность** — ключевое конкурентное преимущество
- **Feature flags** — готовый механизм для тарифных планов
- **Сильный DX** — 100+ документов, CI/CD, Docker, OpenAPI

**Для выхода на рынок критически нужны:** биллинг, invite-flow, email notifications. Остальное — итерации на основе обратной связи от первых клиентов.
