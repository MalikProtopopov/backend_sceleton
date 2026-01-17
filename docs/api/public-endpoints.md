# Public API Endpoints

## Overview

This document lists all public API endpoints that do not require authentication. These endpoints are designed for frontend consumption to display content on the public website.

**Base URL:** `/api/v1`

---

## Content Endpoints

### Articles

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/articles` | List published articles |
| GET | `/public/articles/{slug}` | Get article by slug |

**Query Parameters for List:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code (e.g., "en", "ru")
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)
- `topic` - Filter by topic slug

---

### Topics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/topics` | List all topics |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code

---

### FAQ

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/faq` | List published FAQs |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code
- `category` - Filter by category

---

### Cases (Portfolio)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/cases` | List published cases |
| GET | `/public/cases/{slug}` | Get case by slug |

**Query Parameters for List:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)
- `featured` - Filter featured cases

---

### Reviews (Testimonials)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/reviews` | List approved reviews |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

---

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/documents` | List published documents |
| GET | `/public/documents/{slug}` | Get document by slug |

**Query Parameters for List:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)
- `search` - Search in title
- `document_date_from` - Filter by date from
- `document_date_to` - Filter by date to

---

## Company Endpoints

### Services

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/services` | List published services |
| GET | `/public/services/{slug}` | Get service by slug |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code

---

### Employees (Team)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/employees` | List published employees |
| GET | `/public/employees/{slug}` | Get employee by slug |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code

---

### Practice Areas

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/practice-areas` | List practice areas |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code

---

### Advantages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/advantages` | List company advantages |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `locale` (required) - Language code

---

### Contacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/contacts` | Get contact information |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier

---

## Leads Endpoints

### Inquiries

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/public/inquiries` | Submit inquiry form |

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "message": "I would like to inquire about...",
  "source": "website",
  "service_id": "uuid (optional)"
}
```

**Rate Limited:** 3 requests per 60 seconds per IP

---

## SEO Endpoints

### Meta Tags

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/seo/meta` | Get SEO meta for a page |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier
- `page_type` (required) - Page type (home, about, services, etc.)
- `slug` - Slug for dynamic pages
- `locale` - Language code

---

### Sitemap

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/sitemap.xml` | Generate sitemap XML |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier

**Response:** XML sitemap

---

### Robots.txt

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/public/robots.txt` | Get robots.txt |

**Query Parameters:**
- `tenant_id` (required) - Tenant identifier

**Response:** Plain text robots.txt

---

## Media Endpoints

### Media Files

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/media/{path}` | Serve media files |

**Note:** This endpoint serves images and files from S3/MinIO storage.

**Example:**
```
GET /media/articles/uuid.png
GET /media/documents/uuid.pdf
```

---

## Common Response Formats

### List Response

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### Error Response

```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Resource not found"
}
```

---

## Frontend Integration Notes

### Base URL Configuration

```typescript
// Environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000';
const API_PREFIX = '/api/v1';

// Helper function
const apiUrl = (path: string) => `${API_BASE_URL}${API_PREFIX}${path}`;
```

### Common Query Parameters

All public endpoints require `tenant_id`. Most also require `locale`:

```typescript
const params = new URLSearchParams({
  tenant_id: process.env.NEXT_PUBLIC_TENANT_ID,
  locale: 'en',
  page: '1',
  page_size: '20'
});

const response = await fetch(`${apiUrl('/public/articles')}?${params}`);
```

### Media URLs

Media URLs are returned as relative paths. Prepend the base URL:

```typescript
const getMediaUrl = (path: string | null) => {
  if (!path) return null;
  return `${API_BASE_URL}${path}`;
};
```

---

## Summary Table

| Category | Endpoint | Method | Auth |
|----------|----------|--------|------|
| Content | /public/articles | GET | No |
| Content | /public/articles/{slug} | GET | No |
| Content | /public/topics | GET | No |
| Content | /public/faq | GET | No |
| Content | /public/cases | GET | No |
| Content | /public/cases/{slug} | GET | No |
| Content | /public/reviews | GET | No |
| Content | /public/documents | GET | No |
| Content | /public/documents/{slug} | GET | No |
| Company | /public/services | GET | No |
| Company | /public/services/{slug} | GET | No |
| Company | /public/employees | GET | No |
| Company | /public/employees/{slug} | GET | No |
| Company | /public/practice-areas | GET | No |
| Company | /public/advantages | GET | No |
| Company | /public/contacts | GET | No |
| Leads | /public/inquiries | POST | No |
| SEO | /public/seo/meta | GET | No |
| SEO | /public/sitemap.xml | GET | No |
| SEO | /public/robots.txt | GET | No |
| Media | /media/{path} | GET | No |

**Total Public Endpoints:** 21

