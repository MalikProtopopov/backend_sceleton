# Frontend Integration Guide

> **Версия**: 2.0
> **Обновлено**: 2026-02-23
> **Изменения**: Smart Login (без обязательного X-Tenant-ID), синхронизация паролей, select-tenant

## Authentication Flow

### 1. Smart Login

Заголовок `X-Tenant-ID` теперь **опциональный** при логине. Бэкенд самостоятельно определяет тенант.

```javascript
const login = async (email, password, tenantId = null) => {
  const headers = { 'Content-Type': 'application/json' };

  // Передаём X-Tenant-ID только если тенант известен (например, из домена)
  if (tenantId) {
    headers['X-Tenant-ID'] = tenantId;
  }

  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers,
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) throw new Error('Login failed');

  const data = await response.json();

  if (data.status === 'success') {
    // Один тенант или X-Tenant-ID передан — логин завершён
    localStorage.setItem('access_token', data.tokens.access_token);
    localStorage.setItem('refresh_token', data.tokens.refresh_token);
    return { type: 'success', user: data.user };
  }

  if (data.status === 'tenant_selection_required') {
    // Несколько тенантов — показать экран выбора
    return {
      type: 'tenant_selection',
      tenants: data.tenants,
      selectionToken: data.selection_token,
    };
  }
};
```

### 2. Select Tenant (after login)

Если логин вернул `tenant_selection_required`, пользователь выбирает организацию:

```javascript
const selectTenant = async (selectionToken, tenantId) => {
  const response = await fetch('/api/v1/auth/select-tenant', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      selection_token: selectionToken,
      tenant_id: tenantId,
    }),
  });

  if (!response.ok) throw new Error('Tenant selection failed');

  const data = await response.json();

  localStorage.setItem('access_token', data.tokens.access_token);
  localStorage.setItem('refresh_token', data.tokens.refresh_token);

  return data.user;
};
```

**Важно:** `selection_token` хранить только в state компонента (НЕ в localStorage). Токен действует 15 минут.

### 3. Axios Configuration

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  // JWT-токен на все авторизованные запросы
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// Interceptor для refresh токена
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const { data } = await axios.post(
          `${api.defaults.baseURL}/auth/refresh`,
          { refresh_token: refreshToken }
        );

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api(error.config);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

### 4. React Hook Example

```jsx
// hooks/useAuth.js
import { useState, useEffect } from 'react';
import api from '../api';

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      loadUser();
    } else {
      setLoading(false);
    }
  }, []);

  const loadUser = async () => {
    try {
      const { data } = await api.get('/auth/me');
      setUser(data);
    } catch (error) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password, tenantId = null) => {
    const headers = {};
    if (tenantId) {
      headers['X-Tenant-ID'] = tenantId;
    }

    const { data } = await api.post('/auth/login', { email, password }, { headers });

    if (data.status === 'success') {
      localStorage.setItem('access_token', data.tokens.access_token);
      localStorage.setItem('refresh_token', data.tokens.refresh_token);
      setUser(data.user);
      return { type: 'success', user: data.user };
    }

    // tenant_selection_required
    return {
      type: 'tenant_selection',
      tenants: data.tenants,
      selectionToken: data.selection_token,
    };
  };

  const selectTenant = async (selectionToken, tenantId) => {
    const { data } = await api.post('/auth/select-tenant', {
      selection_token: selectionToken,
      tenant_id: tenantId,
    });

    localStorage.setItem('access_token', data.tokens.access_token);
    localStorage.setItem('refresh_token', data.tokens.refresh_token);
    setUser(data.user);
    return data.user;
  };

  const switchTenant = async (tenantId) => {
    const { data } = await api.post('/auth/switch-tenant', {
      tenant_id: tenantId,
    });

    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    window.location.reload();
  };

  const logout = () => {
    api.post('/auth/logout').catch(() => {});
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return { user, loading, login, selectTenant, switchTenant, logout };
};
```

### 5. Login Component Example

```jsx
import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export const LoginPage = ({ tenantId = null }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // Tenant selection state
  const [tenants, setTenants] = useState(null);
  const [selectionToken, setSelectionToken] = useState(null);

  const { login, selectTenant } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const result = await login(email, password, tenantId);

      if (result.type === 'success') {
        window.location.href = '/dashboard';
      } else {
        // Show tenant picker
        setTenants(result.tenants);
        setSelectionToken(result.selectionToken);
      }
    } catch (err) {
      setError(err.response?.data?.detail?.detail || 'Login failed');
    }
  };

  const handleSelectTenant = async (tid) => {
    try {
      await selectTenant(selectionToken, tid);
      window.location.href = '/dashboard';
    } catch (err) {
      setError('Failed to select organization');
    }
  };

  // Tenant selection screen
  if (tenants) {
    return (
      <div>
        <h2>Select Organization</h2>
        {tenants.map((t) => (
          <button key={t.tenant_id} onClick={() => handleSelectTenant(t.tenant_id)}>
            {t.name} ({t.role})
          </button>
        ))}
      </div>
    );
  }

  // Login form
  return (
    <form onSubmit={handleLogin}>
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" required />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required />
      {error && <div className="error">{error}</div>}
      <button type="submit">Login</button>
    </form>
  );
};
```

## Important Notes

1. **X-Tenant-ID is OPTIONAL on `/auth/login`**
   - Pass it if you know the tenant (e.g. from domain resolution)
   - Omit it and the backend will auto-detect (or return a tenant picker list)

2. **X-Tenant-ID is NOT needed after login**
   - After receiving tokens, `tenant_id` is embedded in the JWT
   - All subsequent requests use only `Authorization: Bearer {token}`
   - Do NOT add `X-Tenant-ID` to the Axios interceptor for general requests

3. **Tenant ID source:**
   - From domain resolution: `GET /public/tenants/by-domain/{hostname}`
   - From JWT (after login): decoded from token or from `GET /auth/me`
   - Never store `tenant_id` separately in localStorage

4. **Password sync:**
   - Changing password in one tenant automatically updates it in all tenants
   - User always logs in with the same password across all organizations

5. **Token storage:**
   - `access_token` -> `localStorage`
   - `refresh_token` -> `localStorage`
   - `selection_token` -> component state ONLY (never persist)

## Bootstrap Sequence

```
1. App loads
2. Check localStorage for access_token
   -> Yes: GET /auth/me
      -> 200: user is logged in -> go to Dashboard, fetch /me/tenants
      -> 401: try refresh -> if fail -> go to step 3
   -> No: go to step 3
3. Resolve domain: GET /public/tenants/by-domain/{hostname}
   -> 200: save tenant info, show login form with tenant logo
   -> 404: show login form with platform logo (generic domain)
4. User submits login (with or without X-Tenant-ID)
5. Check response.status:
   -> "success": store tokens, GET /me/tenants, go to Dashboard
   -> "tenant_selection_required": show tenant picker
6. User picks tenant -> POST /auth/select-tenant
7. Store tokens, GET /me/tenants, go to Dashboard
8. If force_password_change === true -> redirect to /change-password
```

## Error Handling

| Error Code | HTTP | Frontend Action |
|---|---|---|
| `tenant_selection_required` | 200 | Show tenant picker screen |
| `invalid_credentials` | 401 | Show "Incorrect email or password" |
| `tenant_inactive` | 403 | Full-screen block "Organization suspended" |
| `feature_disabled` | 403 | Show "Section unavailable" with contact info |
| `token_expired` | 401 | Try refresh; on failure -> login page |
| `permission_denied` | 403 | Show "Insufficient permissions" |
| Domain 404 | 404 | Show "Domain not configured" screen |
