# Authentication & Authorization

> JWT-based authentication, token management, and Role-Based Access Control (RBAC)

---

## Overview

The API uses JWT (JSON Web Tokens) for authentication with a multi-tenant architecture:

- **Access Token**: Short-lived (15 minutes), used for API requests
- **Refresh Token**: Long-lived (7 days), used to obtain new access tokens
- **Tenant Context**: Embedded in JWT, determines data isolation

---

## Authentication Flow

```
┌─────────────┐     1. POST /auth/login      ┌─────────────┐
│   Frontend  │ ─────────────────────────────▶│   Backend   │
│             │   X-Tenant-ID: {uuid}         │             │
│             │   {email, password}           │             │
│             │                               │             │
│             │◀───────────────────────────── │             │
│             │   {tokens, user}              │             │
└─────────────┘                               └─────────────┘
       │
       │ 2. Store tokens
       ▼
┌─────────────┐
│  localStorage│
│  or Cookie   │
└─────────────┘
       │
       │ 3. All requests: Authorization: Bearer {token}
       ▼
┌─────────────┐     4. GET /auth/me          ┌─────────────┐
│   Frontend  │ ─────────────────────────────▶│   Backend   │
│             │   Authorization: Bearer ...   │             │
│             │◀───────────────────────────── │             │
│             │   {user, permissions}         │             │
└─────────────┘                               └─────────────┘
```

---

## Endpoints

### POST /api/v1/auth/login

Authenticate user and receive JWT tokens.

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| `X-Tenant-ID` | Yes | Tenant UUID |
| `Content-Type` | Yes | `application/json` |

**Request Body:**
```json
{
  "email": "admin@example.com",
  "password": "securepassword123"
}
```

**Success Response (200):**
```json
{
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "admin@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "is_superuser": false,
    "avatar_url": null,
    "last_login_at": "2026-01-14T10:30:00Z",
    "role": {
      "id": "role-uuid",
      "name": "admin",
      "description": "Full access to all features",
      "is_system": true,
      "permissions": [...]
    },
    "created_at": "2025-06-01T00:00:00Z",
    "updated_at": "2026-01-14T10:30:00Z"
  }
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | Missing X-Tenant-ID header |
| 401 | Invalid credentials |
| 404 | Tenant not found or inactive |

```json
// 401 Invalid credentials
{
  "type": "https://api.cms.local/errors/authentication_error",
  "title": "Authentication Error",
  "status": 401,
  "detail": "Invalid email or password"
}
```

**Example:**
```bash
curl -X POST https://api.yoursite.com/api/v1/auth/login \
  -H "X-Tenant-ID: 123e4567-e89b-12d3-a456-426614174000" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "securepassword123"
  }'
```

---

### POST /api/v1/auth/refresh

Get new access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 401 | Invalid or expired refresh token |

**Frontend Implementation:**
```javascript
// Axios interceptor for automatic token refresh
api.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        const { data } = await api.post('/auth/refresh', {
          refresh_token: getRefreshToken()
        })
        
        setTokens(data)
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed - redirect to login
        logout()
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)
```

---

### POST /api/v1/auth/logout

Invalidate current session.

**Headers:**
| Header | Required |
|--------|----------|
| `Authorization` | Yes |

**Response:** `204 No Content`

**Note:** With JWT, logout is primarily client-side. The client should:
1. Clear stored tokens
2. Clear user state
3. Redirect to login page

---

### GET /api/v1/auth/me

Get current authenticated user with permissions.

**Headers:**
| Header | Required |
|--------|----------|
| `Authorization` | Yes |

**Success Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "admin@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "avatar_url": null,
  "is_superuser": false,
  "role": {
    "id": "role-uuid",
    "name": "content_manager",
    "description": "Manage articles, FAQ, services",
    "is_system": false,
    "permissions": [
      {
        "id": "perm-uuid-1",
        "code": "articles:create",
        "name": "Create Articles",
        "resource": "articles",
        "action": "create"
      },
      {
        "id": "perm-uuid-2",
        "code": "articles:read",
        "name": "Read Articles",
        "resource": "articles",
        "action": "read"
      }
    ]
  },
  "permissions": [
    "articles:create",
    "articles:read",
    "articles:update",
    "articles:delete",
    "articles:publish",
    "faq:create",
    "faq:read",
    "faq:update",
    "faq:delete"
  ]
}
```

**Frontend Usage:**
```javascript
// Store user and permissions after login
const { data: me } = await api.get('/auth/me')

// Check permissions
const hasPermission = (permission) => {
  return me.is_superuser || me.permissions.includes(permission)
}

// Usage in components
if (hasPermission('articles:publish')) {
  showPublishButton()
}
```

---

### POST /api/v1/auth/me/password

Change current user's password.

**Headers:**
| Header | Required |
|--------|----------|
| `Authorization` | Yes |

**Request Body:**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newsecurepassword456"
}
```

**Validation:**
- `current_password`: Required, must match current password
- `new_password`: Required, 8-100 characters

**Response:** `204 No Content`

**Error Response (401):**
```json
{
  "type": "https://api.cms.local/errors/authentication_error",
  "title": "Authentication Error",
  "status": 401,
  "detail": "Current password is incorrect"
}
```

---

## User Management

### GET /api/v1/auth/users

List users in tenant.

**Required Permission:** `users:read`

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number (default: 1) |
| `pageSize` | integer | Items per page (default: 20) |
| `is_active` | boolean | Filter by active status |

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "user-uuid-1",
      "tenant_id": "tenant-uuid",
      "email": "admin@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "is_superuser": false,
      "avatar_url": null,
      "last_login_at": "2026-01-14T10:30:00Z",
      "role": {
        "id": "role-uuid",
        "name": "admin",
        "is_system": true,
        "permissions": [...]
      },
      "created_at": "2025-06-01T00:00:00Z",
      "updated_at": "2026-01-14T10:30:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/auth/users

Create a new user.

**Required Permission:** `users:create`

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "securepassword123",
  "first_name": "Jane",
  "last_name": "Smith",
  "role_id": "role-uuid",
  "is_active": true
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `email` | string | Yes | Valid email, unique per tenant |
| `password` | string | Yes | 8-100 characters |
| `first_name` | string | Yes | 1-100 characters |
| `last_name` | string | Yes | 1-100 characters |
| `role_id` | UUID | No | Must exist in tenant |
| `is_active` | boolean | No | Default: true |

**Success Response (201):**
```json
{
  "id": "new-user-uuid",
  "tenant_id": "tenant-uuid",
  "email": "newuser@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "is_active": true,
  "is_superuser": false,
  "role": {...},
  "created_at": "2026-01-14T14:00:00Z",
  "updated_at": "2026-01-14T14:00:00Z"
}
```

**Error Response (422):**
```json
{
  "type": "https://api.cms.local/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Email already exists in this tenant"
}
```

---

### GET /api/v1/auth/users/{user_id}

Get user by ID.

**Required Permission:** `users:read`

---

### PATCH /api/v1/auth/users/{user_id}

Update user.

**Required Permission:** `users:update`

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "avatar_url": "https://example.com/avatar.jpg",
  "is_active": true,
  "role_id": "new-role-uuid",
  "version": 1
}
```

**Note:** `version` field required for optimistic locking.

---

### DELETE /api/v1/auth/users/{user_id}

Soft delete user.

**Required Permission:** `users:delete`

**Response:** `204 No Content`

---

## Roles & Permissions

### GET /api/v1/auth/roles

List all roles in tenant.

**Required Permission:** `users:read`

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "role-uuid-1",
      "name": "admin",
      "description": "Full access to all features",
      "is_system": true,
      "permissions": [
        {
          "id": "perm-uuid",
          "code": "articles:create",
          "name": "Create Articles",
          "resource": "articles",
          "action": "create"
        }
      ],
      "created_at": "2025-06-01T00:00:00Z",
      "updated_at": "2025-06-01T00:00:00Z"
    },
    {
      "id": "role-uuid-2",
      "name": "content_manager",
      "description": "Manage articles, FAQ, services",
      "is_system": true,
      "permissions": [...]
    },
    {
      "id": "role-uuid-3",
      "name": "marketer",
      "description": "Manage cases, reviews, SEO, view leads",
      "is_system": true,
      "permissions": [...]
    }
  ],
  "total": 3
}
```

---

### GET /api/v1/auth/permissions

List all available permissions.

**Required Permission:** `users:read`

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "perm-uuid-1",
      "code": "articles:create",
      "name": "Create Articles",
      "description": null,
      "resource": "articles",
      "action": "create"
    },
    {
      "id": "perm-uuid-2",
      "code": "articles:read",
      "name": "Read Articles",
      "resource": "articles",
      "action": "read"
    }
  ],
  "total": 28
}
```

---

## JWT Token Structure

### Access Token Payload

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "admin@example.com",
  "role": "admin",
  "permissions": [
    "articles:create",
    "articles:read",
    "articles:update",
    "articles:delete",
    "articles:publish"
  ],
  "is_superuser": false,
  "type": "access",
  "exp": 1705244456,
  "iat": 1705243556
}
```

| Field | Description |
|-------|-------------|
| `sub` | User ID (UUID) |
| `tenant_id` | Tenant ID (UUID) |
| `email` | User email |
| `role` | Role name |
| `permissions` | Array of permission codes |
| `is_superuser` | Bypass all permission checks |
| `type` | Token type (`access` or `refresh`) |
| `exp` | Expiration timestamp |
| `iat` | Issued at timestamp |

### Token Expiration

| Token Type | Expiration |
|------------|------------|
| Access Token | 15 minutes |
| Refresh Token | 7 days |

---

## RBAC (Role-Based Access Control)

### Default Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **admin** | Full access | `*` (all permissions) |
| **content_manager** | Content management | `articles:*`, `faq:*`, `services:read`, `services:update`, `employees:read` |
| **marketer** | Marketing & SEO | `cases:*`, `reviews:*`, `seo:*`, `inquiries:read` |

### Permission Format

Permissions follow `resource:action` pattern:

```
articles:create
articles:read
articles:update
articles:delete
articles:publish
```

### Available Permissions

| Resource | Actions |
|----------|---------|
| `articles` | create, read, update, delete, publish |
| `services` | create, read, update, delete |
| `employees` | create, read, update, delete |
| `cases` | create, read, update, delete |
| `reviews` | create, read, update, delete |
| `faq` | create, read, update, delete |
| `inquiries` | read, update, delete |
| `seo` | read, update |
| `settings` | read, update |
| `users` | create, read, update, delete |

### Permission Checking

Backend checks permissions via `PermissionChecker` dependency:

```python
@router.post("/admin/articles")
async def create_article(
    user: AdminUser = Depends(PermissionChecker("articles:create")),
):
    ...
```

### Superuser Bypass

Users with `is_superuser: true` bypass all permission checks.

---

## Frontend Integration

### Token Storage

```javascript
// Recommended: Store in memory + httpOnly cookie for refresh token
// Alternative: localStorage (less secure, but simpler)

const setTokens = ({ access_token, refresh_token }) => {
  localStorage.setItem('access_token', access_token)
  localStorage.setItem('refresh_token', refresh_token)
}

const getAccessToken = () => localStorage.getItem('access_token')
const getRefreshToken = () => localStorage.getItem('refresh_token')

const clearTokens = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}
```

### Axios Configuration

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth header to all requests
api.interceptors.request.use(config => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

### Permission-Based UI

```javascript
// React hook example
const usePermissions = () => {
  const { user } = useAuth()
  
  const hasPermission = (permission) => {
    if (!user) return false
    if (user.is_superuser) return true
    return user.permissions.includes(permission)
  }
  
  const hasAnyPermission = (permissions) => {
    return permissions.some(p => hasPermission(p))
  }
  
  return { hasPermission, hasAnyPermission }
}

// Usage in component
const ArticleActions = ({ article }) => {
  const { hasPermission } = usePermissions()
  
  return (
    <div>
      {hasPermission('articles:update') && (
        <Button onClick={() => edit(article)}>Edit</Button>
      )}
      {hasPermission('articles:publish') && article.status === 'draft' && (
        <Button onClick={() => publish(article)}>Publish</Button>
      )}
      {hasPermission('articles:delete') && (
        <Button danger onClick={() => remove(article)}>Delete</Button>
      )}
    </div>
  )
}
```

### Handling 401/403 Errors

```javascript
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      clearTokens()
      window.location.href = '/login'
    }
    
    if (error.response?.status === 403) {
      // Insufficient permissions
      showNotification({
        type: 'error',
        message: 'You do not have permission to perform this action'
      })
    }
    
    return Promise.reject(error)
  }
)
```

