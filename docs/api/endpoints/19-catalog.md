# Catalog API — Products, Categories, Characteristics

> **Feature flag**: `catalog_module` — все эндпоинты возвращают `403` если флаг выключен для тенанта.  
> **Base URL**: `/api/v1`  
> **Все admin-эндпоинты** требуют заголовок `Authorization: Bearer {access_token}` и заголовок `X-Tenant-ID: {tenant_uuid}`.  
> **Все public-эндпоинты** требуют query-параметр `?tenant_id={uuid}`.

---

## Содержание

1. [Структура объектов](#1-структура-объектов)
2. [UOM — Единицы измерения](#2-uom)
3. [Categories — Категории](#3-categories)
4. [Products — Продукты (CRUD)](#4-products)
5. [Product Characteristics (EAV)](#5-product-characteristics)
6. [Product Images](#6-product-images)
7. [Product Prices](#7-product-prices)
8. [Product Aliases](#8-product-aliases)
9. [Product Analogs](#9-product-analogs)
10. [Product Categories (привязка)](#10-product-categories)
11. [Product Content Blocks](#11-product-content-blocks)
12. [Публичные эндпоинты (без авторизации)](#12-публичные-эндпоинты)
13. [RBAC permissions](#13-rbac-permissions)
14. [TypeScript-типы](#14-typescript-типы)

---

## 1. Структура объектов

### Product (список)

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "sku": "WP-2000",
  "slug": "widget-pro-2000",
  "title": "Widget Pro 2000",
  "brand": "WidgetCorp",
  "model": "Pro-2000",
  "description": "HTML или plain text описание",
  "uom_id": "uuid | null",
  "is_active": true,
  "version": 1,
  "images": [
    {
      "id": "uuid",
      "url": "https://s3.../products/img.jpg",
      "alt": "Фото товара",
      "width": 1200,
      "height": 800,
      "size_bytes": 204800,
      "mime_type": "image/jpeg",
      "sort_order": 0,
      "is_cover": true,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

### ProductDetail (карточка, с include)

Дополнительно к Product добавляются поля:

```json
{
  "chars": [
    { "id": "uuid", "name": "Напряжение", "value_text": "220 В", "uom_id": "uuid|null" }
  ],
  "aliases": [
    { "id": "uuid", "alias": "виджет про" }
  ],
  "categories": [
    { "id": "uuid", "category_id": "uuid", "is_primary": true }
  ],
  "prices": [
    {
      "id": "uuid",
      "price_type": "regular",
      "amount": "1500.00",
      "currency": "RUB",
      "valid_from": "2026-01-01",
      "valid_to": null,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### Category

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "title": "Электрооборудование",
  "slug": "electrical",
  "parent_id": "uuid | null",
  "description": "Описание категории",
  "image_url": "https://s3.../categories/elec.jpg",
  "is_active": true,
  "sort_order": 0,
  "version": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

### UOM

```json
{
  "id": "uuid",
  "name": "Штука",
  "code": "pcs",
  "symbol": "шт.",
  "is_active": true,
  "created_at": "...",
  "updated_at": "..."
}
```

---

## 2. UOM

### GET /api/v1/admin/uoms

Список всех единиц измерения тенанта.

**Permission:** `catalog:read`

```bash
GET /api/v1/admin/uoms
Authorization: Bearer {token}
X-Tenant-ID: {tenant_uuid}
```

**Response 200:**
```json
[
  { "id": "uuid", "name": "Штука", "code": "pcs", "symbol": "шт.", "is_active": true, "..." }
]
```

---

### POST /api/v1/admin/uoms

**Permission:** `catalog:create`

```json
{ "name": "Метр", "code": "m", "symbol": "м" }
```

| Поле | Тип | Обяз. | Ограничения |
|------|-----|-------|-------------|
| `name` | string | Да | 1–100 |
| `code` | string | Да | 1–20, уникальный |
| `symbol` | string | Нет | max 20 |

**Response 201:** UOM объект.

---

### PATCH /api/v1/admin/uoms/{uom_id}

**Permission:** `catalog:update`

```json
{ "is_active": false }
```

---

## 3. Categories

### GET /api/v1/admin/categories

Пагинированный список категорий.

**Permission:** `catalog:read`

**Query:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `page` | int | Страница (default 1) |
| `pageSize` | int | Размер (default 20) |
| `parent_id` | UUID | Фильтр дочерних категорий |

**Response 200:**
```json
{ "items": [...], "total": 12, "page": 1, "page_size": 20 }
```

---

### GET /api/v1/admin/categories/tree

Полное дерево категорий без пагинации.

**Permission:** `catalog:read`

**Response 200:**
```json
{ "items": [...all categories...], "total": 12 }
```

---

### GET /api/v1/admin/categories/{category_id}

**Permission:** `catalog:read`

**Response 200:** Category объект.

---

### POST /api/v1/admin/categories

**Permission:** `catalog:create`

```json
{
  "title": "Электрооборудование",
  "slug": "electrical",
  "parent_id": null,
  "description": "Всё для электрики",
  "image_url": null,
  "is_active": true,
  "sort_order": 0
}
```

| Поле | Тип | Обяз. | Ограничения |
|------|-----|-------|-------------|
| `title` | string | Да | 1–255 |
| `slug` | string | Да | 1–255, уникальный в тенанте |
| `parent_id` | UUID | Нет | Родительская категория |
| `description` | string | Нет | — |
| `image_url` | string | Нет | max 500 |
| `is_active` | bool | Нет | default true |
| `sort_order` | int | Нет | default 0 |

**Response 201:** Category объект.

---

### PATCH /api/v1/admin/categories/{category_id}

**Permission:** `catalog:update`

Поле `version` обязательно (optimistic locking).

```json
{ "title": "Новое название", "version": 1 }
```

---

### DELETE /api/v1/admin/categories/{category_id}

**Permission:** `catalog:delete`  
**Response:** `204 No Content` (soft delete)

---

## 4. Products

### GET /api/v1/admin/products

Пагинированный список продуктов.

**Permission:** `catalog:read`

**Query:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `page` | int | default 1 |
| `pageSize` | int | default 20 |
| `search` | string | Поиск по title, sku, description |
| `brand` | string | Фильтр по бренду |
| `category_id` | UUID | Фильтр по категории |
| `isActive` | bool | Фильтр по статусу |

**Response 200:**
```json
{
  "items": [ { ...Product... } ],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/v1/admin/products/{product_id}

**Permission:** `catalog:read`

**Query:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `include` | string | Список через запятую: `chars,aliases,categories,prices` |

```bash
GET /api/v1/admin/products/uuid?include=chars,prices,categories
```

**Response 200:** ProductDetail объект (с запрошенными related данными).

---

### POST /api/v1/admin/products

**Permission:** `catalog:create`

```json
{
  "sku": "WP-2000",
  "slug": "widget-pro-2000",
  "title": "Widget Pro 2000",
  "brand": "WidgetCorp",
  "model": "Pro-2000",
  "description": "Полное описание товара",
  "uom_id": "uuid-of-uom-or-null",
  "is_active": true,
  "category_ids": ["cat-uuid-1", "cat-uuid-2"]
}
```

| Поле | Тип | Обяз. | Ограничения |
|------|-----|-------|-------------|
| `sku` | string | Да | 1–100, уникальный в тенанте |
| `slug` | string | Да | 1–255, уникальный в тенанте |
| `title` | string | Да | 1–500 |
| `brand` | string | Нет | max 255 |
| `model` | string | Нет | max 255 |
| `description` | string | Нет | — |
| `uom_id` | UUID | Нет | FK to uoms |
| `is_active` | bool | Нет | default true |
| `category_ids` | UUID[] | Нет | Категории привязываются при создании |

**Response 201:** Product объект (без chars/aliases/prices).

---

### PATCH /api/v1/admin/products/{product_id}

**Permission:** `catalog:update`

Поле `version` обязательно (optimistic locking).

```json
{
  "title": "Widget Pro 2000 v2",
  "is_active": false,
  "version": 1
}
```

**Response 200:** обновлённый Product объект.

---

### DELETE /api/v1/admin/products/{product_id}

**Permission:** `catalog:delete`  
**Response:** `204 No Content` (soft delete)

---

## 5. Product Characteristics

EAV (Entity-Attribute-Value) — произвольные пары ключ-значение для продукта.

### GET /api/v1/admin/products/{product_id}/chars

**Permission:** `catalog:read`

**Response 200:**
```json
[
  { "id": "uuid", "name": "Напряжение", "value_text": "220 В", "uom_id": "uuid|null" },
  { "id": "uuid", "name": "Мощность", "value_text": "1500", "uom_id": "uuid-watt" }
]
```

---

### PUT /api/v1/admin/products/{product_id}/chars

Bulk create / update / delete характеристик за один запрос.

**Permission:** `catalog:update`

```json
{
  "created": [
    { "name": "Гарантия", "value_text": "24 мес.", "uom_id": null }
  ],
  "updated": [
    { "id": "existing-char-uuid", "value_text": "230 В" }
  ],
  "deleted": ["char-uuid-to-delete"]
}
```

Все поля необязательны (можно только `created`, только `deleted` и т.д.).

**Response 200:**
```json
{ "created": 1, "updated": 1, "deleted": 1 }
```

---

## 6. Product Images

### GET /api/v1/admin/products/{product_id}/images

**Permission:** `catalog:read`

**Response 200:** `list[ProductImage]`

---

### POST /api/v1/admin/products/{product_id}/images

Загрузка изображения (multipart/form-data).

**Permission:** `catalog:create`

| Поле | Тип | Обяз. | Описание |
|------|-----|-------|----------|
| `file` | File | Да | JPEG, PNG, WebP, GIF. Max 10 MB |
| `alt` | string | Нет | Alt-текст |
| `is_cover` | bool | Нет | Установить как обложку (default false) |

```bash
curl -X POST /api/v1/admin/products/{id}/images \
  -H "Authorization: Bearer {token}" \
  -F "file=@photo.jpg" \
  -F "alt=Фото товара" \
  -F "is_cover=true"
```

**Response 201:** ProductImage объект.

---

### PATCH /api/v1/admin/products/{product_id}/images/{image_id}

Обновить метаданные изображения (alt, sort_order).

**Permission:** `catalog:update`

```json
{ "alt": "Новый alt", "sort_order": 2 }
```

---

### DELETE /api/v1/admin/products/{product_id}/images/{image_id}

**Permission:** `catalog:delete` — удаляет файл из S3 и запись.  
**Response:** `204 No Content`

---

### PUT /api/v1/admin/products/{product_id}/images/reorder

Изменить порядок изображений.

**Permission:** `catalog:update`

```json
{ "ordered_ids": ["uuid-img-3", "uuid-img-1", "uuid-img-2"] }
```

**Response:** `204 No Content`

---

### POST /api/v1/admin/products/{product_id}/images/{image_id}/set-cover

Установить изображение как обложку.

**Permission:** `catalog:update`  
**Response:** `204 No Content`

---

## 7. Product Prices

### GET /api/v1/admin/products/{product_id}/prices

**Permission:** `catalog:read`

**Response 200:**
```json
[
  {
    "id": "uuid",
    "price_type": "regular",
    "amount": "1500.00",
    "currency": "RUB",
    "valid_from": null,
    "valid_to": null,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### POST /api/v1/admin/products/{product_id}/prices

**Permission:** `catalog:create`

```json
{
  "price_type": "regular",
  "amount": 1500.00,
  "currency": "RUB",
  "valid_from": null,
  "valid_to": null
}
```

| Поле | Тип | Значения |
|------|-----|---------|
| `price_type` | string | `regular` \| `sale` \| `wholesale` \| `cost` |
| `amount` | decimal | ≥ 0 |
| `currency` | string | ISO 4217, max 3 символа. Default: `RUB` |
| `valid_from` | date | YYYY-MM-DD |
| `valid_to` | date | YYYY-MM-DD |

**Response 201:** ProductPrice объект.

---

### PATCH /api/v1/admin/products/{product_id}/prices/{price_id}

**Permission:** `catalog:update`

---

### DELETE /api/v1/admin/products/{product_id}/prices/{price_id}

**Permission:** `catalog:delete`  
**Response:** `204 No Content`

---

## 8. Product Aliases

Альтернативные названия товара (для поиска).

### GET /api/v1/admin/products/{product_id}/aliases

**Response 200:** `[{ "id": "uuid", "alias": "виджет про" }]`

---

### POST /api/v1/admin/products/{product_id}/aliases

```json
{ "aliases": ["виджет", "widget pro", "WP2000"] }
```

Уже существующие псевдонимы пропускаются.

**Response 201:**
```json
{ "created": 3, "skipped": 0 }
```

---

### DELETE /api/v1/admin/products/{product_id}/aliases/{alias_id}

**Response:** `204 No Content`

---

## 9. Product Analogs

Аналоги/заменители товара (направленная связь).

### GET /api/v1/admin/products/{product_id}/analogs

**Response 200:**
```json
[
  {
    "analog_product_id": "uuid",
    "sku": "WP-1900",
    "title": "Widget Pro 1900",
    "relation": "worse",
    "notes": "Старая модель"
  }
]
```

---

### POST /api/v1/admin/products/{product_id}/analogs

```json
{
  "analog_product_id": "uuid-other-product",
  "relation": "equivalent",
  "notes": null
}
```

| `relation` | Описание |
|-----------|----------|
| `equivalent` | Полный аналог |
| `better` | Аналог лучше |
| `worse` | Аналог хуже |

**Response 201:** `{ "success": true }`

---

### DELETE /api/v1/admin/products/{product_id}/analogs/{analog_product_id}

**Response:** `204 No Content`

---

## 10. Product Categories

### PUT /api/v1/admin/products/{product_id}/categories

Заменить весь список категорий продукта.

**Permission:** `catalog:update`

```json
["cat-uuid-1", "cat-uuid-2"]
```

**Response 200:** `{ "count": 2 }`

> Первая категория в списке становится `is_primary = true`.

---

## 12. Публичные эндпоинты

Не требуют авторизации. Используют `?tenant_id={uuid}`.  
Требуют включённый feature flag `catalog_module` для тенанта.

---

### GET /api/v1/public/categories?tenant_id={uuid}

Список всех активных категорий.

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Электрооборудование",
      "slug": "electrical",
      "parent_id": null,
      "description": "...",
      "image_url": "https://..."
    }
  ],
  "total": 5
}
```

---

### GET /api/v1/public/categories/{slug}?tenant_id={uuid}

Категория + список продуктов в ней.

**Query:** `page`, `pageSize`

**Response 200:**
```json
{
  "category": { ...CategoryPublic... },
  "products": {
    "items": [ { ...ProductPublic... } ],
    "total": 24,
    "page": 1,
    "page_size": 20
  }
}
```

---

### GET /api/v1/public/products?tenant_id={uuid}

Список активных (`is_active=true`) продуктов.

**Query:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `tenant_id` | UUID | Обязательно |
| `page` | int | default 1 |
| `pageSize` | int | default 20 |
| `search` | string | Поиск |
| `brand` | string | Фильтр по бренду |
| `category` | UUID | Фильтр по категории |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "widget-pro-2000",
      "sku": "WP-2000",
      "title": "Widget Pro 2000",
      "brand": "WidgetCorp",
      "model": "Pro-2000",
      "description": "...",
      "cover_url": "https://s3.../cover.jpg"
    }
  ],
  "total": 48,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/v1/public/products/{slug}?tenant_id={uuid}

Детальная карточка продукта по slug.

**Query:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `tenant_id` | UUID | Обязательно |
| `locale` | string | Фильтр контент-блоков по локали, например `ru` или `en` |

**Response 200:**
```json
{
  "id": "uuid",
  "slug": "widget-pro-2000",
  "sku": "WP-2000",
  "title": "Widget Pro 2000",
  "brand": "WidgetCorp",
  "model": "Pro-2000",
  "description": "Полное описание",
  "images": [
    {
      "id": "uuid",
      "url": "https://s3.../img.jpg",
      "alt": "Фото товара",
      "width": 1200,
      "height": 800,
      "sort_order": 0,
      "is_cover": true
    }
  ],
  "chars": [
    { "name": "Напряжение", "value_text": "220 В" },
    { "name": "Мощность", "value_text": "1500 Вт" }
  ],
  "categories": [
    { "id": "uuid", "title": "Электрооборудование", "slug": "electrical", "parent_id": null }
  ],
  "prices": [
    { "price_type": "regular", "amount": "1500.00", "currency": "RUB" },
    { "price_type": "sale", "amount": "1200.00", "currency": "RUB" }
  ],
  "content_blocks": [
    {
      "id": "uuid",
      "locale": "ru",
      "block_type": "text",
      "sort_order": 0,
      "title": "О продукте",
      "content": "<p>Детальное описание с HTML-форматированием</p>",
      "media_url": null,
      "thumbnail_url": null,
      "link_url": null,
      "link_label": null,
      "device_type": "both",
      "block_metadata": null
    }
  ]
}
```

---

### Оставить заявку на продукт

```bash
POST /api/v1/public/inquiries?tenant_id={uuid}
Content-Type: application/json

{
  "form_slug": "quick",
  "name": "Иван Петров",
  "email": "ivan@example.com",
  "phone": "+7 999 123-45-67",
  "message": "Хочу уточнить наличие",
  "product_id": "uuid-of-product",
  "consent": true,
  "analytics": {
    "source_url": "https://example.com/catalog/widget-pro-2000",
    "page_path": "/catalog/widget-pro-2000"
  }
}
```

Подробнее — см. [`07-leads.md`](./07-leads.md) и [`../changelogs/PRODUCT_INQUIRY_SUPPORT.md`](../changelogs/PRODUCT_INQUIRY_SUPPORT.md).

---

## 11. Product Content Blocks

Контент-блоки — это гибкий способ прикрепить к товару структурированный контент: тексты, изображения, видео, галереи, ссылки (аналогично блокам для статей и услуг).

### GET /api/v1/admin/products/{product_id}/content-blocks

Список контент-блоков товара. Требует: `catalog:read`.

**Query:** `locale` (опционально, фильтр по локали)

**Response 200:** `ContentBlock[]`

---

### POST /api/v1/admin/products/{product_id}/content-blocks

Добавить контент-блок. Требует: `catalog:update`.

**Request:**
```json
{
  "locale": "ru",
  "block_type": "text",
  "sort_order": 0,
  "title": "О продукте",
  "content": "<p>Расширенное описание</p>",
  "media_url": null,
  "thumbnail_url": null,
  "link_url": null,
  "link_label": null,
  "device_type": "both",
  "block_metadata": null
}
```

**Типы блоков (`block_type`):**
| Тип | Описание |
|-----|----------|
| `text` | HTML-текст с заголовком |
| `image` | Изображение (`media_url` + `block_metadata.alt`) |
| `video` | Видео (`media_url`, `thumbnail_url`, `block_metadata.provider`) |
| `gallery` | Галерея (`block_metadata.images: [{url, alt}]`) |
| `link` | Ссылка-кнопка (`link_url`, `link_label`) |
| `result` | Кейс/результат (смешанный) |

**Response 201:** `ContentBlock`

---

### PATCH /api/v1/admin/products/{product_id}/content-blocks/{block_id}

Обновить контент-блок. Требует: `catalog:update`.

**Request:** любые поля из `ContentBlockCreate` (все опциональны).

**Response 200:** `ContentBlock`

---

### DELETE /api/v1/admin/products/{product_id}/content-blocks/{block_id}

Удалить контент-блок. Требует: `catalog:delete`.

**Response 204:** No Content

---

### POST /api/v1/admin/products/{product_id}/content-blocks/reorder

Изменить порядок блоков в конкретной локали. Требует: `catalog:update`.

**Request:**
```json
{
  "locale": "ru",
  "block_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Response 200:** `ContentBlock[]` в новом порядке

---

## 12. Публичные эндпоинты (без авторизации)

> Публичный эндпоинт `GET /public/products/{slug}` возвращает поле `content_blocks[]` — отфильтрованные по `locale` если передан query-параметр `?locale=ru`.

---

## 13. RBAC permissions

| Permission | Описание |
|------------|---------|
| `catalog:read` | Чтение продуктов, категорий, UOM |
| `catalog:create` | Создание продуктов, категорий, изображений, цен |
| `catalog:update` | Редактирование продуктов, категорий, характеристик |
| `catalog:delete` | Удаление продуктов, категорий, изображений |

**Роли по умолчанию:**
| Роль | Права |
|------|-------|
| `site_owner` | `catalog:*` (все) |
| `content_manager` | `catalog:*` (все) |
| `editor` | `catalog:read` |

---

## 14. TypeScript-типы

```typescript
// UOM
interface UOM {
  id: string;
  name: string;
  code: string;
  symbol: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Category
interface Category {
  id: string;
  tenant_id: string;
  title: string;
  slug: string;
  parent_id: string | null;
  description: string | null;
  image_url: string | null;
  is_active: boolean;
  sort_order: number;
  version: number;
  created_at: string;
  updated_at: string;
}

// Product (list item)
interface Product {
  id: string;
  tenant_id: string;
  sku: string;
  slug: string;
  title: string;
  brand: string | null;
  model: string | null;
  description: string | null;
  uom_id: string | null;
  is_active: boolean;
  version: number;
  images: ProductImage[];
  created_at: string;
  updated_at: string;
}

// Product (detail — after ?include=chars,aliases,categories,prices)
interface ProductDetail extends Product {
  chars: ProductChar[];
  aliases: ProductAlias[];
  categories: ProductCategoryLink[];
  prices: ProductPrice[];
}

interface ProductImage {
  id: string;
  url: string;
  alt: string | null;
  width: number | null;
  height: number | null;
  size_bytes: number | null;
  mime_type: string | null;
  sort_order: number;
  is_cover: boolean;
  created_at: string;
}

interface ProductChar {
  id: string;
  name: string;
  value_text: string;
  uom_id: string | null;
}

interface ProductAlias {
  id: string;
  alias: string;
}

interface ProductCategoryLink {
  id: string;
  category_id: string;
  is_primary: boolean;
}

interface ProductPrice {
  id: string;
  price_type: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: string;   // decimal as string
  currency: string; // "RUB", "USD", etc.
  valid_from: string | null;  // "YYYY-MM-DD"
  valid_to: string | null;
  created_at: string;
  updated_at: string;
}

// Public (client-facing) types
interface ProductPublic {
  id: string;
  slug: string;
  sku: string;
  title: string;
  brand: string | null;
  model: string | null;
  description: string | null;
  cover_url: string | null;  // URL обложки (первое изображение с is_cover=true)
}

interface ContentBlock {
  id: string;
  locale: string;
  block_type: 'text' | 'image' | 'video' | 'gallery' | 'link' | 'result';
  sort_order: number;
  title: string | null;
  content: string | null;         // HTML for text blocks
  media_url: string | null;       // image or video URL
  thumbnail_url: string | null;   // video thumbnail
  link_url: string | null;
  link_label: string | null;
  device_type: 'mobile' | 'desktop' | 'both' | null;
  block_metadata: Record<string, unknown> | null; // alt, caption, images[], provider, icon
}

interface ContentBlockCreate {
  locale: string;
  block_type: ContentBlock['block_type'];
  sort_order?: number;
  title?: string | null;
  content?: string | null;
  media_url?: string | null;
  thumbnail_url?: string | null;
  link_url?: string | null;
  link_label?: string | null;
  device_type?: ContentBlock['device_type'];
  block_metadata?: Record<string, unknown> | null;
}

interface ProductPublicDetail {
  id: string;
  slug: string;
  sku: string;
  title: string;
  brand: string | null;
  model: string | null;
  description: string | null;
  images: { id: string; url: string; alt: string | null; width: number | null; height: number | null; sort_order: number; is_cover: boolean }[];
  chars: { name: string; value_text: string }[];
  categories: { id: string; title: string; slug: string; parent_id: string | null; description: string | null; image_url: string | null }[];
  prices: { price_type: string; amount: string; currency: string }[];
  content_blocks: ContentBlock[];
}

// Paginated responses
interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

---

## Типичный flow для frontend-разработчика

### Страница каталога (клиентский фронт)
```
GET /public/categories?tenant_id=...                    → дерево категорий (меню)
GET /public/products?tenant_id=...                      → список товаров
GET /public/products?tenant_id=...&category=...         → список по категории
GET /public/products/{slug}?tenant_id=...               → карточка товара (включает content_blocks[])
GET /public/products/{slug}?tenant_id=...&locale=ru     → карточка с блоками отфильтрованными по локали
POST /public/inquiries?tenant_id=...                    → оставить заявку на товар
```

### Страница управления каталогом (админ-панель)
```
GET /admin/uoms                                         → справочник ед. измерения
GET /admin/categories/tree                              → дерево категорий
GET /admin/products?search=...&isActive=true            → список товаров
POST /admin/products                                    → создать товар
GET /admin/products/{id}?include=chars,prices           → карточка товара
PATCH /admin/products/{id}                              → редактировать
PUT /admin/products/{id}/chars                          → bulk-редактировать характеристики
POST /admin/products/{id}/images                        → загрузить фото
POST /admin/products/{id}/prices                        → добавить цену
GET /admin/products/{id}/content-blocks?locale=ru       → контент-блоки товара
POST /admin/products/{id}/content-blocks                → добавить блок
PATCH /admin/products/{id}/content-blocks/{block_id}    → обновить блок
DELETE /admin/products/{id}/content-blocks/{block_id}   → удалить блок
POST /admin/products/{id}/content-blocks/reorder        → изменить порядок
DELETE /admin/products/{id}                             → удалить (soft)
GET /admin/inquiries?productId={id}                     → заявки на этот товар
```
