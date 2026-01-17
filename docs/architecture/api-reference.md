# API Reference: Corporate CMS Backend
## Полный список всех эндпоинтов

---

## Public API (Read-only)

### Services

```
GET /api/v1/public/services
  Description: List all published services
  Query Params:
    - locale: string (default: "en")
    - limit: integer (1-100, default: 20)
    - page: integer (default: 1)
    - search: string (optional)
    - sort: string (default: "sort_order")
  
  Response 200:
  {
    "data": [
      {
        "id": "uuid",
        "slug": "consulting",
        "name": "Consulting",
        "description": "...",
        "icon_url": "https://...",
        "created_at": "2024-01-14T12:00:00Z"
      }
    ],
    "meta": {
      "total": 5,
      "page": 1,
      "limit": 20,
      "pages": 1,
      "has_next": false,
      "has_prev": false
    }
  }

GET /api/v1/public/services/{slug}
  Description: Get single service by slug
  Query Params:
    - locale: string (default: "en")
  
  Response 200:
  {
    "data": {
      "id": "uuid",
      "slug": "consulting",
      "name": "Consulting",
      "description": "...",
      "icon_url": "https://..."
    }
  }
  
  Response 404: Service not found
```

### Employees

```
GET /api/v1/public/employees
  Description: List team members
  Query Params:
    - locale: string (default: "en")
    - practice_area_id: uuid (optional)
    - limit: integer (1-100, default: 20)
    - page: integer (default: 1)
    - search: string (optional)
  
  Response 200:
  {
    "data": [
      {
        "id": "uuid",
        "slug": "john-doe",
        "first_name": "John",
        "last_name": "Doe",
        "title": "Senior Developer",
        "bio": "...",
        "photo_url": "https://...",
        "practice_areas": ["Consulting", "Development"]
      }
    ],
    "meta": {...}
  }

GET /api/v1/public/employees/{slug}
  Description: Get single employee
  Query Params:
    - locale: string (default: "en")
  
  Response 200: {employee object}
  Response 404: Employee not found
```

### Articles

```
GET /api/v1/public/articles
  Description: List published articles
  Query Params:
    - locale: string (default: "en")
    - topic_id: uuid (optional)
    - limit: integer (1-100, default: 20)
    - page: integer (default: 1)
    - search: string (optional)
    - sort: string (default: "-published_at")
    - featured: boolean (optional)
  
  Response 200:
  {
    "data": [
      {
        "id": "uuid",
        "slug": "seo-tips",
        "title": "SEO Tips for 2024",
        "description": "...",
        "featured": true,
        "featured_image_url": "https://...",
        "published_at": "2024-01-14T12:00:00Z"
      }
    ],
    "meta": {...}
  }

GET /api/v1/public/articles/{slug}
  Description: Get single article
  Query Params:
    - locale: string (default: "en")
  
  Response 200:
  {
    "data": {
      "id": "uuid",
      "slug": "seo-tips",
      "title": "SEO Tips for 2024",
      "description": "...",
      "content": "Full article content...",
      "topic_ids": ["uuid1", "uuid2"],
      "published_at": "2024-01-14T12:00:00Z"
    }
  }
```

### Cases

```
GET /api/v1/public/cases
  Description: List portfolio cases
  Query Params:
    - locale: string (default: "en")
    - service_id: uuid (optional)
    - limit: integer (1-100, default: 20)
    - page: integer (default: 1)
    - search: string (optional)
    - featured: boolean (optional)
  
  Response 200: {cases array with meta}

GET /api/v1/public/cases/{slug}
  Description: Get single case
  Response 200: {case object}
  Response 404: Case not found
```

### FAQ

```
GET /api/v1/public/faq
  Description: List FAQ items
  Query Params:
    - locale: string (default: "en")
    - topic_id: uuid (optional)
    - limit: integer (1-100, default: 20)
    - page: integer (default: 1)
  
  Response 200:
  {
    "data": [
      {
        "id": "uuid",
        "question": "What is your pricing?",
        "answer": "We offer flexible pricing...",
        "topic_id": "uuid"
      }
    ],
    "meta": {...}
  }
```

### Reviews

```
GET /api/v1/public/reviews
  Description: List published reviews
  Query Params:
    - limit: integer (1-100, default: 20)
    - page: integer (default: 1)
    - sort: string (default: "-rating,-created_at")
  
  Response 200: {reviews array}
```

### Contacts

```
GET /api/v1/public/contacts
  Description: Get company contacts
  Response 200:
  {
    "data": {
      "phone": "+1234567890",
      "email": "info@example.com",
      "addresses": [
        {
          "type": "office",
          "street_address": "123 Main St",
          "city": "New York",
          "postal_code": "10001",
          "phone": "+1234567890"
        }
      ]
    }
  }
```

### Inquiries (Forms)

```
POST /api/v1/public/inquiries
  Description: Submit contact form
  Rate Limit: 5 per IP per hour
  
  Body:
  {
    "form_id": "uuid",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "company_name": "ACME Corp",
    "message": "I'm interested in..."
  }
  
  Response 201:
  {
    "data": {
      "id": "uuid",
      "created_at": "2024-01-14T12:00:00Z"
    }
  }
  
  Response 422: Validation error
  Response 429: Rate limit exceeded
```

### SEO

```
GET /api/v1/public/sitemap.xml
  Description: XML sitemap
  Query Params:
    - locale: string (optional)
  
  Response 200: XML with all published pages

GET /api/v1/public/.well-known/robots.txt
  Description: Robots.txt
  
  Response 200: text/plain
```

### Health

```
GET /health
  Description: Public health check
  Response 200: { "status": "ok", "version": "1.0.0" }
```

---

## Admin API (Full CRUD + RBAC)

### Authentication

```
POST /api/v1/auth/login
  Description: Login and get JWT token
  
  Body:
  {
    "email": "admin@example.com",
    "password": "password123"
  }
  
  Response 200:
  {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "uuid",
      "email": "admin@example.com",
      "first_name": "Admin",
      "role": {
        "id": "uuid",
        "name": "admin",
        "permissions": ["*"]
      }
    }
  }
  
  Response 401: Invalid credentials

GET /api/v1/admin/me
  Description: Get current user info
  Auth: Required (JWT)
  
  Response 200: {user object}
  Response 401: Unauthorized
```

### Articles (Admin)

```
GET /api/v1/admin/articles
  Description: List all articles (including drafts)
  Auth: Required
  Permission: view_articles
  
  Query Params:
    - status: string ("draft", "published", "archived")
    - topic_id: uuid
    - locale: string
    - limit: integer
    - page: integer
    - search: string
  
  Response 200:
  {
    "data": [
      {
        "id": "uuid",
        "slug": "my-article",
        "status": "draft",
        "featured": false,
        "locales": [
          {
            "locale": "en",
            "title": "My Article",
            "description": "...",
            "content": "...",
            "slug": "my-article"
          },
          {
            "locale": "ru",
            "title": "Моя статья",
            "description": "...",
            "content": "...",
            "slug": "moya-statya"
          }
        ],
        "topic_ids": ["uuid1"],
        "created_at": "2024-01-14T12:00:00Z",
        "updated_at": "2024-01-14T12:00:00Z"
      }
    ],
    "meta": {...}
  }

GET /api/v1/admin/articles/{id}
  Description: Get single article
  Auth: Required
  Permission: view_articles
  
  Response 200: {article object}
  Response 404: Not found

POST /api/v1/admin/articles
  Description: Create article
  Auth: Required
  Permission: create_articles
  
  Body:
  {
    "slug": "my-article",
    "status": "draft",
    "featured": false,
    "featured_image_url": "https://...",
    "locales": {
      "en": {
        "title": "My Article",
        "description": "Short description",
        "content": "Full content...",
        "slug": "my-article"
      },
      "ru": {
        "title": "Моя статья",
        "description": "Краткое описание",
        "content": "Полный контент...",
        "slug": "moya-statya"
      }
    },
    "topic_ids": ["uuid1"]
  }
  
  Response 201: {article object}
  Response 422: Validation error
  Response 409: Slug already exists

PATCH /api/v1/admin/articles/{id}
  Description: Update article
  Auth: Required
  Permission: edit_articles
  
  Body: (partial update)
  {
    "status": "published",
    "featured": true,
    "locales": {
      "en": {
        "title": "Updated Title",
        "slug": "updated-slug"
      }
    },
    "topic_ids": ["uuid1", "uuid2"]
  }
  
  Response 200: {updated article}
  Response 404: Not found
  Response 409: Conflict

DELETE /api/v1/admin/articles/{id}
  Description: Delete article (soft delete)
  Auth: Required
  Permission: delete_articles
  
  Response 204: No content
  Response 404: Not found
```

### Services (Admin)

```
GET /api/v1/admin/services
  Description: List all services
  Auth: Required
  Permission: view_services
  
  Query Params: status, locale, limit, page, search
  
  Response 200: {services array}

POST /api/v1/admin/services
  Description: Create service
  Auth: Required
  Permission: create_services
  
  Body:
  {
    "slug": "consulting",
    "status": "published",
    "icon_url": "https://...",
    "locales": {
      "en": {
        "name": "Consulting",
        "description": "...",
        "slug": "consulting"
      }
    }
  }
  
  Response 201: {service object}

PATCH /api/v1/admin/services/{id}
  Description: Update service
  Auth: Required
  Permission: edit_services
  
  Response 200: {updated service}

DELETE /api/v1/admin/services/{id}
  Description: Delete service
  Auth: Required
  Permission: delete_services
  
  Response 204
```

### SEO (Admin)

```
GET /api/v1/admin/seo/routes
  Description: List SEO metadata
  Auth: Required
  Permission: view_seo
  
  Query Params:
    - path: string (optional)
    - locale: string (optional)
    - limit: integer
    - page: integer
  
  Response 200: {seo routes array}

PUT /api/v1/admin/seo/routes
  Description: Create or update SEO metadata
  Auth: Required
  Permission: edit_seo
  
  Body:
  {
    "path": "/services",
    "locale": "en",
    "title": "Our Services",
    "description": "We offer...",
    "og_title": "Services | ACME",
    "og_description": "...",
    "og_image_url": "https://...",
    "canonical_url": "self",
    "robots_directive": "index, follow",
    "json_ld": {
      "@context": "https://schema.org",
      "@type": "BreadcrumbList"
    }
  }
  
  Response 200 or 201: {seo route}

POST /api/v1/admin/seo/redirects
  Description: Create redirect
  Auth: Required
  Permission: edit_seo
  
  Body:
  {
    "from_path": "/old-service",
    "to_path": "/services/consulting",
    "status_code": 301
  }
  
  Response 201: {redirect}

GET /api/v1/admin/seo/routes/hreflang
  Description: Get hreflang for path
  Auth: Required
  Permission: view_seo
  
  Query Params:
    - path: string (required)
  
  Response 200:
  {
    "data": [
      { "locale": "en", "path": "/services", "canonical": true },
      { "locale": "ru", "path": "/services", "canonical": false }
    ]
  }
```

### Leads (Admin)

```
GET /api/v1/admin/inquiries
  Description: List all leads
  Auth: Required
  Permission: view_leads
  
  Query Params:
    - status: string
    - limit: integer
    - page: integer
    - sort: string
    - date_from: ISO date
    - date_to: ISO date
  
  Response 200: {inquiries array}

PATCH /api/v1/admin/inquiries/{id}
  Description: Update inquiry status
  Auth: Required
  Permission: edit_leads
  
  Body:
  {
    "status": "contacted"
  }
  
  Response 200: {updated inquiry}

DELETE /api/v1/admin/inquiries/{id}
  Description: Delete inquiry
  Auth: Required
  Permission: delete_leads
  
  Response 204
```

### Users (Admin)

```
GET /api/v1/admin/users
  Description: List admin users
  Auth: Required
  Permission: manage_users
  
  Response 200: {users array}

POST /api/v1/admin/users
  Description: Create admin user
  Auth: Required
  Permission: manage_users
  
  Body:
  {
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe",
    "role_id": "uuid"
  }
  
  Response 201: {user object}

PATCH /api/v1/admin/users/{id}
  Description: Update user
  Auth: Required
  Permission: manage_users
  
  Body:
  {
    "first_name": "Jane",
    "role_id": "uuid",
    "is_active": true
  }
  
  Response 200: {updated user}

DELETE /api/v1/admin/users/{id}
  Description: Delete user (soft delete)
  Auth: Required
  Permission: manage_users
  
  Response 204
```

### Audit Log (Admin)

```
GET /api/v1/admin/audit-log
  Description: List audit entries
  Auth: Required
  Permission: view_audit
  
  Query Params:
    - entity_type: string
    - entity_id: uuid
    - user_id: uuid
    - action: string ("CREATE", "UPDATE", "DELETE")
    - limit: integer
    - page: integer
    - sort: string
  
  Response 200:
  {
    "data": [
      {
        "id": "uuid",
        "action": "UPDATE",
        "entity_type": "article",
        "entity_id": "uuid",
        "user_id": "uuid",
        "old_values": { "status": "draft" },
        "new_values": { "status": "published" },
        "ip_address": "192.168.1.1",
        "created_at": "2024-01-14T12:00:00Z"
      }
    ],
    "meta": {...}
  }
```

### Health (Admin)

```
GET /api/v1/admin/health
  Description: Detailed health check
  Auth: Required
  
  Response 200:
  {
    "status": "ok",
    "database": "connected",
    "cache": "connected",
    "uptime": 86400,
    "memory_usage_mb": 256
  }
```

---

## Error Responses (RFC 7807)

```
400 Bad Request:
{
  "type": "https://api.example.com/errors/bad_request",
  "title": "Bad Request",
  "status": 400,
  "detail": "Invalid request format"
}

422 Validation Error:
{
  "type": "https://api.example.com/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more validation errors occurred",
  "errors": [
    { "field": "title", "message": "Title is required" },
    { "field": "slug", "message": "Slug must match pattern" }
  ]
}

401 Unauthorized:
{
  "type": "https://api.example.com/errors/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Missing or invalid token"
}

403 Forbidden:
{
  "type": "https://api.example.com/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "Insufficient permissions"
}

404 Not Found:
{
  "type": "https://api.example.com/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Resource not found"
}

409 Conflict:
{
  "type": "https://api.example.com/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Resource already exists"
}

429 Rate Limited:
{
  "type": "https://api.example.com/errors/rate_limited",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit exceeded"
}

500 Internal Server Error:
{
  "type": "https://api.example.com/errors/internal_server_error",
  "title": "Internal Server Error",
  "status": 500,
  "detail": "An unexpected error occurred"
}
```

---

## Authentication

All admin endpoints require JWT token in Authorization header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token obtained via:
```
POST /api/v1/auth/login
```

---

## Pagination

All list endpoints support:

```
Query Params:
  - limit: integer (1-100, default: 20)
  - page: integer (default: 1)

Response meta:
{
  "total": 150,          # total items
  "page": 1,             # current page
  "limit": 20,           # items per page
  "pages": 8,            # total pages
  "has_next": true,      # has next page
  "has_prev": false      # has prev page
}
```

---

## Filtering & Sorting

All list endpoints support:

```
Query Params:
  - status: string (e.g., "published", "draft")
  - locale: string (e.g., "en", "ru")
  - search: string (full-text search)
  - sort: string (field name, prefix "-" for DESC)

Examples:
  ?status=published&locale=en&sort=-created_at
  ?search=consulting&limit=50&page=1
  ?sort=title,-updated_at
```

---

## Rate Limiting

Public API:
- 100 requests per minute per IP

Admin API:
- No per-request limit, but global rate limit may apply

Limit info in response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

---

**Last Updated:** 2024-01-14
**API Version:** v1
**Base URL:** /api/v1
