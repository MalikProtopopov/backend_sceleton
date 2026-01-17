# Screen-to-API Mapping

> Mapping admin panel screens to backend API endpoints

This document maps each admin UI screen from the UX specification to the corresponding backend API endpoints.

---

## Dashboard

**Screen URL:** `/admin`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| Load overview stats | GET | `/api/v1/admin/dashboard` | - | ✅ Content, inquiries summary |
| Load recent activity | GET | `/api/v1/admin/dashboard` | - | ✅ Last 10 audit entries |

**See:** [`14-cases-dashboard-bulk.md`](./14-cases-dashboard-bulk.md)

---

## Content: Articles

### Articles List

**Screen URL:** `/admin/articles`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| Load list | GET | `/api/v1/admin/articles` | `page`, `pageSize` | |
| Search articles | GET | `/api/v1/admin/articles` | `search` | ✅ Implemented |
| Filter by status | GET | `/api/v1/admin/articles` | `status=draft\|published\|archived` | ✅ |
| Filter by topic | GET | `/api/v1/admin/articles` | `topicId={uuid}` | ✅ |
| Sort | GET | `/api/v1/admin/articles` | `sortBy`, `sortOrder` | Partially implemented |
| Open article | - | Navigate to edit screen | - | |
| Create new | POST | `/api/v1/admin/articles` | - | ✅ |
| Bulk publish | POST | `/api/v1/admin/bulk` | `{action: "publish", resource_type: "articles", ids: [...]}` | ✅ |
| Bulk archive | POST | `/api/v1/admin/bulk` | `{action: "archive", resource_type: "articles", ids: [...]}` | ✅ |
| Bulk delete | POST | `/api/v1/admin/bulk` | `{action: "delete", resource_type: "articles", ids: [...]}` | ✅ |

### Article Edit/Create

**Screen URL:** `/admin/articles/{id}` or `/admin/articles/new`

| User Action | HTTP Method | Endpoint | Body | Notes |
|-------------|-------------|----------|------|-------|
| Load article | GET | `/api/v1/admin/articles/{id}` | - | ✅ |
| Save changes | PATCH | `/api/v1/admin/articles/{id}` | `{...updates, version}` | ✅ Optimistic lock |
| Publish | POST | `/api/v1/admin/articles/{id}/publish` | - | ✅ |
| Unpublish | POST | `/api/v1/admin/articles/{id}/unpublish` | - | ✅ |
| Archive | PATCH | `/api/v1/admin/articles/{id}` | `{status: "archived", version}` | Via PATCH |
| Delete | DELETE | `/api/v1/admin/articles/{id}` | - | Soft delete ✅ |
| Version history | GET | - | - | **GAP**: Not implemented |
| Preview | - | Public URL | - | Client-side link |
| Upload image | POST | `/api/v1/admin/files/upload-url` | `{filename, content_type}` | ✅ |
| Load topics | GET | `/api/v1/admin/topics` | - | ✅ |

---

## Content: Topics

**Screen URL:** `/admin/articles` (sidebar or modal)

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| List topics | GET | `/api/v1/admin/topics` | ✅ |
| Create topic | POST | `/api/v1/admin/topics` | ✅ |
| Update topic | PATCH | `/api/v1/admin/topics/{id}` | ✅ |
| Delete topic | DELETE | `/api/v1/admin/topics/{id}` | ✅ |

---

## Content: FAQ

**Screen URL:** `/admin/faq`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List FAQ | GET | `/api/v1/admin/faq` | `page`, `pageSize`, `category`, `isPublished` | ✅ |
| Create FAQ | POST | `/api/v1/admin/faq` | - | ✅ |
| Update FAQ | PATCH | `/api/v1/admin/faq/{id}` | - | ✅ |
| Delete FAQ | DELETE | `/api/v1/admin/faq/{id}` | - | ✅ |
| Get FAQ | GET | `/api/v1/admin/faq/{id}` | - | ✅ |

---

## Content: Reviews

**Screen URL:** `/admin/reviews`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List reviews | GET | `/api/v1/admin/reviews` | `status`, `caseId`, `featured` | ✅ |
| Create review | POST | `/api/v1/admin/reviews` | - | ✅ |
| Update review | PATCH | `/api/v1/admin/reviews/{id}` | - | ✅ |
| Approve | POST | `/api/v1/admin/reviews/{id}/approve` | - | ✅ |
| Reject | POST | `/api/v1/admin/reviews/{id}/reject` | - | ✅ |
| Delete | DELETE | `/api/v1/admin/reviews/{id}` | - | ✅ |

---

## Content: Cases (Portfolio)

**Screen URL:** `/admin/cases`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List cases | GET | `/api/v1/admin/cases` | `page`, `pageSize`, `status`, `isFeatured`, `serviceId`, `search` | ✅ |
| Create case | POST | `/api/v1/admin/cases` | - | ✅ |
| Get case | GET | `/api/v1/admin/cases/{id}` | - | ✅ |
| Update case | PATCH | `/api/v1/admin/cases/{id}` | - | ✅ Optimistic lock |
| Publish case | POST | `/api/v1/admin/cases/{id}/publish` | - | ✅ |
| Unpublish case | POST | `/api/v1/admin/cases/{id}/unpublish` | - | ✅ |
| Delete case | DELETE | `/api/v1/admin/cases/{id}` | - | ✅ Soft delete |
| Link services | PATCH | `/api/v1/admin/cases/{id}` | `{service_ids: [...]}` | ✅ |
| View case reviews | GET | `/api/v1/admin/reviews` | `caseId={uuid}` | Via reviews filter ✅ |
| Bulk publish | POST | `/api/v1/admin/bulk` | `{action: "publish", resource_type: "cases", ids: [...]}` | ✅ |

**See:** [`14-cases-dashboard-bulk.md`](./14-cases-dashboard-bulk.md) for full documentation.

---

## People & Company: Team Members

**Screen URL:** `/admin/team`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List employees | GET | `/api/v1/admin/employees` | `page`, `pageSize`, `isPublished` | ✅ |
| Create employee | POST | `/api/v1/admin/employees` | - | ✅ |
| Update employee | PATCH | `/api/v1/admin/employees/{id}` | - | ✅ |
| Delete employee | DELETE | `/api/v1/admin/employees/{id}` | - | ✅ |
| Get employee | GET | `/api/v1/admin/employees/{id}` | - | ✅ |

---

## People & Company: Services

**Screen URL:** `/admin/services`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List services | GET | `/api/v1/admin/services` | `page`, `pageSize`, `isPublished` | ✅ |
| Create service | POST | `/api/v1/admin/services` | - | ✅ |
| Update service | PATCH | `/api/v1/admin/services/{id}` | - | ✅ |
| Delete service | DELETE | `/api/v1/admin/services/{id}` | - | ✅ |
| Get service | GET | `/api/v1/admin/services/{id}` | - | ✅ |

---

## People & Company: Practice Areas

**Screen URL:** `/admin/practice-areas`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| List | GET | `/api/v1/admin/practice-areas` | ✅ |
| Create | POST | `/api/v1/admin/practice-areas` | ✅ |
| Get | GET | `/api/v1/admin/practice-areas/{id}` | ✅ |
| Update | PATCH | `/api/v1/admin/practice-areas/{id}` | ✅ Optimistic lock |
| Delete | DELETE | `/api/v1/admin/practice-areas/{id}` | ✅ Soft delete |

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

---

## People & Company: Advantages

**Screen URL:** `/admin/advantages`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| List | GET | `/api/v1/admin/advantages` | ✅ |
| Create | POST | `/api/v1/admin/advantages` | ✅ |
| Get | GET | `/api/v1/admin/advantages/{id}` | ✅ |
| Update | PATCH | `/api/v1/admin/advantages/{id}` | ✅ Optimistic lock |
| Delete | DELETE | `/api/v1/admin/advantages/{id}` | ✅ Soft delete |

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

---

## People & Company: Contacts

**Screen URL:** `/admin/contacts`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| Get addresses | GET | `/api/v1/admin/addresses` | ✅ |
| Get address | GET | `/api/v1/admin/addresses/{id}` | ✅ |
| Create address | POST | `/api/v1/admin/addresses` | ✅ |
| Update address | PATCH | `/api/v1/admin/addresses/{id}` | ✅ |
| Delete address | DELETE | `/api/v1/admin/addresses/{id}` | ✅ Soft delete |
| Get contacts | GET | `/api/v1/admin/contacts` | ✅ |
| Get contact | GET | `/api/v1/admin/contacts/{id}` | ✅ |
| Create contact | POST | `/api/v1/admin/contacts` | ✅ |
| Update contact | PATCH | `/api/v1/admin/contacts/{id}` | ✅ |
| Delete contact | DELETE | `/api/v1/admin/contacts/{id}` | ✅ Soft delete |

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

---

## Leads & Inquiries

### Inquiries List

**Screen URL:** `/admin/leads`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List inquiries | GET | `/api/v1/admin/inquiries` | `page`, `pageSize`, `status`, `formId`, `assignedTo`, `utmSource` | ✅ |
| Kanban view | GET | `/api/v1/admin/inquiries` | Same endpoint, group client-side | ✅ |
| View detail | GET | `/api/v1/admin/inquiries/{id}` | - | ✅ |
| Update status | PATCH | `/api/v1/admin/inquiries/{id}` | - | ✅ |
| Assign to user | PATCH | `/api/v1/admin/inquiries/{id}` | `{assigned_to: uuid}` | ✅ |
| Add note | PATCH | `/api/v1/admin/inquiries/{id}` | `{notes: "..."}` | ✅ |
| Delete | DELETE | `/api/v1/admin/inquiries/{id}` | - | ✅ |
| Search | GET | `/api/v1/admin/inquiries` | `search` | ✅ |
| Export CSV | GET | `/api/v1/admin/export` | `resourceType=inquiries&format=csv` | ✅ |
| Analytics | GET | `/api/v1/admin/inquiries/analytics` | `days` | ✅ |

### Inquiry Forms

**Screen URL:** `/admin/leads/forms`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| List forms | GET | `/api/v1/admin/inquiry-forms` | ✅ |
| Create form | POST | `/api/v1/admin/inquiry-forms` | ✅ |
| Update form | PATCH | `/api/v1/admin/inquiry-forms/{id}` | ✅ |
| Delete form | DELETE | `/api/v1/admin/inquiry-forms/{id}` | ✅ |

---

## Media Library

**Screen URL:** `/admin/media`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List files | GET | `/api/v1/admin/files` | `page`, `pageSize`, `folder`, `imagesOnly` | ✅ |
| Get upload URL | POST | `/api/v1/admin/files/upload-url` | - | Returns presigned S3 URL |
| Register file | POST | `/api/v1/admin/files` | - | After S3 upload |
| Update metadata | PATCH | `/api/v1/admin/files/{id}` | - | Alt text, folder |
| Delete file | DELETE | `/api/v1/admin/files/{id}` | `hardDelete` | Soft by default |
| Collections | - | - | - | **GAP**: Not implemented |
| File versions | - | - | - | **GAP**: Not implemented |

### Upload Flow

```
1. POST /api/v1/admin/files/upload-url
   → Returns { upload_url, file_url, s3_key }

2. PUT {upload_url}
   → Upload file directly to S3

3. POST /api/v1/admin/files
   → Register file in database
```

---

## SEO Center

### SEO Routes

**Screen URL:** `/admin/seo`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List routes | GET | `/api/v1/admin/seo/routes` | `page`, `pageSize`, `locale` | ✅ |
| Create/Update route | PUT | `/api/v1/admin/seo/routes` | - | Upsert by path+locale |
| Update route | PATCH | `/api/v1/admin/seo/routes/{id}` | - | ✅ |
| Delete route | DELETE | `/api/v1/admin/seo/routes/{id}` | - | ✅ |
| Bulk update | - | - | - | **GAP**: Not implemented |
| Export | - | - | - | **GAP**: Not implemented |

### Redirects

**Screen URL:** `/admin/seo/redirects`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List redirects | GET | `/api/v1/admin/seo/redirects` | `page`, `pageSize`, `isActive` | ✅ |
| Create redirect | POST | `/api/v1/admin/seo/redirects` | - | ✅ |
| Update redirect | PATCH | `/api/v1/admin/seo/redirects/{id}` | - | ✅ |
| Delete redirect | DELETE | `/api/v1/admin/seo/redirects/{id}` | - | ✅ |

---

## Users & Security

### Users List

**Screen URL:** `/admin/users`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List users | GET | `/api/v1/auth/users` | `page`, `pageSize`, `is_active` | ✅ |
| Create user | POST | `/api/v1/auth/users` | - | ✅ |
| Update user | PATCH | `/api/v1/auth/users/{id}` | - | ✅ |
| Delete user | DELETE | `/api/v1/auth/users/{id}` | - | ✅ |
| Get user | GET | `/api/v1/auth/users/{id}` | - | ✅ |

### Roles & Permissions

**Screen URL:** `/admin/roles`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| List roles | GET | `/api/v1/auth/roles` | ✅ |
| List permissions | GET | `/api/v1/auth/permissions` | ✅ |
| Create role | POST | `/api/v1/auth/roles` | ✅ Custom roles |
| Update role | PATCH | `/api/v1/auth/roles/{id}` | ✅ Non-system only |
| Delete role | DELETE | `/api/v1/auth/roles/{id}` | ✅ Non-system only |

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

### Audit Log

**Screen URL:** `/admin/audit`

| User Action | HTTP Method | Endpoint | Query Params | Notes |
|-------------|-------------|----------|--------------|-------|
| List logs | GET | `/api/v1/admin/audit-logs` | `page`, `pageSize` | ✅ |
| Filter by user | GET | `/api/v1/admin/audit-logs` | `userId={uuid}` | ✅ |
| Filter by resource | GET | `/api/v1/admin/audit-logs` | `resourceType`, `resourceId` | ✅ |
| Filter by action | GET | `/api/v1/admin/audit-logs` | `action` | ✅ |
| Filter by date | GET | `/api/v1/admin/audit-logs` | `dateFrom`, `dateTo` | ✅ |
| Export logs | GET | `/api/v1/admin/export` | `resourceType=audit_logs&format=csv` | ✅ |

**See:** [`15-audit-export-search.md`](./15-audit-export-search.md)

### Sessions

**Screen URL:** `/admin/users/{id}/sessions`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| List sessions | GET | - | **GAP**: Not implemented |
| Terminate session | DELETE | - | **GAP**: Not implemented |

---

## Localization

**Screen URL:** `/admin/localization`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| List languages | GET | Via `/api/v1/admin/tenants/{id}` | In tenant settings |
| Add language | POST | - | **GAP**: Needs locale router |
| Update language | PATCH | - | **GAP**: Not implemented |
| Disable language | PATCH | - | **GAP**: Not implemented |
| Translation status | GET | - | **GAP**: Not implemented |

---

## Settings

**Screen URL:** `/admin/settings`

| User Action | HTTP Method | Endpoint | Notes |
|-------------|-------------|----------|-------|
| Get settings | GET | `/api/v1/admin/tenants/{id}` | ✅ |
| Update settings | PUT | `/api/v1/admin/tenants/{id}/settings` | ✅ |
| Feature flags | GET | `/api/v1/admin/feature-flags` | ✅ |
| Toggle feature | PATCH | `/api/v1/admin/feature-flags/{name}` | ✅ |

---

## Summary: Endpoint Coverage

| Module | Screens | Endpoints | Coverage |
|--------|---------|-----------|----------|
| Dashboard | 1 | 1 | ✅ 100% |
| Articles | 2 | 10+ | ✅ 100% (+ search, bulk) |
| FAQ | 1 | 5 | ✅ 100% |
| Reviews | 1 | 7 | ✅ 100% |
| Cases | 1 | 11 | ✅ 100% |
| Team | 2 | 5+ | ✅ 100% (+ search, bulk) |
| Services | 1 | 5 | ✅ 100% |
| Practice Areas | 1 | 5 | ✅ 100% |
| Advantages | 1 | 5 | ✅ 100% |
| Contacts | 1 | 10 | ✅ 100% |
| Tenants | 1 | 8 | ✅ 100% |
| Leads | 2 | 11+ | ✅ 100% (+ search, export) |
| Media | 1 | 5 | ⚠️ 80% (needs collections) |
| SEO | 2 | 9 | ✅ 100% |
| Users | 2 | 10 | ✅ 100% (+ role CRUD) |
| Audit | 1 | 1+ | ✅ 100% (+ export) |
| Localization | 1 | 0 | ⚠️ Planned v1.3 |
| Settings | 1 | 4 | ✅ 100% |

**Overall Coverage: ~95%**

**Last Updated:** 2026-01-15

---

## Remaining Gaps (v1.3+)

Priority 2:
1. `GET /api/v1/admin/localization/status` - Translation status
2. Locale management CRUD
3. Media collections
4. Publishing calendar (`scheduled_at` for articles)

Priority 3 (Enhancement):
1. `GET /api/v1/admin/articles/{id}/history` - Version history
2. `GET /api/v1/auth/sessions` - Session management
3. AI translation integration

---

## Documentation References

- [`14-cases-dashboard-bulk.md`](./14-cases-dashboard-bulk.md) - Cases, Dashboard, Bulk operations
- [`15-audit-export-search.md`](./15-audit-export-search.md) - Audit log, Export, Search, Role CRUD, Company info
- [`13-tenants-settings.md`](./13-tenants-settings.md) - Tenants and Settings API
- [`gap-analysis.md`](./gap-analysis.md) - Full gap analysis report

