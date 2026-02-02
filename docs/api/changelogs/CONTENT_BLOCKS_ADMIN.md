# Content Blocks Admin API Documentation

Данная документация описывает новую систему контент-блоков для гибкого управления содержимым статей, кейсов и услуг.

## Обзор

Content Blocks — система гибких блоков контента, позволяющая:
- Добавлять видео (YouTube, RuTube, другие хостинги)
- Добавлять изображения (для слайдеров, отдельные, с адаптацией под mobile/desktop)
- Добавлять HTML-текст
- Добавлять ссылки (сайт, Telegram бот и др.)
- Добавлять блоки результатов (для кейсов)
- Управлять порядком отображения блоков

## Типы блоков

| block_type | Описание | Ключевые поля |
|------------|----------|---------------|
| `text` | HTML-текст | `content` |
| `image` | Изображение | `media_url`, `device_type`, `block_metadata.alt/caption` |
| `video` | Видео (YouTube/RuTube) | `media_url`, `thumbnail_url`, `block_metadata.provider` |
| `gallery` | Слайдер/галерея | `block_metadata.images[]` |
| `link` | Ссылка | `link_url`, `link_label`, `block_metadata.icon` |
| `result` | Блок результата | `title`, `content`, `media_url`, `link_url` |

## Device Types

| device_type | Описание |
|-------------|----------|
| `mobile` | Показывать только на мобильных устройствах |
| `desktop` | Показывать только на десктопах |
| `both` | Показывать на всех устройствах (по умолчанию) |

---

## Endpoints для Кейсов (Cases)

### Получить список контент-блоков

```
GET /api/v1/admin/cases/{case_id}/content-blocks?locale=ru
```

**Query параметры:**
- `locale` (optional): фильтр по локали

**Response:** `ContentBlockResponse[]`

---

### Добавить контент-блок

```
POST /api/v1/admin/cases/{case_id}/content-blocks
```

**Request Body:**
```json
{
  "locale": "ru",
  "block_type": "text",
  "sort_order": 0,
  "title": "Заголовок блока",
  "content": "<p>HTML содержимое</p>",
  "media_url": null,
  "thumbnail_url": null,
  "link_url": null,
  "link_label": null,
  "device_type": "both",
  "block_metadata": null
}
```

**Примеры создания разных типов:**

**Текстовый блок:**
```json
{
  "locale": "ru",
  "block_type": "text",
  "sort_order": 0,
  "content": "<p>Описание проекта...</p>"
}
```

**Видео блок:**
```json
{
  "locale": "ru",
  "block_type": "video",
  "sort_order": 1,
  "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
  "block_metadata": {
    "provider": "youtube"
  }
}
```

**Изображение:**
```json
{
  "locale": "ru",
  "block_type": "image",
  "sort_order": 2,
  "media_url": "/media/cases/image.jpg",
  "device_type": "both",
  "block_metadata": {
    "alt": "Описание изображения",
    "caption": "Подпись к изображению"
  }
}
```

**Галерея:**
```json
{
  "locale": "ru",
  "block_type": "gallery",
  "sort_order": 3,
  "block_metadata": {
    "images": [
      {"url": "/media/cases/slide1.jpg", "alt": "Слайд 1", "device_type": "both"},
      {"url": "/media/cases/slide2.jpg", "alt": "Слайд 2", "device_type": "both"},
      {"url": "/media/cases/slide3-mobile.jpg", "alt": "Слайд 3", "device_type": "mobile"}
    ]
  }
}
```

**Ссылка (Telegram бот, сайт):**
```json
{
  "locale": "ru",
  "block_type": "link",
  "sort_order": 4,
  "link_url": "https://t.me/mybot",
  "link_label": "Открыть в Telegram",
  "block_metadata": {
    "icon": "telegram"
  }
}
```

**Блок результата:**
```json
{
  "locale": "ru",
  "block_type": "result",
  "sort_order": 5,
  "title": "Результат работы",
  "content": "<ul><li>Увеличение конверсии на 30%</li></ul>",
  "media_url": "https://www.youtube.com/watch?v=demo",
  "link_url": "https://example.com",
  "link_label": "Перейти на сайт"
}
```

---

### Обновить контент-блок

```
PATCH /api/v1/admin/cases/{case_id}/content-blocks/{block_id}
```

**Request Body:** Любые поля из `ContentBlockCreate` (все опциональны)

---

### Удалить контент-блок

```
DELETE /api/v1/admin/cases/{case_id}/content-blocks/{block_id}
```

**Response:** `204 No Content`

---

### Изменить порядок блоков

```
POST /api/v1/admin/cases/{case_id}/content-blocks/reorder
```

**Request Body:**
```json
{
  "locale": "ru",
  "block_ids": [
    "uuid-блока-3",
    "uuid-блока-1",
    "uuid-блока-2"
  ]
}
```

**Response:** `ContentBlockResponse[]` (упорядоченный список)

---

## Endpoints для Статей (Articles)

Аналогичные эндпоинты:

- `GET /api/v1/admin/articles/{article_id}/content-blocks?locale=ru`
- `POST /api/v1/admin/articles/{article_id}/content-blocks`
- `PATCH /api/v1/admin/articles/{article_id}/content-blocks/{block_id}`
- `DELETE /api/v1/admin/articles/{article_id}/content-blocks/{block_id}`
- `POST /api/v1/admin/articles/{article_id}/content-blocks/reorder`

---

## Endpoints для Услуг (Services)

Аналогичные эндпоинты:

- `GET /api/v1/admin/services/{service_id}/content-blocks?locale=ru`
- `POST /api/v1/admin/services/{service_id}/content-blocks`
- `PATCH /api/v1/admin/services/{service_id}/content-blocks/{block_id}`
- `DELETE /api/v1/admin/services/{service_id}/content-blocks/{block_id}`
- `POST /api/v1/admin/services/{service_id}/content-blocks/reorder`

---

## Схемы данных

### ContentBlockCreate

```typescript
interface ContentBlockCreate {
  locale: string;           // "ru", "en"
  block_type: ContentBlockType;
  sort_order?: number;      // default: 0
  title?: string;           // max 255 символов
  content?: string;         // HTML для text блоков
  media_url?: string;       // URL изображения или видео
  thumbnail_url?: string;   // Превью для видео
  link_url?: string;        // URL ссылки
  link_label?: string;      // Текст кнопки/ссылки
  device_type?: DeviceType; // default: "both"
  block_metadata?: object;  // Доп. данные (alt, caption, images[], provider, icon)
}

type ContentBlockType = "text" | "image" | "video" | "gallery" | "link" | "result";
type DeviceType = "mobile" | "desktop" | "both";
```

### ContentBlockResponse

```typescript
interface ContentBlockResponse {
  id: string;               // UUID
  locale: string;
  block_type: string;
  sort_order: number;
  title: string | null;
  content: string | null;
  media_url: string | null;
  thumbnail_url: string | null;
  link_url: string | null;
  link_label: string | null;
  device_type: string | null;
  block_metadata: object | null;
}
```

### ContentBlockReorderRequest

```typescript
interface ContentBlockReorderRequest {
  locale: string;           // Локаль блоков для переупорядочивания
  block_ids: string[];      // Упорядоченный список UUID блоков
}
```

---

## Обновленные Response схемы

Следующие схемы теперь включают поле `content_blocks`:

### CaseResponse

```typescript
interface CaseResponse {
  // ... существующие поля ...
  content_blocks: ContentBlockResponse[];
}
```

### ArticleResponse

```typescript
interface ArticleResponse {
  // ... существующие поля ...
  content_blocks: ContentBlockResponse[];
}
```

### ServiceResponse

```typescript
interface ServiceResponse {
  // ... существующие поля ...
  content_blocks: ContentBlockForServiceResponse[];
}
```

---

## Обратная совместимость

- Существующие поля `description`, `results`, `content` в локалях **остаются без изменений**
- Content Blocks — **дополнительная система**, не заменяющая старые поля
- Фронтенд может выбирать: если `content_blocks` не пустой — рендерить блоки, иначе использовать старые поля

---

## Права доступа

| Endpoint | Требуемое право |
|----------|-----------------|
| GET content-blocks | `{entity}:read` |
| POST/PATCH/DELETE content-blocks | `{entity}:update` |
| POST reorder | `{entity}:update` |

Где `{entity}` = `cases`, `articles` или `services`

---

## Примеры интеграции в админку

### Загрузка блоков при редактировании кейса

```typescript
// После загрузки кейса — загрузить блоки
const caseId = 'uuid-кейса';
const response = await fetch(`/api/v1/admin/cases/${caseId}/content-blocks?locale=ru`, {
  headers: { Authorization: `Bearer ${token}` }
});
const blocks = await response.json();
```

### Добавление нового блока

```typescript
const newBlock = await fetch(`/api/v1/admin/cases/${caseId}/content-blocks`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`
  },
  body: JSON.stringify({
    locale: 'ru',
    block_type: 'text',
    sort_order: blocks.length,
    content: '<p>Новый текст</p>'
  })
});
```

### Drag & Drop сортировка

```typescript
// После drag & drop
const reorderedIds = blocks.map(b => b.id);
await fetch(`/api/v1/admin/cases/${caseId}/content-blocks/reorder`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`
  },
  body: JSON.stringify({
    locale: 'ru',
    block_ids: reorderedIds
  })
});
```
