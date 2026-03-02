# Биллинг — публичные API для клиентского сайта

> Тарифные планы, модули и пакеты — без авторизации

---

## Содержание

1. [Общее](#1-общее)
2. [GET /public/plans — Тарифные планы](#2-тарифные-планы)
3. [GET /public/modules — Модули](#3-модули)
4. [GET /public/bundles — Пакеты (бандлы)](#4-пакеты)
5. [Типы данных и интерфейсы (TypeScript)](#5-typescript-интерфейсы)
6. [Утилиты для отображения](#6-утилиты)
7. [Пример: страница «Тарифы»](#7-пример-страница-тарифы)
8. [Пример: блок «Модули»](#8-пример-блок-модули)

---

## 1. Общее

### Base URL

```
Production: https://api.yoursite.com/api/v1
Development: http://localhost:8000/api/v1
```

### Авторизация

**Не требуется.** Все три эндпоинта полностью публичные.

### Когда использовать

- Страница «Тарифы» / «Pricing» на клиентском сайте
- Блок сравнения планов
- Лендинг с модулями и возможностями
- Форма «Оставить заявку на подключение»

### Цены

Все цены — в **копейках** (целое число, `int`). Для отображения делить на 100.

### Лимиты: значения

| Значение | Означает | Отображение |
|----------|----------|-------------|
| `-1` | Безлимитно | «∞» или «Без ограничений» |
| `0` | Недоступно (не входит в план) | «—» или не показывать |
| `> 0` | Конкретный лимит | Число |

---

## 2. Тарифные планы

### GET /api/v1/public/plans

Возвращает все активные тарифные планы, отсортированные по `sort_order`.

**Запрос:**

```bash
curl https://api.yoursite.com/api/v1/public/plans
```

**Ответ (200):**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "slug": "starter",
    "name": "Starter",
    "name_ru": "Стартовый",
    "description": null,
    "description_ru": "Для небольших компаний и визиток",
    "price_monthly_kopecks": 199000,
    "price_yearly_kopecks": 190800,
    "setup_fee_kopecks": 999000,
    "is_default": true,
    "is_active": true,
    "sort_order": 0,
    "limits": {
      "max_users": 2,
      "max_storage_mb": 5120,
      "max_leads_per_month": 500,
      "max_products": 0,
      "max_variants": 0,
      "max_domains": 1,
      "max_articles": 100,
      "max_rbac_roles": 2
    },
    "modules": [
      {
        "id": "uuid",
        "slug": "core",
        "name": "Core",
        "name_ru": "Базовый",
        "category": "platform",
        "is_base": true
      },
      {
        "id": "uuid",
        "slug": "content",
        "name": "Content",
        "name_ru": "Контент",
        "category": "content",
        "is_base": false
      },
      {
        "id": "uuid",
        "slug": "company",
        "name": "Company",
        "name_ru": "Компания",
        "category": "company",
        "is_base": false
      },
      {
        "id": "uuid",
        "slug": "crm_basic",
        "name": "CRM Basic",
        "name_ru": "CRM Базовый",
        "category": "crm",
        "is_base": false
      }
    ]
  },
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
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
      { "id": "uuid", "slug": "core", "name_ru": "Базовый", "category": "platform", "is_base": true },
      { "id": "uuid", "slug": "content", "name_ru": "Контент", "category": "content", "is_base": false },
      { "id": "uuid", "slug": "company", "name_ru": "Компания", "category": "company", "is_base": false },
      { "id": "uuid", "slug": "crm_basic", "name_ru": "CRM Базовый", "category": "crm", "is_base": false },
      { "id": "uuid", "slug": "crm_pro", "name_ru": "CRM Про", "category": "crm", "is_base": false },
      { "id": "uuid", "slug": "seo_advanced", "name_ru": "SEO Расширенный", "category": "platform", "is_base": false },
      { "id": "uuid", "slug": "multilang", "name_ru": "Мультиязычность", "category": "platform", "is_base": false },
      { "id": "uuid", "slug": "documents", "name_ru": "Документы", "category": "content", "is_base": false }
    ]
  }
]
```

### Поля PlanResponse

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Идентификатор |
| `slug` | string | Уникальный код (`starter`, `business`, `commerce`, `enterprise`, `agency`) |
| `name` | string | Название (EN) |
| `name_ru` | string | **Название (RU) — использовать для отображения** |
| `description_ru` | string \| null | Описание для карточки плана |
| `price_monthly_kopecks` | int | Цена за месяц в копейках |
| `price_yearly_kopecks` | int | Цена за год в копейках (среднемесячная при годовой оплате) |
| `setup_fee_kopecks` | int | Разовая оплата за подключение |
| `is_default` | bool | План по умолчанию |
| `is_active` | bool | Активен (всегда `true` в публичном API) |
| `sort_order` | int | Порядок отображения |
| `limits` | object | Лимиты ресурсов (см. таблицу ниже) |
| `modules` | array | Модули, включённые в план |

### Поля limits

| Ключ | Описание (RU) | Пример |
|------|---------------|--------|
| `max_users` | Пользователи | `2` |
| `max_storage_mb` | Хранилище (МБ) | `5120` (= 5 ГБ) |
| `max_leads_per_month` | Заявки в месяц | `500` |
| `max_products` | Товары | `0` (= недоступно) |
| `max_variants` | Вариации товаров | `0` |
| `max_domains` | Домены | `1` |
| `max_articles` | Статьи | `100`, `-1` (= безлимит) |
| `max_rbac_roles` | Роли доступа | `2` |

---

## 3. Модули

### GET /api/v1/public/modules

Все доступные модули с ценами. Отсортированы по `sort_order`.

**Запрос:**

```bash
curl https://api.yoursite.com/api/v1/public/modules
```

**Ответ (200):**

```json
[
  {
    "id": "uuid",
    "slug": "core",
    "name": "Core",
    "name_ru": "Базовый",
    "description": "Auth, RBAC, SSL, media, sitemap, robots.txt, dashboard, basic audit",
    "description_ru": "Авторизация, RBAC, SSL, медиа, карта сайта, robots.txt, дашборд, базовый аудит",
    "category": "platform",
    "price_monthly_kopecks": 0,
    "is_base": true,
    "sort_order": 0
  },
  {
    "id": "uuid",
    "slug": "content",
    "name": "Content",
    "name_ru": "Контент",
    "description_ru": "Блог, кейсы, отзывы, FAQ, блоки контента, массовые операции",
    "category": "content",
    "price_monthly_kopecks": 99000,
    "is_base": false,
    "sort_order": 1
  },
  {
    "id": "uuid",
    "slug": "catalog_basic",
    "name": "Catalog Basic",
    "name_ru": "Каталог Базовый",
    "description_ru": "Товары, категории, цены, изображения, поиск",
    "category": "commerce",
    "price_monthly_kopecks": 299000,
    "is_base": false,
    "sort_order": 7
  }
]
```

### Поля BillingModuleResponse

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Идентификатор |
| `slug` | string | Уникальный код |
| `name` | string | Название (EN) |
| `name_ru` | string | **Название (RU) — для отображения** |
| `description` | string \| null | Описание (EN) |
| `description_ru` | string \| null | **Описание (RU) — для отображения** |
| `category` | string | Категория: `platform`, `content`, `company`, `crm`, `commerce` |
| `price_monthly_kopecks` | int | Цена отдельной покупки за месяц (0 = бесплатный / базовый) |
| `is_base` | bool | Базовый модуль (всегда включён, бесплатен) |
| `sort_order` | int | Порядок |

---

## 4. Пакеты

### GET /api/v1/public/bundles

Тематические пакеты модулей со скидкой.

**Запрос:**

```bash
curl https://api.yoursite.com/api/v1/public/bundles
```

**Ответ (200):**

```json
[
  {
    "id": "uuid",
    "slug": "seo_pack",
    "name": "SEO Pack",
    "name_ru": "SEO-пакет",
    "description": "SEO Advanced + Multilang",
    "description_ru": "SEO Расширенный + Мультиязычность",
    "price_monthly_kopecks": 199000,
    "discount_percent": 33,
    "is_active": true,
    "sort_order": 0,
    "modules": [
      { "id": "uuid", "slug": "seo_advanced", "name": "SEO Advanced", "name_ru": "SEO Расширенный" },
      { "id": "uuid", "slug": "multilang", "name": "Multilang", "name_ru": "Мультиязычность" }
    ]
  },
  {
    "id": "uuid",
    "slug": "catalog_pack",
    "name": "Catalog Pack",
    "name_ru": "Каталог-пакет",
    "description_ru": "Каталог Базовый + Каталог Про",
    "price_monthly_kopecks": 499000,
    "discount_percent": 9,
    "is_active": true,
    "sort_order": 1,
    "modules": [
      { "id": "uuid", "slug": "catalog_basic", "name_ru": "Каталог Базовый" },
      { "id": "uuid", "slug": "catalog_pro", "name_ru": "Каталог Про" }
    ]
  }
]
```

### Поля BundleResponse

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Идентификатор |
| `slug` | string | Уникальный код |
| `name_ru` | string | **Название (RU)** |
| `description_ru` | string \| null | Описание |
| `price_monthly_kopecks` | int | Цена пакета за месяц |
| `discount_percent` | int | Скидка относительно покупки модулей по отдельности |
| `is_active` | bool | Активен |
| `modules` | array | Модули, входящие в пакет |

---

## 5. TypeScript-интерфейсы

```typescript
// ── Модуль ──

interface BillingModule {
  id: string
  slug: string
  name: string
  name_ru: string
  description: string | null
  description_ru: string | null
  category: 'platform' | 'content' | 'company' | 'crm' | 'commerce'
  price_monthly_kopecks: number
  is_base: boolean
  sort_order: number
}

// ── Модуль внутри плана ──

interface PlanModule {
  id: string
  slug: string
  name: string
  name_ru: string
  category: string
  is_base: boolean
}

// ── План ──

interface PlanLimits {
  max_users: number
  max_storage_mb: number
  max_leads_per_month: number
  max_products: number
  max_variants: number
  max_domains: number
  max_articles: number
  max_rbac_roles: number
}

interface Plan {
  id: string
  slug: string
  name: string
  name_ru: string
  description: string | null
  description_ru: string | null
  price_monthly_kopecks: number
  price_yearly_kopecks: number
  setup_fee_kopecks: number
  is_default: boolean
  is_active: boolean
  sort_order: number
  limits: PlanLimits
  modules: PlanModule[]
}

// ── Модуль внутри бандла ──

interface BundleModule {
  id: string
  slug: string
  name: string
  name_ru: string
}

// ── Бандл ──

interface Bundle {
  id: string
  slug: string
  name: string
  name_ru: string
  description: string | null
  description_ru: string | null
  price_monthly_kopecks: number
  discount_percent: number
  is_active: boolean
  sort_order: number
  modules: BundleModule[]
}
```

---

## 6. Утилиты

### Форматирование цены

```typescript
export function formatPrice(kopecks: number): string {
  if (kopecks === 0) return 'Бесплатно'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(kopecks / 100)
}

// 199000 → "1 990 ₽"
// 0      → "Бесплатно"
```

### Форматирование лимита

```typescript
export function formatLimit(value: number, unit?: string): string {
  if (value === -1) return '∞'
  if (value === 0) return '—'
  if (unit === 'МБ' && value >= 1024) {
    return `${(value / 1024).toFixed(0)} ГБ`
  }
  return `${value.toLocaleString('ru-RU')}${unit ? ` ${unit}` : ''}`
}

// -1          → "∞"
// 0           → "—"
// 5120, "МБ"  → "5 ГБ"
// 500         → "500"
```

### Проверка наличия модуля в плане

```typescript
export function planHasModule(plan: Plan, moduleSlug: string): boolean {
  return plan.modules.some((m) => m.slug === moduleSlug)
}
```

### Расчёт годовой экономии

```typescript
export function yearlyDiscount(plan: Plan): number {
  if (plan.price_monthly_kopecks === 0) return 0
  const monthlyTotal = plan.price_monthly_kopecks * 12
  const yearlyTotal = plan.price_yearly_kopecks * 12
  return Math.round((1 - yearlyTotal / monthlyTotal) * 100)
}
// Starter: (1 - 190800*12 / 199000*12) → ~4%
```

### Русские названия для лимитов

```typescript
export const LIMIT_LABELS: Record<string, { label: string; unit?: string }> = {
  max_users:           { label: 'Пользователи' },
  max_storage_mb:      { label: 'Хранилище',       unit: 'МБ' },
  max_leads_per_month: { label: 'Заявки в месяц' },
  max_products:        { label: 'Товары' },
  max_variants:        { label: 'Вариации товаров' },
  max_domains:         { label: 'Домены' },
  max_articles:        { label: 'Статьи' },
  max_rbac_roles:      { label: 'Роли' },
}
```

### Русские названия для модулей (fallback)

Обычно берутся из `name_ru` ответа API. Если нужен fallback:

```typescript
export const MODULE_LABELS: Record<string, string> = {
  core:          'Базовый',
  content:       'Контент',
  company:       'Компания',
  crm_basic:     'CRM Базовый',
  crm_pro:       'CRM Про',
  seo_advanced:  'SEO Расширенный',
  multilang:     'Мультиязычность',
  catalog_basic: 'Каталог Базовый',
  catalog_pro:   'Каталог Про',
  documents:     'Документы',
}
```

### Русские названия для категорий

```typescript
export const CATEGORY_LABELS: Record<string, string> = {
  platform: 'Платформа',
  content:  'Контент',
  company:  'Компания',
  crm:      'CRM',
  commerce: 'Коммерция',
}
```

---

## 7. Пример: страница «Тарифы»

### Вызовы API при загрузке

```typescript
const [plans, modules, bundles] = await Promise.all([
  fetch('/api/v1/public/plans').then(r => r.json()),
  fetch('/api/v1/public/modules').then(r => r.json()),
  fetch('/api/v1/public/bundles').then(r => r.json()),
])
```

### Структура страницы

```
┌─────────────────────────────────────────────────────┐
│  Тарифные планы                                     │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Стартовый│  │  Бизнес  │  │ Коммерция│          │
│  │ 1 990 ₽  │  │ 4 990 ₽  │  │ 9 990 ₽  │          │
│  │ /мес     │  │ /мес     │  │ /мес     │          │
│  │          │  │          │  │          │          │
│  │ ✅ Конт. │  │ ✅ Конт. │  │ ✅ Конт. │          │
│  │ ✅ Комп. │  │ ✅ Комп. │  │ ✅ Комп. │          │
│  │ ✅ CRM   │  │ ✅ CRM   │  │ ✅ CRM   │          │
│  │          │  │ ✅ SEO   │  │ ✅ SEO   │          │
│  │          │  │ ✅ Multi │  │ ✅ Multi │          │
│  │          │  │          │  │ ✅ Катал.│          │
│  │          │  │          │  │          │          │
│  │ 2 польз. │  │ 5 польз. │  │ 10 польз.│          │
│  │ 5 ГБ    │  │ 20 ГБ   │  │ 50 ГБ   │          │
│  │ 100 стат.│  │ 500 стат.│  │ ∞ статей │          │
│  │          │  │          │  │          │          │
│  │[Выбрать] │  │[Выбрать] │  │[Выбрать] │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                     │
│  Не нашли подходящий? → Корпоративный / Агентский   │
├─────────────────────────────────────────────────────┤
│  Отдельные модули                                   │
│                                                     │
│  SEO Расширенный    1 490 ₽/мес                     │
│  Мультиязычность    1 490 ₽/мес                     │
│  Каталог Базовый    2 990 ₽/мес                     │
│  ...                                                │
├─────────────────────────────────────────────────────┤
│  Пакеты со скидкой                                  │
│                                                     │
│  SEO-пакет          1 990 ₽/мес  (скидка 33%)      │
│    → SEO Расширенный + Мультиязычность              │
│  Каталог-пакет      4 990 ₽/мес  (скидка 9%)       │
│    → Каталог Базовый + Каталог Про                  │
└─────────────────────────────────────────────────────┘
```

### Логика карточки плана

```typescript
function PlanCard({ plan, allModules }: { plan: Plan; allModules: BillingModule[] }) {
  // Модули, НЕ включённые в план (для блока «недоступно»)
  const nonBaseModules = allModules.filter(m => !m.is_base)
  const includedSlugs = new Set(plan.modules.map(m => m.slug))

  return (
    <div>
      <h3>{plan.name_ru}</h3>
      <p>{plan.description_ru}</p>
      <div className="price">
        {formatPrice(plan.price_monthly_kopecks)}<span>/мес</span>
      </div>
      {plan.setup_fee_kopecks > 0 && (
        <div className="setup-fee">
          Разовая оплата: {formatPrice(plan.setup_fee_kopecks)}
        </div>
      )}

      {/* Модули */}
      {nonBaseModules.map(mod => (
        <div key={mod.slug}>
          {includedSlugs.has(mod.slug) ? '✅' : '—'} {mod.name_ru}
        </div>
      ))}

      {/* Лимиты */}
      {Object.entries(LIMIT_LABELS).map(([key, { label, unit }]) => (
        <div key={key}>
          {label}: {formatLimit(plan.limits[key], unit)}
        </div>
      ))}
    </div>
  )
}
```

---

## 8. Пример: блок «Модули»

Для отображения отдельных модулей, сгруппированных по категориям:

```typescript
function ModulesCatalog({ modules }: { modules: BillingModule[] }) {
  const grouped = modules
    .filter(m => !m.is_base)
    .reduce((acc, mod) => {
      const cat = CATEGORY_LABELS[mod.category] || mod.category
      if (!acc[cat]) acc[cat] = []
      acc[cat].push(mod)
      return acc
    }, {} as Record<string, BillingModule[]>)

  return (
    <>
      {Object.entries(grouped).map(([category, mods]) => (
        <div key={category}>
          <h4>{category}</h4>
          {mods.map(mod => (
            <div key={mod.slug}>
              <strong>{mod.name_ru}</strong>
              <p>{mod.description_ru}</p>
              <span>{formatPrice(mod.price_monthly_kopecks)}/мес</span>
            </div>
          ))}
        </div>
      ))}
    </>
  )
}
```

---

## Сводная таблица эндпоинтов

| Метод | Путь | Авторизация | Описание |
|-------|------|-------------|----------|
| GET | `/api/v1/public/plans` | Нет | Активные тарифные планы с модулями и лимитами |
| GET | `/api/v1/public/modules` | Нет | Каталог всех модулей с ценами |
| GET | `/api/v1/public/bundles` | Нет | Активные пакеты модулей со скидками |
