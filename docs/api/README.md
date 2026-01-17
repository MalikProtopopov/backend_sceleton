# Admin Panel API Documentation

> Backend API Reference for Corporate CMS Engine v1.0

## Quick Start

### Base URL
```
Production: https://api.yoursite.com/api/v1
Development: http://localhost:8000/api/v1
```

### Authentication
All admin endpoints require JWT authentication. See [01-authentication.md](./01-authentication.md) for details.

```bash
# Login to get tokens
curl -X POST /api/v1/auth/login \
  -H "X-Tenant-ID: {tenant_uuid}" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "..."}'

# Use access token for subsequent requests
curl -X GET /api/v1/admin/articles \
  -H "Authorization: Bearer {access_token}"
```

### Multi-Tenant Architecture
Every request must include tenant context:
- **Login**: Pass `X-Tenant-ID` header
- **Authenticated requests**: Tenant ID is extracted from JWT token

---

## Table of Contents

### Foundation
| Document | Description |
|----------|-------------|
| [00-conventions.md](./00-conventions.md) | Common patterns: pagination, filtering, errors, versioning |
| [01-authentication.md](./01-authentication.md) | Login flow, JWT tokens, RBAC, permissions |

### Content Module
| Document | Endpoints | Description |
|----------|-----------|-------------|
| [02-articles.md](./02-articles.md) | 8 admin + 2 public | Articles CRUD, topics, publish workflow |
| [03-faq.md](./03-faq.md) | 5 admin + 1 public | FAQ management |
| [04-reviews.md](./04-reviews.md) | 7 admin + 1 public | Reviews/testimonials with moderation |
| [14-cases-dashboard-bulk.md](./14-cases-dashboard-bulk.md) | 11 admin + 2 public | Cases CRUD, Dashboard, Bulk operations |
| [17-documents.md](./17-documents.md) | 9 admin + 2 public | Documents CRUD, localization, versioning, file upload |

### Company Module
| Document | Endpoints | Description |
|----------|-----------|-------------|
| [05-services.md](./05-services.md) | 5 admin + 2 public | Services offered |
| [06-employees.md](./06-employees.md) | 5 admin + 6 public | Team, practice areas, advantages, contacts |

### Operations
| Document | Endpoints | Description |
|----------|-----------|-------------|
| [07-leads.md](./07-leads.md) | 11 admin + 1 public | Inquiries, forms, analytics |
| [08-media.md](./08-media.md) | 5 admin | File uploads, S3 integration |
| [09-seo.md](./09-seo.md) | 9 admin + 3 public | SEO routes, redirects, sitemap |
| [16-image-upload.md](./16-image-upload.md) | 16 admin | Image upload for all entities (multipart/form-data) |

### Administration
| Document | Endpoints | Description |
|----------|-----------|-------------|
| [10-users-rbac.md](./10-users-rbac.md) | 7 endpoints | User management, roles, permissions |
| [11-localization.md](./11-localization.md) | - | Multi-language content structure |
| [13-tenants-settings.md](./13-tenants-settings.md) | 8 endpoints | Tenants, settings, feature flags |
| [15-audit-export-search.md](./15-audit-export-search.md) | 4+ endpoints | Audit log, export, search, roles CRUD, company info |

### Reference
| Document | Description |
|----------|-------------|
| [screen-api-mapping.md](./screen-api-mapping.md) | Admin UI screens → API endpoints mapping |
| [gap-analysis.md](./gap-analysis.md) | Missing features, backend vs UX spec |
| [public-endpoints.md](./public-endpoints.md) | Complete list of all public API endpoints (21 endpoints) |

---

## API Overview

### Endpoint Categories

| Prefix | Auth Required | Description |
|--------|---------------|-------------|
| `/api/v1/auth/*` | Varies | Authentication endpoints |
| `/api/v1/admin/*` | Yes (JWT) | Admin panel endpoints |
| `/api/v1/public/*` | No | Public website endpoints |

### HTTP Methods

| Method | Usage |
|--------|-------|
| `GET` | Retrieve resources (list or single) |
| `POST` | Create new resource |
| `PATCH` | Partial update (with optimistic locking) |
| `PUT` | Full replace or upsert |
| `DELETE` | Soft delete (sets `deleted_at`) |

### Response Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `204` | No Content (successful DELETE) |
| `400` | Bad Request (validation error) |
| `401` | Unauthorized (missing/invalid token) |
| `403` | Forbidden (insufficient permissions) |
| `404` | Not Found |
| `409` | Conflict (optimistic lock failure) |
| `422` | Unprocessable Entity (business logic error) |
| `429` | Rate Limited |
| `500` | Internal Server Error |

---

## Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **Cache**: Redis
- **File Storage**: S3-compatible (MinIO/AWS)
- **Authentication**: JWT (access + refresh tokens)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.4.0 | 2026-01-15 | Added Documents module (9 admin + 2 public endpoints), public-endpoints.md reference |
| 1.3.0 | 2026-01-15 | Added 16 image upload endpoints (multipart/form-data), removed URL fields from create/update schemas |
| 1.2.0 | 2026-01-15 | Added Cases, Dashboard, Bulk ops, Audit, Export, Search |
| 1.1.0 | 2026-01-14 | Added Cases (planned), Tenants, verified schemas |
| 1.0.0 | 2026-01-14 | Initial documentation |

