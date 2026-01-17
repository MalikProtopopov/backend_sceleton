# Frontend Integration Guide

## Authentication Flow

### 1. Login (требует X-Tenant-ID)

**Важно:** Заголовок `X-Tenant-ID` нужен **только для логина**. После получения токена он уже не требуется.

```javascript
// Пример с fetch
const login = async (email, password) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': '2348d266-596f-420f-b046-a63ca3b504f9', // ← ОБЯЗАТЕЛЬНО!
    },
    body: JSON.stringify({
      email,
      password,
    }),
  })
  
  if (!response.ok) {
    throw new Error('Login failed')
  }
  
  const data = await response.json()
  
  // Сохранить токены
  localStorage.setItem('access_token', data.tokens.access_token)
  localStorage.setItem('refresh_token', data.tokens.refresh_token)
  
  return data
}
```

### 2. Axios Configuration

```javascript
import axios from 'axios'

// Создать инстанс
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Tenant ID - хранить в конфиге или env
const TENANT_ID = '2348d266-596f-420f-b046-a63ca3b504f9'

// Interceptor для логина - добавляет X-Tenant-ID
api.interceptors.request.use((config) => {
  // Для логина добавляем X-Tenant-ID
  if (config.url === '/auth/login') {
    config.headers['X-Tenant-ID'] = TENANT_ID
  }
  
  // Для остальных запросов добавляем Authorization
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  
  return config
})

// Interceptor для refresh токена
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true
      
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        const { data } = await axios.post(
          'http://localhost:8000/api/v1/auth/refresh',
          { refresh_token: refreshToken }
        )
        
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        
        error.config.headers.Authorization = `Bearer ${data.access_token}`
        return api(error.config)
      } catch (refreshError) {
        // Refresh failed - logout
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)

export default api
```

### 3. React Hook Example

```jsx
// hooks/useAuth.js
import { useState, useEffect } from 'react'
import api from '../api'

const TENANT_ID = '2348d266-596f-420f-b046-a63ca3b504f9'

export const useAuth = () => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    // Проверить, есть ли токен
    const token = localStorage.getItem('access_token')
    if (token) {
      loadUser()
    } else {
      setLoading(false)
    }
  }, [])
  
  const loadUser = async () => {
    try {
      const { data } = await api.get('/auth/me')
      setUser(data)
    } catch (error) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    } finally {
      setLoading(false)
    }
  }
  
  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', 
      { email, password },
      {
        headers: {
          'X-Tenant-ID': TENANT_ID, // ← Только для логина!
        }
      }
    )
    
    localStorage.setItem('access_token', data.tokens.access_token)
    localStorage.setItem('refresh_token', data.tokens.refresh_token)
    
    setUser(data.user)
    return data
  }
  
  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }
  
  return { user, loading, login, logout }
}
```

### 4. Login Component Example

```jsx
// components/LoginForm.jsx
import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'

const TENANT_ID = '2348d266-596f-420f-b046-a63ca3b504f9'

export const LoginForm = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login } = useAuth()
  
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    try {
      await login(email, password)
      // Redirect to dashboard
      window.location.href = '/dashboard'
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    }
  }
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      {error && <div className="error">{error}</div>}
      <button type="submit">Login</button>
    </form>
  )
}
```

## Environment Variables

Создайте `.env` файл в корне фронтенда:

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_TENANT_ID=2348d266-596f-420f-b046-a63ca3b504f9
```

Использование:

```javascript
// config.js
export const API_URL = import.meta.env.VITE_API_URL
export const TENANT_ID = import.meta.env.VITE_TENANT_ID
```

## Важные моменты

1. **X-Tenant-ID нужен ТОЛЬКО для `/auth/login`**
   - После логина tenant_id уже в JWT токене
   - Для остальных запросов используйте только `Authorization: Bearer {token}`

2. **Где хранить Tenant ID:**
   - В `.env` файле (рекомендуется)
   - В конфиге приложения
   - НЕ в коде напрямую

3. **После логина:**
   - Все запросы используют только `Authorization` header
   - Tenant ID автоматически извлекается из JWT токена

## Получение Tenant ID

Если вы не знаете Tenant ID, его можно получить:

1. Из скрипта инициализации (был выведен при создании админа)
2. Через API (если есть доступ):
   ```bash
   GET /api/v1/admin/tenants
   ```
3. Из базы данных:
   ```sql
   SELECT id, name, slug FROM tenants;
   ```

## Пример полного flow

```javascript
// 1. Login с X-Tenant-ID
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Tenant-ID': '2348d266-596f-420f-b046-a63ca3b504f9',
  },
  body: JSON.stringify({
    email: 'admin@example.com',
    password: 'admin123',
  }),
})

const { tokens, user } = await loginResponse.json()

// 2. Сохранить токены
localStorage.setItem('access_token', tokens.access_token)

// 3. Все последующие запросы - БЕЗ X-Tenant-ID
const articlesResponse = await fetch('/api/v1/admin/articles', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`,
    // X-Tenant-ID НЕ нужен!
  },
})
```



Проверяю, как определить tenant на новом устройстве и зачем нужен tenant_id:


[3 tools called]


## Зачем нужен Tenant ID?

Tenant ID нужен для multi-tenancy — изоляции данных между клиентами. Один backend обслуживает несколько организаций, и каждая должна видеть только свои данные.

```
┌─────────────────────────────────────┐
│         Backend (один)              │
├─────────────────────────────────────┤
│  Tenant A (Компания 1)              │
│  ├─ Users: user1@company1.com       │
│  ├─ Articles: 50                    │
│  └─ Services: 10                    │
├─────────────────────────────────────┤
│  Tenant B (Компания 2)              │
│  ├─ Users: user2@company2.com      │
│  ├─ Articles: 30                    │
│  └─ Services: 5                     │
└─────────────────────────────────────┘
```

Без tenant_id бекенд не поймет, к какому tenant относится пользователь.

## Как получить Tenant ID на новом устройстве?

### Вариант 1: По домену (рекомендуется)

Если у каждого tenant свой домен (например, `client1.example.com`, `client2.example.com`), можно определить автоматически:

```javascript
// При загрузке страницы логина
const getTenantByDomain = async () => {
  const domain = window.location.hostname // "client1.example.com"
  
  // Публичный эндпоинт (нужно добавить на бекенде)
  const response = await fetch(
    `/api/v1/public/tenants/by-domain?domain=${domain}`
  )
  
  if (response.ok) {
    const tenant = await response.json()
    return tenant.id
  }
  
  return null
}

// На странице логина
useEffect(() => {
  const initTenant = async () => {
    const tenantId = await getTenantByDomain()
    if (tenantId) {
      localStorage.setItem('tenant_id', tenantId)
    }
  }
  initTenant()
}, [])
```

Нужно добавить на бекенде:

```python
# В tenants/router.py
@router.get("/public/tenants/by-domain", response_model=TenantResponse)
async def get_tenant_by_domain(
    domain: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Get tenant by domain (public endpoint for login)."""
    service = TenantService(db)
    tenant = await service.get_by_domain(domain)
    return TenantResponse.model_validate(tenant)
```

### Вариант 2: По email пользователя

Если email уникален в рамках tenant, можно определить tenant по email:

```javascript
// Перед логином - определить tenant по email
const getTenantByEmail = async (email) => {
  const response = await fetch(
    `/api/v1/public/tenants/by-email?email=${encodeURIComponent(email)}`
  )
  
  if (response.ok) {
    const tenant = await response.json()
    return tenant.id
  }
  
  return null
}

// В форме логина
const handleLogin = async (email, password) => {
  // 1. Определить tenant по email
  let tenantId = localStorage.getItem('tenant_id')
  
  if (!tenantId) {
    tenantId = await getTenantByEmail(email)
    if (tenantId) {
      localStorage.setItem('tenant_id', tenantId)
    } else {
      throw new Error('Tenant not found for this email')
    }
  }
  
  // 2. Логин с tenant_id
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': tenantId,
    },
    body: JSON.stringify({ email, password }),
  })
  
  return response.json()
}
```

### Вариант 3: Форма выбора tenant

Если у пользователя доступ к нескольким tenant'ам:

```javascript
// Компонент выбора tenant перед логином
const TenantSelector = ({ onSelect }) => {
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    // Получить список tenant'ов (публичный эндпоинт)
    fetch('/api/v1/public/tenants')
      .then(res => res.json())
      .then(data => {
        setTenants(data.items)
        setLoading(false)
      })
  }, [])
  
  const handleSelect = (tenantId) => {
    localStorage.setItem('tenant_id', tenantId)
    onSelect(tenantId)
  }
  
  if (loading) return <div>Loading...</div>
  
  return (
    <div>
      <h2>Выберите организацию</h2>
      {tenants.map(tenant => (
        <button 
          key={tenant.id} 
          onClick={() => handleSelect(tenant.id)}
        >
          {tenant.name}
        </button>
      ))}
    </div>
  )
}
```

### Вариант 4: Комбинированный подход (лучший)

Определять автоматически, с возможностью выбора:

```javascript
// utils/tenant.js
export const getTenantId = async () => {
  // 1. Проверить localStorage (если уже логинились)
  let tenantId = localStorage.getItem('tenant_id')
  if (tenantId) return tenantId
  
  // 2. Попробовать определить по домену
  const domain = window.location.hostname
  if (domain !== 'localhost' && domain !== '127.0.0.1') {
    try {
      const response = await fetch(
        `/api/v1/public/tenants/by-domain?domain=${domain}`
      )
      if (response.ok) {
        const tenant = await response.json()
        tenantId = tenant.id
        localStorage.setItem('tenant_id', tenantId)
        return tenantId
      }
    } catch (e) {
      console.warn('Could not determine tenant by domain', e)
    }
  }
  
  // 3. Если не удалось - показать форму выбора
  return null
}

// В компоненте логина
const LoginPage = () => {
  const [tenantId, setTenantId] = useState(null)
  const [showTenantSelector, setShowTenantSelector] = useState(false)
  
  useEffect(() => {
    getTenantId().then(id => {
      if (id) {
        setTenantId(id)
      } else {
        setShowTenantSelector(true)
      }
    })
  }, [])
  
  if (showTenantSelector) {
    return <TenantSelector onSelect={(id) => {
      setTenantId(id)
      setShowTenantSelector(false)
    }} />
  }
  
  return <LoginForm tenantId={tenantId} />
}
```

## Рекомендуемое решение

Для production лучше использовать вариант 1 (по домену):

1. Каждый tenant имеет свой домен: `client1.example.com`, `client2.example.com`
2. На фронтенде автоматически определяем tenant по домену
3. Сохраняем в localStorage для следующих разов
4. Если не удалось определить — показываем форму выбора

## Что нужно добавить на бекенде

1. Публичный эндпоинт для получения tenant по домену
2. Метод в сервисе `get_by_domain`

```python
# В tenants/service.py добавить:
async def get_by_domain(self, domain: str) -> Tenant:
    """Get tenant by domain."""
    stmt = (
        select(Tenant)
        .where(Tenant.domain == domain)
        .where(Tenant.is_active.is_(True))
        .where(Tenant.deleted_at.is_(None))
    )
    result = await self.db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise NotFoundError("Tenant", domain)
    
    return tenant
```

## Итог

- Зачем нужен: изоляция данных между клиентами (multi-tenancy)
- Откуда брать на новом устройстве:
  - По домену (автоматически)
  - По email (если уникален)
  - Через форму выбора
  - Из localStorage (если уже логинились)

Рекомендация: использовать определение по домену + сохранение в localStorage. Это работает на любом устройстве без дополнительных действий от пользователя.