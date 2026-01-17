# API Endpoints Analysis & Implementation Guide
## Corporate CMS Admin Panel v1.0

**Document Date:** January 15, 2026  
**Status:** Requirements & Architecture Definition  
**For:** FastAPI Backend Development

---

## SUMMARY: Статус описания в Product Spec

### ✅ ОПИСАНЫ В SPEC

Базовая CRUD структура в Appendix C:
- `GET /api/v1/admin/articles` ✅
- `POST /api/v1/admin/articles` ✅
- `PATCH /api/v1/admin/articles/{id}` ✅
- `DELETE /api/v1/admin/articles/{id}` ✅
- User management endpoints ✅
- Role management endpoints ✅
- Media upload endpoints ✅
- Audit logs endpoints ✅

### ⚠️ УПОМЯНУТЫ БЕЗ ДЕТАЛЕЙ

| Группа | Статус | Требует |
|--------|--------|---------|
| **Cases API** (9 endpoints) | ⚠️ Упомянут как "Case Studies CRUD" | ✅ Схема Case Study, фильтры, публикация |
| **Dashboard** (1) | ⚠️ "Overview (stats, recent activity)" | ✅ Какие метрики? Какой формат? |
| **Bulk Operations** (1) | ⚠️ "Bulk actions: Publish, Unpublish, Archive" | ✅ Универсальная schema, async handling |
| **Search** | ⚠️ "Global search (Cmd+K)" | ✅ Какие поля искать? Full-text или LIKE? |
| **Export** | ⚠️ "Export to CSV" | ✅ Какие колонки? Какой формат? |

---

## PRIORITY 1: CRITICAL FOR MVP (20 endpoints)

### 1. Cases API (9 endpoints)

**Endpoints:**
```
GET    /api/v1/admin/cases              # List all cases
POST   /api/v1/admin/cases              # Create
GET    /api/v1/admin/cases/{id}         # Get single
PATCH  /api/v1/admin/cases/{id}         # Edit
DELETE /api/v1/admin/cases/{id}         # Soft delete
POST   /api/v1/admin/cases/{id}/publish # Publish
POST   /api/v1/admin/cases/{id}/unpublish
GET    /api/v1/public/cases             # Public portfolio
GET    /api/v1/public/cases/{slug}      # Public detail
```

**Case Study Model:**
```python
class CaseStudy(Base, UUIDMixin, TimestampMixin, TenantMixin):
    # Basic
    title: str                          # Required
    slug: str                           # Unique
    summary: str                        # Max 160 chars
    description: str                    # Rich text
    
    # Business
    client_name: str
    industry: str
    challenge: str
    solution: str
    result_summary: str
    
    # Media
    featured_image_id: UUID | None
    
    # Relations
    practice_area_ids: list[UUID]      # Many-to-many
    team_member_ids: list[UUID]
    service_ids: list[UUID]
    
    # Status
    status: Enum["draft", "published", "archived"]
    published_at: datetime | None
    featured: bool
    
    # SEO
    meta_title: str | None
    meta_description: str | None
```

**Query parameters (GET /admin/cases):**
```python
status: "draft" | "published" | "archived"
industry: str
featured: bool
search: str              # Search in title, client_name
page: int = 1
page_size: int = 25
sort_by: "title" | "created_at" | "published_at"
sort_direction: "asc" | "desc"
```

**Response structure:**
```json
{
  "data": [
    {
      "id": "uuid",
      "title": "Case Title",
      "client_name": "Client",
      "industry": "Tech",
      "status": "published",
      "featured_image_url": "https://...",
      "published_at": "2026-01-14T00:00:00Z",
      "seo_completion": 85
    }
  ],
  "pagination": {
    "total": 42,
    "page": 1,
    "page_size": 25,
    "total_pages": 2
  }
}
```

---

### 2. Dashboard API (1 endpoint)

**Endpoint:**
```
GET /api/v1/admin/dashboard
```

**Response structure:**
```json
{
  "summary": {
    "total_articles": 42,
    "total_cases": 12,
    "total_team_members": 8,
    "total_inquiries": 156,
    "pending_inquiries": 23,
    "published_content": 42,
    "draft_content": 8,
    "scheduled_content": 3
  },
  
  "recent_activity": [
    {
      "type": "article_published",
      "timestamp": "2026-01-14T14:30:00Z",
      "user": {"name": "Alice Smith"},
      "resource": {"type": "article", "title": "SEO Guide"}
    }
  ],
  
  "content_by_status": {
    "articles": {"published": 20, "draft": 5, "scheduled": 2},
    "cases": {"published": 12, "draft": 1}
  },
  
  "inquiries_summary": {
    "total_this_month": 45,
    "by_source": {"contact_form": 30, "demo_request": 10},
    "by_status": {"new": 23, "in_progress": 12, "done": 10}
  }
}
```

**Implementation:**
- Cache for 5 minutes (Redis)
- Use COUNT queries (not full fetches)
- Limit recent activity to 10 items

---

### 3. Audit Log API (1 endpoint)

**Endpoint:**
```
GET /api/v1/admin/audit-logs
```

**Query parameters:**
```python
user_id: UUID | None
resource_type: "article" | "case" | "employee" | "user" | "media"
resource_id: UUID | None
action: "create" | "update" | "delete" | "publish"
date_from: date
date_to: date
page: int = 1
page_size: int = 25
```

**Response structure:**
```json
{
  "data": [
    {
      "id": "uuid",
      "timestamp": "2026-01-14T14:15:00Z",
      "user": {"email": "alice@...", "name": "Alice Smith"},
      "action": "update",
      "resource_type": "article",
      "resource_id": "uuid",
      "resource_name": "Article Title",
      "changes": {
        "title": {"old": "Old", "new": "New"},
        "status": {"old": "draft", "new": "published"}
      },
      "ip_address": "192.168.1.1",
      "status": "success"
    }
  ],
  "pagination": {"total": 1234, "page": 1, "page_size": 25}
}
```

---

### 4. Bulk Operations API (1 endpoint)

**Endpoint:**
```
POST /api/v1/admin/bulk
```

**Request:**
```json
{
  "resource_type": "articles",
  "action": "publish",
  "ids": ["uuid1", "uuid2", "uuid3"],
  "payload": {
    "tags": ["tag1"],
    "owner_id": "uuid"
  }
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "processing" | "completed",
  "summary": {
    "total": 5,
    "succeeded": 5,
    "failed": 0,
    "details": [
      {"id": "uuid", "status": "success", "message": "Published"}
    ]
  }
}
```

**Logic:**
- < 100 items: synchronous
- ≥ 100 items: async job with Celery

---

### 5. Search Parameter (4 existing endpoints)

Add `search` query parameter:
```
GET /api/v1/admin/articles?search=SEO
GET /api/v1/admin/cases?search=tech+client
GET /api/v1/admin/employees?search=john
GET /api/v1/admin/inquiries?search=demo
```

**Search logic:**
- Case-insensitive partial match
- Search fields: title, slug, content, name, email
- Use PostgreSQL full-text search with GIN index
- Debounce: 300ms on frontend

---

### 6. Role Management CRUD (3 endpoints)

**Endpoints:**
```
POST   /api/v1/auth/roles
PATCH  /api/v1/auth/roles/{role_id}
DELETE /api/v1/auth/roles/{role_id}
```

**Request schema:**
```json
{
  "name": "SEO Specialist",
  "description": "Can view and edit SEO metadata",
  "is_system": false,
  "permissions": {
    "content": {
      "articles": ["read", "update_seo"],
      "cases": ["read", "update_seo"]
    },
    "seo": {
      "seo_routes": ["read", "write"]
    }
  }
}
```

**Predefined roles:**
- Owner (full access)
- Admin (full except user management)
- Editor (create/edit/publish)
- Manager (Editor + approve + analytics)
- SEO Specialist (read all + update SEO only)
- Sales Manager (view inquiries + export)
- HR Manager (manage employees)
- Viewer (read-only)

---

### 7. Export API (1 endpoint)

**Endpoint:**
```
GET /api/v1/admin/export
```

**Query parameters:**
```python
resource_type: "inquiries" | "seo_routes" | "audit_logs" | "team"
filters: dict  # {status: "new", date_from: "2026-01-01"}
format: "csv" | "json" | "xlsx"
columns: list[str]
```

**Response:**
```
Content-Type: text/csv
Content-Disposition: attachment; filename="inquiries_jan14_2026.csv"

Name,Email,Phone,Company,Source,Status,Date,Assigned To
John Doe,john@example.com,+1-555-123,ACME,Contact Form,New,2026-01-14,Unassigned
```

---

### 8. Company Info CRUD (14 endpoints)

#### Practice Areas (4)
```
GET    /api/v1/admin/practice-areas
POST   /api/v1/admin/practice-areas
PATCH  /api/v1/admin/practice-areas/{id}
DELETE /api/v1/admin/practice-areas/{id}
```

#### Advantages (4)
```
GET    /api/v1/admin/advantages
POST   /api/v1/admin/advantages
PATCH  /api/v1/admin/advantages/{id}
DELETE /api/v1/admin/advantages/{id}
```

#### Addresses (4)
```
GET    /api/v1/admin/addresses
GET    /api/v1/admin/addresses/{id}
PATCH  /api/v1/admin/addresses/{id}
DELETE /api/v1/admin/addresses/{id}
```

#### Contacts (2)
```
GET    /api/v1/admin/contacts
PATCH  /api/v1/admin/contacts/{id}
```

**Models:**
```python
class PracticeArea(Base, UUIDMixin, TenantMixin):
    name: str
    slug: str
    description: str | None
    icon_id: UUID | None
    color: str | None
    display_order: int

class Advantage(Base, UUIDMixin, TenantMixin):
    title: str
    description: str
    icon_id: UUID | None
    display_order: int

class Address(Base, UUIDMixin, TenantMixin):
    label: str
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: str | None
    email: str | None
    is_default: bool

class CompanyContact(Base, SingletonMixin, TenantMixin):
    phone: str
    email: str
    address_id: UUID
    social_links: dict
```

---

## PRIORITY 2: IMPORTANT FOR v1.1 (19 endpoints)

### 1. Locale Management (4 endpoints)
```
GET    /api/v1/admin/locales
POST   /api/v1/admin/locales
PATCH  /api/v1/admin/locales/{locale_id}
DELETE /api/v1/admin/locales/{locale_id}
```

### 2. Translation Status (1 endpoint)
```
GET /api/v1/admin/localization/status?content_type=articles
```

### 3. Session Management (3 endpoints)
```
GET    /api/v1/auth/sessions
DELETE /api/v1/auth/sessions/{id}
DELETE /api/v1/auth/sessions/logout-all
```

---

## PRIORITY 3: ENHANCEMENTS (v2+)

### 1. Publishing Calendar (1 endpoint + Model change)
```
GET /api/v1/admin/articles/calendar?month=2026-01&status=scheduled
```

Add to Article model:
```python
scheduled_at: datetime | None
```

### 2. Version History (2 endpoints)
```
GET  /api/v1/admin/{resource_type}/{id}/history
POST /api/v1/admin/{resource_type}/{id}/restore
```

### 3. Media Collections (4 endpoints + Model)
```
GET    /api/v1/admin/media/collections
POST   /api/v1/admin/media/collections
PATCH  /api/v1/admin/media/collections/{id}
DELETE /api/v1/admin/media/collections/{id}
```

---

## FastAPI Best Practices

### Dependency Injection (RBAC)
```python
from typing import Annotated
from fastapi import Depends

async def require_permission(permission: str):
    async def _require(user: User = Depends(get_current_user)):
        if not user.has_permission(permission):
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return _require

# Usage:
@router.get("/admin/cases")
async def list_cases(
    user: Annotated[User, Depends(require_permission("content:read"))]
):
    pass
```

### Tenant Isolation (CRITICAL!)
```python
# EVERY query must include tenant filter
query = select(Case).where(Case.tenant_id == user.tenant_id)
```

### Pagination Mixin
```python
class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int

class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    pagination: PaginationMeta
```

### Async Jobs (Bulk > 100 items)
```python
from celery import Celery

celery_app = Celery("admin_panel")

@router.post("/admin/bulk")
async def bulk_operation(request: BulkOperationRequest):
    if len(request.ids) < 100:
        # Sync
        return await _bulk_sync(request)
    else:
        # Async
        job = bulk_task.delay(request.ids)
        return {"job_id": str(job.id), "status": "processing"}
```

### Caching (Dashboard)
```python
from redis import Redis
import json

cache_key = f"dashboard:{tenant_id}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)

result = await _compute_dashboard(db, tenant_id)
redis.setex(cache_key, 300, json.dumps(result))  # 5 min TTL
```

---

## Implementation Roadmap

| Phase | Duration | Endpoints | Status |
|-------|----------|-----------|--------|
| **MVP** | Week 1-2 | 20 | Cases (9), Dashboard (1), Audit (1), Bulk (1), Search (4), Roles (3), Export (1) |
| **v1.1** | Week 3-4 | 19 | Company Info (14), Locales (4), Translation (1) |
| **v2+** | Future | 7 | Calendar (1), History (2), Collections (4) |
| **Total** | | 46 | All endpoints |

---

## Summary Checklist

✅ Cases API — detailed model, filters, publish logic  
✅ Dashboard — metrics, recent activity, queries to cache  
✅ Audit Log — immutable records, change tracking  
✅ Bulk Operations — sync/async handling  
✅ Search — full-text with PostgreSQL GIN  
✅ Role Management — permission matrix  
✅ Export — CSV format, column mapping  
✅ Company Info — Practice Areas, Advantages, Addresses  
✅ Best Practices — Dependency Injection, Tenant Isolation, Pagination, Caching  
✅ Migration Strategy — phased approach over 6 weeks
