# Административная панель — Каталог продуктов

> **Назначение**: Руководство для фронтенд-разработчика по реализации раздела «Каталог» в административной панели.  
> **Версия бэкенда**: актуальна на 2026-02-24 (ветка `feat/product-catalog`)  
> **Полная API-документация**: [`docs/api/endpoints/19-catalog.md`](../api/endpoints/19-catalog.md)

---

## Содержание

1. [Авторизация и заголовки](#1-авторизация-и-заголовки)
2. [Feature flags — когда показывать каталог](#2-feature-flags)
3. [RBAC — права доступа](#3-rbac)
4. [Навигация и структура раздела](#4-навигация-и-структура)
5. [Раздел: Единицы измерения (UOM)](#5-uom)
6. [Раздел: Категории](#6-категории)
7. [Раздел: Список продуктов](#7-список-продуктов)
8. [Страница продукта: основные данные](#8-страница-продукта--основные-данные)
9. [Вкладка: Характеристики (EAV)](#9-вкладка-характеристики)
10. [Вкладка: Изображения](#10-вкладка-изображения)
11. [Вкладка: Цены](#11-вкладка-цены)
12. [Вкладка: Контент-блоки (НОВОЕ)](#12-вкладка-контент-блоки)
13. [Вкладка: Привязка к категориям](#13-вкладка-привязка-к-категориям)
14. [Вкладка: Алиасы и Аналоги](#14-вкладка-алиасы-и-аналоги)
15. [Заявки на продукт (Leads)](#15-заявки-на-продукт)
16. [TypeScript-типы](#16-typescript-типы)
17. [Типовые ошибки и их обработка](#17-обработка-ошибок)

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
  /admin/catalog/uom              → Единицы измерения
  /admin/catalog/categories       → Дерево категорий
  /admin/catalog/products         → Список продуктов
  /admin/catalog/products/new     → Создание продукта
  /admin/catalog/products/:id     → Карточка продукта
    → вкладки: Основное | Характеристики | Изображения | Цены | Контент | Категории | Алиасы
```

Боковая навигация показывает «Каталог» только если `catalog_module` включён.

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

## 7. Список продуктов

**Страница:** `/admin/catalog/products`

### Загрузка с фильтрами

```typescript
// GET /api/v1/admin/products
interface ProductListParams {
  page?: number;
  pageSize?: number;
  search?: string;       // поиск по title, sku, description
  brand?: string;
  category_id?: string;  // UUID
  isActive?: boolean;
}

const fetchProducts = async (params: ProductListParams) => {
  const qs = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)])
  ).toString();
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
  sku: string;           // уникальный в тенанте, 1–100
  slug: string;          // URL-friendly, уникальный в тенанте, 1–255
  title: string;         // 1–255
  brand?: string;        // max 255
  model?: string;        // max 255
  description?: string;  // HTML или plain text
  uom_id?: string;       // UUID из справочника UOM
  is_active?: boolean;   // default true
}
// Response 201: Product
```

### Удаление (soft)

```typescript
// DELETE /api/v1/admin/products/{product_id}
// Response: 204 No Content
```

---

## 8. Страница продукта — основные данные

**URL:** `/admin/catalog/products/:id`

Страница с вкладками. Сначала загружается сам продукт:

```typescript
// GET /api/v1/admin/products/{product_id}?include=chars,prices,images
// include — опциональный, подгружает отношения
const product = await fetchJson(`/api/v1/admin/products/${id}`);
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

## 9. Вкладка: Характеристики

### Загрузка

```typescript
// GET /api/v1/admin/products/{product_id}/chars
// Response: ProductChar[]
const chars = await fetchJson(`/api/v1/admin/products/${id}/chars`);
```

**Объект характеристики:**
```typescript
interface ProductChar {
  id: string;
  name: string;        // "Напряжение"
  value_text: string;  // "220 В"
  uom_id: string | null;
}
```

### Bulk-обновление (рекомендуется)

Все изменения (добавление, редактирование, удаление) отправляются **одним запросом**:

```typescript
// PUT /api/v1/admin/products/{product_id}/chars
interface ProductCharBulkUpdate {
  created?: { name: string; value_text: string; uom_id?: string }[];
  updated?: { id: string; name?: string; value_text?: string; uom_id?: string }[];
  deleted?: string[];  // массив ID для удаления
}

// Пример: добавить одну и удалить другую
await fetch(`/api/v1/admin/products/${id}/chars`, {
  method: 'PUT',
  headers,
  body: JSON.stringify({
    created: [{ name: 'Вес', value_text: '2.5 кг' }],
    deleted: ['old-char-uuid'],
  }),
});
// Response: { created: 1, updated: 0, deleted: 1 }
```

**UI-паттерн:**
```
[+ Добавить характеристику]

Название          Значение          Ед. изм.   [✕]
──────────────────────────────────────────────────
Напряжение        220 В             В          [✕]
Мощность          1500 Вт           Вт         [✕]
[пустая строка]   [пустая строка]   [Select]

[Сохранить все]
```
Кнопка «Сохранить все» собирает diff и отправляет bulk-запрос.

---

## 10. Вкладка: Изображения

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

## 11. Вкладка: Цены

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

## 12. Вкладка: Контент-блоки

> **НОВЫЙ функционал** — добавлен 2026-02-24.

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

## 13. Вкладка: Привязка к категориям

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

## 14. Вкладка: Алиасы и Аналоги

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

## 15. Заявки на продукт

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

## 16. TypeScript-типы

```typescript
// ========================
// Core types
// ========================

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
  id: string;
  name: string;
  value_text: string;
  uom_id: string | null;
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

interface ProductDetail extends Product {
  chars: ProductChar[];
  aliases: { id: string; alias: string }[];
  categories: ProductCategoryLink[];
  prices: ProductPrice[];
  // content_blocks грузятся отдельно через /content-blocks endpoint
}

// ========================
// Request types
// ========================

interface ProductCreate {
  sku: string;
  slug: string;
  title: string;
  brand?: string;
  model?: string;
  description?: string;
  uom_id?: string;
  is_active?: boolean;
}

interface ProductUpdate extends Partial<ProductCreate> {
  version: number; // обязательно!
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

// ========================
// API responses
// ========================

interface PagedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
```

---

## 17. Обработка ошибок

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

### Sprint 1 — Список и CRUD продуктов
- [ ] Страница `/admin/catalog/products` — таблица с фильтрами
- [ ] Форма создания / редактирования продукта
- [ ] Мягкое удаление

### Sprint 2 — Вложенные данные
- [ ] Вкладка «Характеристики» (EAV bulk-update)
- [ ] Вкладка «Изображения» (upload + drag-and-drop)
- [ ] Вкладка «Цены»

### Sprint 3 — Контент и связи
- [ ] Вкладка «Контент-блоки» (переиспользовать компонент статей)
- [ ] Вкладка «Категории» (дерево с чекбоксами)
- [ ] Вкладка «Алиасы / Аналоги»

### Sprint 4 — Справочники и интеграции
- [ ] Страница «Единицы измерения» (UOM)
- [ ] Страница «Категории» (дерево с drag-and-drop)
- [ ] Блок «Заявки на товар» в карточке продукта
