# Административная панель — Каталог продуктов

> **Назначение**: Руководство для фронтенд-разработчика по реализации раздела «Каталог» в административной панели.  
> **Версия бэкенда**: 2026-02-26 (ветка `feat/product-catalog`)  
> **Полная API-документация**: [`docs/api/endpoints/19-catalog.md`](../api/endpoints/19-catalog.md)  
> **Публичный фронт**: [`CLIENT_CATALOG_FRONTEND.md`](./CLIENT_CATALOG_FRONTEND.md)

---

## Содержание

1. [Авторизация и заголовки](#1-авторизация-и-заголовки)
2. [Feature flags — когда показывать каталог](#2-feature-flags)
3. [RBAC — права доступа](#3-rbac)
4. [Навигация и структура раздела](#4-навигация-и-структура)
5. [Раздел: Единицы измерения (UOM)](#5-uom)
6. [Раздел: Категории](#6-категории)
7. [Раздел: Параметры (словарь характеристик)](#7-параметры)
8. [Раздел: Список продуктов](#8-список-продуктов)
9. [Страница продукта: основные данные](#9-страница-продукта--основные-данные)
10. [Вкладка: Характеристики (нормализованные)](#10-вкладка-характеристики)
11. [Вкладка: Изображения](#11-вкладка-изображения)
12. [Вкладка: Цены](#12-вкладка-цены)
13. [Вкладка: Контент-блоки](#13-вкладка-контент-блоки)
14. [Вкладка: Привязка к категориям](#14-вкладка-привязка-к-категориям)
15. [Вкладка: Алиасы и Аналоги](#15-вкладка-алиасы-и-аналоги)
16. [Заявки на продукт (Leads)](#16-заявки-на-продукт)
17. [Тип продукта и вариативность](#17-тип-продукта)
18. [Вкладка: Группы опций](#18-вкладка-группы-опций)
19. [Вкладка: Вариации](#19-вкладка-вариации)
20. [Вкладка: Цены вариантов](#20-вкладка-цены-вариантов)
21. [Вкладка: Включения (тарифы)](#21-вкладка-включения)
22. [Вкладка: Изображения вариантов](#22-вкладка-изображения-вариантов)
23. [TypeScript-типы](#23-typescript-типы)
24. [Типовые ошибки и их обработка](#24-обработка-ошибок)

---

## 1. Авторизация и заголовки

Все admin-запросы требуют двух заголовков:

```typescript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'X-Tenant-ID': tenantId,         // UUID тенанта из useTenantStore
  'Content-Type': 'application/json',
};
```

`tenantId` получается при загрузке приложения через `GET /api/v1/public/tenants/by-domain/{hostname}` и хранится в Zustand-сторе. Подробнее — [`ADMIN_FRONTEND_READINESS_CHECKLIST.md`](./ADMIN_FRONTEND_READINESS_CHECKLIST.md).

---

## 2. Feature Flags

Раздел «Каталог» отображается **только если** для тенанта включён флаг `catalog_module`.

```typescript
// Проверка из профиля пользователя или отдельным запросом:
// GET /api/v1/admin/feature-flags
// Response: [{ "name": "catalog_module", "is_enabled": true }, ...]

const isCatalogEnabled = featureFlags.find(f => f.name === 'catalog_module')?.is_enabled ?? false;

// В роутере:
if (!isCatalogEnabled) {
  return <Navigate to="/dashboard" />;
}
```

Если флаг выключен — все catalog-эндпоинты вернут `403 Forbidden`.

**Дополнительный флаг: `variants_module`** — управляет видимостью полей `product_type`, `has_variants`, `price_from`/`price_to` и всех вкладок вариантов (группы опций, вариации, цены вариантов, включения, изображения вариантов). Проверяется аналогично:

```typescript
const isVariantsEnabled = featureFlags.find(f => f.name === 'variants_module')?.is_enabled ?? false;
```

---

## 3. RBAC

```typescript
// Права, используемые в каталоге:
type CatalogPermission =
  | 'catalog:read'    // просмотр
  | 'catalog:create'  // создание
  | 'catalog:update'  // редактирование
  | 'catalog:delete'  // удаление

// Права приходят в JWT-токене или из GET /api/v1/auth/me
// user.permissions: string[]

const can = (permission: CatalogPermission) =>
  user.permissions.includes(permission);

// Пример:
{can('catalog:create') && <Button onClick={createProduct}>+ Товар</Button>}
```

**Роли по умолчанию:**
| Роль | catalog:read | catalog:create | catalog:update | catalog:delete |
|------|:---:|:---:|:---:|:---:|
| `site_owner` | ✅ | ✅ | ✅ | ✅ |
| `content_manager` | ✅ | ✅ | ✅ | ✅ |
| `editor` | ✅ | ❌ | ❌ | ❌ |

---

## 4. Навигация и структура

```
/admin/catalog/
  /admin/catalog/uom                → Единицы измерения
  /admin/catalog/categories         → Дерево категорий
  /admin/catalog/parameters         → Словарь параметров (характеристик)
  /admin/catalog/parameters/new     → Создание параметра
  /admin/catalog/parameters/:id     → Карточка параметра (значения, категории)
  /admin/catalog/products           → Список продуктов
  /admin/catalog/products/new       → Создание продукта
  /admin/catalog/products/:id       → Карточка продукта
    → вкладки: Основное | Характеристики | Изображения | Цены | Контент | Категории | Алиасы
    → (если variants_module) : Группы опций | Вариации | Цены вариантов | Включения | Изобр. вариантов
```

Боковая навигация показывает «Каталог» только если `catalog_module` включён.

**Порядок в сайдбаре:**
1. Единицы измерения (справочник — нужен для параметров)
2. Категории (справочник — нужен для параметров и продуктов)
3. Параметры (словарь — нужен для характеристик продуктов)
4. Продукты (основной раздел)

---

## 5. UOM

**Страница:** `/admin/catalog/uom`

Справочная таблица единиц измерения. Нужна при создании/редактировании продукта (поле `uom_id`).

### Загрузка

```typescript
// GET /api/v1/admin/uoms
const fetchUoms = async (): Promise<UOM[]> => {
  const res = await fetch('/api/v1/admin/uoms', { headers });
  return res.json(); // массив UOM[]
};
```

### Создание

```typescript
// POST /api/v1/admin/uoms
const createUom = async (data: { name: string; code: string; symbol?: string }) => {
  const res = await fetch('/api/v1/admin/uoms', {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });
  if (!res.ok) throw await res.json();
  return res.json(); // UOM
};
```

**Валидация:**
- `name`: обязательно, 1–100 символов
- `code`: обязательно, 1–20 символов, уникальный для тенанта
- `symbol`: необязательно, max 20 символов

### Обновление / деактивация

```typescript
// PATCH /api/v1/admin/uoms/{uom_id}
await fetch(`/api/v1/admin/uoms/${uomId}`, {
  method: 'PATCH',
  headers,
  body: JSON.stringify({ is_active: false }), // или любые другие поля
});
```

---

## 6. Категории

**Страница:** `/admin/catalog/categories`

### Получить дерево

```typescript
// GET /api/v1/admin/categories/tree  — все категории, без пагинации
// Используй для рендера дерева в сайдбаре или drag-and-drop
const { items, total } = await fetchJson('/api/v1/admin/categories/tree');

// GET /api/v1/admin/categories?page=1&pageSize=20  — пагинация
// Используй для таблицы с фильтрами
```

### Создание категории

```typescript
// POST /api/v1/admin/categories
const data = {
  title: 'Электрооборудование',
  slug: 'electrical',         // URL-friendly, уникальный для тенанта
  parent_id: null,            // или UUID родительской категории
  description: null,
  image_url: null,
  is_active: true,
  sort_order: 0,
};
```

### Обновление (optimistic locking)

```typescript
// PATCH /api/v1/admin/categories/{category_id}
// ОБЯЗАТЕЛЬНО передавай version — иначе 409 Conflict
const data = {
  title: 'Новое название',
  version: category.version,  // текущая версия объекта
};
```

> **Важно:** поле `version` — защита от конкурентных правок. Если два пользователя открыли карточку, и один уже сохранил изменения — второй получит `409 Conflict`. Покажи сообщение: «Данные изменились. Обновите страницу».

### Удаление (soft)

```typescript
// DELETE /api/v1/admin/categories/{category_id}
// Response: 204 No Content
// Категория скрывается, данные не удаляются физически
```

---

## 7. Параметры (словарь характеристик)

**Страница:** `/admin/catalog/parameters`

> **Что это:** Центральный словарь всех характеристик товаров (цвет, вес, напряжение и т.д.). Параметры создаются один раз и переиспользуются для любого количества продуктов. Параметры с `is_filterable = true` отображаются в публичных фильтрах каталога.

### 7.1 Список параметров

```typescript
// GET /api/v1/admin/parameters?page=1&page_size=20
// Дополнительные фильтры:
//   search    — поиск по имени (max 200)
//   valueType — фильтр по типу: "string" | "number" | "enum" | "bool" | "range"
//   scope     — фильтр по scope: "global" | "category"

const fetchParameters = async (params: ParameterListParams) => {
  const qs = buildQueryString(params);
  const res = await fetch(`/api/v1/admin/parameters?${qs}`, { headers });
  return res.json(); // { items: Parameter[], total, page, page_size }
};
```

**Колонки таблицы:**
| Колонка | Поле | Примечание |
|---------|------|------------|
| Название | `name` | ссылка на карточку |
| Slug | `slug` | авто-генерируемый URL-slug |
| Тип | `value_type` | тег: `enum`, `number`, `string`, `bool`, `range` |
| Фильтруемый | `is_filterable` | toggle-переключатель |
| Scope | `scope` | `global` / `category` |
| Кол-во значений | `values.length` | только для `enum`-типа |
| Категории | `category_ids.length` | привязанные категории |
| Статус | `is_active` | зелёный/серый тег |
| Действия | — | Edit / Deactivate |

### 7.2 Создание параметра

```typescript
// POST /api/v1/admin/parameters
interface ParameterCreate {
  name: string;              // обязательно, 1–255
  slug?: string;             // опционально, авто-генерируется из name если не указан
  value_type: 'string' | 'number' | 'enum' | 'bool' | 'range';  // обязательно
  uom_id?: string;           // UUID единицы измерения (для number/range)
  scope?: 'global' | 'category';  // default "global"
  description?: string;
  constraints?: object;      // JSON — ограничения: { min: 0, max: 100 } и т.д.
  is_filterable?: boolean;   // default false — показывать ли в публичных фильтрах
  is_required?: boolean;     // default false
  sort_order?: number;       // default 0
  category_ids?: string[];   // UUID категорий для привязки
  values?: ParameterValueCreate[];  // начальные значения (только для enum)
}

interface ParameterValueCreate {
  label: string;   // обязательно, 1–255
  slug?: string;   // авто-генерируется из label
  code?: string;   // необязательный внешний код (max 100)
  sort_order?: number;
}

// Пример: создать параметр "Цвет" типа enum
const newParam = await createParameter({
  name: 'Цвет',
  value_type: 'enum',
  is_filterable: true,
  category_ids: [electronicsId, clothingId],
  values: [
    { label: 'Красный' },
    { label: 'Синий' },
    { label: 'Зелёный' },
  ],
});
// slug будет автоматически "tsvet" (транслит), values получат slug "krasnyj", "sinij" и т.д.

// Пример: создать параметр "Вес" типа number
const weightParam = await createParameter({
  name: 'Вес',
  value_type: 'number',
  uom_id: kgUomId,
  is_filterable: true,
});
// Response 201: Parameter (полный объект с id, slug, values, category_ids)
```

### 7.3 Карточка параметра

**URL:** `/admin/catalog/parameters/:id`

```typescript
// GET /api/v1/admin/parameters/{parameter_id}
const param = await fetchJson(`/api/v1/admin/parameters/${id}`);
// Response: Parameter (включая values[] и category_ids[])
```

**Структура карточки — три секции:**

```
┌──────────────────────────────────────────────────────────┐
│  ОСНОВНЫЕ ДАННЫЕ                                          │
│  Название:    [Цвет                ]                      │
│  Slug:        [tsvet               ] (авто / ручное)      │
│  Тип:         enum ▼  (неизменяемый после создания)       │
│  Scope:       global ▼                                    │
│  Ед. изм.:    [— не выбрано —] ▼                         │
│  Описание:    [                    ]                      │
│  ☑ Фильтруемый   ☐ Обязательный   Порядок: [0]          │
│                                             [Сохранить]   │
├──────────────────────────────────────────────────────────┤
│  ЗНАЧЕНИЯ (только для enum)               [+ Добавить]   │
│  ─────────────────────────────────────────────────────   │
│  Метка          Slug          Код     Порядок  Статус     │
│  Красный        krasnyj       RED     0        ✅  [✎][✕] │
│  Синий          sinij         BLUE    1        ✅  [✎][✕] │
│  Зелёный        zelenyj       GRN     2        ✅  [✎][✕] │
├──────────────────────────────────────────────────────────┤
│  ПРИВЯЗКА К КАТЕГОРИЯМ                                    │
│  Если scope = "category", параметр показывается           │
│  в фильтрах только для привязанных категорий.             │
│  ☑ Электрооборудование                                   │
│  ☑ Одежда                                                │
│  ☐ Инструменты                                           │
│                                        [Сохранить связи]  │
└──────────────────────────────────────────────────────────┘
```

### 7.4 Обновление параметра

```typescript
// PATCH /api/v1/admin/parameters/{parameter_id}
interface ParameterUpdate {
  name?: string;
  slug?: string;
  description?: string;
  uom_id?: string | null;
  scope?: 'global' | 'category';
  constraints?: object;
  is_filterable?: boolean;
  is_required?: boolean;
  sort_order?: number;
  is_active?: boolean;
}
// Response: Parameter
```

> **Важно:** Поле `value_type` нельзя менять после создания (логическое ограничение — не меняй тип на фронте, если параметр уже используется продуктами).

### 7.5 Управление значениями (для enum)

```typescript
// Добавить значение
// POST /api/v1/admin/parameters/{parameter_id}/values
const newValue = await fetch(`/api/v1/admin/parameters/${paramId}/values`, {
  method: 'POST',
  headers,
  body: JSON.stringify({ label: 'Жёлтый', code: 'YLW' }),
});
// Response 201: ParameterValue (id, slug автогенерирован)

// Обновить значение
// PATCH /api/v1/admin/parameters/{parameter_id}/values/{value_id}
await fetch(`/api/v1/admin/parameters/${paramId}/values/${valueId}`, {
  method: 'PATCH',
  headers,
  body: JSON.stringify({ label: 'Тёмно-красный', slug: 'dark-red' }),
});

// Удалить значение
// DELETE /api/v1/admin/parameters/{parameter_id}/values/{value_id}
// Response: 204
// ВНИМАНИЕ: Удаление значения удалит все связанные характеристики продуктов!
```

### 7.6 Привязка параметра к категориям

```typescript
// PUT /api/v1/admin/parameters/{parameter_id}/categories
// Полная замена списка категорий (replace all)
await fetch(`/api/v1/admin/parameters/${paramId}/categories`, {
  method: 'PUT',
  headers,
  body: JSON.stringify({
    category_ids: [cat1Id, cat2Id, cat3Id],
  }),
});
// Response: { count: 3 }
```

> Привязка к категориям определяет, для каких категорий параметр отображается в фильтрах на публичном сайте. Если `scope = "global"` — параметр всегда виден. Если `scope = "category"` — только для привязанных категорий.

### 7.7 Деактивация параметра

```typescript
// DELETE /api/v1/admin/parameters/{parameter_id}
// Soft archive: is_active = false, параметр скрывается из фильтров
// Response: 204
```

### 7.8 Типы параметров — что выбрать

| value_type | Описание | Пример | Виджет на фронте | Виджет в фильтре |
|------------|----------|--------|------------------|-------------------|
| `enum` | Предопределённый список значений | Цвет, Материал, Бренд | Select / Multi-select | Чекбоксы |
| `number` | Числовое значение | Вес, Мощность, Длина | Input number | Range slider |
| `string` | Произвольный текст | Артикул поставщика, Описание | Input text | — (обычно не фильтруется) |
| `bool` | Да / Нет | Есть WiFi, Влагозащита | Toggle / Checkbox | Checkbox |
| `range` | Диапазон min–max | Рабочая температура | 2× Input number | Range slider |

---

## 8. Список продуктов

**Страница:** `/admin/catalog/products`

### Загрузка с фильтрами

```typescript
// GET /api/v1/admin/products
interface ProductListParams {
  page?: number;
  pageSize?: number;
  search?: string;       // поиск по title, sku, brand, model (max 200)
  brand?: string;        // фильтр по бренду (max 255)
  category_id?: string;  // UUID категории
  isActive?: boolean;
}

const fetchProducts = async (params: ProductListParams) => {
  const qs = buildQueryString(params);
  const res = await fetch(`/api/v1/admin/products?${qs}`, { headers });
  return res.json(); // { items: Product[], total, page, page_size }
};
```

**Колонки таблицы:**
| Колонка | Поле | Примечание |
|---------|------|------------|
| Фото | `images[0].url` | первое изображение или заглушка |
| Название | `title` | ссылка на карточку |
| SKU | `sku` | |
| Бренд | `brand` | |
| Статус | `is_active` | зелёный/серый тег |
| Категория | из relations | если loaded |
| Действия | — | Edit / Delete |

### Создание продукта

```typescript
// POST /api/v1/admin/products
interface ProductCreate {
  sku: string;             // уникальный в тенанте, 1–100
  slug: string;            // URL-friendly, уникальный в тенанте, 1–255
  title: string;           // 1–500
  brand?: string;          // max 255
  model?: string;          // max 255
  description?: string;    // HTML или plain text
  uom_id?: string;         // UUID из справочника UOM
  is_active?: boolean;     // default true
  category_ids?: string[]; // UUID категорий для привязки при создании
}
// Response 201: Product
```

### Удаление (soft)

```typescript
// DELETE /api/v1/admin/products/{product_id}
// Response: 204 No Content
```

---

## 9. Страница продукта — основные данные

**URL:** `/admin/catalog/products/:id`

Страница с вкладками. Сначала загружается сам продукт:

```typescript
// GET /api/v1/admin/products/{product_id}?include=aliases,categories,prices
// include — опциональный, подгружает отношения через запятую
// Допустимые include: aliases, categories, prices
const product = await fetchJson(`/api/v1/admin/products/${id}?include=aliases,categories,prices`);
```

### Форма редактирования

```typescript
// PATCH /api/v1/admin/products/{product_id}
interface ProductUpdate {
  sku?: string;
  slug?: string;
  title?: string;
  brand?: string;
  model?: string;
  description?: string;
  uom_id?: string | null;
  is_active?: boolean;
  version: number;       // ОБЯЗАТЕЛЬНО — optimistic locking
}
```

**UI-рекомендации:**
- `slug` — автогенерируй из `title` (translit + kebab-case), но разреши ручное редактирование
- `description` — Rich Text / WYSIWYG редактор (HTML)
- `uom_id` — `<Select>` из списка `GET /admin/uoms`
- `version` — скрытое поле, обновляй из ответа после сохранения

---

## 10. Вкладка: Характеристики (нормализованные)

> **ОБНОВЛЕНО 2026-02-26.** Старая EAV-система (свободные `name`/`value_text`) заменена на нормализованную — характеристики привязываются к словарю параметров. Это обеспечивает переиспользуемость, единообразие и фасетную фильтрацию.

### 10.1 Загрузка характеристик продукта

```typescript
// GET /api/v1/admin/products/{product_id}/characteristics
// Response: ProductCharacteristic[]

interface ProductCharacteristic {
  id: string;
  product_id: string;
  parameter_id: string;
  parameter_value_id: string | null;   // UUID значения (для enum)
  value_text: string | null;           // для string-типа
  value_number: number | null;         // для number/range
  value_bool: boolean | null;          // для bool
  uom_id: string | null;              // единица измерения (переопределение)
  source_type: 'manual' | 'import' | 'system';
  is_locked: boolean;                  // заблокированная характеристика (системная)
  created_at: string;
  updated_at: string;
}

const chars = await fetchJson(`/api/v1/admin/products/${id}/characteristics`);
```

### 10.2 Привязка характеристики

```typescript
// POST /api/v1/admin/products/{product_id}/characteristics
// Upsert: если характеристика с таким parameter_id уже есть — обновляется

interface ProductCharacteristicCreate {
  parameter_id: string;                // UUID параметра из словаря (обязательно)
  parameter_value_id?: string;         // UUID значения (для enum)
  value_text?: string;                 // для string
  value_number?: number;               // для number/range
  value_bool?: boolean;                // для bool
  uom_id?: string;                     // переопределить UOM (опционально)
  source_type?: 'manual' | 'import' | 'system';  // default "manual"
}

// Пример: привязать цвет "Красный" к продукту
await fetch(`/api/v1/admin/products/${id}/characteristics`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    parameter_id: colorParamId,
    parameter_value_id: redValueId,
  }),
});
// Response 201: ProductCharacteristic

// Пример: установить вес = 2.5 кг
await fetch(`/api/v1/admin/products/${id}/characteristics`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    parameter_id: weightParamId,
    value_number: 2.5,
  }),
});
```

### 10.3 Bulk-обновление (рекомендуется)

Все характеристики продукта обновляются одним запросом. Для enum-параметров поддерживается множественный выбор через `parameter_value_ids`.

```typescript
// PUT /api/v1/admin/products/{product_id}/characteristics/bulk

interface ProductCharacteristicBulkItem {
  parameter_id: string;
  parameter_value_ids?: string[];   // для enum: список UUID значений (мульти-выбор)
  value_text?: string;              // для string
  value_number?: number;            // для number/range
  value_bool?: boolean;             // для bool
  uom_id?: string;
}

interface ProductCharacteristicBulkCreate {
  characteristics: ProductCharacteristicBulkItem[];
}

// Пример: задать цвета (красный + синий) и вес для продукта
await fetch(`/api/v1/admin/products/${id}/characteristics/bulk`, {
  method: 'PUT',
  headers,
  body: JSON.stringify({
    characteristics: [
      {
        parameter_id: colorParamId,
        parameter_value_ids: [redValueId, blueValueId],  // мульти-выбор
      },
      {
        parameter_id: weightParamId,
        value_number: 2.5,
      },
      {
        parameter_id: wifiParamId,
        value_bool: true,
      },
    ],
  }),
});
// Response: { created: 3, updated: 1, deleted: 0 }
```

> **Логика bulk:** Для каждого `parameter_id` в списке — старые значения заменяются новыми. Параметры, которых нет в массиве, остаются без изменений. Для удаления всех значений параметра — используйте DELETE endpoint.

### 10.4 Удаление характеристики

```typescript
// DELETE /api/v1/admin/products/{product_id}/characteristics/{parameter_id}
// Удаляет ВСЕ значения данного параметра для продукта
// Заблокированные (is_locked) характеристики не удаляются
// Response: 204

await fetch(`/api/v1/admin/products/${id}/characteristics/${paramId}`, {
  method: 'DELETE',
  headers,
});
```

### 10.5 UI — рекомендуемый дизайн вкладки

```
┌──────────────────────────────────────────────────────────────────┐
│  ХАРАКТЕРИСТИКИ ПРОДУКТА                   [+ Добавить параметр] │
│  ────────────────────────────────────────────────────────────── │
│                                                                  │
│  Параметр         Тип      Значение                      [✕]    │
│  ─────────────────────────────────────────────────────────────── │
│  Цвет             enum     [✓ Красный] [✓ Синий] [Зелёный]  [✕] │
│  Вес              number   [2.5] кг                          [✕] │
│  WiFi             bool     [✓]                               [✕] │
│  Описание мат.    string   [Нержавеющая сталь 304]          [✕] │
│                                                                  │
│                                          [Сохранить всё (bulk)]  │
└──────────────────────────────────────────────────────────────────┘
```

**Алгоритм работы UI:**
1. При открытии вкладки: `GET /admin/products/{id}/characteristics` — текущие значения
2. Параллельно: `GET /admin/parameters?page_size=100` — полный словарь для dropdown «Добавить параметр»
3. При выборе параметра из dropdown — отобразить виджет по `value_type`:
   - `enum` → Multi-select (чекбоксы) из `parameter.values`
   - `number` → Input number + UOM-label
   - `string` → Input text
   - `bool` → Toggle
   - `range` → два Input number (min–max)
4. Кнопка «Сохранить всё» → `PUT /characteristics/bulk` со всеми параметрами

**Фильтрация списка параметров по категориям:**
При выборе «Добавить параметр» рекомендуется фильтровать словарь по категориям продукта — показывать параметры с `scope = "global"` или привязанные к текущим категориям продукта.

---

## 11. Вкладка: Изображения

### Загрузка

```typescript
// Изображения приходят вместе с продуктом в поле images[]
// или отдельно: GET /api/v1/admin/products/{id}/images
```

**Объект изображения:**
```typescript
interface ProductImage {
  id: string;
  url: string;
  alt: string | null;
  width: number | null;
  height: number | null;
  sort_order: number;
  is_cover: boolean;     // только одно изображение может быть обложкой
}
```

### Загрузка нового изображения

```typescript
// POST /api/v1/admin/products/{product_id}/images
// Content-Type: multipart/form-data

const formData = new FormData();
formData.append('file', file);         // File object
formData.append('alt', altText);       // опционально
formData.append('sort_order', '0');    // опционально

const res = await fetch(`/api/v1/admin/products/${id}/images`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}`, 'X-Tenant-ID': tenantId },
  // Content-Type НЕ устанавливай — браузер сам проставит boundary
  body: formData,
});
// Response 201: ProductImage
```

### Установить обложку

```typescript
// POST /api/v1/admin/products/{product_id}/images/{image_id}/set-cover
// Body: пустой, Response: 204
await fetch(`/api/v1/admin/products/${id}/images/${imageId}/set-cover`, {
  method: 'POST',
  headers,
});
```

### Изменить alt / порядок

```typescript
// PATCH /api/v1/admin/products/{product_id}/images/{image_id}
await fetch(`/api/v1/admin/products/${id}/images/${imageId}`, {
  method: 'PATCH',
  headers,
  body: JSON.stringify({ alt: 'Новый alt-текст', sort_order: 2 }),
});
```

### Drag-and-drop сортировка

```typescript
// PUT /api/v1/admin/products/{product_id}/images/reorder
// Body: { ordered_ids: [uuid, uuid, uuid] } — полный список в нужном порядке
await fetch(`/api/v1/admin/products/${id}/images/reorder`, {
  method: 'PUT',
  headers,
  body: JSON.stringify({ ordered_ids: newOrder }),
});
// Response: 204
```

### Удаление

```typescript
// DELETE /api/v1/admin/products/{product_id}/images/{image_id}
// Response: 204
```

---

## 12. Вкладка: Цены

### Загрузка

```typescript
// GET /api/v1/admin/products/{product_id}/prices
// Response: ProductPrice[]
```

**Объект цены:**
```typescript
interface ProductPrice {
  id: string;
  price_type: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: string;           // decimal в строке, например "1500.00"
  currency: string;         // "RUB", "USD", "EUR"
  valid_from: string | null; // "YYYY-MM-DD"
  valid_to: string | null;
  created_at: string;
  updated_at: string;
}
```

### Создание

```typescript
// POST /api/v1/admin/products/{product_id}/prices
const data = {
  price_type: 'regular',   // regular | sale | wholesale | cost
  amount: 1500.00,          // число
  currency: 'RUB',
  valid_from: null,         // или "2026-01-01"
  valid_to: null,
};
// Response 201: ProductPrice
```

### Обновление

```typescript
// PATCH /api/v1/admin/products/{product_id}/prices/{price_id}
await fetch(`/api/v1/admin/products/${id}/prices/${priceId}`, {
  method: 'PATCH',
  headers,
  body: JSON.stringify({ amount: 1200.00 }),
});
```

### Удаление

```typescript
// DELETE /api/v1/admin/products/{product_id}/prices/{price_id}
// Response: 204
```

**UI-рекомендации:**
- Показывать тип цены человеко-понятно: `regular` → «Базовая», `sale` → «Акционная», `wholesale` → «Оптовая», `cost` → «Себестоимость»
- Поле `valid_from/valid_to` — DatePicker с возможностью оставить пустым
- Предупреждать если нет ни одной цены типа `regular`

---

## 13. Вкладка: Контент-блоки

Контент-блоки позволяют формировать богатое описание товара: тексты, изображения, видео, галереи, ссылки. Аналогично блокам для статей и услуг.

### Загрузка блоков

```typescript
// GET /api/v1/admin/products/{product_id}/content-blocks?locale=ru
// locale — опционально, фильтрует по языку

const blocks = await fetchJson(
  `/api/v1/admin/products/${id}/content-blocks?locale=${currentLocale}`
);
// Response: ContentBlock[]
```

**Объект блока:**
```typescript
interface ContentBlock {
  id: string;
  locale: string;       // "ru", "en", "kz"
  block_type: 'text' | 'image' | 'video' | 'gallery' | 'link' | 'result';
  sort_order: number;   // 0, 1, 2 ...
  title: string | null;
  content: string | null;          // HTML для text-блоков
  media_url: string | null;        // URL для image/video
  thumbnail_url: string | null;    // превью для video
  link_url: string | null;
  link_label: string | null;       // текст кнопки
  device_type: 'mobile' | 'desktop' | 'both' | null;
  block_metadata: Record<string, unknown> | null;
  // block_metadata используется для:
  // image: { alt: string, caption: string }
  // video: { provider: 'youtube' | 'vimeo' | 'custom', embed_id: string }
  // gallery: { images: { url: string, alt: string }[] }
  // link: { icon: string }
}
```

### Добавление блока

```typescript
// POST /api/v1/admin/products/{product_id}/content-blocks
interface ContentBlockCreate {
  locale: string;           // обязательно, 2–5 символов: "ru", "en"
  block_type: string;       // обязательно
  sort_order?: number;      // default 0
  title?: string | null;    // max 255
  content?: string | null;  // HTML
  media_url?: string | null;
  thumbnail_url?: string | null;
  link_url?: string | null;
  link_label?: string | null;
  device_type?: 'mobile' | 'desktop' | 'both'; // default "both"
  block_metadata?: object | null;
}

// Пример: добавить текстовый блок
const newBlock = await createBlock(productId, {
  locale: 'ru',
  block_type: 'text',
  sort_order: 0,
  title: 'О продукте',
  content: '<p>Подробное описание товара...</p>',
  device_type: 'both',
});
```

### Примеры для каждого типа блока

**Текстовый блок (text):**
```typescript
{
  locale: 'ru',
  block_type: 'text',
  title: 'Описание',
  content: '<p>HTML-контент</p>',
  device_type: 'both',
}
```

**Изображение (image):**
```typescript
{
  locale: 'ru',
  block_type: 'image',
  media_url: 'https://cdn.example.com/products/banner.jpg',
  block_metadata: {
    alt: 'Баннер товара',
    caption: 'Подпись под изображением',
  },
}
```

**Видео (video):**
```typescript
{
  locale: 'ru',
  block_type: 'video',
  media_url: 'https://www.youtube.com/watch?v=XXXXX',
  thumbnail_url: 'https://img.youtube.com/vi/XXXXX/hqdefault.jpg',
  block_metadata: {
    provider: 'youtube', // или 'vimeo', 'custom'
    embed_id: 'XXXXX',
  },
}
```

**Галерея (gallery):**
```typescript
{
  locale: 'ru',
  block_type: 'gallery',
  title: 'Фотогалерея',
  block_metadata: {
    images: [
      { url: 'https://cdn.example.com/1.jpg', alt: 'Фото 1' },
      { url: 'https://cdn.example.com/2.jpg', alt: 'Фото 2' },
    ],
  },
}
```

**Ссылка-кнопка (link):**
```typescript
{
  locale: 'ru',
  block_type: 'link',
  link_url: 'https://example.com/docs/manual.pdf',
  link_label: 'Скачать инструкцию',
  block_metadata: { icon: 'download' },
}
```

### Обновление блока

```typescript
// PATCH /api/v1/admin/products/{product_id}/content-blocks/{block_id}
// Все поля опциональны — отправляй только изменённые

await fetch(`/api/v1/admin/products/${id}/content-blocks/${blockId}`, {
  method: 'PATCH',
  headers,
  body: JSON.stringify({ title: 'Новый заголовок', content: '<p>Обновлённый текст</p>' }),
});
// Response 200: ContentBlock
```

### Удаление блока

```typescript
// DELETE /api/v1/admin/products/{product_id}/content-blocks/{block_id}
// Response: 204 No Content

await fetch(`/api/v1/admin/products/${id}/content-blocks/${blockId}`, {
  method: 'DELETE',
  headers,
});
```

### Изменение порядка (drag-and-drop)

```typescript
// POST /api/v1/admin/products/{product_id}/content-blocks/reorder
// Body: { locale: "ru", block_ids: ["uuid-1", "uuid-2", "uuid-3"] }
// Порядок в массиве = новый sort_order
// ВАЖНО: передавай только блоки одной локали

await fetch(`/api/v1/admin/products/${id}/content-blocks/reorder`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    locale: 'ru',
    block_ids: orderedBlocks.map(b => b.id),
  }),
});
// Response 200: ContentBlock[] в новом порядке
```

### UI — рекомендуемый дизайн вкладки

```
┌─────────────────────────────────────────────────────┐
│  Локаль: [ru ▼] [en] [kz]          [+ Добавить блок]│
├─────────────────────────────────────────────────────┤
│  ☰  [Текст] О продукте                         [✎][✕]│
│     Подробное описание товара...                     │
├─────────────────────────────────────────────────────┤
│  ☰  [Изображение] Баннер                       [✎][✕]│
│     [img preview]                                    │
├─────────────────────────────────────────────────────┤
│  ☰  [Ссылка] Скачать инструкцию                [✎][✕]│
│     → https://example.com/manual.pdf                │
└─────────────────────────────────────────────────────┘
```

- `☰` — handle для drag-and-drop (библиотека `@dnd-kit/sortable` или `react-beautiful-dnd`)
- При перетаскивании — вызов `/reorder` с новым порядком
- Кнопка «+ Добавить блок» — открывает модалку с выбором типа блока
- Переключение локали — перезагружает блоки с `?locale=xx`

### Переиспользование компонента

Если в проекте уже есть компонент редактора блоков для статей (`ArticleContentBlocks`) — **переиспользуй его**, передавая другой `entityId` и `baseUrl`:

```typescript
// Переиспользуемый компонент
interface ContentBlocksEditorProps {
  entityId: string;
  baseUrl: string; // "/api/v1/admin/articles/{id}" или "/api/v1/admin/products/{id}"
  permissions: {
    canRead: boolean;
    canWrite: boolean;
    canDelete: boolean;
  };
}

// Для продукта:
<ContentBlocksEditor
  entityId={productId}
  baseUrl={`/api/v1/admin/products/${productId}`}
  permissions={{
    canRead: can('catalog:read'),
    canWrite: can('catalog:update'),
    canDelete: can('catalog:delete'),
  }}
/>
```

---

## 14. Вкладка: Привязка к категориям

### Загрузка текущих категорий продукта

```typescript
// GET /api/v1/admin/products/{product_id}/categories
// Response: ProductCategoryLink[]
interface ProductCategoryLink {
  id: string;         // ID связи, не категории
  category_id: string;
  is_primary: boolean;
}
```

### Привязать категорию

```typescript
// POST /api/v1/admin/products/{product_id}/categories
await fetch(`/api/v1/admin/products/${id}/categories`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    category_id: selectedCategoryId,
    is_primary: false,  // true — только для одной основной категории
  }),
});
// Response 201: ProductCategoryLink
// Первая привязанная категория автоматически становится is_primary = true
```

### Открепить категорию

```typescript
// DELETE /api/v1/admin/products/{product_id}/categories/{link_id}
// link_id — это id связи (ProductCategoryLink.id), не ID категории!
await fetch(`/api/v1/admin/products/${id}/categories/${linkId}`, {
  method: 'DELETE',
  headers,
});
// Response: 204
```

**UI-рекомендации:**
- Показывай дерево категорий с чекбоксами
- Помечай основную категорию звёздочкой `★`
- Разрешай выбрать несколько, но основная — только одна

---

## 15. Вкладка: Алиасы и Аналоги

### Алиасы (альтернативные названия/артикулы)

```typescript
// GET /api/v1/admin/products/{product_id}/aliases
// Response: { id, alias }[]

// POST /api/v1/admin/products/{product_id}/aliases
// Body: { aliases: ["АРТ-001", "WP2000-EU"] }
// Response: { created: 2, skipped: 0 }

// DELETE /api/v1/admin/products/{product_id}/aliases/{alias_id}
// Response: 204
```

### Аналоги (связанные товары)

```typescript
// GET /api/v1/admin/products/{product_id}/analogs
// Response: ProductAnalog[]

// POST /api/v1/admin/products/{product_id}/analogs
const data = {
  analog_product_id: 'uuid-другого-товара',
  relation: 'equivalent', // 'equivalent' | 'better' | 'worse'
  notes: 'Аналог от другого производителя',
};

// DELETE /api/v1/admin/products/{product_id}/analogs/{analog_id}
// Response: 204
```

---

## 16. Заявки на продукт

Со страницы продукта можно быстро перейти к заявкам, которые оставили именно на этот товар.

```typescript
// GET /api/v1/admin/inquiries?productId={product_id}&page=1&pageSize=20
const { items } = await fetchJson(
  `/api/v1/admin/inquiries?productId=${productId}`
);
// Каждая заявка содержит вложенный объект product:
// { id, product_id, product: { id, title, slug, sku }, name, email, ... }
```

**UI:** кнопка «Заявки на товар (N)» в шапке карточки продукта, ведущая на отфильтрованный список.

Полная документация по заявкам — [`07-leads.md`](../api/endpoints/07-leads.md) и [`PRODUCT_INQUIRY_SUPPORT.md`](../api/changelogs/PRODUCT_INQUIRY_SUPPORT.md).

---

## 17. Тип продукта и вариативность

> **Feature flag:** Поля `product_type`, `has_variants`, `price_from`, `price_to` и все вкладки вариантов отображаются **только если** для тенанта включён флаг `variants_module`.

### 17.1 Поле `product_type`

Продукт теперь имеет тип, определяющий его природу:

| Значение | Описание |
|----------|----------|
| `physical` | Физический товар (по умолчанию) |
| `digital` | Цифровой продукт |
| `service` | Услуга |
| `course` | Курс / обучение |
| `subscription` | Подписка |

```typescript
// В форме редактирования продукта — <Select>
const PRODUCT_TYPES = [
  { value: 'physical', label: 'Физический товар' },
  { value: 'digital', label: 'Цифровой продукт' },
  { value: 'service', label: 'Услуга' },
  { value: 'course', label: 'Курс' },
  { value: 'subscription', label: 'Подписка' },
] as const;

// Показывать Select только при включённом variants_module
{isVariantsEnabled && (
  <Select name="product_type" options={PRODUCT_TYPES} defaultValue="physical" />
)}
```

### 17.2 Поле `has_variants`

Булевый флаг — управляет отображением вкладок вариантов на карточке продукта.

```typescript
// Если has_variants = false — вкладки «Группы опций», «Вариации» и др. скрыты
// Если has_variants = true — вкладки отображаются

{product.has_variants && isVariantsEnabled && (
  <>
    <Tab label="Группы опций" />
    <Tab label="Вариации" />
    <Tab label="Цены вариантов" />
    <Tab label="Включения" />
    <Tab label="Изобр. вариантов" />
  </>
)}
```

### 17.3 Поля `price_from` / `price_to`

Read-only поля, автоматически рассчитываемые бэкендом на основе минимальной и максимальной цены среди всех вариантов продукта.

- Отображать в карточке продукта и в таблице списка
- **Нельзя** менять вручную — пересчитываются автоматически при изменении цен вариантов
- `null` — если у продукта нет вариантов с ценами

```typescript
// В таблице списка продуктов:
<td>{product.price_from && product.price_to
  ? `${product.price_from} – ${product.price_to}`
  : '—'
}</td>
```

---

## 18. Вкладка: Группы опций

> **Feature flag:** Вкладка видна только при `variants_module = true` и `product.has_variants = true`.

Группы опций определяют оси вариативности: размер, цвет, объём и т.д. Каждая группа содержит набор значений.

### 18.1 Загрузка

```typescript
// GET /api/v1/admin/products/{product_id}/option-groups
// Response: OptionGroup[]

const groups = await fetchJson(`/api/v1/admin/products/${id}/option-groups`);
```

### 18.2 Создание группы опций

```typescript
// POST /api/v1/admin/products/{product_id}/option-groups
interface OptionGroupCreate {
  title: string;                // обязательно, 1–255
  slug: string;                 // обязательно, 1–255
  display_type: 'dropdown' | 'buttons' | 'color_swatch' | 'cards';
  sort_order?: number;          // default 0
  is_required?: boolean;        // default true
  parameter_id?: string | null; // привязка к параметру из словаря (опционально)
  values?: OptionValueCreate[]; // начальные значения
}

interface OptionValueCreate {
  title: string;
  slug?: string;
  sort_order?: number;
  color_hex?: string | null;   // для display_type = "color_swatch"
  image_url?: string | null;   // для display_type = "cards"
}

// Пример: создать группу "Размер"
await fetch(`/api/v1/admin/products/${id}/option-groups`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    title: 'Размер',
    slug: 'razmer',
    display_type: 'buttons',
    is_required: true,
    values: [
      { title: 'S' },
      { title: 'M' },
      { title: 'L' },
      { title: 'XL' },
    ],
  }),
});
// Response 201: OptionGroup (с values[])
```

### 18.3 Обновление / удаление

```typescript
// PATCH /api/v1/admin/products/{product_id}/option-groups/{group_id}
await fetch(`/api/v1/admin/products/${id}/option-groups/${groupId}`, {
  method: 'PATCH',
  headers,
  body: JSON.stringify({ title: 'Новое название', display_type: 'dropdown' }),
});

// DELETE /api/v1/admin/products/{product_id}/option-groups/{group_id}
// ВНИМАНИЕ: Удаление группы не удаляет варианты, но разрывает связи через VariantOptionLink. Сами варианты остаются.
// Response: 204
```

### 18.4 UI — рекомендуемый дизайн

```
┌──────────────────────────────────────────────────────────────────┐
│  ГРУППЫ ОПЦИЙ                                 [+ Добавить группу]│
│  ────────────────────────────────────────────────────────────── │
│                                                                  │
│  ☰  Размер  (buttons)  обязательное              [✎][✕]         │
│     Значения: [S] [M] [L] [XL]  [+ добавить]                   │
│                                                                  │
│  ☰  Цвет  (color_swatch)  обязательное           [✎][✕]         │
│     Значения: [🔴 Красный] [🔵 Синий] [+ добавить]             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

- `☰` — drag-handle для сортировки групп
- Значения редактируются inline — клик по значению открывает форму
- `display_type` определяет как значения отображаются на публичном сайте
- `parameter_id` — опциональная привязка к параметру из словаря для синхронизации

---

## 19. Вкладка: Вариации

> **Feature flag:** Вкладка видна только при `variants_module = true` и `product.has_variants = true`.

Вариации — конкретные SKU-позиции, образованные комбинациями значений из групп опций.

### 19.1 Загрузка

```typescript
// GET /api/v1/admin/products/{product_id}/variants
// Response: ProductVariant[]

const variants = await fetchJson(`/api/v1/admin/products/${id}/variants`);
```

### 19.2 Генерация матрицы вариантов

Автоматическая генерация всех комбинаций из групп опций:

```typescript
// POST /api/v1/admin/products/{product_id}/variants/generate
// Создаёт варианты для всех комбинаций значений опций,
// которых ещё нет. Существующие варианты не затрагиваются.

await fetch(`/api/v1/admin/products/${id}/variants/generate`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    option_group_ids: ['uuid1', 'uuid2'],  // обязательно, UUID групп опций
    base_price: 1000,                       // опционально, базовая цена для новых вариантов
  }),
});
// Response: { created_count: N, variants: [...] }
```

### 19.3 Создание варианта вручную

```typescript
// POST /api/v1/admin/products/{product_id}/variants
interface VariantCreate {
  sku: string;                    // уникальный в тенанте
  slug: string;                   // обязательно, 1–255
  title: string;                  // 1–500
  description?: string;
  is_default?: boolean;           // default false; только один может быть default
  is_active?: boolean;            // default true
  sort_order?: number;
  stock_quantity?: number | null;
  weight?: number | null;         // decimal (Decimal | None в Pydantic)
  option_value_ids?: string[];   // UUID значений из групп опций
}
```

### 19.4 Обновление / удаление

```typescript
// PATCH /api/v1/admin/products/{product_id}/variants/{variant_id}
await fetch(`/api/v1/admin/products/${id}/variants/${variantId}`, {
  method: 'PATCH',
  headers,
  body: JSON.stringify({ sku: 'NEW-SKU-001', is_active: false }),
});

// DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}
// Response: 204
```

### 19.5 UI — рекомендуемый дизайн

```
┌──────────────────────────────────────────────────────────────────────┐
│  ВАРИАЦИИ                        [Сгенерировать] [+ Добавить вручную]│
│  ──────────────────────────────────────────────────────────────────  │
│                                                                      │
│  SKU          Название        Размер  Цвет   Сток  Статус  Действия  │
│  ─────────────────────────────────────────────────────────────────── │
│  ▶ SKU-S-RED  Футболка S/Кр.  S      Красн.  50    ✅     [✎][✕]    │
│  ▶ SKU-M-RED  Футболка M/Кр.  M      Красн.  30    ✅     [✎][✕]    │
│  ▼ SKU-L-BLU  Футболка L/Син. L      Синий   0     ⚠️     [✎][✕]    │
│    ├─ Цены: regular 1500₽, sale 1200₽                                │
│    ├─ Изображения: 3 шт.                                            │
│    └─ Включения: 5 пунктов                                          │
│                                                                      │
│  Bulk: [☑ Выбрать все] [Активировать] [Деактивировать] [Удалить]    │
└──────────────────────────────────────────────────────────────────────┘
```

- `▶` / `▼` — раскрываемые строки с деталями (цены, изображения, включения)
- Кнопка «Сгенерировать» — `POST /variants/generate`
- Bulk-операции: выбрать несколько → групповое действие

---

## 20. Вкладка: Цены вариантов

> **Feature flag:** Вкладка видна только при `variants_module = true` и `product.has_variants = true`.

Цены устанавливаются на уровне каждого варианта. Структура идентична ценам продукта (секция 12), но привязана к варианту.

### 20.1 CRUD

```typescript
// GET /api/v1/admin/products/{product_id}/variants/{variant_id}/prices
// Response: VariantPrice[]

// POST /api/v1/admin/products/{product_id}/variants/{variant_id}/prices
interface VariantPriceCreate {
  price_type?: 'regular' | 'sale' | 'wholesale' | 'cost';  // default "regular"
  amount: number;
  currency?: string;        // default "RUB"
  valid_from?: string | null;
  valid_to?: string | null;
}

// PATCH /api/v1/admin/products/{product_id}/variants/{variant_id}/prices/{price_id}
// DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}/prices/{price_id}
// Response: 204
```

### 20.2 Автоматический пересчёт `price_from` / `price_to`

После **любого** изменения цен вариантов (создание, обновление, удаление) бэкенд автоматически пересчитывает `product.price_from` и `product.price_to`. Фронтенд должен перезагрузить продукт для отображения актуальных значений:

```typescript
const handlePriceSave = async (variantId: string, priceData: VariantPriceCreate) => {
  await createVariantPrice(productId, variantId, priceData);
  await refetchProduct(); // обновить price_from / price_to в UI
};
```

---

## 21. Вкладка: Включения (тарифы)

> **Feature flag:** Вкладка видна только при `variants_module = true` и `product.has_variants = true`.  
> **Типы продуктов:** Релевантна для `course`, `subscription`, `service`. Для `physical` и `digital` — вкладку можно скрыть или показать пустой.

Включения позволяют описать, что входит в каждый вариант/тариф — для построения сравнительных таблиц.

### 21.1 CRUD

```typescript
// GET /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions
// Response: VariantInclusion[]

// POST /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions
interface VariantInclusionCreate {
  title: string;                 // обязательно, 1–500
  description?: string | null;
  is_included: boolean;          // true = входит, false = не входит
  sort_order?: number;
  icon?: string | null;          // имя иконки: "check", "star", "lock"
  group?: string | null;         // группировка: "Базовые", "Премиум"
}

// PATCH /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions/{inclusion_id}
// DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}/inclusions/{inclusion_id}
// Response: 204
```

### 21.2 UI — пример сравнительной таблицы

```
┌──────────────────────┬──────────┬──────────┬──────────┐
│  Включено            │  Basic   │  Pro     │  Premium │
├──────────────────────┼──────────┼──────────┼──────────┤
│  Базовые             │          │          │          │
│  ✅ Доступ к курсу   │    ✅    │    ✅    │    ✅    │
│  ✅ Материалы        │    ✅    │    ✅    │    ✅    │
│  Премиум             │          │          │          │
│  🔒 Менторство       │    ❌    │    ✅    │    ✅    │
│  🔒 Сертификат       │    ❌    │    ❌    │    ✅    │
└──────────────────────┴──────────┴──────────┴──────────┘
```

Для генерации такой таблицы на публичном сайте фронтенд загружает `inclusions` всех вариантов и группирует по `group`.

---

## 22. Вкладка: Изображения вариантов

> **Feature flag:** Вкладка видна только при `variants_module = true` и `product.has_variants = true`.

Изображения привязываются к конкретному варианту. Если у варианта нет своих изображений — на публичном сайте показываются изображения продукта (fallback).

### 22.1 CRUD

```typescript
// GET /api/v1/admin/products/{product_id}/variants/{variant_id}/images
// Response: VariantImage[]

// POST /api/v1/admin/products/{product_id}/variants/{variant_id}/images
// Content-Type: multipart/form-data (аналогично загрузке изображений продукта)
const formData = new FormData();
formData.append('file', file);
formData.append('alt', altText);
formData.append('sort_order', '0');

await fetch(`/api/v1/admin/products/${id}/variants/${variantId}/images`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}`, 'X-Tenant-ID': tenantId },
  body: formData,
});
// Response 201: VariantImage

// DELETE /api/v1/admin/products/{product_id}/variants/{variant_id}/images/{image_id}
// Response: 204
```

### 22.2 Логика fallback на фронте

```typescript
const getDisplayImages = (variant: ProductVariant, product: ProductDetail): VariantImage[] | ProductImage[] => {
  if (variant.images.length > 0) {
    return variant.images;
  }
  return product.images;
};
```

---

## 23. TypeScript-типы

```typescript
// ============================================
// Admin Catalog — полные типы (copy-paste ready)
// ============================================

// ---------- Справочники ----------

interface UOM {
  id: string;
  name: string;
  code: string;
  symbol: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

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

// ---------- Параметры (словарь характеристик) ----------

type ParameterValueType = 'string' | 'number' | 'enum' | 'bool' | 'range';
type ParameterScope = 'global' | 'category';

interface ParameterValue {
  id: string;
  parameter_id: string;
  label: string;
  slug: string;
  code: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface Parameter {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  value_type: ParameterValueType;
  uom_id: string | null;
  scope: ParameterScope;
  description: string | null;
  constraints: Record<string, unknown> | null;
  is_filterable: boolean;
  is_required: boolean;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  values: ParameterValue[];
  category_ids: string[];
}

interface ParameterCreate {
  name: string;
  slug?: string;
  value_type: ParameterValueType;
  uom_id?: string;
  scope?: ParameterScope;
  description?: string;
  constraints?: Record<string, unknown>;
  is_filterable?: boolean;
  is_required?: boolean;
  sort_order?: number;
  category_ids?: string[];
  values?: ParameterValueCreate[];
}

interface ParameterUpdate {
  name?: string;
  slug?: string;
  description?: string;
  uom_id?: string | null;
  scope?: ParameterScope;
  constraints?: Record<string, unknown>;
  is_filterable?: boolean;
  is_required?: boolean;
  sort_order?: number;
  is_active?: boolean;
}

interface ParameterValueCreate {
  label: string;
  slug?: string;
  code?: string;
  sort_order?: number;
}

interface ParameterValueUpdate {
  label?: string;
  slug?: string;
  code?: string;
  sort_order?: number;
  is_active?: boolean;
}

interface ParameterCategorySet {
  category_ids: string[];
}

// ---------- Характеристики продукта ----------

type SourceType = 'manual' | 'import' | 'system';

interface ProductCharacteristic {
  id: string;
  product_id: string;
  parameter_id: string;
  parameter_value_id: string | null;
  value_text: string | null;
  value_number: number | null;
  value_bool: boolean | null;
  uom_id: string | null;
  source_type: SourceType;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
}

interface ProductCharacteristicCreate {
  parameter_id: string;
  parameter_value_id?: string;
  value_text?: string;
  value_number?: number;
  value_bool?: boolean;
  uom_id?: string;
  source_type?: SourceType;
}

interface ProductCharacteristicBulkItem {
  parameter_id: string;
  parameter_value_ids?: string[];
  value_text?: string;
  value_number?: number;
  value_bool?: boolean;
  uom_id?: string;
}

interface ProductCharacteristicBulkCreate {
  characteristics: ProductCharacteristicBulkItem[];
}

interface ProductCharacteristicBulkResponse {
  created: number;
  updated: number;
  deleted: number;
}

// ---------- Продукт ----------

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

interface ProductPrice {
  id: string;
  price_type: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: string;
  currency: string;
  valid_from: string | null;
  valid_to: string | null;
  created_at: string;
  updated_at: string;
}

interface ProductCategoryLink {
  id: string;
  category_id: string;
  is_primary: boolean;
}

interface ProductAlias {
  id: string;
  alias: string;
}

interface ProductAnalog {
  analog_product_id: string;
  sku: string;
  title: string;
  relation: 'equivalent' | 'better' | 'worse';
  notes: string | null;
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
  block_metadata: Record<string, unknown> | null;
}

type ProductType = 'physical' | 'digital' | 'service' | 'course' | 'subscription';

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
  product_type: ProductType;
  has_variants: boolean;
  price_from: string | null;
  price_to: string | null;
  is_active: boolean;
  version: number;
  images: ProductImage[];
  created_at: string;
  updated_at: string;
}

interface ProductDetail extends Product {
  aliases: ProductAlias[];
  categories: ProductCategoryLink[];
  prices: ProductPrice[];
  // characteristics загружаются отдельно: GET /admin/products/{id}/characteristics
  // content_blocks загружаются отдельно: GET /admin/products/{id}/content-blocks
}

// ---------- Группы опций и значения ----------

type OptionDisplayType = 'dropdown' | 'buttons' | 'color_swatch' | 'cards';

interface OptionValue {
  id: string;
  title: string;
  slug: string;
  sort_order: number;
  color_hex: string | null;
  image_url: string | null;
  created_at: string;
  updated_at: string;
}

interface OptionGroup {
  id: string;
  product_id: string;
  title: string;
  slug: string;
  display_type: OptionDisplayType;
  sort_order: number;
  is_required: boolean;
  parameter_id: string | null;
  values: OptionValue[];
}

// ---------- Вариации ----------

interface VariantPrice {
  id: string;
  price_type: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: string;
  currency: string;
  valid_from: string | null;
  valid_to: string | null;
  created_at: string;
  updated_at: string;
}

interface VariantInclusion {
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

interface VariantImage {
  id: string;
  url: string;
  alt: string | null;
  width: number | null;
  height: number | null;
  size_bytes: number | null;
  mime_type: string | null;
  sort_order: number;
  is_cover: boolean;
}

interface ProductVariant {
  id: string;
  product_id: string;
  sku: string;
  slug: string;
  title: string;
  description: string | null;
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
  stock_quantity: number | null;
  weight: string | null;
  prices: VariantPrice[];
  option_values: OptionValue[];
  inclusions: VariantInclusion[];
  images: VariantImage[];
}

// ---------- Request types ----------

interface ProductCreate {
  sku: string;
  slug: string;
  title: string;
  brand?: string;
  model?: string;
  description?: string;
  uom_id?: string;
  product_type?: ProductType;    // default "physical" (только при variants_module)
  has_variants?: boolean;        // default false
  is_active?: boolean;
  category_ids?: string[];
}

interface ProductUpdate {
  sku?: string;
  slug?: string;
  title?: string;
  brand?: string;
  model?: string;
  description?: string;
  uom_id?: string | null;
  product_type?: ProductType;    // только при variants_module
  has_variants?: boolean;
  is_active?: boolean;
  version: number; // обязательно — optimistic locking!
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

interface ProductAnalogCreate {
  analog_product_id: string;
  relation?: 'equivalent' | 'better' | 'worse';
  notes?: string;
}

interface ProductPriceCreate {
  price_type?: 'regular' | 'sale' | 'wholesale' | 'cost';
  amount: number;
  currency?: string;
  valid_from?: string | null;
  valid_to?: string | null;
}

// ---------- Variant request types ----------

interface OptionGroupCreate {
  title: string;
  slug: string;
  display_type: OptionDisplayType;
  sort_order?: number;
  is_required?: boolean;
  parameter_id?: string | null;
  values?: Omit<OptionValue, 'id'>[];
}

interface VariantCreate {
  sku: string;
  slug: string;
  title: string;
  description?: string;
  is_default?: boolean;
  is_active?: boolean;
  sort_order?: number;
  stock_quantity?: number | null;
  weight?: number | null;
  option_value_ids?: string[];
}

interface VariantPriceCreate {
  price_type?: VariantPrice['price_type'];
  amount: number;
  currency?: string;
  valid_from?: string | null;
  valid_to?: string | null;
}

interface VariantInclusionCreate {
  title: string;
  description?: string | null;
  is_included: boolean;
  sort_order?: number;
  icon?: string | null;
  group?: string | null;
}

// ---------- API responses ----------

interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

---

## 24. Обработка ошибок

| Код | Причина | Действие в UI |
|-----|---------|---------------|
| `400` | Ошибка валидации | Показать поля с ошибками из `detail[].msg` |
| `401` | Токен истёк | Refresh token → повторить запрос |
| `403` | Нет прав или флаг выключен | «Нет доступа» / скрыть кнопку |
| `404` | Объект не найден | Редирект на список |
| `409` | Конфликт версии (optimistic lock) | «Данные изменились. Обновите страницу» |
| `422` | Ошибка FastAPI-валидации | Показать сообщение из `detail` |
| `500` | Ошибка сервера | «Что-то пошло не так. Попробуйте позже» |

### Структура 422 ответа:

```typescript
interface ValidationError {
  detail: Array<{
    loc: string[];   // ["body", "sku"]
    msg: string;     // "field required"
    type: string;    // "missing"
  }>;
}

// Маппинг на поля формы:
const fieldErrors = error.detail.reduce((acc, err) => {
  const field = err.loc[err.loc.length - 1]; // последний элемент loc
  acc[field] = err.msg;
  return acc;
}, {} as Record<string, string>);
```

### Optimistic locking (409):

```typescript
const handleSave = async (data: ProductUpdate) => {
  try {
    const updated = await updateProduct(id, { ...data, version: product.version });
    setProduct(updated); // обновить version в локальном state
  } catch (err) {
    if (err.status === 409) {
      toast.error('Данные изменились. Обновите страницу и повторите.');
      await refetchProduct(); // перезагрузить свежие данные
    }
  }
};
```

---

## Быстрый план реализации (приоритеты)

### Sprint 1 — Справочники (фундамент)
- [ ] Страница «Единицы измерения» — CRUD таблица
- [ ] Страница «Категории» — дерево с drag-and-drop, CRUD
- [ ] Страница «Параметры» — список с фильтрами, CRUD
- [ ] Карточка параметра — управление enum-значениями, привязка к категориям

### Sprint 2 — Продукты: основное
- [ ] Страница `/admin/catalog/products` — таблица с фильтрами
- [ ] Форма создания продукта (с выбором категорий)
- [ ] Карточка продукта — основные поля, optimistic locking
- [ ] Мягкое удаление

### Sprint 3 — Продукты: характеристики и медиа
- [ ] Вкладка «Характеристики» — привязка параметров, bulk-обновление, виджеты по типам
- [ ] Вкладка «Изображения» — upload, drag-and-drop, cover selection
- [ ] Вкладка «Цены» — CRUD, типы цен, даты действия

### Sprint 4 — Продукты: контент и связи
- [ ] Вкладка «Контент-блоки» (переиспользовать компонент статей)
- [ ] Вкладка «Категории» (дерево с чекбоксами, primary)
- [ ] Вкладка «Алиасы / Аналоги»
- [ ] Блок «Заявки на товар» в карточке продукта

### Sprint 5 — Вариации (требует `variants_module`)
- [ ] Поле `product_type` — dropdown в форме продукта
- [ ] Переключатель `has_variants` — показ/скрытие вкладок вариантов
- [ ] Отображение `price_from` / `price_to` в списке и карточке
- [ ] Вкладка «Группы опций» — CRUD, inline-управление значениями, drag-and-drop сортировка
- [ ] Вкладка «Вариации» — таблица с раскрываемыми строками, генерация матрицы, bulk-операции
- [ ] Вкладка «Цены вариантов» — CRUD цен на уровне варианта, авто-обновление price_from/price_to
- [ ] Вкладка «Включения» — CRUD для тарифных сравнений (course/subscription/service)
- [ ] Вкладка «Изображения вариантов» — upload per-variant, fallback-логика
