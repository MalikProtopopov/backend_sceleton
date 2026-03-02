# Биллинг — API для админ-панели

> Тарифные планы, модули, лимиты, заявки на апгрейд

---

## Содержание

1. [Общее](#1-общее)
2. [Страница «Мой тариф»](#2-страница-мой-тариф)
3. [Страница «Мои модули»](#3-страница-мои-модули)
4. [Страница «Лимиты»](#4-страница-лимиты)
5. [Каталог тарифов (для пользователя)](#5-каталог-тарифов)
6. [Заявки на апгрейд](#6-заявки-на-апгрейд)
7. [Обработка ошибок лимитов](#7-обработка-ошибок-лимитов)
8. [Платформа: управление планами](#8-платформа-управление-планами)
9. [Платформа: управление модулями](#9-платформа-управление-модулями)
10. [Платформа: управление бандлами](#10-платформа-управление-бандлами)
11. [Платформа: заявки на апгрейд](#11-платформа-заявки-на-апгрейд)
12. [Платформа: модули тенанта](#12-платформа-модули-тенанта)
13. [Словарь полей (RU)](#13-словарь-полей)
14. [Screen-to-API Mapping](#14-screen-to-api-mapping)

---

## 1. Общее

### Base URL

```
Production: https://api.yoursite.com/api/v1
Development: http://localhost:8000/api/v1
```

### Авторизация

Все `/admin/*` эндпоинты требуют `Authorization: Bearer {access_token}`.

### Кто что видит

| Роль | Доступ |
|------|--------|
| **Любой авторизованный** (site_owner, content_manager, editor) | «Мой тариф», «Мои модули», «Лимиты», каталог тарифов, создание заявок |
| **platform_owner / superuser** | Всё выше + управление планами, модулями, бандлами, обработка заявок, управление модулями тенантов |

### Цены

Все цены приходят в **копейках** (целое число). Для отображения:

```typescript
function formatPrice(kopecks: number): string {
  return (kopecks / 100).toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
  })
}
// 199000 → "1 990 ₽"
// 499000 → "4 990 ₽"
```

### Лимиты: значения `-1` и `0`

- `-1` = **безлимитно** → отображать как «∞» или «Без ограничений»
- `0` = **недоступно** → отображать как «—» или «Не включено в план»
- Положительное число = конкретный лимит

---

## 2. Страница «Мой тариф»

**Экран:** `/admin/billing` или `/admin/my-plan`

### GET /api/v1/admin/my-plan

Возвращает текущий план, активные модули и использование ресурсов.

**Headers:** `Authorization: Bearer {token}`

**Ответ (200):**

```json
{
  "plan": {
    "id": "uuid",
    "slug": "business",
    "name": "Business",
    "name_ru": "Бизнес",
    "description_ru": "Для растущего бизнеса с SEO и аналитикой",
    "price_monthly_kopecks": 499000,
    "price_yearly_kopecks": 479000,
    "setup_fee_kopecks": 1999000,
    "is_default": false,
    "is_active": true,
    "sort_order": 1,
    "limits": {
      "max_users": 5,
      "max_storage_mb": 20480,
      "max_leads_per_month": 2000,
      "max_products": 0,
      "max_variants": 0,
      "max_domains": 3,
      "max_articles": 500,
      "max_rbac_roles": 5
    },
    "modules": [
      { "id": "uuid", "slug": "core", "name": "Core", "name_ru": "Базовый", "category": "platform", "is_base": true },
      { "id": "uuid", "slug": "content", "name": "Content", "name_ru": "Контент", "category": "content", "is_base": false },
      { "id": "uuid", "slug": "crm_pro", "name": "CRM Pro", "name_ru": "CRM Про", "category": "crm", "is_base": false }
    ]
  },
  "modules": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "module_id": "uuid",
      "module_slug": "content",
      "module_name": "Content",
      "module_name_ru": "Контент",
      "source": "plan",
      "enabled": true,
      "activated_at": "2026-03-01T10:00:00Z",
      "expires_at": null
    },
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "module_id": "uuid",
      "module_slug": "seo_advanced",
      "module_name": "SEO Advanced",
      "module_name_ru": "SEO Расширенный",
      "source": "addon",
      "enabled": true,
      "activated_at": "2026-03-05T12:00:00Z",
      "expires_at": null
    }
  ],
  "usage": {
    "max_users": { "current": 3, "limit": 5, "status": "ok" },
    "max_storage_mb": { "current": 1200, "limit": 20480, "status": "ok" },
    "max_leads_per_month": { "current": 1800, "limit": 2000, "status": "warning" },
    "max_products": { "current": 0, "limit": 0, "status": "ok" },
    "max_articles": { "current": 45, "limit": 500, "status": "ok" },
    "max_domains": { "current": 1, "limit": 3, "status": "ok" }
  }
}
```

### UX-рекомендации для страницы «Мой тариф»

**Карточка плана** (верхняя часть):

| Элемент UI | Поле из API | Пример |
|------------|-------------|--------|
| Заголовок | `plan.name_ru` | «Бизнес» |
| Описание | `plan.description_ru` | «Для растущего бизнеса с SEO и аналитикой» |
| Цена в месяц | `plan.price_monthly_kopecks / 100` | «4 990 ₽/мес» |
| Цена в год | `plan.price_yearly_kopecks / 100` | «47 900 ₽/год» |
| Кнопка | — | «Сменить тариф» → открывает каталог тарифов |

**Блок «Использование ресурсов»** (прогресс-бары):

| Метка (RU) | Ключ в `usage` | Формат значения |
|------------|----------------|-----------------|
| Пользователи | `max_users` | `3 из 5` |
| Хранилище | `max_storage_mb` | `1.2 ГБ из 20 ГБ` |
| Заявки в месяц | `max_leads_per_month` | `1 800 из 2 000` |
| Товары | `max_products` | `0 из 0` или «Не включено» |
| Статьи | `max_articles` | `45 из 500` |
| Домены | `max_domains` | `1 из 3` |

**Цвета прогресс-баров по `status`:**

| status | Цвет | Описание |
|--------|------|----------|
| `ok` | Зелёный / нейтральный | Всё в порядке |
| `warning` | Оранжевый / жёлтый | Использовано 80%+ — показать предупреждение |
| `exceeded` | Красный | Лимит исчерпан — показать блокирующий баннер |

**Блок «Активные модули»** (список):

Для каждого модуля из `modules`:

| Элемент UI | Поле | Пример |
|------------|------|--------|
| Название | `module_name_ru` | «Контент» |
| Источник | `source` | Бейдж: «Из плана» / «Допокупка» / «Бандл» / «Вручную» |
| Статус | `enabled` | Зелёная / серая точка |
| Дата активации | `activated_at` | «1 марта 2026» |

Маппинг `source` для отображения:

```typescript
const sourceLabels: Record<string, string> = {
  plan: 'Из тарифа',
  addon: 'Допокупка',
  bundle: 'Из пакета',
  manual: 'Вручную',
}
```

---

## 3. Страница «Мои модули»

**Экран:** `/admin/my-modules`

### GET /api/v1/admin/my-modules

**Ответ (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "module_id": "uuid",
      "module_slug": "content",
      "module_name": "Content",
      "module_name_ru": "Контент",
      "source": "plan",
      "enabled": true,
      "activated_at": "2026-03-01T10:00:00Z",
      "expires_at": null
    }
  ]
}
```

### UX

Таблица или карточки модулей. Колонки:

| Колонка (RU) | Поле |
|--------------|------|
| Модуль | `module_name_ru` |
| Категория | по `module_slug` → маппинг ниже |
| Источник | `source` → маппинг выше |
| Активен | `enabled` |
| Дата подключения | `activated_at` |
| Действует до | `expires_at` (если null → «Бессрочно») |

Маппинг категорий для фронта:

```typescript
const categoryLabels: Record<string, string> = {
  platform: 'Платформа',
  content: 'Контент',
  company: 'Компания',
  crm: 'CRM',
  commerce: 'Коммерция',
}
```

---

## 4. Страница «Лимиты»

**Экран:** `/admin/my-limits` (или вкладка на странице «Мой тариф»)

### GET /api/v1/admin/my-limits

**Ответ (200):**

```json
{
  "max_users": { "current": 3, "limit": 5, "status": "ok" },
  "max_storage_mb": { "current": 1200, "limit": 20480, "status": "ok" },
  "max_leads_per_month": { "current": 1800, "limit": 2000, "status": "warning" },
  "max_products": { "current": 0, "limit": 0, "status": "ok" },
  "max_variants": { "current": 0, "limit": 0, "status": "ok" },
  "max_articles": { "current": 45, "limit": 500, "status": "ok" },
  "max_domains": { "current": 1, "limit": 3, "status": "ok" }
}
```

Маппинг ключей на русский:

```typescript
const limitLabels: Record<string, { label: string; unit: string }> = {
  max_users:           { label: 'Пользователи',    unit: '' },
  max_storage_mb:      { label: 'Хранилище',       unit: 'МБ' },
  max_leads_per_month: { label: 'Заявки в месяц',  unit: '' },
  max_products:        { label: 'Товары',           unit: '' },
  max_variants:        { label: 'Вариации товаров', unit: '' },
  max_domains:         { label: 'Домены',           unit: '' },
  max_articles:        { label: 'Статьи',           unit: '' },
  max_rbac_roles:      { label: 'Роли',             unit: '' },
}
```

---

## 5. Каталог тарифов

**Экран:** `/admin/plans` или модальное окно из «Мой тариф»

Для отображения каталога тарифов используются **публичные** эндпоинты (не требуют авторизации):

### GET /api/v1/public/plans

Список всех активных планов. Отсортирован по `sort_order`.

**Ответ:** массив `PlanResponse` (см. пример выше в разделе 2).

### GET /api/v1/public/modules

Список всех модулей с ценами. Для отображения «что можно докупить».

**Ответ (200):**

```json
[
  {
    "id": "uuid",
    "slug": "core",
    "name": "Core",
    "name_ru": "Базовый",
    "description": "Auth, RBAC, SSL, media...",
    "description_ru": "Авторизация, RBAC, SSL, медиа...",
    "category": "platform",
    "price_monthly_kopecks": 0,
    "is_base": true,
    "sort_order": 0
  },
  {
    "id": "uuid",
    "slug": "seo_advanced",
    "name": "SEO Advanced",
    "name_ru": "SEO Расширенный",
    "description_ru": "Редиректы, IndexNow, llms.txt, OG-метатеги...",
    "category": "platform",
    "price_monthly_kopecks": 149000,
    "is_base": false,
    "sort_order": 5
  }
]
```

### GET /api/v1/public/bundles

Список тематических пакетов.

**Ответ (200):**

```json
[
  {
    "id": "uuid",
    "slug": "seo_pack",
    "name": "SEO Pack",
    "name_ru": "SEO-пакет",
    "description_ru": "SEO Расширенный + Мультиязычность",
    "price_monthly_kopecks": 199000,
    "discount_percent": 33,
    "is_active": true,
    "sort_order": 0,
    "modules": [
      { "id": "uuid", "slug": "seo_advanced", "name": "SEO Advanced", "name_ru": "SEO Расширенный" },
      { "id": "uuid", "slug": "multilang", "name": "Multilang", "name_ru": "Мультиязычность" }
    ]
  }
]
```

### UX-рекомендации: таблица сравнения планов

Построить таблицу из данных `GET /public/plans` + `GET /admin/my-modules`:

| | Стартовый | Бизнес | Коммерция |
|---|---|---|---|
| **Цена/мес** | 1 990 ₽ | 4 990 ₽ | 9 990 ₽ |
| **Цена/год** | 1 908 ₽/мес | 4 790 ₽/мес | 9 590 ₽/мес |
| **Разовая оплата** | 9 990 ₽ | 19 990 ₽ | 49 990 ₽ |
| Контент | ✅ | ✅ | ✅ |
| Компания | ✅ | ✅ | ✅ |
| CRM Базовый | ✅ | ✅ | ✅ |
| CRM Про | — | ✅ | ✅ |
| SEO Расширенный | — | ✅ | ✅ |
| Мультиязычность | — | ✅ | ✅ |
| Каталог Базовый | — | — | ✅ |
| Каталог Про | — | — | ✅ |
| Документы | — | ✅ | ✅ |
| **Пользователи** | 2 | 5 | 10 |
| **Хранилище** | 5 ГБ | 20 ГБ | 50 ГБ |
| **Статьи** | 100 | 500 | ∞ |
| **Домены** | 1 | 3 | 5 |

Логика для галочек: проверить, содержит ли `plan.modules[]` модуль с данным `slug`.

Текущий план пользователя выделить визуально (рамкой или бейджем «Ваш план»). Для определения — сравнить `plan.slug` из `GET /admin/my-plan` с `slug` в списке.

### UX: кнопки действий

| Контекст | Кнопка | Действие |
|----------|--------|----------|
| Модуль не включён, есть в плане повыше | «Сменить тариф» | Открыть форму заявки `plan_upgrade` |
| Модуль не включён, можно купить отдельно | «Подключить модуль» (цена/мес) | Открыть форму заявки `module_addon` |
| Бандл доступен | «Купить пакет» (цена со скидкой) | Открыть форму заявки `bundle_addon` |
| Модуль уже активен | Бейдж «Подключено» | — |

---

## 6. Заявки на апгрейд

### POST /api/v1/admin/upgrade-requests

Создание заявки на апгрейд. **Rate limit:** 5 запросов в час на тенанта.

**Body:**

```json
{
  "request_type": "plan_upgrade",
  "target_plan_id": "uuid",
  "message": "Хотим перейти на тариф Бизнес"
}
```

Варианты `request_type`:

| Тип | Описание | Какое поле заполнять |
|-----|----------|---------------------|
| `plan_upgrade` | Смена тарифа | `target_plan_id` |
| `module_addon` | Покупка отдельного модуля | `target_module_id` |
| `bundle_addon` | Покупка пакета модулей | `target_bundle_id` |

`message` — необязательное текстовое поле (до 2000 символов). Показать textarea в модалке.

**Ответ (200):**

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "request_type": "plan_upgrade",
  "target_plan_id": "uuid",
  "target_module_id": null,
  "target_bundle_id": null,
  "status": "pending",
  "message": "Хотим перейти на тариф Бизнес",
  "reviewed_by": null,
  "reviewed_at": null,
  "created_at": "2026-03-01T10:30:00Z",
  "updated_at": "2026-03-01T10:30:00Z",
  "target_plan_name": "Бизнес",
  "target_module_name": null,
  "target_bundle_name": null
}
```

**Ошибка 429** (слишком много заявок):

```json
{
  "type": "https://api.cms.local/errors/rate_limit_exceeded",
  "status": 429,
  "detail": "Too many upgrade requests. Please wait before submitting another.",
  "retry_after": 2400
}
```

### GET /api/v1/admin/upgrade-requests

Список заявок текущего тенанта.

**Ответ:** массив `UpgradeRequestResponse`.

### UX модального окна заявки

**Заголовок:** «Заявка на изменение тарифа»

**Поля формы:**

| Поле (RU) | Тип | API-поле | Примечание |
|-----------|-----|----------|------------|
| Тип заявки | Select (скрытый, определяется контекстом) | `request_type` | |
| Тариф / Модуль / Пакет | Автоматически из контекста | `target_plan_id` / `target_module_id` / `target_bundle_id` | Показать название |
| Комментарий | Textarea | `message` | Необязательно |

**Список заявок** (таблица):

| Колонка (RU) | Поле |
|--------------|------|
| Дата | `created_at` |
| Тип | `request_type` → см. маппинг ниже |
| Что запрошено | `target_plan_name` / `target_module_name` / `target_bundle_name` |
| Статус | `status` → см. маппинг ниже |
| Дата рассмотрения | `reviewed_at` |

```typescript
const requestTypeLabels: Record<string, string> = {
  plan_upgrade: 'Смена тарифа',
  module_addon: 'Покупка модуля',
  bundle_addon: 'Покупка пакета',
}

const requestStatusLabels: Record<string, string> = {
  pending: 'На рассмотрении',
  approved: 'Одобрена',
  rejected: 'Отклонена',
}

const requestStatusColors: Record<string, string> = {
  pending: 'yellow',
  approved: 'green',
  rejected: 'red',
}
```

---

## 7. Обработка ошибок лимитов

При создании продукта, статьи, пользователя — бэкенд может вернуть **403** с `error_code: "limit_exceeded"`:

```json
{
  "type": "https://api.cms.local/errors/limit_exceeded",
  "title": "Limit Exceeded",
  "status": 403,
  "detail": "Resource limit reached for 'max_products'. Upgrade your plan or purchase additional capacity.",
  "resource": "max_products",
  "current_usage": 5000,
  "limit": 5000,
  "restriction_level": "organization"
}
```

### UX-обработка

При получении `error_code === "limit_exceeded"`:

1. Показать тост/баннер: **«Лимит исчерпан: {resource_label}. Использовано {current_usage} из {limit}.»**
2. Добавить кнопку: **«Обновить тариф»** → переход на страницу каталога планов.
3. Не показывать стандартную ошибку 403.

```typescript
if (error.detail?.resource && error.status === 403 && error.detail?.type?.includes('limit_exceeded')) {
  const label = limitLabels[error.detail.resource]?.label || error.detail.resource
  showLimitExceededModal(label, error.detail.current_usage, error.detail.limit)
}
```

---

## 8. Платформа: управление планами

> Доступно только **platform_owner** / **superuser**

**Экран:** `/admin/platform/plans`

### GET /api/v1/admin/platform/plans

Все планы, включая неактивные.

### POST /api/v1/admin/platform/plans

**Body:**

```json
{
  "slug": "custom",
  "name": "Custom",
  "name_ru": "Индивидуальный",
  "description_ru": "Индивидуальный план",
  "price_monthly_kopecks": 750000,
  "price_yearly_kopecks": 720000,
  "setup_fee_kopecks": 3000000,
  "is_default": false,
  "is_active": true,
  "sort_order": 5,
  "limits": {
    "max_users": 15,
    "max_storage_mb": 102400,
    "max_leads_per_month": 10000,
    "max_products": 10000,
    "max_variants": 20000,
    "max_domains": 10,
    "max_articles": -1,
    "max_rbac_roles": 20
  },
  "module_slugs": ["core", "content", "company", "crm_basic", "crm_pro", "seo_advanced"]
}
```

### PATCH /api/v1/admin/platform/plans/{plan_id}

Частичное обновление. Передавать только изменённые поля.

### Поля формы плана (RU)

| Поле (RU) | API-поле | Тип | Примечание |
|-----------|----------|-----|------------|
| Слаг | `slug` | string | Только латиница, для создания |
| Название (EN) | `name` | string | |
| Название (RU) | `name_ru` | string | Основное для отображения |
| Описание (RU) | `description_ru` | textarea | |
| Цена в месяц, коп. | `price_monthly_kopecks` | number | Показывать как «₽/мес» |
| Цена в год, коп. | `price_yearly_kopecks` | number | |
| Разовая оплата, коп. | `setup_fee_kopecks` | number | |
| По умолчанию | `is_default` | boolean | Один план в системе |
| Активен | `is_active` | boolean | Неактивный не виден клиентам |
| Порядок сортировки | `sort_order` | number | |
| Лимиты | `limits` | JSON | Форма с полями ниже |
| Модули | `module_slugs` | string[] | Мультиселект из списка модулей |

---

## 9. Платформа: управление модулями

**Экран:** `/admin/platform/modules`

### GET /api/v1/admin/platform/modules

### POST /api/v1/admin/platform/modules

### PATCH /api/v1/admin/platform/modules/{module_id}

### Поля формы модуля (RU)

| Поле (RU) | API-поле | Тип |
|-----------|----------|-----|
| Слаг | `slug` | string |
| Название (EN) | `name` | string |
| Название (RU) | `name_ru` | string |
| Описание (EN) | `description` | textarea |
| Описание (RU) | `description_ru` | textarea |
| Категория | `category` | select: platform, content, company, crm, commerce |
| Цена, коп./мес | `price_monthly_kopecks` | number |
| Базовый (всегда вкл.) | `is_base` | boolean |
| Порядок сортировки | `sort_order` | number |

---

## 10. Платформа: управление бандлами

**Экран:** `/admin/platform/bundles`

### GET /api/v1/admin/platform/bundles

### POST /api/v1/admin/platform/bundles

### PATCH /api/v1/admin/platform/bundles/{bundle_id}

### Поля формы бандла (RU)

| Поле (RU) | API-поле | Тип |
|-----------|----------|-----|
| Слаг | `slug` | string |
| Название (EN) | `name` | string |
| Название (RU) | `name_ru` | string |
| Описание (EN) | `description` | textarea |
| Описание (RU) | `description_ru` | textarea |
| Цена, коп./мес | `price_monthly_kopecks` | number |
| Скидка, % | `discount_percent` | number (0–100) |
| Активен | `is_active` | boolean |
| Порядок сортировки | `sort_order` | number |
| Модули | `module_slugs` | string[] мультиселект |

---

## 11. Платформа: заявки на апгрейд

**Экран:** `/admin/platform/upgrade-requests`

### GET /api/v1/admin/platform/upgrade-requests

**Query:** `?status=pending` (опционально, фильтрация по статусу)

### PATCH /api/v1/admin/platform/upgrade-requests/{request_id}

**Body:**

```json
{ "status": "approved" }
```

или

```json
{ "status": "rejected" }
```

При `approved` — система автоматически:
- **plan_upgrade**: меняет план тенанта, пересоздаёт модули из нового плана (addon/bundle/manual модули сохраняются)
- **module_addon**: добавляет модуль с `source=addon`
- **bundle_addon**: добавляет все модули бандла с `source=bundle`

### UX

Таблица заявок с колонками:

| Колонка (RU) | Поле |
|--------------|------|
| Дата заявки | `created_at` |
| Организация | по `tenant_id` (подтянуть название) |
| Тип | `request_type` → маппинг |
| Цель | `target_plan_name` / `target_module_name` / `target_bundle_name` |
| Комментарий | `message` |
| Статус | `status` → бейдж |
| Действия | Кнопки «Одобрить» / «Отклонить» (только для `pending`) |

---

## 12. Платформа: модули тенанта

### POST /api/v1/admin/platform/tenants/{tenant_id}/modules

Вручную добавить модуль тенанту.

**Body:**

```json
{
  "module_slug": "seo_advanced",
  "source": "manual",
  "enabled": true
}
```

### DELETE /api/v1/admin/platform/tenants/{tenant_id}/modules

Убрать модуль у тенанта.

**Body:**

```json
{ "module_slug": "seo_advanced" }
```

---

## 13. Словарь полей

### Модули (seed-данные)

| slug | Название (RU) для UI | Категория (RU) |
|------|---------------------|----------------|
| `core` | Базовый | Платформа |
| `content` | Контент | Контент |
| `company` | Компания | Компания |
| `crm_basic` | CRM Базовый | CRM |
| `crm_pro` | CRM Про | CRM |
| `seo_advanced` | SEO Расширенный | Платформа |
| `multilang` | Мультиязычность | Платформа |
| `catalog_basic` | Каталог Базовый | Коммерция |
| `catalog_pro` | Каталог Про | Коммерция |
| `documents` | Документы | Контент |

### Планы (seed-данные)

| slug | Название (RU) | Цена/мес |
|------|--------------|----------|
| `starter` | Стартовый | 1 990 ₽ |
| `business` | Бизнес | 4 990 ₽ |
| `commerce` | Коммерция | 9 990 ₽ |
| `enterprise` | Корпоративный | Индивидуально |
| `agency` | Агентский | 990 ₽ |

### Бандлы (seed-данные)

| slug | Название (RU) | Цена/мес | Скидка |
|------|--------------|----------|--------|
| `seo_pack` | SEO-пакет | 1 990 ₽ | 33% |
| `catalog_pack` | Каталог-пакет | 4 990 ₽ | 9% |
| `analytics_pack` | Аналитика-пакет | 1 490 ₽ | — |

---

## 14. Screen-to-API Mapping

| Экран | URL в админке | Метод | Эндпоинт | Роль |
|-------|---------------|-------|----------|------|
| Мой тариф | `/admin/billing` | GET | `/api/v1/admin/my-plan` | Любой |
| Мои модули | `/admin/billing/modules` | GET | `/api/v1/admin/my-modules` | Любой |
| Лимиты | `/admin/billing/limits` | GET | `/api/v1/admin/my-limits` | Любой |
| Каталог тарифов | `/admin/billing/plans` | GET | `/api/v1/public/plans` | Любой |
| Каталог модулей | `/admin/billing/plans` | GET | `/api/v1/public/modules` | Любой |
| Каталог пакетов | `/admin/billing/plans` | GET | `/api/v1/public/bundles` | Любой |
| Создать заявку | модальное окно | POST | `/api/v1/admin/upgrade-requests` | Любой |
| Мои заявки | `/admin/billing/requests` | GET | `/api/v1/admin/upgrade-requests` | Любой |
| Управление планами | `/admin/platform/plans` | GET/POST/PATCH | `/api/v1/admin/platform/plans` | platform_owner |
| Управление модулями | `/admin/platform/modules` | GET/POST/PATCH | `/api/v1/admin/platform/modules` | platform_owner |
| Управление бандлами | `/admin/platform/bundles` | GET/POST/PATCH | `/api/v1/admin/platform/bundles` | platform_owner |
| Заявки (все) | `/admin/platform/requests` | GET/PATCH | `/api/v1/admin/platform/upgrade-requests` | platform_owner |
| Модули тенанта | в карточке тенанта | POST/DELETE | `/api/v1/admin/platform/tenants/{id}/modules` | platform_owner |
