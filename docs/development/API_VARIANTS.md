# API: Варианты продуктов и тарифы (Product Variants & Tariffs)

> **Назначение**: Документация для фронтенда по API вариантов продуктов — единая система «торговых предложений» для физических товаров (цвет/размер), тарифных планов (Basic/Premium/VIP), курсов с разными пакетами и подписок.  
> **Контекст**: Расширяет модуль каталога (`catalog_module`). Требует дополнительный feature flag `variants_module`.  
> **Версия бэкенда**: 2026-02-28 (ветка `feat/product-catalog`)

---

## Содержание

1. [Обзор](#1-обзор)
2. [Модель данных](#2-модель-данных)
3. [Admin API — Option Groups](#3-admin-api--option-groups)
4. [Admin API — Option Values](#4-admin-api--option-values)
5. [Admin API — Variants](#5-admin-api--variants)
6. [Admin API — Variant Prices](#6-admin-api--variant-prices)
7. [Admin API — Variant Inclusions](#7-admin-api--variant-inclusions)
8. [Admin API — Variant Images](#8-admin-api--variant-images)
9. [Публичное API — изменения](#9-публичное-api--изменения)
10. [TypeScript-типы](#10-typescript-типы)
11. [Сценарии UI](#11-сценарии-ui)
12. [Логика селектора вариантов](#12-логика-селектора-вариантов)

---

## 1. Обзор

### Что это

Единая система вариантов/тарифов, позволяющая продукту иметь несколько покупаемых предложений (offers). Каждый вариант — самостоятельный SKU с собственной ценой, остатком и набором опций.

### Типы продуктов

| `product_type` | Описание | Пример вариантов |
|----------------|----------|------------------|
| `physical` | Физический товар | Цвет + Размер |
| `digital` | Цифровой товар | Формат файла, лицензия |
| `service` | Услуга | Тариф обслуживания |
| `course` | Онлайн-курс | Базовый / Премиум / VIP пакет |
| `subscription` | Подписка | Месяц / Год / Пожизненная |

### Feature flags

| Flag | Зависимости | Описание |
|------|-------------|----------|
| `catalog_module` | — | Базовый каталог (продукты, категории, цены) |
| `variants_module` | `catalog_module` | Варианты, группы опций, тарифы |

Если `variants_module` выключен — все эндпоинты вариантов возвращают `403`. Публичное API продуктов отдаёт `option_groups: null`, `variants: null`.

### Обратная совместимость

Простые продукты (`has_variants = false`) работают как раньше: собственные цены на уровне продукта, без групп опций и вариантов. Никаких изменений в UI не требуется для существующих продуктов.

---

## 2. Модель данных

### Новые поля в Product

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| `product_type` | `string` | `"physical"` | Тип продукта: `physical`, `digital`, `service`, `course`, `subscription` |
| `has_variants` | `boolean` | `false` | Есть ли у продукта варианты |
| `price_from` | `decimal \| null` | `null` | Минимальная цена среди вариантов (для отображения «от X ₽») |
| `price_to` | `decimal \| null` | `null` | Максимальная цена среди вариантов |

### Таблицы

```
Product (products)
  ├── ProductOptionGroup (product_option_groups)
  │     └── ProductOptionValue (product_option_values)
  └── ProductVariant (product_variants)
        ├── VariantPrice (variant_prices)
        ├── VariantOptionLink (variant_option_links) ──→ ProductOptionValue
        ├── VariantInclusion (variant_inclusions)
        └── VariantImage (variant_images)
```

### ProductOptionGroup — оси вариации

Группа опций задаёт одно измерение вариации (Цвет, Размер, Тарифный план).

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `id` | UUID | auto | PK |
| `product_id` | UUID | Да | FK → products |
| `tenant_id` | UUID | Да | Scope по тенанту |
| `title` | string(255) | Да | Название: «Цвет», «Размер», «Тарифный план» |
| `slug` | string(255) | Да | URL-slug, уникальный в пределах продукта |
| `display_type` | string(20) | Да | Тип виджета отображения (см. ниже) |
| `sort_order` | int | Нет | Порядок отображения (default 0) |
| `is_required` | boolean | Нет | Обязателен ли выбор (default true) |
| `parameter_id` | UUID \| null | Нет | FK → parameters (привязка к фильтру каталога) |

**Типы отображения (`display_type`):**

| Значение | Описание | Когда использовать |
|----------|----------|--------------------|
| `dropdown` | Выпадающий список | Много значений (>5), тарифные планы |
| `buttons` | Кнопки-чипы | Размер (XS, S, M, L, XL) |
| `color_swatch` | Цветные кружки | Цвет (с `color_hex` из значений) |
| `cards` | Карточки с описанием | Тарифы с визуальным сравнением |

### ProductOptionValue — значения опций

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `id` | UUID | auto | PK |
| `option_group_id` | UUID | Да | FK → product_option_groups |
| `title` | string(255) | Да | Название: «Красный», «XL», «Премиум» |
| `slug` | string(255) | Да | Уникальный в пределах группы |
| `sort_order` | int | Нет | Порядок (default 0) |
| `color_hex` | string(7) \| null | Нет | HEX-цвет для `color_swatch`, например `#FF0000` |
| `image_url` | string(500) \| null | Нет | Изображение значения (превью цвета/материала) |

### ProductVariant — торговое предложение

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `id` | UUID | auto | PK |
| `product_id` | UUID | Да | FK → products |
| `tenant_id` | UUID | Да | Scope по тенанту |
| `sku` | string(100) | Да | Уникальный артикул (в пределах тенанта) |
| `slug` | string(255) | Да | URL-slug (уникальный в пределах продукта) |
| `title` | string(500) | Да | Название варианта |
| `description` | text \| null | Нет | Описание (для тарифов — описание пакета) |
| `is_default` | boolean | Нет | Вариант по умолчанию (default false) |
| `is_active` | boolean | Нет | Активен ли (default true) |
| `sort_order` | int | Нет | Порядок (default 0) |
| `stock_quantity` | int \| null | Нет | Остаток на складе (null = не отслеживается) |
| `weight` | decimal(10,3) \| null | Нет | Вес в кг (для доставки) |
| `deleted_at` | datetime \| null | auto | Soft delete |

### VariantPrice — цена варианта

Та же структура что и `ProductPrice`, но привязана к варианту:

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `id` | UUID | auto | PK |
| `variant_id` | UUID | Да | FK → product_variants |
| `price_type` | string | Да | `regular`, `sale`, `wholesale`, `cost` |
| `amount` | decimal(18,2) | Да | Сумма (≥ 0) |
| `currency` | string(3) | Нет | ISO 4217 (default `RUB`) |
| `valid_from` | date \| null | Нет | Начало действия |
| `valid_to` | date \| null | Нет | Окончание действия |

### VariantOptionLink — связь варианта с опциями (M2M)

| Поле | Тип | Описание |
|------|-----|----------|
| `variant_id` | UUID | FK → product_variants |
| `option_value_id` | UUID | FK → product_option_values |

Уникальная пара `(variant_id, option_value_id)`.

### VariantInclusion — состав тарифа / что включено

Для сравнительных таблиц тарифов (✅ / ❌):

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `id` | UUID | auto | PK |
| `variant_id` | UUID | Да | FK → product_variants |
| `title` | string(500) | Да | Название фичи: «Доступ к видео-урокам» |
| `description` | text \| null | Нет | Подробности |
| `is_included` | boolean | Да | Включено ли (default true) |
| `sort_order` | int | Нет | Порядок (default 0) |
| `icon` | string(100) \| null | Нет | Иконка (название из набора иконок) |
| `group` | string(100) \| null | Нет | Группировка фич: «Обучение», «Поддержка» |

### VariantImage — галерея варианта

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `id` | UUID | auto | PK |
| `variant_id` | UUID | Да | FK → product_variants |
| `url` | text | Да | URL изображения |
| `alt` | string(500) \| null | Нет | Alt-текст |
| `width` | int \| null | auto | Ширина (px) |
| `height` | int \| null | auto | Высота (px) |
| `size_bytes` | int \| null | auto | Размер файла |
| `mime_type` | string(50) \| null | auto | MIME-тип |
| `sort_order` | int | Нет | Порядок (default 0) |
| `is_cover` | boolean | Нет | Обложка варианта (default false) |

---

## 3. Admin API — Option Groups

> Все admin-эндпоинты требуют заголовки `Authorization: Bearer {token}`, `X-Tenant-ID: {tenant_uuid}`.  
> Все эндпоинты этого раздела требуют feature flags: `catalog_module` + `variants_module`.

### GET /api/v1/admin/products/{product_id}/option-groups

Список всех групп опций продукта с вложенными значениями.

**Permission:** `catalog:read`

**Ответ 200:**

```json
[
  {
    "id": "group-uuid-1",
    "product_id": "product-uuid",
    "title": "Цвет",
    "slug": "color",
    "display_type": "color_swatch",
    "sort_order": 0,
    "is_required": true,
    "parameter_id": "color-param-uuid",
    "values": [
      {
        "id": "value-uuid-1",
        "title": "Красный",
        "slug": "red",
        "sort_order": 0,
        "color_hex": "#FF0000",
        "image_url": null,
        "created_at": "2026-02-28T12:00:00Z",
        "updated_at": "2026-02-28T12:00:00Z"
      },
      {
        "id": "value-uuid-2",
        "title": "Синий",
        "slug": "blue",
        "sort_order": 1,
        "color_hex": "#0000FF",
        "image_url": null,
        "created_at": "2026-02-28T12:00:00Z",
        "updated_at": "2026-02-28T12:00:00Z"
      }
    ],
    "created_at": "2026-02-28T12:00:00Z",
    "updated_at": "2026-02-28T12:00:00Z"
  }
]
```

---

### POST /api/v1/admin/products/{product_id}/option-groups

Создать группу опций. Можно сразу передать массив `values[]`.

**Permission:** `catalog:write`

**Тело запроса:**

```json
{
  "title": "Размер",
  "slug": "size",
  "display_type": "buttons",
  "sort_order": 1,
  "is_required": true,
  "parameter_id": null,
  "values": [
    { "title": "S", "slug": "s", "sort_order": 0 },
    { "title": "M", "slug": "m", "sort_order": 1 },
    { "title": "L", "slug": "l", "sort_order": 2 },
    { "title": "XL", "slug": "xl", "sort_order": 3 }
  ]
}
```

| Поле | Тип | Обяз. | Ограничения |
|------|-----|:-----:|-------------|
| `title` | string | Да | 1–255 |
| `slug` | string | Да | 1–255, уникальный в пределах продукта |
| `display_type` | string | Нет | `dropdown` \| `buttons` \| `color_swatch` \| `cards` (default `dropdown`) |
| `sort_order` | int | Нет | default 0 |
| `is_required` | bool | Нет | default true |
| `parameter_id` | UUID \| null | Нет | Привязка к параметру каталога (для фильтров) |
| `values` | array | Нет | Начальные значения (default `[]`) |

**Ответ 201:** `OptionGroupResponse` (с вложенными `values[]`).

---

### PATCH /api/v1/admin/products/{product_id}/option-groups/{group_id}

Обновить группу опций. Все поля необязательны.

**Permission:** `catalog:write`

```json
{
  "title": "Цвет корпуса",
  "display_type": "color_swatch"
}
```

**Ответ 200:** обновлённый `OptionGroupResponse`.

---

### DELETE /api/v1/admin/products/{product_id}/option-groups/{group_id}

Удалить группу опций. Каскадно удаляются все значения группы.

**Permission:** `catalog:write`  
**Ответ:** `204 No Content`

> **Внимание:** Удаление группы не удаляет варианты, но разрывает связи через `VariantOptionLink`.

---

## 4. Admin API — Option Values

### POST /api/v1/admin/products/{product_id}/option-groups/{group_id}/values

Добавить значение к группе опций.

**Permission:** `catalog:write`

```json
{
  "title": "Зелёный",
  "slug": "green",
  "sort_order": 2,
  "color_hex": "#00AA00",
  "image_url": null
}
```

| Поле | Тип | Обяз. | Ограничения |
|------|-----|:-----:|-------------|
| `title` | string | Да | 1–255 |
| `slug` | string | Да | 1–255, уникальный в пределах группы |
| `sort_order` | int | Нет | default 0 |
| `color_hex` | string \| null | Нет | HEX-цвет, max 7 символов (e.g. `#FF0000`) |
| `image_url` | string \| null | Нет | URL изображения, max 500 |

**Ответ 201:** `OptionValueResponse`.

---

### PATCH /api/v1/admin/products/{product_id}/option-groups/{group_id}/values/{value_id}

Обновить значение. Все поля необязательны.

**Permission:** `catalog:write`

```json
{ "title": "Тёмно-зелёный", "color_hex": "#006600" }
```

**Ответ 200:** обновлённый `OptionValueResponse`.

---

### DELETE /api/v1/admin/products/{product_id}/option-groups/{group_id}/values/{value_id}

**Permission:** `catalog:write`  
**Ответ:** `204 No Content`

---

## 5. Admin API — Variants

### GET /api/v1/admin/products/{product_id}/variants

Список вариантов с полной детализацией: цены, значения опций, включения, изображения.

**Permission:** `catalog:read`

**Ответ 200:** `VariantDetailResponse[]`

```json
[
  {
    "id": "variant-uuid-1",
    "product_id": "product-uuid",
    "tenant_id": "tenant-uuid",
    "sku": "TSHIRT-RED-M",
    "slug": "red-m",
    "title": "Красный / M",
    "description": null,
    "is_default": true,
    "is_active": true,
    "sort_order": 0,
    "stock_quantity": 15,
    "weight": "0.200",
    "created_at": "2026-02-28T12:00:00Z",
    "updated_at": "2026-02-28T12:00:00Z",
    "prices": [
      {
        "id": "price-uuid-1",
        "price_type": "regular",
        "amount": "2500.00",
        "currency": "RUB",
        "valid_from": null,
        "valid_to": null,
        "created_at": "2026-02-28T12:00:00Z",
        "updated_at": "2026-02-28T12:00:00Z"
      }
    ],
    "option_values": [
      {
        "id": "value-uuid-1",
        "title": "Красный",
        "slug": "red",
        "sort_order": 0,
        "color_hex": "#FF0000",
        "image_url": null,
        "created_at": "2026-02-28T12:00:00Z",
        "updated_at": "2026-02-28T12:00:00Z"
      },
      {
        "id": "value-uuid-3",
        "title": "M",
        "slug": "m",
        "sort_order": 1,
        "color_hex": null,
        "image_url": null,
        "created_at": "2026-02-28T12:00:00Z",
        "updated_at": "2026-02-28T12:00:00Z"
      }
    ],
    "inclusions": [],
    "images": []
  }
]
```

---

### GET /api/v1/admin/products/{product_id}/variants/{variant_id}

Один вариант с полной детализацией.

**Permission:** `catalog:read`

**Ответ 200:** `VariantDetailResponse`.

---

### POST /api/v1/admin/products/{product_id}/variants

Создать вариант вручную.

**Permission:** `catalog:write`

```json
{
  "sku": "TSHIRT-RED-M",
  "slug": "red-m",
  "title": "Красный / M",
  "description": null,
  "is_default": true,
  "is_active": true,
  "sort_order": 0,
  "stock_quantity": 15,
  "weight": 0.200,
  "option_value_ids": ["value-uuid-red", "value-uuid-m"]
}
```

| Поле | Тип | Обяз. | Ограничения |
|------|-----|:-----:|-------------|
| `sku` | string | Да | 1–100, уникальный в тенанте |
| `slug` | string | Да | 1–255, уникальный в пределах продукта |
| `title` | string | Да | 1–500 |
| `description` | string \| null | Нет | — |
| `is_default` | bool | Нет | default false |
| `is_active` | bool | Нет | default true |
| `sort_order` | int | Нет | default 0 |
| `stock_quantity` | int \| null | Нет | null = не отслеживается |
| `weight` | decimal \| null | Нет | Вес в кг |
| `option_value_ids` | UUID[] | Нет | Привязка к значениям опций (default `[]`) |

**Ответ 201:** `VariantResponse` (без вложенных prices/options).

---

### PATCH /api/v1/admin/products/{product_id}/variants/{variant_id}

Обновить вариант. Все поля необязательны. Если передать `option_value_ids` — связи пересоздаются.

**Permission:** `catalog:write`

```json
{
  "stock_quantity": 10,
  "is_active": false
}
```

**Ответ 200:** обновлённый `VariantResponse`.

---

### DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}

**Soft delete** — вариант помечается `deleted_at`, но не удаляется физически.

**Permission:** `catalog:write`  
**Ответ:** `204 No Content`

---

### POST /api/v1/admin/products/{product_id}/variants/generate

Автоматическая генерация матрицы вариантов из декартова произведения значений выбранных групп опций.

**Permission:** `catalog:write`

**Запрос:**

```json
{
  "option_group_ids": ["color-group-uuid", "size-group-uuid"],
  "base_price": 2500.00
}
```

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `option_group_ids` | UUID[] | Да | Минимум 1 группа |
| `base_price` | decimal \| null | Нет | Базовая цена (`regular`) для каждого варианта |

**Пример:** Цвет (Красный, Синий) × Размер (M, L) → 4 варианта:
- Красный / M
- Красный / L
- Синий / M
- Синий / L

SKU генерируется как `{product_sku}-{value1_slug}-{value2_slug}`.

**Ответ 201:**

```json
{
  "created_count": 4,
  "variants": [
    {
      "id": "uuid-1",
      "product_id": "product-uuid",
      "tenant_id": "tenant-uuid",
      "sku": "TSHIRT-red-m",
      "slug": "red-m",
      "title": "Красный / M",
      "is_default": false,
      "is_active": false,
      "sort_order": 0,
      "stock_quantity": null,
      "weight": null,
      "created_at": "2026-02-28T12:00:00Z",
      "updated_at": "2026-02-28T12:00:00Z"
    }
  ]
}
```

> Уже существующие комбинации пропускаются.

---

## 6. Admin API — Variant Prices

### GET /api/v1/admin/products/{product_id}/variants/{variant_id}/prices

**Permission:** `catalog:read`

**Ответ 200:**

```json
[
  {
    "id": "price-uuid",
    "price_type": "regular",
    "amount": "2500.00",
    "currency": "RUB",
    "valid_from": null,
    "valid_to": null,
    "created_at": "2026-02-28T12:00:00Z",
    "updated_at": "2026-02-28T12:00:00Z"
  }
]
```

---

### POST /api/v1/admin/products/{product_id}/variants/{variant_id}/prices

**Permission:** `catalog:write`

```json
{
  "price_type": "regular",
  "amount": 2500.00,
  "currency": "RUB",
  "valid_from": null,
  "valid_to": null
}
```

| Поле | Тип | Обяз. | Значения |
|------|-----|:-----:|---------|
| `price_type` | string | Нет | `regular` \| `sale` \| `wholesale` \| `cost` (default `regular`) |
| `amount` | decimal | Да | ≥ 0 |
| `currency` | string | Нет | ISO 4217, max 3. Default: `RUB` |
| `valid_from` | date \| null | Нет | `YYYY-MM-DD` |
| `valid_to` | date \| null | Нет | `YYYY-MM-DD` |

**Ответ 201:** `VariantPriceResponse`.

---

### PATCH /api/v1/admin/products/{product_id}/variants/{variant_id}/prices/{price_id}

**Permission:** `catalog:write`

```json
{ "amount": 1999.00, "price_type": "sale" }
```

**Ответ 200:** обновлённый `VariantPriceResponse`.

---

### DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}/prices/{price_id}

**Permission:** `catalog:write`  
**Ответ:** `204 No Content`

---

## 7. Admin API — Variant Inclusions

Используются для сравнительных таблиц тарифов: «что включено в каждый тариф».

### GET /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions

**Permission:** `catalog:read`

**Ответ 200:**

```json
[
  {
    "id": "inc-uuid-1",
    "title": "Доступ к видео-урокам",
    "description": "Все 120 уроков курса",
    "is_included": true,
    "sort_order": 0,
    "icon": "video",
    "group": "Обучение",
    "created_at": "2026-02-28T12:00:00Z",
    "updated_at": "2026-02-28T12:00:00Z"
  },
  {
    "id": "inc-uuid-2",
    "title": "Личный куратор",
    "description": null,
    "is_included": false,
    "sort_order": 1,
    "icon": "user",
    "group": "Поддержка",
    "created_at": "2026-02-28T12:00:00Z",
    "updated_at": "2026-02-28T12:00:00Z"
  }
]
```

---

### POST /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions

**Permission:** `catalog:write`

```json
{
  "title": "Домашние задания с проверкой",
  "description": "Персональная проверка куратором",
  "is_included": true,
  "sort_order": 2,
  "icon": "check-circle",
  "group": "Обучение"
}
```

| Поле | Тип | Обяз. | Ограничения |
|------|-----|:-----:|-------------|
| `title` | string | Да | 1–500 |
| `description` | string \| null | Нет | — |
| `is_included` | bool | Нет | default true |
| `sort_order` | int | Нет | default 0 |
| `icon` | string \| null | Нет | max 100 |
| `group` | string \| null | Нет | max 100 |

**Ответ 201:** `VariantInclusionResponse`.

---

### PATCH /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions/{inclusion_id}

**Permission:** `catalog:write`

```json
{ "is_included": false }
```

**Ответ 200:** обновлённый `VariantInclusionResponse`.

---

### DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions/{inclusion_id}

**Permission:** `catalog:write`  
**Ответ:** `204 No Content`

---

## 8. Admin API — Variant Images

### GET /api/v1/admin/products/{product_id}/variants/{variant_id}/images

**Permission:** `catalog:read`

**Ответ 200:** `VariantImageResponse[]`

```json
[
  {
    "id": "img-uuid-1",
    "url": "https://cdn.example.com/variants/red-m/front.jpg",
    "alt": "Футболка красная — вид спереди",
    "width": 1200,
    "height": 800,
    "size_bytes": 245000,
    "mime_type": "image/jpeg",
    "sort_order": 0,
    "is_cover": true,
    "created_at": "2026-02-28T12:00:00Z"
  }
]
```

---

### POST /api/v1/admin/products/{product_id}/variants/{variant_id}/images

Загрузка изображения (`multipart/form-data`).

**Permission:** `catalog:write`

| Поле | Тип | Обяз. | Описание |
|------|-----|:-----:|----------|
| `file` | File | Да | JPEG, PNG, WebP, GIF. Max 10 MB |
| `alt` | string | Нет | Alt-текст |
| `is_cover` | bool | Нет | Установить как обложку (default false) |

```bash
curl -X POST /api/v1/admin/products/{product_id}/variants/{variant_id}/images \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: {tenant_uuid}" \
  -F "file=@red-front.jpg" \
  -F "alt=Футболка красная — вид спереди" \
  -F "is_cover=true"
```

**Ответ 201:** `VariantImageResponse`.

---

### DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}/images/{image_id}

Удаляет файл из S3 и запись из БД.

**Permission:** `catalog:write`  
**Ответ:** `204 No Content`

---

## 9. Публичное API — изменения

### GET /api/v1/public/products?tenant_id={uuid}

Список продуктов теперь включает новые поля:

```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "tshirt-cotton",
      "sku": "TSHIRT-001",
      "title": "Футболка хлопковая",
      "brand": "BrandName",
      "model": null,
      "description": "Описание...",
      "product_type": "physical",
      "has_variants": true,
      "price_from": "1990.00",
      "price_to": "3500.00",
      "cover_url": "https://cdn.example.com/products/tshirt/cover.jpg"
    }
  ],
  "total": 48,
  "page": 1,
  "page_size": 20
}
```

**Новые поля:**

| Поле | Тип | Описание |
|------|-----|----------|
| `product_type` | string | Тип продукта |
| `has_variants` | boolean | Есть ли варианты |
| `price_from` | string \| null | Мин. цена вариантов (для «от X ₽»), `null` если нет вариантов с ценами |
| `price_to` | string \| null | Макс. цена вариантов |

### Логика отображения цены в списке

```typescript
const renderPrice = (product: ProductPublic) => {
  if (product.has_variants && product.price_from) {
    if (product.price_from === product.price_to) {
      return formatPrice(product.price_from, 'RUB');
    }
    return `от ${formatPrice(product.price_from, 'RUB')}`;
  }
  // Для simple product — цена из prices[] на детальной странице
  return null;
};
```

---

### GET /api/v1/public/products/{slug}?tenant_id={uuid}

Детальная карточка продукта. Когда `has_variants = true` и `variants_module` включён, в ответ добавляются `option_groups[]` и `variants[]`:

```json
{
  "id": "product-uuid",
  "slug": "tshirt-cotton",
  "sku": "TSHIRT-001",
  "title": "Футболка хлопковая",
  "brand": "BrandName",
  "model": null,
  "description": "...",
  "product_type": "physical",
  "has_variants": true,
  "price_from": "1990.00",
  "price_to": "3500.00",
  "images": [ "..." ],
  "characteristics": [ "..." ],
  "chars": [ "..." ],
  "categories": [ "..." ],
  "prices": [],
  "content_blocks": [ "..." ],

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
      "slug": "red-m",
      "title": "Красный / M",
      "sku": "TSHIRT-red-m",
      "description": null,
      "is_default": true,
      "in_stock": true,
      "sort_order": 0,
      "prices": [
        { "price_type": "regular", "amount": "2500.00", "currency": "RUB" },
        { "price_type": "sale", "amount": "1990.00", "currency": "RUB" }
      ],
      "options": {
        "color": "red",
        "size": "m"
      },
      "images": [
        {
          "url": "https://cdn.example.com/variants/red-m/front.jpg",
          "alt": "Футболка красная M",
          "sort_order": 0,
          "is_cover": true
        }
      ],
      "inclusions": []
    },
    {
      "id": "variant-uuid-2",
      "slug": "blue-l",
      "title": "Синий / L",
      "sku": "TSHIRT-blue-l",
      "description": null,
      "is_default": false,
      "in_stock": false,
      "sort_order": 1,
      "prices": [
        { "price_type": "regular", "amount": "2500.00", "currency": "RUB" }
      ],
      "options": {
        "color": "blue",
        "size": "l"
      },
      "images": [],
      "inclusions": []
    }
  ]
}
```

### Поведение в зависимости от условий

| `has_variants` | `variants_module` | `option_groups` | `variants` | `prices` (product-level) |
|:-:|:-:|:-:|:-:|:-:|
| `false` | любой | `null` | `null` | Заполнены |
| `true` | выключен | `null` | `null` | Заполнены (fallback) |
| `true` | включён | `OptionGroupPublic[]` | `VariantPublic[]` | `[]` (цены на уровне вариантов) |

**Ключевое отличие:** Для продуктов с вариантами цены живут на уровне вариантов (`variant.prices[]`), а не на уровне продукта (`product.prices[]`).

---

## 10. TypeScript-типы

```typescript
// =============================================
// Variants — полные типы (copy-paste ready)
// =============================================

// ---------- Admin: Option Groups ----------

interface OptionValueCreate {
  title: string;
  slug: string;
  sort_order?: number;
  color_hex?: string | null;
  image_url?: string | null;
}

interface OptionValueUpdate {
  title?: string;
  slug?: string;
  sort_order?: number;
  color_hex?: string | null;
  image_url?: string | null;
}

interface OptionValueResponse {
  id: string;
  title: string;
  slug: string;
  sort_order: number;
  color_hex: string | null;
  image_url: string | null;
  created_at: string;
  updated_at: string;
}

interface OptionGroupCreate {
  title: string;
  slug: string;
  display_type?: 'dropdown' | 'buttons' | 'color_swatch' | 'cards';
  sort_order?: number;
  is_required?: boolean;
  parameter_id?: string | null;
  values?: OptionValueCreate[];
}

interface OptionGroupUpdate {
  title?: string;
  slug?: string;
  display_type?: 'dropdown' | 'buttons' | 'color_swatch' | 'cards';
  sort_order?: number;
  is_required?: boolean;
  parameter_id?: string | null;
}

interface OptionGroupResponse {
  id: string;
  product_id: string;
  title: string;
  slug: string;
  display_type: 'dropdown' | 'buttons' | 'color_swatch' | 'cards';
  sort_order: number;
  is_required: boolean;
  parameter_id: string | null;
  values: OptionValueResponse[];
  created_at: string;
  updated_at: string;
}

// ---------- Admin: Variant Prices ----------

interface VariantPriceCreate {
  price_type?: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: number;  // decimal
  currency?: string;
  valid_from?: string | null;  // "YYYY-MM-DD"
  valid_to?: string | null;
}

interface VariantPriceUpdate {
  price_type?: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount?: number;
  currency?: string;
  valid_from?: string | null;
  valid_to?: string | null;
}

interface VariantPriceResponse {
  id: string;
  price_type: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: string;   // decimal as string
  currency: string;
  valid_from: string | null;
  valid_to: string | null;
  created_at: string;
  updated_at: string;
}

// ---------- Admin: Variant Inclusions ----------

interface VariantInclusionCreate {
  title: string;
  description?: string | null;
  is_included?: boolean;
  sort_order?: number;
  icon?: string | null;
  group?: string | null;
}

interface VariantInclusionUpdate {
  title?: string;
  description?: string | null;
  is_included?: boolean;
  sort_order?: number;
  icon?: string | null;
  group?: string | null;
}

interface VariantInclusionResponse {
  id: string;
  title: string;
  description: string | null;
  is_included: boolean;
  sort_order: number;
  icon: string | null;
  group: string | null;
  created_at: string;
  updated_at: string;
}

// ---------- Admin: Variant Images ----------

interface VariantImageResponse {
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

// ---------- Admin: Variants ----------

interface VariantCreate {
  sku: string;
  slug: string;
  title: string;
  description?: string | null;
  is_default?: boolean;
  is_active?: boolean;
  sort_order?: number;
  stock_quantity?: number | null;
  weight?: number | null;
  option_value_ids?: string[];
}

interface VariantUpdate {
  sku?: string;
  slug?: string;
  title?: string;
  description?: string | null;
  is_default?: boolean;
  is_active?: boolean;
  sort_order?: number;
  stock_quantity?: number | null;
  weight?: number | null;
  option_value_ids?: string[];
}

interface VariantResponse {
  id: string;
  product_id: string;
  tenant_id: string;
  sku: string;
  slug: string;
  title: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
  stock_quantity: number | null;
  weight: string | null;  // decimal as string
  created_at: string;
  updated_at: string;
}

interface VariantDetailResponse extends VariantResponse {
  prices: VariantPriceResponse[];
  option_values: OptionValueResponse[];
  inclusions: VariantInclusionResponse[];
  images: VariantImageResponse[];
}

// ---------- Admin: Matrix generation ----------

interface VariantGenerateRequest {
  option_group_ids: string[];  // min 1
  base_price?: number | null;
}

interface VariantGenerateResponse {
  created_count: number;
  variants: VariantResponse[];
}

// ---------- Public: Option Groups ----------

interface OptionValuePublic {
  title: string;
  slug: string;
  color_hex: string | null;
  image_url: string | null;
}

interface OptionGroupPublic {
  title: string;
  slug: string;
  display_type: 'dropdown' | 'buttons' | 'color_swatch' | 'cards';
  values: OptionValuePublic[];
}

// ---------- Public: Variants ----------

interface VariantPricePublic {
  price_type: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: string;   // decimal as string: "2500.00"
  currency: string;
}

interface VariantInclusionPublic {
  title: string;
  description: string | null;
  is_included: boolean;
  icon: string | null;
  group: string | null;
}

interface VariantImagePublic {
  url: string;
  alt: string | null;
  sort_order: number;
  is_cover: boolean;
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
  options: Record<string, string>;  // { "color": "red", "size": "m" }
  images: VariantImagePublic[];
  inclusions: VariantInclusionPublic[];
}

// ---------- Public: Updated Product ----------

interface ProductPublicUpdated {
  id: string;
  slug: string;
  sku: string;
  title: string;
  brand: string | null;
  model: string | null;
  description: string | null;
  product_type: 'physical' | 'digital' | 'service' | 'course' | 'subscription';
  has_variants: boolean;
  price_from: string | null;   // decimal as string
  price_to: string | null;
  cover_url: string | null;
}

interface ProductDetailWithVariants {
  id: string;
  slug: string;
  sku: string;
  title: string;
  brand: string | null;
  model: string | null;
  description: string | null;
  product_type: 'physical' | 'digital' | 'service' | 'course' | 'subscription';
  has_variants: boolean;
  price_from: string | null;
  price_to: string | null;
  images: ProductImage[];
  characteristics: ProductCharacteristic[];
  chars: ProductChar[];
  categories: CategoryPublic[];
  prices: ProductPrice[];
  content_blocks: ContentBlock[];
  // Variants data (null when has_variants=false or variants_module disabled)
  option_groups: OptionGroupPublic[] | null;
  variants: VariantPublic[] | null;
}
```

---

## 11. Сценарии UI

### Сценарий 1: Физический товар с цветом и размером

**Продукт:** Футболка хлопковая (`product_type: "physical"`, `has_variants: true`)

**Группы опций:**
- Цвет (`color_swatch`): Красный, Синий, Зелёный
- Размер (`buttons`): S, M, L, XL

**Варианты:** 12 штук (3 цвета × 4 размера), каждый со своим SKU, остатком, ценой.

**UI:**
1. В списке каталога: «от 1 990 ₽» (из `price_from`)
2. На карточке: два ряда выбора — цветные кружки и кнопки размеров
3. При выборе Красный + M → показать цену, остаток, фото этого варианта
4. Недоступные комбинации (out of stock) — заблокированы

---

### Сценарий 2: Онлайн-курс с тарифами

**Продукт:** Курс «Python с нуля» (`product_type: "course"`, `has_variants: true`)

**Группы опций:**
- Тарифный план (`cards`): Базовый, Премиум, VIP

**Варианты:**
- Базовый: 15 000 ₽ — доступ к видео
- Премиум: 35 000 ₽ — видео + домашки + чат
- VIP: 75 000 ₽ — всё + личный куратор

**Inclusions для сравнительной таблицы:**

| Фича | Базовый | Премиум | VIP |
|------|:-------:|:-------:|:---:|
| Доступ к видео-урокам | ✅ | ✅ | ✅ |
| Домашние задания | ❌ | ✅ | ✅ |
| Чат с группой | ❌ | ✅ | ✅ |
| Личный куратор | ❌ | ❌ | ✅ |
| Сертификат | ❌ | ✅ | ✅ |

**UI:**
1. Три карточки тарифов с ценами
2. Сравнительная таблица из `inclusions` (группировка по `group`)
3. Кнопка «Купить» у каждого тарифа

---

### Сценарий 3: Услуга с тарифами

**Продукт:** SEO-продвижение (`product_type: "service"`, `has_variants: true`)

**Группы опций:**
- Пакет (`cards`): Стартовый, Бизнес, Корпоративный

**Варианты** с ежемесячной ценой и набором включённых услуг.

**UI:** аналогичен курсу — карточки + сравнительная таблица.

---

### Сценарий 4: Простой продукт без вариантов (обратная совместимость)

**Продукт:** Кабель USB-C (`product_type: "physical"`, `has_variants: false`)

**Данные:**
- `option_groups: null`
- `variants: null`
- `prices: [{ price_type: "regular", amount: "590.00", currency: "RUB" }]`

**UI:** обычная карточка товара, как до введения вариантов. Цена отображается из `prices[]` на уровне продукта.

---

## 12. Логика селектора вариантов

### Поиск варианта по выбранным опциям

```typescript
const findVariant = (
  variants: VariantPublic[],
  selected: Record<string, string>,  // { color: "red", size: "m" }
): VariantPublic | undefined => {
  return variants.find(v =>
    Object.entries(selected).every(
      ([groupSlug, valueSlug]) => v.options[groupSlug] === valueSlug,
    ),
  );
};
```

### Определение доступных значений (зависимые опции)

Когда пользователь выбрал Цвет = Красный, нужно определить, какие Размеры доступны для красных вариантов:

```typescript
const getAvailableValues = (
  variants: VariantPublic[],
  groupSlug: string,
  selected: Record<string, string>,  // текущий выбор без groupSlug
): Set<string> => {
  const available = new Set<string>();

  for (const variant of variants) {
    if (!variant.in_stock) continue;

    const matchesOtherSelections = Object.entries(selected).every(
      ([slug, value]) => slug === groupSlug || variant.options[slug] === value,
    );

    if (matchesOtherSelections && variant.options[groupSlug]) {
      available.add(variant.options[groupSlug]);
    }
  }

  return available;
};

// Пример: пользователь выбрал color=red
const availableSizes = getAvailableValues(variants, 'size', { color: 'red' });
// → Set { "s", "m", "l" }  (xl нет в наличии для красного)
```

### Отображение статуса остатков

```typescript
const getStockLabel = (variant: VariantPublic): string => {
  if (!variant.in_stock) return 'Нет в наличии';
  return 'В наличии';
};
```

### Отображение цены

```typescript
const getVariantPrice = (variant: VariantPublic): {
  regular: string | null;
  sale: string | null;
  hasSale: boolean;
} => {
  const regular = variant.prices.find(p => p.price_type === 'regular');
  const sale = variant.prices.find(p => p.price_type === 'sale');
  return {
    regular: regular?.amount ?? null,
    sale: sale?.amount ?? null,
    hasSale: !!sale,
  };
};
```

### Переключение галереи изображений

```typescript
const getVariantImages = (
  variant: VariantPublic | undefined,
  productImages: ProductImage[],
): (VariantImagePublic | ProductImage)[] => {
  if (variant?.images?.length) {
    return variant.images;
  }
  return productImages;
};
```

### React hook для селектора

```typescript
const useVariantSelector = (
  optionGroups: OptionGroupPublic[],
  variants: VariantPublic[],
) => {
  const defaultVariant = variants.find(v => v.is_default) ?? variants[0];
  const [selected, setSelected] = useState<Record<string, string>>(
    defaultVariant?.options ?? {},
  );

  const currentVariant = useMemo(
    () => findVariant(variants, selected),
    [variants, selected],
  );

  const selectOption = useCallback((groupSlug: string, valueSlug: string) => {
    setSelected(prev => ({ ...prev, [groupSlug]: valueSlug }));
  }, []);

  const availableByGroup = useMemo(() => {
    const result: Record<string, Set<string>> = {};
    for (const group of optionGroups) {
      const otherSelected = { ...selected };
      delete otherSelected[group.slug];
      result[group.slug] = getAvailableValues(variants, group.slug, otherSelected);
    }
    return result;
  }, [optionGroups, variants, selected]);

  return {
    selected,
    currentVariant,
    selectOption,
    availableByGroup,
  };
};
```

### Полный пример компонента

```tsx
const VariantSelector = ({
  product,
}: {
  product: ProductDetailWithVariants;
}) => {
  if (!product.option_groups || !product.variants) {
    return null;
  }

  const {
    selected,
    currentVariant,
    selectOption,
    availableByGroup,
  } = useVariantSelector(product.option_groups, product.variants);

  return (
    <div>
      {product.option_groups.map(group => (
        <div key={group.slug}>
          <label>{group.title}</label>

          {group.display_type === 'color_swatch' && (
            <div className="color-swatches">
              {group.values.map(val => {
                const available = availableByGroup[group.slug]?.has(val.slug);
                return (
                  <button
                    key={val.slug}
                    className={[
                      'swatch',
                      selected[group.slug] === val.slug && 'active',
                      !available && 'disabled',
                    ].filter(Boolean).join(' ')}
                    style={{ backgroundColor: val.color_hex ?? '#ccc' }}
                    onClick={() => available && selectOption(group.slug, val.slug)}
                    disabled={!available}
                    title={val.title}
                  />
                );
              })}
            </div>
          )}

          {group.display_type === 'buttons' && (
            <div className="button-group">
              {group.values.map(val => {
                const available = availableByGroup[group.slug]?.has(val.slug);
                return (
                  <button
                    key={val.slug}
                    className={[
                      'btn-option',
                      selected[group.slug] === val.slug && 'active',
                      !available && 'disabled',
                    ].filter(Boolean).join(' ')}
                    onClick={() => available && selectOption(group.slug, val.slug)}
                    disabled={!available}
                  >
                    {val.title}
                  </button>
                );
              })}
            </div>
          )}

          {group.display_type === 'dropdown' && (
            <select
              value={selected[group.slug] ?? ''}
              onChange={e => selectOption(group.slug, e.target.value)}
            >
              {group.values.map(val => (
                <option
                  key={val.slug}
                  value={val.slug}
                  disabled={!availableByGroup[group.slug]?.has(val.slug)}
                >
                  {val.title}
                </option>
              ))}
            </select>
          )}
        </div>
      ))}

      {currentVariant && (
        <div className="variant-info">
          <div className="price">
            {(() => {
              const { regular, sale, hasSale } = getVariantPrice(currentVariant);
              if (hasSale && regular && sale) {
                return (
                  <>
                    <span className="price-old">{formatPrice(regular, 'RUB')}</span>
                    <span className="price-sale">{formatPrice(sale, 'RUB')}</span>
                  </>
                );
              }
              if (regular) return <span>{formatPrice(regular, 'RUB')}</span>;
              return <span>Цена по запросу</span>;
            })()}
          </div>
          <div className="stock">{getStockLabel(currentVariant)}</div>
          <div className="sku">Артикул: {currentVariant.sku}</div>
        </div>
      )}
    </div>
  );
};
```

---

## Типичный flow для frontend-разработчика

### Админ-панель — управление вариантами

```
1. Включить варианты для продукта:
   PATCH /admin/products/{id}                              → { has_variants: true, product_type: "physical" }

2. Создать группы опций:
   POST /admin/products/{id}/option-groups                 → { title: "Цвет", slug: "color", display_type: "color_swatch", values: [...] }
   POST /admin/products/{id}/option-groups                 → { title: "Размер", slug: "size", display_type: "buttons", values: [...] }

3. Сгенерировать матрицу вариантов:
   POST /admin/products/{id}/variants/generate             → { option_group_ids: ["...", "..."], base_price: 2500 }

4. Настроить цены:
   POST /admin/products/{id}/variants/{vid}/prices         → { price_type: "regular", amount: 2500 }
   POST /admin/products/{id}/variants/{vid}/prices         → { price_type: "sale", amount: 1990 }

5. Загрузить фото вариантов:
   POST /admin/products/{id}/variants/{vid}/images         → multipart (file + alt)

6. Для курсов — добавить inclusions:
   POST /admin/products/{id}/variants/{vid}/inclusions     → { title: "Доступ к видео", is_included: true, group: "Обучение" }
```

### Клиентский фронт — показ вариантов

```
1. Список каталога:
   GET /public/products                                    → product_type, has_variants, price_from, price_to

2. Карточка продукта:
   GET /public/products/{slug}                             → option_groups[], variants[]

3. На фронте:
   → Рендерить селектор опций (color_swatch / buttons / dropdown / cards)
   → Найти вариант по выбранным опциям через options map
   → Показать цену, остаток, изображения текущего варианта
   → Для курсов/услуг: показать сравнительную таблицу inclusions
```
