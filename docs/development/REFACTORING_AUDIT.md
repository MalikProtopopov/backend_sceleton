# Аудит проекта для рефакторинга

> Дата составления: 24 февраля 2026  
> Ветка: `feat/product-catalog`  
> Цель документа: предоставить полный контекст проекта для поиска разработчика и составления плана рефакторинга

---

## 1. Что это за проект

**Multi-tenant SaaS бэкенд** — система управления контентом (CMS) для B2B-клиентов.  
Каждый клиент (tenant) получает изолированную среду со своим контентом, пользователями, доменом и конфигурацией.

### Основные возможности

- Управление тенантами (организациями), пользователями и ролями
- Контент-модули: статьи, кейсы, отзывы, FAQ, сервисы, сотрудники
- Каталог продуктов: категории, UOM, товары, цены (новый модуль, в разработке)
- Параметры продуктов: словарь атрибутов, характеристики товаров (новый модуль)
- SEO: маршруты, редиректы, ситкарта
- Лиды (заявки) с аналитикой
- Документы с версионированием
- Уведомления (Email / Telegram)
- S3-хранилище (MinIO в dev, S3-совместимые в prod)
- Аудит-лог действий пользователей
- API как для публичного фронтенда, так и для административной панели

### Для кого строится

Платформный оператор (`platform_owner`) управляет набором организаций. Каждая организация (`site_owner`, `content_manager` и т.д.) работает в изоляции друг от друга.

---

## 2. Технологический стек

| Категория | Технология | Версия |
|---|---|---|
| Язык | Python | 3.11+ |
| Веб-фреймворк | FastAPI | 0.109.0+ |
| ASGI-сервер | Uvicorn | 0.27.0+ |
| ORM | SQLAlchemy (async) | 2.0.25+ |
| Валидация | Pydantic | 2.5.3+ |
| БД | PostgreSQL | 16 |
| Async-драйвер БД | asyncpg | 0.29.0+ |
| Миграции | Alembic | 1.13.1+ |
| Кэш / Очереди | Redis | 7 (redis-py 5.0.1+) |
| Очередь задач | taskiq + taskiq-redis | 0.11.0+ |
| Auth | python-jose (JWT), passlib (bcrypt) | 3.3.0+ / 1.7.4+ |
| S3-хранилище | boto3 | 1.34.0+ |
| HTTP-клиент | httpx | 0.26.0+ |
| Логирование | structlog | 24.1.0+ |
| Retry | tenacity | 8.2.3+ |
| Email | aiosmtplib | 3.0.0+ |
| Slugify | python-slugify | 8.0.1+ |
| Контейнеризация | Docker + docker-compose | — |
| Объектное хранилище (dev) | MinIO | latest |
| Линтер | ruff | 0.1.14+ |
| Типизация | mypy (strict) | 1.8.0+ |
| Тесты | pytest + pytest-asyncio | 8.0.0+ |

---

## 3. Метрики кодовой базы

| Показатель | Значение |
|---|---|
| Всего Python-файлов | ~130 |
| Всего строк кода (Python) | ~30 000 |
| Модулей в `app/modules/` | 16 |
| Миграций Alembic | 32 |
| Эндпоинтов API (оценка) | 150+ |
| Файлов ядра (`app/core/`) | 17 |

### Крупнейшие файлы

| Файл | Строк | Комментарий |
|---|---|---|
| `content/service.py` | 1 853 | Самый большой — кандидат на декомпозицию |
| `company/service.py` | 1 276 | Большой, но управляемый |
| `auth/service.py` | 1 102 | Включает всю логику RBAC |
| `platform_dashboard/service.py` | 1 008 | Агрегирует данные по всем тенантам |
| `auth/router.py` | 923 | Много маршрутов — допустимо |
| `seo/router.py` | 847 | Аналогично |
| `catalog/service.py` | 841 | Новый модуль |
| `core/redis.py` | 517 | Клиенты Redis + blacklist |
| `core/exceptions.py` | 508 | Иерархия ошибок RFC 7807 |
| `core/security.py` | 479 | JWT + RBAC |

---

## 4. Архитектура

### Структура приложения

```
backend/
├── app/
│   ├── core/                # Ядро: DB, Redis, JWT, исключения, базовые классы
│   │   ├── base_model.py    # Миксины: TenantMixin, SoftDeleteMixin, VersionMixin, SEOMixin
│   │   ├── base_service.py  # Базовый CRUD-сервис (310 строк)
│   │   ├── database.py      # Async-сессии SQLAlchemy
│   │   ├── security.py      # JWT, bcrypt, RBAC
│   │   ├── dependencies.py  # FastAPI DI: get_current_user, PermissionChecker
│   │   ├── exceptions.py    # RFC 7807 иерархия ошибок
│   │   ├── tenant.py        # Резолвинг тенанта
│   │   ├── redis.py         # Blacklist токенов, кэш
│   │   ├── pagination.py    # Cursor/offset пагинация
│   │   ├── audit.py         # Хелперы для аудит-лога
│   │   ├── locale_helpers.py
│   │   ├── image_upload.py  # S3 загрузка
│   │   └── encryption.py
│   ├── middleware/
│   │   ├── cors.py          # Динамический CORS из БД
│   │   ├── rate_limit.py    # Rate limiting
│   │   ├── cache.py         # Cache-Control заголовки
│   │   ├── request_logging.py
│   │   └── feature_check.py # Проверка feature flags
│   ├── modules/
│   │   ├── auth/            # Авторизация, RBAC, пользователи, роли
│   │   ├── tenants/         # Управление тенантами, feature flags, домены
│   │   ├── content/         # Статьи, кейсы, отзывы, FAQ, топики
│   │   ├── company/         # Сервисы, сотрудники, практики, контакты
│   │   ├── catalog/         # [NEW] Товары, категории, UOM, цены
│   │   ├── parameters/      # [NEW] Словарь параметров, характеристики
│   │   ├── leads/           # Заявки, аналитика
│   │   ├── seo/             # SEO-маршруты, редиректы, sitemap
│   │   ├── assets/          # Загрузка файлов, S3
│   │   ├── documents/       # Документы с локализацией и версионированием
│   │   ├── audit/           # Просмотр аудит-лога
│   │   ├── dashboard/       # Статистика тенанта
│   │   ├── platform_dashboard/ # Статистика платформного оператора
│   │   ├── export/          # Экспорт данных
│   │   ├── telegram/        # Telegram-бот
│   │   ├── notifications/   # Email/SMS уведомления
│   │   ├── localization/    # Конфигурация локалей
│   │   └── internal/        # Внутренние эндпоинты (Caddy TLS arbiter)
│   └── main.py              # Инициализация FastAPI, регистрация роутеров
├── alembic/
│   ├── env.py
│   └── versions/            # 32 миграции (001–032)
└── pyproject.toml
```

### Паттерны, применённые в проекте

1. **Domain-Driven Design (DDD)** — каждый модуль = домен (`models`, `schemas`, `service`, `router`)
2. **Repository pattern** через `BaseService` — общий CRUD, автоматическая изоляция по `tenant_id`
3. **Dependency Injection** через FastAPI DI — `get_current_user`, `PermissionChecker`, `require_feature()`
4. **Soft delete** — `SoftDeleteMixin` на большинстве сущностей (`deleted_at`)
5. **Optimistic locking** — `VersionMixin` предотвращает конфликты параллельного редактирования
6. **Локализация через отдельные таблицы** — `*Locale` таблицы, не JSONB
7. **RFC 7807** — унифицированный формат ошибок с кодами

---

## 5. Мультитенантность

### Принцип работы

- **Изоляция на уровне строк**: у каждой модели есть `tenant_id` через `TenantMixin`
- **Резолвинг тенанта**:
  - Admin API → из JWT-токена (`token.tenant_id`)
  - Public API → query-параметр `tenant_id` или резолвинг по домену
  - Single-tenant mode → автоматически берёт единственного тенанта
- **Проверка при аутентификации**: проверяет `tenant.is_active` при каждом запросе
- **Переключение контекста**: `POST /auth/me/select-tenant` для платформного оператора

### Feature flags (8 флагов)

| Флаг | Описание |
|---|---|
| `blog_module` | Модуль блога (статьи, темы) |
| `cases_module` | Модуль кейсов |
| `reviews_module` | Модуль отзывов |
| `faq_module` | Модуль FAQ |
| `services_module` | Модуль услуг |
| `employees_module` | Модуль сотрудников |
| `documents_module` | Модуль документов |
| `catalog_module` | Модуль каталога (новый) |

---

## 6. Аутентификация и авторизация

### Auth-flow

```
POST /auth/login
  → валидация email/password
  → проверка tenant.is_active
  → выдача access_token (30 мин) + refresh_token (7 дней)
  → payload: {sub, tenant_id, email, role, permissions, is_superuser, jti}

POST /auth/refresh
  → проверка refresh_token (не в blacklist)
  → проверка tenant.is_active
  → новая пара токенов

POST /auth/logout
  → добавление jti в Redis blacklist
```

### RBAC

| Роль | Описание |
|---|---|
| `platform_owner` | Полный доступ, управление всеми тенантами |
| `site_owner` | Полный доступ внутри своего тенанта |
| `content_manager` | Управление контентом |
| `marketer` | Управление SEO и аналитикой |
| `editor` | Базовое редактирование |

- 28 permissions по паттерну `resource:action` (например `articles:create`)
- Поддержка wildcard: `articles:*`, `*`
- `PermissionChecker` — FastAPI dependency

---

## 7. Схема БД — сводка по сущностям

### Auth & Tenants (миграции 001–003)
- `Tenant`, `TenantSettings`, `TenantDomain`, `FeatureFlag`
- `AdminUser`, `Role`, `Permission`, `RolePermission`
- `AuditLog`

### Content & Company (миграции 004–016)
- `Article`, `ArticleLocale`, `Topic`, `TopicLocale`, `ArticleTopic`
- `FAQ`, `FAQLocale`, `Case`, `CaseLocale`, `Review`
- `Service`, `ServiceLocale`, `ServicePrice`, `ServiceTag`
- `Employee`, `EmployeeLocale`, `PracticeArea`, `PracticeAreaLocale`
- `Advantage`, `AdvantageLocale`, `Address`, `Contact`

### Остальные модули (миграции 006–027)
- `InquiryForm`, `Inquiry` — лиды
- `SEORoute`, `Redirect` — SEO
- `FileAsset` — S3-активы
- `Document`, `DocumentLocale` — документы
- `LocaleConfig` — локали

### Catalog & Parameters (миграции 028–032, NEW)
- `UOM` — единицы измерения
- `Category` — иерархические категории
- `Product`, `ProductImage`, `ProductChar`, `ProductAlias`, `ProductAnalog`, `ProductCategory`
- `ProductPrice` — временны́е, многотиповые цены (regular, sale, wholesale, cost)
- `Parameter`, `ParameterValue` — словарь параметров с типами (string, number, enum, bool, range)
- `ProductCharacteristic` — связь товаров и параметров

### Ключевые миксины (применяются повсеместно)

| Миксин | Добавляет |
|---|---|
| `TenantMixin` | `tenant_id` (FK → tenants) |
| `SoftDeleteMixin` | `deleted_at`, `is_deleted` |
| `VersionMixin` | `version` (optimistic locking) |
| `SEOMixin` | `meta_title`, `meta_description`, `og_image` |
| `TimestampMixin` | `created_at`, `updated_at` |

---

## 8. API — карта эндпоинтов

### Структура URL

```
/api/v1/auth/*          — аутентификация, пользователи, роли
/api/v1/tenants/*       — управление тенантами (platform_owner)
/api/v1/admin/*         — административные CRUD по модулям
/api/v1/public/*        — публичные эндпоинты для фронтенда
/internal/*             — внутренние (Caddy TLS arbiter)
/health                 — healthcheck
```

### Примерное распределение эндпоинтов

| Модуль | Admin | Public | Итого |
|---|---|---|---|
| Auth & Users | ~18 | 0 | ~18 |
| Tenants | ~15 | 0 | ~15 |
| Content (articles/cases/reviews/FAQ) | ~35 | ~6 | ~41 |
| Company (services/employees/etc.) | ~25 | ~10 | ~35 |
| Catalog (NEW) | ~20 | ~5 | ~25 |
| Parameters (NEW) | ~8 | 0 | ~8 |
| Leads | ~10 | 1 | ~11 |
| SEO | ~9 | ~3 | ~12 |
| Assets | 5 | 0 | 5 |
| Documents | ~9 | ~2 | ~11 |
| Audit / Dashboard | ~6 | 0 | ~6 |
| **Итого** | **~160** | **~27** | **~187** |

---

## 9. Инфраструктура и деплой

### Docker-compose (dev)

| Сервис | Порт | Описание |
|---|---|---|
| PostgreSQL 16-alpine | 5433→5432 | Основная БД |
| Redis 7-alpine | 6379 | Кэш + blacklist |
| MinIO | 9000 / 9001 | S3-совместимое хранилище |
| Backend (FastAPI) | 8000 | Hot-reload в dev |
| Migrations | — | `alembic upgrade head` при старте |

### Конфигурация (.env)

Ключевые переменные:
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `JWT_SECRET_KEY` — секрет для JWT
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` / `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- `CORS_ORIGINS` — статические разрешённые origins
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`
- Email: провайдер (console/sendgrid/mailgun), SMTP-настройки
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `SINGLE_TENANT_MODE` — булев флаг

---

## 10. Что сделано хорошо (сильные стороны)

1. **Чистая модульная архитектура** — DDD-подход, чёткие границы доменов
2. **Стабильный BaseService** — переиспользуемый CRUD, автоматическая мультитенантность
3. **Сильная типизация** — mypy strict mode, Pydantic v2
4. **RFC 7807 ошибки** — унифицированный формат, коды для перевода на фронте
5. **Soft delete везде** — сохраняет SEO, не ломает FK
6. **Локализация через таблицы** — не JSONB, нормальная реляционная модель
7. **Оптимистичная блокировка** — предотвращает race conditions на редактирование
8. **Аудит-лог** — покрывает ключевые операции (после рефакторинга)
9. **Динамический CORS** — origins из БД + статический fallback
10. **Redis blacklist** — надёжный logout
11. **Feature flags** — per-tenant управление модулями
12. **Полная документация** — OpenAPI + 13 markdown-документов в `/docs/development/`

---

## 11. Проблемные зоны (области для рефакторинга)

### 🔴 Высокий приоритет

#### 11.1 Гигантские service-файлы

| Файл | Строк | Проблема |
|---|---|---|
| `content/service.py` | 1 853 | Один файл на статьи + кейсы + отзывы + FAQ + топики |
| `company/service.py` | 1 276 | Один файл на все компанийные сущности |
| `auth/service.py` | 1 102 | Auth + пользователи + роли в одном файле |

**Риск**: сложно поддерживать, тестировать и онбордить новых разработчиков.  
**Решение**: разбить по sub-сервисам аналогично тому, как уже сделано в `company/routers/` (уже декомпозированы на `service_router.py`, `employee_router.py`, `other_router.py`).

#### 11.2 Покрытие тестами

Структура тестов есть (`pytest`, `pytest-asyncio`, `factory-boy`), но по анализу кода фактическое покрытие невысокое.

**Критически важно покрыть тестами**:
- Мультитенантную изоляцию (tenant A не видит данные tenant B)
- RBAC (permission checks)
- Feature flag guards
- Auth flow (login / refresh / logout / token blacklist)

**Цель**: 70–80% покрытия на критических путях.

#### 11.3 Отсутствие явных границ транзакций

Некоторые многошаговые операции (например, создание продукта с изображениями + характеристиками + ценами) выполняются без явного `BEGIN ... COMMIT`. При частичном сбое возможны "повисшие" данные.

**Решение**: ввести явные `async with session.begin()` блоки или транзакционные декораторы для сложных операций.

### 🟡 Средний приоритет

#### 11.4 Инвалидация кэша

Redis-кэш для доменов и статусов тенантов работает по TTL. При обновлении тенанта/домена кэш не инвалидируется немедленно.

**Решение**: явная инвалидация ключей кэша в сервисах при обновлении тенанта.

#### 11.5 N+1 запросы

`BaseService._get_default_options()` задаёт стратегию eager loading, но не все сервисы переопределяют его корректно. В catalog-модуле (новый) это ещё не проверено в нагрузочных условиях.

**Решение**: аудит всех `selectinload`/`joinedload` в сервисах, особенно для списковых эндпоинтов.

#### 11.6 Структура нового каталога (catalog + parameters)

Новые модули (`catalog/`, `parameters/`) написаны в uncommitted-состоянии и ещё не прошли review. Их архитектура соответствует паттернам проекта, но нужно:
- Проверить корректность миграций (028–032) перед мержем
- Убедиться что feature flag `catalog_module` применён ко всем роутам
- Проверить публичные эндпоинты на tenant isolation
- Протестировать temporal pricing логику (`ProductPrice`)

#### 11.7 Дублирование маппинг-логики

Файлы `content/mappers.py` (442 строки) и `company/mappers.py` (366 строк) содержат ручную логику маппинга между ORM-объектами и схемами Pydantic. Часть этого можно унифицировать или заменить на Pydantic `model_validate`.

### 🟢 Низкий приоритет

#### 11.8 Строки ошибок в коде

Часть error message-ов захардкожена на русском/английском. Уже есть error codes для перевода на фронте — нужно завершить унификацию.

#### 11.9 Архитектурная документация

Есть подробная документация API и интеграционные гайды, но нет:
- Диаграммы архитектуры (C4 или ERD)
- Описания базовых миксинов и паттернов для онбординга
- ADR (Architecture Decision Records)

---

## 12. Текущее состояние (что в работе)

### Незакоммиченные изменения (ветка `feat/product-catalog`)

| Файл / Папка | Статус | Описание |
|---|---|---|
| `backend/app/modules/catalog/` | NEW (untracked) | Модуль каталога: models, schemas, service, router |
| `backend/app/modules/parameters/` | NEW (untracked) | Модуль параметров: models, schemas, service, router |
| `backend/alembic/versions/028–032` | NEW (untracked) | 5 новых миграций для каталога и параметров |
| `backend/app/main.py` | Modified | Регистрация новых роутеров |
| `backend/alembic/env.py` | Modified | Импорт новых моделей |
| `backend/app/middleware/feature_check.py` | Modified | Добавлен `require_catalog` |
| `backend/app/modules/auth/models.py` | Modified | Добавлены catalog permissions |

### Ранее завершённые фазы (из плана рефакторинга)

Все фазы плана `multi-tenant_saas_backend_plan` выполнены:
- ✅ Фаза 1: Принудительная проверка `tenant.is_active`
- ✅ Фаза 2: `require_feature()` guards на 88+ admin-маршрутах
- ✅ Фаза 3: Cross-tenant управление пользователями для `platform_owner`
- ✅ Фаза 4: Welcome email при создании пользователя
- ✅ Фаза 5: Feature catalog endpoint (`/me/features`)
- ✅ Фаза 6: Расширение аудит-лога (user CRUD, изменения тенанта, роли)
- ✅ Фаза 7: Мелкие улучшения (password reset, rate limiting)

---

## 13. Профиль разработчика для рефакторинга

### Обязательные навыки

| Навык | Уровень | Зачем нужно |
|---|---|---|
| Python 3.11+ | Senior | Весь кодбейс |
| FastAPI | Senior | Архитектура роутеров, DI, middleware |
| SQLAlchemy 2.x async | Senior | Сложные запросы, eager loading, транзакции |
| Pydantic v2 | Middle+ | Схемы, валидация, маппинг |
| Alembic | Middle | Написание и проверка миграций |
| PostgreSQL | Middle+ | Понимание индексов, constraints, partial indexes |
| Redis | Middle | Blacklist, кэш, TTL, инвалидация |
| Docker / docker-compose | Middle | Локальная разработка и деплой |
| Async Python (asyncio) | Senior | Весь стек асинхронный |

### Желательные навыки

| Навык | Зачем нужно |
|---|---|
| DDD / Clean Architecture | Понимание текущих паттернов |
| Pytest + pytest-asyncio | Написание тестов |
| mypy strict mode | Поддержание типизации |
| S3 / MinIO | Работа с assets-модулем |
| Multi-tenancy patterns | Ключевая часть архитектуры |
| JWT / RBAC | Auth-модуль |
| ruff / pre-commit | CI/CD code quality |

### Что НЕ требуется

- GraphQL — нет в проекте
- Celery — используется taskiq
- Django ORM — только SQLAlchemy
- Синхронный Python — всё асинхронно

---

## 14. Рекомендуемые приоритеты для плана рефакторинга

### Sprint 1 — Каталог (текущая задача)
1. Code review модулей `catalog/` и `parameters/`
2. Тест-запуск миграций 028–032 на чистой БД
3. Написание smoke-тестов для catalog API
4. Мерж в main после approve

### Sprint 2 — Декомпозиция больших сервисов
1. Разбить `content/service.py` на `article_service.py`, `case_service.py`, `review_service.py`, `faq_service.py`
2. Разбить `company/service.py` по доменам
3. Разбить `auth/service.py` на `user_service.py`, `role_service.py`, `session_service.py`
4. Убедиться, что все импорты обновлены

### Sprint 3 — Тесты
1. Тесты tenant isolation (критично!)
2. Тесты RBAC и permission checks
3. Тесты auth flow
4. Тесты feature flags
5. Настроить CI с минимальным coverage gate (70%)

### Sprint 4 — Качество
1. Ввести явные транзакционные границы для сложных операций
2. Аудит N+1 запросов в listing endpoints
3. Инвалидация Redis-кэша при изменении тенанта/домена
4. Унификация error messages

### Sprint 5 — Документация
1. ERD-диаграмма БД (хотя бы для core + catalog)
2. ADR для ключевых архитектурных решений
3. Онбординг-гид для нового разработчика

---

## 15. Вопросы, которые стоит задать разработчику на аудит

1. Как бы вы декомпозировали `content/service.py` в 1853 строки — на уровне классов или модулей?
2. Как бы вы выстроили стратегию покрытия тестами в async SQLAlchemy + FastAPI стеке?
3. Какой подход к инвалидации Redis-кэша вы бы применили для tenant-статусов?
4. Есть ли у вас опыт с multi-tenant row-level isolation в PostgreSQL и SQLAlchemy?
5. Как бы вы подошли к аудиту N+1 запросов в asyncpg?
6. Приходилось ли работать с Alembic на live БД с данными? Как вы организуете zero-downtime миграции?
7. Знакомы ли вы с Pydantic v2 и его изменениями по сравнению с v1?

---

*Документ составлен автоматически на основе анализа кодовой базы. Обновлять по мере изменений проекта.*
