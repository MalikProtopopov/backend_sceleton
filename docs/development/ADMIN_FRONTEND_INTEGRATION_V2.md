# Admin Frontend Integration Guide (V2)

This document describes how the **admin panel frontend** should integrate with the backend for organization management, user management, and platform_owner workflows.

---

## 1. Platform Owner Dashboard

Platform owners (role `platform_owner` or `is_superuser=true`) have access to organization-level management.

### List Organizations

```
GET /api/v1/tenants?page=1&page_size=20&search=acme&sort_by=name&sort_order=asc&is_active=true
Authorization: Bearer <access_token>
```

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |
| `search` | string | Search by organization name (ilike) |
| `is_active` | bool | Filter by active/inactive status |
| `sort_by` | string | Sort field: `name` or `created_at` (default: `created_at`) |
| `sort_order` | string | `asc` or `desc` (default: `desc`) |

**Response includes `users_count`:**

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Acme Corp",
      "slug": "acme",
      "is_active": true,
      "users_count": 5,
      "version": 3,
      "created_at": "...",
      ...
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

## 2. Organization Management

### Create Organization

```
POST /api/v1/tenants
{
  "name": "Acme Corp",
  "slug": "acme",
  "domain": "acme.example.com",
  "is_active": true,
  "contact_email": "admin@acme.com",
  "contact_phone": "+1234567890",
  "primary_color": "#FF5722"
}
```

New tenants are created with **all feature flags enabled** by default (including `services_module`).

### Update Organization

```
PATCH /api/v1/tenants/{tenant_id}
{
  "name": "Acme Corp Updated",
  "is_active": false,
  "version": 3
}
```

**`version` is required** for optimistic locking. If another user modified the tenant, you'll get a 409 `version_conflict` error.

### Deactivate Organization

Set `is_active: false` in the PATCH request. **Consequences:**

- All users in the organization are immediately locked out (next API call returns 403 `tenant_inactive`)
- Active sessions become invalid (not revoked, but blocked on next request)
- Public API stops serving content for this tenant
- Platform owners and superusers are not affected

### Delete Organization (soft delete)

```
DELETE /api/v1/tenants/{tenant_id}
```

Soft-deletes the tenant. Data is preserved but marked as deleted.

---

## 3. User Management within Organization

### Cross-Tenant Mode

Platform owners can manage users in **any** organization by passing the `tenant_id` query parameter.

### List Users

```
GET /api/v1/auth/users?tenant_id=<uuid>&page=1&search=john&is_active=true
Authorization: Bearer <access_token>
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `tenant_id` | UUID (optional) | Target tenant (platform owner only). Omit for own tenant. |
| `page` | int | Page number |
| `page_size` | int | Items per page |
| `search` | string | Search in email and name |
| `is_active` | bool | Filter by active/inactive |

### Create User

```
POST /api/v1/auth/users?tenant_id=<uuid>
{
  "email": "new@acme.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123",
  "role_id": "uuid-of-role",
  "is_active": true,
  "send_credentials": true
}
```

**Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `email` | yes | User email (unique within tenant) |
| `first_name` | yes | First name |
| `last_name` | yes | Last name |
| `password` | yes | Initial password (min 8 chars) |
| `role_id` | no | Role to assign (null = no role) |
| `is_active` | no | Active status (default: true) |
| `send_credentials` | no | Send welcome email (default: true) |

**What happens:**

1. User is created with `force_password_change=true`
2. If `send_credentials=true`, a welcome email is sent (does NOT contain password)
3. Admin must communicate the password to the user via another channel
4. On first login, the frontend should detect `force_password_change` and redirect to password change page

### Update User

```
PATCH /api/v1/auth/users/{user_id}?tenant_id=<uuid>
{
  "first_name": "Jane",
  "is_active": false,
  "role_id": "uuid-of-new-role",
  "version": 2
}
```

### Toggle User Active Status

Use the PATCH endpoint with `is_active: false` to deactivate a user. The user will be blocked on their next API request (not immediately kicked from active session).

### Delete User (soft delete)

```
DELETE /api/v1/auth/users/{user_id}?tenant_id=<uuid>
```

---

## 4. Cross-Tenant Context

### How `tenant_id` Query Param Works

- All user management endpoints accept an optional `tenant_id` query parameter
- **Platform owners and superusers**: Can use any `tenant_id` to manage users across organizations
- **Regular users (site_owner, content_manager, etc.)**: Cannot use `tenant_id` param; they're restricted to their own tenant. If they try, they get 403 `permission_denied`.
- **If `tenant_id` is omitted**: Defaults to the user's own tenant (from their JWT token)

### UI Pattern for Platform Owner

1. Platform owner navigates to organization list
2. Clicks on an organization to view details
3. On the organization detail page, there's a "Users" tab
4. The "Users" tab makes API calls with `tenant_id=<selected-org-id>`
5. Create/edit/delete actions also pass `tenant_id`

---

## 5. Role and Permission Management

### List Roles

```
GET /api/v1/auth/roles
```

Returns roles for the current tenant.

### Create Custom Role

```
POST /api/v1/auth/roles
{
  "name": "custom_role",
  "description": "Custom role for specific needs",
  "permission_ids": ["uuid1", "uuid2"]
}
```

### List Available Permissions

```
GET /api/v1/auth/permissions
```

Returns all 28+ permissions available in the system.

### System Roles

System roles (`platform_owner`, `site_owner`, `content_manager`, `marketer`, `editor`) **cannot be modified or deleted**. Attempting to do so returns 403 `system_role_protected`.

---

## 6. Feature Flag Management

### List Feature Flags for Organization

```
GET /api/v1/feature-flags?tenant_id=<uuid>
```

### Toggle Feature

```
PATCH /api/v1/feature-flags/{feature_name}?tenant_id=<uuid>
{ "enabled": true }
```

**Impact of disabling a feature:**

- All admin routes for that module start returning 403 `feature_disabled`
- All public routes for that module start returning 404 `feature_not_available`
- Users currently on that section get an error on their next API call
- The feature catalog (`/me/features`) reflects the change immediately

### Available Features

| Feature Name | Russian Name | Description |
|-------------|-------------|-------------|
| `blog_module` | Блог / Статьи | Blog and article management |
| `cases_module` | Кейсы / Портфолио | Case studies and portfolio |
| `reviews_module` | Отзывы | Reviews and testimonials |
| `faq_module` | Вопросы и ответы | FAQ management |
| `team_module` | Команда / Сотрудники | Team member profiles |
| `services_module` | Услуги | Services and practice areas |
| `seo_advanced` | Расширенное SEO | Advanced SEO (redirects, custom meta) |
| `multilang` | Мультиязычность | Multi-language content support |
| `analytics_advanced` | Расширенная аналитика | Detailed lead analytics |

---

## 7. Understanding 403 Errors: Organization vs User Level

All 403 errors now include a `restriction_level` field that tells the frontend **who** is missing the access. This allows showing the correct message and contact target.

### Error Differentiation

| Error Code | `restriction_level` | Meaning | User-Facing Message |
|------------|---------------------|---------|---------------------|
| `feature_disabled` | `organization` | The organization does not have this feature enabled | "This feature is not available for your organization. Contact your **platform administrator** to enable it." |
| `permission_denied` | `user` | The user's role lacks the required permission | "You do not have sufficient permissions. Contact your **organization administrator** to update your role." |
| `insufficient_role` | `user` | The user's role is not sufficient | "You do not have the required role. Contact your **organization administrator**." |
| `tenant_inactive` | -- | The entire organization is suspended | "Your organization is suspended. Contact **platform support**." |

### How to Handle in the Frontend

```javascript
// In your HTTP error interceptor
function handle403(error) {
  const body = error.response.data;
  
  switch (body.error_code || body.type?.split('/').pop()) {
    case 'feature_disabled':
      // Organization-level: feature not enabled
      showModal({
        title: 'Раздел недоступен',
        message: body.detail,
        action: 'Обратитесь к администратору платформы',
        level: 'organization',
      });
      break;

    case 'permission_denied':
    case 'insufficient_role':
      // User-level: insufficient permissions
      showModal({
        title: 'Нет доступа',
        message: body.detail,
        action: 'Обратитесь к администратору организации',
        level: 'user',
      });
      break;

    case 'tenant_inactive':
      // Organization suspended
      showFullScreenBlock({
        title: 'Организация приостановлена',
        message: body.detail,
      });
      break;
  }
}
```

### Key Differences

| Aspect | Organization-level (`feature_disabled`) | User-level (`permission_denied`) |
|--------|----------------------------------------|----------------------------------|
| **Who fixes it** | Platform administrator enables the feature for the org | Organization administrator updates the user's role |
| **Scope** | Affects ALL users in the org | Affects only this specific user |
| **Response field** | `restriction_level: "organization"` | `restriction_level: "user"` |
| **Feature name** | Present in `feature` field | Absent |
| **Permission** | Absent | Present in `required_permission` field |

---

## 8. Welcome Email Behavior

When `send_credentials=true` on user creation:

1. An email is sent to the user with:
   - Invitation notice
   - Login URL
   - Their email address
   - Note: "Your password has been set by your administrator. Please change it after your first login."
2. The email does **NOT** contain the password
3. The admin should communicate the password via another channel
4. The user has `force_password_change=true` set on their account
5. On first login, the frontend detects this flag and redirects to password change

---

## 9. Audit Log Viewer

### List Audit Logs

```
GET /api/v1/admin/audit-logs?page=1&page_size=50
```

### What is Logged

| Resource Type | Actions | Details |
|--------------|---------|---------|
| `auth` | `login`, `logout` | User ID, IP address |
| `user` | `create`, `update`, `delete` | Changed fields with old/new values |
| `tenant` | `create`, `update`, `delete` | Changed fields (especially `is_active`) |
| `feature_flag` | `update` | Feature name, old/new enabled status |
| `role` | `create`, `update`, `delete` | Role name, permissions updated |

### Audit Log Entry Format

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "resource_type": "user",
  "resource_id": "uuid",
  "action": "update",
  "changes": {
    "is_active": { "old": "True", "new": "False" }
  },
  "ip_address": "192.168.1.1",
  "created_at": "2026-02-11T12:00:00Z"
}
```

---

## 10. Error Code Reference

| Error Code | HTTP | `restriction_level` | Description | Recommended UX |
|------------|------|---------------------|-------------|----------------|
| `authentication_required` | 401 | -- | No token or expired | Redirect to login |
| `invalid_credentials` | 401 | -- | Wrong email/password | Show form error |
| `token_expired` | 401 | -- | Token expired | Auto-refresh or redirect to login |
| `invalid_token` | 401 | -- | Revoked or malformed token | Redirect to login |
| `tenant_inactive` | 403 | -- | Organization suspended | Full-screen block |
| `feature_disabled` | 403 | `organization` | Module not enabled for org | "Section unavailable" + contact platform admin |
| `permission_denied` | 403 | `user` | User lacks permission | "No access" + contact org admin |
| `insufficient_role` | 403 | `user` | User role insufficient | "No access" + contact org admin |
| `system_role_protected` | 403 | -- | Cannot modify system roles | Show error toast |
| `rate_limit_exceeded` | 429 | -- | Too many requests | Show countdown |
| `not_found` | 404 | -- | Resource not found | Show 404 page |
| `already_exists` | 409 | -- | Duplicate resource | Show form error |
| `version_conflict` | 409 | -- | Optimistic locking conflict | Prompt reload and retry |

---

## 11. Edge Cases / Scenarios

### Platform owner deactivates org that has active sessions

- Users get 403 `tenant_inactive` on their next API request
- No push notification -- frontend discovers this on next API call
- Frontend should handle by showing a full-screen "Organization suspended" page

### Platform owner disables feature that org is actively using

- Admin users on that section get 403 `feature_disabled` on their next API call (with `restriction_level: "organization"`)
- Public visitors see 404 `feature_not_available`
- Frontend should show "This section is no longer available" message

### User sees 403 -- how to tell if it's org-level or user-level

1. Check `restriction_level` field in the response body:
   - `"organization"` -- the org doesn't have the feature. Show "Contact platform administrator".
   - `"user"` -- the user lacks permissions. Show "Contact organization administrator".
2. If `restriction_level` is absent, check `error_code` for `tenant_inactive` or `system_role_protected`.

### Creating user with duplicate email in same tenant

- Returns 409 `already_exists` with `{ "resource": "User", "field": "email" }`

### Attempting to delete system role

- Returns 403 `system_role_protected`

### Editing user's role while they have active session

- The user's permissions in their JWT token become stale
- Permissions are re-evaluated on token refresh
- For immediate effect, user needs to logout and login again (or wait for token refresh)
