# Client Frontend Integration Guide (V2)

This document describes how the **client-facing frontend** should integrate with the backend's multi-tenant, role-based, feature-flagged architecture.

---

## Для публичного сайта (отдельный фронт: лендинг/сайт, не админка)

Если у вас **отдельный сервер с публичным сайтом** (без логина, без админки), нужны только следующие вещи.

### 1. Все запросы к API — только к публичным эндпоинтам

- Базовый путь: `GET /api/v1/public/...`
- **Авторизация не нужна** — не передавайте `Authorization` для публичных запросов.

### 2. Обязательный параметр: `tenant_id`

В multi-tenant режиме у **каждого** публичного запроса должен быть query-параметр:

- `tenant_id` — UUID тенанта (сайта/организации), чьи данные запрашиваете.

Примеры:

```
GET /api/v1/public/articles?tenant_id=<uuid>&locale=ru
GET /api/v1/public/cases?tenant_id=<uuid>&locale=ru
GET /api/v1/public/employees?tenant_id=<uuid>&locale=ru
GET /api/v1/public/services?tenant_id=<uuid>&locale=ru
GET /api/v1/public/faq?tenant_id=<uuid>&locale=ru
GET /api/v1/public/reviews?tenant_id=<uuid>
GET /api/v1/public/sitemap.xml?tenant_id=<uuid>&locale=ru
GET /api/v1/public/robots.txt?tenant_id=<uuid>
GET /api/v1/public/seo/meta?tenant_id=<uuid>&path=/about&locale=ru
POST /api/v1/public/inquiries?tenant_id=<uuid>
```

Откуда брать `tenant_id`: из конфига фронта для этого сайта (один сайт = один тенант) или из домена/окружения при сборке.

### 3. Локаль

Где нужна локаль — передавайте `locale` в query: `locale=ru` или `locale=en`.

### 4. Ошибка 404: фича отключена у тенанта

Если у тенанта выключен модуль (например, блог), бэкенд вернёт **404** с телом в формате RFC 7807:

```json
{
  "type": "https://api.cms.local/errors/feature_not_available",
  "title": "Feature Not Available",
  "status": 404,
  "detail": "The requested resource is not available.",
  "feature": "blog_module",
  "_hint": "This feature is disabled for the tenant. Enable it via the admin panel."
}
```

**Что делать на публичном сайте:**

1. По ответу с `status === 404` смотреть в тело: есть ли поле `feature` и тип ошибки `feature_not_available`.
2. Если **да** (`feature_not_available`) — показать страницу «Раздел временно недоступен» или редирект на главную, **не** показывать контакты админа посетителям.
3. Если **нет** (обычный 404, например `not_found`) — показать стандартную страницу 404.

Так поисковики и пользователи видят обычный 404, а не «forbidden».

### 5. Несуществующий или неактивный тенант

Если передан несуществующий или неактивный `tenant_id`, API может вернуть **400** или **404**. Показывать нейтральную страницу ошибки, не светить внутренние детали.

### 6. Итого для публичного фронта

| Что | Детали |
|-----|--------|
| Эндпоинты | Только `GET/POST /api/v1/public/*` |
| Авторизация | Не нужна |
| Параметры | `tenant_id` — обязательно; `locale` — где нужна локаль |
| 404 с `feature` | Модуль выключен → «Раздел недоступен» или 404-страница |
| 404 без `feature` | Обычный 404 |

Всё остальное в этом документе (логин, токены, сайдбар, каталог фич, 403 для админки, смена пароля и т.д.) относится к **админскому фронту**, публичному сайту не нужно.

### 7. Верификация владения сайтом (опционально)

Если нужна верификация для Яндекс.Вебмастера или Google Search Console:

**Шаг 1**: Настроить проксирование верификационных файлов в `next.config.js` (rewrites):

```typescript
{
  source: '/yandex_:code.html',
  destination: `${API_BASE}/api/v1/public/tenants/${TENANT_ID}/verification/yandex_:code.html`,
},
{
  source: '/google:code.html',
  destination: `${API_BASE}/api/v1/public/tenants/${TENANT_ID}/verification/google:code.html`,
},
```

**Шаг 2**: Для Google мета-тега добавить в layout:

```typescript
const analytics = await fetchPublic<TenantAnalytics>(`/public/tenants/${TENANT_ID}/analytics`);
// analytics.google_verification_meta — значение для <meta name="google-site-verification" content="...">
```

**Шаг 3**: Администратор вводит коды в админке (раздел «Настройки» → «SEO и аналитика»).

Подробнее: [CLIENT_FRONTEND_PUBLIC_API.md](../api/CLIENT_FRONTEND_PUBLIC_API.md) → секция «Верификация владения сайтом».

---

## 1. Authentication Flow (админский фронт)

### Login

```
POST /api/v1/auth/login
X-Tenant-ID: <tenant-uuid>

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "tokens": {
    "access_token": "...",
    "refresh_token": "...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_superuser": false,
    "force_password_change": true,
    "role": { "name": "editor", "permissions": [...] },
    ...
  }
}
```

### Token Storage

- Store `access_token` and `refresh_token` in memory or secure storage (not localStorage for access tokens).
- Include in every request: `Authorization: Bearer <access_token>`.

### Token Refresh

```
POST /api/v1/auth/refresh
{ "refresh_token": "..." }
```

### Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

The token is revoked server-side via Redis blacklist.

### Password Reset

```
POST /api/v1/auth/forgot-password
X-Tenant-ID: <tenant-uuid>
{ "email": "user@example.com" }
```

Always returns 204 (prevents email enumeration). If user exists, a reset email is sent.

```
POST /api/v1/auth/reset-password
{ "token": "<reset-token>", "new_password": "newpass123" }
```

---

## 2. Feature Catalog Integration

### Fetching the Catalog

```
GET /api/v1/auth/me/features?locale=ru
Authorization: Bearer <access_token>
```

**Response:**

```json
{
  "features": [
    {
      "name": "blog_module",
      "title": "Блог / Статьи",
      "description": "Создание и управление статьями и блогом",
      "category": "content",
      "enabled": true,
      "can_request": false
    },
    {
      "name": "cases_module",
      "title": "Кейсы / Портфолио",
      "description": "Публикация кейсов и портфолио работ",
      "category": "content",
      "enabled": false,
      "can_request": true
    }
  ],
  "all_features_enabled": false,
  "tenant_id": "uuid"
}
```

### Building the Sidebar

For each feature in the catalog:

| `enabled` | `can_request` | UI Treatment |
|-----------|---------------|--------------|
| `true`    | `false`       | Show normally, fully clickable |
| `false`   | `true`        | Show grayed out with "Available on request" badge |
| `false`   | `false`       | Hide completely (shouldn't happen currently) |

If `all_features_enabled` is `true`, show all sections (superuser/platform_owner).

### Mapping Features to Sidebar Sections

| Feature Key | Sidebar Section |
|-------------|-----------------|
| `blog_module` | Articles / Blog |
| `cases_module` | Cases / Portfolio |
| `reviews_module` | Reviews / Testimonials |
| `faq_module` | FAQ |
| `team_module` | Team / Employees |
| `services_module` | Services / Practice Areas |
| `seo_advanced` | SEO Settings |
| `multilang` | Localization |
| `analytics_advanced` | Analytics |

---

## 3. Handling Feature-Disabled Errors

### Public API: `feature_not_available` (404)

When a public page requests data from a disabled feature (e.g., `/public/articles` when `blog_module` is off), the API returns **404** (not 403):

```json
{
  "type": "https://api.cms.local/errors/feature_not_available",
  "title": "Feature Not Available",
  "status": 404,
  "detail": "The requested resource is not available.",
  "feature": "blog_module",
  "_hint": "This feature is disabled for the tenant. Enable it via the admin panel."
}
```

**Why 404?** Public visitors and crawlers should see a standard "not found" instead of "forbidden". The `_hint` field is for developers only.

**How to distinguish from a real 404:**

| Scenario | `error_code` | `feature` field |
|----------|-------------|-----------------|
| Feature disabled for tenant | `feature_not_available` | Present (e.g., `"blog_module"`) |
| Resource genuinely not found | `not_found` | Absent |

**Recommended UX for public pages:**

1. Check `error_code` in the response body.
2. If `feature_not_available`: show a friendly "This section is currently unavailable" page or redirect to home.
3. If `not_found`: show standard 404 page.
4. Do NOT show admin contact info to public visitors.

### Admin API: `feature_disabled` (403)

When an authenticated admin navigates to a disabled section, the API returns **403**:

```json
{
  "type": "https://api.cms.local/errors/feature_disabled",
  "title": "Feature Disabled",
  "status": 403,
  "detail": "This feature is not enabled for your organization. Contact your platform administrator to enable it.",
  "feature": "cases_module",
  "contact_admin": true,
  "restriction_level": "organization"
}
```

**Recommended UX:**

1. Intercept 403 responses with `error_code === "feature_disabled"`.
2. Show a modal or inline banner:
   - Title: "Section unavailable"
   - Message: Use `detail` from response
   - If `contact_admin: true`, show a "Contact administrator" button/link
3. Do NOT redirect to login (this is authorization, not authentication).

---

## 4. Understanding `restriction_level` in 403 Errors

All 403 errors now include a `restriction_level` field that tells you **who** is missing the access:

| `restriction_level` | Meaning | User-Facing Message |
|---------------------|---------|---------------------|
| `"organization"` | The organization does not have this feature enabled | "This feature is not available for your organization. Contact your platform administrator." |
| `"user"` | The user's role lacks the required permission | "You do not have sufficient permissions. Contact your organization administrator." |

**How to use in the frontend:**

```javascript
if (error.status === 403) {
  if (error.body.restriction_level === 'organization') {
    showOrgFeatureDisabledMessage(error.body.detail);
  } else if (error.body.restriction_level === 'user') {
    showPermissionDeniedMessage(error.body.detail);
  }
}
```

---

## 5. Handling `tenant_inactive` (403)

When the entire organization is suspended:

```json
{
  "type": "https://api.cms.local/errors/tenant_inactive",
  "title": "Tenant Inactive",
  "status": 403,
  "detail": "Organization is currently suspended. Contact platform administrator."
}
```

**Recommended UX:**

1. Show a full-screen block page:
   - "Your organization is suspended"
   - "Contact platform support for assistance"
2. Clear stored tokens (they won't work anyway).
3. This can happen mid-session (next API call after tenant deactivation returns 403).

---

## 6. Force Password Change Flow

### Detection

After login, check `user.force_password_change`:

```javascript
if (loginResponse.user.force_password_change) {
  router.push('/change-password');
}
```

### Implementation

1. On the change-password page, call:

```
POST /api/v1/auth/me/password
Authorization: Bearer <access_token>
{
  "current_password": "...",
  "new_password": "..."
}
```

2. After success (204), the `force_password_change` flag is cleared server-side.
3. Redirect to dashboard.

### Guard

Block navigation to other pages while `force_password_change` is true:

```javascript
// In router guard
const me = await fetchMe();
if (me.force_password_change && to.path !== '/change-password') {
  return redirect('/change-password');
}
```

---

## 7. Error Code Reference

| Error Code | HTTP | `restriction_level` | Description | Recommended UX |
|------------|------|---------------------|-------------|----------------|
| `authentication_required` | 401 | -- | No token or expired | Redirect to login |
| `invalid_credentials` | 401 | -- | Wrong email/password | Show form error |
| `token_expired` | 401 | -- | Token expired | Auto-refresh or redirect to login |
| `invalid_token` | 401 | -- | Revoked or malformed token | Redirect to login |
| `tenant_inactive` | 403 | -- | Organization suspended | Full-screen block |
| `feature_disabled` | 403 | `organization` | Module not enabled for org | Show "unavailable" with contact CTA |
| `feature_not_available` | 404 | -- | Module disabled (public API) | Show friendly "unavailable" or 404 page |
| `permission_denied` | 403 | `user` | User lacks permission | Show "access denied" |
| `insufficient_role` | 403 | `user` | User role insufficient | Show "access denied" |
| `rate_limit_exceeded` | 429 | -- | Too many requests | Show countdown, retry after `retry_after` seconds |
| `not_found` | 404 | -- | Resource not found | Show 404 page |
| `version_conflict` | 409 | -- | Optimistic locking conflict | Prompt user to reload and retry |

---

## 8. Edge Cases / Scenarios

### User navigates to disabled section via direct URL

- **Public page:** API returns 404 `feature_not_available`. Show "This section is currently unavailable" page.
- **Admin page:** API returns 403 `feature_disabled`. Handle as described in Section 3.

### User's session is active when tenant gets deactivated

The next API call returns 403 `tenant_inactive`. Handle as described in Section 5.

### Feature gets disabled while user is on that page

The next API call to that feature's endpoints returns 403 `feature_disabled` (admin) or 404 `feature_not_available` (public). Show inline notification and disable form submissions.

### User with `force_password_change` tries to navigate away

Use a router guard to redirect back to the password change page. Only allow `/change-password` and `/logout` routes.

### Public site crawled while feature is disabled

Crawlers receive a standard 404 response. This prevents indexing of disabled features and avoids "403 Forbidden" entries in search console.
