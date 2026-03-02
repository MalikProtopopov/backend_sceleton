# Система доступов, лимитов и ролей — документация для фронта админки

## 1. Три уровня ограничений

Каждый API-запрос проходит проверки в следующем порядке:

```
Авторизация → Биллинг (модули) → Лимиты → RBAC (права роли)
```

### Уровень 1: Биллинг (тариф / модули)

- **Что проверяет:** включён ли модуль в тарифе тенанта (например, каталог, SEO, документы).
- **HTTP-ответ при отказе:** `403`, `error_code: "feature_disabled"`, `restriction_level: "organization"`.
- **Поле в sidebar:** `accessible: false`, `reason: "billing"`.
- **Действие на фронте:** замочек + «Недоступно в вашем тарифе. Обновите план.» + кнопка на `/billing/plans`.

### Уровень 2: Лимиты (количественные ограничения плана)

- **Что проверяет:** не превышен ли числовой лимит (товары, статьи, пользователи и т.д.).
- **HTTP-ответ при отказе:** `403`, `error_code: "limit_exceeded"`, `restriction_level: "organization"`.
- **Поле в sidebar:** `limit_info.status: "exceeded"` или `"not_available"`.
- **Действие на фронте:** «Лимит исчерпан: 100 из 100 статей» + кнопка на `/billing`.

### Уровень 3: RBAC (права роли пользователя)

- **Что проверяет:** есть ли у роли пользователя нужное право (например, `articles:create`).
- **HTTP-ответ при отказе:** `403`, `error_code: "permission_denied"`, `restriction_level: "user"`.
- **Поле в sidebar:** `accessible: false`, `reason: "role"`.
- **Действие на фронте:** «Нет доступа. Обратитесь к администратору.»

### Ключевой принцип: `restriction_level`

| Значение | Кто решает | Что делать на фронте |
|----------|------------|----------------------|
| `"organization"` | Тариф / биллинг | Показать ссылку на биллинг, предложить апгрейд |
| `"user"` | Роль пользователя | Показать «обратитесь к администратору» |

---

## 2. API-справочник

### 2.1 GET /api/v1/auth/me/sidebar

**Назначение:** получить полный список разделов сайдбара с информацией о доступности.

**Query-параметры:**

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `locale` | string | `"ru"` | Локаль для `title` (`"ru"` или `"en"`) |

**Ответ:**

```json
{
  "tenant_id": "uuid",
  "role": "site_owner",
  "all_access": false,
  "sections": [
    {
      "name": "blog_module",
      "title": "Блог / Статьи",
      "category": "content",
      "path": "/articles",
      "icon": "file-text",
      "visible": true,
      "accessible": true,
      "reason": null,
      "required_permission": null,
      "limit_info": {
        "resource": "max_articles",
        "current": 42,
        "limit": 100,
        "status": "ok"
      }
    },
    {
      "name": "catalog_module",
      "title": "Каталог товаров",
      "category": "commerce",
      "path": "/catalog/products",
      "icon": "shopping-bag",
      "visible": true,
      "accessible": false,
      "reason": "billing",
      "required_permission": null,
      "limit_info": {
        "resource": "max_products",
        "current": 0,
        "limit": 0,
        "status": "not_available"
      }
    }
  ]
}
```

**Поля `SidebarItemAccess`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Ключ секции (`blog_module`, `_dashboard`, `_billing` и т.д.) |
| `title` | string | Заголовок (учитывает `locale`) |
| `category` | string | Группа: `core`, `content`, `company`, `commerce`, `crm`, `platform`, `admin`, `billing`, `platform_admin` |
| `path` | string | Путь страницы во фронте (использовать как есть для роутера) |
| `icon` | string | Имя иконки |
| `visible` | boolean | Показывать ли пункт (всегда `true`; скрытые секции не попадают в ответ) |
| `accessible` | boolean | Доступен ли раздел (биллинг + RBAC) |
| `reason` | string / null | Причина блокировки: `"billing"`, `"role"`, `"billing+role"`, или `null` |
| `required_permission` | string / null | Код права, которого не хватает (при `reason` = `"role"` или `"billing+role"`) |
| `limit_info` | object / null | Информация о лимите ресурса (см. ниже) |

**Поля `limit_info`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `resource` | string | Ключ лимита: `max_products`, `max_articles`, `max_users` |
| `current` | integer | Текущее использование |
| `limit` | integer / null | Лимит по плану (`null` = безлимитно) |
| `status` | string | `"ok"`, `"warning"`, `"exceeded"`, `"not_available"` |

**Значения `status` в `limit_info`:**

| Статус | Описание | Действие на фронте |
|--------|----------|---------------------|
| `ok` | Лимит не превышен | Показать счётчик «42 из 100» |
| `warning` | Использовано >= 80% лимита | Жёлтая плашка «Осталось мало» |
| `exceeded` | Лимит достигнут | Красная плашка, скрыть кнопку «Добавить» |
| `not_available` | Лимит = 0 (не входит в тариф) | «Недоступно в текущем тарифе» |

---

### 2.2 GET /api/v1/auth/me/features

**Назначение:** список всех фич с их статусом (включена/выключена).

**Ответ:**

```json
{
  "features": [
    {
      "name": "blog_module",
      "title": "Блог / Статьи",
      "description": "Создание и управление статьями",
      "category": "content",
      "enabled": true,
      "can_request": false
    }
  ],
  "all_features_enabled": false,
  "tenant_id": "uuid"
}
```

---

### 2.3 GET /api/v1/admin/my-plan

**Назначение:** текущий план тенанта с модулями и полным отчётом по использованию.

**Ответ (основные поля):**

```json
{
  "plan": {
    "id": "uuid",
    "slug": "starter",
    "name": "Стартовый",
    "limits": { "max_products": 0, "max_articles": 100 }
  },
  "modules": [ { "slug": "core", "name": "Базовый" } ],
  "usage": {
    "max_products": { "current": 0, "limit": 0, "status": "not_available" },
    "max_articles": { "current": 42, "limit": 100, "status": "ok" },
    "max_users":    { "current": 1, "limit": 2, "status": "ok" }
  }
}
```

---

### 2.4 GET /api/v1/admin/my-limits

**Назначение:** подробный отчёт по лимитам и использованию.

**Ответ:**

```json
{
  "max_users":          { "current": 1,  "limit": 2,    "status": "ok" },
  "max_storage_mb":     { "current": 120,"limit": 5120, "status": "ok" },
  "max_leads_per_month":{ "current": 23, "limit": 500,  "status": "ok" },
  "max_products":       { "current": 0,  "limit": 0,    "status": "not_available" },
  "max_variants":       { "current": 0,  "limit": 0,    "status": "not_available" },
  "max_domains":        { "current": 1,  "limit": 1,    "status": "exceeded" },
  "max_articles":       { "current": 95, "limit": 100,  "status": "warning" },
  "max_rbac_roles":     { "current": 3,  "limit": 2,    "status": "exceeded" }
}
```

---

### 2.5 GET /api/v1/auth/me

**Назначение:** данные текущего пользователя, включая роль и права.

Используйте `role.permissions` для проактивного скрытия кнопок/действий, к которым у пользователя нет прав.

---

## 3. Матрица «тариф → что доступно»

### Модули по тарифам

| Модуль | Starter | Business | Commerce | Enterprise | Agency |
|--------|---------|----------|----------|------------|--------|
| core (auth, media, dashboard) | + | + | + | + | + |
| content (блог, кейсы, отзывы, FAQ) | + | + | + | + | + |
| company (услуги, команда) | + | + | + | + | + |
| crm_basic (заявки) | + | + | + | + | + |
| crm_pro (аналитика, экспорт) | — | + | + | + | + |
| seo_advanced (редиректы, IndexNow) | — | + | + | + | + |
| multilang (мультиязычность) | — | + | + | + | + |
| documents (документы) | — | + | + | + | + |
| catalog_basic (каталог товаров) | — | — | + | + | + |
| catalog_pro (вариации, параметры) | — | — | + | + | + |

### Лимиты по тарифам

| Лимит | Starter | Business | Commerce | Enterprise | Agency |
|-------|---------|----------|----------|------------|--------|
| max_users | 2 | 5 | 10 | ∞ | 3 |
| max_storage_mb | 5 120 | 20 480 | 51 200 | ∞ | 10 240 |
| max_leads_per_month | 500 | 2 000 | 5 000 | ∞ | 1 000 |
| max_products | 0 | 0 | 5 000 | ∞ | 500 |
| max_variants | 0 | 0 | 10 000 | ∞ | 1 000 |
| max_domains | 1 | 3 | 5 | ∞ | 2 |
| max_articles | 100 | 500 | ∞ | ∞ | 200 |
| max_rbac_roles | 2 | 5 | 10 | ∞ | 3 |

**Условные обозначения:** `0` = недоступно в тарифе (`status: "not_available"`); `∞` = без ограничений (`limit: null`).

---

## 4. Матрица «роль → что может»

| Право | platform_owner | site_owner | content_manager | marketer | editor |
|-------|:-:|:-:|:-:|:-:|:-:|
| articles:* | + | + | + | — | create/read/update |
| services:* | + | + | read/update | — | — |
| employees:* | + | + | read | — | — |
| catalog:* | + | + | + | — | read |
| cases:* | + | + | — | + | — |
| reviews:* | + | + | — | + | — |
| faq:* | + | + | + | — | create/read/update |
| documents:* | + | + | read/create/update | read | read/create/update |
| inquiries:* | + | + | — | read | — |
| seo:* | + | + | — | + | — |
| settings:* | + | + | — | — | — |
| users:* | + | + | — | — | — |
| users:manage | + | + | — | — | — |
| export:read | + | + | — | + | — |
| content:bulk | + | + | + | — | — |
| audit:read | + | + | — | — | — |
| dashboard:read | + | + | + | + | + |
| platform:* | + | — | — | — | — |
| features:* | + | — | — | — | — |

---

## 5. Как строить сайдбар

### Алгоритм

```
1. Запросить GET /auth/me/sidebar?locale=ru
2. При ошибке или пустом sections → показать fallback (статичную навигацию)
3. Для каждой секции:
   a. Если accessible === true → обычный пункт, переход по path
   b. Если accessible === false:
      - reason === "billing" → замочек + тултип «Недоступно в тарифе»
      - reason === "role" → замочек + тултип «Нет прав»
      - reason === "billing+role" → замочек + тултип «Недоступно»
   c. Если limit_info !== null:
      - status === "not_available" → бейдж «Недоступно»
      - status === "warning" → жёлтый бейдж «Осталось мало»
      - status === "exceeded" → красный бейдж «Лимит»
      - status === "ok" и limit !== null → серый бейдж «42 / 100»
      - limit === null → не показывать счётчик (безлимит)
4. Группировать по category
```

### Fallback при ошибке API

Если `GET /auth/me/sidebar` вернул ошибку или пустой `sections`, показывать статичную навигацию:

- **Главное:** Дашборд (`/`)
- **Контент:** Статьи (`/articles`), Кейсы (`/cases`), Услуги (`/services`), Медиатека (`/media`), Заявки (`/leads`), О компании (`/company`)
- **Биллинг:** Мой тариф (`/billing`), Каталог тарифов (`/billing/plans`)

---

## 6. Как обрабатывать 403

### Формат ответа (RFC 7807)

```json
{
  "type": "https://api.example.com/errors/feature_disabled",
  "title": "Feature Disabled",
  "status": 403,
  "detail": "...",
  "instance": "/api/v1/admin/products",
  "error_code": "feature_disabled",
  "restriction_level": "organization",
  "feature": "catalog_module"
}
```

### Таблица error_code → действие

| error_code | restriction_level | Что показывать | Кнопка |
|------------|-------------------|----------------|--------|
| `feature_disabled` | organization | «Раздел недоступен в вашем тарифе» | «Обновить тариф» → `/billing/plans` |
| `limit_exceeded` | organization | «Лимит исчерпан: {current} из {limit}» | «Обновить тариф» → `/billing` |
| `permission_denied` | user | «Нет доступа к этому действию» | «Обратитесь к администратору» |
| `insufficient_role` | user | «Недостаточно прав» | «Обратитесь к администратору» |
| `tenant_inactive` | organization | «Организация деактивирована» | «Обратитесь в поддержку» |

### Пример обработки (Axios interceptor)

```typescript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) return Promise.reject(error)

    const { status, data } = error.response
    const errorCode = data?.type?.split('/').pop() || ''

    if (status === 401) {
      // Токен истёк или невалидный → редирект на логин
      authStore.logout()
      router.push('/login')
    }

    if (status === 403) {
      switch (errorCode) {
        case 'feature_disabled':
          showModal({
            type: 'billing',
            title: 'Раздел недоступен',
            message: `Функция «${FEATURE_NAMES[data.feature] || data.feature}» недоступна в вашем тарифе.`,
            action: { label: 'Обновить тариф', to: '/billing/plans' },
          })
          break

        case 'limit_exceeded':
          showModal({
            type: 'billing',
            title: 'Лимит исчерпан',
            message: `${RESOURCE_NAMES[data.resource] || data.resource}: ${data.current_usage ?? '?'} из ${data.limit ?? '?'}`,
            action: { label: 'Обновить тариф', to: '/billing' },
          })
          break

        case 'permission_denied':
          showModal({
            type: 'permission',
            title: 'Нет доступа',
            message: 'У вас недостаточно прав для этого действия. Обратитесь к администратору.',
          })
          break
      }
    }

    if (status === 429) {
      const retryAfter = data?.retry_after || 60
      showToast(`Слишком много запросов. Повторите через ${retryAfter} сек.`)
    }

    return Promise.reject(error)
  }
)
```

---

## 7. Лимиты — как показывать на страницах

### Проактивная проверка

При входе на страницу раздела (каталог, статьи, пользователи) запросить `GET /admin/my-limits` и показать плашку:

| Статус | Вид | Текст |
|--------|-----|-------|
| `ok` | Серый бейдж | «Товаров: 42 из 500» |
| `warning` | Жёлтая плашка | «Осталось мало: 450 из 500 товаров» |
| `exceeded` | Красная плашка | «Лимит исчерпан: 500 из 500. Обновите тариф.» + скрыть кнопку «Добавить» |
| `not_available` | Серая плашка | «Товары недоступны в вашем тарифе. Обновите план.» + скрыть весь CRUD |
| `limit: null` | Не показывать | Безлимитный тариф |

### Маппинг ресурсов на русский

```typescript
const RESOURCE_NAMES: Record<string, string> = {
  max_users: 'Пользователей',
  max_storage_mb: 'Хранилище (МБ)',
  max_leads_per_month: 'Заявок в месяц',
  max_products: 'Товаров',
  max_variants: 'Вариаций товаров',
  max_domains: 'Доменов',
  max_articles: 'Статей',
  max_rbac_roles: 'Ролей',
}
```

### Маппинг фич на русский

```typescript
const FEATURE_NAMES: Record<string, string> = {
  blog_module: 'Блог / Статьи',
  cases_module: 'Кейсы / Портфолио',
  reviews_module: 'Отзывы',
  faq_module: 'Вопросы и ответы',
  team_module: 'Команда / Сотрудники',
  services_module: 'Услуги',
  seo_advanced: 'Расширенное SEO',
  multilang: 'Мультиязычность',
  analytics_advanced: 'Расширенная аналитика',
  catalog_module: 'Каталог товаров',
  variants_module: 'Вариации товаров',
  documents: 'Документы',
  company: 'О компании',
  crm_basic: 'CRM',
}
```

---

## 8. TypeScript-типы

```typescript
// ── Sidebar ──

interface SidebarLimitInfo {
  resource: string
  current: number
  limit: number | null
  status: 'ok' | 'warning' | 'exceeded' | 'not_available'
}

interface SidebarSection {
  name: string
  title: string
  category: string
  path: string
  icon: string
  visible: boolean
  accessible: boolean
  reason: 'billing' | 'role' | 'billing+role' | null
  required_permission: string | null
  limit_info: SidebarLimitInfo | null
}

interface SidebarResponse {
  tenant_id: string
  role: string | null
  all_access: boolean
  sections: SidebarSection[]
}

// ── Limits / Usage ──

interface UsageInfo {
  current: number
  limit: number | null
  status: 'ok' | 'warning' | 'exceeded' | 'not_available'
}

type UsageReport = Record<string, UsageInfo>

// ── Features ──

interface FeatureItem {
  name: string
  title: string
  description: string
  category: string
  enabled: boolean
  can_request: boolean
}

interface FeaturesResponse {
  features: FeatureItem[]
  all_features_enabled: boolean
  tenant_id: string
}

// ── Errors ──

type ErrorCode =
  | 'feature_disabled'
  | 'limit_exceeded'
  | 'permission_denied'
  | 'insufficient_role'
  | 'tenant_inactive'
  | 'rate_limit_exceeded'

interface ApiError {
  type: string
  title: string
  status: number
  detail: string
  instance: string
  // 403 fields
  error_code?: ErrorCode
  restriction_level?: 'user' | 'organization'
  feature?: string
  resource?: string
  current_usage?: number
  limit?: number
  required_permission?: string
  // 429
  retry_after?: number
}
```

---

## 9. Список всех разделов сайдбара

| name | path | category | Биллинг (feature) | RBAC (perm) | Лимит |
|------|------|----------|--------------------|-------------|-------|
| `_dashboard` | `/` | core | — | dashboard:read | — |
| `_media` | `/media` | core | — | settings:read | — |
| `blog_module` | `/articles` | content | blog_module | articles:read | max_articles |
| `cases_module` | `/cases` | content | cases_module | cases:read | — |
| `faq_module` | `/faq` | content | faq_module | faq:read | — |
| `_documents` | `/documents` | content | documents | documents:read | — |
| `services_module` | `/services` | company | services_module | services:read | — |
| `team_module` | `/team` | company | team_module | employees:read | — |
| `reviews_module` | `/reviews` | company | reviews_module | reviews:read | — |
| `_company` | `/company` | company | company | services:read | — |
| `catalog_module` | `/catalog/products` | commerce | catalog_module | catalog:read | max_products |
| `_leads` | `/leads` | crm | crm_basic | inquiries:read | — |
| `seo_advanced` | `/seo/paths` | platform | seo_advanced | seo:read | — |
| `_users` | `/users` | admin | — | users:read | max_users |
| `_audit` | `/audit` | admin | — | audit:read | — |
| `_settings` | `/settings` | admin | — | settings:read | — |
| `_billing` | `/billing` | billing | — | dashboard:read | — |
| `_platform_dashboard` | `/platform` | platform_admin | — | platform:read | superuser only |
| `_tenants` | `/tenants` | platform_admin | — | platform:read | superuser only |
| `_platform_plans` | `/platform/plans` | platform_admin | — | platform:read | superuser only |
| `_platform_modules` | `/platform/modules` | platform_admin | — | platform:read | superuser only |
| `_platform_bundles` | `/platform/bundles` | platform_admin | — | platform:read | superuser only |
| `_platform_requests` | `/platform/requests` | platform_admin | — | platform:read | superuser only |

---

## 10. Чек-лист для фронта

- [ ] Запрашивать `GET /auth/me/sidebar` при загрузке и строить сайдбар по ответу
- [ ] Реализовать fallback при ошибке / пустом `sections`
- [ ] Показывать замочек для `accessible: false` с тултипом по `reason`
- [ ] Показывать `limit_info` (бейдж/плашка) для секций с лимитами
- [ ] Реализовать глобальный interceptor для 401 / 403 / 429
- [ ] При `feature_disabled` → модалка «Обновите тариф»
- [ ] При `limit_exceeded` → модалка «Лимит исчерпан» с числами
- [ ] При `permission_denied` → модалка «Нет доступа»
- [ ] На страницах каталога и статей проактивно запрашивать `GET /admin/my-limits`
- [ ] При `status: "not_available"` скрывать кнопки создания и показывать плашку
- [ ] При `status: "exceeded"` скрывать кнопку «Добавить» и показывать красную плашку
- [ ] При `limit: null` не показывать счётчик (безлимит)
