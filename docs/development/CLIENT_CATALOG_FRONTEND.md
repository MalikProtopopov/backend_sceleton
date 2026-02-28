# Клиентский фронтенд — Каталог продуктов (Public API)

> **Назначение**: Полное руководство для фронтенд-разработчика по реализации каталога товаров на клиентском сайте.  
> **Авторизация**: Не требуется. Все запросы — публичные.  
> **Версия бэкенда**: 2026-02-28 (ветка `feat/product-catalog`)  
> **Feature flag**: `catalog_module` — если выключен, все эндпоинты вернут `404`.

---

## Содержание

1. [Общие принципы](#1-общие-принципы)
2. [Резолв тенанта](#2-резолв-тенанта)
3. [Формат ошибок (RFC 7807)](#3-формат-ошибок)
4. [API: Категории](#4-api-категории)
5. [API: Фильтры каталога (фасетная навигация)](#5-api-фильтры-каталога)
6. [API: Список продуктов (с фильтрацией и сортировкой)](#6-api-список-продуктов)
7. [API: Карточка продукта](#7-api-карточка-продукта)
8. [Варианты и тарифы на карточке товара](#8-варианты-и-тарифы-на-карточке-товара)
9. [ЧПУ-спецификация (SEO-friendly URLs)](#9-чпу-спецификация)
10. [SEO: Генерация страниц фильтров](#10-seo-генерация-страниц)
11. [API: Заявка на продукт](#11-api-заявка-на-продукт)
12. [Rate Limiting](#12-rate-limiting)
13. [TypeScript-типы (copy-paste ready)](#13-typescript-типы)
14. [Примеры интеграции (React/Next.js)](#14-примеры-интеграции)
15. [Типичные сценарии и страницы](#15-типичные-сценарии)

---

## 1. Общие принципы

### Base URL

```
https://{site-domain}/api/v1
```

### Идентификация тенанта

Каждый публичный запрос требует query-параметр `tenant_id`:

```
GET /api/v1/public/products?tenant_id={uuid}
```

`tenant_id` получается один раз при загрузке сайта и сохраняется на всю сессию (см. раздел 2).

### Заголовки

```typescript
const headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};
// Авторизация НЕ нужна для публичных запросов
```

### Пагинация

Все списковые эндпоинты поддерживают пагинацию:

| Параметр | Тип | Default | Ограничения | Описание |
|----------|-----|---------|-------------|----------|
| `page` | int | `1` | >= 1 | Номер страницы |
| `page_size` | int | `20` | 1–100 | Элементов на странице |

**Ответ всегда содержит:**
```typescript
{
  items: T[],
  total: number,      // общее кол-во элементов
  page: number,       // текущая страница
  page_size: number   // размер страницы
}
```

---

## 2. Резолв тенанта

При загрузке сайта — определить `tenant_id` по домену:

```typescript
// GET /api/v1/public/tenants/by-domain/{hostname}

const resolveTenant = async (): Promise<TenantInfo> => {
  const hostname = window.location.hostname;
  const res = await fetch(`/api/v1/public/tenants/by-domain/${hostname}`);

  if (res.status === 404) {
    // Домен не привязан ни к одному тенанту
    throw new Error('Сайт не найден');
  }

  return res.json();
};

// Результат:
interface TenantInfo {
  tenant_id: string;     // UUID — сохранить и использовать во всех запросах
  slug: string;
  name: string;
  logo_url: string | null;
  primary_color: string | null;
  site_url: string | null;
}
```

Сохрани `tenant_id` в глобальный state (Zustand / React Context / Next.js middleware) и передавай во все запросы.

---

## 3. Формат ошибок

Все ошибки возвращаются в формате **RFC 7807 Problem Details**:

```typescript
interface ApiError {
  type: string;         // URL-идентификатор типа ошибки
  title: string;        // Человекочитаемый заголовок
  status: number;       // HTTP-код
  detail: string;       // Описание ошибки
  instance: string | null;
  // + дополнительные поля в зависимости от типа
}
```

### Все возможные HTTP-коды для публичных запросов

| Код | error_code | Когда | Что делать в UI |
|-----|------------|-------|-----------------|
| **200** | — | Успешный ответ | Рендерить данные |
| **201** | — | Заявка создана | Показать "Спасибо!" |
| **400** | `tenant_required` | Не передан `tenant_id` | Проверить логику резолва тенанта |
| **400** | `invalid_tenant_id` | Невалидный формат UUID | Проверить `tenant_id` |
| **400** | `validation_error` | Ошибки валидации полей | Показать ошибки в форме |
| **404** | `not_found` | Товар/категория не найден(а) | Показать страницу 404 |
| **404** | `tenant_not_found` | Тенант не найден/неактивен | Показать "Сайт недоступен" |
| **404** | `feature_not_available` | Каталог выключен для тенанта | Скрыть раздел каталога |
| **422** | — | Ошибка валидации FastAPI (поля) | Показать ошибки в форме |
| **429** | `rate_limit_exceeded` | Слишком много запросов | Показать "Подождите" + retry |
| **500** | — | Ошибка сервера | "Что-то пошло не так" |
| **502** | `external_service_error` | Внешний сервис недоступен | "Попробуйте позже" |
| **503** | `database_error` | БД недоступна | "Сервис временно недоступен" |

### Примеры тел ошибок

**404 — товар не найден:**
```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Product with id 'widget-pro-xxx' not found",
  "instance": null,
  "resource": "Product"
}
```

**404 — каталог выключен (feature flag):**
```json
{
  "type": "https://api.cms.local/errors/feature_not_available",
  "title": "Feature Not Available",
  "status": 404,
  "detail": "The requested resource is not available.",
  "instance": null,
  "feature": "catalog_module",
  "_hint": "This feature is disabled for the tenant. Enable it via the admin panel."
}
```

**400 — tenant_id не передан:**
```json
{
  "type": "https://api.cms.local/errors/tenant_required",
  "title": "Tenant Required",
  "status": 400,
  "detail": "tenant_id parameter is required in multi-tenant mode",
  "instance": null
}
```

**422 — ошибка валидации (заявка):**
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    },
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error"
    }
  ]
}
```

**429 — rate limit:**
```json
{
  "type": "https://api.cms.local/errors/rate_limit_exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many requests",
  "instance": null,
  "retry_after": 60
}
```

### Универсальный обработчик ошибок

```typescript
class ApiClient {
  private tenantId: string;
  private baseUrl: string;

  constructor(tenantId: string, baseUrl = '/api/v1') {
    this.tenantId = tenantId;
    this.baseUrl = baseUrl;
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);
    url.searchParams.set('tenant_id', this.tenantId);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') url.searchParams.set(k, v);
      });
    }

    const res = await fetch(url.toString());
    if (!res.ok) {
      const error = await res.json().catch(() => null);
      throw new ApiError(res.status, error);
    }
    return res.json();
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);
    url.searchParams.set('tenant_id', this.tenantId);

    const res = await fetch(url.toString(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => null);
      throw new ApiError(res.status, error);
    }
    return res.json();
  }
}

class ApiError extends Error {
  status: number;
  code: string | null;
  body: any;

  constructor(status: number, body: any) {
    const detail = body?.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((e: any) => e.msg).join('; ')
        : `HTTP ${status}`;

    super(message);
    this.status = status;
    this.code = body?.type?.split('/').pop() ?? null; // "not_found", "rate_limit_exceeded", etc.
    this.body = body;
  }

  get isNotFound() { return this.status === 404; }
  get isValidation() { return this.status === 422 || this.status === 400; }
  get isRateLimit() { return this.status === 429; }
  get isServerError() { return this.status >= 500; }

  get fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.body?.detail)) return {};
    return this.body.detail.reduce((acc: Record<string, string>, err: any) => {
      const field = err.loc?.[err.loc.length - 1];
      if (field) acc[field] = err.msg;
      return acc;
    }, {});
  }

  get retryAfter(): number | null {
    return this.body?.retry_after ?? null;
  }
}
```

---

## 4. API: Категории

### 4.1 Список категорий (дерево)

```
GET /api/v1/public/categories?tenant_id={uuid}
```

**Параметры:**
| Параметр | Тип | Обяз. | Описание |
|----------|-----|-------|----------|
| `tenant_id` | UUID | Да | ID тенанта |

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Электрооборудование",
      "slug": "electrical",
      "parent_id": null,
      "description": "Всё для электрики",
      "image_url": "https://cdn.example.com/categories/electrical.jpg"
    },
    {
      "id": "...",
      "title": "Кабели и провода",
      "slug": "cables",
      "parent_id": "550e8400-e29b-41d4-a716-446655440000",
      "description": null,
      "image_url": null
    }
  ],
  "total": 12
}
```

**Коды ответа:**
| Код | Описание |
|-----|----------|
| 200 | Список категорий |
| 400 | `tenant_id` не передан или невалидный |
| 404 | Тенант не найден или каталог выключен |

**Построение дерева на фронте:**
```typescript
interface Category {
  id: string;
  title: string;
  slug: string;
  parent_id: string | null;
  description: string | null;
  image_url: string | null;
}

interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[];
}

const buildTree = (categories: Category[]): CategoryTreeNode[] => {
  const map = new Map<string, CategoryTreeNode>();
  const roots: CategoryTreeNode[] = [];

  categories.forEach(cat => map.set(cat.id, { ...cat, children: [] }));

  map.forEach(node => {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  });

  return roots;
};
```

---

### 4.2 Категория + продукты

```
GET /api/v1/public/categories/{slug}?tenant_id={uuid}&page=1&page_size=20
```

**Параметры:**
| Параметр | Тип | Обяз. | Описание |
|----------|-----|-------|----------|
| `slug` | string (path) | Да | URL-slug категории |
| `tenant_id` | UUID | Да | ID тенанта |
| `page` | int | Нет | Страница (default 1) |
| `page_size` | int | Нет | Размер (default 20, max 100) |

**Ответ 200:**
```json
{
  "category": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Электрооборудование",
    "slug": "electrical",
    "parent_id": null,
    "description": "Всё для электрики",
    "image_url": "https://cdn.example.com/categories/electrical.jpg"
  },
  "products": {
    "items": [
      {
        "id": "uuid",
        "slug": "widget-pro-2000",
        "sku": "WP-2000",
        "title": "Widget Pro 2000",
        "brand": "WidgetCorp",
        "model": "Pro-2000",
        "description": "Краткое описание",
        "cover_url": "https://cdn.example.com/products/wp2000/cover.jpg",
        "product_type": "physical",
        "has_variants": false,
        "price_from": "15000.00",
        "price_to": "15000.00"
      }
    ],
    "total": 24,
    "page": 1,
    "page_size": 20
  }
}
```

**Коды ответа:**
| Код | Описание |
|-----|----------|
| 200 | Категория с продуктами |
| 400 | `tenant_id` не передан |
| 404 | Категория с таким slug не найдена, или каталог выключен |

---

## 5. API: Фильтры каталога (фасетная навигация)

```
GET /api/v1/public/filters?tenant_id={uuid}
```

Возвращает доступные фильтры с динамическими счётчиками. При выборе одного фильтра счётчики в остальных фасетах автоматически пересчитываются (показывают только товары, совместимые с выбором).

**Параметры:**
| Параметр | Тип | Обяз. | Описание |
|----------|-----|-------|----------|
| `tenant_id` | UUID | Да | ID тенанта |
| `category` | string | Нет | Slug категории или несколько через запятую: `electronics,clothing` |
| `price_min` | decimal | Нет | Минимальная цена |
| `price_max` | decimal | Нет | Максимальная цена |
| `{parameter_slug}` | string | Нет | Фильтр по параметру: `color=red,blue` |

> **Динамические параметры**: Любой query-параметр, не входящий в `tenant_id`, `category`, `price_min`, `price_max`, `page`, `page_size` — считается фильтром по slug параметра. Значения через запятую.

**Ответ 200:**
```json
{
  "filters": [
    {
      "slug": "color",
      "name": "Цвет",
      "type": "enum",
      "values": [
        { "slug": "red", "label": "Красный", "count": 15 },
        { "slug": "blue", "label": "Синий", "count": 8 },
        { "slug": "green", "label": "Зелёный", "count": 3 }
      ],
      "uom": null,
      "min": null,
      "max": null
    },
    {
      "slug": "weight",
      "name": "Вес",
      "type": "number",
      "values": [],
      "uom": { "code": "kg", "symbol": "кг" },
      "min": 0.5,
      "max": 25.0
    }
  ],
  "price_range": { "min": 100.00, "max": 50000.00, "currency": "RUB" },
  "total_products": 48
}
```

### Алгоритм пересчёта фасетных счётчиков

При выбранном фильтре `color=red`:
- `count` каждого значения в фильтре **"Материал"** — количество товаров с `color=red` И данным материалом
- `count` каждого значения в фильтре **"Цвет"** — количество товаров с данным цветом (без учёта цветового фильтра, чтобы показать альтернативы)
- Фильтры без подходящих товаров автоматически скрываются

### UX-паттерны

```typescript
// 1. При изменении фильтра — параллельные запросы:
const onFilterChange = async (filters: SelectedFilters) => {
  const [filtersData, productsData] = await Promise.all([
    api.get<FiltersResponse>('/public/filters', buildFilterParams(filters)),
    api.get<ProductListResponse>('/public/products', { ...buildFilterParams(filters), page: '1' }),
  ]);
  // Обновить и список фильтров, и товары
};

// 2. Построение query-параметров из selected filters:
const buildFilterParams = (filters: SelectedFilters): Record<string, string> => {
  const params: Record<string, string> = {};
  if (filters.categories.length) params.category = filters.categories.join(',');
  if (filters.priceMin) params.price_min = filters.priceMin.toString();
  if (filters.priceMax) params.price_max = filters.priceMax.toString();
  for (const [slug, values] of Object.entries(filters.params)) {
    if (values.length) params[slug] = values.join(',');
  }
  return params;
};
```

**Коды ответа:**
| Код | Описание |
|-----|----------|
| 200 | Фильтры с фасетными счётчиками |
| 400 | `tenant_id` не передан |
| 404 | Тенант не найден или каталог выключен |

---

## 6. API: Список продуктов (с фильтрацией и сортировкой)

```
GET /api/v1/public/products?tenant_id={uuid}
```

**Параметры:**
| Параметр | Тип | Обяз. | Описание |
|----------|-----|-------|----------|
| `tenant_id` | UUID | Да | ID тенанта |
| `page` | int | Нет | Страница (default 1) |
| `page_size` | int | Нет | Элементов на странице (default 20, max 100) |
| `search` | string | Нет | Поиск по title, sku, brand (max 200 символов) |
| `brand` | string | Нет | Фильтр по бренду (подстрока, max 255) |
| `category` | string | Нет | Slug категории (или несколько через запятую: `electronics,clothing`) |
| `price_min` | decimal | Нет | Минимальная цена |
| `price_max` | decimal | Нет | Максимальная цена |
| `sort` | string | Нет | Сортировка: `price_asc`, `price_desc`, `newest`, `title_asc`, `title_desc` (default `newest`) |
| `{parameter_slug}` | string | Нет | Фильтр по параметру: `color=red,blue` |

> **Фильтрация по характеристикам**: Используй slug параметра как ключ query-параметра, slug значений через запятую. Пример: `?color=red,blue&material=metal` — товары, которые красные ИЛИ синие, И при этом из металла.

**Ответ 200:**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "slug": "widget-pro-2000",
      "sku": "WP-2000",
      "title": "Widget Pro 2000",
      "brand": "WidgetCorp",
      "model": "Pro-2000",
      "description": "Профессиональный виджет",
      "cover_url": "https://cdn.example.com/products/wp2000/cover.jpg",
      "product_type": "physical",
      "has_variants": true,
      "price_from": "12000.00",
      "price_to": "25000.00"
    }
  ],
  "total": 48,
  "page": 1,
  "page_size": 20
}
```

> **Важно**: В списке НЕ отдаются изображения, характеристики, цены. Только `cover_url` — URL обложки (первое изображение с `is_cover=true`, или первое изображение по порядку, или `null`).

> **Новые поля**:
> - `product_type` — тип продукта: `physical`, `digital`, `service`, `course`, `subscription`
> - `has_variants` — есть ли у товара варианты/тарифы
> - `price_from` / `price_to` — денормализованный диапазон цен (минимальная и максимальная цена среди всех вариантов). `null` если цены не заданы. Для товаров без вариантов равны основной цене.

### Логика фильтрации

- Фильтры по **разным параметрам** — AND (пересечение): `color=red&material=metal` → товары красные И металлические
- Фильтры **внутри одного параметра** — OR (объединение): `color=red,blue` → товары красные ИЛИ синие
- Фильтры по **нескольким категориям** — OR: `category=electronics,clothing` → товары в любой из категорий

### Сортировка по цене

Сортировка `price_asc` / `price_desc` использует текущую `regular` цену (действующую по дате). Товары без цены отображаются в конце.

**Коды ответа:**
| Код | Описание |
|-----|----------|
| 200 | Пагинированный список продуктов |
| 400 | `tenant_id` не передан, или невалидные параметры |
| 404 | Тенант не найден или каталог выключен |
| 422 | `page_size` > 100, `search` > 200, или невалидный `sort` |

---

## 7. API: Карточка продукта

```
GET /api/v1/public/products/{slug}?tenant_id={uuid}&locale=ru
```

**Параметры:**
| Параметр | Тип | Обяз. | Описание |
|----------|-----|-------|----------|
| `slug` | string (path) | Да | URL-slug продукта |
| `tenant_id` | UUID | Да | ID тенанта |
| `locale` | string | Нет | Фильтр контент-блоков по локали (`ru`, `en`, `kz`) |

**Ответ 200:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "slug": "widget-pro-2000",
  "sku": "WP-2000",
  "title": "Widget Pro 2000",
  "brand": "WidgetCorp",
  "model": "Pro-2000",
  "description": "Полное описание товара в HTML или plain text",
  "product_type": "physical",
  "has_variants": true,
  "price_from": "12000.00",
  "price_to": "25000.00",

  "images": [
    {
      "id": "img-uuid-1",
      "url": "https://cdn.example.com/products/wp2000/main.jpg",
      "alt": "Widget Pro 2000 — вид спереди",
      "width": 1200,
      "height": 800,
      "sort_order": 0,
      "is_cover": true
    },
    {
      "id": "img-uuid-2",
      "url": "https://cdn.example.com/products/wp2000/side.jpg",
      "alt": "Widget Pro 2000 — вид сбоку",
      "width": 1200,
      "height": 800,
      "sort_order": 1,
      "is_cover": false
    }
  ],

  "characteristics": [
    {
      "parameter_slug": "voltage",
      "parameter_name": "Напряжение",
      "type": "number",
      "values": [],
      "value_text": "220",
      "value_number": 220,
      "value_bool": null,
      "uom": { "code": "V", "symbol": "В" }
    },
    {
      "parameter_slug": "color",
      "parameter_name": "Цвет",
      "type": "enum",
      "values": [
        { "slug": "red", "label": "Красный" }
      ],
      "value_text": null,
      "value_number": null,
      "value_bool": null,
      "uom": null
    },
    {
      "parameter_slug": "weight",
      "parameter_name": "Вес",
      "type": "number",
      "values": [],
      "value_text": null,
      "value_number": 2.5,
      "value_bool": null,
      "uom": { "code": "kg", "symbol": "кг" }
    }
  ],

  "chars": [
    { "name": "Напряжение", "value_text": "220 В" },
    { "name": "Цвет", "value_text": "Красный" },
    { "name": "Вес", "value_text": "2.5 кг" }
  ],

  "categories": [
    {
      "id": "cat-uuid-1",
      "title": "Электрооборудование",
      "slug": "electrical",
      "parent_id": null,
      "description": null,
      "image_url": null
    }
  ],

  "prices": [
    { "price_type": "regular", "amount": "15000.00", "currency": "RUB" },
    { "price_type": "sale", "amount": "12000.00", "currency": "RUB" }
  ],

  "content_blocks": [
    {
      "id": "block-uuid-1",
      "locale": "ru",
      "block_type": "text",
      "sort_order": 0,
      "title": "Описание",
      "content": "<p>Расширенное описание с HTML-форматированием, таблицами, списками</p>",
      "media_url": null,
      "thumbnail_url": null,
      "link_url": null,
      "link_label": null,
      "device_type": "both",
      "block_metadata": null
    },
    {
      "id": "block-uuid-2",
      "locale": "ru",
      "block_type": "image",
      "sort_order": 1,
      "title": null,
      "content": null,
      "media_url": "https://cdn.example.com/products/wp2000/diagram.png",
      "thumbnail_url": null,
      "link_url": null,
      "link_label": null,
      "device_type": "both",
      "block_metadata": {
        "alt": "Техническая схема Widget Pro 2000",
        "caption": "Рис. 1 — Габаритная схема"
      }
    },
    {
      "id": "block-uuid-3",
      "locale": "ru",
      "block_type": "video",
      "sort_order": 2,
      "title": "Видеообзор",
      "content": null,
      "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
      "link_url": null,
      "link_label": null,
      "device_type": "both",
      "block_metadata": {
        "provider": "youtube",
        "embed_id": "dQw4w9WgXcQ"
      }
    },
    {
      "id": "block-uuid-4",
      "locale": "ru",
      "block_type": "link",
      "sort_order": 3,
      "title": null,
      "content": null,
      "media_url": null,
      "thumbnail_url": null,
      "link_url": "https://example.com/docs/wp2000-manual.pdf",
      "link_label": "Скачать инструкцию (PDF)",
      "device_type": "both",
      "block_metadata": { "icon": "download" }
    }
  ],

  "option_groups": [
    {
      "title": "Цвет",
      "slug": "color",
      "display_type": "color_swatch",
      "values": [
        { "title": "Красный", "slug": "red", "color_hex": "#FF0000", "image_url": null },
        { "title": "Синий", "slug": "blue", "color_hex": "#0000FF", "image_url": null }
      ]
    },
    {
      "title": "Размер",
      "slug": "size",
      "display_type": "buttons",
      "values": [
        { "title": "S", "slug": "s", "color_hex": null, "image_url": null },
        { "title": "M", "slug": "m", "color_hex": null, "image_url": null },
        { "title": "L", "slug": "l", "color_hex": null, "image_url": null }
      ]
    }
  ],

  "variants": [
    {
      "id": "variant-uuid-1",
      "slug": "widget-pro-2000-red-s",
      "title": "Widget Pro 2000 — Красный, S",
      "sku": "WP-2000-RED-S",
      "description": null,
      "is_default": true,
      "in_stock": true,
      "sort_order": 0,
      "prices": [
        { "price_type": "regular", "amount": "15000.00", "currency": "RUB" },
        { "price_type": "sale", "amount": "12000.00", "currency": "RUB" }
      ],
      "options": { "color": "red", "size": "s" },
      "images": [
        { "url": "https://cdn.example.com/variants/red-s.jpg", "alt": "Красный S", "sort_order": 0, "is_cover": true }
      ],
      "inclusions": []
    }
  ]
}
```

**Коды ответа:**
| Код | Описание |
|-----|----------|
| 200 | Полная карточка продукта |
| 400 | `tenant_id` не передан |
| 404 | Продукт с таким slug не найден, или каталог выключен |

### Поля ответа — детальное описание

| Поле | Тип | Всегда есть | Описание |
|------|-----|:-----------:|----------|
| `id` | UUID | ✅ | Уникальный ID товара |
| `slug` | string | ✅ | URL-slug (`/products/{slug}`) |
| `sku` | string | ✅ | Артикул |
| `title` | string | ✅ | Название |
| `brand` | string \| null | ❌ | Бренд/производитель |
| `model` | string \| null | ❌ | Модель |
| `description` | string \| null | ❌ | Краткое описание (plain text / HTML) |
| `product_type` | string | ✅ | Тип продукта: `physical`, `digital`, `service`, `course`, `subscription` |
| `has_variants` | boolean | ✅ | Есть ли варианты/тарифы |
| `price_from` | string \| null | ❌ | Денормализованная мин. цена (по всем вариантам) |
| `price_to` | string \| null | ❌ | Денормализованная макс. цена (по всем вариантам) |
| `images` | array | ✅ | Изображения (может быть `[]`) |
| `characteristics` | array | ✅ | Нормализованные характеристики (slug, type, values/number/text) |
| `chars` | array | ✅ | Упрощённые характеристики `{name, value_text}` — backward compat |
| `categories` | array | ✅ | Привязанные категории (может быть `[]`) |
| `prices` | array | ✅ | Цены (может быть `[]`) |
| `content_blocks` | array | ✅ | Контент-блоки (может быть `[]`) |
| `option_groups` | array \| null | ❌ | Группы опций (только если `has_variants=true` и `variants_module` включён) |
| `variants` | array \| null | ❌ | Варианты товара (только если `has_variants=true` и `variants_module` включён) |

### Типы контент-блоков — как рендерить

| `block_type` | Какие поля используются | Как рендерить |
|--------------|------------------------|---------------|
| `text` | `title`, `content` (HTML) | Заголовок + HTML-контент через `dangerouslySetInnerHTML` |
| `image` | `media_url`, `block_metadata.alt`, `block_metadata.caption` | `<img>` с alt-текстом и подписью |
| `video` | `media_url`, `thumbnail_url`, `block_metadata.provider`, `block_metadata.embed_id` | YouTube/Vimeo iframe или `<video>` для custom |
| `gallery` | `block_metadata.images[]` (массив `{url, alt}`) | Слайдер / lightbox с изображениями |
| `link` | `link_url`, `link_label`, `block_metadata.icon` | Кнопка-ссылка |
| `result` | `title`, `content`, `media_url` | Комбинированный блок (кейс/результат) |

### Поле `device_type` — адаптивность

| Значение | Описание |
|----------|----------|
| `both` | Показывать на всех устройствах |
| `mobile` | Только на мобильных (< 768px) |
| `desktop` | Только на десктопе (>= 768px) |

```typescript
const shouldShowBlock = (block: ContentBlock, isMobile: boolean) => {
  if (block.device_type === 'both' || block.device_type === null) return true;
  if (block.device_type === 'mobile') return isMobile;
  if (block.device_type === 'desktop') return !isMobile;
  return true;
};
```

### Цены — как показывать

```typescript
const PRICE_LABELS: Record<string, string> = {
  regular: 'Цена',
  sale: 'Акция',
  wholesale: 'Оптом',
  cost: 'Себестоимость', // обычно не показывают клиентам
};

const formatPrice = (amount: string, currency: string) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
  }).format(Number(amount));
};

// Логика отображения:
// 1. Если есть sale — показать перечёркнутую regular + жирную sale
// 2. Если только regular — показать обычную цену
// 3. wholesale — показать отдельно: "Оптом: ..."
// 4. cost — не показывать клиентам
```

---

## 8. Варианты и тарифы на карточке товара

> **Feature flag**: `variants_module` — если включён, у товаров с `has_variants=true` в ответе карточки появляются `option_groups` и `variants`. Если модуль выключен — эти поля приходят как `null`.

### 8.1 Когда отображать варианты

Варианты рендерятся на карточке товара когда **одновременно**:
- `has_variants === true`
- `option_groups !== null && option_groups.length > 0`
- `variants !== null && variants.length > 0`

Если `has_variants=false` — товар простой, показывай цены из `prices[]` напрямую.

### 8.2 Структура данных

**option_groups[]** — группы опций для построения UI-селекторов:

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | string | Название группы («Цвет», «Размер», «Тариф») |
| `slug` | string | Slug для маппинга к `variants[].options` |
| `display_type` | string | Тип отображения: `dropdown`, `buttons`, `color_swatch`, `cards` |
| `values[]` | array | Список значений |
| `values[].title` | string | Отображаемое название значения |
| `values[].slug` | string | Slug значения (ключ в `variants[].options`) |
| `values[].color_hex` | string \| null | HEX-цвет для `color_swatch` |
| `values[].image_url` | string \| null | URL изображения для `cards` |

**variants[]** — конкретные варианты товара:

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Уникальный ID варианта |
| `slug` | string | URL-slug варианта |
| `title` | string | Название варианта |
| `sku` | string | Артикул варианта |
| `description` | string \| null | Описание варианта |
| `is_default` | boolean | Вариант по умолчанию (выбрать при загрузке) |
| `in_stock` | boolean | В наличии |
| `sort_order` | number | Порядок сортировки |
| `prices[]` | array | Цены варианта (`price_type`, `amount`, `currency`) |
| `options` | object | Маппинг `{group_slug: value_slug}`, напр. `{"color": "red", "size": "s"}` |
| `images[]` | array | Изображения варианта (`url`, `alt`, `sort_order`, `is_cover`) |
| `inclusions[]` | array | Состав/включения для тарифных сравнений |

**inclusions[]** — что входит в вариант (для тарифных планов):

| Поле | Тип | Описание |
|------|-----|----------|
| `title` | string | Название пункта |
| `description` | string \| null | Дополнительное описание |
| `is_included` | boolean | Входит ли в данный вариант |
| `icon` | string \| null | Иконка (slug или URL) |
| `group` | string \| null | Группировка пунктов (для визуального разделения) |

### 8.3 Логика выбора варианта (Variant Selector)

```typescript
// 1. Построить UI из option_groups
// Каждая группа → отдельный селектор в зависимости от display_type:
//   - dropdown   → <select>
//   - buttons    → набор кнопок
//   - color_swatch → цветные кружки (color_hex)
//   - cards      → карточки с изображением (image_url)

// 2. При выборе опции — найти допустимые комбинации
const findMatchingVariants = (
  variants: VariantPublic[],
  selected: Record<string, string>
): VariantPublic[] => {
  return variants.filter(v =>
    Object.entries(selected).every(([group, value]) => v.options[group] === value)
  );
};

// 3. Определить доступные значения для остальных групп
const getAvailableValues = (
  variants: VariantPublic[],
  selected: Record<string, string>,
  groupSlug: string
): Set<string> => {
  const otherSelections = { ...selected };
  delete otherSelections[groupSlug];

  const compatible = variants.filter(v => {
    if (!v.in_stock) return false;
    return Object.entries(otherSelections).every(([g, val]) => v.options[g] === val);
  });

  return new Set(compatible.map(v => v.options[groupSlug]));
};

// 4. Начальное состояние — выбрать вариант с is_default=true
const defaultVariant = variants.find(v => v.is_default) ?? variants[0];
const initialSelection = defaultVariant.options; // {"color": "red", "size": "s"}
```

**UX-правила:**
- При загрузке выбирается вариант с `is_default=true` (или первый)
- Недоступные комбинации (нет варианта) — визуально отключить (disabled)
- Варианты с `in_stock=false` — показывать с пометкой «Нет в наличии»
- При выборе варианта — переключить галерею на `variant.images[]` (если непустой), иначе показывать `product.images[]`

### 8.4 Правила отображения цен

**Простой товар** (`has_variants=false`):
- Показывать `prices[]` из основного объекта продукта
- Логика sale/regular — как в разделе 7

**Товар с вариантами** (`has_variants=true`):
- **В списке (каталог):** показывать «от {price_from}» если `price_from !== price_to`, иначе показывать точную цену
- **На карточке до выбора варианта:** показывать диапазон «от {price_from} до {price_to}» или цену дефолтного варианта
- **На карточке после выбора варианта:** показывать `variant.prices[]` выбранного варианта

```typescript
const formatVariantPrice = (product: ProductDetail, selectedVariant?: VariantPublic) => {
  if (!product.has_variants) {
    return formatProductPrices(product.prices);
  }

  if (selectedVariant) {
    return formatProductPrices(selectedVariant.prices);
  }

  if (product.price_from && product.price_to) {
    if (product.price_from === product.price_to) {
      return formatPrice(product.price_from, 'RUB');
    }
    return `от ${formatPrice(product.price_from, 'RUB')}`;
  }

  return 'Цена по запросу';
};
```

### 8.5 Таблица сравнения тарифов (Inclusions)

Когда у вариантов заполнены `inclusions[]`, можно построить сравнительную таблицу тарифов:

```typescript
const buildComparisonGrid = (variants: VariantPublic[]) => {
  const allInclusions = new Map<string, { title: string; group: string | null; icon: string | null }>();

  for (const v of variants) {
    for (const inc of v.inclusions) {
      if (!allInclusions.has(inc.title)) {
        allInclusions.set(inc.title, { title: inc.title, group: inc.group, icon: inc.icon });
      }
    }
  }

  const rows = Array.from(allInclusions.values());

  // Группировка по group
  const grouped = new Map<string | null, typeof rows>();
  for (const row of rows) {
    const key = row.group ?? '__ungrouped__';
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(row);
  }

  return { grouped, variants };
};

// Рендер ячейки:
// inclusion найден у варианта → is_included ? ✓ : ✗
// inclusion не найден → ✗
const getCellValue = (variant: VariantPublic, inclusionTitle: string): boolean => {
  const inc = variant.inclusions.find(i => i.title === inclusionTitle);
  return inc?.is_included ?? false;
};
```

**Визуальное представление:**

| Функция | Базовый | Про | Бизнес |
|---------|:-------:|:---:|:------:|
| **Основное** | | | |
| Доступ к API | ✓ | ✓ | ✓ |
| Техподдержка | ✗ | ✓ | ✓ |
| **Расширенное** | | | |
| Приоритетная поддержка | ✗ | ✗ | ✓ |
| SLA 99.9% | ✗ | ✗ | ✓ |

- Строки группируются по `inclusion.group`
- Для каждой группы — заголовок-разделитель
- В ячейке: `is_included=true` → галочка (✓), `is_included=false` → крестик (✗)
- Если `inclusion.description` не пустое — показать тултипом или подстрокой

---

## 9. ЧПУ-спецификация (SEO-friendly URLs)

### Формат URL фильтрованных страниц

```
/catalog/{category-slug}/{parameter-slug}--{value-slug}/{parameter-slug}--{value-slug}
```

**Примеры:**
```
/catalog/electronics                       → все товары категории "electronics"
/catalog/electronics/color--red            → электроника красного цвета
/catalog/electronics/color--red/brand--apple  → красная электроника Apple
/catalog/color--red                        → все товары красного цвета (без категории)
```

### Маппинг URL → Query параметры

```typescript
// URL: /catalog/electronics/color--red/material--metal
// → API: GET /public/products?category=electronics&color=red&material=metal

const parseFilterUrl = (segments: string[]): Record<string, string> => {
  const params: Record<string, string> = {};
  const filterSegments: string[] = [];
  let categorySlug: string | null = null;

  for (const seg of segments) {
    if (seg.includes('--')) {
      filterSegments.push(seg);
    } else if (!categorySlug) {
      categorySlug = seg;
    }
  }

  if (categorySlug) params.category = categorySlug;

  for (const filterSeg of filterSegments) {
    const [paramSlug, valueSlug] = filterSeg.split('--', 2);
    if (paramSlug && valueSlug) {
      if (params[paramSlug]) {
        params[paramSlug] += `,${valueSlug}`;
      } else {
        params[paramSlug] = valueSlug;
      }
    }
  }

  return params;
};

// Обратное преобразование: query → ЧПУ-путь
const buildFilterUrl = (category?: string, filters?: Record<string, string[]>): string => {
  const parts = ['/catalog'];
  if (category) parts.push(category);

  if (filters) {
    const sortedKeys = Object.keys(filters).sort();
    for (const key of sortedKeys) {
      for (const val of filters[key].sort()) {
        parts.push(`${key}--${val}`);
      }
    }
  }

  return parts.join('/');
};
```

### Next.js App Router интеграция

```typescript
// app/catalog/[...segments]/page.tsx
export default async function CatalogPage({
  params,
}: {
  params: { segments: string[] };
}) {
  const filterParams = parseFilterUrl(params.segments);
  const [filters, products] = await Promise.all([
    fetchFilters(filterParams),
    fetchProducts(filterParams),
  ]);

  return <CatalogView filters={filters} products={products} />;
}
```

---

## 10. SEO: Генерация страниц фильтров

```
GET /api/v1/public/seo/filter-pages?tenant_id={uuid}
```

Генерирует список комбинаций фильтров для sitemap. Включает одиночные и парные комбинации параметров.

**Параметры:**
| Параметр | Тип | Обяз. | Описание |
|----------|-----|-------|----------|
| `tenant_id` | UUID | Да | ID тенанта |
| `category` | string | Нет | Slug категории (ограничить генерацию одной категорией) |
| `min_products` | int | Нет | Минимум товаров для включения страницы (default 1) |
| `page` | int | Нет | Страница (default 1) |
| `page_size` | int | Нет | Элементов на странице (default 100, max 100) |

**Ответ 200:**
```json
{
  "pages": [
    {
      "category_slug": "electronics",
      "filters": [
        { "parameter_slug": "color", "value_slug": "red" }
      ],
      "product_count": 15,
      "url_path": "/catalog/electronics/color--red"
    },
    {
      "category_slug": "electronics",
      "filters": [
        { "parameter_slug": "color", "value_slug": "red" },
        { "parameter_slug": "brand", "value_slug": "apple" }
      ],
      "product_count": 8,
      "url_path": "/catalog/electronics/color--red/brand--apple"
    }
  ],
  "total": 156
}
```

### Использование для sitemap

```typescript
// scripts/generate-sitemap.ts
const generateFilterSitemap = async (tenantId: string): Promise<string[]> => {
  const urls: string[] = [];
  let page = 1;

  while (true) {
    const res = await fetch(
      `${API_URL}/public/seo/filter-pages?tenant_id=${tenantId}&page=${page}&page_size=100&min_products=3`
    );
    const data = await res.json();

    for (const p of data.pages) {
      urls.push(`https://example.com${p.url_path}`);
    }

    if (urls.length >= data.total) break;
    page++;
  }

  return urls;
};
```

---

## 11. API: Заявка на продукт

```
POST /api/v1/public/inquiries?tenant_id={uuid}
Content-Type: application/json
```

### Тело запроса

```json
{
  "form_slug": "quick",
  "name": "Иван Петров",
  "email": "ivan@example.com",
  "phone": "+7 999 123-45-67",
  "message": "Хочу уточнить наличие и сроки доставки",
  "product_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "consent": true,
  "analytics": {
    "utm_source": "google",
    "utm_medium": "cpc",
    "source_url": "https://example.com/products/widget-pro-2000",
    "page_path": "/products/widget-pro-2000",
    "page_title": "Widget Pro 2000 — купить",
    "user_agent": "Mozilla/5.0...",
    "session_id": "abc123"
  }
}
```

### Поля запроса

| Поле | Тип | Обяз. | Ограничения | Описание |
|------|-----|:-----:|-------------|----------|
| `form_slug` | string | Нет* | max 100 | Идентификатор формы: `"quick"` или `"mvp-brief"` |
| `name` | string | **Да** | 1–255 | Имя клиента |
| `email` | email | Нет | Валидный email | Электронная почта |
| `phone` | string | Нет | max 50 | Телефон |
| `company` | string | Нет | max 255 | Компания |
| `message` | string | **Да*** | — | Сообщение (обяз. для `form_slug=quick`) |
| `telegram` | string | Нет | max 255 | Telegram username |
| `consent` | boolean | Нет | — | Согласие на обработку ПД |
| `product_id` | UUID | Нет | Валидный UUID товара | ID товара, на который заявка |
| `service_id` | UUID | Нет | Валидный UUID услуги | ID услуги (альтернатива product_id) |
| `analytics` | object | Нет | — | UTM-метки и аналитика |
| `custom_fields` | object | Нет | — | Произвольные поля |

> **`*`** Если `form_slug = "quick"` → `message` обязательно.  
> Если `form_slug = "mvp-brief"` → `idea` обязательно (вместо message).

### Поля analytics

| Поле | Тип | Описание |
|------|-----|----------|
| `utm_source` | string | UTM source |
| `utm_medium` | string | UTM medium |
| `utm_campaign` | string | UTM campaign |
| `utm_term` | string | UTM term |
| `utm_content` | string | UTM content |
| `referrer_url` | string | Откуда перешёл (max 2000) |
| `source_url` | string | URL страницы отправки (max 2000) |
| `page_path` | string | Путь на сайте (max 500) |
| `page_title` | string | Заголовок страницы (max 500) |
| `user_agent` | string | User-Agent браузера (max 500) |
| `device_type` | string | `"mobile"` / `"desktop"` / `"tablet"` (max 20) |
| `browser` | string | Название браузера (max 100) |
| `os` | string | Операционная система (max 100) |
| `screen_resolution` | string | `"1920x1080"` (max 20) |
| `session_id` | string | ID сессии (max 100) |
| `session_page_views` | int | Просмотров за сессию |
| `time_on_page` | int | Секунд на странице |

### Ответ 201

```json
{
  "id": "inquiry-uuid",
  "tenant_id": "tenant-uuid",
  "form_id": "form-uuid",
  "form_slug": "quick",
  "name": "Иван Петров",
  "email": "ivan@example.com",
  "phone": "+7 999 123-45-67",
  "company": null,
  "message": "Хочу уточнить наличие и сроки доставки",
  "status": "new",
  "product_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "product": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "slug": "widget-pro-2000",
    "sku": "WP-2000",
    "name": "Widget Pro 2000"
  },
  "source": "website",
  "ip_address": "185.12.34.56",
  "custom_fields": null,
  "analytics": { "utm_source": "google", "..." : "..." },
  "assigned_to": null,
  "notes": null,
  "created_at": "2026-02-24T12:00:00Z",
  "updated_at": "2026-02-24T12:00:00Z"
}
```

### Коды ответа

| Код | Описание | Когда |
|-----|----------|-------|
| 201 | Заявка создана | Успех |
| 400 | Ошибка валидации | `tenant_id` не передан |
| 404 | Не найдено | Тенант или product_id не найден |
| 422 | Ошибка валидации полей | `name` пустое, `email` невалидный, `message` пустое для `quick` |
| 429 | Rate limit | > 3 заявок в минуту с одного IP |

### Альтернативный формат: multipart/form-data

Для форм с файлами используй альтернативный эндпоинт:

```
POST /api/v1/public/inquiries/upload?tenant_id={uuid}
Content-Type: multipart/form-data
```

Те же поля, но как `FormData`:

```typescript
const submitInquiryMultipart = async (data: InquiryForm, files?: File[]) => {
  const formData = new FormData();
  formData.append('form_slug', 'quick');
  formData.append('name', data.name);
  if (data.email) formData.append('email', data.email);
  if (data.phone) formData.append('phone', data.phone);
  if (data.message) formData.append('message', data.message);
  if (data.productId) formData.append('product_id', data.productId);
  formData.append('consent', 'true');

  if (data.analytics) {
    formData.append('analytics', JSON.stringify(data.analytics));
  }

  files?.forEach(file => formData.append('files', file));

  const url = `/api/v1/public/inquiries/upload?tenant_id=${tenantId}`;
  const res = await fetch(url, { method: 'POST', body: formData });
  // НЕ устанавливай Content-Type — браузер сам добавит boundary
  if (!res.ok) throw new ApiError(res.status, await res.json());
  return res.json();
};
```

---

## 12. Rate Limiting

Публичные API имеют rate limiting по IP:

| Эндпоинт | Лимит | Окно |
|----------|-------|------|
| `GET /public/*` | 100 запросов | 1 минута |
| `POST /public/inquiries` | 3 запроса | 1 минута |
| `POST /public/inquiries/upload` | 3 запроса | 1 минута |

### Заголовки ответа

Каждый ответ содержит rate limit headers:

```
X-RateLimit-Limit: 100          // Максимум запросов
X-RateLimit-Remaining: 97       // Осталось запросов
X-RateLimit-Reset: 45           // Секунд до сброса лимита
```

### Обработка 429

```typescript
const submitWithRetry = async (data: InquiryForm) => {
  try {
    return await submitInquiry(data);
  } catch (err) {
    if (err instanceof ApiError && err.isRateLimit) {
      const retryAfter = err.retryAfter ?? 60;
      showToast(`Слишком много запросов. Попробуйте через ${retryAfter} сек.`);
      return null;
    }
    throw err;
  }
};
```

---

## 13. TypeScript-типы

```typescript
// =============================================
// Catalog — публичные типы (copy-paste ready)
// =============================================

// ---------- Категории ----------

interface CategoryPublic {
  id: string;
  title: string;
  slug: string;
  parent_id: string | null;
  description: string | null;
  image_url: string | null;
}

interface CategoryTreeResponse {
  items: CategoryPublic[];
  total: number;
}

interface CategoryTreeNode extends CategoryPublic {
  children: CategoryTreeNode[];
}

// ---------- Продукты (список) ----------

interface ProductPublic {
  id: string;
  slug: string;
  sku: string;
  title: string;
  brand: string | null;
  model: string | null;
  description: string | null;
  cover_url: string | null;
  product_type: 'physical' | 'digital' | 'service' | 'course' | 'subscription';
  has_variants: boolean;
  price_from: string | null;
  price_to: string | null;
}

interface ProductListResponse {
  items: ProductPublic[];
  total: number;
  page: number;
  page_size: number;
}

// ---------- Продукт (детали) ----------

interface ProductImage {
  id: string;
  url: string;
  alt: string | null;
  width: number | null;
  height: number | null;
  sort_order: number;
  is_cover: boolean;
}

interface ProductChar {
  name: string;
  value_text: string;
}

interface UOMPublic {
  code: string;
  symbol: string | null;
}

interface CharacteristicValue {
  slug: string;
  label: string;
}

interface ProductCharacteristic {
  parameter_slug: string;
  parameter_name: string;
  type: 'enum' | 'number' | 'string' | 'bool' | 'range';
  values: CharacteristicValue[];
  value_text: string | null;
  value_number: number | null;
  value_bool: boolean | null;
  uom: UOMPublic | null;
}

// ---------- Фильтры (фасетная навигация) ----------

interface FilterValue {
  slug: string;
  label: string;
  count: number;
}

interface FilterParameter {
  slug: string;
  name: string;
  type: 'enum' | 'number' | 'range';
  values: FilterValue[];
  uom: UOMPublic | null;
  min: number | null;
  max: number | null;
}

interface PriceRange {
  min: number | null;
  max: number | null;
  currency: string;
}

interface FiltersResponse {
  filters: FilterParameter[];
  price_range: PriceRange;
  total_products: number;
}

// ---------- SEO ----------

interface SeoFilterItem {
  parameter_slug: string;
  value_slug: string;
}

interface SeoFilterPage {
  category_slug: string | null;
  filters: SeoFilterItem[];
  product_count: number;
  url_path: string;
}

interface SeoFilterPagesResponse {
  pages: SeoFilterPage[];
  total: number;
}

// ---------- Выбранные фильтры (client state) ----------

interface SelectedFilters {
  categories: string[];
  priceMin?: number;
  priceMax?: number;
  params: Record<string, string[]>;
  sort: 'price_asc' | 'price_desc' | 'newest' | 'title_asc' | 'title_desc';
}

interface ProductPrice {
  price_type: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: string;    // decimal в строке: "15000.00"
  currency: string;  // "RUB", "USD", "EUR"
}

interface ContentBlock {
  id: string;
  locale: string;
  block_type: 'text' | 'image' | 'video' | 'gallery' | 'link' | 'result';
  sort_order: number;
  title: string | null;
  content: string | null;
  media_url: string | null;
  thumbnail_url: string | null;
  link_url: string | null;
  link_label: string | null;
  device_type: 'mobile' | 'desktop' | 'both' | null;
  block_metadata: Record<string, any> | null;
}

interface ProductDetail extends ProductPublic {
  images: ProductImage[];
  characteristics: ProductCharacteristic[];
  chars: ProductChar[];  // backward compat (flat name+value_text)
  categories: CategoryPublic[];
  prices: ProductPrice[];
  content_blocks: ContentBlock[];
  option_groups: OptionGroupPublic[] | null;
  variants: VariantPublic[] | null;
}

// ---------- Варианты ----------

interface OptionGroupPublic {
  title: string;
  slug: string;
  display_type: 'dropdown' | 'buttons' | 'color_swatch' | 'cards';
  values: OptionValuePublic[];
}

interface OptionValuePublic {
  title: string;
  slug: string;
  color_hex: string | null;
  image_url: string | null;
}

interface VariantPublic {
  id: string;
  slug: string;
  title: string;
  sku: string;
  description: string | null;
  is_default: boolean;
  in_stock: boolean;
  sort_order: number;
  prices: VariantPricePublic[];
  options: Record<string, string>;
  images: VariantImagePublic[];
  inclusions: VariantInclusionPublic[];
}

interface VariantPricePublic {
  price_type: string;
  amount: string;
  currency: string;
}

interface VariantImagePublic {
  url: string;
  alt: string | null;
  sort_order: number;
  is_cover: boolean;
}

interface VariantInclusionPublic {
  title: string;
  description: string | null;
  is_included: boolean;
  icon: string | null;
  group: string | null;
}

// ---------- Категория + продукты ----------

interface CategoryWithProductsResponse {
  category: CategoryPublic;
  products: ProductListResponse;
}

// ---------- Заявка ----------

interface InquiryAnalytics {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  referrer_url?: string;
  source_url?: string;
  page_path?: string;
  page_title?: string;
  user_agent?: string;
  device_type?: string;
  browser?: string;
  os?: string;
  screen_resolution?: string;
  session_id?: string;
  session_page_views?: number;
  time_on_page?: number;
}

interface InquiryCreateRequest {
  form_slug?: string;
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  message?: string;
  telegram?: string;
  consent?: boolean;
  product_id?: string;
  service_id?: string;
  analytics?: InquiryAnalytics;
  custom_fields?: Record<string, any>;
}

interface InquiryProductBrief {
  id: string;
  slug: string;
  sku: string;
  name: string;
}

interface InquiryResponse {
  id: string;
  tenant_id: string;
  form_id: string | null;
  form_slug: string | null;
  name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  message: string | null;
  status: string;
  product_id: string | null;
  product: InquiryProductBrief | null;
  source: string;
  ip_address: string | null;
  custom_fields: Record<string, any> | null;
  analytics: InquiryAnalytics | null;
  assigned_to: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ---------- Общие ----------

interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

interface ApiErrorBody {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string | null;
  [key: string]: any;
}

interface ValidationErrorBody {
  detail: Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
}
```

---

## 14. Примеры интеграции

### React hook для каталога

```typescript
import { useState, useEffect, useCallback } from 'react';

const useCatalog = (tenantId: string) => {
  const api = new ApiClient(tenantId);

  const getCategories = useCallback(async () => {
    return api.get<CategoryTreeResponse>('/public/categories');
  }, [tenantId]);

  const getProducts = useCallback(async (params?: Record<string, string>) => {
    return api.get<ProductListResponse>('/public/products', params);
  }, [tenantId]);

  const getProduct = useCallback(async (slug: string, locale?: string) => {
    const params: Record<string, string> = {};
    if (locale) params.locale = locale;
    return api.get<ProductDetail>(`/public/products/${slug}`, params);
  }, [tenantId]);

  const getFilters = useCallback(async (params?: Record<string, string>) => {
    return api.get<FiltersResponse>('/public/filters', params);
  }, [tenantId]);

  const submitInquiry = useCallback(async (data: InquiryCreateRequest) => {
    return api.post<InquiryResponse>('/public/inquiries', data);
  }, [tenantId]);

  return { getCategories, getProducts, getProduct, getFilters, submitInquiry };
};
```

### React hook для фасетных фильтров

```typescript
const useCatalogFilters = (tenantId: string, initialCategory?: string) => {
  const api = new ApiClient(tenantId);
  const [selected, setSelected] = useState<SelectedFilters>({
    categories: initialCategory ? [initialCategory] : [],
    params: {},
    sort: 'newest',
  });
  const [filters, setFilters] = useState<FiltersResponse | null>(null);
  const [products, setProducts] = useState<ProductListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const buildParams = useCallback((): Record<string, string> => {
    const p: Record<string, string> = {};
    if (selected.categories.length) p.category = selected.categories.join(',');
    if (selected.priceMin) p.price_min = selected.priceMin.toString();
    if (selected.priceMax) p.price_max = selected.priceMax.toString();
    if (selected.sort !== 'newest') p.sort = selected.sort;
    p.page = page.toString();
    for (const [slug, vals] of Object.entries(selected.params)) {
      if (vals.length) p[slug] = vals.join(',');
    }
    return p;
  }, [selected, page]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const params = buildParams();
      const [f, p] = await Promise.all([
        api.get<FiltersResponse>('/public/filters', params),
        api.get<ProductListResponse>('/public/products', params),
      ]);
      setFilters(f);
      setProducts(p);
      setLoading(false);
    };
    load();
  }, [buildParams]);

  const toggleParam = (paramSlug: string, valueSlug: string) => {
    setPage(1);
    setSelected(prev => {
      const current = prev.params[paramSlug] ?? [];
      const next = current.includes(valueSlug)
        ? current.filter(v => v !== valueSlug)
        : [...current, valueSlug];
      return { ...prev, params: { ...prev.params, [paramSlug]: next } };
    });
  };

  const setSort = (sort: SelectedFilters['sort']) => {
    setPage(1);
    setSelected(prev => ({ ...prev, sort }));
  };

  const setPriceRange = (min?: number, max?: number) => {
    setPage(1);
    setSelected(prev => ({ ...prev, priceMin: min, priceMax: max }));
  };

  const clearAll = () => {
    setPage(1);
    setSelected(prev => ({ ...prev, params: {}, priceMin: undefined, priceMax: undefined }));
  };

  return {
    filters, products, loading, selected, page,
    toggleParam, setSort, setPriceRange, setPage, clearAll,
  };
};
```

### Next.js Server Component (App Router)

```typescript
// app/products/[slug]/page.tsx

async function getProduct(slug: string, tenantId: string, locale: string) {
  const res = await fetch(
    `${process.env.API_URL}/api/v1/public/products/${slug}?tenant_id=${tenantId}&locale=${locale}`,
    { next: { revalidate: 60 } } // ISR: обновлять каждые 60 сек
  );

  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json() as Promise<ProductDetail>;
}

export default async function ProductPage({ params }: { params: { slug: string } }) {
  const tenantId = process.env.TENANT_ID!;
  const product = await getProduct(params.slug, tenantId, 'ru');

  if (!product) return notFound();

  return <ProductDetailView product={product} />;
}
```

### Форма заявки на продукт

```tsx
const ProductInquiryForm = ({ product }: { product: ProductDetail }) => {
  const { submitInquiry } = useCatalog(tenantId);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStatus('loading');
    setErrors({});

    const form = new FormData(e.currentTarget);
    try {
      await submitInquiry({
        form_slug: 'quick',
        name: form.get('name') as string,
        email: form.get('email') as string || undefined,
        phone: form.get('phone') as string || undefined,
        message: form.get('message') as string,
        product_id: product.id,
        consent: true,
        analytics: {
          source_url: window.location.href,
          page_path: window.location.pathname,
          page_title: document.title,
          user_agent: navigator.userAgent,
        },
      });
      setStatus('success');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.isValidation) {
          setErrors(err.fieldErrors);
        } else if (err.isRateLimit) {
          setErrors({ _form: `Подождите ${err.retryAfter ?? 60} секунд` });
        } else {
          setErrors({ _form: 'Ошибка отправки. Попробуйте позже.' });
        }
      }
      setStatus('error');
    }
  };

  if (status === 'success') {
    return <div className="success">Спасибо! Мы свяжемся с вами в ближайшее время.</div>;
  }

  return (
    <form onSubmit={handleSubmit}>
      <h3>Оставить заявку на {product.title}</h3>
      <input name="name" placeholder="Ваше имя *" required />
      {errors.name && <span className="error">{errors.name}</span>}

      <input name="email" type="email" placeholder="Email" />
      {errors.email && <span className="error">{errors.email}</span>}

      <input name="phone" type="tel" placeholder="Телефон" />

      <textarea name="message" placeholder="Сообщение *" required />
      {errors.message && <span className="error">{errors.message}</span>}

      {errors._form && <div className="form-error">{errors._form}</div>}

      <button type="submit" disabled={status === 'loading'}>
        {status === 'loading' ? 'Отправка...' : 'Отправить заявку'}
      </button>
    </form>
  );
};
```

---

## 15. Типичные сценарии

### Страница каталога — полный flow

```
1. При загрузке:
   GET /public/categories        → дерево категорий для сайдбара/меню
   GET /public/filters           → список фильтров с счётчиками
   GET /public/products          → первая страница товаров

2. Пользователь выбрал категорию "electronics":
   GET /public/filters?category=electronics    → фильтры для этой категории
   GET /public/products?category=electronics   → товары с пагинацией
   URL: /catalog/electronics

3. Пользователь выбрал фильтр "цвет: красный":
   GET /public/filters?category=electronics&color=red    → пересчёт счётчиков
   GET /public/products?category=electronics&color=red   → отфильтрованные товары
   URL: /catalog/electronics/color--red

4. Пользователь добавил фильтр "материал: металл":
   GET /public/filters?category=electronics&color=red&material=metal
   GET /public/products?category=electronics&color=red&material=metal&sort=price_asc
   URL: /catalog/electronics/color--red/material--metal

5. Пользователь ищет "кабель":
   GET /public/products?search=кабель

6. Пользователь открыл карточку товара:
   GET /public/products/widget-pro-2000?locale=ru

7. Пользователь отправил заявку:
   POST /public/inquiries  { product_id: "...", ... }
```

### Структура страниц

```
/catalog                                     → GET /public/filters + GET /public/products
/catalog/{category-slug}                     → Товары в категории
/catalog/{category-slug}/{param}--{value}    → Фильтрованная страница (ЧПУ)
/catalog/{param}--{value}                    → Фильтр без категории
/catalog/products/{product-slug}             → GET /public/products/{slug}?locale=ru
```

### SEO-рекомендации

- Используй `slug` продуктов и категорий в URL, а не `id`
- Поля `title`, `description`, `brand` — для meta-тегов
- `images[0]` с `is_cover=true` — для `og:image`
- Контент-блоки типа `text` — индексируемый контент для поисковиков
- `characteristics` — для structured data (JSON-LD Product schema)
- `GET /public/seo/filter-pages` — для генерации sitemap фильтрованных страниц
- Формат ЧПУ `/{category}/{param}--{value}` — SEO-friendly URL для фасетных страниц

```typescript
// JSON-LD пример для карточки товара
const productJsonLd = {
  '@context': 'https://schema.org',
  '@type': 'Product',
  name: product.title,
  description: product.description,
  sku: product.sku,
  brand: product.brand ? { '@type': 'Brand', name: product.brand } : undefined,
  image: product.images.map(img => img.url),
  additionalProperty: product.characteristics.map(c => ({
    '@type': 'PropertyValue',
    name: c.parameter_name,
    value: c.type === 'enum'
      ? c.values.map(v => v.label).join(', ')
      : c.value_number ?? c.value_text ?? String(c.value_bool),
    unitCode: c.uom?.code,
  })),
  offers: product.prices
    .filter(p => p.price_type !== 'cost')
    .map(p => ({
      '@type': 'Offer',
      price: p.amount,
      priceCurrency: p.currency,
      availability: 'https://schema.org/InStock',
    })),
};
```
