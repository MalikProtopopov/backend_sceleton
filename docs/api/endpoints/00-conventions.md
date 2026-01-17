# API Conventions

> Common patterns, headers, pagination, filtering, and error handling

---

## Request Headers

### Required Headers

| Header | When Required | Description |
|--------|---------------|-------------|
| `Authorization` | All admin endpoints | `Bearer {access_token}` |
| `Content-Type` | POST/PATCH/PUT | `application/json` |
| `X-Tenant-ID` | Login endpoint only | Tenant UUID for authentication |

### Optional Headers

| Header | Description |
|--------|-------------|
| `Accept-Language` | Preferred locale (e.g., `ru`, `en`) |
| `X-Request-ID` | Client-generated request ID for tracing |

### Example Request

```http
GET /api/v1/admin/articles HTTP/1.1
Host: api.yoursite.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
Accept-Language: ru
```

---

## Pagination

All list endpoints support pagination using query parameters.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number (1-based) |
| `pageSize` | integer | `20` | Items per page (1-100) |

### Response Format

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### Example

```bash
# Get page 2 with 50 items per page
GET /api/v1/admin/articles?page=2&pageSize=50
```

### Pagination Metadata

| Field | Description |
|-------|-------------|
| `items` | Array of resources for current page |
| `total` | Total count of all matching resources |
| `page` | Current page number |
| `page_size` | Items per page |

**Calculating total pages:**
```javascript
const totalPages = Math.ceil(total / page_size)
```

---

## Sorting

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sortBy` | string | `created_at` | Field to sort by |
| `sortOrder` | string | `desc` | Sort direction: `asc` or `desc` |

### Example

```bash
# Sort articles by title ascending
GET /api/v1/admin/articles?sortBy=title&sortOrder=asc

# Sort by publish date descending (newest first)
GET /api/v1/admin/articles?sortBy=published_at&sortOrder=desc
```

### Sortable Fields (per entity)

| Entity | Sortable Fields |
|--------|-----------------|
| Articles | `created_at`, `updated_at`, `published_at`, `sort_order` |
| Employees | `created_at`, `sort_order` |
| Inquiries | `created_at`, `updated_at` |
| Files | `created_at`, `file_size` |

---

## Filtering

### Common Filter Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Full-text search (where implemented) |
| `isPublished` | boolean | Filter by published status |
| `status` | string | Filter by status (draft/published/archived) |

### Entity-Specific Filters

#### Articles
```bash
GET /api/v1/admin/articles?status=draft&topicId={uuid}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `draft`, `published`, `archived` |
| `topicId` | UUID | Filter by topic |

#### Inquiries
```bash
GET /api/v1/admin/inquiries?status=new&assignedTo={uuid}&utmSource=google
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `new`, `in_progress`, `contacted`, `completed`, `spam` |
| `formId` | UUID | Filter by inquiry form |
| `assignedTo` | UUID | Filter by assigned user |
| `utmSource` | string | Filter by UTM source |

#### Files
```bash
GET /api/v1/admin/files?folder=blog&imagesOnly=true
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `folder` | string | Filter by folder |
| `imagesOnly` | boolean | Only return image files |

---

## Localization

### Locale Parameter (Public API)

Public endpoints accept `locale` query parameter:

```bash
GET /api/v1/public/articles?locale=en&tenant_id={uuid}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `locale` | string | `ru` | Language code (2-5 chars) |

### Localized Content Structure

Entities with translations use a `locales` array:

```json
{
  "id": "article-uuid",
  "status": "published",
  "locales": [
    {
      "locale": "ru",
      "title": "Заголовок статьи",
      "slug": "zagolovok-stati",
      "content": "...",
      "meta_title": "...",
      "meta_description": "..."
    },
    {
      "locale": "en",
      "title": "Article Title",
      "slug": "article-title",
      "content": "...",
      "meta_title": "...",
      "meta_description": "..."
    }
  ]
}
```

### Creating Localized Content

When creating content, provide at least one locale:

```json
{
  "status": "draft",
  "locales": [
    {
      "locale": "ru",
      "title": "Новая статья",
      "slug": "novaya-statya",
      "content": "Текст статьи..."
    }
  ]
}
```

---

## Optimistic Locking

All mutable entities use optimistic locking via `version` field to prevent concurrent edit conflicts.

### How It Works

1. **GET** resource - note the `version` field
2. **PATCH** resource - include current `version` in request body
3. If `version` matches → update succeeds, `version` increments
4. If `version` differs → `409 Conflict` error

### Request Example

```json
PATCH /api/v1/admin/articles/{id}

{
  "title": "Updated Title",
  "version": 3
}
```

### Success Response

```json
{
  "id": "...",
  "title": "Updated Title",
  "version": 4,
  ...
}
```

### Conflict Response (409)

```json
{
  "type": "https://api.cms.local/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Resource was modified by another user. Please refresh and try again.",
  "instance": "/api/v1/admin/articles/abc123"
}
```

### Frontend Handling

```javascript
try {
  await api.patch(`/articles/${id}`, { title, version })
} catch (error) {
  if (error.status === 409) {
    // Reload latest version and show diff to user
    const latest = await api.get(`/articles/${id}`)
    showConflictDialog(localChanges, latest)
  }
}
```

---

## Error Responses

All errors follow [RFC 7807](https://tools.ietf.org/html/rfc7807) Problem Details format.

### Error Response Structure

```json
{
  "type": "https://api.cms.local/errors/{error_type}",
  "title": "Human-readable title",
  "status": 400,
  "detail": "Detailed error message",
  "instance": "/api/v1/admin/articles/123"
}
```

### Error Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Error type URI (for programmatic handling) |
| `title` | string | Short, human-readable summary |
| `status` | integer | HTTP status code |
| `detail` | string | Detailed explanation |
| `instance` | string | URI of the request that caused error |
| `errors` | array | Field-level validation errors (422 only) |

### Common Error Types

#### 400 Bad Request
```json
{
  "type": "https://api.cms.local/errors/bad_request",
  "title": "Bad Request",
  "status": 400,
  "detail": "X-Tenant-ID header is required"
}
```

#### 401 Unauthorized
```json
{
  "type": "https://api.cms.local/errors/authentication_error",
  "title": "Authentication Error",
  "status": 401,
  "detail": "Authorization header required"
}
```

#### 403 Forbidden
```json
{
  "type": "https://api.cms.local/errors/permission_denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "You do not have permission to perform this action",
  "required_permission": "articles:publish"
}
```

#### 404 Not Found
```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Article not found"
}
```

#### 409 Conflict
```json
{
  "type": "https://api.cms.local/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Version mismatch: expected 3, got 2"
}
```

#### 422 Validation Error
```json
{
  "type": "https://api.cms.local/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    {
      "loc": ["body", "locales", 0, "title"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    },
    {
      "loc": ["body", "locales", 0, "slug"],
      "msg": "String should have at least 2 characters",
      "type": "string_too_short"
    }
  ]
}
```

#### 429 Rate Limited
```json
{
  "type": "https://api.cms.local/errors/rate_limit_exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many requests. Please try again later.",
  "retry_after": 60
}
```

---

## Soft Delete

All DELETE operations perform soft delete by setting `deleted_at` timestamp.

### Behavior

- Soft-deleted records are excluded from all queries
- Records can be restored by admin (if UI supports)
- Hard delete requires explicit `hardDelete=true` parameter (where supported)

### Response

```
DELETE /api/v1/admin/articles/{id}
HTTP/1.1 204 No Content
```

### Hard Delete (Assets only)

```bash
DELETE /api/v1/admin/files/{id}?hardDelete=true
```

---

## Rate Limiting

Public endpoints are rate-limited to prevent abuse.

### Current Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /public/inquiries` | 3 requests | 60 seconds |
| All public endpoints | 100 requests | 60 seconds |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705123456
```

### Handling Rate Limits

```javascript
if (response.status === 429) {
  const retryAfter = response.headers.get('Retry-After') || 60
  await sleep(retryAfter * 1000)
  // Retry request
}
```

---

## Date/Time Format

All dates use ISO 8601 format with timezone:

```json
{
  "created_at": "2026-01-14T14:30:00Z",
  "updated_at": "2026-01-14T15:45:30Z",
  "published_at": "2026-01-15T09:00:00Z"
}
```

### Timezone

- All dates stored in UTC
- Frontend should convert to user's local timezone for display
- When sending dates, use UTC or include timezone offset

---

## UUID Format

All resource IDs use UUID v4 format:

```
550e8400-e29b-41d4-a716-446655440000
```

### Example URLs

```
GET /api/v1/admin/articles/550e8400-e29b-41d4-a716-446655440000
PATCH /api/v1/admin/users/123e4567-e89b-12d3-a456-426614174000
```

