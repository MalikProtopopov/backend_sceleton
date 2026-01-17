# Gap Analysis: Backend vs UX Specification

> Comparison of current backend implementation against admin_panel_spec.md requirements

This document identifies missing features, endpoints, and functionality that need to be implemented to fully support the admin panel UX specification.

---

## Executive Summary

| Category | Implemented | Missing | Coverage |
|----------|-------------|---------|----------|
| Core CRUD | 65+ endpoints | 5 endpoints | 93% |
| Cases Module | 11 endpoints | 0 | ✅ 100% |
| Publishing Workflow | Basic + Bulk | Calendar, Scheduling | 80% |
| Bulk Operations | 1 endpoint (unified) | 0 | ✅ 100% |
| Search | All major lists | - | ✅ 100% |
| Export | 1 endpoint (4 resources) | Import | 80% |
| Dashboard | 1 endpoint | - | ✅ 100% |
| Audit Log | 1 endpoint | - | ✅ 100% |
| Localization | Model only | 4 endpoints | 25% |

**Overall Readiness: ~90%**

**Last Updated:** 2026-01-15

---

## Implemented Features (v1.2.0 - January 2026)

The following critical features have been implemented:

### ✅ Cases API (11 endpoints)

**See:** [`14-cases-dashboard-bulk.md`](./14-cases-dashboard-bulk.md)

- Admin: list, create, get, update, delete, publish, unpublish (7 endpoints)
- Public: list published, get by slug (2 endpoints)
- With search, filtering by service, featured status

### ✅ Dashboard API (1 endpoint)

**See:** [`14-cases-dashboard-bulk.md`](./14-cases-dashboard-bulk.md)

- GET /api/v1/admin/dashboard
- Content summary (articles, cases, FAQ, services, employees)
- Inquiry summary (by status)
- Recent activity (last 10 audit log entries)
- Redis caching (5 min TTL)

### ✅ Audit Log API (1 endpoint)

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

- GET /api/v1/admin/audit-logs
- Filterable by user, resource type, action, date range

### ✅ Bulk Operations (1 unified endpoint)

**See:** [`14-cases-dashboard-bulk.md`](./14-cases-dashboard-bulk.md)

- POST /api/v1/admin/bulk
- Actions: publish, unpublish, archive, delete
- Resources: articles, cases, employees
- Returns processed/failed counts

### ✅ Search Functionality (5 endpoints enhanced)

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

- GET /api/v1/admin/articles?search=...
- GET /api/v1/admin/cases?search=...
- GET /api/v1/admin/employees?search=...
- GET /api/v1/admin/inquiries?search=...
- GET /api/v1/auth/users?search=...

### ✅ Export API (1 endpoint, 4 resources)

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

- GET /api/v1/admin/export
- Resources: inquiries, team, seo_routes, audit_logs
- Formats: CSV, JSON

### ✅ Role Management CRUD (3 endpoints)

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

- POST /api/v1/auth/roles - create custom role
- PATCH /api/v1/auth/roles/{id} - update (non-system only)
- DELETE /api/v1/auth/roles/{id} - delete (non-system only)

### ✅ Company Info CRUD (14 endpoints)

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

Practice Areas, Advantages, Addresses, Contacts - full CRUD

---

## Remaining Gaps (Priority 2)

---

### 1. Publishing Calendar

**UX Requirement:** "Publishing Calendar - schedule content, view publishing timeline"

**Current Status:** ❌ Not implemented

**Needed:**
- Add `scheduled_at` field to Article model
- Add `scheduled` to ArticleStatus enum
- Create calendar view endpoint

```
GET /api/v1/admin/articles/calendar
Query: month=2026-01, status=scheduled

Response:
{
  "2026-01-15": [
    { "id": "...", "title": "...", "scheduled_at": "2026-01-15T14:00:00Z" }
  ],
  "2026-01-20": [...]
}
```

**Model Changes:**
```python
class ArticleStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"  # NEW
    PUBLISHED = "published"
    ARCHIVED = "archived"

# Add to Article model:
scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

---

### 2. Version History

**UX Requirement:** "Version History - see change history, restore versions"

**Current Status:** ❌ Not implemented

**Needed:**
```
GET /api/v1/admin/articles/{id}/history
Response:
{
  "versions": [
    {
      "version": 3,
      "author_id": "user-uuid",
      "changes": { "title": { "old": "...", "new": "..." } },
      "created_at": "2026-01-14T15:00:00Z"
    }
  ]
}

POST /api/v1/admin/articles/{id}/restore
{ "version": 2 }
```

**Implementation Options:**
1. Store snapshots in separate table (disk-intensive)
2. Store diffs using audit log (more complex)
3. Use PostgreSQL temporal tables (advanced)

---

### 3. Translation Status Report

**UX Requirement:** "Translation Status Report - show completion % per language"

**Current Status:** ❌ Not implemented

**Needed:**
```
GET /api/v1/admin/localization/status
Query: contentType=article|faq|service

Response:
{
  "overall": {
    "ru": { "total": 42, "complete": 42, "percent": 100 },
    "en": { "total": 42, "complete": 30, "percent": 71 },
    "de": { "total": 42, "complete": 10, "percent": 24 }
  },
  "by_type": {
    "articles": { "ru": 100, "en": 75, "de": 20 },
    "faq": { "ru": 100, "en": 80, "de": 30 }
  }
}
```

---

### 4. Locale Management CRUD

**UX Requirement:** "Languages - add/manage locales"

**Current Status:** ⚠️ Model exists (`LocaleConfig`), no router

**Needed:**
```
GET /api/v1/admin/locales
POST /api/v1/admin/locales
PATCH /api/v1/admin/locales/{id}
DELETE /api/v1/admin/locales/{id}
```

**Constraints:**
- Cannot delete default locale
- Cannot delete locale with published content
- RTL support flag

---

### 5. Media Collections

**UX Requirement:** "Collections (folders/tags) for media organization"

**Current Status:** ⚠️ `folder` field exists, no collection entity

**Needed:**
- Create `MediaCollection` model
- Add collection CRUD endpoints
- Many-to-many with files

---

### 6. Session Management

**UX Requirement:** "Active Sessions - view and terminate user sessions"

**Current Status:** ❌ Not implemented

**Needed:**
```
GET /api/v1/auth/sessions
Response: List of active sessions with device info

DELETE /api/v1/auth/sessions/{session_id}
DELETE /api/v1/auth/sessions/all
```

**Implementation:**
- Store sessions in Redis
- Track device, IP, last activity
- Allow termination

---

## Low Priority Gaps (Priority 3 - v2)

### 7. AI Translation

**UX Requirement:** "Auto-Translate using AI"

**Status:** External integration, not in v1 scope

### 8. Analytics Dashboard

**UX Requirement:** "Traffic, engagement by article"

**Status:** Requires analytics service integration

### 9. Webhooks

**UX Requirement:** "Webhooks for external systems"

**Status:** Not in current scope

### 10. Custom Fields

**UX Requirement:** "Custom fields per entity"

**Status:** Complex feature, v2

### 11. MFA Management

**UX Requirement:** "TOTP setup, backup codes"

**Status:** Security enhancement, v1.5

---

## Schema Changes Required

### Article Model

```python
# Add to ArticleStatus enum
SCHEDULED = "scheduled"

# Add to Article model
scheduled_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

### Review Model (Optional)

```python
# Add IN_REVIEW status if approval workflow needed
class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"  # Optional
    APPROVED = "approved"
    REJECTED = "rejected"
```

---

## Implementation Roadmap

### ✅ Completed (v1.2.0 - January 2026)
1. ✅ Cases API (11 endpoints)
2. ✅ Dashboard endpoint
3. ✅ Audit log endpoint
4. ✅ Search parameter (5 lists)
5. ✅ Bulk operations (unified endpoint)
6. ✅ Role management CRUD (3 endpoints)
7. ✅ Export endpoint (4 resources)
8. ✅ Company info CRUD (14 endpoints)

### Next Sprint (v1.3)
1. Publishing calendar
2. Version history for articles
3. Locale management CRUD
4. Media collections

### Post-MVP (v1.5+)
1. Translation status report
2. Session management
3. MFA management
4. AI translation integration
5. Webhooks
6. Custom fields
7. Advanced analytics

---

## API Endpoint Summary

### Currently Implemented: ~95+ endpoints
### Missing for MVP: 0 (MVP complete)
### Missing for Full Spec: ~15 endpoints

| Category | Count | Status |
|----------|-------|--------|
| Auth | 13 | ✅ Complete (+ 3 role CRUD) |
| Articles | 10 | ✅ Complete (+ search, bulk) |
| Topics | 4 | ✅ Complete |
| FAQ | 5 | ✅ Complete |
| Reviews | 7 | ✅ Complete |
| **Cases** | 11 | ✅ **NEW** - Full CRUD + public |
| Services | 5 | ✅ Complete |
| Employees | 5 | ✅ Complete (+ search) |
| Practice Areas | 4 | ✅ **NEW** - Full CRUD |
| Advantages | 4 | ✅ **NEW** - Full CRUD |
| Addresses | 4 | ✅ **NEW** - Full CRUD |
| Contacts | 4 | ✅ **NEW** - Full CRUD |
| Tenants | 5 | ✅ Complete |
| Tenant Settings | 1 | ✅ Complete |
| Feature Flags | 2 | ✅ Complete |
| Inquiries | 6 | ✅ Complete (+ search, export) |
| Inquiry Forms | 5 | ✅ Complete |
| Files | 5 | ⚠️ 80% (needs collections) |
| SEO Routes | 4 | ✅ Complete |
| Redirects | 5 | ✅ Complete |
| **Dashboard** | 1 | ✅ **NEW** |
| **Audit** | 1 | ✅ **NEW** |
| **Export** | 1 | ✅ **NEW** (4 resources) |
| **Bulk** | 1 | ✅ **NEW** (3 resources) |
| Locales | 0 | ⚠️ Planned v1.3 |
| Sessions | 0 | ⚠️ Planned v1.5 |

---

## Recommendations

### For PM/Tech Lead

1. **MVP is complete** - All critical features are implemented
2. **Focus on testing** - Integration tests for new endpoints before release
3. **Consider v1.3 scope** - Calendar and locale management are next priorities
4. **Documentation is current** - See `14-cases-dashboard-bulk.md` and `15-audit-export-search.md`

### For Backend Dev

1. ✅ All P1 items implemented
2. Next: Implement `scheduled_at` field for publishing calendar
3. Next: Create locale management router
4. Consider: Version history for content (trade-off: storage vs. complexity)

### For Frontend Dev

1. **All major endpoints ready** - Start full admin panel implementation
2. **Use new documentation** - Detailed schemas and examples in new docs
3. **Implement debounced search** - All list endpoints now support it
4. **Dashboard caching** - Backend uses 5min Redis cache, match on frontend
5. **Bulk operations** - Unified endpoint for articles, cases, employees

