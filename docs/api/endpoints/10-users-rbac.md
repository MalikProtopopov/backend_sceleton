# Users & RBAC API

> User management, roles, and Role-Based Access Control

---

## Overview

User management for the admin panel includes:
- User CRUD operations
- Role assignment
- Permission management
- Password management

For authentication endpoints (login, refresh, etc.), see [01-authentication.md](./01-authentication.md).

---

## User Management

### GET /api/v1/auth/users

List all users in tenant.

**Required Permission:** `users:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `is_active` | boolean | - | Filter by active status |

**Example Request:**
```bash
GET /api/v1/auth/users?page=1&is_active=true
Authorization: Bearer {token}
```

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
      "avatar_url": "https://cdn.example.com/avatars/john.jpg",
      "last_login_at": "2026-01-14T10:30:00Z",
      "role": {
        "id": "role-uuid",
        "name": "admin",
        "description": "Full access to all features",
        "is_system": true,
        "permissions": [...]
      },
      "created_at": "2025-06-01T00:00:00Z",
      "updated_at": "2026-01-14T10:30:00Z",
      "version": 1
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
| `avatar_url` | string | No | Max 500 chars |

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
  "avatar_url": null,
  "role": {...},
  "created_at": "2026-01-14T14:00:00Z",
  "updated_at": "2026-01-14T14:00:00Z",
  "version": 1
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 422 | Email already exists |
| 422 | Role not found |
| 422 | Password too short |

---

### GET /api/v1/auth/users/{user_id}

Get user by ID.

**Required Permission:** `users:read`

**Success Response (200):** Full user object.

---

### PATCH /api/v1/auth/users/{user_id}

Update user.

**Required Permission:** `users:update`

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "avatar_url": "https://cdn.example.com/avatars/jane.jpg",
  "is_active": true,
  "role_id": "new-role-uuid",
  "version": 1
}
```

**Note:** 
- `version` required for optimistic locking
- Cannot change `email` after creation
- Cannot update own `is_active` to false
- Cannot update own `role_id`

**Success Response (200):** Updated user object.

---

### DELETE /api/v1/auth/users/{user_id}

Soft delete user.

**Required Permission:** `users:delete`

**Constraints:**
- Cannot delete yourself
- Cannot delete superuser (unless you are superuser)

**Response:** `204 No Content`

---

## Roles

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
          "description": null,
          "resource": "articles",
          "action": "read"
        }
        // ... more permissions
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

### Default Roles

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| **admin** | Full access | All permissions |
| **content_manager** | Content management | `articles:*`, `faq:*`, `services:read/update`, `employees:read` |
| **marketer** | Marketing & SEO | `cases:*`, `reviews:*`, `seo:*`, `inquiries:read` |

---

## Permissions

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
      "description": null,
      "resource": "articles",
      "action": "read"
    }
    // ... more permissions
  ],
  "total": 28
}
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

---

## Frontend Integration

### Users List Page

```jsx
const UsersPage = () => {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const { hasPermission } = usePermissions()
  
  useEffect(() => {
    Promise.all([
      api.get('/auth/users'),
      api.get('/auth/roles')
    ]).then(([usersRes, rolesRes]) => {
      setUsers(usersRes.data.items)
      setRoles(rolesRes.data.items)
    })
  }, [])
  
  const handleRoleChange = async (userId, roleId, version) => {
    await api.patch(`/auth/users/${userId}`, { role_id: roleId, version })
    // Refresh users
  }
  
  const handleDeactivate = async (userId, version) => {
    await api.patch(`/auth/users/${userId}`, { is_active: false, version })
    // Refresh users
  }
  
  const handleDelete = async (userId) => {
    if (confirm('Delete this user?')) {
      await api.delete(`/auth/users/${userId}`)
      // Refresh users
    }
  }
  
  return (
    <div>
      <Header>
        <h1>Users</h1>
        {hasPermission('users:create') && (
          <Button onClick={() => setShowCreateModal(true)}>Add User</Button>
        )}
      </Header>
      
      <Table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Last Login</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <UserRow 
              key={user.id}
              user={user}
              roles={roles}
              onRoleChange={handleRoleChange}
              onDeactivate={handleDeactivate}
              onDelete={handleDelete}
            />
          ))}
        </tbody>
      </Table>
    </div>
  )
}
```

### User Create/Edit Form

```jsx
const UserForm = ({ user, roles, onSave, onCancel }) => {
  const isEdit = !!user
  
  const [formData, setFormData] = useState({
    email: user?.email || '',
    password: '',
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    role_id: user?.role?.id || '',
    is_active: user?.is_active ?? true
  })
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    
    const payload = { ...formData }
    
    if (isEdit) {
      delete payload.email // Cannot change email
      if (!payload.password) delete payload.password // Only update if provided
      payload.version = user.version
      await api.patch(`/auth/users/${user.id}`, payload)
    } else {
      await api.post('/auth/users', payload)
    }
    
    onSave()
  }
  
  return (
    <Form onSubmit={handleSubmit}>
      <Input 
        name="email" 
        label="Email" 
        type="email"
        required
        disabled={isEdit}
        value={formData.email}
        onChange={(e) => setFormData({...formData, email: e.target.value})}
      />
      
      <Input 
        name="password" 
        label={isEdit ? "New Password (leave blank to keep)" : "Password"}
        type="password"
        required={!isEdit}
        minLength={8}
        value={formData.password}
        onChange={(e) => setFormData({...formData, password: e.target.value})}
      />
      
      <div className="row">
        <Input 
          name="first_name" 
          label="First Name" 
          required
          value={formData.first_name}
          onChange={(e) => setFormData({...formData, first_name: e.target.value})}
        />
        <Input 
          name="last_name" 
          label="Last Name" 
          required
          value={formData.last_name}
          onChange={(e) => setFormData({...formData, last_name: e.target.value})}
        />
      </div>
      
      <Select 
        name="role_id" 
        label="Role"
        value={formData.role_id}
        onChange={(e) => setFormData({...formData, role_id: e.target.value})}
        options={roles.map(r => ({ value: r.id, label: r.name }))}
      />
      
      <Switch 
        name="is_active" 
        label="Active"
        checked={formData.is_active}
        onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
      />
      
      <div className="actions">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">
          {isEdit ? 'Update User' : 'Create User'}
        </Button>
      </div>
    </Form>
  )
}
```

### Permission Matrix View

```jsx
const PermissionMatrix = ({ roles, permissions }) => {
  // Group permissions by resource
  const grouped = permissions.reduce((acc, perm) => {
    if (!acc[perm.resource]) acc[perm.resource] = []
    acc[perm.resource].push(perm)
    return acc
  }, {})
  
  const hasPermission = (role, permCode) => {
    return role.permissions.some(p => p.code === permCode)
  }
  
  return (
    <Table>
      <thead>
        <tr>
          <th>Resource</th>
          <th>Action</th>
          {roles.map(role => (
            <th key={role.id}>{role.name}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Object.entries(grouped).map(([resource, perms]) => (
          <>
            {perms.map((perm, idx) => (
              <tr key={perm.id}>
                {idx === 0 && (
                  <td rowSpan={perms.length}>{resource}</td>
                )}
                <td>{perm.action}</td>
                {roles.map(role => (
                  <td key={role.id}>
                    {hasPermission(role, perm.code) ? '✓' : '-'}
                  </td>
                ))}
              </tr>
            ))}
          </>
        ))}
      </tbody>
    </Table>
  )
}
```

### usePermissions Hook

```javascript
import { createContext, useContext, useMemo } from 'react'

const AuthContext = createContext(null)

export const usePermissions = () => {
  const { user } = useContext(AuthContext)
  
  return useMemo(() => ({
    hasPermission: (permission) => {
      if (!user) return false
      if (user.is_superuser) return true
      return user.permissions.includes(permission)
    },
    
    hasAnyPermission: (permissions) => {
      if (!user) return false
      if (user.is_superuser) return true
      return permissions.some(p => user.permissions.includes(p))
    },
    
    hasAllPermissions: (permissions) => {
      if (!user) return false
      if (user.is_superuser) return true
      return permissions.every(p => user.permissions.includes(p))
    },
    
    canRead: (resource) => hasPermission(`${resource}:read`),
    canCreate: (resource) => hasPermission(`${resource}:create`),
    canUpdate: (resource) => hasPermission(`${resource}:update`),
    canDelete: (resource) => hasPermission(`${resource}:delete`)
  }), [user])
}

// Usage
const ArticleActions = ({ article }) => {
  const { canUpdate, canDelete, hasPermission } = usePermissions()
  
  return (
    <>
      {canUpdate('articles') && <Button>Edit</Button>}
      {hasPermission('articles:publish') && <Button>Publish</Button>}
      {canDelete('articles') && <Button>Delete</Button>}
    </>
  )
}
```

---

## Known Gaps

See [gap-analysis.md](./gap-analysis.md) for details on:

1. **Role CRUD** - Currently read-only, no create/update/delete for roles
2. **Audit Log** - Model exists but no router to view who did what
3. **Session Management** - No endpoint to view/terminate active sessions
4. **MFA** - Not implemented

---

## Security Best Practices

1. **Minimum Privilege** - Assign lowest role that allows job function
2. **Review Regularly** - Audit user access periodically
3. **Deactivate vs Delete** - Prefer deactivation to preserve audit trail
4. **Strong Passwords** - Enforce minimum 8 characters
5. **Token Expiry** - Access tokens expire in 15 minutes

