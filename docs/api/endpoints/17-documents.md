# Documents API

## Overview

Documents API provides endpoints for managing legal, corporate, and informational documents with support for:
- Localization (multi-language content)
- Version control (document versions like "1.0", "v2.3")
- Document dates
- HTML descriptions (full and excerpt)
- SEO meta tags
- File uploads (PDF, DOC, etc.)
- Publish/draft workflow

## Data Model

### Document

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `tenant_id` | UUID | Tenant identifier |
| `status` | string | `draft`, `published`, `archived` |
| `document_version` | string | Version (e.g., "1.0", "v2.3") |
| `document_date` | date | Date of the document |
| `published_at` | datetime | When published |
| `file_url` | string | URL to document file |
| `sort_order` | int | Display order |
| `version` | int | Optimistic locking version |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `locales` | array | Localized content |

### DocumentLocale

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `document_id` | UUID | Parent document ID |
| `locale` | string | Language code (e.g., "en", "ru") |
| `title` | string | Document title |
| `slug` | string | URL-friendly identifier |
| `excerpt` | string | Short description (max 500) |
| `full_description` | text | Full HTML description |
| `meta_title` | string | SEO title (max 70) |
| `meta_description` | string | SEO description (max 160) |

---

## Admin API Endpoints

### List Documents

```http
GET /api/v1/admin/documents
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page |
| `status` | string | - | Filter by status |
| `search` | string | - | Search in title |
| `document_date_from` | date | - | Filter by date from |
| `document_date_to` | date | - | Filter by date to |
| `sort_by` | string | created_at | Sort field |
| `sort_direction` | string | desc | asc/desc |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "status": "published",
      "document_version": "1.0",
      "document_date": "2026-01-15",
      "published_at": "2026-01-15T10:00:00Z",
      "file_url": "/media/documents/uuid.pdf",
      "sort_order": 0,
      "version": 1,
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-01-15T10:00:00Z",
      "locales": [
        {
          "id": "uuid",
          "document_id": "uuid",
          "locale": "en",
          "title": "Privacy Policy",
          "slug": "privacy-policy",
          "excerpt": "Our privacy policy...",
          "full_description": "<p>Full HTML content...</p>",
          "meta_title": "Privacy Policy | Company",
          "meta_description": "Learn about our privacy practices",
          "created_at": "2026-01-15T10:00:00Z",
          "updated_at": "2026-01-15T10:00:00Z"
        }
      ]
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

**Required Permission:** `documents:read`

---

### Create Document

```http
POST /api/v1/admin/documents
```

**Request Body:**

```json
{
  "status": "draft",
  "document_version": "1.0",
  "document_date": "2026-01-15",
  "sort_order": 0,
  "locales": [
    {
      "locale": "en",
      "title": "Privacy Policy",
      "slug": "privacy-policy",
      "excerpt": "Our commitment to protecting your privacy",
      "full_description": "<h2>Introduction</h2><p>We value your privacy...</p>",
      "meta_title": "Privacy Policy | Company",
      "meta_description": "Learn about our privacy practices"
    },
    {
      "locale": "ru",
      "title": "Политика конфиденциальности",
      "slug": "politika-konfidencialnosti",
      "excerpt": "Наше обязательство по защите вашей конфиденциальности",
      "full_description": "<h2>Введение</h2><p>Мы ценим вашу конфиденциальность...</p>",
      "meta_title": "Политика конфиденциальности | Компания",
      "meta_description": "Узнайте о наших практиках конфиденциальности"
    }
  ]
}
```

**Response:** `201 Created` with DocumentResponse

**Required Permission:** `documents:create`

---

### Get Document

```http
GET /api/v1/admin/documents/{document_id}
```

**Required Permission:** `documents:read`

---

### Update Document

```http
PATCH /api/v1/admin/documents/{document_id}
```

**Request Body:**

```json
{
  "status": "published",
  "document_version": "1.1",
  "document_date": "2026-01-20",
  "locales": [
    {
      "locale": "en",
      "title": "Privacy Policy (Updated)",
      "excerpt": "Updated privacy policy"
    }
  ],
  "version": 1
}
```

> **Note:** The `version` field is required for optimistic locking.

**Required Permission:** `documents:update`

---

### Delete Document

```http
DELETE /api/v1/admin/documents/{document_id}
```

**Response:** `204 No Content`

**Required Permission:** `documents:delete`

---

### Publish Document

```http
POST /api/v1/admin/documents/{document_id}/publish
```

**Response:** DocumentResponse with `status: "published"` and `published_at` set

**Required Permission:** `documents:update`

---

### Unpublish Document

```http
POST /api/v1/admin/documents/{document_id}/unpublish
```

**Response:** DocumentResponse with `status: "draft"`

**Required Permission:** `documents:update`

---

### Upload Document File

```http
POST /api/v1/admin/documents/{document_id}/file
Content-Type: multipart/form-data
```

**Form Data:**

| Field | Type | Description |
|-------|------|-------------|
| `file` | file | Document file (PDF, DOC, etc.) |

**Example (curl):**

```bash
curl -X POST "http://localhost:3000/api/v1/admin/documents/{id}/file" \
  -H "Authorization: Bearer {token}" \
  -F "file=@/path/to/document.pdf"
```

**Response:** DocumentResponse with updated `file_url`

**Required Permission:** `documents:update`

---

### Delete Document File

```http
DELETE /api/v1/admin/documents/{document_id}/file
```

**Response:** DocumentResponse with `file_url: null`

**Required Permission:** `documents:update`

---

## Public API Endpoints

### List Published Documents

```http
GET /api/v1/public/documents
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant identifier |
| `locale` | string | Yes | Language code |
| `page` | int | No | Page number (default: 1) |
| `page_size` | int | No | Items per page (default: 20) |
| `search` | string | No | Search in title |
| `document_date_from` | date | No | Filter by date from |
| `document_date_to` | date | No | Filter by date to |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "privacy-policy",
      "title": "Privacy Policy",
      "excerpt": "Our commitment to protecting your privacy",
      "full_description": null,
      "file_url": "/media/documents/uuid.pdf",
      "document_version": "1.0",
      "document_date": "2026-01-15",
      "published_at": "2026-01-15T10:00:00Z",
      "meta_title": "Privacy Policy | Company",
      "meta_description": "Learn about our privacy practices"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

> **Note:** `full_description` is not included in list response to reduce payload size.

---

### Get Published Document by Slug

```http
GET /api/v1/public/documents/{slug}
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant identifier |
| `locale` | string | Yes | Language code |

**Response:**

```json
{
  "id": "uuid",
  "slug": "privacy-policy",
  "title": "Privacy Policy",
  "excerpt": "Our commitment to protecting your privacy",
  "full_description": "<h2>Introduction</h2><p>We value your privacy...</p>",
  "file_url": "/media/documents/uuid.pdf",
  "document_version": "1.0",
  "document_date": "2026-01-15",
  "published_at": "2026-01-15T10:00:00Z",
  "meta_title": "Privacy Policy | Company",
  "meta_description": "Learn about our privacy practices"
}
```

---

## Error Responses

### 404 Not Found

```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Document not found: {id}"
}
```

### 409 Conflict (Slug exists)

```json
{
  "type": "https://api.cms.local/errors/slug_exists",
  "title": "Slug Already Exists",
  "status": 409,
  "detail": "Slug 'privacy-policy' already exists for locale 'en'"
}
```

### 409 Conflict (Version conflict)

```json
{
  "type": "https://api.cms.local/errors/version_conflict",
  "title": "Version Conflict",
  "status": 409,
  "detail": "Document version conflict: expected 2, got 1"
}
```

---

## Frontend Integration

### TypeScript Types

```typescript
interface Document {
  id: string;
  tenant_id: string;
  status: 'draft' | 'published' | 'archived';
  document_version: string | null;
  document_date: string | null; // ISO date
  published_at: string | null;  // ISO datetime
  file_url: string | null;
  sort_order: number;
  version: number;
  created_at: string;
  updated_at: string;
  locales: DocumentLocale[];
}

interface DocumentLocale {
  id: string;
  document_id: string;
  locale: string;
  title: string;
  slug: string;
  excerpt: string | null;
  full_description: string | null;
  meta_title: string | null;
  meta_description: string | null;
  created_at: string;
  updated_at: string;
}

interface DocumentPublic {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  full_description: string | null;
  file_url: string | null;
  document_version: string | null;
  document_date: string | null;
  published_at: string | null;
  meta_title: string | null;
  meta_description: string | null;
}
```

### File URL Handling

The `file_url` field returns a relative path (e.g., `/media/documents/uuid.pdf`). Frontend should:

1. Prepend the API base URL for display
2. Handle CDN URLs in production

```typescript
const getFileUrl = (fileUrl: string | null): string | null => {
  if (!fileUrl) return null;
  return `${process.env.API_BASE_URL}${fileUrl}`;
};
```

### HTML Content

The `full_description` field contains HTML content. Use a sanitizer before rendering:

```tsx
import DOMPurify from 'dompurify';

const DocumentContent = ({ html }: { html: string }) => (
  <div 
    dangerouslySetInnerHTML={{ 
      __html: DOMPurify.sanitize(html) 
    }} 
  />
);
```

---

## Use Cases

### Legal Documents
- Privacy Policy
- Terms of Service
- Cookie Policy
- GDPR Compliance

### Corporate Documents
- Annual Reports
- Investor Presentations
- Company Policies
- Certificates

### Informational
- Product Documentation
- User Guides
- FAQs (extended format)
- White Papers

