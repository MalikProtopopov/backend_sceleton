# Articles API

> Blog posts, news articles, and related topics management

---

## Overview

Articles are the primary content type for blogs and news sections. Features include:
- Multi-language support via `locales`
- Topic categorization
- Publishing workflow (draft → published → archived)
- View count tracking
- SEO metadata per locale

---

## State Machine

```
                    ┌──────────────┐
                    │    DRAFT     │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            │            ▼
    ┌──────────────┐       │   ┌──────────────┐
    │  PUBLISHED   │◀──────┘   │   ARCHIVED   │
    └──────┬───────┘           └──────────────┘
           │                          ▲
           │                          │
           └──────────────────────────┘
```

| From | To | Action | Endpoint |
|------|-----|--------|----------|
| Draft | Published | Publish | `POST /articles/{id}/publish` |
| Published | Draft | Unpublish | `POST /articles/{id}/unpublish` |
| Any | Archived | Archive | `PATCH` with `status: archived` |
| Archived | Draft | Restore | `PATCH` with `status: draft` |

---

## Admin Endpoints

### GET /api/v1/admin/articles

List all articles with pagination and filters.

**Required Permission:** `articles:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page (max 100) |
| `status` | string | - | Filter: `draft`, `published`, `archived` |
| `topicId` | UUID | - | Filter by topic |

**Example Request:**
```bash
GET /api/v1/admin/articles?page=1&pageSize=20&status=draft
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "article-uuid-1",
      "tenant_id": "tenant-uuid",
      "status": "draft",
      "cover_image_url": "https://cdn.example.com/images/cover.jpg",
      "reading_time_minutes": 5,
      "sort_order": 0,
      "version": 1,
      "published_at": null,
      "view_count": 0,
      "author_id": "user-uuid",
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z",
      "locales": [
        {
          "id": "locale-uuid-1",
          "article_id": "article-uuid-1",
          "locale": "ru",
          "title": "Заголовок статьи",
          "slug": "zagolovok-stati",
          "excerpt": "Краткое описание статьи...",
          "content": "<p>Полный текст статьи...</p>",
          "meta_title": "SEO заголовок",
          "meta_description": "SEO описание",
          "created_at": "2026-01-14T10:00:00Z",
          "updated_at": "2026-01-14T10:00:00Z"
        }
      ],
      "topics": [
        {
          "topic_id": "topic-uuid-1"
        }
      ]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/admin/articles

Create a new article.

**Required Permission:** `articles:create`

**Request Body:**
```json
{
  "status": "draft",
  "cover_image_url": "https://cdn.example.com/images/cover.jpg",
  "reading_time_minutes": 5,
  "sort_order": 0,
  "topic_ids": ["topic-uuid-1", "topic-uuid-2"],
  "locales": [
    {
      "locale": "ru",
      "title": "Заголовок статьи",
      "slug": "zagolovok-stati",
      "excerpt": "Краткое описание...",
      "content": "<p>Полный текст статьи...</p>",
      "meta_title": "SEO заголовок | Компания",
      "meta_description": "SEO описание для поисковых систем"
    },
    {
      "locale": "en",
      "title": "Article Title",
      "slug": "article-title",
      "excerpt": "Brief description...",
      "content": "<p>Full article content...</p>",
      "meta_title": "SEO Title | Company",
      "meta_description": "SEO description for search engines"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `status` | string | No | Default: `draft`. Values: `draft`, `published`, `archived` |
| `cover_image_url` | string | No | Max 500 chars |
| `reading_time_minutes` | integer | No | - |
| `sort_order` | integer | No | Default: 0 |
| `topic_ids` | UUID[] | No | Array of topic UUIDs |
| `locales` | array | Yes | At least 1 locale required |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars (e.g., `ru`, `en`, `de`) |
| `title` | string | Yes | 1-255 chars |
| `slug` | string | Yes | 2-255 chars, URL-safe |
| `excerpt` | string | No | Max 500 chars |
| `content` | string | No | HTML content |
| `meta_title` | string | No | Max 70 chars |
| `meta_description` | string | No | Max 160 chars |

**Success Response (201):**
```json
{
  "id": "new-article-uuid",
  "tenant_id": "tenant-uuid",
  "status": "draft",
  "version": 1,
  "author_id": "current-user-uuid",
  "created_at": "2026-01-14T14:00:00Z",
  "updated_at": "2026-01-14T14:00:00Z",
  "locales": [...],
  "topics": [...]
}
```

**Error Response (422):**
```json
{
  "type": "https://api.cms.local/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    {
      "loc": ["body", "locales"],
      "msg": "List should have at least 1 item",
      "type": "too_short"
    }
  ]
}
```

---

### GET /api/v1/admin/articles/{article_id}

Get article by ID.

**Required Permission:** `articles:read`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `article_id` | UUID | Article ID |

**Success Response (200):** Same structure as list item.

**Error Response (404):**
```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Article not found"
}
```

---

### PATCH /api/v1/admin/articles/{article_id}

Update article.

**Required Permission:** `articles:update`

**Request Body:**
```json
{
  "status": "draft",
  "cover_image_url": "https://cdn.example.com/images/new-cover.jpg",
  "reading_time_minutes": 8,
  "sort_order": 1,
  "topic_ids": ["topic-uuid-1"],
  "version": 1
}
```

**Note:** 
- `version` field is required for optimistic locking
- Only include fields you want to update
- To update locales, use separate locale endpoints (if available) or provide full `locales` array

**Success Response (200):** Updated article object.

**Error Response (409):**
```json
{
  "type": "https://api.cms.local/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Version mismatch: expected 2, got 1"
}
```

---

### POST /api/v1/admin/articles/{article_id}/publish

Publish an article.

**Required Permission:** `articles:publish`

**Request Body:** None

**Behavior:**
- Sets `status` to `published`
- Sets `published_at` to current timestamp (if not already set)
- Increments `version`

**Success Response (200):**
```json
{
  "id": "article-uuid",
  "status": "published",
  "published_at": "2026-01-14T15:00:00Z",
  "version": 2,
  ...
}
```

**Error Response (422):**
```json
{
  "type": "https://api.cms.local/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Article must have at least one locale with title and content"
}
```

---

### POST /api/v1/admin/articles/{article_id}/unpublish

Unpublish an article (move to draft).

**Required Permission:** `articles:publish`

**Request Body:** None

**Behavior:**
- Sets `status` to `draft`
- Keeps `published_at` unchanged
- Increments `version`

**Success Response (200):** Updated article object.

---

### DELETE /api/v1/admin/articles/{article_id}

Soft delete an article.

**Required Permission:** `articles:delete`

**Response:** `204 No Content`

**Behavior:**
- Sets `deleted_at` timestamp
- Article excluded from all queries
- Can be restored by clearing `deleted_at` (admin operation)

---

## Topics

Topics are categories for organizing articles.

### GET /api/v1/admin/topics

List all topics.

**Required Permission:** `articles:read`

**Success Response (200):**
```json
[
  {
    "id": "topic-uuid-1",
    "tenant_id": "tenant-uuid",
    "icon": "📰",
    "color": "#3B82F6",
    "sort_order": 0,
    "version": 1,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "locales": [
      {
        "id": "locale-uuid",
        "topic_id": "topic-uuid-1",
        "locale": "ru",
        "title": "Новости",
        "slug": "novosti",
        "description": "Последние новости компании",
        "meta_title": null,
        "meta_description": null,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z"
      }
    ]
  }
]
```

---

### POST /api/v1/admin/topics

Create a new topic.

**Required Permission:** `articles:create`

**Request Body:**
```json
{
  "icon": "📰",
  "color": "#3B82F6",
  "sort_order": 0,
  "locales": [
    {
      "locale": "ru",
      "title": "Новости",
      "slug": "novosti",
      "description": "Последние новости компании",
      "meta_title": "Новости | Компания",
      "meta_description": "Читайте последние новости"
    }
  ]
}
```

**Success Response (201):** Created topic object.

---

### PATCH /api/v1/admin/topics/{topic_id}

Update a topic.

**Required Permission:** `articles:update`

**Request Body:**
```json
{
  "icon": "🗞️",
  "color": "#10B981",
  "sort_order": 1,
  "version": 1
}
```

---

### DELETE /api/v1/admin/topics/{topic_id}

Soft delete a topic.

**Required Permission:** `articles:delete`

**Response:** `204 No Content`

---

## Public Endpoints

### GET /api/v1/public/articles

List published articles for public display.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |
| `page` | integer | No | Page number |
| `pageSize` | integer | No | Items per page |
| `topic` | string | No | Filter by topic slug |

**Example Request:**
```bash
GET /api/v1/public/articles?tenant_id={uuid}&locale=ru&topic=novosti
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "article-uuid",
      "slug": "zagolovok-stati",
      "title": "Заголовок статьи",
      "excerpt": "Краткое описание...",
      "content": null,
      "cover_image_url": "https://cdn.example.com/images/cover.jpg",
      "reading_time_minutes": 5,
      "published_at": "2026-01-14T10:00:00Z",
      "meta_title": "SEO заголовок",
      "meta_description": "SEO описание",
      "topics": [
        {
          "id": "topic-uuid",
          "slug": "novosti",
          "title": "Новости",
          "description": "Последние новости",
          "icon": "📰",
          "color": "#3B82F6"
        }
      ]
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

**Note:** `content` is `null` in list view for performance. Fetch single article for full content.

---

### GET /api/v1/public/articles/{slug}

Get published article by slug.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |

**Example Request:**
```bash
GET /api/v1/public/articles/zagolovok-stati?tenant_id={uuid}&locale=ru
```

**Success Response (200):**
```json
{
  "id": "article-uuid",
  "slug": "zagolovok-stati",
  "title": "Заголовок статьи",
  "excerpt": "Краткое описание...",
  "content": "<p>Полный текст статьи...</p>",
  "cover_image_url": "https://cdn.example.com/images/cover.jpg",
  "reading_time_minutes": 5,
  "published_at": "2026-01-14T10:00:00Z",
  "meta_title": "SEO заголовок",
  "meta_description": "SEO описание",
  "topics": [...]
}
```

**Behavior:**
- Only returns published articles
- Automatically increments view count
- Returns 404 if article not found or not published

---

### GET /api/v1/public/topics

List all topics.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |

**Success Response (200):**
```json
[
  {
    "id": "topic-uuid",
    "slug": "novosti",
    "title": "Новости",
    "description": "Последние новости компании",
    "icon": "📰",
    "color": "#3B82F6"
  }
]
```

---

## Frontend Integration

### Articles List Page

```javascript
// Fetch articles with filters
const fetchArticles = async (filters = {}) => {
  const params = new URLSearchParams({
    page: filters.page || 1,
    pageSize: filters.pageSize || 20,
    ...(filters.status && { status: filters.status }),
    ...(filters.topicId && { topicId: filters.topicId })
  })
  
  const { data } = await api.get(`/admin/articles?${params}`)
  return data
}

// Status badge colors
const statusColors = {
  draft: 'gray',
  published: 'green',
  archived: 'orange'
}
```

### Article Editor

```javascript
// Create article
const createArticle = async (articleData) => {
  const { data } = await api.post('/admin/articles', articleData)
  return data
}

// Update article with optimistic locking
const updateArticle = async (id, updates, currentVersion) => {
  try {
    const { data } = await api.patch(`/admin/articles/${id}`, {
      ...updates,
      version: currentVersion
    })
    return data
  } catch (error) {
    if (error.response?.status === 409) {
      // Handle conflict - show diff dialog
      throw new ConflictError('Article was modified by another user')
    }
    throw error
  }
}

// Publish flow
const publishArticle = async (id) => {
  const { data } = await api.post(`/admin/articles/${id}/publish`)
  showNotification({ type: 'success', message: 'Article published!' })
  return data
}
```

### Localization Tabs

```jsx
const ArticleEditor = ({ article }) => {
  const [activeLocale, setActiveLocale] = useState('ru')
  const availableLocales = ['ru', 'en', 'de']
  
  const getLocaleData = (locale) => {
    return article.locales.find(l => l.locale === locale) || {
      locale,
      title: '',
      slug: '',
      content: ''
    }
  }
  
  return (
    <div>
      <Tabs value={activeLocale} onChange={setActiveLocale}>
        {availableLocales.map(locale => (
          <Tab 
            key={locale} 
            value={locale}
            label={
              <span>
                {locale.toUpperCase()}
                {getLocaleData(locale).title ? ' ✓' : ' ⚠️'}
              </span>
            }
          />
        ))}
      </Tabs>
      
      <LocaleForm 
        data={getLocaleData(activeLocale)}
        onChange={(data) => updateLocale(activeLocale, data)}
      />
    </div>
  )
}
```

